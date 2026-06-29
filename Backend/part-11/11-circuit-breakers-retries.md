# Part 11.2: Circuit Breakers, Retries, Timeouts & Bulkhead

## What You'll Learn
- How to build resilient service-to-service communication
- Retry strategies that don't amplify failures
- Circuit breaker state machine — how it protects downstream services
- Timeout hierarchies and how cascading timeouts kill systems
- Bulkhead isolation — containing failures to one subsystem
- Fallback strategies and graceful degradation
- Implementations in Go, Node.js, and Python

## Table of Contents
1. [Why Resilience Patterns Matter](#1-why-resilience-patterns-matter)
2. [Retry Pattern](#2-retry-pattern)
3. [Circuit Breaker Pattern](#3-circuit-breaker-pattern)
4. [Timeout Pattern](#4-timeout-pattern)
5. [Bulkhead Pattern](#5-bulkhead-pattern)
6. [Fallback Patterns](#6-fallback-patterns)
7. [Implementation Examples](#7-implementation-examples)
8. [Common Patterns & Best Practices](#8-common-patterns--best-practices)
9. [Common Pitfalls](#9-common-pitfalls)
10. [Interview Questions & Answers](#10-interview-questions--answers)
11. [Resources](#11-resources)

---

## 1. Why Resilience Patterns Matter

In a distributed system, failure is not an exception — it is a certainty. Any network call can fail. Any service can become slow. A database can have a momentary spike. Without explicit resilience patterns, one slow dependency can cascade into a system-wide outage.

```
Without resilience:

  Client ──► API Gateway ──► Order Service ──► Payment Service (slow)
                                   │
                                   └── All Order Service threads waiting on Payment
                                       Order Service becomes slow
                                       API Gateway threads waiting on Order Service
                                       API Gateway becomes slow
                                       All clients timing out
                                       TOTAL OUTAGE
```

```
With circuit breaker + bulkhead:

  Client ──► API Gateway ──► Order Service ──► Payment Service (slow)
                                   │
                                   ├── Circuit breaker OPENS after threshold
                                   ├── Requests to Payment fail fast (2ms instead of 30s)
                                   ├── Thread pool for Payment Service is isolated
                                   └── Order Service remains healthy for other operations
```

The four patterns work together:
- **Retry** — handle transient failures automatically
- **Circuit Breaker** — stop calling a failing service to let it recover
- **Timeout** — bound the time any operation can consume
- **Bulkhead** — isolate failure domains so one dependency can't starve all others

---

## 2. Retry Pattern

### When to Retry

Not all failures are worth retrying. Retrying the wrong errors wastes resources and delays the inevitable failure response.

```
RETRY these:
  - 429 Too Many Requests (with Retry-After header)
  - 500 Internal Server Error (server might be momentarily unhealthy)
  - 502 Bad Gateway
  - 503 Service Unavailable
  - 504 Gateway Timeout
  - Network timeout (ETIMEDOUT, ECONNRESET)
  - Connection refused (service restarting)

DO NOT RETRY these:
  - 400 Bad Request (the request is broken — retrying won't fix it)
  - 401 Unauthorized (token is invalid — retrying won't fix it)
  - 403 Forbidden (permission issue — retrying won't fix it)
  - 404 Not Found (resource doesn't exist — retrying won't fix it)
  - 409 Conflict (business logic conflict)
  - Non-idempotent operations: POST /orders (might create duplicates)
```

**Idempotency is a prerequisite for retrying mutations.** A `POST /orders` without an idempotency key must not be retried. A `PUT /orders/{id}` is idempotent — retrying it is safe.

### Exponential Backoff

Linear backoff (retry every 1 second) is not enough — all clients retry in lockstep, creating thundering herd. Exponential backoff spaces retries further apart each attempt:

```
Attempt 1: wait 100ms
Attempt 2: wait 200ms
Attempt 3: wait 400ms
Attempt 4: wait 800ms
Attempt 5: wait 1600ms (or maxDelay, whichever is smaller)
```

Formula: `delay = min(baseDelay × 2^(attempt-1), maxDelay)`

```
attempt | base=100ms | maxDelay=10s
   1    |    100ms   |    100ms
   2    |    200ms   |    200ms
   3    |    400ms   |    400ms
   4    |    800ms   |    800ms
   5    |   1600ms   |   1600ms
   6    |   3200ms   |   3200ms
   7    |   6400ms   |   6400ms
   8    |  12800ms   |  10000ms  ← capped at maxDelay
```

### Jitter — Preventing Thundering Herd

Without jitter, 1000 clients all hit a recovered service at the same time after backing off the same amount. The thundering herd re-kills the service.

**Full Jitter:** `delay = random(0, baseDelay × 2^attempt)`
- Spreads retries randomly across the window
- Easiest to implement
- Maximum spread

**Decorrelated Jitter (AWS recommendation):**
```
sleep = min(cap, random(base, previous_sleep × 3))
```
- Each client's delays are decorrelated from each other
- Better distribution across time

**Equal Jitter:** `delay = cap/2 + random(0, cap/2)`
- Guarantees minimum delay (no zero-delay retries)

```
100 clients retrying at T=0, without jitter:

T=100ms:  ████████████████████████████████████████ 100 clients hit
T=200ms:  ████████████████████████████████████████ 100 clients hit

With full jitter:

T=0-100ms:  ████████████ 30 clients
T=100-200ms: ██████████ 25 clients
T=200-300ms: █████████ 22 clients
T=300-400ms: ████████ 23 clients
```

### Retry Budget

A retry budget limits the fraction of total requests that can be retries:

```
Total requests to Payment Service: 1000/sec
Retry budget: 10%
Max retries allowed: 100/sec

Without retry budget: during an outage, 1000 original requests × 3 retries = 3000 requests/sec hammering a recovering service

With retry budget: at most 1100 requests/sec (1000 original + 100 retries)
```

---

## 3. Circuit Breaker Pattern

### State Machine

```
              failures > threshold
   Closed ──────────────────────────► Open
     ▲                                  │
     │                                  │ after timeout (e.g., 30s)
     │                                  ▼
     │    probe succeeds           Half-Open
     └────────────────────────────── (1 probe allowed)
                                        │
                                        │ probe fails
                                        └──────────────► Open (reset timer)
```

### Closed State (Normal Operation)

- All requests flow through to the dependency
- Tracks a rolling window of failures (e.g., last 10 requests, or last 30 seconds)
- When failures exceed threshold, transitions to Open

**Threshold examples:**
- "5 consecutive failures"
- "50% failure rate in the last 20 requests"
- "10 failures in the last 60 seconds"

### Open State (Stop Calling)

- All requests **fail immediately** without calling the dependency
- This is "fail fast" — response time goes from 30s (timeout) to 2ms (immediate rejection)
- The service gets a recovery window — no traffic during this period
- Caller receives a circuit-open error and can fall back to cache/default

```
Open circuit prevents:
  - Cascading failures (your service stays healthy)
  - Resource exhaustion (no threads blocked waiting)
  - Amplifying load on a struggling dependency
```

### Half-Open State (Probing)

- After the open timeout, allows **one test request** through
- If the probe succeeds → transition to Closed, resume normal traffic
- If the probe fails → transition back to Open, reset the timer

**Why not allow all traffic immediately after timeout?** The service might have recovered just enough to handle one request but not a flood.

### Circuit Breaker Configuration

```
Parameters to tune:
  failureThreshold:  How many failures to open (e.g., 5)
  successThreshold:  How many successes to close from half-open (e.g., 2)
  timeout:           How long to stay open before probing (e.g., 30s)
  volumeThreshold:   Min requests before percentage-based threshold applies (e.g., 10)
  windowSize:        Rolling window for counting failures (e.g., last 60s)
```

### What to Count as a Failure

```
Count as failures:
  - HTTP 5xx responses
  - Network timeouts
  - Connection refused

Do NOT count as failures:
  - HTTP 4xx responses (client errors — the downstream service is working)
  - Successful slow responses (unless you also want latency-based opening)
```

---

## 4. Timeout Pattern

### Why You Must Always Set Timeouts

Without a timeout, a single slow dependency can hold threads indefinitely:

```
Thread pool: 100 threads
Request to slow DB: no timeout

After 10 seconds of slow requests:
  100 threads blocked waiting on DB
  New requests queue up
  Queue fills up
  New requests rejected with 503
  Service appears down
  DB was just slow — now you've amplified the failure
```

With a 500ms timeout: requests fail fast, threads are freed, service stays healthy (at the cost of returning errors for some requests — which is correct behavior).

### Timeout Types

```
DNS Timeout:        Time to resolve hostname → typically 2-5s
Connection Timeout: Time to establish TCP connection → typically 1-3s
Write Timeout:      Time to send the request → typically 5-30s
Read Timeout:       Time to receive the first byte of response → typically 5-30s
Idle Timeout:       Time between bytes in a streaming response
Total/Request Timeout: End-to-end time from request start to response end

Note: Read timeout ≠ Total timeout.
A read timeout of 30s means "30s between bytes", not "30s total".
A slow service can send one byte every 29s and never trigger the read timeout.
Always set a total/request timeout in addition to read timeout.
```

### Cascading Timeout Failures

```
Client timeout: 30s
  └── Service A timeout: 25s
        └── Service B timeout: 20s
              └── Database timeout: 15s

If DB is slow (takes 16s):
  DB returns at 16s (to service B)
  Service B timeout at 20s — DB response discarded
  Service A timeout at 25s — service B response discarded
  Client timeout at 30s — wasted

Better: set each layer's timeout shorter than its parent:
  Client:    30s
  Service A: 20s  (≤ client timeout - propagation time)
  Service B: 10s  (≤ Service A timeout - propagation time)
  DB:         5s  (≤ Service B timeout - propagation time)
```

### Context-Based Timeouts in Go

Go propagates deadlines via `context.Context`. Every function that does I/O should accept and respect a `ctx`:

```go
// Create a context with 5-second deadline
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel() // ALWAYS defer cancel to release resources

// The context deadline propagates through the entire call chain
result, err := serviceB.Call(ctx, request)
if err != nil {
    if errors.Is(err, context.DeadlineExceeded) {
        // This specific operation timed out
    }
    if errors.Is(err, context.Canceled) {
        // Parent context was cancelled (e.g., client disconnected)
    }
}
```

**Critical rule:** `defer cancel()` must always be called, even if the context completes before the timeout. Failing to call `cancel` leaks the context goroutine.

---

## 5. Bulkhead Pattern

The term comes from ship design: bulkheads are watertight compartments that prevent one breach from sinking the whole ship.

```
Without bulkhead:
  ┌─────────────────────────────────────────┐
  │           Thread Pool (100 threads)     │
  │  Payment  Payment  Payment  Payment ... │ ← All threads waiting on slow Payment
  │  UserSvc  UserSvc  UserSvc             │ ← No threads left for UserSvc
  └─────────────────────────────────────────┘

With bulkhead:
  ┌────────────────────┐  ┌────────────────────┐
  │  Payment Pool (30) │  │  UserSvc Pool (30) │
  │  Payment  Payment  │  │  User   User       │
  │  Payment  Payment  │  │  User   User       │
  └────────────────────┘  └────────────────────┘
  Payment can only use 30 threads — UserSvc is always available
```

### Thread Pool Bulkhead

Separate thread pools per external dependency. If Payment Service hangs, only the Payment thread pool is exhausted. UserService, NotificationService, etc. are unaffected.

In Go, goroutines are cheap, but you still need to limit concurrency to downstream services using semaphores or worker pools.

### Semaphore Bulkhead

Limit the number of concurrent in-flight requests to a dependency:

```go
type Bulkhead struct {
    sem chan struct{}
}

func NewBulkhead(maxConcurrent int) *Bulkhead {
    return &Bulkhead{sem: make(chan struct{}, maxConcurrent)}
}

func (b *Bulkhead) Execute(ctx context.Context, fn func() error) error {
    // Try to acquire semaphore
    select {
    case b.sem <- struct{}{}:
        // Acquired
    case <-ctx.Done():
        return fmt.Errorf("bulkhead: context cancelled waiting for slot: %w", ctx.Err())
    default:
        // Non-blocking: if full, fail immediately
        return ErrBulkheadFull
    }

    defer func() { <-b.sem }() // Release on return

    return fn()
}
```

### Connection Pool Isolation

Different dependencies should use different connection pools:

```go
// BAD: all services share one HTTP client
var sharedClient = &http.Client{Timeout: 30 * time.Second}

// GOOD: each dependency has its own client with appropriate limits
var (
    paymentClient = &http.Client{
        Timeout: 5 * time.Second,
        Transport: &http.Transport{
            MaxIdleConns:        10,
            MaxConnsPerHost:     10,
            IdleConnTimeout:     90 * time.Second,
        },
    }
    notificationClient = &http.Client{
        Timeout: 2 * time.Second,
        Transport: &http.Transport{
            MaxIdleConns:        5,
            MaxConnsPerHost:     5,
        },
    }
)
```

---

## 6. Fallback Patterns

When a circuit is open or a retry budget is exhausted, you need a fallback strategy.

### Cached Response Fallback

Return the last known good value from cache:

```
User requests product details.
Product Service circuit is open.
Fallback: return cached product details from Redis (may be stale by N minutes).
Better than a 503.
```

### Default Value Fallback

Return a safe default when the real value isn't available:

```
Recommendation Service is down.
Fallback: return top-10 trending products (static, always available).
```

### Partial Data / Graceful Degradation

Return what you can, omit what you can't:

```json
{
  "user": {
    "id": "abc123",
    "name": "Alice",
    "email": "alice@example.com",
    "recommendations": null,  ← recommendation service was down
    "recentOrders": [...]      ← order service was healthy
  }
}
```

### Fail Fast vs Fail Safe

**Fail Fast:** Reject the request immediately when the circuit is open. Return an error to the client quickly. The client can retry later or show an error UI. Best for write operations.

**Fail Safe:** Return a default/cached response even when the circuit is open. The client gets a degraded but functional response. Best for read operations where stale data is acceptable.

---

## 7. Implementation Examples

### Go + Chi Router

**Retry with Exponential Backoff + Jitter:**

```go
// resilience/retry.go
package resilience

import (
    "context"
    "errors"
    "math"
    "math/rand"
    "net/http"
    "time"
)

type RetryConfig struct {
    MaxAttempts int
    BaseDelay   time.Duration
    MaxDelay    time.Duration
    Multiplier  float64
}

var DefaultRetryConfig = RetryConfig{
    MaxAttempts: 3,
    BaseDelay:   100 * time.Millisecond,
    MaxDelay:    10 * time.Second,
    Multiplier:  2.0,
}

// IsRetryable returns true for errors worth retrying
func IsRetryable(err error) bool {
    var httpErr *HTTPError
    if errors.As(err, &httpErr) {
        switch httpErr.StatusCode {
        case http.StatusTooManyRequests,
            http.StatusInternalServerError,
            http.StatusBadGateway,
            http.StatusServiceUnavailable,
            http.StatusGatewayTimeout:
            return true
        }
        return false
    }
    // Network errors are retryable
    return true
}

type HTTPError struct {
    StatusCode int
    Body       string
}

func (e *HTTPError) Error() string {
    return fmt.Sprintf("HTTP %d: %s", e.StatusCode, e.Body)
}

// Retry executes fn with exponential backoff + full jitter
func Retry(ctx context.Context, cfg RetryConfig, fn func(ctx context.Context) error) error {
    var lastErr error
    for attempt := 0; attempt < cfg.MaxAttempts; attempt++ {
        if attempt > 0 {
            delay := calculateDelay(cfg, attempt)
            select {
            case <-time.After(delay):
            case <-ctx.Done():
                return fmt.Errorf("retry cancelled: %w", ctx.Err())
            }
        }

        lastErr = fn(ctx)
        if lastErr == nil {
            return nil
        }

        if !IsRetryable(lastErr) {
            return lastErr // don't retry non-retryable errors
        }
    }
    return fmt.Errorf("all %d attempts failed, last error: %w", cfg.MaxAttempts, lastErr)
}

func calculateDelay(cfg RetryConfig, attempt int) time.Duration {
    // Exponential backoff: base × multiplier^(attempt-1)
    backoff := float64(cfg.BaseDelay) * math.Pow(cfg.Multiplier, float64(attempt-1))
    // Cap at maxDelay
    if backoff > float64(cfg.MaxDelay) {
        backoff = float64(cfg.MaxDelay)
    }
    // Full jitter: random value in [0, backoff]
    jitter := rand.Float64() * backoff
    return time.Duration(jitter)
}
```

**Circuit Breaker:**

```go
// resilience/circuit_breaker.go
package resilience

import (
    "context"
    "errors"
    "sync"
    "time"
)

type State int

const (
    StateClosed   State = iota // Normal operation
    StateOpen                  // Rejecting requests
    StateHalfOpen              // Probing
)

func (s State) String() string {
    switch s {
    case StateClosed:
        return "closed"
    case StateOpen:
        return "open"
    case StateHalfOpen:
        return "half-open"
    }
    return "unknown"
}

var ErrCircuitOpen = errors.New("circuit breaker is open")

type CircuitBreaker struct {
    mu               sync.Mutex
    state            State
    failures         int
    successes        int
    lastFailureTime  time.Time
    failureThreshold int
    successThreshold int
    openTimeout      time.Duration
    name             string
}

func NewCircuitBreaker(name string, failureThreshold, successThreshold int, openTimeout time.Duration) *CircuitBreaker {
    return &CircuitBreaker{
        name:             name,
        state:            StateClosed,
        failureThreshold: failureThreshold,
        successThreshold: successThreshold,
        openTimeout:      openTimeout,
    }
}

func (cb *CircuitBreaker) Execute(ctx context.Context, fn func(ctx context.Context) error) error {
    if err := cb.allow(); err != nil {
        return err
    }

    err := fn(ctx)
    cb.record(err)
    return err
}

func (cb *CircuitBreaker) allow() error {
    cb.mu.Lock()
    defer cb.mu.Unlock()

    switch cb.state {
    case StateClosed:
        return nil
    case StateOpen:
        if time.Since(cb.lastFailureTime) > cb.openTimeout {
            cb.state = StateHalfOpen
            cb.successes = 0
            return nil // allow one probe request
        }
        return fmt.Errorf("%w: %s", ErrCircuitOpen, cb.name)
    case StateHalfOpen:
        return nil // allow probe request
    }
    return nil
}

func (cb *CircuitBreaker) record(err error) {
    cb.mu.Lock()
    defer cb.mu.Unlock()

    if err != nil {
        cb.failures++
        cb.successes = 0
        cb.lastFailureTime = time.Now()

        switch cb.state {
        case StateClosed:
            if cb.failures >= cb.failureThreshold {
                cb.state = StateOpen
            }
        case StateHalfOpen:
            cb.state = StateOpen // probe failed — reopen
        }
    } else {
        cb.failures = 0
        switch cb.state {
        case StateHalfOpen:
            cb.successes++
            if cb.successes >= cb.successThreshold {
                cb.state = StateClosed
            }
        case StateClosed:
            // no state change
        }
    }
}

func (cb *CircuitBreaker) State() State {
    cb.mu.Lock()
    defer cb.mu.Unlock()
    return cb.state
}
```

**Semaphore Bulkhead:**

```go
// resilience/bulkhead.go
package resilience

import (
    "context"
    "errors"
)

var ErrBulkheadFull = errors.New("bulkhead: max concurrent calls reached")

type Bulkhead struct {
    name string
    sem  chan struct{}
}

func NewBulkhead(name string, maxConcurrent int) *Bulkhead {
    return &Bulkhead{
        name: name,
        sem:  make(chan struct{}, maxConcurrent),
    }
}

// Execute runs fn if a slot is available; otherwise fails fast
func (b *Bulkhead) Execute(ctx context.Context, fn func() error) error {
    select {
    case b.sem <- struct{}{}:
        defer func() { <-b.sem }()
        return fn()
    case <-ctx.Done():
        return fmt.Errorf("bulkhead %s: context cancelled: %w", b.name, ctx.Err())
    default:
        return fmt.Errorf("bulkhead %s: %w", b.name, ErrBulkheadFull)
    }
}

// ExecuteWithWait runs fn, waiting up to ctx deadline for a slot
func (b *Bulkhead) ExecuteWithWait(ctx context.Context, fn func() error) error {
    select {
    case b.sem <- struct{}{}:
        defer func() { <-b.sem }()
        return fn()
    case <-ctx.Done():
        return fmt.Errorf("bulkhead %s: timed out waiting for slot: %w", b.name, ctx.Err())
    }
}
```

**Usage in a service:**

```go
// services/payment_client.go
type PaymentClient struct {
    cb       *resilience.CircuitBreaker
    bulkhead *resilience.Bulkhead
    client   *http.Client
    baseURL  string
}

func NewPaymentClient(baseURL string) *PaymentClient {
    return &PaymentClient{
        cb:       resilience.NewCircuitBreaker("payment", 5, 2, 30*time.Second),
        bulkhead: resilience.NewBulkhead("payment", 20),
        client: &http.Client{
            Timeout: 5 * time.Second,
        },
        baseURL: baseURL,
    }
}

func (c *PaymentClient) Charge(ctx context.Context, req ChargeRequest) (*ChargeResponse, error) {
    var resp *ChargeResponse

    err := c.bulkhead.Execute(ctx, func() error {
        return c.cb.Execute(ctx, func(ctx context.Context) error {
            return resilience.Retry(ctx, resilience.DefaultRetryConfig, func(ctx context.Context) error {
                var err error
                resp, err = c.doCharge(ctx, req)
                return err
            })
        })
    })

    if err != nil {
        if errors.Is(err, resilience.ErrCircuitOpen) {
            // Fallback: return cached last-known status or fail gracefully
            return nil, fmt.Errorf("payment service unavailable: %w", err)
        }
        if errors.Is(err, resilience.ErrBulkheadFull) {
            return nil, fmt.Errorf("payment service overloaded: %w", err)
        }
        return nil, fmt.Errorf("charge failed: %w", err)
    }

    return resp, nil
}
```

**Context Timeout in Handler:**

```go
func (h *OrderHandler) CreateOrder(w http.ResponseWriter, r *http.Request) {
    // Bound the entire operation to 10 seconds
    ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
    defer cancel()

    order, err := h.svc.Create(ctx, req)
    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) {
            middleware.WriteError(w, r, appErrors.New(504, "GATEWAY_TIMEOUT", "request timed out"))
            return
        }
        middleware.WriteError(w, r, err)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(order)
}
```

---

### Node.js + Express

**Retry with Exponential Backoff + Jitter:**

```javascript
// resilience/retry.js
const RETRYABLE_STATUS_CODES = new Set([429, 500, 502, 503, 504]);

class RetryError extends Error {
    constructor(message, lastError, attempts) {
        super(message);
        this.name = 'RetryError';
        this.lastError = lastError;
        this.attempts = attempts;
    }
}

async function withRetry(fn, options = {}) {
    const {
        maxAttempts = 3,
        baseDelayMs = 100,
        maxDelayMs = 10000,
        multiplier = 2,
        isRetryable = defaultIsRetryable,
    } = options;

    let lastError;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        if (attempt > 0) {
            const delay = calculateDelay(attempt, baseDelayMs, maxDelayMs, multiplier);
            await sleep(delay);
        }

        try {
            return await fn(attempt);
        } catch (err) {
            lastError = err;
            if (!isRetryable(err)) {
                throw err; // don't retry non-retryable errors
            }
        }
    }

    throw new RetryError(
        `All ${maxAttempts} attempts failed`,
        lastError,
        maxAttempts
    );
}

function defaultIsRetryable(err) {
    if (err.statusCode && RETRYABLE_STATUS_CODES.has(err.statusCode)) return true;
    if (err.code === 'ETIMEDOUT' || err.code === 'ECONNRESET') return true;
    return false;
}

function calculateDelay(attempt, baseDelay, maxDelay, multiplier) {
    const exponential = baseDelay * Math.pow(multiplier, attempt - 1);
    const capped = Math.min(exponential, maxDelay);
    // Full jitter
    return Math.random() * capped;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

module.exports = { withRetry, RetryError };
```

**Circuit Breaker (using opossum):**

```javascript
// resilience/circuitBreaker.js
const CircuitBreaker = require('opossum');
const logger = require('../logger');

const DEFAULT_OPTIONS = {
    timeout: 5000,           // 5s — if fn doesn't complete in 5s, count as failure
    errorThresholdPercentage: 50,  // open when 50% of requests fail
    resetTimeout: 30000,     // 30s before attempting to close
    volumeThreshold: 5,      // min 5 requests before threshold applies
};

function createCircuitBreaker(name, fn, options = {}) {
    const breaker = new CircuitBreaker(fn, {
        ...DEFAULT_OPTIONS,
        ...options,
        name,
    });

    breaker.on('open', () => {
        logger.warn({ circuit: name }, 'Circuit breaker OPENED');
    });

    breaker.on('halfOpen', () => {
        logger.info({ circuit: name }, 'Circuit breaker HALF-OPEN — probing');
    });

    breaker.on('close', () => {
        logger.info({ circuit: name }, 'Circuit breaker CLOSED — recovered');
    });

    breaker.on('fallback', (result) => {
        logger.info({ circuit: name, result }, 'Circuit breaker fallback triggered');
    });

    return breaker;
}

module.exports = { createCircuitBreaker };
```

```javascript
// services/paymentClient.js
const axios = require('axios');
const { createCircuitBreaker } = require('../resilience/circuitBreaker');
const { withRetry } = require('../resilience/retry');

class PaymentClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
        this.axiosInstance = axios.create({
            baseURL,
            timeout: 5000,
        });

        // Wrap the actual call in a circuit breaker
        this._chargeBreaker = createCircuitBreaker(
            'payment-charge',
            this._doCharge.bind(this),
            { timeout: 5000, errorThresholdPercentage: 40 }
        );

        // Fallback: return an error indicating payment is temporarily unavailable
        this._chargeBreaker.fallback(() => {
            throw new ServiceUnavailableError('Payment service is temporarily unavailable');
        });

        // Semaphore: limit to 20 concurrent requests
        this._maxConcurrent = 20;
        this._inFlight = 0;
    }

    async charge(request) {
        if (this._inFlight >= this._maxConcurrent) {
            throw new Error('Payment service bulkhead full');
        }

        this._inFlight++;
        try {
            return await withRetry(
                (attempt) => {
                    if (attempt > 0) {
                        logger.debug({ attempt }, 'Retrying payment charge');
                    }
                    return this._chargeBreaker.fire(request);
                },
                { maxAttempts: 3, baseDelayMs: 200 }
            );
        } finally {
            this._inFlight--;
        }
    }

    async _doCharge(request) {
        const response = await this.axiosInstance.post('/charge', request);
        return response.data;
    }
}

module.exports = PaymentClient;
```

**Context Timeout (AbortController):**

```javascript
// utils/withTimeout.js
async function withTimeout(promise, timeoutMs, errorMessage = 'Operation timed out') {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        return await promise;
    } catch (err) {
        if (err.name === 'AbortError') {
            throw new TimeoutError(errorMessage);
        }
        throw err;
    } finally {
        clearTimeout(timeoutId);
    }
}

// Express handler usage:
app.post('/orders', asyncHandler(async (req, res) => {
    const result = await withTimeout(
        orderService.create(req.body),
        10000,
        'Order creation timed out'
    );
    res.status(201).json(result);
}));
```

---

### Python + FastAPI

**Retry with Exponential Backoff + Jitter (using tenacity):**

```python
# resilience/retry.py
import asyncio
import logging
import random
from functools import wraps
from typing import Callable, Iterable, Type

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
    before_sleep_log,
    RetryError,
)

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class RetryableHTTPError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def is_retryable_exception(exc: BaseException) -> bool:
    if isinstance(exc, RetryableHTTPError):
        return exc.status_code in RETRYABLE_STATUS_CODES
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    return False


# Tenacity-based retry decorator
def with_retry(max_attempts: int = 3, base_delay: float = 0.1, max_delay: float = 10.0):
    """Decorator: retry async function with exponential backoff + jitter."""
    def decorator(fn):
        @retry(
            retry=retry_if_exception_type((RetryableHTTPError, httpx.TimeoutException, httpx.ConnectError)),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential_jitter(initial=base_delay, max=max_delay, jitter=base_delay),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            return await fn(*args, **kwargs)
        return wrapper
    return decorator
```

**Circuit Breaker:**

```python
# resilience/circuit_breaker.py
import asyncio
import enum
import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    def __init__(self, name: str):
        super().__init__(f"Circuit breaker '{name}' is open")
        self.name = name


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        open_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.open_timeout = open_timeout

        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def execute(self, fn: Callable, *args, **kwargs):
        async with self._lock:
            if not await self._allow():
                raise CircuitOpenError(self.name)

        try:
            result = await fn(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as exc:
            await self._on_failure()
            raise

    async def _allow(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            if time.monotonic() - (self._last_failure_time or 0) > self.open_timeout:
                self._state = CircuitState.HALF_OPEN
                self._successes = 0
                logger.info("Circuit breaker '%s' → HALF_OPEN", self.name)
                return True
            return False
        # HALF_OPEN — allow one probe
        return True

    async def _on_success(self):
        async with self._lock:
            self._failures = 0
            if self._state == CircuitState.HALF_OPEN:
                self._successes += 1
                if self._successes >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    logger.info("Circuit breaker '%s' → CLOSED", self.name)

    async def _on_failure(self):
        async with self._lock:
            self._failures += 1
            self._last_failure_time = time.monotonic()
            if self._state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self._failures >= self.failure_threshold or self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.OPEN
                    logger.warning("Circuit breaker '%s' → OPEN", self.name)
```

**Semaphore Bulkhead:**

```python
# resilience/bulkhead.py
import asyncio
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class BulkheadFullError(Exception):
    def __init__(self, name: str):
        super().__init__(f"Bulkhead '{name}' is full")
        self.name = name


class Bulkhead:
    """Limits concurrent calls to a dependency."""

    def __init__(self, name: str, max_concurrent: int):
        self.name = name
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent

    async def execute(self, fn: Callable, *args, **kwargs):
        """Execute fn if capacity is available; otherwise fail fast."""
        acquired = self._semaphore._value > 0  # Non-blocking check
        if not acquired:
            raise BulkheadFullError(self.name)

        async with self._semaphore:
            return await fn(*args, **kwargs)

    async def execute_with_wait(self, fn: Callable, timeout: float, *args, **kwargs):
        """Execute fn, waiting up to timeout seconds for a slot."""
        try:
            async with asyncio.timeout(timeout):
                async with self._semaphore:
                    return await fn(*args, **kwargs)
        except asyncio.TimeoutError:
            raise BulkheadFullError(f"{self.name} (timed out waiting for slot)")
```

**Combined usage in a FastAPI service:**

```python
# services/payment_client.py
import httpx
import asyncio
from resilience.circuit_breaker import CircuitBreaker, CircuitOpenError
from resilience.bulkhead import Bulkhead, BulkheadFullError
from resilience.retry import with_retry, RetryableHTTPError
from errors.exceptions import AppError

class PaymentClient:
    def __init__(self, base_url: str):
        self._base_url = base_url
        self._client = httpx.AsyncClient(base_url=base_url, timeout=5.0)
        self._circuit_breaker = CircuitBreaker("payment", failure_threshold=5, open_timeout=30.0)
        self._bulkhead = Bulkhead("payment", max_concurrent=20)

    @with_retry(max_attempts=3, base_delay=0.2)
    async def _do_charge(self, request: dict) -> dict:
        response = await self._client.post("/charge", json=request)
        if response.status_code in {500, 502, 503, 504}:
            raise RetryableHTTPError(response.status_code, f"Payment returned {response.status_code}")
        response.raise_for_status()
        return response.json()

    async def charge(self, request: dict) -> dict:
        try:
            return await self._bulkhead.execute(
                self._circuit_breaker.execute,
                self._do_charge,
                request,
            )
        except CircuitOpenError:
            raise AppError("Payment service temporarily unavailable", status_code=503, code="SERVICE_UNAVAILABLE")
        except BulkheadFullError:
            raise AppError("Too many concurrent payment requests", status_code=503, code="OVERLOADED")

    async def close(self):
        await self._client.aclose()
```

**FastAPI route with timeout:**

```python
# routers/orders.py
import asyncio
from fastapi import APIRouter
from errors.exceptions import AppError

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/")
async def create_order(request: CreateOrderRequest, svc: OrderService = Depends(get_order_service)):
    try:
        async with asyncio.timeout(10.0):  # 10s total timeout (Python 3.11+)
            order = await svc.create(request)
            return {"data": order}
    except asyncio.TimeoutError:
        raise AppError("Order creation timed out", status_code=504, code="GATEWAY_TIMEOUT")
```

---

## 8. Common Patterns & Best Practices

### Pattern 1: Compose All Four Patterns

The correct order for outgoing requests:

```
Request → Bulkhead → Circuit Breaker → Timeout → Retry → Actual Call
```

- **Bulkhead first** — don't even start the operation if we're at capacity
- **Circuit Breaker second** — don't start if the service is known-bad
- **Timeout on each attempt** — bound individual call time
- **Retry around the whole thing** — retry if attempt failed and retryable

### Pattern 2: Per-Dependency Configuration

Different dependencies have different SLAs and failure characteristics:

```go
var (
    // Payment: critical, strict limits, no fallback
    paymentCB = NewCircuitBreaker("payment", 3, 2, 60*time.Second)
    paymentBH = NewBulkhead("payment", 10)

    // Recommendation: non-critical, permissive, fallback to popular items
    recoCB = NewCircuitBreaker("recommendation", 10, 3, 10*time.Second)
    recoBH = NewBulkhead("recommendation", 50)
)
```

### Pattern 3: Metrics on Every Pattern

Every circuit breaker state change, every retry attempt, every bulkhead rejection should emit a metric:

```go
// Increment on circuit open
metrics.Increment("circuit_breaker.opened", map[string]string{"service": name})

// Histogram for retry attempts
metrics.Observe("retry.attempts", float64(attempt), map[string]string{"service": name})

// Counter for bulkhead rejections
metrics.Increment("bulkhead.rejected", map[string]string{"service": name})
```

These metrics let you know:
- Which downstream services are flapping
- How often retries are happening (high retries → dependency is struggling)
- Which bulkheads are near capacity

### Pattern 4: Idempotency Keys for Safe Retries

```go
// Generate idempotency key from stable inputs
idempotencyKey := fmt.Sprintf("order-%s-%d", userID, items.Hash())

// Include in request header
req.Header.Set("Idempotency-Key", idempotencyKey)

// Retry safely — server deduplicates based on key
resp, err = httpClient.Do(req)
```

---

## 9. Common Pitfalls

### Pitfall 1: Retrying Non-Idempotent Operations

```javascript
// BAD — retrying POST /charges might double-charge the customer
await withRetry(() => axios.post('/charges', { amount: 100 }));

// GOOD — use idempotency key so server deduplicates
await withRetry(() => axios.post('/charges', { amount: 100 }, {
    headers: { 'Idempotency-Key': idempotencyKey }
}));
```

### Pitfall 2: Circuit Breaker Counting 4xx as Failures

A 404 means the resource doesn't exist — the service is healthy. Counting 404 as a circuit-opening failure will incorrectly open the circuit when many users look up non-existent resources.

```go
func isCircuitFailure(err error) bool {
    var httpErr *HTTPError
    if errors.As(err, &httpErr) {
        return httpErr.StatusCode >= 500 // only 5xx opens circuit
    }
    return true // network errors always count
}
```

### Pitfall 3: Not Cancelling Context After Timeout

```go
// BAD — context never cancelled, goroutine leaks
ctx, _ := context.WithTimeout(r.Context(), 5*time.Second)
result, err := service.Call(ctx, req)

// GOOD — always defer cancel
ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
defer cancel()
result, err := service.Call(ctx, req)
```

### Pitfall 4: Retry Budget Ignored — Amplifying Load During Outage

During an outage of Service B:
- 1000 requests/sec arrive at Service A
- Each fails and gets retried 3 times
- Service B receives 4000 requests/sec during recovery
- Service B can't recover under 4× load

Solution: Implement retry budgets or use circuit breakers to stop retrying entirely when failure rate is high.

### Pitfall 5: Bulkhead Too Small or Too Large

Too small: legitimate traffic gets rejected  
Too large: might as well not have a bulkhead

Start with: `bulkhead_size = avg_concurrent_requests × 1.5`  
Monitor bulkhead rejections — if you see zero rejections, the bulkhead may be too large to isolate failures.

### Pitfall 6: Using the Same Thread Pool for All Dependencies

In Python with synchronous code, all blocking calls share the same thread pool (via `asyncio.to_thread` or `run_in_executor`). Without explicit limits, a slow dependency can exhaust the thread pool.

```python
# BAD — unlimited concurrency to payment service
async def charge(request):
    return await asyncio.to_thread(blocking_payment_call, request)

# GOOD — semaphore limits concurrent calls
_payment_semaphore = asyncio.Semaphore(20)

async def charge(request):
    async with _payment_semaphore:
        return await asyncio.to_thread(blocking_payment_call, request)
```

---

## 10. Interview Questions & Answers

### Q1: Explain the circuit breaker pattern and its three states.

**Answer:** The circuit breaker pattern prevents a service from repeatedly calling a failing dependency, allowing the dependency time to recover.

**Three states:**
- **Closed** — normal operation. Requests flow through. Failures are counted in a rolling window. When failures exceed the threshold (e.g., 5 in 30 seconds), transition to Open.
- **Open** — all requests fail immediately without calling the dependency. The caller receives an error immediately (fail fast — 2ms instead of 30s timeout). After a configurable timeout (e.g., 30 seconds), transition to Half-Open.
- **Half-Open** — one probe request is allowed through. If it succeeds, transition to Closed (normal operation). If it fails, transition back to Open and restart the timeout.

**Why it matters:** Without circuit breakers, a slow downstream service causes thread exhaustion in the calling service, which cascades to its callers, eventually causing a total system outage. The circuit breaker bounds the blast radius to requests that depend on the failing service.

---

### Q2: What is exponential backoff with jitter and why is jitter important?

**Answer:** 

**Exponential backoff** means doubling the wait time between retry attempts: 100ms, 200ms, 400ms, 800ms... This prevents hammering a recovering service with immediate retries.

**The thundering herd problem:** If 1000 clients all experience a failure at T=0, and all use the same exponential backoff without jitter, they all retry at T=100ms, then T=200ms, etc. The retries arrive in synchronized waves, which can re-kill a service that just recovered.

**Jitter** adds randomness to the delay: `delay = random(0, exponential_backoff)`. This spreads retries uniformly across the backoff window, smoothing the load on the recovering service.

**AWS's decorrelated jitter** is even better: each client's delay is based on its own previous delay rather than the attempt number, ensuring delays are completely decorrelated across clients.

---

### Q3: When should you NOT retry a failed request?

**Answer:** Do not retry when:

1. **4xx errors** — These indicate the request is wrong (bad input, unauthorized, not found). The request itself must change before a retry can succeed. Retrying won't help.
2. **Non-idempotent operations** — POST requests that create resources (e.g., `POST /charges`) must not be retried without idempotency keys, as they could create duplicate resources (double-charge a customer).
3. **When retry budget is exhausted** — If the system is under high retry load, additional retries amplify the problem.
4. **When circuit is open** — The circuit breaker already determined the service is unhealthy. Retrying attempts against an open circuit should fail immediately.
5. **When context is cancelled** — If the client disconnected or the parent timeout expired, there's no point retrying.

---

### Q4: What is the bulkhead pattern?

**Answer:** The bulkhead pattern isolates resources (thread pools, connection pools, semaphores) per dependency so that a failure in one dependency cannot exhaust resources needed by other dependencies.

**Analogy:** A ship has watertight bulkheads — if one compartment floods, it doesn't sink the ship. Similarly, if the Payment Service becomes slow and exhausts its allocated thread pool, the User Service and Recommendation Service still have their own pools and remain healthy.

**Implementation options:**
- **Thread pool bulkhead** — separate thread pools per dependency (Java/Hystrix style)
- **Semaphore bulkhead** — limit concurrent in-flight calls using a semaphore (works well with async code)
- **Connection pool isolation** — separate HTTP client/DB pool per external service

---

### Q5: What is the difference between a request timeout and a read timeout?

**Answer:**

- **Connection timeout** — time allowed to establish the TCP connection (3-way handshake). If the server isn't reachable, this fires quickly.
- **Read timeout** — time allowed between consecutive bytes of the response. If the server sends one byte every 29 seconds and your read timeout is 30s, it will never fire even if the response takes hours.
- **Request/total timeout** — end-to-end time from when the request was sent to when the full response is received. This is the one you almost always want to set.
- **Write timeout** — time allowed to write the request body to the connection.

**In practice:** Always set a total/request timeout. The read timeout alone does not protect against a slow-responding server that keeps the connection alive.

**Go example:**
```go
client := &http.Client{
    Timeout: 5 * time.Second, // This is the total/request timeout — use this
}
// For granular control, configure Transport:
transport := &http.Transport{
    DialContext:           (&net.Dialer{Timeout: 3 * time.Second}).DialContext,
    ResponseHeaderTimeout: 5 * time.Second,
    IdleConnTimeout:       90 * time.Second,
}
```

---

### Q6: What does "fail fast" mean in the context of resilience?

**Answer:** Fail fast means detecting a failure condition and returning an error immediately, without waiting for the full timeout duration.

**Why it matters:** If Service A has a 30-second timeout when calling Service B, and Service B is down:
- Without fail fast: every request to Service A blocks for 30 seconds, consuming threads. 100 threads × 30s = 3000 thread-seconds wasted before giving up.
- With fail fast (circuit breaker open): every request to Service A fails in 2ms. Threads are freed immediately. Service A remains healthy for other operations.

**Implementations:**
- Circuit breaker in Open state → fail fast (don't call the dependency at all)
- Bulkhead full → fail fast (don't queue, reject immediately)
- Context already cancelled → fail fast (don't start the operation)

The trade-off is correctness: some requests fail that might have succeeded. The benefit is system stability.

---

## 11. Resources

- [AWS Architecture Blog: Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Martin Fowler: Circuit Breaker](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Release It! (book) — Michael Nygard — coined bulkhead pattern](https://pragprog.com/titles/mnee2/release-it-second-edition/)
- [go-resilience (Go circuit breaker)](https://github.com/eapache/go-resilience)
- [opossum (Node.js circuit breaker)](https://github.com/nodeshift/opossum)
- [tenacity (Python retry library)](https://github.com/jd/tenacity)
- [Google SRE Book: Handling Overload](https://sre.google/sre-book/handling-overload/)
- [Netflix Hystrix — the original Java bulkhead/circuit breaker](https://github.com/Netflix/Hystrix/wiki/How-it-Works)

---

**Next:** [Part 12.1: Testing Backend Services](../part-12/12-testing-backend-services.md)
