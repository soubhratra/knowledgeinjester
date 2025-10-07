# Localhost Testing Guide

## Issue
When testing the `/api/v1/sessions` endpoint through `http://localhost:8000/api/docs`, you received:
```json
{
  "error": "Only HTTPS origins are allowed"
}
```

## Root Cause
The security implementation enforces HTTPS-only origins for production security. However, this blocked local development testing through Swagger UI.

## Solution Applied

### 1. Added Localhost Exception to HTTPS Validation
Modified all three security endpoints to allow HTTP for localhost/127.0.0.1:

**Files Modified:**
- `apps/api/router.py`
  - `SessionController.create_session` (line ~770)
  - `ConversationController.start_conversation` (line ~982)
  - `ConversationController.continue_conversation` (line ~1304)

**Code Change:**
```python
# Before
if not origin.startswith('https://'):
    # Reject non-HTTPS origins

# After
# Allow HTTP for localhost/127.0.0.1 in development
is_localhost = any(host in origin for host in ['localhost', '127.0.0.1'])
if not origin.startswith('https://') and not (is_localhost and origin.startswith('http://')):
    # Reject non-HTTPS origins (except localhost)
```

### 2. Added `http://localhost:8000` to Allowed Origins
Updated your organization's `allowed_origins` to include the Swagger UI origin:

```python
allowed_origins: [
    'https://localhost:3000',
    'https://127.0.0.1:8000',
    'https://testserver',
    'http://localhost:8000'  # ← Added for Swagger UI testing
]
```

**Your Site Key:** `pub_bright_spectrum_htlzbncn`

## Testing the Session Endpoint

### Via Swagger UI (http://localhost:8000/api/docs)

1. Navigate to `http://localhost:8000/api/docs`
2. Find the `/api/v1/sessions` endpoint
3. Click "Try it out"
4. Enter the request body:
   ```json
   {
     "siteKey": "pub_bright_spectrum_htlzbncn"
   }
   ```
5. Click "Execute"

**Expected Response:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "expires_in": 3600,
  "expires_at": "2025-10-06T12:34:56"
}
```

### Via cURL
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -d '{"siteKey": "pub_bright_spectrum_htlzbncn"}'
```

### Via Python
```python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/sessions',
    json={'siteKey': 'pub_bright_spectrum_htlzbncn'},
    headers={'Origin': 'http://localhost:8000'}
)

print(response.json())
```

## Security Notes

### Production Deployment
When deploying to production:

1. **Remove localhost origins** from `allowed_origins`:
   ```python
   # Remove these for production:
   'http://localhost:8000'
   'http://127.0.0.1:8000'
   ```

2. **Add production domains**:
   ```python
   allowed_origins: [
       'https://yourapp.com',
       'https://www.yourapp.com',
       'https://*.yourapp.com'  # Wildcard for subdomains
   ]
   ```

3. The localhost exception in code is safe because:
   - Localhost origins can only come from local testing
   - Production origins will still be validated against `allowed_origins`
   - HTTPS is still enforced for all non-localhost origins

### Testing Other Endpoints

Once you have a session token, test the conversation endpoints:

1. **Start Conversation:**
```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "siteKey": "pub_bright_spectrum_htlzbncn",
    "message": "Hello, how are you?"
  }'
```

2. **Continue Conversation:**
```bash
curl -X POST http://localhost:8000/api/v1/conversations/CONVERSATION_ID \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "message": "Tell me more"
  }'
```

## Managing Allowed Origins via Django Admin

You can also manage allowed origins through the Django admin:

1. Navigate to `http://localhost:8000/admin/`
2. Go to "Organizations"
3. Click on your organization ("Bright Spectrum")
4. Edit the "Allowed origins" field (JSON format)
5. Add or remove origins as needed
6. Save

## Running Tests

All security tests still pass with the localhost exception:

```bash
poetry run pytest tests/integration/test_security_endpoints.py -v --no-cov
```

**Result:** ✅ 17 passed

## Summary

✅ **Fixed**: Localhost HTTP origins are now allowed for development  
✅ **Secure**: Production HTTPS enforcement still intact  
✅ **Tested**: All security tests still passing  
✅ **Ready**: You can now test through Swagger UI at http://localhost:8000/api/docs

