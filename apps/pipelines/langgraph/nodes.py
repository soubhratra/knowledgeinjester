from apps.crawler.services import crawl_website_sync
from apps.extractor.services import extract_markdown
from apps.vectorizer.services import vectorize_docs
from apps.pipelines.schemas import PipelineState

def crawl_node(state: PipelineState) -> PipelineState:
    """Crawl website and extract raw pages."""
    state.raw_pages = crawl_website_sync(state.root_url, state.max_pages)
    state.status = "crawling"
    return state

def extract_node(state: PipelineState) -> PipelineState:
    """Extract markdown from raw pages."""
    state.processed_docs = extract_markdown(state.raw_pages or [])
    state.status = "extracting"
    return state

def vectorize_node(state: PipelineState) -> PipelineState:
    """Vectorize documents and store in database."""
    docs_count, chunks_count = vectorize_docs(state.tenant_id or "public", state.processed_docs or [])
    state.vectorization_summary = {"docs": docs_count, "chunks": chunks_count}
    state.result = {"docs": docs_count, "chunks": chunks_count}  # Also set result field
    state.status = "completed"
    return state

