# Track 3: Scalability & Performance — System Design Study Guide

*Part of Gautham Gokulakonda's system design self-study series. This track covers the tools and patterns that make systems faster and handle more load: caching at every layer, message queues for decoupling, and architectural patterns for scaling reads and writes independently.*

---

## 1. Horizontal vs Vertical Scaling

### Scale Up vs Scale Out

**What it is:** Vertical scaling ("scale up") means adding more resources — CPU, RAM, disk — to a single machine. Horizontal scaling ("scale out") means adding more machines and distributing load across them.

**Why it exists / What problem it solves:** Every system eventually outgrows a single machine's capacity. The question is whether you make that one machine bigger, or you add more machines and split the work.

**How it works:**
- Vertical: upgrade your DB server from 16 vCPUs to 64 vCPUs, double the RAM, move to faster NVMe disks.
- Horizontal: add more application servers behind a load balancer, shard your database across multiple nodes, add more Kafka brokers.

**Why not just always scale vertically?**
- There's a hard ceiling — the biggest cloud instance GCP or AWS offers is still finite. You will hit it.
- Vertical scaling usually requires downtime (resizing an instance means a restart).
- Cost grows non-linearly — a machine with 2x the specs often costs more than 2x the price (diminishing returns).
- Single point of failure — one big machine dying takes everything down. Horizontal scaling gives you redundancy for free.

**The prerequisite for horizontal scaling: statelessness.** You can only add more app server replicas behind a load balancer if any replica can handle any request. If a server stores session data in local memory, request #2 from the same user might hit a different server that has no idea who they are. This is why session state gets pushed to Redis, why uploaded files go to object storage (GCS/S3) instead of local disk, and why app servers should be treated as disposable cattle, not pets.

**Auto-scaling in cloud environments:** GCP (Managed Instance Groups) and AWS (Auto Scaling Groups) let you define a policy — e.g., "if average CPU > 70% for 5 minutes, add 2 more instances" — and the cloud provider handles spinning up/down replicas automatically. This only works cleanly if your services are stateless and your load balancer health-checks new instances before routing traffic to them.

**Key numbers / rules of thumb:**
- Vertical scaling: good for quick wins, simpler ops, but expect to hit a ceiling and pay a premium near the top of the instance size curve.
- Horizontal scaling: more operational complexity (load balancing, distributed state, network partitions) but no ceiling and built-in redundancy.
- Most real systems do both: vertically size each node reasonably, then scale horizontally for the rest.

> **Key insight:** Vertical scaling buys you time. Horizontal scaling is the actual solution for production-grade systems — but it forces you to confront statelessness, distributed consistency, and coordination problems you could previously ignore.

**Interview Q&A:**
- Q: "Why is horizontal scaling generally preferred over vertical scaling at production scale?"
  A: "Vertical scaling has a hard ceiling — you eventually run out of bigger machines to buy, and cost grows non-linearly as you approach the top of the instance size curve. It's also a single point of failure: one machine going down takes the whole service with it. Horizontal scaling has no real ceiling — you keep adding commodity machines — and it gives you redundancy for free, since the load balancer can route around a dead node. The trade-off is complexity: horizontal scaling requires stateless services, distributed session management, and dealing with consistency across nodes, which vertical scaling never forces you to think about."
- Q: "What has to be true about a service before you can scale it horizontally?"
  A: "It has to be stateless — any instance should be able to handle any request without depending on data that only lives on one specific server. That means session data goes into a shared store like Redis instead of local memory, files go into object storage instead of local disk, and there's no in-memory cache that one replica has and another doesn't (or if there is, it's treated as best-effort, not source of truth)."

---

## 2. Caching — The Fundamentals

**What it is:** Caching is storing a copy of frequently accessed data in a faster storage layer so future requests for that data can be served without redoing the expensive work (a DB query, an API call, a computation).

**Why it exists / What problem it solves:** There's a massive latency gap between memory and disk/network. RAM access is on the order of ~100 nanoseconds; a network round-trip to a database can be 1-10 milliseconds — roughly 10,000-100,000x slower. Caching exploits this gap: keep hot data in RAM, and you've eliminated most of your latency and most of your database load.

**How it works:**
- **Cache hit:** the requested data is found in the cache. Return it immediately — fast path, no DB/origin call needed.
- **Cache miss:** the data isn't in the cache. Fall back to the source of truth (DB, API, computation), fetch the result, **then** populate the cache with it so the next request is a hit.
- Every cache miss costs you the full latency of the origin call *plus* a small write to populate the cache. This is why miss rate matters as much as hit rate.

**Cache eviction policies** — since cache memory is finite, you need a strategy for what to throw out when it's full:

| Policy | How it works | Best for |
|---|---|---|
| **LRU** (Least Recently Used) | Evict the item that hasn't been accessed in the longest time | General-purpose, default choice — Redis uses this |
| **LFU** (Least Frequently Used) | Evict the item with the lowest access count | Skewed access patterns where a few items are accessed *very* often (e.g. viral content) |
| **FIFO** | Evict the oldest item, regardless of access pattern | Rarely optimal — doesn't account for actual usage at all |
| **TTL-based** | Evict items after a fixed time window, regardless of access | Data that becomes stale on a known schedule (e.g. a stock price, a session token) |

**Why not just cache everything forever?** Memory is expensive and finite. You can't cache the entire dataset, so you need a policy that approximates "keep what's likely to be requested again."

**The 80/20 rule in caching:** In most real systems, a small fraction of data accounts for most of the traffic (a power-law / Zipfian distribution) — think of the most popular tweets, the top-selling products, the most-viewed profiles. Caching roughly 20% of your dataset (the hot set) can serve 80%+ of requests. This is *why* caching works so well in practice — you don't need to cache everything, just the hot keys.

**Cold start problem:** When a cache is freshly deployed or just flushed, it's empty — every request is a miss, and the origin system (usually the DB) gets hit with full traffic load all at once. This is dangerous right after a deploy or a cache cluster restart.
- **Solution — cache warming:** pre-populate the cache with known-hot keys before traffic hits it (e.g., replay yesterday's top queries, or run a warm-up script on deploy).

**Interview Q&A:**
- Q: "Why does caching work so well in most real-world systems?"
  A: "Because real access patterns follow a power-law distribution, not a uniform one — a small set of 'hot' items account for most of the requests. That's the 80/20 rule: caching roughly 20% of your data can serve 80%+ of your traffic. So you don't need to cache everything, which would be infeasible memory-wise — you just need a good eviction policy that keeps the hot set in cache and evicts the cold tail."
- Q: "What's the cold start / cache warming problem, and when does it bite you?"
  A: "Right after a deploy, a cache flush, or scaling up a new cache node, the cache is empty. Every request becomes a miss, and all that traffic gets redirected straight to the database at once — which can cause a load spike right when the system is least prepared for it. The fix is cache warming: proactively populating the cache with known-hot keys before you start routing live traffic to it, instead of letting it fill up reactively under load."

---

## 3. Cache Layers — Where to Cache

**What it is:** Caching doesn't happen in one place — a single request can pass through multiple cache layers before it ever reaches your database, each with different trade-offs around speed, sharing, and staleness.

**Why it exists / What problem it solves:** Each layer sits at a different distance from the user, and "distance" is directly proportional to latency. The closer to the user you can serve a cached response, the less work the rest of your system has to do.

### The Layers

**Client-side cache (browser, mobile app)**
- Controlled via HTTP caching headers: `Cache-Control` (max-age, no-cache, no-store), `ETag` (a content hash the client sends back to check if its copy is still valid), `Last-Modified` (timestamp-based validation).
- Zero network round-trip if the cache is valid — the fastest possible "cache hit" since the request never leaves the device.
- Trade-off: you have very little control once it's on the client. You can't force-invalidate a browser cache; you can only set short TTLs or rely on versioned URLs.

**CDN cache (edge nodes)**
- Geographically distributed servers (Cloudflare, Akamai, GCP Cloud CDN, Fastly) that cache content close to the user's physical location.
- Best for: static assets (images, JS/CSS bundles, videos), and increasingly, cacheable API responses (product listings, public profile pages).
- Not appropriate for: highly personalized or rapidly changing data, unless you cache per-user fragments separately.

**Application-level cache (in-process)**
- Lives inside the application's own memory — Go's `sync.Map`, Python's `functools.lru_cache`, an in-process map.
- Fastest possible server-side cache — no network hop at all, just a memory lookup in the same process.
- Critical limitation: **not shared.** If you have 10 replicas of a service, each one has its own independent in-process cache. This means inconsistent state across replicas, and 10x the memory footprint for the same hot data.
- Best for: data that's safe to be eventually-consistent across replicas and small enough to duplicate per-instance (e.g., a feature-flag config, a compiled regex, a rarely-changing lookup table).

**Distributed cache (Redis, Memcached)**
- A separate, shared cache layer that all service instances talk to over the network.
- Solves the "not shared" problem of in-process caches — one cache, one source of truth for cached data, consistent across all replicas.
- Trade-off: it's a network call, so it's slower than in-process (though still far faster than hitting the DB) — and it's now a new piece of infrastructure that can become a bottleneck or a single point of failure if not made highly available.

### How They Combine

A real request often passes through multiple layers in sequence:

```
Browser cache (miss) 
  → CDN edge cache (miss) 
    → Load balancer → App server's in-process cache (miss)
      → Distributed cache / Redis (hit!) → return
```

Each layer is a chance to short-circuit before hitting the most expensive resource — the database.

> **Key insight:** The general principle is "cache as close to the user as correctness allows." The closer the cache, the faster the response — but also the harder it is to invalidate reliably. Personalized or fast-changing data pushes you toward the distributed cache; static or slow-changing data can live safely all the way out at the CDN or client.

**Interview Q&A:**
- Q: "Where would you put caching for a product listing page on an e-commerce site?"
  A: "I'd layer it. Product images and static assets go on the CDN since they rarely change and are identical for every user. The product listing JSON itself — price, name, stock status — is a good candidate for a short-TTL CDN or distributed cache entry if it's not personalized, since most users browsing the same category see the same data. Anything personalized — like 'recommended for you' or cart contents — has to skip the CDN and either go in a distributed cache keyed by user ID, or be computed live. The key question for each piece of data is: how many users see the exact same value, and how often does it change?"
- Q: "Why not just use an in-process cache instead of standing up a Redis cluster?"
  A: "In-process caches aren't shared across replicas — if I have 10 instances of a service behind a load balancer, each one would build and hold its own copy of the hot data, which means 10x the memory for the same data and inconsistent results depending on which replica handles your request. Redis solves that by being one shared cache all instances hit, at the cost of a network round-trip instead of an in-memory lookup. For data where consistency across replicas matters, that trade-off is worth it."

---

## 4. Cache Write Strategies

**What it is:** When a write happens, there are several patterns for deciding when the cache and the database each get updated — and that ordering decision creates very different consistency and performance guarantees.

**Why it exists / What problem it solves:** Reads and writes have different needs. A write strategy chosen badly can either slow down every write (waiting on two systems) or open a window where the cache and DB disagree (stale or incorrect reads).

### The Strategies

| Strategy | How it works | Consistency | Write latency | Risk |
|---|---|---|---|---|
| **Write-through** | Write to cache and DB at the same time (synchronously) | Strong — cache is never stale | Higher — waits on both | None, but slower writes |
| **Write-back (write-behind)** | Write to cache immediately, flush to DB asynchronously later | Weak — DB lags behind cache | Lowest — only waits on cache | Data loss if cache crashes before flush |
| **Write-around** | Write directly to DB, skip the cache entirely | Cache may be stale until next read | DB-only latency | Avoids polluting cache with data that's rarely re-read |
| **Read-through** | (Read pattern, not write) — on a cache miss, the cache itself fetches from DB and populates itself, transparent to the app | N/A — this governs reads | N/A | Simplifies application code |

**Write-through, in depth:**
- Every write goes to both cache and DB before returning success to the caller.
- Guarantees the cache is never out of sync with the DB.
- Cost: every write pays the latency of *both* systems. Worse for write-heavy workloads.
- Use when: correctness matters more than write speed — e.g., financial balances, inventory counts.

**Write-back, in depth:**
- Write hits the cache and returns immediately; a background process flushes to the DB later (batched or on an interval).
- Much faster writes — the caller doesn't wait on the DB at all.
- Risk: if the cache node crashes before the flush happens, that write is gone forever. This is a real durability risk, not a theoretical one.
- Use when: write throughput matters more than durability of every single write, and some data loss is tolerable — e.g., view counters, analytics events, "last seen" timestamps.

**Write-around, in depth:**
- Skips the cache on write entirely; only populates the cache later, on a read (cache miss → fetch from DB → populate).
- Useful when data is written once but rarely re-read soon after (avoids filling the cache with "write-once, read-never" data that just evicts genuinely hot keys).
- Use when: write-heavy, read-rarely data — e.g., logging events, audit trails.

**Read-through, in depth:**
- This pairs naturally with write-around. On a cache miss, instead of the application manually querying the DB and then writing to the cache, the caching layer itself handles that fetch-and-populate logic transparently.
- Simplifies application code — the app just asks the cache for data, and the cache handles the miss internally.

### Decision Matrix

| Scenario | Recommended strategy | Why |
|---|---|---|
| Bank account balance | Write-through | Cache must never disagree with DB |
| Page view counter | Write-back | Speed matters, occasional loss is fine |
| Audit log / event log | Write-around | Rarely re-read immediately after write |
| User profile reads after a write | Write-through or read-through | Users expect their own update to show up instantly |
| High-volume IoT sensor data | Write-back (batched) | Throughput over individual-write durability |

> **Key insight:** There's no universally "best" write strategy — it's a direct trade-off between write latency, durability, and consistency, and the right choice depends entirely on whether *this specific data* can tolerate staleness or loss.

**Interview Q&A:**
- Q: "What is the difference between write-through and write-back caching? When would you use each?"
  A: "Write-through writes to the cache and the database synchronously, in the same operation — so the cache is always consistent with the DB, but every write pays the latency cost of both systems. Write-back writes to the cache first and returns immediately, flushing to the database asynchronously later — writes are much faster, but if the cache crashes before that flush happens, that data is lost. I'd use write-through for anything where correctness can't be compromised, like account balances or inventory counts. I'd use write-back for high-volume, loss-tolerant data like view counters or telemetry, where throughput matters more than guaranteeing every single write survives a crash."
- Q: "Why would you ever choose write-around instead of write-through?"
  A: "Write-around makes sense when data is written once and rarely read again soon after — think audit logs or event records. If you write-through that kind of data, you're filling up your limited cache space with entries that are unlikely to be requested again, which pushes out genuinely hot data and lowers your overall hit rate. Write-around keeps the cache focused on data that's actually re-read."

---

## 5. Cache Invalidation — "The Hardest Problem in CS"

**What it is:** Cache invalidation is the problem of knowing *when* cached data has become stale (because the underlying source changed) and removing or updating it before a client reads the wrong value.

**Why it exists / What problem it solves:** Caching is easy when data never changes. The moment data is mutable, you have two copies of the truth — the DB and the cache — and they can disagree. Phil Karlton's famous line ("There are only two hard things in Computer Science: cache invalidation and naming things") exists because there's no single correct answer; every approach trades off complexity against staleness window.

**Why it's genuinely hard:**
- The cache doesn't automatically know when the DB changes underneath it — something has to *tell* it.
- Multiple services or instances might be writing to the same data, all needing to trigger invalidation.
- Invalidating too aggressively (e.g., flushing on every write) destroys your hit rate. Invalidating too lazily means serving stale data.

### Strategies

**TTL-based invalidation**
- Simplest approach — every cache entry expires automatically after a fixed time window.
- Pro: requires no coordination, no event system, dead simple to reason about.
- Con: there's always a stale window between when the underlying data changes and when the TTL naturally expires. For some data (a homepage banner) that's fine; for others (a stock price) it's not.

**Event-driven invalidation**
- The cache is actively told to purge or update a key the moment the underlying data changes.
- Typically implemented via CDC (Change Data Capture) — a tool like Debezium watches the DB's write-ahead log and emits a change event — or directly via application code publishing an event to Kafka when a write happens, with a consumer that invalidates the relevant cache key.
- Pro: near-zero staleness window.
- Con: more moving parts — you now depend on the event pipeline being reliable. If an invalidation event is dropped, you have silent staleness with no automatic recovery (unless paired with a TTL as a safety net).

**Versioned cache keys**
- Instead of invalidating a key, embed a version number in the key itself: `user:123:v2` instead of `user:123`.
- When the underlying data changes, you bump the version pointer (stored somewhere cheap to look up) and start writing to `user:123:v3`. Old versions naturally fall out of the cache via normal eviction — no active deletion needed.
- Pro: avoids race conditions around "did the delete happen before or after the next read repopulated the old value?"
- Con: slightly more complex key management; old versions linger in memory until evicted (minor memory overhead).

### Cache Stampede / Thundering Herd Problem

**What it is:** When a popular cache key expires, many concurrent requests can all miss at the same instant and all hammer the database simultaneously trying to repopulate the same key — a spike that can take down the DB even though the system was handling load fine moments before.

**Solutions:**
- **Mutex locking:** the first request to miss acquires a lock and goes to the DB; all other concurrent requests for the same key wait for that lock to release, then read the now-populated cache instead of independently querying the DB.
- **Probabilistic early expiration:** refresh a cache entry slightly *before* its TTL actually expires, with a small random probability that increases as it gets closer to expiry — spreads out refreshes instead of having them all happen at the exact expiry instant.
- **Background refresh:** a separate process proactively refreshes hot keys before they expire, so user-facing requests never actually experience a true miss for high-traffic keys.

> **Key insight:** Most production cache-invalidation strategies are a TTL *combined with* one other mechanism — TTL as the safety net that guarantees eventual correctness even if an event gets dropped, plus event-driven invalidation or versioning for low-latency correctness in the common case.

**Interview Q&A:**
- Q: "How do you solve the cache invalidation problem?"
  A: "There's no single solution — it's a spectrum of trade-offs. The simplest is TTL-based expiry, which needs no coordination but leaves a stale window. For lower staleness, you go event-driven: hook into DB change events, often via CDC or an application-level event published to Kafka, and have a consumer purge or update the relevant cache key the moment the underlying data changes. In practice, most systems combine both — event-driven invalidation for the common case, with a TTL as a safety net so that if an invalidation event ever gets dropped, the entry still self-corrects eventually instead of staying stale forever."
- Q: "What is the Thundering Herd problem and how do you prevent it?"
  A: "It happens when a popular cache key expires and many concurrent requests miss at the same instant, all hitting the database to repopulate the same key — which can spike load enough to take the DB down. The standard fix is a mutex: the first request that misses acquires a lock and goes to the DB, while every other concurrent request for that key waits and then reads the cache instead of independently querying the DB. An alternative is probabilistic early expiration, where you refresh slightly before the real TTL with increasing probability as expiry approaches, which spreads refreshes out instead of letting them all collide at one instant."

---

## 6. Redis Deep Dive

**What it is:** Redis is an in-memory data structure store — not just a key-value cache, but a server that natively understands lists, sets, sorted sets, hashes, and more, each with operations tailored to that structure.

**Why it exists / What problem it solves:** A plain key-value cache only gets you "GET" and "SET" on opaque blobs. Redis's data structures let you push specific operations (rank by score, check set membership, atomically increment) down into the data store itself, instead of pulling a blob out, deserializing it in your app, mutating it, and writing the whole thing back — which is both slower and racy under concurrent access.

### Data Structures and Their System Design Use Cases

| Structure | Core operations | System design use case |
|---|---|---|
| **String** | GET, SET, INCR | Simple cache values, atomic counters, rate limiting (`INCR` + `EXPIRE`) |
| **List** | LPUSH, RPUSH, BRPOP | Lightweight message queue (`LPUSH` to enqueue, `BRPOP` to block-and-dequeue), activity feeds (recent N items) |
| **Set** | SADD, SISMEMBER, SINTER | Unique visitor tracking, tag systems, friend/follower lists, fast "is X in this group" checks |
| **Sorted Set (ZSet)** | ZADD, ZRANGE, ZRANGEBYSCORE | Leaderboards (score = rank metric), priority queues, sliding-window rate limiting (score = timestamp) |
| **Hash** | HSET, HGET, HGETALL | Storing object fields efficiently — a user profile or shopping cart as field/value pairs under one key |
| **HyperLogLog** | PFADD, PFCOUNT | Approximate unique counts (e.g. daily active users) using a tiny, fixed amount of memory regardless of cardinality |
| **Pub/Sub** | PUBLISH, SUBSCRIBE | Lightweight real-time message broadcast — **not durable**, messages are lost if no subscriber is listening at publish time |

**Why Sorted Sets are the leaderboard answer:** `ZADD leaderboard 1500 "user123"` inserts/updates a member with a score; `ZREVRANGE leaderboard 0 9 WITHSCORES` gets the top 10 in O(log N) — Redis maintains the sorted order internally via a skip list, so you never have to sort on read.

**Why Sets/Sorted Sets work for rate limiting:** A sliding-window rate limiter can use a Sorted Set keyed per user, where the score is the request timestamp — `ZADD`, then `ZREMRANGEBYSCORE` to drop entries older than the window, then `ZCARD` to count requests still in the window. This gives a true sliding window instead of the bucket edge-effects of fixed-window counters.

**Why HyperLogLog over a Set for unique counts:** A regular Set storing every unique user ID for "daily active users" grows linearly with cardinality — millions of users means megabytes of memory. HyperLogLog uses a probabilistic algorithm to estimate cardinality with ~0.81% standard error, using a fixed ~12KB regardless of whether you're counting a thousand or a billion unique items. The trade-off is you give up exact counts and the ability to list members — you only get the count.

**Why Pub/Sub isn't a replacement for Kafka:** Redis Pub/Sub is "fire and forget" — if a subscriber isn't connected at the moment of `PUBLISH`, that message is gone. There's no offset, no replay, no persistence. It's great for ephemeral real-time signals (like "invalidate this cache key now," or live notification fan-out) but wrong for anything that needs durability or replay — that's Kafka's job.

### Redis Persistence

| Mechanism | How it works | Trade-off |
|---|---|---|
| **RDB (snapshot)** | Periodic point-in-time snapshot of the whole dataset written to disk | Fast to restore, compact file — but you lose everything since the last snapshot on a crash |
| **AOF (Append-Only File)** | Every write operation is logged to a file, replayed on restart | Much less data loss (configurable fsync — every write, every second, or OS-decided) — but larger files, slower restart since it replays the whole log |

Most production setups use both: RDB for fast full restores/backups, AOF for finer-grained durability, or AOF with periodic RDB-style rewriting to keep the log compact.

### Redis Replication and Sentinel

- **Replication:** one primary node accepts writes; one or more replica nodes asynchronously copy data from the primary, serving reads to offload read traffic.
- **Redis Sentinel:** a separate set of processes that monitor the primary, and if it goes down, automatically promote a replica to be the new primary — providing automatic failover without a human intervening.

### Redis Cluster

- Redis Cluster shards data across multiple nodes so the dataset isn't limited by a single machine's memory, and write throughput scales by spreading keys across nodes.
- Uses a form of **consistent hashing** (specifically, hash slots — 16,384 fixed slots, each key hashed into one slot, slots distributed across nodes) so that adding or removing a node only requires reshuffling a fraction of the keyspace, not the whole thing — this is the same underlying problem and solution as sharding in any distributed system.

### Redis vs Memcached

| Aspect | Redis | Memcached |
|---|---|---|
| Data structures | Rich (strings, lists, sets, sorted sets, hashes, etc.) | Simple key-value only |
| Persistence | Yes (RDB/AOF) | No — pure in-memory, data lost on restart |
| Replication/HA | Built-in (Sentinel, Cluster) | Not built-in — needs external tooling |
| Multi-threading | Mostly single-threaded core (newer versions have some I/O threading) | Multi-threaded by design |
| Best for | Anything needing structure, persistence, or pub/sub | Pure, simple, maximally fast key-value caching with no extra features needed |

**Why not always pick Redis then?** If your use case truly is "cache plain blobs, nothing else, restart-tolerance doesn't matter," Memcached's multi-threaded design can give it an edge in raw throughput for that narrow case, with less operational surface area. In practice, most teams pick Redis by default because they end up wanting at least one of its extra features eventually.

> **Key insight:** The reason Redis shows up everywhere in system design interviews isn't "it's a fast cache" — it's that its data structures let you offload coordination logic (ranking, deduplication, atomic counting) onto the data store itself, which is both faster and avoids race conditions you'd otherwise have to handle in application code with locks.

**Interview Q&A:**
- Q: "Design a rate limiter using Redis."
  A: "I'd use a Sorted Set per user, where each request adds an entry scored by its timestamp via `ZADD`. On each incoming request, I first run `ZREMRANGEBYSCORE` to drop entries older than the rate limit window, then `ZCARD` to count what's left. If the count is under the limit, allow the request and add the new entry; otherwise reject. This gives a true sliding window, unlike a simple `INCR`-based fixed-window counter, which has edge effects where a burst right at a window boundary can let through nearly double the intended rate. For very high QPS, I'd also consider a simpler token-bucket using `INCR` plus `EXPIRE` if approximate fixed-window behavior is good enough, since it's cheaper than maintaining a sorted set per user."
- Q: "How would you implement a real-time leaderboard?"
  A: "Redis Sorted Sets are built for exactly this. `ZADD leaderboard <score> <user_id>` to update a player's score — Redis keeps the set ordered internally, so there's no sort-on-read cost. `ZREVRANGE leaderboard 0 9 WITHSCORES` gets the top 10 in logarithmic time, and `ZRANK` gets a specific player's rank instantly. This avoids the alternative of pulling all scores into the application and sorting them on every read, which wouldn't scale past a small number of players."
- Q: "What Redis data structure would you use for a shopping cart? For a leaderboard? For rate limiting?"
  A: "Shopping cart: a Hash, with the cart ID as the key and each field being a product ID mapped to quantity — lets you update one item's quantity without touching the rest of the cart. Leaderboard: a Sorted Set, scored by whatever ranking metric you're tracking, for O(log N) ranked reads. Rate limiting: either a String with `INCR`+`EXPIRE` for simple fixed-window limits, or a Sorted Set scored by timestamp for a precise sliding-window limiter."
- Q: "Redis vs Memcached — when would you choose each?"
  A: "I'd default to Redis unless I have a specific reason not to, because it gives me data structures beyond plain key-value, built-in persistence if I ever need restart-tolerance, and built-in replication and clustering for HA. Memcached is a better fit only when the use case is purely simple key-value caching with no need for persistence, and the multi-threaded architecture's raw throughput matters more than any of Redis's extra capabilities — which in practice is a narrower set of cases than people assume going in."

---

## 7. Message Queues — Why They Exist

**What it is:** A message queue is an intermediary that sits between services, letting a producer hand off work or data without waiting for a consumer to process it immediately.

**Why it exists / What problem it solves:** When Service A calls Service B synchronously (a direct HTTP/RPC call), A is blocked waiting for B to respond. If B is slow, A is slow. If B is down, A fails too. This tight coupling means failures and latency cascade backward through every caller in the chain. A message queue breaks that coupling — A drops a message and moves on; B picks it up whenever it's ready.

**How it works — key concepts:**
- **Producer:** the service that creates and sends messages.
- **Consumer:** the service that reads and processes messages.
- **Queue / Topic:** the channel messages are written to and read from. ("Queue" in traditional systems like RabbitMQ/SQS; "topic" in log-based systems like Kafka.)
- **Offset:** a pointer tracking how far a consumer has read into a topic (Kafka-specific concept — see below).
- **Consumer group:** a set of consumers that split the work of reading from a topic between them, so no two consumers in the same group process the same message.
- **Partition:** a topic is split into partitions for parallelism — each partition can be consumed independently.

**Delivery guarantees:**

| Guarantee | What it means | Risk |
|---|---|---|
| **At-most-once** | Message is delivered zero or one times — never redelivered | Possible message loss, but never duplicates |
| **At-least-once** | Message is guaranteed to be delivered, but might be delivered more than once on retry | Possible duplicate processing — consumer must be idempotent |
| **Exactly-once** | Message is delivered and processed exactly one time, no loss, no duplicates | Hardest to implement — requires careful coordination (e.g. Kafka's idempotent producer + transactional consumer) |

**Why this matters:** Most real systems run at-least-once because it's the achievable default, and push idempotency onto the consumer (e.g., using a unique message ID to detect and skip already-processed messages) rather than trying to guarantee perfect exactly-once delivery end-to-end, which is expensive and complex.

**Message ordering:** In Kafka, ordering is guaranteed *within a partition* — messages with the same partition key are processed in the order they were produced. There is no global ordering guarantee across partitions. This is why partition key selection matters (see Kafka section below).

**Dead Letter Queues (DLQ):** When a message repeatedly fails processing (e.g., a consumer throws an exception every time it tries), retrying forever would block the queue. A DLQ is a separate destination where messages get routed after exceeding a retry limit, so they can be inspected and reprocessed manually later without blocking the rest of the pipeline.

> **Key insight:** The core value of a message queue isn't speed — it's decoupling. The producer doesn't need to know if the consumer is up, fast, or even listening right now. That decoupling is what lets each side scale, fail, and deploy independently.

**Interview Q&A:**
- Q: "Why use a message queue instead of a direct synchronous call between services?"
  A: "A synchronous call couples the caller's availability and latency directly to the callee's. If the downstream service is slow or down, that failure propagates straight back to the caller, and under load this can cascade — one slow dependency backs up every service that depends on it. A message queue decouples them: the producer writes a message and moves on, and the consumer processes it whenever it's ready, independently. This means each side can scale, deploy, and fail independently, and a temporary consumer outage just becomes a backlog instead of a cascading failure."
- Q: "What's the difference between at-least-once and exactly-once delivery, and which do most systems actually use?"
  A: "At-least-once guarantees a message is never lost, but it might be delivered more than once if a retry happens after the first delivery actually succeeded — for example, the consumer processed it but the acknowledgment didn't make it back in time. Exactly-once guarantees no loss and no duplicates, but it's expensive to implement correctly end-to-end. Most production systems run at-least-once and make their consumers idempotent — using a unique message or event ID to detect and skip messages they've already processed — rather than trying to achieve true exactly-once semantics everywhere."

---

## 8. Kafka Deep Dive

**What it is:** Kafka is a distributed event streaming platform built around an append-only, partitioned, replicated log — fundamentally different from a traditional message queue in that consuming a message doesn't remove it.

**Why it exists / What problem it solves:** Traditional queues (RabbitMQ, SQS) typically delete a message once it's consumed and acknowledged — once it's gone, it's gone, and only one consumer (or one logical destination) sees it. Kafka instead keeps messages on disk for a configurable retention period, letting multiple independent consumer groups read the same data at their own pace, and letting any consumer replay history by resetting its offset backward. This makes Kafka suited to high-throughput event streaming, not just task distribution.

### Architecture

- **Brokers:** individual Kafka server instances that store data and serve client requests. A Kafka cluster is multiple brokers.
- **Topics:** a named stream of messages — the logical channel producers write to and consumers read from.
- **Partitions:** each topic is split into partitions, which are the unit of parallelism — each partition is an ordered, immutable, append-only log, and each can be hosted on (and consumed from) a different broker.
- **Consumer groups:** a named group of consumers that divide partitions between them — each partition is read by exactly one consumer within a group at a time, which is what lets you scale consumption horizontally while still treating it as one logical "the group processed this."
- **ZooKeeper / KRaft:** ZooKeeper was historically used to manage cluster metadata (which broker is the leader for which partition, cluster membership, etc.). Newer Kafka versions use **KRaft**, Kafka's own built-in consensus protocol, removing the ZooKeeper dependency entirely and simplifying operations.

### Why Kafka Is a Log, Not a Queue

- A traditional queue is destructive — pop a message, it's gone.
- Kafka's log is **non-destructive** — consuming a message just advances your offset (your personal bookmark in the log); the message itself stays on disk until its retention period expires, regardless of who's read it.
- This is what enables: replaying events for debugging, onboarding a brand-new consumer that needs historical data, and having multiple totally independent consumer groups read the same topic for different purposes (e.g., one group updates a search index, another group sends analytics events, both from the same topic).

### Kafka vs RabbitMQ vs SQS

| | **Kafka** | **RabbitMQ** | **SQS** |
|---|---|---|---|
| Model | Partitioned log, replay-capable | Traditional broker, complex routing (exchanges, bindings) | Fully managed simple queue |
| Throughput | Very high | Moderate | Moderate, auto-scales (managed) |
| Latency | Low, but optimized for throughput | Very low — built for fast task dispatch | Higher (managed service overhead) |
| Ordering | Guaranteed per-partition | Per-queue (with care) | FIFO queues available, but throughput trade-off |
| Replay | Yes — reset offset, reread history | No — message gone once acked | No |
| Ops overhead | Higher — you manage brokers/partitions (unless using a managed Kafka) | Moderate | None — fully managed |
| Best for | Event streaming, event sourcing, CDC, high-throughput pipelines | Complex routing logic, low-latency task queues, RPC-style patterns | Simple async task queuing in AWS-native stacks |

**Why not always use Kafka?** Kafka's operational complexity (partitions, consumer group rebalancing, retention tuning) is overkill if you just need "send this task to a worker asynchronously" — that's exactly SQS's or RabbitMQ's sweet spot. Reach for Kafka when you need replay, multiple independent consumers of the same stream, or genuinely high sustained throughput — not as a default choice for every async need.

### Consumer Group Mechanics

- Each partition within a topic is assigned to exactly one consumer instance within a given consumer group at any time.
- If a topic has 6 partitions and a consumer group has 3 consumer instances, each instance gets 2 partitions on average.
- Adding a 4th consumer triggers a **rebalance** — partitions get reassigned so the new consumer gets some too. Adding *more* consumers than partitions means some consumers sit idle — partition count is the hard ceiling on consumption parallelism within a single group.
- Different consumer groups are fully independent — Group A and Group B can both read the entire topic from the beginning, at their own pace, without affecting each other.

### Partition Key Selection

- Choosing what to key messages by (e.g., user ID, order ID) determines which partition a message lands in — Kafka hashes the key to pick a partition.
- This is the exact same problem as choosing a shard key in a sharded database: pick a key with high cardinality and even distribution, or you get **hot partitions** — one partition (and the broker hosting it) takes disproportionate load while others sit idle.
- All messages with the same key always land on the same partition, which is what gives you ordering guarantees *for that key* (e.g., all events for `order_id=123` are processed in order, even though events for other order IDs may be processed out of order relative to them, on other partitions).

### Kafka for Event Sourcing and CDC

- Because Kafka retains a full ordered history, it's a natural fit for **event sourcing** (storing every state change as an event) and **CDC** (Change Data Capture) — tools like Debezium tail a database's write-ahead log and publish every row-level change as a Kafka event, letting downstream systems (caches, search indexes, analytics) stay in sync without polling the DB.

### When NOT to Use Kafka

- Low, sporadic throughput where the operational overhead of running/managing Kafka isn't justified.
- Simple "fire off this background job" task queuing — SQS or RabbitMQ is simpler and sufficient.
- When you need complex routing logic (route by message attribute to different consumers) — RabbitMQ's exchange/binding model handles that more naturally than Kafka's simpler partition model.

### Kafka Backpressure

- If a consumer is slower than the rate messages are produced, its **consumer lag** (the gap between the latest offset in the partition and the consumer's current offset) grows.
- Kafka itself doesn't "push back" on producers the way some queue systems do (there's no built-in flow control signal that says "slow down") — instead, lag just accumulates on disk up to the retention limit, and monitoring that lag is how you detect a struggling consumer before it becomes a real problem.
- The actual backpressure response is operational: scale out consumers (more instances, up to partition count), or optimize the consumer's processing logic, or, in the worst case, those messages eventually fall off via retention and are lost.

> **Key insight:** Kafka's defining feature isn't "fast pub/sub" — it's the durable, replayable, partitioned log model. If your system doesn't need replay or multiple independent consumers of the same data stream, a simpler queue is often the better engineering choice, not a worse one.

**Interview Q&A:**
- Q: "Kafka vs RabbitMQ — which would you choose and why?"
  A: "It depends on the access pattern. If I need high-throughput event streaming, the ability to replay history, or multiple independent consumer groups reading the same data for different purposes — like one group indexing for search while another runs analytics off the same stream — Kafka's log model is the right fit. If I just need a straightforward task queue with low latency and possibly complex routing logic — like routing by message type to different handlers — RabbitMQ's broker model with exchanges and bindings is simpler to operate and a more natural fit. I wouldn't default to Kafka for every async use case; its operational complexity around partitions and consumer groups is only worth it when I actually need what only Kafka provides."
- Q: "How does Kafka guarantee message ordering?"
  A: "Ordering is guaranteed within a partition, not globally across a topic. Every message with the same partition key always lands on the same partition, and within that partition, messages are strictly ordered by the order they were written. So if I key by `order_id`, all events for a given order are processed in order — but events for two different orders, sitting on two different partitions, have no ordering guarantee relative to each other. If you need global ordering, you'd need a single partition, which sacrifices the parallelism that's the whole point of partitioning."
- Q: "What happens when a Kafka consumer can't keep up with the producer?"
  A: "Consumer lag grows — the gap between the latest produced offset and what the consumer has actually processed widens. Kafka doesn't have built-in producer-side flow control the way some other systems do; the messages just accumulate on disk until they age out via the topic's retention policy. In practice, you monitor consumer lag as a key health metric, and respond by scaling out consumer instances — up to the number of partitions, since that's the ceiling on parallelism within one consumer group — or by speeding up the per-message processing logic itself."

---

## 9. Event-Driven Architecture

**What it is:** Event-driven architecture (EDA) is a design style where services communicate primarily by producing and reacting to events — facts about something that happened — rather than calling each other directly.

**Why it exists / What problem it solves:** Direct service-to-service calls create tight coupling — the caller needs to know who to call and wait for a response. EDA inverts this: a service announces "this happened" and doesn't know or care who's listening, which lets new consumers be added later without ever touching the producer.

### Event vs Message vs Command — The Distinction Matters

| Term | Meaning | Example |
|---|---|---|
| **Event** | A fact about something that already happened, in the past tense. The producer doesn't expect or require any specific action. | `OrderPlaced`, `UserSignedUp` |
| **Command** | An instruction telling a specific receiver to do something, expecting it to happen. | `ChargeCreditCard`, `SendWelcomeEmail` |
| **Message** | The general envelope/transport mechanism carrying either an event or a command between systems. | (Either of the above, transported) |

This distinction matters because it changes coupling: an event-driven system doesn't break if you add a new consumer (loose coupling) — but a command implies the sender expects a specific outcome from a specific receiver (tighter coupling, closer to an RPC call just made asynchronous).

### Event Sourcing

**What it is:** Instead of storing only the current state of an entity (e.g., "this order's status is SHIPPED"), you store the full sequence of events that led to that state (`OrderCreated` → `PaymentReceived` → `OrderShipped`), and the current state is derived by replaying those events.

**Benefits:**
- **Audit log for free:** you have a complete, immutable history of every change, which is exactly what's needed for compliance, debugging, and dispute resolution.
- **Time travel:** you can reconstruct what the state was at any point in the past by replaying events up to that point.
- **Replay:** if a downstream read model or cache gets corrupted, you can rebuild it from scratch just by replaying the event log.

**Drawbacks:**
- **Query complexity:** "What's the current state?" now requires replaying events (or maintaining a separately updated read model — see CQRS below), instead of a simple `SELECT`.
- **Schema evolution:** events are immutable and live forever — if you change an event's shape, old events in the log still have the old shape, so your replay/consumer logic has to handle multiple historical versions gracefully (versioned event schemas, upcasting old events to new shapes, etc.).

### Choreography vs Orchestration

| | **Choreography** | **Orchestration** |
|---|---|---|
| How it works | Each service reacts to events independently; there's no central coordinator | A central orchestrator service explicitly calls each step in sequence |
| Coupling | Loose — services don't know about each other, only about events | Tighter — the orchestrator knows about every participant |
| Visibility | Harder to see the overall flow — it's implicit, spread across services | Easy to see — the whole flow lives in one place |
| Failure handling | Harder to coordinate compensating actions across many independent reactors | Easier — orchestrator can explicitly handle retries/rollbacks for the whole flow |
| Best for | Simple, loosely coupled flows where steps genuinely don't need central coordination | Complex multi-step workflows (e.g., sagas) where you need to track overall progress and handle partial failure explicitly |

**Why not always choose choreography (it sounds more "decoupled")?** As a workflow grows more complex — more steps, more conditional branches, more compensating actions on failure — choreography becomes very hard to reason about, because the "flow" doesn't exist anywhere as a readable artifact; it's implicitly encoded across every service's event handlers. Orchestration trades some coupling for a workflow you can actually look at and debug.

### The Outbox Pattern

**What problem it solves:** If a service needs to both (a) write to its own database and (b) publish an event about that write to Kafka, doing these as two separate operations creates an atomicity problem — what if the DB write succeeds but the Kafka publish fails (or vice versa)? You'd end up with inconsistent state: data changed but no one downstream was told, or an event published about a write that never actually committed.

**How it works:**
- Instead of writing to the DB and publishing to Kafka as two separate steps, write the event into an `outbox` table in the *same database transaction* as the actual data change. Since it's the same transaction, both succeed or both fail together — atomic by construction.
- A separate process (a poller, or a CDC tool like Debezium watching the outbox table) reads new rows from the outbox table and publishes them to Kafka, then marks them as published.
- This guarantees the event is eventually published if and only if the original write actually committed.

> **Key insight:** The outbox pattern exists because you can't get atomicity for free across two different systems (a DB and a message broker) — so you collapse it back down to one atomic operation (a single DB transaction) and let a separate, idempotent process handle the second system asynchronously.

**Interview Q&A:**
- Q: "What's the difference between an event and a command, and why does it matter for system design?"
  A: "An event is a statement of fact about something that already happened — the producer doesn't know or care who reacts to it, which keeps the system loosely coupled. A command is a direct instruction to a specific receiver, expecting a specific outcome — which is closer to a remote procedure call, just made asynchronous, and creates tighter coupling between sender and receiver. The distinction matters because if you design with commands everywhere, you end up with the same fragile dependency graph as synchronous RPC calls, just hidden behind a queue — you lose the actual benefit of decoupling that event-driven design is supposed to give you."
- Q: "How do you reliably publish an event to Kafka when writing to your database, without risking the two getting out of sync?"
  A: "This is the outbox pattern. You write the event into an outbox table as part of the same database transaction as the actual data change, so they're atomic together — either both happen or neither does. Then a separate process, often a CDC tool tailing that outbox table, reads new rows and publishes them to Kafka, marking them done afterward. This avoids the classic dual-write problem where the DB write succeeds but the Kafka publish fails, or vice versa, leaving the two systems silently inconsistent."

---

## 10. CQRS (Command Query Responsibility Segregation)

**What it is:** CQRS is the pattern of using separate models — and often separate data stores entirely — for writes (commands) and reads (queries), instead of a single model that handles both.

**Why it exists / What problem it solves:** Read and write workloads frequently have very different shapes and scaling needs. Writes often need strong consistency and normalized data to avoid anomalies; reads often need to be fast, denormalized, and heavily cacheable, and read volume is frequently orders of magnitude higher than write volume. Forcing both through one model means optimizing for one at the expense of the other.

**How it works:**
- **Write side:** a model optimized for handling commands correctly — typically normalized, with strong validation and consistency guarantees (a traditional relational schema).
- **Read side:** one or more separate models, often denormalized, shaped exactly for the queries the application actually needs to run (e.g., a pre-joined, flattened view stored in a different database optimized for fast reads, like Elasticsearch for search or a denormalized table for a dashboard).
- The read models are kept in sync with the write model asynchronously — usually by listening to events emitted whenever the write model changes (which pairs naturally with event sourcing and the outbox pattern above).

### CQRS + Event Sourcing

These two patterns are frequently used together, though they're independent:
- Event sourcing gives you the write-side: state is derived from a sequence of events.
- CQRS gives you the read-side: each event updates one or more purpose-built read models (sometimes called "projections") tailored to specific query needs.
- Together: write a `OrderPlaced` event → it updates a normalized order-events log (write side) → and *also* triggers updates to a denormalized "orders by customer" read table, a search index, and an analytics aggregate — each read model shaped for its own specific query pattern, all derived from the same source-of-truth event stream.

**When CQRS is overkill:**
- Simple CRUD applications where reads and writes use the same shape of data and read volume isn't dramatically higher than write volume — the added complexity of synchronizing two models buys you nothing.
- Early-stage products where you don't yet know what the actual hot read patterns will be — premature CQRS means building denormalized models for query patterns that might not even be the right ones.

**When CQRS is necessary:**
- Read volume vastly exceeds write volume and the read patterns are well understood and stable (e.g., a social feed, a product catalog search).
- Different parts of the system need fundamentally different views of the same data (e.g., a customer-facing dashboard vs an internal analytics pipeline) that would be awkward or slow to serve from one shared schema.

### Read Model Synchronization — Eventual Consistency Implications

- Because read models are updated asynchronously after a write (via events), there's a window where a write has committed but hasn't yet propagated to the read model.
- This means: a user could write an update and, for a brief moment, read back stale data from the read-side model — classic eventual consistency.
- Mitigations: route a user's *own* immediate read-after-write back to the write model (or a cache populated synchronously) right after their own write, while letting everyone else's reads go through the eventually-consistent read model.

> **Key insight:** CQRS isn't about using two databases for the sake of it — it's a direct consequence of accepting that "the best shape for writing data" and "the best shape for reading data" are frequently different, and trying to force one model to serve both well usually means it serves neither particularly well.

**Interview Q&A:**
- Q: "What is CQRS and when would you use it?"
  A: "CQRS means using separate models for writes and reads instead of one shared model. The write side stays normalized and consistency-focused; the read side is one or more denormalized models shaped specifically for the queries the application actually runs, kept in sync asynchronously — usually via events emitted on every write. I'd reach for it when read volume is much higher than write volume and the read access patterns are well understood, like a product catalog or a social feed. I'd avoid it for simple CRUD apps, or early in a product's life before you actually know what your hot read patterns are going to be — at that point the synchronization complexity isn't bought back by any real benefit."
- Q: "What's the consistency trade-off with CQRS?"
  A: "Since the read model is updated asynchronously after the write model commits, there's a window of eventual consistency where a user's own recent write hasn't propagated to the read side yet. The common mitigation is routing a user's immediate read-after-write back to the source of truth — or a synchronously-updated cache — right after their own write, while letting everyone else's reads continue to hit the eventually-consistent read model, which is fine for most other users since they weren't the one who just wrote it."

---

## 11. Backpressure

**What it is:** Backpressure is the mechanism by which a slow downstream consumer signals an upstream producer to slow down, instead of the producer continuing to push work faster than the consumer can absorb it.

**Why it exists / What problem it solves:** Without backpressure, a fast producer and a slow consumer leads to an ever-growing buffer between them — queue depth climbs, memory usage climbs, and eventually something runs out of memory or starts dropping data uncontrollably. Backpressure converts an unbounded, silent failure mode into an explicit, bounded, controllable one.

**How to implement it:**
- **Bounded queues:** give the buffer between producer and consumer a fixed maximum size. Once full, the producer is forced to either block (wait), drop the new item, or reject it explicitly — any of which is better than the queue growing without limit.
- **Flow control:** the consumer explicitly communicates its current capacity back to the producer (e.g., TCP's own flow control window, or an application-level "ready for N more" signal), so the producer only sends what the consumer has indicated it can currently handle.
- **Circuit breakers:** when a downstream dependency is failing or too slow, a circuit breaker stops sending it traffic entirely for a cooldown period, instead of continuing to pile on a system that's already struggling — this protects the struggling system and fails fast for the caller instead of queueing up timeouts.

**Kafka and backpressure:**
- Kafka doesn't have explicit producer-throttling backpressure built in by default — a slow consumer just falls behind, and **consumer lag** (the gap between the latest produced offset and the consumer's current offset) grows as the observable signal.
- In practice, "backpressure" in a Kafka-based system is handled operationally: monitor lag, alert on it, and scale consumers (or fix slow processing logic) before lag grows large enough that messages start aging out via retention and get lost — which is a real failure mode if the issue isn't caught.

> **Key insight:** Backpressure is fundamentally about making overload visible and actionable instead of invisible and catastrophic. A system without it doesn't avoid overload — it just hides the overload until something breaks suddenly, rather than degrading predictably and observably.

**Interview Q&A:**
- Q: "How do you handle backpressure in a distributed system?"
  A: "The core idea is to make a slow consumer's limits explicit to the producer instead of letting work pile up invisibly. Concretely, that means bounded queues — so a buffer has a hard size limit and forces an explicit decision (block, drop, or reject) once full, rather than growing unboundedly — and flow control, where the consumer signals its real-time capacity back to the producer. Circuit breakers help at the service level: if a downstream dependency is struggling, stop sending it traffic for a cooldown period instead of piling timeouts on top of an already-overloaded system. In a Kafka-based pipeline specifically, there's no built-in producer throttling, so the practical approach is treating consumer lag as the signal — monitoring it and scaling out consumers or fixing slow processing before lag grows large enough to risk messages aging out of retention."

---

## 12. Database Connection Pooling Revisited (Performance Angle)

**What it is:** Connection pooling means maintaining a reusable set of open database connections that the application borrows from and returns to, instead of opening a brand-new connection for every single query.

**Why it exists / What problem it solves:** Establishing a raw DB connection is expensive — it involves a TCP handshake, authentication, and (for Postgres specifically) forking a new backend process per connection. Doing this per-request at any real scale turns connection setup into the dominant cost of every query, and the database itself has a hard limit on how many concurrent connections it can sustain before performance degrades.

**How pooling helps:**
- A pool of already-established connections sits ready; the application checks one out, uses it, and returns it — no handshake/auth/process-fork cost on the hot path.
- This also implicitly caps how many connections actually reach the database, protecting it from being overwhelmed by, say, 500 application server threads all trying to open their own direct connection simultaneously.

### PgBouncer for PostgreSQL

PgBouncer is a lightweight connection pooler that sits between the application and Postgres, multiplexing many client connections onto a smaller number of actual database connections.

| Mode | Behavior | Trade-off |
|---|---|---|
| **Session mode** | A client gets a dedicated DB connection for its entire session (until it disconnects) | Safe for everything (full feature support, e.g. session-level settings, advisory locks) but pools less efficiently — connections are held even when idle |
| **Transaction mode** | A DB connection is only held for the duration of a single transaction, then returned to the pool immediately after commit/rollback | Much more efficient multiplexing — far more clients can share fewer real connections — but breaks anything that depends on session state persisting across transactions (e.g., session-level temp tables, certain prepared statement behaviors) |

**Why not always use transaction mode (it pools better)?** Some application patterns genuinely need session-level guarantees — and using transaction mode with code that assumes session persistence causes confusing, hard-to-debug failures. The choice depends on whether your application code is written to be transaction-mode-safe.

### Optimal Pool Size

A widely cited starting formula (from PostgreSQL connection pooling guidance, generalized):

```
connections = ((core_count * 2) + effective_spindle_count)
```

In practice, for modern SSD-backed systems, a simpler heuristic is often used: start with a pool size in the range of 2x-4x the number of CPU cores on the DB server, then load test and tune based on observed latency and DB CPU/connection utilization. The intuition: more connections than you have cores to actually execute concurrent queries just creates contention (context switching, lock contention) without adding real throughput — past a certain point, *more* connections make things slower, not faster.

### What Happens When the Pool Is Exhausted

- New requests needing a DB connection have to **wait** for one to free up.
- If wait time exceeds a configured timeout, the request fails outright.
- Under sustained load, this creates a backlog of waiting requests, which itself consumes memory and threads on the application side — and if enough requests pile up waiting, this becomes its own cascading failure, where the symptom ("requests are slow/failing") looks like a general app problem but the root cause is pool exhaustion specifically.

> **Key insight:** Connection pooling is one of the most common hidden bottlenecks in production systems — it's invisible until load crosses a threshold, at which point it becomes a sudden, confusing source of cascading timeouts that doesn't look like a "connections" problem on the surface.

**Interview Q&A:**
- Q: "Why is connection pooling important for scalability, and what happens without it?"
  A: "Opening a raw database connection is expensive — TCP handshake, authentication, and for Postgres specifically, forking a backend process — so doing that per query turns connection setup into your dominant latency cost at any real scale. Worse, every database has a hard ceiling on concurrent connections, and without pooling, a horizontally scaled fleet of app servers can easily try to open far more connections than the DB can sustain, degrading or crashing it. A connection pool reuses a fixed set of already-established connections and implicitly caps how many ever reach the database, which protects it and removes the per-query connection setup cost."
- Q: "What's the difference between PgBouncer's session mode and transaction mode?"
  A: "Session mode dedicates a real database connection to a client for as long as that client's session is open, which is fully safe for any feature that relies on session-level state, but doesn't pool efficiently since idle sessions still hold a connection. Transaction mode only holds a connection for the duration of a single transaction and returns it to the pool immediately after, which lets far more clients share a much smaller number of real connections — but it breaks anything that assumes state persists across transactions within the same session, so the application code has to actually be written to be safe under transaction-mode pooling."

---

## 13. Horizontal Scaling Patterns

**What it is:** A set of recurring patterns for actually making a horizontally scaled fleet of services work correctly together — not just "add more servers," but the supporting infrastructure that makes that safe and effective.

**Why it exists / What problem it solves:** Simply running more copies of a service doesn't automatically make a system correct or fast — you still need to handle session state, route requests to the right place, manage DB connections across a much larger number of total clients, and route reads vs writes correctly. These patterns are the standard answers to those problems.

### Stateless Services — The Prerequisite (Revisited)

As covered in Topic 1: any app server instance must be interchangeable. No request-specific data should live only on the server that happened to handle a previous request from the same user.

### Session Management at Scale

| Approach | How it works | Trade-off |
|---|---|---|
| **Sticky sessions** | The load balancer always routes a given user's requests to the same server instance, based on a cookie or IP hash | Simple, but defeats some of the point of horizontal scaling — if that one server goes down, the user's session goes with it, and load isn't perfectly balanced if some users are far more active than others |
| **Distributed session (Redis)** | Session data lives in a shared store (Redis), and any server instance can look it up for any user | True statelessness — any instance, any request — but adds a network hop to every request that needs session data, and now Redis itself needs to be highly available |

**Why distributed sessions are generally preferred at scale:** Sticky sessions reintroduce a soft form of statefulness through the back door — the *load balancer's routing decision* becomes state that, if lost, breaks the user's experience. Distributed sessions remove that entirely, at the cost of a Redis lookup per request, which is usually a worthwhile trade given how fast Redis is.

### Database Connection Management Across Horizontally Scaled App Servers

- More app server replicas means more total potential DB connections — this is exactly why connection pooling (Topic 12) becomes more critical, not less, as you scale horizontally. A pooler like PgBouncer sitting in front of the DB, shared across all app instances, prevents N replicas × M connections-per-replica from overwhelming the database.

### Read Replica Routing

- **What it is:** maintaining one or more read-only replicas of the primary database, and routing read queries to replicas while writes go to the primary.
- **How it's implemented at the application layer:** typically via a query router or an ORM-level read/write split — write operations (INSERT/UPDATE/DELETE) are pinned to the primary connection, while SELECT queries (where staleness is acceptable) are routed to a replica connection pool.
- **The catch:** replication is asynchronous, so a read immediately after a write might hit a replica that hasn't caught up yet (replication lag) — the same read-after-write consistency problem seen in CQRS. Mitigation is the same: route a user's own immediate read-after-write back to the primary, or to a cache populated synchronously at write time.

### Service Mesh (Istio, Linkerd)

**What it is:** A dedicated infrastructure layer (typically implemented as sidecar proxies running alongside each service instance) that handles service-to-service communication concerns — retries, timeouts, load balancing, mTLS encryption, observability — outside of application code.

**What problem it solves at scale:** As the number of services grows, each one re-implementing its own retry logic, timeout handling, circuit breaking, and TLS setup becomes duplicated, inconsistent, and hard to audit. A service mesh centralizes these cross-cutting concerns into the infrastructure layer (the sidecar), so application code can stay focused on business logic while the mesh handles "how do these services talk to each other safely and reliably."

**Why not just build this into each service?** You could, but every team reimplementing retry/timeout/mTLS logic slightly differently is a consistency and maintenance nightmare at real scale — a service mesh is the infrastructure answer to "let's not solve this N times."

> **Key insight:** Horizontal scaling isn't free just because you can spin up more containers — every one of these patterns exists because naively running N copies of a stateful-by-default application breaks in a specific, predictable way, and each pattern is the standard fix for one of those specific breakages.

**Interview Q&A:**
- Q: "How would you scale a service from 1,000 to 10 million users?"
  A: "I'd start by making sure the service is actually stateless, since that's the prerequisite for everything else — session data moves to Redis instead of local memory, file uploads move to object storage. Then horizontal scaling itself: more app server replicas behind a load balancer, with auto-scaling based on load. On the database side, that many users means read traffic likely dwarfs write traffic, so I'd introduce read replicas and route reads vs writes at the application layer, while watching out for replication lag on read-after-write paths. Connection pooling becomes critical at this point too, since many more app instances means many more potential DB connections. And if the service-to-service communication graph has grown complex, a service mesh centralizes retry, timeout, and mTLS logic instead of every service reimplementing it. The exact mix depends on where the actual bottleneck is — I'd profile first rather than apply all of these blindly."
- Q: "Sticky sessions vs distributed sessions — which would you choose and why?"
  A: "I'd default to distributed sessions via Redis, because sticky sessions quietly reintroduce statefulness — the load balancer's routing decision becomes a single point of failure for that user's session, and if that server goes down, the session goes with it. Distributed sessions mean any app instance can serve any request by looking up session state in Redis, which is the whole point of horizontal scaling. The cost is a network hop per request that needs session data, but Redis is fast enough that this is usually a good trade, and it removes a subtle failure mode that sticky sessions carry."

---

## 14. Bloom Filters

**What it is:** A Bloom filter is a space-efficient, probabilistic data structure that answers "is this item possibly in the set?" — and its key property is that it can have false positives, but **never** false negatives.

**Why it exists / What problem it solves:** Checking "does this key exist?" against a database is a real query with real latency and load. If you're doing that check very frequently — especially for keys that *don't* exist — you're paying full DB-query cost for a negative answer, every time. A Bloom filter lets you cheaply rule out "definitely not in the set" in memory, without touching the DB at all, and only fall through to the real DB check when the filter says "maybe."

**How it works:**
- A Bloom filter is a bit array, initially all zeros, plus several independent hash functions.
- To add an item: run it through each hash function, and set the bit at each resulting index to 1.
- To check membership: run the item through the same hash functions; if *any* of the resulting bit positions is 0, the item is **definitely not** in the set. If *all* are 1, the item is **possibly** in the set (it might be a different item whose hashes happened to collide on all the same bits).

**False positives vs false negatives:**
- **False positive** (says "maybe in set" when it's actually not): possible, and the rate is tunable based on filter size and number of hash functions.
- **False negative** (says "not in set" when it actually is): **impossible** by construction — if an item was ever added, every one of its hash-mapped bits was set to 1, so it will always pass the check.

**Use cases:**
- **URL shortener lookup:** before doing an expensive DB lookup to check if a short code already exists (to avoid collisions when generating new ones), check the Bloom filter first — if it says "definitely not," you can skip the DB call entirely and know the code is free.
- **Username availability check:** similarly, a quick in-memory "definitely not taken" check avoids hitting the DB for the common case of a genuinely available username, only falling through to a real DB check when the filter says "maybe taken" (which needs confirmation, since it could be a false positive).
- More broadly: any place you're checking "does X exist" against a large, mostly-static or slow-changing set, where most checks are expected to come back negative.

**Space efficiency vs false positive rate trade-off:**
- A larger bit array and more hash functions reduce the false positive rate, but cost more memory.
- The key efficiency win is that a Bloom filter is *dramatically* smaller than storing the actual set of items — you're trading a small, tunable false-positive rate for massive space savings, which is exactly the trade most "does X exist" pre-checks are happy to make.

> **Key insight:** A Bloom filter is never the final answer — it's a cheap, fast pre-filter that lets you skip expensive lookups for the common case (genuinely absent items), while still requiring a real check to confirm any positive result. It only adds value when negative checks vastly outnumber positive ones and the underlying lookup is expensive enough to be worth shortcutting.

**Interview Q&A:**
- Q: "What is a Bloom filter and where would you use one in system design?"
  A: "It's a probabilistic, space-efficient data structure that tells you 'definitely not in the set' or 'possibly in the set' — it can produce false positives, but never false negatives, because of how it sets hash-derived bits when items are added. A classic use case is a URL shortener: before generating a new short code, you check the Bloom filter first, and if it says 'definitely not in use,' you skip an expensive database lookup entirely. You only fall through to the real DB check when the filter says 'maybe,' since that could be a false positive. It's valuable specifically when negative checks vastly outnumber positive ones and the real lookup is expensive enough to be worth shortcutting."
- Q: "Why can a Bloom filter have false positives but never false negatives?"
  A: "When you add an item, you hash it through several independent hash functions and set the bit at each resulting position to 1. So if an item was genuinely added, every one of its bits is guaranteed to be 1 — checking it later will always find all its bits set, so it can never wrongly say 'not in set' for something that actually is. False positives happen because bit positions are shared across different items — another item's hashes might happen to set all the same bit positions that a never-added item would also map to, making the filter say 'maybe' for something that was never actually added."

---

## Quick Revision Cheatsheet

**Scaling**
- Vertical = bigger machine (ceiling exists, simpler, SPOF). Horizontal = more machines (no ceiling, needs statelessness, built-in redundancy).
- Statelessness is the prerequisite for horizontal scaling — push state to Redis/object storage.

**Caching**
- Hit = served from cache. Miss = fetch from origin, then populate cache.
- Eviction: LRU (default), LFU (skewed access), FIFO (rarely optimal), TTL (time-based).
- 80/20 rule: cache ~20% of data (the hot set), serve ~80% of traffic.
- Layers (closest to user → furthest): Client → CDN → App in-process (not shared) → Distributed (Redis, shared).
- Write strategies: Write-through (strong consistency, slow writes) · Write-back (fast writes, data-loss risk) · Write-around (skip cache on write, avoid polluting with write-once data) · Read-through (cache handles miss transparently).
- Invalidation: TTL (simple, stale window) · Event-driven/CDC (low staleness, more moving parts) · Versioned keys (avoid race conditions). Most systems combine TTL + one other.
- Thundering Herd fix: mutex lock on miss, probabilistic early expiration, or background refresh.

**Redis**
- String (counters, rate limit) · List (queue, feed) · Set (unique/membership) · **ZSet (leaderboards, sliding-window rate limit)** · Hash (objects like cart/profile) · HyperLogLog (approximate unique count, fixed tiny memory) · Pub/Sub (ephemeral, NOT durable).
- RDB (snapshot, fast restore, more data loss) vs AOF (write log, less data loss, slower restore). Often both.
- Sentinel = automatic failover. Cluster = sharding via hash slots (consistent hashing).
- Redis > Memcached by default (data structures, persistence, HA); Memcached only wins on pure simple-KV raw throughput.

**Message Queues / Kafka**
- Queues decouple producer/consumer — failures and latency stop cascading.
- At-most-once (may lose) · At-least-once (may duplicate, default in practice — make consumers idempotent) · Exactly-once (hardest, rarely fully achieved end-to-end).
- Kafka = durable, replayable, partitioned **log** (not destructive on read) — not a traditional queue.
- Ordering guaranteed **per-partition only**, never globally across a topic.
- Kafka vs RabbitMQ vs SQS: Kafka = high-throughput/replay/event-streaming; RabbitMQ = complex routing/low-latency tasks; SQS = managed/simple/AWS-native.
- Partition key = same problem as shard key — pick high-cardinality, even distribution, avoid hot partitions.
- Consumer lag = the backpressure signal in Kafka (no built-in producer throttling).

**Event-Driven Architecture / CQRS**
- Event (fact, past tense, loose coupling) vs Command (instruction to a specific receiver, tighter coupling).
- Event sourcing: store events, derive state by replay. Pro: audit log, replay, time travel. Con: query complexity, schema evolution.
- Choreography (no central coordinator, loosely coupled, hard to debug complex flows) vs Orchestration (central coordinator, easier to reason about complex/multi-step workflows).
- Outbox pattern: write event + data change in one DB transaction → separate process publishes to Kafka → solves the dual-write atomicity problem.
- CQRS: separate write model (consistency-focused) and read model(s) (denormalized, query-shaped), synced via events. Necessary when read volume >> write volume with stable patterns; overkill for simple CRUD.

**Backpressure**
- Downstream signals upstream to slow down — bounded queues, flow control, circuit breakers.
- Without it: unbounded queue growth → memory exhaustion → crash, instead of a controlled, visible slowdown.

**Connection Pooling**
- Raw connections are expensive (handshake, auth, process fork) — pools reuse them.
- PgBouncer session mode (safe, less efficient pooling) vs transaction mode (efficient pooling, breaks session-state-dependent code).
- Pool size ≈ 2-4x DB server CPU cores as a starting heuristic, then load test.
- Exhausted pool → requests queue/timeout → looks like a general app slowdown but the root cause is connection-specific.

**Horizontal Scaling Patterns**
- Sticky sessions (simple, reintroduces a SPOF) vs distributed sessions/Redis (true statelessness, default choice at scale).
- Read replica routing: writes → primary, reads → replica; watch for replication lag on read-after-write.
- Service mesh (Istio/Linkerd): centralizes retries/timeouts/mTLS/observability as infrastructure instead of duplicated app code.

**Bloom Filters**
- Probabilistic "definitely not in set" / "maybe in set." False positives possible, false negatives impossible.
- Use for cheap pre-checks before an expensive lookup (URL shortener collision check, username availability) when most checks are expected negative.
- Trade-off: bigger filter + more hash functions = lower false-positive rate, more memory.
