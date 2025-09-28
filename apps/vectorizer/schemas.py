"""
Pydantic schemas for vectorizer operations.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ChunkSchema(BaseModel):
    """Schema for chunk data."""
    url: str
    title: Optional[str] = None
    ordinal: int
    text: str
    doc_hash: Optional[str] = None
    metadata: Dict[str, Any] = {}

class DocumentSchema(BaseModel):
    """Schema for document data."""
    source_url: str
    title: Optional[str] = None
    doc_hash: str
    chunks: List[ChunkSchema] = []

class VectorizationResult(BaseModel):
    """Result of vectorization process."""
    docs_count: int
    chunks_count: int
    success: bool = True
    error_message: Optional[str] = None
