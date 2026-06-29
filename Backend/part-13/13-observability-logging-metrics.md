# Part 13.1: Observability — Structured Logging & Metrics

## What You'll Learn
- The three pillars of observability and how they complement each other
- Why structured logging beats printf-style logging at scale
- Log levels, what to include in every log line, and what never to include
- Correlation IDs and propagating context across service boundaries
- Metrics types: counters, gauges, histograms, summaries
- RED and USE methods for systematic metric coverage
- Prometheus pull model, PromQL, and high-cardinality pitfalls
- Grafana dashboards, SLO tracking, and alerting
- Production-ready implementations in Go, Node.js, and Python

## Table of Contents
1. [The Three Pillars of Observability](#1-the-three-pillars-of-observability)
2. [Structured Logging](#2-structured-logging)
3. [Log Levels](#3-log-levels)
4. [What Every Log Line Should Include](#4-what-every-log-line-should-include)
5. [Correlation IDs](#5-correlation-ids)
6. [Log Sampling](#6-log-sampling)
7. [Log Rotation and Retention](#7-log-rotation-and-retention)
8. [PII and Compliance](#8-pii-and-compliance)
9. [Metrics — Types and Semantics](#9-metrics--types-and-semantics)
10. [RED and USE Methods](#10-red-and-use-methods)
11. [Prometheus](#11-prometheus)
12. [PromQL Basics](#12-promql-basics)
13. [Grafana and Alerting](#13-grafana-and-alerting)
14. [Implementation Examples](#14-implementation-examples)
15. [Common Patterns & Best Practices](#15-common-patterns--best-practices)
16. [Common Pitfalls](#16-common-pitfalls)
17. [Interview Questions](#17-interview-questions)
18. [Resources](#18-resources)

---

## 1. The Three Pillars of Observability

Observability is the ability to understand the internal state of a system from its external outputs. In distributed systems, this is non-trivial — a single user request might touch 10 services, spawn 30 database queries, and complete in 200ms across 5 data centers.

The three pillars give you different lenses into the same system:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    THE THREE PILLARS                                 │
├──────────────────┬──────────────────────┬───────────────────────────┤
│      LOGS        │       METRICS        │         TRACES            │
├──────────────────┼──────────────────────┼───────────────────────────┤
│ Discrete events  │ Aggregated numbers   │ Request flow across       │
│ What happened    │ How system behaves   │ services                  │
│                  │ over time            │ Where time is spent       │
├──────────────────┼──────────────────────┼───────────────────────────┤
│ "User 123 failed │ "Error rate: 2.3%"   │ "Auth: 5ms,               │
│ login at 14:02"  │ "p99 latency: 450ms" │  DB: 150ms,               │
│                  │ "Queue depth: 4500"  │  Redis: 2ms"              │
├──────────────────┼──────────────────────┼───────────────────────────┤
│ Storage: high    │ Storage: low         │ Storage: medium           │
│ Query: slow      │ Query: fast          │ Query: medium             │
│ Cardinality: any │ Cardinality: low     │ Cardinality: medium       │
└──────────────────┴──────────────────────┴───────────────────────────┘
```

**When to use which:**
- **Logs**: Debugging a specific incident, auditing, understanding the exact sequence of events for one request
- **Metrics**: Dashboards, alerting, capacity planning, trend analysis
- **Traces**: Performance optimization, identifying bottlenecks in distributed requests, N+1 query detection

They are **complementary, not alternatives**. A good observability setup has all three. When an alert fires (metric), you look at traces to find the slow span, then look at logs for that specific request.

---

## 2. Structured Logging

### Unstructured Logging (The Old Way)

```python
# Unstructured — grep-able only by text matching
print(f"User {user_id} failed to login from {ip_address} at {timestamp}")
print(f"DB query took {duration}ms for query {query_type}")
print(f"ERROR: Payment failed for order {order_id}: {error_message}")
```

Problems with unstructured logging:
- **Hard to query**: You can grep for "ERROR" but not "all errors in the last hour where user_id starts with 123"
- **No consistent schema**: Every developer formats differently
- **Multi-line logs break parsers**: Stack traces, JSON payloads — log aggregators struggle
- **No machine readability**: ELK/Loki cannot index fields they cannot identify

### Structured Logging (The Right Way)

Structured logging means every log line is a machine-parseable document (JSON) with consistent fields:

```json
{
  "timestamp": "2026-06-29T08:34:12.543Z",
  "level": "ERROR",
  "message": "Payment failed",
  "service": "payment-service",
  "version": "1.4.2",
  "environment": "production",
  "request_id": "req_8f3a2b1c",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "user_id": "user_abc123",
  "order_id": "ord_xyz789",
  "error": "insufficient_funds",
  "duration_ms": 234,
  "http_status": 402
}
```

Now you can query in Kibana/Grafana Loki:
```
# All errors for user_abc123 in the last hour
{service="payment-service"} | json | level="ERROR" | user_id="user_abc123"

# P99 duration by endpoint
avg_over_time({service="payment-service"} | json | unwrap duration_ms [5m]) by (path)
```

### Why JSON is the standard

1. **Universally parseable** — every language, every tool
2. **Nested structures** — you can log complex objects
3. **Type preservation** — numbers stay numbers, booleans stay booleans
4. **Consistent with API responses** — same mental model throughout

---

## 3. Log Levels

Log levels are not just severity labels — they are a **sampling and routing mechanism**. Understanding when to use each level is critical:

```
TRACE/VERBOSE   ← extremely detailed, function entry/exit, usually disabled
    │
    ▼
  DEBUG          ← verbose detail useful during development
    │
    ▼
  INFO           ← normal operational events (request served, user logged in)
    │
    ▼
  WARN           ← something unexpected happened but we handled it
    │
    ▼
  ERROR          ← something went wrong, needs attention
    │
    ▼
  FATAL/CRITICAL ← system cannot continue, process exits
```

### Level Decision Guide

| Level | When to Use | Example |
|-------|-------------|---------|
| `DEBUG` | Implementation details, variable states, SQL queries | `DEBUG: Executing query SELECT * FROM users WHERE id=?` |
| `INFO` | Normal operations, lifecycle events | `INFO: Server started on :8080` / `INFO: User logged in` |
| `WARN` | Handled errors, degraded mode, deprecated usage | `WARN: Cache miss, falling back to DB` / `WARN: Retry 2/3` |
| `ERROR` | Unhandled errors, failed operations | `ERROR: DB connection failed` / `ERROR: Payment processing failed` |
| `FATAL` | Unrecoverable state, process will exit | `FATAL: Cannot read config file, exiting` |

### Production Logging Levels

```
Development:  DEBUG and above
Staging:      INFO and above
Production:   INFO and above (ERROR and above for some services)
```

In production, `DEBUG` logs flood your log aggregator and cost money. Most services run at `INFO` level. If you need to debug a production issue, you temporarily lower the log level for a specific service instance.

---

## 4. What Every Log Line Should Include

A well-structured log line is a **forensic record**. After an incident, you should be able to reconstruct what happened from logs alone.

### Required Fields

```json
{
  "timestamp":   "2026-06-29T08:34:12.543Z",   // ISO 8601, UTC always
  "level":       "ERROR",                        // Log level
  "message":     "Payment processing failed",    // Human-readable description
  "service":     "payment-service",              // Which microservice
  "version":     "1.4.2",                        // Deployment version for regression tracking
  "environment": "production",                   // prod/staging/dev
  "request_id":  "req_8f3a2b1c9d2e",            // Unique per request
  "trace_id":    "4bf92f3577b34da6a",            // OpenTelemetry trace ID
  "span_id":     "00f067aa0ba902b7",             // Current span
  "duration_ms": 234,                            // How long the operation took
  "http_method": "POST",                         // HTTP method
  "http_path":   "/v1/payments",                 // URL path (not query string with PII)
  "http_status": 402                             // Response status code
}
```

### Contextual Fields (Add When Relevant)

```json
{
  "user_id":    "user_abc123",    // Who is making the request (hashed/opaque ID)
  "order_id":   "ord_xyz789",     // Domain entity being operated on
  "error":      "insufficient_funds",
  "error_code": "PAY_001",
  "retry_count": 2,
  "component":  "stripe_client"
}
```

### For Errors — Always Include

```json
{
  "error":       "stripe.CardError: Your card has insufficient funds",
  "error_type":  "stripe.CardError",
  "error_code":  "card_declined",
  "stack_trace": "..." // In development. In production, log the trace_id instead
}
```

**In production, avoid full stack traces in logs** — they are verbose and often contain sensitive paths. Log the error message and the trace ID; retrieve the stack trace from your APM tool using the trace ID.

---

## 5. Correlation IDs

### The Problem Without Correlation IDs

```
# Log from gateway
INFO: Request received path=/checkout user_id=123

# Log from order-service
INFO: Creating order for customer_id=456

# Log from payment-service
ERROR: Payment failed order_id=789

# Question: Are these three log lines from the same request?
# Answer: You have no idea.
```

### Correlation IDs Solve This

A correlation ID (also called request ID or trace ID) is a UUID generated at the request entry point and **propagated to every downstream service**.

```
Client → API Gateway → Order Service → Payment Service → DB
           │                │                │
           └── request_id: "req_8f3a2b1c" ──┘
                propagated via HTTP headers
```

**Standard HTTP headers for propagation:**

```
X-Request-ID: req_8f3a2b1c9d2e4f5a       # Custom request ID
X-Correlation-ID: corr_a1b2c3d4e5f6      # Correlation across systems
traceparent: 00-4bf92f3577b34da6a-00f067aa0ba902b7-01  # W3C TraceContext
```

### Propagation Pattern

```
1. Request arrives at gateway
2. Gateway generates request_id = uuid() (or reads from X-Request-ID header if trusted)
3. Gateway adds request_id to:
   - Its own log context
   - The downstream HTTP headers when calling services
   - The response headers (so client can include it in support tickets)
4. Each service reads X-Request-ID from incoming request
5. Each service adds it to its log context
6. Each service forwards it to its own downstream calls
```

Now every log line across every service for the same user request has the same `request_id`:

```bash
# Grep all logs across all services for one request
grep '"request_id":"req_8f3a2b1c"' /var/log/services/*.log
```

### Context Propagation in Code

**Go — Using context.Context:**
```go
// Middleware attaches request_id to context
func RequestIDMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        requestID := r.Header.Get("X-Request-ID")
        if requestID == "" {
            requestID = uuid.New().String()
        }
        ctx := context.WithValue(r.Context(), ctxKeyRequestID, requestID)
        w.Header().Set("X-Request-ID", requestID)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

// Downstream: extract from context when calling other services
func callPaymentService(ctx context.Context, orderID string) error {
    requestID, _ := ctx.Value(ctxKeyRequestID).(string)
    req, _ := http.NewRequestWithContext(ctx, "POST", paymentURL, body)
    req.Header.Set("X-Request-ID", requestID)
    // ...
}
```

---

## 6. Log Sampling

Not every log line needs to be stored forever. At scale, logging 100% of traffic is expensive:
- 10,000 req/sec × 1KB per log = 10MB/sec = 864GB/day

### Sampling Strategy

```
Errors and warnings:  100% — always log, these need attention
Slow requests:        100% — requests above latency threshold
Normal requests:      1-5%  — random sample sufficient for analysis
```

### Head-Based vs Tail-Based Sampling

**Head-based sampling** (simple): Decide at request start whether to log this request.
```go
// Log 1% of normal requests
func shouldSample(level LogLevel) bool {
    if level >= WARN {
        return true // Always log errors and warnings
    }
    return rand.Float32() < 0.01 // 1% of INFO/DEBUG
}
```

**Tail-based sampling** (smarter): Buffer the logs, make sampling decision at end of request based on outcome:
```
- If request returned 5xx: save all buffered logs
- If request took > 500ms: save all buffered logs
- Otherwise: discard
```

This is better because you always have logs for problematic requests without knowing in advance which those will be.

---

## 7. Log Rotation and Retention

### On-Disk Log Rotation

```
Production log lifecycle:
  Day 0: app.log (current)
  Day 1: app.log.2026-06-29.gz (rotated and compressed)
  Day 30: delete logs older than 30 days
```

Tools: `logrotate` on Linux, or built into logging libraries.

### Centralized Log Aggregation (Production Standard)

Don't store logs on individual servers. Use:

```
                   ┌─────────────────────────────┐
Service A logs ───►│                             │
Service B logs ───►│  Log Aggregator             ├──► Elasticsearch/OpenSearch
Service C logs ───►│  (Fluentd/Vector/Filebeat)  │    or Grafana Loki
Container logs ───►│                             │
                   └─────────────────────────────┘
                              │
                              ▼
                        Grafana / Kibana
                         (Query & Visualize)
```

### Retention Policies

| Log Type | Retention |
|----------|-----------|
| Application logs | 30-90 days |
| Security/audit logs | 1-7 years (compliance) |
| Access logs | 90 days |
| Debug logs | 7 days |

Costs money to store — tier older logs to cold storage (S3 Glacier).

---

## 8. PII and Compliance

**Never log:**
- Passwords (even hashed)
- Full credit card numbers (PAN)
- CVV codes
- Social Security Numbers (SSN / Aadhaar)
- Full bank account numbers
- OAuth tokens, API keys, JWTs (they're credentials)
- PHI — Protected Health Information (HIPAA)

**Regulations that mandate this:**
- **GDPR** (EU): Log access, right to deletion — if PII is in logs, deleting it is nearly impossible
- **PCI-DSS**: Card data must not appear in logs
- **HIPAA**: Health information must not appear in logs
- **SOC 2**: Audit controls on data access

### Safe Alternatives

```go
// Bad — logs full card number
log.Info("Processing payment", "card_number", card.Number)

// Good — log only last 4 digits
log.Info("Processing payment", "card_last4", card.Number[len(card.Number)-4:])

// Bad — logs user email
log.Info("User logged in", "email", user.Email)

// Good — log opaque user ID only
log.Info("User logged in", "user_id", user.ID)

// Never log the JWT — it's a bearer credential
// Bad:
log.Debug("Auth header", "authorization", r.Header.Get("Authorization"))
```

### Data Masking in Middleware

```go
func maskSensitiveFields(fields map[string]interface{}) map[string]interface{} {
    sensitiveKeys := map[string]bool{
        "password": true, "card_number": true, "cvv": true,
        "ssn": true, "token": true, "secret": true,
    }
    for k := range fields {
        if sensitiveKeys[strings.ToLower(k)] {
            fields[k] = "[REDACTED]"
        }
    }
    return fields
}
```

---

## 9. Metrics — Types and Semantics

Metrics are numerical measurements sampled over time. Unlike logs, metrics are **aggregated** — you don't store every individual request, you store summary statistics.

### Counter

A counter only goes up (resets on process restart).

```
Use for:
- Total HTTP requests served
- Total errors
- Total bytes sent
- Total successful logins
- Total jobs processed

Never use for:
- Values that can decrease (use Gauge instead)
```

```
http_requests_total{method="GET", path="/users", status="200"} = 142857
http_requests_total{method="GET", path="/users", status="500"} = 23
```

### Gauge

A gauge can go up or down — it represents a current state.

```
Use for:
- Current number of active connections
- Current queue depth
- Current memory usage
- CPU utilization right now
- Number of goroutines / threads
- Cache hit rate (current)
```

```
active_connections{service="api"} = 342
queue_depth{queue="email"} = 1547
memory_bytes{type="heap"} = 524288000
```

### Histogram

A histogram samples observations and places them in configurable **buckets**. Crucial for understanding **distributions** of values like latency.

```
http_request_duration_seconds_bucket{le="0.005"} = 24054  ← requests < 5ms
http_request_duration_seconds_bucket{le="0.01"}  = 33444  ← requests < 10ms
http_request_duration_seconds_bucket{le="0.025"} = 100392 ← requests < 25ms
http_request_duration_seconds_bucket{le="0.05"}  = 129389 ← requests < 50ms
http_request_duration_seconds_bucket{le="0.1"}   = 133988 ← requests < 100ms
http_request_duration_seconds_bucket{le="0.25"}  = 143423 ← requests < 250ms
http_request_duration_seconds_bucket{le="0.5"}   = 145072 ← requests < 500ms
http_request_duration_seconds_bucket{le="1.0"}   = 145143 ← requests < 1s
http_request_duration_seconds_bucket{le="+Inf"}  = 145144 ← all requests
http_request_duration_seconds_sum               = 2693.3
http_request_duration_seconds_count            = 145144
```

From this you can calculate **percentile latencies** using PromQL.

### Summary

A summary is similar to a histogram but calculates quantiles **client-side** (in the application process). 

```
# Summary pre-calculates percentiles
http_request_duration_seconds{quantile="0.5"}  = 0.052
http_request_duration_seconds{quantile="0.9"}  = 0.113
http_request_duration_seconds{quantile="0.99"} = 0.392
```

**Histogram vs Summary:**

| Aspect | Histogram | Summary |
|--------|-----------|---------|
| Quantile calculation | Server-side (PromQL) | Client-side (app) |
| Aggregatable across instances | Yes | No |
| Configurable post-hoc | Yes | No (quantiles fixed at code time) |
| Recommendation | **Use histogram** | Avoid in new systems |

The key advantage of histograms is that you can **aggregate across multiple instances** — if you have 10 servers, you can combine their histograms in PromQL to get fleet-wide p99. Summaries from different instances cannot be combined meaningfully.

---

## 10. RED and USE Methods

These are systematic frameworks for deciding what to measure. Without a framework, teams measure random things and miss important signals.

### RED Method (for Services)

Every **service** should have these three metrics:

```
R — Rate:     How many requests per second is this service handling?
E — Errors:   What fraction of requests are resulting in errors?
D — Duration: How long do requests take? (p50, p95, p99)
```

```
# Rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Duration p99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

Apply RED to every service in your system: API gateway, auth service, payment service, notification service.

### USE Method (for Resources)

Every **resource** (CPU, memory, disk, network) should have these three metrics:

```
U — Utilization: How busy is the resource? (CPU: 67%, Disk: 84%)
S — Saturation:  Is the resource overloaded? (queue depth, wait time)
E — Errors:      Are there errors? (disk errors, network packet drops)
```

```
┌─────────────────────────────────────────────────────┐
│                  USE Checklist                       │
├──────────────┬────────────┬────────────┬────────────┤
│ Resource     │Utilization │ Saturation │  Errors    │
├──────────────┼────────────┼────────────┼────────────┤
│ CPU          │ Usage %    │ Run queue  │ (rare)     │
│ Memory       │ Used/Total │ Paging     │ OOM kills  │
│ Disk I/O     │ IOPS used  │ Wait time  │ I/O errors │
│ Network      │ Bandwidth  │ Drops/RTT  │ Errors     │
│ DB pool      │ Conns used │ Queue wait │ Timeouts   │
│ Thread pool  │ Threads    │ Queue size │ Panics     │
└──────────────┴────────────┴────────────┴────────────┘
```

**Combined approach in practice:**
- Use RED for your **application-level** dashboards (business metrics)
- Use USE for your **infrastructure-level** dashboards (system health)

---

## 11. Prometheus

Prometheus is the industry-standard metrics system. It uses a **pull model** — instead of services pushing metrics to a central server, Prometheus **scrapes** a `/metrics` HTTP endpoint on each service.

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Prometheus Architecture                   │
│                                                            │
│  ┌──────────────┐    scrape /metrics    ┌──────────────┐  │
│  │ API Service  │◄──────────────────────│              │  │
│  │ :9090/metrics│                       │  Prometheus  │  │
│  └──────────────┘                       │    Server    │  │
│                                         │              │  │
│  ┌──────────────┐    scrape /metrics    │  - TSDB      │  │
│  │ Order Service│◄──────────────────────│  - PromQL    │  │
│  │ :9090/metrics│                       │  - Alerting  │  │
│  └──────────────┘                       └──────┬───────┘  │
│                                                │           │
│  ┌──────────────┐    scrape /metrics           │           │
│  │  DB Exporter │◄──────────────────────┘      │           │
│  │ :9187/metrics│                              │           │
│  └──────────────┘                              ▼           │
│                                         ┌─────────────┐   │
│                                         │   Grafana   │   │
│                                         │  Alertmanager│  │
│                                         └─────────────┘   │
└────────────────────────────────────────────────────────────┘
```

### Pull Model vs Push Model

| Aspect | Pull (Prometheus) | Push (StatsD, InfluxDB) |
|--------|-------------------|-------------------------|
| Discovery | Prometheus discovers targets | Services must know where to push |
| Network direction | Prometheus pulls inward | Services push outward |
| Dead service detection | Easy — scrape fails | Harder — silence detection |
| Short-lived jobs | Hard (job may die before scrape) | Easy |
| Firewall complexity | Prometheus needs access to services | Services need access to collector |

For **short-lived jobs** (batch jobs, cron), Prometheus provides the **Pushgateway** — services push to it, and Prometheus scrapes the Pushgateway.

### Labels and High Cardinality

Labels are key-value pairs that add dimensions to metrics. They're powerful but dangerous when misused.

```
# Good labels — low cardinality (few distinct values)
http_requests_total{method="GET", path="/users", status="200"}
http_requests_total{method="POST", path="/orders", status="500"}

# The cardinality is: methods × paths × statuses = 5 × 20 × 15 = 1,500 time series
# This is fine.
```

**High cardinality problem:**

```
# BAD — user_id as a label
http_requests_total{user_id="user_abc123", path="/users", status="200"}
# If you have 10M users × 20 paths × 15 statuses = 3 BILLION time series
# Prometheus dies. OOM. Catastrophic failure.
```

**Rules for labels:**
- Labels should have bounded, small cardinality (< 1000 distinct values ideally)
- NEVER use: user_id, session_id, order_id, IP address, email, UUID
- OK to use: method, status code, endpoint path (normalized), environment, region, instance

**Normalizing paths:**
```
# Raw paths — high cardinality (each order has unique ID)
/orders/ord_abc123    ← bad label value
/orders/ord_xyz789    ← bad label value

# Normalized — low cardinality
/orders/:id           ← good — one label value for all orders
```

---

## 12. PromQL Basics

PromQL (Prometheus Query Language) is used to query and aggregate time series data.

### Essential Queries

```promql
# Total request rate across all instances (per second, over 5-minute window)
rate(http_requests_total[5m])

# Error rate as percentage
100 * rate(http_requests_total{status=~"5.."}[5m]) 
    / rate(http_requests_total[5m])

# p99 latency from histogram
histogram_quantile(0.99, 
  rate(http_request_duration_seconds_bucket[5m])
)

# p99 latency per endpoint
histogram_quantile(0.99,
  sum by (le, path) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)

# Average request rate grouped by HTTP method
sum by (method) (rate(http_requests_total[5m]))

# Active connections gauge
active_connections{service="api"}

# Memory usage above 80%
(node_memory_MemTotal_bytes - node_memory_MemFree_bytes) 
  / node_memory_MemTotal_bytes > 0.8
```

### Understanding rate() and irate()

```
rate(counter[5m])  — average rate over 5 minutes, smoothed
irate(counter[5m]) — instant rate, last two data points only, spiky

Use rate() for dashboards (smooth trends)
Use irate() for alerting (catches sudden spikes)
```

### Calculating Percentiles from Histograms

```promql
# The formula
histogram_quantile(φ, sum by (le) (rate(metric_bucket[window])))

# p50 (median)
histogram_quantile(0.50, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

# p95
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

# p99
histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
```

**How histogram_quantile works:**
Prometheus uses linear interpolation between bucket boundaries to estimate the percentile. The accuracy depends on your bucket configuration — buckets should be densely packed where your values typically fall.

---

## 13. Grafana and Alerting

### Essential Dashboards

**Service RED Dashboard:**
```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│   Request Rate      │    Error Rate        │   p99 Latency       │
│   (req/sec)         │    (% of total)      │   (seconds)         │
│                     │                      │                     │
│  ████▄▄███▄         │    ▁▁▁▁▂▁▁▁▁▁▁      │   ▁▁▁▁▁▁▁▁▁▂▄      │
│  12.4 req/s         │    0.23%             │   142ms             │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

**SLO Tracking Dashboard:**
```
┌────────────────────────────────────────────────────────┐
│   SLO: 99.9% of requests complete in < 500ms           │
│   Current: 99.94% ████████████████████░ (0.06% budget) │
│   Error budget remaining: 43 minutes this month        │
└────────────────────────────────────────────────────────┘
```

### Alerting Rules

Prometheus alerting rules are defined in YAML and evaluated periodically:

```yaml
groups:
  - name: api_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status=~"5.."}[5m])
          / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanizePercentage }}"
          runbook: "https://wiki.example.com/runbooks/high-error-rate"

      # High latency
      - alert: HighLatencyP99
        expr: |
          histogram_quantile(0.99,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "p99 latency above 500ms"

      # Service down
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
```

### Alert Routing to PagerDuty

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'cluster']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'pagerduty-critical'
  routes:
    - match:
        severity: warning
      receiver: 'slack-warnings'

receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - routing_key: '<PD_KEY>'
        description: '{{ .CommonAnnotations.summary }}'

  - name: 'slack-warnings'
    slack_configs:
      - api_url: '<SLACK_WEBHOOK>'
        channel: '#alerts'
```

---

## 14. Implementation Examples

### Go + Chi Router

#### Setup with zerolog and Prometheus

```go
// go.mod dependencies:
// github.com/rs/zerolog
// github.com/prometheus/client_golang/prometheus
// github.com/prometheus/client_golang/prometheus/promauto
// github.com/prometheus/client_golang/prometheus/promhttp

package main

import (
    "net/http"
    "strconv"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
    "github.com/prometheus/client_golang/prometheus/promhttp"
    "github.com/rs/zerolog"
    "github.com/rs/zerolog/log"
)

// Metrics — defined at package level, registered once
var (
    httpRequestsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total HTTP requests processed",
        },
        []string{"method", "path", "status"},
    )

    httpRequestDuration = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "http_request_duration_seconds",
            Help:    "HTTP request duration in seconds",
            Buckets: []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5},
        },
        []string{"method", "path"},
    )

    // Custom business metric
    ordersCreatedTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "orders_created_total",
            Help: "Total orders created",
        },
        []string{"status"}, // "success" or "failed"
    )

    activeConnections = promauto.NewGauge(prometheus.GaugeOpts{
        Name: "active_connections",
        Help: "Current active HTTP connections",
    })
)

func main() {
    // zerolog setup — JSON output in production
    zerolog.TimeFieldFormat = zerolog.TimeFormatUnixMs
    logger := log.With().
        Str("service", "order-service").
        Str("version", "1.4.2").
        Str("environment", "production").
        Logger()

    r := chi.NewRouter()

    // Middleware stack
    r.Use(RequestIDMiddleware)
    r.Use(StructuredLoggingMiddleware(logger))
    r.Use(PrometheusMiddleware)
    r.Use(middleware.Recoverer)

    // Metrics endpoint — Prometheus scrapes this
    r.Handle("/metrics", promhttp.Handler())

    // Health endpoints
    r.Get("/healthz", livenessHandler)
    r.Get("/readyz", readinessHandler)

    // Business routes
    r.Post("/v1/orders", createOrderHandler)
    r.Get("/v1/orders/{id}", getOrderHandler)

    logger.Info().Str("addr", ":8080").Msg("Server starting")
    http.ListenAndServe(":8080", r)
}

// StructuredLoggingMiddleware logs every request as structured JSON
func StructuredLoggingMiddleware(logger zerolog.Logger) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            start := time.Now()

            // Wrap ResponseWriter to capture status code
            ww := middleware.NewWrapResponseWriter(w, r.ProtoMajor)

            // Attach logger with request context to context
            requestID := r.Header.Get("X-Request-ID")
            reqLogger := logger.With().
                Str("request_id", requestID).
                Str("method", r.Method).
                Str("path", r.URL.Path).
                Str("remote_addr", r.RemoteAddr).
                Logger()

            ctx := reqLogger.WithContext(r.Context())
            next.ServeHTTP(ww, r.WithContext(ctx))

            duration := time.Since(start)
            status := ww.Status()

            // Log at appropriate level based on status
            event := reqLogger.Info()
            if status >= 500 {
                event = reqLogger.Error()
            } else if status >= 400 {
                event = reqLogger.Warn()
            }

            event.
                Int("status", status).
                Dur("duration_ms", duration).
                Int("bytes", ww.BytesWritten()).
                Msg("Request completed")
        })
    }
}

// PrometheusMiddleware records request metrics
func PrometheusMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Normalize path — extract route pattern, not actual path
        // This prevents high cardinality (e.g., /orders/123 becomes /orders/{id})
        rctx := chi.RouteContext(r.Context())
        routePattern := r.URL.Path
        if rctx != nil && rctx.RoutePattern() != "" {
            routePattern = rctx.RoutePattern()
        }

        activeConnections.Inc()
        defer activeConnections.Dec()

        start := time.Now()
        ww := middleware.NewWrapResponseWriter(w, r.ProtoMajor)

        next.ServeHTTP(ww, r)

        duration := time.Since(start).Seconds()
        status := strconv.Itoa(ww.Status())

        httpRequestsTotal.WithLabelValues(r.Method, routePattern, status).Inc()
        httpRequestDuration.WithLabelValues(r.Method, routePattern).Observe(duration)
    })
}

// Business handler that logs and records custom metrics
func createOrderHandler(w http.ResponseWriter, r *http.Request) {
    logger := zerolog.Ctx(r.Context()) // Extract logger from context

    // ... parse request body ...
    var req CreateOrderRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        logger.Error().Err(err).Msg("Failed to decode request body")
        ordersCreatedTotal.WithLabelValues("failed").Inc()
        http.Error(w, "Invalid request", http.StatusBadRequest)
        return
    }

    order, err := orderService.Create(r.Context(), req)
    if err != nil {
        logger.Error().
            Err(err).
            Str("order_id", req.ID).
            Msg("Failed to create order")
        ordersCreatedTotal.WithLabelValues("failed").Inc()
        http.Error(w, "Internal error", http.StatusInternalServerError)
        return
    }

    logger.Info().
        Str("order_id", order.ID).
        Str("user_id", order.UserID).
        Float64("amount", order.Amount).
        Msg("Order created successfully")

    ordersCreatedTotal.WithLabelValues("success").Inc()

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(order)
}
```

---

### Node.js + Express

```javascript
// Dependencies: pino, prom-client, express, uuid

const express = require('express');
const pino = require('pino');
const { v4: uuidv4 } = require('uuid');
const client = require('prom-client');

// ─── Logger Setup ──────────────────────────────────────────────────────────

const logger = pino({
    level: process.env.LOG_LEVEL || 'info',
    // In production, output JSON; in development, pretty-print
    transport: process.env.NODE_ENV === 'development'
        ? { target: 'pino-pretty' }
        : undefined,
    base: {
        service: 'order-service',
        version: process.env.npm_package_version || '1.0.0',
        environment: process.env.NODE_ENV || 'production',
    },
    // Redact sensitive fields — pino will replace them with [Redacted]
    redact: {
        paths: ['req.headers.authorization', 'body.password', 'body.card_number'],
        censor: '[REDACTED]',
    },
    timestamp: pino.stdTimeFunctions.isoTime,
});

// ─── Prometheus Setup ───────────────────────────────────────────────────────

// Collect default Node.js metrics (CPU, memory, event loop lag)
client.collectDefaultMetrics({
    prefix: 'nodejs_',
    labels: { service: 'order-service' },
});

const httpRequestsTotal = new client.Counter({
    name: 'http_requests_total',
    help: 'Total HTTP requests',
    labelNames: ['method', 'path', 'status'],
});

const httpRequestDuration = new client.Histogram({
    name: 'http_request_duration_seconds',
    help: 'HTTP request duration in seconds',
    labelNames: ['method', 'path'],
    buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
});

const ordersCreatedTotal = new client.Counter({
    name: 'orders_created_total',
    help: 'Total orders created',
    labelNames: ['status'],
});

// ─── Middleware ─────────────────────────────────────────────────────────────

const app = express();
app.use(express.json({ limit: '1mb' }));

// Request ID middleware
app.use((req, res, next) => {
    req.requestId = req.headers['x-request-id'] || uuidv4();
    res.setHeader('X-Request-ID', req.requestId);
    
    // Child logger with request context
    req.log = logger.child({
        request_id: req.requestId,
        method: req.method,
        path: req.path,
    });
    
    next();
});

// Structured logging + Prometheus middleware
app.use((req, res, next) => {
    const start = Date.now();
    const end = httpRequestDuration.startTimer({ method: req.method, path: req.route?.path || req.path });

    res.on('finish', () => {
        const duration = Date.now() - start;
        const statusCode = res.statusCode.toString();

        httpRequestsTotal.inc({ method: req.method, path: req.route?.path || req.path, status: statusCode });
        end(); // Records histogram observation

        const logEvent = {
            status: res.statusCode,
            duration_ms: duration,
            bytes: parseInt(res.getHeader('content-length') || '0', 10),
            msg: 'Request completed',
        };

        if (res.statusCode >= 500) {
            req.log.error(logEvent);
        } else if (res.statusCode >= 400) {
            req.log.warn(logEvent);
        } else {
            req.log.info(logEvent);
        }
    });

    next();
});

// ─── Routes ─────────────────────────────────────────────────────────────────

// Prometheus metrics endpoint
app.get('/metrics', async (req, res) => {
    res.setHeader('Content-Type', client.register.contentType);
    res.end(await client.register.metrics());
});

// Health endpoints
app.get('/healthz', (req, res) => res.json({ status: 'ok' }));

app.get('/readyz', async (req, res) => {
    try {
        await Promise.all([
            db.query('SELECT 1').timeout(2000),
            redis.ping().timeout(1000),
        ]);
        res.json({ status: 'ready', checks: { db: 'ok', redis: 'ok' } });
    } catch (err) {
        req.log.error({ err }, 'Readiness check failed');
        res.status(503).json({ status: 'not ready', error: err.message });
    }
});

// Business route
app.post('/v1/orders', async (req, res) => {
    try {
        const order = await orderService.create(req.body);
        
        req.log.info({
            order_id: order.id,
            user_id: order.userId,
            amount: order.amount,
            msg: 'Order created',
        });
        
        ordersCreatedTotal.inc({ status: 'success' });
        res.status(201).json(order);
    } catch (err) {
        req.log.error({ err, msg: 'Failed to create order' });
        ordersCreatedTotal.inc({ status: 'failed' });
        res.status(500).json({ error: 'Internal server error' });
    }
});

app.listen(8080, () => logger.info({ msg: 'Server started', port: 8080 }));
```

---

### Python + FastAPI

```python
# Dependencies: fastapi, uvicorn, structlog, prometheus-fastapi-instrumentator

import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator

# ─── Structlog Setup ────────────────────────────────────────────────────────

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,      # Merge context vars (request_id, etc.)
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),           # JSON output
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

configure_logging()
logger = structlog.get_logger()

# ─── Prometheus Metrics ──────────────────────────────────────────────────────

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'path'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5]
)

orders_created_total = Counter(
    'orders_created_total',
    'Total orders created',
    ['status']
)

# ─── Application ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server starting", service="order-service", version="1.4.2")
    yield
    logger.info("Server shutting down")

app = FastAPI(lifespan=lifespan)

# Auto-instrument with Prometheus (adds /metrics endpoint and request tracking)
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/healthz", "/readyz"],
)
instrumentator.instrument(app).expose(app)

# ─── Middleware ──────────────────────────────────────────────────────────────

@app.middleware("http")
async def request_context_middleware(request: Request, call_next: Callable) -> Response:
    """Add request_id to every log line via structlog context vars."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    
    # structlog context vars — automatically included in all log lines
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        service="order-service",
    )
    
    start = time.time()
    
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error("Unhandled exception", exc_info=exc)
        raise
    finally:
        duration = time.time() - start
        status = getattr(response, 'status_code', 500)
        
        log_fn = logger.info
        if status >= 500:
            log_fn = logger.error
        elif status >= 400:
            log_fn = logger.warning
            
        log_fn(
            "Request completed",
            status=status,
            duration_ms=round(duration * 1000, 2),
        )
        
        # Set correlation ID in response header
        response.headers["X-Request-ID"] = request_id
    
    return response

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/healthz")
async def liveness():
    return {"status": "ok"}

@app.get("/readyz")
async def readiness():
    checks = {}
    healthy = True
    
    try:
        await db.execute("SELECT 1")
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
        healthy = False
    
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        healthy = False
    
    status_code = 200 if healthy else 503
    return JSONResponse(
        content={"status": "ready" if healthy else "not ready", "checks": checks},
        status_code=status_code,
    )

@app.post("/v1/orders", status_code=201)
async def create_order(request: CreateOrderRequest):
    try:
        order = await order_service.create(request)
        
        logger.info(
            "Order created",
            order_id=order.id,
            user_id=order.user_id,
            amount=float(order.amount),
        )
        orders_created_total.labels(status="success").inc()
        return order
        
    except InsufficientFundsError as e:
        logger.warning("Order creation failed - insufficient funds", error=str(e))
        orders_created_total.labels(status="failed").inc()
        raise HTTPException(status_code=402, detail="Insufficient funds")
        
    except Exception as e:
        logger.error("Order creation failed", error=str(e))
        orders_created_total.labels(status="failed").inc()
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 15. Common Patterns & Best Practices

### 1. Log at Service Boundaries, Not Inside Every Function

```go
// Bad — log inside every function, duplicate/noisy
func getUser(id string) (*User, error) {
    log.Info("Getting user", "id", id)         // noise
    user, err := db.Query(...)
    log.Info("Got user from DB", "id", id)     // noise
    return user, err
}

// Good — log at the handler level with full context
func getUserHandler(w http.ResponseWriter, r *http.Request) {
    id := chi.URLParam(r, "id")
    user, err := userService.Get(r.Context(), id)
    if err != nil {
        log.Error("Failed to get user", "user_id", id, "error", err)
        // ...
    }
    log.Info("Request served", "user_id", id, "duration_ms", ...)
}
```

### 2. Use Buckets That Match Your SLO

```go
// If your SLO is p99 < 200ms, put buckets near 200ms
Buckets: []float64{0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0}
//                                              ^^^^ dense around SLO boundary
```

### 3. Metric Naming Conventions

```
# Follow Prometheus naming conventions:
<namespace>_<subsystem>_<name>_<unit>

# Examples:
http_requests_total           # counter — total suffix
http_request_duration_seconds # histogram — unit in name
process_open_fds              # gauge — no suffix needed
grpc_client_msg_received_total
db_query_duration_seconds
cache_hits_total
cache_misses_total
```

### 4. Always Expose Build Info Metric

```go
// Useful for tracking deployments in Grafana
buildInfo = promauto.NewGaugeVec(
    prometheus.GaugeOpts{Name: "build_info", Help: "Build information"},
    []string{"version", "commit", "build_date"},
)
buildInfo.WithLabelValues("1.4.2", "a1b2c3d", "2026-06-29").Set(1)
```

### 5. Error Logging — Include All Context

```go
// Bad — not enough context to debug
log.Error("DB query failed")

// Good — full context
log.Error().
    Err(err).
    Str("query_type", "get_user").
    Str("user_id", userID).
    Dur("duration", time.Since(start)).
    Int("retry_attempt", retryCount).
    Msg("Database query failed after retries")
```

---

## 16. Common Pitfalls

### Pitfall 1: Using fmt.Printf / console.log in Production

```go
// Bad — unstructured, not queryable, no context
fmt.Printf("Error processing order %s: %v\n", orderID, err)

// Good
log.Error().Err(err).Str("order_id", orderID).Msg("Error processing order")
```

### Pitfall 2: High Cardinality Labels

```go
// CATASTROPHIC — user_id has millions of distinct values
httpRequests.WithLabelValues(r.Method, userID, path, status).Inc()
// This will OOM your Prometheus instance

// Correct — low cardinality labels only
httpRequests.WithLabelValues(r.Method, routePattern, status).Inc()
```

### Pitfall 3: Not Normalizing URL Paths

```go
// Bad — each order creates a unique time series
// /orders/ord_a1b2c3, /orders/ord_x9y8z7 — thousands of unique paths

// Good — use route pattern from router
rctx := chi.RouteContext(r.Context())
path := rctx.RoutePattern() // Returns "/orders/{id}"
```

### Pitfall 4: Logging PII

```python
# Bad
logger.info("User logged in", email=user.email, password=password)

# Good
logger.info("User logged in", user_id=user.id)
```

### Pitfall 5: Histogram Buckets Too Wide

```go
// Bad — default Prometheus buckets (.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10)
// If all your requests take 50-100ms, everything lands in the same bucket
// histogram_quantile gives inaccurate results

// Good — custom buckets matching your service's actual latency profile
Buckets: prometheus.LinearBuckets(0.01, 0.01, 20) // 10ms, 20ms, ... 200ms
```

### Pitfall 6: Creating New Metric Objects per Request

```go
// WRONG — creates a new counter on every request, panics on duplicate registration
func handler(w http.ResponseWriter, r *http.Request) {
    counter := prometheus.NewCounter(prometheus.CounterOpts{Name: "requests"})
    counter.Inc()
}

// Correct — register once at package level
var requestsTotal = promauto.NewCounter(prometheus.CounterOpts{Name: "requests_total"})

func handler(w http.ResponseWriter, r *http.Request) {
    requestsTotal.Inc()
}
```

### Pitfall 7: Swallowing Errors Without Logging

```go
// Silent failure — you'll never know this happened
result, _ := db.Query(ctx, "SELECT ...")

// Correct
result, err := db.Query(ctx, "SELECT ...")
if err != nil {
    log.Error().Err(err).Msg("DB query failed")
    return fmt.Errorf("db query: %w", err)
}
```

---

## 17. Interview Questions

**Q1: What is the difference between logs, metrics, and traces?**

Logs are discrete event records capturing what happened at a specific point in time (structured JSON documents). Metrics are aggregated numerical measurements over time — counters, gauges, histograms — that show how the system behaves at macro scale. Traces represent a single request's journey through distributed services, showing parent-child span relationships and where time was spent. They are complementary: metrics tell you something is wrong, traces tell you where, and logs tell you exactly what happened.

**Q2: What are the RED metrics? What are the USE metrics?**

RED is for services: **Rate** (requests per second), **Errors** (error rate), **Duration** (latency percentiles). USE is for resources: **Utilization** (how busy), **Saturation** (queuing/backpressure), **Errors** (error events). Every service should have RED dashboards; every resource (CPU, memory, DB connections) should have USE dashboards.

**Q3: What is structured logging and why does it matter?**

Structured logging means emitting log lines as machine-parseable documents (JSON) with consistent field names and types, rather than unstructured printf-style text strings. It matters because: (1) log aggregation systems (ELK, Loki) can index and query individual fields — you can ask "all errors for user_id X in the last hour" instead of grepping free text; (2) fields have types — numbers stay numbers; (3) correlation IDs and context propagation are natural — fields, not embedded in strings.

**Q4: What is high cardinality in Prometheus metrics and why is it a problem?**

Cardinality is the number of unique time series created by metric labels. High cardinality means labels with many distinct values — like user_id, session_id, or IP addresses. A metric with a user_id label for a 10M user service would create 10M × (other label combinations) time series. Prometheus stores all active time series in memory. Hundreds of millions of series causes OOM (out of memory) crashes and makes Prometheus unusable. Solution: only use labels with bounded, small sets of values (HTTP method, status code, route pattern — not user/request IDs).

**Q5: How do you calculate p99 latency from a histogram?**

Use the `histogram_quantile` PromQL function: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))`. This applies linear interpolation within the bucket that contains the 99th percentile observation. Accuracy depends on bucket granularity — buckets should be densely packed around expected values. The histogram stores cumulative bucket counts (`_bucket`), total sum (`_sum`), and total count (`_count`).

**Q6: What should every request log include?**

Timestamp (ISO 8601, UTC), log level, message, service name, version, environment, request_id (for correlation), trace_id and span_id (for distributed tracing integration), HTTP method, normalized path, response status code, and duration in milliseconds. Optionally: user_id (opaque), relevant business entity IDs (order_id, etc.), error details for non-2xx responses.

**Q7: Why shouldn't you log PII?**

Compliance regulations: GDPR requires data minimization and the right to erasure — if PII is in logs, it's nearly impossible to delete; PCI-DSS prohibits card data in logs; HIPAA prohibits health information in logs. Logs are often stored long-term, replicated across systems, and accessible to engineers who shouldn't see user data. A data breach of logs is as serious as a database breach. Log opaque user IDs instead of emails/names/phone numbers.

---

## 18. Resources

- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/) — Official naming and metric design guide
- [Google SRE Book — Chapter 6: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) — Origin of RED/USE methods
- [zerolog Documentation](https://github.com/rs/zerolog) — Zero-allocation JSON logger for Go
- [pino Documentation](https://getpino.io/) — Fastest Node.js JSON logger
- [structlog Documentation](https://www.structlog.org/) — Structured logging for Python
- [Grafana Loki](https://grafana.com/oss/loki/) — Log aggregation system compatible with Prometheus
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/) — Standards for logs, metrics, traces
- [Brendan Gregg's USE Method](https://www.brendangregg.com/usemethod.html) — Original USE method article
- [Tom Wilkie's RED Method](https://www.weave.works/blog/the-red-method-key-metrics-for-microservices-architecture/) — Original RED method article

---

**Next:** [Part 13.2: Distributed Tracing, Health Checks & Alerting](./13-distributed-tracing-health.md)
