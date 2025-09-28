"""
Pydantic schemas for pipeline state management.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from apps.core.types import PageRaw, Doc, UpsertSummary


class PipelineState(BaseModel):
    """State object for the ingestion pipeline."""
    
    # Input
    root_url: str
    tenant_id: Optional[str] = None
    max_pages: int = 100
    crawler_type: str = "llm"  # "comprehensive" or "llm"
    max_depth: int = 5  # Only used with LLM crawler
    
    # Intermediate results
    raw_pages: List[PageRaw] = Field(default_factory=list)
    processed_docs: List[Doc] = Field(default_factory=list)
    
    # Final results
    vectorization_summary: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    
    # Metadata
    job_id: str = Field(default_factory=lambda: "default")
    status: str = "pending"  # pending, crawling, extracting, vectorizing, completed, failed
    error_message: Optional[str] = None
    
    # Progress tracking
    progress: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


