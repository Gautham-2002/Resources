# Part 4.1: Authentication — JWT & Sessions

## What You'll Learn
- The precise difference between authentication and authorization, and why conflating them causes bugs
- Session-based auth: the full lifecycle, storage backends, horizontal scaling problems, and security attacks
- JWT internals: the three-part structure, signing algorithms (HS256 vs RS256), and all standard claims
- The access token + refresh token pattern, rotation, and why it exists
- Token revocation — the hardest problem with JWTs, and pragmatic solutions
- JWT storage in the browser: the security trade-offs of localStorage vs httpOnly cookies vs memory
- Security vulnerabilities: the `alg:none` attack, weak secrets, JWT confusion attacks
- Full production-quality implementations in Go+Chi, Node.js+Express, Python+FastAPI

---

## Table of Contents

1. [Authentication vs Authorization](#1-authentication-vs-authorization)
2. [Session-Based Authentication](#2-session-based-authentication)
3. [Session Security](#3-session-security)
4. [Horizontal Scaling with Sessions](#4-horizontal-scaling-with-sessions)
5. [Token-Based Authentication (JWT)](#5-token-based-authentication-jwt)
6. [JWT Structure Internals](#6-jwt-structure-internals)
7. [Signing Algorithms: HS256 vs RS256](#7-signing-algorithms-hs256-vs-rs256)
8. [JWT Standard Claims](#8-jwt-standard-claims)
9. [Access Token + Refresh Token Pattern](#9-access-token--refresh-token-pattern)
10. [Refresh Token Rotation](#10-refresh-token-rotation)
11. [Token Revocation](#11-token-revocation)
12. [JWT Storage in the Browser](#12-jwt-storage-in-the-browser)
13. [JWT Security Vulnerabilities](#13-jwt-security-vulnerabilities)
14. [Implementation Examples](#14-implementation-examples)
15. [Common Patterns & Best Practices](#common-patterns--best-practices)
16. [Common Pitfalls](#common-pitfalls)
17. [Interview Questions](#interview-questions)
18. [Resources](#resources)

---

## 1. Authentication vs Authorization

These two terms are often used interchangeably in casual conversation, but they are fundamentally different security concerns.

```
Authentication: WHO are you?
Authorization:  WHAT are you allowed to do?

Examples:
  "I am Alice" → Authentication (verify identity)
  "Alice can read posts but not delete them" → Authorization (check permissions)

In code:
  AuthN middleware: validate JWT, set req.user = { id: "alice", role: "user" }
  AuthZ middleware: check req.user.role === "admin" before proceeding

The distinction matters because:
  - They fail with different HTTP status codes (401 vs 403)
  - They belong in different layers (often different middleware)
  - You can be authenticated but not authorized
  - You can't be authorized without being authenticated first
```

| | Authentication | Authorization |
|---|---|---|
| **Question** | Who are you? | What can you do? |
| **Failure code** | `401 Unauthorized` | `403 Forbidden` |
| **Data needed** | Credential (password, token) | Identity + permission rules |
| **Examples** | JWT validation, session lookup | RBAC role check, ABAC policy |
| **When fails** | Token missing or invalid | Token valid but insufficient permissions |

**Common interview trap:** `401 Unauthorized` is poorly named. It actually means "unauthenticated" (you haven't proven who you are). `403 Forbidden` means "authenticated but not authorized" (I know who you are, but you can't do this). Many developers get this backwards.

---

## 2. Session-Based Authentication

Session-based auth predates JWTs and is still widely used, especially in traditional web applications. Understanding it is essential for interviews at companies with legacy systems.

### How It Works

```
┌─────────────┐                              ┌─────────────┐        ┌─────────────┐
│   Browser   │                              │   Server    │        │    Redis    │
└─────────────┘                              └─────────────┘        └─────────────┘
      │                                             │                      │
      │ POST /login {email, password}               │                      │
      │ ─────────────────────────────────────────► │                      │
      │                                             │                      │
      │                          Verify credentials │                      │
      │                          Create session ID  │                      │
      │                          (cryptographic random, 32+ bytes)         │
      │                                             │ SET session:{id} ──► │
      │                                             │   {userId, createdAt}│
      │                                             │   EX 86400            │
      │ Set-Cookie: session_id=abc123; HttpOnly     │                      │
      │ ◄─────────────────────────────────────────  │                      │
      │                                             │                      │
      │ GET /api/profile (Cookie: session_id=abc123)│                      │
      │ ─────────────────────────────────────────► │                      │
      │                                             │ GET session:abc123 ─►│
      │                                             │ ◄─ {userId: 42} ─────│
      │                                             │                      │
      │                          Load user from DB  │                      │
      │          200 {name: "Alice", ...}           │                      │
      │ ◄─────────────────────────────────────────  │                      │
```

### Session Lifecycle

**Create (Login):**
1. Verify credentials (email + password)
2. Generate a cryptographically random session ID (at least 128 bits of entropy)
3. Store session data in Redis/DB: `session:{id} → {userId, createdAt, ip, userAgent}`
4. Set `Set-Cookie: session_id={id}; HttpOnly; Secure; SameSite=Strict`

**Read (Each Request):**
1. Extract session ID from cookie
2. Look up in Redis: O(1), extremely fast
3. If found and not expired, extract user ID
4. Load user from DB (or cache)
5. Attach to request context

**Update (Refresh / Activity Tracking):**
1. Update `lastActivity` in session store
2. Optionally extend the TTL (sliding expiration)

**Destroy (Logout):**
1. Delete the session from Redis: `DEL session:{id}`
2. Set `Set-Cookie: session_id=; HttpOnly; Expires=Thu, 01 Jan 1970 00:00:00 GMT` (invalidate cookie)

### Sessions vs Cookies: They're Different Things

A **cookie** is a browser mechanism to store a small key-value pair and send it back with every request to the same origin. A **session** is a server-side data structure stored in a backend (Redis, DB, memory).

The session ID stored in the cookie is just a pointer — a random lookup key. The actual session data lives on the server. This is fundamentally different from a JWT, which contains data in the token itself.

---

## 3. Session Security

### Session Fixation Attack

An attacker tricks a user into using a known session ID, then hijacks the session after the user authenticates.

```
Attack flow:
  1. Attacker visits /login and gets session ID: ABC
  2. Attacker crafts a link: https://victim.com/login?session_id=ABC
     (or injects via subdomain cookie, XSS, etc.)
  3. Victim clicks link, authenticates, session ABC now has victim's identity
  4. Attacker uses session ID ABC to impersonate victim

Defense: Regenerate session ID upon successful authentication
  Before login:  session_id = ABC (unauthenticated)
  After login:   session_id = XYZ (new, contains user data)
                 OLD session ABC is deleted
```

```go
// Go: session regeneration after login
func loginHandler(w http.ResponseWriter, r *http.Request) {
    // Verify credentials...
    user, err := authService.VerifyCredentials(email, password)
    
    // Destroy old session (if any) before creating new one
    if oldSessionID := getSessionCookie(r); oldSessionID != "" {
        sessionStore.Delete(r.Context(), oldSessionID)
    }
    
    // Create NEW session with new ID
    newSessionID := generateSecureSessionID()
    sessionStore.Set(r.Context(), newSessionID, SessionData{UserID: user.ID})
    
    http.SetCookie(w, &http.Cookie{
        Name:     "session_id",
        Value:    newSessionID,
        HttpOnly: true,
        Secure:   true,
        SameSite: http.SameSiteStrictMode,
        MaxAge:   86400,
    })
}
```

### Session Hijacking and CSRF

- **Session Hijacking:** Attacker steals the session cookie (XSS, network sniffing) and sends requests with it. Defense: `HttpOnly` (prevents JS access), `Secure` (HTTPS only), short TTLs.
- **CSRF (Cross-Site Request Forgery):** Attacker tricks authenticated user's browser into making requests to your site. The browser sends the cookie automatically. Defense: `SameSite=Strict` or `SameSite=Lax`, CSRF tokens for state-changing requests.

---

## 4. Horizontal Scaling with Sessions

Sessions stored in server memory (default in many frameworks) don't scale horizontally.

```
Server A memory: { "ABC" → user:42 }     Server B memory: { }
Server C memory: { }                      Load Balancer (round-robin)
                                                 ↑
User's request with session ABC → Load Balancer → Routes to Server B
Server B: "I don't know session ABC" → 401!
```

### Solutions

**Sticky Sessions (Session Affinity):**
- Load balancer routes all requests from the same client to the same server
- Problem: server failure loses all its sessions; uneven load if users have varying activity

**Centralized Session Store (Correct Solution):**
- All servers share a Redis cluster
- Any server can look up any session
- Redis TTL handles expiration automatically
- Redis replication handles high availability

```
Server A ─┐                      ┌── Session stored in Redis
Server B ─┼── Redis Cluster ─────┤   Key: session:{id}
Server C ─┘                      └── Value: {userId, createdAt, ...}

Any server can handle any request.
```

**Database-backed Sessions:**
- Works but slower than Redis for session lookups
- Consider a DB read cache in front of it

---

## 5. Token-Based Authentication (JWT)

JWT (JSON Web Token) is a standard (RFC 7519) for encoding claims as a signed JSON object. Unlike sessions, the token contains data — the server doesn't need to look anything up.

```
Session-based:
  Request → Server → Redis lookup → User data → Handler
  
JWT-based:
  Request → Server → Cryptographic verification → Decode claims → Handler
  (No network I/O for auth!)
```

### The Trade-off: Stateless vs Revocable

| | Session | JWT |
|---|---|---|
| **State** | Server-side | Client-side |
| **Revocation** | Delete from store | Difficult (see Section 11) |
| **Scaling** | Needs shared store | Works with any server |
| **Payload** | Unlimited | Sent in every request (keep small) |
| **Expiry** | Server controls TTL | Client holds until `exp` |

---

## 6. JWT Structure Internals

A JWT is three Base64URL-encoded JSON objects separated by dots:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
.eyJzdWIiOiJ1c2VyXzQyIiwiZW1haWwiOiJhbGljZUBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNzE5NjUwMDAwLCJleHAiOjE3MTk2NTM2MDAsImlzcyI6ImFwaS5leGFtcGxlLmNvbSIsImp0aSI6IjAxSFhZWjEyMzQ1NiJ9
.HMAC_SHA256(secret, header + "." + payload)

Part 1: Header (algorithm + type)
Part 2: Payload (claims)
Part 3: Signature (cryptographic proof)
```

### Header

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

`alg` declares the signing algorithm. This is where the `alg:none` vulnerability lives (see Section 13).

### Payload (Claims)

```json
{
  "sub":   "user_42",
  "email": "alice@example.com",
  "role":  "user",
  "iat":   1719650000,
  "exp":   1719653600,
  "iss":   "api.example.com",
  "aud":   "api.example.com",
  "jti":   "01HXYZ123456"
}
```

### Signature

For HS256:
```
signature = HMAC-SHA256(
  base64url(header) + "." + base64url(payload),
  secret_key
)
```

For RS256:
```
signature = RSA-PKCS1v15-SHA256(
  base64url(header) + "." + base64url(payload),
  private_key
)
```

### Base64URL vs Base64

JWT uses Base64URL encoding, which uses `-` instead of `+` and `_` instead of `/`, and omits `=` padding. This makes JWTs safe to include in URLs without percent-encoding.

```
Base64:    "abc+/def=="
Base64URL: "abc-_def"
```

---

## 7. Signing Algorithms: HS256 vs RS256

This is a very common interview question at FAANG.

### HS256 (HMAC-SHA256) — Symmetric

Uses a **single shared secret key** for both signing and verification.

```
Signing:    token = sign(payload, secret)
Verifying:  valid = verify(token, secret)

Both operations require the SAME secret.
```

**When to use HS256:**
- Single service (no need to share verification with other services)
- Microservices in the same trust boundary where all services have the secret
- Simpler key management

**Risks:**
- Every service that verifies tokens needs the secret — if any service is compromised, the secret is exposed and attackers can forge tokens
- No way to distinguish signing capability from verification capability

### RS256 (RSA-SHA256) — Asymmetric

Uses a **private key** to sign and a **public key** to verify.

```
Signing:    token = sign(payload, private_key)   ← only auth service has this
Verifying:  valid = verify(token, public_key)    ← any service can have this

Private key stays in the auth service.
Public key can be freely distributed.
```

**When to use RS256:**
- Multiple services need to verify tokens (microservices, third-party integrations)
- You want to give services verification capability without signing capability
- Zero-trust architecture — services shouldn't trust each other's tokens without cryptographic proof
- Public key published via JWKS endpoint (`.well-known/jwks.json`)

```
Auth Service        API Gateway       User Service      Order Service
  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
  │ private  │      │  public  │      │  public  │      │  public  │
  │  key     │      │   key    │      │   key    │      │   key    │
  │ (secret) │      │ (shared) │      │ (shared) │      │ (shared) │
  └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
       │                 │                 │                  │
       │ Signs tokens     │ Verifies        │ Verifies         │ Verifies
       │                 │ (can't forge)   │ (can't forge)    │ (can't forge)
```

### ES256 (ECDSA) — Also Asymmetric

Similar security model to RS256, but uses Elliptic Curve Cryptography. Produces shorter signatures (64 bytes for ES256 vs 256 bytes for RS256), better performance on modern hardware.

---

## 8. JWT Standard Claims

Knowing these by name and meaning is interview-required knowledge:

| Claim | Full Name | Meaning |
|---|---|---|
| `iss` | Issuer | Who created the token (e.g., `"api.example.com"`) |
| `sub` | Subject | WHO the token is about (user ID) |
| `aud` | Audience | WHO the token is intended for (service name or URL) |
| `exp` | Expiration Time | Unix timestamp when token expires |
| `iat` | Issued At | Unix timestamp when token was issued |
| `nbf` | Not Before | Token is invalid before this timestamp |
| `jti` | JWT ID | Unique token ID — used for revocation blocklists |

### Why `aud` (Audience) Matters

A token issued for `api.example.com` should not be accepted by `admin.example.com`. If a service is compromised and its tokens are stolen, they shouldn't work on other services.

```go
// Verify audience during validation:
token, err := jwt.ParseWithClaims(tokenStr, &claims, keyFunc,
    jwt.WithAudience("api.example.com"),  // Must match the aud claim
    jwt.WithIssuer("auth.example.com"),   // Must match the iss claim
    jwt.WithExpirationRequired(),
)
```

### Recommended Expiry Times

| Token Type | Recommended Expiry |
|---|---|
| Access Token | 15 minutes (production) to 1 hour (lenient) |
| Refresh Token | 7-30 days |
| ID Token (OIDC) | Same as access token |
| One-time tokens | 5-15 minutes |

Short access token expiry limits the window of damage if a token is stolen.

---

## 9. Access Token + Refresh Token Pattern

A short-lived access token alone creates a bad UX — users would need to log in every 15 minutes. The refresh token pattern solves this.

```
┌─────────┐                                        ┌─────────────┐
│ Client  │                                        │ Auth Server │
└─────────┘                                        └─────────────┘
     │                                                     │
     │── POST /auth/login ────────────────────────────────►│
     │   { email, password }                               │
     │                                                     │ Verify credentials
     │◄── 200 ────────────────────────────────────────────│
     │   {                                                 │
     │     access_token:  "eyJ..." (15 min),               │
     │     refresh_token: "rt_..." (30 days),              │
     │     expires_in: 900                                 │
     │   }                                                 │
     │                                                     │
     │── GET /api/data (Bearer: access_token) ────────────►│
     │◄── 200 data ───────────────────────────────────────│
     │                                                     │
     │   ... 15 minutes later, access token expired ...   │
     │                                                     │
     │── GET /api/data (Bearer: expired_access_token) ────►│
     │◄── 401 Token Expired ──────────────────────────────│
     │                                                     │
     │── POST /auth/refresh ──────────────────────────────►│
     │   { refresh_token: "rt_..." }                       │
     │                                                     │ Verify refresh token
     │◄── 200 ────────────────────────────────────────────│
     │   {                                                 │
     │     access_token: "eyJ..." (NEW, 15 min),           │
     │     refresh_token: "rt_..." (NEW, 30 days),         │ ← rotation!
     │   }                                                 │
     │                                                     │
     │── GET /api/data (Bearer: new_access_token) ────────►│
     │◄── 200 data ───────────────────────────────────────│
```

### Refresh Token Storage

Refresh tokens must be stored server-side (unlike JWTs). Typical storage:
- **Redis:** `refresh_token:{token_hash}` → `{userId, createdAt, deviceId}`
- **Database:** `refresh_tokens` table with indexed token hash

You store a **hash** of the refresh token, never the plaintext. This way, even if your DB is compromised, tokens can't be used.

---

## 10. Refresh Token Rotation

Rotation is the practice of issuing a new refresh token every time the old one is used, and invalidating the old one.

### Why rotation matters

Without rotation:
```
Attacker steals refresh token → uses it indefinitely → full account access for 30 days
```

With rotation:
```
Attacker steals refresh token → uses it once → gets new access + new refresh token
Legitimate user tries to refresh → FAIL (old refresh token was rotated away)
System detects token reuse → revoke ALL tokens for this user/session
```

This is called **refresh token reuse detection**. If an old (already-rotated) refresh token is used, it's evidence that the token was stolen. The server should:
1. Invalidate ALL refresh tokens for that session/user
2. Force re-authentication
3. Alert the user

### Rotation Implementation Requirements

1. Each refresh token has a unique ID (`jti` or a DB column)
2. After use, mark the old token as "used" (never deleted — needed for reuse detection)
3. Issue a new refresh token with a new ID
4. Link the new token to the old one (parent-child chain) to enable "revoke tree" operations

```sql
-- refresh_tokens table
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash  BYTEA NOT NULL UNIQUE,  -- bcrypt or SHA256 hash
    user_id     UUID NOT NULL REFERENCES users(id),
    session_id  UUID NOT NULL,           -- groups a chain of rotated tokens
    parent_id   UUID REFERENCES refresh_tokens(id),  -- NULL for first token
    used_at     TIMESTAMP,               -- set when rotated
    expires_at  TIMESTAMP NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    revoked_at  TIMESTAMP               -- set when explicitly revoked (logout)
);
```

---

## 11. Token Revocation

This is the most difficult problem with JWTs. Because JWTs are stateless (the server stores nothing), you can't "delete" a token — it's valid until it expires.

### The Revocation Problem

```
Scenario: User changes password (or is compromised)
          We need to invalidate all their existing tokens immediately.

Session-based:  DEL session:{id}  ← instant, O(1)
JWT-based:      ??? token is valid until exp, server-side state is per-design absent
```

### Solution 1: Short Expiry (Accept the Window)

Set access token expiry to 1-15 minutes. A stolen token is only valid for at most that duration. For most use cases, this is acceptable.

**When it's NOT acceptable:** Logout, password change, account compromise, employee termination.

### Solution 2: Blocklist (Denylist)

Store revoked JWT IDs (`jti`) in Redis. On every request, check if the token's `jti` is in the blocklist.

```go
func isTokenRevoked(ctx context.Context, jti string) bool {
    result, err := redisClient.Exists(ctx, "revoked:"+jti).Result()
    return err == nil && result > 0
}

func revokeToken(ctx context.Context, jti string, exp time.Time) error {
    // Store until expiry — after that, the token is invalid anyway
    ttl := time.Until(exp)
    return redisClient.SetEx(ctx, "revoked:"+jti, "1", ttl).Err()
}
```

**Cost:** One Redis lookup per request (very fast, ~1ms, but not zero).

**Problem:** The blocklist grows over time. Need to clean up expired entries (set TTL = token TTL).

### Solution 3: Short-lived Access + Refresh Token Revocation

Keep access tokens short (15 min) and only worry about revoking refresh tokens. The compromise window is bounded by the access token lifetime. This is the most pragmatic approach for most applications.

### Solution 4: Opaque Tokens

Use an opaque (random) access token stored in Redis, similar to sessions but without the full session model. Each validation requires a Redis lookup. This is essentially session-based auth with different naming.

---

## 12. JWT Storage in the Browser

This is one of the most hotly debated topics in web security. The answer is "it depends," but you need to know why.

### Option 1: localStorage

```javascript
localStorage.setItem('access_token', token);
// Retrieved with: localStorage.getItem('access_token')
```

**Security:** VULNERABLE to XSS (Cross-Site Scripting). Any JavaScript on your page can read `localStorage`, including injected scripts from XSS attacks.

**Convenience:** Easy to implement, persists across tabs and browser restarts.

**Verdict:** Never store sensitive tokens in `localStorage` unless you are certain about your XSS posture (and you can never be 100% certain with third-party scripts, npm packages, CDN resources).

### Option 2: Memory (JavaScript Variable)

```javascript
let accessToken = null; // module-level variable

function setToken(token) { accessToken = token; }
function getToken() { return accessToken; }
```

**Security:** NOT accessible via XSS (JavaScript in other scripts can't access your module's variables if you're careful). But: the token is lost on page refresh/navigation.

**Verdict:** Best security for access tokens. Use with a long-lived `HttpOnly` cookie storing the refresh token. On page load, use the refresh token to silently obtain a new access token.

### Option 3: HttpOnly Cookie

```
Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict; Path=/auth/refresh
```

**Security:** JavaScript cannot read `HttpOnly` cookies (`document.cookie` doesn't include them). Not vulnerable to XSS for token theft.

**CSRF:** Cookies are automatically sent by the browser, making them vulnerable to CSRF. Defense: `SameSite=Strict` or `SameSite=Lax`, or CSRF tokens for state-changing operations.

**Verdict:** The recommended storage for refresh tokens. Scope the path to just the refresh endpoint (`Path=/auth/refresh`) to minimize exposure.

### The Recommended Pattern

```
Access token:  memory (JavaScript variable) — lost on refresh, very short-lived anyway
Refresh token: HttpOnly cookie, Path=/auth/refresh, Secure, SameSite=Strict

On page load:
  1. POST /auth/refresh (cookie is sent automatically)
  2. Receive new access token → store in memory
  3. Repeat every 14 minutes (before 15-min access token expiry)

On logout:
  1. Call POST /auth/logout → server deletes refresh token from DB
  2. Clear access token from memory
  3. Server sets expired cookie to clear it from browser
```

```
Token Storage Comparison:
┌──────────────────┬─────────────────┬─────────────────┬─────────────────┐
│                  │   localStorage  │     Memory      │  HttpOnly Cookie│
├──────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ XSS theft        │    VULNERABLE   │   Protected     │   Protected     │
│ CSRF             │    Protected    │   Protected     │   VULNERABLE    │
│ Persists refresh │    Yes          │   No            │   Yes           │
│ Sub-domain access│    No           │   No            │   Configurable  │
│ Server control   │    No           │   No            │   Yes (HttpOnly)│
└──────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

---

## 13. JWT Security Vulnerabilities

### 1. The `alg:none` Vulnerability (Critical)

Early JWT libraries allowed the algorithm to be set to `"none"`, meaning "no signature required." An attacker could:

1. Take any valid JWT
2. Decode it (it's just Base64)
3. Modify the payload (e.g., change `role: "user"` to `role: "admin"`)
4. Re-encode with `alg: "none"` and no signature
5. Send it — some libraries would accept it!

```json
// Attacker's forged header:
{ "alg": "none", "typ": "JWT" }

// Attacker's modified payload:
{ "sub": "user_42", "role": "admin", "exp": 9999999999 }

// Attacker's token: header.payload.   (empty signature)
```

**Defense: Always explicitly specify allowed algorithms:**
```go
jwt.ParseWithClaims(tokenStr, &claims, keyFunc,
    jwt.WithValidMethods([]string{"HS256"}), // ONLY allow HS256
)
```
Never accept a token without verifying the algorithm matches what you expect.

### 2. Algorithm Confusion Attack (RS256 → HS256)

If a server signs with RS256 and publishes its public key, an attacker can:
1. Get the server's public key (often publicly available at JWKS endpoint)
2. Use the public key as an HMAC secret to sign a forged token with `alg: "HS256"`
3. If the server accepts HS256 tokens and uses the public key as the HMAC secret for verification, it accepts the forged token

**Defense:** Bind each key to exactly one algorithm. A RS256 key should only verify RS256 tokens.

### 3. Weak Secrets (HS256)

HS256 is only as secure as the secret. Using a predictable or short secret (< 256 bits) allows brute-force attacks.

```
Weak:   jwt_secret_123  ← easily brute-forced
Weak:   myapp_secret    ← dictionary attack
Strong: 32+ random bytes from a CSPRNG (os.urandom(32))
```

Generate a strong secret:
```bash
openssl rand -hex 32
# or
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Long Expiry Times

A token valid for 1 year is nearly as dangerous as a permanent password. If leaked, it's usable for 365 days.

### 5. Sensitive Data in Payload

JWT payloads are Base64-encoded, NOT encrypted. Anyone with the token can decode the payload.

```
base64url_decode("eyJzdWIiOiJ1c2VyXzQyIiwiZW1haWwiOiJhbGljZUBleGFtcGxlLmNvbSJ9")
→ {"sub":"user_42","email":"alice@example.com"}
```

Never put sensitive data (passwords, PII, financial data, security answers) in JWT payloads.

---

## 14. Implementation Examples

### Go + Chi: Complete Auth System

```go
package main

import (
    "context"
    "crypto/rand"
    "encoding/hex"
    "encoding/json"
    "errors"
    "fmt"
    "net/http"
    "os"
    "strings"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"
    "github.com/golang-jwt/jwt/v5"
    "github.com/redis/go-redis/v9"
    "golang.org/x/crypto/bcrypt"
)

// --------------------------------------------------------------------------
// Configuration
// --------------------------------------------------------------------------

var (
    jwtSecret        = []byte(os.Getenv("JWT_SECRET")) // min 32 bytes
    accessTokenTTL   = 15 * time.Minute
    refreshTokenTTL  = 30 * 24 * time.Hour
)

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

type contextKey string
const contextKeyUser contextKey = "user"

type AuthUser struct {
    ID    string
    Email string
    Role  string
}

type Claims struct {
    Email string `json:"email"`
    Role  string `json:"role"`
    jwt.RegisteredClaims
}

type LoginRequest struct {
    Email    string `json:"email"`
    Password string `json:"password"`
}

type TokenPair struct {
    AccessToken  string `json:"access_token"`
    RefreshToken string `json:"refresh_token"`
    ExpiresIn    int    `json:"expires_in"` // seconds
}

// --------------------------------------------------------------------------
// Token generation
// --------------------------------------------------------------------------

func generateAccessToken(userID, email, role string) (string, error) {
    now := time.Now()
    jtiBytes := make([]byte, 16)
    rand.Read(jtiBytes)
    
    claims := Claims{
        Email: email,
        Role:  role,
        RegisteredClaims: jwt.RegisteredClaims{
            Subject:   userID,
            IssuedAt:  jwt.NewNumericDate(now),
            ExpiresAt: jwt.NewNumericDate(now.Add(accessTokenTTL)),
            Issuer:    "api.example.com",
            Audience:  jwt.ClaimStrings{"api.example.com"},
            ID:        hex.EncodeToString(jtiBytes), // jti for revocation
        },
    }

    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString(jwtSecret)
}

func generateRefreshToken() (string, error) {
    bytes := make([]byte, 32)
    if _, err := rand.Read(bytes); err != nil {
        return "", err
    }
    return hex.EncodeToString(bytes), nil
}

// --------------------------------------------------------------------------
// Token validation
// --------------------------------------------------------------------------

func validateAccessToken(tokenStr string) (*Claims, error) {
    claims := &Claims{}
    token, err := jwt.ParseWithClaims(tokenStr, claims, func(t *jwt.Token) (interface{}, error) {
        // CRITICAL: verify signing method to prevent alg:none and confusion attacks
        if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
            return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
        }
        return jwtSecret, nil
    },
        jwt.WithAudience("api.example.com"),
        jwt.WithIssuer("api.example.com"),
        jwt.WithExpirationRequired(),
    )

    if err != nil {
        return nil, err
    }
    if !token.Valid {
        return nil, errors.New("invalid token")
    }
    return claims, nil
}

// --------------------------------------------------------------------------
// Auth middleware
// --------------------------------------------------------------------------

func AuthMiddleware(rdb *redis.Client) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            authHeader := r.Header.Get("Authorization")
            if authHeader == "" {
                writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "missing authorization header"})
                return
            }

            parts := strings.SplitN(authHeader, " ", 2)
            if len(parts) != 2 || !strings.EqualFold(parts[0], "bearer") {
                writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "invalid authorization header"})
                return
            }

            claims, err := validateAccessToken(parts[1])
            if err != nil {
                if errors.Is(err, jwt.ErrTokenExpired) {
                    writeJSON(w, http.StatusUnauthorized, map[string]string{
                        "error": "token_expired",
                        "code":  "TOKEN_EXPIRED",
                    })
                    return
                }
                writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "invalid token"})
                return
            }

            // Optional: check revocation blocklist
            jti := claims.ID
            if jti != "" {
                revoked, err := rdb.Exists(r.Context(), "revoked:"+jti).Result()
                if err == nil && revoked > 0 {
                    writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "token has been revoked"})
                    return
                }
            }

            // Inject user into context
            user := &AuthUser{
                ID:    claims.Subject,
                Email: claims.Email,
                Role:  claims.Role,
            }
            ctx := context.WithValue(r.Context(), contextKeyUser, user)
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}

// --------------------------------------------------------------------------
// Handlers
// --------------------------------------------------------------------------

// loginHandler: verify credentials, issue token pair
func loginHandler(userStore UserStore, tokenStore TokenStore) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        var req LoginRequest
        if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
            writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request body"})
            return
        }

        // Verify credentials
        user, err := userStore.GetByEmail(r.Context(), req.Email)
        if err != nil || bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(req.Password)) != nil {
            // Same error for wrong email OR wrong password — prevents email enumeration
            writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "invalid credentials"})
            return
        }

        // Generate tokens
        accessToken, err := generateAccessToken(user.ID, user.Email, user.Role)
        if err != nil {
            writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "failed to generate token"})
            return
        }

        refreshToken, err := generateRefreshToken()
        if err != nil {
            writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "failed to generate token"})
            return
        }

        // Store refresh token (hashed)
        if err := tokenStore.StoreRefreshToken(r.Context(), user.ID, refreshToken, refreshTokenTTL); err != nil {
            writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
            return
        }

        // Set refresh token as HttpOnly cookie
        http.SetCookie(w, &http.Cookie{
            Name:     "refresh_token",
            Value:    refreshToken,
            Path:     "/auth/refresh",
            HttpOnly: true,
            Secure:   true,
            SameSite: http.SameSiteStrictMode,
            MaxAge:   int(refreshTokenTTL.Seconds()),
        })

        writeJSON(w, http.StatusOK, TokenPair{
            AccessToken:  accessToken,
            ExpiresIn:    int(accessTokenTTL.Seconds()),
            // Don't include refresh token in body — it's in the cookie
        })
    }
}

// refreshHandler: validate refresh token, issue new token pair (rotation)
func refreshHandler(tokenStore TokenStore) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        cookie, err := r.Cookie("refresh_token")
        if err != nil {
            writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "missing refresh token"})
            return
        }

        refreshToken := cookie.Value

        // Look up and validate refresh token
        session, err := tokenStore.ValidateRefreshToken(r.Context(), refreshToken)
        if err != nil {
            if errors.Is(err, ErrTokenReused) {
                // Reuse detected — revoke ALL tokens for this user
                tokenStore.RevokeAllUserTokens(r.Context(), session.UserID)
                writeJSON(w, http.StatusUnauthorized, map[string]string{
                    "error": "refresh token reuse detected — all sessions terminated",
                })
                return
            }
            writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "invalid refresh token"})
            return
        }

        // Rotate: mark old token as used, generate new pair
        user, err := tokenStore.RotateRefreshToken(r.Context(), session, refreshToken)
        if err != nil {
            writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
            return
        }

        newAccessToken, err := generateAccessToken(user.ID, user.Email, user.Role)
        if err != nil {
            writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
            return
        }
        
        newRefreshToken, err := generateRefreshToken()
        if err != nil {
            writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
            return
        }

        if err := tokenStore.StoreRefreshToken(r.Context(), user.ID, newRefreshToken, refreshTokenTTL); err != nil {
            writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
            return
        }

        // Update cookie with new refresh token
        http.SetCookie(w, &http.Cookie{
            Name:     "refresh_token",
            Value:    newRefreshToken,
            Path:     "/auth/refresh",
            HttpOnly: true,
            Secure:   true,
            SameSite: http.SameSiteStrictMode,
            MaxAge:   int(refreshTokenTTL.Seconds()),
        })

        writeJSON(w, http.StatusOK, TokenPair{
            AccessToken: newAccessToken,
            ExpiresIn:   int(accessTokenTTL.Seconds()),
        })
    }
}

// logoutHandler: revoke current refresh token
func logoutHandler(tokenStore TokenStore) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        cookie, err := r.Cookie("refresh_token")
        if err == nil {
            tokenStore.RevokeRefreshToken(r.Context(), cookie.Value)
        }

        // Clear the cookie
        http.SetCookie(w, &http.Cookie{
            Name:     "refresh_token",
            Path:     "/auth/refresh",
            HttpOnly: true,
            Secure:   true,
            SameSite: http.SameSiteStrictMode,
            MaxAge:   -1, // delete immediately
        })

        writeJSON(w, http.StatusOK, map[string]string{"message": "logged out"})
    }
}

// meHandler: return current user — demonstrates context extraction
func meHandler(w http.ResponseWriter, r *http.Request) {
    user, ok := r.Context().Value(contextKeyUser).(*AuthUser)
    if !ok {
        writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthenticated"})
        return
    }
    writeJSON(w, http.StatusOK, user)
}

// --------------------------------------------------------------------------
// Router
// --------------------------------------------------------------------------

func NewRouter(userStore UserStore, tokenStore TokenStore, rdb *redis.Client) http.Handler {
    r := chi.NewRouter()
    r.Use(middleware.RequestID)
    r.Use(middleware.Logger)
    r.Use(middleware.Recoverer)

    // Auth endpoints — no JWT required
    r.Route("/auth", func(r chi.Router) {
        r.Post("/login", loginHandler(userStore, tokenStore))
        r.Post("/refresh", refreshHandler(tokenStore))
        r.Post("/logout", logoutHandler(tokenStore))
    })

    // Protected endpoints
    r.Route("/api/v1", func(r chi.Router) {
        r.Use(AuthMiddleware(rdb))
        r.Get("/me", meHandler)
    })

    return r
}

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

func writeJSON(w http.ResponseWriter, status int, v any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(v)
}

// Stub interfaces (implement with your DB/Redis)
type UserStore interface {
    GetByEmail(ctx context.Context, email string) (*DBUser, error)
}
type TokenStore interface {
    StoreRefreshToken(ctx context.Context, userID, token string, ttl time.Duration) error
    ValidateRefreshToken(ctx context.Context, token string) (*TokenSession, error)
    RotateRefreshToken(ctx context.Context, session *TokenSession, oldToken string) (*DBUser, error)
    RevokeRefreshToken(ctx context.Context, token string) error
    RevokeAllUserTokens(ctx context.Context, userID string) error
}
type DBUser struct {
    ID           string
    Email        string
    Role         string
    PasswordHash string
}
type TokenSession struct {
    UserID string
}
var ErrTokenReused = errors.New("token reuse detected")
```

---

### Node.js + Express

```javascript
// auth.js
import express from 'express';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcrypt';
import crypto from 'crypto';
import { createClient } from 'redis';

const router = express.Router();

const JWT_SECRET = process.env.JWT_SECRET;
const ACCESS_TOKEN_TTL = 15 * 60;        // 15 minutes in seconds
const REFRESH_TOKEN_TTL = 30 * 24 * 3600; // 30 days in seconds

// ── Token generation ────────────────────────────────────────────────────────

function generateAccessToken(userId, email, role) {
  return jwt.sign(
    {
      sub: userId,
      email,
      role,
      jti: crypto.randomUUID(), // unique ID for revocation
    },
    JWT_SECRET,
    {
      algorithm: 'HS256',
      expiresIn: ACCESS_TOKEN_TTL,
      issuer: 'api.example.com',
      audience: 'api.example.com',
    }
  );
}

function generateRefreshToken() {
  return crypto.randomBytes(32).toString('hex');
}

// ── JWT validation ──────────────────────────────────────────────────────────

function verifyAccessToken(token) {
  return jwt.verify(token, JWT_SECRET, {
    algorithms: ['HS256'],  // ONLY allow HS256 — prevents alg:none
    issuer: 'api.example.com',
    audience: 'api.example.com',
  });
}

// ── Auth middleware ─────────────────────────────────────────────────────────

export function authMiddleware(redisClient) {
  return async (req, res, next) => {
    const authHeader = req.headers['authorization'];
    if (!authHeader) {
      return res.status(401).json({ error: 'missing authorization header' });
    }

    const parts = authHeader.split(' ');
    if (parts.length !== 2 || parts[0].toLowerCase() !== 'bearer') {
      return res.status(401).json({ error: 'invalid authorization header format' });
    }

    try {
      const payload = verifyAccessToken(parts[1]);

      // Check revocation blocklist
      if (payload.jti) {
        const isRevoked = await redisClient.exists(`revoked:${payload.jti}`);
        if (isRevoked) {
          return res.status(401).json({ error: 'token has been revoked' });
        }
      }

      req.user = {
        id: payload.sub,
        email: payload.email,
        role: payload.role,
        jti: payload.jti,
      };
      next();
    } catch (err) {
      if (err.name === 'TokenExpiredError') {
        return res.status(401).json({ error: 'token_expired', code: 'TOKEN_EXPIRED' });
      }
      return res.status(401).json({ error: 'invalid token' });
    }
  };
}

// ── Refresh token store (Redis) ─────────────────────────────────────────────

async function storeRefreshToken(redisClient, userId, token) {
  const hash = crypto.createHash('sha256').update(token).digest('hex');
  await redisClient.setEx(
    `refresh:${hash}`,
    REFRESH_TOKEN_TTL,
    JSON.stringify({ userId, createdAt: Date.now() })
  );
}

async function validateRefreshToken(redisClient, token) {
  const hash = crypto.createHash('sha256').update(token).digest('hex');
  const data = await redisClient.get(`refresh:${hash}`);
  if (!data) return null;
  return JSON.parse(data);
}

async function deleteRefreshToken(redisClient, token) {
  const hash = crypto.createHash('sha256').update(token).digest('hex');
  await redisClient.del(`refresh:${hash}`);
}

// ── Auth routes ─────────────────────────────────────────────────────────────

export function createAuthRouter(userStore, redisClient) {
  const router = express.Router();

  router.post('/login', async (req, res) => {
    const { email, password } = req.body;
    if (!email || !password) {
      return res.status(400).json({ error: 'email and password are required' });
    }

    const user = await userStore.findByEmail(email);
    if (!user || !(await bcrypt.compare(password, user.passwordHash))) {
      // Same message for wrong email AND wrong password — no enumeration
      return res.status(401).json({ error: 'invalid credentials' });
    }

    const accessToken = generateAccessToken(user.id, user.email, user.role);
    const refreshToken = generateRefreshToken();
    await storeRefreshToken(redisClient, user.id, refreshToken);

    // Refresh token in HttpOnly cookie
    res.cookie('refresh_token', refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: REFRESH_TOKEN_TTL * 1000,
      path: '/auth/refresh',
    });

    res.json({
      access_token: accessToken,
      expires_in: ACCESS_TOKEN_TTL,
    });
  });

  router.post('/refresh', async (req, res) => {
    const refreshToken = req.cookies?.refresh_token;
    if (!refreshToken) {
      return res.status(401).json({ error: 'missing refresh token' });
    }

    const session = await validateRefreshToken(redisClient, refreshToken);
    if (!session) {
      return res.status(401).json({ error: 'invalid or expired refresh token' });
    }

    const user = await userStore.findById(session.userId);
    if (!user) {
      return res.status(401).json({ error: 'user not found' });
    }

    // Rotate: delete old, issue new
    await deleteRefreshToken(redisClient, refreshToken);
    const newAccessToken = generateAccessToken(user.id, user.email, user.role);
    const newRefreshToken = generateRefreshToken();
    await storeRefreshToken(redisClient, user.id, newRefreshToken);

    res.cookie('refresh_token', newRefreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: REFRESH_TOKEN_TTL * 1000,
      path: '/auth/refresh',
    });

    res.json({ access_token: newAccessToken, expires_in: ACCESS_TOKEN_TTL });
  });

  router.post('/logout', async (req, res) => {
    const refreshToken = req.cookies?.refresh_token;
    if (refreshToken) {
      await deleteRefreshToken(redisClient, refreshToken);
    }

    res.clearCookie('refresh_token', { path: '/auth/refresh' });
    res.json({ message: 'logged out' });
  });

  return router;
}
```

---

### Python + FastAPI

```python
# auth.py
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import bcrypt
import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from redis.asyncio import Redis

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    expires_in: int

# ── Token generation ──────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
        "iss": "api.example.com",
        "aud": "api.example.com",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token() -> str:
    return secrets.token_hex(32)  # 256-bit random token


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# ── Token validation ──────────────────────────────────────────────────────────

class AuthUser(BaseModel):
    id: str
    email: str
    role: str
    jti: str


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> AuthUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],  # Explicit whitelist — prevents alg:none
            audience="api.example.com",
            issuer="api.example.com",
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "token_expired", "code": "TOKEN_EXPIRED"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    if jti:
        is_revoked = await redis.exists(f"revoked:{jti}")
        if is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token has been revoked",
            )

    return AuthUser(
        id=payload["sub"],
        email=payload["email"],
        role=payload["role"],
        jti=jti or "",
    )

CurrentUser = Annotated[AuthUser, Depends(get_current_user)]

# ── Auth routes ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    user_store: Annotated[UserStore, Depends(get_user_store)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    user = await user_store.find_by_email(body.email)
    
    if user is None or not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        # Constant-time comparison prevents timing attacks
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token()

    # Store refresh token hash in Redis
    token_hash = hash_token(refresh_token)
    await redis.setex(
        f"refresh:{token_hash}",
        int(REFRESH_TOKEN_TTL.total_seconds()),
        user.id,
    )

    # Set refresh token as HttpOnly cookie scoped to /auth/refresh
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
        path="/auth/refresh",
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    redis: Annotated[Redis, Depends(get_redis)],
    user_store: Annotated[UserStore, Depends(get_user_store)],
    refresh_token: Annotated[Optional[str], Cookie()] = None,
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing refresh token")

    token_hash = hash_token(refresh_token)
    user_id = await redis.get(f"refresh:{token_hash}")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired refresh token")

    user = await user_store.find_by_id(user_id.decode())
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")

    # Rotate: delete old token, issue new one
    await redis.delete(f"refresh:{token_hash}")

    new_access_token = create_access_token(user.id, user.email, user.role)
    new_refresh_token = create_refresh_token()
    new_hash = hash_token(new_refresh_token)
    await redis.setex(
        f"refresh:{new_hash}",
        int(REFRESH_TOKEN_TTL.total_seconds()),
        user.id,
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
        path="/auth/refresh",
    )

    return TokenResponse(
        access_token=new_access_token,
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    redis: Annotated[Redis, Depends(get_redis)],
    refresh_token: Annotated[Optional[str], Cookie()] = None,
) -> dict:
    if refresh_token:
        token_hash = hash_token(refresh_token)
        await redis.delete(f"refresh:{token_hash}")

    response.delete_cookie(key="refresh_token", path="/auth/refresh")
    return {"message": "logged out"}


@router.get("/me")
async def me(current_user: CurrentUser) -> AuthUser:
    return current_user


# ── Stub types ──────────────────────────────────────────────────────────────────

from abc import ABC, abstractmethod

class UserStore(ABC):
    @abstractmethod
    async def find_by_email(self, email: str): ...
    @abstractmethod
    async def find_by_id(self, user_id: str): ...

async def get_redis() -> Redis: ...  # implement with actual Redis connection
async def get_user_store() -> UserStore: ...  # implement with actual DB
```

---

## Common Patterns & Best Practices

### 1. Hash Refresh Tokens Before Storage
Store `SHA256(refresh_token)` in your database/Redis, never the plaintext token. If your database is breached, attackers get hashes they can't use without the original tokens.

### 2. Use Constant-Time Comparisons
When comparing password hashes or token values, use constant-time comparison to prevent timing attacks:
```go
// Go: crypto/subtle package
import "crypto/subtle"
if subtle.ConstantTimeCompare(hashA, hashB) != 1 {
    // not equal
}
```

### 3. Include `jti` in Access Tokens for Auditing
Even if you don't maintain a revocation blocklist, including `jti` in access tokens gives you a unique identifier for auditing and future revocation if needed.

### 4. Fail with Same Error for Invalid Credentials
Whether the email doesn't exist or the password is wrong, return the same error message. This prevents email enumeration attacks.

### 5. Rate-Limit Login Endpoints
Login endpoints are targets for brute-force and credential stuffing. Apply aggressive rate limiting (e.g., 5 attempts per IP per minute, with exponential backoff).

### 6. Validate `iss` and `aud` Claims
Always verify the issuer and audience during token validation. This prevents tokens issued for service A from being accepted by service B.

---

## Common Pitfalls

- ❌ **WRONG:** Not specifying `algorithms` parameter — lets attacker choose `alg: none`
  ```go
  jwt.Parse(token, keyFunc)  // missing algorithm whitelist
  ```
  **✅ CORRECT:**
  ```go
  jwt.ParseWithClaims(token, claims, keyFunc, jwt.WithValidMethods([]string{"HS256"}))
  ```

- ❌ **WRONG:** Storing full refresh token plaintext in database
  **✅ CORRECT:** Store `SHA256(token)` as the lookup key. Store only the hash.

- ❌ **WRONG:** Long access token expiry (24h or more)
  **✅ CORRECT:** Access tokens should be 15 minutes. Use refresh tokens for longevity.

- ❌ **WRONG:** Returning different errors for "wrong email" vs "wrong password"
  ```json
  { "error": "no user with that email" }  // email enumeration
  ```
  **✅ CORRECT:** `{ "error": "invalid credentials" }` — identical for both cases.

- ❌ **WRONG:** Storing refresh tokens in localStorage
  **✅ CORRECT:** `HttpOnly` cookie scoped to the refresh endpoint path.

- ❌ **WRONG:** Not regenerating session ID after login (session fixation)
  **✅ CORRECT:** Destroy the pre-login session and create a brand new one after successful authentication.

- ❌ **WRONG:** Returning `401` when the user is authenticated but lacks permission
  **✅ CORRECT:** Authenticated + unauthorized → `403 Forbidden`. Not authenticated → `401`.

- ❌ **WRONG:** Sensitive data in JWT payload (PII, passwords, financial data)
  **✅ CORRECT:** JWT payload is Base64-encoded (not encrypted) — visible to anyone with the token. Keep payloads minimal.

---

## Interview Questions

**Q1. What is the difference between authentication and authorization?**

**Answer:** Authentication answers "Who are you?" — it verifies identity by checking credentials (password, token). Authorization answers "What can you do?" — it checks whether an authenticated identity has permission to perform a specific action. They fail differently: failed authentication returns `401 Unauthorized`, failed authorization returns `403 Forbidden`. In code, authentication middleware runs first and sets `req.user`; authorization middleware runs second and checks `req.user.role` or similar. You cannot have authorization without authentication, but you can have authentication without checking authorization (public endpoints).

---

**Q2. Why are JWTs stateless? What problem does that create?**

**Answer:** A JWT is stateless because the server stores nothing about it. All information (subject, expiry, role) is inside the token, cryptographically signed. Any server can validate it by verifying the signature — no shared database lookup required.

The problem: because the server holds no state, it cannot revoke a token before its expiry. If a user logs out, changes their password, or their account is compromised, their existing access tokens remain valid until `exp`. Solutions include: very short expiry (15 min), a Redis-backed revocation blocklist (checked on every request), or switching to opaque tokens (effectively session-based, losing the statelessness benefit).

---

**Q3. How do you handle JWT revocation?**

**Answer:** Three approaches with different trade-offs:

1. **Accept the window:** Keep access tokens short (15 min). A stolen or invalid token is only dangerous for 15 minutes. Use refresh tokens for longevity but revoke those server-side.

2. **Blocklist:** Maintain a Redis set of revoked `jti` values. On every request, check `EXISTS revoked:{jti}`. Set TTL equal to the token's remaining lifetime — entries expire automatically. Cost: one Redis round-trip per request (~1ms).

3. **Version counter:** Store a `token_version` counter per user. Include the version in the JWT. On logout or password change, increment the counter. Validation rejects tokens where `jwt.version < stored_version`. Cost: one DB read per request (or one cache read if versioned in Redis).

In practice, approach 1 for access tokens (keep them short) + approach 2/3 for security-critical events is the most common production pattern.

---

**Q4. What is refresh token rotation and why is it important?**

**Answer:** Rotation means issuing a new refresh token every time the old one is used, and marking the old one as consumed. If a refresh token is used twice (original user + attacker who stole it), the second use detects the old token as already-rotated and revokes ALL tokens for that session — forcing re-authentication.

Without rotation: attacker steals a 30-day refresh token → has 30-day access.
With rotation + reuse detection: attacker uses stolen token → new tokens issued → legitimate user's token is now the stolen one → legitimate user's next refresh fails → server detects reuse → revokes all tokens → both parties must re-authenticate → alert sent.

---

**Q5. Where should you store JWTs in the browser and why?**

**Answer:**
- **Access token:** In memory (a JavaScript variable), never persisted. Lost on page refresh — that's intentional, since it's short-lived anyway. Can be silently renewed using a refresh token.
- **Refresh token:** In an `HttpOnly` cookie (not readable by JavaScript), scoped to the refresh endpoint path (`Path=/auth/refresh`), with `Secure` and `SameSite=Strict`.

`localStorage` is vulnerable to XSS — any JavaScript on the page can read it, including injected scripts from compromised npm packages or CDN resources. `HttpOnly` cookies prevent JavaScript access entirely. The `SameSite=Strict` flag prevents CSRF (the cookie won't be sent with cross-site requests). This combination provides the best security trade-off.

---

**Q6. What is the `alg:none` JWT vulnerability?**

**Answer:** The JWT specification originally allowed `"alg": "none"` to indicate an unsigned token. Some early JWT libraries, when parsing a token with `alg:none`, would skip signature verification and accept the token as valid.

An attacker exploits this by:
1. Taking any valid JWT and decoding its Base64 payload
2. Modifying the payload (e.g., escalate role to admin)
3. Changing the header to `{"alg":"none","typ":"JWT"}`
4. Re-encoding with no signature (`header.payload.`)
5. Sending to a vulnerable server → accepted as valid

**Defense:** Always explicitly whitelist accepted algorithms in your JWT library. Never accept `alg:none`. Modern libraries require you to specify algorithms explicitly, which prevents this by default.

---

**Q7. When would you use RS256 over HS256?**

**Answer:** Use RS256 (asymmetric) when:
- Multiple services need to verify tokens but shouldn't be able to forge them. Distribute the public key; keep the private key only in the auth service.
- You're publishing tokens to third parties (external partners, federated identity).
- You publish a JWKS endpoint (`.well-known/jwks.json`) so consumers can fetch your public key automatically.
- You're building an OIDC identity provider.

Use HS256 (symmetric) when:
- A single service both issues and verifies tokens.
- All services share the same trust boundary and the secret is manageable.
- You need simpler key management (one secret vs. key pair + rotation).

The security level is equivalent for the given attack models, but RS256 gives you better separation of concerns in distributed architectures.

---

**Q8. How do sessions scale horizontally?**

**Answer:** Sessions stored in server process memory don't scale horizontally — a request hitting a different server than where the session was created won't find it. Two approaches:

1. **Sticky sessions:** The load balancer always routes the same client to the same server (based on IP or cookie). Problem: server failure loses all sessions; poor load distribution.

2. **Centralized session store (correct):** Use Redis (or a DB) as a shared session backend. All servers can read/write to it. Redis with replication handles availability. A session lookup is an O(1) Redis GET — fast enough for production. This is the standard approach and the reason Redis is nearly ubiquitous in production web architectures.

JWTs were partly motivated by the desire to avoid this centralized store, since the token is self-contained. But as discussed, they introduce the revocation problem in return.

---

## Resources

- [RFC 7519 — JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [jwt.io — JWT Debugger and Algorithm Comparison](https://jwt.io)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [golang-jwt/jwt library](https://github.com/golang-jwt/jwt)
- [Auth0 Refresh Token Rotation](https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [The Web Security Academy — JWT Attacks](https://portswigger.net/web-security/jwt)
- [Redis for Session Storage](https://redis.io/docs/manual/patterns/twitter-clone/)

---

**Next:** [Part 4.2: OAuth2, OIDC & API Keys](./04-oauth2-and-api-keys.md)
