# Security Upgrade Summary

## Quick Overview

This upgrade transforms the KnowledgeInjester API from tenant_id-based authentication to a robust **site-key + origin validation** security model with optional **JWT tokens**.

## What Changed

### 🔐 Security Model

| Before | After |
|--------|-------|
| Client sends `tenant_id` in request body | Client sends `siteKey` (public identifier) |
| No origin validation | Strict HTTPS origin validation |
| No conversation binding | Conversations bound to originating domain |
| No audit trail | Comprehensive audit logging |
| - | Optional JWT tokens for enhanced security |

### 📊 Database Changes

#### Organization Model
- **Added**: `site_key` (public identifier)
- **Added**: `allowed_origins` (list of HTTPS origins)
- **Added**: `domain` (primary domain)
- **Added**: `status` (active/disabled)
- **Added**: `env` (prod/stage/dev)
- **Kept**: `tenant_id` (internal identifier)

#### New Models
- **Conversation**: Persistent conversation tracking with origin binding
- **Session**: JWT session management and audit
- **ActivityAudit**: Enhanced with security audit fields

### 🚀 New API Endpoints

1. **POST `/api/v1/sessions`** (Phase 1)
   - Create JWT session tokens
   - Origin validation
   - Returns: `{token, session_id, expires_in, expires_at}`

2. **POST `/api/v1/conversations`** (Updated)
   - Use `siteKey` instead of `tenant_id`
   - Origin validation (Phase 0)
   - Optional JWT token support (Phase 1)
   - Returns: `{conversation_id, text, sources}`

3. **POST `/api/v1/conversations/{id}`** (Updated)
   - Strict origin validation against stored conversation
   - No `tenant_id` in request (derived from conversation)
   - Optional JWT token support (Phase 1)

### 🛡️ Security Features

#### Phase 0 (Implemented)
- ✅ Site-key based access control
- ✅ HTTPS-only origin validation
- ✅ Exact origin matching (no wildcards)
- ✅ Conversation origin binding
- ✅ Status-based kill switch
- ✅ Comprehensive audit logging

#### Phase 1 (Implemented)
- ✅ JWT token generation
- ✅ Origin-bound tokens
- ✅ Token expiration (1 hour default)
- ✅ Session tracking and revocation
- ✅ Token validation on every request

## Quick Start Guide

### For Administrators

1. **Run migrations:**
   ```bash
   poetry run python manage.py migrate tenants
   ```

2. **Configure organization:**
   ```python
   org = Organization.objects.get(name="Your Organization")
   org.allowed_origins = ["https://www.yoursite.com"]
   org.domain = "yoursite.com"
   org.status = "active"
   org.save()
   ```

3. **Get site_key** (auto-generated):
   ```python
   print(org.site_key)  # e.g., "pub_yourorg_a1b2c3d4"
   ```

### For Widget Developers

#### Phase 0 (Basic Security)

```javascript
// Start conversation
const response = await fetch('/api/v1/conversations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    // Origin header sent automatically by browser
  },
  body: JSON.stringify({
    siteKey: 'pub_yourorg_a1b2c3d4',  // Your site key
    message: 'Hello, how can I help?',
    citations: true
  })
});

const { conversation_id, text, sources } = await response.json();

// Continue conversation
const continueResponse = await fetch(`/api/v1/conversations/${conversation_id}`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Tell me more',
    citations: true
  })
});
```

#### Phase 1 (Enhanced with JWT)

```javascript
// 1. Create session (do this once, reuse token)
const sessionResponse = await fetch('/api/v1/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    siteKey: 'pub_yourorg_a1b2c3d4'
  })
});

const { token } = await sessionResponse.json();

// 2. Use token for all conversations
const response = await fetch('/api/v1/conversations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`  // Add JWT token
  },
  body: JSON.stringify({
    siteKey: 'pub_yourorg_a1b2c3d4',
    message: 'Hello',
  })
});
```

## Security Benefits

### 🛡️ Protection Against

- **Domain Spoofing**: Strict origin validation prevents unauthorized domains
- **Conversation Hijacking**: Origin binding prevents cross-domain access
- **Replay Attacks**: JWT tokens are origin-bound and expire
- **Man-in-the-Middle**: HTTPS-only enforcement
- **Unauthorized Access**: Site status and allowed origins control

### 📊 Audit & Compliance

- Full audit trail for all security events
- IP address tracking
- Session usage metrics
- Conversation lifecycle tracking
- Origin block logging

## Testing

### Test Origin Validation

```bash
# Valid request
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: https://www.acme.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_acme_prod_7Hk2x", "message": "Hello"}'

# Invalid: HTTP origin (should fail)
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: http://www.acme.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_acme_prod_7Hk2x", "message": "Hello"}'

# Invalid: Not in allowed_origins (should fail)
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: https://evil.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_acme_prod_7Hk2x", "message": "Hello"}'
```

## Files Changed

### Models
- ✅ `apps/tenants/models.py` - Updated Organization, added Conversation, Session, enhanced ActivityAudit

### API
- ✅ `apps/api/router.py` - Added SessionController, updated ConversationController
- ✅ `apps/api/schemas.py` - Added SessionIn/Out, updated conversation schemas
- ✅ `apps/api/services/jwt_service.py` - New JWT token service

### Admin
- ✅ `apps/tenants/admin.py` - Updated admin interfaces for new models

### Configuration
- ✅ `requirements.txt` - Added PyJWT>=2.8.0

### Migrations
- ✅ `apps/tenants/migrations/0004_*.py` - Schema changes
- ✅ `apps/tenants/migrations/0005_generate_site_keys.py` - Data migration for site_keys

### Documentation
- ✅ `SECURITY_UPGRADE.md` - Comprehensive security documentation
- ✅ `SECURITY_UPGRADE_SUMMARY.md` - This summary

## Backward Compatibility

The old `/api/v1/ask` endpoint still works with `tenant_id` for backward compatibility:

```python
POST /api/v1/ask
{
  "tenant_id": "tenant_123",  # Still works
  "message": "Hello",
}
```

**Recommendation**: Migrate to new endpoints for enhanced security.

## Next Steps

1. ✅ Run migrations
2. ✅ Configure organizations with allowed_origins
3. ✅ Update client widgets to use siteKey
4. ⏳ Test with your domains
5. ⏳ Deploy to staging
6. ⏳ Monitor audit logs
7. ⏳ Deploy to production

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Origin not allowed" | Add origin to `Organization.allowed_origins` |
| "Missing Origin header" | Ensure client sends Origin header |
| "Non-HTTPS origin" | Use HTTPS (http:// is not allowed) |
| "Conversation not found" | Check database for Conversation record |
| "Origin mismatch" | Cannot continue conversation from different domain |
| "Invalid token" | JWT expired, create new session |

## Support & Documentation

- **Full Documentation**: See `SECURITY_UPGRADE.md`
- **Django Admin**: Check audit logs and manage organizations
- **Logs**: Review security events in application logs

## Summary

This upgrade provides **enterprise-grade security** for the KnowledgeInjester API while maintaining simplicity and backward compatibility. The phased approach allows gradual migration from Phase 0 (basic security) to Phase 1 (enhanced with JWT tokens) based on your needs.

**Key Takeaway**: Your API is now protected against common security vulnerabilities and provides comprehensive audit trails for compliance and monitoring.

