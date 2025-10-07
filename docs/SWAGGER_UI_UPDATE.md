# Swagger UI Update - Request Body Now Visible

## Issue Fixed
The POST `/api/v1/conversations` and `/api/v1/conversations/{conversation_id}` endpoints were not showing request body fields in Swagger UI.

## Changes Made

### 1. Added Request Body Parameters to Endpoints

**Before:**
```python
def start_conversation(self, request):
    # Body was parsed manually inside the function
    payload = parse_request_data(request, ConversationStartIn)
```

**After:**
```python
def start_conversation(self, request, payload: ConversationStartIn):
    # Django Ninja automatically parses the request body
    # and generates Swagger UI documentation
```

### 2. Same Fix for Continue Conversation

**Before:**
```python
def continue_conversation(self, request, conversation_id: str):
    # Body was parsed manually
```

**After:**
```python
def continue_conversation(self, request, conversation_id: str, payload: ConversationContinueIn):
    # Body now documented and auto-parsed
```

### 3. Removed Duplicate Parsing Logic

Removed manual `parse_request_data()` calls since Django Ninja now handles this automatically.

## What You'll See in Swagger UI

### POST `/api/v1/sessions`
**Request Body:**
```json
{
  "siteKey": "string"
}
```

**Optional Fields:**
- `pageUrlHash`: string (telemetry)
- `nonce`: string (tracking)

---

### POST `/api/v1/conversations`
**Request Body:**
```json
{
  "siteKey": "pub_bright_spectrum_htlzbncn",
  "message": "Your question here",
  "citations": true
}
```

**Fields:**
- `siteKey` (**required**): Your public site key
- `message` (**required**): The user's question/message
- `citations` (optional, default: true): Include source citations
- `pageUrlHash` (optional): SHA256 of page URL for telemetry
- `nonce` (optional): Client-side nonce for tracking

**Headers:**
- `Origin`: http://localhost:8000 (automatically set by Swagger UI)
- `Authorization`: Bearer <token> (optional, JWT from `/sessions`)

---

### POST `/api/v1/conversations/{conversation_id}`
**Request Body:**
```json
{
  "message": "Follow-up question",
  "citations": true
}
```

**Fields:**
- `message` (**required**): The user's follow-up message
- `citations` (optional, default: true): Include source citations

**Headers:**
- `Origin`: http://localhost:8000 (must match conversation origin)
- `Authorization`: Bearer <token> (optional, JWT from `/sessions`)

**Path Parameters:**
- `conversation_id`: The ID returned from starting the conversation

## Testing Flow in Swagger UI

### Step 1: Create a Session (Optional for Phase 0)
```
POST /api/v1/sessions
Body: {"siteKey": "pub_bright_spectrum_htlzbncn"}
→ Copy the "token" from response
```

### Step 2: Start a Conversation
```
POST /api/v1/conversations
Body: {
  "siteKey": "pub_bright_spectrum_htlzbncn",
  "message": "What is autism?"
}
Headers: Authorization: Bearer <token> (optional)
→ Copy the "conversation_id" from response
```

### Step 3: Continue the Conversation
```
POST /api/v1/conversations/{conversation_id}
Body: {
  "message": "Tell me more"
}
Headers: Authorization: Bearer <token> (optional)
```

## JWT Token vs No Token

### Without JWT Token (Phase 0 - Basic Security)
- Only `Origin` and `siteKey` validation
- Works for quick testing
- Less secure (no session tracking)

### With JWT Token (Phase 1 - Full Security)
- Creates a session record in database
- Token is origin-bound (can't be used from different origins)
- Session tracking and audit logging
- Can be revoked via admin
- Recommended for production

## Your Site Key

```
pub_bright_spectrum_htlzbncn
```

## Allowed Origins (for testing)

```
http://localhost:8000
https://localhost:3000
https://127.0.0.1:8000
https://testserver
```

## Verification

All 17 security tests pass: ✅

```bash
poetry run pytest tests/integration/test_security_endpoints.py -v --no-cov
# Result: 17 passed
```

## Next Steps

1. Navigate to http://localhost:8000/api/docs
2. You should now see request body fields for all POST endpoints
3. Try the testing flow above
4. Check responses and conversation tracking

## Notes

- Request bodies are now properly documented and validated by Django Ninja
- All security checks remain in place
- Localhost HTTP is allowed for development
- Production HTTPS enforcement is preserved for non-localhost origins

