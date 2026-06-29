# Part 15.1: Microservices Architecture

## What You'll Learn

- When to use microservices vs monoliths (and why many teams get this wrong)
- How to decompose a system into services using Domain-Driven Design
- Inter-service communication patterns: synchronous vs asynchronous
- API Gateway and Backend-for-Frontend (BFF) patterns
- Service discovery, load balancing, and service mesh
- Production-ready implementations in Go+Chi, Node.js+Express, and Python+FastAPI

---

## Table of Contents

1. [Monolith vs Microservices](#1-monolith-vs-microservices)
2. [The Modular Monolith — Best of Both Worlds](#2-the-modular-monolith)
3. [Service Decomposition with DDD](#3-service-decomposition-with-ddd)
4. [Database Per Service Pattern](#4-database-per-service-pattern)
5. [Inter-Service Communication](#5-inter-service-communication)
6. [API Gateway Pattern](#6-api-gateway-pattern)
7. [Backend for Frontend (BFF)](#7-backend-for-frontend-bff)
8. [Service Discovery](#8-service-discovery)
9. [Load Balancing Strategies](#9-load-balancing-strategies)
10. [Service Mesh](#10-service-mesh)
11. [How It Works Internally (ASCII Diagrams)](#11-how-it-works-internally)
12. [Implementation Examples](#12-implementation-examples)
13. [Common Patterns & Best Practices](#13-common-patterns--best-practices)
14. [Common Pitfalls](#14-common-pitfalls)
15. [Interview Questions & Answers](#15-interview-questions--answers)
16. [Resources](#16-resources)

---

## 1. Monolith vs Microservices

### The Monolith

A monolith is a single deployable unit where all business logic, data access, and UI (or API) are bundled together and deployed as one artifact.

```
┌─────────────────────────────────────────────────────────────┐
│                      MONOLITH                               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  User Module │  │ Order Module │  │ Payment Module   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│        │                  │                   │             │
│  ┌─────▼──────────────────▼───────────────────▼─────────┐  │
│  │                 Shared Database                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Advantages of a Monolith:**

- **Simple to develop initially** — no network calls between components, easy debugging, single IDE project
- **Atomic transactions** — everything in the same DB means ACID transactions across the whole domain
- **Simple deployment** — one artifact to deploy, one place to look at logs
- **No distributed systems complexity** — no network partitions, no eventual consistency
- **Simple testing** — unit and integration tests without mocking remote services

**When a monolith is the right choice:**

1. **Small team** — fewer than 8–10 engineers; microservices require coordination overhead
2. **Early stage / unclear domain** — you don't yet know your bounded contexts well; splitting prematurely creates wrong boundaries that are expensive to fix
3. **Low traffic** — a single well-tuned monolith can handle millions of requests per day
4. **Time to market** — microservices take 2–3x longer to bootstrap

**When a monolith starts to hurt:**

- Build times are > 10 minutes; everyone is waiting on CI
- Deploying one feature requires testing the entire app
- Different modules need to scale differently (e.g., notification service needs more I/O, payment service needs more CPU)
- Teams step on each other's code constantly (merge conflicts, coupling)
- You want to use Python for ML but the rest of the system is in Go
- One module crashes and takes down the entire application

---

### Microservices

Microservices is an architectural style where an application is built as a collection of small, independently deployable services, each running its own process and communicating over well-defined APIs.

**Defining characteristics:**

1. **Single responsibility** — each service does one business thing well
2. **Independent deployability** — you can deploy the Payment Service without touching the Order Service
3. **Owns its data** — each service has its own database; no shared DB
4. **Communicates over the network** — HTTP/REST, gRPC, or message queues
5. **Failure isolation** — a crashing Notification Service doesn't take down Order Service

**Advantages:**

- Independent scaling — payment processing is CPU-heavy; notification delivery is I/O-heavy; scale each independently
- Technology diversity — use Go for latency-critical services, Python for ML services, Node.js for real-time services
- Independent teams — "two pizza rule" (2 engineers can own one service end-to-end)
- Faster deployments — deploy 200-line Payment Service in 2 minutes vs 500,000-line monolith in 20 minutes
- Fault isolation — Recommendation Service down = no recommendations, not zero availability

**Martin Fowler's "Microservice Premium":**

Martin Fowler introduced the concept that microservices add significant overhead — distributed tracing, eventual consistency, network failures, complex deployment pipelines. This overhead is only worth it above a certain complexity threshold. Below that threshold, you pay the premium without getting the benefit.

> "Don't start with microservices. Start with a monolith. Extract services when you feel the monolith's pain." — Martin Fowler

---

## 2. The Modular Monolith

The modular monolith is a powerful intermediate step that gets you most of the benefits of microservices while keeping the simplicity of a monolith.

```
┌─────────────────────────────────────────────────────────────┐
│                   MODULAR MONOLITH                          │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │   User Module    │    │   Order Module   │              │
│  │  (well-defined   │    │  (well-defined   │              │
│  │   interface)     │    │   interface)     │              │
│  └──────┬───────────┘    └───────┬──────────┘              │
│         │  No direct DB access   │                         │
│         │  across modules        │                         │
│  ┌──────▼────────────────────────▼──────────┐              │
│  │              Shared Database             │              │
│  │  (but each module uses its own schema)   │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

**Rules of a modular monolith:**

1. **Module boundaries are enforced** — modules communicate through interfaces, not direct function calls across package boundaries
2. **No cross-module DB access** — Order module does not query the users table directly; it calls User module's interface
3. **Each module owns its schema** — `users.*`, `orders.*`, `payments.*`
4. **Deploy as one unit** — but the code is pre-organized for extraction later

**Why this matters for interviews:** Being able to describe the modular monolith shows architectural maturity. Many teams jump straight to microservices and create distributed monoliths (all services are coupled at the DB level). A modular monolith avoids this.

---

## 3. Service Decomposition with DDD

Domain-Driven Design (DDD) gives us systematic tools for finding the right service boundaries.

### Bounded Contexts

A **bounded context** is a boundary within which a particular model is consistent and applicable. The same word can mean different things in different contexts.

Example: "Customer" in e-commerce:
- **Order context**: a Customer has orders, shipping address, payment methods
- **Support context**: a Customer has support tickets, chat history, satisfaction score
- **Marketing context**: a Customer has email preferences, campaign memberships, segments

These are different models. Putting them in one service creates a bloated, incoherent service. Separate bounded contexts → separate services.

### Event Storming

Event Storming is a workshop technique for discovering domain events and finding service boundaries.

**Process:**
1. Write domain events on orange sticky notes (things that happened): `OrderPlaced`, `PaymentProcessed`, `InventoryReserved`, `EmailSent`
2. Add commands (things users do) on blue notes: `PlaceOrder`, `CancelOrder`
3. Add actors (who does it) on yellow notes: `Customer`, `Warehouse Staff`
4. Add systems (external) on pink notes: `Payment Gateway`, `Email Provider`
5. Group related events → these suggest service boundaries

**Example event flow:**

```
[Customer]
    │
    ▼ PlaceOrder
[OrderPlaced] ──────────────────────────────────────────────┐
    │                                                        │
    ▼                                                        ▼
[PaymentService]                                    [InventoryService]
 PaymentRequested                                    InventoryReserved
 PaymentProcessed                                    InventoryReleased
 PaymentFailed
    │
    ▼
[NotificationService]
 EmailSent
 SMSSent
```

Clusters of events that belong together = a service.

### Decompose by Business Capability

Each service represents a single business capability:

| Service            | Capability                        | Owns                        |
|--------------------|-----------------------------------|-----------------------------|
| User Service       | Identity, authentication          | users, sessions             |
| Product Service    | Catalog, search, pricing          | products, categories        |
| Order Service      | Order lifecycle                   | orders, order_items         |
| Payment Service    | Payment processing, refunds       | payments, transactions      |
| Inventory Service  | Stock levels, reservations        | inventory, reservations     |
| Notification Svc   | Email, SMS, push                  | notification_log            |
| Shipping Service   | Shipment tracking, carriers       | shipments                   |

### Decompose by Subdomain

DDD classifies subdomains:
- **Core domain** — your competitive advantage; build this yourself (Order management for Amazon)
- **Supporting domain** — necessary but not differentiating; build or buy (Inventory)
- **Generic domain** — commodity functionality; buy/use SaaS (Email sending → SendGrid)

For core domains: invest heavily, own the data model, build microservices. For generic domains: use third-party APIs and don't build your own service.

---

## 4. Database Per Service Pattern

Each service must own its own database. No other service can access it directly.

```
┌──────────────────────────────────────────────────────────────────┐
│  DATABASE PER SERVICE                                            │
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                       │
│  │  Order Svc   │         │ Payment Svc  │                       │
│  │              │         │              │                       │
│  │  GET /orders │         │  POST /pay   │                       │
│  └──────┬───────┘         └──────┬───────┘                       │
│         │                        │                               │
│  ┌──────▼───────┐         ┌──────▼───────┐                       │
│  │  orders_db   │         │ payments_db  │                       │
│  │ (PostgreSQL) │         │  (MySQL)     │                       │
│  └──────────────┘         └──────────────┘                       │
│                                                                  │
│  ✓ Order Svc CAN query orders_db                                 │
│  ✗ Payment Svc CANNOT query orders_db directly                   │
│  ✓ Payment Svc MUST call Order Svc API to get order data         │
└──────────────────────────────────────────────────────────────────┘
```

**Why database per service?**

1. **Loose coupling** — if Order Service changes its schema, only Order Service needs to update queries
2. **Technology choice** — use PostgreSQL for relational data, MongoDB for documents, Redis for caching, Elasticsearch for search — pick the right DB for each service
3. **Independent scaling** — scale Order DB separately from Payment DB
4. **Failure isolation** — Payment DB going down doesn't affect Order Service reads

**The Shared Database Anti-Pattern:**

```
┌──────────────────────────────────────────────────┐
│  SHARED DATABASE ANTI-PATTERN ❌                 │
│                                                  │
│  ┌───────────┐  ┌───────────┐  ┌──────────────┐ │
│  │ Order Svc │  │Payment Svc│  │Inventory Svc │ │
│  └─────┬─────┘  └─────┬─────┘  └──────┬───────┘ │
│        │              │               │          │
│        └──────────────┴───────────────┘          │
│                       │                          │
│              ┌────────▼──────┐                   │
│              │  SHARED DB    │                   │
│              └───────────────┘                   │
│                                                  │
│  Problems:                                       │
│  - Schema change in orders table breaks          │
│    Payment Svc immediately                       │
│  - Can't choose different DB technology          │
│  - Lock contention across services               │
│  - You've built a distributed monolith           │
└──────────────────────────────────────────────────┘
```

A "distributed monolith" is the worst of both worlds: you have all the complexity of microservices (network calls, deployment coordination) but none of the benefits (you're still coupled at the database level).

---

## 5. Inter-Service Communication

### Synchronous Communication (HTTP/REST and gRPC)

A service makes a request and **waits** for the response before continuing.

**HTTP/REST:**
- JSON over HTTP; most common, universally understood
- Easy to debug (curl, Postman, browser)
- Higher latency than gRPC (text serialization, no multiplexing)
- Best for: external APIs, simple CRUD operations

**gRPC:**
- Protocol Buffers (binary) over HTTP/2
- 3–10x faster than REST for internal service calls
- Streaming support (server-side, client-side, bidirectional)
- Strong typing via `.proto` files
- Best for: high-throughput internal communication, streaming

**When to use synchronous:**
- The user is waiting for the result (e.g., "place order" must return order ID immediately)
- The downstream service's response affects the next step
- Simple request-response with low latency requirements

**Synchronous call chain problem:**

```
Client → Order Svc → Payment Svc → Inventory Svc → Shipping Svc
         200ms         150ms           100ms            80ms
                                                   Total: 530ms

Plus: if any service is down, the whole chain fails
```

---

### Asynchronous Communication (Message Queues)

A service publishes a message and **does not wait** for the response. Another service consumes the message at its own pace.

**Tools:** Apache Kafka, RabbitMQ, AWS SQS/SNS, Google Pub/Sub

```
Order Service                 Message Broker               Notification Svc
     │                              │                            │
     │── OrderPlaced event ────────>│                            │
     │   (publish & continue)       │                            │
     │                              │──── deliver message ──────>│
     │                              │                            │── send email
     │                              │                            │── send SMS
```

**When to use asynchronous:**
- Eventual consistency is acceptable ("your email will arrive in a few seconds")
- Fire-and-forget operations (logging, notifications, analytics)
- Decoupling producer from consumer availability
- Fan-out scenarios (one event → multiple consumers)
- Buffering load spikes — the queue absorbs bursts

**When NOT to use async:**
- You need an immediate answer (payment authorization result)
- The downstream response affects the current request
- Debugging is already painful and you want to keep it simple

---

### Request-Reply Over Async (Correlation ID Pattern)

Sometimes you need async messaging but still need a reply. The correlation ID pattern handles this.

```
Client                  Order Service              Payment Service
  │                          │                           │
  │── POST /orders ─────────>│                           │
  │                          │── PaymentRequest ─────────>│
  │                          │   {correlationId: "abc123"}│
  │                          │                           │── process
  │                          │<── PaymentResult ──────── │
  │                          │   {correlationId: "abc123"}│
  │                          │   match correlationId     │
  │<── 201 Created ──────────│                           │
  │   {orderId: "xyz"}       │                           │
```

The producer creates a unique `correlationId`, sends the message, and waits on a reply queue filtered by that `correlationId`. The consumer processes the message and sends the response to the reply queue with the same `correlationId`.

---

## 6. API Gateway Pattern

The API Gateway is the single entry point for all client requests. Clients never call microservices directly.

```
                    ┌─────────────────────────────────────┐
                    │           API GATEWAY               │
                    │                                     │
Mobile App ─────────► ┌─────────────────────────────┐    │
                    │ │  1. Authentication/JWT verify │    │
Web App ────────────► │  2. Rate limiting             │    │
                    │ │  3. Request routing           │    │
Third-party API ────► │  4. Protocol translation      │    │
                    │ │  5. Request aggregation       │    │
                    │ │  6. SSL termination           │    │
                    │ └──────────────┬────────────────┘    │
                    └───────────────┼─────────────────────┘
                                    │
          ┌─────────────────────────┼──────────────────────┐
          ▼                         ▼                      ▼
   ┌────────────┐          ┌────────────┐         ┌────────────┐
   │  User Svc  │          │ Order Svc  │         │Product Svc │
   └────────────┘          └────────────┘         └────────────┘
```

### API Gateway Responsibilities

**Should do:**
- **Authentication** — verify JWT/API key; add user context to downstream request headers
- **Rate limiting** — global throttling per user, per IP, per API key
- **Request routing** — route `/api/orders/*` to Order Service, `/api/users/*` to User Service
- **SSL termination** — terminate HTTPS at the gateway, use plain HTTP internally
- **Protocol translation** — REST-to-gRPC, WebSocket handling
- **Request/response transformation** — rename fields, combine responses
- **Circuit breaking** — fail fast if downstream is down
- **Observability** — access logs, metrics, tracing injection

**Should NOT do:**
- Business logic — an API Gateway that knows about your domain is a liability
- Database access — gateways should be stateless
- Complex aggregation — if you're joining data from 5 services, consider a BFF instead

### API Gateway Tools

| Tool              | Type              | Best for                                    |
|-------------------|-------------------|---------------------------------------------|
| Kong              | Open-source       | On-premise, plugin ecosystem, Lua scripting |
| AWS API Gateway   | Managed           | AWS-native, serverless integrations         |
| Nginx             | Reverse proxy     | Simple routing, high performance            |
| Envoy             | Proxy             | Service mesh data plane, advanced routing   |
| Traefik           | Cloud-native      | Kubernetes, auto-discovery                  |

---

## 7. Backend for Frontend (BFF)

The standard API Gateway is one-size-fits-all. But a mobile app and a web app have very different data needs.

**Problem with a single API:**
- Mobile needs a compact response (limited bandwidth, small screen)
- Web needs rich data (sidebar, analytics, detailed views)
- Smart TV needs a completely different payload structure

**BFF Solution:** Create a dedicated gateway (Backend for Frontend) for each client type.

```
                   ┌─────────┐   ┌─────────┐   ┌─────────┐
                   │ Mobile  │   │  Web    │   │   TV    │
                   │  App    │   │  App    │   │  App    │
                   └────┬────┘   └────┬────┘   └────┬────┘
                        │             │              │
                        ▼             ▼              ▼
                 ┌────────────┐ ┌──────────┐ ┌────────────┐
                 │ Mobile BFF │ │ Web BFF  │ │   TV BFF   │
                 │(compact    │ │(full     │ │(simplified │
                 │ responses) │ │ data)    │ │ responses) │
                 └──────┬─────┘ └────┬─────┘ └──────┬─────┘
                        │            │               │
          ┌─────────────┼────────────┼───────────────┤
          ▼             ▼            ▼               ▼
   ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │  User Svc  │ │Order Svc │ │Product   │ │Payment   │
   │            │ │          │ │   Svc    │ │   Svc    │
   └────────────┘ └──────────┘ └──────────┘ └──────────┘
```

**Each BFF:**
- Is owned by the frontend team (mobile team owns Mobile BFF)
- Aggregates data from multiple services in the way that client needs
- Handles client-specific authentication flows (device tokens vs browser sessions)
- Can evolve independently — mobile BFF can change without affecting web BFF

**When to use BFF:**
- Multiple client types with different data requirements
- Front-end teams want autonomy over their API contract
- Performance optimization per client (mobile needs fewer fields)

---

## 8. Service Discovery

In microservices, services need to know where to call each other. IPs change as services scale up/down. Service discovery solves this.

### Client-Side Discovery

The client (calling service) queries the service registry to get the IP/port of the target service, then calls it directly.

```
Order Service                 Service Registry           Payment Service
     │                          (Consul/Eureka)          (3 instances)
     │                               │                   10.0.1.10:8080
     │── "where is payment-svc?" ──>│                   10.0.1.11:8080
     │<── [10.0.1.10, 10.0.1.11] ──│                   10.0.1.12:8080
     │                               │
     │── load balance ──────────────────────────────>10.0.1.11:8080
     │<── response ─────────────────────────────────
```

**Pros:** Client has full control over load balancing algorithm
**Cons:** Every client must implement service discovery logic; language-specific SDKs needed (Netflix Eureka client for Java, Go, etc.)

### Server-Side Discovery

The client calls a load balancer or router. The load balancer queries the registry and forwards the request.

```
Order Service           Load Balancer/Router      Payment Service
     │                       (Nginx, ELB)         (3 instances)
     │── call payment-svc ──>│                   10.0.1.10:8080
     │                       │── query registry   10.0.1.11:8080
     │                       │── forward ──────>10.0.1.12:8080
     │<── response ──────────│<── response ─────
```

**Pros:** Clients are simple; any language works without SDK
**Cons:** Load balancer can be a bottleneck; one more hop in the call chain

### DNS-Based Discovery (Kubernetes)

Kubernetes creates a DNS entry for every Service object. Services discover each other via DNS.

```yaml
# This creates a DNS name: payment-service.default.svc.cluster.local
apiVersion: v1
kind: Service
metadata:
  name: payment-service
spec:
  selector:
    app: payment
  ports:
    - port: 8080
```

Inside Kubernetes: `http://payment-service:8080/pay` works automatically. The kube-proxy routes traffic to a healthy pod.

### Health Checks and Deregistration

Services register with the registry at startup and must send heartbeats. If a service misses heartbeats (or its health check fails), the registry removes it from the pool.

```
Service startup:
  1. Service starts
  2. Service registers: POST /register {name, ip, port}
  3. Registry starts polling GET /health every 10s
  4. If /health fails 3 times → deregister

Service shutdown:
  1. Receive SIGTERM
  2. Deregister from registry immediately
  3. Complete in-flight requests
  4. Exit
```

---

## 9. Load Balancing Strategies

### Round Robin

Requests are distributed sequentially across all healthy instances.

```
Request 1 → Server A
Request 2 → Server B
Request 3 → Server C
Request 4 → Server A (back to start)
```

**Best for:** Stateless services where all instances are identical and have similar capacity.

### Weighted Round Robin

Same as round robin, but each server gets proportional traffic based on weight.

```
Server A (weight: 3) → gets 3 out of every 5 requests
Server B (weight: 2) → gets 2 out of every 5 requests
```

**Best for:** Heterogeneous infrastructure — some servers have more CPU/RAM.

### Least Connections

Route each new request to the server with the fewest active connections.

```
Server A: 15 active connections
Server B: 8 active connections  ← next request goes here
Server C: 22 active connections
```

**Best for:** Long-lived connections (WebSockets, file uploads) where request duration varies significantly.

### Consistent Hashing

Hash a key (user ID, session ID) to deterministically select a server. The same key always routes to the same server.

```
hash(user_id_123) % N_servers = Server B
hash(user_id_456) % N_servers = Server A
hash(user_id_123) % N_servers = Server B  (same result every time)
```

**Best for:** Caching layers (route the same user to the same cache node to maximize cache hits), sticky sessions, data sharding.

**Virtual nodes problem:** When a server is added/removed, only K/N keys need to be remapped (not all). Use consistent hashing ring with virtual nodes to distribute load evenly.

---

## 10. Service Mesh

### The Problem Without a Service Mesh

In a large microservices system, each service needs to implement:
- mTLS (mutual TLS) for service-to-service encryption
- Circuit breaking
- Retries with exponential backoff
- Distributed tracing (inject and propagate trace headers)
- Metrics (latency, error rate, request count per upstream)
- Rate limiting

Without a service mesh, each service team implements this independently. Library drift occurs — Go services use one circuit breaker library, Java services use another. Configuration is scattered.

### What a Service Mesh Does

A service mesh runs a **sidecar proxy** (typically Envoy) alongside every service pod. All traffic goes through the sidecar, not directly between services.

```
Pod A                                        Pod B
┌──────────────────────────┐    ┌──────────────────────────┐
│ ┌──────────┐  ┌────────┐ │    │ ┌────────┐  ┌──────────┐ │
│ │  App     │  │ Envoy  │ │    │ │ Envoy  │  │  App     │ │
│ │ Container│  │Sidecar │ │    │ │Sidecar │  │ Container│ │
│ └─────┬────┘  └───┬────┘ │    │ └────┬───┘  └─────┬────┘ │
│       │  127.0.0.1│      │    │      │  127.0.0.1  │      │
│       └───────────┘      │    │      └─────────────┘      │
└──────────────┬───────────┘    └─────────────┬─────────────┘
               │                              │
               └──── mTLS encrypted ──────────┘
               │    traffic (Envoy-to-Envoy)  │
```

**Service mesh handles (transparently):**
- **mTLS** — automatic certificate management, no application code changes
- **Observability** — metrics, logs, traces emitted automatically per request
- **Traffic management** — weighted routing (canary deployments), fault injection, retries
- **Circuit breaking** — if upstream is slow, open the circuit
- **Access policies** — Service A is allowed to call Service B, but not Service C

**Control plane (Istio, Linkerd) manages:**
- Certificate distribution
- Policy configuration
- Traffic routing rules
- Telemetry collection

**Without service mesh:** application code is responsible for resilience, security, observability.
**With service mesh:** infrastructure layer handles it; application code is clean business logic.

---

## 11. How It Works Internally

### Full Microservices Architecture

```
                          ┌─────────────────────┐
                          │    Clients           │
                          │  (Web, Mobile, APIs) │
                          └──────────┬──────────┘
                                     │ HTTPS
                          ┌──────────▼──────────┐
                          │     API GATEWAY      │
                          │  - Auth verification │
                          │  - Rate limiting     │
                          │  - Request routing   │
                          │  - SSL termination   │
                          └──────────┬──────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          ▼                          ▼                          ▼
   ┌────────────┐            ┌────────────┐            ┌────────────┐
   │  User Svc  │            │ Order Svc  │            │Payment Svc │
   │  :8001     │            │  :8002     │            │  :8003     │
   └─────┬──────┘            └─────┬──────┘            └─────┬──────┘
         │                         │                          │
   ┌─────▼──────┐           ┌──────▼─────┐            ┌──────▼─────┐
   │  Users DB  │           │  Orders DB │            │Payments DB │
   │(PostgreSQL)│           │(PostgreSQL)│            │  (MySQL)   │
   └────────────┘           └──────┬─────┘            └────────────┘
                                   │ Async events
                          ┌────────▼──────────┐
                          │   Message Broker   │
                          │  (Kafka/RabbitMQ)  │
                          └────────┬──────────┘
                                   │
                          ┌────────▼──────────┐
                          │  Notification Svc  │
                          │     :8004          │
                          └───────────────────┘

Supporting Infrastructure:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│Service Regist│  │ Distributed  │  │  Centralized  │  │   Metrics    │
│  (Consul)    │  │   Tracing    │  │   Logging     │  │ (Prometheus) │
│              │  │   (Jaeger)   │  │ (ELK Stack)   │  │  Grafana     │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

### Request Flow: "Place Order"

```
Client                 API Gateway       Order Svc          Payment Svc
  │                        │                │                    │
  │── POST /orders ─────►  │                │                    │
  │   Authorization: Bearer│── verify JWT   │                    │
  │   {items, total}       │── rate limit   │                    │
  │                        │── route ──────►│                    │
  │                        │               │── POST /pay ───────►│
  │                        │               │   {amount, user_id} │
  │                        │               │                    │── charge card
  │                        │               │◄── {status: ok} ───│
  │                        │               │── save order to DB  │
  │                        │               │── publish OrderPlaced│
  │◄── 201 {orderId} ──────│◄── 201 ───────│   to Kafka          │
  │                        │                │                    │
  │                                         ▼                    │
  │                                  Notification Svc            │
  │                                  (consumes OrderPlaced)      │
  │                                  ── sends confirmation email │
```

---

## 12. Implementation Examples

### Go + Chi Router

**Health Check Endpoint (used by Kubernetes and service registry):**

```go
package main

import (
    "context"
    "encoding/json"
    "log/slog"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"
)

type HealthResponse struct {
    Status    string            `json:"status"`
    Service   string            `json:"service"`
    Version   string            `json:"version"`
    Timestamp time.Time         `json:"timestamp"`
    Checks    map[string]string `json:"checks"`
}

type Server struct {
    router *chi.Mux
    db     *sql.DB
    logger *slog.Logger
}

func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
    checks := map[string]string{}
    status := "healthy"

    // Check DB connectivity
    ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
    defer cancel()
    if err := s.db.PingContext(ctx); err != nil {
        checks["database"] = "unhealthy: " + err.Error()
        status = "degraded"
    } else {
        checks["database"] = "healthy"
    }

    resp := HealthResponse{
        Status:    status,
        Service:   "order-service",
        Version:   os.Getenv("APP_VERSION"),
        Timestamp: time.Now().UTC(),
        Checks:    checks,
    }

    w.Header().Set("Content-Type", "application/json")
    if status != "healthy" {
        w.WriteHeader(http.StatusServiceUnavailable)
    }
    json.NewEncoder(w).Encode(resp)
}

// Inter-service HTTP client with timeout and retry
type ServiceClient struct {
    baseURL    string
    httpClient *http.Client
}

func NewServiceClient(baseURL string) *ServiceClient {
    return &ServiceClient{
        baseURL: baseURL,
        httpClient: &http.Client{
            Timeout: 5 * time.Second,
            Transport: &http.Transport{
                MaxIdleConns:        100,
                MaxIdleConnsPerHost: 20,
                IdleConnTimeout:     90 * time.Second,
            },
        },
    }
}

func (c *ServiceClient) ChargePayment(ctx context.Context, req PaymentRequest) (*PaymentResponse, error) {
    body, _ := json.Marshal(req)
    
    httpReq, err := http.NewRequestWithContext(
        ctx,
        http.MethodPost,
        c.baseURL+"/internal/charge",
        bytes.NewReader(body),
    )
    if err != nil {
        return nil, fmt.Errorf("creating request: %w", err)
    }
    
    // Propagate tracing headers
    httpReq.Header.Set("Content-Type", "application/json")
    httpReq.Header.Set("X-Request-ID", middleware.GetReqID(ctx))
    
    resp, err := c.httpClient.Do(httpReq)
    if err != nil {
        return nil, fmt.Errorf("calling payment service: %w", err)
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("payment service returned %d", resp.StatusCode)
    }
    
    var payResp PaymentResponse
    if err := json.NewDecoder(resp.Body).Decode(&payResp); err != nil {
        return nil, fmt.Errorf("decoding response: %w", err)
    }
    return &payResp, nil
}

// Service registry client (Consul)
func registerWithConsul(serviceID, serviceName, address string, port int) error {
    registration := &api.AgentServiceRegistration{
        ID:      serviceID,
        Name:    serviceName,
        Address: address,
        Port:    port,
        Check: &api.AgentServiceCheck{
            HTTP:                           fmt.Sprintf("http://%s:%d/health", address, port),
            Interval:                       "10s",
            Timeout:                        "3s",
            DeregisterCriticalServiceAfter: "30s",
        },
    }
    
    client, err := api.NewClient(api.DefaultConfig())
    if err != nil {
        return err
    }
    return client.Agent().ServiceRegister(registration)
}
```

**Kafka event publishing (Order Service):**

```go
package events

import (
    "context"
    "encoding/json"
    "fmt"
    "time"

    "github.com/segmentio/kafka-go"
)

type OrderEvent struct {
    EventType string      `json:"event_type"`
    OrderID   string      `json:"order_id"`
    UserID    string      `json:"user_id"`
    Total     float64     `json:"total"`
    Items     []OrderItem `json:"items"`
    OccurredAt time.Time  `json:"occurred_at"`
}

type EventPublisher struct {
    writer *kafka.Writer
}

func NewEventPublisher(brokers []string) *EventPublisher {
    return &EventPublisher{
        writer: &kafka.Writer{
            Addr:         kafka.TCP(brokers...),
            Balancer:     &kafka.LeastBytes{},
            RequiredAcks: kafka.RequireAll,
            Async:        false, // synchronous for at-least-once delivery
        },
    }
}

func (p *EventPublisher) PublishOrderPlaced(ctx context.Context, event OrderEvent) error {
    event.EventType = "order.placed"
    event.OccurredAt = time.Now().UTC()
    
    payload, err := json.Marshal(event)
    if err != nil {
        return fmt.Errorf("marshaling event: %w", err)
    }
    
    return p.writer.WriteMessages(ctx, kafka.Message{
        Topic: "orders",
        Key:   []byte(event.OrderID), // same order always goes to same partition
        Value: payload,
        Headers: []kafka.Header{
            {Key: "event-type", Value: []byte(event.EventType)},
            {Key: "schema-version", Value: []byte("v1")},
        },
    })
}
```

---

### Node.js + Express

**API Gateway pattern with http-proxy-middleware:**

```javascript
// api-gateway/src/server.js
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const rateLimit = require('express-rate-limit');
const jwt = require('jsonwebtoken');

const app = express();

// Rate limiting: 100 requests per 15 minutes per IP
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, please try again later.' },
});
app.use(limiter);

// Auth middleware
function authenticate(req, res, next) {
  const authHeader = req.headers['authorization'];
  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing authorization header' });
  }

  const token = authHeader.slice(7);
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET);
    // Inject user context for downstream services
    req.headers['x-user-id'] = payload.sub;
    req.headers['x-user-role'] = payload.role;
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

// Route definitions
const routes = [
  {
    path: '/api/users',
    target: process.env.USER_SERVICE_URL || 'http://user-service:8001',
    requiresAuth: false, // public for registration/login
  },
  {
    path: '/api/orders',
    target: process.env.ORDER_SERVICE_URL || 'http://order-service:8002',
    requiresAuth: true,
  },
  {
    path: '/api/payments',
    target: process.env.PAYMENT_SERVICE_URL || 'http://payment-service:8003',
    requiresAuth: true,
  },
];

// Register routes
routes.forEach(({ path, target, requiresAuth }) => {
  const middlewares = [];

  if (requiresAuth) {
    middlewares.push(authenticate);
  }

  middlewares.push(
    createProxyMiddleware({
      target,
      changeOrigin: true,
      pathRewrite: { [`^${path}`]: '' },
      on: {
        error: (err, req, res) => {
          console.error(`Proxy error for ${path}: ${err.message}`);
          res.status(502).json({ error: 'Service temporarily unavailable' });
        },
      },
    })
  );

  app.use(path, ...middlewares);
});

// Health endpoint (not proxied)
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'api-gateway', timestamp: new Date() });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`API Gateway running on :${PORT}`);
});
```

**Service-to-service call with retry and circuit breaker:**

```javascript
// shared/service-client.js
const axios = require('axios');
const CircuitBreaker = require('opossum');

class ServiceClient {
  constructor(serviceName, baseURL) {
    this.serviceName = serviceName;
    
    const axiosInstance = axios.create({
      baseURL,
      timeout: 5000,
      headers: { 'Content-Type': 'application/json' },
    });

    // Circuit breaker wraps the axios call
    this.breaker = new CircuitBreaker(
      (config) => axiosInstance.request(config),
      {
        timeout: 5000,           // if request takes >5s, trigger failure
        errorThresholdPercentage: 50,  // open if 50% of requests fail
        resetTimeout: 10000,     // try again after 10s
        volumeThreshold: 5,      // need at least 5 requests before checking threshold
      }
    );

    this.breaker.on('open', () => {
      console.warn(`Circuit breaker OPEN for ${serviceName}`);
    });
    this.breaker.on('halfOpen', () => {
      console.info(`Circuit breaker HALF-OPEN for ${serviceName}, probing...`);
    });
    this.breaker.on('close', () => {
      console.info(`Circuit breaker CLOSED for ${serviceName}, service recovered`);
    });
  }

  async call(method, path, data = null, headers = {}) {
    try {
      const response = await this.breaker.fire({
        method,
        url: path,
        data,
        headers,
      });
      return response.data;
    } catch (err) {
      if (err.code === 'EOOPEN') {
        throw new Error(`${this.serviceName} is currently unavailable (circuit open)`);
      }
      throw err;
    }
  }
}

// Usage in Order Service
const paymentClient = new ServiceClient(
  'payment-service',
  process.env.PAYMENT_SERVICE_URL
);

async function processOrder(orderData, userId) {
  // This call goes through circuit breaker
  const paymentResult = await paymentClient.call(
    'POST',
    '/internal/charge',
    { amount: orderData.total, userId },
    { 'x-correlation-id': orderData.correlationId }
  );
  return paymentResult;
}
```

---

### Python + FastAPI

**Microservice with health check, service client, and async messaging:**

```python
# order_service/main.py
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime

import httpx
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from aiokafka import AIOKafkaProducer
import json

# --- Models ---
class OrderCreate(BaseModel):
    items: list[dict]
    total: float
    shipping_address: str

class HealthCheck(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
    checks: dict[str, str]

# --- Startup/Shutdown lifecycle ---
kafka_producer: Optional[AIOKafkaProducer] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    global kafka_producer
    
    # Startup
    kafka_producer = AIOKafkaProducer(
        bootstrap_servers=os.environ["KAFKA_BROKERS"],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",  # wait for all replicas
    )
    await kafka_producer.start()
    print("Kafka producer started")
    
    yield
    
    # Shutdown
    await kafka_producer.stop()
    print("Kafka producer stopped")

app = FastAPI(title="Order Service", version="1.0.0", lifespan=lifespan)

# --- Health check ---
@app.get("/health", response_model=HealthCheck)
async def health_check():
    checks = {}
    status = "healthy"
    
    # Check DB
    try:
        # await db.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        status = "degraded"
    
    # Check Kafka
    if kafka_producer and kafka_producer._closed:
        checks["kafka"] = "unhealthy: producer closed"
        status = "degraded"
    else:
        checks["kafka"] = "healthy"
    
    http_status = 200 if status == "healthy" else 503
    return JSONResponse(
        status_code=http_status,
        content={
            "status": status,
            "service": "order-service",
            "version": os.environ.get("APP_VERSION", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        }
    )

# --- Service client ---
class PaymentServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    
    async def charge(self, amount: float, user_id: str, correlation_id: str) -> dict:
        try:
            response = await self.client.post(
                "/internal/charge",
                json={"amount": amount, "user_id": user_id},
                headers={"x-correlation-id": correlation_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(503, "Payment service timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, f"Payment service error: {e.response.text}")
    
    async def close(self):
        await self.client.aclose()

payment_client = PaymentServiceClient(
    base_url=os.environ.get("PAYMENT_SERVICE_URL", "http://payment-service:8003")
)

# --- Order creation ---
@app.post("/orders", status_code=201)
async def create_order(
    order: OrderCreate,
    x_user_id: str = Header(...),
    x_correlation_id: str = Header(default=""),
):
    import uuid
    order_id = str(uuid.uuid4())
    correlation_id = x_correlation_id or str(uuid.uuid4())
    
    # Call payment service synchronously (user is waiting)
    payment_result = await payment_client.charge(
        amount=order.total,
        user_id=x_user_id,
        correlation_id=correlation_id,
    )
    
    if payment_result.get("status") != "success":
        raise HTTPException(402, "Payment failed")
    
    # Persist order to DB
    # await db.execute("INSERT INTO orders ...")
    
    # Publish event asynchronously (non-blocking)
    await kafka_producer.send_and_wait(
        "orders",
        key=order_id.encode(),
        value={
            "event_type": "order.placed",
            "order_id": order_id,
            "user_id": x_user_id,
            "total": order.total,
            "correlation_id": correlation_id,
            "occurred_at": datetime.utcnow().isoformat(),
        },
    )
    
    return {"order_id": order_id, "status": "confirmed"}
```

---

## 13. Common Patterns & Best Practices

### Idempotency Keys

Distributed systems experience network failures. A client might retry a request that already succeeded. Idempotency keys ensure that retrying the same operation is safe.

```
POST /orders
Idempotency-Key: client-generated-unique-uuid

Server behavior:
1. Check if idempotency-key exists in cache/DB
2. If yes → return cached response (don't process again)
3. If no → process, cache response with key, return response

Cache TTL: 24-48 hours
```

### Bulkhead Pattern

Isolate resources for different types of requests so a slow dependency doesn't exhaust all resources.

```
Without bulkhead:
Thread pool (50 threads shared)
├── 30 threads stuck on slow Payment Service
└── Only 20 threads left for all other operations → service degraded

With bulkhead:
├── Thread pool: Payment calls (15 threads max)
├── Thread pool: Order operations (25 threads max)
└── Thread pool: User operations (10 threads max)
Payment degradation doesn't affect Order or User operations
```

### Correlation ID / Trace ID Propagation

Every request gets a unique ID at the API Gateway. All downstream service calls propagate this ID in headers. This allows tracing a request across all services in logs.

```go
// Middleware to propagate or generate trace ID
func TraceMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        traceID := r.Header.Get("X-Trace-ID")
        if traceID == "" {
            traceID = uuid.New().String()
        }
        ctx := context.WithValue(r.Context(), "trace_id", traceID)
        w.Header().Set("X-Trace-ID", traceID)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

### Strangler Fig Pattern

When migrating from monolith to microservices, don't do a big-bang rewrite. Use the Strangler Fig:

1. Put a facade (API Gateway/proxy) in front of the monolith
2. Extract one service at a time (start with the most independent one)
3. Route traffic for that domain to the new service
4. Gradually, the monolith shrinks; new services grow around it
5. Eventually, the monolith is gone

```
Phase 1:              Phase 2:              Phase 3:
                       New Services          Monolith shrunk
Client                 ┌──────────┐         ┌──────────┐
  │                    │ User Svc │         │ User Svc │
  ▼                    └──────────┘         └──────────┘
┌──────┐   ┌──────┐   ┌──────────┐         ┌──────────┐
│Facade│──►│Mono- │   │ Order Svc│         │ Order Svc│
│      │   │lith  │   └──────────┘         └──────────┘
└──────┘   └──────┘   ┌──────────┐         ┌──────────┐
              all      │  Facade  │──►┌──►  │Payment   │
                       └──────────┘   │     │   Svc    │
                            │         │     └──────────┘
                            └──►┌─────┘         │
                                │Monolith│       │ monolith
                                │(rest)  │       │ tiny now
                                └────────┘       ▼ ...
```

---

## 14. Common Pitfalls

### 1. Distributed Monolith

Building "microservices" that all share one database. You get all the overhead of microservices with none of the benefits. The services are still tightly coupled — a schema change in the shared DB breaks all services simultaneously.

**Fix:** Enforce database per service from day one. If two services need to share data, define a well-typed API between them.

### 2. Synchronous Call Chains

```
A → B → C → D → E
```

If E has a 500ms tail latency, the entire chain takes 500ms+. If E is down, the whole chain fails. This creates tight availability coupling.

**Fix:** Identify which downstream calls are truly synchronous (user waiting for response) and which can be async. Make as many calls async as possible.

### 3. Chatty Services

Service A makes 20 calls to Service B to render one page. N+1 problem over the network.

**Fix:** Design coarser-grained APIs. Use GraphQL or BFF to batch queries. Consider if the two services should actually be one.

### 4. Missing Correlation IDs

When a bug occurs in production, you look at logs from 7 services. Without correlation IDs, you can't connect which log lines belong to the same request.

**Fix:** Inject correlation ID at the gateway; propagate to all downstream services; log it in every log line.

### 5. Wrong Service Boundaries

Splitting by technical layer (Data Service, Logic Service, Presentation Service) instead of business capability creates services that are almost always deployed together and always call each other.

**Fix:** Split by business capability / bounded context, not by technical layer.

### 6. Ignoring the Network

Treating service calls like function calls. Not setting timeouts, not handling failures, not retrying.

**Fix:** Always set explicit timeouts on all inter-service calls. Always handle failures (fallback, retry, circuit break). Assume the network will fail.

---

## 15. Interview Questions & Answers

**Q: What is the main technical challenge of microservices?**

The fundamental challenge is **distributed systems complexity**. When services communicate over the network, you face problems that don't exist in a monolith: network failures, partial failures, eventual consistency, distributed transactions, distributed debugging/tracing, and the need for complex infrastructure (service discovery, load balancing, API gateway). You trade simple code + complex deployment for complex code + complex deployment.

---

**Q: What is the database-per-service pattern and why does it exist?**

Each microservice has its own private database that no other service can access directly. It exists because a shared database creates tight coupling — any service can read or write any data, making independent deployment impossible and schema evolution dangerous. With database per service: services are truly independent, each can choose the right database technology (PostgreSQL, MongoDB, Redis), and a schema change only affects one service.

---

**Q: What is an API Gateway and what should it do vs not do?**

An API Gateway is the single entry point for all client requests. It should handle: authentication, rate limiting, SSL termination, request routing, protocol translation, and basic observability. It should NOT contain business logic, access databases, or do complex data aggregation — that becomes a bottleneck and couples the gateway to your domain. Business logic in the gateway is a smell; it should belong in the service.

---

**Q: What is a BFF and when would you use it?**

A Backend for Frontend is a dedicated API Gateway for each client type (mobile, web, TV). Use it when different clients have substantially different data requirements — mobile needs compact responses for bandwidth, web needs rich data for complex UIs. Each BFF is owned by the frontend team and can evolve independently. Without BFF, a single API gateway becomes a compromise that serves no client well.

---

**Q: What is a service mesh?**

A service mesh adds a sidecar proxy (Envoy) to every service pod. All traffic goes through the sidecar instead of directly between services. The mesh handles cross-cutting concerns like mTLS, distributed tracing, metrics, retries, circuit breaking, and traffic management — transparently, without changing application code. The control plane (Istio, Linkerd) manages the sidecar configurations centrally.

---

**Q: How does service discovery work in Kubernetes?**

Kubernetes uses DNS-based service discovery. When you create a Service object, Kubernetes creates a DNS record: `<service-name>.<namespace>.svc.cluster.local`. kube-proxy runs on every node and maintains iptables rules to route traffic matching that service's ClusterIP to healthy pods. Pods discover services by hostname — they don't need to know IP addresses. When pods scale up/down, the Endpoints object is updated, and kube-proxy updates iptables accordingly.

---

**Q: When would you choose synchronous vs asynchronous inter-service communication?**

Use **synchronous** (REST/gRPC) when:
- The user is actively waiting for a response (place order → return order ID)
- The downstream result determines the next step (payment must succeed before saving order)
- The operation must be atomic across services from the user's perspective

Use **asynchronous** (Kafka/RabbitMQ) when:
- Eventual consistency is acceptable (send confirmation email after order placed)
- You want to decouple service availability (Notification Service can be down without affecting Order Service)
- You need fan-out (one event → multiple consumers)
- You want to absorb load spikes (queue buffers bursts)

---

**Q: What is the Strangler Fig pattern?**

A migration strategy for moving from monolith to microservices. You put a proxy/gateway in front of the monolith and gradually extract services one at a time, routing specific domain traffic to new services. The monolith "dies" slowly as services are extracted — like a strangler fig vine growing around a tree. This is safer than a big-bang rewrite because you can validate each extracted service in production before extracting the next one.

---

## 16. Resources

- [Martin Fowler — Microservices](https://martinfowler.com/articles/microservices.html)
- [Martin Fowler — Microservice Premium](https://martinfowler.com/bliki/MicroservicePremium.html)
- [Martin Fowler — Strangler Fig Application](https://martinfowler.com/bliki/StranglerFigApplication.html)
- [Sam Newman — Building Microservices (2nd Ed)](https://samnewman.io/books/building_microservices_2nd_edition/)
- [Chris Richardson — Microservices Patterns](https://microservices.io/patterns/index.html)
- [BFF Pattern — Sam Newman](https://samnewman.io/patterns/architectural/bff/)
- [Istio Service Mesh](https://istio.io/latest/docs/concepts/what-is-istio/)
- [Consul Service Discovery](https://developer.hashicorp.com/consul/docs/concepts/service-discovery)

---

**Next:** [Part 15.2: Saga, CQRS & Event Sourcing](./15-saga-cqrs-event-sourcing.md)
