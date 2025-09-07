from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Union

class MessageContent(BaseModel):
    """Message content for chat-based requests"""
    role: str  # "user", "assistant", "system"
    text: str

class AskIn(BaseModel):
    messages: List[MessageContent]
    tenant_id: Optional[str] = "public"

class AskOut(BaseModel):
    """Response format matching UI component expectations"""
    text: Optional[str] = None
    role: Optional[str] = "assistant"
    error: Optional[str] = None
    overwrite: Optional[bool] = None

class CrawlIn(BaseModel):
    url: HttpUrl
    max_pages: Optional[int] = Field(default=100, ge=1, le=1000)
    tenant_id: Optional[str] = "public"

class CrawlOut(BaseModel):
    message: str
    urls_discovered: int
    pages_crawled: int
