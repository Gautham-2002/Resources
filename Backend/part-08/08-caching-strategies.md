# Part 8.1: Caching Strategies

## What You'll Learn
- Why caching exists: the physics of memory hierarchy and latency gaps
- The four fundamental caching strategies and when to use each
- TTL selection trade-offs by data type
- Cache invalidation — the hardest problem in distributed systems
- Cache failure modes: stampede, penetration, avalanche — and how to prevent them
- Multi-level caching architectures
- Production implementations in Go+Chi, Node.js+Express, Python+FastAPI

---

## Table of Contents
1. [Why Cache? The Physics](#1-why-cache-the-physics)
2. [Cache Strategies](#2-cache-strategies)
   - Cache-Aside (Lazy Loading)
   - Write-Through
   - Write-Behind (Write-Back)
   - Refresh-Ahead (Read-Ahead)
3. [TTL Selection](#3-ttl-selection)
4. [Cache Invalidation](#4-cache-invalidation)
5. [Cache Failure Modes](#5-cache-failure-modes)
   - Cache Stampede / Thundering Herd
   - Cache Penetration
   - Cache Avalanche
6. [Multi-Level Caching](#6-multi-level-caching)
7. [Implementation Examples](#7-implementation-examples)
   - Go + Chi
   - Node.js + Express
   - Python + FastAPI
8. [Common Patterns & Best Practices](#8-common-patterns--best-practices)
9. [Common Pitfalls](#9-common-pitfalls)
10. [Interview Questions & Model Answers](#10-interview-questions--model-answers)
11. [Resources](#11-resources)

---

## 1. Why Cache? The Physics

Caching exists because different storage systems have orders-of-magnitude latency differences. Understanding these numbers is essential for designing systems and explaining caching decisions in interviews.

### The Memory Hierarchy

| Storage Level | Typical Latency | Notes |
|---|---|---|
| CPU L1 Cache | ~1 ns | ~4KB per core, hardwired |
| CPU L2 Cache | ~4 ns | ~256KB per core |
| CPU L3 Cache | ~10 ns | Shared across cores, 4-64MB |
| Main Memory (RAM) | ~100 ns | DRAM, GBs of capacity |
| NVMe SSD (local) | ~100 μs (0.1ms) | Sequential read optimized |
| SATA SSD | ~250 μs (0.25ms) | More common, slower |
| Same-DC Network round-trip | ~0.5-1 ms | TCP+application overhead |
| Redis (local/same-DC) | ~0.5-2 ms | Network + in-memory lookup |
| PostgreSQL (indexed query) | ~1-10 ms | Query planning + disk I/O |
| HDD seek | ~10 ms | Mechanical, random I/O |
| Cross-region network | ~100-300 ms | Speed of light across continent |
| Human perception threshold | ~100 ms | Below this feels "instant" |

**Key insight:** A single cache hit in Redis (1ms) that avoids a PostgreSQL query (10ms) is a 10× latency improvement. At scale, if you have 10,000 RPS and each request triggers 3 DB queries, that's 30,000 DB queries/sec. If 80% of those queries are cache-able, you reduce DB load to 6,000 queries/sec — making the difference between a $50/mo database and a $500/mo database.

### What Caching Actually Does

Caching is about **moving data closer to where it's consumed**:
- An in-process LRU cache (in-memory in your Go/Node/Python app) is ~100ns — no network, no disk
- A Redis cluster in the same datacenter is ~1ms — fast, shared across app instances
- PostgreSQL with warm buffer cache is ~5-10ms for indexed queries
- PostgreSQL with cold disk is ~50-100ms for queries requiring physical I/O

**When NOT to cache:**
- Data that changes on every read (live stock prices updating 1000×/sec)
- Highly personalized data with a unique key per user per request — cache won't be hit
- Very small tables that fit in PostgreSQL's shared_buffers anyway
- Security-sensitive data where returning stale data causes business harm

---

## 2. Cache Strategies

### Cache-Aside (Lazy Loading)

The application is responsible for all cache interactions. The cache is purely a performance layer — the database remains the source of truth.

**Read flow:**
1. Application checks cache for key
2. **Cache HIT:** Return cached value (fast path)
3. **Cache MISS:** Fetch from database, store in cache with TTL, return value

**Write flow:**
1. Application writes to database
2. Application **invalidates** (deletes) the cache key for that item
3. Next read will miss the cache and reload from DB

```
Read:                    Write:
App → Cache (HIT?)       App → DB (write)
        ↓ MISS           App → Cache (DELETE key)
App → DB (read)
App → Cache (SET with TTL)
App → Return data
```

**Pros:**
- **Only caches what's requested** — no wasted memory on cold data
- **Resilient to cache failure** — if Redis is down, requests just go to DB (degraded performance, not downtime)
- **Tolerates cold start** — cache fills up organically as requests arrive
- Most flexible — different TTLs per key type

**Cons:**
- **Cache miss penalty** — first request (and requests after TTL expiry) pay full DB latency
- **Data freshness window** — between a write and a cache invalidation (or TTL expiry), the cache may serve stale data (if invalidation fails or is delayed)
- **Thundering herd risk** — if many requests miss the cache for the same key simultaneously (see §5)

**Best for:** Most read-heavy workloads. The de facto standard caching strategy. Start here.

---

### Write-Through

Every write to the database is accompanied by a synchronous write to the cache.

**Write flow:**
1. Application writes to cache (SET key)
2. Application writes to database
3. Both succeed — data is consistent
4. Reads always hit the cache

**Pros:**
- **Always fresh:** Cache is never stale — it's updated on every write
- **No cold-start problem:** Data is in cache before it's ever read
- **Simple reads:** No miss/refill logic needed on reads

**Cons:**
- **Write latency doubles** — every write now requires two round-trips (cache + DB) or at minimum the latency of the slower of the two
- **Caches data that may never be read** — if you write 1000 records and only read 50, you've stored 950 records in cache memory unnecessarily
- **Consistency edge cases** — if the DB write succeeds but the cache write fails (or vice versa), you have an inconsistency. Requires careful error handling.
- **Cache size pressure** — entire working set is in cache, not just hot data

**Best for:** Low write-volume workloads where data is almost always read back after writes. Configuration data, user preferences, small reference tables.

---

### Write-Behind (Write-Back)

The application writes to cache only. The cache asynchronously flushes data to the database in the background.

**Write flow:**
1. Application writes to cache only (fast return to client)
2. Cache marks the key as "dirty"
3. Background worker asynchronously flushes dirty keys to DB (batched or on a timer)

**Read flow:** Same as cache-aside/write-through — reads come from cache.

**Pros:**
- **Extremely fast writes** — write latency is just a cache write (~1ms) — no DB involvement on the hot path
- **Write coalescing** — multiple rapid writes to the same key can be merged into one DB write
- **DB write batching** — bulk inserts to DB are more efficient than individual writes

**Cons:**
- **Data loss risk** — if the cache crashes before flushing, all dirty writes are lost
- **Complexity** — requires a reliable "dirty queue", failure handling, and replay logic
- **Consistency** — DB is not the source of truth until the flush occurs; direct DB queries return stale data
- **Two-phase failure** — crash during flush can leave DB in partially-written state

**Best for:** Very write-heavy, loss-tolerant workloads. Analytics event ingestion (losing 5 seconds of events is acceptable). Gaming leaderboard scores. Shopping cart (can tolerate losing in-progress cart items).

**NOT for:** Financial transactions, order creation, inventory updates — these require durable DB writes.

---

### Refresh-Ahead (Read-Ahead)

The cache proactively refreshes data before its TTL expires, based on predicted access patterns.

**Flow:**
1. Item is loaded into cache with TTL = 60 seconds
2. At 80% of TTL (48 seconds), a background task **proactively fetches fresh data** from DB and updates the cache
3. Reads never see a cache miss for hot data — cache always has fresh data ready

**Variants:**
- **Fixed-schedule refresh:** A background job periodically refreshes known hot keys (e.g., homepage featured products, top-10 leaderboard)
- **Threshold-based refresh:** As in the above — when TTL drops below X%, trigger async refresh

**Pros:**
- **No miss penalty for hot data** — proactive refresh ensures cache is always populated
- **Consistent read latency** — eliminates the cold-start penalty entirely for predicted-hot keys

**Cons:**
- **May refresh data that's no longer hot** — wastes resources refreshing keys that aren't being accessed
- **Requires prediction** — must know which keys are hot in advance
- **Complex to implement correctly** — background job scheduling, failure handling, avoiding refresh storms

**Best for:** Known-hot static-ish data. Homepage featured products, global configuration, app-wide settings, top charts/leaderboards. Pairs well with cache-aside for the general case.

---

## 3. TTL Selection

Choosing TTL is a trade-off between **data freshness** and **cache hit rate**.

**Short TTL:**
- More cache misses → more DB load
- Fresher data → fewer stale reads
- Higher infrastructure cost (more DB queries)

**Long TTL:**
- Fewer cache misses → less DB load
- Staler data → risk of serving outdated information
- More memory needed (keys stay in cache longer)

### TTL by Data Type

| Data Type | Recommended TTL | Reasoning |
|---|---|---|
| User profile (name, email, avatar) | 5-15 minutes | Changes infrequently, stale profile is minor UX issue |
| Product catalog (name, description) | 1-4 hours | Updated manually, high read volume |
| Product pricing | 5-15 minutes | Pricing changes are important, can't be too stale |
| Exchange rates / currency | 30-60 seconds | Market-driven, frequent small changes |
| Sports scores (live) | 5-15 seconds | Live data, latency matters |
| News feed / content list | 1-5 minutes | Freshness expected but not critical |
| Authentication token validity | Match token TTL | Must match exact expiry |
| User permissions / roles | 1-5 minutes | Security-sensitive, don't cache too long |
| Static reference data (countries, categories) | 1-24 hours | Almost never changes |
| Shopping cart | Session-scoped (30min inactivity) | Per-user, write-through or just use DB |
| Analytics aggregates | 5-60 minutes | Approximate is acceptable |
| Search results | 1-5 minutes | Query-dependent freshness |

### Sliding vs Fixed TTL

**Fixed TTL:** The key expires exactly N seconds after it was SET, regardless of whether it was accessed.
```
SET key value EX 300    # expires in 5 minutes from now
```

**Sliding TTL:** The key's expiration is reset every time it's accessed. As long as the key is accessed at least once every N seconds, it never expires.
Redis does not natively support sliding TTL — you simulate it by calling `EXPIRE key N` on every read:
```
GET key
EXPIRE key 300    # reset TTL to 5 minutes from now
```

**When to use sliding TTL:** Sessions (a user actively using the app shouldn't get logged out mid-session), recently-viewed items, per-user caches.

**When to use fixed TTL:** Product catalogs, reference data, anything where absolute freshness matters more than access-based retention.

---

## 4. Cache Invalidation

> "There are only two hard things in Computer Science: cache invalidation and naming things." — Phil Karlton

Cache invalidation is the act of removing or updating a cache entry when the underlying data changes.

### Event-Driven Invalidation

Delete or update the cache key immediately when the source data changes.

```python
# Write operation: update user, then invalidate cache
async def update_user(user_id: int, name: str, session: AsyncSession, redis: Redis):
    await session.execute(
        text("UPDATE users SET name = :name WHERE id = :id"),
        {"name": name, "id": user_id}
    )
    await session.commit()
    # Invalidate immediately — next read will fetch fresh data from DB
    await redis.delete(f"user:{user_id}")
    await redis.delete(f"user:profile:{user_id}")  # all related keys
```

**Pros:** Near-zero staleness window after writes.
**Cons:** Requires the write path to know all cache keys to invalidate. Easy to miss keys. Cross-service invalidation requires messaging.

### TTL-Based Invalidation

Let keys expire naturally. Accept eventual consistency — data may be stale for up to TTL seconds.

**Pros:** No code needed on write path. Tolerates write-side failures (key expires anyway).
**Cons:** Stale data window = TTL. Not suitable for data where freshness is critical.

### Versioned Cache Keys

Embed a version/timestamp in the cache key itself. "Invalidation" means incrementing the version — old keys are abandoned and expire naturally.

```python
# Key: user:{id}:v{version}
# Get current version from a metadata store
async def get_user_version(user_id: int, redis: Redis) -> int:
    v = await redis.get(f"user:{user_id}:version")
    return int(v) if v else 1

async def get_user(user_id: int, redis: Redis) -> dict:
    version = await get_user_version(user_id, redis)
    key = f"user:{user_id}:v{version}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    # fetch from DB, cache with new version key
    ...

async def invalidate_user(user_id: int, redis: Redis):
    # Increment version — old key becomes unreachable
    await redis.incr(f"user:{user_id}:version")
    # Old keys expire via TTL; no need to actively delete them
```

**Pros:** Atomic invalidation — no race condition between delete and read.
**Cons:** Orphaned old keys linger until TTL expiry — requires appropriate TTL.

### Cache Tags

Group related cache keys under a "tag". Invalidate all keys with a given tag atomically.

```python
# Pseudo-implementation using Redis sets
async def set_with_tags(redis: Redis, key: str, value: str, tags: list[str], ttl: int):
    pipe = redis.pipeline()
    pipe.setex(key, ttl, value)
    for tag in tags:
        pipe.sadd(f"tag:{tag}", key)
        pipe.expire(f"tag:{tag}", ttl)
    await pipe.execute()

async def invalidate_tag(redis: Redis, tag: str):
    keys = await redis.smembers(f"tag:{tag}")
    if keys:
        await redis.delete(*keys)
    await redis.delete(f"tag:{tag}")

# Usage
await set_with_tags(redis, f"product:{id}", json.dumps(product), 
                    tags=[f"product:{id}", "products:featured", f"category:{cat_id}"])
# Later: when category is updated, invalidate all products in that category
await invalidate_tag(redis, f"category:{cat_id}")
```

**Pros:** Powerful group invalidation. Invalidate an entire category of cached data with one operation.
**Cons:** Complexity. The tag set itself must be maintained. Works best in single-Redis deployments.

### Stale-While-Revalidate Pattern

Serve stale data immediately, then refresh in the background. Used extensively in HTTP caching (`Cache-Control: stale-while-revalidate=60`) and can be implemented in application-level caches.

```python
import asyncio
from datetime import datetime, timedelta

async def get_with_stale_revalidate(redis: Redis, key: str, 
                                     fetcher_fn, ttl: int, stale_ttl: int):
    """
    ttl: freshness window (serve from cache, definitely fresh)
    stale_ttl: staleness window (serve stale, but trigger background refresh)
    After stale_ttl: cache miss, must wait for fresh data
    """
    meta_key = f"{key}:meta"
    cached_value = await redis.get(key)
    meta = await redis.hgetall(meta_key)
    
    if not cached_value:
        # Full cache miss — fetch synchronously
        value = await fetcher_fn()
        await cache_set(redis, key, meta_key, value, ttl, stale_ttl)
        return value
    
    fetched_at = float(meta.get(b'fetched_at', 0))
    age = datetime.now().timestamp() - fetched_at
    
    if age < ttl:
        # Fresh — return immediately
        return json.loads(cached_value)
    elif age < stale_ttl:
        # Stale but within acceptable window — return stale, refresh async
        asyncio.create_task(background_refresh(redis, key, meta_key, fetcher_fn, ttl, stale_ttl))
        return json.loads(cached_value)
    else:
        # Too stale — synchronous refresh
        value = await fetcher_fn()
        await cache_set(redis, key, meta_key, value, ttl, stale_ttl)
        return value
```

---

## 5. Cache Failure Modes

### Cache Stampede / Thundering Herd

**What it is:**
A popular cache key expires. Before the first request can refill it, 1000 concurrent requests all see a cache miss and all issue the same expensive DB query simultaneously. The DB is suddenly hit with 1000 identical queries — a stampede.

This is particularly dangerous because:
- It happens at the worst time — when traffic is high (popular items expire under load)
- The DB gets hit by a spike of identical queries it normally handles as 1 (cache hit)
- Under DB pressure, queries slow down — which makes the stampede worse
- Can cascade: slow DB responses → request queuing → timeout → retry storm

**Solution 1: Mutex / Lock**
Only one request is allowed to query the DB on a miss. Other requests wait for the first to finish and populate the cache.

```go
// Go: using Redis as distributed mutex
func (c *Cache) GetWithMutex(ctx context.Context, key string, 
                              fetcher func() (any, error)) (any, error) {
    // Fast path: cache hit
    if val, err := c.redis.Get(ctx, key).Result(); err == nil {
        return val, nil
    }

    // Try to acquire lock
    lockKey := "lock:" + key
    acquired, err := c.redis.SetNX(ctx, lockKey, "1", 10*time.Second).Result()
    if err != nil {
        return nil, err
    }

    if acquired {
        // We hold the lock — fetch from DB and populate cache
        defer c.redis.Del(ctx, lockKey)
        value, err := fetcher()
        if err != nil {
            return nil, err
        }
        c.redis.Set(ctx, key, value, c.ttl)
        return value, nil
    }

    // Another goroutine holds the lock — wait briefly and retry
    time.Sleep(50 * time.Millisecond)
    val, err := c.redis.Get(ctx, key).Result()
    if err != nil {
        return nil, fmt.Errorf("waited for lock but cache still empty: %w", err)
    }
    return val, nil
}
```

**Solution 2: Probabilistic Early Expiration (PER)**
Also called "XFetch" algorithm. Before a key expires, randomly decide to refresh it with increasing probability as the key ages toward expiry. No locking required.

```python
import math
import random
import time

async def get_with_xfetch(redis, key: str, fetcher_fn, ttl: int, beta: float = 1.0):
    """
    beta: higher = more aggressive early recomputation (1.0 is usually fine)
    """
    result = await redis.get(key)
    ttl_remaining = await redis.ttl(key)
    
    if result is not None:
        # Compute probability of early refresh
        # As TTL approaches 0, this probability increases
        # beta * log(random()) is always negative; when close to expiry it exceeds -ttl_remaining
        if -beta * math.log(random.random()) < ttl_remaining:
            return json.loads(result)
        # else: probabilistically decide to refresh early
    
    # Fetch fresh data from DB
    value = await fetcher_fn()
    await redis.setex(key, ttl, json.dumps(value))
    return value
```

**Solution 3: Background Refresh**
Keep an in-memory record of when each cache key was populated. Start an async refresh before the TTL expires so the key is never truly "cold".

---

### Cache Penetration

**What it is:**
Requests come in for keys that **don't exist in the database**. The cache misses (correctly — data doesn't exist), the DB is queried (finds nothing), and the result is NOT cached (nothing to cache). Every subsequent request for the same non-existent key hits the DB again.

Attack vector: Malicious user queries `GET /users/99999999` for IDs that don't exist. Each request bypasses the cache and hits the DB.

**Solution 1: Cache null/negative results**
```python
SENTINEL = "__null__"

async def get_user(user_id: int, redis, session) -> Optional[dict]:
    key = f"user:{user_id}"
    cached = await redis.get(key)
    
    if cached is not None:
        if cached == SENTINEL:
            return None  # Cached absence — not in DB
        return json.loads(cached)
    
    # DB lookup
    result = await session.execute(...)
    user = result.first()
    
    if user is None:
        # Cache the absence with a SHORT TTL (don't lock it out forever)
        await redis.setex(key, 60, SENTINEL)  # 60 seconds for non-existent
        return None
    
    await redis.setex(key, 300, json.dumps(dict(user._mapping)))
    return dict(user._mapping)
```

**Solution 2: Bloom Filter**
A space-efficient probabilistic data structure that can definitively say "this key does NOT exist" (no false negatives) with a small false-positive rate. Store all valid IDs in a Bloom filter. Before querying cache or DB, check the Bloom filter.

```python
# Using Redis Bloom module (RedisBloom)
async def setup_bloom_filter(redis, all_user_ids: list[int]):
    # Create filter: capacity 10M items, 1% false positive rate
    await redis.execute_command('BF.RESERVE', 'user_ids', 0.01, 10_000_000)
    # Batch-add all existing user IDs
    await redis.execute_command('BF.MADD', 'user_ids', *[str(id) for id in all_user_ids])

async def get_user_with_bloom(user_id: int, redis, session):
    # Quick check: definitely not in DB if Bloom filter says False
    exists = await redis.execute_command('BF.EXISTS', 'user_ids', str(user_id))
    if not exists:
        return None  # No cache check, no DB check
    
    # Proceed with normal cache-aside
    return await get_user(user_id, redis, session)
```

**Trade-off:** Bloom filters have false positives (may say "exists" when it doesn't) but never false negatives (if it says "doesn't exist," it definitely doesn't). For cache penetration defense, this is exactly what we want.

---

### Cache Avalanche

**What it is:**
A large number of cache keys expire at the same time — typically because they were all populated together (e.g., at startup, or after a cache flush). Suddenly, thousands of keys are expired simultaneously and all requests miss the cache, creating a massive flood of DB queries.

Different from stampede (one key → many requests). Avalanche = many keys → many requests, all simultaneously.

**Solution: TTL Jitter**
Add a random offset to the TTL when setting cache keys so they don't all expire at the same time:

```go
// Go: add jitter to TTL
func (c *Cache) Set(ctx context.Context, key string, value any, baseTTL time.Duration) error {
    // Jitter: add 0-20% random offset to base TTL
    jitter := time.Duration(rand.Int63n(int64(baseTTL / 5)))
    ttl := baseTTL + jitter
    
    data, err := json.Marshal(value)
    if err != nil {
        return err
    }
    return c.redis.Set(ctx, key, data, ttl).Err()
}

// Usage: base TTL = 5 minutes, actual TTL = 5:00 to 6:00 randomly
c.Set(ctx, "product:1", product, 5*time.Minute)
c.Set(ctx, "product:2", product2, 5*time.Minute)  // Different expiry time
```

```javascript
// Node.js: TTL with jitter
function setWithJitter(redis, key, value, baseTtlSeconds, jitterPct = 0.2) {
  const jitter = Math.floor(Math.random() * baseTtlSeconds * jitterPct);
  const ttl = baseTtlSeconds + jitter;
  return redis.set(key, JSON.stringify(value), 'EX', ttl);
}
```

```python
# Python: TTL with jitter
import random

def set_with_jitter(redis_client, key: str, value, base_ttl: int, jitter_pct: float = 0.2):
    jitter = random.randint(0, int(base_ttl * jitter_pct))
    ttl = base_ttl + jitter
    redis_client.setex(key, ttl, json.dumps(value))
```

**Other solutions:**
- **Pre-warming:** On cache flush or restart, proactively populate the cache before serving traffic
- **Circuit breaker:** If cache hit rate drops below threshold, stop serving traffic until cache warms
- **Staggered cache population:** During mass-load, introduce deliberate delays between key populations

---

## 6. Multi-Level Caching

Real-world systems often have multiple cache layers, each with different latency, capacity, and consistency characteristics.

### Typical Stack

```
Request → [L1: In-process LRU] → [L2: Redis] → [L3: Database]
            ~100ns                 ~1ms            ~10ms
            MB-scale               GB-scale         TB-scale
            per-instance           shared            shared
            lost on restart        survives restart  durable
```

**L1: In-Process Cache (in-memory, per-instance)**
- A small LRU map (e.g., 1000-10000 entries) inside your application process
- Zero network overhead — memory access only
- Per-instance: each app server has its own L1. Changes on one server are NOT visible on others until the key expires.
- Best for: very hot, rarely-changing data (app config, feature flags, frequently-accessed reference data)

```go
// Go: simple in-process LRU using golang.org/x/exp or github.com/hashicorp/golang-lru
import lru "github.com/hashicorp/golang-lru/v2"

type MultiLevelCache struct {
    l1    *lru.Cache[string, []byte]
    redis *redis.Client
    l1TTL time.Duration
}

func NewMultiLevelCache(l1Size int, redis *redis.Client, l1TTL time.Duration) *MultiLevelCache {
    cache, _ := lru.New[string, []byte](l1Size)
    return &MultiLevelCache{l1: cache, redis: redis, l1TTL: l1TTL}
}

func (c *MultiLevelCache) Get(ctx context.Context, key string) ([]byte, bool) {
    // L1 check
    if val, ok := c.l1.Get(key); ok {
        return val, true // L1 hit: ~100ns
    }
    
    // L2 (Redis) check
    val, err := c.redis.Get(ctx, key).Bytes()
    if err == nil {
        c.l1.Add(key, val) // backfill L1
        return val, true // L2 hit: ~1ms
    }
    
    return nil, false // full miss — caller must fetch from DB
}
```

**L2: Redis (distributed, shared)**
- Shared across all app instances — consistent view
- Survives app restarts
- Best for: user sessions, hot items that aren't worth keeping in every app instance's L1

**L3: Database**
- Authoritative source of truth
- Always the fallback

### CDN as HTTP-Level Cache

For HTTP responses, CDNs (Cloudflare, CloudFront, Fastly) act as a cache layer closer to users. They cache based on HTTP `Cache-Control` headers:

```
Cache-Control: public, max-age=3600, stale-while-revalidate=86400
```
- `max-age=3600`: CDN caches response for 1 hour (fresh)
- `stale-while-revalidate=86400`: After 1 hour, serve stale response while fetching fresh in background (up to 24 hours)

For dynamic API responses that are safe to cache:
```
Cache-Control: public, max-age=60, s-maxage=300
# s-maxage overrides max-age for shared caches (CDNs) — cache for 5 minutes at CDN level
# max-age=60 for browser cache — client caches for 1 minute
```

For user-specific data (never cache at CDN):
```
Cache-Control: private, no-store
```

---

## 7. Implementation Examples

### Go + Chi: Cache-Aside with Stampede Prevention

```go
package cache

import (
    "context"
    "encoding/json"
    "errors"
    "fmt"
    "math/rand"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/redis/go-redis/v9"
)

var ErrCacheMiss = errors.New("cache miss")

type CacheLayer struct {
    client  *redis.Client
    baseTTL time.Duration
}

func NewCacheLayer(redisURL string, baseTTL time.Duration) (*CacheLayer, error) {
    opts, err := redis.ParseURL(redisURL)
    if err != nil {
        return nil, err
    }
    client := redis.NewClient(opts)
    if err := client.Ping(context.Background()).Err(); err != nil {
        return nil, fmt.Errorf("redis ping: %w", err)
    }
    return &CacheLayer{client: client, baseTTL: baseTTL}, nil
}

// ttlWithJitter adds 0-20% random jitter to prevent cache avalanche
func (c *CacheLayer) ttlWithJitter(base time.Duration) time.Duration {
    maxJitter := int64(base / 5) // 20% jitter
    jitter := time.Duration(rand.Int63n(maxJitter))
    return base + jitter
}

// GetOrFetch is the core cache-aside pattern with stampede protection via mutex
func (c *CacheLayer) GetOrFetch(
    ctx context.Context,
    key string,
    dest any,
    fetcher func(ctx context.Context) (any, error),
    ttl time.Duration,
) error {
    // 1. Try cache first
    raw, err := c.client.Get(ctx, key).Bytes()
    if err == nil {
        return json.Unmarshal(raw, dest)
    }
    if !errors.Is(err, redis.Nil) {
        return fmt.Errorf("redis get %s: %w", key, err)
    }

    // 2. Cache miss — try to acquire distributed mutex to prevent stampede
    lockKey := "lock:" + key
    lockVal := fmt.Sprintf("%d", rand.Int63()) // unique value per lock holder
    
    acquired, lockErr := c.client.SetNX(ctx, lockKey, lockVal, 15*time.Second).Result()
    if lockErr != nil {
        // If we can't acquire the lock due to Redis issues, just fetch without locking
        return c.fetchAndCache(ctx, key, dest, fetcher, ttl)
    }
    
    if !acquired {
        // Someone else is fetching. Wait briefly and retry from cache.
        time.Sleep(100 * time.Millisecond)
        raw2, err2 := c.client.Get(ctx, key).Bytes()
        if err2 == nil {
            return json.Unmarshal(raw2, dest)
        }
        // Still not in cache — fall through and fetch ourselves
        // (lock holder may have failed)
    }

    if acquired {
        // We hold the lock — release it when done
        defer func() {
            // Only delete if we still own the lock (check value matches)
            script := redis.NewScript(`
                if redis.call("GET", KEYS[1]) == ARGV[1] then
                    return redis.call("DEL", KEYS[1])
                else
                    return 0
                end
            `)
            script.Run(ctx, c.client, []string{lockKey}, lockVal)
        }()
    }

    return c.fetchAndCache(ctx, key, dest, fetcher, ttl)
}

func (c *CacheLayer) fetchAndCache(
    ctx context.Context,
    key string,
    dest any,
    fetcher func(ctx context.Context) (any, error),
    ttl time.Duration,
) error {
    value, err := fetcher(ctx)
    if err != nil {
        return fmt.Errorf("fetcher for %s: %w", key, err)
    }

    data, err := json.Marshal(value)
    if err != nil {
        return err
    }

    // Store result with jitter to prevent avalanche
    effectiveTTL := c.ttlWithJitter(ttl)
    
    // Handle null results (prevent cache penetration)
    if value == nil {
        c.client.Set(ctx, key, `null`, 60*time.Second) // short TTL for nulls
        return nil
    }
    
    if err := c.client.Set(ctx, key, data, effectiveTTL).Err(); err != nil {
        // Cache write failure is non-fatal — log and continue
        fmt.Printf("warn: cache set %s: %v\n", key, err)
    }

    return json.Unmarshal(data, dest)
}

// Invalidate deletes cache keys (supports wildcards via SCAN, not KEYS)
func (c *CacheLayer) Invalidate(ctx context.Context, keys ...string) error {
    if len(keys) == 0 {
        return nil
    }
    return c.client.Del(ctx, keys...).Err()
}

// ─── Chi Router Integration ───────────────────────────────────────────────────

type UserHandler struct {
    db    *DB
    cache *CacheLayer
}

func (h *UserHandler) GetUser(w http.ResponseWriter, r *http.Request) {
    userID := chi.URLParam(r, "userID")
    cacheKey := fmt.Sprintf("user:%s", userID)

    var user User
    err := h.cache.GetOrFetch(r.Context(), cacheKey, &user,
        func(ctx context.Context) (any, error) {
            return h.db.GetUserByID(ctx, userID)
        },
        5*time.Minute,
    )
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(user)
}

func (h *UserHandler) UpdateUser(w http.ResponseWriter, r *http.Request) {
    userID := chi.URLParam(r, "userID")
    var req UpdateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "bad request", http.StatusBadRequest)
        return
    }

    if err := h.db.UpdateUser(r.Context(), userID, req); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

    // Invalidate all related cache keys
    h.cache.Invalidate(r.Context(),
        fmt.Sprintf("user:%s", userID),
        fmt.Sprintf("user:profile:%s", userID),
    )

    w.WriteHeader(http.StatusNoContent)
}
```

---

### Node.js + Express: Cache-Aside with Jitter

```javascript
const Redis = require('ioredis');

const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: parseInt(process.env.REDIS_PORT || '6379'),
  retryStrategy: (times) => Math.min(times * 100, 3000), // exponential backoff
  enableReadyCheck: true,
  maxRetriesPerRequest: 3,
});

// TTL with jitter to prevent cache avalanche
function ttlWithJitter(baseTtlSeconds, jitterPct = 0.2) {
  const jitter = Math.floor(Math.random() * baseTtlSeconds * jitterPct);
  return baseTtlSeconds + jitter;
}

// Cache-aside: get from cache or fetch from DB
async function cacheAside(key, fetcher, ttlSeconds = 300) {
  try {
    const cached = await redis.get(key);
    if (cached !== null) {
      // Handle cached null (cache penetration defense)
      if (cached === '__null__') return null;
      return JSON.parse(cached);
    }
  } catch (err) {
    // Redis failure: degrade gracefully, go to DB
    console.warn(`Redis GET failed for ${key}:`, err.message);
  }

  // Cache miss: fetch from source
  const value = await fetcher();

  try {
    const ttl = ttlWithJitter(ttlSeconds);
    if (value === null || value === undefined) {
      // Cache null with short TTL (prevent penetration)
      await redis.set(key, '__null__', 'EX', 60);
    } else {
      await redis.set(key, JSON.stringify(value), 'EX', ttl);
    }
  } catch (err) {
    console.warn(`Redis SET failed for ${key}:`, err.message);
    // Non-fatal: just return the value without caching
  }

  return value;
}

// Stampede prevention using a simple in-memory lock per key
// For distributed locking across instances, use Redis SETNX (see Part 8.2)
const inFlightFetches = new Map();

async function getOrFetch(key, fetcher, ttlSeconds = 300) {
  // Check cache first
  try {
    const cached = await redis.get(key);
    if (cached !== null) {
      return cached === '__null__' ? null : JSON.parse(cached);
    }
  } catch (err) {
    console.warn('Redis error:', err.message);
  }

  // Check if there's already an in-flight fetch for this key (single-process dedup)
  if (inFlightFetches.has(key)) {
    return inFlightFetches.get(key);
  }

  // Start the fetch and register the promise
  const fetchPromise = fetcher()
    .then(async (value) => {
      try {
        const ttl = ttlWithJitter(ttlSeconds);
        if (value == null) {
          await redis.set(key, '__null__', 'EX', 60);
        } else {
          await redis.set(key, JSON.stringify(value), 'EX', ttl);
        }
      } catch (err) {
        console.warn('Cache set error:', err.message);
      }
      return value;
    })
    .finally(() => {
      inFlightFetches.delete(key);
    });

  inFlightFetches.set(key, fetchPromise);
  return fetchPromise;
}

// Express middleware: cache entire route response
function cacheMiddleware(ttlSeconds = 60) {
  return async (req, res, next) => {
    // Don't cache non-GET or authenticated routes with user-specific data
    if (req.method !== 'GET' || req.user) {
      return next();
    }

    const key = `route:${req.originalUrl}`;
    const cached = await redis.get(key).catch(() => null);
    
    if (cached) {
      res.setHeader('X-Cache', 'HIT');
      res.setHeader('Content-Type', 'application/json');
      return res.send(cached);
    }

    // Capture response
    const originalJson = res.json.bind(res);
    res.json = (data) => {
      redis.set(key, JSON.stringify(data), 'EX', ttlWithJitter(ttlSeconds))
           .catch((err) => console.warn('Cache middleware SET error:', err));
      res.setHeader('X-Cache', 'MISS');
      return originalJson(data);
    };

    next();
  };
}

// Express routes
const express = require('express');
const router = express.Router();

const db = require('./db');

router.get('/products/:id', async (req, res) => {
  const product = await getOrFetch(
    `product:${req.params.id}`,
    () => db.getProduct(req.params.id),
    3600 // 1 hour TTL with jitter
  );
  if (!product) return res.status(404).json({ error: 'Not found' });
  res.json(product);
});

router.put('/products/:id', async (req, res) => {
  await db.updateProduct(req.params.id, req.body);
  // Invalidate
  await redis.del(`product:${req.params.id}`);
  res.json({ success: true });
});

// Public product catalog route with full-page caching
router.get('/products', cacheMiddleware(300), async (req, res) => {
  const products = await db.getProducts(req.query);
  res.json(products);
});

module.exports = router;
```

---

### Python + FastAPI: Cache-Aside with Stampede Prevention

```python
from __future__ import annotations
import json
import random
import asyncio
import time
from typing import Any, Callable, Awaitable, Optional, TypeVar
from redis.asyncio import Redis
from fastapi import FastAPI, Depends, HTTPException
from functools import wraps
import logging

logger = logging.getLogger(__name__)
T = TypeVar("T")

class CacheService:
    NULL_SENTINEL = "__null__"

    def __init__(self, redis: Redis, default_ttl: int = 300):
        self.redis = redis
        self.default_ttl = default_ttl
        # In-process lock registry: prevents thundering herd within a single process
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_meta: dict[str, float] = {}  # track last acquired time

    def _ttl_with_jitter(self, base_ttl: int, jitter_pct: float = 0.2) -> int:
        jitter = random.randint(0, int(base_ttl * jitter_pct))
        return base_ttl + jitter

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache. Returns None on miss or error."""
        try:
            raw = await self.redis.get(key)
            if raw is None:
                return None
            if raw == self.NULL_SENTINEL:
                return self.NULL_SENTINEL  # sentinel: cached non-existence
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Cache GET error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with jittered TTL."""
        effective_ttl = self._ttl_with_jitter(ttl or self.default_ttl)
        try:
            if value is None:
                await self.redis.setex(key, 60, self.NULL_SENTINEL)  # short TTL for null
            else:
                await self.redis.setex(key, effective_ttl, json.dumps(value))
        except Exception as e:
            logger.warning(f"Cache SET error for {key}: {e}")

    async def invalidate(self, *keys: str) -> None:
        """Delete one or more cache keys."""
        if keys:
            try:
                await self.redis.delete(*keys)
            except Exception as e:
                logger.warning(f"Cache invalidation error: {e}")

    async def get_or_fetch(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Cache-aside with in-process stampede prevention.
        For cross-process stampede prevention, extend with Redis SETNX lock.
        """
        # Fast path: cache hit
        cached = await self.get(key)
        if cached is not None:
            return None if cached == self.NULL_SENTINEL else cached

        # Prevent multiple concurrent in-process fetches for the same key
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            # Double-check after acquiring lock — another coroutine may have populated cache
            cached = await self.get(key)
            if cached is not None:
                return None if cached == self.NULL_SENTINEL else cached

            # Fetch from source
            try:
                value = await fetcher()
            except Exception as e:
                logger.error(f"Fetcher error for {key}: {e}")
                raise

            await self.set(key, value, ttl)
            return value


# ─── Dependency injection ──────────────────────────────────────────────────────

async def get_redis() -> Redis:
    return Redis.from_url(
        "redis://localhost:6379",
        decode_responses=True,
        socket_timeout=1.0,        # fail fast on Redis issues
        socket_connect_timeout=1.0,
    )

async def get_cache(redis: Redis = Depends(get_redis)) -> CacheService:
    return CacheService(redis, default_ttl=300)


# ─── Decorator pattern for caching ────────────────────────────────────────────

def cached(key_template: str, ttl: int = 300):
    """Decorator to cache async functions. key_template uses .format(**kwargs)."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache: CacheService = kwargs.get("cache") or args[0].cache
            cache_key = key_template.format(**kwargs)
            return await cache.get_or_fetch(
                cache_key,
                lambda: func(*args, **kwargs),
                ttl,
            )
        return wrapper
    return decorator


# ─── FastAPI application ───────────────────────────────────────────────────────

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    cache: CacheService = Depends(get_cache),
    session = Depends(get_session),
):
    """Cache-aside: check cache, miss → DB, populate cache."""
    return await cache.get_or_fetch(
        key=f"user:{user_id}",
        fetcher=lambda: fetch_user_from_db(session, user_id),
        ttl=300,  # 5 minutes + jitter
    )

@app.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    cache: CacheService = Depends(get_cache),
    session = Depends(get_session),
):
    """Write-through pattern: write to DB, then invalidate cache."""
    await update_user_in_db(session, user_id, body)
    # Invalidate all keys related to this user
    await cache.invalidate(
        f"user:{user_id}",
        f"user:profile:{user_id}",
        f"user:orders:{user_id}",
    )
    return {"status": "updated"}

@app.get("/products")
async def list_products(
    category: Optional[str] = None,
    cache: CacheService = Depends(get_cache),
    session = Depends(get_session),
):
    """Cache entire product list by category — write-through on product updates."""
    key = f"products:category:{category or 'all'}"
    return await cache.get_or_fetch(
        key=key,
        fetcher=lambda: fetch_products_from_db(session, category),
        ttl=3600,  # 1 hour for product catalog
    )

async def fetch_user_from_db(session, user_id: int):
    from sqlalchemy import text
    result = await session.execute(
        text("SELECT id, name, email, created_at FROM users WHERE id = :id AND deleted_at IS NULL"),
        {"id": user_id}
    )
    row = result.first()
    return dict(row._mapping) if row else None
```

---

## 8. Common Patterns & Best Practices

**Key naming conventions:**
```
{service}:{entity}:{id}           → user:profile:42
{service}:{entity}:{id}:{field}   → user:orders:42:count
{service}:{entity}:{filter}       → products:category:electronics
route:{method}:{path}             → route:GET:/api/products?page=1
```

**Always use serialization consistently:** JSON is safe. Avoid language-specific serialization (pickle in Python) — it ties your cache to a specific application version.

**Monitor cache hit rates:** Target >80% hit rate for frequently-accessed data. Below 60% means your TTL is too short or keys are too granular.

**Key eviction planning:** Set `maxmemory` and `maxmemory-policy` in Redis. For pure cache use cases, `allkeys-lru` evicts least-recently-used keys when memory is full. For mixed use (cache + durable data), use `volatile-lru` to only evict keys with TTL set.

**Never cache inside a transaction:** Cache writes should happen after the DB transaction commits — not inside it. If the transaction rolls back, the cache would contain data that was never persisted.

---

## 9. Common Pitfalls

| Pitfall | Problem | Fix |
|---|---|---|
| Caching inside DB transaction | Cache has data for rolled-back transactions | Only cache after successful commit |
| Not setting TTL | Memory fills up, keys never expire | Always set TTL; use `allkeys-lru` as safety net |
| `KEYS *` in production | Blocks Redis single thread for seconds | Use `SCAN` with cursor for key iteration |
| Storing large objects | Serialization overhead + memory pressure | Break large objects into smaller keys |
| Caching non-serializable objects | Crashes on serialize/deserialize | Always test round-trip |
| Not handling Redis connection failure | Application throws 500 on Redis down | Wrap cache calls in try/catch; degrade to DB |
| Language-specific serialization (pickle) | Cache incompatible after code deployment | Use JSON or MessagePack |
| Cache key collisions between environments | Dev cache poisoning prod | Add environment prefix: `prod:user:42` |
| Not invalidating on updates | Stale data served after writes | Explicitly delete cache keys on writes |
| Single long TTL for all keys | Avalanche risk | Use jitter or staggered TTLs |

---

## 10. Interview Questions & Model Answers

**Q: Explain cache-aside vs write-through. When would you choose each?**

Cache-aside (lazy loading): On read, check cache first; on miss, fetch from DB and populate cache. On write, update DB and delete the cache key. The cache only contains what's been recently read. Choose this when: reads vastly outnumber writes, you're okay with a miss penalty on first access, and cache failure should degrade gracefully (app still works, just slower).

Write-through: Every write goes to both cache and DB simultaneously. Cache is always fresh; no cold start. Choose this when: write volume is low, data is almost always read back after writes, and you can tolerate slightly higher write latency. Example: user preferences, app configuration.

In practice, cache-aside is the default for most systems because it only caches hot data and is resilient to cache failure.

**Q: What is cache stampede? How do you prevent it?**

Cache stampede (thundering herd) occurs when a popular cache key expires and many concurrent requests all see a cache miss and simultaneously query the database. Each request independently decides to fetch and repopulate the cache, creating a sudden spike of identical DB queries.

Prevention strategies: (1) **Mutex lock** — use Redis SETNX to acquire a per-key lock; only the lock holder fetches from DB, others wait briefly and retry from cache; (2) **Probabilistic early expiration (XFetch)** — randomly decide to refresh the key before it expires, with increasing probability as TTL approaches zero; no locking needed; (3) **Background refresh** — proactively refresh hot keys before they expire using a background job.

**Q: What is the difference between cache penetration and cache avalanche?**

Cache penetration: Requests for keys that don't exist in the database. The cache correctly misses (nothing to cache), and every request hits the DB. Can be a DDoS vector. Fix: cache null/sentinel values for non-existent keys with a short TTL; or use a Bloom filter to immediately return "not found" for provably non-existent keys.

Cache avalanche: Many cache keys expire simultaneously, causing a wave of DB queries. Typically happens after a cache flush or when keys are populated together with the same TTL. Fix: add random jitter to TTL (e.g., 5min base ± 1min random). This spreads expiry times so no two keys expire at exactly the same moment.

**Q: How do you handle cache invalidation in a distributed system?**

This is fundamentally hard because there's no atomic "update DB + invalidate cache" operation. Common strategies: (1) **Delete on write** — update DB, then delete cache key; next read repopulates (cache-aside). Risk: brief staleness window between write and delete. (2) **TTL-based** — accept eventual consistency; cache keys expire naturally. Simple but has a staleness window of up to TTL. (3) **Event-driven** — publish an "entity updated" event (Kafka/Redis Streams) that all services consume to invalidate their local caches. Decoupled but adds complexity. (4) **Versioned keys** — include a version in the key (`user:42:v3`); invalidation means incrementing the version; old keys expire naturally. Atomic but leaves orphaned keys.

**Q: What TTL would you set for user profile data?**

5-15 minutes is a reasonable range. Reasoning: user profiles (name, email, avatar, bio) change infrequently — maybe once a week. A 5-minute staleness window means a profile change might show the old value for up to 5 minutes, which is acceptable UX. Shorter (30s-1min) is unnecessarily aggressive and increases DB load. Longer (1hr) risks users seeing very stale data after an important update (like email change). You'd also use event-driven invalidation on top of TTL — when a user updates their profile, explicitly delete the cache key so the next read gets the fresh value immediately. The TTL is the safety net for missed invalidations.

**Q: What is the stale-while-revalidate pattern?**

Stale-while-revalidate serves cached data immediately (even if stale) while asynchronously fetching fresh data in the background. It eliminates the "miss penalty" — users never wait for a cache refresh. The client receives a response immediately; in the background, the system fetches fresh data and updates the cache for the next request. In HTTP caching: `Cache-Control: max-age=60, stale-while-revalidate=300` means: serve from cache for 60s (fresh), then for up to 5 more minutes serve stale data while revalidating in the background. In application caches: when you detect a key is older than its fresh-window but younger than its stale-window, return the stale value immediately and spawn an async task to refresh it.

---

## 11. Resources

- [Redis Documentation](https://redis.io/docs/)
- [AWS ElastiCache Best Practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)
- [Caching Patterns by AWS](https://aws.amazon.com/caching/best-practices/)
- [Martin Fowler: Cache Aside Pattern](https://martinfowler.com/bliki/CachingBestPractices.html)
- [An Analysis of Facebook's Memcache Paper](https://www.usenix.org/system/files/conference/nsdi13/nsdi13-final170_update.pdf)
- [XFetch Algorithm (Probabilistic Cache Stampede Prevention)](https://cseweb.ucsd.edu/~avattani/papers/cache_stampede.pdf)
- [Designing Data-Intensive Applications](https://dataintensive.net/) — Martin Kleppmann

---

**Next:** [Part 8.2: Redis Patterns & Data Structures](./08-redis-patterns.md)
