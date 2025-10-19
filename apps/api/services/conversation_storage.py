"""
Conversation Storage Service

This service manages conversation history using Django's caching framework
with LRU eviction. It provides a clean interface for storing and retrieving
conversation data without requiring clients to pass full conversation history.
"""

import json
import time
import logging
from typing import List, Dict, Optional, Any
from django.core.cache import caches
from django.conf import settings
from collections import OrderedDict

logger = logging.getLogger('apps.api')

class ConversationMessage:
    """Represents a single message in a conversation"""
    
    def __init__(self, role: str, content: str, timestamp: Optional[float] = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time())
        )

class ConversationData:
    """Represents a complete conversation with metadata"""
    
    def __init__(self, conversation_id: str, tenant_id: str, created_at: Optional[float] = None):
        self.conversation_id = conversation_id
        self.tenant_id = tenant_id
        self.created_at = created_at or time.time()
        self.last_activity = self.created_at
        self.messages: List[ConversationMessage] = []
        self.metadata: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation"""
        message = ConversationMessage(role, content)
        self.messages.append(message)
        self.last_activity = time.time()
    
    def get_messages_dict(self) -> List[Dict[str, str]]:
        """Get messages in the format expected by the conversation pipeline"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize conversation to dictionary"""
        return {
            "conversation_id": self.conversation_id,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationData':
        """Deserialize conversation from dictionary"""
        conv = cls(
            conversation_id=data["conversation_id"],
            tenant_id=data["tenant_id"],
            created_at=data.get("created_at", time.time())
        )
        conv.last_activity = data.get("last_activity", conv.created_at)
        conv.messages = [
            ConversationMessage.from_dict(msg_data)
            for msg_data in data.get("messages", [])
        ]
        conv.metadata = data.get("metadata", {})
        return conv

class ConversationStorageService:
    """Service for managing conversation storage with LRU eviction"""
    
    def __init__(self):
        self.cache = caches['conversations']
        self.max_entries = getattr(settings, 'CONVERSATION_MAX_ENTRIES', 50)
        self.cache_timeout = getattr(settings, 'CONVERSATION_CACHE_TIMEOUT', 7200)
    
    def _get_conversation_key(self, conversation_id: str, tenant_id: str) -> str:
        """Generate cache key for conversation"""
        return f"conv:{tenant_id}:{conversation_id}"
    
    def _get_tenant_conversations_key(self, tenant_id: str) -> str:
        """Generate cache key for tenant's conversation list"""
        return f"tenant_convs:{tenant_id}"
    
    def create_conversation(self, conversation_id: str, tenant_id: str) -> ConversationData:
        """Create a new conversation"""
        conversation = ConversationData(conversation_id, tenant_id)
        self._save_conversation(conversation)
        self._add_to_tenant_list(tenant_id, conversation_id)
        
        logger.info("Created new conversation", extra={
            'event_type': 'conversation_created',
            'conversation_id': conversation_id,
            'tenant_id': tenant_id,
            'timestamp': time.time()
        })
        
        return conversation
    
    def get_conversation(self, conversation_id: str, tenant_id: str) -> Optional[ConversationData]:
        """Retrieve a conversation by ID"""
        key = self._get_conversation_key(conversation_id, tenant_id)
        data = self.cache.get(key)
        
        if data is None:
            logger.debug("Conversation not found in cache", extra={
                'conversation_id': conversation_id,
                'tenant_id': tenant_id
            })
            return None
        
        try:
            conversation = ConversationData.from_dict(data)
            logger.debug("Retrieved conversation from cache", extra={
                'conversation_id': conversation_id,
                'tenant_id': tenant_id,
                'message_count': len(conversation.messages)
            })
            return conversation
        except Exception as e:
            logger.error(f"Error deserializing conversation: {str(e)}", extra={
                'conversation_id': conversation_id,
                'tenant_id': tenant_id
            })
            return None
    
    def add_message(self, conversation_id: str, tenant_id: str, role: str, content: str) -> bool:
        """Add a message to an existing conversation"""
        conversation = self.get_conversation(conversation_id, tenant_id)
        
        if conversation is None:
            logger.warning("Attempted to add message to non-existent conversation", extra={
                'conversation_id': conversation_id,
                'tenant_id': tenant_id
            })
            return False
        
        conversation.add_message(role, content)
        self._save_conversation(conversation)
        
        logger.debug("Added message to conversation", extra={
            'conversation_id': conversation_id,
            'tenant_id': tenant_id,
            'role': role,
            'message_length': len(content),
            'total_messages': len(conversation.messages)
        })
        
        return True
    
    def get_conversation_messages(self, conversation_id: str, tenant_id: str) -> List[Dict[str, str]]:
        """Get conversation messages in the format expected by the pipeline"""
        conversation = self.get_conversation(conversation_id, tenant_id)
        
        if conversation is None:
            return []
        
        return conversation.get_messages_dict()
    
    def clear_conversation(self, conversation_id: str, tenant_id: str) -> bool:
        """Clear a conversation"""
        key = self._get_conversation_key(conversation_id, tenant_id)
        self.cache.delete(key)
        self._remove_from_tenant_list(tenant_id, conversation_id)
        
        logger.info("Cleared conversation", extra={
            'event_type': 'conversation_cleared',
            'conversation_id': conversation_id,
            'tenant_id': tenant_id,
            'timestamp': time.time()
        })
        
        return True
    
    def list_tenant_conversations(self, tenant_id: str, limit: int = 20, offset: int = 0) -> List[ConversationData]:
        """List conversations for a tenant"""
        tenant_key = self._get_tenant_conversations_key(tenant_id)
        conversation_ids = self.cache.get(tenant_key, [])
        
        conversations = []
        for conv_id in conversation_ids[offset:offset + limit]:
            conversation = self.get_conversation(conv_id, tenant_id)
            if conversation:
                conversations.append(conversation)
        
        logger.debug("Listed tenant conversations", extra={
            'tenant_id': tenant_id,
            'limit': limit,
            'offset': offset,
            'total_found': len(conversations)
        })
        
        return conversations
    
    def _save_conversation(self, conversation: ConversationData) -> None:
        """Save conversation to cache"""
        key = self._get_conversation_key(conversation.conversation_id, conversation.tenant_id)
        data = conversation.to_dict()
        
        try:
            self.cache.set(key, data, timeout=self.cache_timeout)
        except Exception as e:
            logger.error(f"Error saving conversation to cache: {str(e)}", extra={
                'conversation_id': conversation.conversation_id,
                'tenant_id': conversation.tenant_id
            })
    
    def _add_to_tenant_list(self, tenant_id: str, conversation_id: str) -> None:
        """Add conversation ID to tenant's conversation list"""
        tenant_key = self._get_tenant_conversations_key(tenant_id)
        conversation_ids = self.cache.get(tenant_key, [])
        
        if conversation_id not in conversation_ids:
            conversation_ids.append(conversation_id)
            # Keep only the most recent conversations (LRU)
            if len(conversation_ids) > self.max_entries:
                conversation_ids = conversation_ids[-self.max_entries:]
            
            self.cache.set(tenant_key, conversation_ids, timeout=self.cache_timeout)
    
    def _remove_from_tenant_list(self, tenant_id: str, conversation_id: str) -> None:
        """Remove conversation ID from tenant's conversation list"""
        tenant_key = self._get_tenant_conversations_key(tenant_id)
        conversation_ids = self.cache.get(tenant_key, [])
        
        if conversation_id in conversation_ids:
            conversation_ids.remove(conversation_id)
            self.cache.set(tenant_key, conversation_ids, timeout=self.cache_timeout)
    
    def get_conversation_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get conversation statistics for a tenant"""
        conversations = self.list_tenant_conversations(tenant_id, limit=1000)  # Get all
        
        total_conversations = len(conversations)
        total_messages = sum(len(conv.messages) for conv in conversations)
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "cache_timeout": self.cache_timeout,
            "max_entries": self.max_entries
        }
    
    def get_all_tenants_with_conversations(self) -> List[str]:
        """Get list of all tenant_ids that have conversations in cache"""
        from apps.tenants.models import Organization
        
        # Get all tenant_ids from organizations
        all_tenant_ids = Organization.objects.values_list('tenant_id', flat=True)
        
        # Filter to only those with cached conversations
        tenants_with_convs = []
        for tenant_id in all_tenant_ids:
            tenant_key = self._get_tenant_conversations_key(tenant_id)
            conversation_ids = self.cache.get(tenant_key, [])
            if conversation_ids:
                tenants_with_convs.append(tenant_id)
        
        logger.debug("Found tenants with conversations", extra={
            'total_tenants': len(tenants_with_convs)
        })
        
        return tenants_with_convs
    
    def get_all_conversations_by_tenant(
        self, 
        tenant_ids: List[str], 
        conv_limit: int = 10, 
        conv_offset: int = 0
    ) -> Dict[str, List[ConversationData]]:
        """Get conversations for multiple tenants with pagination"""
        result = {}
        
        for tenant_id in tenant_ids:
            conversations = self.list_tenant_conversations(
                tenant_id, 
                limit=conv_limit, 
                offset=conv_offset
            )
            result[tenant_id] = conversations
        
        logger.debug("Retrieved conversations for multiple tenants", extra={
            'tenant_count': len(tenant_ids),
            'conv_limit': conv_limit,
            'conv_offset': conv_offset
        })
        
        return result

# Global instance
conversation_storage = ConversationStorageService()
