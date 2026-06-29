# Part 13.2: Distributed Tracing, Health Checks & Alerting

## What You'll Learn
- Why distributed tracing is essential in microservice architectures
- The vocabulary: traces, spans, span contexts, parent-child relationships
- W3C TraceContext standard and HTTP header propagation
- OpenTelemetry — the vendor-neutral observability standard
- Sampling strategies for different environments
- How to read a Jaeger trace waterfall and identify bottlenecks
- Liveness, readiness, and startup probes — what each means and what to check
- Kubernetes integration for health checks
- SLIs, SLOs, SLAs, and error budgets
- Alert design: burn rate alerting vs raw error rate alerting
- Production-ready implementations in Go, Node.js, and Python

## Table of Contents
1. [Why Distributed Tracing](#1-why-distributed-tracing)
2. [Core Vocabulary](#2-core-vocabulary)
3. [Parent-Child Span Relationships](#3-parent-child-span-relationships)
4. [Trace Context Propagation](#4-trace-context-propagation)
5. [OpenTelemetry](#5-opentelemetry)
6. [Sampling Strategies](#6-sampling-strategies)
7. [Reading a Trace Waterfall](#7-reading-a-trace-waterfall)
8. [Health Checks](#8-health-checks)
9. [Kubernetes Health Check Integration](#9-kubernetes-health-check-integration)
10. [SLIs, SLOs, SLAs, and Error Budgets](#10-slis-slos-slas-and-error-budgets)
11. [Alerting Design](#11-alerting-design)
12. [Implementation Examples](#12-implementation-examples)
13. [Common Patterns & Best Practices](#13-common-patterns--best-practices)
14. [Common Pitfalls](#14-common-pitfalls)
15. [Interview Questions](#15-interview-questions)
16. [Resources](#16-resources)

---

## 1. Why Distributed Tracing

In a monolith, debugging is straightforward: one process, one log file, one stack trace. In microservices, a single user action might:

```
User clicks "Place Order"
        │
        ▼
  API Gateway (auth check)
        │
        ▼
  Order Service (validate, create order)
        │
        ├──► Inventory Service (reserve stock)
        │
        ├──► Payment Service (charge card)
        │         │
        │         └──► Stripe API (external)
        │
        ├──► Notification Service (send email/SMS)
        │         │
        │         └──► SendGrid API (external)
        │
        └──► Analytics Service (track event)

Total: 6 internal services, 2 external APIs, ~15 DB queries
       Completing in ~350ms across 4 servers
```

**What logs tell you:** Scattered JSON lines across 6 log files. You know the error occurred. You don't know *which service* is slow or *in what order* things happened.

**What metrics tell you:** Error rate is 3%, p99 latency is 800ms. Something is wrong but you can't tell *where*.

**What traces tell you:** The Inventory Service is making sequential DB queries for each item that should be parallel. That's where your 600ms is going.

Distributed tracing is the tool that connects all the dots. It gives you a **visual map of every operation** that happened as part of a request, with exact timing for each.

---

## 2. Core Vocabulary

### Trace

A trace represents a **complete end-to-end journey** of a request through the system. Every trace has a unique `trace_id` (16 bytes / 128-bit hex string).

```
Trace ID: 4bf92f3577b34da6a3ce929d0e0e4736
This ID uniquely identifies ONE user's request from entry to exit.
```

### Span

A span represents **a single unit of work** — one function call, one DB query, one HTTP request to another service. Spans are the building blocks of a trace.

Every span has:
```
span_id:        00f067aa0ba902b7        (8 bytes / 64-bit hex)
trace_id:       4bf92f3577b34da6a3ce929d0e0e4736 (links to parent trace)
parent_span_id: aabb00112233ffee       (nil if root span)
operation_name: "GET /orders/{id}"
start_time:     1719651652543000000    (nanoseconds since epoch)
end_time:       1719651652743000000
duration:       200ms
status:         OK / ERROR
attributes:     {http.method: "GET", db.system: "postgresql", ...}
events:         [{name: "cache_miss", timestamp: ...}, ...]
```

### Span Context

The **span context** is the minimal information that needs to be **propagated** from one service to another to link spans into the same trace:

```
trace_id   — which trace this span belongs to
span_id    — the current span's ID (becomes parent_span_id in child)
trace_flags — sampling decision (sampled: yes/no)
trace_state — vendor-specific data
```

This is what gets serialized into HTTP headers when a service calls another service.

---

## 3. Parent-Child Span Relationships

Spans form a tree structure. When Service A calls Service B, Service B's span is a **child** of Service A's span.

```
Trace ID: 4bf92f3577b34da6a3ce929d0e0e4736

Root Span (API Gateway)
  span_id: 0001
  operation: "POST /checkout"
  duration: 0-350ms
  │
  ├── Child Span (Auth Middleware)
  │     span_id: 0002, parent: 0001
  │     operation: "auth.validate_token"
  │     duration: 0-5ms
  │
  └── Child Span (Order Service)
        span_id: 0003, parent: 0001
        operation: "POST /orders"
        duration: 5-350ms
        │
        ├── Child Span (DB: insert order)
        │     span_id: 0004, parent: 0003
        │     duration: 5-20ms
        │
        ├── Child Span (Inventory gRPC call)
        │     span_id: 0005, parent: 0003
        │     duration: 20-40ms
        │
        └── Child Span (Payment gRPC call)
              span_id: 0006, parent: 0003
              duration: 40-350ms ← SLOW
              │
              └── Child Span (Stripe HTTP call)
                    span_id: 0007, parent: 0006
                    duration: 40-348ms ← BOTTLENECK
```

Each service **reads the parent span context** from incoming headers and **creates child spans** for its own work. This is how the tree is built across process boundaries.

---

## 4. Trace Context Propagation

### W3C TraceContext (The Standard)

W3C TraceContext is the industry standard (RFC). Two headers:

```http
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             ^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^ ^^
             version  trace_id (128-bit hex)     span_id(64-bit)  flags

tracestate: rojo=00f067aa0ba902b7,congo=t61rcWkgMzE
            vendor-specific key-value pairs
```

**traceparent breakdown:**
- `00` — version (always 00 currently)
- `4bf92f3577b34da6a3ce929d0e0e4736` — trace ID
- `00f067aa0ba902b7` — parent span ID (the current span from the calling service)
- `01` — flags, where `01` = sampled (should be traced), `00` = not sampled

### Propagation Flow

```
Service A makes HTTP call to Service B:
  1. Service A has current span: trace_id=4bf92f..., span_id=00f067...
  2. Service A adds to outgoing request headers:
     traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
  3. Service B receives request, reads traceparent header
  4. Service B creates new span:
     - trace_id = 4bf92f3577b34da6a3ce929d0e0e4736  (SAME as parent)
     - span_id  = aabb112233ff0011                   (NEW — this span's ID)
     - parent_span_id = 00f067aa0ba902b7              (from traceparent header)
  5. Service B adds its own traceparent to any outgoing requests it makes
```

### Legacy Formats (Still Common)

```
B3 (Zipkin):
  X-B3-TraceId: 80f198ee56343ba864fe8b2a57d3eff7
  X-B3-ParentSpanId: 05e3ac9a4f6e3b90
  X-B3-SpanId: e457b5a2e4d86bd1
  X-B3-Sampled: 1

Jaeger:
  uber-trace-id: {trace-id}:{span-id}:{parent-span-id}:{flags}
```

OpenTelemetry supports all propagation formats via its propagators system.

---

## 5. OpenTelemetry

OpenTelemetry (OTel) is the **CNCF standard** for observability instrumentation. Before OTel, every APM vendor (DataDog, New Relic, Jaeger, Zipkin) had its own SDK. You'd lock in to a vendor's instrumentation library. Switching vendors meant rewriting all instrumentation.

OTel solves this with a **vendor-neutral API and SDK**:

```
┌──────────────────────────────────────────────────────────────────┐
│                    OpenTelemetry Architecture                     │
│                                                                   │
│  Your Application                                                 │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │   OTel API (create spans, record metrics, emit logs)      │   │
│  │   OTel SDK (batching, sampling, resource detection)       │   │
│  └─────────────────────────┬─────────────────────────────────┘   │
│                             │ OTLP (OpenTelemetry Protocol)       │
│                             ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              OTel Collector (optional but recommended)       │ │
│  │  - Receives OTLP from your app                              │ │
│  │  - Processes (batch, retry, filter, tail-sample)            │ │
│  │  - Exports to multiple backends simultaneously              │ │
│  └──────┬─────────────────────────┬──────────────────┬─────────┘ │
│         │                         │                  │            │
│         ▼                         ▼                  ▼            │
│      Jaeger                    Zipkin           DataDog/          │
│     (traces)                  (traces)          New Relic         │
│                                              Honeycomb/etc        │
└──────────────────────────────────────────────────────────────────┘
```

### OTel Components

**API**: The interfaces your code calls. Stable, vendor-neutral. What you import in your application code.

**SDK**: The implementation. Handles sampling, batching, exporting. Pluggable.

**Collector**: A standalone process that receives telemetry, processes it, and exports to backends. Running the Collector decouples your app from backend vendor changes.

**Instrumentation Libraries**: Auto-instrumentation for common frameworks — HTTP servers, DB drivers, gRPC, Redis clients. You don't need to manually create spans for every DB query; the library does it.

**OTLP**: OpenTelemetry Protocol — the standard wire format for sending telemetry. Works over gRPC or HTTP/protobuf.

### Automatic vs Manual Instrumentation

**Automatic instrumentation** — Libraries that hook into frameworks and automatically create spans:
```
go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp  → HTTP server/client
go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc → gRPC
github.com/uptrace/bun → database
```

**Manual instrumentation** — Creating custom spans for business logic:
```go
ctx, span := tracer.Start(ctx, "validateOrder")
defer span.End()

span.SetAttributes(
    attribute.String("order.id", orderID),
    attribute.Float64("order.amount", amount),
)

if err := validate(order); err != nil {
    span.RecordError(err)
    span.SetStatus(codes.Error, err.Error())
}
```

Use automatic instrumentation for infrastructure (HTTP, DB, cache) and manual spans for meaningful business operations.

---

## 6. Sampling Strategies

In high-throughput systems you cannot record every span — the cost (CPU, memory, storage, network) would be prohibitive. Sampling decides which traces to keep.

### Always-On Sampling (Development)

```
Record 100% of traces.
Use in: development, staging, low-traffic services
Cost: High. Not for production at scale.
```

### Probabilistic / Head-Based Sampling

```
Record X% of traces, decided at the start of the trace.
Configured in the root service (API gateway).

Pros: Simple. Predictable cost.
Cons: Errors may be in the unsampled fraction.
      You don't know which traces will be interesting when you start them.

Example: Sample 1% in production → manageable volume
```

```go
// OpenTelemetry probabilistic sampler
sampler := sdktrace.TraceIDRatioBased(0.01) // 1%
```

### Tail-Based Sampling (Production Best Practice)

```
Buffer all spans for a trace. Make sampling decision AFTER the trace completes.
Sample based on outcome:

If trace contains an ERROR    → always keep (100%)
If trace.duration > 1s        → always keep (slow = interesting)
If trace spans an interesting path → keep
Otherwise                     → discard (1% random sample)
```

```
Pros: You always have traces for errors and slow requests.
      Much better signal-to-noise.
Cons: More complex to implement.
      Requires buffering spans (memory) or the OTel Collector.
      The "tail" decision happens in the Collector, not the app.
```

Tail-based sampling is implemented in the **OTel Collector** using the `tailsampling` processor, not in your application code.

### Rate-Limited Sampling

```
Keep at most N traces per second.
Good for ensuring minimum coverage without runaway costs.

Example: max 100 traces/sec regardless of traffic spike
```

### Practical Production Config

```yaml
# OTel Collector tail sampling config
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    policies:
      - name: errors-policy
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: slow-requests-policy
        type: latency
        latency: {threshold_ms: 500}
      - name: probabilistic-policy
        type: probabilistic
        probabilistic: {sampling_percentage: 1}
```

---

## 7. Reading a Trace Waterfall

The Jaeger / Zipkin waterfall view shows time on the X axis and spans on the Y axis. Each row is a span. Nesting shows parent-child relationships.

```
Request POST /checkout ─────────────────────────────────────── 350ms
│
├── [API Gateway] auth_middleware ──── 5ms
│   └── [Redis] GET session:abc123 ── 3ms
│
└── [API Gateway → Order Service] HTTP POST /orders ─────────── 340ms
    │
    ├── [Order Service] validate_request ── 2ms
    │
    ├── [Order Service → DB] INSERT orders ──── 15ms
    │
    ├── [Order Service → Inventory] gRPC CheckStock ──── 20ms
    │   └── [Inventory Service → DB] SELECT inventory ── 18ms
    │
    └── [Order Service → Payment] gRPC ChargeCard ──────────── 295ms  ← !
        └── [Payment Service] stripe.charge ────────────────── 290ms  ← !
            └── [HTTP] POST api.stripe.com/v1/charges ──────── 285ms  ← EXTERNAL
```

**Reading the waterfall:**

1. **Width = duration** — wider bars are slower operations
2. **Position on X axis** — when the operation started relative to the root span
3. **Nesting** — parent-child relationships, shows causality
4. **Gaps** — time the parent span spent between child calls (queueing, computation)
5. **Sequential vs parallel** — are child spans stacked (sequential) or overlapping (parallel)?

**What to look for:**

```
N+1 Query Pattern:
  Handler (1000ms)
  ├── DB query ── 5ms  (repeated 100 times for 100 items)
  ├── DB query ── 5ms
  ├── DB query ── 5ms
  ... × 100
  Total: 500ms just in DB queries that should be 1 batched query

Sequential calls that should be parallel:
  Handler (300ms)
  ├── Redis GET user ──────── 10ms  ─┐ These should run
  └── Redis GET settings ──── 10ms  ─┘ concurrently (20ms total → 10ms)
  (instead they run sequentially: 20ms)

External API bottleneck:
  Handler (500ms)
  └── External API call ──────── 490ms ← consider caching / async
```

---

## 8. Health Checks

Health checks are HTTP endpoints that answer the question: "Is this service OK?" Kubernetes, load balancers, and monitoring systems call these endpoints.

### Three Types of Health Checks

#### Liveness Probe — Is the Process Alive?

```
Purpose: Detect if the process is in an unrecoverable broken state
         (deadlock, infinite loop, corrupted state)
Action on failure: Kubernetes RESTARTS the container
Check: Should be simple — if the process can respond at all, it's alive

Wrong: Check DB in liveness probe — DB being down doesn't mean restart the service
Right: Return 200 if the process is running

Example response:
GET /healthz → 200 OK
{"status": "ok"}

Only return non-200 if the process itself is broken (e.g., couldn't acquire startup lock)
```

#### Readiness Probe — Is the Service Ready to Serve Traffic?

```
Purpose: Detect if the service can actually handle requests
         (dependencies not available, still loading caches, overloaded)
Action on failure: Kubernetes REMOVES pod from load balancer
                   (pod keeps running but receives no traffic)
Check: Verify all required dependencies are available

Should check:
  ✓ Database connection (can we connect and execute SELECT 1?)
  ✓ Redis connection (can we PING?)
  ✓ Required external services
  ✓ Required config/secrets loaded
  ✗ Non-critical services (don't fail readiness for analytics service being down)

Example response:
GET /readyz → 200 OK
{
  "status": "ready",
  "checks": {
    "database": {"status": "ok", "latency_ms": 2},
    "redis": {"status": "ok", "latency_ms": 1},
    "migrations": {"status": "ok", "version": "v20260629"}
  }
}

GET /readyz → 503 Service Unavailable
{
  "status": "not_ready",
  "checks": {
    "database": {"status": "error", "error": "connection refused"},
    "redis": {"status": "ok", "latency_ms": 1}
  }
}
```

#### Startup Probe — Is the Service Done Initializing?

```
Purpose: For slow-starting containers that need time to initialize
         (loading ML model, warming up caches, running migrations)
Action: Until startup probe succeeds, liveness/readiness probes are disabled
        After startup probe succeeds, normal liveness/readiness takes over

Use case: Java services with 30-60s startup time
          Services that run DB migrations on startup
          Services that load large datasets into memory

If the startup probe fails after failureThreshold attempts: container is killed and restarted
```

### Key Distinction

```
Liveness  = "Am I alive?" (restart me if I'm broken)
Readiness = "Am I ready?" (remove me from load balancer if I can't serve)
Startup   = "Am I done starting up?" (don't check liveness/readiness until I say so)

A pod can be:
  Alive + Not Ready  = Initializing, or dependency unavailable — gets no traffic
  Alive + Ready      = Normal — gets traffic
  Not Alive          = Restarted
```

### Health Check Timeouts

Always check dependencies with a **short timeout**. Never let a health check hang:

```go
// Always use timeouts in readiness checks
ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
defer cancel()

if err := db.PingContext(ctx); err != nil {
    // DB unavailable — report not ready
}
```

If you don't timeout and a DB is slow, your health check hangs, Kubernetes thinks the service is unresponsive and starts restarting pods — making the problem worse.

---

## 9. Kubernetes Health Check Integration

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: order-service
          image: order-service:1.4.2
          ports:
            - containerPort: 8080

          # Startup probe — wait up to 60s for startup
          startupProbe:
            httpGet:
              path: /startupz
              port: 8080
            failureThreshold: 12        # 12 × 5s = 60s max startup time
            periodSeconds: 5

          # Liveness probe — check every 10s, restart after 3 failures
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 0     # startupProbe handles delay
            periodSeconds: 10
            failureThreshold: 3        # 3 × 10s = 30s before restart
            timeoutSeconds: 5

          # Readiness probe — check every 5s, remove from LB after 2 failures
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
            initialDelaySeconds: 0
            periodSeconds: 5
            failureThreshold: 2        # 2 × 5s = 10s before LB removal
            successThreshold: 1        # 1 success to re-add to LB
            timeoutSeconds: 3
```

### Health Check Paths Convention

```
/healthz  or  /health/live    → liveness
/readyz   or  /health/ready   → readiness
/startupz or  /health/startup → startup
/metrics                       → Prometheus metrics (not a health check)
```

---

## 10. SLIs, SLOs, SLAs, and Error Budgets

These four concepts form the foundation of **SRE (Site Reliability Engineering)** and how teams think about reliability.

### SLI — Service Level Indicator

A specific, measurable metric that indicates service health:

```
Examples:
- Availability: % of requests that return a non-5xx response
- Latency: % of requests that complete in < 200ms
- Error rate: % of failed requests
- Throughput: requests per second successfully processed
- Durability: % of data successfully written that can be read back
```

SLIs are **what you measure** — the raw numbers from your metrics system.

### SLO — Service Level Objective

A **target** for an SLI over a time window:

```
"99.9% of requests complete with a non-5xx status code (30-day rolling window)"
"p99 latency < 200ms (1-hour rolling window)"
"99.99% of writes are durable within 5 seconds"
```

SLOs are **internal targets**. They're what your team commits to achieving. They're stricter than your SLA (you want a safety margin).

### SLA — Service Level Agreement

A **contractual commitment** with customers, often with financial penalties:

```
"99.9% monthly uptime (three nines)"
Downtime allowed: 43.8 minutes per month

"99.95% monthly uptime"
Downtime allowed: 21.9 minutes per month
```

SLAs should be **less strict than SLOs**. If your SLO is 99.9%, your SLA might be 99.5%. The gap is your safety margin.

### Error Budget

The **error budget** is the maximum allowable unreliability within the SLO window:

```
SLO: 99.9% availability over 30 days
Total requests in 30 days: ~1 billion

Error budget = 1 - 0.999 = 0.001 = 0.1% of requests
             = 1,000,000 allowed errors in 30 days
             ≈ 43.8 minutes of complete downtime

If you've consumed 80% of error budget by day 20:
  → Slow down feature releases
  → Prioritize reliability work
  → No risky deploys until budget resets
```

```
Month 1: Error rate 0.05% → Used 50% of budget. Healthy.
Month 2: Error rate 0.15% → Exceeded budget. SLO violated.
         → Post-mortem, fix root cause, reduce release velocity
```

### Error Budget Policy

```
Budget remaining > 50%:  Normal velocity. Ship features freely.
Budget remaining 25-50%: Caution. Code review more carefully.
Budget remaining < 25%:  Slow down. Only critical fixes.
Budget exhausted:         Feature freeze. All hands on reliability.
```

---

## 11. Alerting Design

### The Problem with Threshold Alerts

```
WRONG approach:
Alert when error rate > 1% for 5 minutes.

Problems:
- Misses slow burns (error rate 0.5% for 24 hours consumes entire budget)
- False positives (brief spike at 1.1% for 5 minutes, then fine)
- Doesn't account for traffic volume (1% of 1000 req/s = 10 errors/s, very different from 1% of 1 req/s)
```

### SLO Burn Rate Alerting

A **burn rate** of 1x means you're consuming the error budget at exactly the SLO rate (perfect). A burn rate of 10x means you're consuming it 10x faster than expected.

```
If SLO = 99.9% (0.1% error budget for 30 days = 43.8 minutes)

Burn rate 1x  → Budget consumed in 30 days (expected)
Burn rate 10x → Budget consumed in 3 days  (alert!)
Burn rate 60x → Budget consumed in 12 hours (page oncall NOW)
```

**Multi-window, multi-burn-rate alerts:**

```yaml
# Page immediately (critical) — fast burn detected
- alert: SLOBurnRateCritical
  expr: |
    (
      rate(http_requests_total{status=~"5.."}[1h])
      / rate(http_requests_total[1h])
    ) > 14.4 * 0.001   # 14.4x burn rate over 1h
    AND
    (
      rate(http_requests_total{status=~"5.."}[5m])
      / rate(http_requests_total[5m])
    ) > 14.4 * 0.001   # also burning fast in short window
  for: 2m
  labels:
    severity: critical
    page: "true"

# Ticket (warning) — slow burn detected
- alert: SLOBurnRateWarning
  expr: |
    (
      rate(http_requests_total{status=~"5.."}[6h])
      / rate(http_requests_total[6h])
    ) > 6 * 0.001   # 6x burn rate over 6 hours
  for: 30m
  labels:
    severity: warning
```

### Runbooks

Every alert should have a **runbook** — a documented response procedure:

```markdown
## Alert: HighErrorRate

### Symptoms
- Error rate > 5% for more than 5 minutes

### Immediate actions
1. Check Grafana dashboard: https://grafana.internal/d/api-red
2. Check recent deployments: kubectl rollout history deployment/api
3. Check DB health: kubectl exec -it db-0 -- psql -c "SELECT 1"
4. If recent deploy is cause: kubectl rollout undo deployment/api

### Investigation
1. Open Jaeger: https://jaeger.internal, filter by status=error
2. Find common error pattern in spans
3. Check logs: kubectl logs -l app=api --since=1h | grep ERROR

### Escalation
- If not resolved in 15 minutes, page senior engineer
- Slack: #oncall-escalation
```

---

## 12. Implementation Examples

### Go + Chi Router

```go
// Dependencies:
// go.opentelemetry.io/otel
// go.opentelemetry.io/otel/sdk
// go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc
// go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp

package main

import (
    "context"
    "encoding/json"
    "net/http"
    "time"

    "github.com/go-chi/chi/v5"
    "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/codes"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/propagation"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
    "go.opentelemetry.io/otel/trace"
)

var tracer trace.Tracer

// initTracer sets up OpenTelemetry with OTLP gRPC exporter
func initTracer(ctx context.Context) (func(context.Context) error, error) {
    // Exporter — sends traces to OTel Collector (or Jaeger) via gRPC
    exporter, err := otlptracegrpc.New(ctx,
        otlptracegrpc.WithEndpoint("localhost:4317"), // OTel Collector address
        otlptracegrpc.WithInsecure(),
    )
    if err != nil {
        return nil, err
    }

    // Resource — describes this service in all traces
    res, err := resource.New(ctx,
        resource.WithAttributes(
            semconv.ServiceName("order-service"),
            semconv.ServiceVersion("1.4.2"),
            semconv.DeploymentEnvironment("production"),
        ),
    )
    if err != nil {
        return nil, err
    }

    // TracerProvider — the SDK with tail sampling and batching
    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(res),
        sdktrace.WithSampler(
            // In production: use ParentBased so sampling decision is inherited
            // from upstream (if they sampled, we sample too)
            sdktrace.ParentBased(
                sdktrace.TraceIDRatioBased(0.1), // 10% for root traces
            ),
        ),
    )

    // Register as global tracer provider
    otel.SetTracerProvider(tp)

    // Register W3C TraceContext propagator — reads/writes traceparent headers
    otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
        propagation.TraceContext{},
        propagation.Baggage{},
    ))

    tracer = otel.Tracer("order-service")

    return tp.Shutdown, nil
}

func main() {
    ctx := context.Background()

    shutdown, err := initTracer(ctx)
    if err != nil {
        panic(err)
    }
    defer shutdown(ctx)

    r := chi.NewRouter()

    // otelhttp auto-instruments all HTTP routes:
    // - Creates root spans from incoming requests
    // - Reads traceparent headers from incoming requests
    // - Sets span attributes (http.method, http.route, http.status_code)
    r.Use(func(next http.Handler) http.Handler {
        return otelhttp.NewHandler(next, "order-service",
            otelhttp.WithMessageEvents(otelhttp.ReadEvents, otelhttp.WriteEvents),
        )
    })

    r.Get("/healthz", livenessHandler)
    r.Get("/readyz", readinessHandler(/* db, redis */))
    r.Post("/v1/orders", createOrderHandler)

    http.ListenAndServe(":8080", r)
}

// livenessHandler — simple, just confirm process is alive
func livenessHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

// readinessHandler — check all dependencies
func readinessHandler(db *sql.DB, redis *redis.Client) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        checks := map[string]interface{}{}
        allOK := true

        // DB check with strict timeout
        dbCtx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
        defer cancel()
        if err := db.PingContext(dbCtx); err != nil {
            checks["database"] = map[string]string{"status": "error", "error": err.Error()}
            allOK = false
        } else {
            checks["database"] = map[string]string{"status": "ok"}
        }

        // Redis check
        redisCtx, cancel2 := context.WithTimeout(r.Context(), 1*time.Second)
        defer cancel2()
        if err := redis.Ping(redisCtx).Err(); err != nil {
            checks["redis"] = map[string]string{"status": "error", "error": err.Error()}
            allOK = false
        } else {
            checks["redis"] = map[string]string{"status": "ok"}
        }

        status := "ready"
        httpStatus := http.StatusOK
        if !allOK {
            status = "not_ready"
            httpStatus = http.StatusServiceUnavailable
        }

        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(httpStatus)
        json.NewEncoder(w).Encode(map[string]interface{}{
            "status": status,
            "checks": checks,
        })
    }
}

// createOrderHandler demonstrates manual span creation
func createOrderHandler(w http.ResponseWriter, r *http.Request) {
    // The root span is already created by otelhttp middleware
    // We add a child span for the business logic
    ctx, span := tracer.Start(r.Context(), "createOrder",
        trace.WithAttributes(
            attribute.String("order.source", "web"),
        ),
    )
    defer span.End()

    var req CreateOrderRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        span.RecordError(err)
        span.SetStatus(codes.Error, "invalid request body")
        http.Error(w, "Bad request", http.StatusBadRequest)
        return
    }

    // Add request attributes to span
    span.SetAttributes(
        attribute.String("order.user_id", req.UserID),
        attribute.Float64("order.amount", req.Amount),
        attribute.Int("order.item_count", len(req.Items)),
    )

    // Validate inventory — child span
    if err := checkInventory(ctx, req.Items); err != nil {
        span.RecordError(err)
        span.SetStatus(codes.Error, "inventory check failed")
        http.Error(w, "Out of stock", http.StatusConflict)
        return
    }

    // Create order in DB — child span automatically created by DB instrumentation
    order, err := db.CreateOrder(ctx, req)
    if err != nil {
        span.RecordError(err)
        span.SetStatus(codes.Error, "db error")
        http.Error(w, "Internal error", http.StatusInternalServerError)
        return
    }

    span.SetAttributes(attribute.String("order.id", order.ID))
    span.SetStatus(codes.Ok, "")

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(order)
}

// checkInventory — creates its own child span
func checkInventory(ctx context.Context, items []OrderItem) error {
    ctx, span := tracer.Start(ctx, "checkInventory")
    defer span.End()

    span.SetAttributes(attribute.Int("items.count", len(items)))

    // The HTTP client call to inventory service will automatically propagate
    // the traceparent header if you use otelhttp transport
    resp, err := inventoryClient.CheckStock(ctx, items)
    if err != nil {
        span.RecordError(err)
        span.SetStatus(codes.Error, err.Error())
        return err
    }

    span.SetAttributes(attribute.Bool("inventory.available", resp.Available))
    return nil
}
```

---

### Node.js + Express

```javascript
// Dependencies: @opentelemetry/sdk-node, @opentelemetry/auto-instrumentations-node
// @opentelemetry/exporter-trace-otlp-grpc

// tracing.js — must be required BEFORE your app code
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');
const { TraceIdRatioBased, ParentBasedSampler } = require('@opentelemetry/sdk-trace-node');

const sdk = new NodeSDK({
    resource: new Resource({
        [SemanticResourceAttributes.SERVICE_NAME]: 'order-service',
        [SemanticResourceAttributes.SERVICE_VERSION]: '1.4.2',
        [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: 'production',
    }),
    traceExporter: new OTLPTraceExporter({
        url: 'grpc://localhost:4317',
    }),
    sampler: new ParentBasedSampler({
        root: new TraceIdRatioBased(0.1), // 10% sample rate for root spans
    }),
    instrumentations: [
        getNodeAutoInstrumentations({
            '@opentelemetry/instrumentation-http': { enabled: true },
            '@opentelemetry/instrumentation-express': { enabled: true },
            '@opentelemetry/instrumentation-pg': { enabled: true },      // PostgreSQL
            '@opentelemetry/instrumentation-ioredis': { enabled: true }, // Redis
        }),
    ],
});

sdk.start();
process.on('SIGTERM', () => sdk.shutdown());

// app.js — start with: node -r ./tracing.js app.js
const express = require('express');
const { trace, context, SpanStatusCode } = require('@opentelemetry/api');

const app = express();
app.use(express.json());

const tracer = trace.getTracer('order-service', '1.4.2');

// Health endpoints
app.get('/healthz', (req, res) => res.json({ status: 'ok' }));

app.get('/readyz', async (req, res) => {
    const checks = {};
    let allOK = true;

    try {
        await Promise.race([
            db.query('SELECT 1'),
            new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 2000))
        ]);
        checks.database = { status: 'ok' };
    } catch (err) {
        checks.database = { status: 'error', error: err.message };
        allOK = false;
    }

    try {
        await Promise.race([
            redis.ping(),
            new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 1000))
        ]);
        checks.redis = { status: 'ok' };
    } catch (err) {
        checks.redis = { status: 'error', error: err.message };
        allOK = false;
    }

    res.status(allOK ? 200 : 503).json({
        status: allOK ? 'ready' : 'not_ready',
        checks,
    });
});

app.post('/v1/orders', async (req, res) => {
    // Create a child span (parent span already created by otelhttp instrumentation)
    const span = tracer.startSpan('createOrder', {
        attributes: {
            'order.user_id': req.body.userId,
            'order.amount': req.body.amount,
            'order.item_count': req.body.items?.length || 0,
        },
    });

    // Bind span to current context
    const ctx = trace.setSpan(context.active(), span);

    try {
        const order = await context.with(ctx, async () => {
            // All async operations inside context.with() will be children of our span
            return await orderService.create(req.body);
        });

        span.setAttributes({ 'order.id': order.id });
        span.setStatus({ code: SpanStatusCode.OK });
        res.status(201).json(order);
    } catch (err) {
        span.recordException(err);
        span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        span.end();
    }
});

app.listen(8080);
```

---

### Python + FastAPI

```python
# Dependencies: opentelemetry-sdk, opentelemetry-exporter-otlp-proto-grpc
# opentelemetry-instrumentation-fastapi, opentelemetry-instrumentation-sqlalchemy
# opentelemetry-instrumentation-redis

from contextlib import asynccontextmanager
from typing import Optional
import asyncio

from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import (
    ParentBasedTraceIdRatio,
    DEFAULT_ON,
)
from opentelemetry.trace import StatusCode


def configure_tracing():
    """Initialize OpenTelemetry with OTLP exporter."""
    resource = Resource.create({
        SERVICE_NAME: "order-service",
        SERVICE_VERSION: "1.4.2",
        "deployment.environment": "production",
    })

    provider = TracerProvider(
        resource=resource,
        sampler=ParentBasedTraceIdRatio(0.1),  # 10% sampling for root spans
    )

    # OTLP exporter — sends to OTel Collector
    exporter = OTLPSpanExporter(
        endpoint="http://localhost:4317",
        insecure=True,
    )

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrument DB and Redis
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()


configure_tracing()
tracer = trace.get_tracer("order-service", "1.4.2")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

# Auto-instrument FastAPI — creates spans for all requests
FastAPIInstrumentor.instrument_app(app)


# ─── Health Endpoints ─────────────────────────────────────────────────────────

@app.get("/healthz")
async def liveness():
    """Liveness: just return 200 if process is running."""
    return {"status": "ok"}


@app.get("/readyz")
async def readiness():
    """Readiness: check all dependencies with timeouts."""
    checks = {}
    all_ok = True

    # Check DB with timeout
    try:
        await asyncio.wait_for(db.execute("SELECT 1"), timeout=2.0)
        checks["database"] = {"status": "ok"}
    except asyncio.TimeoutError:
        checks["database"] = {"status": "error", "error": "timeout"}
        all_ok = False
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}
        all_ok = False

    # Check Redis
    try:
        await asyncio.wait_for(redis.ping(), timeout=1.0)
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)}
        all_ok = False

    if not all_ok:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": checks}
        )

    return {"status": "ready", "checks": checks}


# ─── Business Routes ──────────────────────────────────────────────────────────

@app.post("/v1/orders", status_code=201)
async def create_order(request: CreateOrderRequest):
    """Create order with manual tracing."""
    # Get current span (already created by FastAPIInstrumentor)
    current_span = trace.get_current_span()
    current_span.set_attributes({
        "order.user_id": request.user_id,
        "order.amount": float(request.amount),
        "order.item_count": len(request.items),
    })

    # Create child span for business validation logic
    with tracer.start_as_current_span("validateAndCreateOrder") as span:
        try:
            # Check inventory — this will have its own child span
            # (auto-instrumented if using aiohttp or httpx)
            await check_inventory(request.items)

            # Create order — DB calls auto-instrumented by SQLAlchemyInstrumentor
            order = await order_service.create(request)

            span.set_attributes({"order.id": order.id})
            span.set_status(StatusCode.OK)

            return order

        except OutOfStockError as e:
            span.record_exception(e)
            span.set_status(StatusCode.ERROR, str(e))
            raise HTTPException(status_code=409, detail="Item out of stock")

        except Exception as e:
            span.record_exception(e)
            span.set_status(StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Internal server error")


async def check_inventory(items: list) -> None:
    """Check inventory with its own span."""
    with tracer.start_as_current_span("checkInventory") as span:
        span.set_attributes({"items.count": len(items)})

        # HTTP call to inventory service — propagates traceparent header
        # automatically if using opentelemetry-instrumentation-httpx
        response = await inventory_client.check_stock(items)

        if not response.available:
            span.set_status(StatusCode.ERROR, "out of stock")
            raise OutOfStockError("One or more items are out of stock")

        span.set_status(StatusCode.OK)
```

---

## 13. Common Patterns & Best Practices

### 1. Use Span Events for Significant Moments Within a Span

```go
// Instead of creating a child span for every small thing,
// use span events for noteworthy moments within a span
span.AddEvent("cache_miss", trace.WithAttributes(
    attribute.String("cache.key", cacheKey),
))
span.AddEvent("db_fallback_started")

// Events are timestamped and visible in Jaeger
// Good for: cache hit/miss, retry attempts, cache warmup, state transitions
```

### 2. Propagate Context Through goroutines

```go
// WRONG — context not propagated, span lost
go func() {
    doSomethingWithDB(context.Background()) // no trace context!
}()

// CORRECT — always pass ctx through
go func(ctx context.Context) {
    doSomethingWithDB(ctx) // inherits trace context
}(ctx)
```

### 3. Readiness Check Should Be Fast

```go
// Readiness is called every 5 seconds by Kubernetes
// It must complete quickly or you'll have cascading timeouts

// Add a short circuit — if the last check passed < 3 seconds ago, skip
var lastCheck time.Time
var lastCheckResult bool

func isReady() bool {
    if time.Since(lastCheck) < 3*time.Second {
        return lastCheckResult
    }
    // ... run actual checks
}
```

### 4. Span Naming — Use Consistent Conventions

```go
// Consistent naming makes Jaeger/Zipkin easy to navigate
// Format: "noun verb" or "service.operation"

tracer.Start(ctx, "orders.create")          // Good
tracer.Start(ctx, "db.query.users")         // Good
tracer.Start(ctx, "cache.get")              // Good
tracer.Start(ctx, "payment.charge_card")    // Good

tracer.Start(ctx, "handler")                // Bad — too generic
tracer.Start(ctx, "doSomething")            // Bad — meaningless
```

### 5. Record Errors on Spans

```go
// Always record errors on spans — they show up in Jaeger with stack traces
if err != nil {
    span.RecordError(err)                              // Records the error
    span.SetStatus(codes.Error, err.Error())           // Marks span as failed
    // Now Jaeger will show this span in red
}

// Don't just log the error — record it on the span too
```

---

## 14. Common Pitfalls

### Pitfall 1: Not Propagating TraceContext in Internal HTTP Calls

```go
// WRONG — trace context lost, spans not linked
req, _ := http.NewRequest("POST", inventoryURL, body)
// No traceparent header — Inventory Service creates a new trace, not a child

// CORRECT — use otelhttp transport which automatically injects headers
client := &http.Client{
    Transport: otelhttp.NewTransport(http.DefaultTransport),
}
req, _ := http.NewRequestWithContext(ctx, "POST", inventoryURL, body)
client.Do(req) // traceparent header automatically injected
```

### Pitfall 2: Liveness Probe Checks Dependencies

```go
// WRONG — if DB goes down, all pods restart, making the outage worse
func livenessHandler(w http.ResponseWriter, r *http.Request) {
    if err := db.Ping(); err != nil {
        w.WriteHeader(503) // Triggers pod restart — BAD
    }
}

// CORRECT — liveness only checks if process is functional
func livenessHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(200) // If we can respond, we're alive
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}
```

### Pitfall 3: No Timeout on Health Check Dependencies

```go
// WRONG — if DB hangs, readiness probe hangs, Kubernetes restarts the pod
func readinessHandler(w http.ResponseWriter, r *http.Request) {
    if err := db.Ping(); err != nil { // No timeout — can hang forever
        w.WriteHeader(503)
    }
}

// CORRECT
func readinessHandler(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
    defer cancel()
    if err := db.PingContext(ctx); err != nil {
        w.WriteHeader(503)
        return
    }
    w.WriteHeader(200)
}
```

### Pitfall 4: Alerting on Symptoms, Not Causes

```
WRONG: Alert when CPU > 80%
       CPU is high — but is there a problem? Maybe it's just a traffic spike.
       Alert fatigue. Team learns to ignore CPU alerts.

RIGHT: Alert when error rate exceeds SLO burn rate.
       Users are experiencing errors. This is always actionable.
```

### Pitfall 5: Missing Span End

```go
// WRONG — span never ends, appears as pending in Jaeger forever
ctx, span := tracer.Start(ctx, "doSomething")
result, err := doSomething(ctx)
if err != nil {
    return err // span.End() never called
}
span.End()

// CORRECT — defer ensures End() is always called
ctx, span := tracer.Start(ctx, "doSomething")
defer span.End()
result, err := doSomething(ctx)
```

---

## 15. Interview Questions

**Q1: What is a trace and how is it different from a log?**

A log is a discrete event record — what happened at a specific time in a specific service. A trace represents a complete request journey across multiple services, composed of spans (units of work) linked by a common trace ID. Logs tell you what happened; traces tell you the sequence, timing, and causality of everything that happened during one request. A single trace might aggregate spans from 10 services, with timing that shows exactly which service and which operation was the bottleneck.

**Q2: What is OpenTelemetry?**

OpenTelemetry (OTel) is a CNCF open-source observability framework that provides vendor-neutral APIs, SDKs, and instrumentation for generating traces, metrics, and logs. Before OTel, you'd lock into a vendor's SDK (DataDog, New Relic, etc.) — switching required rewriting all instrumentation. With OTel, you instrument once against the OTel API, then configure an exporter to send to any backend: Jaeger, Zipkin, DataDog, Honeycomb, etc. The OTel Collector is an optional sidecar/gateway that receives OTLP telemetry, processes it, and fans out to multiple backends.

**Q3: What is the difference between liveness and readiness probes?**

Liveness checks if the process is in a healthy runnable state — if it fails, Kubernetes **restarts** the container. Use a simple check (can the process respond at all?). Never check external dependencies in liveness — if DB goes down and all pods fail liveness, they all restart simultaneously, making the outage worse.

Readiness checks if the service is ready to receive traffic — if it fails, Kubernetes **removes the pod from the load balancer** (pod keeps running but gets no requests). Check all required dependencies (DB, Redis, etc.) with short timeouts. Use for graceful startup and dependency outage handling.

**Q4: What is an SLO vs SLA?**

An SLO (Service Level Objective) is an internal reliability target — what your team commits to achieving, e.g., "99.9% of requests succeed in < 200ms over a 30-day window." It's set by engineering based on user expectations and system capabilities.

An SLA (Service Level Agreement) is a contractual commitment with customers, often with financial penalties for violation. SLAs should be less strict than SLOs — the gap between SLO and SLA gives you a safety margin. If your SLO is 99.9%, your SLA might be 99.5%.

**Q5: What is tail-based sampling and when do you use it?**

Tail-based sampling buffers all spans for a trace and makes the sampling decision *after* the trace is complete, based on the outcome. This allows you to always keep 100% of traces that contain errors or exceeded latency thresholds, while discarding most successful fast traces. It's better than head-based sampling (decide at trace start) because you can't predict at request start which requests will fail or be slow. Tail sampling is implemented in the OTel Collector (not the application) since it needs to see all spans before deciding. Use in production for high-traffic services.

**Q6: How would you debug a slow endpoint using distributed tracing?**

1. Open Jaeger/Zipkin, filter by the slow endpoint and time range
2. Sort traces by duration, open the slowest ones
3. Look at the waterfall — find the widest (slowest) span
4. Check if the bottleneck is: an external API call, N+1 DB queries (many sequential identical-looking DB spans), a lock/mutex (gap between spans), or serialization overhead
5. Check span attributes and events for additional context (e.g., cache miss events)
6. Cross-reference with logs using the trace_id to get the exact error messages
7. Cross-reference with metrics to determine if this is affecting many users (p99 latency dashboard)

---

## 16. Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/) — Official OTel docs
- [Jaeger Documentation](https://www.jaegertracing.io/docs/) — Jaeger distributed tracing system
- [W3C TraceContext Specification](https://www.w3.org/TR/trace-context/) — The traceparent header standard
- [Google SRE Book — Chapter 4: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) — Origin of SLO/SLA/Error Budget concepts
- [SLO Burn Rate Alerting](https://sre.google/workbook/alerting-on-slos/) — Google's multi-window burn rate alerting guide
- [OpenTelemetry Go Contrib](https://github.com/open-telemetry/opentelemetry-go-contrib) — Auto-instrumentation for Go frameworks
- [Kubernetes Health Check Best Practices](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) — Official K8s probe documentation
- [Tail Sampling in OTel Collector](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/tailsamplingprocessor) — Tail sampling processor config

---

**Next:** [Part 14.1: Security & OWASP](../part-14/14-security-owasp.md)
