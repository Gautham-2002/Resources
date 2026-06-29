# Part 1.1: HTTP Fundamentals

## What You'll Learn
- How HTTP evolved from 1.1 → 2 → 3 and the performance problems each version solved
- Exact semantics, idempotency, and safety of every HTTP method
- Which status code to use in each real-world scenario (and why the wrong ones matter)
- How CORS actually works under the hood, not just "add the header"
- The complete request lifecycle from DNS lookup through TLS handshake to response
- How TLS 1.3 differs from TLS 1.2 and why it matters for latency
- How to implement production-grade headers, CORS, and connection handling in Go, Node.js, and Python

## Table of Contents
1. [HTTP Version Evolution](#http-version-evolution)
2. [HTTP Methods — Semantics, Safety, Idempotency](#http-methods)
3. [Status Codes — Complete Reference](#status-codes)
4. [HTTP Headers Deep Dive](#http-headers)
5. [Request/Response Lifecycle](#requestresponse-lifecycle)
6. [Keep-Alive and Connection Pooling](#keep-alive-and-connection-pooling)
7. [HTTPS and TLS 1.3 Handshake](#https-and-tls-13)
8. [CORS — Cross-Origin Resource Sharing](#cors)
9. [Cookies — Security Flags](#cookies)
10. [Content Negotiation](#content-negotiation)
11. [Implementation Examples](#implementation-examples)
12. [Common Patterns & Best Practices](#common-patterns--best-practices)
13. [Common Pitfalls](#common-pitfalls)
14. [Interview Questions](#interview-questions)
15. [Resources](#resources)

---

## HTTP Version Evolution

HTTP is the application-layer protocol that powers the web. Understanding its evolution is crucial for explaining performance decisions in system design interviews.

### HTTP/1.0 (1996) — One Request Per Connection

Each request opens a new TCP connection. After the response, the connection closes. This means:
- DNS lookup + TCP 3-way handshake + (optionally TLS) per request
- Loading a page with 30 resources = 30 separate TCP handshakes
- High latency, heavy server load

### HTTP/1.1 (1997) — Persistent Connections

Key improvements:
- **Persistent connections** (`Connection: keep-alive` by default): TCP connection reused across multiple requests
- **Pipelining**: Client can send multiple requests without waiting for responses — but servers must respond in order
- **Chunked transfer encoding**: Stream response bodies without knowing content length
- **Host header**: Required, enabling virtual hosting (multiple domains on one IP)

**Problem: Head-of-Line (HoL) Blocking at the HTTP layer**

```
Client          Server
  |--GET /a.js-->|
  |              | (processing)
  |--GET /b.css->|  ← queued, can't be processed out of order
  |              |
  |<--/a.js resp-|
  |<--/b.css rsp-|
```

If `/a.js` takes 500ms to process, `/b.css` waits even if it's ready in 5ms. Browsers work around this by opening 6 parallel TCP connections per domain — a hack, not a solution.

### HTTP/2 (2015, RFC 9113) — Binary Framing and Multiplexing

HTTP/2 rewrites the wire format while keeping the same semantics (methods, status codes, headers still work identically).

**Core changes:**

1. **Binary framing layer**: All communication is split into small binary frames. Text parsing is replaced with binary parsing — faster and less error-prone.

2. **Multiplexing**: Multiple requests/responses interleaved on a **single TCP connection** using stream IDs.

```
Single TCP Connection
┌────────────────────────────────────────────┐
│  Stream 1: [HEADERS] [DATA] [DATA]         │
│  Stream 3: [HEADERS] [DATA]                │  ← Concurrent, no ordering constraint
│  Stream 5: [HEADERS] [DATA] [DATA] [DATA]  │
└────────────────────────────────────────────┘
```

3. **Header compression (HPACK)**: HTTP/1.1 headers repeat on every request (e.g., `Cookie`, `User-Agent` sent every time). HPACK uses a shared compression table + Huffman encoding. Headers are indexed — "send header #62" instead of "send `Content-Type: application/json`" again.

4. **Server push**: Server can push resources to the client cache before the client asks (e.g., push `style.css` when `index.html` is requested). Mostly deprecated in practice due to poor real-world performance.

5. **Stream prioritization**: Clients can hint which streams are more important.

**Remaining problem: TCP Head-of-Line Blocking**

HTTP/2 solves HoL at the *application* layer, but TCP itself has packet-level HoL blocking. If one TCP packet is lost, all streams on that connection stall until retransmission. On lossy networks (mobile, WiFi), HTTP/2 can be *slower* than HTTP/1.1 with multiple connections.

### HTTP/3 (2022, RFC 9114) — QUIC-Based Transport

HTTP/3 replaces TCP with **QUIC** (Quick UDP Internet Connections), a transport protocol built on UDP.

```
HTTP/1.1  →  TCP  →  IP
HTTP/2    →  TCP  →  IP
HTTP/3    →  QUIC (UDP-based)  →  IP
```

**Key QUIC features:**

1. **Independent streams**: Each HTTP/3 stream is independently flow-controlled. A lost UDP packet affects only that stream, not all streams. True application-level multiplexing without transport-level HoL blocking.

2. **0-RTT and 1-RTT handshakes**: QUIC integrates TLS 1.3 into the handshake itself.
   - New connection: 1-RTT (vs TCP 3-way handshake + TLS = 2-3 RTT in HTTP/2)
   - Resumed connection: 0-RTT (data sent with the first packet, using cached session keys)

3. **Connection migration**: QUIC connections are identified by a Connection ID, not by (IP, port) tuple. When a mobile client switches from WiFi to 4G (IP changes), the connection survives — no reconnection needed.

4. **Built-in encryption**: QUIC always encrypts. There is no plaintext QUIC (unlike HTTP/2 which technically allows `h2c` cleartext).

**Version comparison at a glance:**

```
Feature                  HTTP/1.1    HTTP/2      HTTP/3
─────────────────────────────────────────────────────────
Multiplexing             No          Yes         Yes
HoL blocking (app)       Yes         No          No
HoL blocking (transport) No*         Yes (TCP)   No (QUIC)
Header compression       No          HPACK       QPACK
TLS required             No          No (h2c)    Yes
Connection migration     No          No          Yes
0-RTT reconnect          No          No          Yes
Transport                TCP         TCP         QUIC/UDP
```

*HTTP/1.1 opens multiple connections to avoid HoL, so each connection is independent.

---

## HTTP Methods

HTTP defines a set of request methods with specific semantics. Interviewers frequently test whether candidates understand *safety* and *idempotency* — not just "GET fetches, POST creates."

### Safety

A method is **safe** if it does not modify server state. Safe methods can be cached, prefetched, or retried freely by clients and proxies.

Safe: `GET`, `HEAD`, `OPTIONS`  
Unsafe: `POST`, `PUT`, `PATCH`, `DELETE`

### Idempotency

A method is **idempotent** if making the same request multiple times has the same effect as making it once. The *result* of the first call and the Nth call are equivalent from the server's perspective.

| Method  | Safe | Idempotent | Body | Notes                                      |
|---------|------|------------|------|--------------------------------------------|
| GET     | ✓    | ✓          | No*  | Retrieve resource                          |
| HEAD    | ✓    | ✓          | No   | GET without response body                  |
| OPTIONS | ✓    | ✓          | No   | Describe communication options             |
| POST    | ✗    | ✗          | Yes  | Create resource or trigger action          |
| PUT     | ✗    | ✓          | Yes  | Replace resource entirely                  |
| PATCH   | ✗    | ✗**        | Yes  | Partially update resource                  |
| DELETE  | ✗    | ✓          | No*  | Remove resource (idempotent: deleting twice = same result) |

*GET and DELETE can technically carry a body per RFC but most clients/servers ignore it.  
**PATCH can be designed to be idempotent (e.g., `SET price=100`) but isn't required to be.

### GET
Retrieve a representation of a resource. No side effects. Should be cacheable. Never use GET to trigger mutations — some proxies aggressively cache GET responses.

### HEAD
Like GET but the server only sends headers, no body. Use to check if a resource exists, get its `Content-Length`, or validate a cached ETag without downloading the body.

### POST
Send data to a resource for processing. Create subordinate resources (e.g., POST to `/users` creates a user). Not idempotent — POSTing twice may create two records.

### PUT
Replace the **entire** resource at the given URI. If the resource doesn't exist, create it. The request body must contain the complete representation.
```
PUT /users/42
{"name": "Alice", "email": "alice@example.com", "role": "admin"}
```
Omitting `role` from a PUT would overwrite it to null/default. This is the key distinction from PATCH.

### PATCH
Apply a **partial** modification. Only send the fields you want to change.
```
PATCH /users/42
{"email": "newalice@example.com"}
```
PATCH is not inherently idempotent. `PATCH /counter {"increment": 1}` applied twice increments by 2. But `PATCH /user/42 {"status": "active"}` is effectively idempotent. Design matters.

### DELETE
Remove a resource. Idempotent: `DELETE /users/42` returns 200 or 204 the first time. If called again and the resource is gone, return 404 (some argue 204 is acceptable too for strict idempotency).

### OPTIONS
Returns the allowed methods and CORS headers. Browsers send this as a CORS preflight request. Servers should respond with `Allow: GET, POST, OPTIONS` headers.

---

## Status Codes

### 1xx — Informational

**100 Continue**: Server tells client to proceed with sending a large request body (used with `Expect: 100-continue` header). Client sends headers first, waits for 100 before sending body. Saves bandwidth if server would reject anyway (e.g., auth failure).

**101 Switching Protocols**: Server is switching to WebSocket or HTTP/2 upgrade.

### 2xx — Success

**200 OK**: Request succeeded. Response body contains the requested data. Use for GET, POST (when creating and returning the new resource), PUT, PATCH.

**201 Created**: Resource was created successfully. **Must** include a `Location` header pointing to the new resource URI.
```
HTTP/1.1 201 Created
Location: /users/42
Content-Type: application/json

{"id": 42, "name": "Alice"}
```

**202 Accepted**: Request accepted for processing, but processing hasn't completed. Used for async operations — return a job ID.
```
HTTP/1.1 202 Accepted
{"jobId": "abc123", "statusUrl": "/jobs/abc123"}
```

**204 No Content**: Request succeeded, no body to return. Use for DELETE, PUT/PATCH when you don't return the updated resource, or logout. The client should not navigate away from its current page.

**206 Partial Content**: Response to a range request (`Range: bytes=0-1023`). Used for video streaming, download resumption.

### 3xx — Redirection

**301 Moved Permanently**: Resource has moved. Browser caches this indefinitely. Safe to use for permanent URL changes (e.g., HTTP → HTTPS redirect). Use with caution — very hard to undo without cache busting.

**302 Found**: Temporary redirect. Browser does NOT cache. Server might change the destination next time.

**303 See Other**: After POST, redirect to a GET URL. Prevents form resubmission on browser refresh (Post/Redirect/Get pattern).

**304 Not Modified**: Resource hasn't changed since the client's cached version (checked via `ETag`/`If-None-Match` or `Last-Modified`/`If-Modified-Since`). Client uses its cache. No body in response.

**307 Temporary Redirect**: Like 302, but guarantees the original HTTP method is preserved. A POST to `/submit` redirected to `/new-submit` will be a POST (not a GET like 302 might do).

**308 Permanent Redirect**: Like 301, but preserves HTTP method.

### 4xx — Client Errors

**400 Bad Request**: Malformed request syntax, invalid parameters, missing required fields, request body fails validation. Return a descriptive error body.

**401 Unauthorized**: Authentication is required and has not been provided, or credentials are invalid. Despite the name, it means *unauthenticated*. Response must include `WWW-Authenticate` header.

**403 Forbidden**: Authentication succeeded (we know who you are), but you don't have permission for this action. No `WWW-Authenticate` header needed.

```
Key difference:
401 = "Who are you? Show me ID."
403 = "I know who you are. You can't come in."
```

**404 Not Found**: Resource doesn't exist. Also used intentionally to hide the existence of resources (e.g., return 404 instead of 403 to avoid leaking that a resource exists).

**405 Method Not Allowed**: The resource exists but doesn't support this HTTP method. Response must include `Allow: GET, HEAD` header listing supported methods.

**409 Conflict**: Request conflicts with the current state of the resource. Use for:
- Duplicate creation (username already taken)
- Optimistic locking conflicts (version mismatch)
- Trying to delete a resource that has dependent records

**410 Gone**: Resource existed but has been permanently deleted. Unlike 404, it explicitly communicates "this used to exist." Search engines remove links on 410.

**412 Precondition Failed**: Conditional request failed (e.g., `If-Match` ETag doesn't match — someone else modified it first). Critical for optimistic concurrency control.

**422 Unprocessable Entity**: Request is syntactically correct (valid JSON), but semantically invalid (field values fail business logic validation). Preferred over 400 when the structure is right but content is wrong.
```json
{"errors": [{"field": "email", "message": "Email domain is blacklisted"}]}
```

**429 Too Many Requests**: Rate limit exceeded. Must include `Retry-After` header.
```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1719654000
```

### 5xx — Server Errors

**500 Internal Server Error**: Generic catch-all for unexpected server failures. Log the full error internally; return minimal details to clients (avoid leaking stack traces).

**501 Not Implemented**: Server doesn't support the functionality required. Rarely used.

**502 Bad Gateway**: The server acting as a gateway (e.g., nginx, load balancer) received an invalid response from an upstream server. Common when a backend service crashes or returns garbage.

**503 Service Unavailable**: Server is temporarily unable to handle requests (overloaded or down for maintenance). Include `Retry-After` header. Load balancers remove servers returning 503 from the rotation.

**504 Gateway Timeout**: Gateway did not receive a response from the upstream server in time. Common in microservices when a downstream service is slow.

```
502 = upstream returned a bad response (server replied, but nonsense)
503 = server is refusing requests (overloaded/maintenance)
504 = upstream didn't respond in time (timeout)
```

---

## HTTP Headers Deep Dive

### Authentication Headers

**Authorization**: Carries credentials.
```
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...   (JWT / OAuth 2.0)
Authorization: Basic dXNlcjpwYXNz              (Base64 user:pass — only over HTTPS)
Authorization: Digest ...                       (Challenge-response, rarely used now)
```

**WWW-Authenticate**: Sent with 401 responses, tells client what auth scheme to use.
```
WWW-Authenticate: Bearer realm="api", error="invalid_token"
```

### Content Headers

**Content-Type**: Media type of the request/response body. Server should return 415 Unsupported Media Type if it can't handle the client's Content-Type.
```
Content-Type: application/json; charset=utf-8
Content-Type: multipart/form-data; boundary=----FormBoundary7MA4YWxk
Content-Type: application/x-www-form-urlencoded
```

**Content-Length**: Exact body size in bytes. Required for non-chunked responses. Allows clients to show progress bars and validate complete receipt.

**Content-Encoding**: How the body is encoded (compressed).
```
Content-Encoding: gzip
Content-Encoding: br        (Brotli — better compression than gzip, modern browsers support it)
```

**Transfer-Encoding: chunked**: Body sent in chunks, each prefixed with its hex size. Used when total length is unknown at response start (e.g., server-sent events, large generated responses).

**Accept**: What media types the client can handle.
```
Accept: application/json, text/html;q=0.9, */*;q=0.8
```
`q` values are quality factors (0-1). Server uses this for content negotiation.

### Caching Headers

**Cache-Control**: The primary caching directive.
```
Cache-Control: no-store               # Never cache (sensitive data)
Cache-Control: no-cache               # Must revalidate with server before using cache
Cache-Control: private, max-age=3600  # Browser cache only, 1 hour
Cache-Control: public, max-age=86400, s-maxage=3600  # CDN caches for 1h, browser for 24h
Cache-Control: immutable              # Content will never change (use with content-hashed URLs)
```

**ETag**: A version identifier for a resource (typically a hash of the content).
```
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
ETag: W/"weak-etag"   (W/ prefix = weak ETag, semantic equivalence, not byte-for-byte)
```

**If-None-Match**: Client sends its cached ETag; server returns 304 if resource hasn't changed.
```
If-None-Match: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

**If-Match**: Optimistic concurrency control. Server returns 412 if ETag doesn't match (resource was modified since last fetch).
```
If-Match: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

**Last-Modified / If-Modified-Since**: Alternative to ETag using timestamps. Less precise (1-second resolution), ETag preferred.

**Vary**: Tells caches which request headers affect the response, so different versions are cached separately.
```
Vary: Accept-Encoding    # Cache separate gzip and non-gzip versions
Vary: Accept-Language    # Cache per language
Vary: Authorization      # Don't share cache between users (be careful with this)
```

### Request Tracking Headers

**X-Request-ID** / **X-Correlation-ID**: A unique identifier for this request, used to correlate logs across distributed systems. Generate if absent, propagate downstream.
```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

**X-Forwarded-For**: The original client IP when behind a proxy/load balancer.
```
X-Forwarded-For: 203.0.113.195, 70.41.3.18, 150.172.238.178
```
The leftmost IP is the original client (but can be spoofed). Use `X-Real-IP` or trust only specific proxy hops.

### Rate Limiting Headers (IETF Draft)
```
RateLimit-Limit: 100          # Max requests per window
RateLimit-Remaining: 87       # Requests remaining in current window
RateLimit-Reset: 1719654000   # Unix timestamp when window resets
Retry-After: 60               # Seconds to wait (with 429 or 503)
```

### CORS Headers (covered in detail in CORS section)
```
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
Access-Control-Expose-Headers: X-Request-ID
Access-Control-Allow-Credentials: true
```

---

## Request/Response Lifecycle

What actually happens when you type `https://api.example.com/users` in a browser or make an API call?

```
Browser/Client
     │
     │  1. URL Parsing
     │     Protocol: https, Host: api.example.com, Path: /users
     │
     │  2. DNS Resolution
     │     OS checks /etc/hosts → local DNS cache → recursive resolver
     │     → root nameserver → TLD (.com) nameserver → authoritative NS
     │     → returns: 203.0.113.1
     │     (TTL cached locally for next requests)
     │
     │  3. TCP Connection (3-way handshake)
     │     Client → SYN → Server
     │     Client ← SYN-ACK ← Server
     │     Client → ACK → Server
     │     (1 RTT, typically ~50-150ms cross-region)
     │
     │  4. TLS Handshake (TLS 1.3 — 1 RTT)
     │     Client → ClientHello (TLS version, cipher suites, key_share) → Server
     │     Client ← ServerHello + EncryptedExtensions + Certificate
     │               + CertificateVerify + Finished ← Server
     │     Client → Finished → Server
     │     (Both sides now have symmetric session keys)
     │
     │  5. HTTP Request
     │     GET /users HTTP/2
     │     Host: api.example.com
     │     Authorization: Bearer eyJ...
     │     Accept: application/json
     │
     │  6. Server Processing
     │     Load Balancer → App Server → Middleware → Handler → DB/Cache
     │
     │  7. HTTP Response
     │     HTTP/2 200 OK
     │     Content-Type: application/json
     │     Cache-Control: private, max-age=60
     │     [body]
     │
     │  8. Connection: keep-alive (HTTP/1.1) or persistent (HTTP/2)
     │     Connection reused for subsequent requests
     ▼
  Done
```

### DNS Caching Layers
1. Browser DNS cache (chrome://net-internals/#dns)
2. OS DNS cache (nscd, systemd-resolved)
3. Resolving DNS server (ISP or 8.8.8.8)
4. Root / TLD nameservers (rarely hit due to caching)

A TTL of 300s means DNS result is valid for 5 minutes. Very low TTLs (30s) are used for fast failover but increase DNS load. Cloud providers like AWS Route 53 use TTL=60 for health-check-based routing.

### TCP 3-Way Handshake
```
Client                        Server
  |-------SYN (seq=x)--------->|
  |<------SYN-ACK (seq=y,ack=x+1)--|
  |-------ACK (ack=y+1)------->|
  |  (connection established)  |
```
Cost: 1 RTT before any data is sent. This is why connection reuse (keep-alive) and QUIC's 0-RTT are significant.

---

## Keep-Alive and Connection Pooling

### HTTP Keep-Alive (Persistent Connections)

HTTP/1.1 defaults to `Connection: keep-alive`. The TCP connection stays open after the response for reuse.

```
Without keep-alive:     With keep-alive:
Req1: TCP open           Req1: TCP open
Req1: HTTP req/res       Req1: HTTP req/res
Req1: TCP close          Req2: HTTP req/res  ← reuses same TCP
Req2: TCP open           Req3: HTTP req/res  ← still same TCP
Req2: HTTP req/res       ... TCP close (after timeout or max requests)
Req2: TCP close
```

Configure on server side:
- `Keep-Alive: timeout=75, max=1000` — close connection after 75s of inactivity or 1000 requests

### Connection Pooling (Client-Side)

When a service makes many outgoing HTTP requests (e.g., calling a microservice), maintaining a pool of pre-established TCP/TLS connections eliminates per-request handshake overhead.

```
Service A (pool size: 10)
├── Conn 1 ──→ Service B
├── Conn 2 ──→ Service B  (all pre-warmed)
├── Conn 3 ──→ Service B
...
└── Conn 10 ──→ Service B

Request arrives → grab idle conn from pool → send → return to pool
```

**Sizing connection pools**: Too small = requests queue. Too large = port exhaustion or overwhelming downstream. Rule of thumb: `pool_size = (avg_latency_ms / 1000) * requests_per_second * safety_factor`.

**In Go**: `http.Transport` has `MaxIdleConns`, `MaxIdleConnsPerHost`, `IdleConnTimeout` — always configure these for production.

**In Node.js**: `http.globalAgent` has `maxSockets` (default: `Infinity`). For production, use `agentkeepalive` package or configure `undici` pool.

---

## HTTPS and TLS 1.3

### Why TLS 1.2 Was Slow

TLS 1.2 required a 2-RTT handshake before application data could flow:
```
Client            Server
  |--ClientHello-->|
  |<-ServerHello---|
  |<-Certificate---|
  |<-ServerHelloDone|
  |--ClientKeyEx-->|
  |--ChangeCipher->|
  |--Finished----->|
  |<--ChangeCipher-|
  |<--Finished-----|
  |---HTTP GET---->|  ← application data only starts here (2 RTT after TCP)
```

### TLS 1.3 (RFC 8446) — 1-RTT Handshake

TLS 1.3 removed weak cipher suites, simplified the handshake, and reduced it to 1 RTT:

```
Client                              Server
  |--ClientHello                    |
  |  (supported versions, ciphers,  |
  |   key_share: ECDH public key)-->|
  |                                 | (derives session keys immediately)
  |<--ServerHello                   |
  |   EncryptedExtensions           |
  |   Certificate                   |
  |   CertificateVerify             |
  |   Finished                      |
  |   (all encrypted) --------------|
  |--Finished---------------------->|
  |--HTTP GET (encrypted)---------->|  ← 1 RTT after TCP, not 2
```

**0-RTT Resumption**: For resumed sessions (session ticket from prior connection), the client can send application data in the very first packet. The server processes it before the handshake completes. 

Security tradeoff: 0-RTT data is vulnerable to replay attacks. Never use 0-RTT for non-idempotent requests (POST, payments). Only use for safe, idempotent GET requests.

### Certificate Validation Chain

```
Root CA (e.g., DigiCert Global Root)
  └── Intermediate CA (e.g., DigiCert TLS RSA SHA256 2020 CA1)
       └── Your certificate (api.example.com)
```

Browsers/clients trust a set of root CAs baked into the OS/browser. Your server presents the full chain (leaf + intermediate). Clients verify each signature up to a trusted root.

**HSTS (HTTP Strict Transport Security)**: Forces browsers to always use HTTPS, even for the first request.
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```
Once set, the browser won't even attempt HTTP — it converts the URL to HTTPS client-side. Submit to Chrome's HSTS preload list for max security.

---

## CORS

### Why CORS Exists

Browsers enforce the **Same-Origin Policy (SOP)**: JavaScript running on `https://app.example.com` cannot read responses from `https://api.other.com`. This prevents malicious websites from stealing data using the user's cookies.

An **origin** = scheme + host + port: `https://example.com:443`

CORS (Cross-Origin Resource Sharing) is the mechanism that lets servers *opt-in* to allowing cross-origin requests from specific origins.

**CORS is a browser mechanism only.** Direct API calls from curl, Postman, or server-to-server calls are NOT subject to CORS. It's enforced by the browser, not the server.

### Simple Requests vs Preflight

**Simple requests** don't trigger a preflight. Conditions:
- Method: GET, HEAD, or POST
- Only safe headers: `Accept`, `Accept-Language`, `Content-Language`, `Content-Type` (limited to `application/x-www-form-urlencoded`, `multipart/form-data`, `text/plain`)

Even for simple requests, the browser checks `Access-Control-Allow-Origin` before exposing the response to JavaScript.

**Preflight requests** are triggered when:
- Method is PUT, DELETE, PATCH, or OPTIONS
- Custom headers are included (e.g., `Authorization`, `X-Request-ID`)
- `Content-Type: application/json` (not in the safe list!)

Essentially, any real API call from a browser triggers a preflight.

### The CORS Preflight Flow

```
Browser (app.frontend.com)                   API Server (api.backend.com)
          |                                           |
          |--OPTIONS /users-------------------------->|
          |  Origin: https://app.frontend.com         |
          |  Access-Control-Request-Method: POST       |
          |  Access-Control-Request-Headers: Authorization, Content-Type
          |                                           |
          |<--200 OK-----------------------------------|
          |  Access-Control-Allow-Origin: https://app.frontend.com
          |  Access-Control-Allow-Methods: GET, POST, DELETE
          |  Access-Control-Allow-Headers: Authorization, Content-Type
          |  Access-Control-Max-Age: 86400            |
          |  (browser caches this for 86400 seconds)  |
          |                                           |
          |  ↑ If this fails, actual request blocked  |
          |                                           |
          |--POST /users------------------------------>|
          |  Origin: https://app.frontend.com         |
          |  Authorization: Bearer eyJ...             |
          |  Content-Type: application/json           |
          |                                           |
          |<--201 Created------------------------------|
          |  Access-Control-Allow-Origin: https://app.frontend.com
          |  (browser allows JS to read this response)|
```

**Access-Control-Max-Age**: How long the browser caches the preflight result. Set to 86400 (24h) for production. Chrome caps at 2h, Firefox at 24h, Safari at 5 minutes.

**Access-Control-Allow-Credentials**: Required if you're sending cookies or Authorization headers with credentials. Cannot use `*` for `Allow-Origin` when this is `true` — must specify exact origin.

**Access-Control-Expose-Headers**: Which response headers JavaScript is allowed to read. By default, only `Cache-Control`, `Content-Language`, `Content-Length`, `Content-Type`, `Expires`, `Last-Modified`, `Pragma` are accessible.

### CORS Security Mistakes

```
❌ Access-Control-Allow-Origin: *     with credentials: true
   → Browsers reject this combination. Must specify exact origin.

❌ Reflecting Origin header blindly:
   Access-Control-Allow-Origin: $request_origin   (without validating it)
   → Any origin can access your API, defeating the purpose.

✅ Maintain an allowlist:
   const allowed = new Set(["https://app.example.com", "https://admin.example.com"])
   if (allowed.has(requestOrigin)) respond with that origin
```

---

## Cookies

Cookies are sent by the server in a `Set-Cookie` response header and echoed back by the browser in every subsequent request to the same domain.

### Cookie Security Flags

**HttpOnly**: Cookie cannot be accessed via JavaScript (`document.cookie`). Prevents XSS attacks from stealing session tokens. **Always set on session cookies.**

**Secure**: Cookie only sent over HTTPS. Prevents man-in-the-middle attacks over HTTP. **Always set in production.**

**SameSite**: Controls when cookies are sent on cross-site requests.
- `SameSite=Strict`: Cookie only sent for same-site requests. Breaks OAuth flows, cross-site links that load the user as logged in.
- `SameSite=Lax`: Cookie sent on top-level navigation (clicking a link) and same-site requests, but not on cross-site subrequests (images, iframes, AJAX). **Good default** — protects against CSRF while not breaking typical flows. Browser default since 2020.
- `SameSite=None; Secure`: Cookie sent on all cross-site requests. Required for embedded iframes (payment widgets, auth widgets). **Must** pair with `Secure`.

```
Set-Cookie: sessionId=abc123; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=3600; Domain=example.com
```

**Domain**: Subdomain sharing. `Domain=example.com` shares the cookie across `app.example.com`, `api.example.com`. Without `Domain`, defaults to exact host only.

**Path**: Cookie only sent for requests matching this path prefix.

**Max-Age / Expires**: Session cookie (no Max-Age/Expires) deleted when browser closes. Persistent cookie survives browser restarts.

---

## Content Negotiation

The server selects the response format based on client preferences expressed in `Accept` headers.

### Server-Driven Content Negotiation

```
Client Request:
Accept: application/json;q=0.9, text/xml;q=0.8, */*;q=0.1
Accept-Language: en-US,en;q=0.9,hi;q=0.7
Accept-Encoding: gzip, br, deflate

Server Response (picks best match):
Content-Type: application/json
Content-Language: en-US
Content-Encoding: br
```

If the server can't satisfy any of the client's formats, it returns **406 Not Acceptable** with available formats.

### Practical content types for APIs
```
application/json              → Standard REST API
application/problem+json      → RFC 7807 Problem Details (error responses)
application/ld+json           → JSON-LD (semantic web)
application/vnd.api+json      → JSON:API spec
multipart/form-data           → File uploads
text/event-stream             → Server-Sent Events
application/x-ndjson          → Newline-delimited JSON (streaming)
```

### RFC 7807 Problem Details
Using a standard error response format makes API errors predictable:
```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Your request parameters didn't validate.",
  "status": 422,
  "detail": "The email field must be a valid email address.",
  "instance": "/users",
  "errors": [
    {"field": "email", "message": "Invalid format"}
  ]
}
```
With `Content-Type: application/problem+json`.

---

## How It Works Internally

### HTTP/2 Frame Anatomy

```
HTTP/2 Frame:
┌─────────────────────────────────────────┐
│ Length (24 bits) │ Type (8 bits)        │
│ Flags (8 bits)   │ Stream ID (31 bits)  │
│ Frame Payload (variable)                │
└─────────────────────────────────────────┘

Frame Types:
  0x0 DATA         - Response/request body
  0x1 HEADERS      - Header fields
  0x3 RST_STREAM   - Cancel a stream
  0x4 SETTINGS     - Connection parameters
  0x6 PING         - Keep-alive / RTT measurement
  0x7 GOAWAY       - Connection shutdown
  0x8 WINDOW_UPDATE - Flow control
  0x9 CONTINUATION - Continuation of HEADERS

Multiple streams multiplexed:
Stream 1: [HEADERS:1][DATA:1][DATA:1][DATA:1 END_STREAM]
Stream 3:       [HEADERS:3][DATA:3 END_STREAM]
Stream 5:              [HEADERS:5][DATA:5][DATA:5 END_STREAM]
─────────────── TCP packet boundaries ──────────────────────
```

### HPACK Header Compression

```
Request 1:
  method: GET              → index 2 (static table)
  scheme: https            → index 7
  path: /index.html        → index 5 (modified) → literal with indexing
  authority: example.com   → new entry, added to dynamic table at index 62

Request 2 (same path):
  method: GET              → index 2
  path: /index.html        → index 62 (dynamic table hit!) ← huge saving
  authority: example.com   → index 63

Wire bytes: request 2 sends 2 bytes instead of ~40 bytes for path alone.
```

---

## Implementation Examples

### Go + Chi Router

```go
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/google/uuid"
)

// corsMiddleware implements CORS with an allowlist approach
func corsMiddleware(allowedOrigins []string) func(http.Handler) http.Handler {
	originSet := make(map[string]struct{}, len(allowedOrigins))
	for _, o := range allowedOrigins {
		originSet[o] = struct{}{}
	}

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if _, ok := originSet[origin]; ok {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Set("Vary", "Origin") // critical: tells caches this varies by origin
				w.Header().Set("Access-Control-Allow-Credentials", "true")
			}

			if r.Method == http.MethodOptions {
				// Preflight request
				w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
				w.Header().Set("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Request-ID")
				w.Header().Set("Access-Control-Max-Age", "86400")
				w.Header().Set("Access-Control-Expose-Headers", "X-Request-ID, RateLimit-Remaining")
				w.WriteHeader(http.StatusNoContent) // 204 for preflight
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

// requestIDMiddleware generates or propagates a request ID
func requestIDMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := r.Header.Get("X-Request-ID")
		if requestID == "" {
			requestID = uuid.New().String()
		}
		// Echo it back in response headers
		w.Header().Set("X-Request-ID", requestID)
		// Store in context for logging
		ctx := r.Context()
		r = r.WithContext(ctx)
		next.ServeHTTP(w, r)
	})
}

type ErrorResponse struct {
	Type   string `json:"type"`
	Title  string `json:"title"`
	Status int    `json:"status"`
	Detail string `json:"detail"`
}

func writeError(w http.ResponseWriter, status int, title, detail string) {
	w.Header().Set("Content-Type", "application/problem+json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(ErrorResponse{
		Type:   "https://api.example.com/errors/" + strings.ToLower(strings.ReplaceAll(title, " ", "-")),
		Title:  title,
		Status: status,
		Detail: detail,
	})
}

type User struct {
	ID    int    `json:"id"`
	Name  string `json:"name"`
	Email string `json:"email"`
}

func main() {
	r := chi.NewRouter()

	// Standard middleware stack
	r.Use(middleware.RequestID) // chi's built-in request ID
	r.Use(middleware.RealIP)    // respects X-Forwarded-For
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer) // 500 on panic instead of crash
	r.Use(middleware.Timeout(30 * time.Second))
	r.Use(middleware.Compress(5)) // gzip compression level 5

	// CORS
	allowedOrigins := strings.Split(os.Getenv("ALLOWED_ORIGINS"), ",")
	r.Use(corsMiddleware(allowedOrigins))
	r.Use(requestIDMiddleware)

	// Content negotiation via Accept header check
	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			accept := r.Header.Get("Accept")
			if accept != "" && accept != "*/*" &&
				!strings.Contains(accept, "application/json") &&
				!strings.Contains(accept, "*/*") {
				writeError(w, http.StatusNotAcceptable, "Not Acceptable",
					"This API only produces application/json")
				return
			}
			next.ServeHTTP(w, r)
		})
	})

	r.Route("/api/v1", func(r chi.Router) {
		r.Get("/users", listUsers)
		r.Post("/users", createUser)
		r.Get("/users/{id}", getUser)
		r.Put("/users/{id}", replaceUser)
		r.Patch("/users/{id}", updateUser)
		r.Delete("/users/{id}", deleteUser)
	})

	// Health check — important: no auth, no CORS, used by load balancers
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-store")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	srv := &http.Server{
		Addr:              ":8080",
		Handler:           r,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       120 * time.Second, // keep-alive timeout
		ReadHeaderTimeout: 5 * time.Second,
		MaxHeaderBytes:    1 << 20, // 1 MB
	}

	log.Printf("Server starting on :8080")
	log.Fatal(srv.ListenAndServe())
}

func listUsers(w http.ResponseWriter, r *http.Request) {
	users := []User{{ID: 1, Name: "Alice", Email: "alice@example.com"}}

	// Conditional GET with ETag
	etag := `"abc123"` // In production: hash of the response data
	if r.Header.Get("If-None-Match") == etag {
		w.Header().Set("ETag", etag)
		w.WriteHeader(http.StatusNotModified) // 304
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "private, max-age=60")
	w.Header().Set("ETag", etag)
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(users)
}

func createUser(w http.ResponseWriter, r *http.Request) {
	// Validate Content-Type
	if !strings.HasPrefix(r.Header.Get("Content-Type"), "application/json") {
		writeError(w, http.StatusUnsupportedMediaType, "Unsupported Media Type",
			"Request body must be application/json")
		return
	}

	var input User
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		writeError(w, http.StatusBadRequest, "Bad Request", "Invalid JSON body")
		return
	}

	if input.Email == "" {
		writeError(w, http.StatusUnprocessableEntity, "Validation Error",
			"Email is required")
		return
	}

	// Create user...
	created := User{ID: 42, Name: input.Name, Email: input.Email}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Location", "/api/v1/users/42") // 201 must include Location
	w.WriteHeader(http.StatusCreated)              // 201
	json.NewEncoder(w).Encode(created)
}

func getUser(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	_ = id // fetch from DB

	// Simulate not found
	writeError(w, http.StatusNotFound, "Not Found", "User with id "+id+" not found")
}

func replaceUser(w http.ResponseWriter, r *http.Request) {
	// Optimistic locking: check If-Match header
	ifMatch := r.Header.Get("If-Match")
	currentETag := `"current-etag"` // fetch from DB

	if ifMatch != "" && ifMatch != currentETag {
		writeError(w, http.StatusPreconditionFailed, "Precondition Failed",
			"Resource has been modified since your last fetch")
		return
	}

	// Replace entire resource...
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
}

func updateUser(w http.ResponseWriter, r *http.Request) {
	// Partial update — only overwrite provided fields
	w.WriteHeader(http.StatusNoContent) // 204 if not returning body
}

func deleteUser(w http.ResponseWriter, r *http.Request) {
	// Idempotent: return 204 even if already deleted (or 404 if strict)
	w.WriteHeader(http.StatusNoContent) // 204
}
```

### Node.js + Express

```javascript
import express from 'express';
import { v4 as uuidv4 } from 'uuid';

const app = express();

// Parse JSON bodies
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request ID middleware
app.use((req, res, next) => {
  const requestId = req.headers['x-request-id'] || uuidv4();
  req.requestId = requestId;
  res.setHeader('X-Request-ID', requestId);
  next();
});

// CORS middleware with allowlist
const ALLOWED_ORIGINS = new Set(
  (process.env.ALLOWED_ORIGINS || '').split(',').filter(Boolean)
);

app.use((req, res, next) => {
  const origin = req.headers.origin;
  
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin'); // Prevent cache poisoning
    res.setHeader('Access-Control-Allow-Credentials', 'true');
  }

  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type, X-Request-ID');
    res.setHeader('Access-Control-Max-Age', '86400');
    res.setHeader('Access-Control-Expose-Headers', 'X-Request-ID, RateLimit-Remaining');
    return res.status(204).end(); // 204 No Content for preflight
  }

  next();
});

// Content-Type enforcement for mutation routes
const requireJSON = (req, res, next) => {
  if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
    if (!req.is('application/json')) {
      return res.status(415).json({
        type: 'https://api.example.com/errors/unsupported-media-type',
        title: 'Unsupported Media Type',
        status: 415,
        detail: 'Request body must be application/json',
      });
    }
  }
  next();
};

// Helper: RFC 7807 Problem Details
const problemJSON = (res, status, title, detail, extra = {}) => {
  res.status(status)
    .type('application/problem+json')
    .json({
      type: `https://api.example.com/errors/${title.toLowerCase().replace(/\s+/g, '-')}`,
      title,
      status,
      detail,
      ...extra,
    });
};

// Routes
app.get('/api/v1/users', (req, res) => {
  const users = [{ id: 1, name: 'Alice', email: 'alice@example.com' }];

  // ETag-based conditional GET
  const etag = '"abc123"';
  if (req.headers['if-none-match'] === etag) {
    return res.status(304).set('ETag', etag).end();
  }

  res
    .set('Cache-Control', 'private, max-age=60')
    .set('ETag', etag)
    .json(users);
});

app.post('/api/v1/users', requireJSON, (req, res) => {
  const { name, email } = req.body;

  if (!email) {
    return problemJSON(res, 422, 'Validation Error', 'Email is required', {
      errors: [{ field: 'email', message: 'Required field' }],
    });
  }

  const user = { id: 42, name, email };
  res
    .status(201)
    .location(`/api/v1/users/${user.id}`)
    .json(user);
});

app.get('/api/v1/users/:id', (req, res) => {
  const { id } = req.params;
  // Simulate not found
  return problemJSON(res, 404, 'Not Found', `User ${id} not found`);
});

app.put('/api/v1/users/:id', requireJSON, (req, res) => {
  const ifMatch = req.headers['if-match'];
  const currentETag = '"current-etag"'; // Would come from DB

  if (ifMatch && ifMatch !== currentETag) {
    return problemJSON(res, 412, 'Precondition Failed',
      'Resource modified since last fetch');
  }

  res.json({ id: req.params.id, ...req.body });
});

app.patch('/api/v1/users/:id', requireJSON, (req, res) => {
  // Only update provided fields
  res.status(204).end();
});

app.delete('/api/v1/users/:id', (req, res) => {
  res.status(204).end(); // Idempotent
});

// Health check
app.get('/health', (req, res) => {
  res.set('Cache-Control', 'no-store').json({ status: 'ok' });
});

// Global error handler
app.use((err, req, res, next) => {
  console.error({ requestId: req.requestId, error: err.message, stack: err.stack });
  
  if (res.headersSent) return next(err);

  // Don't leak internal details
  problemJSON(res, 500, 'Internal Server Error', 'An unexpected error occurred');
});

// Configure keep-alive for production
const server = app.listen(8080, () => {
  console.log('Server running on :8080');
});

server.keepAliveTimeout = 75000; // 75 seconds
server.headersTimeout = 80000;   // Must be > keepAliveTimeout
```

### Python + FastAPI

```python
import os
import uuid
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
import hashlib
import json


# Lifespan handler for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: initialize DB pools, etc.
    yield
    # shutdown: close connections

app = FastAPI(
    title="Example API",
    version="1.0.0",
    lifespan=lifespan,
    # Disable default validation error handler to use RFC 7807
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — FastAPI's built-in middleware
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,       # Use ["*"] only for truly public APIs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "RateLimit-Remaining"],
    max_age=86400,
)


# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Pydantic models
class UserCreate(BaseModel):
    name: str
    email: EmailStr  # validates email format automatically

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class UserResponse(BaseModel):
    id: int
    name: str
    email: str


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str


def problem_response(status: int, title: str, detail: str, extra: dict = None) -> JSONResponse:
    slug = title.lower().replace(" ", "-")
    body = {
        "type": f"https://api.example.com/errors/{slug}",
        "title": title,
        "status": status,
        "detail": detail,
    }
    if extra:
        body.update(extra)
    return JSONResponse(
        content=body,
        status_code=status,
        media_type="application/problem+json",
    )


# Override FastAPI's default 422 validation error format
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(loc) for loc in e["loc"][1:]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return problem_response(422, "Validation Error",
                            "Request body failed validation",
                            {"errors": errors})


# ETag helper
def compute_etag(data: any) -> str:
    content = json.dumps(data, sort_keys=True, default=str)
    return f'"{hashlib.md5(content.encode()).hexdigest()}"'


@app.get("/api/v1/users", response_model=list[UserResponse])
async def list_users(
    request: Request,
    response: Response,
    if_none_match: Optional[str] = Header(None),
):
    users = [{"id": 1, "name": "Alice", "email": "alice@example.com"}]
    etag = compute_etag(users)

    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, max-age=60"
    return users


@app.post("/api/v1/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, response: Response):
    # In production: insert into DB, handle unique constraint → 409
    created = UserResponse(id=42, name=user.name, email=user.email)
    response.headers["Location"] = f"/api/v1/users/{created.id}"
    return created


@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    # Simulate not found
    raise HTTPException(status_code=404, detail=f"User {user_id} not found")


@app.put("/api/v1/users/{user_id}", response_model=UserResponse)
async def replace_user(
    user_id: int,
    user: UserCreate,
    if_match: Optional[str] = Header(None),
):
    current_etag = '"current-etag"'  # Would come from DB

    if if_match and if_match != current_etag:
        return problem_response(412, "Precondition Failed",
                                "Resource was modified since your last fetch")

    return UserResponse(id=user_id, name=user.name, email=user.email)


@app.patch("/api/v1/users/{user_id}", status_code=204)
async def update_user(user_id: int, updates: dict):
    # Partial update, return 204 with no body
    return Response(status_code=204)


@app.delete("/api/v1/users/{user_id}", status_code=204)
async def delete_user(user_id: int):
    # Idempotent — return 204 whether it existed or not
    return Response(status_code=204)


@app.get("/health")
async def health_check(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"status": "ok"}


# Override HTTPException to use RFC 7807 format
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return problem_response(exc.status_code, "Error", exc.detail)
```

---

## Common Patterns & Best Practices

1. **Always set `Cache-Control: no-store` on sensitive endpoints** (auth, personal data). Default browser caching can expose data on shared computers.

2. **Use ETags for GET-heavy resources**: Dramatically reduces bandwidth. A 200KB JSON response returning 304 saves 200KB per cache hit.

3. **Set `Vary: Origin` on CORS responses**: Without this, a CDN might cache a response with one origin's CORS headers and serve it to a different origin.

4. **Prefer 422 over 400 for semantic validation errors**: 400 means "I can't parse your request." 422 means "I parsed it, but the data is invalid."

5. **Return `Location` header on 201**: Clients should not have to know how to construct the URL of a created resource.

6. **Tune server timeouts for your SLA**: `ReadTimeout` should match your max request size at reasonable bandwidth. `WriteTimeout` should match your slowest query. `IdleTimeout` should be longer than client keep-alive.

7. **Log `X-Request-ID` in every log line**: Enables distributed tracing by correlating all log lines for a single request across services.

8. **Use `SameSite=Lax` as default cookie policy**: Modern browsers default to this, but be explicit. It stops 90% of CSRF attacks without breaking normal navigation.

9. **Set `ReadHeaderTimeout`** (Go): Protects against Slowloris attacks where a client slowly sends headers indefinitely.

10. **Return `Retry-After` with 429 and 503**: Without it, clients will hammer your server in a retry loop the moment the window resets.

---

## Common Pitfalls

- ❌ **WRONG**: Using 200 for all responses, including errors (`{"status": "error", "message": "..."}`)
  - ✅ **CORRECT**: Use proper HTTP status codes. HTTP status is the protocol's error signaling mechanism. Tools (load balancers, monitoring, API clients) rely on it.

- ❌ **WRONG**: `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true`
  - ✅ **CORRECT**: When using credentials, specify exact origins. Wildcards cannot be used with credentials.

- ❌ **WRONG**: Reflecting `Origin` header without validating it against an allowlist
  - ✅ **CORRECT**: Check `if allowedOrigins.has(origin)` before setting the CORS header.

- ❌ **WRONG**: Using POST for both "create user" and "delete user" because "REST is hard"
  - ✅ **CORRECT**: Use the appropriate HTTP method. DELETE is idempotent and semantically correct.

- ❌ **WRONG**: Returning 401 for "you don't have permission"
  - ✅ **CORRECT**: 401 = unauthenticated, 403 = unauthorized. Use 403 when the user is logged in but lacks permission.

- ❌ **WRONG**: Not setting `Vary: Origin` when your CORS middleware modifies responses based on the Origin header
  - ✅ **CORRECT**: CDNs use `Vary` to differentiate cache keys. Without it, cached responses leak CORS headers between origins.

- ❌ **WRONG**: Using 302 redirect after a form POST (causes form resubmission on refresh)
  - ✅ **CORRECT**: Use 303 See Other (Post/Redirect/Get pattern).

- ❌ **WRONG**: Not configuring `IdleTimeout` in Go's http.Server (default: infinite, causes connection leaks)
  - ✅ **CORRECT**: Set `IdleTimeout: 120 * time.Second` and `ReadHeaderTimeout: 5 * time.Second`.

- ❌ **WRONG**: Storing session tokens in `localStorage` (vulnerable to XSS)
  - ✅ **CORRECT**: Use `HttpOnly; Secure; SameSite=Lax` cookies for session tokens.

- ❌ **WRONG**: Sending stack traces in 500 error responses
  - ✅ **CORRECT**: Log the error with request ID internally; return only `{"detail": "An unexpected error occurred"}` to clients.

---

## Interview Questions

**Q1. What is the difference between PUT and PATCH?**

**Answer:** PUT replaces the **entire** resource at the target URI with the request body. If you omit a field, it gets overwritten to null or default. PATCH applies a **partial modification** — only the fields in the request body are changed, others remain untouched.

Idempotency: PUT is always idempotent (sending the same PUT twice has the same result). PATCH may or may not be idempotent — `PATCH {"increment": 1}` is not idempotent, but `PATCH {"status": "active"}` is.

Real example: For a 10-field user record, updating just the email:
- PUT requires sending all 10 fields (risk of accidentally overwriting fields you didn't mean to)
- PATCH requires only `{"email": "newemail@example.com"}`

---

**Q2. What is the difference between 401 and 403?**

**Answer:** 
- **401 Unauthorized**: The client is *unauthenticated*. Either no credentials were provided, or they were invalid. The server must return `WWW-Authenticate` header telling the client how to authenticate. The name "Unauthorized" is a historical misnomer — it really means "unauthenticated."
- **403 Forbidden**: The client *is* authenticated (we know who you are), but you are not *authorized* to perform this action. No `WWW-Authenticate` header.

"401: We don't know who you are. 403: We know who you are, but you can't come in."

Edge case: Some APIs return 404 instead of 403 to avoid revealing that a resource exists (e.g., "you don't have access to /admin/secrets" might return 404 to hide that the resource exists).

---

**Q3. Explain what happens when you type a URL in a browser (full lifecycle)**

**Answer:**
1. **URL parsing**: Browser extracts scheme (https), host (api.example.com), path, query string, fragment
2. **HSTS check**: Browser checks if domain is in HSTS list, upgrades http to https if so
3. **DNS resolution**: Checks browser cache → OS cache → resolving nameserver → root/TLD/authoritative nameservers → returns IP. Result cached per TTL.
4. **TCP 3-way handshake**: SYN → SYN-ACK → ACK. Establishes connection. (~1 RTT)
5. **TLS 1.3 handshake**: ClientHello (with key_share) → ServerHello + Certificate + Finished → client Finished. (~1 RTT). Both sides derive symmetric session keys.
6. **HTTP/2 connection preface**: Both sides exchange SETTINGS frames.
7. **HTTP request sent**: Headers (HPACK compressed) and optional body, multiplexed on stream ID 1.
8. **Server processing**: Load balancer → app server → middleware (auth, logging) → handler → database/cache → response generated
9. **HTTP response**: Status line, headers, body streamed back
10. **Browser rendering**: HTML parsed, additional sub-resources fetched (CSS, JS, images) — many as parallel streams on the same HTTP/2 connection
11. **Connection kept alive**: TCP/HTTP/2 connection maintained for subsequent requests

---

**Q4. What is CORS and why does it exist?**

**Answer:** CORS (Cross-Origin Resource Sharing) is a browser security mechanism that allows servers to declare which origins are permitted to read their responses from JavaScript.

**Why it exists**: Browsers enforce the Same-Origin Policy — JavaScript on `app.evil.com` cannot read responses from `api.yourbank.com`. Without SOP, malicious sites could use your cookies to make authenticated API calls and read the response. CORS lets legitimate cross-origin sites (your frontend on `app.myproduct.com` calling `api.myproduct.com`) opt in to being readable.

**How it works**: For "non-simple" requests (anything with custom headers, JSON body, or non-GET/POST methods), the browser first sends an OPTIONS preflight. The server responds with what's allowed. If the preflight passes, the actual request is made. The browser checks `Access-Control-Allow-Origin` before exposing the response to JavaScript.

**Key insight**: CORS is enforced *by the browser*, not the server. Server-to-server calls, curl, and Postman are never subject to CORS.

---

**Q5. What is HTTP/2 and what problems does it solve over HTTP/1.1?**

**Answer:** HTTP/2 solves the fundamental performance limitations of HTTP/1.1:

1. **Head-of-line blocking** (application layer): HTTP/1.1 pipelining requires responses in order — a slow resource blocks faster ones. HTTP/2 multiplexes requests/responses on a single TCP connection using stream IDs — any stream can complete independently.

2. **Connection overhead**: Browsers open 6 TCP connections per domain to work around HTTP/1.1's limitation. HTTP/2 uses a single connection with full multiplexing, reducing handshake overhead and server port pressure.

3. **Header overhead**: HTTP/1.1 headers are plaintext and repeat on every request (Cookie, User-Agent, Authorization). HTTP/2's HPACK compression indexes repeated headers — `Authorization: Bearer <token>` sent once, referenced by index thereafter.

4. **Binary framing**: HTTP/2 is binary, not text. Faster to parse, less error-prone.

What HTTP/2 does NOT solve: TCP-level head-of-line blocking — a dropped TCP packet stalls all streams. HTTP/3 + QUIC solves this.

---

**Q6. When would you use 204 vs 200?**

**Answer:** 
- **200 OK**: Request succeeded and the response body contains a representation of the result. Use when returning data to the client.
- **204 No Content**: Request succeeded but there is no body to return. The client should not navigate away from its current page.

Use 204 for:
- DELETE: resource deleted, nothing to return
- PUT/PATCH: update accepted, client already has the updated data (or doesn't need it)
- Logout endpoint
- Webhook acknowledgment
- Background operations where the client just needs confirmation

Use 200 for:
- GET: returning resource data
- POST when returning the created/processed result
- PUT/PATCH when you want to return the updated resource (saves client a round-trip fetch)

Rule of thumb: 204 if there's no useful body; 200 if you're sending data back.

---

**Q7. What is idempotency and which HTTP methods are idempotent?**

**Answer:** An operation is **idempotent** if performing it N times has the same effect on server state as performing it once. The response may differ (first DELETE returns 200, second returns 404), but the *server state* is the same.

Idempotent methods: GET, HEAD, OPTIONS, PUT, DELETE.
Non-idempotent: POST, PATCH (by convention, though can be designed to be idempotent).

**Why it matters for distributed systems**:
- If a client sends a DELETE and the network times out before the response arrives, can it safely retry? Yes — DELETE is idempotent. Either it was processed once or twice, the resource is still deleted.
- If a client sends a POST (create order) and times out — retrying creates a duplicate order. Solutions: idempotency keys (client sends unique key, server deduplicates).

**Idempotency keys pattern**: Client generates UUID and includes `Idempotency-Key: <uuid>` header. Server stores `(key → response)` in Redis/DB for 24h. Duplicate requests return the cached response instead of re-executing. Stripe and most payment APIs use this pattern.

---

## Resources

- [MDN HTTP Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP)
- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)
- [RFC 9113 — HTTP/2](https://www.rfc-editor.org/rfc/rfc9113)
- [RFC 9114 — HTTP/3](https://www.rfc-editor.org/rfc/rfc9114)
- [Cloudflare Blog — HTTP/3 and QUIC](https://blog.cloudflare.com/http3-the-past-present-and-future/)
- [RFC 8446 — TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446)
- [RFC 7807 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc7807)
- [OWASP — Transport Layer Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html)
- [High Performance Browser Networking — Ilya Grigorik (free online)](https://hpbn.co/)
- [Everything you need to know about HTTP security headers](https://securityheaders.com/)

---

**Next:** [Part 1.2: REST vs GraphQL vs gRPC](./01-rest-vs-graphql-grpc.md)
