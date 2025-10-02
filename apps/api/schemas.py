from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Union

class MessageContent(BaseModel):
    """Message content for chat-based requests"""
    role: str  # "user", "assistant", "system"
    text: str

class AskIn(BaseModel):
    message: str  # Single user message
    tenant_id: str  # Required - no default
    citations: Optional[bool] = True
    conversation_id: Optional[str] = None  # Optional conversation ID for history

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
    conversation_id: Optional[str] = None  # Return conversation ID for client tracking

class ConversationSession(BaseModel):
    """Conversation session information"""
    conversation_id: str
    tenant_id: str
    created_at: str
    last_activity: str
    message_count: int

class ConversationListOut(BaseModel):
    """List of conversation sessions"""
    conversations: List[ConversationSession]
    total: int

class ConversationStartIn(BaseModel):
    """Request to start a new conversation"""
    message: str
    tenant_id: str
    citations: Optional[bool] = True

class ConversationContinueIn(BaseModel):
    """Request to continue an existing conversation"""
    message: str
    tenant_id: str
    citations: Optional[bool] = True

class ConversationResponse(BaseModel):
    """Response from conversation endpoints"""
    text: str
    role: str = "assistant"
    conversation_id: str
    sources: Optional[List[Source]] = None
    error: Optional[str] = None

