# Part 14.2: Rate Limiting, DDoS Protection & Secrets Management

## What You'll Learn

- The four rate limiting algorithms and their trade-offs (fixed window, sliding window, token bucket, leaky bucket)
- Why per-user rate limiting is better than per-IP
- How to implement distributed rate limiting with Redis
- Rate limit response headers and HTTP 429
- Secrets management from environment variables to HashiCorp Vault
- Security headers that every API should return
- mTLS for service-to-service authentication

---

## Table of Contents

1. [Rate Limiting Algorithms](#rate-limiting-algorithms)
2. [Distributed Rate Limiting with Redis](#distributed-rate-limiting-with-redis)
3. [Rate Limit Headers & HTTP 429](#rate-limit-headers--http-429)
4. [DDoS Protection](#ddos-protection)
5. [Secrets Management](#secrets-management)
6. [Security Headers](#security-headers)
7. [mTLS](#mtls)
8. [Implementation Examples](#implementation-examples)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Interview Questions](#interview-questions)
12. [Resources](#resources)

---

## Rate Limiting Algorithms

### Fixed Window

Count requests within a fixed time window (e.g., 1000 req/minute). Reset counter at window boundary.

```
Window: 12:00:00 → 12:01:00
  Request 1 at 12:00:58 → counter: 1
  Request 2 at 12:00:59 → counter: 2
  ...
  Request 1000 at 12:00:59.9 → counter: 1000 — limit hit
  Window resets at 12:01:00
  Request 1001 at 12:01:00 → counter: 1 — allowed!

Problem: burst at window boundary
  999 requests at 12:00:59 + 999 requests at 12:01:00.001
  → 1998 requests in ~2 seconds — 2x the intended rate
```

**Pros:** Simple, O(1) memory per key  
**Cons:** Burst at window boundary doubles allowed rate

### Sliding Window Log

Store timestamp of every request in a sorted set. Count requests within the rolling window.

```
Window: [now - 60s, now]
  On each request: count entries in window
  If count >= limit: reject
  Always add new request timestamp
```

**Pros:** Accurate — no boundary burst  
**Cons:** O(requests) memory — stores every timestamp; expensive for high-traffic keys

### Sliding Window Counter (Hybrid)

Approximate sliding window using two fixed window counters.

```
current_window_count + previous_window_count × (1 - elapsed_fraction_of_current_window)

At 12:00:45 (45s into 60s window):
  current_count = 300
  prev_count = 900
  elapsed_fraction = 45/60 = 0.75
  estimated_count = 300 + 900 × (1 - 0.75) = 300 + 225 = 525
```

**Pros:** O(1) memory, more accurate than fixed window  
**Cons:** Approximate (within ~0.1% error in practice)

### Token Bucket

A bucket holds tokens. Tokens are added at a fixed rate (refill rate). Each request consumes one token. Burst is allowed up to bucket capacity.

```
Bucket capacity: 100 tokens
Refill rate: 10 tokens/second
Initial: 100 tokens (full)

Request: consumes 1 token → 99 remaining
Burst: 100 requests in 1 second — all allowed (bucket empties)
Next request: must wait for token refill (~100ms for next token)
Steady state: 10 req/sec sustained

Key property: allows burst up to capacity, then enforces average rate
```

**Pros:** Allows bursts; smooth average rate; intuitive  
**Cons:** Two parameters (capacity + refill rate) to tune; slightly complex  
**Used by:** AWS API Gateway, Stripe, most production rate limiters

### Leaky Bucket

Requests enter a FIFO queue (the bucket) and are processed at a fixed outflow rate. If queue is full, new requests are dropped.

```
Queue capacity: 100 requests
Process rate: 10 req/second

High traffic: requests queue up → smooth outflow at 10/sec
If queue full: drop (HTTP 429) → excess traffic is shed

Key property: smooth output rate regardless of input burst
```

**Pros:** Smooth output rate — good for protecting downstream services  
**Cons:** Queuing adds latency; burstiness is absorbed but not served faster  
**Used by:** Traffic shaping at network level, API gateways enforcing smooth downstream load

### Comparison Table

| Algorithm | Memory | Burst | Accuracy | Complexity |
|---|---|---|---|---|
| Fixed Window | O(1) | Yes (boundary) | ~2x burst possible | Very simple |
| Sliding Window Log | O(n) per key | No | Exact | Complex |
| Sliding Window Counter | O(1) | Minimal | ~0.1% error | Medium |
| Token Bucket | O(1) | Yes (by design) | Exact | Medium |
| Leaky Bucket | O(queue size) | Absorbed (queued) | Exact | Medium |

---

## Distributed Rate Limiting with Redis

Single-server rate limiting (in-process) doesn't work when you have multiple instances. Redis provides a shared, atomic counter.

### Fixed Window with Redis INCR

```
Key: rate_limit:{user_id}:{window}
  where window = floor(timestamp / window_size_seconds)
```

```python
import redis
import time

def is_rate_limited(user_id: str, limit: int = 1000, window_seconds: int = 60) -> bool:
    r = redis.Redis()
    window = int(time.time()) // window_seconds
    key = f"rate_limit:{user_id}:{window}"

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds * 2)  # expire after 2 windows (cleanup)
    results = pipe.execute()

    count = results[0]
    return count > limit
```

### Token Bucket with Redis Lua Script

Using Lua for atomicity — INCR + EXPIRE is two commands and NOT atomic:

```lua
-- Token bucket Lua script
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])  -- tokens per second
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
  tokens = capacity
  last_refill = now
end

-- Refill tokens based on elapsed time
local elapsed = now - last_refill
local new_tokens = math.min(capacity, tokens + elapsed * refill_rate)

if new_tokens >= requested then
  -- Allow request
  redis.call('HSET', key, 'tokens', new_tokens - requested, 'last_refill', now)
  redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2)
  return 1  -- allowed
else
  redis.call('HSET', key, 'tokens', new_tokens, 'last_refill', now)
  return 0  -- denied
end
```

### Sliding Window with Sorted Set

```python
import redis
import time

def sliding_window_rate_limit(user_id: str, limit: int = 100, window_ms: int = 60_000) -> bool:
    r = redis.Redis()
    now_ms = int(time.time() * 1000)
    window_start = now_ms - window_ms
    key = f"rate_limit:sw:{user_id}"

    pipe = r.pipeline()
    # Remove old entries outside window
    pipe.zremrangebyscore(key, 0, window_start)
    # Count requests in window
    pipe.zcard(key)
    # Add current request
    pipe.zadd(key, {str(now_ms): now_ms})
    # Set expiry
    pipe.expire(key, window_ms // 1000 + 1)
    results = pipe.execute()

    count = results[1]
    return count >= limit  # True means rate limited
```

---

## Rate Limit Headers & HTTP 429

Every rate-limited API should return these headers on every response:

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 742
X-RateLimit-Reset: 1719660000    # Unix timestamp when limit resets
X-RateLimit-Window: 60           # Window size in seconds

# On 429:
HTTP/1.1 429 Too Many Requests
Retry-After: 30                  # Seconds until client can retry
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1719660000
Content-Type: application/problem+json

{
  "type": "https://api.example.com/errors/rate-limited",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "You have exceeded 1000 requests per minute.",
  "retry_after": 30
}
```

### Per-Endpoint Rate Limits

Different endpoints warrant different limits:
- `POST /auth/login` → 10 req/min (brute force protection)
- `POST /auth/register` → 5 req/min (account creation abuse)
- `GET /users/{id}` → 1000 req/min (normal read)
- `POST /payments` → 10 req/min (financial operations)
- `GET /search` → 100 req/min (search is expensive)

---

## DDoS Protection

### Layer 3/4 vs Layer 7 Attacks

- **L3/4 (Volumetric)**: flood with UDP/TCP packets, exhaust bandwidth/connections. Mitigated at network level (AWS Shield, Cloudflare Magic Transit).
- **L7 (Application)**: HTTP floods, slowloris (keep connections open), API abuse. Mitigated at application layer (rate limiting, WAF, bot detection).

### Defense Layers

```
Internet → Cloudflare/AWS Shield (L3/4) → WAF (L7) → Rate Limiter → Your API
```

1. **CDN/DDoS provider**: Cloudflare, AWS Shield Advanced — absorbs volumetric attacks before they reach your servers
2. **WAF (Web Application Firewall)**: block known attack patterns, geo-blocking, IP reputation lists
3. **Rate limiting**: per-IP, per-user, per-endpoint
4. **Connection limits**: nginx `limit_conn_zone`, Go `net/http` server `MaxHeaderBytes`
5. **Bot detection**: CAPTCHA, device fingerprinting, honeypot endpoints

### Nginx Rate Limiting

```nginx
http {
    # Define rate limit zone: 10MB shared memory, 10 req/sec per IP
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        location /api/ {
            # Allow burst of 20, nodelay = serve burst immediately (no queuing)
            limit_req zone=api burst=20 nodelay;
            limit_req_status 429;
            proxy_pass http://backend;
        }

        location /auth/ {
            limit_req zone=api burst=5 nodelay;
            limit_req_status 429;
            proxy_pass http://backend;
        }
    }
}
```

---

## Secrets Management

### The Hierarchy (Worst to Best)

```
❌ Hardcoded in code          → visible in git, logs, stack traces
❌ .env file committed to git → visible to anyone with repo access
⚠  .env file (gitignored)    → better, but manual rotation, visible on disk
✅ Environment variables      → not in code, but visible in process list
✅ AWS Secrets Manager/SSM    → encrypted, audited, rotation support
✅ HashiCorp Vault            → dynamic secrets, fine-grained access, leases
```

### Environment Variables (12-Factor App)

```bash
# .env (gitignored, local dev only)
DATABASE_URL=postgresql://user:pass@localhost/mydb
REDIS_URL=redis://localhost:6379
JWT_SECRET=my-dev-secret-change-in-prod
STRIPE_API_KEY=sk_test_...

# Production: set via platform (k8s Secret, ECS environment, Heroku config)
```

**Never commit `.env` files.** Always add to `.gitignore`. Use `.env.example` with placeholder values.

### Detecting Secrets in Code

```bash
# git-secrets — prevent committing secrets
git secrets --install
git secrets --register-aws

# truffleHog — scan git history for secrets
trufflehog git https://github.com/org/repo --only-verified

# GitHub Secret Scanning — automatic on push (GitHub Advanced Security)
```

### AWS Secrets Manager

```python
import boto3
import json
from functools import lru_cache

@lru_cache(maxsize=None)
def get_secret(secret_name: str) -> dict:
    client = boto3.client('secretsmanager', region_name='ap-south-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
secrets = get_secret("prod/myapp/db")
db_url = f"postgresql://{secrets['username']}:{secrets['password']}@{secrets['host']}/mydb"
```

### HashiCorp Vault — Dynamic Secrets

Vault generates short-lived credentials on demand. When the lease expires, credentials are revoked. No long-lived passwords.

```python
import hvac
import os

client = hvac.Client(
    url='https://vault.internal:8200',
    token=os.environ['VAULT_TOKEN']  # Vault AppRole or K8s auth
)

# Read a static secret
secret = client.secrets.kv.v2.read_secret_version(
    path='myapp/database',
    mount_point='secret'
)
db_password = secret['data']['data']['password']

# Dynamic DB credentials (Vault generates them, auto-revokes after TTL)
creds = client.secrets.database.generate_credentials(name='myapp-readonly')
username = creds['data']['username']  # auto-generated, valid for 1h
password = creds['data']['password']
```

### Secret Rotation

Applications must handle secret rotation without downtime:

1. **Dual credentials**: new and old credentials valid simultaneously during rotation window
2. **Reload on startup** vs **dynamic reload** (listen for rotation events)
3. **Lease renewal**: Vault leases with `renew_self` before expiry

```python
# ✅ CORRECT — reload DB pool on secret rotation signal
import signal

def reload_db_pool(signum, frame):
    new_secrets = get_secret("prod/myapp/db")  # fetches latest
    app.state.db_pool = create_new_pool(new_secrets)

signal.signal(signal.SIGUSR1, reload_db_pool)
```

---

## Security Headers

Every API response should include these headers:

```
# Force HTTPS for 1 year, include subdomains
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

# Prevent MIME type sniffing
X-Content-Type-Options: nosniff

# Prevent clickjacking
X-Frame-Options: DENY

# Limit referrer information
Referrer-Policy: strict-origin-when-cross-origin

# Control browser features
Permissions-Policy: camera=(), microphone=(), geolocation=()

# Content Security Policy (for APIs returning HTML; for JSON APIs less critical)
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
```

---

## mTLS

Mutual TLS (mTLS) means both client and server present certificates. Used for service-to-service authentication in microservices.

```
Normal TLS:
  Client          Server
    ──── ClientHello ────>
    <─── ServerHello + Server Certificate ────
    ──── validates server cert ────
    [encrypted channel established]

mTLS:
  Client          Server
    ──── ClientHello ────>
    <─── ServerHello + Server Certificate ────
    ──── Client Certificate ────>
    <─── validates client cert ────
    [both authenticated, encrypted channel established]
```

In Kubernetes, Istio/Linkerd service mesh handles mTLS automatically — every sidecar proxy presents a certificate issued by the mesh's internal CA. No application code changes needed.

---

## Implementation Examples

### Go + Chi Router

```go
package main

import (
    "context"
    "fmt"
    "net/http"
    "sync"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/redis/go-redis/v9"
)

// Token bucket rate limiter using Redis
type RateLimiter struct {
    rdb      *redis.Client
    capacity int64
    refillPs int64 // tokens per second
}

func NewRateLimiter(rdb *redis.Client, capacity, refillPerSecond int64) *RateLimiter {
    return &RateLimiter{rdb: rdb, capacity: capacity, refillPs: refillPerSecond}
}

var tokenBucketScript = redis.NewScript(`
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

local elapsed = now - last_refill
local new_tokens = math.min(capacity, tokens + elapsed * refill_rate)

if new_tokens >= 1 then
    redis.call('HSET', key, 'tokens', new_tokens - 1, 'last_refill', now)
    redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2)
    return {1, math.floor(new_tokens - 1)}
else
    redis.call('HSET', key, 'tokens', new_tokens, 'last_refill', now)
    return {0, 0}
end
`)

func (rl *RateLimiter) Allow(ctx context.Context, key string) (bool, int64, error) {
    now := float64(time.Now().UnixMilli()) / 1000.0
    result, err := tokenBucketScript.Run(ctx, rl.rdb,
        []string{fmt.Sprintf("rate:%s", key)},
        rl.capacity, rl.refillPs, now,
    ).Int64Slice()
    if err != nil {
        return true, 0, err // fail open on Redis errors
    }
    return result[0] == 1, result[1], nil
}

// Middleware
func RateLimitMiddleware(limiter *RateLimiter) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            // Prefer user ID from context over IP
            userID := getUserID(r.Context())
            key := userID
            if key == "" {
                key = "ip:" + r.RemoteAddr
            }

            allowed, remaining, err := limiter.Allow(r.Context(), key)
            if err != nil {
                // Fail open — don't block legitimate users on Redis failure
                next.ServeHTTP(w, r)
                return
            }

            w.Header().Set("X-RateLimit-Limit", fmt.Sprintf("%d", limiter.capacity))
            w.Header().Set("X-RateLimit-Remaining", fmt.Sprintf("%d", remaining))

            if !allowed {
                w.Header().Set("Retry-After", "10")
                w.Header().Set("Content-Type", "application/problem+json")
                w.WriteHeader(http.StatusTooManyRequests)
                w.Write([]byte(`{"type":"rate_limited","title":"Too Many Requests","status":429}`))
                return
            }

            next.ServeHTTP(w, r)
        })
    }
}

// Security headers middleware
func SecurityHeaders(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        w.Header().Set("X-Content-Type-Options", "nosniff")
        w.Header().Set("X-Frame-Options", "DENY")
        w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
        w.Header().Set("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        next.ServeHTTP(w, r)
    })
}

func main() {
    rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
    limiter := NewRateLimiter(rdb, 100, 10) // 100 capacity, 10/sec refill

    r := chi.NewRouter()
    r.Use(SecurityHeaders)
    r.Use(RateLimitMiddleware(limiter))

    // Stricter limit for auth endpoints
    r.Group(func(r chi.Router) {
        authLimiter := NewRateLimiter(rdb, 10, 1) // 10 capacity, 1/sec
        r.Use(RateLimitMiddleware(authLimiter))
        r.Post("/auth/login", loginHandler)
    })

    http.ListenAndServe(":8080", r)
}
```

### Node.js + Express

```javascript
const express = require('express');
const { createClient } = require('redis');

const redisClient = createClient({ url: 'redis://localhost:6379' });
await redisClient.connect();

// Fixed window rate limiter
async function rateLimitMiddleware(limit = 100, windowSeconds = 60) {
  return async (req, res, next) => {
    const identifier = req.user?.id || req.ip;
    const window = Math.floor(Date.now() / 1000 / windowSeconds);
    const key = `rate:${identifier}:${window}`;

    const count = await redisClient.incr(key);
    if (count === 1) {
      await redisClient.expire(key, windowSeconds * 2);
    }

    const remaining = Math.max(0, limit - count);
    res.setHeader('X-RateLimit-Limit', limit);
    res.setHeader('X-RateLimit-Remaining', remaining);
    res.setHeader('X-RateLimit-Reset', (Math.floor(Date.now() / 1000 / windowSeconds) + 1) * windowSeconds);

    if (count > limit) {
      return res.status(429).json({
        type: 'rate_limited',
        title: 'Too Many Requests',
        status: 429,
        detail: `Rate limit of ${limit} requests per ${windowSeconds}s exceeded`,
        retry_after: windowSeconds - (Math.floor(Date.now() / 1000) % windowSeconds),
      });
    }
    next();
  };
}

// Security headers middleware
function securityHeaders(req, res, next) {
  res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  next();
}

const app = express();
app.use(securityHeaders);
app.use(await rateLimitMiddleware(1000, 60));

// Stricter for auth
app.use('/auth', await rateLimitMiddleware(10, 60));
```

### Python + FastAPI

```python
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
import time

app = FastAPI()
redis: Redis = None

@app.on_event("startup")
async def startup():
    global redis
    redis = Redis.from_url("redis://localhost:6379", decode_responses=True)

class RateLimiter:
    def __init__(self, redis: Redis, limit: int = 100, window: int = 60):
        self.redis = redis
        self.limit = limit
        self.window = window

    async def is_allowed(self, identifier: str) -> tuple[bool, int]:
        now = int(time.time())
        window_key = now // self.window
        key = f"rate:{identifier}:{window_key}"

        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window * 2)
        results = await pipe.execute()
        count = results[0]

        remaining = max(0, self.limit - count)
        return count <= self.limit, remaining

def rate_limit(limit: int = 100, window: int = 60):
    limiter = RateLimiter(redis, limit=limit, window=window)

    async def dependency(request: Request, response: Response):
        # Prefer authenticated user ID over IP
        identifier = getattr(request.state, "user_id", None) or request.client.host
        allowed, remaining = await limiter.is_allowed(identifier)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        reset = (int(time.time()) // window + 1) * window
        response.headers["X-RateLimit-Reset"] = str(reset)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "rate_limited",
                    "title": "Too Many Requests",
                    "status": 429,
                    "retry_after": reset - int(time.time()),
                }
            )
    return dependency

# Security headers middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# Reading secrets from environment (pydantic-settings)
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str
    stripe_api_key: str
    debug: bool = False

    model_config = {"env_file": ".env"}

settings = Settings()  # fails fast if required vars missing

# Usage with rate limiting dependency
from fastapi import Depends

@app.get("/users/{id}", dependencies=[Depends(rate_limit(limit=1000, window=60))])
async def get_user(id: int):
    return {"id": id}

@app.post("/auth/login", dependencies=[Depends(rate_limit(limit=10, window=60))])
async def login(body: dict):
    return {"token": "..."}
```

---

## Common Patterns & Best Practices

### Pattern 1: Fail Open on Rate Limiter Errors

If Redis is down, don't block all traffic. Log the error and allow the request through.

```go
allowed, remaining, err := limiter.Allow(ctx, key)
if err != nil {
    log.Warn("Rate limiter unavailable, failing open", "error", err)
    next.ServeHTTP(w, r) // allow through
    return
}
```

### Pattern 2: Per-Endpoint Granularity

Don't apply a single global rate limit. Auth endpoints need tighter limits than read endpoints.

```
/auth/login         → 5 req/min (brute force protection)
/auth/register      → 3 req/min
/auth/otp/verify    → 3 req/5min
/api/users          → 1000 req/min
/api/search         → 100 req/min (expensive)
/api/payments       → 10 req/min (financial)
```

### Pattern 3: Rate Limit per User, Fall Back to IP

```python
identifier = request.state.user_id if hasattr(request.state, "user_id") else request.client.host
```

Per-user is better: shared NAT means thousands of users have the same IP. Per-IP would rate-limit an entire office.

---

## Common Pitfalls

- ❌ WRONG: Rate limiting per IP in production — corporate NATs share IPs, blocks entire offices
- ✅ CORRECT: Rate limit per authenticated user ID; IP as fallback for unauthenticated endpoints

- ❌ WRONG: Using `INCR` + `EXPIRE` as two separate commands — not atomic, race condition on first request
- ✅ CORRECT: Use pipeline, Lua script, or Redis `SET key 0 NX EX window` pattern

- ❌ WRONG: Storing secrets in environment variables as the final answer — fine for dev, not for production
- ✅ CORRECT: AWS Secrets Manager, GCP Secret Manager, or HashiCorp Vault in production

- ❌ WRONG: Returning 403 for rate-limited requests
- ✅ CORRECT: HTTP 429 Too Many Requests with `Retry-After` header

- ❌ WRONG: Logging secrets in error messages, debug logs, or structured log fields
- ✅ CORRECT: Redact sensitive fields (`password`, `token`, `secret`) before logging

- ❌ WRONG: Committing `.env` files to git
- ✅ CORRECT: `.gitignore` the `.env` file, commit `.env.example` with dummy values

---

## Interview Questions

**Q1. What is the difference between a token bucket and a leaky bucket rate limiter?**

**Answer:** A token bucket allows bursts — requests consume tokens from the bucket, which refills at a fixed rate. If the bucket is full (say 100 tokens), a client can send 100 requests instantly, then is limited to the refill rate. This allows legitimate bursts. A leaky bucket queues requests and processes them at a fixed outflow rate. It smooths traffic — a sudden burst goes into the queue and drains at the steady rate. If the queue is full, new requests are dropped. Use token bucket when you want to allow bursts. Use leaky bucket when protecting a downstream service from burst load.

---

**Q2. Why is rate limiting per user better than per IP address?**

**Answer:** IP-based rate limiting breaks in environments with shared IPs: corporate offices, universities, mobile carrier NATs — hundreds or thousands of users can share a single public IP. Rate limiting that IP would block all of them when one misbehaves. Per-user rate limiting (using authenticated user ID) is fair and accurate. Use IP-based rate limiting only for unauthenticated endpoints (login, register) where no user identity is available yet.

---

**Q3. What happens at the window boundary in a fixed window rate limiter?**

**Answer:** A burst attack is possible. If the limit is 1000 req/min and a window runs from 12:00:00–12:01:00, an attacker can send 999 requests at 12:00:59 (within limit) and 999 more at 12:01:00 (new window starts). This delivers 1998 requests in ~2 seconds — double the intended rate. The sliding window counter algorithm fixes this by using a weighted blend of the current and previous window counts.

---

**Q4. How do you manage secrets in a production environment?**

**Answer:** Never hardcode secrets or commit `.env` files. For simple cloud deployments, use the platform's secrets store (AWS Secrets Manager, GCP Secret Manager, Kubernetes Secrets). For enterprise, use HashiCorp Vault which supports dynamic secrets (generates short-lived DB credentials on demand, auto-revokes them), audit logging, and fine-grained access policies. Applications should validate all required secrets at startup (fail fast if missing) and support rotation without downtime by using dual-credential rotation periods.

---

**Q5. What HTTP response code should a rate-limited request return?**

**Answer:** HTTP 429 Too Many Requests. Always include a `Retry-After` header (seconds until the client can retry) and `X-RateLimit-Remaining: 0`. Return the response as `application/problem+json` (RFC 7807) with a human-readable message explaining the limit. Never use 403 (that's for authorization failures) or 503 (that's for service unavailability).

---

**Q6. What is mTLS and when would you use it?**

**Answer:** Mutual TLS (mTLS) means both the client and server authenticate each other with X.509 certificates during the TLS handshake — unlike normal TLS where only the server presents a certificate. It's used for service-to-service authentication in microservices to ensure that Service A can only be called by authorised services (not random internal traffic or external attackers who've breached the network). In Kubernetes, service meshes like Istio and Linkerd handle mTLS transparently — injecting sidecar proxies that present certificates issued by the mesh's internal certificate authority. Application code needs no changes.

---

## Resources

- [OWASP API Security — Rate Limiting](https://owasp.org/www-project-api-security/)
- [Cloudflare — Rate Limiting](https://www.cloudflare.com/learning/bots/what-is-rate-limiting/)
- [Redis — Rate Limiting Patterns](https://redis.io/learn/develop/java/spring/rate-limiting/fixed-window)
- [HashiCorp Vault Documentation](https://developer.hashicorp.com/vault/docs)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [MDN — HTTP Security Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers#security)
- [HSTS Preload List](https://hstspreload.org/)
- [Mozilla Observatory — Test your headers](https://observatory.mozilla.org/)

---

**Next:** [Part 15.1: Microservices Architecture](../part-15/15-microservices-architecture.md)
