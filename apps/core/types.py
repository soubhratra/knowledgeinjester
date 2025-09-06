"""
Shared Pydantic models and type aliases for the knowledge injester.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, validator


# Type aliases
ContentId = str
Url = str
Domain = str
ChunkId = str


class PageRaw(BaseModel):
    """Raw page data from crawler."""
    url: HttpUrl
    title: Optional[str] = None
    content: str
    html: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        return urlparse(str(self.url)).netloc
    
    @property
    def content_id(self) -> ContentId:
        """Generate unique content ID."""
        from .hashing import content_id
        return content_id(self.content, str(self.url))


class Doc(BaseModel):
    """Processed document ready for vectorization."""
    content_id: ContentId
    url: HttpUrl
    title: Optional[str] = None
    content: str
    markdown: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        return urlparse(str(self.url)).netloc


class Chunk(BaseModel):
    """Text chunk for vectorization."""
    chunk_id: ChunkId
    content_id: ContentId
    content: str
    chunk_index: int
    total_chunks: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('chunk_index')
    def validate_chunk_index(cls, v, values):
        """Validate chunk index is non-negative."""
        if v < 0:
            raise ValueError('chunk_index must be non-negative')
        return v
    
    @validator('total_chunks')
    def validate_total_chunks(cls, v, values):
        """Validate total chunks is positive."""
        if v <= 0:
            raise ValueError('total_chunks must be positive')
        return v


class Embedding(BaseModel):
    """Text embedding with metadata."""
    chunk_id: ChunkId
    content_id: ContentId
    embedding: List[float]
    model: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('embedding')
    def validate_embedding_dimension(cls, v):
        """Validate embedding has reasonable dimension."""
        if not v or len(v) < 100:  # Most embeddings are 384+ dimensions
            raise ValueError('embedding must have reasonable dimension')
        return v


class UpsertSummary(BaseModel):
    """Summary of vectorization upsert operation."""
    total_chunks: int
    successful_upserts: int
    failed_upserts: int
    skipped_duplicates: int
    processing_time_seconds: float
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_chunks == 0:
            return 0.0
        return self.successful_upserts / self.total_chunks


class CrawlJob(BaseModel):
    """Crawl job configuration."""
    job_id: str
    root_url: HttpUrl
    max_pages: int = 100
    tenant_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = 'pending'  # pending, running, completed, failed
    
    class Config:
        use_enum_values = True


class IngestJob(BaseModel):
    """End-to-end ingestion job."""
    job_id: str
    root_url: HttpUrl
    tenant_id: Optional[str] = None
    crawl_config: Dict[str, Any] = Field(default_factory=dict)
    extract_config: Dict[str, Any] = Field(default_factory=dict)
    vectorize_config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = 'pending'  # pending, crawling, extracting, vectorizing, completed, failed
    
    class Config:
        use_enum_values = True


# API Request/Response models
class IngestRequest(BaseModel):
    """API request for ingestion."""
    root_url: HttpUrl
    tenant_id: Optional[str] = None
    max_pages: int = Field(default=100, ge=1, le=1000)
    crawl_config: Dict[str, Any] = Field(default_factory=dict)
    extract_config: Dict[str, Any] = Field(default_factory=dict)
    vectorize_config: Dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    """API response for ingestion."""
    job_id: str
    status: str
    message: str
    created_at: datetime
    estimated_completion: Optional[datetime] = None


class JobStatusResponse(BaseModel):
    """API response for job status."""
    job_id: str
    status: str
    progress: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


