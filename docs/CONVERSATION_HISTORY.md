# Enhanced Conversation History with RESTful API Design

This document describes the enhanced conversation history feature implemented using LangGraph with server-side storage and a RESTful API design for optimal performance and intuitive client usage.

## Overview

The enhanced conversation history feature enables the LLM to maintain context across multiple messages in a conversation using server-side storage. The new RESTful API design treats conversations as first-class resources with dedicated endpoints for starting and continuing conversations.

## Key Features

- **RESTful API Design**: Conversations are treated as first-class resources with dedicated endpoints
- **Server-Side Storage**: Conversations are stored on the server using Django's caching framework
- **LRU Eviction**: Automatic cleanup of old conversations using Least Recently Used eviction
- **Intuitive Endpoints**: `POST /conversations` to start, `POST /conversations/{id}` to continue
- **Enhanced Context Retrieval**: Combines RAG with conversation history for better responses
- **Conversation Management**: Full CRUD operations for conversation sessions
- **Backward Compatibility**: Original `/ask` endpoint still works for existing clients
- **Performance Optimized**: Uses Django's LocMemCache with configurable limits

## Implementation Details

### 1. Conversation Storage Service (`apps/api/services/conversation_storage.py`)

The `ConversationStorageService` class provides:
- **Django Cache Integration**: Uses Django's caching framework with LRU eviction
- **Conversation Management**: Create, retrieve, update, and delete conversations
- **Message Storage**: Store and retrieve conversation messages with timestamps
- **Tenant Isolation**: Conversations are isolated by tenant ID
- **Automatic Cleanup**: LRU eviction when cache limits are reached

### 2. Enhanced Conversation Pipeline (`apps/api/services/conversation_pipeline.py`)

The `ConversationPipeline` class provides:
- **Server-Side Integration**: Uses conversation storage service
- **Simplified Interface**: Only requires user message and conversation ID
- **Graph-based Processing**: Three main nodes:
  - `retrieve_context`: Fetches relevant context using RAG
  - `generate_response`: Generates response using conversation history + context
  - `process_citations`: Handles citation processing if enabled

### 3. Simplified API Schema (`apps/api/schemas.py`)

Updated schemas for simplified usage:
- `AskIn.message`: Single user message (no more messages array)
- `AskIn.conversation_id`: Optional conversation ID for existing conversations
- `AskOut.conversation_id`: Returns conversation ID for client tracking
- `ConversationSession`: Conversation metadata for management endpoints

### 4. New Conversation Endpoints (`apps/api/router.py`)

**POST /conversations** - Start a new conversation:
- Accepts a single message and tenant ID
- Creates a new conversation and returns conversation ID
- Uses server-side conversation storage
- Maintains all existing functionality (moderation, citations, etc.)

**POST /conversations/{conversation_id}** - Continue an existing conversation:
- Accepts a single message and conversation ID
- Retrieves conversation history from server-side storage
- Adds new message and generates response
- Maintains all existing functionality (moderation, citations, etc.)

**GET /conversations** - List conversations for a tenant
**POST /conversations/{id}/clear** - Clear a specific conversation
**GET /conversations/stats** - Get conversation statistics

### 5. Backward Compatibility (`apps/api/router.py`)

The `/ask` endpoint is maintained for backward compatibility:
- Accepts only a single message and optional conversation ID
- Uses server-side conversation storage
- Automatically manages conversation history
- Returns conversation ID for tracking
- Maintains all existing functionality (moderation, citations, etc.)

## Usage

### New RESTful API (Recommended)

#### Starting a New Conversation

```python
# Start a new conversation
payload = {
    "message": "What is autism?",
    "tenant_id": "your-tenant-id",
    "citations": True
}

response = requests.post("/api/v1/conversations", json=payload)
conversation_id = response.json()["conversation_id"]
```

#### Continuing a Conversation

```python
# Continue the conversation
payload = {
    "message": "Can you tell me about common symptoms?",
    "tenant_id": "your-tenant-id",
    "citations": True
}

response = requests.post(f"/api/v1/conversations/{conversation_id}", json=payload)
```

### Legacy API (Backward Compatibility)

#### Using the /ask endpoint

```python
# First message (creates new conversation)
payload = {
    "message": "What is autism?",
    "tenant_id": "your-tenant-id",
    "citations": True
}

response = requests.post("/api/v1/ask", json=payload)
conversation_id = response.json()["conversation_id"]

# Follow-up message (uses conversation_id)
payload = {
    "message": "Can you tell me about common symptoms?",
    "tenant_id": "your-tenant-id",
    "citations": True,
    "conversation_id": conversation_id
}

response = requests.post("/api/v1/ask", json=payload)
```

### Conversation Management

```python
# List conversations
conversations = requests.get("/api/v1/conversations", params={
    "tenant_id": "your-tenant-id",
    "limit": 20
})

# Get conversation stats
stats = requests.get("/api/v1/conversations/stats", params={
    "tenant_id": "your-tenant-id"
})

# Clear a conversation
requests.post(f"/api/v1/conversations/{conversation_id}/clear", params={
    "tenant_id": "your-tenant-id"
})
```

## Benefits

1. **RESTful Design**: Intuitive API design treating conversations as resources
2. **Simplified Client Code**: Clients only need to pass a single message and conversation ID
3. **Server-Side Management**: No need to manage conversation history on the client side
4. **Contextual Understanding**: The LLM can reference previous parts of the conversation
5. **Natural Follow-ups**: Users can ask "Can you tell me more about that?" and get relevant responses
6. **Reduced Repetition**: The LLM doesn't repeat information already provided
7. **Better User Experience**: More natural, flowing conversations
8. **Automatic Cleanup**: LRU eviction prevents memory bloat
9. **Performance Optimized**: Uses Django's efficient caching framework
10. **Backward Compatibility**: Existing clients can continue using the `/ask` endpoint

## Technical Architecture

### New RESTful API Flow

```
POST /conversations
User Message → Moderation → Create Conversation → Conversation Pipeline → LangGraph → Response
                     ↓              ↓                        ↓
              [Validation]    [Server Storage]    [RAG Context Retrieval]
                     ↓              ↓                        ↓
              [New Conv ID]  [Store Message]    [LLM with Full Context]

POST /conversations/{id}
User Message → Moderation → Retrieve Conversation → Conversation Pipeline → LangGraph → Response
                     ↓              ↓                        ↓
              [Validation]    [Get History]    [RAG Context Retrieval]
                     ↓              ↓                        ↓
              [Conv Exists?]  [Add Message]    [LLM with Full Context]
```

### Legacy API Flow

```
POST /ask
User Message → Moderation → Conversation Storage → Conversation Pipeline → LangGraph → Response
                     ↓              ↓                        ↓
              [Validation]    [Retrieve/Create]    [RAG Context Retrieval]
                     ↓              ↓                        ↓
              [Server Storage]  [Add Message]    [LLM with Full Context]
```

## Configuration

The enhanced system uses Django's caching configuration:

```python
# settings.py
CACHES = {
    'conversations': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'conversation-storage',
        'TIMEOUT': 7200,  # 2 hours
        'OPTIONS': {
            'MAX_ENTRIES': 50,  # Maximum conversations
            'CULL_FREQUENCY': 4,  # LRU eviction frequency
        }
    }
}

CONVERSATION_CACHE_TIMEOUT = 7200  # 2 hours
CONVERSATION_MAX_ENTRIES = 50
```

## Testing

Use the provided test script to verify functionality:

```bash
python test_new_conversation_api.py
```

Make sure to:
1. Update `TENANT_ID` in the test script
2. Ensure the Django server is running
3. Have valid tenant data in the database

The test script covers:
- Starting new conversations with `POST /conversations`
- Continuing conversations with `POST /conversations/{id}`
- Error handling scenarios
- Backward compatibility with `/ask` endpoint
- Conversation management endpoints

## Migration Notes

- **New RESTful API**: Recommended approach using dedicated conversation endpoints
- **Backward Compatibility**: Original `/ask` endpoint still works for existing clients
- **Simplified Usage**: Much easier for clients to implement with new API
- **Performance**: Better performance with server-side storage
- **Memory Management**: Automatic cleanup prevents memory issues

## API Comparison

### New RESTful API (Recommended)
```python
# Start conversation
response = requests.post("/api/v1/conversations", json={
    "message": "What is autism?",
    "tenant_id": "tenant-id",
    "citations": True
})
conversation_id = response.json()["conversation_id"]

# Continue conversation
response = requests.post(f"/api/v1/conversations/{conversation_id}", json={
    "message": "Tell me about symptoms",
    "tenant_id": "tenant-id",
    "citations": True
})
```

### Legacy API (Backward Compatible)
```python
# First message
response = requests.post("/api/v1/ask", json={
    "message": "What is autism?",
    "tenant_id": "tenant-id",
    "citations": True
})
conversation_id = response.json()["conversation_id"]

# Follow-up message
response = requests.post("/api/v1/ask", json={
    "message": "Tell me about symptoms",
    "tenant_id": "tenant-id",
    "citations": True,
    "conversation_id": conversation_id
})
```

### Old API (Deprecated)
```python
# This approach is no longer recommended
payload = {
    "messages": [
        {"role": "user", "text": "What is autism?"},
        {"role": "assistant", "text": "Previous response..."},
        {"role": "user", "text": "Tell me about symptoms"}
    ],
    "tenant_id": "tenant-id",
    "citations": True,
    "conversation_id": "conv-123"
}
```

## Future Enhancements

1. **Persistent Storage**: Add database-backed storage for production
2. **Redis Integration**: Use Redis for distributed caching
3. **Context Window Management**: Implement smart context truncation for long conversations
4. **Conversation Analytics**: Add detailed analytics and metrics
5. **Multi-tenant Optimization**: Further optimize for multi-tenant scenarios
