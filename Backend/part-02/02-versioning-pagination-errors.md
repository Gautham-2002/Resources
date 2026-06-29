# Part 2.2: Versioning, Pagination & Error Handling

## What You'll Learn
- Four API versioning strategies with their trade-offs and when to choose each
- Semantic versioning adapted for REST APIs
- Offset pagination — simplicity, limitations, and when it breaks
- Cursor/keyset pagination — how it works, why it's O(log n), and how to implement it
- The deep pagination problem and why `LIMIT 10000 OFFSET 9990` kills your database
- RFC 7807 Problem Details — the standard error format for HTTP APIs
- HTTP status code selection — a complete decision tree
- Field-level validation error responses
- Error correlation with request IDs across distributed services

## Table of Contents
1. [API Versioning Strategies](#api-versioning-strategies)
2. [When to Version vs Evolve Gracefully](#when-to-version-vs-evolve-gracefully)
3. [Semantic Versioning for APIs](#semantic-versioning-for-apis)
4. [Pagination](#pagination)
5. [The Deep Pagination Problem](#the-deep-pagination-problem)
6. [Cursor Pagination Implementation](#cursor-pagination-implementation)
7. [Error Handling](#error-handling)
8. [HTTP Status Code Decision Tree](#http-status-code-decision-tree)
9. [RFC 7807 Problem Details](#rfc-7807-problem-details)
10. [Error Correlation and Request IDs](#error-correlation-and-request-ids)
11. [Implementation Examples](#implementation-examples)
12. [Common Pitfalls](#common-pitfalls)
13. [Interview Questions](#interview-questions)

---

## API Versioning Strategies

When you need to make a breaking change, you have four main strategies. Each has real trade-offs.

### Strategy 1: URL Path Versioning

```
GET https://api.example.com/v1/users
GET https://api.example.com/v2/users
```

**How it works:** The version is embedded directly in the URL path. When you need a breaking change, you create a new path prefix.

**Pros:**
- Immediately visible in URLs — easy to see which version you're calling
- Dead simple to test in a browser, curl, Postman
- Easy to route at the load balancer or API gateway level (`/v1/*` → service-v1)
- Works with HTTP caching (different URLs → different cache keys)
- Easy to log and monitor per-version usage in access logs

**Cons:**
- Not "pure REST" — a resource's URL should be stable, not version-stamped
- Creates route duplication — `v1/users` and `v2/users` often share 90% of logic
- The version in the URL applies to all resources, even those that didn't change

**When to use:** Most APIs. The practical benefits far outweigh the theoretical purity concerns. Used by Stripe, GitHub, Twilio, Twitter.

```
Real-world examples:
https://api.stripe.com/v1/charges
https://api.github.com/v3/repos/{owner}/{repo}
https://api.twitter.com/2/tweets
```

---

### Strategy 2: Header Versioning

```
GET https://api.example.com/users
Accept: application/vnd.mycompany.api.v2+json
```

or using a custom header:

```
GET https://api.example.com/users
API-Version: 2
```

**How it works:** The version is carried in the `Accept` header (using vendor MIME types) or a custom header. The URL stays clean.

**Pros:**
- Clean, version-agnostic URLs (more "RESTful")
- A single URL can serve multiple versions based on header
- Resources can be versioned independently (users endpoint at v2, orders still at v1)

**Cons:**
- Can't test by pasting URL in browser — requires a tool like curl or Postman
- Easy to forget the header — clients that omit it get unpredictable behavior
- Complicated cache key: CDNs and proxies cache by URL by default; you need `Vary: Accept` or similar
- Harder to route at the infrastructure level
- Logs and metrics don't naturally separate versions

**When to use:** Internal APIs where all clients are controlled and use HTTP client libraries. GitHub uses this for their JSON API: `Accept: application/vnd.github.v3+json`.

---

### Strategy 3: Query Parameter Versioning

```
GET https://api.example.com/users?version=2
GET https://api.example.com/users?api-version=2026-01-01
```

**How it works:** Version is passed as a query parameter.

**Pros:**
- Simple to implement and understand
- Version is visible in URLs but doesn't clutter the path
- Easy to test in a browser

**Cons:**
- Easy to forget — what's the default when the parameter is missing?
- Query parameters interact with caching in complex ways (different URLs per version, but proxies may not respect this)
- Version applies to the whole request, but mixed-version needs per-resource are clunky
- Logs can contain many different version combinations

**When to use:** Microsoft Azure REST API uses this approach (`?api-version=2023-09-01`). Useful for services with infrequent versioning needs and controlled clients.

---

### Strategy 4: Subdomain Versioning

```
GET https://v1.api.example.com/users
GET https://v2.api.example.com/users
```

**How it works:** Each version gets its own subdomain.

**Pros:**
- Complete isolation — different subdomains can point to entirely different infrastructure
- Easy to deprecate: just stop serving the old subdomain
- Useful for major version migrations where you want clean separation

**Cons:**
- CORS configuration becomes complex (v1.api.example.com vs v2.api.example.com)
- TLS certificate management for each subdomain
- DNS propagation latency during rollouts
- Unusual and unfamiliar to most API consumers

**When to use:** Rarely. Only when you want complete infrastructure separation between versions. Almost no popular public APIs use this.

---

### Comparison Table

```
┌──────────────────┬──────────────┬────────────────┬──────────────┬──────────────────┐
│ Strategy         │ Browser-     │ Cache          │ Infrastructure│ Real-world       │
│                  │ friendly?    │ behavior       │ routing       │ usage            │
├──────────────────┼──────────────┼────────────────┼──────────────┼──────────────────┤
│ URL Path (/v1/)  │ ✅ Yes       │ ✅ Natural      │ ✅ Easy       │ Stripe, GitHub   │
│ Header versioning│ ❌ No        │ ⚠️  Needs Vary  │ ❌ Complex    │ GitHub JSON API  │
│ Query param      │ ✅ Yes       │ ⚠️  Varies      │ ⚠️  Medium    │ Azure REST API   │
│ Subdomain (v2.)  │ ✅ Yes       │ ✅ Natural      │ ✅ Easy       │ Very rare        │
└──────────────────┴──────────────┴────────────────┴──────────────┴──────────────────┘
```

---

## When to Version vs Evolve Gracefully

Not every change requires a version bump. The decision tree:

```
Is the change breaking?
├── NO → Evolve gracefully (additive change)
│        Add optional field, new endpoint, relaxed validation
│        Use Deprecation header if removing future behavior
│
└── YES → Can you avoid it?
          ├── YES → Redesign to make it additive
          │         (e.g., add new field instead of renaming old one)
          │
          └── NO → Must version
                   ├── Is this a minor behavioral tweak?
                   │   → Consider feature flag or header-based rollout first
                   │
                   └── Is this a major redesign?
                       → URL version bump (/v1/ → /v2/)
```

**Graceful evolution tricks to avoid versioning:**

1. **Add, don't rename.** Instead of renaming `username` → `handle`, add `handle` alongside `username` and deprecate `username`. Both coexist.

2. **Additive enums.** Adding a new enum value (e.g., status `"refunding"`) is safe if clients handle unknown values gracefully (they should).

3. **Expand, don't contract.** Instead of changing a field from `string` to `object`, expand: add a parallel `addressObject` field while keeping the old `address` string.

4. **Flag gating.** Roll out new behavior behind a feature flag (`?experimental=true`) before making it the default.

---

## Semantic Versioning for APIs

Software libraries use semver: `MAJOR.MINOR.PATCH`. APIs adapt this:

```
MAJOR version → Breaking change (rename field, remove endpoint, change auth)
MINOR version → New feature, backward compatible (add endpoint, add optional field)
PATCH version → Bug fix, no API surface change
```

In URL versioning, you typically only increment the major version:
```
/v1/ → /v2/    (breaking change)
```

Minor and patch changes are transparent to clients since they're additive.

For services with many consumers, use **date-based versioning** (Azure style):
```
/2024-01-01/users
/2025-06-01/users
```

This communicates *when* the version was introduced, which helps operators understand what behavior to expect and when to migrate.

**API lifecycle stages:**

```
alpha → beta → GA (Generally Available) → Deprecated → Retired

alpha:      May change without notice, not for production
beta:       Mostly stable, minor breaking changes possible
GA:         Stable contract, breaking changes require new version
Deprecated: Still functional, sunset date announced
Retired:    Returns 410 Gone or redirects to new version
```

---

## Pagination

When a collection has more items than you want to return in one response, you need pagination. There are three main strategies.

### Offset Pagination

```sql
SELECT * FROM users ORDER BY created_at DESC LIMIT 20 OFFSET 40;
```

```
GET /users?page=3&per_page=20
GET /users?offset=40&limit=20
```

**Response:**
```json
{
  "data": [...],
  "meta": {
    "total": 243,
    "page": 3,
    "perPage": 20,
    "totalPages": 13
  }
}
```

**How it works:** Skip the first N rows, return the next M. Page 3 with 20 items per page = OFFSET 40.

**Pros:**
- Simple to implement and understand
- Supports random page access (jump to page 7)
- Users can see total pages

**Cons:**

1. **Data drift on mutations.** If someone inserts or deletes an item while the user is paginating:

```
Page 1: [user-1, user-2, user-3, ..., user-20]  ← user reads page 1
         ↑ New user-0 inserted here
Page 2: [user-1, user-2, ..., user-20, user-21]  ← OFFSET 20 returns user-1 again!
         user-20 from page 1 reappears on page 2
```

2. **O(n) database scan.** For `LIMIT 20 OFFSET 9990`, the database must read and discard 9990 rows before returning your 20. This is the deep pagination problem.

3. **COUNT(*) is expensive.** Returning `total` requires a full table count, which is slow on large tables.

---

### Page-Based Pagination

Same as offset, but expressed as page numbers:

```
GET /users?page=1        → OFFSET 0  LIMIT 20
GET /users?page=2        → OFFSET 20 LIMIT 20
GET /users?page=100      → OFFSET 1980 LIMIT 20
```

This is just offset pagination with sugar. Same pros and cons. Page numbers are more user-friendly in UI but have identical database behavior.

---

### Cursor / Keyset Pagination

```sql
-- First page
SELECT * FROM users ORDER BY created_at DESC, id DESC LIMIT 20;

-- Next page (using the last row's values as the cursor)
SELECT * FROM users
WHERE (created_at, id) < ('2026-01-15T10:30:00Z', '123')
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

```
GET /users?cursor=eyJjcmVhdGVkX2F0IjoiMjAyNi0wMS0xNVQxMDozMDowMFoiLCJpZCI6IjEyMyJ9&limit=20
```

**Response:**
```json
{
  "data": [...20 items...],
  "meta": {
    "nextCursor": "eyJjcmVhdGVkX2F0IjoiMjAyNi0wMS0xNFQwOToyMTowMFoiLCJpZCI6IjEwMCJ9",
    "hasMore": true,
    "limit": 20
  }
}
```

**How it works:**
1. Return the first N items
2. Encode the "position" of the last item as an opaque cursor
3. The next request passes this cursor; the query fetches items AFTER this position
4. Because you're using indexed columns for comparison, the database can use the index directly — no offset scan

**Cursor encoding:** Base64-encode a JSON object containing the sort key values of the last returned item:

```
{ "created_at": "2026-01-15T10:30:00Z", "id": "123" }
→ base64 encode →
eyJjcmVhdGVkX2F0IjoiMjAyNi0wMS0xNVQxMDozMDowMFoiLCJpZCI6IjEyMyJ9
```

The cursor is opaque to clients — they don't need to know its structure, just pass it back.

**Pros:**
- **Stable under mutations.** No items are skipped or duplicated when data changes between requests.
- **O(log n) database performance.** Uses the index on the sort key — no full table scan.
- **Works at any depth.** Page 1000 is as fast as page 1.

**Cons:**
- **No random page access.** Can't jump to page 7; must paginate sequentially.
- **No total count.** You can't show "showing page 3 of 47".
- **More complex to implement.**
- **Cursor must be stable.** If you sort by `created_at` and two rows have the same timestamp, you must include `id` as a tiebreaker in both the cursor and the WHERE clause.

---

### Comparison Table

```
┌─────────────────────┬───────────────┬────────────────────┬──────────────────────┐
│ Feature             │ Offset/Page   │ Cursor/Keyset      │ When to use          │
├─────────────────────┼───────────────┼────────────────────┼──────────────────────┤
│ Implementation      │ Simple        │ Moderate           │                      │
│ DB performance      │ O(n) at depth │ O(log n)           │                      │
│ Random page jump    │ ✅ Yes        │ ❌ No              │                      │
│ Stable under inserts│ ❌ Drifts     │ ✅ Stable          │                      │
│ Total count         │ ✅ Yes        │ ❌ No              │                      │
│ Infinite scroll     │ ⚠️ Drifts     │ ✅ Perfect         │                      │
│ Deep pages          │ ❌ Slow       │ ✅ Fast            │                      │
│ Use case            │ Admin tables  │ Feeds, timelines   │                      │
└─────────────────────┴───────────────┴────────────────────┴──────────────────────┘
```

---

## The Deep Pagination Problem

This is a classic interview topic. Let's understand why `LIMIT 20 OFFSET 9990` is a performance disaster.

```sql
-- "Show me page 500 with 20 items per page"
SELECT * FROM posts ORDER BY created_at DESC LIMIT 20 OFFSET 9980;
```

What the database actually does:

```
1. Full index scan on created_at
2. Read rows 1 through 10,000 from the index
3. DISCARD rows 1 through 9,980
4. Return rows 9,981 through 10,000
```

You're paying the cost of reading 10,000 rows to serve 20. At page 5,000 (100,000 rows offset), this becomes untenable. Even with an index, the database must traverse 100,000 index entries.

```
Time complexity: O(OFFSET + LIMIT) per page
Page 1:    O(20)
Page 100:  O(2,000)
Page 500:  O(10,000)
Page 5000: O(100,000)
```

**Cursor pagination solution:**

```sql
-- After getting last item with (created_at='2026-01-10', id='5000')
SELECT * FROM posts
WHERE (created_at < '2026-01-10')
   OR (created_at = '2026-01-10' AND id < '5000')
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

With a composite index on `(created_at DESC, id DESC)`, the database:
1. Seeks directly to the cursor position in the index — O(log n)
2. Reads the next 20 rows — O(1)
3. Total: O(log n) regardless of depth

```
Time complexity: O(log n + LIMIT) per page
Page 1:    O(log n + 20) ≈ same as cursor-based
Page 100:  O(log n + 20) ≈ same
Page 5000: O(log n + 20) ≈ same  ← cursor pagination shines here
```

**When offset pagination is acceptable:**

- Small tables (< 10,000 rows) where offset cost is negligible
- Admin UIs where random page access is needed and users rarely go beyond page 10
- Export/batch processing where you control pagination and can add DB hints

---

## Error Handling

### The Philosophy of Error Responses

Errors are part of your API's contract. They need to be as carefully designed as success responses. A good error response:

1. Tells the client **what went wrong** (machine-readable code)
2. Tells a developer **why** (human-readable message)
3. Tells the client **what to do** (retry? fix input? authenticate?)
4. Enables **debugging** (request ID to correlate with logs)
5. **Doesn't leak** internals (no stack traces, no SQL errors, no internal IDs)

---

## HTTP Status Code Decision Tree

```
Was the request malformed or invalid?
├── Can't parse the JSON body → 400 Bad Request
├── Passes parsing but fails validation → 422 Unprocessable Entity
├── Required header missing (e.g., Content-Type) → 400 Bad Request
└── Correct syntax, correct semantics → proceed

Is the client authenticated?
└── No valid auth token/session → 401 Unauthorized

Is the client authorized to do this?
└── Authenticated but lacks permission → 403 Forbidden

Does the resource exist?
├── Never existed → 404 Not Found
└── Existed but permanently deleted → 410 Gone

Is there a conflict?
├── Duplicate key / already exists → 409 Conflict
├── Optimistic lock mismatch (ETag) → 412 Precondition Failed
└── Idempotency key in-flight → 409 Conflict

Is the client sending too many requests?
└── Rate limit exceeded → 429 Too Many Requests

Is the method not supported?
└── 405 Method Not Allowed (include Allow header with supported methods)

Did the server encounter an internal error?
├── Unexpected exception → 500 Internal Server Error
├── Upstream service returned error → 502 Bad Gateway
├── Server temporarily unavailable → 503 Service Unavailable
└── Upstream service timed out → 504 Gateway Timeout

Is the operation async?
└── Accepted for background processing → 202 Accepted

Did the operation succeed?
├── Created a new resource → 201 Created (with Location header)
├── Succeeded but no body to return → 204 No Content
└── Standard success with body → 200 OK
```

### The 400 vs 422 Distinction

This trips up many engineers:

- **400 Bad Request**: The request is syntactically malformed. The server can't parse it. Examples: invalid JSON, missing required header, wrong Content-Type.

- **422 Unprocessable Entity**: The request is syntactically valid (the server can parse it), but semantically invalid. Examples: valid JSON but email field has wrong format, age is negative, date range is backwards.

```
POST /users
Content-Type: application/json
Body: {this is not valid json}
→ 400 Bad Request  (can't even parse the body)

POST /users
Content-Type: application/json
Body: {"name": "Alice", "email": "not-an-email", "age": -5}
→ 422 Unprocessable Entity  (valid JSON, but invalid field values)
```

In practice, many APIs use 400 for both. The distinction matters when you want clients to know whether the problem is structural (fix your JSON) or logical (fix your field values).

---

## RFC 7807 Problem Details

RFC 7807 defines a standard format for HTTP error responses. It's worth knowing for interviews and adopting for production APIs.

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The request body contains invalid field values.",
  "instance": "/v1/users/requests/req_7f3a9b2c",
  "errors": [
    {
      "field": "email",
      "message": "Must be a valid email address"
    }
  ]
}
```

**Fields defined by RFC 7807:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | URI | A URL identifying the error type. Should resolve to human-readable documentation. Use `about:blank` if you don't have a page. |
| `title` | string | Short, human-readable summary of the error type. Should be the same for the same type every time. |
| `status` | integer | The HTTP status code. Included in the body for convenience. |
| `detail` | string | Human-readable explanation specific to this occurrence of the error. |
| `instance` | URI | A URI identifying this specific occurrence of the error (e.g., a request ID URL). |

**Extension fields** (not in the spec but allowed): `errors`, `requestId`, `timestamp`, etc.

**Content-Type for Problem Details:**
```
Content-Type: application/problem+json
```

This signals to clients that this is an RFC 7807 error response, not a regular JSON body.

### Why Use RFC 7807?

1. **Standardization.** Clients written for different services can handle errors uniformly.
2. **Machine-readable error types.** `type` is a URL — clients can look it up or map it to a specific error-handling branch.
3. **Interoperability.** API gateways, monitoring tools, and error tracking services can parse it without custom configuration.
4. **Extensible.** You can add any field you need (validation details, request IDs) while staying compliant.

---

## Error Correlation and Request IDs

In a microservices architecture, a single API call can fan out to 5+ downstream services. When something fails, you need to trace the error across services.

```
Client → API Gateway → User Service → Auth Service → DB
                     ↓                    ↓
                  Order Service       Cache (Redis)
```

**The pattern:** Generate a `requestId` (UUID) at the API gateway and propagate it through all downstream calls via headers.

```
X-Request-ID: req_7f3a9b2c1d4e5f6a

API Gateway → User Service:    X-Request-ID: req_7f3a9b2c1d4e5f6a
User Service → Auth Service:   X-Request-ID: req_7f3a9b2c1d4e5f6a
User Service → Order Service:  X-Request-ID: req_7f3a9b2c1d4e5f6a
```

Every service logs the `requestId` with every log line. To debug, you search for the `requestId`:

```bash
grep "req_7f3a9b2c1d4e5f6a" /var/log/services/*.log
# Instantly shows the full request trace across all services
```

**Include `requestId` in error responses:**

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "requestId": "req_7f3a9b2c1d4e5f6a"
  }
}
```

When a user reports an error, they paste the `requestId` and you instantly find all related logs.

### Structured Logging Format

Log errors in a machine-parseable format:

```json
{
  "level": "error",
  "timestamp": "2026-01-15T10:30:05.123Z",
  "requestId": "req_7f3a9b2c1d4e5f6a",
  "userId": "user-123",
  "method": "POST",
  "path": "/v1/payments",
  "statusCode": 500,
  "durationMs": 245,
  "error": {
    "name": "DatabaseError",
    "message": "Connection pool exhausted",
    "stack": "..." // only in non-production logs
  }
}
```

**What to log server-side vs what to return to clients:**

```
Server-side logs:              Client response:
───────────────────            ─────────────────────────
Full stack trace          ✅   requestId              ✅
Internal error message    ✅   Generic error message  ✅
User ID / session info    ✅   Error code             ✅
Database query details    ✅   Stack trace            ❌ (security risk)
Request headers/body      ✅   Internal error message ❌ (leaks internals)
System state at failure   ✅   Database details       ❌ (attack surface)
```

---

## Implementation Examples

### Go + Chi Router

```go
package main

import (
    "context"
    "encoding/base64"
    "encoding/json"
    "fmt"
    "net/http"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"
    "github.com/google/uuid"
)

// ─── RFC 7807 Problem Details ─────────────────────────────────────────────────

type ProblemDetails struct {
    Type       string        `json:"type"`
    Title      string        `json:"title"`
    Status     int           `json:"status"`
    Detail     string        `json:"detail"`
    Instance   string        `json:"instance"`
    RequestID  string        `json:"requestId,omitempty"`
    Errors     []FieldProblem `json:"errors,omitempty"`
}

type FieldProblem struct {
    Field   string `json:"field"`
    Message string `json:"message"`
    Code    string `json:"code"`
}

func writeProblem(w http.ResponseWriter, r *http.Request, status int, problemType, title, detail string, fieldErrors ...FieldProblem) {
    reqID, _ := r.Context().Value(middleware.RequestIDKey).(string)
    problem := ProblemDetails{
        Type:      "https://api.example.com/errors/" + problemType,
        Title:     title,
        Status:    status,
        Detail:    detail,
        Instance:  fmt.Sprintf("/requests/%s", reqID),
        RequestID: reqID,
        Errors:    fieldErrors,
    }
    w.Header().Set("Content-Type", "application/problem+json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(problem)
}

// ─── Cursor Pagination ────────────────────────────────────────────────────────

type Cursor struct {
    CreatedAt time.Time `json:"created_at"`
    ID        string    `json:"id"`
}

func encodeCursor(createdAt time.Time, id string) string {
    c := Cursor{CreatedAt: createdAt, ID: id}
    b, _ := json.Marshal(c)
    return base64.URLEncoding.EncodeToString(b)
}

func decodeCursor(encoded string) (*Cursor, error) {
    b, err := base64.URLEncoding.DecodeString(encoded)
    if err != nil {
        return nil, fmt.Errorf("invalid cursor encoding: %w", err)
    }
    var c Cursor
    if err := json.Unmarshal(b, &c); err != nil {
        return nil, fmt.Errorf("invalid cursor content: %w", err)
    }
    return &c, nil
}

type PaginatedResponse struct {
    Data       any     `json:"data"`
    NextCursor *string `json:"nextCursor"`
    HasMore    bool    `json:"hasMore"`
    Limit      int     `json:"limit"`
    RequestID  string  `json:"requestId"`
}

type Post struct {
    ID        string    `json:"id"`
    Title     string    `json:"title"`
    CreatedAt time.Time `json:"createdAt"`
}

// Simulates a cursor-paginated DB query
func queryPostsWithCursor(ctx context.Context, cursor *Cursor, limit int) ([]Post, error) {
    // In production this would be a real DB query like:
    //
    // WHERE (created_at < $1) OR (created_at = $1 AND id < $2)
    // ORDER BY created_at DESC, id DESC
    // LIMIT $3
    //
    // Using (created_at, id) composite index for O(log n) access

    now := time.Now()
    posts := make([]Post, 0, limit)
    for i := 0; i < limit+1; i++ { // +1 to detect hasMore
        id := uuid.New().String()
        post := Post{
            ID:        id,
            Title:     fmt.Sprintf("Post %d", i),
            CreatedAt: now.Add(-time.Duration(i) * time.Hour),
        }
        if cursor != nil && !post.CreatedAt.Before(cursor.CreatedAt) {
            continue
        }
        posts = append(posts, post)
        if len(posts) == limit+1 {
            break
        }
    }
    return posts, nil
}

func listPostsHandler(w http.ResponseWriter, r *http.Request) {
    reqID, _ := r.Context().Value(middleware.RequestIDKey).(string)

    // Parse limit
    limit := 20
    if l := r.URL.Query().Get("limit"); l != "" {
        fmt.Sscanf(l, "%d", &limit)
        if limit < 1 || limit > 100 {
            writeProblem(w, r, http.StatusBadRequest, "invalid-parameter",
                "Invalid Parameter", "limit must be between 1 and 100")
            return
        }
    }

    // Parse cursor
    var cursor *Cursor
    if cursorStr := r.URL.Query().Get("cursor"); cursorStr != "" {
        var err error
        cursor, err = decodeCursor(cursorStr)
        if err != nil {
            writeProblem(w, r, http.StatusBadRequest, "invalid-cursor",
                "Invalid Cursor", "The provided cursor is invalid or expired")
            return
        }
    }

    posts, err := queryPostsWithCursor(r.Context(), cursor, limit)
    if err != nil {
        writeProblem(w, r, http.StatusInternalServerError, "internal-error",
            "Internal Server Error", "An unexpected error occurred")
        return
    }

    hasMore := len(posts) > limit
    if hasMore {
        posts = posts[:limit] // trim the extra item
    }

    var nextCursor *string
    if hasMore && len(posts) > 0 {
        last := posts[len(posts)-1]
        encoded := encodeCursor(last.CreatedAt, last.ID)
        nextCursor = &encoded
    }

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(PaginatedResponse{
        Data:       posts,
        NextCursor: nextCursor,
        HasMore:    hasMore,
        Limit:      limit,
        RequestID:  reqID,
    })
}

// ─── Versioned Routes ─────────────────────────────────────────────────────────

func NewVersionedRouter() http.Handler {
    r := chi.NewRouter()
    r.Use(middleware.RequestID)
    r.Use(middleware.Logger)
    r.Use(middleware.Recoverer)

    // V1 routes
    r.Route("/v1", func(r chi.Router) {
        r.Get("/posts", listPostsHandler)
        r.Get("/users/{userID}", getUserV1Handler)
    })

    // V2 routes — breaking changes from V1
    r.Route("/v2", func(r chi.Router) {
        r.Get("/users/{userID}", getUserV2Handler) // different response shape
        r.Get("/posts", listPostsHandler)          // same handler — no change
    })

    return r
}

// V1 returns { id, username, email }
func getUserV1Handler(w http.ResponseWriter, r *http.Request) {
    userID := chi.URLParam(r, "userID")
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]any{
        "id":       userID,
        "username": "priya_k",
        "email":    "priya@example.com",
    })
}

// V2 returns { id, handle, email, profile } — "username" renamed to "handle"
func getUserV2Handler(w http.ResponseWriter, r *http.Request) {
    userID := chi.URLParam(r, "userID")
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]any{
        "id":     userID,
        "handle": "priya_k",
        "email":  "priya@example.com",
        "profile": map[string]any{
            "bio":    "Backend engineer",
            "avatar": "https://cdn.example.com/avatars/priya.jpg",
        },
    })
}

func main() {
    http.ListenAndServe(":8080", NewVersionedRouter())
}
```

### Node.js + Express

```javascript
// versioning-pagination-errors.js
const express = require('express');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(express.json());

// ─── Request ID Middleware ────────────────────────────────────────────────────

app.use((req, res, next) => {
  req.requestId = req.headers['x-request-id'] || uuidv4();
  res.setHeader('X-Request-ID', req.requestId);
  next();
});

// ─── RFC 7807 Problem Details Helper ──────────────────────────────────────────

const sendProblem = (res, req, status, type, title, detail, extensions = {}) => {
  res.status(status)
     .type('application/problem+json')
     .json({
       type: `https://api.example.com/errors/${type}`,
       title,
       status,
       detail,
       instance: `/requests/${req.requestId}`,
       requestId: req.requestId,
       ...extensions,
     });
};

// ─── Cursor Encoding/Decoding ─────────────────────────────────────────────────

const encodeCursor = (createdAt, id) => {
  const payload = JSON.stringify({ createdAt, id });
  return Buffer.from(payload).toString('base64url');
};

const decodeCursor = (encoded) => {
  try {
    const payload = Buffer.from(encoded, 'base64url').toString('utf-8');
    return JSON.parse(payload);
  } catch {
    return null;
  }
};

// ─── Simulated DB (replace with real DB queries in production) ────────────────

const generatePosts = (count, startOffset = 0) =>
  Array.from({ length: count }, (_, i) => ({
    id: uuidv4(),
    title: `Post ${startOffset + i + 1}`,
    createdAt: new Date(Date.now() - (startOffset + i) * 3600 * 1000).toISOString(),
  }));

// Simulates cursor-based DB query
// In production this would be:
// WHERE (created_at < $cursor.createdAt OR (created_at = $cursor.createdAt AND id < $cursor.id))
// ORDER BY created_at DESC, id DESC
// LIMIT $limit + 1
const queryPostsWithCursor = (cursor, limit) => {
  const allPosts = generatePosts(200);
  let filtered = allPosts;

  if (cursor) {
    const idx = allPosts.findIndex(p => p.createdAt <= cursor.createdAt);
    filtered = idx >= 0 ? allPosts.slice(idx) : [];
  }

  return filtered.slice(0, limit + 1); // +1 to detect hasMore
};

// ─── V1 Routes ────────────────────────────────────────────────────────────────

const v1Router = express.Router();

v1Router.get('/posts', (req, res) => {
  const limit = Math.min(parseInt(req.query.limit) || 20, 100);
  const cursorStr = req.query.cursor;

  let cursor = null;
  if (cursorStr) {
    cursor = decodeCursor(cursorStr);
    if (!cursor) {
      return sendProblem(res, req, 400, 'invalid-cursor',
        'Invalid Cursor', 'The provided cursor is malformed or expired');
    }
  }

  const posts = queryPostsWithCursor(cursor, limit);
  const hasMore = posts.length > limit;
  const page = hasMore ? posts.slice(0, limit) : posts;

  let nextCursor = null;
  if (hasMore && page.length > 0) {
    const last = page[page.length - 1];
    nextCursor = encodeCursor(last.createdAt, last.id);
  }

  res.json({
    data: page,
    meta: {
      nextCursor,
      hasMore,
      limit,
      requestId: req.requestId,
    },
  });
});

// V1 user response: { id, username, email }
v1Router.get('/users/:userId', (req, res) => {
  const { userId } = req.params;

  if (userId === '999') {
    return sendProblem(res, req, 404, 'not-found',
      'Not Found', `User with ID ${userId} does not exist`);
  }

  res.json({
    data: {
      id: userId,
      username: 'priya_k',
      email: 'priya@example.com',
    },
    meta: { requestId: req.requestId },
  });
});

// ─── V2 Routes ────────────────────────────────────────────────────────────────

const v2Router = express.Router();

// V2 user response: breaking change — "username" renamed to "handle", added "profile"
v2Router.get('/users/:userId', (req, res) => {
  const { userId } = req.params;

  if (userId === '999') {
    return sendProblem(res, req, 404, 'not-found',
      'Not Found', `User with ID ${userId} does not exist`);
  }

  res.json({
    data: {
      id: userId,
      handle: 'priya_k',           // was "username" in v1
      email: 'priya@example.com',
      profile: {                    // new in v2
        bio: 'Backend engineer',
        avatar: 'https://cdn.example.com/avatars/priya.jpg',
      },
    },
    meta: { requestId: req.requestId },
  });
});

// Posts endpoint unchanged in v2 — re-use v1 handler
v2Router.get('/posts', v1Router.stack.find(r => r.route?.path === '/posts')?.route.stack[0].handle);

// ─── Mount versioned routers ──────────────────────────────────────────────────

app.use('/v1', v1Router);
app.use('/v2', v2Router);

// ─── Global Error Handler ─────────────────────────────────────────────────────

app.use((err, req, res, next) => {
  // Log server-side (include stack trace)
  console.error({
    requestId: req.requestId,
    error: err.message,
    stack: err.stack,
  });

  if (err.type === 'entity.parse.failed') {
    return sendProblem(res, req, 400, 'invalid-json',
      'Invalid JSON', 'The request body could not be parsed as JSON');
  }

  sendProblem(res, req, 500, 'internal-error',
    'Internal Server Error', 'An unexpected error occurred');
});

// ─── Validation Error Helper ──────────────────────────────────────────────────

const validateUser = (body) => {
  const errors = [];

  if (!body.name?.trim()) {
    errors.push({ field: 'name', message: 'Name is required' });
  } else if (body.name.length > 100) {
    errors.push({ field: 'name', message: 'Name must not exceed 100 characters' });
  }

  if (!body.email) {
    errors.push({ field: 'email', message: 'Email is required' });
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email)) {
    errors.push({ field: 'email', message: 'Must be a valid email address' });
  }

  if (body.age !== undefined && (body.age < 0 || body.age > 150)) {
    errors.push({ field: 'age', message: 'Age must be between 0 and 150' });
  }

  return errors;
};

v1Router.post('/users', (req, res) => {
  const errors = validateUser(req.body);
  if (errors.length > 0) {
    return sendProblem(res, req, 422, 'validation-error',
      'Validation Error', 'The request body contains invalid field values', { errors });
  }

  const user = {
    id: uuidv4(),
    username: req.body.name.trim(),
    email: req.body.email.toLowerCase(),
    createdAt: new Date().toISOString(),
  };

  res.setHeader('Location', `/v1/users/${user.id}`);
  res.status(201).json({ data: user, meta: { requestId: req.requestId } });
});

module.exports = app;
```

### Python + FastAPI

```python
# versioning_pagination_errors.py
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from fastapi import FastAPI, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, ValidationError

app = FastAPI(title="Blog API", version="2.0.0")

DataT = TypeVar("DataT")


# ─── RFC 7807 Problem Details ─────────────────────────────────────────────────

class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    request_id: Optional[str] = None
    errors: list[dict] = []

    model_config = {"populate_by_name": True}


def problem_response(
    request: Request,
    status_code: int,
    error_type: str,
    title: str,
    detail: str,
    errors: list[dict] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status_code,
        content={
            "type": f"https://api.example.com/errors/{error_type}",
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": f"/requests/{request_id}",
            "requestId": request_id,
            "errors": errors or [],
        },
        media_type="application/problem+json",
    )


# ─── Request ID Middleware ─────────────────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ─── Cursor Encoding/Decoding ─────────────────────────────────────────────────

def encode_cursor(created_at: datetime, item_id: str) -> str:
    """Base64url-encode a cursor containing sort key values."""
    payload = {"created_at": created_at.isoformat(), "id": item_id}
    raw = json.dumps(payload, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(encoded: str) -> dict | None:
    """Decode a cursor, returning None if invalid."""
    try:
        # Add padding if needed
        padded = encoded + "=" * (-len(encoded) % 4)
        raw = base64.urlsafe_b64decode(padded).decode()
        return json.loads(raw)
    except Exception:
        return None


# ─── Models ───────────────────────────────────────────────────────────────────

class Post(BaseModel):
    id: str
    title: str
    created_at: datetime


class CursorPage(BaseModel, Generic[DataT]):
    data: list[DataT]
    next_cursor: Optional[str] = None
    has_more: bool
    limit: int


class UserV1(BaseModel):
    id: str
    username: str
    email: str


class UserV2(BaseModel):
    id: str
    handle: str   # renamed from username
    email: str
    profile: dict


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    age: Optional[int] = Field(default=None, ge=0, le=150)


# ─── Simulated DB ─────────────────────────────────────────────────────────────

def generate_posts(count: int, offset_hours: int = 0) -> list[Post]:
    now = datetime.now(timezone.utc)
    return [
        Post(
            id=str(uuid.uuid4()),
            title=f"Post {i + 1 + offset_hours}",
            created_at=datetime(
                now.year, now.month, now.day, now.hour, now.minute, now.second,
                tzinfo=timezone.utc
            ).replace(second=0) - __import__("datetime").timedelta(hours=i + offset_hours),
        )
        for i in range(count)
    ]


def query_posts_cursor(cursor: dict | None, limit: int) -> list[Post]:
    """
    Simulate cursor-based pagination.
    Real SQL:
      SELECT * FROM posts
      WHERE (created_at < %(cursor_ts)s)
         OR (created_at = %(cursor_ts)s AND id < %(cursor_id)s)
      ORDER BY created_at DESC, id DESC
      LIMIT %(limit)s + 1
    """
    all_posts = generate_posts(200)
    if cursor:
        cursor_ts = datetime.fromisoformat(cursor["created_at"])
        all_posts = [p for p in all_posts if p.created_at < cursor_ts]
    return all_posts[:limit + 1]  # +1 to check hasMore


# ─── V1 Routes ────────────────────────────────────────────────────────────────

from fastapi import APIRouter

v1_router = APIRouter(prefix="/v1", tags=["v1"])
v2_router = APIRouter(prefix="/v2", tags=["v2"])


@v1_router.get("/posts", response_model=CursorPage[Post])
async def list_posts_v1(
    request: Request,
    cursor: Optional[str] = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    decoded_cursor = None
    if cursor:
        decoded_cursor = decode_cursor(cursor)
        if decoded_cursor is None:
            return problem_response(
                request, 400, "invalid-cursor",
                "Invalid Cursor", "The provided cursor is malformed or expired"
            )

    posts = query_posts_cursor(decoded_cursor, limit)
    has_more = len(posts) > limit
    page = posts[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(last.created_at, last.id)

    return CursorPage(
        data=page,
        next_cursor=next_cursor,
        has_more=has_more,
        limit=limit,
    )


@v1_router.get("/users/{user_id}", response_model=UserV1)
async def get_user_v1(request: Request, user_id: str):
    if user_id == "999":
        return problem_response(
            request, 404, "not-found",
            "Not Found", f"User with ID {user_id} does not exist"
        )
    return UserV1(id=user_id, username="priya_k", email="priya@example.com")


@v1_router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user_v1(request: Request, response: Response, body: CreateUserRequest):
    user = UserV1(id=str(uuid.uuid4()), username=body.name, email=body.email)
    response.headers["Location"] = f"/v1/users/{user.id}"
    return {"data": user.model_dump(), "meta": {"requestId": request.state.request_id}}


# ─── V2 Routes ────────────────────────────────────────────────────────────────

@v2_router.get("/users/{user_id}", response_model=UserV2)
async def get_user_v2(request: Request, user_id: str):
    """V2: breaking change — 'username' renamed to 'handle', new 'profile' field."""
    if user_id == "999":
        return problem_response(
            request, 404, "not-found",
            "Not Found", f"User with ID {user_id} does not exist"
        )
    return UserV2(
        id=user_id,
        handle="priya_k",  # was "username" in v1 — breaking change requires new version
        email="priya@example.com",
        profile={
            "bio": "Backend engineer",
            "avatar": "https://cdn.example.com/avatars/priya.jpg",
        },
    )


# Posts endpoint is the same in v2 — reuse v1 handler
@v2_router.get("/posts", response_model=CursorPage[Post])
async def list_posts_v2(
    request: Request,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    return await list_posts_v1(request, cursor, limit)


# ─── Mount Routers ────────────────────────────────────────────────────────────

app.include_router(v1_router)
app.include_router(v2_router)


# ─── Global Exception Handler for Pydantic Validation Errors ─────────────────

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(p) for p in error["loc"] if p != "body")
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
        })
    return problem_response(
        request, 422, "validation-error",
        "Validation Error", "The request body contains invalid field values",
        errors=errors,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log with request ID for correlation
    import logging
    logging.error(
        "Unhandled exception",
        extra={
            "requestId": getattr(request.state, "request_id", "unknown"),
            "path": str(request.url.path),
            "error": str(exc),
        },
        exc_info=True,
    )
    return problem_response(
        request, 500, "internal-error",
        "Internal Server Error", "An unexpected error occurred"
    )
```

---

## How It Works Internally

### Why Cursor Pagination Uses a Composite Index

The key insight is that the WHERE clause in cursor pagination maps directly to a B-tree index lookup:

```
Index on (created_at DESC, id DESC):

                    [2026-01-15, id-500]
                   /                     \
        [2026-01-14, id-300]          [2026-01-16, id-700]
        /            \
[2026-01-13, ...]  [2026-01-14, id-400]

Cursor query: WHERE created_at < '2026-01-14' OR (created_at = '2026-01-14' AND id < 'id-300')
→ B-tree seek directly to (2026-01-14, id-300) position — O(log n)
→ Read next N rows forward in the index — O(N)
```

Offset pagination traverses the index from the root, counting nodes. It can't "jump" to position 10,000 — it has to walk there.

### Base64 Cursor Encoding Rationale

The cursor is opaque to clients intentionally:
1. Clients shouldn't parse or construct cursors — it's an implementation detail
2. The encoding can change (you might add fields to the cursor) without a breaking API change
3. It prevents clients from hardcoding cursor values

Using `base64url` (not standard base64) avoids URL encoding issues since `+` and `/` in standard base64 require percent-encoding in URLs.

---

## Common Patterns & Best Practices

1. **Always include a `hasMore` field**, not just `nextCursor`. Even if `nextCursor` is non-null, having an explicit boolean is clearer.

2. **The +1 trick for detecting hasMore**: Query `LIMIT + 1` rows. If you get `LIMIT + 1` back, there's a next page. Return only `LIMIT` rows. This avoids an extra COUNT query.

3. **Never expose sort key values directly in cursors without encoding.** Raw values like `"cursor=2026-01-15T10:30:00Z,123"` leak your data model. Base64 encoding makes it opaque.

4. **Use `Deprecation` and `Sunset` headers when versioning:**
```
Deprecation: true
Sunset: Sat, 01 Jan 2027 00:00:00 GMT
Link: <https://api.example.com/v2/users>; rel="successor-version"
```

5. **For validation errors, always return ALL errors at once.** Don't stop at the first error. Users hate fixing one error only to hit another.

6. **Use `application/problem+json` content type for errors.** This signals to API clients that the response follows RFC 7807.

7. **Default page size should be stated in docs and consistent.** If you don't specify a default, developers will be confused. 20–50 items is a sensible default for most APIs.

8. **Cursor should be stable for the life of the pagination session.** Don't invalidate cursors after 1 minute — make them valid for at least 24 hours.

---

## Common Pitfalls

- ❌ **WRONG:** Using offset pagination for feeds/timelines with high mutation rates
- ✅ **CORRECT:** Use cursor pagination — offset pagination drifts when items are inserted/deleted

- ❌ **WRONG:** `SELECT COUNT(*) FROM posts` on every paginated request
- ✅ **CORRECT:** Use approximate counts (`pg_class.reltuples` in Postgres) or cache the count; exact counts are expensive on large tables

- ❌ **WRONG:** Cursor based only on `created_at` with no tiebreaker
- ✅ **CORRECT:** Always include a unique `id` as a tiebreaker: `WHERE (created_at, id) < ($ts, $id)`

- ❌ **WRONG:** Returning 200 with `{ "success": false, "error": "Not found" }`
- ✅ **CORRECT:** Return 404 with proper error body — HTTP status codes are the primary signal

- ❌ **WRONG:** Starting v2 development by copying v1 code into a new directory
- ✅ **CORRECT:** Share business logic in a service layer; only the controller/handler layer changes per version

- ❌ **WRONG:** Returning stack traces in production error responses
- ✅ **CORRECT:** Log stack traces server-side; return only `requestId` and generic message to client

- ❌ **WRONG:** `400 Bad Request` for semantic validation errors (wrong email format)
- ✅ **CORRECT:** `422 Unprocessable Entity` for semantically invalid but syntactically valid requests

- ❌ **WRONG:** Different error formats per endpoint (`{ "msg": "..." }` here, `{ "error": "..." }` there)
- ✅ **CORRECT:** One error format for the entire API, enforced via a shared error middleware

- ❌ **WRONG:** No request IDs in responses
- ✅ **CORRECT:** Generate a UUID per request, add it to response headers and error bodies; propagate through downstream calls

---

## Interview Questions

**Q1. Why is cursor pagination better than offset pagination for large datasets?**

**Answer:** Offset pagination has two fundamental problems at scale:

First, **O(n) database scans**. `LIMIT 20 OFFSET 9990` forces the database to read and discard 9,990 rows. At offset 100,000 it reads 100,000 rows to serve 20. Even with an index, this is an index scan of N entries.

Second, **data drift**. If a user reads page 1 (items 1–20), then someone inserts a new item at position 5, page 2 would repeat item 20 (now pushed to page 2) or skip item 21 (now on page 1). The pagination becomes inconsistent under concurrent writes.

Cursor pagination solves both: it uses `WHERE created_at < $cursor AND id < $cursor_id` with a composite index, which is an O(log n) index seek — the database jumps directly to the cursor position. No scan. No drift — the cursor points to a specific row in the ordered sequence, not a relative position.

---

**Q2. How do you choose between URL versioning and header versioning?**

**Answer:** For most APIs, URL versioning wins on pragmatic grounds.

URL versioning is visible, testable in a browser, and easy to route at the infrastructure level. `/v1/users` and `/v2/users` are different URLs — CDNs and proxies naturally differentiate them. Logs and metrics automatically separate version traffic. You can copy a URL and share it with a colleague, and they see the same version you do.

Header versioning is "purer REST" — a resource's URL should be stable, and versioning is a representation concern. But in practice: clients often forget to send the header (hard to debug), caches need a `Vary: Accept` directive (often misconfigured), and you can't test by pasting a URL.

**Recommendation:** Use URL versioning for public APIs and external consumers. Header versioning is acceptable for internal APIs where all clients are controlled and use HTTP client libraries that always set the header.

---

**Q3. What is the deep pagination problem?**

**Answer:** When using offset pagination, `LIMIT 20 OFFSET N` forces the database to read and discard N rows before returning 20. At large offsets (N = 10,000, 100,000), this becomes a full table or index scan up to position N — even though you only need 20 rows.

This is O(N) per page request, where N is the page offset. Page 500 with 20 items per page requires touching 10,000 rows. The query time grows linearly with page depth.

**Solutions:**
1. **Cursor pagination**: Replace offset with a keyset WHERE clause — O(log N) index seek.
2. **Seek method**: For known IDs, use `WHERE id > $last_id` instead of OFFSET.
3. **Materialized views**: For admin exports, pre-compute pagination data.
4. **Limit depth**: Simply disallow pages beyond a reasonable depth (e.g., max OFFSET 10,000) and tell users to search instead of paginate.

---

**Q4. What should be in a standardized error response?**

**Answer:** A good error response should include:

- **HTTP status code**: The primary signal (4xx client error, 5xx server error)
- **Error type** (`type`): A URI identifying the error category, per RFC 7807
- **Title** (`title`): Short, stable description of the error type
- **Detail** (`detail`): Human-readable explanation of this specific occurrence
- **Request ID** (`requestId`/`instance`): Unique ID correlating this response with server logs
- **Field-level errors** (`errors`): For validation failures, array of `{ field, message }` per field

What NOT to include:
- Stack traces (security risk, leaks internals)
- SQL error messages (leaks schema, potential SQL injection info)
- Internal error codes without explanation
- Sensitive data (PII, credentials, tokens)

---

**Q5. When should you return 400 vs 422?**

**Answer:**

**400 Bad Request**: The request is syntactically malformed — the server cannot parse it. Examples: invalid JSON body, missing required Content-Type header, malformed query parameter that can't be parsed.

**422 Unprocessable Entity**: The request is syntactically valid (parseable), but semantically invalid. Examples: valid JSON but `email` field has wrong format, `start_date` is after `end_date`, `age` is negative.

Mnemonic: 400 = "I can't read this," 422 = "I can read this but it's wrong."

In practice, many teams use 400 for both because 422 was originally an HTTP extension (WebDAV). The distinction matters when clients need to differentiate "my request format is broken" from "my field values are wrong" to display appropriate error messages.

---

**Q6. What is RFC 7807 and why should you follow it?**

**Answer:** RFC 7807 ("Problem Details for HTTP APIs") defines a standard JSON (and XML) format for error responses. It specifies:

- `type`: URI identifying the error type (links to documentation)
- `title`: Stable, human-readable name for the error type
- `status`: HTTP status code
- `detail`: Specific explanation of this occurrence
- `instance`: URI identifying this specific error occurrence

**Why follow it:**

1. **Standardization**: Clients written for multiple APIs can handle errors uniformly if everyone follows RFC 7807.
2. **Machine-readable error types**: The `type` URI allows clients to map error types to specific handling logic.
3. **Ecosystem tooling**: API gateways, monitoring tools, and error trackers can parse it without custom configuration.
4. **Content type signal**: Using `application/problem+json` tells client middleware that this is an error response, not a partial success.
5. **Extensibility**: You can add any fields you need (requestId, validation errors) while staying compliant.

The `type` doesn't have to resolve to a working URL, but it should be a stable, unique URI that identifies the error type in your system.

---

## Resources

- [RFC 7807 — Problem Details for HTTP APIs](https://tools.ietf.org/html/rfc7807)
- [RFC 8594 — The Sunset HTTP Header Field](https://tools.ietf.org/html/rfc8594)
- [RFC 5988 — Web Linking](https://tools.ietf.org/html/rfc5988)
- [Keyset Pagination — Use the Index, Luke](https://use-the-index-luke.com/no-offset)
- [Stripe Pagination Docs](https://stripe.com/docs/api/pagination)
- [GitHub Pagination Docs](https://docs.github.com/en/rest/guides/using-pagination-in-the-rest-api)
- [Azure API Versioning Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md#versioning)
- [Google Cloud API Versioning](https://cloud.google.com/apis/design/versioning)
- [Zalando REST API Guidelines — Pagination](https://opensource.zalando.com/restful-api-guidelines/#pagination)

---

**Next:** [Part 3.1: Routing & Middleware](../part-03/03-routing-and-middleware.md)
