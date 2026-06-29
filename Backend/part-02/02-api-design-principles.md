# Part 2.1: API Design Principles

## What You'll Learn
- How to name RESTful resources correctly (nouns, plural, hierarchical)
- CRUD to HTTP method mapping and the semantic meaning of each verb
- Idempotency — definition, which operations have it, and how to implement idempotency keys
- How to design consistent request/response envelopes
- API contracts: contract-first vs code-first, and OpenAPI/Swagger documentation
- Backward compatibility strategies and deprecation patterns
- HATEOAS — what it is, when it helps, when to skip
- Content negotiation with Accept and Content-Type headers
- Null vs absent fields and when to use each
- Consistent error response formats
- API design anti-patterns to avoid

## Table of Contents
1. [RESTful Resource Naming](#restful-resource-naming)
2. [CRUD to HTTP Method Mapping](#crud-to-http-method-mapping)
3. [Idempotency](#idempotency)
4. [Request and Response Design](#request-and-response-design)
5. [API Contracts and OpenAPI](#api-contracts-and-openapi)
6. [Backward Compatibility](#backward-compatibility)
7. [HATEOAS](#hateoas)
8. [Content Negotiation](#content-negotiation)
9. [Null vs Absent Fields](#null-vs-absent-fields)
10. [Consistent Error Response Format](#consistent-error-response-format)
11. [API Design Anti-Patterns](#api-design-anti-patterns)
12. [Implementation Examples](#implementation-examples)
13. [Common Pitfalls](#common-pitfalls)
14. [Interview Questions](#interview-questions)

---

## RESTful Resource Naming

REST stands for Representational State Transfer. The "resource" is the central abstraction. A resource is a noun — a thing that exists in your system, not an action performed on it.

### The Core Rule: Nouns, Not Verbs

Your URL identifies **what** you're acting on. The HTTP method tells the server **how** to act on it.

```
BAD  → POST /createUser
BAD  → GET  /getUserById?id=123
BAD  → POST /deleteOrder
BAD  → GET  /fetchProductList

GOOD → POST /users
GOOD → GET  /users/123
GOOD → DELETE /orders/456
GOOD → GET  /products
```

The HTTP verb is already the action. Adding verbs to the URL is redundant and breaks the REST constraint.

### Plural Resource Names

Always use plural nouns for collections, even when accessing a single resource. This consistency matters:

```
/users          ← collection of users
/users/123      ← a specific user
/orders         ← collection of orders
/orders/789     ← a specific order
```

Why plural? Because `/user/123` implies there is only one user in the system, or that you're accessing a singleton. `/users/123` makes it clear you're accessing user 123 within the users collection.

### Hierarchical Resources

Use path nesting to express ownership or containment relationships:

```
/users/{userId}/orders              ← all orders for a user
/users/{userId}/orders/{orderId}    ← a specific order for a user
/users/{userId}/addresses           ← all addresses for a user
/organizations/{orgId}/members      ← members of an organization
/organizations/{orgId}/members/{memberId}/roles  ← roles of a member
```

**Rules for nesting depth:**
- Keep nesting to 2–3 levels maximum
- If you're at 4+ levels, consider whether the sub-resource can stand alone
- `/orders/{orderId}` is often better than `/users/{userId}/orders/{orderId}` if order IDs are globally unique

```
Too deep (avoid):
/organizations/{orgId}/departments/{deptId}/teams/{teamId}/members/{memberId}

Better:
/teams/{teamId}/members/{memberId}
```

### Relationship Resources

Sometimes you have many-to-many relationships. Model them as their own resource:

```
POST   /users/{userId}/follow         ← follow a user (creates a "follow" relationship)
DELETE /users/{userId}/follow         ← unfollow
GET    /users/{userId}/followers      ← people following this user
GET    /users/{userId}/following      ← people this user follows

POST   /courses/{courseId}/enrollments   ← enroll in a course
DELETE /courses/{courseId}/enrollments/{enrollmentId}
```

### Controller-Style Endpoints (Acceptable Exceptions)

Some actions don't map cleanly to CRUD. Use a verb as a sub-resource in these cases:

```
POST /orders/{orderId}/cancel      ← cancel an order (not DELETE — it still exists)
POST /invoices/{invoiceId}/send    ← send an invoice via email
POST /users/{userId}/verify        ← trigger email verification
POST /payments/{paymentId}/refund  ← issue a refund
POST /accounts/{accountId}/lock    ← lock an account
```

These are "controller resources" — they represent an action that causes a state transition. POST is appropriate because the action has side effects, is not idempotent in all cases, and creates a new event.

---

## CRUD to HTTP Method Mapping

```
┌────────────┬──────────────────────────────────────────┬─────────────┬──────────────┐
│ HTTP Method│ Meaning                                  │ Idempotent  │ Safe         │
├────────────┼──────────────────────────────────────────┼─────────────┼──────────────┤
│ GET        │ Retrieve a resource or collection        │ Yes         │ Yes          │
│ POST       │ Create a new resource                    │ No*         │ No           │
│ PUT        │ Replace a resource entirely              │ Yes         │ No           │
│ PATCH      │ Partially update a resource              │ No*         │ No           │
│ DELETE     │ Remove a resource                        │ Yes         │ No           │
│ HEAD       │ Like GET but returns only headers        │ Yes         │ Yes          │
│ OPTIONS    │ Describe communication options (CORS)    │ Yes         │ Yes          │
└────────────┴──────────────────────────────────────────┴─────────────┴──────────────┘

* POST can be made idempotent with idempotency keys
* PATCH can be designed to be idempotent (set-based patches)
```

**Safe** means the operation does not modify server state. Safe operations can be cached, bookmarked, and replayed without side effects.

**Idempotent** means calling the operation N times produces the same result as calling it once. This matters hugely for retry logic.

### GET — Read

```
GET /users          → returns list of users (200 OK)
GET /users/123      → returns user 123 (200 OK) or 404 Not Found
GET /users?role=admin&page=2  → filtered list
```

GET must never have side effects. Never use GET to delete or modify data. GET requests should be cacheable.

### POST — Create

```
POST /users
Body: { "name": "Priya", "email": "priya@example.com" }
→ 201 Created
→ Location: /users/456
→ Body: { "id": 456, "name": "Priya", ... }
```

POST creates a new resource. The server assigns the ID. The response should include a `Location` header pointing to the newly created resource.

### PUT — Replace

PUT replaces the entire resource. If you PUT a user and omit the `email` field, the email is gone.

```
PUT /users/123
Body: { "name": "Priya Kumar", "email": "priya.kumar@example.com", "role": "admin" }
→ 200 OK (returns updated resource)
  or 204 No Content (no body)
```

PUT is idempotent: calling it 5 times with the same payload results in the same resource state.

### PATCH — Partial Update

PATCH updates only the fields you send. Fields not in the body remain unchanged.

```
PATCH /users/123
Body: { "name": "Priya Kumar" }
→ 200 OK (returns updated resource)

# Only name changed. email, role, etc. untouched.
```

Two approaches for PATCH semantics:
1. **Merge patch** (RFC 7396): The body is merged into the resource. `null` means delete the field.
2. **JSON Patch** (RFC 6902): An array of operations (`add`, `remove`, `replace`, `move`, `copy`, `test`).

```json
// JSON Patch (RFC 6902)
[
  { "op": "replace", "path": "/name", "value": "Priya Kumar" },
  { "op": "add", "path": "/nickname", "value": "PK" },
  { "op": "remove", "path": "/temporary_flag" }
]
```

### DELETE — Remove

```
DELETE /users/123
→ 204 No Content (most common)
→ 200 OK (if you return the deleted resource)
→ 202 Accepted (if deletion is async)
```

DELETE is idempotent: deleting an already-deleted resource should return 404 or 204 (be consistent). Returning 404 on repeated deletes is technically correct but can break idempotent retry logic. Many APIs return 204 regardless.

### PUT vs PATCH — The Interview Gotcha

This is asked constantly:

| Aspect | PUT | PATCH |
|--------|-----|-------|
| Semantics | Replace the whole resource | Modify specific fields |
| Missing fields | Treated as deleted/nulled | Left unchanged |
| Idempotency | Always idempotent | Depends on implementation |
| Payload size | Full resource every time | Only changed fields |
| Use case | Full replacement (e.g., config files) | Partial updates (e.g., profile edit) |

---

## Idempotency

### Definition

An operation is idempotent if applying it multiple times produces the same result as applying it once.

```
f(f(x)) = f(x)
```

In HTTP:
- **GET** is naturally idempotent — reading the same resource 10 times returns the same data (assuming no concurrent writes)
- **PUT** is idempotent — replacing a resource with the same data 10 times leaves the same state
- **DELETE** is idempotent — deleting a resource that's already deleted is a no-op (same end state)
- **POST** is NOT idempotent — posting a payment 10 times charges the user 10 times

### Why Idempotency Matters for Retries

In distributed systems, requests can fail ambiguously:
- The request reached the server and succeeded, but the response was lost
- The request timed out before reaching the server
- The network dropped mid-flight

If you retry a non-idempotent POST (like "charge $100"), you might double-charge. **Idempotency keys solve this.**

```
                 Client                    Server
                   │                         │
                   │── POST /payments ───────>│
                   │   Idempotency-Key: abc   │
                   │                         │─ Process payment
                   │                         │─ Store (key=abc, result=success)
                   │        [TIMEOUT]         │
                   │                         │
                   │── POST /payments ───────>│  (retry)
                   │   Idempotency-Key: abc   │
                   │                         │─ Look up key=abc
                   │                         │─ Found! Return cached result
                   │<── 200 OK (same result) ─│
                   │   (no duplicate charge)  │
```

### Implementing Idempotency Keys

1. Client generates a unique key (UUID v4) per logical operation
2. Client sends key in `Idempotency-Key` header (Stripe's convention) or as part of the request body
3. Server checks if it has seen this key before
4. If seen: return the cached response
5. If not seen: process the request, store result with key, return result

Key storage considerations:
- Use Redis with TTL (24–48 hours is typical)
- Store: key → (status_code, response_body, created_at)
- Use atomic check-and-set (SETNX) to avoid race conditions on concurrent retries
- Consider the key scope: per-user? per-endpoint? global?

```
Redis key: idempotency:{userId}:{idempotencyKey}
TTL: 86400 seconds (24 hours)
Value: { "status": 201, "body": {...}, "created_at": "2026-01-01T10:00:00Z" }
```

**What to store:** The exact HTTP response — status code and body. Do not re-execute business logic; return the cached response verbatim.

**Handling in-flight requests:** If two requests with the same key arrive simultaneously, one should win and the other should wait or return a 409 Conflict. Use a distributed lock or optimistic locking.

---

## Request and Response Design

### Consistent Response Envelope

Every response should have a predictable shape. Don't return raw arrays or inconsistent structures.

**Single resource:**
```json
{
  "data": {
    "id": "123",
    "name": "Priya Kumar",
    "email": "priya@example.com",
    "createdAt": "2026-01-15T10:30:00Z"
  },
  "meta": {
    "requestId": "req_7f3a9b2c"
  }
}
```

**Collection:**
```json
{
  "data": [
    { "id": "1", "name": "Alice" },
    { "id": "2", "name": "Bob" }
  ],
  "meta": {
    "total": 245,
    "page": 1,
    "perPage": 20,
    "requestId": "req_7f3a9b2c"
  }
}
```

**Error:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "field": "email", "message": "Invalid email format" },
      { "field": "age", "message": "Must be at least 18" }
    ],
    "requestId": "req_7f3a9b2c"
  }
}
```

### Field Naming Conventions

Pick one and be consistent across your entire API:

| Convention | Example | Common in |
|------------|---------|-----------|
| camelCase | `createdAt`, `userId` | JavaScript/Node.js APIs, most REST APIs |
| snake_case | `created_at`, `user_id` | Python APIs, Ruby APIs, PostgreSQL columns |
| PascalCase | `CreatedAt`, `UserId` | C#/.NET APIs |
| kebab-case | `created-at` | Rare, avoid in JSON |

**Recommendation:** Use camelCase for JSON responses regardless of your server language. It matches JavaScript conventions on the client side. Go's `json:"created_at"` tags let you map snake_case struct fields to camelCase JSON.

### Timestamp Formatting

Always use ISO 8601 with UTC timezone:

```
2026-01-15T10:30:00Z        ← UTC (recommended)
2026-01-15T16:00:00+05:30   ← With timezone offset
```

Never return Unix timestamps in production APIs unless you also return the ISO string. Unix timestamps are unreadable and timezone-ambiguous in logs.

### ID Formatting

Prefer string IDs over integer IDs in JSON responses:

```json
{ "id": "123" }     ← String (safe in all languages)
{ "id": 123 }       ← Integer (JavaScript loses precision above 2^53)
```

JavaScript's `number` type is a 64-bit float, which can represent integers precisely only up to 2^53 - 1 (9007199254740991). PostgreSQL's BIGSERIAL can generate IDs larger than this. Use string IDs or UUIDs to avoid this bug.

---

## API Contracts

### What Is an API Contract?

An API contract is a formal agreement between the API provider and its consumers. It defines:
- Available endpoints and their URLs
- Accepted request formats (headers, body schema, query params)
- Response formats for success and error cases
- Authentication requirements
- Rate limits and quotas
- Behavioral guarantees (idempotency, ordering, consistency)

Once published, breaking the contract breaks your clients. This is why contract discipline matters.

### Contract-First vs Code-First

**Contract-First:**
1. Write the OpenAPI spec file first
2. Review and agree with consumers
3. Generate server stubs and client SDKs from the spec
4. Implement business logic inside the stubs

Pros:
- Forces design thinking before coding
- Enables parallel frontend/backend development
- Makes breaking changes obvious before they're coded

Cons:
- Higher upfront effort
- Spec can drift from implementation if not enforced

**Code-First:**
1. Write the implementation
2. Use annotations/decorators to generate the spec from code
3. Publish the generated spec

Pros:
- Faster initial development
- Spec is always in sync with implementation

Cons:
- Design thinking happens after coding (hard to change)
- Consumers can't work in parallel

**Industry practice:** Most teams use code-first for speed but enforce contract testing (Pact, Dredd) to catch breaking changes.

### OpenAPI/Swagger

OpenAPI 3.x is the industry standard for describing REST APIs. A minimal example:

```yaml
openapi: 3.0.3
info:
  title: User Service API
  version: 1.0.0

paths:
  /users:
    get:
      summary: List users
      parameters:
        - name: role
          in: query
          schema:
            type: string
            enum: [admin, user, readonly]
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserListResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'

  /users/{userId}:
    get:
      summary: Get a user by ID
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '404':
          $ref: '#/components/responses/NotFound'

components:
  schemas:
    User:
      type: object
      required: [id, name, email]
      properties:
        id:
          type: string
        name:
          type: string
        email:
          type: string
          format: email
        createdAt:
          type: string
          format: date-time
```

Use `$ref` to avoid duplicating schema definitions. Keep schemas in `components/schemas` and reuse them.

---

## Backward Compatibility

### Why It Matters

Your API is a public interface. Breaking it silently breaks your clients — mobile apps that can't be force-updated, third-party integrations you don't control, and microservices on their own release cycle.

### Safe (Additive) Changes

These are backward compatible — existing clients continue to work:

```
✅ Adding a new optional field to a response
✅ Adding a new optional query parameter
✅ Adding a new endpoint
✅ Adding a new HTTP method to an existing endpoint
✅ Adding a new value to an enum (in responses)
✅ Relaxing validation rules (accepting more inputs)
✅ Adding new error codes your client doesn't handle yet
```

### Breaking Changes

These will break existing clients:

```
❌ Renaming a field (createdAt → created_at)
❌ Changing a field's type (string → integer)
❌ Removing a field from responses
❌ Making an optional field required
❌ Changing the meaning of a field
❌ Removing an endpoint
❌ Changing authentication mechanism
❌ Adding a new required field to request body
❌ Restricting an enum (removing a value clients might send)
❌ Changing HTTP status code semantics
```

### Deprecation Strategy

1. **Announce deprecation** with a `Deprecation` header and a sunset date
2. **Keep the old behavior** running during the deprecation window (minimum 6–12 months for public APIs)
3. **Log usage** of deprecated endpoints to know when it's safe to remove
4. **Communicate** via changelog, email, dashboard warnings

```
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 01 Jan 2027 00:00:00 GMT
Link: <https://api.example.com/v2/users>; rel="successor-version"
```

The `Sunset` header (RFC 8594) tells clients the exact date after which the endpoint will be gone.

### Versioning to Handle Breaking Changes

When a breaking change is unavoidable, version your API. Don't break existing contracts — create a new version. See Part 2.2 for full versioning strategies.

---

## HATEOAS

### What Is HATEOAS?

Hypermedia As The Engine Of Application State. The idea: every response includes links to related actions, so clients don't need to hardcode URLs or know the API structure in advance.

```json
{
  "data": {
    "id": "order-789",
    "status": "pending",
    "total": 99.99
  },
  "_links": {
    "self": { "href": "/orders/789" },
    "cancel": { "href": "/orders/789/cancel", "method": "POST" },
    "payment": { "href": "/orders/789/payment", "method": "POST" },
    "customer": { "href": "/users/123" }
  }
}
```

The client follows links rather than constructing URLs. The server controls navigation.

### When HATEOAS Is Practical

- APIs consumed by generic clients (crawlers, API explorers)
- Workflow APIs where available actions change based on state (e.g., a payment that can only be refunded when in "completed" state)
- APIs used by clients you don't control and can't update

### When to Skip HATEOAS

Most production REST APIs skip full HATEOAS and here's why:

1. **Clients ignore it in practice.** Mobile and web clients hardcode URLs anyway because it's simpler and more performant.
2. **Documentation is better.** Clients read OpenAPI docs, not response links.
3. **Payload bloat.** Adding `_links` to every response increases payload size.
4. **Complexity overhead.** Link generation logic clutters response serialization.

**Pragmatic middle ground:** Return only the most actionable links (next/prev for pagination, related resources). Don't add links for every possible operation.

---

## Content Negotiation

### How It Works

The client tells the server what formats it can accept. The server picks the best match.

```
Client → Server:
GET /users/123
Accept: application/json, application/xml;q=0.8, text/html;q=0.5

Server → Client:
HTTP/1.1 200 OK
Content-Type: application/json
```

`q` values (quality factors) indicate preference (1.0 is highest, 0 is "not acceptable"). The server picks the highest quality format it supports.

### Content-Type for Requests

The `Content-Type` header tells the server the format of the request body:

```
POST /users
Content-Type: application/json
Body: {"name": "Priya"}

POST /upload
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary
Body: <binary file data>
```

### Common Content Types

```
application/json                    ← JSON (most REST APIs)
application/x-www-form-urlencoded   ← HTML form submission
multipart/form-data                 ← File uploads
application/xml                     ← XML
text/plain                          ← Plain text
application/octet-stream            ← Binary data
application/vnd.api+json            ← JSON:API spec
application/problem+json            ← RFC 7807 error responses
```

### Versioning via Content-Type (Vendor MIME Types)

```
Accept: application/vnd.mycompany.api.v2+json
Content-Type: application/vnd.mycompany.api.v2+json
```

This is the "header versioning" approach. See Part 2.2 for full comparison.

---

## Null vs Absent Fields

This distinction is subtle but important. There are three distinct states:

```json
{ "nickname": "PK" }     ← Field present, has value
{ "nickname": null }     ← Field present, explicitly null (user cleared it)
{}                       ← Field absent (server doesn't know / not applicable)
```

### When to Use Each

**Absent field:** The field doesn't apply to this resource, or the client didn't ask for it (sparse fieldsets). Example: a guest checkout order has no `userId` field (not null, just not applicable).

**Null value:** The field applies but has been explicitly cleared. Example: a user had a nickname, then removed it. `"nickname": null` means "this used to have a value and was explicitly removed."

**Practical rule for responses:**
- Return `null` for optional fields that were set and then cleared
- Omit fields entirely when they are not applicable to the resource type
- Be consistent — never return a field sometimes and omit it other times for the same resource type

**For PATCH requests:**
- In JSON Merge Patch (RFC 7396): sending `null` means "delete this field"
- In JSON Patch (RFC 6902): use the `remove` operation explicitly

```json
// JSON Merge Patch: null removes the field
PATCH /users/123
{ "nickname": null }   ← removes nickname

// JSON Patch: explicit remove
PATCH /users/123
[{ "op": "remove", "path": "/nickname" }]
```

---

## Consistent Error Response Format

### Why It Matters

When clients get an error, they need to:
1. Know what went wrong (user error vs server error)
2. Know if/when to retry
3. Show a useful message to the user
4. Correlate the error with server-side logs

### Standard Error Fields

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "User with ID 123 does not exist",
    "details": [],
    "requestId": "req_7f3a9b2c1d4e5f6a",
    "timestamp": "2026-01-15T10:30:00Z",
    "path": "/users/123"
  }
}
```

**Fields explained:**

| Field | Purpose |
|-------|---------|
| `code` | Machine-readable string code for programmatic handling |
| `message` | Human-readable description of what went wrong |
| `details` | Array of field-level errors for validation failures |
| `requestId` | Unique ID for this request, correlates with server logs |
| `timestamp` | When the error occurred |
| `path` | The URL path that triggered the error |

### Validation Error Details

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "code": "INVALID_FORMAT",
        "message": "Must be a valid email address",
        "value": "not-an-email"
      },
      {
        "field": "age",
        "code": "MIN_VALUE",
        "message": "Must be at least 18",
        "value": 15
      }
    ],
    "requestId": "req_abc123"
  }
}
```

### HTTP Status Code Quick Reference

```
2xx — Success
  200 OK              → Standard success (GET, PUT, PATCH)
  201 Created         → Resource created (POST)
  202 Accepted        → Async operation started
  204 No Content      → Success, no body (DELETE, some PUT/PATCH)

3xx — Redirection
  301 Moved Permanently → URL permanently changed
  304 Not Modified      → Cache hit (ETag/Last-Modified)
  307 Temporary Redirect → Temporary, preserve method
  308 Permanent Redirect → Permanent, preserve method

4xx — Client Errors
  400 Bad Request       → Malformed request syntax
  401 Unauthorized      → Not authenticated (misleading name)
  403 Forbidden         → Authenticated but not authorized
  404 Not Found         → Resource doesn't exist
  405 Method Not Allowed → HTTP method not supported
  408 Request Timeout   → Client was too slow
  409 Conflict          → State conflict (duplicate, optimistic lock)
  410 Gone              → Resource existed but was permanently deleted
  422 Unprocessable Entity → Syntactically valid but semantically wrong
  429 Too Many Requests → Rate limit exceeded

5xx — Server Errors
  500 Internal Server Error → Unexpected server failure
  502 Bad Gateway           → Upstream server error
  503 Service Unavailable   → Server overloaded or down for maintenance
  504 Gateway Timeout       → Upstream server timed out
```

---

## API Design Anti-Patterns

### 1. Chatty APIs

A chatty API requires many requests to accomplish one user action.

```
BAD: To render a user profile page, the client makes:
  GET /user/123           → basic info
  GET /user/123/followers → follower count
  GET /user/123/posts     → recent posts
  GET /user/123/badges    → achievements
  = 4 round trips, 4x latency, 4x connection overhead

GOOD: One endpoint returns everything needed for the page
  GET /users/123/profile  → all profile data in one response
  or use GraphQL for flexible field selection
```

**Fix:** Design endpoints around client use cases, not resource granularity. Use compound documents or sparse fieldsets.

### 2. God Endpoints

The opposite problem — one endpoint does too much.

```
BAD:
POST /api/process
{
  "action": "createUser",    // or "updateUser", or "deleteUser"
  "data": {...}
}
```

This is RPC disguised as REST. It breaks caching, makes logging opaque, and violates the principle of least surprise.

### 3. RPC-Style URLs

```
BAD:
POST /api/getUserData
POST /api/updateUserProfile
POST /api/deleteUserAccount
POST /api/sendPasswordResetEmail
GET  /api/fetchAllOrders
```

**Fix:** Use nouns and let HTTP methods carry the action:
```
GET    /users/{id}
PUT    /users/{id}
DELETE /users/{id}
POST   /users/{id}/password-reset
GET    /orders
```

### 4. Inconsistent Naming

```
BAD (mixed conventions in same API):
GET /users        → returns { userId, userName, createdAt }
GET /orders       → returns { order_id, order_date, user_id }
GET /products     → returns { ProductID, ProductName, CreatedDate }
```

**Fix:** Enforce a naming convention at the serialization layer, not by hand.

### 5. Leaking Implementation Details

```
BAD:
GET /users/123
Response: {
  "mysql_row_id": 123,
  "db_created_timestamp": 1705312200,
  "internal_status_code": 4,  ← what does 4 mean?
  "raw_password_hash": "..."  ← NEVER
}
```

Your API is a public interface. Internal identifiers, database column names, implementation status codes, and sensitive data should never appear in responses.

### 6. Ignoring HTTP Caching

```
BAD:
GET /users/123
(No Cache-Control header, no ETag, no Last-Modified)

GOOD:
GET /users/123
Cache-Control: max-age=60, must-revalidate
ETag: "abc123def456"
Last-Modified: Wed, 15 Jan 2026 10:30:00 GMT
```

Without cache headers, clients and CDNs can't cache your responses, increasing load on your servers.

---

## Implementation Examples

### Go + Chi Router

```go
package main

import (
    "context"
    "encoding/json"
    "errors"
    "net/http"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"
    "github.com/google/uuid"
    "github.com/redis/go-redis/v9"
)

// ─── Response Envelope ───────────────────────────────────────────────────────

type Response struct {
    Data  any       `json:"data,omitempty"`
    Error *APIError `json:"error,omitempty"`
    Meta  *Meta     `json:"meta,omitempty"`
}

type Meta struct {
    RequestID string `json:"requestId"`
    Total     *int   `json:"total,omitempty"`
    Page      *int   `json:"page,omitempty"`
    PerPage   *int   `json:"perPage,omitempty"`
}

type APIError struct {
    Code      string        `json:"code"`
    Message   string        `json:"message"`
    Details   []FieldError  `json:"details,omitempty"`
    RequestID string        `json:"requestId"`
    Timestamp time.Time     `json:"timestamp"`
    Path      string        `json:"path"`
}

type FieldError struct {
    Field   string `json:"field"`
    Code    string `json:"code"`
    Message string `json:"message"`
}

// Helper to write JSON responses
func writeJSON(w http.ResponseWriter, status int, payload any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(payload)
}

func writeSuccess(w http.ResponseWriter, r *http.Request, status int, data any) {
    writeJSON(w, status, Response{
        Data: data,
        Meta: &Meta{RequestID: requestID(r)},
    })
}

func writeError(w http.ResponseWriter, r *http.Request, status int, code, message string, details ...FieldError) {
    writeJSON(w, status, Response{
        Error: &APIError{
            Code:      code,
            Message:   message,
            Details:   details,
            RequestID: requestID(r),
            Timestamp: time.Now().UTC(),
            Path:      r.URL.Path,
        },
    })
}

func requestID(r *http.Request) string {
    id, _ := r.Context().Value(middleware.RequestIDKey).(string)
    return id
}

// ─── Idempotency Key Middleware ───────────────────────────────────────────────

type idempotencyStore struct {
    redis *redis.Client
}

type cachedResponse struct {
    Status int    `json:"status"`
    Body   []byte `json:"body"`
}

func (s *idempotencyStore) Middleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Only apply to state-mutating methods
        if r.Method == http.MethodGet || r.Method == http.MethodHead {
            next.ServeHTTP(w, r)
            return
        }

        key := r.Header.Get("Idempotency-Key")
        if key == "" {
            next.ServeHTTP(w, r)
            return
        }

        ctx := r.Context()
        redisKey := "idempotency:" + key

        // Check if we have a cached response
        val, err := s.redis.Get(ctx, redisKey).Bytes()
        if err == nil {
            // Cache hit — return the cached response
            var cached cachedResponse
            if json.Unmarshal(val, &cached) == nil {
                w.Header().Set("Content-Type", "application/json")
                w.Header().Set("Idempotent-Replayed", "true")
                w.WriteHeader(cached.Status)
                w.Write(cached.Body)
                return
            }
        }

        // Acquire a lock to prevent concurrent processing of the same key
        lockKey := "idempotency:lock:" + key
        set, err := s.redis.SetNX(ctx, lockKey, "1", 30*time.Second).Result()
        if err != nil || !set {
            writeJSON(w, http.StatusConflict, Response{
                Error: &APIError{
                    Code:    "IDEMPOTENCY_CONFLICT",
                    Message: "Another request with this idempotency key is in progress",
                },
            })
            return
        }
        defer s.redis.Del(ctx, lockKey)

        // Intercept the response writer
        rec := &responseRecorder{ResponseWriter: w, status: 200}
        next.ServeHTTP(rec, r)

        // Cache the response
        cached := cachedResponse{Status: rec.status, Body: rec.body}
        if data, err := json.Marshal(cached); err == nil {
            s.redis.Set(ctx, redisKey, data, 24*time.Hour)
        }
    })
}

type responseRecorder struct {
    http.ResponseWriter
    status int
    body   []byte
}

func (r *responseRecorder) WriteHeader(status int) {
    r.status = status
    r.ResponseWriter.WriteHeader(status)
}

func (r *responseRecorder) Write(b []byte) (int, error) {
    r.body = append(r.body, b...)
    return r.ResponseWriter.Write(b)
}

// ─── User Handlers ────────────────────────────────────────────────────────────

type User struct {
    ID        string    `json:"id"`
    Name      string    `json:"name"`
    Email     string    `json:"email"`
    CreatedAt time.Time `json:"createdAt"`
}

type CreateUserRequest struct {
    Name  string `json:"name"`
    Email string `json:"email"`
}

func (req *CreateUserRequest) Validate() []FieldError {
    var errs []FieldError
    if req.Name == "" {
        errs = append(errs, FieldError{Field: "name", Code: "REQUIRED", Message: "Name is required"})
    }
    if req.Email == "" {
        errs = append(errs, FieldError{Field: "email", Code: "REQUIRED", Message: "Email is required"})
    }
    return errs
}

func createUserHandler(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        writeError(w, r, http.StatusBadRequest, "INVALID_JSON", "Request body is not valid JSON")
        return
    }

    if errs := req.Validate(); len(errs) > 0 {
        writeError(w, r, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Request validation failed", errs...)
        return
    }

    user := User{
        ID:        uuid.New().String(),
        Name:      req.Name,
        Email:     req.Email,
        CreatedAt: time.Now().UTC(),
    }

    w.Header().Set("Location", "/users/"+user.ID)
    writeSuccess(w, r, http.StatusCreated, user)
}

func getUserHandler(w http.ResponseWriter, r *http.Request) {
    userID := chi.URLParam(r, "userID")
    // Simulate DB lookup
    if userID == "999" {
        writeError(w, r, http.StatusNotFound, "RESOURCE_NOT_FOUND",
            "User with ID "+userID+" does not exist")
        return
    }

    user := User{
        ID:        userID,
        Name:      "Priya Kumar",
        Email:     "priya@example.com",
        CreatedAt: time.Now().UTC(),
    }
    writeSuccess(w, r, http.StatusOK, user)
}

// ─── Router Setup ─────────────────────────────────────────────────────────────

func NewRouter(rdb *redis.Client) http.Handler {
    r := chi.NewRouter()
    r.Use(middleware.RequestID)
    r.Use(middleware.Logger)
    r.Use(middleware.Recoverer)

    idempStore := &idempotencyStore{redis: rdb}
    r.Use(idempStore.Middleware)

    r.Route("/v1", func(r chi.Router) {
        r.Route("/users", func(r chi.Router) {
            r.Get("/", listUsersHandler)
            r.Post("/", createUserHandler)
            r.Route("/{userID}", func(r chi.Router) {
                r.Get("/", getUserHandler)
                r.Put("/", replaceUserHandler)
                r.Patch("/", updateUserHandler)
                r.Delete("/", deleteUserHandler)
                r.Route("/orders", func(r chi.Router) {
                    r.Get("/", getUserOrdersHandler)
                })
            })
        })
    })

    return r
}

// Stub handlers
func listUsersHandler(w http.ResponseWriter, r *http.Request)      {}
func replaceUserHandler(w http.ResponseWriter, r *http.Request)    {}
func updateUserHandler(w http.ResponseWriter, r *http.Request)     {}
func deleteUserHandler(w http.ResponseWriter, r *http.Request)     {}
func getUserOrdersHandler(w http.ResponseWriter, r *http.Request)  {}
```

### Node.js + Express

```javascript
// api-design.js
const express = require('express');
const { v4: uuidv4 } = require('uuid');
const redis = require('redis');

const app = express();
app.use(express.json());

// ─── Request ID Middleware ────────────────────────────────────────────────────

app.use((req, res, next) => {
  req.requestId = req.headers['x-request-id'] || uuidv4();
  res.setHeader('X-Request-ID', req.requestId);
  next();
});

// ─── Response Helpers ─────────────────────────────────────────────────────────

const sendSuccess = (res, req, statusCode, data, meta = {}) => {
  res.status(statusCode).json({
    data,
    meta: {
      requestId: req.requestId,
      ...meta,
    },
  });
};

const sendError = (res, req, statusCode, code, message, details = []) => {
  res.status(statusCode).json({
    error: {
      code,
      message,
      details,
      requestId: req.requestId,
      timestamp: new Date().toISOString(),
      path: req.path,
    },
  });
};

// ─── Idempotency Key Middleware ───────────────────────────────────────────────

const createIdempotencyMiddleware = (redisClient) => {
  return async (req, res, next) => {
    // Only apply to mutating methods
    if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
      return next();
    }

    const key = req.headers['idempotency-key'];
    if (!key) return next();

    const redisKey = `idempotency:${key}`;
    const lockKey = `idempotency:lock:${key}`;

    try {
      // Check for cached response
      const cached = await redisClient.get(redisKey);
      if (cached) {
        const { status, body } = JSON.parse(cached);
        res.setHeader('Idempotent-Replayed', 'true');
        return res.status(status).json(JSON.parse(body));
      }

      // Acquire lock (NX = only set if not exists, EX = TTL in seconds)
      const lockAcquired = await redisClient.set(lockKey, '1', {
        NX: true,
        EX: 30,
      });

      if (!lockAcquired) {
        return sendError(res, req, 409, 'IDEMPOTENCY_CONFLICT',
          'Another request with this idempotency key is in progress');
      }

      // Intercept the response
      const originalJson = res.json.bind(res);
      let capturedStatus = 200;
      let capturedBody = null;

      res.status = function(code) {
        capturedStatus = code;
        return this;
      };

      res.json = function(body) {
        capturedBody = body;
        // Cache the response before sending
        const payload = JSON.stringify({
          status: capturedStatus,
          body: JSON.stringify(body),
        });
        redisClient.set(redisKey, payload, { EX: 86400 }); // 24h TTL
        redisClient.del(lockKey);
        return originalJson(body);
      };

      next();
    } catch (err) {
      console.error('Idempotency middleware error:', err);
      next(); // Fail open — let the request proceed
    }
  };
};

// ─── Validation ───────────────────────────────────────────────────────────────

const validateCreateUser = (body) => {
  const errors = [];
  if (!body.name || body.name.trim() === '') {
    errors.push({ field: 'name', code: 'REQUIRED', message: 'Name is required' });
  }
  if (!body.email) {
    errors.push({ field: 'email', code: 'REQUIRED', message: 'Email is required' });
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email)) {
    errors.push({ field: 'email', code: 'INVALID_FORMAT', message: 'Must be a valid email address' });
  }
  return errors;
};

// ─── Route Handlers ───────────────────────────────────────────────────────────

const router = express.Router();

// GET /v1/users
router.get('/users', async (req, res) => {
  const users = [
    { id: '1', name: 'Alice', email: 'alice@example.com', createdAt: new Date().toISOString() },
    { id: '2', name: 'Bob', email: 'bob@example.com', createdAt: new Date().toISOString() },
  ];
  sendSuccess(res, req, 200, users, { total: 2, page: 1, perPage: 20 });
});

// POST /v1/users
router.post('/users', async (req, res) => {
  const errors = validateCreateUser(req.body);
  if (errors.length > 0) {
    return sendError(res, req, 422, 'VALIDATION_ERROR', 'Request validation failed', errors);
  }

  const user = {
    id: uuidv4(),
    name: req.body.name.trim(),
    email: req.body.email.toLowerCase(),
    createdAt: new Date().toISOString(),
  };

  res.setHeader('Location', `/v1/users/${user.id}`);
  sendSuccess(res, req, 201, user);
});

// GET /v1/users/:userId
router.get('/users/:userId', async (req, res) => {
  const { userId } = req.params;

  // Simulate "not found"
  if (userId === '999') {
    return sendError(res, req, 404, 'RESOURCE_NOT_FOUND',
      `User with ID ${userId} does not exist`);
  }

  const user = {
    id: userId,
    name: 'Priya Kumar',
    email: 'priya@example.com',
    createdAt: new Date().toISOString(),
  };
  sendSuccess(res, req, 200, user);
});

// PATCH /v1/users/:userId
router.patch('/users/:userId', async (req, res) => {
  const { userId } = req.params;
  const allowedFields = ['name', 'email'];
  const updates = {};

  for (const field of allowedFields) {
    if (field in req.body) {
      updates[field] = req.body[field];
    }
  }

  if (Object.keys(updates).length === 0) {
    return sendError(res, req, 400, 'NO_FIELDS', 'No valid fields provided for update');
  }

  const updated = { id: userId, ...updates, updatedAt: new Date().toISOString() };
  sendSuccess(res, req, 200, updated);
});

// DELETE /v1/users/:userId
router.delete('/users/:userId', async (req, res) => {
  const { userId } = req.params;
  // Idempotent: return 204 whether or not user existed
  res.status(204).send();
});

// ─── Nested resource: GET /v1/users/:userId/orders ──────────────────────────

router.get('/users/:userId/orders', async (req, res) => {
  const { userId } = req.params;
  const orders = [
    { id: 'ord-1', userId, total: 99.99, status: 'completed' },
  ];
  sendSuccess(res, req, 200, orders, { total: 1 });
});

// ─── Global Error Handler ────────────────────────────────────────────────────

app.use((err, req, res, next) => {
  console.error({ requestId: req.requestId, error: err });
  if (err.type === 'entity.parse.failed') {
    return sendError(res, req, 400, 'INVALID_JSON', 'Request body is not valid JSON');
  }
  sendError(res, req, 500, 'INTERNAL_ERROR', 'An unexpected error occurred');
});

app.use('/v1', router);
module.exports = app;
```

### Python + FastAPI

```python
# api_design.py
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator

app = FastAPI(title="User Service", version="1.0.0")

DataT = TypeVar("DataT")

# ─── Response Models ──────────────────────────────────────────────────────────

class Meta(BaseModel):
    request_id: str
    total: Optional[int] = None
    page: Optional[int] = None
    per_page: Optional[int] = None


class FieldError(BaseModel):
    field: str
    code: str
    message: str


class APIError(BaseModel):
    code: str
    message: str
    details: list[FieldError] = []
    request_id: str
    timestamp: datetime
    path: str


class SuccessResponse(BaseModel, Generic[DataT]):
    data: DataT
    meta: Optional[Meta] = None


class ErrorResponse(BaseModel):
    error: APIError


# ─── Request ID Middleware ─────────────────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ─── Idempotency Middleware ────────────────────────────────────────────────────

rdb = aioredis.from_url("redis://localhost:6379", decode_responses=True)

@app.middleware("http")
async def idempotency_middleware(request: Request, call_next):
    # Only apply to mutating methods
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    key = request.headers.get("idempotency-key")
    if not key:
        return await call_next(request)

    redis_key = f"idempotency:{key}"
    lock_key = f"idempotency:lock:{key}"

    # Check for cached response
    cached = await rdb.get(redis_key)
    if cached:
        import json
        data = json.loads(cached)
        return JSONResponse(
            content=data["body"],
            status_code=data["status"],
            headers={"Idempotent-Replayed": "true"},
        )

    # Acquire lock
    acquired = await rdb.set(lock_key, "1", nx=True, ex=30)
    if not acquired:
        return JSONResponse(
            content={
                "error": {
                    "code": "IDEMPOTENCY_CONFLICT",
                    "message": "Another request with this idempotency key is in progress",
                }
            },
            status_code=status.HTTP_409_CONFLICT,
        )

    try:
        response = await call_next(request)

        # Read response body and cache it
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk

        import json
        body_str = body_bytes.decode("utf-8")
        payload = json.dumps({"status": response.status_code, "body": json.loads(body_str)})
        await rdb.set(redis_key, payload, ex=86400)  # 24h TTL

        return Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
    finally:
        await rdb.delete(lock_key)


# ─── Request/Response Models ──────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()


class PatchUserRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None


# ─── Helper Functions ─────────────────────────────────────────────────────────

def success_response(request: Request, data: Any, status_code: int = 200, **meta_kwargs):
    return JSONResponse(
        content={
            "data": data,
            "meta": {
                "requestId": request.state.request_id,
                **{k: v for k, v in meta_kwargs.items() if v is not None},
            },
        },
        status_code=status_code,
    )


def error_response(request: Request, status_code: int, code: str, message: str, details=None):
    return JSONResponse(
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "requestId": request.state.request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
            }
        },
        status_code=status_code,
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/v1/users", response_model=SuccessResponse[list[UserResponse]])
async def list_users(request: Request, page: int = 1, per_page: int = 20):
    users = [
        {"id": "1", "name": "Alice", "email": "alice@example.com",
         "createdAt": datetime.now(timezone.utc).isoformat()},
    ]
    return success_response(request, users, total=len(users), page=page, perPage=per_page)


@app.post("/v1/users", status_code=status.HTTP_201_CREATED)
async def create_user(request: Request, response: Response, body: CreateUserRequest):
    user = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "email": body.email,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    response.headers["Location"] = f"/v1/users/{user['id']}"
    return success_response(request, user, 201)


@app.get("/v1/users/{user_id}")
async def get_user(request: Request, user_id: str):
    if user_id == "999":
        return error_response(request, 404, "RESOURCE_NOT_FOUND",
                               f"User with ID {user_id} does not exist")
    user = {
        "id": user_id,
        "name": "Priya Kumar",
        "email": "priya@example.com",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    return success_response(request, user)


@app.patch("/v1/users/{user_id}")
async def patch_user(request: Request, user_id: str, body: PatchUserRequest):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return error_response(request, 400, "NO_FIELDS", "No valid fields provided for update")

    updated = {"id": user_id, **updates, "updatedAt": datetime.now(timezone.utc).isoformat()}
    return success_response(request, updated)


@app.delete("/v1/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    # Idempotent: always return 204
    return None


@app.get("/v1/users/{user_id}/orders")
async def get_user_orders(request: Request, user_id: str):
    orders = [
        {"id": "ord-1", "userId": user_id, "total": 99.99, "status": "completed"},
    ]
    return success_response(request, orders, total=len(orders))


# ─── Global Exception Handler ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return error_response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred")
```

---

## How It Works Internally

### HTTP Method Semantics at the Protocol Level

When your client sends `DELETE /users/123`, the HTTP/1.1 spec (RFC 7231) defines what DELETE means. The **spec** says it should be idempotent. The **server** is responsible for enforcing that semantics. A server could technically do anything when it receives DELETE, but violating the spec breaks clients that assume idempotency.

### How Idempotency Keys Work in Redis

```
Client sends:
  POST /payments
  Idempotency-Key: uuid-abc-123
  Body: { amount: 1000 }

Server checks:
  SETNX idempotency:uuid-abc-123 "processing"   ← atomic: set if not exists
  ↓ returns 1 (set) or 0 (already exists)

If 1 (new key):
  → Process payment
  → SET idempotency:uuid-abc-123 {status:201, body:{...}} EX 86400
  → Return 201

If 0 (existing key):
  → GET idempotency:uuid-abc-123
  → Return the cached response
```

The SETNX operation is atomic. Two concurrent requests with the same key will have exactly one succeed in setting the key. The other gets the cached result.

---

## Common Patterns & Best Practices

1. **Always include a `requestId` in responses.** This is your debug handle. When a user reports "my request failed at 3:47 PM," you need to find it in logs instantly.

2. **Use the `Location` header on 201 Created.** Tell clients exactly where to find the resource they just created.

3. **Return the full updated resource in PUT/PATCH responses.** Don't just return 204 — clients often need the server-computed fields (updatedAt, computed status, etc.).

4. **Standardize error codes as SCREAMING_SNAKE_CASE strings.** Never use numeric error codes — strings are readable in logs and don't require a lookup table.

5. **Use `ETag` and `If-Match` for optimistic concurrency.** Before allowing a PUT/PATCH, check that the client's version matches the server's current version. Prevents lost updates.

6. **Never 200 an error.** Don't return `{ "success": false, "error": "Not found" }` with status 200. Use proper status codes. Monitoring tools and load balancers work on HTTP status codes.

7. **Design for the client, not the database.** Your API should represent business concepts, not database tables. A `/checkout` endpoint might write to 5 tables. That's fine.

---

## Common Pitfalls

- ❌ **WRONG:** `POST /getUser?id=123` — mixing verb in URL with wrong HTTP method
- ✅ **CORRECT:** `GET /users/123`

- ❌ **WRONG:** Returning raw 500 errors: `{ "error": "null pointer dereference at line 47" }`
- ✅ **CORRECT:** `{ "error": { "code": "INTERNAL_ERROR", "message": "An unexpected error occurred", "requestId": "..." } }`

- ❌ **WRONG:** Silently ignoring unknown PATCH fields: `PATCH /users/123 { "hacked_field": "val" }` processed without error
- ✅ **CORRECT:** Whitelist allowed fields; ignore or reject unknown fields

- ❌ **WRONG:** Returning arrays directly: `GET /users → [{"id":1},{"id":2}]`
- ✅ **CORRECT:** Wrap in envelope: `{ "data": [...], "meta": { "total": 2 } }`

- ❌ **WRONG:** Using PUT for partial updates (omitted fields get nulled)
- ✅ **CORRECT:** Use PATCH for partial updates; PUT only for full replacement

- ❌ **WRONG:** Inconsistent status codes: sometimes 200, sometimes 204 for DELETE
- ✅ **CORRECT:** Pick a convention and document it; be 100% consistent

- ❌ **WRONG:** `POST /users` without idempotency → double-clicking "submit" creates two users
- ✅ **CORRECT:** Implement idempotency key middleware + frontend sends a UUID per submit

- ❌ **WRONG:** Returning database column names in responses: `mysql_auto_id`, `db_timestamp`
- ✅ **CORRECT:** Map internal names to clean API field names at the serialization layer

---

## Interview Questions

**Q1. What makes a good API vs a bad one?**

**Answer:** A good API is:
- **Predictable**: follows conventions so developers can guess behavior without reading docs
- **Consistent**: same patterns for naming, error formats, pagination across all endpoints
- **Minimal**: exposes only what clients need, not internal implementation details
- **Evolvable**: designed so future changes don't break existing clients (additive changes only)
- **Documented**: has an OpenAPI spec that's always in sync with implementation
- **Observable**: includes request IDs for debugging, proper status codes for monitoring

A bad API: uses RPC-style URLs, returns 200 for errors, has inconsistent naming, exposes internals, requires reading source code to understand behavior.

---

**Q2. How do you handle backward compatibility when evolving an API?**

**Answer:** The rule is: additive changes are safe, anything else requires a version bump.

Safe changes: adding optional fields, adding new endpoints, adding optional query params, relaxing validation. These don't break existing clients because they ignore fields they don't know about.

Unsafe changes: renaming fields, changing types, removing fields, making optional fields required. These require a new API version.

For graceful evolution:
1. Add `Deprecation` and `Sunset` headers to warn clients
2. Log usage of deprecated endpoints to track adoption
3. Keep old version running until traffic drops to near-zero
4. Provide migration guides in your changelog

Stripe is the gold standard for API backward compatibility — they maintain compatibility for years and never break existing integrations.

---

**Q3. What is idempotency and why does it matter for POST requests?**

**Answer:** An operation is idempotent if executing it N times produces the same result as executing it once. GET, PUT, and DELETE are naturally idempotent. POST is not — `POST /payments` would charge the user every time.

This matters because in distributed systems, requests can fail ambiguously (network timeout, connection reset). You don't know if the server processed the request or not. For idempotent operations, retrying is safe. For non-idempotent operations like POST, retrying can cause double charges, duplicate records, or duplicate emails.

Idempotency keys solve this: the client generates a UUID for each logical operation and sends it in the `Idempotency-Key` header. The server caches the result keyed by this UUID for 24 hours. On retry, the server returns the cached result without reprocessing.

---

**Q4. What is the difference between PUT and PATCH semantically?**

**Answer:** PUT replaces the entire resource. If you PUT a user object and omit the email field, the email is gone. PATCH updates only the fields you send — unmentioned fields remain unchanged.

PUT is always idempotent: sending the same full representation multiple times results in the same state. PATCH's idempotency depends on implementation — a set-based patch (replace name with X) is idempotent, but an increment-based patch (add 1 to balance) is not.

Use PUT when clients always have and send the full representation (configuration files, settings objects). Use PATCH for typical UI "edit" scenarios where users change a subset of fields.

---

**Q5. What are the trade-offs of HATEOAS in practice?**

**Answer:** HATEOAS is theoretically elegant but practically complex.

Pros: Clients don't hardcode URLs, the API is self-describing, and available actions can change based on resource state (e.g., a "cancel" link only appears when an order is cancellable).

Cons: Real clients (mobile apps, SPAs) ignore HATEOAS links in practice — they hardcode URLs anyway because it's simpler. HATEOAS adds payload size, complicates serialization logic, and provides value only to truly generic clients.

Pragmatic approach: Implement pagination links (`next`, `prev`, `first`, `last`) since they're genuinely useful. Implement state-based action links for complex workflows (payment, approval flows). Skip HATEOAS for simple CRUD resources. OpenAPI documentation provides better discoverability for most teams.

---

**Q6. How would you design an API that multiple client types (mobile, web, third-party) consume?**

**Answer:** Key considerations:

1. **Consistent baseline**: Same REST conventions, same error format, same auth mechanism for all clients.
2. **Sparse fieldsets / projections**: Let clients request only the fields they need (`?fields=id,name,email`) to avoid mobile clients downloading unnecessary data.
3. **API Gateway pattern**: Put a gateway in front that handles auth, rate limiting, and can do light response shaping per client type.
4. **Backend-For-Frontend (BFF)**: For very different clients (mobile vs web), consider separate BFF services that aggregate and shape data differently while sharing the same core APIs.
5. **Versioning**: Use URL versioning (`/v1/`, `/v2/`) so different client versions can evolve independently.
6. **Rate limits per client type**: Third-party clients get stricter rate limits than your own mobile app.
7. **Pagination**: Use cursor pagination (not offset) since mobile clients do infinite scroll, not page jumps.

---

**Q7. What should a standard error response include?**

**Answer:** A standard error response should include:

- **HTTP status code**: Correct 4xx/5xx code (not 200 for errors)
- **Machine-readable error code**: String like `RESOURCE_NOT_FOUND`, `VALIDATION_ERROR` for programmatic handling
- **Human-readable message**: Descriptive sentence explaining what went wrong
- **Field-level details**: For validation errors, an array of `{ field, code, message }` objects
- **Request ID**: A unique ID correlating this response with server-side logs — essential for debugging
- **Timestamp**: When the error occurred (ISO 8601)
- **Path**: The URL path that produced the error

What NOT to include: stack traces, internal error codes, database column names, raw exception messages, or anything that leaks implementation details.

---

## Resources

- [RFC 7231 — HTTP/1.1 Semantics and Content](https://tools.ietf.org/html/rfc7231)
- [RFC 5789 — PATCH Method for HTTP](https://tools.ietf.org/html/rfc5789)
- [RFC 7396 — JSON Merge Patch](https://tools.ietf.org/html/rfc7396)
- [RFC 6902 — JSON Patch](https://tools.ietf.org/html/rfc6902)
- [RFC 8594 — The Sunset HTTP Header Field](https://tools.ietf.org/html/rfc8594)
- [Stripe API Design](https://stripe.com/docs/api) — industry gold standard
- [Google API Design Guide](https://cloud.google.com/apis/design)
- [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines)
- [OpenAPI Specification](https://spec.openapis.org/oas/v3.1.0)
- [Zalando RESTful API Guidelines](https://opensource.zalando.com/restful-api-guidelines/)

---

**Next:** [Part 2.2: Versioning, Pagination & Error Handling](./02-versioning-pagination-errors.md)
