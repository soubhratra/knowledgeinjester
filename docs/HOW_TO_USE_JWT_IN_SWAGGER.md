# How to Pass JWT Token in Swagger UI

## Method 1: Using Browser Developer Tools (Recommended for Testing)

This is the easiest way to test JWT tokens through Swagger UI:

### Steps:

1. **Get a JWT Token**
   - Go to http://localhost:8000/api/docs
   - Find `POST /api/v1/sessions`
   - Click "Try it out"
   - Enter:
     ```json
     {
       "siteKey": "pub_bright_spectrum_htlzbncn"
     }
     ```
   - Click "Execute"
   - **Copy the token** from the response

2. **Open Browser Developer Tools**
   - Press `F12` or right-click → Inspect
   - Go to the **Console** tab

3. **Set Authorization Header for All Requests**
   Paste this in the console (replace `YOUR_TOKEN` with your actual token):
   ```javascript
   // Store the token
   const jwtToken = "YOUR_TOKEN_HERE";
   
   // Intercept all fetch requests and add Authorization header
   const originalFetch = window.fetch;
   window.fetch = function(...args) {
       let [url, config] = args;
       config = config || {};
       config.headers = config.headers || {};
       config.headers['Authorization'] = `Bearer ${jwtToken}`;
       console.log('Adding JWT token to request:', url);
       return originalFetch(url, config);
   };
   
   console.log('✅ JWT token will be added to all API requests');
   ```

4. **Test Your Endpoints**
   - Now go back to Swagger UI
   - Try `POST /api/v1/conversations`
   - The Authorization header will be automatically added!

---

## Method 2: Using curl Command

If you prefer command-line testing:

```bash
# 1. Get a session token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -d '{"siteKey": "pub_bright_spectrum_htlzbncn"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

echo "Token: $TOKEN"

# 2. Start a conversation with the token
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "siteKey": "pub_bright_spectrum_htlzbncn",
    "message": "What is autism?"
  }' | python3 -m json.tool
```

---

## Method 3: Using Python requests

```python
import requests

# 1. Get JWT token
session_response = requests.post(
    'http://localhost:8000/api/v1/sessions',
    json={'siteKey': 'pub_bright_spectrum_htlzbncn'},
    headers={'Origin': 'http://localhost:8000'}
)
token = session_response.json()['token']
print(f"Token: {token}")

# 2. Start conversation with JWT token
conversation_response = requests.post(
    'http://localhost:8000/api/v1/conversations',
    json={
        'siteKey': 'pub_bright_spectrum_htlzbncn',
        'message': 'What is autism?'
    },
    headers={
        'Origin': 'http://localhost:8000',
        'Authorization': f'Bearer {token}'
    }
)
print(conversation_response.json())
```

---

## Method 4: Using Postman

1. **Get Token:**
   - Method: POST
   - URL: `http://localhost:8000/api/v1/sessions`
   - Headers:
     - `Content-Type: application/json`
     - `Origin: http://localhost:8000`
   - Body (raw JSON):
     ```json
     {"siteKey": "pub_bright_spectrum_htlzbncn"}
     ```
   - Send and copy the `token` from response

2. **Use Token in Conversation:**
   - Method: POST
   - URL: `http://localhost:8000/api/v1/conversations`
   - Headers:
     - `Content-Type: application/json`
     - `Origin: http://localhost:8000`
     - `Authorization: Bearer YOUR_TOKEN_HERE`
   - Body (raw JSON):
     ```json
     {
       "siteKey": "pub_bright_spectrum_htlzbncn",
       "message": "What is autism?"
     }
     ```

---

## Swagger UI Limitations

### Why Can't I Add Authorization Header Directly in Swagger UI?

Swagger UI (OpenAPI) has built-in support for authentication schemes, but Django Ninja's implementation requires additional configuration. Since the JWT token is **optional** for our endpoints (Phase 0 works without it), we didn't enforce it at the API level.

### Workaround Options:

1. **Use Browser Console Method** (Method 1 above) - Easiest
2. **Use curl/Python/Postman** - Most reliable
3. **Modify Swagger UI directly** (Advanced):
   ```javascript
   // In browser console on /api/docs page
   // This modifies the Swagger UI to add an "Authorize" button
   setTimeout(() => {
       const ui = window.ui;
       if (ui) {
           ui.authActions.authorize({
               bearerAuth: {
                   name: "bearerAuth",
                   schema: {type: "http", scheme: "bearer"},
                   value: "YOUR_TOKEN_HERE"
               }
           });
       }
   }, 2000);
   ```

---

## Testing Without JWT Token

JWT tokens are **optional** in Phase 0. You can test without them:

```json
POST /api/v1/conversations
{
  "siteKey": "pub_bright_spectrum_htlzbncn",
  "message": "Hello"
}
```

Headers needed:
- `Origin: http://localhost:8000` (Swagger UI adds this automatically)

JWT tokens add:
- ✅ Session tracking
- ✅ Enhanced audit logging
- ✅ Request count tracking
- ✅ Revocation capability
- ✅ Better security for production

---

## Quick Reference

**Your Site Key:**
```
pub_bright_spectrum_htlzbncn
```

**Token Format:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Token Lifetime:**
- Default: 1 hour
- Configurable via JWT_EXPIRATION_HOURS setting

**Check Token in Console:**
```javascript
// After using Method 1, verify token is being sent:
console.log(document.cookie); // If stored in cookies
// Or check Network tab in DevTools → Headers → Request Headers
```

---

## Troubleshooting

### "Origin header is required"
- Make sure Origin header is set to `http://localhost:8000`
- Swagger UI usually adds this automatically

### "Origin not allowed for this site"
- Verify your organization has `http://localhost:8000` in `allowed_origins`
- Check: `http://localhost:8000/admin/tenants/organization/`

### "Invalid or disabled site key"
- Double-check your site key: `pub_bright_spectrum_htlzbncn`
- Verify organization status is "active"

### Token expired
- Get a new token from `/api/v1/sessions`
- Tokens expire after 1 hour by default

---

## Production Notes

For production deployment:
1. Remove `http://localhost:8000` from allowed_origins
2. Add your production domain: `https://yourapp.com`
3. JWT tokens are **recommended** for production (Phase 1)
4. Set JWT_EXPIRATION_HOURS in production settings

