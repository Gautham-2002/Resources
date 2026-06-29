# Part 4.2: OAuth2, OIDC & API Keys

## What You'll Learn
- What OAuth2 actually is (authorization delegation, NOT authentication) and the four roles
- All major grant types: Authorization Code + PKCE, Client Credentials, Device Flow, and why Implicit is deprecated
- The Authorization Code + PKCE flow step-by-step, with security reasoning at each step
- OpenID Connect (OIDC): what it adds on top of OAuth2, the ID token, UserInfo endpoint, and discovery
- API keys: when to use them, format best practices, secure storage, rotation, and per-key rate limiting
- Full production implementations in Go+Chi, Node.js+Express, Python+FastAPI

---

## Table of Contents

1. [What OAuth2 Is (and Is Not)](#1-what-oauth2-is-and-is-not)
2. [The Four OAuth2 Roles](#2-the-four-oauth2-roles)
3. [OAuth2 Grant Types](#3-oauth2-grant-types)
4. [Authorization Code + PKCE Flow (Deep Dive)](#4-authorization-code--pkce-flow-deep-dive)
5. [Client Credentials Flow](#5-client-credentials-flow)
6. [Device Authorization Flow](#6-device-authorization-flow)
7. [OAuth2 Scopes](#7-oauth2-scopes)
8. [Token Types in OAuth2](#8-token-types-in-oauth2)
9. [The State Parameter (CSRF Protection)](#9-the-state-parameter-csrf-protection)
10. [OpenID Connect (OIDC)](#10-openid-connect-oidc)
11. [API Keys](#11-api-keys)
12. [API Key Security](#12-api-key-security)
13. [Implementation Examples](#13-implementation-examples)
14. [Common Patterns & Best Practices](#common-patterns--best-practices)
15. [Common Pitfalls](#common-pitfalls)
16. [Interview Questions](#interview-questions)
17. [Resources](#resources)

---

## 1. What OAuth2 Is (and Is Not)

**OAuth2 is an authorization framework, NOT an authentication protocol.**

This is the most commonly misunderstood aspect of OAuth2 and a classic interview trap.

```
Authentication: "Who are you?"  → OAuth2 does NOT do this
Authorization:  "What can Alice allow this app to do on her behalf?"  → OAuth2 DOES do this
```

### The Problem OAuth2 Solves

Before OAuth2, if you wanted App B to access your data on Service A, you'd give App B your Service A password. This was terrible:
- App B could do anything with your account, not just what you intended
- You couldn't revoke App B's access without changing your password
- If App B was compromised, attackers had your Service A password

OAuth2 solves this with **delegated authorization**:
- You (the user) authorize App B to access specific parts of Service A on your behalf
- App B gets a limited-scope access token, not your password
- You can revoke App B's token without affecting your password
- The token can expire automatically

### "OAuth2 is not authentication" — Why it matters

Using OAuth2 access tokens to "log users in" without OIDC is dangerous:

```
Naive "login with Google" without OIDC:
  1. User clicks "Login with Google"
  2. Google redirects back with access_token
  3. App calls Google API: GET https://www.googleapis.com/oauth2/v3/userinfo
  4. App gets { email: "alice@gmail.com" } and creates a session

The problem:
  What if the access token was intended for a different service?
  What if the Google token was obtained by a malicious app and forwarded here?
  There is no way to verify the token was issued FOR your app specifically.
```

OIDC solves this by providing an **ID token** with an `aud` (audience) claim specifying your app's client ID. If the `aud` doesn't match your client ID, reject the token.

---

## 2. The Four OAuth2 Roles

```
┌──────────────────────────────────────────────────────────────────┐
│                    OAuth2 Roles                                   │
│                                                                   │
│  ┌───────────────────┐      ┌──────────────────────────────┐     │
│  │  Resource Owner   │      │   Authorization Server        │     │
│  │  (User / Alice)   │      │   (Google, GitHub, Auth0,    │     │
│  │                   │      │    your own OAuth server)     │     │
│  └──────────┬────────┘      └───────────────┬──────────────┘     │
│             │ grants                         │ issues             │
│             │ permission                     │ tokens             │
│             ▼                               ▼                    │
│  ┌───────────────────┐      ┌──────────────────────────────┐     │
│  │      Client       │      │    Resource Server           │     │
│  │  (Your App /      │ ───► │  (API that holds Alice's      │     │
│  │   3rd-party app)  │      │   data: Google Drive, GitHub │     │
│  └───────────────────┘      └──────────────────────────────┘     │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

| Role | Definition | Example |
|---|---|---|
| **Resource Owner** | The user who owns the data and can grant access | Alice, the Google user |
| **Client** | The application requesting access on behalf of the user | Your web app, mobile app |
| **Authorization Server** | Issues tokens after verifying the user's consent | Google accounts.google.com |
| **Resource Server** | The API that serves protected resources | Google Drive API |

In many systems (like Auth0 or your own service), the Authorization Server and Resource Server are the same system. In Google's ecosystem, they're separate (`accounts.google.com` vs `drive.googleapis.com`).

### Confidential vs Public Clients

| | Confidential Client | Public Client |
|---|---|---|
| **Type** | Server-side app | SPA, mobile app, CLI |
| **Can keep secrets?** | Yes (code runs on your server) | No (code runs on user's device) |
| **Client secret** | Has one | Does NOT (or it's extractable) |
| **PKCE requirement** | Optional (but recommended) | Mandatory |
| **Example** | Node.js backend, Go service | React SPA, iOS app |

---

## 3. OAuth2 Grant Types

A **grant type** defines the mechanism by which a client obtains tokens. Different grants exist for different client types and use cases.

### Grant Type Decision Tree

```
Is this machine-to-machine (no user involved)?
  YES → Client Credentials Grant
  NO  ↓

Is the device input-constrained (TV, CLI, IoT)?
  YES → Device Authorization Grant
  NO  ↓

Is the client a browser-only SPA or mobile app?
  YES → Authorization Code + PKCE (Public client)
  NO  ↓

Is the client a server-side app?
  YES → Authorization Code + PKCE (Confidential client)
```

### Authorization Code Grant (+ PKCE)
- **Who uses it:** Web apps, SPAs, mobile apps
- **User interaction:** Yes — browser redirect to authorization server
- **Security level:** Highest for user-facing flows
- **PKCE:** Required for public clients, strongly recommended for all

### Client Credentials Grant
- **Who uses it:** Server-to-server, microservices, background jobs
- **User interaction:** None
- **Token acquired by:** Service authenticates directly with client ID + secret
- **Use case:** "Service A needs to call Service B's API"

### Device Authorization Grant (Device Flow)
- **Who uses it:** TV apps, CLI tools, IoT devices
- **User interaction:** User visits a URL on another device (phone/computer)
- **Use case:** "Login with GitHub" on a CLI tool — you can't easily open a browser

### Implicit Grant (DEPRECATED)
- **Why deprecated:** Access token was returned directly in the URL fragment (`#access_token=...`), exposing it in browser history, server logs, referrer headers, and via `window.location` to JavaScript
- **Replaced by:** Authorization Code + PKCE for SPAs
- **Do not use:** PKCE solves all the problems that motivated the Implicit grant

### Resource Owner Password Credentials Grant (ROPC — Also Deprecated)
- **What it does:** Client collects username/password directly and exchanges them for tokens
- **Why deprecated:** Defeats the purpose of OAuth2 — the client sees the user's password
- **Only exception:** First-party highly trusted clients migrating from basic auth (and even then, prefer Auth Code + PKCE)

---

## 4. Authorization Code + PKCE Flow (Deep Dive)

PKCE (Proof Key for Code Exchange, pronounced "pixy") was originally designed for mobile apps that couldn't keep client secrets, but is now recommended for ALL clients.

### The Problem PKCE Solves

Without PKCE, if an attacker intercepts the authorization code (e.g., via a malicious app registered for the same redirect URI scheme on mobile), they can exchange it for tokens. PKCE prevents this by binding the code exchange to the original authorization request.

### Step-by-Step Flow

```
Browser / Client App                  Auth Server                Resource Server
─────────────────                     ─────────────              ───────────────

Step 1: Generate PKCE pair
  code_verifier = random 43-128 char string (URL-safe base64)
  code_challenge = BASE64URL(SHA256(code_verifier))

Step 2: Build authorization URL
  GET https://auth.example.com/authorize?
    response_type=code
    &client_id=my_client_id
    &redirect_uri=https://myapp.com/callback
    &scope=openid profile email
    &state=RANDOM_STRING_32_BYTES     ← CSRF protection
    &code_challenge=BASE64URL_SHA256  ← PKCE
    &code_challenge_method=S256

  Store {state, code_verifier} in session/local storage

Step 3: User authenticates at auth server
  (User enters credentials, consents to scopes)

Step 4: Auth server redirects back with code
  GET https://myapp.com/callback?
    code=AUTHORIZATION_CODE
    &state=RANDOM_STRING_32_BYTES     ← verify matches what we sent!

Step 5: Verify state parameter
  stored_state == received_state?  ← If no, ABORT (CSRF attack)

Step 6: Exchange code for tokens
  POST https://auth.example.com/token
    Content-Type: application/x-www-form-urlencoded

    grant_type=authorization_code
    &code=AUTHORIZATION_CODE
    &redirect_uri=https://myapp.com/callback
    &client_id=my_client_id
    &client_secret=SECRET              ← confidential clients only
    &code_verifier=ORIGINAL_VERIFIER   ← PKCE: auth server recomputes SHA256 and verifies

Step 7: Auth server verifies
  SHA256(code_verifier) == stored_code_challenge?  ← PKCE check
  code not expired? (typically 30-60 seconds)
  code not already used? (one-time use)
  redirect_uri matches registration?

Step 8: Auth server responds with tokens
  {
    "access_token": "eyJ...",    ← opaque or JWT
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "rt_...",
    "id_token": "eyJ..."          ← OIDC only
  }

Step 9: Client validates ID token (OIDC)
  Verify signature, iss, aud (must match client_id!), exp, nonce
```

### PKCE Code Verifier and Challenge Generation

```javascript
// Generate code verifier: 43-128 URL-safe base64 chars
function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

// Generate code challenge: BASE64URL(SHA256(verifier))
async function generateCodeChallenge(verifier) {
  const data = new TextEncoder().encode(verifier);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}
```

### The Security Properties PKCE Provides

1. **If the code is intercepted:** Attacker has the code but not the `code_verifier`. They cannot exchange the code — the auth server will reject them.
2. **Binding to session:** The `code_verifier` proves this token exchange is being done by the same entity that started the authorization request.
3. **Why S256 and not plain:** `S256` uses SHA256(verifier) as the challenge. Even if the challenge is intercepted (it's sent in the URL), the attacker can't reverse SHA256 to get the verifier. `plain` method (sends verifier directly as challenge) provides no protection against interception.

---

## 5. Client Credentials Flow

The simplest OAuth2 flow. No user interaction. A service authenticates itself with its `client_id` and `client_secret` to get an access token.

```
Service A                           Auth Server                 Service B (API)
─────────                           ───────────                 ───────────────

POST /token
  grant_type=client_credentials
  client_id=service_a
  client_secret=SECRET
  scope=read:orders write:inventory
─────────────────────────────────►

                                    Verify client credentials
                                    Issue access token
                                    (no refresh token — just re-authenticate)
◄─────────────────────────────────
  {
    "access_token": "...",
    "token_type": "bearer",
    "expires_in": 3600
    // No refresh_token — get a new one when this expires
  }

GET /api/orders
Authorization: Bearer {access_token}
───────────────────────────────────────────────────────────────►

                                                                Validate token
                                                                Check scopes
◄───────────────────────────────────────────────────────────────
  200 OK { orders: [...] }
```

**Key differences from user-facing flows:**
- No user consent screen
- No refresh token — when the access token expires, the service simply re-authenticates
- Client authenticates via `client_id` + `client_secret` in the request body OR via HTTP Basic Auth
- Scopes are pre-configured (not user-granted)

---

## 6. Device Authorization Flow

For devices that can display a short code but can't easily receive redirect URIs.

```
Device (TV/CLI)                     Auth Server              User's Phone/Browser
────────────────                    ───────────              ────────────────────

POST /device/code
  client_id=tv_app
  scope=read:library
───────────────────►

                                    {
                                      "device_code": "DEVICE_CODE",
                                      "user_code": "ABCD-1234",
                                      "verification_uri": "https://auth.example.com/device",
                                      "expires_in": 600,
                                      "interval": 5
                                    }
◄───────────────────

Device displays:
  "Visit https://auth.example.com/device
   Enter code: ABCD-1234"

Poll every 5 seconds:            User visits URL, enters code,
POST /token                      authenticates, approves
  grant_type=device_code
  device_code=DEVICE_CODE        ◄─────────────────────────────
───────────────────►

                                    While not approved:
◄───────────────────               { "error": "authorization_pending" }

                                    After user approves:
◄───────────────────
                                    {
                                      "access_token": "...",
                                      "token_type": "bearer",
                                      "refresh_token": "..."
                                    }
```

---

## 7. OAuth2 Scopes

Scopes define what the access token permits. They're the "least privilege" mechanism of OAuth2.

```
scope=read:emails write:calendar profile offline_access
```

### Scope Design Patterns

**Coarse-grained (simple, less flexible):**
```
read     — read all resources
write    — write all resources
admin    — full access
```

**Fine-grained (better for least privilege):**
```
users:read         — read user profiles
users:write        — create/update users
orders:read        — read order data
orders:write       — create/update orders
payments:process   — process payments
```

**GitHub's approach:**
```
repo               — full control of private repos
repo:status        — only access commit status
public_repo        — only public repos
read:user          — read user profile data
user:email         — read email addresses
```

### `offline_access` Scope

The `offline_access` scope, per OAuth2 spec, is required to receive a refresh token. Without it, the authorization server may issue only an access token.

### OIDC Standard Scopes

| Scope | Claims returned by UserInfo endpoint |
|---|---|
| `openid` | Required. Signals OIDC flow |
| `profile` | `name`, `given_name`, `family_name`, `picture` |
| `email` | `email`, `email_verified` |
| `address` | `address` object |
| `phone` | `phone_number`, `phone_number_verified` |

---

## 8. Token Types in OAuth2

### Access Token
- Short-lived (minutes to hours)
- Sent in every API request (`Authorization: Bearer {token}`)
- Can be opaque (random string) or JWT
- Contains or represents the scopes granted

### Refresh Token
- Long-lived (days to months)
- Used ONLY to obtain new access tokens
- Stored server-side (at minimum a hash)
- Must be rotated (see Part 4.1)

### ID Token (OIDC only)
- Always a JWT
- Contains claims about the authenticated user
- Meant for the **client** to consume, not sent to APIs
- Must verify `aud` matches your `client_id`

```
Access Token: "I have permission to do X on behalf of User Alice"
  → Sent to APIs. APIs verify it.

Refresh Token: "I can get more Access Tokens for User Alice"
  → Sent only to the auth server. Never to APIs.

ID Token: "User Alice authenticated at time T with methods M"
  → Consumed by your app. Never sent to APIs.
```

---

## 9. The State Parameter (CSRF Protection)

The `state` parameter in the authorization request is a critical security mechanism.

### The Attack It Prevents

Without `state`:
```
1. Attacker starts OAuth2 flow on your site
2. Gets authorization URL: https://auth.example.com/authorize?...&redirect_uri=https://victim.com/callback
3. Attacker does NOT visit the URL, captures it
4. Attacker tricks victim into visiting the URL (CSRF, iframe, email link)
5. Victim authenticates (or is already authenticated)
6. Auth server redirects to victim's browser: https://victim.com/callback?code=ATTACKER_CONTROLLED_CODE
7. Victim's browser exchanges the code → victim is now logged in to attacker's account
8. Attacker's OAuth-linked account is now used by victim

This is an "OAuth CSRF" or "Authorization Code Injection" attack.
```

### The Defense

```
1. Before redirecting, generate a random state: state = random_bytes(32)
2. Store in session: session.oauth_state = state
3. Include in authorization URL: &state={state}
4. In callback handler:
   a. Retrieve state from callback: req.query.state
   b. Compare to session: session.oauth_state
   c. If they don't match → REJECT. Possible CSRF attack.
   d. If they match → proceed to code exchange
   e. Delete state from session (one-time use)
```

```go
// Go: state generation and verification
func startOAuth(w http.ResponseWriter, r *http.Request) {
    state := generateSecureRandom(32) // 256 bits of entropy
    
    // Store in session
    session := getSession(r)
    session.Set("oauth_state", state)
    session.Save(w, r)
    
    authURL := oauthConfig.AuthCodeURL(state,
        oauth2.SetAuthURLParam("code_challenge", codeChallenge),
        oauth2.SetAuthURLParam("code_challenge_method", "S256"),
    )
    http.Redirect(w, r, authURL, http.StatusTemporaryRedirect)
}

func handleCallback(w http.ResponseWriter, r *http.Request) {
    session := getSession(r)
    storedState := session.Get("oauth_state")
    receivedState := r.URL.Query().Get("state")
    
    // Constant-time comparison to prevent timing attacks
    if subtle.ConstantTimeCompare([]byte(storedState), []byte(receivedState)) != 1 {
        http.Error(w, "invalid state parameter", http.StatusBadRequest)
        return
    }
    
    session.Delete("oauth_state")
    
    // Proceed with code exchange...
}
```

### Nonce (OIDC)

The `nonce` parameter in OIDC serves a similar function but for ID tokens. Include a random nonce in the authorization request; the auth server embeds it in the ID token. Verify the nonce in the ID token matches what you sent.

This prevents replay attacks — an old ID token cannot be reused for a new session because the nonce won't match.

---

## 10. OpenID Connect (OIDC)

OIDC (OpenID Connect) is a thin identity layer built on top of OAuth2. It standardizes:

1. **Identity:** An ID Token (JWT) that proves who the user is
2. **UserInfo endpoint:** A standardized API to fetch user claims
3. **Discovery:** A `.well-known/openid-configuration` endpoint that describes the server
4. **Standard claims:** Consistent field names across providers

### What OIDC Adds to OAuth2

```
OAuth2 alone:
  "Here's an access token to read Alice's GitHub repos"
  → Does NOT tell you WHO Alice is

OAuth2 + OIDC:
  "Here's an access token + here's an ID token that proves Alice is alice@example.com"
  → Both authorization AND authentication
```

### The ID Token

```json
{
  "iss": "https://accounts.google.com",
  "sub": "110169484474386276334",       ← stable user identifier
  "aud": "my_client_id",                ← MUST match your client_id
  "exp": 1719653600,
  "iat": 1719650000,
  "nonce": "abc123",                    ← MUST match what you sent
  "email": "alice@gmail.com",
  "email_verified": true,
  "name": "Alice Smith",
  "picture": "https://..."
}
```

**Critical validations for ID token:**
1. `iss` must match the expected issuer
2. `aud` must contain your `client_id`
3. `exp` must be in the future
4. `iat` should be recent (within clock skew tolerance)
5. `nonce` must match what you stored before the flow

### OIDC Discovery Endpoint

```
GET https://accounts.google.com/.well-known/openid-configuration

{
  "issuer": "https://accounts.google.com",
  "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
  "token_endpoint": "https://oauth2.googleapis.com/token",
  "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
  "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
  "scopes_supported": ["openid", "email", "profile"],
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
  "id_token_signing_alg_values_supported": ["RS256"]
}
```

The `jwks_uri` points to the public keys used to sign ID tokens. Your app fetches these (and caches them) to verify the ID token signature.

### ID Token vs Access Token

| | ID Token | Access Token |
|---|---|---|
| **Purpose** | Authenticate the user | Authorize API calls |
| **Format** | Always JWT | JWT or opaque |
| **Audience** | Your client application | The resource server (API) |
| **Send to APIs?** | No | Yes |
| **Contains** | User identity claims | Scopes, user reference |

**Common mistake:** Sending the ID token to your own API for verification. The API should receive the access token. The ID token is for the client app (frontend/backend) to know who logged in.

### UserInfo Endpoint

```
GET https://openidconnect.googleapis.com/v1/userinfo
Authorization: Bearer {access_token}  ← access token, not ID token

→ {
    "sub": "110169484474386276334",
    "name": "Alice Smith",
    "email": "alice@gmail.com",
    "email_verified": true,
    "picture": "https://..."
  }
```

The UserInfo endpoint returns the same claims as the ID token but is a live lookup. Prefer using the ID token claims directly (already validated) rather than making an extra HTTP call.

---

## 11. API Keys

API keys are a simpler alternative to OAuth2, suitable for specific use cases.

### When to Use API Keys vs OAuth2

| Scenario | Recommendation |
|---|---|
| Machine-to-machine, same organization | API Key or Client Credentials |
| Machine-to-machine, external partners | Client Credentials (OAuth2) |
| User delegates access to third-party | OAuth2 Authorization Code |
| Simple integration, no user data | API Key |
| Need scoped access | OAuth2 scopes > API key scopes |
| High-security enterprise integrations | OAuth2 + PKCE + mTLS |

**API keys excel when:**
- Simple server-to-server integrations where OAuth2 is overkill
- Public APIs with many developers (e.g., payment processors, weather APIs, mapping APIs)
- Early-stage APIs where OAuth2 complexity isn't justified yet
- The consumer is a trusted server (not a browser)

### API Key Format Best Practices

```
Format: {prefix}_{environment}_{random_bytes}

Examples (never use real keys in code or docs):
  sk_live_<your_production_secret_key>    (production secret key)
  sk_test_<your_test_secret_key>          (test/sandbox key)
  pk_live_<your_production_public_key>    (public key, safe for frontend)

Benefits of prefixes:
  - "sk_live_" in a GitHub commit triggers automated secret scanning alerts
  - GitHub, GitLab, and secret scanning tools know to alert on these patterns
  - Users and ops teams can immediately identify a leaked key's environment
  - Easy to search logs for accidental exposure

Random part:
  - 32+ bytes from a CSPRNG (crypto/rand in Go, secrets.token_hex in Python)
  - URL-safe base64 or hex encoding
  - Never use UUIDs (too short, non-random UUID versions exist)
```

**Well-known prefixes in the wild:**
```
Stripe:  sk_live_... / pk_live_...
Twilio:  SK... (SIDs)
Sendgrid: SG....
OpenAI:  sk-...
GitHub:  ghp_... (personal access tokens)
```

### API Key Types

| Type | Purpose | Prefix |
|---|---|---|
| **Secret key** | Server-to-server, full permissions | `sk_live_`, `sk_test_` |
| **Publishable key** | Client-safe, read-only | `pk_live_`, `pk_test_` |
| **Restricted key** | Limited scopes | Custom |

---

## 12. API Key Security

### Storage: Hash It, Never Store Plaintext

Store a hash of the API key, never the plaintext. This way, a database breach doesn't expose usable keys.

```
Key generation:
  1. Generate random key: sk_live_a1b2c3d4e5...
  2. Show to user ONCE (this is the only time)
  3. Hash it: SHA256(key) → hash
  4. Store in DB: { id, prefix_hint: "sk_live_a1b2", hash, user_id, scopes, created_at }

Key verification:
  1. Receive key from request header: X-API-Key: sk_live_a1b2c3d4e5...
  2. Hash it: SHA256(key)
  3. Lookup in DB: SELECT * FROM api_keys WHERE hash = $1
  4. If found and not revoked → authenticate

Why SHA256 (not bcrypt) for API keys?
  bcrypt is intentionally slow (defense against password brute-force).
  API keys are 256+ bits of randomness — brute force is computationally infeasible.
  SHA256 is fast (~microseconds), which matters since you compute it on every request.
  bcrypt's slowness would add 100-300ms to every API call.
```

### Store a Prefix Hint for Identification

Since you can't reverse the hash, users need a way to identify which key is which:
```sql
CREATE TABLE api_keys (
    id          UUID PRIMARY KEY,
    prefix_hint VARCHAR(12) NOT NULL,     -- "sk_live_a1b2" — first 12 chars, safe to store
    key_hash    BYTEA NOT NULL UNIQUE,    -- SHA256 of full key
    user_id     UUID NOT NULL,
    name        VARCHAR(255),            -- user-provided label: "Production API"
    scopes      TEXT[],
    last_used_at TIMESTAMP,
    expires_at  TIMESTAMP,
    created_at  TIMESTAMP DEFAULT NOW(),
    revoked_at  TIMESTAMP
);

-- Fast lookup index on hash
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
```

### API Key Rotation

Provide a first-class rotation mechanism:
1. User generates a new key
2. Both old and new key work during a transition period (e.g., 24 hours)
3. User updates their integration with the new key
4. User revokes the old key (or it auto-expires)

Never force instant revocation without a transition period — this causes downtime.

### Rate Limiting Per Key

Each API key should have its own rate limit budget:
```
key_1: 1000 requests/minute → quota tracked in Redis
key_2: 100 requests/minute  → lower tier
key_3: 10000 requests/minute → enterprise tier
```

```go
// Redis-based sliding window rate limiter per API key
func checkRateLimit(ctx context.Context, rdb *redis.Client, keyID string, limit int, window time.Duration) (bool, int, error) {
    now := time.Now().UnixMilli()
    windowStart := now - window.Milliseconds()
    
    pipe := rdb.Pipeline()
    
    // Remove entries older than window
    pipe.ZRemRangeByScore(ctx, "ratelimit:"+keyID,
        "-inf", strconv.FormatInt(windowStart, 10))
    
    // Count entries in window
    countCmd := pipe.ZCard(ctx, "ratelimit:"+keyID)
    
    // Add current request
    pipe.ZAdd(ctx, "ratelimit:"+keyID, redis.Z{
        Score:  float64(now),
        Member: strconv.FormatInt(now, 10) + "-" + uuid.New().String(),
    })
    
    // Set TTL on the key
    pipe.Expire(ctx, "ratelimit:"+keyID, window)
    
    _, err := pipe.Exec(ctx)
    if err != nil {
        return false, 0, err
    }
    
    count := int(countCmd.Val())
    remaining := limit - count - 1
    if remaining < 0 {
        remaining = 0
    }
    
    return count < limit, remaining, nil
}
```

---

## 13. Implementation Examples

### Go + Chi: OAuth2 Client Credentials + API Key Middleware

```go
package main

import (
    "context"
    "crypto/sha256"
    "crypto/subtle"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "net/http"
    "os"
    "strings"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"
    "golang.org/x/oauth2"
    "golang.org/x/oauth2/clientcredentials"
)

// --------------------------------------------------------------------------
// API Key types
// --------------------------------------------------------------------------

type APIKey struct {
    ID       string
    UserID   string
    Name     string
    Scopes   []string
    KeyHash  []byte
    RevokedAt *time.Time
}

type APIKeyStore interface {
    GetByHash(ctx context.Context, hash []byte) (*APIKey, error)
    UpdateLastUsed(ctx context.Context, keyID string) error
}

// --------------------------------------------------------------------------
// API Key middleware
// --------------------------------------------------------------------------

type contextKey string
const contextKeyAPIKey contextKey = "api_key"

func APIKeyMiddleware(store APIKeyStore) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            // Accept key from header or query param (header preferred)
            apiKey := r.Header.Get("X-API-Key")
            if apiKey == "" {
                apiKey = r.URL.Query().Get("api_key") // discourage this but support it
            }

            if apiKey == "" {
                writeJSON(w, http.StatusUnauthorized, map[string]string{
                    "error": "missing API key (provide via X-API-Key header)",
                })
                return
            }

            // Hash the key for lookup
            hash := hashAPIKey(apiKey)

            key, err := store.GetByHash(r.Context(), hash)
            if err != nil || key == nil {
                writeJSON(w, http.StatusUnauthorized, map[string]string{
                    "error": "invalid API key",
                })
                return
            }

            if key.RevokedAt != nil {
                writeJSON(w, http.StatusUnauthorized, map[string]string{
                    "error": "API key has been revoked",
                })
                return
            }

            // Async update last_used_at — don't block the request
            go store.UpdateLastUsed(context.Background(), key.ID)

            // Inject key info into context
            ctx := context.WithValue(r.Context(), contextKeyAPIKey, key)
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}

func hashAPIKey(key string) []byte {
    hash := sha256.Sum256([]byte(key))
    return hash[:]
}

// --------------------------------------------------------------------------
// Scope-based authorization for API keys
// --------------------------------------------------------------------------

func RequireScope(scope string) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            key, ok := r.Context().Value(contextKeyAPIKey).(*APIKey)
            if !ok {
                writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthenticated"})
                return
            }

            for _, s := range key.Scopes {
                if s == scope || s == "*" {
                    next.ServeHTTP(w, r)
                    return
                }
            }

            writeJSON(w, http.StatusForbidden, map[string]string{
                "error": fmt.Sprintf("API key missing required scope: %s", scope),
            })
        })
    }
}

// --------------------------------------------------------------------------
// OAuth2 Client Credentials — outbound (this service calls another service)
// --------------------------------------------------------------------------

func NewServiceClient(tokenURL, clientID, clientSecret string, scopes []string) *http.Client {
    config := clientcredentials.Config{
        ClientID:     clientID,
        ClientSecret: clientSecret,
        TokenURL:     tokenURL,
        Scopes:       scopes,
    }

    // TokenSource automatically refreshes tokens before expiry
    ctx := context.Background()
    return config.Client(ctx) // wraps http.Client with automatic token injection
}

// --------------------------------------------------------------------------
// OAuth2 Authorization Code flow (server-side)
// --------------------------------------------------------------------------

var oauthConfig = &oauth2.Config{
    ClientID:     os.Getenv("OAUTH_CLIENT_ID"),
    ClientSecret: os.Getenv("OAUTH_CLIENT_SECRET"),
    RedirectURL:  "https://myapp.com/auth/callback",
    Scopes:       []string{"openid", "profile", "email", "offline_access"},
    Endpoint: oauth2.Endpoint{
        AuthURL:  "https://accounts.google.com/o/oauth2/v2/auth",
        TokenURL: "https://oauth2.googleapis.com/token",
    },
}

func oauthStartHandler(w http.ResponseWriter, r *http.Request) {
    // Generate PKCE pair
    verifier, err := generateCodeVerifier()
    if err != nil {
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }
    challenge := generateCodeChallenge(verifier)

    // Generate state
    state := generateSecureRandom(32)

    // Store state + verifier in session
    session := getSession(r)
    session.Values["oauth_state"] = state
    session.Values["pkce_verifier"] = verifier
    session.Save(r, w)

    // Build auth URL
    authURL := oauthConfig.AuthCodeURL(state,
        oauth2.SetAuthURLParam("code_challenge", challenge),
        oauth2.SetAuthURLParam("code_challenge_method", "S256"),
        oauth2.AccessTypeOffline, // request refresh token
    )

    http.Redirect(w, r, authURL, http.StatusTemporaryRedirect)
}

func oauthCallbackHandler(w http.ResponseWriter, r *http.Request) {
    session := getSession(r)

    // Verify state
    storedState, ok := session.Values["oauth_state"].(string)
    receivedState := r.URL.Query().Get("state")

    if !ok || subtle.ConstantTimeCompare([]byte(storedState), []byte(receivedState)) != 1 {
        http.Error(w, "invalid state parameter — possible CSRF attack", http.StatusBadRequest)
        return
    }

    // Check for error from auth server
    if errParam := r.URL.Query().Get("error"); errParam != "" {
        errDesc := r.URL.Query().Get("error_description")
        http.Error(w, fmt.Sprintf("oauth error: %s: %s", errParam, errDesc), http.StatusBadRequest)
        return
    }

    code := r.URL.Query().Get("code")
    verifier := session.Values["pkce_verifier"].(string)

    // Exchange code for tokens (with PKCE verifier)
    token, err := oauthConfig.Exchange(r.Context(), code,
        oauth2.SetAuthURLParam("code_verifier", verifier),
    )
    if err != nil {
        http.Error(w, "failed to exchange code", http.StatusInternalServerError)
        return
    }

    // Extract ID token (OIDC)
    idToken, ok := token.Extra("id_token").(string)
    if !ok {
        http.Error(w, "missing id_token", http.StatusInternalServerError)
        return
    }

    // Validate and parse ID token...
    _ = idToken

    // Clean up session state
    delete(session.Values, "oauth_state")
    delete(session.Values, "pkce_verifier")
    session.Save(r, w)

    http.Redirect(w, r, "/dashboard", http.StatusTemporaryRedirect)
}

// --------------------------------------------------------------------------
// Router
// --------------------------------------------------------------------------

func NewRouter(apiKeyStore APIKeyStore) http.Handler {
    r := chi.NewRouter()
    r.Use(middleware.RequestID)
    r.Use(middleware.Logger)
    r.Use(middleware.Recoverer)

    // OAuth2 endpoints
    r.Get("/auth/login", oauthStartHandler)
    r.Get("/auth/callback", oauthCallbackHandler)

    // API key protected routes
    r.Route("/v1", func(r chi.Router) {
        r.Use(APIKeyMiddleware(apiKeyStore))

        r.Route("/orders", func(r chi.Router) {
            r.With(RequireScope("orders:read")).Get("/", listOrdersHandler)
            r.With(RequireScope("orders:write")).Post("/", createOrderHandler)
        })
    })

    return r
}

// --------------------------------------------------------------------------
// Stubs
// --------------------------------------------------------------------------

func listOrdersHandler(w http.ResponseWriter, r *http.Request) {
    writeJSON(w, http.StatusOK, map[string]interface{}{"orders": []string{}})
}

func createOrderHandler(w http.ResponseWriter, r *http.Request) {
    writeJSON(w, http.StatusCreated, map[string]string{"id": "new-order"})
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(v)
}

func generateSecureRandom(n int) string {
    b := make([]byte, n)
    _, _ = rand.Read(b)
    return hex.EncodeToString(b)
}

func generateCodeVerifier() (string, error) {
    b := make([]byte, 32)
    if _, err := rand.Read(b); err != nil {
        return "", err
    }
    return base64.RawURLEncoding.EncodeToString(b), nil
}

func generateCodeChallenge(verifier string) string {
    h := sha256.New()
    h.Write([]byte(verifier))
    return base64.RawURLEncoding.EncodeToString(h.Sum(nil))
}
```

---

### Node.js + Express: OAuth2 + API Keys

```javascript
// oauth.js + apikeys.js
import express from 'express';
import crypto from 'crypto';
import axios from 'axios';
import qs from 'qs';

const app = express();
app.use(express.json());

// ── PKCE utilities ──────────────────────────────────────────────────────────

function generateCodeVerifier() {
  return crypto.randomBytes(32).toString('base64url'); // URL-safe base64
}

function generateCodeChallenge(verifier) {
  return crypto.createHash('sha256').update(verifier).digest('base64url');
}

// ── OAuth2 Authorization Code + PKCE flow ───────────────────────────────────

const OAUTH_CONFIG = {
  clientId: process.env.OAUTH_CLIENT_ID,
  clientSecret: process.env.OAUTH_CLIENT_SECRET,
  redirectUri: 'https://myapp.com/auth/callback',
  authorizationEndpoint: 'https://accounts.google.com/o/oauth2/v2/auth',
  tokenEndpoint: 'https://oauth2.googleapis.com/token',
  scopes: ['openid', 'profile', 'email', 'offline_access'],
};

app.get('/auth/login', (req, res) => {
  const state = crypto.randomBytes(32).toString('hex');
  const verifier = generateCodeVerifier();
  const challenge = generateCodeChallenge(verifier);

  // Store in session
  req.session.oauthState = state;
  req.session.pkceVerifier = verifier;

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: OAUTH_CONFIG.clientId,
    redirect_uri: OAUTH_CONFIG.redirectUri,
    scope: OAUTH_CONFIG.scopes.join(' '),
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256',
    access_type: 'offline', // Google-specific: get refresh token
    prompt: 'consent',      // Google-specific: always show consent
  });

  res.redirect(`${OAUTH_CONFIG.authorizationEndpoint}?${params}`);
});

app.get('/auth/callback', async (req, res) => {
  const { code, state, error, error_description } = req.query;

  // Handle auth server error
  if (error) {
    return res.status(400).json({
      error,
      description: error_description,
    });
  }

  // Verify state (CSRF protection)
  const storedState = req.session.oauthState;
  if (!storedState || !crypto.timingSafeEqual(
    Buffer.from(storedState),
    Buffer.from(state || '')
  )) {
    return res.status(400).json({ error: 'invalid state — possible CSRF attack' });
  }

  const verifier = req.session.pkceVerifier;
  delete req.session.oauthState;
  delete req.session.pkceVerifier;

  try {
    // Exchange code for tokens
    const tokenResponse = await axios.post(
      OAUTH_CONFIG.tokenEndpoint,
      qs.stringify({
        grant_type: 'authorization_code',
        code,
        redirect_uri: OAUTH_CONFIG.redirectUri,
        client_id: OAUTH_CONFIG.clientId,
        client_secret: OAUTH_CONFIG.clientSecret, // confidential client
        code_verifier: verifier,
      }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );

    const { access_token, refresh_token, id_token, expires_in } = tokenResponse.data;

    // Validate and decode ID token
    const idTokenPayload = decodeAndValidateIdToken(id_token);
    
    // Create session for user
    req.session.userId = idTokenPayload.sub;
    req.session.user = {
      email: idTokenPayload.email,
      name: idTokenPayload.name,
    };

    res.redirect('/dashboard');
  } catch (err) {
    console.error('Token exchange failed:', err.response?.data || err.message);
    res.status(500).json({ error: 'authentication failed' });
  }
});

// Validate ID token (basic — use a proper OIDC library in production)
function decodeAndValidateIdToken(idToken) {
  const [headerB64, payloadB64] = idToken.split('.');
  const payload = JSON.parse(Buffer.from(payloadB64, 'base64url').toString());

  // Validate claims
  if (payload.aud !== OAUTH_CONFIG.clientId) {
    throw new Error(`invalid aud: ${payload.aud}`);
  }
  if (payload.iss !== 'https://accounts.google.com') {
    throw new Error(`invalid iss: ${payload.iss}`);
  }
  if (payload.exp < Math.floor(Date.now() / 1000)) {
    throw new Error('id token expired');
  }

  return payload;
}

// ── OAuth2 Client Credentials (outbound — this service calls another) ────────

class ServiceTokenManager {
  constructor({ tokenUrl, clientId, clientSecret, scopes }) {
    this.tokenUrl = tokenUrl;
    this.clientId = clientId;
    this.clientSecret = clientSecret;
    this.scopes = scopes;
    this.cachedToken = null;
    this.tokenExpiry = null;
  }

  async getToken() {
    // Return cached token if still valid (with 30s buffer)
    if (this.cachedToken && this.tokenExpiry > Date.now() + 30000) {
      return this.cachedToken;
    }

    const response = await axios.post(
      this.tokenUrl,
      qs.stringify({
        grant_type: 'client_credentials',
        client_id: this.clientId,
        client_secret: this.clientSecret,
        scope: this.scopes.join(' '),
      }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );

    this.cachedToken = response.data.access_token;
    this.tokenExpiry = Date.now() + response.data.expires_in * 1000;
    return this.cachedToken;
  }

  async request(method, url, data) {
    const token = await this.getToken();
    return axios({ method, url, data, headers: { Authorization: `Bearer ${token}` } });
  }
}

// ── API Key middleware ────────────────────────────────────────────────────────

function hashApiKey(key) {
  return crypto.createHash('sha256').update(key).digest('hex');
}

function apiKeyMiddleware(apiKeyStore) {
  return async (req, res, next) => {
    const apiKey = req.headers['x-api-key'];
    if (!apiKey) {
      return res.status(401).json({ error: 'missing X-API-Key header' });
    }

    // Basic format validation
    if (!apiKey.startsWith('sk_live_') && !apiKey.startsWith('sk_test_')) {
      return res.status(401).json({ error: 'invalid API key format' });
    }

    const keyHash = hashApiKey(apiKey);
    const keyRecord = await apiKeyStore.findByHash(keyHash);

    if (!keyRecord || keyRecord.revokedAt) {
      return res.status(401).json({ error: 'invalid API key' });
    }

    req.apiKey = keyRecord;
    next();
  };
}

function requireScope(scope) {
  return (req, res, next) => {
    if (!req.apiKey) {
      return res.status(401).json({ error: 'unauthenticated' });
    }
    if (!req.apiKey.scopes.includes(scope) && !req.apiKey.scopes.includes('*')) {
      return res.status(403).json({ error: `missing required scope: ${scope}` });
    }
    next();
  };
}

// ── API Key generation ────────────────────────────────────────────────────────

function generateApiKey(environment = 'live') {
  const randomPart = crypto.randomBytes(24).toString('base64url'); // 192 bits of randomness
  return `sk_${environment}_${randomPart}`;
}

// Usage:
// const key = generateApiKey('live');          → "sk_live_a1b2c3..."
// const hash = hashApiKey(key);               → store this in DB
// show key to user ONCE, never retrieve again

// Protected routes
app.use('/v1', apiKeyMiddleware(apiKeyStore));
app.get('/v1/orders', requireScope('orders:read'), (req, res) => {
  res.json({ orders: [] });
});
app.post('/v1/orders', requireScope('orders:write'), (req, res) => {
  res.status(201).json({ id: 'new-order' });
});
```

---

### Python + FastAPI: OAuth2 + API Keys

```python
# oauth.py
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timezone
from typing import Annotated, Optional
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

router = APIRouter(tags=["auth"])

OAUTH_CONFIG = {
    "client_id": os.environ["OAUTH_CLIENT_ID"],
    "client_secret": os.environ["OAUTH_CLIENT_SECRET"],
    "redirect_uri": "https://myapp.com/auth/callback",
    "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_endpoint": "https://oauth2.googleapis.com/token",
    "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
    "scopes": ["openid", "profile", "email", "offline_access"],
}

# ── PKCE utilities ─────────────────────────────────────────────────────────────

import base64
import hashlib

def generate_code_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()

def generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

# ── OAuth2 Authorization Code + PKCE ──────────────────────────────────────────

@router.get("/auth/login")
async def oauth_login(request: Request) -> RedirectResponse:
    state = secrets.token_hex(32)
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)

    # Store in session
    request.session["oauth_state"] = state
    request.session["pkce_verifier"] = verifier

    params = urlencode({
        "response_type": "code",
        "client_id": OAUTH_CONFIG["client_id"],
        "redirect_uri": OAUTH_CONFIG["redirect_uri"],
        "scope": " ".join(OAUTH_CONFIG["scopes"]),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    })

    return RedirectResponse(
        f"{OAUTH_CONFIG['authorization_endpoint']}?{params}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/auth/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
) -> RedirectResponse:
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}: {error_description}",
        )

    # Verify state
    stored_state = request.session.get("oauth_state")
    if not stored_state or not secrets.compare_digest(stored_state, state or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid state — possible CSRF attack",
        )

    verifier = request.session.pop("pkce_verifier", None)
    del request.session["oauth_state"]

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            OAUTH_CONFIG["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": OAUTH_CONFIG["redirect_uri"],
                "client_id": OAUTH_CONFIG["client_id"],
                "client_secret": OAUTH_CONFIG["client_secret"],
                "code_verifier": verifier,
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="token exchange failed",
            )

        tokens = token_response.json()

    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(status_code=500, detail="missing id_token")

    # Validate ID token (use PyJWT with JWKS in production)
    payload = validate_id_token(id_token)

    request.session["user_id"] = payload["sub"]
    request.session["user"] = {"email": payload["email"], "name": payload.get("name")}

    return RedirectResponse("/dashboard", status_code=status.HTTP_302_FOUND)


def validate_id_token(id_token: str) -> dict:
    """
    In production: fetch JWKS from jwks_uri, cache it, and use jwt.decode
    with the appropriate key from the JWKS. Using jwt.decode here for illustration.
    """
    header = jwt.get_unverified_header(id_token)
    # Fetch the right key from JWKS based on header["kid"]
    # For now, illustrate the validation logic:
    payload = jwt.decode(
        id_token,
        options={"verify_signature": False},  # Would verify in production
    )
    
    if payload.get("aud") != OAUTH_CONFIG["client_id"]:
        raise ValueError(f"invalid aud: {payload.get('aud')}")
    
    if payload.get("exp", 0) < datetime.now(tz=timezone.utc).timestamp():
        raise ValueError("id token expired")

    return payload


# ── API Key middleware (FastAPI dependency) ────────────────────────────────────

from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyRecord(BaseModel):
    id: str
    user_id: str
    name: str
    scopes: list[str]
    revoked_at: Optional[datetime] = None


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def get_api_key(
    api_key: Annotated[Optional[str], Depends(api_key_header)],
    api_key_store: Annotated[APIKeyStore, Depends(get_api_key_store)],
) -> APIKeyRecord:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing X-API-Key header",
        )

    # Validate format
    if not (api_key.startswith("sk_live_") or api_key.startswith("sk_test_")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid API key format",
        )

    key_hash = hash_api_key(api_key)
    record = await api_key_store.find_by_hash(key_hash)

    if not record or record.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid API key",
        )

    return record

APIKeyAuth = Annotated[APIKeyRecord, Depends(get_api_key)]


def require_scope(scope: str):
    async def _check_scope(key: APIKeyAuth) -> APIKeyRecord:
        if scope not in key.scopes and "*" not in key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required scope: {scope}",
            )
        return key
    return _check_scope


# ── API Key generation ─────────────────────────────────────────────────────────

def generate_api_key(environment: str = "live") -> str:
    random_part = secrets.token_urlsafe(32)  # 256 bits of URL-safe randomness
    return f"sk_{environment}_{random_part}"


# ── Protected routes ──────────────────────────────────────────────────────────

api_router = APIRouter(prefix="/v1", tags=["api"])

@api_router.get("/orders")
async def list_orders(
    key: Annotated[APIKeyRecord, Depends(require_scope("orders:read"))],
) -> dict:
    return {"orders": [], "key_owner": key.user_id}


@api_router.post("/orders", status_code=201)
async def create_order(
    key: Annotated[APIKeyRecord, Depends(require_scope("orders:write"))],
) -> dict:
    return {"id": "new-order"}


# ── OAuth2 Client Credentials (outbound) ─────────────────────────────────────

class ServiceTokenManager:
    """Token manager for machine-to-machine calls using Client Credentials."""

    def __init__(self, token_url: str, client_id: str, client_secret: str, scopes: list[str]):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self._token: Optional[str] = None
        self._expires_at: float = 0

    async def get_token(self) -> str:
        import time
        # Return cached token with 30s buffer
        if self._token and self._expires_at > time.time() + 30:
            return self._token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": " ".join(self.scopes),
                },
            )
            response.raise_for_status()
            data = response.json()

        self._token = data["access_token"]
        self._expires_at = time.time() + data.get("expires_in", 3600)
        return self._token

    async def get(self, url: str, **kwargs) -> httpx.Response:
        token = await self.get_token()
        async with httpx.AsyncClient() as client:
            return await client.get(
                url, headers={"Authorization": f"Bearer {token}"}, **kwargs
            )


# Stubs
class APIKeyStore:
    async def find_by_hash(self, key_hash: str) -> Optional[APIKeyRecord]: ...

async def get_api_key_store() -> APIKeyStore: ...
```

---

## Common Patterns & Best Practices

### 1. Always Use PKCE, Even for Confidential Clients
PKCE was designed for public clients but is recommended for all. The extra roundtrip is minimal overhead and provides protection against authorization code injection attacks.

### 2. Validate All ID Token Claims
Check `iss`, `aud` (must match your `client_id`), `exp`, `iat`, and `nonce`. Never accept an ID token without verifying the audience — this is the primary OIDC security invariant.

### 3. Cache Service Tokens with Buffer
When using Client Credentials for service-to-service calls, cache the token and refresh it before it expires (30-60 second buffer). Never request a new token on every API call.

### 4. Store API Keys as SHA256 Hashes
SHA256 is appropriate for API key storage (unlike bcrypt for passwords) because API keys have sufficient entropy to be brute-force infeasible, and SHA256's speed doesn't matter for security here while mattering a lot for per-request lookup performance.

### 5. Use Prefix-Based Format for API Keys
The format `sk_live_xxxxx` enables:
- Automated secret scanning in code repositories
- Quick identification of key environment (live vs test)
- User-facing identification without revealing the key

### 6. Scope Validation Should Be Declarative
Don't scatter `if key.scopes.includes('orders:read')` checks inside handlers. Use middleware or dependency injection that raises/returns errors automatically. This prevents accidentally forgetting the check.

---

## Common Pitfalls

- ❌ **WRONG:** Using OAuth2 access tokens for authentication without OIDC
  ```javascript
  // WRONG: OAuth2 access token doesn't prove who the user is to YOUR app
  const user = await googleapis.getProfile(accessToken);
  req.user = user;
  ```
  **✅ CORRECT:** Use the ID token (OIDC) for authentication. Verify `aud` matches your client ID.

- ❌ **WRONG:** Not verifying the `state` parameter in OAuth2 callbacks
  **✅ CORRECT:** Always verify `state` matches before processing the authorization code. Use `crypto.timingSafeEqual` or `secrets.compare_digest` for comparison.

- ❌ **WRONG:** Using the Implicit grant type for SPAs
  **✅ CORRECT:** Use Authorization Code + PKCE. Implicit was deprecated because access tokens in URL fragments are visible in browser history, logs, and referrer headers.

- ❌ **WRONG:** Sending the ID token to your API as authentication
  **✅ CORRECT:** ID token is for your client (frontend) to consume. Send the access token to APIs.

- ❌ **WRONG:** Storing API keys in plaintext in the database
  ```sql
  INSERT INTO api_keys (key) VALUES ('sk_live_abc123...');
  ```
  **✅ CORRECT:** Store `SHA256(key)`. Show the key to the user once at creation time. You cannot retrieve it again.

- ❌ **WRONG:** Using UUID for API key random part
  **✅ CORRECT:** Use 24+ random bytes from a CSPRNG. UUID v4 is only 122 bits of randomness and some UUID versions aren't random at all.

- ❌ **WRONG:** Using `plain` PKCE method instead of `S256`
  **✅ CORRECT:** Always use `S256`. `plain` sends the verifier as the challenge, providing no protection if the challenge is intercepted.

- ❌ **WRONG:** Requesting overly broad scopes
  ```
  scope: "admin"   ← gives access to everything
  ```
  **✅ CORRECT:** Request minimum scopes needed. Users see scope consent screens — broad scopes reduce trust and conversion.

- ❌ **WRONG:** Trusting `client_id` in a token issued for a different service
  **✅ CORRECT:** Always verify `aud` claim matches the expected value for your service. A token for `api.example.com` should be rejected by `admin.example.com`.

---

## Interview Questions

**Q1. What is the difference between OAuth2 and OIDC?**

**Answer:** OAuth2 is an authorization framework — it defines how users delegate access to their resources to third-party applications. OAuth2 issues access tokens that represent permission to perform actions on behalf of a user, but says nothing about who that user is.

OIDC (OpenID Connect) is an identity layer built on top of OAuth2. It adds an ID token (always a JWT), a standard UserInfo endpoint, a discovery document, and standardized claims about the authenticated user. When you want to know who the user is — not just what they've authorized — you use OIDC. You can think of it as: "OAuth2 is about `what`, OIDC is about `who`."

The practical difference: when implementing "Login with Google," use OIDC (request `openid` scope, validate the ID token). When implementing "Give this app access to my Google Calendar," use OAuth2 alone.

---

**Q2. What is PKCE and why was it introduced?**

**Answer:** PKCE (Proof Key for Code Exchange, RFC 7636) is a security extension to the OAuth2 Authorization Code grant that prevents authorization code interception attacks.

Without PKCE, on mobile apps, an attacker's malicious app registered with the same custom URL scheme (`myapp://`) could intercept the authorization code redirect and exchange the code for tokens.

PKCE works by generating a cryptographic challenge before starting the flow:
1. Client generates a random `code_verifier` (32+ bytes)
2. Client computes `code_challenge = BASE64URL(SHA256(code_verifier))`
3. Client includes `code_challenge` in the authorization request
4. Auth server stores it alongside the authorization code
5. When exchanging the code, client sends `code_verifier`
6. Auth server verifies `SHA256(code_verifier) == stored_code_challenge`

Even if an attacker intercepts the code, they can't exchange it — they don't have the `code_verifier`. PKCE was originally for mobile public clients but is now recommended for all clients since it provides security with minimal overhead.

---

**Q3. Why is the Implicit grant type deprecated?**

**Answer:** The Implicit grant returned the access token directly in the URL fragment (`#access_token=...`). This exposed tokens in:
- Browser history
- Server access logs (via Referer header when navigating to another page)
- JavaScript's `window.location`
- Any code that reads URL fragments (third-party analytics scripts, etc.)

Additionally, the Implicit grant provides no refresh tokens, meaning users must re-authenticate frequently.

PKCE solves all the problems that motivated Implicit without its vulnerabilities: the code in the URL is short-lived (30-60 seconds), single-use, and useless without the `code_verifier` that's never in the URL. PKCE is now the recommended approach for SPAs and mobile apps.

---

**Q4. When would you choose API keys over OAuth2?**

**Answer:** API keys are appropriate when:
1. **No user delegation needed:** The caller is a server acting on its own behalf, not on behalf of a user. OAuth2 Client Credentials would also work, but API keys are simpler.
2. **Simple integration:** Third-party developers querying a public API (weather, mapping, payment processing). The barrier to getting started should be minimal — generate a key, put it in the header, done.
3. **No scope differentiation needed:** If all callers get the same access level, the scope machinery of OAuth2 adds complexity without benefit.
4. **Internal tooling:** Scripts, cron jobs, monitoring agents where the overhead of OAuth2 isn't justified.

OAuth2 is better when: you need fine-grained scopes, third-party delegation (user authorizes another service), standardized token rotation, or integration with identity providers. The key question: "Is a user delegating access to their resources?" If yes, OAuth2. If it's purely machine-to-machine with the same permissions for all callers, API keys are reasonable.

---

**Q5. How do you securely store API keys in a database?**

**Answer:** Hash the key with SHA256 before storing; never store plaintext. The security reasoning differs from password hashing (bcrypt): API keys are generated with 192+ bits of cryptographic randomness, making brute-force computationally infeasible regardless of hash speed. SHA256's speed (~microseconds) matters here because it runs on every authenticated API request, where bcrypt's intentional 100-300ms delay would be unacceptable.

Implementation:
```
1. Generate key: sk_live_{32 random bytes as base64url}
2. Show to user ONCE — this is the last time anyone sees it
3. Store: { key_hash: SHA256(key), prefix_hint: first 12 chars, user_id, ... }
4. On each request: lookup by SHA256(presented_key)
```

Store the first 12 characters as a `prefix_hint` (e.g., `sk_live_a1b2`) to help users identify which key is which in the management UI, since you can't show the full key again.

---

**Q6. What is the state parameter in OAuth2 for?**

**Answer:** The `state` parameter is an opaque CSRF token used to bind the authorization request to the callback. Without it, an attacker can perform an OAuth CSRF attack:
- Attacker initiates an OAuth flow but doesn't complete it
- Captures the resulting callback URL (which would link attacker's identity to a victim's session)
- Tricks the victim into visiting the callback URL (via CSRF, phishing, or embedding)
- Victim's browser completes the exchange — their account gets linked to the attacker's OAuth identity

The `state` parameter prevents this because it's stored in the user's session before the redirect and must match when the callback is received. The attacker can't forge or predict the value from the victim's session.

Implementation: generate `state = crypto.randomBytes(32).hex()`, store in session, include in auth URL. In callback: compare received state to session state using constant-time comparison. Delete from session after use (single-use).

---

## Resources

- [OAuth 2.0 Authorization Framework (RFC 6749)](https://datatracker.ietf.org/doc/html/rfc6749)
- [PKCE (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
- [OAuth 2.0 Security Best Current Practice (RFC 9700)](https://datatracker.ietf.org/doc/html/rfc9700)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [OIDC Discovery (RFC 8414)](https://datatracker.ietf.org/doc/html/rfc8414)
- [OAuth 2.0 Device Authorization Grant (RFC 8628)](https://datatracker.ietf.org/doc/html/rfc8628)
- [OAuth 2.0 Threat Model (RFC 6819)](https://datatracker.ietf.org/doc/html/rfc6819)
- [Go oauth2 package](https://pkg.go.dev/golang.org/x/oauth2)
- [FastAPI OAuth2 with Password](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Auth0 — Which OAuth2 flow to use?](https://auth0.com/docs/get-started/authentication-and-authorization-flow)

---

**Next:** [Part 5.1: Authorization](../part-05/05-authorization-rbac-abac.md)
