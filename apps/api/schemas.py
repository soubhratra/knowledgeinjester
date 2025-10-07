from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Union

class MessageContent(BaseModel):
    """Message content for chat-based requests"""
    role: str  # "user", "assistant", "system"
    text: str

class AskIn(BaseModel):
    message: str  # Single user message
    tenant_id: str  # Required - no default (kept for backward compatibility)
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

# ===== New Schemas for Site-Key Based Security =====

class SessionIn(BaseModel):
    """Request to create a new session (Phase 1)"""
    siteKey: str = Field(..., description="Public site key (e.g., pub_acme_prod_7Hk2x)")
    pageUrlHash: Optional[str] = Field(None, description="SHA256 hash of location.href (optional telemetry)")
    nonce: Optional[str] = Field(None, description="Optional client-provided nonce (UUID)")

class SessionOut(BaseModel):
    """Response from session creation"""
    token: str = Field(..., description="JWT bearer token")
    session_id: str = Field(..., description="Session identifier")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    expires_at: str = Field(..., description="ISO 8601 timestamp of expiration")

class ConversationStartIn(BaseModel):
    """Request to start a new conversation (Phase 0: siteKey + Origin)"""
    siteKey: str = Field(..., description="Public site key")
    message: str = Field(..., description="User's first message")
    citations: Optional[bool] = Field(True, description="Whether to include citations in response")
    pageUrlHash: Optional[str] = Field(None, description="SHA256 hash of location.href (optional telemetry)")
    nonce: Optional[str] = Field(None, description="Optional nonce for tracking")

class ConversationContinueIn(BaseModel):
    """Request to continue an existing conversation (Phase 0: Origin validation)"""
    message: str = Field(..., description="User's message")
    citations: Optional[bool] = Field(True, description="Whether to include citations in response")

class ConversationCreateOut(BaseModel):
    """Response from starting a new conversation"""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    expires_in: Optional[int] = Field(3600, description="Informational: conversation lifetime in seconds")

class ConversationResponse(BaseModel):
    """Response from conversation endpoints"""
    text: str
    role: str = "assistant"
    conversation_id: str
    sources: Optional[List[Source]] = None
    error: Optional[str] = None

