# Part 8.2: Redis Patterns & Data Structures

## What You'll Learn
- Every Redis data structure: when to use each and why Redis supports them natively
- Production-grade patterns: session storage, rate limiting, distributed locks, pub/sub, job queues, leaderboards, geospatial, Bloom filters
- Redis internals: single-threaded model, persistence (RDB vs AOF), eviction policies, Cluster vs Sentinel
- Complete implementations in Go (go-redis), Node.js (ioredis), Python (redis-py)

---

## Table of Contents
1. [Redis Data Structures](#1-redis-data-structures)
   - Strings
   - Hashes
   - Lists
   - Sets
   - Sorted Sets (ZSets)
   - Streams
   - Bitmaps
2. [Redis Patterns](#2-redis-patterns)
   - Session Storage
   - Rate Limiting
   - Distributed Lock (SETNX + Redlock)
   - Pub/Sub vs Streams
   - Job Queue
   - Leaderboard
   - Geospatial
   - Bloom Filter
3. [Redis Internals](#3-redis-internals)
   - Single-Threaded Model
   - Persistence: RDB vs AOF
   - Redis Cluster vs Sentinel
   - Eviction Policies
   - Memory Management
4. [Redis Production Considerations](#4-redis-production-considerations)
5. [Implementation Examples](#5-implementation-examples)
   - Go (go-redis)
   - Node.js (ioredis)
   - Python (redis-py)
6. [Common Patterns & Best Practices](#6-common-patterns--best-practices)
7. [Common Pitfalls](#7-common-pitfalls)
8. [Interview Questions & Model Answers](#8-interview-questions--model-answers)
9. [Resources](#9-resources)

---

## 1. Redis Data Structures

Understanding which data structure to reach for is the first step in any Redis-related interview question. Redis is not just a key-value store — it's a data structure server.

### Strings

The simplest type: a binary-safe byte sequence under a key. Despite the name, strings hold integers, floats, serialized JSON, binary blobs — anything up to 512MB.

**Key commands:**
```redis
SET key value [EX seconds] [PX milliseconds] [NX | XX] [GET]
GET key
INCR key              # atomic increment (integer strings only)
INCRBY key delta
DECR key
DECRBY key delta
INCRBYFLOAT key delta # atomic float increment
SETNX key value       # set only if Not eXists (legacy; prefer SET ... NX)
GETEX key EX seconds  # get + update expiry atomically (Redis 6.2+)
GETDEL key            # get + delete atomically
```

**`SET` options explained:**
- `EX 300` — expire in 300 seconds
- `PX 5000` — expire in 5000 milliseconds
- `NX` — only set if key does NOT exist (used for distributed locking)
- `XX` — only set if key DOES exist (update, not create)
- `GET` — return old value (Redis 6.2+) — enables atomic test-and-set

**Use cases:**
- Simple caching: `SET product:42 "{...json...}" EX 3600`
- Counters: `INCR api:requests:2024-01-15` — atomic, no read-modify-write race condition
- Feature flags: `SET feature:dark_mode "true" EX 86400`
- Session tokens: `SET session:abc123 user_id_42 EX 1800`
- Distributed lock: `SET lock:resource_x unique_val NX EX 30`

**Why INCR instead of GET+increment+SET?**
Because `INCR` is atomic at the Redis command level — no other command can execute between the read and write. With GET+SET you have a race condition in concurrent environments.

---

### Hashes

A hash is a map of field-value pairs stored under a single key. Think of it as a Redis-native object representation.

**Key commands:**
```redis
HSET key field value [field value ...]  # set one or more fields
HGET key field
HMGET key field [field ...]             # get multiple fields
HGETALL key                             # get all field-value pairs
HDEL key field [field ...]
HEXISTS key field
HLEN key                                # number of fields
HINCRBY key field delta                 # atomic field increment
HKEYS key                               # list all field names
HVALS key                               # list all values
```

**Use cases:**
- **User sessions:** `HSET session:abc123 user_id 42 email user@example.com last_seen 1705123456 role admin`
- **User profiles:** One hash per user. Get individual fields without deserializing the entire object.
- **Rate limit counters per endpoint:** `HSET ratelimit:user:42 /api/orders 15 /api/products 3`
- **Shopping cart:** `HSET cart:user:42 product:1 2 product:3 1` (product_id → quantity)
- **Caching partial objects:** Avoids over-fetching when you only need one field

**Hash vs String for objects:**
- String + JSON: Simple, one GET/SET per object. Can't update one field without fetching and reserializing the entire object.
- Hash: Can HGET/HSET individual fields. More memory overhead per key (field name stored per hash). Ideal when you frequently update specific fields.
- Rule of thumb: Use Hash when you need partial updates or reads. Use String+JSON for immutable or fully-replaced objects.

**Memory note:** Redis uses a compressed encoding (`ziplist` or `listpack`) for small hashes (<128 fields, <64 bytes per field by default). Once those thresholds are exceeded, it switches to a hash table — memory usage increases. Tune `hash-max-listpack-entries` and `hash-max-listpack-value` for your workload.

---

### Lists

An ordered sequence of strings. Redis Lists are implemented as a doubly-linked list or compressed encoding for small lists.

**Key commands:**
```redis
LPUSH key value [value ...]   # push to Left (head)
RPUSH key value [value ...]   # push to Right (tail)
LPOP key [count]              # pop from left
RPOP key [count]              # pop from right
BLPOP key [key ...] timeout   # blocking pop — waits if list is empty
BRPOP key [key ...] timeout   # blocking pop from right
LRANGE key start stop         # get elements by index range
LLEN key                      # length
LINDEX key index              # element at index (O(n) — avoid for large lists)
LINSERT key BEFORE|AFTER pivot element
LREM key count value          # remove occurrences of value
LTRIM key start stop          # keep only elements in range (capped list pattern)
```

**Use cases:**
- **Task queues (FIFO):** Producers RPUSH, consumers BLPOP. `BLPOP queue:tasks 30` blocks for up to 30 seconds waiting for a job.
- **Recent activity feed:** `LPUSH feed:user:42 activity_json` + `LTRIM feed:user:42 0 99` to keep only the 100 most recent items.
- **Chat message history:** `RPUSH chat:room:123 msg_json`, serve with `LRANGE chat:room:123 -50 -1` (last 50 messages).
- **Producer-consumer patterns:** Multiple workers BLPOP from the same list.

**Capped list pattern:**
```redis
LPUSH recent:views:user:42 "product:567"
LTRIM recent:views:user:42 0 9   # keep only 10 most recent
```

**List vs Stream:** Lists are simple but lack consumer groups, message acknowledgment, and durability of the consumer position. Use Streams when you need reliable message delivery (see §Streams).

---

### Sets

Unordered collection of unique strings.

**Key commands:**
```redis
SADD key member [member ...]    # add members (ignores duplicates)
SREM key member [member ...]    # remove members
SMEMBERS key                    # get all members (avoid on large sets)
SISMEMBER key member            # O(1) membership test
SMISMEMBER key member [member...] # test multiple members (Redis 6.2+)
SCARD key                       # cardinality (count)
SPOP key [count]                # remove and return random member(s)
SRANDMEMBER key [count]         # random member without removing
SUNION key [key ...]            # union of sets
SINTER key [key ...]            # intersection
SDIFF key [key ...]             # difference
SUNIONSTORE dest key [key ...]  # store union result in dest
SINTERSTORE dest key [key ...]
```

**Use cases:**
- **Unique visitors:** `SADD visitors:2024-01-15 user_42` + `SCARD visitors:2024-01-15` for daily unique count
- **Tags on posts:** `SADD post:567:tags "golang" "backend" "redis"` + `SMEMBERS post:567:tags`
- **Following/followers:** `SADD following:user:42 user:100 user:200`. `SINTER following:user:42 following:user:100` = mutual follows
- **Online users:** `SADD online_users user:42` + EXPIRE. `SMEMBERS online_users` for online list.
- **Preventing duplicate processing:** `SADD processed:jobs job_id_xyz` → if SADD returns 0, already processed

**Performance note:** `SMEMBERS` is O(N) and returns all elements — avoid on large sets (>1000 members) in hot paths. Use `SSCAN` to iterate large sets in batches.

---

### Sorted Sets (ZSets)

The most powerful and unique Redis data structure. A set where every member has an associated float score. Members are stored sorted by score (ascending by default). Score ties are broken lexicographically.

**Key commands:**
```redis
ZADD key [NX|XX] [GT|LT] [CH] score member [score member ...]
ZSCORE key member                          # get score of a member
ZINCRBY key delta member                   # atomic score increment
ZRANK key member                           # rank (0-based, ascending)
ZREVRANK key member                        # rank (0-based, descending)
ZRANGE key start stop [BYSCORE] [REV] [LIMIT offset count] [WITHSCORES]
ZRANGEBYSCORE key min max [WITHSCORES] [LIMIT offset count]
ZRANGEBYLEX key min max [LIMIT offset count]  # when all scores equal
ZREM key member [member ...]
ZPOPMIN key [count]                        # pop N lowest-score members
ZPOPMAX key [count]                        # pop N highest-score members
BZPOPMIN key [key ...] timeout             # blocking version
ZCARD key                                  # cardinality
ZCOUNT key min max                         # count members in score range
ZUNIONSTORE dest numkeys key [key ...] [WEIGHTS ...]
ZINTERSTORE dest numkeys key [key ...]
```

**ZADD flags:**
- `NX` — only add new members (don't update scores)
- `XX` — only update existing members (don't add new)
- `GT` — only update if new score is Greater Than current score
- `LT` — only update if new score is Less Than current score
- `CH` — change return value from "new members added" to "members changed"

**Use cases:**
- **Leaderboard:** `ZADD leaderboard 1500 player:42`. `ZREVRANGE leaderboard 0 9 WITHSCORES` = top 10.
- **Rate limiting (sliding window):** Score = timestamp. See §Rate Limiting below.
- **Priority queue:** Score = priority level. `ZPOPMAX queue:tasks` = pop highest-priority task.
- **Time-sorted events:** Score = UNIX timestamp. `ZRANGEBYSCORE events:user:42 from to` = events in time range.
- **Autocomplete:** When scores are equal, members sort lexicographically. `ZRANGEBYLEX autocomplete "[jo" "[jo\xff"` = all entries starting with "jo".
- **Delayed task scheduling:** `ZADD scheduled_tasks run_at_timestamp "task:json"`. Worker polls `ZPOPMIN scheduled_tasks -inf NOW_TIMESTAMP` periodically.

---

### Streams

Redis Streams (added in Redis 5.0) are an append-only log — similar conceptually to Kafka partitions, but simpler and within Redis.

**Key commands:**
```redis
XADD key [MAXLEN [~] count] * field value [field value ...]
# * = auto-generate ID (millisecond-sequence format: 1705123456789-0)
# MAXLEN ~ 1000 = trim to approximately 1000 entries

XREAD [COUNT n] [BLOCK ms] STREAMS key [key ...] id [id ...]
# id "0" = read from beginning
# id "$" = read only new entries (like tail -f)
# id ">" in consumer groups = read undelivered entries

XRANGE key start end [COUNT n]   # read range of entries
XLEN key                          # number of entries

# Consumer groups (reliable delivery)
XGROUP CREATE key group_name id [MKSTREAM]
XREADGROUP GROUP group consumer [COUNT n] [BLOCK ms] NOACK STREAMS key [key...] id
XACK key group entry_id [entry_id ...]  # acknowledge processed entries
XPENDING key group                       # list pending (unacknowledged) entries
XCLAIM key group consumer min-idle-ms entry_id  # steal ownership of stale entry
XAUTOCLAIM key group consumer min-idle-ms start  # Redis 7.0+
```

**Stream entry IDs:** `1705123456789-0` — millisecond timestamp + sequence number. Monotonically increasing, globally unique per stream.

**Consumer groups:** Multiple consumers can read from the same stream. Each consumer in a group gets a unique subset of messages. Messages are not deleted until explicitly ACKed. If a consumer crashes, its unacked messages can be claimed by another consumer.

**When to use Streams vs Lists vs Pub/Sub:**
| Feature | List | Pub/Sub | Stream |
|---|---|---|---|
| Persistence | Yes | No | Yes |
| Consumer groups | No | No | Yes |
| Message history | Yes | No | Yes |
| Ack/retry | No | No | Yes |
| Multiple consumers | Manual | Yes (broadcast) | Yes (partitioned) |
| Best for | Simple queues | Fire-and-forget events | Reliable event log |

**Use case:** Streams are Redis's answer to "I want something like Kafka but within my existing Redis cluster." Activity feeds, audit logs, event sourcing at modest scale.

---

### Bitmaps

Not a distinct Redis type — Strings accessed with bit-level commands. A 512MB string can represent 4 billion bits.

**Key commands:**
```redis
SETBIT key offset value         # set bit at offset to 0 or 1
GETBIT key offset               # get bit at offset
BITCOUNT key [start end]        # count set bits
BITPOS key bit [start end]      # position of first 0 or 1
BITOP AND|OR|XOR|NOT destkey key [key ...]  # bitwise operations
```

**Use cases:**
- **Daily Active Users (DAU):** One bitmap per day, user_id as bit offset. `SETBIT dau:2024-01-15 42 1` = user 42 was active. `BITCOUNT dau:2024-01-15` = total DAU.
  - For 100M users: 100M bits = 12.5MB per day. Extremely space-efficient.
- **Feature flag per user:** `SETBIT feature:beta_ui user_id 1` — efficiently track which users have a feature enabled.
- **Attendance tracking:** `SETBIT attendance:event:xyz user_id 1`
- **Set membership with space efficiency:** If your keys are dense integers, bitmaps beat Sets massively. A Set of 100M integer members uses ~6.4GB. A Bitmap needs 12.5MB.

**HyperLogLog (related):**
`PFADD` / `PFCOUNT` — probabilistic approximate cardinality counting. Use ~12KB of memory to count unique elements with <1% error. Perfect for "how many unique IPs visited this URL today" where exact count isn't needed.

---

## 2. Redis Patterns

### Session Storage

Redis is the standard choice for distributed session storage because:
- Fast reads (~1ms) vs database sessions (~10ms)
- Built-in TTL for automatic session expiry
- Shared across all app instances (unlike in-memory sessions)
- HSET allows partial session field updates without serializing the entire session

```redis
# Store session as hash
HSET session:abc123 
    user_id 42 
    email "user@example.com" 
    role "admin" 
    created_at 1705123456 
    last_seen 1705123456
EXPIRE session:abc123 1800   # 30 minute session TTL

# Get specific fields
HGET session:abc123 user_id
HMGET session:abc123 user_id role

# Extend session on activity (sliding TTL)
HSET session:abc123 last_seen 1705125256
EXPIRE session:abc123 1800

# Invalidate (logout)
DEL session:abc123

# Invalidate all sessions for a user (if you track them)
# Store: SET user:42:session_ids [session_abc123, session_def456]
# On password change: DEL all sessions for that user
```

**Session storage considerations:**
- Use `HSET` for structured sessions — can update individual fields without race conditions
- Use `SET` with JSON for simple sessions — single atomic read/write
- Set `maxmemory` and `maxmemory-policy volatile-lru` so old sessions are evicted gracefully
- For JWT-based auth where you need blacklisting: `SET blacklist:token:jwt_jti 1 EX jwt_exp_seconds`

---

### Rate Limiting

Two canonical approaches: Fixed Window and Sliding Window.

**Fixed Window (simple, slightly inaccurate at window boundaries):**
```redis
# Key: ratelimit:{user_id}:{window_start}
# Window = current minute truncated to minute boundary

# Atomic: increment counter and set TTL if key is new
local key = "ratelimit:user:42:1705123440"   # floor to nearest minute
local count = redis.call("INCR", key)
if count == 1 then
    redis.call("EXPIRE", key, 60)
end
if count > limit then
    -- reject
end
```

Problem with fixed window: A user can make 100 requests in the last second of minute 1 and 100 more in the first second of minute 2 — 200 requests in 2 seconds, but both windows allow it.

**Sliding Window with Sorted Set (accurate, slightly more expensive):**
```redis
# Key: ratelimit:{user_id}
# Score = UNIX timestamp (milliseconds)
# Member = unique request ID (or timestamp itself if unique)

-- Lua script for atomic sliding window rate limiting:
local key = KEYS[1]
local now = tonumber(ARGV[1])        -- current timestamp ms
local window = tonumber(ARGV[2])     -- window size ms (e.g., 60000)
local limit = tonumber(ARGV[3])      -- max requests per window
local request_id = ARGV[4]           -- unique ID for this request

-- Remove entries outside the window
redis.call("ZREMRANGEBYSCORE", key, 0, now - window)

-- Count requests in window
local count = redis.call("ZCARD", key)

if count < limit then
    -- Add this request
    redis.call("ZADD", key, now, request_id)
    redis.call("EXPIRE", key, math.ceil(window / 1000) + 1)
    return {1, limit - count - 1}  -- allowed, remaining
else
    return {0, 0}  -- rejected
end
```

**Trade-offs:**
| | Fixed Window | Sliding Window |
|---|---|---|
| Memory | O(1) per user | O(requests in window) per user |
| Accuracy | At boundary: 2× burst | Accurate |
| Speed | O(1) | O(log N) for ZSet ops |
| Implementation | Simple INCR | Lua script + ZSet |

For most APIs: fixed window is sufficient and simpler. For strict rate limiting (financial, SMS sending), use sliding window.

---

### Distributed Lock

A distributed lock ensures only one process/thread can perform an operation at a time across multiple machines.

**Basic lock with SETNX:**
```redis
-- Acquire lock: SET key value NX EX timeout
-- NX: only set if not exists (atomic lock acquisition)
-- EX: expiry prevents deadlocks if lock holder crashes

SET lock:order:42 "worker-abc123" NX EX 30
-- Returns "OK" if acquired, nil if already locked

-- Release lock (must be owner):
-- Use Lua for atomic check-and-delete
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
```

**Why store a unique value in the lock?**
Without a unique value, any process could delete any lock. Imagine:
1. Process A acquires lock, starts work
2. Process A takes too long — lock expires
3. Process B acquires the lock
4. Process A finishes — calls DEL on the lock key — deletes Process B's lock!

With a unique token (UUID per lock acquisition), Process A can only delete the lock if it still holds it (token matches).

**Limitations of single-node lock:**
If Redis itself crashes and restarts, all locks are lost. If Redis has async replication and the primary crashes before replicating the lock to a standby, the standby won't know the lock exists — a second process could acquire it.

**Redlock Algorithm:**
Proposed by Salvatore Sanfilippo for multi-node locking across N independent Redis instances (typically 5).

```
For N=5 Redis instances:

1. Get current timestamp T1 (ms)
2. Try to acquire lock on ALL N instances with same key and unique token.
   Use a short timeout (e.g., 10ms) per instance so a slow instance doesn't block.
3. Count successful acquisitions.
4. Check: lock is valid if:
   - More than N/2 instances (quorum, e.g., 3 out of 5) acquired the lock
   - Total elapsed time (now - T1) < lock expiry
5. If valid: lock acquired. Effective TTL = lock_expiry - elapsed_time
6. If not valid: release lock on all instances and retry with backoff

Release:
- Send DEL with Lua check-token script to ALL instances (even ones that failed)
```

**Redlock controversy:** Martin Kleppmann wrote a [detailed critique](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html) arguing that Redlock doesn't guarantee safety under certain failure scenarios (clock drift, process pauses). Antirez (Redis creator) [responded](http://antirez.com/news/101). The consensus: Redlock is fine for most practical use cases but is not suitable for absolute correctness requirements (use ZooKeeper/etcd for that).

---

### Pub/Sub vs Streams

**Pub/Sub:**
```redis
-- Subscriber side
SUBSCRIBE channel:events            # subscribe to a channel
PSUBSCRIBE events:*                  # pattern subscribe

-- Publisher side  
PUBLISH channel:events "message"    # broadcast to all subscribers
```

**Key characteristics:**
- **Fire and forget:** If no subscriber is listening when a message is published, the message is **lost**
- **Not persisted:** Messages are not stored in Redis — only in-flight delivery
- **No consumer groups:** All subscribers receive all messages (broadcast)
- **No acknowledgment:** No way to confirm a subscriber received and processed a message

**Use Pub/Sub for:** Real-time notifications where message loss is acceptable (chat notifications, live score updates, dashboard refresh triggers, cache invalidation signals).

**Use Streams for:** Any scenario requiring durability, at-least-once delivery, consumer groups, or message replay.

---

### Job Queue

**Simple queue (List-based):**
```redis
-- Producer
RPUSH queue:email_jobs '{"to":"user@example.com","template":"welcome"}'

-- Consumer (blocking, waits up to 30s)
BLPOP queue:email_jobs 30
-- Returns: [queue_name, job_payload]
```

**Priority queue (ZSet-based):**
```redis
-- Higher score = higher priority
ZADD queue:tasks 10 "task:send-invoice"   -- priority 10
ZADD queue:tasks 5  "task:cleanup-logs"   -- priority 5
ZADD queue:tasks 100 "task:process-payment" -- urgent

-- Consumer: pop highest priority task
ZPOPMAX queue:tasks
```

**Reliable queue (Streams-based — for production):**
```redis
-- Producer
XADD job_queue * type email payload '{"to":"user@example.com"}'

-- Consumer group setup (once)
XGROUP CREATE job_queue workers $ MKSTREAM

-- Consumer reads
XREADGROUP GROUP workers worker-1 COUNT 10 BLOCK 30000 STREAMS job_queue >
-- ">" means: give me messages not yet delivered to any consumer in this group

-- Acknowledge after processing
XACK job_queue workers entry_id_123

-- Handle stale/unacked messages (worker crashed mid-processing)
XPENDING job_queue workers - + 10   -- list pending entries
XCLAIM job_queue workers worker-2 60000 entry_id_123  -- steal ownership after 60s
```

For production job queues, consider battle-tested libraries built on Redis: **BullMQ** (Node.js), **Celery+Redis** (Python), **Asynq** (Go) — they handle retries, dead-letter queues, delayed jobs, and monitoring on top of Redis primitives.

---

### Leaderboard

Sorted Sets are purpose-built for leaderboards. O(log N) inserts and O(log N + K) range queries.

```redis
-- Add/update player score (GT: only update if new score is higher)
ZADD leaderboard GT 1500 "player:42"
ZADD leaderboard GT 2300 "player:99"
ZADD leaderboard GT 1800 "player:7"

-- Top 10 players (descending score)
ZREVRANGE leaderboard 0 9 WITHSCORES
-- Returns: ["player:99", "2300", "player:7", "1800", "player:42", "1500"]

-- Player's rank (0-based, descending)
ZREVRANK leaderboard "player:42"
-- Returns: 2 (3rd place)

-- Players around a specific player (±2 positions)
local rank = ZREVRANK leaderboard "player:42"  -- get rank first
ZREVRANGE leaderboard (rank-2) (rank+2) WITHSCORES

-- Score of a specific player
ZSCORE leaderboard "player:42"

-- Top players in a score range (e.g., scores between 1000 and 2000)
ZRANGEBYSCORE leaderboard 1000 2000 WITHSCORES

-- Increment score (atomic)
ZINCRBY leaderboard 100 "player:42"  -- player:42 gained 100 points

-- Total number of players
ZCARD leaderboard
```

**Seasonal/daily leaderboards:**
```redis
-- Separate leaderboard per time period
ZADD leaderboard:2024-01 GT 1500 "player:42"
ZADD leaderboard:2024-01-15 GT 1500 "player:42"

-- Expire daily leaderboards automatically
EXPIRE leaderboard:2024-01-15 604800  -- delete after 7 days
```

---

### Geospatial

Redis Geo commands store location data using Sorted Sets internally (encoding lat/lon as a geohash score).

```redis
-- Add locations
GEOADD restaurants:nyc 
    -74.0060 40.7128 "resto:pizza_palace"
    -73.9857 40.7580 "resto:sushi_bar"
    -74.0090 40.7061 "resto:burger_joint"

-- Distance between two locations
GEODIST restaurants:nyc "resto:pizza_palace" "resto:sushi_bar" km
-- Returns: "5.2341" km

-- Get coordinates of a member
GEOPOS restaurants:nyc "resto:pizza_palace"

-- Find restaurants within 2km of a point (Redis 6.2+)
GEOSEARCH restaurants:nyc 
    FROMMEMBER "resto:pizza_palace" 
    BYRADIUS 2 km 
    ASC 
    COUNT 5 
    WITHCOORD WITHDIST

-- Legacy (before Redis 6.2):
GEORADIUS restaurants:nyc -74.0060 40.7128 2 km ASC COUNT 5 WITHCOORD WITHDIST
```

**Use cases:** Restaurant/driver/store finder, geo-fencing, "find users near me," delivery radius checks.

**Precision:** Redis geospatial uses 52-bit geohash, giving ~0.6m accuracy at the equator — sufficient for most location-based features.

---

### Bloom Filter (Redis Bloom Module)

A Bloom filter is a probabilistic data structure that can definitively say "does NOT exist" but may have false positives ("might exist"). Space-efficient for large datasets.

```redis
-- Requires RedisBloom module (bundled with Redis Stack)

-- Create filter: expected 1M items, 1% false positive rate
BF.RESERVE blocked_users 0.01 1000000

-- Add items
BF.ADD blocked_users "user:42"
BF.MADD blocked_users "user:99" "user:100" "user:7"

-- Check existence
BF.EXISTS blocked_users "user:42"     -- 1 (probably exists)
BF.EXISTS blocked_users "user:999"    -- 0 (definitely does NOT exist)
BF.MEXISTS blocked_users "user:42" "user:999"

-- Reserve with scaling (auto-scales when full)
BF.RESERVE scaled_filter 0.01 100000 EXPANSION 2
```

**Use cases:**
- **Cache penetration defense:** Before querying cache/DB, check if the ID exists in the Bloom filter. If not — immediately return 404. No cache query, no DB query.
- **Duplicate request deduplication:** Have we already processed payment request ID X?
- **Email spam filtering:** Is this email address in the known-bad list?
- **URL shortener:** Is this short code already taken?

**Trade-off:** False positive rate vs memory. 1M items at 1% FPR ≈ 1.2MB. At 0.1% FPR ≈ 1.8MB. Increasing precision requires more memory.

---

## 3. Redis Internals

### Single-Threaded Command Processing

Redis processes commands in a **single-threaded event loop**. One command at a time, no parallel execution.

**Why single-threaded?**
- No mutex locking for data structures — eliminates lock contention overhead
- Cache-friendly access patterns — no context switching between threads
- Simplicity — atomic operations at the command level are guaranteed
- Network I/O bound, not CPU bound — for most workloads, the bottleneck is network throughput, not CPU

**Why is it still fast (100K-1M ops/sec)?**
- All data in RAM: memory access is nanoseconds vs microseconds/milliseconds for disk
- Efficient data structures (skip lists, hash tables, compressed encodings)
- Non-blocking I/O via `epoll`/`kqueue` — Redis handles thousands of connections without blocking
- Minimal per-command overhead — INCR is ~1μs

**Redis 6.0+ threaded I/O:**
Redis 6 introduced optional threaded I/O — reading from and writing to sockets is parallelized across multiple threads. The command processing loop is still single-threaded, but reading/parsing requests and writing responses can happen concurrently. Enabled via `io-threads` config. Provides ~2× throughput improvement for bandwidth-heavy workloads.

**Redis 7.0 multi-threaded for background tasks:**
BGSAVE, AOF rewrite, and other background work have always been done in forked child processes/separate threads. This didn't change in Redis 7.

**Implications for use:**
- Long-running commands (KEYS *, SORT on large sets, LRANGE on huge lists) **block all other clients** during execution
- Avoid using `KEYS *` in production — use `SCAN` instead
- Lua scripts execute atomically — keep them short
- Use pipelining to batch multiple commands into one network round-trip

---

### Persistence: RDB vs AOF

**RDB (Redis Database Snapshot):**
- Takes periodic point-in-time snapshots of the dataset to disk
- A child process is forked (copy-on-write) to write the snapshot — minimal main thread impact
- File is compact binary format — fast to load on restart
- Configured with SAVE conditions:
  ```
  save 3600 1      # save if at least 1 key changed in 1 hour
  save 300 100     # save if at least 100 keys changed in 5 min
  save 60 10000    # save if at least 10000 keys changed in 1 min
  ```
- `BGSAVE` — trigger manual background save
- `LASTSAVE` — Unix timestamp of last save

**RDB pros:** Fast startup (load one file), compact storage, minimal runtime overhead, great for backups.
**RDB cons:** Risk of data loss between snapshots. If Redis crashes 45 minutes into a 1-hour snapshot interval, you lose up to 45 minutes of writes.

**AOF (Append-Only File):**
- Every write command is logged to an append-only file as it executes
- On restart, Redis replays the AOF to reconstruct the dataset
- Three fsync policies:
  - `always` — fsync after every command. Slowest (~1/2 throughput), no data loss
  - `everysec` — fsync every 1 second (default). Fast, lose at most 1 second of data
  - `no` — let OS decide when to fsync. Fastest, may lose ~30s of data on crash

**AOF pros:** Durability (at most 1 second of data loss with `everysec`), append-only is disk-friendly, human-readable file for debugging.
**AOF cons:** Larger file size over time (AOF rewrite compacts it). Slower startup (must replay all commands). Slightly higher runtime I/O.

**AOF rewrite:** `BGREWRITEAOF` or automatic trigger — compacts the AOF by replacing historical commands with the minimal set needed to reconstruct current state.

**RDB + AOF (recommended for production):**
Use both. RDB provides fast restarts and backups. AOF provides durability. On restart, Redis prefers the AOF (more up-to-date).

```
# redis.conf — recommended production settings
save 3600 1
save 300 100
save 60 10000

appendonly yes
appendfsync everysec
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Disable RDB if pure AOF is desired (AOF provides better durability)
# save ""
```

---

### Redis Cluster vs Sentinel

**Redis Sentinel (HA for single master):**
- Monitors a primary + replicas
- Automatically promotes a replica to primary if the primary fails
- Provides service discovery — clients query Sentinel for the current primary address
- Uses Raft-like consensus (majority of Sentinels must agree on a failure)
- Minimum: 3 Sentinel instances for reliable quorum

```
   [Sentinel 1] [Sentinel 2] [Sentinel 3]
         ↕             ↕             ↕
   [Primary] ──replicate──► [Replica 1]
                      └──► [Replica 2]
```

Sentinel handles HA (failover) but does NOT handle scaling — all data still lives on a single primary. Use Sentinel when your dataset fits on one machine.

**Redis Cluster (HA + horizontal scaling):**
- Shards data across 16,384 hash slots
- Each node owns a subset of slots
- No external proxy needed — clients use the Cluster protocol (MOVED redirects)
- Data is automatically distributed across nodes
- Minimum: 6 nodes for production (3 primaries + 3 replicas)

```
Slot 0-5460:    Primary A ──► Replica A'
Slot 5461-10922: Primary B ──► Replica B'
Slot 10923-16383: Primary C ──► Replica C'
```

Hash slot calculation: `CRC16(key) % 16384` → determines which slot and therefore which node.

**Hash tags:** Force related keys to the same slot: `{user:42}:orders` and `{user:42}:profile` both hash the `{user:42}` tag, landing on the same slot. Required for multi-key commands (MGET, transactions) across related keys.

**Cluster limitations:**
- Multi-key commands require all keys to be in the same slot (use hash tags)
- Lua scripts must operate on keys in the same slot
- Transactions (MULTI/EXEC) restricted to keys in the same slot

Use Cluster when: dataset exceeds single-node memory, or write throughput exceeds single-node capacity.

---

### Eviction Policies

When Redis hits `maxmemory`, it must evict keys according to the configured policy:

| Policy | What it does | Best for |
|---|---|---|
| `noeviction` | Return error on writes when full | Authoritative data (don't lose anything) |
| `allkeys-lru` | Evict least recently used key from all keys | Pure cache — evict cold data |
| `allkeys-lfu` | Evict least frequently used key from all keys | Cache with skewed access patterns |
| `allkeys-random` | Evict a random key from all keys | Not recommended |
| `volatile-lru` | Evict LRU key from keys WITH an expiry set | Mixed: cache + durable data |
| `volatile-lfu` | Evict LFU key from keys WITH an expiry set | Same as volatile-lru but frequency-based |
| `volatile-random` | Evict random key from keys with expiry | Not recommended |
| `volatile-ttl` | Evict key with shortest remaining TTL | Expire-aware cache |

**Decision guide:**
- **Pure cache (only cached data in Redis):** Use `allkeys-lru` or `allkeys-lfu`. LFU is better for keys with variable access frequency (some keys hit 1000×/sec, others 1×/min).
- **Mixed (cache + sessions + durable counters):** Use `volatile-lru` — only evicts keys that have a TTL set (your cache keys), never touches keys without TTL (your durable counters/session keys).
- **Mission-critical data in Redis:** Use `noeviction` with monitoring and memory headroom — you'll get errors rather than silent data loss.

**LRU vs LFU:**
- LRU: recently used items are kept. Good for "recent" access patterns.
- LFU: frequently used items are kept. Better when some items are very hot (accessed thousands of times) and others are one-shots.
- Redis 4.0+ implements approximated LFU using a counter with decay — fast and memory-efficient.

---

### Memory Management

Redis uses `jemalloc` as its memory allocator by default — it's more efficient than `glibc malloc` for the allocation patterns Redis exhibits (many small, fixed-size allocations).

**Memory optimization techniques:**
- Use appropriate data structures (hashes use `ziplist`/`listpack` encoding for small sizes)
- Tune `hash-max-listpack-entries`, `hash-max-listpack-value`, `zset-max-listpack-entries`
- Store serialized data (MessagePack is ~30% smaller than JSON)
- Use integer encoding — Redis automatically uses a more compact encoding for integer values
- Avoid very short-lived keys if creation rate is high (allocation overhead)

**Memory fragmentation:**
Redis can fragment memory over time (allocate 100MB, use 70MB, OS sees 100MB allocated). Fragmentation ratio > 1.5 is concerning. Redis 4.0+ supports `MEMORY PURGE` (jemalloc `mallopt`) and `activedefrag` (active defragmentation) to reclaim fragmented memory online.

```redis
INFO memory
-- mem_allocator: jemalloc-5.3.0
-- used_memory: 1073741824       -- 1GB logical memory Redis uses
-- used_memory_rss: 1258291200   -- 1.2GB physical memory OS sees
-- mem_fragmentation_ratio: 1.17 -- ok (< 1.5)
```

---

## 4. Redis Production Considerations

### Connection Pooling

**Never create a new Redis connection per request.** TCP connection setup takes ~1ms — longer than the Redis operation itself for simple commands. Always use a connection pool.

```go
// go-redis: built-in pool
rdb := redis.NewClient(&redis.Options{
    Addr:         "localhost:6379",
    PoolSize:     20,   // max connections
    MinIdleConns: 5,    // keep 5 connections warm
    PoolTimeout:  3 * time.Second,
    DialTimeout:  1 * time.Second,
    ReadTimeout:  2 * time.Second,
    WriteTimeout: 2 * time.Second,
})
```

### Key Naming Conventions

Use structured key names: `{prefix}:{type}:{identifier}`

```
user:session:{session_id}
user:profile:{user_id}
user:orders:{user_id}:{page}
product:cache:{product_id}
ratelimit:api:{user_id}:{window}
lock:{resource_name}:{resource_id}
queue:{queue_name}
leaderboard:{game}:{season}
```

**Rules:**
- Use colon (`:`) as separator — conventional and easy to read
- Avoid spaces and special characters in key names
- Keep key names short but descriptive — key names consume memory too
- Add environment prefix in non-production: `dev:user:42`, `staging:user:42`

### Avoiding `KEYS *` in Production

`KEYS *` is O(N) and **blocks all other clients** for its entire duration. On a 10M-key Redis instance, this can take seconds.

**Always use `SCAN`:**
```redis
-- SCAN is O(1) per call, iterates in chunks
SCAN 0 MATCH "user:*" COUNT 100
-- Returns: [next_cursor, [matching_keys...]]
-- When next_cursor returns 0, iteration is complete

-- Python example:
for key in redis.scan_iter("user:*", count=100):
    print(key)
```

### Monitoring

```redis
INFO all                          -- comprehensive stats
INFO memory                       -- memory usage
INFO stats                        -- command stats, connections
INFO replication                  -- replication status
INFO clients                      -- connected clients
INFO keyspace                     -- key counts per DB

SLOWLOG GET 10                    -- last 10 slow commands (> slowlog-log-slower-than)
SLOWLOG RESET

MONITOR                           -- real-time command stream (dev only! huge overhead)
CLIENT LIST                       -- list connected clients

MEMORY USAGE key                  -- memory used by a specific key
MEMORY DOCTOR                     -- recommendations
DEBUG SLEEP 5                     -- simulate blocking (dev use only)
```

**Key metrics to alert on:**
- `used_memory` vs `maxmemory` — memory headroom
- `rejected_connections` — client connection exhaustion
- `blocked_clients` — clients waiting on BLPOP (expected) or locks
- `keyspace_misses` / (`keyspace_hits` + `keyspace_misses`) = cache miss rate
- `rdb_last_bgsave_status` — last save success/failure
- `aof_last_write_status` — last AOF write status
- `master_link_status` — replica connection to primary
- `connected_slaves` — number of connected replicas

---

## 5. Implementation Examples

### Go (go-redis): Distributed Lock + Rate Limiter + Leaderboard

```go
package redis_patterns

import (
    "context"
    "errors"
    "fmt"
    "math/rand"
    "time"

    "github.com/redis/go-redis/v9"
)

var ErrLockNotAcquired = errors.New("lock not acquired")
var ErrLockNotOwned    = errors.New("cannot release lock: not the owner")

// ─── Distributed Lock ─────────────────────────────────────────────────────────

type DistributedLock struct {
    client *redis.Client
    key    string
    token  string
    ttl    time.Duration
}

// NewLock creates a lock handle. Call Acquire() to actually acquire it.
func NewLock(client *redis.Client, resource string, ttl time.Duration) *DistributedLock {
    return &DistributedLock{
        client: client,
        key:    fmt.Sprintf("lock:%s", resource),
        token:  fmt.Sprintf("%d", rand.Int63()), // unique per acquisition attempt
        ttl:    ttl,
    }
}

// Acquire tries to acquire the lock. Returns ErrLockNotAcquired if already held.
func (l *DistributedLock) Acquire(ctx context.Context) error {
    ok, err := l.client.SetNX(ctx, l.key, l.token, l.ttl).Result()
    if err != nil {
        return fmt.Errorf("redis setnx: %w", err)
    }
    if !ok {
        return ErrLockNotAcquired
    }
    return nil
}

// AcquireWithRetry tries to acquire the lock with exponential backoff.
func (l *DistributedLock) AcquireWithRetry(ctx context.Context, maxAttempts int) error {
    for attempt := 0; attempt < maxAttempts; attempt++ {
        if err := l.Acquire(ctx); err == nil {
            return nil
        } else if !errors.Is(err, ErrLockNotAcquired) {
            return err
        }
        // Exponential backoff with jitter
        backoff := time.Duration(50*(1<<attempt)) * time.Millisecond
        jitter := time.Duration(rand.Int63n(int64(backoff / 4)))
        select {
        case <-time.After(backoff + jitter):
        case <-ctx.Done():
            return ctx.Err()
        }
    }
    return ErrLockNotAcquired
}

// releaseScript: atomically check token and delete — prevents releasing another owner's lock
var releaseScript = redis.NewScript(`
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    else
        return 0
    end
`)

// Release releases the lock. Returns ErrLockNotOwned if this instance no longer owns it.
func (l *DistributedLock) Release(ctx context.Context) error {
    result, err := releaseScript.Run(ctx, l.client, []string{l.key}, l.token).Int()
    if err != nil {
        return fmt.Errorf("lock release: %w", err)
    }
    if result == 0 {
        return ErrLockNotOwned // lock expired or stolen
    }
    return nil
}

// WithLock acquires lock, runs fn, releases lock.
func WithLock(ctx context.Context, client *redis.Client, resource string, ttl time.Duration, fn func(ctx context.Context) error) error {
    lock := NewLock(client, resource, ttl)
    if err := lock.AcquireWithRetry(ctx, 3); err != nil {
        return fmt.Errorf("acquire lock for %s: %w", resource, err)
    }
    defer lock.Release(ctx) // best-effort release
    return fn(ctx)
}

// ─── Sliding Window Rate Limiter ──────────────────────────────────────────────

var rateLimitScript = redis.NewScript(`
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local request_id = ARGV[4]

    -- Remove expired entries
    redis.call("ZREMRANGEBYSCORE", key, 0, now - window)

    -- Count current requests in window
    local count = tonumber(redis.call("ZCARD", key))

    if count < limit then
        -- Add this request with current timestamp as score
        redis.call("ZADD", key, now, request_id)
        local ttl_seconds = math.ceil(window / 1000) + 1
        redis.call("EXPIRE", key, ttl_seconds)
        return {1, limit - count - 1}  -- {allowed, remaining}
    else
        return {0, 0}  -- {blocked, remaining}
    end
`)

type RateLimiter struct {
    client     *redis.Client
    limit      int
    windowMs   int64  // window size in milliseconds
}

type RateLimitResult struct {
    Allowed   bool
    Remaining int
}

func NewRateLimiter(client *redis.Client, limit int, window time.Duration) *RateLimiter {
    return &RateLimiter{
        client:   client,
        limit:    limit,
        windowMs: window.Milliseconds(),
    }
}

func (r *RateLimiter) Allow(ctx context.Context, identifier string) (RateLimitResult, error) {
    key := fmt.Sprintf("ratelimit:%s", identifier)
    nowMs := time.Now().UnixMilli()
    requestID := fmt.Sprintf("%d-%d", nowMs, rand.Int63())

    result, err := rateLimitScript.Run(ctx, r.client,
        []string{key},
        nowMs, r.windowMs, r.limit, requestID,
    ).Int64Slice()
    if err != nil {
        return RateLimitResult{Allowed: true}, err // fail open on Redis error
    }

    return RateLimitResult{
        Allowed:   result[0] == 1,
        Remaining: int(result[1]),
    }, nil
}

// ─── Leaderboard ──────────────────────────────────────────────────────────────

type Leaderboard struct {
    client *redis.Client
    key    string
}

func NewLeaderboard(client *redis.Client, name string) *Leaderboard {
    return &Leaderboard{client: client, key: "leaderboard:" + name}
}

type LeaderboardEntry struct {
    PlayerID string
    Score    float64
    Rank     int64
}

func (lb *Leaderboard) AddScore(ctx context.Context, playerID string, score float64) error {
    return lb.client.ZAdd(ctx, lb.key, redis.Z{
        Score:  score,
        Member: playerID,
    }).Err()
}

func (lb *Leaderboard) IncrScore(ctx context.Context, playerID string, delta float64) (float64, error) {
    return lb.client.ZIncrBy(ctx, lb.key, delta, playerID).Result()
}

func (lb *Leaderboard) TopN(ctx context.Context, n int) ([]LeaderboardEntry, error) {
    results, err := lb.client.ZRevRangeWithScores(ctx, lb.key, 0, int64(n-1)).Result()
    if err != nil {
        return nil, err
    }

    entries := make([]LeaderboardEntry, len(results))
    for i, z := range results {
        entries[i] = LeaderboardEntry{
            PlayerID: z.Member.(string),
            Score:    z.Score,
            Rank:     int64(i + 1),
        }
    }
    return entries, nil
}

func (lb *Leaderboard) GetRank(ctx context.Context, playerID string) (int64, float64, error) {
    rank, err := lb.client.ZRevRank(ctx, lb.key, playerID).Result()
    if err != nil {
        return 0, 0, err
    }
    score, err := lb.client.ZScore(ctx, lb.key, playerID).Result()
    return rank + 1, score, err // 1-based rank
}

// ─── Session Store ────────────────────────────────────────────────────────────

type SessionStore struct {
    client     *redis.Client
    sessionTTL time.Duration
}

func NewSessionStore(client *redis.Client, ttl time.Duration) *SessionStore {
    return &SessionStore{client: client, sessionTTL: ttl}
}

type Session struct {
    UserID    string
    Email     string
    Role      string
    CreatedAt int64
    LastSeen  int64
}

func (s *SessionStore) Create(ctx context.Context, sessionID string, sess Session) error {
    key := "user:session:" + sessionID
    pipe := s.client.Pipeline()
    pipe.HSet(ctx, key,
        "user_id", sess.UserID,
        "email", sess.Email,
        "role", sess.Role,
        "created_at", sess.CreatedAt,
        "last_seen", sess.LastSeen,
    )
    pipe.Expire(ctx, key, s.sessionTTL)
    _, err := pipe.Exec(ctx)
    return err
}

func (s *SessionStore) Get(ctx context.Context, sessionID string) (*Session, error) {
    key := "user:session:" + sessionID
    result, err := s.client.HGetAll(ctx, key).Result()
    if err != nil {
        return nil, err
    }
    if len(result) == 0 {
        return nil, nil // session not found / expired
    }

    var sess Session
    sess.UserID = result["user_id"]
    sess.Email = result["email"]
    sess.Role = result["role"]
    return &sess, nil
}

func (s *SessionStore) Refresh(ctx context.Context, sessionID string) error {
    key := "user:session:" + sessionID
    pipe := s.client.Pipeline()
    pipe.HSet(ctx, key, "last_seen", time.Now().Unix())
    pipe.Expire(ctx, key, s.sessionTTL) // reset sliding TTL
    _, err := pipe.Exec(ctx)
    return err
}

func (s *SessionStore) Delete(ctx context.Context, sessionID string) error {
    return s.client.Del(ctx, "user:session:"+sessionID).Err()
}
```

---

### Node.js (ioredis): Rate Limiter + Distributed Lock + Leaderboard

```javascript
const Redis = require('ioredis');

const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  retryStrategy: (times) => Math.min(times * 100, 3000),
  lazyConnect: false,
  keepAlive: 10000,
  maxRetriesPerRequest: 3,
});

// ─── Distributed Lock ──────────────────────────────────────────────────────────

class DistributedLock {
  constructor(redis, resource, ttlMs = 30000) {
    this.redis = redis;
    this.key = `lock:${resource}`;
    this.token = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    this.ttlMs = ttlMs;
  }

  async acquire() {
    const result = await this.redis.set(this.key, this.token, 'NX', 'PX', this.ttlMs);
    return result === 'OK';
  }

  async acquireWithRetry(maxAttempts = 3, baseDelayMs = 100) {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      if (await this.acquire()) return true;
      const delay = baseDelayMs * Math.pow(2, attempt) + Math.random() * baseDelayMs;
      await new Promise((r) => setTimeout(r, delay));
    }
    return false;
  }

  async release() {
    // Atomic check-and-delete via Lua
    const script = `
      if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
      else
        return 0
      end
    `;
    return this.redis.eval(script, 1, this.key, this.token);
  }

  async extend(additionalTtlMs) {
    const script = `
      if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("PEXPIRE", KEYS[1], ARGV[2])
      else
        return 0
      end
    `;
    return this.redis.eval(script, 1, this.key, this.token, additionalTtlMs);
  }
}

async function withLock(redis, resource, ttlMs, fn) {
  const lock = new DistributedLock(redis, resource, ttlMs);
  const acquired = await lock.acquireWithRetry();
  if (!acquired) throw new Error(`Could not acquire lock for ${resource}`);
  try {
    return await fn();
  } finally {
    await lock.release().catch((err) => console.warn('Lock release error:', err));
  }
}

// ─── Rate Limiter ──────────────────────────────────────────────────────────────

const slidingWindowScript = `
  local key = KEYS[1]
  local now = tonumber(ARGV[1])
  local window = tonumber(ARGV[2])
  local limit = tonumber(ARGV[3])
  local request_id = ARGV[4]

  redis.call("ZREMRANGEBYSCORE", key, 0, now - window)
  local count = tonumber(redis.call("ZCARD", key))

  if count < limit then
    redis.call("ZADD", key, now, request_id)
    redis.call("EXPIRE", key, math.ceil(window / 1000) + 1)
    return {1, limit - count - 1}
  else
    return {0, 0}
  end
`;

async function rateLimitCheck(redis, identifier, limitPerWindow, windowMs) {
  const key = `ratelimit:${identifier}`;
  const now = Date.now();
  const requestId = `${now}-${Math.random().toString(36).slice(2)}`;

  const [allowed, remaining] = await redis.eval(
    slidingWindowScript, 1, key, now, windowMs, limitPerWindow, requestId
  );

  return {
    allowed: allowed === 1,
    remaining: parseInt(remaining),
    limit: limitPerWindow,
    resetMs: now + windowMs,
  };
}

// Express rate limit middleware
function createRateLimitMiddleware(limit = 100, windowSeconds = 60) {
  return async (req, res, next) => {
    const identifier = `${req.ip}:${req.path}`;
    try {
      const result = await rateLimitCheck(redis, identifier, limit, windowSeconds * 1000);
      res.set({
        'X-RateLimit-Limit': result.limit,
        'X-RateLimit-Remaining': result.remaining,
        'X-RateLimit-Reset': new Date(result.resetMs).toISOString(),
      });
      if (!result.allowed) {
        return res.status(429).json({
          error: 'Too Many Requests',
          retryAfter: Math.ceil(windowSeconds),
        });
      }
    } catch (err) {
      console.warn('Rate limit error (failing open):', err.message);
      // Fail open: Redis down shouldn't block all API traffic
    }
    next();
  };
}

// ─── Leaderboard ──────────────────────────────────────────────────────────────

class Leaderboard {
  constructor(redis, name) {
    this.redis = redis;
    this.key = `leaderboard:${name}`;
  }

  async addScore(playerId, score) {
    return this.redis.zadd(this.key, 'GT', score, playerId);
  }

  async incrementScore(playerId, delta) {
    return parseFloat(await this.redis.zincrby(this.key, delta, playerId));
  }

  async getTopN(n = 10) {
    const results = await this.redis.zrevrange(this.key, 0, n - 1, 'WITHSCORES');
    const entries = [];
    for (let i = 0; i < results.length; i += 2) {
      entries.push({
        rank: i / 2 + 1,
        playerId: results[i],
        score: parseFloat(results[i + 1]),
      });
    }
    return entries;
  }

  async getPlayerRank(playerId) {
    const [rank, score] = await Promise.all([
      this.redis.zrevrank(this.key, playerId),
      this.redis.zscore(this.key, playerId),
    ]);
    return {
      rank: rank !== null ? rank + 1 : null,
      score: score ? parseFloat(score) : null,
    };
  }

  async getAroundPlayer(playerId, radius = 2) {
    const rank = await this.redis.zrevrank(this.key, playerId);
    if (rank === null) return [];
    const start = Math.max(0, rank - radius);
    const stop = rank + radius;
    const results = await this.redis.zrevrange(this.key, start, stop, 'WITHSCORES');
    const entries = [];
    for (let i = 0; i < results.length; i += 2) {
      entries.push({
        rank: start + i / 2 + 1,
        playerId: results[i],
        score: parseFloat(results[i + 1]),
        isCurrentPlayer: results[i] === playerId,
      });
    }
    return entries;
  }
}

// ─── Express app wiring ────────────────────────────────────────────────────────

const express = require('express');
const app = express();
app.use(express.json());

const leaderboard = new Leaderboard(redis, 'global');

app.get('/leaderboard/top', async (req, res) => {
  const top = await leaderboard.getTopN(10);
  res.json(top);
});

app.post('/score', createRateLimitMiddleware(60, 60), async (req, res) => {
  const { playerId, score } = req.body;
  await withLock(redis, `player:${playerId}:score`, 5000, async () => {
    await leaderboard.addScore(playerId, score);
  });
  const rank = await leaderboard.getPlayerRank(playerId);
  res.json(rank);
});
```

---

### Python (redis-py): Session + Rate Limiter + Leaderboard

```python
from __future__ import annotations
import json
import time
import uuid
import random
from dataclasses import dataclass, asdict
from typing import Optional
from redis.asyncio import Redis
from redis.asyncio.lock import Lock as RedisLock
from fastapi import FastAPI, HTTPException, Request, Depends
import logging

logger = logging.getLogger(__name__)

# ─── Redis client setup ────────────────────────────────────────────────────────

async def get_redis() -> Redis:
    return Redis.from_url(
        "redis://localhost:6379",
        decode_responses=True,
        socket_timeout=2.0,
        socket_connect_timeout=2.0,
        retry_on_timeout=True,
        health_check_interval=30,
    )

# ─── Session Store ─────────────────────────────────────────────────────────────

@dataclass
class SessionData:
    user_id: str
    email: str
    role: str
    created_at: float = 0.0
    last_seen: float = 0.0

class SessionStore:
    SESSION_TTL = 1800  # 30 minutes

    def __init__(self, redis: Redis):
        self.redis = redis

    def _key(self, session_id: str) -> str:
        return f"user:session:{session_id}"

    async def create(self, user_id: str, email: str, role: str) -> str:
        session_id = str(uuid.uuid4())
        now = time.time()
        key = self._key(session_id)

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping={
                "user_id": user_id,
                "email": email,
                "role": role,
                "created_at": str(now),
                "last_seen": str(now),
            })
            pipe.expire(key, self.SESSION_TTL)
            await pipe.execute()

        return session_id

    async def get(self, session_id: str) -> Optional[SessionData]:
        data = await self.redis.hgetall(self._key(session_id))
        if not data:
            return None
        return SessionData(
            user_id=data["user_id"],
            email=data["email"],
            role=data["role"],
            created_at=float(data.get("created_at", 0)),
            last_seen=float(data.get("last_seen", 0)),
        )

    async def refresh(self, session_id: str) -> bool:
        key = self._key(session_id)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, "last_seen", str(time.time()))
            pipe.expire(key, self.SESSION_TTL)  # sliding TTL
            results = await pipe.execute()
        return results[1] == 1  # EXPIRE returned 1 = key exists

    async def delete(self, session_id: str) -> None:
        await self.redis.delete(self._key(session_id))


# ─── Rate Limiter (Sliding Window) ────────────────────────────────────────────

SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local request_id = ARGV[4]

redis.call("ZREMRANGEBYSCORE", key, 0, now - window)
local count = tonumber(redis.call("ZCARD", key))

if count < limit then
    redis.call("ZADD", key, now, request_id)
    redis.call("EXPIRE", key, math.ceil(window / 1000) + 1)
    return {1, limit - count - 1}
else
    return {0, 0}
end
"""

class SlidingWindowRateLimiter:
    def __init__(self, redis: Redis, limit: int, window_seconds: int):
        self.redis = redis
        self.limit = limit
        self.window_ms = window_seconds * 1000
        self._script = redis.register_script(SLIDING_WINDOW_LUA)

    async def check(self, identifier: str) -> tuple[bool, int]:
        """Returns (allowed, remaining)."""
        key = f"ratelimit:{identifier}"
        now_ms = int(time.time() * 1000)
        request_id = f"{now_ms}-{random.randint(0, 999999)}"

        try:
            result = await self._script(
                keys=[key],
                args=[now_ms, self.window_ms, self.limit, request_id]
            )
            allowed, remaining = int(result[0]), int(result[1])
            return bool(allowed), remaining
        except Exception as e:
            logger.warning(f"Rate limit check failed for {identifier}: {e}")
            return True, -1  # fail open


# ─── Leaderboard ───────────────────────────────────────────────────────────────

@dataclass
class LeaderboardEntry:
    rank: int
    player_id: str
    score: float
    is_current_player: bool = False

class LeaderboardService:
    def __init__(self, redis: Redis, name: str):
        self.redis = redis
        self.key = f"leaderboard:{name}"

    async def add_or_update_score(self, player_id: str, score: float) -> None:
        """Use GT flag: only update if new score is higher."""
        await self.redis.zadd(self.key, {player_id: score}, gt=True)

    async def increment_score(self, player_id: str, delta: float) -> float:
        new_score = await self.redis.zincrby(self.key, delta, player_id)
        return float(new_score)

    async def get_top_n(self, n: int = 10) -> list[LeaderboardEntry]:
        results = await self.redis.zrevrange(self.key, 0, n - 1, withscores=True)
        return [
            LeaderboardEntry(rank=i + 1, player_id=member, score=score)
            for i, (member, score) in enumerate(results)
        ]

    async def get_player_rank(self, player_id: str) -> Optional[LeaderboardEntry]:
        rank, score = await asyncio.gather(
            self.redis.zrevrank(self.key, player_id),
            self.redis.zscore(self.key, player_id),
        )
        if rank is None:
            return None
        return LeaderboardEntry(rank=rank + 1, player_id=player_id, score=float(score))

    async def get_around_player(self, player_id: str, radius: int = 2) -> list[LeaderboardEntry]:
        rank = await self.redis.zrevrank(self.key, player_id)
        if rank is None:
            return []
        start = max(0, rank - radius)
        stop = rank + radius
        results = await self.redis.zrevrange(self.key, start, stop, withscores=True)
        return [
            LeaderboardEntry(
                rank=start + i + 1,
                player_id=member,
                score=float(score),
                is_current_player=(member == player_id),
            )
            for i, (member, score) in enumerate(results)
        ]

# ─── FastAPI routes ────────────────────────────────────────────────────────────

import asyncio
app = FastAPI()

async def get_session_store(redis: Redis = Depends(get_redis)) -> SessionStore:
    return SessionStore(redis)

async def get_leaderboard(redis: Redis = Depends(get_redis)) -> LeaderboardService:
    return LeaderboardService(redis, "global")

async def get_rate_limiter(redis: Redis = Depends(get_redis)) -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(redis, limit=100, window_seconds=60)

@app.post("/auth/login")
async def login(
    email: str,
    password: str,
    sessions: SessionStore = Depends(get_session_store),
):
    user = await authenticate_user(email, password)  # your auth logic
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session_id = await sessions.create(user.id, user.email, user.role)
    return {"session_id": session_id}

@app.get("/leaderboard/top")
async def get_top_players(
    n: int = 10,
    request: Request = None,
    lb: LeaderboardService = Depends(get_leaderboard),
    limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
):
    allowed, remaining = await limiter.check(f"ip:{request.client.host}")
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many requests")
    return await lb.get_top_n(n)

@app.post("/game/score")
async def submit_score(
    player_id: str,
    score: float,
    redis: Redis = Depends(get_redis),
    lb: LeaderboardService = Depends(get_leaderboard),
):
    # Use Redis built-in lock (redis-py Lock)
    async with RedisLock(redis, f"lock:player:{player_id}:score", timeout=10):
        await lb.add_or_update_score(player_id, score)
    return await lb.get_player_rank(player_id)

async def authenticate_user(email: str, password: str):
    pass  # stub
```

---

## 6. Common Patterns & Best Practices

**Pipeline reads/writes to reduce round-trips:**
```python
# Instead of 3 separate round-trips:
# await redis.set("a", 1)
# await redis.set("b", 2)  
# await redis.set("c", 3)

# Single round-trip with pipeline:
async with redis.pipeline(transaction=False) as pipe:
    pipe.set("a", 1, ex=300)
    pipe.set("b", 2, ex=300)
    pipe.set("c", 3, ex=300)
    await pipe.execute()
```

**Use Lua scripts for atomic multi-step operations.** Redis guarantees that a Lua script executes atomically — no other command can run between the script's Redis calls.

**Always set TTL on cache keys.** `maxmemory-policy allkeys-lru` is a safety net, not a substitute for TTL management.

**Key expiry observation:** Redis key expiry is lazy (checked on access) + periodic background sweep. A key may live slightly beyond its TTL if not accessed. Design with this in mind.

**Use pipelining for batched reads:** If you need to read 50 keys, pipeline them into one network round-trip instead of 50.

---

## 7. Common Pitfalls

| Pitfall | Problem | Fix |
|---|---|---|
| `KEYS *` in production | Blocks Redis for seconds, kills performance | Use `SCAN` with `COUNT` |
| No connection pool | TCP setup per request adds ~1ms overhead | Use client's built-in pool |
| Large values in Redis | > 100KB per key causes network/memory pressure | Break into smaller keys, or use S3 |
| `HGETALL` on large hashes | Returns all fields — O(N) | Use `HGET`/`HMGET` for specific fields; use `HSCAN` for large hashes |
| `SMEMBERS` on large sets | Returns all members — O(N) | Use `SSCAN` for large sets |
| Forgetting to ACK stream messages | Messages stay in PEL forever, memory leak | Always `XACK` after processing |
| Using `MULTI`/`EXEC` in Cluster mode | Transaction fails if keys span multiple slots | Use hash tags or Lua scripts |
| Storing session in Redis without fallback | Redis down = all sessions lost | Design auth to tolerate session loss (re-login); or use session replication |
| Lock without unique token | Lock holder A can delete lock holder B's lock | Always store unique token in lock value |
| Not setting `maxmemory` | Redis OOM-killed by OS | Set `maxmemory` + appropriate eviction policy |
| Reusing script SHA without handling NOSCRIPT | Script evicted from script cache | Always use `EVALSHA` with `EVAL` fallback |

---

## 8. Interview Questions & Model Answers

**Q: What Redis data structure would you use for a leaderboard?**

Sorted Set (ZSet). Each player is a member with their score as the sorted score. `ZADD leaderboard score player_id` to add/update. `ZREVRANGE leaderboard 0 9 WITHSCORES` for top 10 in O(log N + K) time. `ZREVRANK leaderboard player_id` for a player's rank in O(log N). `ZINCRBY leaderboard delta player_id` for atomic score updates. The key advantage: Redis maintains the sorted order automatically, so rank queries are always fast regardless of dataset size. For seasonal leaderboards, create separate keys per time period (`leaderboard:2024-01`) and set expiry.

**Q: How do you implement a distributed lock with Redis? What are its limitations?**

Use `SET lock_key unique_token NX PX lock_ttl_ms`. NX ensures only one client sets the key. The unique token prevents a timed-out lock holder from releasing another client's lock. To release: use a Lua script that atomically checks the token and deletes only if the value matches.

Limitations: (1) Clock drift — if the lock TTL is short and the lock holder experiences a GC pause or network slowdown, the lock may expire while work is in progress, allowing two clients to proceed simultaneously; (2) Redis replication gap — with async replication, if the primary crashes immediately after SET NX but before replication, the standby won't have the lock key, and a second client can acquire it. The Redlock algorithm addresses the replication issue by acquiring the lock on N/2+1 independent Redis instances. For strict requirements, use ZooKeeper or etcd.

**Q: What is the Redlock algorithm?**

Redlock is a distributed locking algorithm for Redis that tolerates node failures. With N independent Redis nodes (typically 5): (1) Get timestamp T1; (2) Try to acquire lock on all N nodes with the same key, unique token, and short per-node timeout (~10ms); (3) Lock is valid if: acquired on majority (>N/2) nodes AND total elapsed time < lock TTL; (4) If valid, use the lock with effective TTL = lock_ttl - elapsed; if not valid, release on all nodes. This ensures that even if one Redis node fails, the lock can't be acquired simultaneously by two clients because both would fail to reach quorum. Controversy: Martin Kleppmann argues it's still not safe under certain failure scenarios involving process pauses and clock drift.

**Q: What is the difference between RDB and AOF persistence?**

RDB takes periodic binary snapshots (via fork + copy-on-write). Fast to load on restart (~seconds), compact storage, minimal runtime impact, but loses all writes since the last snapshot (minutes of data). AOF logs every write command as it happens. At `appendfsync everysec`, you lose at most 1 second of writes, but startup requires replaying all commands (slower) and the file grows until AOF rewrite. In production, use both: RDB for fast restarts and backups, AOF for durability. On restart, Redis prefers the AOF (more recent). Trade-off summary: RDB = fast recovery, potential data loss up to snapshot interval; AOF = minimal data loss (1s), slower recovery, larger disk usage.

**Q: Why is Redis single-threaded and still fast?**

Redis's single-threaded command processing is fast because: (1) All data is in RAM — memory access is nanoseconds vs microseconds/milliseconds for disk; (2) No lock contention — a single thread accessing data structures has no mutex overhead; (3) CPU is rarely the bottleneck — most Redis workloads are network-bound (reading requests, writing responses), not CPU-bound; (4) Efficient I/O multiplexing — Redis uses `epoll`/`kqueue` to handle thousands of connections without blocking; (5) Highly optimized data structures with O(1) or O(log N) operations. Redis achieves 100K-1M simple ops/sec on a single core. Redis 6+ added threaded I/O for reading/writing sockets in parallel while keeping command processing single-threaded.

**Q: How do you implement rate limiting with Redis sorted sets?**

Sliding window with sorted set: use `user_id` as the key namespace, current timestamp (ms) as the score, and a unique request ID as the member. For each request: (1) ZREMRANGEBYSCORE to remove entries older than the window; (2) ZCARD to count remaining entries; (3) if count < limit: ZADD current request + EXPIRE the key; (4) else: reject. Wrap in a Lua script for atomicity — between ZREMRANGEBYSCORE and ZADD, no other command runs. This gives accurate sliding window behavior unlike fixed-window (INCR-based) which allows 2× burst at window boundaries.

**Q: What eviction policy would you use for a pure cache use case?**

`allkeys-lru` or `allkeys-lfu`. With `allkeys-lru`, Redis evicts the least recently used key from ALL keys (not just those with TTL set). This is correct for a pure cache: all keys are ephemeral and the least recently accessed data is the best candidate for eviction. `allkeys-lfu` (Redis 4.0+) is better when access patterns are highly skewed — some very hot keys (accessed 1000×/sec) and many cold keys (accessed 1×/day). LFU keeps the hot keys and evicts cold ones, whereas LRU would evict recently-not-accessed keys which might just be cyclically accessed. Use `noeviction` only for authoritative data stores (not caches) where data loss is unacceptable.

---

## 9. Resources

- [Redis Documentation](https://redis.io/docs/) — official, comprehensive
- [Redis University (free courses)](https://university.redis.com/)
- [Redis Command Reference](https://redis.io/commands/)
- [Distributed Locks with Redis (Martin Kleppmann critique)](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)
- [Antirez Response to Redlock Critique](http://antirez.com/news/101)
- [go-redis Documentation](https://redis.uptrace.dev/)
- [ioredis (Node.js)](https://github.com/redis/ioredis)
- [redis-py (Python)](https://redis-py.readthedocs.io/)
- [Redis in Action](https://www.manning.com/books/redis-in-action) — Josiah Carlson
- [Designing Data-Intensive Applications](https://dataintensive.net/) — Ch. 9 (distributed coordination)

---

**Next:** [Part 9.1: Message Queues & Kafka](../part-09/09-message-queues-kafka.md)
