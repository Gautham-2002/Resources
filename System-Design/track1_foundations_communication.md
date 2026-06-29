# Track 1: Foundations & Communication — System Design Study Guide

### System Design Self-Study Series for Gautham Gokulakonda

> This is Track 1 of 5. It covers networking, DNS, CDN, load balancers, API design, gateways, proxies, rate limiting, and real-time protocols. Breadth first — but with enough depth to answer _why_, not just _what_.

---

# How to Use This Guide

This guide builds mental models, not memorised definitions. Each topic follows the same structure: what it is → why it exists → how it works → trade-offs → interview Q&A. The goal is that you can answer 'why did you choose X over Y?' for every concept here.

**Interview philosophy:**

- FAANG tests trade-offs and scale reasoning — know when X beats Y, not just what X is.
- Indian unicorn interviews (Razorpay, Swiggy, PhonePe) test practical component knowledge and data modelling.
- Both test: can you explain why, not just what.

> **💡 Tip:** Gautham's context is baked in. References to Kafka, Redis, GKE, PayGuard AI, and Deepta AI are intentional — your real-world experience is your interview edge. Use these examples when interviewers ask for concrete illustrations.

## Table of Contents

1. [1. Networking Fundamentals](#1-networking-fundamentals)
2. [2. DNS — Domain Name System](#2-dns-domain-name-system)
3. [3. CDN — Content Delivery Network](#3-cdn-content-delivery-network)
4. [4. Load Balancers](#4-load-balancers)
5. [5. API Design](#5-api-design)
6. [6. API Gateway](#6-api-gateway)
7. [7. Forward Proxy vs Reverse Proxy](#7-forward-proxy-vs-reverse-proxy)
8. [8. Rate Limiting](#8-rate-limiting)
9. [9. WebSockets](#9-websockets)
10. [10. Server-Sent Events (SSE)](#10-server-sent-events-sse)
11. [11. Polling & WebHooks](#11-polling-webhooks)
12. [Quick Revision Cheatsheet](#quick-revision-cheatsheet--track-1)

---

## 1. Networking Fundamentals

### OSI Model — The 7 Layers

**What it is:** A conceptual framework dividing network communication into 7 distinct layers, each with a specific responsibility. In system design, you mostly care about L3 (Network), L4 (Transport), and L7 (Application).

| **Layer** | **Name**     | **Protocol Examples**  | **System Design Relevance**                      |
| --------- | ------------ | ---------------------- | ------------------------------------------------ |
| 7         | Application  | HTTP, gRPC, WebSocket  | API design, L7 LB, API gateway routing           |
| 6         | Presentation | TLS/SSL, JSON encoding | Encryption, compression                          |
| 5         | Session      | WebSocket sessions     | Session management                               |
| 4         | Transport    | TCP, UDP               | L4 LB, connection management, port-level routing |
| 3         | Network      | IP, ICMP               | Routing, Geo-DNS, anycast IPs                    |
| 2         | Data Link    | Ethernet, WiFi         | Rarely discussed in SD interviews                |
| 1         | Physical     | Cables, signals        | Never discussed in SD interviews                 |

> **💡 Tip:** When someone says 'L4 vs L7 load balancer', they mean whether the LB operates at the TCP/port level or the HTTP header/URL level. This distinction matters for TLS termination, sticky sessions, and routing intelligence.

### TCP vs UDP

**What it is:** TCP (Transmission Control Protocol) is connection-oriented with guaranteed ordered delivery. UDP (User Datagram Protocol) is connectionless and fire-and-forget. All your existing backend services — Kafka, Redis, PostgreSQL — run over TCP.

| **Dimension**      | **TCP**                                 | **UDP**                                    |
| ------------------ | --------------------------------------- | ------------------------------------------ |
| Connection         | 3-way handshake required                | No connection setup                        |
| Reliability        | Guaranteed delivery, retransmit on loss | Best-effort, packets can be lost           |
| Ordering           | In-order delivery guaranteed            | Packets can arrive out of order            |
| Speed              | Slower (per-packet overhead)            | Faster (no handshake, no overhead)         |
| Congestion control | Yes (slows under load)                  | No                                         |
| Use cases          | HTTP APIs, databases, Kafka, Redis      | Video streaming, gaming, DNS queries, VoIP |

> **💡 Tip:** Rule of thumb: TCP when correctness matters (all your backend calls). UDP when latency matters more than losing a packet — live video frames, game state updates, DNS lookups. For 99% of backend engineering work, you're using TCP.

### HTTP/1.1 vs HTTP/2 vs HTTP/3

| **Feature**           | **HTTP/1.1**                    | **HTTP/2**                        | **HTTP/3**                              |
| --------------------- | ------------------------------- | --------------------------------- | --------------------------------------- |
| Multiplexing          | No — one request per connection | Yes — multiple streams on one TCP | Yes — QUIC-based multiplexing           |
| Header compression    | None                            | HPACK compression                 | QPACK compression                       |
| Transport             | TCP                             | TCP                               | UDP (QUIC protocol)                     |
| Head-of-line blocking | Per connection                  | Per TCP connection                | Eliminated (per-stream in QUIC)         |
| Server Push           | No                              | Yes                               | Yes                                     |
| TLS                   | Optional                        | Effectively required              | Always — built into QUIC                |
| Best for              | Legacy APIs, simple services    | Modern APIs, SPAs, gRPC           | Mobile users, high-packet-loss networks |

> **📌 Note:** gRPC runs on HTTP/2, which is why it gets binary framing, multiplexed streams, and header compression for free. This is a key reason gRPC beats REST for internal microservice communication — fewer connections, less overhead.

### HTTPS and TLS

**What it is:** HTTPS = HTTP over TLS. TLS (Transport Layer Security) encrypts the channel between client and server, preventing eavesdropping and man-in-the-middle attacks.

TLS Handshake — simplified, interview-ready:

1. Client sends 'ClientHello' — supported cipher suites + a random nonce.
2. Server sends its certificate (containing its public key) + chosen cipher suite.
3. Client verifies the certificate against a trusted Certificate Authority (CA).
4. Both parties derive symmetric session keys using asymmetric crypto (ECDH or RSA key exchange).
5. All subsequent communication uses fast symmetric encryption (AES-256) with those session keys.

> **📌 Note:** TLS termination: In production (including your GKE setup), TLS is typically terminated at the load balancer or ingress controller. Internal pod-to-pod traffic runs plain HTTP, reducing CPU overhead on every service. This is standard and secure as long as your internal network is trusted.

### IPs, Ports, Sockets — Just Enough

- IP address: identifies a machine on a network (IPv4: 32-bit e.g. 10.128.0.1; IPv6: 128-bit)
- Port: identifies a process on a machine (0-65535). Common: HTTP=80, HTTPS=443, PostgreSQL=5432, Redis=6379, Kafka=9092
- Socket: IP + port combination. A TCP connection is uniquely identified by 4-tuple: (src_ip, src_port, dst_ip, dst_port)
- Why this matters: when a load balancer routes to 'backend:8080', that 8080 is the port. When you expose a Kubernetes service, you're mapping pod ports to service ports — same concept.

**Interview Q&A:**

- **Q: Walk me through what happens when you type google.com into a browser.**

  A: Browser checks its DNS cache. On miss, OS cache, then the configured recursive resolver (e.g. 8.8.8.8). Resolver traverses: root nameservers → .com TLD nameservers → Google's authoritative nameserver → returns the IP. Browser opens a TCP connection (3-way handshake: SYN, SYN-ACK, ACK) to the IP on port 443. TLS handshake establishes encrypted session. Browser sends HTTP GET /. The request likely hits a Cloudflare CDN edge node first — cache hit returns immediately. On cache miss, CDN forwards to Google's load balancer, which routes to a healthy backend. Response flows back, rendered in browser. This single question covers DNS, TCP, TLS, CDN, and load balancing all at once — it's the canonical warm-up question.

---

## 2. DNS — Domain Name System

### What DNS Does and Why It Matters

**What it is:** DNS translates human-readable domain names (api.deepta.ai) into IP addresses (34.102.136.180). It's the phonebook of the internet — but also a routing layer in its own right.

**Why it matters beyond 'looks up IPs':**

- Multi-region routing: Geo-DNS routes Mumbai users to your GKE Asia cluster, Frankfurt users to EU cluster
- Failover: health-check-aware DNS (Route53 health checks) removes a dead endpoint from responses
- Load distribution: DNS round-robin across multiple IPs

### DNS Resolution Flow — Step by Step

1. Browser checks its own DNS cache (TTL-gated).
2. OS checks its DNS cache and /etc/hosts file.
3. Query goes to configured Recursive Resolver (your ISP's resolver or 8.8.8.8).
4. Resolver checks its cache. On miss: queries Root Nameservers (.) — returns addresses of .com TLD servers.
5. Resolver queries .com TLD nameservers — returns Google's authoritative nameservers (ns1.google.com etc).
6. Resolver queries Google's authoritative nameserver — returns A record (IP address).
7. Resolver caches result for TTL seconds. Returns IP to OS, OS returns to browser.

> **📌 Note:** Record types to know: A (IPv4), AAAA (IPv6), CNAME (alias to another domain — cannot be at zone apex), MX (mail), TXT (SPF, DKIM, domain verification), NS (delegate to nameserver), SOA (start of authority metadata).

### TTL and DNS Caching

TTL (Time to Live): how long resolvers and browsers cache a DNS record. Low TTL = fast propagation, more DNS queries. High TTL = fewer queries, slow to update.

- Standard TTL: 300–3600 seconds (5 min to 1 hour)
- Pre-migration: lower TTL to 30–60s 24 hours in advance so changes propagate instantly during cutover
- High-traffic stable services: 3600s — reduces DNS query load significantly

> **⚠️ Warning:** You cannot forcibly expire cached DNS from client machines. If your TTL is 3600 and you need emergency failover, some clients will hit the old IP for up to an hour. Always lower TTL before planned changes.

### Geo-DNS and DNS-Based Load Balancing

Geo-DNS routes DNS queries based on the geographic location of the querying IP. Same domain, different IPs returned depending on where the user is.

- Tools: AWS Route53 latency-based routing, Cloudflare load balancing, Google Cloud DNS geo policies
- Limitation: DNS doesn't know server load — routes by geography or latency estimate, not current utilisation
- Combine with health checks: Route53 removes unhealthy endpoints from DNS responses (detection takes 30-90 seconds)

**Interview Q&A:**

- **Q: How does a request reach your server?**

  A: DNS resolves the domain via the resolution chain: browser cache → OS → recursive resolver → root → TLD → authoritative nameserver returns IP. If using Geo-DNS, the authoritative nameserver returns the IP of the nearest regional cluster. The IP points to our load balancer (or CDN edge). TCP connection established, TLS handshake occurs (terminated at the LB/ingress), HTTP request forwarded to a healthy pod in our GKE cluster. The LB picked the pod using the configured algorithm (e.g., least connections).

---

## 3. CDN — Content Delivery Network

### What a CDN Is and What It Caches

**What it is:** A globally distributed network of edge servers that cache content close to end users, reducing latency and load on your origin servers. Cloudflare has 300+ edge locations; CloudFront has 450+.

What CDNs cache:

- Static assets: JavaScript bundles, CSS, images, fonts, videos — the primary use case
- API responses: public, cacheable GET endpoints (product catalogue, university programme listings, public config)
- Rendered HTML pages (SSR apps, marketing sites)

What CDNs should NOT cache:

- Authenticated/personalised responses (set Cache-Control: private)
- POST/PUT/DELETE responses (CDNs don't cache non-GET requests)
- Real-time or per-user dynamic data (fraud scores, live inventory, session-specific content)

### Push CDN vs Pull CDN

|                   | **Push CDN**                                      | **Pull CDN**                                          |
| ----------------- | ------------------------------------------------- | ----------------------------------------------------- |
| How it works      | You proactively upload content to CDN edge nodes  | CDN fetches from origin on first request, then caches |
| Best for          | Large known static files, video assets            | Sites with unpredictable access patterns              |
| Freshness control | You control exactly when content is updated       | TTL-based expiry + Cache-Control headers              |
| Cold start        | No — content pre-populated                        | Yes — first request per edge node hits origin         |
| Example           | Manual S3 → CloudFront distribution               | Cloudflare (default mode), most CDN setups            |
| Drawback          | Must push every update; can go stale if forgotten | First-hit latency to origin on each new edge node     |

### Cache-Control Headers

- Cache-Control: public, max-age=86400 — cache for 24 hours by any intermediary (CDN + browser)
- Cache-Control: private, max-age=300 — cache only in user's browser, NOT in CDN
- Cache-Control: no-cache — must revalidate with origin before serving (uses ETag/Last-Modified)
- Cache-Control: no-store — never cache anywhere (payment pages, auth tokens, sensitive data)
- s-maxage=3600 — overrides max-age for shared caches (CDN) specifically; browser uses max-age

> **💡 Tip:** Best practice for Deepta AI's JS bundle: set Cache-Control: public, max-age=31536000, immutable. Use content hashing in filenames (main.a3f7c9.js). When you deploy, filename changes, CDN sees a new URL and fetches fresh. Old users automatically get the new version on next load.

### Why Not Just Use Redis Instead?

- Redis caches inside your data centre — reduces DB load but not geographic latency
- CDN caches at 300+ global edge nodes — reduces latency for users physically distant from your server
- CDN also offloads bandwidth from your origin servers; Redis doesn't
- They are complementary: Redis for backend-tier caching (expensive DB queries, session data), CDN for user-facing static and semi-static content

**Interview Q&A:**

- **Q: How does a CDN work and when would you not use one?**

  A: A CDN caches content at globally distributed edge nodes. DNS (often Anycast or Geo-DNS) routes users to the nearest edge. On cache hit, the edge serves directly — zero origin load, low latency. On cache miss, the edge fetches from origin, caches per Cache-Control headers, then serves. I wouldn't use a CDN for: authenticated or personalised API responses (risk of serving user A's data to user B), highly dynamic data where staleness is unacceptable (fraud scores, live inventory, real-time pricing), or internal microservice traffic where a CDN adds no value and unnecessary complexity.

---

## 4. Load Balancers

### What a Load Balancer Does and Why It's Needed

A load balancer distributes incoming requests across multiple backend servers, preventing any single instance from becoming a bottleneck. Without it, horizontal scaling is useless — all traffic still hits one server.

- Distributes requests across healthy backend instances
- Detects failures via health checks and stops routing to unhealthy instances
- Presents a single stable IP/hostname to clients, abstracting backend topology
- Enables zero-downtime deployments: drain connections from old pods, new pods come up, traffic shifts

### Layer 4 vs Layer 7 Load Balancers

| **Dimension**        | **L4 (Transport Layer)**                   | **L7 (Application Layer)**                       |
| -------------------- | ------------------------------------------ | ------------------------------------------------ |
| Operates on          | TCP/UDP packets (IP + port)                | HTTP headers, URLs, cookies, body                |
| Speed                | Faster — no content inspection needed      | Slightly slower — parses requests                |
| Routing intelligence | Source IP and destination port only        | Path, host header, HTTP method, cookie           |
| Sticky sessions      | IP hash only                               | Cookie-based (more reliable, survives IP change) |
| TLS termination      | Usually passthrough (encrypted to backend) | Yes — decrypts, inspects, optionally re-encrypts |
| Use cases            | Non-HTTP TCP services (databases), raw UDP | REST APIs, gRPC, microservices, WebSockets       |
| Examples             | AWS NLB, HAProxy in TCP mode               | Nginx, AWS ALB, GCP HTTP(S) LB, Kong             |

> **📌 Note:** Your GKE Ingress controller (Nginx or GCP HTTP(S) LB) is an L7 load balancer. It routes traffic based on host headers and URL paths — path-based routing across your microservices. This is something you operate daily.

### Load Balancing Algorithms

#### Round Robin

Requests distributed sequentially across servers: S1 → S2 → S3 → S1 → ... Simple, stateless, no overhead.

- Problem: assumes all requests have equal cost. A 5ms health check and a 2s ML inference are treated identically.
- Use when: requests are homogeneous and servers are equally sized.

#### Weighted Round Robin

Servers get weights proportional to capacity. A server with weight 3 gets 3x the requests of a server with weight 1.

- Better than round robin for heterogeneous fleets
- Still doesn't account for current load — a heavy server with weight 3 and 80% CPU gets the same traffic as an idle one

#### Least Connections

Route to the server with the fewest active connections. LB must track open connection count per server.

- Excellent when request processing time varies significantly — prevents hot servers
- Ideal for: ML inference endpoints, large SQL queries, streaming responses
- Requires stateful tracking at the LB

#### IP Hash (and Consistent Hashing)

Hash the client IP (or a session key) to deterministically select a server. Same client always goes to the same server.

- Enables sticky sessions without cookies — critical for WebSocket connections
- Plain IP hash flaw: adding or removing a server rehashes most clients, causing mass session disruption
- Consistent hashing fix: when a server is added/removed, only K/N clients reroute (K = affected keys, N = server count). Much less disruption.
- Consistent hashing is also how Kafka assigns partitions to consumers and how Redis Cluster shards keys — same mental model across the stack.

### Health Checks

Load balancers continuously probe backends to detect failures and route around them automatically.

- Active health check: LB sends periodic GET /health requests every 10-30s
- Mark unhealthy after: 2-3 consecutive failures (to avoid flapping on brief blips)
- Mark healthy after: 2-3 consecutive successes (gradual warm-up)
- Passive health check: LB observes real traffic — if backend returns 5xx repeatedly, mark unhealthy
- Kubernetes integration: Kubernetes readinessProbe ensures pods only receive traffic when truly ready. Your GKE deployments should already have this.

### Active-Active vs Active-Passive

|               | **Active-Active**                    | **Active-Passive**                                   |
| ------------- | ------------------------------------ | ---------------------------------------------------- |
| All servers   | Serving traffic simultaneously       | One or more on standby                               |
| Utilisation   | High — full capacity used            | Low — standby wastes resources                       |
| Failover time | Instant (traffic simply reroutes)    | Seconds to minutes (passive must activate)           |
| Complexity    | Higher — sessions must be shareable  | Lower — simpler state model                          |
| Use case      | Stateless microservices, API servers | Databases (primary/replica failover, Redis Sentinel) |

### Making Load Balancers Themselves Highly Available

The irony: the LB is a single point of failure. Solutions:

- LB pair with VIP (Virtual IP): two LB instances share a virtual IP. Primary handles traffic; if it dies, secondary claims the VIP via VRRP protocol. Failover in seconds.
- Cloud-managed LBs (AWS ALB, GCP HTTP(S) LB): the cloud provider runs multiple LB nodes behind the scenes. You never see this — it's invisible and always-on.
- Anycast IP: traffic is routed at the BGP level to the nearest healthy LB node globally. Used by Cloudflare and large CDNs.

**Interview Q&A:**

- **Q: What load balancing algorithm would you use and why?**

  A: For stateless REST APIs with uniform request sizes: Round Robin — simple, no overhead. For variable processing times (some endpoints do Redis lookups in 5ms, others run complex DB queries in 500ms): Least Connections — prevents slow backends from accumulating a backlog. For WebSocket connections or any stateful protocol: Consistent Hashing for sticky sessions. For a mixed-capacity fleet: Weighted Round Robin or Weighted Least Connections. I'd avoid plain IP Hash at scale — Consistent Hashing is strictly better because server additions only reroute K/N clients rather than nearly all clients.

---

## 5. API Design

### REST Principles

REST (Representational State Transfer) is an architectural style for distributed systems. Key constraints that make an API RESTful:

- Stateless: every request must contain all information needed to process it. No server-side session state. JWTs satisfy this; server-side sessions do not.
- Uniform interface: resource-based URLs, consistent HTTP methods, standard response structure
- Client-server separation: UI and backend evolve independently — the embeddable SDK doesn't need to know your internal microservice topology
- Cacheable: responses explicitly declare whether they can be cached (Cache-Control headers)

### REST Best Practices

#### HTTP Methods — Use Them Semantically

| **Method** | **Operation**                  | **Example**                  | **Idempotent?** |
| ---------- | ------------------------------ | ---------------------------- | --------------- |
| GET        | Read resource                  | GET /universities/42         | Yes             |
| POST       | Create resource                | POST /applications           | No              |
| PUT        | Replace resource (full update) | PUT /applications/7          | Yes             |
| PATCH      | Partial update                 | PATCH /applications/7/status | Depends on impl |
| DELETE     | Delete resource                | DELETE /applications/7       | Yes             |

#### Status Codes — The Key Ones

| **Code** | **Meaning**           | **When to Return**                                             |
| -------- | --------------------- | -------------------------------------------------------------- |
| 200      | OK                    | Successful GET, PUT, PATCH with response body                  |
| 201      | Created               | Successful POST — include Location: /resource/id header        |
| 204      | No Content            | Successful DELETE, or PUT/PATCH with no body needed            |
| 400      | Bad Request           | Malformed JSON, missing required fields, validation failure    |
| 401      | Unauthorised          | Missing or invalid auth token (JWT expired, invalid signature) |
| 403      | Forbidden             | Authenticated but not permitted (wrong role, wrong tenant)     |
| 404      | Not Found             | Resource doesn't exist                                         |
| 409      | Conflict              | Duplicate resource creation, optimistic lock conflict          |
| 422      | Unprocessable Entity  | Valid JSON syntax but semantic error (invalid enum value)      |
| 429      | Too Many Requests     | Rate limit exceeded — include Retry-After header               |
| 500      | Internal Server Error | Unhandled exception — never expose internal details            |
| 503      | Service Unavailable   | Temporarily overloaded or in maintenance — include Retry-After |

#### Pagination

- Offset-based: GET /applications?limit=20&offset=40 — simple but DB scans all rows to skip offset. Slow at high offsets.
- Cursor-based: GET /applications?after=eyJpZCI6NDJ9 (base64 encoded last ID/timestamp) — constant time regardless of page. Used by Stripe, Twitter, Facebook Graph API.
- Use cursor-based for any list that could grow large. Offset-based is fine for admin tools with small datasets.

#### API Versioning Strategies

| **Strategy**        | **Example**                         | **Trade-offs**                                                  |
| ------------------- | ----------------------------------- | --------------------------------------------------------------- |
| URI versioning      | GET /v1/universities                | Simple, visible, easy to route. Breaking changes need new path. |
| Header versioning   | Accept-Version: v2                  | Clean URLs, but harder to test in browser / Postman             |
| Query parameter     | GET /universities?version=2         | Explicit but pollutes query params; often skipped in logs       |
| Content negotiation | Accept: application/vnd.app.v2+json | Purist REST but complex; rarely seen in practice                |

> **💡 Tip:** URI versioning is the most common in practice. It's explicit, browser-testable, easy to route in API gateways (strip the /v1 prefix before forwarding to services), and visible in access logs. Start with this.

### GraphQL

**What it is:** A query language for APIs where clients specify exactly what data they need. One /graphql endpoint replaces dozens of REST endpoints. The schema is the contract.

**Why it exists** — REST's two problems:

- Over-fetching: GET /users/1 returns 20 fields; you needed 3. Waste on mobile.
- Under-fetching: you need user + their applications + their university — 3 REST calls. In GraphQL, one query.

- **Pros: **Exactly the data you need; single endpoint; self-documenting schema via introspection; one call instead of N; great for mobile where payload size matters
- **Cons: **Caching is hard (all queries are POST requests; can't use HTTP caching layers); N+1 query problem unless you use DataLoader; complex queries can overload DB; steeper initial setup; harder to version

### gRPC

**What it is:** A high-performance RPC framework from Google. You define services in Protocol Buffers (.proto files); gRPC generates client and server code in your language. Runs over HTTP/2.

**Why it wins** for internal service-to-service communication:

- Binary Protobuf serialisation: 5-10x smaller payloads than JSON, faster to parse
- Strongly typed: .proto schema is the contract. Type mismatches are compile-time errors, not runtime surprises.
- HTTP/2 multiplexing: multiple RPC calls on one TCP connection, no head-of-line blocking
- Native streaming: client-streaming, server-streaming, and bidirectional streaming out of the box

- **Pros: **Low latency, low bandwidth, strongly typed, streaming support, great for polyglot microservices
- **Cons: **Binary format — can't curl or read in browser without tooling; browser support needs grpc-web wrapper; schema management overhead for large teams

### REST vs GraphQL vs gRPC — Decision Matrix

| **Dimension**   | **REST**                      | **GraphQL**                          | **gRPC**                |
| --------------- | ----------------------------- | ------------------------------------ | ----------------------- |
| Data format     | JSON                          | JSON (query-defined shape)           | Protobuf (binary)       |
| Transport       | HTTP/1.1 or HTTP/2            | HTTP/1.1 or HTTP/2                   | HTTP/2 only             |
| Typing          | None (OpenAPI optional)       | Schema-typed                         | Strongly typed (.proto) |
| HTTP caching    | Easy (GET + Cache-Control)    | Hard (all POST requests)             | Not native              |
| Browser support | Native                        | Native                               | Needs grpc-web          |
| Streaming       | No (use SSE or WebSocket)     | Subscriptions (WebSocket under hood) | Native bidirectional    |
| Best for        | Public APIs, external clients | Product APIs, multi-client           | Internal microservices  |

**Interview Q&A:**

- **Q: REST vs GraphQL vs gRPC — when would you use each?**

  A: REST for public-facing APIs: Deepta AI's embeddable SDK exposes REST because university developers don't want to deal with Protobuf schemas. REST is simple, cacheable, browser-native. gRPC for internal microservice communication: in PayGuard AI, the Transaction Behaviour agent calling the Decision Agent should use gRPC — binary serialisation, lower latency, strongly typed contracts. GraphQL when you have multiple client types with divergent data needs: a web dashboard, mobile app, and embedded widget all need different shapes of the same student data — GraphQL lets each client ask for exactly what it needs, and one endpoint replaces many REST routes.

### Idempotency

**What it is:** An operation is idempotent if executing it once produces the same result as executing it N times. DELETE /orders/7 is idempotent: whether the order exists or was already deleted, the outcome is the same.

**Why it matters**:

- Network failures cause automatic retries. Without idempotency, a retry can double-charge a user or create duplicate records.
- Kafka consumers use at-least-once delivery — your consumer will process some messages more than once. The handler must be idempotent.

Idempotency key pattern (used by Stripe, Razorpay):

1. Client generates a UUID: Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
2. Server stores the key + response in Redis with a 24-hour TTL.
3. On duplicate key: return the cached response without reprocessing. Client gets the same result.
4. Key expires after 24h — client must regenerate for genuinely new operations.

> **⚠️ Warning:** PayGuard AI: your fraud analysis endpoint should use idempotency keys. If the LangGraph multi-agent pipeline partially completes and the client retries, you don't want to re-run the full pipeline and possibly get a different fraud verdict on the same transaction.

---

## 6. API Gateway

### What an API Gateway Does

An API gateway is a single entry point for all client requests. It handles cross-cutting concerns that every service would otherwise implement independently — avoiding duplication across dozens of microservices.

- Request routing: forward /users/_ to user service, /fraud/_ to PayGuard AI service
- Authentication: validate JWT or API key before the request ever reaches a service
- Rate limiting: reject requests exceeding per-user or per-endpoint quotas
- Request/response transformation: strip internal headers, add correlation IDs, translate REST → gRPC
- Centralised logging and distributed tracing (correlation ID injected at gateway)
- SSL/TLS termination: decrypt once; internal traffic is plain HTTP
- Circuit breaking: stop forwarding to a service that's consistently failing

### API Gateway vs Load Balancer — Key Differences

| **Dimension**        | **API Gateway**                                             | **Load Balancer**                                   |
| -------------------- | ----------------------------------------------------------- | --------------------------------------------------- |
| Primary purpose      | Cross-cutting concerns (auth, rate limiting, routing logic) | Distribute traffic across healthy backend instances |
| Request awareness    | Full HTTP — methods, headers, body, path                    | L4: IP+port only; L7: URL and headers               |
| Authentication       | Yes — validates JWT, API keys                               | No                                                  |
| Rate limiting        | Yes — per user, per endpoint, per tier                      | No                                                  |
| Protocol translation | Yes (REST → gRPC, HTTP/1 → HTTP/2)                          | No                                                  |
| Health-based routing | Basic                                                       | Core function with sophisticated health checks      |
| Examples             | Kong, AWS API Gateway, Nginx+Lua, Envoy                     | Nginx (plain), AWS ALB/NLB, HAProxy, GCP LB         |

> **💡 Tip:** In most production architectures, both exist: the Load Balancer sits in front for traffic distribution across API Gateway instances; the API Gateway handles application-layer concerns. Sometimes they're combined in one tool (Kong acts as both).

### BFF — Backend for Frontend

**What it is:** Instead of one API serving all clients (web, mobile, embedded SDK), you create a dedicated API layer per client type. Each BFF aggregates, shapes, and optimises data specifically for its frontend.

When the BFF pattern makes sense:

- Multiple client types with divergent data needs — mobile needs minimal data, web dashboard needs rich detail
- Different auth mechanisms per client — JWT for web app, API key for SDK, session cookie for admin portal
- Reducing round trips on mobile — BFF aggregates 5 microservice calls into one mobile-optimised response
- Isolating client-specific logic so backend services stay generic

Deepta AI use case: the embeddable JS SDK for university portals is a perfect BFF target. The SDK's BFF handles university authentication (API key), aggregates student + application + university data, and returns the exact shape the widget needs — without exposing raw internal microservices to third-party university portals.

**Interview Q&A:**

- **Q: What is the BFF pattern and when does it make sense?**

  A: BFF means creating a dedicated API layer per client type rather than one generic API serving all. It makes sense when: clients have meaningfully different data requirements (mobile vs web vs embedded widget), different auth mechanisms per client, or when you need to aggregate multiple microservice calls into client-optimised responses. The cost is maintaining multiple BFF services — worth it when clients are genuinely different, overkill for a single-client product. At companies like Spotify and Netflix, the BFF pattern is standard — each app team owns their BFF.

**Interview Q&A:**

- **Q: What is an API Gateway and what does it do that a load balancer doesn't?**

  A: An API gateway handles cross-cutting application-layer concerns: JWT validation, rate limiting per user and endpoint, path-based routing, protocol translation, and centralised logging. A load balancer's job is traffic distribution — routing requests across healthy backend instances using health checks and a balancing algorithm. The gateway understands your application semantics; the LB understands network-layer routing. In production, both coexist: the LB distributes across multiple gateway instances; the gateway handles everything above the transport layer.

---

## 7. Forward Proxy vs Reverse Proxy

### Forward Proxy — Serves the Client

A forward proxy sits in front of clients and makes requests on their behalf. The destination server sees the proxy's IP, not the original client's IP.

- Clients know about the forward proxy and are configured to use it
- Use cases: corporate internet filtering (block social media on work network), VPNs, anonymising traffic, accessing geo-restricted content
- Examples: Squid proxy, enterprise HTTP proxies, VPN exit nodes

### Reverse Proxy — Serves the Server

A reverse proxy sits in front of servers and accepts requests on their behalf. Clients don't know which server they're talking to — they just see the proxy's address.

- Clients are completely unaware of the reverse proxy — it's transparent
- Use cases: SSL/TLS termination, static asset caching, request routing, hiding internal topology, DDoS protection
- Examples: Nginx, HAProxy, Cloudflare (which is a massive distributed reverse proxy), AWS ALB

### Reverse Proxy vs Load Balancer

A load balancer is a specialised type of reverse proxy, but not all reverse proxies are load balancers.

|                             | **Reverse Proxy**                                     | **Load Balancer**                                   |
| --------------------------- | ----------------------------------------------------- | --------------------------------------------------- |
| Core job                    | Intercept and forward requests (can be to one server) | Distribute requests across multiple healthy servers |
| Requires multiple backends? | No — can proxy to a single origin                     | Yes — requires multiple backends to balance across  |
| Health checks               | Optional (depends on tool/config)                     | Core feature — integral to routing decisions        |
| SSL termination             | Yes (Nginx ssl_certificate)                           | Yes (L7 LB; L4 is passthrough)                      |
| Caching                     | Yes (Nginx proxy_cache)                               | Not typically                                       |
| Relationship                | LB is a reverse proxy that adds load distribution     | Subset of reverse proxy functionality               |

**Interview Q&A:**

- **Q: What is a reverse proxy and how is it different from a load balancer?**

  A: A reverse proxy intercepts client requests and forwards them to one or more backends — it's transparent to clients. Responsibilities include SSL termination, caching, request transformation, and hiding internal server topology. A load balancer is a reverse proxy specialised in distributing requests across multiple healthy servers using health checks and a routing algorithm. Every load balancer is a reverse proxy; not every reverse proxy balances load. Nginx can act as either: as a caching reverse proxy to one backend, or as a round-robin load balancer across ten.

---

## 8. Rate Limiting

### Why Rate Limiting Is Needed

- DoS/DDoS protection: prevent one client from exhausting server resources and starving everyone else
- Fair use: ensure heavy users don't degrade service for others
- Cost control: LLM API calls, ML inference, and third-party APIs cost money per call — cap usage per user
- Business rules: freemium tiers (100 API calls/day on free plan, unlimited on paid)

### Rate Limiting Algorithms

#### Token Bucket

A bucket holds N tokens. Each request consumes 1 token. Tokens are added at a fixed refill rate (e.g., 10 tokens/second). If the bucket is empty, the request is rejected.

- Allows bursting: if idle for 10 seconds, you accumulate 100 tokens and can burst 100 requests instantly
- Best for: APIs where occasional bursts are acceptable (batch uploads, bulk API calls)
- Parameters: bucket capacity (burst size) and refill rate (sustained rate)

#### Leaky Bucket

Requests go into a FIFO queue (the bucket). They are processed at a fixed constant rate (they 'leak' out). If the queue is full, new requests are rejected.

- Output rate is always constant — regardless of burst input. Smooths traffic.
- Good for: rate-controlling outgoing calls to external APIs (SMS at max 10/sec to avoid provider throttling)
- Key difference from token bucket: leaky bucket does NOT allow bursting; token bucket does

#### Fixed Window Counter

Divide time into fixed windows (e.g., each minute). Count requests per window. If count exceeds limit, reject.

- Simplest to implement: Redis INCR with EXPIRE
- Fatal flaw: boundary exploit — if limit is 100/min, a client can send 100 at :59 and 100 at :01 = 200 requests in 2 seconds
- Acceptable for loose rate limiting where the boundary exploit isn't critical

#### Sliding Window Log

Store a timestamp for every request. For each new request, count all timestamps within the last N seconds.

- Most accurate — no boundary problem
- Memory intensive: O(requests per window) storage per user
- Redis: use a sorted set — ZADD timestamp, ZREMRANGEBYSCORE to evict old entries, ZCARD to count
- Best for: strict compliance limits where accuracy is critical (financial APIs, medical data APIs)

#### Sliding Window Counter — The Production Choice

Approximate a sliding window using two fixed-window counters, weighted by position within the current window.
Formula: effective_count = prev_window_count × (1 − elapsed_fraction) + current_window_count

- Memory: constant — just two counters per user
- Accuracy: within ~1% of true sliding window — good enough for all practical purposes
- Used by: Cloudflare, most production API gateways
- Best default choice for distributed rate limiting

### Where to Implement Rate Limiting

| **Layer**     | **Location**                               | **Best For**                                                |
| ------------- | ------------------------------------------ | ----------------------------------------------------------- |
| CDN/Edge      | Cloudflare WAF rules, CloudFront functions | DDoS, bot traffic — stopped before reaching origin          |
| API Gateway   | Kong, AWS API Gateway, Nginx rate_limit    | Global policy across all services — standard choice         |
| Service level | In each microservice (middleware)          | Fine-grained per-endpoint business rules                    |
| Client-side   | SDK or mobile app                          | Reducing unnecessary network calls — not a security control |

### Distributed Rate Limiting — The Hard Part

Challenge: with 10 API servers, each server sees only 1/10 of total traffic. A per-server limit of 100 req/min allows 1000 req/min cluster-wide — 10x more than intended.

Solutions:

- Centralised Redis counter (standard): every server increments a shared Redis key atomically on each request. INCR with EXPIRE for fixed window; sorted set for sliding window. Single Redis adds ~1ms latency per request.
- Redis Lua script: execute check-and-increment atomically in one round-trip. Prevents TOCTOU race conditions.
- Local token bucket + Redis sync: each server has a local token bucket. Only hits Redis when local bucket approaches empty. Reduces Redis calls by 80-90%.
- Sticky routing (consistent hashing): route by user ID so each server owns its users' rate limits locally. Zero Redis overhead. Slightly less flexible for failover.

Redis sliding window implementation:
MULTI
ZADD user:{id}:reqs {now_ms} {uuid} -- add current request
ZREMRANGEBYSCORE user:{id}:reqs 0 {now_ms - window_ms} -- evict old
ZCARD user:{id}:reqs -- count in window
EXPIRE user:{id}:reqs {window_seconds} -- auto-cleanup
EXEC

**Interview Q&A:**

- **Q: How would you design a rate limiter?**

  A: I'd implement a sliding window counter using Redis. For each user (identified by API key or JWT sub), maintain a sorted set where entries are request UUIDs and scores are millisecond timestamps. On each request: ZADD current timestamp, ZREMRANGEBYSCORE to evict entries older than the window, ZCARD to get count. If count > limit, return 429 with Retry-After header. Wrap all four commands in a MULTI/EXEC pipeline for atomicity. For high-throughput paths, add a local token bucket per server as a fast-path — only hit Redis when the local bucket runs low, reducing Redis calls by ~80%. Expose the rate limit state in response headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset.

**Interview Q&A:**

- **Q: How would you implement rate limiting across a distributed system?**

  A: The challenge is that each server sees only 1/N of traffic. Fix: centralised rate limit state in Redis. Each server, before processing a request, atomically checks and increments the counter in Redis using a pipelined ZADD + ZREMRANGEBYSCORE + ZCARD. Redis ensures consistency. For latency-sensitive APIs, use a two-tier approach: lightweight local token bucket as fast path (no Redis call for most requests), only check Redis when local bucket is depleted. For extreme scale, sticky routing via consistent hashing on user ID lets each server own its users' rate limits locally — zero Redis overhead at the cost of some failover complexity.

---

## 9. WebSockets

### What WebSockets Are

WebSockets provide a persistent, full-duplex (bidirectional) communication channel over a single TCP connection. Unlike HTTP (request → response → connection idle), either side can send a message at any time after the initial handshake.

### The WebSocket Handshake

1. Client sends HTTP GET with Upgrade: websocket and Sec-WebSocket-Key: <base64-nonce> headers.
2. Server responds with 101 Switching Protocols and Sec-WebSocket-Accept: <derived-key>.
3. The underlying TCP connection stays open. Both sides switch to WebSocket framing.
4. Either side can now send frames (text or binary) at any time — no request needed.

> **📌 Note:** The upgrade handshake is standard HTTP — it passes transparently through load balancers and firewalls. This is why WebSockets work on port 443 (wss://) without special network configuration.

### Use Cases

- Real-time chat: WhatsApp Web, Slack — messages pushed to all connected clients immediately
- Live data feeds: stock tickers, sports scores, order book updates on trading platforms
- Collaborative editing: Google Docs, Figma — all participants receive edits in real-time
- Multiplayer games: game state synchronised across all players
- Fraud alert streaming: in PayGuard AI, push fraud score updates to the HumanGate UI as each LangGraph agent completes, rather than waiting for the full pipeline

### When NOT to Use WebSockets

- Server-to-client only (unidirectional): use SSE — simpler, native HTTP/2, auto-reconnect built in
- Infrequent updates (one notification per hour): long polling or webhooks are sufficient and cheaper
- Stateless request-response pattern: plain HTTP handles this better; WebSocket overhead is wasted
- When you need CDN caching: WebSocket messages cannot be cached

### Scaling WebSocket Servers

The fundamental challenge: WebSockets are stateful. Each client is connected to one specific server. If you have 10 servers and user A is on server 1, user B on server 2, and they need to exchange messages — server 1 must somehow deliver to server 2's client.

- Sticky sessions: configure L7 load balancer to use cookie-based session affinity. All messages from one client always reach the same server. Problem: server failures disconnect all its clients.
- Redis Pub/Sub (the standard pattern): when server 1 receives a message for user B, it publishes to a Redis channel (e.g., user:B:messages). Server 2 subscribes to that channel and delivers to user B's WebSocket. This decouples servers completely — any server can serve any user.
- Horizontal scaling: with Redis Pub/Sub, you can run any number of WebSocket servers. Redis is the message bus.

> **📌 Note:** Redis Pub/Sub vs Kafka for WebSocket relay: Redis Pub/Sub is fire-and-forget (no message persistence), very low latency (~1ms), simple. Kafka has durability and replay but more overhead. For real-time chat relay where you don't need missed-message replay, Redis wins. For fraud alerts where every alert must be delivered reliably, put them in Kafka first.

### Connection Management

- Heartbeats: send WebSocket ping frames every 30 seconds. Close connection if no pong within 10 seconds. Detects dead connections that TCP keepalives miss.
- Client reconnection: exponential backoff (500ms → 1s → 2s → 4s → max 30s). Randomised jitter prevents thundering herd after server restart.
- Connection limits: each WebSocket holds a TCP connection and a file descriptor. At 100k concurrent connections, tune ulimit (fs.file-max on Linux). A single Nginx instance can handle 100k+ connections with proper tuning.

**Interview Q&A:**

- **Q: How do WebSockets work and when would you use them over polling?**

  A: WebSockets start as HTTP: client sends Upgrade: websocket, server responds 101, the TCP connection is promoted to a persistent bidirectional channel. Either side can send frames at any time with no per-message overhead. Use WebSockets when: (1) the server needs to push data frequently without the client asking, (2) latency matters — each polling request has HTTP overhead (headers, connection setup), (3) bidirectional communication is needed (chat, collaborative editing). Prefer SSE for server-to-client-only streams (simpler, HTTP/2-native, auto-reconnect). Prefer polling when updates are rare (every few minutes) — WebSocket overhead doesn't justify itself at low frequency.

---

## 10. Server-Sent Events (SSE)

### What SSE Is

SSE is a one-way server-to-client streaming protocol that runs over plain HTTP. The client makes a single GET request with Accept: text/event-stream; the server keeps the connection open and sends newline-delimited events whenever data is available.

### SSE vs WebSockets

| **Dimension**    | **SSE**                                        | **WebSocket**                              |
| ---------------- | ---------------------------------------------- | ------------------------------------------ |
| Direction        | Server → Client only                           | Bidirectional (both directions)            |
| Protocol         | Plain HTTP (text/event-stream)                 | Custom WebSocket framing (ws:// or wss://) |
| HTTP/2 native    | Yes — multiplexed on existing connection       | Separate connection per socket             |
| Auto-reconnect   | Built in — browser reconnects automatically    | Must implement manually in client code     |
| Setup complexity | Very simple — one GET request, EventSource API | More complex lifecycle management          |
| Data format      | Text only (UTF-8 strings)                      | Text or binary frames                      |
| Proxy/firewall   | Works transparently (it's HTTP)                | May need proxy configuration               |

### Use Cases for SSE

- LLM token streaming: ChatGPT, Claude — tokens pushed via SSE as they're generated. Each token is one SSE event.
- Live dashboards: real-time metrics, monitoring feeds, analytics numbers
- Notification feeds: 'new application submitted', 'document approved', 'payment received'
- Activity feeds and social timelines
- PayGuard AI: streaming fraud analysis progress to the HumanGate UI as each LangGraph agent completes — each agent result is one SSE event. No WebSocket needed since it's server-to-client only.

### SSE vs Polling vs WebSocket vs WebHook — Full Comparison

|             | **Short Poll**           | **Long Poll**      | **SSE**             | **WebSocket**       | **WebHook**        |
| ----------- | ------------------------ | ------------------ | ------------------- | ------------------- | ------------------ |
| Direction   | C→S pull                 | C→S pull           | S→C push            | Bidirectional       | S→S push           |
| Connection  | New each poll            | Held until data    | One persistent HTTP | One persistent WS   | New per event      |
| Latency     | = polling interval       | Near real-time     | Real-time           | Real-time           | Near real-time     |
| Server load | High (many requests)     | Medium             | Low                 | Low                 | Low                |
| Complexity  | Very simple              | Simple             | Simple              | Complex             | Simple             |
| Best for    | Slow, infrequent updates | Moderate frequency | Server push streams | Chat, games, collab | B2B event delivery |

---

## 11. Polling & WebHooks

### Short Polling — Simplest, Most Wasteful

Client repeatedly asks 'any updates?' on a timer (e.g., every 2 seconds). Regardless of whether there's new data, a full HTTP request is made.

- Pros: trivially simple — setInterval + fetch; works behind any proxy or firewall
- Cons: most requests return empty; high server load at scale (1000 users × 30 req/min = 30,000 req/min for nothing)
- Use when: updates are very infrequent, real-time isn't required, or you need an MVP working today

### Long Polling — More Efficient Pull

Client sends a request; server holds the connection open until it has data to return (or a timeout fires). Client immediately sends another request after receiving a response.

- More efficient: one request per event rather than one request per polling interval
- Near-real-time: data pushed as soon as available
- Complexity: server must hold many open connections; timeout and error handling is tricky
- Was the standard real-time technique before WebSockets (Comet frameworks, Bayeux protocol)
- Still used where WebSockets can't: behind some corporate proxies that block upgrade requests

### WebHooks — Event-Driven Server-to-Server

A webhook is an HTTP callback. When an event occurs in system A, it makes an HTTP POST to a URL registered in system B, delivering the event payload. The receiver processes the event asynchronously.

- Examples: Razorpay POSTs to your /payments/webhook when payment succeeds; GitHub POSTs to your CI pipeline on PR merge; Stripe sends payment_intent.succeeded to your webhook endpoint
- Asynchronous: the sender doesn't wait for your processing — it fires and moves on
- Reliability: good webhook senders retry with exponential backoff on failure (often for 24-72 hours)
- Security: always verify the webhook signature (HMAC-SHA256 of payload with a shared secret). Reject any request without a valid signature.
- Idempotency: your webhook handler must be idempotent — delivery is at-least-once

> **📌 Note:** Deepta AI B2B integration: university portals should receive webhooks when student application status changes. They register a callback URL; you POST to it. No polling, no persistent connection. This is the standard B2B integration pattern — Salesforce, Shopify, Twilio all use it.

---

## Quick Revision Cheatsheet — Track 1

## Networking

- L4 = IP+port routing (fast, no content inspection). L7 = URL+header routing (smarter, slightly slower).
- TCP = reliable/ordered. UDP = fast/lossy. All backend services use TCP.
- HTTP/2 = multiplexed streams + binary framing. gRPC requires HTTP/2.
- TLS handshake: ClientHello → Certificate → Key exchange → Symmetric session keys → Encrypted channel.

## DNS

- Resolution chain: browser cache → OS → recursive resolver → root → TLD → authoritative NS → IP.
- Lower TTL before migrations/failover. Cannot recall cached DNS from client machines.
- Geo-DNS routes by geography, not server load. Combine with health checks for failover.

## CDN

- Pull CDN: fetches from origin on first request, caches per Cache-Control headers.
- Push CDN: pre-populate edge nodes — better for large known static files.
- Don't cache: authenticated responses (private), real-time data, personalised content.
- Content-hash filenames + max-age=31536000 = perfect long-term static asset caching.
- Redis reduces DB load (internal). CDN reduces latency (edge, global). Complementary, not competing.

## Load Balancers

- L4 LB: fast, IP+port only, no TLS termination. L7 LB: path/header routing, TLS termination.
- Round Robin: uniform requests. Least Connections: variable processing time. Consistent Hashing: sticky sessions.
- Consistent Hashing > IP Hash at scale: only K/N clients reroute when servers change.
- HA: VIP pair with VRRP, or use cloud-managed LB (AWS ALB, GCP LB) — inherently redundant.

## API Design

- REST: stateless, resource URLs, correct HTTP methods, semantic status codes. Cache-friendly.
- gRPC: binary Protobuf, HTTP/2, strongly typed contracts (.proto). Best for internal microservices.
- GraphQL: one endpoint, client specifies shape. Best for multi-client products with divergent data needs.
- Idempotency keys: client UUID → server checks Redis → return cached response on duplicate. Prevents double-processing.
- Cursor-based pagination > offset for large datasets. Offset scans all rows up to the offset.
- URI versioning (/v1/resource) is the most practical versioning strategy.

## API Gateway & Proxies

- Gateway = auth + rate limit + routing intelligence + logging. LB = traffic distribution.
- Both usually coexist in production. LB distributes across gateway instances.
- BFF: dedicated API per client type. Worth it for divergent data needs or auth models.
- Forward proxy: serves client (VPN, corporate filter). Reverse proxy: serves server (Nginx, Cloudflare).
- Every LB is a reverse proxy. Not every reverse proxy is a LB.

## Rate Limiting

- Token bucket: allows bursts (bucket fills when idle). Leaky bucket: constant output, no burst.
- Fixed window: simple but boundary exploit. Sliding window log: accurate but memory-heavy.
- Sliding window counter (hybrid): near-accurate, constant memory, used by Cloudflare. Best default.
- Distributed: centralised Redis sorted set (ZADD + ZREMRANGEBYSCORE + ZCARD in MULTI/EXEC).
- Return X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset headers with every response.

## WebSockets

- Full-duplex, persistent TCP. Starts with HTTP upgrade (101 Switching Protocols).
- Scale: sticky sessions at LB + Redis Pub/Sub as message bus between servers.
- Heartbeat: ping every 30s, close if no pong. Client: exponential backoff reconnect.
- When not to use: server-push only (use SSE), infrequent updates (use polling/webhooks).

## SSE, Polling, WebHooks

- SSE: HTTP-native S→C push. One-way. HTTP/2-native. Auto-reconnect. Text only. Use for LLM streaming, notifications, dashboards.
- Short polling: simple, wasteful. Long polling: efficient but complex. Use polling when updates are rare.
- WebHook: server-to-server event push. Verify HMAC signature. Handler must be idempotent. Retry on failure.

## The 10 Interview Questions — One-Line Answers

| **Question**                           | **Core of the Answer**                                                                                         |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| What happens when you type google.com? | DNS chain → TCP 3-way handshake → TLS handshake → HTTP GET → CDN edge (hit/miss) → LB → App                    |
| Design a rate limiter                  | Sliding window counter: Redis sorted set, ZADD+ZREMRANGEBYSCORE+ZCARD in MULTI/EXEC pipeline                   |
| REST vs GraphQL vs gRPC?               | REST=public/external (cacheable). gRPC=internal (binary, typed). GraphQL=multi-client (flexible shape).        |
| Reverse proxy vs load balancer?        | LB is a type of reverse proxy specialised in distribution. Not all reverse proxies balance load.               |
| WebSockets vs polling?                 | WS=bidirectional/real-time. SSE=server-push only. Polling for infrequent updates. Match latency to need.       |
| API Gateway vs load balancer?          | Gateway=auth+rate limit+routing logic. LB=traffic distribution. Both in prod; LB sits in front of gateway.     |
| Distributed rate limiting?             | Centralised Redis: ZADD+ZREMRANGEBYSCORE+ZCARD per user. Two-tier with local bucket for high throughput.       |
| Load balancing algorithm?              | Variable request cost → Least Connections. Sticky sessions needed → Consistent Hashing. Uniform → Round Robin. |
| CDN — when not to use?                 | Skip CDN for authenticated/personalised responses, real-time dynamic data, or internal microservices.          |
| BFF pattern?                           | Dedicated API per client type. Use when clients have divergent data needs or different auth mechanisms.        |

_Track 1 Complete · System Design Self-Study Series · Gautham Gokulakonda · 5 Tracks Total_
