from ninja_extra import NinjaExtraAPI, api_controller, http_get, http_post
from django.conf import settings
from pydantic import BaseModel, HttpUrl, ValidationError as PydanticValidationError
from typing import Dict, Any
import logging
import time
import uuid
from datetime import datetime
import traceback
import json

# keep your existing schemas for ask
from .schemas import (
    AskIn, AskOut, Source, ConversationSession, ConversationListOut,
    ConversationStartIn, ConversationContinueIn, ConversationResponse
)

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
# Conversation pipeline with LangGraph history support
from .services.conversation_pipeline import conversation_pipeline
# Conversation storage service
from .services.conversation_storage import conversation_storage

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

def parse_request_data(request, model_class):
    """
    Parse request data from either JSON or form data and validate against the model.
    This handles both Content-Type: application/json and application/x-www-form-urlencoded
    """
    try:
        # Try to parse as JSON first
        if request.content_type == 'application/json':
            try:
                # Ensure we have bytes and decode properly
                if isinstance(request.body, bytes):
                    body_str = request.body.decode('utf-8')
                else:
                    body_str = str(request.body)
                
                data = json.loads(body_str)
                
                # Handle case where JSON string contains escaped JSON (double-encoded)
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        pass  # If it's not valid JSON, keep the original string
                
                # Ensure data is a dictionary
                if not isinstance(data, dict):
                    logger.error("JSON data is not a dictionary", extra={
                        'content_type': request.content_type,
                        'body_preview': body_str[:200],
                        'data_type': type(data).__name__,
                        'data_value': str(data)[:200]
                    })
                    raise ValueError("JSON data must be an object/dictionary")
                
                return model_class(**data)
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse JSON request body", extra={
                    'error': str(e),
                    'content_type': request.content_type,
                    'body_preview': str(request.body)[:200]
                })
                raise ValueError("Invalid JSON format")
        
        # Fall back to form data
        elif request.content_type in ['application/x-www-form-urlencoded', 'multipart/form-data']:
            data = request.POST.dict()
            # Convert string values to appropriate types for boolean fields
            if 'citations' in data:
                if isinstance(data['citations'], str):
                    data['citations'] = data['citations'].lower() in ('true', '1', 'yes', 'on')
            return model_class(**data)
        
        # Try to parse as JSON if content type is not specified or is text/plain
        else:
            try:
                # Ensure we have bytes and decode properly
                if isinstance(request.body, bytes):
                    body_str = request.body.decode('utf-8')
                else:
                    body_str = str(request.body)
                
                data = json.loads(body_str)
                
                # Handle case where JSON string contains escaped JSON (double-encoded)
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        pass  # If it's not valid JSON, keep the original string
                
                # Ensure data is a dictionary
                if not isinstance(data, dict):
                    logger.error("JSON data is not a dictionary", extra={
                        'content_type': request.content_type,
                        'body_preview': body_str[:200],
                        'data_type': type(data).__name__,
                        'data_value': str(data)[:200]
                    })
                    raise ValueError("JSON data must be an object/dictionary")
                
                return model_class(**data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Last resort: try form data
                data = request.POST.dict()
                if 'citations' in data and isinstance(data['citations'], str):
                    data['citations'] = data['citations'].lower() in ('true', '1', 'yes', 'on')
                return model_class(**data)
                
    except (ValueError, PydanticValidationError) as e:
        logger.error("Validation error parsing request data", extra={
            'error': str(e),
            'content_type': request.content_type,
            'body_preview': str(request.body)[:200] if hasattr(request, 'body') else 'No body',
            'form_data': dict(request.POST) if hasattr(request, 'POST') else 'No POST data'
        })
        raise

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
    @traceable(name="ask_endpoint", exclude_parameters=["request"])
    def ask(self, request, payload: AskIn):
        """
        Enhanced ask endpoint with server-side conversation history support.
        Uses conversation storage to maintain context without requiring clients to pass history.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        tenant_id = payload.tenant_id
        enable_citations = payload.citations
        conversation_id = payload.conversation_id
        user_message = payload.message.strip()
        
        log_request_start("ask", request_id, tenant_id=tenant_id, 
                         enable_citations=enable_citations, 
                         conversation_id=conversation_id,
                         message_length=len(user_message))
        
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
                    sources=None,
                    conversation_id=conversation_id
                )
            
            # Validate user message
            if not user_message:
                log_error("ask", request_id, ValueError("Empty user message"), tenant_id=tenant_id)
                return AskOut(error="User message cannot be empty.", conversation_id=conversation_id)
            
            logger.info("Ask request details", extra={
                'event_type': 'ask_request_details',
                'request_id': request_id,
                'tenant_id': tenant_id,
                'message_length': len(user_message),
                'message_preview': user_message[:100] + "..." if len(user_message) > 100 else user_message,
                'enable_citations': enable_citations,
                'conversation_id': conversation_id,
                'timestamp': datetime.utcnow().isoformat()
            })

            # Moderate the question content
            moderation_start = time.time()
            moderation_service = ModerationService()
            moderation_result = moderation_service.moderate_question(user_message)
            moderation_duration = (time.time() - moderation_start) * 1000
            
            log_performance_metric("moderation", moderation_duration, tenant_id=tenant_id)
            
            if not moderation_result["is_appropriate"]:
                logger.warning("Question flagged by moderation", extra={
                    'event_type': 'moderation_flagged',
                    'request_id': request_id,
                    'tenant_id': tenant_id,
                    'reason': moderation_result['reason'],
                    'message_preview': user_message[:100] + "..." if len(user_message) > 100 else user_message,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                duration_ms = (time.time() - start_time) * 1000
                log_request_end("ask", request_id, duration_ms, "moderation_flagged", 
                              tenant_id=tenant_id, moderation_reason=moderation_result['reason'])
                return AskOut(
                    text=moderation_result["response"],
                    role="assistant",
                    sources=None,
                    conversation_id=conversation_id
                )

            # Use the conversation pipeline with server-side storage
            pipeline_start = time.time()
            result = conversation_pipeline.process_conversation(
                user_message=user_message,
                tenant_id=tenant_id,
                enable_citations=enable_citations,
                conversation_id=conversation_id
            )
            pipeline_duration = (time.time() - pipeline_start) * 1000
            
            log_performance_metric("conversation_pipeline", pipeline_duration, tenant_id=tenant_id,
                                 conversation_id=result.get("conversation_id"),
                                 answer_length=len(result.get("answer", "")))
            
            # Convert sources to the expected format
            source_objects = None
            if result.get("sources") and enable_citations:
                source_objects = []
                for i, source in enumerate(result["sources"], 1):
                    if isinstance(source, dict) and "title" in source and "url" in source:
                        source_objects.append(Source(
                            index=i,
                            title=source.get("title", ""),
                            url=source.get("url", "")
                        ))

            # Log successful completion
            duration_ms = (time.time() - start_time) * 1000
            log_request_end("ask", request_id, duration_ms, "success", 
                          tenant_id=tenant_id, answer_length=len(result.get("answer", "")),
                          sources_count=len(source_objects) if source_objects else 0,
                          conversation_id=result.get("conversation_id"))
            
            log_business_metric("question_answered", tenant_id, 
                              question_length=len(user_message),
                              answer_length=len(result.get("answer", "")),
                              sources_used=len(source_objects) if source_objects else 0,
                              citations_enabled=enable_citations,
                              conversation_id=result.get("conversation_id"))

            # Return response with conversation ID
            return AskOut(
                text=result.get("answer", ""),
                role="assistant",
                sources=source_objects,
                conversation_id=result.get("conversation_id")
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error("ask", request_id, e, tenant_id=tenant_id)
            log_request_end("ask", request_id, duration_ms, "error", tenant_id=tenant_id)
            return AskOut(
                error=f"Error generating response: {str(e)}",
                conversation_id=conversation_id
            )


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


@api_controller("v1", tags=["conversations"])
class ConversationController:
    @http_post("/conversations", response=ConversationResponse)
    @traceable(name="start_conversation", exclude_parameters=["request"])
    def start_conversation(self, request):
        """
        Start a new conversation with the AI assistant.
        Returns a conversation_id that can be used for follow-up messages.
        Handles both JSON and form-encoded request bodies.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Parse request data using our robust parser
            payload = parse_request_data(request, ConversationStartIn)
            
            tenant_id = payload.tenant_id
            enable_citations = payload.citations
            user_message = payload.message.strip()
            
        except (ValueError, PydanticValidationError) as e:
            logger.error("Validation error in start_conversation", extra={
                'event_type': 'validation_error',
                'request_id': request_id,
                'error': str(e),
                'content_type': request.content_type,
                'timestamp': datetime.utcnow().isoformat()
            })
            duration_ms = (time.time() - start_time) * 1000
            log_request_end("start_conversation", request_id, duration_ms, "validation_error")
            return ConversationResponse(
                text="",
                role="assistant",
                conversation_id="",
                error=f"Invalid request data: {str(e)}"
            )
        
        log_request_start("start_conversation", request_id, tenant_id=tenant_id, 
                         enable_citations=enable_citations, 
                         message_length=len(user_message))
        
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
                log_request_end("start_conversation", request_id, duration_ms, "invalid_tenant", tenant_id=tenant_id)
                return ConversationResponse(
                    text="Invalid tenant ID. Please contact your administrator.",
                    role="assistant",
                    conversation_id="",
                    error="Invalid tenant ID"
                )
            
            # Validate user message
            if not user_message:
                log_error("start_conversation", request_id, ValueError("Empty user message"), tenant_id=tenant_id)
                return ConversationResponse(
                    text="",
                    role="assistant", 
                    conversation_id="",
                    error="User message cannot be empty."
                )
            
            logger.info("Start conversation request details", extra={
                'event_type': 'start_conversation_details',
                'request_id': request_id,
                'tenant_id': tenant_id,
                'message_length': len(user_message),
                'message_preview': user_message[:100] + "..." if len(user_message) > 100 else user_message,
                'enable_citations': enable_citations,
                'timestamp': datetime.utcnow().isoformat()
            })

            # Moderate the question content
            moderation_start = time.time()
            moderation_service = ModerationService()
            moderation_result = moderation_service.moderate_question(user_message)
            moderation_duration = (time.time() - moderation_start) * 1000
            
            log_performance_metric("moderation", moderation_duration, tenant_id=tenant_id)
            
            if not moderation_result["is_appropriate"]:
                logger.warning("Question flagged by moderation", extra={
                    'event_type': 'moderation_flagged',
                    'request_id': request_id,
                    'tenant_id': tenant_id,
                    'reason': moderation_result['reason'],
                    'message_preview': user_message[:100] + "..." if len(user_message) > 100 else user_message,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                duration_ms = (time.time() - start_time) * 1000
                log_request_end("start_conversation", request_id, duration_ms, "moderation_flagged", 
                              tenant_id=tenant_id, moderation_reason=moderation_result['reason'])
                return ConversationResponse(
                    text=moderation_result["response"],
                    role="assistant",
                    conversation_id="",
                    error="Content flagged by moderation"
                )

            # Use the conversation pipeline to start a new conversation
            pipeline_start = time.time()
            result = conversation_pipeline.process_conversation(
                user_message=user_message,
                tenant_id=tenant_id,
                enable_citations=enable_citations,
                conversation_id=None  # None means create new conversation
            )
            pipeline_duration = (time.time() - pipeline_start) * 1000
            
            log_performance_metric("conversation_pipeline", pipeline_duration, tenant_id=tenant_id,
                                 conversation_id=result.get("conversation_id"),
                                 answer_length=len(result.get("answer", "")))
            
            # Convert sources to the expected format
            source_objects = None
            if result.get("sources") and enable_citations:
                source_objects = []
                for i, source in enumerate(result["sources"], 1):
                    if isinstance(source, dict) and "title" in source and "url" in source:
                        source_objects.append(Source(
                            index=i,
                            title=source.get("title", ""),
                            url=source.get("url", "")
                        ))

            # Log successful completion
            duration_ms = (time.time() - start_time) * 1000
            log_request_end("start_conversation", request_id, duration_ms, "success", 
                          tenant_id=tenant_id, answer_length=len(result.get("answer", "")),
                          sources_count=len(source_objects) if source_objects else 0,
                          conversation_id=result.get("conversation_id"))
            
            log_business_metric("conversation_started", tenant_id, 
                              question_length=len(user_message),
                              answer_length=len(result.get("answer", "")),
                              sources_used=len(source_objects) if source_objects else 0,
                              citations_enabled=enable_citations,
                              conversation_id=result.get("conversation_id"))

            # Return response with conversation ID
            return ConversationResponse(
                text=result.get("answer", ""),
                role="assistant",
                conversation_id=result.get("conversation_id", ""),
                sources=source_objects
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error("start_conversation", request_id, e, tenant_id=tenant_id)
            log_request_end("start_conversation", request_id, duration_ms, "error", tenant_id=tenant_id)
            return ConversationResponse(
                text="",
                role="assistant",
                conversation_id="",
                error=f"Error generating response: {str(e)}"
            )
    
    @http_post("/conversations/{conversation_id}", response=ConversationResponse)
    @traceable(name="continue_conversation", exclude_parameters=["request"])
    def continue_conversation(self, request, conversation_id: str):
        """
        Continue an existing conversation by sending a new message.
        The conversation_id should be obtained from a previous conversation response.
        Handles both JSON and form-encoded request bodies.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Parse request data using our robust parser
            payload = parse_request_data(request, ConversationContinueIn)
            
            tenant_id = payload.tenant_id
            enable_citations = payload.citations
            user_message = payload.message.strip()
            
        except (ValueError, PydanticValidationError) as e:
            logger.error("Validation error in continue_conversation", extra={
                'event_type': 'validation_error',
                'request_id': request_id,
                'conversation_id': conversation_id,
                'error': str(e),
                'content_type': request.content_type,
                'timestamp': datetime.utcnow().isoformat()
            })
            duration_ms = (time.time() - start_time) * 1000
            log_request_end("continue_conversation", request_id, duration_ms, "validation_error")
            return ConversationResponse(
                text="",
                role="assistant",
                conversation_id=conversation_id,
                error=f"Invalid request data: {str(e)}"
            )
        
        log_request_start("continue_conversation", request_id, tenant_id=tenant_id, 
                         enable_citations=enable_citations, 
                         conversation_id=conversation_id,
                         message_length=len(user_message))
        
        try:
            # Validate tenant_id exists in the database
            try:
                organization = Organization.objects.get(tenant_id=tenant_id)
            except Organization.DoesNotExist:
                logger.warning("Invalid tenant_id provided", extra={
                    'event_type': 'invalid_tenant',
                    'request_id': request_id,
                    'tenant_id': tenant_id,
                    'conversation_id': conversation_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
                duration_ms = (time.time() - start_time) * 1000
                log_request_end("continue_conversation", request_id, duration_ms, "invalid_tenant", tenant_id=tenant_id)
                return ConversationResponse(
                    text="Invalid tenant ID. Please contact your administrator.",
                    role="assistant",
                    conversation_id=conversation_id,
                    error="Invalid tenant ID"
                )
            
            # Validate user message
            if not user_message:
                log_error("continue_conversation", request_id, ValueError("Empty user message"), tenant_id=tenant_id)
                return ConversationResponse(
                    text="",
                    role="assistant", 
                    conversation_id=conversation_id,
                    error="User message cannot be empty."
                )
            
            # Check if conversation exists
            conversation = conversation_storage.get_conversation(conversation_id, tenant_id)
            if conversation is None:
                logger.warning("Conversation not found", extra={
                    'event_type': 'conversation_not_found',
                    'request_id': request_id,
                    'tenant_id': tenant_id,
                    'conversation_id': conversation_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
                return ConversationResponse(
                    text="Conversation not found. Please start a new conversation.",
                    role="assistant",
                    conversation_id=conversation_id,
                    error="Conversation not found"
                )
            
            logger.info("Continue conversation request details", extra={
                'event_type': 'continue_conversation_details',
                'request_id': request_id,
                'tenant_id': tenant_id,
                'conversation_id': conversation_id,
                'message_length': len(user_message),
                'message_preview': user_message[:100] + "..." if len(user_message) > 100 else user_message,
                'enable_citations': enable_citations,
                'existing_messages': len(conversation.messages),
                'timestamp': datetime.utcnow().isoformat()
            })

            # Moderate the question content
            moderation_start = time.time()
            moderation_service = ModerationService()
            moderation_result = moderation_service.moderate_question(user_message)
            moderation_duration = (time.time() - moderation_start) * 1000
            
            log_performance_metric("moderation", moderation_duration, tenant_id=tenant_id)
            
            if not moderation_result["is_appropriate"]:
                logger.warning("Question flagged by moderation", extra={
                    'event_type': 'moderation_flagged',
                    'request_id': request_id,
                    'tenant_id': tenant_id,
                    'conversation_id': conversation_id,
                    'reason': moderation_result['reason'],
                    'message_preview': user_message[:100] + "..." if len(user_message) > 100 else user_message,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                duration_ms = (time.time() - start_time) * 1000
                log_request_end("continue_conversation", request_id, duration_ms, "moderation_flagged", 
                              tenant_id=tenant_id, moderation_reason=moderation_result['reason'])
                return ConversationResponse(
                    text=moderation_result["response"],
                    role="assistant",
                    conversation_id=conversation_id,
                    error="Content flagged by moderation"
                )

            # Use the conversation pipeline to continue the conversation
            pipeline_start = time.time()
            result = conversation_pipeline.process_conversation(
                user_message=user_message,
                tenant_id=tenant_id,
                enable_citations=enable_citations,
                conversation_id=conversation_id
            )
            pipeline_duration = (time.time() - pipeline_start) * 1000
            
            log_performance_metric("conversation_pipeline", pipeline_duration, tenant_id=tenant_id,
                                 conversation_id=result.get("conversation_id"),
                                 answer_length=len(result.get("answer", "")))
            
            # Convert sources to the expected format
            source_objects = None
            if result.get("sources") and enable_citations:
                source_objects = []
                for i, source in enumerate(result["sources"], 1):
                    if isinstance(source, dict) and "title" in source and "url" in source:
                        source_objects.append(Source(
                            index=i,
                            title=source.get("title", ""),
                            url=source.get("url", "")
                        ))

            # Log successful completion
            duration_ms = (time.time() - start_time) * 1000
            log_request_end("continue_conversation", request_id, duration_ms, "success", 
                          tenant_id=tenant_id, answer_length=len(result.get("answer", "")),
                          sources_count=len(source_objects) if source_objects else 0,
                          conversation_id=result.get("conversation_id"))
            
            log_business_metric("conversation_continued", tenant_id, 
                              question_length=len(user_message),
                              answer_length=len(result.get("answer", "")),
                              sources_used=len(source_objects) if source_objects else 0,
                              citations_enabled=enable_citations,
                              conversation_id=result.get("conversation_id"))

            # Return response with conversation ID
            return ConversationResponse(
                text=result.get("answer", ""),
                role="assistant",
                conversation_id=result.get("conversation_id", conversation_id),
                sources=source_objects
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error("continue_conversation", request_id, e, tenant_id=tenant_id)
            log_request_end("continue_conversation", request_id, duration_ms, "error", tenant_id=tenant_id)
            return ConversationResponse(
                text="",
                role="assistant",
                conversation_id=conversation_id,
                error=f"Error generating response: {str(e)}"
            )
    @http_get("/conversations", response=ConversationListOut)
    def list_conversations(self, request, tenant_id: str, limit: int = 20, offset: int = 0):
        """
        List conversation sessions for a tenant using server-side storage.
        """
        try:
            # Validate tenant_id exists
            try:
                organization = Organization.objects.get(tenant_id=tenant_id)
            except Organization.DoesNotExist:
                return ConversationListOut(conversations=[], total=0)
            
            # Get conversations from storage
            conversations_data = conversation_storage.list_tenant_conversations(tenant_id, limit, offset)
            
            # Convert to response format
            conversations = []
            for conv in conversations_data:
                conversations.append(ConversationSession(
                    conversation_id=conv.conversation_id,
                    tenant_id=conv.tenant_id,
                    created_at=datetime.fromtimestamp(conv.created_at).isoformat(),
                    last_activity=datetime.fromtimestamp(conv.last_activity).isoformat(),
                    message_count=len(conv.messages)
                ))
            
            logger.info("Listed conversations", extra={
                'event_type': 'conversations_listed',
                'tenant_id': tenant_id,
                'limit': limit,
                'offset': offset,
                'total_found': len(conversations),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return ConversationListOut(conversations=conversations, total=len(conversations))
            
        except Exception as e:
            logger.error(f"Error listing conversations: {str(e)}")
            return ConversationListOut(conversations=[], total=0)
    
    @http_post("/conversations/{conversation_id}/clear")
    def clear_conversation(self, request, conversation_id: str, tenant_id: str):
        """
        Clear a conversation session using server-side storage.
        """
        try:
            # Validate tenant_id exists
            try:
                organization = Organization.objects.get(tenant_id=tenant_id)
            except Organization.DoesNotExist:
                return {"error": "Invalid tenant ID"}
            
            # Clear conversation from storage
            success = conversation_storage.clear_conversation(conversation_id, tenant_id)
            
            if success:
                logger.info("Cleared conversation", extra={
                    'event_type': 'conversation_cleared',
                    'tenant_id': tenant_id,
                    'conversation_id': conversation_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
                return {"message": "Conversation cleared successfully"}
            else:
                return {"error": "Failed to clear conversation"}
            
        except Exception as e:
            logger.error(f"Error clearing conversation: {str(e)}")
            return {"error": f"Error clearing conversation: {str(e)}"}
    
    @http_get("/conversations/stats")
    def get_conversation_stats(self, request, tenant_id: str):
        """
        Get conversation statistics for a tenant.
        """
        try:
            # Validate tenant_id exists
            try:
                organization = Organization.objects.get(tenant_id=tenant_id)
            except Organization.DoesNotExist:
                return {"error": "Invalid tenant ID"}
            
            # Get stats from storage
            stats = conversation_storage.get_conversation_stats(tenant_id)
            
            logger.info("Retrieved conversation stats", extra={
                'event_type': 'conversation_stats_retrieved',
                'tenant_id': tenant_id,
                'stats': stats,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting conversation stats: {str(e)}")
            return {"error": f"Error getting conversation stats: {str(e)}"}

api.register_controllers(MetaController, AskController, IngestController, AdminController, ConversationController)
