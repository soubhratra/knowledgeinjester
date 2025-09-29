from ninja_extra import NinjaExtraAPI, api_controller, http_get, http_post
from django.conf import settings
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any
import logging
import time
import uuid
from datetime import datetime
import traceback

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

# LangSmith tracing
try:
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    def traceable(func):
        return func

# Activity audit
from apps.tenants.models import ActivityAudit, Organization

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

# Structured logging setup
logger = logging.getLogger('apps.api')

def log_request_start(endpoint: str, request_id: str, tenant_id: str = None, **kwargs):
    """Log the start of an API request with structured data"""
    log_data = {
        'event_type': 'request_start',
        'request_id': request_id,
        'endpoint': endpoint,
        'timestamp': datetime.utcnow().isoformat(),
        'tenant_id': tenant_id,
        **kwargs
    }
    logger.info('API request started', extra=log_data)

def log_request_end(endpoint: str, request_id: str, duration_ms: float, status: str, tenant_id: str = None, **kwargs):
    """Log the end of an API request with structured data"""
    log_data = {
        'event_type': 'request_end',
        'request_id': request_id,
        'endpoint': endpoint,
        'duration_ms': duration_ms,
        'status': status,
        'timestamp': datetime.utcnow().isoformat(),
        'tenant_id': tenant_id,
        **kwargs
    }
    logger.info('API request completed', extra=log_data)

def log_error(endpoint: str, request_id: str, error: Exception, tenant_id: str = None, **kwargs):
    """Log errors with structured data and stack trace"""
    log_data = {
        'event_type': 'error',
        'request_id': request_id,
        'endpoint': endpoint,
        'error_type': type(error).__name__,
        'error_message': str(error),
        'stack_trace': traceback.format_exc(),
        'timestamp': datetime.utcnow().isoformat(),
        'tenant_id': tenant_id,
        **kwargs
    }
    logger.error('API error occurred', extra=log_data)

def log_business_metric(event_type: str, tenant_id: str, **kwargs):
    """Log business metrics for analytics"""
    log_data = {
        'event_type': f'business_{event_type}',
        'tenant_id': tenant_id,
        'timestamp': datetime.utcnow().isoformat(),
        **kwargs
    }
    logger.info(f'Business metric: {event_type}', extra=log_data)

def log_performance_metric(operation: str, duration_ms: float, tenant_id: str = None, **kwargs):
    """Log performance metrics"""
    log_data = {
        'event_type': 'performance',
        'operation': operation,
        'duration_ms': duration_ms,
        'timestamp': datetime.utcnow().isoformat(),
        'tenant_id': tenant_id,
        **kwargs
    }
    logger.info(f'Performance metric: {operation}', extra=log_data)

@api_controller("", tags=["meta"])
class MetaController:
    @http_get("/healthz")
    def healthz(self, request):
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        log_request_start("healthz", request_id)
        
        try:
            result = {"status": "ok", "env": getattr(settings, "ENV", "dev")}
            duration_ms = (time.time() - start_time) * 1000
            
            log_request_end("healthz", request_id, duration_ms, "success")
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error("healthz", request_id, e)
            log_request_end("healthz", request_id, duration_ms, "error")
            raise
    
    @http_get("/debug/urls")
    def debug_urls(self, request):
        """Debug endpoint to check configured URL patterns"""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        log_request_start("debug_urls", request_id)
        
        try:
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
            result = {"url_patterns": url_patterns}
            duration_ms = (time.time() - start_time) * 1000
            
            log_request_end("debug_urls", request_id, duration_ms, "success", 
                          url_pattern_count=len(url_patterns))
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error("debug_urls", request_id, e)
            log_request_end("debug_urls", request_id, duration_ms, "error")
            raise

@api_controller("v1", tags=["admin"])
class AdminController:
    @http_get("/admin/stats/{tenant_id}", response=TenantStatsOut)
    def get_tenant_stats(self, request, tenant_id: str):
        """Get statistics for a tenant's data."""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        log_request_start("get_tenant_stats", request_id, tenant_id=tenant_id)
        
        try:
            stats = get_tenant_stats(tenant_id)
            result = TenantStatsOut(**stats)
            duration_ms = (time.time() - start_time) * 1000
            
            log_request_end("get_tenant_stats", request_id, duration_ms, "success", 
                          tenant_id=tenant_id, documents=stats.get('documents', 0), 
                          chunks=stats.get('chunks', 0))
            log_business_metric("stats_retrieved", tenant_id, 
                              documents=stats.get('documents', 0), 
                              chunks=stats.get('chunks', 0),
                              total_bytes=stats.get('total_bytes', 0))
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error("get_tenant_stats", request_id, e, tenant_id=tenant_id)
            log_request_end("get_tenant_stats", request_id, duration_ms, "error", 
                          tenant_id=tenant_id)
            return {"error": f"Failed to get stats: {str(e)}"}
    
    @http_post("/admin/cleanup/{tenant_id}")
    def cleanup_tenant(self, request, tenant_id: str):
        """Clean up all data for a tenant."""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        log_request_start("cleanup_tenant", request_id, tenant_id=tenant_id)
        
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
            
            result = {
                "message": f"Cleaned up {deleted_docs} documents and {deleted_chunks} chunks",
                "deleted_documents": deleted_docs,
                "deleted_chunks": deleted_chunks
            }
            duration_ms = (time.time() - start_time) * 1000
            
            log_request_end("cleanup_tenant", request_id, duration_ms, "success", 
                          tenant_id=tenant_id, deleted_documents=deleted_docs, 
                          deleted_chunks=deleted_chunks)
            log_business_metric("tenant_cleanup", tenant_id, 
                              deleted_documents=deleted_docs, 
                              deleted_chunks=deleted_chunks)
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error("cleanup_tenant", request_id, e, tenant_id=tenant_id)
            log_request_end("cleanup_tenant", request_id, duration_ms, "error", 
                          tenant_id=tenant_id)
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
    @traceable(name="ask_endpoint")
    def ask(self, request, payload: AskIn):
        """
        Updated: hybrid retrieval (pgvector cosine + FTS) then call LLM.
        AskIn should have: messages (List[MessageContent]), tenant_id (str), and optionally citations (bool).
        If citations is not provided, we default to True.
        Extracts the latest user message from the messages array.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        tenant_id = payload.tenant_id
        enable_citations = payload.citations
        
        log_request_start("ask", request_id, tenant_id=tenant_id, 
                         enable_citations=enable_citations, 
                         total_messages=len(payload.messages))
        
        try:
            # Validate tenant_id exists in the database
            try:
                organization = Organization.objects.get(tenant_id=tenant_id)
            except Organization.DoesNotExist:
                logger.warning("Invalid tenant_id provided", extra={
                    'event_type': 'invalid_tenant',
                    'request_id': request_id,
                    'tenant_id': tenant_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
                duration_ms = (time.time() - start_time) * 1000
                log_request_end("ask", request_id, duration_ms, "invalid_tenant", tenant_id=tenant_id)
                return AskOut(
                    text="Invalid tenant ID. Please contact your administrator.",
                    role="assistant",
                    sources=None
                )
            # Extract the latest user message from the messages array
            user_messages = [msg for msg in payload.messages if msg.role == "user"]
            if not user_messages:
                log_error("ask", request_id, ValueError("No user message found"), tenant_id=tenant_id)
                return AskOut(error="No user message found in the messages array.")
            
            question = user_messages[-1].text.strip()  # Get the latest user message
            
            logger.info("Ask request details", extra={
                'event_type': 'ask_request_details',
                'request_id': request_id,
                'tenant_id': tenant_id,
                'question_length': len(question),
                'question_preview': question[:100] + "..." if len(question) > 100 else question,
                'total_messages': len(payload.messages),
                'user_messages': len(user_messages),
                'enable_citations': enable_citations,
                'timestamp': datetime.utcnow().isoformat()
            })

            # Moderate the question content
            moderation_start = time.time()
            moderation_service = ModerationService()
            moderation_result = moderation_service.moderate_question(question)
            moderation_duration = (time.time() - moderation_start) * 1000
            
            log_performance_metric("moderation", moderation_duration, tenant_id=tenant_id)
            
            if not moderation_result["is_appropriate"]:
                logger.warning("Question flagged by moderation", extra={
                    'event_type': 'moderation_flagged',
                    'request_id': request_id,
                    'tenant_id': tenant_id,
                    'reason': moderation_result['reason'],
                    'question_preview': question[:100] + "..." if len(question) > 100 else question,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                duration_ms = (time.time() - start_time) * 1000
                log_request_end("ask", request_id, duration_ms, "moderation_flagged", 
                              tenant_id=tenant_id, moderation_reason=moderation_result['reason'])
                return AskOut(
                    text=moderation_result["response"],
                    role="assistant",
                    sources=None
                )

            # Embed question once
            embedding_start = time.time()
            qvec = embed_texts([question])[0]
            embedding_duration = (time.time() - embedding_start) * 1000
            
            log_performance_metric("embedding", embedding_duration, tenant_id=tenant_id, 
                                 vector_length=len(qvec))

            # Retrieve hybrid hits
            search_start = time.time()
            top_k = getattr(settings, "RETRIEVAL_TOP_K", 6)
            hits = hybrid_search(tenant_id, question, qvec, top_k=top_k)
            search_duration = (time.time() - search_start) * 1000
            
            log_performance_metric("hybrid_search", search_duration, tenant_id=tenant_id, 
                                 top_k=top_k, hits_found=len(hits))
            
            # Log search results details
            logger.info("Search results", extra={
                'event_type': 'search_results',
                'request_id': request_id,
                'tenant_id': tenant_id,
                'hits_found': len(hits),
                'top_k': top_k,
                'search_duration_ms': search_duration,
                'hits_details': [
                    {
                        'index': i+1,
                        'score': hit.get('score'),
                        'sim': hit.get('sim'),
                        'fts_rank': hit.get('fts_rank'),
                        'title': hit.get('title', ''),
                        'source_url': hit.get('source_url', ''),
                        'text_length': len(hit.get('text', ''))
                    }
                    for i, hit in enumerate(hits)
                ],
                'timestamp': datetime.utcnow().isoformat()
            })

            # Build context based on citations flag
            context_start = time.time()
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
            
            context_duration = (time.time() - context_start) * 1000
            
            logger.info("Context built", extra={
                'event_type': 'context_built',
                'request_id': request_id,
                'tenant_id': tenant_id,
                'context_length': len(context),
                'context_duration_ms': context_duration,
                'citations_enabled': enable_citations,
                'unique_sources': len(unique_docs) if enable_citations else len(hits),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            log_performance_metric("context_building", context_duration, tenant_id=tenant_id, 
                                 context_length=len(context), citations_enabled=enable_citations)

            # Create a traced LLM call
            llm_start = time.time()
            if LANGSMITH_AVAILABLE:
                from langsmith import traceable
                
                @traceable(name="llm_chat_completion")
                def call_llm(prompt_text):
                    return _llm.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt_text}],
                        temperature=0.2,
                    )
                
                resp = call_llm(prompt)
            else:
                resp = _llm.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
            llm_duration = (time.time() - llm_start) * 1000
            
            answer = resp.choices[0].message.content
            
            log_performance_metric("llm_completion", llm_duration, tenant_id=tenant_id, 
                                 model="gpt-4o-mini", answer_length=len(answer))

            # Process citations based on the flag
            citation_start = time.time()
            if enable_citations:
                source_objects, answer = process_citations(hits, answer, enable_citations=True)
            else:
                source_objects = None
            citation_duration = (time.time() - citation_start) * 1000
            
            log_performance_metric("citation_processing", citation_duration, tenant_id=tenant_id, 
                                 citations_enabled=enable_citations, 
                                 sources_count=len(source_objects) if source_objects else 0)

            # Log successful completion
            duration_ms = (time.time() - start_time) * 1000
            log_request_end("ask", request_id, duration_ms, "success", 
                          tenant_id=tenant_id, answer_length=len(answer),
                          sources_count=len(source_objects) if source_objects else 0)
            
            log_business_metric("question_answered", tenant_id, 
                              question_length=len(question),
                              answer_length=len(answer),
                              sources_used=len(source_objects) if source_objects else 0,
                              citations_enabled=enable_citations)

            # Return in the new format with sources only if citations are enabled and present
            return AskOut(text=answer, role="assistant", sources=source_objects)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error("ask", request_id, e, tenant_id=tenant_id)
            log_request_end("ask", request_id, duration_ms, "error", tenant_id=tenant_id)
            return AskOut(error=f"Error generating response: {str(e)}")


@api_controller("v1", tags=["ingest"])
class IngestController:
    @http_post("/ingest", response=IngestOut)
    def ingest(self, request, payload: IngestIn):
        """
        New: Small jobs run synchronously via graph.invoke; larger ones enqueue Celery.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        url_str = str(payload.url)
        log_request_start("ingest", request_id, tenant_id=payload.tenant_id, 
                         url=url_str, max_pages=payload.max_pages, 
                         crawler_type=payload.crawler_type, max_depth=payload.max_depth)
        
        try:
            threshold = 80  # pages
            
            logger.info("Starting ingest operation", extra={
                'event_type': 'ingest_started',
                'request_id': request_id,
                'tenant_id': payload.tenant_id,
                'url': url_str,
                'max_pages': payload.max_pages,
                'crawler_type': payload.crawler_type,
                'max_depth': payload.max_depth,
                'threshold': threshold,
                'timestamp': datetime.utcnow().isoformat()
            })

            if payload.max_pages <= threshold:
                # Synchronous processing
                graph_start = time.time()
                graph = build_graph()
                graph_duration = (time.time() - graph_start) * 1000
                
                log_performance_metric("graph_building", graph_duration, tenant_id=payload.tenant_id)
                
                state = PipelineState(
                    tenant_id=payload.tenant_id,
                    root_url=url_str,
                    max_pages=payload.max_pages,
                    crawler_type=payload.crawler_type,
                    max_depth=payload.max_depth,
                )
                
                pipeline_start = time.time()
                final_state = graph.invoke(state)
                pipeline_duration = (time.time() - pipeline_start) * 1000
                
                log_performance_metric("pipeline_execution", pipeline_duration, tenant_id=payload.tenant_id,
                                     max_pages=payload.max_pages, crawler_type=payload.crawler_type)
                
                # LangGraph returns state as a dictionary, not a PipelineState object
                if isinstance(final_state, dict):
                    out = final_state.get("result") or final_state.get("vectorization_summary") or {"docs": 0, "chunks": 0}
                else:
                    out = final_state.result or final_state.vectorization_summary or {"docs": 0, "chunks": 0}
                
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
                
                result = IngestOut(job_id=0, docs=out.get("docs", 0), chunks=out.get("chunks", 0), message="sync")
                duration_ms = (time.time() - start_time) * 1000
                
                log_request_end("ingest", request_id, duration_ms, "success", 
                              tenant_id=payload.tenant_id, operation_type="sync",
                              docs_processed=out.get("docs", 0), chunks_created=out.get("chunks", 0))
                
                log_business_metric("ingest_completed", payload.tenant_id, 
                                  operation_type="sync", url=url_str,
                                  docs_processed=out.get("docs", 0), 
                                  chunks_created=out.get("chunks", 0),
                                  max_pages=payload.max_pages)
                
                return result
            else:
                # Asynchronous processing
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
                
                result = IngestOut(job_id=async_res.id, docs=0, chunks=0, message="enqueued")
                duration_ms = (time.time() - start_time) * 1000
                
                log_request_end("ingest", request_id, duration_ms, "success", 
                              tenant_id=payload.tenant_id, operation_type="async",
                              job_id=async_res.id)
                
                log_business_metric("ingest_enqueued", payload.tenant_id, 
                                  operation_type="async", url=url_str,
                                  job_id=async_res.id, max_pages=payload.max_pages)
                
                return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error("ingest", request_id, e, tenant_id=payload.tenant_id, 
                     url=url_str, max_pages=payload.max_pages)
            log_request_end("ingest", request_id, duration_ms, "error", 
                          tenant_id=payload.tenant_id)
            return IngestOut(job_id=-1, docs=0, chunks=0, message=f"error: {e}")

api.register_controllers(MetaController, AskController, IngestController, AdminController)
