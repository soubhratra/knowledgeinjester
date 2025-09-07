from ninja_extra import NinjaExtraAPI, api_controller, http_get, http_post
from django.conf import settings
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any

# keep your existing schemas for ask/crawl
from .schemas import AskIn, AskOut, CrawlIn, CrawlOut

# NEW: minimal ingest DTOs local to this router to avoid breaking your existing schemas
class IngestIn(BaseModel):
    tenant_id: str
    url: HttpUrl
    max_pages: int = 200

class IngestOut(BaseModel):
    job_id: str | int
    docs: int
    chunks: int
    message: str | None = None

# LangGraph (our crawl→extract→vectorize graph)
from apps.pipelines.langgraph.graph import build_graph
from apps.pipelines.schemas import PipelineState

# Celery task for async ingestion
from apps.vectorizer.tasks import ingest_task

# RAG pieces
from apps.vectorizer.embedder import embed_texts
from apps.vectorizer.supabase_store import hybrid_search
from openai import OpenAI

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

@api_controller("v1", tags=["ask"])
class AskController:
    @http_post("/ask", response=AskOut)
    def ask(self, request, payload: AskIn):
        """
        Updated: hybrid retrieval (pgvector cosine + FTS) then call LLM.
        AskIn should have: question (str), and optionally tenant_id (str).
        If tenant_id is not provided, we default to 'public'.
        """
        tenant_id = payload.tenant_id
        question = payload.question.strip()
        
        print(f"DEBUG: Ask request - tenant_id: {tenant_id}, question: {question}")

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

        # Build short, source-cited context
        context = "\n\n".join(
            f"[{i+1}] {h.get('title') or h.get('source_url')}\n{h.get('text','')}"
            for i, h in enumerate(hits)
        )
        print(f"DEBUG: Built context length: {len(context)} characters")
        print(f"DEBUG: Context preview: {context[:200]}...")

        prompt = f"""You are a helpful assistant. Use the context to answer accurately.

Context:
{context}

Question: {question}

If you use the context, cite sources by number like [1], [2] when helpful.
If the context is insufficient, say so briefly and answer to the best of your ability.
"""

        resp = _llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        answer = resp.choices[0].message.content

        # Preserve your AskOut(answer=...)
        return AskOut(answer=answer)

@api_controller("v1", tags=["crawl"])
class CrawlController:
    @http_post("/crawl", response=CrawlOut)
    def crawl(self, request, payload: CrawlIn):
        """
        Retrofit: run the full LangGraph pipeline (crawl→extract→vectorize)
        so that /crawl completes the vectorization step too.
        CrawlIn should have: url (HttpUrl), max_pages (int, optional), tenant_id (optional).
        """
        try:
            url_str = str(payload.url)
            max_pages = payload.max_pages or 100
            tenant_id = payload.tenant_id

            graph = build_graph()
            state = PipelineState(tenant_id=tenant_id, root_url=url_str, max_pages=max_pages)
            final_state = graph.invoke(state)
            # LangGraph returns state as a dictionary, not a PipelineState object
            if isinstance(final_state, dict):
                result = final_state.get("result") or final_state.get("vectorization_summary") or {"docs": 0, "chunks": 0}
            else:
                result = final_state.result or final_state.vectorization_summary or {"docs": 0, "chunks": 0}

            # Map to your CrawlOut fields; we treat docs as pages discovered for compatibility
            return CrawlOut(
                message=f"Vectorized crawl completed for {url_str}",
                urls_discovered=result.get("docs", 0),
                pages_crawled=result.get("docs", 0),
            )
        except Exception as e:
            return CrawlOut(
                message=f"Error crawling {payload.url}: {str(e)}",
                urls_discovered=0,
                pages_crawled=0,
            )

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
                return IngestOut(job_id=0, docs=out.get("docs", 0), chunks=out.get("chunks", 0), message="sync")
            else:
                async_res = ingest_task.delay(payload.tenant_id, url_str, payload.max_pages)
                # return Celery task id so the caller can poll if they want
                return IngestOut(job_id=async_res.id, docs=0, chunks=0, message="enqueued")
        except Exception as e:
            import traceback
            print(f"DEBUG: Exception caught: {e}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return IngestOut(job_id=-1, docs=0, chunks=0, message=f"error: {e}")

api.register_controllers(MetaController, AskController, CrawlController, IngestController)
