# Security Upgrade - Migration Checklist

## Pre-Migration

- [ ] Review `SECURITY_UPGRADE.md` for full details
- [ ] Review `SECURITY_UPGRADE_SUMMARY.md` for quick overview
- [ ] Backup production database
- [ ] Test in staging environment first
- [ ] Notify clients of upcoming changes

## Database Migration

### Step 1: Install Dependencies
```bash
cd /path/to/knowledgeinjester
poetry install
# or
pip install -r requirements.txt
```

**New dependency**: PyJWT>=2.8.0

- [ ] Dependencies installed successfully

### Step 2: Run Migrations
```bash
poetry run python manage.py migrate tenants
# or
python manage.py migrate tenants
```

**What this does**:
- Adds new fields to Organization model
- Creates Conversation and Session models
- Enhances ActivityAudit model
- Auto-generates site_key for existing organizations

- [ ] Migrations completed successfully
- [ ] No migration errors in logs

### Step 3: Verify Migration
```bash
poetry run python manage.py shell
```

```python
from apps.tenants.models import Organization, Conversation, Session

# Check Organization has new fields
org = Organization.objects.first()
print(f"Site Key: {org.site_key}")
print(f"Status: {org.status}")
print(f"Env: {org.env}")
print(f"Allowed Origins: {org.allowed_origins}")
print(f"Domain: {org.domain}")

# Check Conversation table exists
print(f"Conversation count: {Conversation.objects.count()}")

# Check Session table exists
print(f"Session count: {Session.objects.count()}")
```

- [ ] All new fields are present
- [ ] New tables created
- [ ] site_key auto-generated for existing orgs

## Organization Configuration

For **each** customer organization:

### Step 1: Get Site Key
```python
from apps.tenants.models import Organization

org = Organization.objects.get(slug="customer-slug")
print(f"Site Key: {org.site_key}")
```

- [ ] Site key retrieved for organization: _______________

### Step 2: Configure Allowed Origins
```python
org.allowed_origins = [
    "https://www.customer.com",
    "https://app.customer.com",
    # Add all domains that should have access
]
org.domain = "customer.com"  # Primary domain
org.status = "active"
org.env = "prod"  # or "stage", "dev"
org.save()
```

**Important**: 
- Must be exact HTTPS URLs
- No wildcards
- No trailing slashes
- Include all subdomains that need access

- [ ] Allowed origins configured
- [ ] Domain set
- [ ] Status set to "active"
- [ ] Environment set correctly

### Step 3: Test Configuration
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Origin: https://www.customer.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "YOUR_SITE_KEY_HERE"}'
```

- [ ] Session creation successful
- [ ] Token returned
- [ ] No errors in logs

## Client Widget Updates

### Phase 0 (Minimum Required)

Update your client widget to use `siteKey` instead of `tenant_id`:

**Before:**
```javascript
fetch('/api/v1/conversations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    tenant_id: 'tenant_123',  // ❌ OLD
    message: 'Hello',
  })
});
```

**After:**
```javascript
fetch('/api/v1/conversations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    siteKey: 'pub_customer_a1b2c3d4',  // ✅ NEW
    message: 'Hello',
  })
});
```

- [ ] Widget code updated
- [ ] siteKey configured in widget
- [ ] Tested in development
- [ ] Tested in staging

### Phase 1 (Recommended - JWT Tokens)

Add JWT token support:

```javascript
// 1. Create session on widget load
const sessionResponse = await fetch('/api/v1/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    siteKey: 'pub_customer_a1b2c3d4'
  })
});

const { token, expires_in } = await sessionResponse.json();

// Store token for reuse
localStorage.setItem('chat_token', token);
localStorage.setItem('chat_token_expires', Date.now() + (expires_in * 1000));

// 2. Use token for all conversations
fetch('/api/v1/conversations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    siteKey: 'pub_customer_a1b2c3d4',
    message: 'Hello',
  })
});
```

- [ ] Session creation implemented
- [ ] Token storage implemented
- [ ] Token refresh logic implemented
- [ ] Authorization header added to requests

## Testing

### Test 1: Valid Origin
```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: https://www.customer.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_customer_a1b2c3d4", "message": "Hello"}'
```

Expected: 200 OK with conversation_id

- [ ] Test passed

### Test 2: Invalid Origin (HTTP)
```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: http://www.customer.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_customer_a1b2c3d4", "message": "Hello"}'
```

Expected: 403 Forbidden "Only HTTPS origins are allowed"

- [ ] Test passed

### Test 3: Unauthorized Origin
```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: https://evil.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_customer_a1b2c3d4", "message": "Hello"}'
```

Expected: 403 Forbidden "Origin not allowed for this site"

- [ ] Test passed

### Test 4: Disabled Site
```python
org.status = 'disabled'
org.save()
```

```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: https://www.customer.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_customer_a1b2c3d4", "message": "Hello"}'
```

Expected: 404 Not Found "Invalid or disabled site key"

- [ ] Test passed
- [ ] Re-enable site: `org.status = 'active'; org.save()`

### Test 5: Conversation Origin Binding
```bash
# Start conversation from origin A
CONV_ID=$(curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: https://www.customer.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_customer_a1b2c3d4", "message": "Hello"}' \
  | jq -r '.conversation_id')

# Try to continue from origin B (should fail)
curl -X POST "http://localhost:8000/api/v1/conversations/$CONV_ID" \
  -H "Origin: https://app.customer.com" \
  -H "Content-Type: application/json" \
  -d '{"message": "Continue"}'
```

Expected: 403 Forbidden "Origin mismatch"

- [ ] Test passed

### Test 6: JWT Token Flow
```bash
# Create session
TOKEN=$(curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Origin: https://www.customer.com" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_customer_a1b2c3d4"}' \
  | jq -r '.token')

# Use token
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Origin: https://www.customer.com" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"siteKey": "pub_customer_a1b2c3d4", "message": "Hello"}'
```

Expected: 200 OK

- [ ] Test passed

## Monitoring Setup

### Step 1: Set Up Alerts
Configure alerts for:

```python
# High rate of origin blocks
ActivityAudit.objects.filter(
    activity_type='origin_blocked',
    created_at__gte=datetime.now() - timedelta(hours=1)
).count()
```

- [ ] Alert configured for origin blocks (threshold: >10/hour)

```python
# Failed JWT validations
# Check logs for 'jwt_validation_failed' events
```

- [ ] Alert configured for JWT failures (threshold: >5/minute)

### Step 2: Set Up Dashboard

Monitor:
1. Active conversations by site_key
2. Session creation rate
3. Origin blocks
4. JWT token usage
5. Conversation duration

- [ ] Dashboard created/updated
- [ ] Metrics visible

### Step 3: Audit Log Review

```python
from apps.tenants.models import ActivityAudit

# Recent security events
ActivityAudit.objects.filter(
    activity_type__in=['session_created', 'conversation_started', 'origin_blocked']
).order_by('-created_at')[:100]
```

- [ ] Audit logs accessible
- [ ] Security events visible

## Rollback Plan

If issues occur:

### Option 1: Disable New Security (Temporary)
Keep using old `/api/v1/ask` endpoint which still accepts tenant_id.

- [ ] Documented rollback procedure

### Option 2: Database Rollback
```bash
poetry run python manage.py migrate tenants 0003_activityaudit
```

**Warning**: This will lose all Conversation and Session data.

- [ ] Documented rollback risks

## Post-Migration

### Immediate (Day 1)
- [ ] Monitor logs for errors
- [ ] Check audit logs for suspicious activity
- [ ] Verify all client widgets working
- [ ] Monitor conversation success rate

### Short-term (Week 1)
- [ ] Review origin block patterns
- [ ] Optimize allowed_origins if needed
- [ ] Collect feedback from customers
- [ ] Performance monitoring

### Long-term (Month 1)
- [ ] Analyze security metrics
- [ ] Plan Phase 2 enhancements
- [ ] Document lessons learned
- [ ] Update client documentation

## Customer Communication

### Before Migration
- [ ] Send notification email (1 week before)
- [ ] Provide updated documentation
- [ ] Share new site_key
- [ ] Schedule migration window

### Email Template
```
Subject: KnowledgeInjester Security Upgrade - Action Required

Dear Customer,

We're upgrading our API security on [DATE]. This requires a small update to your chat widget.

What you need to do:
1. Your new site key: [SITE_KEY]
2. Update your widget code (see attached guide)
3. Test in staging before [DATE]

What we're adding:
- Enhanced security with origin validation
- Optional JWT tokens
- Better audit logging

Questions? Contact us at [SUPPORT_EMAIL]

Best regards,
KnowledgeInjester Team
```

- [ ] Notification sent
- [ ] Documentation shared
- [ ] Support team briefed

### After Migration
- [ ] Confirm migration successful
- [ ] Collect feedback
- [ ] Document any issues
- [ ] Update knowledge base

## Sign-Off

### Development
- [ ] All code changes reviewed
- [ ] Tests passing
- [ ] Documentation complete
- [ ] Reviewed by: _____________ Date: _______

### Testing
- [ ] All tests passed
- [ ] Security tests passed
- [ ] Performance acceptable
- [ ] Tested by: _____________ Date: _______

### Deployment
- [ ] Staging deployment successful
- [ ] Production deployment successful
- [ ] No rollback required
- [ ] Deployed by: _____________ Date: _______

### Sign-Off
- [ ] Product Owner approval
- [ ] Security team approval
- [ ] Operations team approval
- [ ] Migration complete

---

## Notes

Use this space to document any issues, deviations, or additional steps:

```
[Add your notes here]
```

---

## Quick Reference

**Site Key Format**: `pub_{name}_{random8}`

**JWT Token Lifetime**: 1 hour (configurable via `JWT_EXPIRATION_HOURS`)

**JWT Secret Key**: Set via `JWT_SECRET_KEY` env var (defaults to Django `SECRET_KEY`)

**Origin Format**: Must be exact HTTPS URL, e.g., `https://www.example.com`

**Admin URL**: `https://your-api.com/admin/tenants/organization/`

**Audit Logs**: `https://your-api.com/admin/tenants/activityaudit/`

---

**Migration Version**: 1.0  
**Last Updated**: October 6, 2025  
**Contact**: KnowledgeInjester Team

