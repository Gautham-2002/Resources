# Part 17.2: WebSockets, Server-Sent Events & File Streaming

## What You'll Learn
- The WebSocket upgrade handshake and protocol internals
- Full-duplex communication vs HTTP request/response vs SSE
- When to use WebSocket vs SSE vs Long Polling
- Horizontal scaling challenges with stateful connections and Redis pub/sub solutions
- Server-Sent Events: one-way streaming over HTTP
- File streaming, range requests, and chunked transfer encoding
- Idempotency keys: preventing duplicate operations across retries
- Production implementations in Go+Chi, Node.js+Express, Python+FastAPI

## Table of Contents
1. [HTTP vs WebSockets vs SSE](#1-http-vs-websockets-vs-sse)
2. [WebSocket Protocol Internals](#2-websocket-protocol-internals)
3. [WebSocket Use Cases](#3-websocket-use-cases)
4. [WebSocket Challenges & Scaling](#4-websocket-challenges--scaling)
5. [Server-Sent Events (SSE)](#5-server-sent-events-sse)
6. [Comparison: WebSocket vs SSE vs Long Polling](#6-comparison-websocket-vs-sse-vs-long-polling)
7. [Horizontal Scaling with Redis Pub/Sub](#7-horizontal-scaling-with-redis-pubsub)
8. [File Streaming](#8-file-streaming)
9. [Idempotency Keys](#9-idempotency-keys)
10. [How It Works Internally](#10-how-it-works-internally)
11. [Implementation Examples](#11-implementation-examples)
    - [Go + Chi](#go--chi)
    - [Node.js + Express](#nodejs--express)
    - [Python + FastAPI](#python--fastapi)
12. [Common Patterns & Best Practices](#12-common-patterns--best-practices)
13. [Common Pitfalls](#13-common-pitfalls)
14. [Interview Questions](#14-interview-questions)
15. [Resources](#15-resources)

---

## 1. HTTP vs WebSockets vs SSE

### HTTP Request-Response (the baseline)

```
Client                    Server
  │                          │
  │── GET /messages ────────►│
  │                          │  process
  │◄── 200 OK + body ────────│
  │                          │
  │  (connection closes)     │
  │                          │
  │── GET /messages ────────►│  (client must poll again)
  │◄── 200 OK + body ────────│
```

**Characteristics:**
- Stateless — each request is independent
- Half-duplex — one party speaks at a time (request → response)
- Connection closes after each exchange (HTTP/1.1 uses keep-alive for connection reuse, but the logical exchange is still req→resp)
- Client must initiate every exchange — server cannot push to client unprompted

**Problem with polling:** To get "real-time" data over HTTP, clients must repeatedly poll:
```
Every 2 seconds:
client → GET /notifications
server → 200 [] (empty)
server → 200 [] (empty)
server → 200 [] (empty)
server → 200 [{"message": "You got paid!"}]  ← finally, data after 6 seconds avg
```

This is wasteful: most polls return empty, and latency is up to the poll interval.

### WebSocket: Full-Duplex Persistent Connection

```
Client                    Server
  │                          │
  │── HTTP GET /ws ─────────►│  (Upgrade handshake)
  │   Upgrade: websocket     │
  │◄── 101 Switching ────────│
  │                          │
  │   (persistent connection established)
  │                          │
  │── "Hello!" ─────────────►│  (client sends anytime)
  │◄── "Hi back!" ───────────│  (server sends anytime)
  │◄── "New order!" ─────────│  (server pushes unprompted)
  │── "ACK" ────────────────►│
  │◄── "System alert" ───────│
  │                          │
  │  (connection stays open indefinitely)
```

**Characteristics:**
- Persistent — one TCP connection stays open
- Full-duplex — both sides can send/receive simultaneously
- Low latency — no per-message handshake overhead
- Stateful — the server must remember this connection

### Server-Sent Events: Unidirectional Stream over HTTP

```
Client                    Server
  │                          │
  │── GET /events ──────────►│
  │   Accept: text/event-stream
  │                          │
  │◄── 200 OK ───────────────│  (headers, connection stays open)
  │◄── data: {"msg":"hi"}\n\n│  (server pushes anytime)
  │◄── data: {"msg":"hey"}\n\n│
  │◄── data: {"price":42}\n\n │
  │   [auto-reconnect if dropped]
  │── GET /events ──────────►│  (Last-Event-ID: 17 — resumes from here)
```

**Characteristics:**
- Unidirectional — server → client only
- Plain HTTP — works through proxies, HTTP/2, load balancers
- Built-in reconnect — browser EventSource API reconnects automatically
- Text-based — easy to debug with curl

---

## 2. WebSocket Protocol Internals

### The Upgrade Handshake

WebSocket starts as an HTTP request and upgrades to the WebSocket protocol.

**Client sends:**
```
GET /ws/chat HTTP/1.1
Host: api.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Sec-WebSocket-Protocol: chat, superchat
```

**Server responds:**
```
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
Sec-WebSocket-Protocol: chat
```

The `Sec-WebSocket-Accept` is computed as:
```
SHA1(Sec-WebSocket-Key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
→ base64 encoded
```

This proves the server genuinely accepted a WebSocket upgrade (not a confused HTTP server treating the WS frames as garbage).

After the 101 response, the TCP connection is "owned" by the WebSocket protocol — no more HTTP.

### WebSocket Frame Format

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
├─┼─┼─┼─┼─────────┼─┼─────────────────────────────────────────────┤
│F│R│R│R│ opcode  │M│    Payload len    │   Extended payload len   │
│I│S│S│S│         │A│                   │      (if needed)         │
│N│V│V│V│         │S│                   │                          │
│ │1│2│3│         │K│                   │                          │
├─┴─┴─┴─┴─────────┴─┴───────────────────────────────────────────── ┤
│                 Masking key (4 bytes, if MASK=1)                  │
├──────────────────────────────────────────────────────────────────┤
│                      Payload Data                                 │
└──────────────────────────────────────────────────────────────────┘

FIN:     1 = this is the final fragment of the message
Opcode:  0x1 = text frame
         0x2 = binary frame
         0x8 = connection close
         0x9 = ping
         0xA = pong
MASK:    1 = payload is masked (client→server MUST be masked; server→client unmasked)
```

**Payload length encoding:**
- 0-125: stored directly in the 7-bit field
- 126: next 2 bytes are the true length (up to 65535)
- 127: next 8 bytes are the true length (large messages)

### Ping/Pong Keepalive

WebSocket has built-in keepalive frames:
```
Server → Client: PING frame (opcode 0x9)
Client → Server: PONG frame (opcode 0xA)  ← browser responds automatically

Server detects stale connection:
  If no PONG received within X seconds → close connection, clean up resources
```

Why this matters: TCP connections can silently die (NAT timeout, idle firewall, network cut) without sending a FIN/RST. Without ping/pong, the server holds a "zombie" connection object forever, leaking memory.

**Typical keepalive configuration:**
- Server sends PING every 30 seconds
- If no PONG within 10 seconds → mark connection as dead, close

---

## 3. WebSocket Use Cases

### Live Chat
```
Client A ──── WS ────► Server ────► Redis Pub/Sub ────► Server ────► WS ──── Client B

Alice types "Hello Bob" → server receives → publishes to room channel →
all servers subscribed to room channel → push to Bob's connection
```

### Real-Time Notifications
```
User opens app → WS connects to /ws/notifications?token=xxx
Server: subscribe to user's notification channel in Redis
Backend job: INSERT notification → publish to Redis channel → WS push to user
Result: notification appears in-app without polling
```

### Live Dashboards (Stock Tickers, Analytics)
```
Analytics server computes metrics every second
→ publishes to Redis channel "dashboard:metrics"
→ all connected dashboard clients receive updates via WS
```

### Collaborative Editing (Google Docs-style)
```
Client A edits line 5 → sends delta to server → server applies to CRDT
→ broadcasts delta to all other clients in the document session
→ Client B's document updates in real time
```

### Live Order Tracking
```
Customer opens order tracking page → WS connects
Driver's app sends GPS updates → server publishes to "order:{id}:location"
Customer's WS subscription receives updates → map updates in real time
```

---

## 4. WebSocket Challenges & Scaling

### Challenge 1: Stateful Connections

HTTP servers are designed to be stateless — any server can handle any request. WebSockets break this:

```
Client ──── TCP connection ──── Server A

The connection is OWNED by Server A.
If Server A restarts, the connection is closed.
If load balancer routes next request to Server B, Server B doesn't know about this connection.
```

### Challenge 2: Horizontal Scaling

```
Naive approach (broken):
                        ┌─────────────────────┐
Client A ──── WS ──────►│     Server A        │
                        │  conn map: {A: ws_a}│
                        └─────────────────────┘

                        ┌─────────────────────┐
Client B ──── WS ──────►│     Server B        │
                        │  conn map: {B: ws_b}│
                        └─────────────────────┘

Admin sends broadcast to Server A:
  Server A → sends to Client A ✓
  Server A → doesn't know about Client B ✗   ← message lost!
```

### Challenge 3: Load Balancer Configuration

Standard load balancers (round-robin) break WebSockets because they'll try to route the second request to a different server. You need:

**Option A: Sticky sessions (IP hash or session cookie)**
```nginx
upstream ws_backend {
    ip_hash;  # same client IP always goes to same server
    server backend1:8080;
    server backend2:8080;
    server backend3:8080;
}
```

**Option B: Layer 7 WebSocket-aware load balancing**
```nginx
location /ws {
    proxy_pass http://ws_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;  # don't timeout idle WS connections
}
```

### Challenge 4: Reconnection Logic (Client-Side)

Clients must implement exponential backoff reconnect:
```javascript
class WebSocketClient {
  constructor(url) {
    this.url = url;
    this.reconnectDelay = 1000;  // start at 1 second
    this.maxDelay = 30000;       // cap at 30 seconds
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('connected');
      this.reconnectDelay = 1000;  // reset on successful connection
    };

    this.ws.onclose = () => {
      console.log(`disconnected, reconnecting in ${this.reconnectDelay}ms`);
      setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxDelay);
    };

    this.ws.onerror = (err) => console.error('ws error:', err);
    this.ws.onmessage = (event) => this.handleMessage(event.data);
  }
}
```

### Challenge 5: Backpressure (Slow Consumers)

If a client receives messages slower than the server sends them, messages pile up in the send buffer. Solutions:
- Monitor the send buffer size before writing
- Drop or compress messages for slow consumers
- Implement explicit flow control (client sends "ready" signals)
- Close connections that fall too far behind (with appropriate error message)

---

## 5. Server-Sent Events (SSE)

### Protocol Details

SSE uses a simple text protocol over a persistent HTTP response:

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no     ← tell nginx not to buffer SSE responses

data: Hello World\n\n     ← minimal event (just data)

event: price_update\n     ← named event type
data: {"ticker":"AAPL","price":227.50}\n\n

id: 42\n                  ← event ID (for reconnect)
event: notification\n
data: {"msg":"Your order shipped"}\n
retry: 5000\n\n           ← tell client to retry after 5 seconds on disconnect
```

**Field types:**
- `data:` — the event payload (can span multiple lines with multiple `data:` entries)
- `event:` — optional event name (client can listen for specific event types)
- `id:` — event ID sent as `Last-Event-ID` header on reconnect (enables resumable streams)
- `retry:` — reconnect delay hint to the client (in milliseconds)

### SSE vs WebSocket Decision Tree

```
Does the client need to send data to the server?
├── YES → Use WebSocket
└── NO
    ├── Do you need HTTP/2 multiplexing or proxy compatibility?
    │   └── YES → Use SSE (plain HTTP, easier to operate)
    ├── Do you need browser auto-reconnect?
    │   └── YES → Use SSE (EventSource API reconnects automatically)
    └── Is the data text-based events?
        └── YES → SSE is simpler and sufficient
```

### SSE Limitations

1. **Unidirectional** — client can't send data over the SSE stream (use separate HTTP endpoints)
2. **Browser connection limit** — HTTP/1.1 browsers limit to 6 connections per domain; multiple SSE tabs compete (HTTP/2 eliminates this via multiplexing)
3. **No binary support** — SSE is text only (WebSocket supports binary frames)
4. **IE/Edge legacy** — SSE not supported in IE (WebSocket is more universally supported)

---

## 6. Comparison: WebSocket vs SSE vs Long Polling

| Feature | WebSocket | SSE | Long Polling |
|---------|-----------|-----|--------------|
| **Direction** | Bidirectional | Server → Client | Server → Client |
| **Protocol** | `ws://` / `wss://` | HTTP | HTTP |
| **Connection** | Persistent TCP | Persistent HTTP | Request held open until data |
| **Auto-reconnect** | No (manual) | Yes (EventSource) | Manual |
| **HTTP/2 support** | No (own protocol) | Yes | Yes |
| **Binary data** | Yes (binary frames) | No (text only) | Yes (but awkward) |
| **Proxy-friendly** | Sometimes problematic | Yes | Yes |
| **Browser support** | All modern browsers | All except IE | All browsers |
| **Server complexity** | High | Medium | Low |
| **Latency** | Lowest | Low | Medium (up to timeout) |
| **Bandwidth** | Most efficient | Efficient | Inefficient (many requests) |
| **Best for** | Chat, gaming, collab | Notifications, feeds, live data | Legacy systems, simple push |

### Long Polling Mechanics (for completeness)

```
Client                    Server
  │── GET /updates ──────────►│
  │                           │  wait... (connection held open)
  │                           │  wait... (up to 30 seconds)
  │◄── 200 OK {"event":...} ──│  (data available, respond immediately)
  │── GET /updates ──────────►│  (immediately re-open next long poll)
  │                           │  wait...
```

**Why it's legacy:** works everywhere, but each "connection" is a new HTTP request with full headers, and the server holds a thread/connection open per waiting client. SSE does the same thing more efficiently.

---

## 7. Horizontal Scaling with Redis Pub/Sub

### The Problem

```
Without Redis Pub/Sub:

User A connected to Server 1
User B connected to Server 2

Admin wants to broadcast "System maintenance in 10 minutes" to ALL users

Admin → POST /admin/broadcast → Server 1
Server 1 sends to User A ✓
Server 1 CANNOT send to User B ✗  (connection is on Server 2)
```

### The Solution: Redis Pub/Sub as Message Bus

```
                     ┌──────────────────────────────────────────┐
                     │              Redis                        │
                     │   Channel: "broadcast:all"               │
                     │   Channel: "user:1001:notifications"     │
                     │   Channel: "room:general"                │
                     └───┬──────────────────────────────────────┘
                         │
            ┌────────────┴─────────────┐
            │  SUBSCRIBE               │  SUBSCRIBE
            ▼                          ▼
┌──────────────────────┐   ┌──────────────────────┐
│       Server 1       │   │       Server 2       │
│                      │   │                      │
│  Connections:        │   │  Connections:        │
│  User A ──── ws_a   │   │  User B ──── ws_b   │
│  User C ──── ws_c   │   │  User D ──── ws_d   │
└──────────────────────┘   └──────────────────────┘

Flow: Admin broadcasts to ALL users
  1. Admin → POST /admin/broadcast → hits Server 2 (via load balancer)
  2. Server 2 → Redis PUBLISH "broadcast:all" "maintenance in 10min"
  3. Redis delivers to ALL subscribers: Server 1 AND Server 2
  4. Server 1 pushes to User A and User C via their ws connections
  5. Server 2 pushes to User B and User D via their ws connections
  ✓ All users receive the broadcast
```

### Redis Pub/Sub vs Redis Streams

| | Redis Pub/Sub | Redis Streams |
|---|---|---|
| Message persistence | No (fire-and-forget) | Yes (messages stored) |
| Replay on reconnect | No | Yes (from last ID) |
| Consumer groups | No | Yes |
| Message ACK | No | Yes |
| Use case | Real-time broadcast (WS fan-out) | Reliable event processing |

For WebSocket fan-out (broadcast to all connected clients), Redis Pub/Sub is appropriate because:
- You want all connected servers to receive broadcasts simultaneously
- Messages don't need to be persisted (if a client is disconnected, they'll request missed messages via separate API)

### Per-User Channel Pattern

```
Client connects:
  1. Authenticate (validate JWT, extract user_id)
  2. Subscribe to Redis channel: "user:{user_id}:events"
  3. Subscribe to room channels: "room:{room_id}:messages"

When a backend job wants to notify User 1001:
  PUBLISH user:1001:events '{"type":"notification","msg":"Order shipped"}'

Redis delivers to whatever server User 1001 is connected to.
That server pushes the message via WebSocket.
```

---

## 8. File Streaming

### The Problem with Loading Files into Memory

```go
// BAD: loads entire 2GB video file into memory
func serveVideo(w http.ResponseWriter, r *http.Request) {
    data, err := os.ReadFile("/videos/movie.mp4")  // 2GB in RAM
    if err != nil {
        http.Error(w, "not found", 404)
        return
    }
    w.Write(data)  // copies 2GB to response
}
// Result: OOM kill, terrible performance, no seeking
```

```go
// GOOD: streaming with io.Copy
func serveVideo(w http.ResponseWriter, r *http.Request) {
    file, err := os.Open("/videos/movie.mp4")
    if err != nil {
        http.Error(w, "not found", 404)
        return
    }
    defer file.Close()
    http.ServeContent(w, r, "movie.mp4", time.Now(), file)
    // Automatically handles Range requests, sends 8KB chunks, never loads full file
}
```

### Range Requests (HTTP 206 Partial Content)

Range requests allow clients to request specific byte ranges of a file — essential for video seeking and resumable downloads.

```
Client requests bytes 1000000-1999999 of a video (seeking to 10 minutes in):

Request:
  GET /video/movie.mp4 HTTP/1.1
  Range: bytes=1000000-1999999

Response:
  HTTP/1.1 206 Partial Content
  Content-Range: bytes 1000000-1999999/524288000
  Content-Length: 1000000
  Accept-Ranges: bytes

  [1MB of video data starting at byte 1,000,000]
```

**Range request flow for video streaming:**
```
Browser video player:
  1. GET /video/movie.mp4 → 200 OK, Content-Length: 524288000, Accept-Ranges: bytes
  2. GET /video/movie.mp4 Range: bytes=0-1048575      → 206 (first 1MB)
  3. User scrubs to 20min mark
  4. GET /video/movie.mp4 Range: bytes=250000000-251048575  → 206 (1MB at ~20min mark)
  5. Continue playing from there
```

### Chunked Transfer Encoding

When you don't know the total size upfront (streaming generated content), use chunked transfer:

```
HTTP/1.1 200 OK
Transfer-Encoding: chunked
Content-Type: application/octet-stream

1A\r\n                    ← chunk size in hex (26 bytes)
abcdefghijklmnopqrstuvwxyz\r\n
1A\r\n
ABCDEFGHIJKLMNOPQRSTUVWXYZ\r\n
0\r\n                     ← final chunk: size 0 = end of stream
\r\n
```

Use cases: streaming large CSV/JSON exports, real-time log streaming, AI token streaming.

### Streaming File Upload to S3 Without Buffering to Disk

```go
// BAD: buffer entire upload to disk, then upload to S3
func uploadFile(w http.ResponseWriter, r *http.Request) {
    r.ParseMultipartForm(100 << 20)  // 100MB limit
    file, _, _ := r.FormFile("file")
    defer file.Close()

    tmpFile, _ := os.CreateTemp("", "upload-*")
    io.Copy(tmpFile, file)  // write 500MB to disk
    defer os.Remove(tmpFile.Name())

    s3Client.UploadFile(tmpFile.Name())  // upload 500MB from disk
}

// GOOD: stream directly from HTTP request to S3
func uploadFile(w http.ResponseWriter, r *http.Request) {
    // AWS SDK multipart upload: 5MB chunks piped directly
    uploader := s3manager.NewUploader(sess)
    _, err := uploader.Upload(&s3manager.UploadInput{
        Bucket: aws.String("my-bucket"),
        Key:    aws.String("uploads/file.mp4"),
        Body:   r.Body,  // stream directly from request body
    })
    // Memory usage: ~5MB (one S3 part) regardless of file size
}
```

### Multipart Upload for Large Files

```
Traditional upload:                     Multipart upload:
──────────────────────────────          ──────────────────────────────
POST /upload                            POST /upload/initiate → UploadId
[full 5GB file]                         PUT /upload/{id}/part/1 [5MB]
                                        PUT /upload/{id}/part/2 [5MB]
                                        ...
                                        PUT /upload/{id}/part/1000 [5MB]
                                        POST /upload/{id}/complete
```

Benefits of multipart:
- Resumable (restart from failed part, not from zero)
- Parallel (upload multiple parts simultaneously)
- Progress tracking (parts completed / total parts)

---

## 9. Idempotency Keys

### The Problem

Network failures cause clients to retry. When a client sends "charge $100" and gets a network error (not knowing if the server received it), what should it do?

```
Client                    Server              Stripe
  │── POST /checkout ─────►│── charge $100 ──►│
  │                        │                   │ charged ✓
  │  [NETWORK TIMEOUT]     │◄── success ───────│
  │   client never         │
  │   received the         │
  │   response             │

Client:
  "Did the request succeed? I got a timeout. I'll retry to be safe."
  │── POST /checkout ─────►│── charge $100 ──►│  ← double charge! ✗
```

### The Solution: Idempotency Keys

The client generates a unique key for each "logical operation" and includes it in the request. The server uses it to deduplicate:

```
Client generates:  idempotency_key = "order_checkout_user1234_2026-06-29T10:00:00Z"
                   (or just a UUID generated before the first attempt)

First attempt:
  POST /checkout
  Idempotency-Key: abc-123-def-456

  Server:
    1. Check Redis/DB: has key "abc-123-def-456" been processed?
    2. NO → process the payment → store result with key → return result

Second attempt (retry on timeout):
  POST /checkout
  Idempotency-Key: abc-123-def-456   ← SAME key

  Server:
    1. Check Redis/DB: has key "abc-123-def-456" been processed?
    2. YES → return the STORED result (don't charge again)
    3. Client receives success response
    ✓ No double charge
```

### Implementation Design

```
Request arrives with Idempotency-Key header:
│
├── Check idempotency store (Redis):
│   ├── Key found AND status = "processing" → return 409 (request in flight)
│   ├── Key found AND status = "completed"  → return stored response (200)
│   └── Key not found → proceed
│
├── Store key with status = "processing" (with TTL)
│
├── Execute the actual operation
│
├── Store result (request + response) against key, status = "completed"
│
└── Return result to client

TTL for idempotency keys:
  - Stripe uses 24 hours
  - Payment systems: 7 days
  - General APIs: 1-24 hours depending on retry window
```

### Redis Data Structure for Idempotency

```
Key:   idempotency:{key_hash}
Value: {
  "status": "completed",
  "request_hash": "sha256 of request body",
  "response_status": 200,
  "response_body": "{\"id\":\"order_123\",\"amount\":100}",
  "created_at": "2026-06-29T10:00:00Z"
}
TTL: 86400 (24 hours)
```

**Important:** Also hash the request body. If a client reuses the same idempotency key with a DIFFERENT request body, that's a bug — return a 422 (Unprocessable Entity) error.

---

## 10. How It Works Internally

### WebSocket Connection Lifecycle in Go's net/http

```
net/http server (TCP listener)
│
├── Accept TCP connection
├── Read HTTP request
├── Match to handler
│
├── Handler calls websocket.Upgrade(w, r, headers)
│   ├── Validates Upgrade/Connection headers
│   ├── Computes Sec-WebSocket-Accept
│   ├── Hijacks the net.Conn (takes control from http.ResponseWriter)
│   │   └── After hijack: http package no longer manages this connection
│   └── Returns *websocket.Conn (wraps the raw TCP connection)
│
└── Handler now owns the TCP connection:
    ├── Read loop: ws.ReadMessage() → blocks until frame arrives
    ├── Write: ws.WriteMessage() → sends frame
    └── On close: ws.Close() → send close frame, close TCP connection

Memory: each WebSocket connection = ~8KB overhead (goroutine stack, buffers)
       10,000 connections = ~80MB — manageable, but watch for leaks
```

### SSE in Go (net/http)

```
SSE uses http.Flusher — an optional interface implemented by ResponseWriters that support streaming:

handler:
  w.Header().Set("Content-Type", "text/event-stream")
  w.Header().Set("Cache-Control", "no-cache")
  w.WriteHeader(200)

  flusher := w.(http.Flusher)

  for event := range events {
      fmt.Fprintf(w, "data: %s\n\n", event)
      flusher.Flush()   ← forces data through the HTTP response buffer to the client
  }
  // When handler returns, HTTP response closes, client reconnects
```

### Redis Pub/Sub Internals

```
Redis Pub/Sub is implemented as:
  - A table mapping channel names → list of subscriber clients
  - PUBLISH is O(N) where N = number of subscribers
  - Messages are NOT persisted — if subscriber is disconnected, message is lost

SUBSCRIBE user:1001:notifications
  → Redis adds this connection to "subscribers[user:1001:notifications]"

PUBLISH user:1001:notifications '{"type":"order_shipped"}'
  → Redis iterates subscribers list
  → Sends message to each subscriber connection
  → Returns the number of clients that received the message

UNSUBSCRIBE user:1001:notifications
  → Redis removes from subscribers list
```

---

## 11. Implementation Examples

### Go + Chi

**WebSocket handler with connection management:**
```go
package main

import (
    "context"
    "encoding/json"
    "log"
    "net/http"
    "sync"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/gorilla/websocket"
    "github.com/redis/go-redis/v9"
)

var upgrader = websocket.Upgrader{
    ReadBufferSize:  1024,
    WriteBufferSize: 1024,
    CheckOrigin: func(r *http.Request) bool {
        // In production: validate Origin header against allowed domains
        return true
    },
}

// Hub manages all active WebSocket connections
type Hub struct {
    mu          sync.RWMutex
    connections map[string]*Client  // userID → client
    redisClient *redis.Client
}

type Client struct {
    userID string
    conn   *websocket.Conn
    send   chan []byte  // buffered channel for outgoing messages
}

type Message struct {
    Type    string          `json:"type"`
    Payload json.RawMessage `json:"payload"`
}

var hub = &Hub{
    connections: make(map[string]*Client),
}

// WebSocket endpoint: GET /ws
func (h *Hub) HandleWebSocket(w http.ResponseWriter, r *http.Request) {
    // 1. Authenticate — extract user from JWT
    userID := r.Context().Value("userID").(string)
    if userID == "" {
        http.Error(w, "unauthorized", http.StatusUnauthorized)
        return
    }

    // 2. Upgrade HTTP to WebSocket
    conn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
        log.Printf("websocket upgrade failed: %v", err)
        return
    }

    client := &Client{
        userID: userID,
        conn:   conn,
        send:   make(chan []byte, 256),
    }

    // 3. Register connection
    h.mu.Lock()
    h.connections[userID] = client
    h.mu.Unlock()

    log.Printf("user %s connected (total: %d)", userID, h.connCount())

    // 4. Start read and write goroutines
    go client.readPump(h)
    go client.writePump()

    // 5. Subscribe to Redis channel for this user
    go h.subscribeUserChannel(r.Context(), userID, client)
}

// readPump reads messages from the WebSocket connection
func (c *Client) readPump(h *Hub) {
    defer func() {
        h.unregister(c)
        c.conn.Close()
        log.Printf("user %s disconnected", c.userID)
    }()

    // Configure connection
    c.conn.SetReadLimit(512 * 1024)  // 512KB max message size
    c.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
    c.conn.SetPongHandler(func(string) error {
        // Reset read deadline on pong — proves client is alive
        c.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
        return nil
    })

    for {
        _, message, err := c.conn.ReadMessage()
        if err != nil {
            if websocket.IsUnexpectedCloseError(err,
                websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
                log.Printf("unexpected close from user %s: %v", c.userID, err)
            }
            break
        }

        // Handle incoming message from client
        var msg Message
        if err := json.Unmarshal(message, &msg); err != nil {
            log.Printf("invalid message from user %s: %v", c.userID, err)
            continue
        }

        h.handleClientMessage(c.userID, msg)
    }
}

// writePump writes messages from the send channel to the WebSocket connection
func (c *Client) writePump() {
    // Send ping every 30 seconds to keep connection alive
    ticker := time.NewTicker(30 * time.Second)
    defer func() {
        ticker.Stop()
        c.conn.Close()
    }()

    for {
        select {
        case message, ok := <-c.send:
            c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
            if !ok {
                // Channel closed — send close frame
                c.conn.WriteMessage(websocket.CloseMessage, []byte{})
                return
            }

            w, err := c.conn.NextWriter(websocket.TextMessage)
            if err != nil {
                return
            }
            w.Write(message)

            // Batch: write any pending messages in the same WebSocket frame
            n := len(c.send)
            for i := 0; i < n; i++ {
                w.Write([]byte{'\n'})
                w.Write(<-c.send)
            }
            w.Close()

        case <-ticker.C:
            // Send ping
            c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
            if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
                return  // connection dead
            }
        }
    }
}

// subscribeUserChannel subscribes to Redis and forwards messages to the WebSocket
func (h *Hub) subscribeUserChannel(ctx context.Context, userID string, client *Client) {
    channel := "user:" + userID + ":notifications"
    pubsub := h.redisClient.Subscribe(ctx, channel)
    defer pubsub.Close()

    for msg := range pubsub.Channel() {
        select {
        case client.send <- []byte(msg.Payload):
        default:
            // Client's send buffer is full — they're too slow
            log.Printf("user %s send buffer full, dropping message", userID)
        }
    }
}

// Broadcast sends a message to all connected clients via Redis pub/sub
func (h *Hub) Broadcast(ctx context.Context, message []byte) error {
    return h.redisClient.Publish(ctx, "broadcast:all", message).Err()
}

// SendToUser sends a message to a specific user
func (h *Hub) SendToUser(ctx context.Context, userID string, message []byte) error {
    channel := "user:" + userID + ":notifications"
    return h.redisClient.Publish(ctx, channel, message).Err()
}

func (h *Hub) unregister(c *Client) {
    h.mu.Lock()
    defer h.mu.Unlock()
    if _, ok := h.connections[c.userID]; ok {
        delete(h.connections, c.userID)
        close(c.send)
    }
}

func (h *Hub) connCount() int {
    h.mu.RLock()
    defer h.mu.RUnlock()
    return len(h.connections)
}
```

**SSE endpoint:**
```go
// SSE endpoint: GET /events
func HandleSSE(w http.ResponseWriter, r *http.Request) {
    // Verify client supports SSE flushing
    flusher, ok := w.(http.Flusher)
    if !ok {
        http.Error(w, "streaming not supported", http.StatusInternalServerError)
        return
    }

    userID := r.Context().Value("userID").(string)

    // SSE headers
    w.Header().Set("Content-Type", "text/event-stream")
    w.Header().Set("Cache-Control", "no-cache")
    w.Header().Set("Connection", "keep-alive")
    w.Header().Set("X-Accel-Buffering", "no")  // disable nginx buffering

    // Send initial heartbeat
    fmt.Fprintf(w, ": heartbeat\n\n")
    flusher.Flush()

    // Subscribe to Redis channel
    ctx := r.Context()
    pubsub := redisClient.Subscribe(ctx, "user:"+userID+":events")
    defer pubsub.Close()

    // Heartbeat ticker — send comment every 30s to keep connection alive through proxies
    heartbeat := time.NewTicker(30 * time.Second)
    defer heartbeat.Stop()

    var eventID int64

    for {
        select {
        case <-ctx.Done():
            // Client disconnected
            log.Printf("SSE client %s disconnected", userID)
            return

        case <-heartbeat.C:
            fmt.Fprintf(w, ": heartbeat\n\n")
            flusher.Flush()

        case msg := <-pubsub.Channel():
            eventID++
            // SSE format
            fmt.Fprintf(w, "id: %d\n", eventID)
            fmt.Fprintf(w, "event: notification\n")
            fmt.Fprintf(w, "data: %s\n\n", msg.Payload)
            flusher.Flush()
        }
    }
}
```

**File streaming with range support:**
```go
// Large file streaming: GET /files/{id}
func StreamFile(w http.ResponseWriter, r *http.Request) {
    fileID := chi.URLParam(r, "id")

    // Get file metadata from DB
    meta, err := db.GetFileMeta(r.Context(), fileID)
    if err != nil {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }

    // Open file (could be local disk or S3 via io.ReadSeeker)
    file, err := os.Open(meta.Path)
    if err != nil {
        http.Error(w, "file unavailable", http.StatusInternalServerError)
        return
    }
    defer file.Close()

    // Set content type
    w.Header().Set("Content-Type", meta.ContentType)
    w.Header().Set("Content-Disposition", "inline; filename=\""+meta.Filename+"\"")

    // http.ServeContent handles:
    // - Range requests (206 Partial Content) automatically
    // - If-Modified-Since, ETag caching
    // - Chunked sending (never loads full file into memory)
    http.ServeContent(w, r, meta.Filename, meta.ModifiedAt, file)
}

// Streaming S3 download (no local buffering)
func StreamFromS3(w http.ResponseWriter, r *http.Request) {
    fileKey := chi.URLParam(r, "*")

    result, err := s3Client.GetObject(r.Context(), &s3.GetObjectInput{
        Bucket: aws.String(os.Getenv("S3_BUCKET")),
        Key:    aws.String(fileKey),
    })
    if err != nil {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    defer result.Body.Close()

    w.Header().Set("Content-Type", aws.ToString(result.ContentType))
    w.Header().Set("Content-Length", fmt.Sprintf("%d", aws.ToInt64(result.ContentLength)))

    // Stream: never loads full file into memory
    if _, err := io.Copy(w, result.Body); err != nil {
        log.Printf("stream error for %s: %v", fileKey, err)
    }
}
```

**Idempotency key middleware:**
```go
// IdempotencyMiddleware — attach to POST/PATCH/DELETE routes
func IdempotencyMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Only applies to mutating requests
        if r.Method == http.MethodGet || r.Method == http.MethodHead {
            next.ServeHTTP(w, r)
            return
        }

        key := r.Header.Get("Idempotency-Key")
        if key == "" {
            // Don't require for all routes — only for critical operations
            next.ServeHTTP(w, r)
            return
        }

        // Validate key format (UUID)
        if !isValidUUID(key) {
            http.Error(w, "invalid idempotency key format", http.StatusBadRequest)
            return
        }

        ctx := r.Context()
        redisKey := "idempotency:" + key

        // Check if already processed
        val, err := redisClient.Get(ctx, redisKey).Bytes()
        if err == nil {
            // Already processed — return cached response
            var cached CachedResponse
            if err := json.Unmarshal(val, &cached); err == nil {
                w.Header().Set("Idempotent-Replayed", "true")
                w.WriteHeader(cached.Status)
                w.Write(cached.Body)
                return
            }
        }

        // Mark as "processing" to handle concurrent requests with same key
        processing, err := redisClient.SetNX(ctx, redisKey+":lock", "1",
            10*time.Second).Result()
        if err != nil || !processing {
            // Another request with this key is in flight
            http.Error(w, "concurrent request with same idempotency key",
                http.StatusConflict)
            return
        }
        defer redisClient.Del(ctx, redisKey+":lock")

        // Capture the response
        rec := httptest.NewRecorder()
        next.ServeHTTP(rec, r)

        // Store result for 24 hours
        cached, _ := json.Marshal(CachedResponse{
            Status: rec.Code,
            Body:   rec.Body.Bytes(),
        })
        redisClient.Set(ctx, redisKey, cached, 24*time.Hour)

        // Write the actual response
        for k, v := range rec.Header() {
            w.Header()[k] = v
        }
        w.WriteHeader(rec.Code)
        w.Write(rec.Body.Bytes())
    })
}

type CachedResponse struct {
    Status int    `json:"status"`
    Body   []byte `json:"body"`
}
```

---

### Node.js + Express

**WebSocket server with Redis pub/sub fan-out:**
```javascript
import express from 'express';
import { WebSocketServer, WebSocket } from 'ws';
import { createClient } from 'redis';
import http from 'http';

const app = express();
const server = http.createServer(app);

// Connection registry: userId → ws
const clients = new Map();

// Redis connections (separate clients for pub and sub)
const redisPublisher = createClient({ url: process.env.REDIS_URL });
const redisSubscriber = createClient({ url: process.env.REDIS_URL });

await redisPublisher.connect();
await redisSubscriber.connect();

// WebSocket server on the same HTTP server
const wss = new WebSocketServer({ server, path: '/ws' });

wss.on('connection', async (ws, req) => {
  // 1. Authenticate
  const token = new URL(req.url, 'http://localhost').searchParams.get('token');
  const user = await verifyJWT(token);
  if (!user) {
    ws.close(1008, 'unauthorized');
    return;
  }

  const userId = user.id;

  // 2. Register connection
  clients.set(userId, ws);
  console.log(`User ${userId} connected. Total: ${clients.size}`);

  // 3. Keepalive: send ping every 30s
  const pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.ping();
    }
  }, 30000);

  ws.on('pong', () => {
    ws.isAlive = true;  // mark as alive on pong receipt
  });

  // 4. Subscribe to Redis channel for this user
  await redisSubscriber.subscribe(`user:${userId}:events`, (message) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(message);
    }
  });

  // 5. Handle incoming messages from client
  ws.on('message', async (data) => {
    try {
      const msg = JSON.parse(data.toString());
      await handleClientMessage(userId, msg);
    } catch (err) {
      console.error(`Invalid message from user ${userId}:`, err);
    }
  });

  // 6. Cleanup on disconnect
  ws.on('close', async () => {
    clearInterval(pingInterval);
    clients.delete(userId);
    await redisSubscriber.unsubscribe(`user:${userId}:events`);
    console.log(`User ${userId} disconnected. Total: ${clients.size}`);
  });

  ws.on('error', (err) => {
    console.error(`WebSocket error for user ${userId}:`, err);
  });
});

// Dead connection cleanup (runs every 30s)
setInterval(() => {
  wss.clients.forEach((ws) => {
    if (!ws.isAlive) {
      ws.terminate();  // force close zombie connections
      return;
    }
    ws.isAlive = false;
    ws.ping();
  });
}, 30000);

// Send notification to a specific user
export async function notifyUser(userId, payload) {
  const message = JSON.stringify(payload);
  // Publish to Redis — whichever server the user is on will deliver it
  await redisPublisher.publish(`user:${userId}:events`, message);
}

// Broadcast to all connected users
export async function broadcast(payload) {
  const message = JSON.stringify(payload);
  await redisPublisher.publish('broadcast:all', message);
}

// Subscribe to broadcast channel
await redisSubscriber.subscribe('broadcast:all', (message) => {
  clients.forEach((ws) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(message);
    }
  });
});

server.listen(3000);
```

**SSE endpoint:**
```javascript
// GET /events - Server-Sent Events endpoint
app.get('/events', authenticate, async (req, res) => {
  const userId = req.user.id;

  // SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();  // send headers immediately

  let eventId = 0;

  const sendEvent = (type, data) => {
    eventId++;
    res.write(`id: ${eventId}\n`);
    res.write(`event: ${type}\n`);
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  };

  // Initial connection event
  sendEvent('connected', { userId, timestamp: new Date().toISOString() });

  // Subscribe to Redis channel
  const subscriber = redisSubscriber.duplicate();
  await subscriber.connect();
  await subscriber.subscribe(`user:${userId}:events`, (message) => {
    sendEvent('notification', JSON.parse(message));
  });

  // Heartbeat every 30s (keeps connection through proxies)
  const heartbeat = setInterval(() => {
    res.write(': heartbeat\n\n');
  }, 30000);

  // Cleanup on client disconnect
  req.on('close', async () => {
    clearInterval(heartbeat);
    await subscriber.unsubscribe(`user:${userId}:events`);
    await subscriber.quit();
    console.log(`SSE client ${userId} disconnected`);
  });
});
```

**Idempotency middleware:**
```javascript
import { createHash } from 'crypto';

export const idempotencyMiddleware = async (req, res, next) => {
  const idempotencyKey = req.headers['idempotency-key'];

  if (!idempotencyKey || req.method === 'GET' || req.method === 'HEAD') {
    return next();
  }

  const redisKey = `idempotency:${idempotencyKey}`;

  try {
    // Check for existing result
    const existing = await redisClient.get(redisKey);
    if (existing) {
      const cached = JSON.parse(existing);
      res.set('Idempotent-Replayed', 'true');
      return res.status(cached.status).json(cached.body);
    }

    // Set processing lock (10s TTL)
    const locked = await redisClient.set(
      `${redisKey}:lock`, '1',
      { NX: true, EX: 10 }
    );
    if (!locked) {
      return res.status(409).json({
        error: 'Concurrent request with same idempotency key'
      });
    }

    // Intercept response to cache it
    const originalJson = res.json.bind(res);
    res.json = async (body) => {
      // Cache the result
      await redisClient.setEx(redisKey, 86400, JSON.stringify({
        status: res.statusCode,
        body,
      }));
      await redisClient.del(`${redisKey}:lock`);
      return originalJson(body);
    };

    next();
  } catch (err) {
    console.error('Idempotency middleware error:', err);
    next();
  }
};

// Usage:
app.post('/payments', idempotencyMiddleware, processPayment);
```

---

### Python + FastAPI

**WebSocket handler with connection management:**
```python
import asyncio
import json
import logging
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from redis.asyncio import Redis

logger = logging.getLogger(__name__)
app = FastAPI()


class ConnectionManager:
    """Manages WebSocket connections and Redis pub/sub fan-out."""

    def __init__(self, redis: Redis):
        self.redis = redis
        self.connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.connections[user_id] = websocket
        logger.info(f"User {user_id} connected. Total: {len(self.connections)}")

    async def disconnect(self, user_id: str):
        self.connections.pop(user_id, None)
        logger.info(f"User {user_id} disconnected. Total: {len(self.connections)}")

    async def send_to_user(self, user_id: str, data: dict) -> bool:
        """Send directly to a local connection, returns True if sent."""
        ws = self.connections.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
                return True
            except Exception:
                return False
        return False

    async def publish_to_user(self, user_id: str, data: dict):
        """Publish via Redis pub/sub — reaches user on any server."""
        channel = f"user:{user_id}:events"
        await self.redis.publish(channel, json.dumps(data))

    async def broadcast(self, data: dict):
        """Broadcast to all connected users via Redis."""
        await self.redis.publish("broadcast:all", json.dumps(data))


manager: Optional[ConnectionManager] = None


@app.on_event("startup")
async def startup():
    global manager
    redis = Redis.from_url("redis://localhost:6379")
    manager = ConnectionManager(redis)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    # Authenticate
    user = await verify_jwt(token)
    if not user:
        await websocket.close(code=1008, reason="unauthorized")
        return

    user_id = str(user.id)

    await manager.connect(websocket, user_id)

    # Subscribe to Redis channel for this user
    redis_sub = manager.redis.pubsub()
    await redis_sub.subscribe(f"user:{user_id}:events", "broadcast:all")

    # Task to forward Redis messages to WebSocket
    async def redis_to_ws():
        async for message in redis_sub.listen():
            if message["type"] == "message":
                if websocket.client_state.value == 1:  # CONNECTED
                    try:
                        await websocket.send_text(message["data"].decode())
                    except Exception:
                        break

    redis_task = asyncio.create_task(redis_to_ws())

    try:
        # Ping/pong keepalive
        ping_task = asyncio.create_task(keepalive_ping(websocket))

        # Read messages from client
        while True:
            data = await websocket.receive_json()
            await handle_client_message(user_id, data)

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected cleanly")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        redis_task.cancel()
        ping_task.cancel()
        await redis_sub.unsubscribe(f"user:{user_id}:events", "broadcast:all")
        await redis_sub.close()
        await manager.disconnect(user_id)


async def keepalive_ping(websocket: WebSocket):
    """Send ping every 30 seconds to detect dead connections."""
    while True:
        await asyncio.sleep(30)
        try:
            await websocket.send_json({"type": "ping"})
        except Exception:
            break
```

**SSE endpoint:**
```python
import asyncio
from fastapi import Request
from fastapi.responses import StreamingResponse


@app.get("/events")
async def sse_endpoint(request: Request, user_id: str = Depends(get_current_user)):
    """Server-Sent Events endpoint for real-time notifications."""

    async def event_generator():
        redis_sub = manager.redis.pubsub()
        await redis_sub.subscribe(f"user:{user_id}:events")

        event_id = 0

        try:
            # Send connection confirmation
            event_id += 1
            yield f"id: {event_id}\nevent: connected\ndata: {{\"userId\": \"{user_id}\"}}\n\n"

            heartbeat_task = asyncio.create_task(asyncio.sleep(30))

            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.info(f"SSE client {user_id} disconnected")
                    break

                # Check for Redis messages (non-blocking, 1s timeout)
                message = await redis_sub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message:
                    event_id += 1
                    data = message["data"].decode()
                    yield f"id: {event_id}\nevent: notification\ndata: {data}\n\n"
                elif heartbeat_task.done():
                    # Send heartbeat comment (keeps connection alive through proxies)
                    yield ": heartbeat\n\n"
                    heartbeat_task = asyncio.create_task(asyncio.sleep(30))

        finally:
            await redis_sub.unsubscribe(f"user:{user_id}:events")
            await redis_sub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

**File streaming:**
```python
import os
import aiofiles
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, FileResponse
import boto3


@app.get("/files/{file_id}")
async def stream_file(file_id: str, user=Depends(get_current_user)):
    """Stream a file without loading it into memory."""

    meta = await db.get_file_meta(file_id)
    if not meta or meta.user_id != user.id:
        raise HTTPException(status_code=404)

    # For local files: use FileResponse (handles Range requests automatically)
    if meta.storage == "local":
        return FileResponse(
            path=meta.path,
            media_type=meta.content_type,
            filename=meta.filename,
        )

    # For S3: stream directly without buffering
    if meta.storage == "s3":
        return await stream_from_s3(meta)


async def stream_from_s3(meta) -> StreamingResponse:
    """Stream S3 object without loading into memory."""
    s3 = boto3.client("s3")

    try:
        obj = s3.get_object(Bucket=meta.bucket, Key=meta.s3_key)
    except s3.exceptions.NoSuchKey:
        raise HTTPException(status_code=404)

    async def s3_stream():
        # Stream in 64KB chunks
        chunk_size = 64 * 1024
        stream = obj["Body"]
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            yield chunk

    return StreamingResponse(
        s3_stream(),
        media_type=meta.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{meta.filename}"',
            "Content-Length": str(obj["ContentLength"]),
        },
    )


@app.post("/upload")
async def upload_file(request: Request, user=Depends(get_current_user)):
    """Stream upload directly to S3 without buffering to disk."""
    import aioboto3

    content_type = request.headers.get("content-type", "application/octet-stream")
    file_key = f"uploads/{user.id}/{uuid4()}"

    session = aioboto3.Session()
    async with session.client("s3") as s3:
        # Multipart upload for large files
        mpu = await s3.create_multipart_upload(
            Bucket=os.getenv("S3_BUCKET"),
            Key=file_key,
            ContentType=content_type,
        )

        parts = []
        part_number = 1
        buffer = b""
        min_part_size = 5 * 1024 * 1024  # S3 minimum: 5MB per part

        async for chunk in request.stream():
            buffer += chunk
            if len(buffer) >= min_part_size:
                part = await s3.upload_part(
                    Bucket=os.getenv("S3_BUCKET"),
                    Key=file_key,
                    UploadId=mpu["UploadId"],
                    PartNumber=part_number,
                    Body=buffer,
                )
                parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
                part_number += 1
                buffer = b""

        # Upload final part (may be < 5MB, allowed for last part)
        if buffer:
            part = await s3.upload_part(
                Bucket=os.getenv("S3_BUCKET"),
                Key=file_key,
                UploadId=mpu["UploadId"],
                PartNumber=part_number,
                Body=buffer,
            )
            parts.append({"PartNumber": part_number, "ETag": part["ETag"]})

        await s3.complete_multipart_upload(
            Bucket=os.getenv("S3_BUCKET"),
            Key=file_key,
            UploadId=mpu["UploadId"],
            MultipartUpload={"Parts": parts},
        )

    return {"key": file_key, "url": f"https://cdn.example.com/{file_key}"}
```

**Idempotency key middleware:**
```python
import hashlib
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware to handle idempotency keys for mutating operations."""

    def __init__(self, app, redis: Redis):
        super().__init__(app)
        self.redis = redis

    async def dispatch(self, request: Request, call_next):
        # Only apply to mutating methods
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        redis_key = f"idempotency:{idempotency_key}"

        # Check for existing result
        cached = await self.redis.get(redis_key)
        if cached:
            data = json.loads(cached)
            response = JSONResponse(
                content=data["body"],
                status_code=data["status"],
                headers={"Idempotent-Replayed": "true"},
            )
            return response

        # Acquire processing lock (prevent concurrent requests with same key)
        lock_key = f"{redis_key}:lock"
        locked = await self.redis.set(lock_key, "1", nx=True, ex=10)
        if not locked:
            return JSONResponse(
                content={"error": "Concurrent request with same idempotency key"},
                status_code=409,
            )

        try:
            # Process the request
            response = await call_next(request)

            # Read response body
            body_bytes = b""
            async for chunk in response.body_iterator:
                body_bytes += chunk

            body = json.loads(body_bytes)

            # Cache result for 24 hours
            await self.redis.setex(
                redis_key,
                86400,
                json.dumps({"status": response.status_code, "body": body}),
            )

            return Response(
                content=body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        finally:
            await self.redis.delete(lock_key)


# Register in FastAPI
app.add_middleware(IdempotencyMiddleware, redis=redis_client)
```

---

## 12. Common Patterns & Best Practices

### Pattern 1: Message Envelope (Typed WebSocket Messages)

Always wrap WebSocket messages in a typed envelope:

```json
{
  "type": "chat_message",
  "payload": {
    "room_id": "general",
    "text": "Hello!",
    "timestamp": "2026-06-29T10:00:00Z"
  },
  "version": "1"
}
```

This lets you:
- Dispatch to different handlers by type
- Version your messages
- Ignore unknown types gracefully (forward compatibility)

### Pattern 2: Resumable SSE Streams

Use `Last-Event-ID` to resume from where the client left off:

```go
func HandleSSE(w http.ResponseWriter, r *http.Request) {
    lastEventID := r.Header.Get("Last-Event-ID")
    startID, _ := strconv.ParseInt(lastEventID, 10, 64)

    // Replay missed events from DB
    missedEvents, _ := db.GetEventsSince(r.Context(), userID, startID)
    for _, event := range missedEvents {
        fmt.Fprintf(w, "id: %d\ndata: %s\n\n", event.ID, event.Data)
        flusher.Flush()
    }

    // Then subscribe to new events...
}
```

### Pattern 3: Connection Metadata Store in Redis

Store active connection info in Redis (not just in memory):

```redis
HSET ws:connections:{user_id}
  server_id    server-1
  connected_at 2026-06-29T10:00:00Z
  ip_address   1.2.3.4

EXPIRE ws:connections:{user_id} 3600
```

Benefits:
- Admin tools can see all active connections across all servers
- Can route push notifications to the correct server
- Health monitoring (connection counts per server)

### Pattern 4: Circuit Breaker for External Streaming

When streaming from an external service (S3, GCS), use a circuit breaker to fail fast if the external service is down rather than holding HTTP connections open:

```go
func StreamWithCircuitBreaker(w http.ResponseWriter, key string) error {
    return circuitBreaker.Execute(func() error {
        return streamFromS3(w, key)
    })
}
```

### Pattern 5: Idempotency Key Format

Use a composite key that's meaningful for debugging:

```
{operation}:{resource_id}:{client_generated_uuid}
payment:order_456:01J8X-ABC-123
email:user_789:01J8X-DEF-456
```

---

## 13. Common Pitfalls

### Pitfall 1: Not Setting WebSocket Write Deadlines

If you never set a write deadline, a slow/dead client's send buffer fills up and the goroutine/thread blocks indefinitely, leaking memory:

```go
// ALWAYS set write deadlines before writing
conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
conn.WriteMessage(websocket.TextMessage, data)
```

### Pitfall 2: Not Handling Client Disconnection in SSE

If a client disconnects and you don't check `r.Context().Done()` or `request.is_disconnected()`, your goroutine/coroutine leaks — it keeps receiving Redis messages and trying to write to a closed connection:

```go
// ALWAYS check context cancellation in SSE
select {
case <-ctx.Done():
    return  // client disconnected, clean up
case msg := <-pubsub.Channel():
    // send to client
}
```

### Pitfall 3: Nginx / Proxy Buffering Breaking SSE

By default, nginx buffers upstream responses. For SSE, this means events accumulate in nginx's buffer and aren't delivered to the client until the buffer is full:

```nginx
location /events {
    proxy_pass http://backend;
    proxy_buffering off;           # ← critical for SSE
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding on;
}
```

### Pitfall 4: Using In-Memory Connection Registry Across Servers

```javascript
// BAD: connections Map only contains THIS server's connections
const connections = new Map();
broadcast(msg) {
  connections.forEach(ws => ws.send(msg));  // ← misses clients on other servers
}

// GOOD: use Redis pub/sub to reach all servers
async broadcast(msg) {
  await redisPublisher.publish('broadcast:all', JSON.stringify(msg));
}
```

### Pitfall 5: Not Handling WebSocket Upgrade in Load Balancer

Standard HTTP load balancers may not forward `Upgrade` and `Connection` headers correctly. Always configure your load balancer to proxy WebSocket connections:

```nginx
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
```

### Pitfall 6: Idempotency Key Collision

If two different operations accidentally use the same idempotency key, the second operation will return the first operation's cached result — potentially applying the wrong response to the wrong request. Include a user ID and operation type in the key structure to make collisions impossible.

### Pitfall 7: Streaming Large Files with `response.body = data`

```python
# BAD: loads entire file into memory
@app.get("/download/{id}")
async def download(id: str):
    data = await s3.download_entire_file(id)  # 2GB in memory
    return Response(content=data)             # then copies to response

# GOOD: stream in chunks
@app.get("/download/{id}")
async def download(id: str):
    return StreamingResponse(stream_chunks_from_s3(id))  # 64KB at a time
```

### Pitfall 8: Race Condition in Idempotency Check

```
Thread 1: Check Redis → key not found → proceed to process
Thread 2: Check Redis → key not found → proceed to process  ← both proceed!
Thread 1: Process payment (charge $100)
Thread 2: Process payment (charge $100)  ← double charge!
```

Solution: use Redis SET NX (atomic set-if-not-exists) for the idempotency lock, not a separate GET + SET.

---

## 14. Interview Questions

**Q: What is the WebSocket upgrade handshake?**

A: The WebSocket connection starts as a standard HTTP GET request with two special headers: `Upgrade: websocket` and `Connection: Upgrade`. The client also sends a `Sec-WebSocket-Key` — a random base64-encoded value. The server responds with HTTP 101 Switching Protocols and a `Sec-WebSocket-Accept` header, which is the SHA1 hash of the client's key concatenated with a fixed GUID, base64-encoded. This proves the server understood the WebSocket upgrade. After the 101 response, the TCP connection is "owned" by the WebSocket protocol — no more HTTP framing.

---

**Q: How do you scale WebSocket servers horizontally?**

A: WebSockets are stateful — each connection is owned by one server — which makes horizontal scaling harder than stateless HTTP. Two approaches: (1) Sticky sessions at the load balancer (IP hash or session cookie), so the same client always routes to the same server. (2) Redis pub/sub as a message bus — every server subscribes to Redis channels; when any server wants to push a message, it publishes to Redis and every server that has relevant connections delivers it. Option 2 is the production standard because it doesn't break when servers restart.

---

**Q: What is the difference between WebSocket and SSE? When would you use each?**

A: WebSocket is a separate protocol (ws://) that provides full-duplex, bidirectional communication over a persistent connection. It's best for interactive real-time features: chat, gaming, collaborative editing, live order tracking. SSE (Server-Sent Events) is unidirectional — server to client only — using a plain HTTP response with `Content-Type: text/event-stream`. The browser's `EventSource` API reconnects automatically on disconnect. SSE is simpler to implement, works through HTTP proxies and HTTP/2, and is appropriate when you only need server push: notification feeds, live dashboards, activity streams. The rule of thumb: if the client needs to send data in real time, use WebSocket; if it only needs to receive, use SSE.

---

**Q: What is an idempotency key and how do you implement it?**

A: An idempotency key is a client-generated unique identifier that lets the server detect and deduplicate retried requests. The client generates a UUID before the first attempt and includes it in the `Idempotency-Key` header on every retry. The server checks Redis for this key before processing. If found (completed), it returns the cached response. If not found, it processes the request, caches the result against the key (with 24h TTL), and returns the result. A processing lock (Redis SET NX) prevents two concurrent requests with the same key from both proceeding. Critical for payment processing — it guarantees a network retry doesn't cause a double charge.

---

**Q: How do you stream large files without loading them into memory?**

A: Use streaming I/O primitives. In Go, `http.ServeContent` streams a `ReadSeeker` in chunks and handles Range requests automatically. For S3 objects, call `GetObject` and `io.Copy` the response body to `http.ResponseWriter` — the S3 SDK streams it in chunks. In Python FastAPI, return a `StreamingResponse` with an async generator that yields chunks. The key principle is to never read the entire file into a byte slice or buffer — always pipe through fixed-size chunks. For video, also implement Range request support so clients can seek without downloading from the beginning.

---

**Q: What is Redis pub/sub and how does it enable broadcasting across WebSocket servers?**

A: Redis pub/sub is a messaging primitive where publishers send messages to named channels, and all current subscribers receive them. It's fire-and-forget — no persistence, no consumer groups. For WebSocket scaling: each server subscribes to relevant Redis channels (broadcast, per-user notifications, per-room messages). When any server wants to push to a user, it publishes to that user's Redis channel. Redis delivers the message to all subscriber connections — specifically the server that holds that user's WebSocket connection. That server then sends it over the WebSocket. The result: you can publish from any server and the message reaches any user, regardless of which server they're connected to.

---

**Q: What happens when a WebSocket connection goes stale (the client crashed without sending a close frame)?**

A: The TCP connection remains in the server's connection table because no FIN/RST was sent. Without keepalive, the server holds a zombie connection indefinitely, leaking memory and file descriptors. The solution is WebSocket ping/pong: the server sends PING frames every 30 seconds. The browser's WebSocket implementation automatically responds with PONG. If no PONG is received within a timeout (e.g., 10 seconds), the server terminates the connection and cleans up resources. In Go, you implement this with `SetReadDeadline` that gets reset on each PONG, combined with a ticker that sends PINGs and detects when the deadline expires.

---

## 15. Resources

- [MDN: WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket) — comprehensive browser WebSocket reference
- [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) — SSE specification and browser API
- [RFC 6455: The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455) — the actual WebSocket spec
- [gorilla/websocket](https://github.com/gorilla/websocket) — Go WebSocket library
- [ws npm package](https://github.com/websockets/ws) — Node.js WebSocket library
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) — FastAPI WebSocket documentation
- [AWS: Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) — why jitter matters
- [Stripe: Idempotency Keys](https://stripe.com/docs/api/idempotent_requests) — real-world idempotency implementation
- [HTTP Range Requests (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests) — range requests explained
- [Redis Pub/Sub Documentation](https://redis.io/docs/manual/pubsub/) — Redis pub/sub internals

---

**Next:** You've completed the backend guide! Cross-reference with [System Design](../System-Design/) for interview preparation. The concepts in this guide — job queues, WebSockets, idempotency, file streaming — appear heavily in system design interviews for companies like Stripe (idempotency), Discord (WebSocket scaling), Netflix (file streaming), and Uber (real-time tracking).
