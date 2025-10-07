# Security Upgrade: Site-Key Based Authentication

This document describes the comprehensive security upgrade implemented for the KnowledgeInjester API, introducing **site-key based authentication** with **origin validation** and **JWT tokens**.

## Overview

The security model has been upgraded from a simple tenant_id-based system to a robust, phased security approach:

- **Phase 0**: Site-key + Origin validation (HTTPS-only, no tokens)
- **Phase 1**: JWT tokens with origin binding for enhanced security

This upgrade ensures that only authorized domains can access the API on behalf of their customers, preventing unauthorized access and domain spoofing.

## Architecture Changes

### 1. Django Models

#### Organization Model (Updated)
New fields added to support site-key based security:

```python
class Organization(models.Model):
    # Existing fields
    tenant_id = models.CharField(max_length=64, unique=True)  # Internal ID
    
    # New security fields
    site_key = models.CharField(max_length=128, unique=True, db_index=True)  # Public ID
    allowed_origins = models.JSONField(default=list)  # List of HTTPS origins
    domain = models.CharField(max_length=255, blank=True)  # Primary domain
    status = models.CharField(max_length=20, default='active')  # active/disabled
    env = models.CharField(max_length=20, default='prod')  # prod/stage/dev
```

**Key Changes:**
- `site_key`: Public identifier used by clients (e.g., `pub_acme_prod_7Hk2x`)
- `allowed_origins`: List of exact HTTPS origins allowed for this site
- `status`: Active sites can create conversations; disabled sites are blocked
- `env`: Environment tracking (prod, stage, dev)

#### Conversation Model (New)
Persistent storage for conversation metadata with origin binding:

```python
class Conversation(models.Model):
    conversation_id = models.CharField(max_length=128, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    tenant_id = models.CharField(max_length=64)  # Copied from org
    site_key = models.CharField(max_length=128)  # Public key
    origin = models.CharField(max_length=512)  # Captured from first request
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    message_count = models.PositiveIntegerField(default=0)
    page_url_hash = models.CharField(max_length=64, blank=True)  # Telemetry
    nonce = models.CharField(max_length=128, blank=True)  # Telemetry
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
```

**Purpose:**
- Origin binding: Each conversation is tied to its originating domain
- Security: Prevents conversation hijacking across domains
- Audit trail: Full tracking of conversation lifecycle

#### Session Model (New)
JWT session tracking for Phase 1 authentication:

```python
class Session(models.Model):
    session_id = models.CharField(max_length=128, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    tenant_id = models.CharField(max_length=64)
    site_key = models.CharField(max_length=128)
    origin = models.CharField(max_length=512)  # Token origin binding
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(auto_now=True)
    request_count = models.PositiveIntegerField(default=0)
```

**Purpose:**
- Token tracking: Audit trail for all issued JWT tokens
- Revocation: Ability to revoke tokens server-side
- Analytics: Usage tracking per session

#### ActivityAudit Model (Enhanced)
Enhanced with security-specific audit fields:

```python
# New activity types
ACTIVITY_TYPES = [
    ('ingest', 'Ingest'),
    ('cleanup', 'Cleanup'),
    ('session_created', 'Session Created'),
    ('conversation_started', 'Conversation Started'),
    ('origin_blocked', 'Origin Blocked'),
]

# New fields
site_key = models.CharField(max_length=128, blank=True)
origin = models.CharField(max_length=512, blank=True)
ip_address = models.GenericIPAddressField(null=True, blank=True)
```

### 2. API Endpoints

#### POST `/api/v1/sessions` (Phase 1)
Create a JWT session token.

**Request:**
```json
POST /api/v1/sessions
Origin: https://www.customer.com
Content-Type: application/json

{
  "siteKey": "pub_acme_prod_7Hk2x",
  "pageUrlHash": "sha256(location.href)",  // optional
  "nonce": "uuid-optional"  // optional
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "expires_in": 3600,
  "expires_at": "2025-10-06T12:00:00Z"
}
```

**Security Checks:**
1. Validates `Origin` header is present and HTTPS
2. Looks up Site by `siteKey`, checks `status=active`
3. Validates `Origin` is in `allowed_origins`
4. Generates JWT with claims: `{sid, tid, skey, org, env, iat, exp}`
5. Stores session in database for audit/revocation
6. Audits session creation

#### POST `/api/v1/conversations` (Phase 0/1)
Start a new conversation.

**Request:**
```json
POST /api/v1/conversations
Origin: https://www.customer.com
Authorization: Bearer <token>  // optional (Phase 1)
Content-Type: application/json

{
  "siteKey": "pub_acme_prod_7Hk2x",
  "message": "What is your return policy?",
  "citations": true,
  "pageUrlHash": "sha256(...)",  // optional
  "nonce": "uuid"  // optional
}
```

**Response:**
```json
{
  "text": "Our return policy allows...",
  "role": "assistant",
  "conversation_id": "c_2c1f1d9f...c1b",
  "sources": [
    {
      "index": 1,
      "title": "Return Policy",
      "url": "https://www.customer.com/returns"
    }
  ]
}
```

**Security Checks (Phase 0):**
1. Validates `Origin` header is present and HTTPS
2. Looks up Site by `siteKey`, checks `status=active`
3. Validates `Origin` is in `allowed_origins`
4. Creates `Conversation` record with origin binding
5. Derives `tenant_id` from site (never trusts client)
6. Processes conversation through pipeline
7. Returns answer with `conversation_id`

**Additional Security (Phase 1, if JWT provided):**
- Validates JWT token signature and expiration
- Checks token origin matches request origin
- Checks token site_key matches request site_key

#### POST `/api/v1/conversations/{conversation_id}` (Phase 0/1)
Continue an existing conversation.

**Request:**
```json
POST /api/v1/conversations/c_2c1f1d9f...c1b
Origin: https://www.customer.com
Authorization: Bearer <token>  // optional (Phase 1)
Content-Type: application/json

{
  "message": "How long do I have to return items?",
  "citations": true
}
```

**Response:**
```json
{
  "text": "You have 30 days from purchase...",
  "role": "assistant",
  "conversation_id": "c_2c1f1d9f...c1b",
  "sources": [...]
}
```

**Security Checks (Phase 0):**
1. Validates `Origin` header is present and HTTPS
2. Loads `Conversation` from database by `conversation_id`
3. **Enforces strict origin check**: `Origin === conversation.origin`
4. Derives `tenant_id` from conversation (never trusts client)
5. Updates `message_count` and `last_seen_at`
6. Processes message through pipeline

**Additional Security (Phase 1, if JWT provided):**
- Validates JWT token signature and expiration
- Checks token origin matches request origin
- Checks token site_key matches conversation site_key
- Updates session usage tracking

### 3. JWT Service

New service for JWT token generation and validation:

```python
from apps.api.services.jwt_service import jwt_service

# Generate token
token_data = jwt_service.generate_token(
    tenant_id="tenant_123",
    site_key="pub_acme_prod_7Hk2x",
    origin="https://www.customer.com",
    env="prod"
)

# Verify token
payload = jwt_service.verify_token(token, expected_origin="https://www.customer.com")

# Extract from Authorization header
token = jwt_service.extract_bearer_token(authorization_header)

# Get client IP (handles proxies)
ip = jwt_service.get_client_ip(request)
```

**JWT Token Claims:**
```json
{
  "sid": "session-uuid",           // session ID
  "tid": "tenant-internal-id",     // tenant ID (internal)
  "skey": "pub_acme_prod_7Hk2x",  // site key (public)
  "org": "https://www.customer.com", // origin (bound)
  "env": "prod",                   // environment
  "iat": 1696000000,              // issued at (Unix timestamp)
  "exp": 1696003600               // expires at (Unix timestamp)
}
```

### 4. Security Sequence Diagrams

#### Phase 0: Start Conversation (siteKey + Origin)

```
Browser Widget → API: POST /api/v1/conversations
                      {siteKey, message}
                      Origin: https://www.acme.org

API → DB: Site = lookup(siteKey)
       assert status=active
       assert Origin ∈ Site.allowed_origins

API → DB: conversation = create({
            tenant_id: Site.tenant_id,
            site_key, origin,
            conversation_id: uuid()
          })

API → RAG: process(tenant_id, message)

RAG → API: {answer, sources}

API → Browser: 200 {conversation_id, text, sources}
```

#### Phase 0: Continue Conversation (Origin validation)

```
Browser Widget → API: POST /api/v1/conversations/{id}
                      {message}
                      Origin: https://www.acme.org

API → DB: conv = get_conversation(id)
       assert Origin === conv.origin

API → RAG: process(conv.tenant_id, message, history)

API → DB: update(conv.message_count++, last_seen_at)

RAG → API: {answer, sources}

API → Browser: 200 {text, sources}
```

#### Phase 1: Create Session (JWT)

```
Browser Widget → API: POST /api/v1/sessions
                      {siteKey}
                      Origin: https://www.acme.org

API → DB: Site = lookup(siteKey)
       assert status=active
       assert Origin ∈ Site.allowed_origins

API → JWT Service: generate_token(tenant_id, siteKey, origin, env)

JWT Service → API: {token, session_id, expires_at}

API → DB: session = create({
            session_id, tenant_id, site_key,
            origin, expires_at
          })

API → Browser: 200 {token, session_id, expires_in, expires_at}
```

## Configuration

### 1. Organization Setup

For each customer organization, configure:

```python
# In Django admin or via management command
organization = Organization.objects.create(
    name="Acme Corporation",
    slug="acme-corp",
    tenant_id="tenant_acme_12345",  # Internal ID
    site_key="pub_acme_prod_7Hk2x",  # Public ID (auto-generated)
    allowed_origins=[
        "https://www.acme.com",
        "https://app.acme.com",
        "https://acme.com"
    ],
    domain="acme.com",  # Primary domain
    status="active",
    env="prod"
)
```

### 2. JWT Secret Key

Set in environment variables:

```bash
# .env
JWT_SECRET_KEY=your-secret-key-here  # Defaults to Django SECRET_KEY
JWT_EXPIRATION_HOURS=1  # Token lifetime (default: 1 hour)
```

### 3. CORS Configuration

The API automatically handles CORS for allowed origins. No additional configuration needed.

## Migration Guide

### Step 1: Install Dependencies

```bash
poetry install
# or
pip install -r requirements.txt
```

PyJWT>=2.8.0 has been added to requirements.

### Step 2: Run Migrations

```bash
poetry run python manage.py migrate tenants
```

This will:
1. Add new fields to `Organization` model
2. Create `Conversation` and `Session` models
3. Enhance `ActivityAudit` model
4. Auto-generate `site_key` for existing organizations

### Step 3: Configure Organizations

For each existing organization:

```bash
poetry run python manage.py shell
```

```python
from apps.tenants.models import Organization

org = Organization.objects.get(tenant_id="your-tenant-id")
org.allowed_origins = ["https://www.yoursite.com"]
org.domain = "yoursite.com"
org.status = "active"
org.env = "prod"
org.save()
```

### Step 4: Update Client Widget

**Phase 0 (Immediate):**

```javascript
// Old: Using tenant_id
const response = await fetch('/api/v1/conversations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    tenant_id: 'tenant_123',  // ❌ Old way
    message: 'Hello',
  })
});

// New: Using siteKey + Origin
const response = await fetch('/api/v1/conversations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    // Origin header is automatically sent by browser
  },
  body: JSON.stringify({
    siteKey: 'pub_acme_prod_7Hk2x',  // ✅ New way
    message: 'Hello',
  })
});
```

**Phase 1 (Enhanced Security with JWT):**

```javascript
// 1. Create session first
const sessionResponse = await fetch('/api/v1/sessions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    siteKey: 'pub_acme_prod_7Hk2x',
  })
});

const { token, session_id, expires_at } = await sessionResponse.json();

// 2. Use token for conversations
const response = await fetch('/api/v1/conversations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,  // ✅ Add JWT token
  },
  body: JSON.stringify({
    siteKey: 'pub_acme_prod_7Hk2x',
    message: 'Hello',
  })
});
```

## Security Benefits

### 1. Origin Binding
- Conversations are bound to their originating domain
- Prevents conversation hijacking across domains
- Blocks unauthorized access attempts

### 2. HTTPS-Only
- All origins must be HTTPS (no HTTP allowed)
- Protects against man-in-the-middle attacks

### 3. Site-Key Based Access
- Public site keys are safe to expose in client code
- Site keys can be rotated without changing tenant IDs
- Kill switch via `status=disabled`

### 4. Exact Origin Matching
- No wildcards in origin validation
- Exact string match required
- Prevents subdomain spoofing

### 5. JWT Token Security (Phase 1)
- Origin-bound tokens (can't be reused from different domains)
- Short-lived (1 hour default)
- Server-side revocation support
- Full audit trail

### 6. Audit Trail
- All security events logged (origin blocks, token issues, etc.)
- IP address tracking
- Usage metrics per session
- Conversation lifecycle tracking

## Backward Compatibility

The `/ask` endpoint remains unchanged for backward compatibility:

```python
POST /api/v1/ask
{
  "tenant_id": "tenant_123",  # Still works
  "message": "Hello",
  "citations": true
}
```

However, it is recommended to migrate to the new `/conversations` endpoints for enhanced security.

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Origin Blocks**: `ActivityAudit.filter(activity_type='origin_blocked')`
2. **Session Creations**: `Session.objects.filter(issued_at__gte=...)`
3. **Token Failures**: Check logs for `jwt_validation_failed` events
4. **Conversation Activity**: `Conversation.objects.annotate(activity=...)`

### Recommended Alerts

1. Alert on high rate of origin blocks (possible attack)
2. Alert on unusual session creation patterns
3. Alert on JWT validation failures
4. Alert on disabled site access attempts

## Testing

### Test Origin Validation

```bash
# Should succeed
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: https://www.acme.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_acme_prod_7Hk2x", "message": "Hello"}'

# Should fail (HTTP origin)
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: http://www.acme.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_acme_prod_7Hk2x", "message": "Hello"}'

# Should fail (not in allowed_origins)
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: https://evil.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_acme_prod_7Hk2x", "message": "Hello"}'
```

### Test JWT Tokens

```bash
# 1. Create session
SESSION=$(curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Origin: https://www.acme.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_acme_prod_7Hk2x"}')

TOKEN=$(echo $SESSION | jq -r '.token')

# 2. Use token for conversation
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: https://www.acme.com" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_acme_prod_7Hk2x", "message": "Hello"}'
```

## Troubleshooting

### "Origin header is required"
- Client must send `Origin` header
- Browsers automatically send this for cross-origin requests
- For server-to-server calls, manually add the header

### "Only HTTPS origins are allowed"
- Origin must start with `https://`
- For local development, add exception in settings (not recommended for production)

### "Origin not allowed for this site"
- Check `Organization.allowed_origins` in Django admin
- Ensure exact match (including protocol and port)
- Origins are case-sensitive

### "Conversation not found"
- Conversation may have expired from cache
- Check database for `Conversation` record
- Ensure `conversation_id` is correct

### "Origin mismatch"
- Request origin doesn't match stored conversation origin
- Cannot continue conversation from different domain
- This is by design for security

### "Invalid or expired token"
- JWT token has expired (default: 1 hour)
- Create a new session
- Check server time synchronization

## Future Enhancements

### Phase 2 (Planned)
- Rate limiting per site_key, origin, and IP
- Anomaly detection for unusual patterns
- Geographical restrictions
- Device fingerprinting
- Token refresh mechanism

### Phase 3 (Planned)
- Multi-factor authentication for sensitive operations
- OAuth2 integration for enterprise customers
- Advanced fraud detection
- Real-time security dashboard

## Support

For questions or issues:
- Check Django admin for audit logs
- Review application logs for security events
- Contact the KnowledgeInjester team

## References

- [Django CORS Headers](https://github.com/adamchainz/django-cors-headers)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)

