from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

class AskIn(BaseModel):
    question: str
    tenant_id: Optional[str] = "public"

class AskOut(BaseModel):
    answer: str

class CrawlIn(BaseModel):
    url: HttpUrl
    max_pages: Optional[int] = Field(default=100, ge=1, le=1000)
    tenant_id: Optional[str] = "public"

class CrawlOut(BaseModel):
    message: str
    urls_discovered: int
    pages_crawled: int
