from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Union

class MessageContent(BaseModel):
    """Message content for chat-based requests"""
    role: str  # "user", "assistant", "system"
    text: str

class AskIn(BaseModel):
    messages: List[MessageContent]
    tenant_id: str  # Required - no default
    citations: Optional[bool] = True

class Source(BaseModel):
    """Source reference with clickable link"""
    index: int
    title: str
    url: str

class AskOut(BaseModel):
    """Response format matching UI component expectations"""
    text: Optional[str] = None
    role: Optional[str] = "assistant"
    error: Optional[str] = None
    overwrite: Optional[bool] = None
    sources: Optional[List[Source]] = None

