from ninja_extra import NinjaExtraAPI, api_controller, http_get, http_post
from django.conf import settings
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any

# keep your existing schemas for ask
from .schemas import AskIn, AskOut, Source

# NEW: minimal ingest DTOs local to this router to avoid breaking your existing schemas
class IngestIn(BaseModel):
    tenant_id: str
    url: HttpUrl
    max_pages: int = 200
    crawler_type: str = "llm"  # "comprehensive" or "llm"
    max_depth: int = 5  # Only used with LLM crawler

class IngestOut(BaseModel):
    job_id: str | int
    docs: int
    chunks: int
    message: str | None = None

class TenantStatsOut(BaseModel):
    documents: int
    chunks: int
    total_size: str
    total_bytes: int

# LangGraph (our crawl→extract→vectorize graph)
from apps.pipelines.langgraph.graph import build_graph
from apps.pipelines.schemas import PipelineState

# Celery task for async ingestion
from apps.vectorizer.tasks import ingest_task

# RAG pieces
from apps.vectorizer.embedder import embed_texts
from apps.vectorizer.supabase_store import hybrid_search, get_tenant_stats, cleanup_tenant_data
from openai import OpenAI

# Activity audit
from apps.tenants.models import ActivityAudit

# Prompt service for organization-specific prompts
from .services.prompt_service import PromptService
# Moderation service for content filtering
from .services.moderation_service import ModerationService

# You previously imported a different graph (for Q/A) here:
# from .services.langgraph_pipeline import graph
# We now use build_graph() for ingestion pipeline, and do RAG explicitly for /ask.

api = NinjaExtraAPI(title="KnowledgeInjester API", version="0.1.0")

# LLM client
_llm = OpenAI()

@api_controller("", tags=["meta"])
class MetaController:
    @http_get("/healthz")
    def healthz(self):
        # keep your ENV passthrough
        return {"status": "ok", "env": getattr(settings, "ENV", "dev")}
    
    @http_get("/debug/urls")
    def debug_urls(self):
        """Debug endpoint to check configured URL patterns"""
        from django.urls import get_resolver
        resolver = get_resolver()
        url_patterns = []
        
        def extract_patterns(patterns, prefix=""):
            for pattern in patterns:
                if hasattr(pattern, 'pattern'):
                    url_patterns.append(f"{prefix}{pattern.pattern}")
                if hasattr(pattern, 'url_patterns'):
                    extract_patterns(pattern.url_patterns, f"{prefix}{pattern.pattern}")
        
        extract_patterns(resolver.url_patterns)
        return {"url_patterns": url_patterns}

@api_controller("v1", tags=["admin"])
class AdminController:
    @http_get("/admin/stats/{tenant_id}", response=TenantStatsOut)
    def get_tenant_stats(self, request, tenant_id: str):
        """Get statistics for a tenant's data."""
        try:
            stats = get_tenant_stats(tenant_id)
            return TenantStatsOut(**stats)
        except Exception as e:
            return {"error": f"Failed to get stats: {str(e)}"}
    
    @http_post("/admin/cleanup/{tenant_id}")
    def cleanup_tenant(self, request, tenant_id: str):
        """Clean up all data for a tenant."""
        try:
            deleted_docs, deleted_chunks = cleanup_tenant_data(tenant_id)
            
            # Log the cleanup activity
            ActivityAudit.objects.create(
                tenant_id=tenant_id,
                activity_type='cleanup',
                performed_by='admin',
                details={
                    'deleted_documents': deleted_docs,
                    'deleted_chunks': deleted_chunks,
                    'operation': 'tenant_cleanup'
                }
            )
            
            return {
                "message": f"Cleaned up {deleted_docs} documents and {deleted_chunks} chunks",
                "deleted_documents": deleted_docs,
                "deleted_chunks": deleted_chunks
            }
        except Exception as e:
            return {"error": f"Failed to cleanup: {str(e)}"}

def process_citations(hits, answer, enable_citations=True):
    """
    Process citations and return filtered sources with continuous numbering.
    If enable_citations is False, return None for sources.
    """
    if not enable_citations:
        return None
    
    # Deduplicate by document (source_url) and create stable source enumeration
    unique_docs = {}
    for hit in hits:
        source_url = hit.get('source_url', '')
        if source_url not in unique_docs:
            unique_docs[source_url] = {
                'title': hit.get('title', ''),
                'url': source_url,
                'chunks': []
            }
        unique_docs[source_url]['chunks'].append(hit.get('text', ''))
    
    # Create stable source list (limit to 3-5 most relevant sources)
    sources = []
    source_index = 1
    for source_url, doc_info in list(unique_docs.items())[:5]:
        sources.append({
            'index': source_index,
            'title': doc_info['title'] or source_url,
            'url': source_url
        })
        source_index += 1

    # Check if the response contains any citation numbers like [1], [2], etc.
    import re
    citation_pattern = r'\[\d+\]'
    has_citations = bool(re.search(citation_pattern, answer))
    
    # Only include sources if the response actually contains citations
    source_objects = None
    if has_citations and sources:
        # Extract all citation numbers from the response
        citation_matches = re.findall(r'\[(\d+)\]', answer)
        referenced_indices = set(int(match) for match in citation_matches)
        
        # Filter sources that are actually referenced
        referenced_sources = []
        for source in sources:
            if source['index'] in referenced_indices:
                referenced_sources.append(source)
        
        # Sort by original index to maintain order
        referenced_sources.sort(key=lambda x: x['index'])
        
        # Create continuous numbering mapping
        index_mapping = {}
        source_objects = []
        for i, source in enumerate(referenced_sources, 1):
            old_index = source['index']
            new_index = i
            index_mapping[old_index] = new_index
            
            source_objects.append(Source(
                index=new_index,
                title=source['title'],
                url=source['url']
            ))
        
        # Remap citation numbers in the response text to continuous sequence
        def replace_citation(match):
            old_num = int(match.group(1))
            if old_num in index_mapping:
                return f"[{index_mapping[old_num]}]"
            return match.group(0)  # Keep original if not found
        
        answer = re.sub(r'\[(\d+)\]', replace_citation, answer)
    
    return source_objects, answer

@api_controller("v1", tags=["ask"])
class AskController:
    @http_post("/ask", response=AskOut)
    def ask(self, request, payload: AskIn):
        """
        Updated: hybrid retrieval (pgvector cosine + FTS) then call LLM.
        AskIn should have: messages (List[MessageContent]), and optionally tenant_id (str) and citations (bool).
        If tenant_id is not provided, we default to 'public'.
        If citations is not provided, we default to True.
        Extracts the latest user message from the messages array.
        """
        tenant_id = payload.tenant_id
        enable_citations = payload.citations
        print(f"DEBUG: Ask request - tenant_id: {tenant_id}, enable_citations: {enable_citations}")
        # Extract the latest user message from the messages array
        user_messages = [msg for msg in payload.messages if msg.role == "user"]
        if not user_messages:
            return AskOut(error="No user message found in the messages array.")
        
        question = user_messages[-1].text.strip()  # Get the latest user message
        
        print(f"DEBUG: Ask request - tenant_id: {tenant_id}, question: {question}")
        print(f"DEBUG: Total messages: {len(payload.messages)}, user messages: {len(user_messages)}")

        # Moderate the question content
        moderation_service = ModerationService()
        moderation_result = moderation_service.moderate_question(question)
        
        if not moderation_result["is_appropriate"]:
            print(f"DEBUG: Question flagged by moderation: {moderation_result['reason']}")
            return AskOut(
                text=moderation_result["response"],
                role="assistant",
                sources=None
            )

        # Embed question once
        qvec = embed_texts([question])[0]
        print(f"DEBUG: Generated embedding vector of length: {len(qvec)}")

        # Retrieve hybrid hits
        top_k = getattr(settings, "RETRIEVAL_TOP_K", 6)
        print(f"DEBUG: Searching with top_k: {top_k}")
        hits = hybrid_search(tenant_id, question, qvec, top_k=top_k)
        print(f"DEBUG: Found {len(hits)} hits from hybrid_search")
        
        # Debug: Print details of each hit
        for i, hit in enumerate(hits):
            print(f"DEBUG: Hit {i+1}: score={hit.get('score', 'N/A'):.4f}, sim={hit.get('sim', 'N/A'):.4f}, fts_rank={hit.get('fts_rank', 'N/A'):.4f}")
            print(f"DEBUG: Hit {i+1}: title='{hit.get('title', 'N/A')}', source_url='{hit.get('source_url', 'N/A')}'")
            print(f"DEBUG: Hit {i+1}: text preview='{hit.get('text', '')[:100]}...'")
            print("---")

        # Build context based on citations flag
        if enable_citations:
            # Deduplicate by document (source_url) and create stable source enumeration
            unique_docs = {}
            for hit in hits:
                source_url = hit.get('source_url', '')
                if source_url not in unique_docs:
                    unique_docs[source_url] = {
                        'title': hit.get('title', ''),
                        'url': source_url,
                        'chunks': []
                    }
                unique_docs[source_url]['chunks'].append(hit.get('text', ''))
            
            # Create stable source list (limit to 3-5 most relevant sources)
            sources = []
            source_index = 1
            for source_url, doc_info in list(unique_docs.items())[:5]:
                sources.append({
                    'index': source_index,
                    'title': doc_info['title'] or source_url,
                    'url': source_url
                })
                source_index += 1

            # Build context with stable source numbering
            context_parts = []
            for source_url, doc_info in list(unique_docs.items())[:5]:
                source_num = next(s['index'] for s in sources if s['url'] == source_url)
                # Combine all chunks from the same document
                combined_text = '\n\n'.join(doc_info['chunks'])
                context_parts.append(f"[{source_num}] {doc_info['title'] or source_url}\n{combined_text}")
            
            context = "\n\n".join(context_parts)
            
            # Build source list for the prompt
            source_list = "\n".join([f"[{s['index']}] {s['title']} - {s['url']}" for s in sources])

            # Use organization-specific prompt with fallback to default
            prompt = PromptService.get_prompt_for_organization(
                tenant_id=tenant_id,
                enable_citations=enable_citations,
                context=context,
                question=question,
                sources=source_list
            )
        else:
            # Simple context without citations
            context_parts = []
            for i, hit in enumerate(hits):
                context_parts.append(f"{hit.get('title', '') or hit.get('source_url', '')}\n{hit.get('text', '')}")
            
            context = "\n\n".join(context_parts)

            # Use organization-specific prompt with fallback to default
            prompt = PromptService.get_prompt_for_organization(
                tenant_id=tenant_id,
                enable_citations=enable_citations,
                context=context,
                question=question,
                sources=""
            )
        
        print(f"DEBUG: Built context length: {len(context)} characters")
        print(f"DEBUG: Context preview: {context[:200]}...")
        print(f"DEBUG: Citations enabled: {enable_citations}")

        try:
            resp = _llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            answer = resp.choices[0].message.content

            # Process citations based on the flag
            if enable_citations:
                source_objects, answer = process_citations(hits, answer, enable_citations=True)
            else:
                source_objects = None

            # Return in the new format with sources only if citations are enabled and present
            return AskOut(text=answer, role="assistant", sources=source_objects)
        except Exception as e:
            return AskOut(error=f"Error generating response: {str(e)}")


@api_controller("v1", tags=["ingest"])
class IngestController:
    @http_post("/ingest", response=IngestOut)
    def ingest(self, request, payload: IngestIn):
        """
        New: Small jobs run synchronously via graph.invoke; larger ones enqueue Celery.
        """
        try:
            threshold = 80  # pages
            url_str = str(payload.url)
            print(f"DEBUG: Starting ingest for {url_str} with max_pages={payload.max_pages}")

            if payload.max_pages <= threshold:
                print("DEBUG: Building graph...")
                graph = build_graph()
                print("DEBUG: Graph built successfully")
                
                print("DEBUG: Creating pipeline state...")
                state = PipelineState(
                    tenant_id=payload.tenant_id,
                    root_url=url_str,
                    max_pages=payload.max_pages,
                    crawler_type=payload.crawler_type,
                    max_depth=payload.max_depth,
                )
                print(f"DEBUG: Pipeline state created: {type(state)}")
                
                print("DEBUG: Invoking graph...")
                final_state = graph.invoke(state)
                print(f"DEBUG: Graph invoked successfully, final_state type: {type(final_state)}")
                
                # LangGraph returns state as a dictionary, not a PipelineState object
                if isinstance(final_state, dict):
                    print(f"DEBUG: final_state is dict, keys: {final_state.keys()}")
                    out = final_state.get("result") or final_state.get("vectorization_summary") or {"docs": 0, "chunks": 0}
                else:
                    print(f"DEBUG: final_state.result = {getattr(final_state, 'result', 'NOT_FOUND')}")
                    print(f"DEBUG: final_state.vectorization_summary = {getattr(final_state, 'vectorization_summary', 'NOT_FOUND')}")
                    out = final_state.result or final_state.vectorization_summary or {"docs": 0, "chunks": 0}
                print(f"DEBUG: Final out = {out}")
                
                # Log the ingest activity
                ActivityAudit.objects.create(
                    tenant_id=payload.tenant_id,
                    activity_type='ingest',
                    performed_by='admin',
                    details={
                        'url': str(payload.url),
                        'max_pages': payload.max_pages,
                        'docs_processed': out.get("docs", 0),
                        'chunks_created': out.get("chunks", 0),
                        'operation': 'sync_ingest'
                    }
                )
                
                return IngestOut(job_id=0, docs=out.get("docs", 0), chunks=out.get("chunks", 0), message="sync")
            else:
                async_res = ingest_task.delay(
                    payload.tenant_id, 
                    url_str, 
                    payload.max_pages,
                    payload.crawler_type,
                    payload.max_depth
                )
                
                # Log the async ingest activity
                ActivityAudit.objects.create(
                    tenant_id=payload.tenant_id,
                    activity_type='ingest',
                    performed_by='admin',
                    details={
                        'url': str(payload.url),
                        'max_pages': payload.max_pages,
                        'job_id': async_res.id,
                        'operation': 'async_ingest'
                    }
                )
                
                # return Celery task id so the caller can poll if they want
                return IngestOut(job_id=async_res.id, docs=0, chunks=0, message="enqueued")
        except Exception as e:
            import traceback
            print(f"DEBUG: Exception caught: {e}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return IngestOut(job_id=-1, docs=0, chunks=0, message=f"error: {e}")

api.register_controllers(MetaController, AskController, IngestController, AdminController)
