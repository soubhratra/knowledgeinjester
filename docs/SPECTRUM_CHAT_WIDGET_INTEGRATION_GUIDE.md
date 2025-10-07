# Spectrum-Chat Widget Integration Guide
## KnowledgeInjester API Integration Documentation

**API Version:** v1  
**Last Updated:** October 6, 2025  
**Security Model:** Site-Key + Origin Validation (Phase 0) with Optional JWT (Phase 1)

---

## Table of Contents

1. [Overview](#overview)
2. [Security Architecture](#security-architecture)
3. [API Endpoints](#api-endpoints)
4. [Request/Response Schemas](#requestresponse-schemas)
5. [Browser Session Management](#browser-session-management)
6. [Implementation Guide](#implementation-guide)
7. [Error Handling](#error-handling)
8. [Testing & Development](#testing--development)

---

## Overview

The KnowledgeInjester API provides a secure, conversation-based RAG (Retrieval Augmented Generation) system with two security phases:

- **Phase 0 (Required)**: Site-key based authentication with origin validation
- **Phase 1 (Optional)**: Enhanced security with JWT session tokens

All conversations are stored server-side with automatic history management. The widget only needs to track the `conversation_id` and make simple API calls.

### Key Features

- **Server-Side Conversation Management**: Full conversation history stored on server
- **Origin-Bound Security**: Conversations bound to originating domain
- **RESTful Design**: Simple, intuitive API design
- **Automatic Moderation**: Built-in content moderation
- **Citation Support**: Optional source citations with clickable links
- **HTTPS Enforcement**: Production requires HTTPS origins (HTTP allowed for localhost in development)

---

## Security Architecture

### Phase 0: Site-Key + Origin Validation (Required)

**How it works:**
1. Widget sends `siteKey` in request body
2. Browser automatically sends `Origin` header
3. API validates:
   - Site key exists and is active
   - Origin is HTTPS
   - Origin is in the site's allowed origins list
4. Conversation is created and bound to origin
5. Subsequent requests to same conversation must come from same origin

**Security guarantees:**
- Prevents unauthorized domains from using your site key
- Prevents conversation hijacking across domains
- No sensitive credentials in client code (site key is public)

### Phase 1: JWT Session Tokens (Optional, Enhanced Security)

**How it works:**
1. Widget requests session token from `/api/v1/sessions`
2. API returns JWT token bound to origin
3. Widget stores token in sessionStorage/localStorage
4. Widget includes token in `Authorization` header for all requests
5. API validates token signature, expiration, and origin binding

**Additional security guarantees:**
- Time-limited access (default: 1 hour)
- Token bound to origin (can't be reused from different domain)
- Server-side revocation support
- Full audit trail

---

## API Endpoints

### Base URL

```
Production: https://your-api-domain.com/api/v1
Development: http://localhost:8000/api/v1
```

### 1. Create Session (Phase 1 - Optional)

**Endpoint:** `POST /api/v1/sessions`

**Purpose:** Create a JWT session token for enhanced security.

**Headers:**
```http
Origin: https://www.your-domain.com    # Required, auto-sent by browser
Content-Type: application/json
```

**Request Body:**
```json
{
  "siteKey": "pub_customer_a1b2c3d4",      // Required: Your public site key
  "pageUrlHash": "sha256_hash_optional",   // Optional: SHA256 hash of current page URL
  "nonce": "uuid-optional"                 // Optional: Client-provided nonce for tracking
}
```

**Response (200 OK):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "expires_in": 3600,                      // Seconds until expiration
  "expires_at": "2025-10-06T13:00:00Z"     // ISO 8601 timestamp
}
```

**JWT Token Claims:**
```json
{
  "sid": "session-uuid",                   // Session ID
  "tid": "tenant-internal-id",             // Tenant ID (internal)
  "skey": "pub_customer_a1b2c3d4",        // Site key (public)
  "org": "https://www.your-domain.com",   // Origin (bound to token)
  "env": "prod",                          // Environment (prod/stage/dev)
  "iat": 1696000000,                      // Issued at (Unix timestamp)
  "exp": 1696003600                       // Expires at (Unix timestamp)
}
```

**Error Responses:**
- `403 Forbidden`: Origin not allowed, non-HTTPS origin, or missing Origin header
- `404 Not Found`: Invalid or disabled site key
- `500 Internal Server Error`: Server error

---

### 2. Start Conversation

**Endpoint:** `POST /api/v1/conversations`

**Purpose:** Start a new conversation with the AI assistant.

**Headers:**
```http
Origin: https://www.your-domain.com        # Required, auto-sent by browser
Content-Type: application/json
Authorization: Bearer <token>              # Optional (Phase 1 only)
```

**Request Body:**
```json
{
  "siteKey": "pub_customer_a1b2c3d4",     // Required: Your public site key
  "message": "What is your return policy?", // Required: User's first message
  "citations": true,                       // Optional: Include source citations (default: true)
  "pageUrlHash": "sha256_hash_optional",  // Optional: Page URL hash for telemetry
  "nonce": "uuid-optional"                // Optional: Client nonce for tracking
}
```

**Response (200 OK):**
```json
{
  "text": "Our return policy allows you to return items within 30 days...",
  "role": "assistant",
  "conversation_id": "c_2c1f1d9f8e7d6c5b4a3f2e1d0c9b8a7f",
  "sources": [
    {
      "index": 1,
      "title": "Return Policy",
      "url": "https://www.your-domain.com/returns"
    },
    {
      "index": 2,
      "title": "Refund Information",
      "url": "https://www.your-domain.com/refunds"
    }
  ],
  "error": null
}
```

**Important:** Save the `conversation_id` to continue the conversation later!

**Error Response:**
```json
{
  "text": "Error message for user display",
  "role": "assistant",
  "conversation_id": "",
  "sources": null,
  "error": "Technical error description"
}
```

**Possible Errors:**
- `403 Forbidden`: Origin validation failed
- `404 Not Found`: Invalid site key
- Content moderation flag: `error: "Content flagged by moderation"`

---

### 3. Continue Conversation

**Endpoint:** `POST /api/v1/conversations/{conversation_id}`

**Purpose:** Continue an existing conversation with a new message.

**Headers:**
```http
Origin: https://www.your-domain.com        # Required, must match conversation origin
Content-Type: application/json
Authorization: Bearer <token>              # Optional (Phase 1 only)
```

**Request Body:**
```json
{
  "message": "How long do I have to return items?",  // Required: User's message
  "citations": true                                  // Optional: Include citations (default: true)
}
```

**Response (200 OK):**
```json
{
  "text": "You have 30 days from the date of purchase to return items...",
  "role": "assistant",
  "conversation_id": "c_2c1f1d9f8e7d6c5b4a3f2e1d0c9b8a7f",
  "sources": [
    {
      "index": 1,
      "title": "Return Timeline",
      "url": "https://www.your-domain.com/return-timeline"
    }
  ],
  "error": null
}
```

**Important Security Notes:**
- Request Origin MUST match the origin that started the conversation
- Attempting to continue a conversation from a different origin will result in `403 Forbidden`
- This prevents conversation hijacking across domains

**Possible Errors:**
- `403 Forbidden`: Origin mismatch or invalid token
- `404 Not Found`: Conversation not found (may have expired from cache)
- Content moderation flag: `error: "Content flagged by moderation"`

---

### 4. List Conversations (Optional)

**Endpoint:** `GET /api/v1/conversations?tenant_id={tenant_id}&limit={limit}&offset={offset}`

**Purpose:** List conversation sessions for management/history features.

**Query Parameters:**
- `tenant_id`: Required - Internal tenant ID (derived from site key)
- `limit`: Optional - Number of conversations to return (default: 20)
- `offset`: Optional - Offset for pagination (default: 0)

**Response:**
```json
{
  "conversations": [
    {
      "conversation_id": "c_2c1f1d9f...",
      "tenant_id": "tenant_123",
      "created_at": "2025-10-06T10:30:00Z",
      "last_activity": "2025-10-06T10:35:00Z",
      "message_count": 5
    }
  ],
  "total": 1
}
```

**Note:** You'll need to track the `tenant_id` separately or retrieve it from the session token.

---

### 5. Clear Conversation (Optional)

**Endpoint:** `POST /api/v1/conversations/{conversation_id}/clear?tenant_id={tenant_id}`

**Purpose:** Clear a specific conversation from server-side storage.

**Response:**
```json
{
  "message": "Conversation cleared successfully"
}
```

---

## Request/Response Schemas

### Request Schemas

#### SessionIn (Create Session)
```typescript
interface SessionIn {
  siteKey: string;           // Required: Public site key
  pageUrlHash?: string;      // Optional: SHA256 of page URL
  nonce?: string;           // Optional: Client nonce (UUID)
}
```

#### ConversationStartIn (Start Conversation)
```typescript
interface ConversationStartIn {
  siteKey: string;           // Required: Public site key
  message: string;           // Required: User's first message
  citations?: boolean;       // Optional: Include citations (default: true)
  pageUrlHash?: string;      // Optional: SHA256 of page URL
  nonce?: string;           // Optional: Client nonce
}
```

#### ConversationContinueIn (Continue Conversation)
```typescript
interface ConversationContinueIn {
  message: string;           // Required: User's message
  citations?: boolean;       // Optional: Include citations (default: true)
}
```

### Response Schemas

#### SessionOut (Session Creation Response)
```typescript
interface SessionOut {
  token: string;             // JWT bearer token
  session_id: string;        // Session identifier (UUID)
  expires_in: number;        // Token lifetime in seconds (e.g., 3600 = 1 hour)
  expires_at: string;        // ISO 8601 expiration timestamp
}
```

#### ConversationResponse (Conversation Responses)
```typescript
interface ConversationResponse {
  text: string;              // AI assistant's response text
  role: string;              // Always "assistant"
  conversation_id: string;   // Conversation identifier (save this!)
  sources?: Source[];        // Array of source citations (if citations enabled)
  error?: string;           // Error message if request failed
}

interface Source {
  index: number;             // Citation number (1, 2, 3, ...)
  title: string;             // Source document title
  url: string;              // Clickable URL to source
}
```

---

## Browser Session Management

### What to Store

The widget should maintain the following in browser storage:

#### 1. Site Key (Required)
```typescript
// Store in widget configuration (not browser storage)
const SITE_KEY = 'pub_customer_a1b2c3d4';  // Your public site key
```

#### 2. JWT Token (Phase 1 - Optional)
```typescript
// Store in sessionStorage (cleared when tab closes) or localStorage (persists)
interface TokenData {
  token: string;
  session_id: string;
  expires_at: string;  // ISO 8601 timestamp
}

// Example storage
sessionStorage.setItem('kij_token', JSON.stringify({
  token: 'eyJhbGciOiJI...',
  session_id: '550e8400-e29b-41d4-a716-446655440000',
  expires_at: '2025-10-06T13:00:00Z'
}));
```

**Recommendation:** Use `sessionStorage` for better security (token cleared when tab closes).

#### 3. Conversation ID (Required)
```typescript
// Store in widget state (React state, Vue data, etc.)
// Or in sessionStorage for persistence across page reloads
interface ConversationState {
  conversation_id: string;
  created_at: string;      // ISO 8601 timestamp
  message_count: number;   // Track locally for UI
}

// Example storage
sessionStorage.setItem('kij_conversation', JSON.stringify({
  conversation_id: 'c_2c1f1d9f8e7d6c5b4a3f2e1d0c9b8a7f',
  created_at: '2025-10-06T10:30:00Z',
  message_count: 5
}));
```

### Storage Strategy

#### Option A: Session-Based (Recommended)
- Use `sessionStorage` for token and conversation ID
- Conversation persists during browser session
- Cleared when tab closes (clean slate on new visit)

```typescript
// Store token
sessionStorage.setItem('kij_token', JSON.stringify(tokenData));

// Store conversation
sessionStorage.setItem('kij_conversation', JSON.stringify(conversationState));
```

#### Option B: Persistent
- Use `localStorage` for token and conversation ID
- Conversation persists across browser sessions
- User can continue conversation even after closing browser

```typescript
// Store token
localStorage.setItem('kij_token', JSON.stringify(tokenData));

// Store conversation
localStorage.setItem('kij_conversation', JSON.stringify(conversationState));
```

#### Option C: In-Memory Only
- Store in widget state only (React state, Vue data, etc.)
- Conversation lost on page reload
- Simplest implementation, but worst UX

### Token Expiration Handling

```typescript
function isTokenValid(tokenData: TokenData): boolean {
  if (!tokenData || !tokenData.expires_at) {
    return false;
  }
  
  const expiresAt = new Date(tokenData.expires_at);
  const now = new Date();
  
  // Check if token expires in next 5 minutes (refresh buffer)
  const bufferMs = 5 * 60 * 1000;  // 5 minutes
  return expiresAt.getTime() - now.getTime() > bufferMs;
}

function shouldRefreshToken(tokenData: TokenData): boolean {
  if (!tokenData || !tokenData.expires_at) {
    return true;
  }
  
  return !isTokenValid(tokenData);
}
```

---

## Implementation Guide

### Phase 0: Basic Implementation (Site-Key Only)

This is the minimum required implementation without JWT tokens.

```typescript
import axios from 'axios';

const API_BASE_URL = 'https://your-api-domain.com/api/v1';
const SITE_KEY = 'pub_customer_a1b2c3d4';  // Your public site key

class KnowledgeInjesterClient {
  private conversationId: string | null = null;

  constructor() {
    // Load conversation ID from sessionStorage if exists
    const stored = sessionStorage.getItem('kij_conversation');
    if (stored) {
      const data = JSON.parse(stored);
      this.conversationId = data.conversation_id;
    }
  }

  /**
   * Start a new conversation or continue existing one
   */
  async sendMessage(message: string, citations: boolean = true): Promise<ConversationResponse> {
    try {
      if (this.conversationId) {
        // Continue existing conversation
        return await this.continueConversation(message, citations);
      } else {
        // Start new conversation
        return await this.startConversation(message, citations);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }

  /**
   * Start a new conversation
   */
  private async startConversation(
    message: string, 
    citations: boolean = true
  ): Promise<ConversationResponse> {
    const response = await axios.post<ConversationResponse>(
      `${API_BASE_URL}/conversations`,
      {
        siteKey: SITE_KEY,
        message: message,
        citations: citations,
        pageUrlHash: this.hashPageUrl(),  // Optional telemetry
        nonce: this.generateNonce()       // Optional tracking
      },
      {
        headers: {
          'Content-Type': 'application/json'
          // Origin header is automatically sent by browser
        }
      }
    );

    const data = response.data;

    // Save conversation ID
    if (data.conversation_id) {
      this.conversationId = data.conversation_id;
      sessionStorage.setItem('kij_conversation', JSON.stringify({
        conversation_id: data.conversation_id,
        created_at: new Date().toISOString(),
        message_count: 1
      }));
    }

    return data;
  }

  /**
   * Continue an existing conversation
   */
  private async continueConversation(
    message: string, 
    citations: boolean = true
  ): Promise<ConversationResponse> {
    if (!this.conversationId) {
      throw new Error('No active conversation');
    }

    const response = await axios.post<ConversationResponse>(
      `${API_BASE_URL}/conversations/${this.conversationId}`,
      {
        message: message,
        citations: citations
      },
      {
        headers: {
          'Content-Type': 'application/json'
          // Origin header is automatically sent by browser
        }
      }
    );

    // Update message count
    const stored = sessionStorage.getItem('kij_conversation');
    if (stored) {
      const data = JSON.parse(stored);
      data.message_count += 1;
      sessionStorage.setItem('kij_conversation', JSON.stringify(data));
    }

    return response.data;
  }

  /**
   * Clear current conversation and start fresh
   */
  clearConversation(): void {
    this.conversationId = null;
    sessionStorage.removeItem('kij_conversation');
  }

  /**
   * Get current conversation ID
   */
  getConversationId(): string | null {
    return this.conversationId;
  }

  /**
   * Generate SHA256 hash of current page URL (optional telemetry)
   */
  private async hashPageUrl(): Promise<string> {
    try {
      const encoder = new TextEncoder();
      const data = encoder.encode(window.location.href);
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } catch {
      return '';
    }
  }

  /**
   * Generate UUID v4 nonce (optional tracking)
   */
  private generateNonce(): string {
    return crypto.randomUUID();
  }
}

// Usage example
const client = new KnowledgeInjesterClient();

// Start conversation
const response1 = await client.sendMessage("What is your return policy?");
console.log(response1.text);
console.log(response1.sources);

// Continue conversation
const response2 = await client.sendMessage("How long do I have to return items?");
console.log(response2.text);

// Start new conversation
client.clearConversation();
const response3 = await client.sendMessage("What are your shipping options?");
```

---

### Phase 1: Enhanced Implementation (With JWT Tokens)

This adds JWT token support for enhanced security.

```typescript
import axios from 'axios';

const API_BASE_URL = 'https://your-api-domain.com/api/v1';
const SITE_KEY = 'pub_customer_a1b2c3d4';

interface TokenData {
  token: string;
  session_id: string;
  expires_at: string;
}

interface ConversationState {
  conversation_id: string;
  created_at: string;
  message_count: number;
}

class KnowledgeInjesterClient {
  private conversationId: string | null = null;
  private tokenData: TokenData | null = null;

  constructor() {
    // Load token from storage
    const storedToken = sessionStorage.getItem('kij_token');
    if (storedToken) {
      this.tokenData = JSON.parse(storedToken);
    }

    // Load conversation from storage
    const storedConv = sessionStorage.getItem('kij_conversation');
    if (storedConv) {
      const data: ConversationState = JSON.parse(storedConv);
      this.conversationId = data.conversation_id;
    }
  }

  /**
   * Initialize session with JWT token
   */
  async initializeSession(): Promise<void> {
    // Check if existing token is still valid
    if (this.tokenData && this.isTokenValid(this.tokenData)) {
      return;  // Token still valid
    }

    // Create new session
    try {
      const response = await axios.post<SessionOut>(
        `${API_BASE_URL}/sessions`,
        {
          siteKey: SITE_KEY,
          pageUrlHash: await this.hashPageUrl(),
          nonce: this.generateNonce()
        },
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      this.tokenData = {
        token: response.data.token,
        session_id: response.data.session_id,
        expires_at: response.data.expires_at
      };

      // Store token
      sessionStorage.setItem('kij_token', JSON.stringify(this.tokenData));
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    }
  }

  /**
   * Send a message (start or continue conversation)
   */
  async sendMessage(message: string, citations: boolean = true): Promise<ConversationResponse> {
    // Ensure we have a valid token
    await this.initializeSession();

    try {
      if (this.conversationId) {
        return await this.continueConversation(message, citations);
      } else {
        return await this.startConversation(message, citations);
      }
    } catch (error) {
      // If token expired, refresh and retry
      if (this.isTokenExpiredError(error)) {
        this.tokenData = null;
        await this.initializeSession();
        return await this.sendMessage(message, citations);
      }
      throw error;
    }
  }

  /**
   * Start a new conversation
   */
  private async startConversation(
    message: string,
    citations: boolean = true
  ): Promise<ConversationResponse> {
    const response = await axios.post<ConversationResponse>(
      `${API_BASE_URL}/conversations`,
      {
        siteKey: SITE_KEY,
        message: message,
        citations: citations,
        pageUrlHash: await this.hashPageUrl(),
        nonce: this.generateNonce()
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.tokenData?.token}`
        }
      }
    );

    const data = response.data;

    // Save conversation ID
    if (data.conversation_id && !data.error) {
      this.conversationId = data.conversation_id;
      sessionStorage.setItem('kij_conversation', JSON.stringify({
        conversation_id: data.conversation_id,
        created_at: new Date().toISOString(),
        message_count: 1
      }));
    }

    return data;
  }

  /**
   * Continue an existing conversation
   */
  private async continueConversation(
    message: string,
    citations: boolean = true
  ): Promise<ConversationResponse> {
    if (!this.conversationId) {
      throw new Error('No active conversation');
    }

    const response = await axios.post<ConversationResponse>(
      `${API_BASE_URL}/conversations/${this.conversationId}`,
      {
        message: message,
        citations: citations
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.tokenData?.token}`
        }
      }
    );

    // Handle conversation not found (expired from cache)
    if (response.data.error === 'Conversation not found') {
      // Clear stale conversation and start new one
      this.clearConversation();
      return await this.startConversation(message, citations);
    }

    // Update message count
    const stored = sessionStorage.getItem('kij_conversation');
    if (stored) {
      const data: ConversationState = JSON.parse(stored);
      data.message_count += 1;
      sessionStorage.setItem('kij_conversation', JSON.stringify(data));
    }

    return response.data;
  }

  /**
   * Clear conversation and start fresh
   */
  clearConversation(): void {
    this.conversationId = null;
    sessionStorage.removeItem('kij_conversation');
  }

  /**
   * Clear session token and conversation
   */
  clearSession(): void {
    this.tokenData = null;
    this.conversationId = null;
    sessionStorage.removeItem('kij_token');
    sessionStorage.removeItem('kij_conversation');
  }

  /**
   * Check if token is valid
   */
  private isTokenValid(tokenData: TokenData): boolean {
    if (!tokenData || !tokenData.expires_at) {
      return false;
    }

    const expiresAt = new Date(tokenData.expires_at);
    const now = new Date();

    // Add 5 minute buffer for refresh
    const bufferMs = 5 * 60 * 1000;
    return expiresAt.getTime() - now.getTime() > bufferMs;
  }

  /**
   * Check if error is due to token expiration
   */
  private isTokenExpiredError(error: any): boolean {
    return (
      error?.response?.status === 401 ||
      error?.response?.data?.error?.includes('expired') ||
      error?.response?.data?.error?.includes('Invalid token')
    );
  }

  /**
   * Generate SHA256 hash of current page URL
   */
  private async hashPageUrl(): Promise<string> {
    try {
      const encoder = new TextEncoder();
      const data = encoder.encode(window.location.href);
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } catch {
      return '';
    }
  }

  /**
   * Generate UUID v4 nonce
   */
  private generateNonce(): string {
    return crypto.randomUUID();
  }

  /**
   * Get current conversation ID
   */
  getConversationId(): string | null {
    return this.conversationId;
  }

  /**
   * Get current session ID
   */
  getSessionId(): string | null {
    return this.tokenData?.session_id || null;
  }
}

// Usage example
const client = new KnowledgeInjesterClient();

// Initialize session (creates JWT token)
await client.initializeSession();

// Send messages
const response1 = await client.sendMessage("What is your return policy?");
console.log(response1.text);

const response2 = await client.sendMessage("How long do I have?");
console.log(response2.text);

// Start new conversation
client.clearConversation();
const response3 = await client.sendMessage("Tell me about shipping");
console.log(response3.text);
```

---

## Error Handling

### Common Error Scenarios

#### 1. Origin Validation Failures

**Error:** `403 Forbidden - "Origin not allowed for this site"`

**Causes:**
- Origin not in allowed origins list
- Non-HTTPS origin (production)
- Missing Origin header

**Solutions:**
- Verify origin is configured in API admin panel
- Ensure production site uses HTTPS
- Check that fetch/axios is making proper cross-origin request

```typescript
async function handleOriginError(error: any) {
  if (error.response?.status === 403) {
    const errorMsg = error.response?.data?.error || '';
    
    if (errorMsg.includes('Origin not allowed')) {
      console.error('Your domain is not authorized. Contact support.');
      // Show user-friendly message
      return {
        text: 'This chat service is not authorized for this website.',
        error: 'origin_not_allowed'
      };
    }
    
    if (errorMsg.includes('HTTPS')) {
      console.error('HTTPS required for production.');
      return {
        text: 'This chat service requires a secure connection (HTTPS).',
        error: 'https_required'
      };
    }
  }
}
```

#### 2. Conversation Not Found

**Error:** `404 Not Found - "Conversation not found"`

**Causes:**
- Conversation expired from server cache (LRU eviction)
- Invalid conversation ID
- Conversation cleared manually

**Solution:**
```typescript
async function sendMessageWithRetry(client: KnowledgeInjesterClient, message: string) {
  try {
    return await client.sendMessage(message);
  } catch (error) {
    if (error.response?.data?.error === 'Conversation not found') {
      // Clear stale conversation and start fresh
      client.clearConversation();
      return await client.sendMessage(message);
    }
    throw error;
  }
}
```

#### 3. Token Expiration (Phase 1)

**Error:** `401 Unauthorized - "Invalid or expired token"`

**Causes:**
- JWT token expired (default: 1 hour)
- Token revoked server-side
- Clock skew between client and server

**Solution:**
```typescript
async function sendMessageWithTokenRefresh(
  client: KnowledgeInjesterClient, 
  message: string
) {
  try {
    return await client.sendMessage(message);
  } catch (error) {
    if (error.response?.status === 401 || 
        error.response?.data?.error?.includes('expired')) {
      // Refresh token and retry
      await client.initializeSession();
      return await client.sendMessage(message);
    }
    throw error;
  }
}
```

#### 4. Content Moderation

**Error:** `error: "Content flagged by moderation"`

**Causes:**
- User message contains inappropriate content
- Message detected as spam or abuse

**Solution:**
```typescript
function handleModerationError(response: ConversationResponse) {
  if (response.error === 'Content flagged by moderation') {
    // Display moderation message to user
    // response.text contains user-friendly explanation
    return {
      text: response.text,
      isModerated: true
    };
  }
}
```

#### 5. Site Key Issues

**Error:** `404 Not Found - "Invalid or disabled site key"`

**Causes:**
- Site key doesn't exist
- Site status is 'disabled'
- Typo in site key

**Solution:**
```typescript
function handleSiteKeyError(error: any) {
  if (error.response?.status === 404 && 
      error.response?.data?.error?.includes('site key')) {
    console.error('Invalid site key. Check configuration.');
    return {
      text: 'Chat service is currently unavailable. Please contact support.',
      error: 'invalid_site_key'
    };
  }
}
```

### Complete Error Handler

```typescript
class ErrorHandler {
  static handleApiError(error: any): { text: string; error: string } {
    // Network errors
    if (!error.response) {
      return {
        text: 'Unable to connect to chat service. Please check your internet connection.',
        error: 'network_error'
      };
    }

    const status = error.response.status;
    const errorData = error.response.data;
    const errorMsg = errorData?.error || '';

    // Origin validation errors (403)
    if (status === 403) {
      if (errorMsg.includes('Origin not allowed')) {
        return {
          text: 'This domain is not authorized to use this chat service.',
          error: 'origin_not_allowed'
        };
      }
      if (errorMsg.includes('HTTPS')) {
        return {
          text: 'This chat service requires a secure connection (HTTPS).',
          error: 'https_required'
        };
      }
      if (errorMsg.includes('Origin mismatch')) {
        return {
          text: 'Session security error. Please refresh the page.',
          error: 'origin_mismatch'
        };
      }
    }

    // Not found errors (404)
    if (status === 404) {
      if (errorMsg.includes('Conversation not found')) {
        return {
          text: 'Conversation expired. Starting a new conversation.',
          error: 'conversation_expired'
        };
      }
      if (errorMsg.includes('site key')) {
        return {
          text: 'Chat service is currently unavailable.',
          error: 'invalid_site_key'
        };
      }
    }

    // Token errors (401)
    if (status === 401) {
      return {
        text: 'Session expired. Please try again.',
        error: 'token_expired'
      };
    }

    // Content moderation
    if (errorData?.error === 'Content flagged by moderation') {
      return {
        text: errorData.text || 'Your message was flagged by content moderation.',
        error: 'moderation_flagged'
      };
    }

    // Server errors (500)
    if (status >= 500) {
      return {
        text: 'An error occurred. Please try again later.',
        error: 'server_error'
      };
    }

    // Default error
    return {
      text: 'An unexpected error occurred. Please try again.',
      error: 'unknown_error'
    };
  }
}

// Usage
try {
  const response = await client.sendMessage(message);
  displayResponse(response);
} catch (error) {
  const errorResponse = ErrorHandler.handleApiError(error);
  displayError(errorResponse.text);
  console.error('API Error:', errorResponse.error, error);
}
```

---

## Testing & Development

### Local Development with Localhost

For local development, the API allows HTTP origins for localhost:

```typescript
// Development configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';  // HTTP allowed for localhost
const SITE_KEY = 'pub_test_dev_12345';  // Development site key

// The Origin header will be:
// Origin: http://localhost:3000 (or your dev port)
// This is automatically sent by the browser and is allowed for localhost
```

### Testing Checklist

#### Phase 0 Testing (Site-Key Only)

1. **Start Conversation**
   ```bash
   curl -X POST http://localhost:8000/api/v1/conversations \
     -H "Origin: http://localhost:3000" \
     -H "Content-Type: application/json" \
     -d '{
       "siteKey": "pub_test_dev_12345",
       "message": "Hello, can you help me?",
       "citations": true
     }'
   ```

2. **Continue Conversation**
   ```bash
   curl -X POST http://localhost:8000/api/v1/conversations/c_abc123... \
     -H "Origin: http://localhost:3000" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Tell me more",
       "citations": true
     }'
   ```

3. **Test Origin Validation**
   ```bash
   # Should fail - wrong origin
   curl -X POST http://localhost:8000/api/v1/conversations \
     -H "Origin: https://evil.com" \
     -H "Content-Type: application/json" \
     -d '{
       "siteKey": "pub_test_dev_12345",
       "message": "Hello"
     }'
   ```

#### Phase 1 Testing (With JWT)

1. **Create Session**
   ```bash
   curl -X POST http://localhost:8000/api/v1/sessions \
     -H "Origin: http://localhost:3000" \
     -H "Content-Type: application/json" \
     -d '{
       "siteKey": "pub_test_dev_12345"
     }'
   ```

2. **Use Token**
   ```bash
   # Save token from previous response
   TOKEN="eyJhbGciOiJI..."
   
   curl -X POST http://localhost:8000/api/v1/conversations \
     -H "Origin: http://localhost:3000" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "siteKey": "pub_test_dev_12345",
       "message": "Hello with token",
       "citations": true
     }'
   ```

### Browser Console Testing

```javascript
// Test in browser console
const API_URL = 'http://localhost:8000/api/v1';
const SITE_KEY = 'pub_test_dev_12345';

// Start conversation
fetch(`${API_URL}/conversations`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    siteKey: SITE_KEY,
    message: 'Hello from browser',
    citations: true
  })
})
.then(r => r.json())
.then(data => {
  console.log('Response:', data);
  console.log('Conversation ID:', data.conversation_id);
  
  // Save conversation ID for next request
  window.conversationId = data.conversation_id;
});

// Continue conversation
fetch(`${API_URL}/conversations/${window.conversationId}`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Tell me more',
    citations: true
  })
})
.then(r => r.json())
.then(data => console.log('Response:', data));
```

### Swagger UI Testing

Interactive API documentation available at:
- **Development:** http://localhost:8000/api/docs
- **Production:** https://your-api-domain.com/api/docs

**Note:** Swagger UI cannot set the Origin header automatically. For full testing with Origin validation, use curl or browser fetch.

---

## Quick Reference

### Environment Variables

The API uses the following configuration:

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key          # Defaults to Django SECRET_KEY
JWT_EXPIRATION_HOURS=1                  # Token lifetime (default: 1 hour)

# Conversation Storage
CONVERSATION_CACHE_TIMEOUT=7200         # 2 hours
CONVERSATION_MAX_ENTRIES=50             # LRU eviction limit
```

### Important Notes

1. **Origin Header**: Automatically sent by browser for cross-origin requests. No need to set manually.

2. **HTTPS Requirement**: Production requires HTTPS origins. HTTP allowed only for localhost in development.

3. **Conversation Expiration**: Conversations are cached with LRU eviction (default: 50 conversations, 2 hour timeout).

4. **Token Lifetime**: JWT tokens expire after 1 hour by default. Implement refresh logic.

5. **Rate Limiting**: Not currently implemented but planned for Phase 2.

6. **CORS**: Automatically handled by API for allowed origins.

### Site Key Format

```
pub_{name}_{random8}

Examples:
- pub_customer_a1b2c3d4
- pub_acme_prod_7Hk2x
- pub_test_dev_12345
```

### Conversation ID Format

```
c_{hexadecimal}

Example:
- c_2c1f1d9f8e7d6c5b4a3f2e1d0c9b8a7f
```

---

## Support & Resources

### API Documentation
- **Swagger UI:** http://localhost:8000/api/docs
- **Full Security Guide:** See `SECURITY_UPGRADE.md` in API repo
- **Migration Guide:** See `MIGRATION_CHECKLIST.md` in API repo

### Getting Your Site Key

Contact your API administrator or check the Django admin panel:
- **Admin URL:** https://your-api-domain.com/admin/tenants/organization/

### Configuring Allowed Origins

Allowed origins must be configured server-side by the API administrator. Contact support to add your domain:

```python
# Example configuration (server-side only)
organization.allowed_origins = [
    "https://www.your-domain.com",
    "https://app.your-domain.com",
    "https://your-domain.com"
]
```

---

## Changelog

### Version 1.0 (October 6, 2025)
- Initial documentation
- Phase 0 and Phase 1 security implementation
- Server-side conversation management
- Origin-based security
- JWT token authentication
- Content moderation
- Citation support

---

**End of Documentation**

For questions or issues, contact the KnowledgeInjester team or refer to the full technical documentation in the API repository.


