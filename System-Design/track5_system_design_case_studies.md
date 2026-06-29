# Track 5: System Design in Practice — Case Studies
### System Design Self-Study Series for Gautham Gokulakonda

---

> **Why this track matters:** This is the capstone track where all concepts from Tracks 1–4 are applied to real-world systems. Each of the 15 case studies follows the same 7-step structure used in real system design interviews.

**Case Studies Covered:** URL Shortener · Rate Limiter · Pastebin · Instagram · Twitter · WhatsApp · YouTube · Uber · Google Drive · Notifications · Search Autocomplete · Web Crawler · Distributed Cache · Payment System · Ticket Booking

---

# How to Use This Guide
This is Track 5 of the System Design Self-Study Series — the capstone track where all concepts from Tracks 1–4 are applied to real-world systems. Each of the 15 case studies follows the same 7-step structure used in real system design interviews.

**How Each Case Study is Structured**

**Step 1 (5 min)**

Clarify Requirements — Ask these questions at the start of every interview. Missing this step costs you points.

**Step 2**

Capacity Estimation — Show the interviewer you can reason about scale. Back every design decision with numbers.

**Step 3**

High-Level Design — Start broad. Draw the components. Explain the data flow. Only go deep when the interviewer asks.

**Step 4**

Data Modelling — Know your schema cold. Interviewers at Razorpay and Flipkart often probe this more than the architecture.

**Step 5**

API Design — REST endpoints, request/response shapes, idempotency. Indian unicorn interviews love this section.

**Step 6**

Key Design Decisions — Every choice has a trade-off. Name it before the interviewer asks "why not X?"

**Step 7**

Bottlenecks — Show you can reason about failure. This separates Senior from Staff in most FAANG rubrics.

**Q&A Box**

These are the actual follow-up questions you'll get. Practice answering them out loud in 60–90 seconds.

**Interview Strategy by Company Type**

- FAANG (Google, Meta, Amazon): Follow the 7 steps in order. Expect the interviewer to cut you off after the high-level design and say "let's deep-dive into X" — be ready to go very deep on any component.
- Indian Unicorns (Razorpay, PhonePe, Flipkart, Swiggy, Zepto): Spend more time on data modelling and API design. Interviewers here care about practical implementation — "how exactly would you implement idempotency?" is more common than "how does consistent hashing work?"
- Both: Always start with clarifying questions. Always mention trade-offs. Always relate your choices to your own experience — reference Kafka usage at Deepta AI, Redis caching patterns you've seen, or Kubernetes autoscaling in your GCP setup.

## 1. Design a URL Shortener (TinyURL)
**Difficulty**

Beginner

**Asked At**

Google, Amazon, Flipkart, Swiggy

**Time Budget**

35–40 min

**Core Concepts Tested**

- Hashing and ID generation (collision avoidance)
- Key-value store design and Redis caching
- HTTP redirect semantics (301 vs 302)
- Read-heavy scale — how to serve millions of redirects per second
- URL expiry and background cleanup

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- What is the expected daily active users (DAU) and how many URLs are shortened per day?
- Should shortened URLs expire? If so, who controls expiry — the user or the system?
- Do we need analytics (click counts, referrer, geo data per URL)?
- Is custom alias support required (e.g. tiny.url/mycompany)?
- Should the redirect be permanent (301) or temporary (302) — does SEO matter for the use case?
- Is there a need for a REST API for third-party integrations, or just a web UI?
- Do we need authentication — should users be able to manage their own URLs?

**Assumptions (After Clarification)**

- Functional: Create short URL from long URL; redirect short → long; optional expiry; optional custom alias; basic click analytics
- 100M DAU; 100:1 read:write ratio
- Non-functional: Redirect latency < 50ms (p99); 99.99% availability; URL stored for max 5 years

### Step 2: Capacity Estimation
**Component**

**Role**

**DAU**

100M users

**Write QPS**

100M * 10 URLs/day = ~11,500 writes/sec (round to 12K)

**Read QPS**

100:1 ratio → ~1.15M reads/sec (round to 1.2M)

**URL size**

Long URL ~2KB, short key 7 chars = ~7 bytes, metadata ~100B → ~2.1KB/record

**Storage (5yr)**

12K writes/sec * 86400 * 365 * 5 = ~1.9TB of URL data

**Bandwidth**

1.2M reads/sec * 2KB = ~2.4GB/s read bandwidth — must be cached aggressively

### Step 3: High-Level Design
*The system has two main flows: the write path (shorten a URL) and the read path (redirect). Because read QPS is 100x write QPS, the read path must be heavily optimized — this is where Redis earns its place.*

**Core Components**

**Component**

**Role**

**API Gateway**

Receives all client requests; rate limits per IP; routes to URL Service or Analytics Service

**URL Service**

Core microservice: generates short IDs, writes to DB, reads from cache; exposes REST endpoints

**Redis Cache**

Caches shortCode → longURL mappings; handles 99%+ of redirect reads with sub-millisecond latency

**PostgreSQL (Primary DB)**

Source of truth for all URLs; handles writes and cache misses; partitioned by shortCode hash

**Analytics Service**

Consumes click events from Kafka; aggregates click stats asynchronously; does not block redirect

**Kafka**

On each redirect, URL Service publishes a click event; Analytics Service consumes it; write-behind pattern

**Cleanup Worker**

Background job that runs nightly; marks expired URLs as inactive and evicts from Redis

**Data Flow — Shorten URL**

1. Client sends POST /shorten with {longUrl, customAlias?, ttlDays?}
2. URL Service generates a unique 7-char shortCode (Base62)
3. Checks Redis + DB for collision; regenerates if collision found (rare)
4. Writes to PostgreSQL: INSERT into urls table
5. Warms Redis: SET shortCode → longURL with TTL
6. Returns short URL to client

**Data Flow — Redirect**

1. Client sends GET /{shortCode}
2. URL Service checks Redis first: GET shortCode → 99% cache hit, return 302 redirect instantly
3. On cache miss: query PostgreSQL WHERE short_code = ? ; warm Redis; return redirect
4. Asynchronously publish click event to Kafka topic "url.clicks"
5. Analytics Service consumes from Kafka and updates click_stats table

### Step 4: Data Modelling
**Table: urls**

**Component**

**Role**

**id (BIGINT PK)**

Auto-increment; used internally

__short_code (VARCHAR 10)__

Base62 encoded ID; UNIQUE INDEX — this is the primary lookup key

__long_url (TEXT)__

The original URL, up to 2048 chars

__user_id (BIGINT FK)__

Owner of the URL (nullable if anonymous)

__expires_at (TIMESTAMPTZ)__

NULL means no expiry; indexed for cleanup worker queries

__created_at (TIMESTAMPTZ)__

Immutable, set on insert

__is_active (BOOLEAN)__

Soft delete; cleanup worker sets to false when expired

__Table: click_stats (Analytics)__

**Component**

**Role**

__short_code (VARCHAR 10)__

FK to urls; partition key for TimescaleDB or Cassandra

__clicked_at (TIMESTAMPTZ)__

Time of click; enables time-series aggregation

**country (VARCHAR 2)**

Derived from IP via GeoIP lookup

**referrer (TEXT)**

HTTP Referer header

__user_agent (TEXT)__

Device/browser info

**Storage Choice: **PostgreSQL for URL metadata (relational, ACID, strong consistency needed for ID uniqueness). Redis for the read hot path. For click_stats at scale, consider Cassandra or TimescaleDB — write-heavy, time-series, append-only, no JOINs needed.

### Step 5: API Design
**Component**

**Role**

**POST /api/v1/shorten**

Body: {longUrl, customAlias?, ttlDays?}. Returns: {shortUrl, expiresAt}. 201 Created.

**GET /{shortCode}**

Redirect endpoint. Returns 302 (or 301 if user selects permanent). Body empty. Location header set.

**GET /api/v1/urls/{shortCode}/stats**

Returns: {totalClicks, clicksByDay[], clicksByCountry[]}. Auth required.

**DELETE /api/v1/urls/{shortCode}**

Soft-deletes URL (sets is_active=false). Auth required. 204 No Content.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Base62 encoding for short codes (not UUID, not sequential integer)**

**Why**

Base62 (a-z, A-Z, 0-9) gives 62^7 = ~3.5 trillion unique codes from 7 characters. Human-readable, URL-safe, compact. A sequential integer would leak business metrics (total URL count). UUID is 36 chars — too long for a "short" URL.

**Trade-off**

Not truly random — a determined attacker could guess short codes by brute force. Mitigation: add a random salt or use a counter-based approach with a secret offset.

**Alternative**

Use a counter-based approach with a distributed ID generator (like Twitter Snowflake) and then Base62-encode the counter. This avoids collision entirely but requires a distributed counter service.

**DECISION**

**302 (Temporary) Redirect instead of 301 (Permanent)**

**Why**

With 302, the browser always asks our server before redirecting. This lets us: (a) count every click accurately, (b) update or deactivate URLs after creation, (c) capture analytics. With 301, the browser caches the redirect forever and never calls us again.

**Trade-off**

Slightly higher server load because every redirect hits our service. For extremely high-traffic URLs, we lose the browser-level caching benefit.

**Alternative**

Use 301 if analytics are not required and you want maximum performance via browser caching. Some teams use a hybrid: 302 for the first N clicks, then switch to 301 when a URL is proven stable.

**DECISION**

**Redis as cache, not primary store**

**Why**

Redis is a cache (eviction policies, volatile-lru), not a database. PostgreSQL is the source of truth. On Redis failure, we fall back to PostgreSQL — the system degrades gracefully. If Redis were primary, a failure would take down all redirects.

**Trade-off**

Every new URL requires a write to both PostgreSQL and Redis (dual-write). A small window exists where Redis has stale data after a URL is deactivated.

**Alternative**

For extreme scale (Twitter-level), you could use a dedicated distributed KV store like Apache Cassandra or DynamoDB as the primary store and remove the SQL layer entirely.

### Step 7: Bottlenecks & How to Address Them
- Read QPS at 1.2M/sec overwhelms any single DB: Solved by Redis cache. With a 99% hit rate, PostgreSQL only handles 12K read QPS (cache misses) — easily handled by read replicas.
- Single Redis node becomes a SPOF: Use Redis Cluster (horizontal sharding by shortCode hash) with sentinel/AOF persistence. For GCP, use Memorystore Redis with automatic failover.
- Hot URLs (viral content): A single short code receiving 100K req/sec saturates even Redis. Solution: use local in-memory cache (sync.Map in Go) for the top-1000 most-accessed codes. Refresh every 30 seconds from Redis.
- ID generation under high concurrency: Multiple URL Service instances generating IDs simultaneously could collide. Solution: pre-allocate ranges from a counter service (ZooKeeper or PostgreSQL sequence), assign each server a range, generate IDs locally within that range.
- Cleanup of expired URLs: A naive SELECT WHERE expires_at < NOW() across 2TB of data is slow. Solution: partition the urls table by expires_at month, so cleanup only scans the relevant partition.

### Interview Q&A
**Q: **How would you handle a viral URL that receives 1 million requests per second?

**A: **Three layers of caching: (1) local in-process cache in each URL Service pod (Go sync.Map, evict every 30 seconds), (2) Redis cluster (shared across all pods), (3) CDN-level caching for predictable patterns. For truly viral URLs, CDN edge nodes serve the redirect without the request ever reaching our infrastructure.

**Q: **Why not use a database auto-increment ID as the short code directly?

**A: **It exposes business metrics (total URLs created = last ID). It also creates a predictable enumeration attack — anyone can crawl all URLs by iterating IDs. Base62 encoding with a random offset provides opacity. Some teams XOR the counter with a secret key before encoding.

**Q: **How do you handle custom aliases colliding with an existing short code?

**A: **Before inserting, check if the alias exists (SELECT from DB, not just Redis since cache might be cold). If taken, return 409 Conflict with a suggestion. The DB has a UNIQUE constraint on short_code as the final safety net, so even a race condition is caught at the DB level.

## 2. Design a Rate Limiter
**Difficulty**

Intermediate

**Asked At**

Google, Amazon, Razorpay, PhonePe, Zepto

**Time Budget**

35–40 min

**Core Concepts Tested**

- Algorithm selection: token bucket, leaky bucket, fixed window, sliding window
- Distributed rate limiting across multiple API server replicas
- Redis atomic operations (INCR, Lua scripts) for consistency
- Granularity: per-user, per-IP, per-API-key, global per-endpoint
- Graceful rejection with proper HTTP 429 responses and Retry-After headers

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- Is this a client-side or server-side rate limiter? (API gateway level vs per-service)
- What is the granularity? Per user ID, per IP, per API key, or global per endpoint?
- Hard limit (drop request) or soft limit (queue and delay)? What happens when the limit is hit?
- Do different API endpoints need different rate limits (e.g. login: 5/min, feed: 100/min)?
- Should limits be configurable at runtime without code deployment?
- What latency overhead is acceptable for the rate limiter check? (< 1ms is typical target)
- Is there a need for rate limit bypass for internal services or premium users?

**Assumptions (After Clarification)**

- Server-side rate limiter running in API Gateway layer (not in each microservice)
- Granularity: per user-ID for authenticated requests; per IP for unauthenticated
- Hard limit: reject with 429 Too Many Requests immediately
- Different rules per endpoint stored in a config service (Redis Hash); rules: 100 req/min for most APIs, 5 req/min for login/OTP
- p99 overhead < 2ms (one Redis round-trip)

### Step 2: Capacity Estimation
**Component**

**Role**

**API servers**

50 instances (Kubernetes pods), each handling ~2K req/sec

**Total QPS**

100K req/sec at peak

**Rate limit checks**

One Redis command per request = 100K Redis ops/sec

**Redis throughput**

Redis handles ~1M ops/sec on a single node — well within budget

**Memory (sliding window)**

1 sorted set per user per endpoint. 100K active users * 10 endpoints * avg 100 entries = ~500MB

### Step 3: High-Level Design
*The rate limiter sits in the API Gateway as middleware. Every incoming request passes through it. The gateway checks Redis for the current count/tokens, decides allow/reject, and only forwards allowed requests to downstream services.*

**Algorithm Comparison (Interview Must-Know)**

**Algorithm**

**How it works**

**Pros**

**Cons**

Fixed Window

Counter resets every minute boundary

Simple; O(1) space

Burst attack at window boundary: 200 reqs in 2 sec by straddling two windows

Sliding Window Log

Sorted set of timestamps; count entries in last 60s

Accurate; no boundary burst

High memory: stores every request timestamp

Sliding Window Counter

Hybrid: weighted sum of current + prev window

Memory efficient; near-accurate; O(1)

Slight over/under-counting (~0.003% error)

Token Bucket

Bucket fills at rate R; each request takes 1 token

Allows bursting; smooth; widely used

Slightly complex implementation; distributed sync needed

Leaky Bucket

Queue; processes at fixed rate; excess dropped

Smooth output rate guaranteed

Queue adds latency; not good for bursty workloads

**Recommendation: **Use Sliding Window Counter for most APIs — memory-efficient, accurate enough, and simple to implement in Redis. Use Token Bucket for APIs that legitimately need burst support (e.g. a dashboard loading 20 API calls simultaneously on page load).

**Core Components**

**Component**

**Role**

**API Gateway (Go)**

Middleware intercepts every request; calls RateLimiter.Allow(userID, endpoint); rejects or forwards

**Rate Limiter Service**

Stateless Go service; implements algorithm logic; calls Redis for state; returns allow/deny + headers

**Redis Cluster**

Stores rate limit state (counters, sorted sets, token buckets); atomic ops via Lua scripts

**Config Store (Redis Hash)**

Maps endpoint patterns to rate limit rules; polled every 30 seconds by each gateway instance; allows runtime config changes

**Metrics + Alerting**

Track rate_limited_requests_total by endpoint and user tier; alert if > X% of traffic is being rate limited (DDoS signal)

**Sliding Window Counter — Redis Implementation**

Two counters: current window (curr) and previous window (prev). Weighted sum = prev * ((window_size - elapsed) / window_size) + curr.

-- Lua script (atomic): check and increment

local key_curr = KEYS[1]   -- "rl:{userId}:{endpoint}:{currentMinute}"

local key_prev = KEYS[2]   -- "rl:{userId}:{endpoint}:{prevMinute}"

local limit = tonumber(ARGV[1])

local elapsed = tonumber(ARGV[2])  -- seconds into current window

local prev = tonumber(redis.call("GET", key_prev) or 0)

local curr = tonumber(redis.call("GET", key_curr) or 0)

local weight = (60 - elapsed) / 60

local count = math.floor(prev * weight + curr)

if count >= limit then return 0 end

redis.call("INCR", key_curr)

redis.call("EXPIRE", key_curr, 120)

return 1

### Step 4: Data Modelling
**Redis Key Schema**

**Component**

**Role**

**rl:{userId}:{endpoint}:{minute}**

Sliding window counter. Type: String (integer). TTL: 120s (two windows).

__rl:config:{endpoint_pattern}__

Rate limit rules. Type: Hash. Fields: limit (int), window (int), algorithm (str).

**rl:exempt:{userId}**

Users exempt from rate limiting (internal services, premium). Type: String. Value: "1".

**HTTP Response on Rate Limit (429)**

HTTP/1.1 429 Too Many Requests

X-RateLimit-Limit: 100

X-RateLimit-Remaining: 0

X-RateLimit-Reset: 1719500460   (Unix timestamp of window reset)

Retry-After: 45

{"error": "rate_limit_exceeded", "message": "Too many requests. Retry after 45 seconds."}

### Step 5: API Design
**Component**

**Role**

**Middleware: Allow(userID, endpoint)**

Internal call from gateway. Returns: {allowed: bool, remaining: int, resetAt: time}. Not exposed externally.

**GET /admin/v1/rate-limit/rules**

Returns current rate limit rules per endpoint. Admin only.

**PUT /admin/v1/rate-limit/rules/{endpoint}**

Update rule for endpoint at runtime: {limit, window, algorithm}. Admin only. Propagates via Redis.

**GET /admin/v1/rate-limit/status/{userId}**

Current counter state for a user. Useful for debugging. Admin only.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Centralised Redis for rate limit state (not local in-memory counter per pod)**

**Why**

With 50 API gateway pods, a local counter would allow 50x the actual limit (each pod allows 100 requests independently). Centralised Redis ensures the limit is enforced globally across all pods.

**Trade-off**

Every request makes a network call to Redis (~0.5ms). This adds latency to every API call. On Redis downtime, you must decide: fail open (allow all) or fail closed (reject all). Fail open is safer for availability.

**Alternative**

Local in-memory counter + periodic sync to Redis. Allows a small burst above the limit (proportional to sync interval) but removes the Redis call from the hot path. Works well for soft limits.

**DECISION**

**Lua scripts for atomic check-and-increment in Redis**

**Why**

A non-atomic read → check → write sequence has a race condition: two concurrent requests both read count=99, both pass the check, and both increment to 100, allowing 101 requests. A Lua script runs atomically on the Redis server, eliminating the race entirely.

**Trade-off**

Lua scripts cannot be used across Redis Cluster nodes (scripts are node-local). Keys must be on the same shard. We use hash tags: {userId} to ensure all keys for a user land on the same shard.

**Alternative**

Redis MULTI/EXEC transactions are an alternative but still make multiple round-trips. Lua is preferred. For extreme performance, consider a dedicated in-process rate limiter with Redis only for sync.

### Step 7: Bottlenecks & How to Address Them
- Redis single point of failure: Use Redis Sentinel (automatic failover) or Redis Cluster (horizontal sharding). On GCP, Memorystore Redis offers managed HA. For rate limiting, a brief Redis outage can be handled by failing open — log the gap and alert.
- Hot user causing Redis hot key: A single user hammering 100K req/sec concentrates all traffic on one Redis shard. Solution: use local in-process cache to absorb the rate limit check for the same user within a 100ms window before hitting Redis.
- Config propagation delay: Rate limit rules stored in Redis need to propagate to all 50 gateway pods. Each pod polls Redis every 30 seconds. There is a 30-second window where a new rule is not yet active. Mitigation: pub/sub channel for immediate invalidation.
- Bypass via IP rotation: A bot using thousands of IPs bypasses per-IP limiting. Solution: Layer multiple strategies — per-IP, per-account, per-device fingerprint, and behavioural analysis (rapid succession of failed requests triggers a challenge).

### Interview Q&A
**Q: **What happens if Redis goes down while the rate limiter is running?

**A: **Fail open: temporarily allow all requests and log the incident. A rate limiter outage causing 100% traffic rejection is worse than briefly exceeding limits. Set an alert: if Redis is unreachable for > 5 seconds, page the on-call team. Use circuit breaker pattern: after N consecutive Redis failures, switch to local in-memory fallback mode.

**Q: **How do you handle a user who has both free and premium rate limits depending on their subscription?

**A: **The config store maps user tier to limit rules. On each request, the gateway reads the user tier from the JWT claims (or from a fast user-info cache), selects the appropriate rule key, and passes it to the rate limiter. Premium users might get 1000 req/min vs 100 for free users. This is resolved at config lookup time, not hard-coded.

## 3. Design Pastebin / Code Sharing
**Difficulty**

Beginner–Intermediate

**Asked At**

Amazon, Microsoft, Atlassian (Bitbucket Snippets)

**Time Budget**

30–35 min

**Core Concepts Tested**

- Object storage vs database for large content
- Unique ID generation with collision avoidance
- CDN for frequently accessed pastes
- Background expiry handling
- Syntax highlighting and read/write access control

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- What is the maximum size of a paste? (Pastebin allows up to 512KB)
- Do we need user accounts, or can anyone create an anonymous paste?
- Is paste visibility public/private/unlisted? Can the owner share a private URL?
- Does the paste expire? Is expiry user-controlled or system-enforced?
- Do we need syntax highlighting? Full-text search across pastes?
- Read vs write ratio estimate — is this more read-heavy or write-heavy?

**Assumptions (After Clarification)**

- Functional: Create paste; view paste by ID; optional expiry; optional owner-set visibility; no full-text search in scope
- Max paste size: 512KB; 10M DAU; 10:1 read:write ratio
- Non-functional: View latency < 100ms; 99.9% availability; data stored for up to 10 years

### Step 2: Capacity Estimation
**Component**

**Role**

**DAU**

10M users

**Write QPS**

10M * 2 pastes/day / 86400 = ~230 writes/sec

**Read QPS**

10:1 → ~2300 reads/sec

**Paste avg size**

30KB (code files are small on average)

**Storage (10yr)**

230 writes/sec * 86400 * 365 * 10 * 30KB = ~22TB. Store in object storage (GCS/S3), not DB.

**Metadata size**

~500B per paste * 230 writes/sec * 10yr = ~36GB for metadata DB (trivial for PostgreSQL)

### Step 3: High-Level Design
*The key insight here: paste content should NOT go into a relational database. 22TB of text blobs would destroy DB performance. Content goes to object storage; only metadata (ID, owner, expiry, language, visibility) goes to PostgreSQL.*

**Core Components**

**Component**

**Role**

**Paste Service**

Handles create and read; generates IDs; writes content to GCS; writes metadata to PostgreSQL; reads from CDN/GCS on view

**Google Cloud Storage (GCS)**

Stores paste content as objects; key = {pasteId}; 99.999999999% durability; cheap at scale

**CDN (Cloudflare / Cloud CDN)**

Caches public paste content at edge; dramatically reduces GCS egress costs; TTL-based invalidation on update/delete

**PostgreSQL**

Stores paste metadata: ID, owner, language, visibility, expiry, created_at, hit_count

**Redis Cache**

Caches hot paste metadata (ID → metadata) for sub-millisecond lookup; also caches the paste content itself for very hot pastes

**Expiry Worker**

Cron job running every hour; SELECT * FROM pastes WHERE expires_at < NOW(); marks as expired; sends GCS delete; evicts from CDN via purge API

**Data Flow — Create Paste**

1. Client sends POST /paste with {content, language, expiryHours?, visibility}
2. Paste Service generates a unique 8-char Base62 pasteId
3. Uploads content to GCS: PUT gs://pastes-bucket/{pasteId} with content-type: text/plain
4. Writes metadata to PostgreSQL
5. Returns {pasteId, url: "paste.bin/{pasteId}"}

**Data Flow — View Paste**

1. Client requests GET /paste/{pasteId}
2. CDN checks cache (for public pastes) — cache hit: serve from edge, done
3. CDN miss → Paste Service checks Redis for metadata (expiry, visibility)
4. If expired or private (and requester not owner): return 404 or 403
5. Fetch content from GCS: GET gs://pastes-bucket/{pasteId}
6. Serve content; CDN caches the response for public pastes

### Step 4: Data Modelling
**Table: pastes**

**Component**

**Role**

__paste_id (VARCHAR 10)__

Base62 encoded; PRIMARY KEY; used as GCS object name

__owner_id (BIGINT FK)__

Nullable for anonymous pastes

**language (VARCHAR 30)**

Syntax highlighting hint: "python", "golang", "sql", etc.

**visibility (ENUM)**

"public", "private", "unlisted"; controls CDN cachability

__expires_at (TIMESTAMPTZ)__

NULL = never expires; INDEX for cleanup worker

__size_bytes (INT)__

Size of content in GCS; for display and quota enforcement

__hit_count (BIGINT)__

Incremented asynchronously (Kafka counter consumer); approximate view count

__created_at (TIMESTAMPTZ)__

Immutable creation time

**Why GCS over PostgreSQL for content: **PostgreSQL stores data in pages (8KB blocks). A 512KB paste would span 64 pages and bloat the buffer cache with non-indexed data. GCS costs ~$0.02/GB/month vs ~$0.10/GB for managed PostgreSQL — 5x cheaper, with no performance penalty for the DB.

### Step 5: API Design
**Component**

**Role**

**POST /api/v1/paste**

Body: {content, language, visibility, expiryHours?}. Returns: {pasteId, url, expiresAt}. 201 Created.

**GET /p/{pasteId}**

Returns paste content (text/plain or text/html with highlighting). 200 OK or 404/403.

**DELETE /api/v1/paste/{pasteId}**

Owner or admin only. Deletes from GCS + marks metadata as deleted. 204 No Content.

**PUT /api/v1/paste/{pasteId}**

Update visibility or extend expiry. Does NOT change content (immutable after creation). 200 OK.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Content stored in GCS (object storage), not PostgreSQL TEXT column**

**Why**

Object storage is purpose-built for large, unstructured, immutable blobs. It scales to exabytes, costs 5x less than DB storage, and does not degrade DB query performance. PostgreSQL TEXT columns of 512KB would bloat shared_buffers and slow down all other queries on the table.

**Trade-off**

Two separate storage systems to manage (GCS + PostgreSQL). On a GCS write failure, we must roll back the PostgreSQL metadata insert. Use a transactional outbox pattern or simply retry the GCS write before committing the metadata.

**Alternative**

For a simpler system (small scale, < 1TB), storing content as BYTEA in PostgreSQL is fine and removes the two-system complexity. Only reach for object storage when scale demands it.

**DECISION**

**CDN caching for public pastes**

**Why**

Public pastes are immutable after creation (content does not change, only metadata). They are perfect CDN candidates. A popular paste shared on Hacker News could receive 100K views in an hour — CDN handles this with zero load on our backend.

**Trade-off**

Private pastes cannot be CDN-cached (they must go to origin every time). For mixed public/private traffic, CDN only helps the public fraction. CDN costs for egress must be budgeted.

**Alternative**

Without CDN: serve all content from GCS directly via signed URLs. GCS is highly available but more expensive for high-egress workloads and adds latency for geographically distant users.

### Step 7: Bottlenecks & How to Address Them
- ID collisions: With Base62^8 = ~218 trillion codes, collision probability is negligible at our scale. But for production safety: attempt INSERT; if UNIQUE violation, regenerate. Log collision count as a metric — if it grows, switch to counter-based generation.
- GCS latency for hot pastes: A paste that goes viral faces GCS latency (50–200ms per fetch). CDN solves this for public pastes. For private pastes, cache the content in Redis with a 5-minute TTL and LRU eviction.
- Expiry cleanup at scale: At 10 years of data, the pastes table has ~72 billion rows (unrealistic but illustrative). Partition by created_at year. Expiry worker scans only the relevant partitions. For best performance, also maintain a separate expiry_queue table sorted by expires_at — the worker only reads from this queue.

### Interview Q&A
**Q: **How do you prevent abuse — someone uploading illegal content or malware as a paste?

**A: **Multiple layers: (1) content scanning on upload using Cloud DLP or ClamAV for malware signatures; (2) DMCA takedown endpoint for legal requests; (3) rate limiting per IP/user to prevent bulk uploads; (4) hash-based blocklist: compute SHA-256 of content on upload, check against a known-bad-content blocklist (similar to PhotoDNA for images). Flag for manual review if uncertain.

**Q: **If a user deletes a paste, how do you ensure the content is actually gone from the CDN?

**A: **Send a CDN purge API call (Cloudflare: DELETE /zones/{zone}/purge_cache) immediately on delete. The metadata is marked deleted in PostgreSQL so even if CDN serves a stale response for a brief window, the Paste Service will return 404 on re-validation. For compliance (GDPR), GCS deletion is instant; CDN propagation takes up to 60 seconds globally.

## 4. Design Instagram / Photo Sharing
**Difficulty**

Intermediate

**Asked At**

Meta, Google, Amazon, Flipkart (Myntra)

**Time Budget**

45–50 min

**Core Concepts Tested**

- Media upload pipeline: chunked upload, async processing, CDN distribution
- Fan-out for newsfeed generation (the core system design challenge)
- Image processing pipeline: resizing, format conversion (WebP), thumbnail generation
- Storage hierarchy: S3/GCS for originals, CDN for delivery
- Social graph: follower/following relationships and how they affect feed queries

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- What features are in scope? (Upload photo, follow users, view feed, like/comment?)
- Is the feed chronological or ranked? (Instagram switched from chronological to ML-ranked in 2016)
- What is the expected scale? DAU, number of photos uploaded per day?
- Video support or photos only? (Changes the upload pipeline significantly)
- Geographic distribution — global or India-only? (CDN edge node placement)
- What is the maximum following count? (500 vs 50M — affects fan-out strategy)

**Assumptions (After Clarification)**

- Functional: Upload photo; view home feed (chronological); follow/unfollow users; like photos; view profile
- 300M DAU; 5M photos uploaded per day; average photo size 3MB (original), 200KB (compressed)
- Chronological feed for simplicity (not ML-ranked)
- Max followers per account: 50M (need celebrity handling)
- Non-functional: Feed load < 200ms; photo view < 100ms; 99.9% availability

### Step 2: Capacity Estimation
**Component**

**Role**

**Photo uploads/day**

5M photos → ~58 writes/sec

**Photo views/day**

300M DAU * 30 photos viewed = 9B views/day → 104K reads/sec

**Upload bandwidth**

58 writes/sec * 3MB original = 174MB/s inbound

**Storage (5yr)**

5M photos/day * 365 * 5 * 200KB (compressed) = ~1.8PB for processed images

**Original storage**

5M * 3MB * 365 * 5 = ~27PB for originals — likely tiered to cold storage after 90 days

**CDN egress**

104K reads/sec * 200KB = ~20GB/s — must be CDN-served

### Step 3: High-Level Design
**Core Components**

**Component**

**Role**

**Upload Service**

Receives photo upload (multipart); generates photo_id; stores original in GCS; publishes to Kafka "photo.uploaded"

**Image Processing Worker**

Consumes "photo.uploaded" from Kafka; generates multiple sizes (thumb 150px, medium 640px, large 1080px); converts to WebP; stores processed versions in GCS; updates photo metadata

**CDN (Cloud CDN)**

Serves all processed images; photo URL includes size hint: cdn.insta.app/{photoId}/{size}.webp; long TTL (1 year) since images are immutable after processing

**Feed Service**

Generates home feed for a user; fan-out strategy determines whether this reads from Redis or queries a feed table

**Social Graph Service**

Stores follower/following relationships; used by Feed Service to determine whose posts go in a user's feed

**Notification Service**

Async: sends push notification when someone follows you or likes your photo; uses Kafka + APNs/FCM

**User Service**

Profile data: username, bio, profile photo; used by Feed Service to enrich feed items

**PostgreSQL**

Stores: users, photos (metadata only), follows, likes; partitioned by user_id

**Redis**

Feed cache (list of photo_ids per user); like count cache; online presence

**Photo Upload Flow**

1. Client sends multipart POST /upload with photo bytes + caption + location
2. Upload Service stores original in GCS: gs://originals/{photoId}
3. Writes photo metadata to PostgreSQL: photo_id, uploader_id, caption, s3_key, status="processing"
4. Publishes event to Kafka: {photoId, uploaderId, gcsKey}
5. Returns 202 Accepted with photoId — client polls or waits for push notification
6. Image Processing Worker consumes event, generates sizes, updates status="ready"
7. Feed fan-out worker picks up "photo.ready" event and pushes to followers' feeds

### Step 4: Data Modelling
**Table: photos**

**Component**

**Role**

__photo_id (BIGINT PK)__

Snowflake ID (time-ordered); sortable by creation time

__uploader_id (BIGINT FK)__

INDEX: all photos by a user

**caption (TEXT)**

Up to 2200 chars (Instagram limit)

__gcs_key_original (VARCHAR)__

gs://bucket/original/{photoId}

__gcs_key_processed (VARCHAR)__

gs://bucket/processed/{photoId}/{size}.webp — one row, different size suffixes

**status (ENUM)**

"uploading", "processing", "ready", "deleted"

__created_at (TIMESTAMPTZ)__

Used for chronological feed ordering; indexed

__like_count (INT)__

Denormalised counter; periodically synced from Redis; eventual consistency acceptable

**Table: follows**

**Component**

**Role**

__follower_id (BIGINT)__

User doing the following; INDEX(follower_id) for "who am I following?"

__followee_id (BIGINT)__

User being followed; INDEX(followee_id) for "who follows me?"

__created_at (TIMESTAMPTZ)__

When follow happened

**PRIMARY KEY**

(follower_id, followee_id) — composite to prevent duplicate follows

### Step 5: API Design
**Component**

**Role**

**POST /api/v1/photos/upload**

Multipart body: photo file + {caption, location?}. Returns: {photoId, status: "processing"}. 202 Accepted.

**GET /api/v1/feed**

Query: ?cursor={lastPhotoId}&limit=20. Returns: [{photoId, imageUrl, caption, uploaderUsername, likeCount, createdAt}]. Cursor-based pagination.

**POST /api/v1/photos/{photoId}/like**

Toggles like. Returns: {liked: bool, totalLikes: int}. Idempotent.

**POST /api/v1/users/{userId}/follow**

Follow a user. Returns: {following: bool}. Triggers fan-out on future posts.

**GET /api/v1/users/{userId}/profile**

Returns user profile + photo grid (most recent 9 photos for grid preview).

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Fan-out on write for feed generation (push model)**

**Why**

When a user posts a photo, immediately push the photo_id to all followers' Redis feed lists. Feed reads are then O(1) — just read from a pre-computed list. This makes feed reads fast, which is the more frequent operation (read QPS >> write QPS).

**Trade-off**

For celebrity accounts with 50M followers, a single photo upload triggers 50M Redis writes synchronously or near-synchronously. This is the "celebrity problem." Solution: process fan-out asynchronously via Kafka and batch the Redis writes (1000 followers per batch).

**Alternative**

Fan-out on read (pull model): when user opens feed, query follows table to get all followees, then query most recent photos from each. Fast writes, slow reads. At 1000 followees, this means 1000 DB queries per feed load — unacceptable at scale.

**DECISION**

**Hybrid fan-out for celebrity accounts (> 1M followers)**

**Why**

Regular users (< 1M followers): fan-out on write to Redis. Celebrities: skip fan-out entirely. When reading feed, merge pre-computed feed from Redis with a live query for celebrity posts. The number of celebrities is small; live-querying their latest posts for each feed load is cheap.

**Trade-off**

Feed read path becomes more complex: merge two sources (Redis + DB live query for celebrities). Requires defining a "celebrity" threshold (e.g. > 1M followers) and re-classifying accounts when they cross the threshold.

**Alternative**

Pure fan-out on read with aggressive caching: cache each user's latest photos in Redis, query at read time. Works for smaller scales but becomes slow when following > 500 users.

### Step 7: Bottlenecks & How to Address Them
- Celebrity fan-out problem: 50M Redis writes per post = ~2 hours on a single Redis node. Solution: hybrid approach (skip fan-out for celebrities) + Kafka-based async fan-out with batch writes of 1000 followers/batch using Redis pipelining.
- Image upload bottleneck: 174MB/s inbound to Upload Service. Use direct-to-GCS upload with pre-signed URLs — client uploads directly to GCS, bypassing our servers. Upload Service only receives metadata after GCS confirms the upload. Reduces inbound bandwidth on our services to near-zero.
- Feed cache memory: 300M users * avg 50 cached feed items * 8 bytes per photo_id = ~120GB. Redis Cluster with 5–10 nodes handles this easily. Evict feed cache for inactive users (not logged in > 7 days) to reclaim memory.
- Like count contention: 100K likes per second on a viral photo all hitting the same Redis key. Use Redis INCR (atomic, lock-free). For extreme cases, use a local counter in each service instance and flush to Redis every second (approximate count, acceptable for likes).

### Interview Q&A
**Q: **How would you add video support to this design?

**A: **Videos require transcoding (FFmpeg) into multiple resolutions and formats (HLS for adaptive bitrate streaming). The Image Processing Worker becomes a Video Processing Pipeline: transcode to 360p/720p/1080p HLS segments, store segments in GCS, update metadata with HLS manifest URL. CDN serves HLS segments. For thumbnails, extract frame at 1 second. Key difference: video processing takes 2–10 minutes vs seconds for photos — the polling/notification pattern becomes more important.

**Q: **How do you handle the case where a user with 50M followers posts a photo and the Kafka consumer can't keep up?

**A: **Scale Kafka consumers horizontally — add more Image Processing Worker pods. Kafka partitions fan-out work: partition by uploader_id so all followers of a given celebrity are processed by one consumer (maintains ordering). For truly burst scenarios, Kafka acts as a buffer: the photo is visible in the uploader's profile immediately, and the fan-out completes within minutes rather than seconds. Monitor consumer lag as a key SLA metric.

## 5. Design Twitter / Newsfeed System
**Difficulty**

Advanced

**Asked At**

Meta, Google, Amazon, Twitter/X, Flipkart

**Time Budget**

50–60 min

**Core Concepts Tested**

- Fan-out: write-time vs read-time vs hybrid — the central trade-off of social feed systems
- Redis sorted set as a timeline store
- Kafka for async fan-out at scale
- The celebrity/whale problem and how to handle it without poisoning the system
- Feed ranking vs chronological ordering
- Consistency vs availability trade-offs for timeline

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- Is the feed chronological or ranked by engagement score?
- What is the tweet character limit and media support scope?
- Is retweet/quote-tweet in scope? (Affects fan-out complexity)
- What is the expected maximum follower count? (10K vs 10M vs 100M)
- Should we handle @ mentions and trending hashtags?
- DAU and tweets per day estimates?

**Assumptions (After Clarification)**

- Functional: Post tweet (text, image); view home timeline; follow/unfollow; like tweet
- 300M DAU; 100M tweets/day (~1200 writes/sec); average user follows 400 accounts
- Max followers: 100M (celebrities like Narendra Modi, Sachin Tendulkar level)
- Chronological feed (no ML ranking for this design)
- Non-functional: Timeline load < 200ms; tweet post < 500ms to confirm; 99.9% availability

### Step 2: Capacity Estimation
**Component**

**Role**

**Tweet writes**

100M tweets/day = 1,157 writes/sec

**Timeline reads**

300M DAU * 10 feed checks/day = 3B reads/day = 34,700 reads/sec

**Fan-out writes**

If avg follower count = 400: 1,157 * 400 = 462,800 fan-out writes/sec to Redis feeds

**Tweet storage**

1,157 writes/sec * 1KB (tweet metadata) = ~1.2MB/s → ~36GB/year → trivial for PostgreSQL

**Redis timeline memory**

300M users * 50 cached tweet IDs * 8 bytes = ~120GB (Twitter uses ~TB of RAM in practice)

**Bandwidth (read)**

34,700 reads/sec * 5KB per feed page = ~173MB/s outbound — served via CDN

### Step 3: High-Level Design — The Fan-Out Deep Dive
*The central design question in Twitter's architecture is: when should the feed be computed? There are three strategies, and the answer is "it depends on the user's follower count." This hybrid approach is what Twitter actually uses.*

**Strategy A: Fan-Out on Write (Push Model)**

When a user posts a tweet, immediately write that tweet_id into every follower's Redis timeline (sorted set, score = timestamp). Feed reads are just ZREVRANGE — O(1), sub-millisecond.

- Best for: Users with < 1M followers (the vast majority of users)
- Problem: If @NarendraModi (100M followers) tweets, you need to write 100M Redis entries. At 50K writes/sec per Redis node, this takes 2,000 seconds = 33 minutes. Unacceptable.
- Also wastes memory: writing to feeds of users who haven't logged in for months

**Strategy B: Fan-Out on Read (Pull Model)**

When a user loads their feed, query the follows table to get all followees, then query each followee's most recent tweets, merge and sort. No pre-computation.

- Best for: Accounts with very high follower counts (the celebrities)
- Problem: Following 400 accounts = 400 DB queries or a complex 400-way merge. At 34,700 reads/sec, this is catastrophic. A user with 1,000 followees would generate 1,000 DB reads per feed load.

**Strategy C: Hybrid (What Twitter Actually Uses)**

Combine both strategies based on a celebrity threshold (e.g. 1M followers):

- Regular users (< 1M followers): Fan-out on write. When they tweet, push tweet_id to all their followers' Redis sorted sets asynchronously via Kafka.
- Celebrity users (> 1M followers): Skip fan-out entirely. Do NOT push to follower feeds.
- At read time: Fetch the user's pre-computed Redis timeline PLUS live-query the latest N tweets from each celebrity they follow. Merge the two result sets, sort by timestamp, return the merged feed.
- The number of celebrities a user follows is small (typically < 10). Querying 10 celebrities' latest tweets at read time is cheap — each celebrity's recent tweets are cached in Redis anyway.

**Kafka for Async Fan-Out**

The fan-out from write to Redis timelines is asynchronous via Kafka. This decouples the tweet write from the timeline fan-out:

1. User posts tweet → Tweet Service writes to PostgreSQL → publishes to Kafka topic "tweets.new" → returns 200 OK to user immediately
2. Fan-out Worker consumers pull from "tweets.new" → look up follower list from Social Graph Service → batch-write tweet_id to each follower's Redis sorted set (ZADD)
3. Fan-out is delayed by seconds (not visible instantly to followers) — acceptable for most social apps. Twitter's SLA: delivered to 99.9% of timelines within 5 seconds.

**Core Components**

**Component**

**Role**

**Tweet Service**

Writes tweet to PostgreSQL; publishes to Kafka; returns 200 OK to client

**Fan-out Worker (Kafka Consumer)**

Reads "tweets.new"; fetches follower list (batched); ZADDs tweet_id to each follower's Redis sorted set

**Timeline Service**

Reads home timeline: ZREVRANGE user:{userId}:timeline 0 49; enriches with tweet content from Tweet Cache; merges celebrity tweets (live query)

**Redis Sorted Sets**

Key: user:{userId}:timeline; Score: tweet timestamp (Unix ms); Value: tweet_id; Max size per user: 800 entries (older tweets trimmed)

**Tweet Cache (Redis Hash)**

Key: tweet:{tweetId}; Value: full tweet JSON; TTL: 24 hours for regular tweets; evicted when tweet is deleted

**Social Graph Service**

PostgreSQL + Redis cache of follower lists; used by Fan-out Worker to determine which timelines to update

**Celebrity Cache**

Redis Sorted Set of celebrity account IDs and their latest tweet IDs; refreshed on each celebrity tweet; queried at timeline read time

### Step 4: Data Modelling
**Table: tweets**

**Component**

**Role**

__tweet_id (BIGINT PK)__

Snowflake ID: timestamp-ordered; globally unique across cluster

__author_id (BIGINT FK)__

INDEX for profile page queries

**content (VARCHAR 280)**

280 char limit; stored in PostgreSQL

__media_urls (TEXT[])__

Array of GCS URLs for attached images/videos

__reply_to_tweet_id (BIGINT FK)__

NULL for original tweets; FK for replies (thread support)

__retweet_of_tweet_id (BIGINT FK)__

NULL for original tweets; set for retweets

__like_count (INT)__

Denormalised; updated by Like Service async; eventual consistency OK

__retweet_count (INT)__

Denormalised; updated by Retweet Service async

__created_at (TIMESTAMPTZ)__

Derived from Snowflake ID but also stored for easy querying

**Redis Data Structures**

**Component**

**Role**

**user:{userId}:timeline (Sorted Set)**

Home feed. Score = tweet_id (Snowflake = timestamp-ordered). Value = tweet_id. Max 800 entries per user.

**tweet:{tweetId} (Hash)**

Tweet content cache. Fields: authorId, content, mediaUrls, likeCount, createdAt. TTL: 24h.

**user:{userId}:followers (Set)**

Cached follower list for fan-out. Invalidated on follow/unfollow. For celebrities: stored in shards.

**celebrity:accounts (Sorted Set)**

Set of celebrity user IDs (follower count > 1M). Score = follower count. Refreshed daily.

### Step 5: API Design
**Component**

**Role**

**POST /api/v1/tweets**

Body: {content, mediaUrls?}. Returns: {tweetId, createdAt}. 201 Created. (async fan-out; feed updated within 5s)

**GET /api/v1/timeline/home**

Query: ?cursor={lastTweetId}&limit=20. Returns: [{tweetId, author, content, mediaUrls, likeCount, createdAt}]. Cursor-based.

**POST /api/v1/tweets/{tweetId}/like**

Toggle like. Returns {liked: bool, totalLikes: int}. Idempotent.

**POST /api/v1/users/{userId}/follow**

Follow user. Triggers reclassification if followee crosses celebrity threshold. 200 OK.

**DELETE /api/v1/tweets/{tweetId}**

Delete tweet: mark deleted in DB; evict from Timeline Redis sets asynchronously; evict from Tweet Cache. 204.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

__Snowflake IDs for tweet_id instead of UUID or auto-increment__

**Why**

Snowflake IDs embed the timestamp in the ID, making them naturally time-sorted. This means sorted sets in Redis (scored by tweet_id) are automatically in chronological order without a separate timestamp field. Auto-increment from a single DB sequence becomes a bottleneck at 1,157 writes/sec. UUID is not time-sorted.

**Trade-off**

Snowflake requires a distributed ID generator service (or library), adding operational complexity. The machine_id component (10 bits = 1024 workers max) must be carefully managed in a Kubernetes environment where pod IDs are dynamic.

**Alternative**

Use UUID v7, which embeds a timestamp prefix and is sortable. Simpler to implement than Snowflake but slightly longer (128-bit vs 64-bit). PostgreSQL handles UUID natively.

**DECISION**

**Trim Redis timeline to 800 entries per user**

**Why**

At 50 tweet IDs (8 bytes each) * 300M users = 120GB — already near the limit of what is cost-effective in Redis. If we store 800 IDs, that's 1.9TB just for timelines. We cap at 800: this covers weeks of feed content for an active user. For users who scroll past the 800 limit, we fall back to a DB query.

**Trade-off**

Users who scroll past 800 tweets hit the PostgreSQL fallback — slower (200–500ms vs 1ms). But fewer than 0.1% of users scroll that deep, so it's acceptable.

**Alternative**

Store only 20–50 entries (one page) in Redis and always query DB for more. Smaller memory footprint but loses the benefit of pre-computed feed for all but the first page.

### Step 7: Bottlenecks & How to Address Them
- Kafka Fan-out Worker lag: If fan-out workers fall behind (e.g. a celebrity with 100M followers posts), timeline delivery is delayed. Solution: increase Kafka partitions (100 partitions for "tweets.new") and Fan-out Worker replicas. Each partition handles ~12 tweet writes/sec; fan-out for one tweet can be distributed across workers in parallel by partitioning by follower_id.
- Redis timeline memory at scale: 1.9TB for 300M users at 800 entries each. Use Redis Cluster with 20+ nodes. Evict timelines of users inactive > 30 days (regenerate from DB on next login). Compress tweet_ids (delta encoding: store differences between consecutive IDs, not full IDs).
- Hot celebrity tweet causing read amplification: When Taylor Swift tweets, all 200M followers' timeline reads include a live query for her latest tweets. Cache the celebrity's latest 20 tweet_ids in a dedicated Redis key with 10-second TTL. All read requests share this cached result — only one DB query per 10 seconds regardless of read volume.
- Follower list size for fan-out worker: Fetching 10M follower IDs from Social Graph Service for a celebrity takes time. Pre-partition follower lists into shards of 10K followers each; store shard IDs in the user's celebrity record. Fan-out worker processes shards in parallel across Kafka partitions.

### Interview Q&A
**Q: **How does a user's timeline get updated when they follow a new account?

**A: **After the follow is recorded, the Timeline Service backfills: fetch the last N tweets (e.g. 20) from the newly followed account and ZADD them to the follower's Redis timeline, merging with existing entries. If the followee is a celebrity, no backfill needed — their tweets are fetched live at read time anyway. Backfill is asynchronous (Kafka task) so the follow action returns immediately.

**Q: **How do you handle tweet deletion and ensuring deleted tweets don't appear in feeds?

**A: **Four steps: (1) Mark tweet as deleted in PostgreSQL (soft delete: is_deleted=true). (2) Evict from Tweet Cache (Redis Hash DEL tweet:{tweetId}). (3) Publish "tweet.deleted" to Kafka; fan-out workers scan timelines and ZREM the tweet_id — this is expensive for popular tweets but necessary. (4) For Timeline Service reads, skip any tweet_id whose Tweet Cache is empty (treat as deleted). The combination of cache eviction and timeline cleanup ensures the tweet disappears within minutes.

**Q: **What changes if the feed needs to be ranked by ML score instead of chronological?

**A: **Fan-out on write still works but the score in the Redis sorted set becomes an ML relevance score instead of timestamp. The challenge: ML scores are computed at read time (they depend on the user's current context), not at write time. Solution: two-phase approach — fan-out writes tweet_id with timestamp score; at read time, fetch the top 200 candidates from Redis, score them with a lightweight ML model, return the top 20. This is called candidate generation + ranking, and is the approach used by both Twitter and Meta.

## 6. Design WhatsApp / Chat System (1:1 and Group)
**Difficulty**

Advanced

**Asked At**

Meta, Google, Amazon, Zepto, PhonePe

**Time Budget**

50–60 min

**Core Concepts Tested**

- WebSocket connections for real-time bidirectional messaging
- Message delivery states: sent → delivered → read (the three-tick problem)
- Offline delivery: storing messages and delivering on reconnect
- Group chat fan-out at scale
- Online presence and heartbeat mechanism
- Message ordering and deduplication

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- 1:1 messaging only, or group chat as well? What is the maximum group size?
- Do we need message delivery receipts (sent/delivered/read indicators)?
- Online/offline presence indicators?
- Media sharing (photos, files) or text only for this design?
- Message retention: are messages stored on server forever or end-to-end encrypted (E2E)?
- Push notifications for offline users?
- Expected scale: DAU, messages per day?

**Assumptions (After Clarification)**

- Functional: 1:1 and group chat (max 500 members); delivery receipts (sent/delivered/read); online presence; media sharing (images only); push notifications for offline users
- 2B DAU; 100B messages/day (~1.16M messages/sec); average message 100 bytes
- Non-functional: Message delivery < 100ms when both online; 99.99% availability; messages stored for 5 years

### Step 2: Capacity Estimation
**Component**

**Role**

**Message write QPS**

100B/day / 86400 = 1.16M messages/sec

**Message storage**

1.16M/sec * 100 bytes = 116MB/sec → 10TB/day → ~36PB/5yr — need Cassandra/HBase

**WebSocket connections**

2B DAU; assume 10% active concurrently = 200M persistent WebSocket connections → need 100K+ Chat Servers

**Presence updates**

200M active users; each sends heartbeat every 30s = ~6.7M heartbeat writes/sec to presence store

**Media storage**

5% of messages have images; avg 200KB → 1.16M * 0.05 * 200KB = ~11.6GB/sec media writes — stored in GCS

### Step 3: High-Level Design
**Core Components**

**Component**

**Role**

**Chat Server (WebSocket)**

Maintains persistent WebSocket connections with clients; each server handles ~50K connections; routes messages to recipients

**Service Discovery (ZooKeeper)**

Maps userId → chatServerId; client connects to the server assigned to their userId; allows other servers to forward messages

**Message Store (Cassandra)**

Stores all messages; partitioned by conversation_id; sorted by message_id (time-ordered); write-heavy workload fits Cassandra perfectly

**Presence Service**

Tracks online/offline status via heartbeats; Redis for fast reads; last_seen stored in DB for offline display

**Push Notification Service**

For offline users: Chat Server publishes to "notifications" Kafka topic; Notification Service sends APNs/FCM

**Media Service**

Handles image upload (direct-to-GCS pre-signed URL); stores metadata; returns CDN URL for embedding in message

**Sync Service**

When a user reconnects, fetches all messages delivered while offline; Cassandra query by conversation + timestamp

**API Gateway**

REST API for non-real-time operations: group creation, user profile, media upload initiation

**Message Delivery — Deep Dive**

*The key challenge: message delivery states. WhatsApp shows one grey tick (sent to server), two grey ticks (delivered to device), two blue ticks (read). This requires tracking state per message per recipient.*

**Delivery Flow — Both Users Online**

1. Sender (Alice) sends message via WebSocket to her Chat Server A
2. Chat Server A generates message_id (Snowflake), persists to Cassandra: status=SENT
3. Chat Server A looks up Bob's Chat Server in ZooKeeper → Chat Server B
4. Chat Server A forwards message to Chat Server B
5. Chat Server B delivers message to Bob via his WebSocket
6. Chat Server B sends ACK back to Chat Server A: message DELIVERED to Bob
7. Chat Server A updates Cassandra: status=DELIVERED; sends "delivered" receipt to Alice
8. Bob opens the message → sends READ receipt via WebSocket
9. Chat Server B updates Cassandra: status=READ; forwards receipt to Alice via Chat Server A

**Delivery Flow — Bob is Offline**

1. Steps 1–3 same as above: message persisted with status=SENT
2. Chat Server A sees Bob is offline (checks Presence Service)
3. Publishes to Kafka: {messageId, recipientId: Bob, fcmToken: Bob's token}
4. Notification Service consumes Kafka event; sends push notification to Bob's device via FCM
5. When Bob comes online, his client WebSocket reconnects; Sync Service fetches unread messages from Cassandra
6. Bob's device sends delivered receipts for all fetched messages

### Step 4: Data Modelling
**Cassandra Table: messages (Primary Store)**

**Component**

**Role**

__conversation_id (UUID)__

Partition key — all messages in one conversation stored together; enables efficient range scans

__message_id (BIGINT)__

Clustering key DESC — Snowflake ID (time-ordered); newest messages first within partition

__sender_id (BIGINT)__

Who sent the message

**content (TEXT)**

Message text; up to 65KB

__media_url (TEXT)__

GCS/CDN URL for attached media; null for text-only

__message_type (TEXT)__

"text", "image", "video", "system"

__created_at (TIMESTAMP)__

Redundant with message_id but useful for display

__Cassandra Table: message_status (Receipts)__

**Component**

**Role**

__message_id (BIGINT)__

Partition key

__recipient_id (BIGINT)__

Clustering key — for group messages, one row per recipient

**status (TEXT)**

"SENT", "DELIVERED", "READ"

__updated_at (TIMESTAMP)__

Last status update time

**Redis: Presence Store**

**Component**

**Role**

**presence:{userId} (String)**

Value: "online" or last_seen Unix timestamp. TTL: 60 seconds. Refreshed by heartbeat every 30s.

**user:{userId}:chatServer (String)**

Which Chat Server the user is connected to. TTL: connection lifetime. Set on connect, deleted on disconnect.

**Why Cassandra for Messages?**

- Write throughput: Cassandra handles millions of writes/sec via its LSM tree structure — perfect for 1.16M messages/sec
- Partition by conversation_id: all messages for a chat are co-located; range queries (fetch last 50 messages) are single-partition scans
- No single point of failure: Cassandra's masterless replication across 3+ nodes (RF=3) gives 99.99% write availability
- Time-to-live: Cassandra native TTL support — set TTL on messages for auto-expiry without running a cleanup job

### Step 5: API Design
**Component**

**Role**

**WebSocket: /ws/connect**

Client upgrades HTTP → WebSocket. Server registers in ZooKeeper. Heartbeat every 30s to keep alive.

__WebSocket: send_message event__

Client sends: {conversationId, content, mediaUrl?, clientMessageId}. Server persists, routes, ACKs.

__WebSocket: typing_indicator event__

Client sends: {conversationId, isTyping: bool}. Server relays to other participants. Not persisted.

**GET /api/v1/conversations/{id}/messages**

REST fallback for sync. Query: ?before={messageId}&limit=50. Returns message list with delivery status.

**POST /api/v1/media/upload-url**

Returns a pre-signed GCS URL for direct upload. Client uploads media directly, then sends message with returned CDN URL.

**GET /api/v1/users/{userId}/presence**

Returns: {status: "online"|"offline", lastSeen: timestamp}. REST endpoint — no WebSocket needed.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**WebSocket (persistent connection) over HTTP long-polling or SSE**

**Why**

Chat is inherently bidirectional: server must push messages to client without client polling. WebSocket provides full-duplex communication over a single TCP connection. HTTP long-polling (client holds an open HTTP request waiting for response) wastes a connection per pending message. SSE is server-to-client only — cannot send messages from client to server.

**Trade-off**

Persistent WebSocket connections consume server resources (memory, file descriptors). 200M concurrent connections requires careful resource management — each Go goroutine handling a WebSocket uses ~8KB stack, so 200M connections = ~1.6TB RAM across the chat server fleet. Use connection multiplexing and limit to the most active users.

**Alternative**

HTTP/2 Server-Sent Events for a read-heavy notification system (like Stack Overflow's real-time updates). For true chat, WebSocket remains the right choice.

**DECISION**

**Group chat fan-out: server-side delivery to all members**

**Why**

When Alice sends a message to a 500-member group, Chat Server A must deliver to all 500 members. It looks up group membership, finds each member's Chat Server via ZooKeeper, and forwards. For members who are offline, it queues a push notification. This is synchronous fan-out within the Chat Server layer.

**Trade-off**

For a 500-member group, one message triggers 499 delivery operations. At 1M group messages/sec with avg 50 members, that's 50M delivery ops/sec — the Chat Server fleet must be sized for this. Kafka can buffer the fan-out for large groups.

**Alternative**

Client-side fan-out: sender's app sends the message directly to each recipient's Chat Server. Simpler server but breaks if sender goes offline mid-delivery. Server-side fan-out is more reliable.

### Step 7: Bottlenecks & How to Address Them
- 200M concurrent WebSocket connections: At 50K connections per Chat Server, you need 4,000 Chat Servers. On GCP Kubernetes with c2-standard-16 nodes (each running ~10 Chat Server pods), that's 400 nodes. Scale horizontally — stateless routing via ZooKeeper makes this manageable.
- Presence service write storm: 200M heartbeats every 30s = 6.7M writes/sec. Redis Cluster handles this, but individual node hot keys (presence:{userId} for celebrities) need sharding. Presence updates are eventually consistent — a 60-second staleness is acceptable.
- Message ordering in group chat: Multiple members sending simultaneously. Use server-assigned message_id (Snowflake, monotonically increasing) as the canonical order. Client-side "optimistic" rendering shows local order; server corrects on receipt of message_id.
- Cassandra hot partition for popular group chats: A conversation with billions of messages in one partition hits Cassandra's partition size limits (~100GB). Solution: sub-partition by time bucket — partition key becomes (conversation_id, year_month). Old buckets become cold and compacted.

### Interview Q&A
**Q: **How does the system handle the case where a user is on two devices simultaneously (phone + laptop)?

**A: **A user has multiple WebSocket connections — one per device. ZooKeeper maps userId to a list of chatServerIds (one per active device). When a message arrives, the Chat Server delivers to all devices for that userId. Read receipts are only sent when the message is read on at least one device. The "last active device" is tracked, and presence shows "online" if any device is connected.

**Q: **How do you guarantee message ordering in a 1:1 chat when both users are sending simultaneously?

**A: **Cassandra's clustering key (message_id DESC) provides ordering by server-assigned Snowflake ID. Since Snowflake IDs are generated on the Chat Server at receipt time, the server's wall clock determines ordering. For simultaneous sends, there is an inherent ordering ambiguity — the server assigns IDs in the order messages arrive. This is the same approach used by WhatsApp and iMessage. For strict ordering, you could use a per-conversation sequence counter (atomic INCR in Redis), but this adds latency and a Redis dependency on every message.

**Q: **Explain the heartbeat mechanism for online presence in detail.

**A: **Client sends a ping frame over WebSocket every 30 seconds. Chat Server receives ping, issues Redis SETEX presence:{userId} "online" 60 — TTL of 60 seconds (2x the heartbeat interval). If the client disconnects cleanly (TCP FIN), the Chat Server immediately DEL the key and sets last_seen. If the connection drops ungracefully (network failure, app crash), the Redis key expires naturally after 60 seconds — so the user appears offline within 60 seconds of losing connectivity. This is the standard Phi accrual failure detector pattern applied to presence.

## 7. Design YouTube / Video Streaming
**Difficulty**

Advanced

**Asked At**

Google, Amazon, Netflix, Hotstar (Disney+)

**Time Budget**

50–60 min

**Core Concepts Tested**

- Large file upload: chunked upload, resumable uploads, direct-to-storage
- Async transcoding pipeline: multiple resolutions, adaptive bitrate (HLS/DASH)
- CDN architecture for global video delivery
- Metadata management: search, recommendations (high level)
- Streaming protocols: HLS vs DASH vs MP4 progressive download

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- Upload and watch videos — what else? Comments, likes, subscriptions, search?
- Live streaming or on-demand only?
- Maximum video length and file size?
- Global audience or India-specific (Hotstar/JioCinema)?
- What video quality levels to support? (360p to 4K)
- Expected scale: DAU, videos uploaded per day, average watch time?

**Assumptions (After Clarification)**

- Functional: Upload video; watch video with adaptive quality; search by title; like/comment; subscribe to channel
- 1B DAU; 500 hours of video uploaded per minute; avg video 500MB original, 30min duration
- Supports 360p, 720p, 1080p. No 4K in this design scope.
- On-demand only (no live streaming)
- Non-functional: Video start time < 2 seconds; 99.99% availability; 5 nines for video storage

### Step 2: Capacity Estimation
**Component**

**Role**

**Upload rate**

500 hr/min = ~8.3 hr/sec; avg 500MB/30min video → 8.3 * (500MB/30min) = ~139MB/sec inbound

**Processed storage**

Each video stored at 3 bitrates; 360p ~50MB, 720p ~150MB, 1080p ~300MB per 30min → 500MB total processed per video

**Processed storage growth**

8.3 hr/sec * 2 * (500MB / 0.5hr) = ~16.6GB/sec → 1.4PB/day → ~500PB/year

**Video watch QPS**

1B DAU * 5 videos/day / 86400 = ~57,870 concurrent video starts/sec

**CDN bandwidth**

57,870 streams * avg 3Mbps (720p) = ~174Gbps outbound — must be CDN-served globally

### Step 3: High-Level Design
**Core Components**

**Component**

**Role**

**Upload Service**

Accepts chunked video upload (resumable); stores raw chunks in GCS; assembles and triggers transcoding pipeline

**Transcoding Pipeline**

Kafka-driven async pipeline: raw video → FFmpeg workers → output HLS segments at 360p/720p/1080p; stores segments in GCS

**GCS (Video Storage)**

Stores: raw uploads, HLS segments, thumbnails; geo-replicated; lifecycle rules move cold videos to Nearline storage after 90 days

**CDN (Fastly / Akamai / Cloud CDN)**

Serves HLS segments to users; edge nodes in 200+ PoPs globally; cache-hit ratio > 80% for popular videos; long TTL since segments are immutable

**Metadata Service**

Manages video metadata: title, description, channel, duration, view_count, processing status; PostgreSQL

**Search Service**

Elasticsearch index on video title, description, channel, tags; updated asynchronously when video is uploaded/edited

**Recommendation Engine**

Offline ML pipeline (BigQuery + Vertex AI); produces watch history → recommended video_ids; served via Redis per user

**View Count Service**

Approximate count: Redis INCR per video; periodically (every 5min) flushed to PostgreSQL with Kafka batch writes

**Video Upload Flow**

1. Client requests upload session: POST /upload/initiate → returns upload_session_id and GCS resumable upload URL
2. Client uploads video in 5MB chunks directly to GCS (resumable upload protocol — if interrupted, resumes from last chunk)
3. GCS triggers a Pub/Sub notification when upload completes: {videoId, gcsPath}
4. Transcoding Coordinator picks up event; splits video into segments; dispatches to Kafka: one task per resolution per segment
5. FFmpeg Worker pods (auto-scaled) consume Kafka tasks; transcode each segment; upload HLS segments to GCS
6. After all segments complete, Coordinator generates HLS manifest (.m3u8); updates video status to "ready"
7. Thumbnails generated from frame at 10% duration; stored in GCS; CDN URL written to metadata

**HLS Adaptive Bitrate Streaming**

*HLS (HTTP Live Streaming) splits video into 6-10 second segments. The client player downloads a master playlist (.m3u8) listing all quality variants. The player monitors download speed and switches quality levels dynamically — if bandwidth drops, it switches from 1080p segments to 360p segments without buffering.*

- Master playlist: gs://cdn/videos/{videoId}/master.m3u8 — lists 360p.m3u8, 720p.m3u8, 1080p.m3u8
- Variant playlist: gs://cdn/videos/{videoId}/720p.m3u8 — lists 720p/seg001.ts, 720p/seg002.ts, ...
- Segments: gs://cdn/videos/{videoId}/720p/seg{N}.ts — 6-second .ts files; immutable; CDN-cached with 1-year TTL

### Step 4: Data Modelling
**Table: videos**

**Component**

**Role**

__video_id (BIGINT PK)__

Snowflake ID; time-ordered

__channel_id (BIGINT FK)__

Uploader's channel; INDEX for channel page queries

**title (VARCHAR 100)**

Indexed in Elasticsearch for search

**description (TEXT)**

Up to 5000 chars; indexed in Elasticsearch

__gcs_path_raw (VARCHAR)__

Original upload path in GCS; moved to Coldline after transcoding

__hls_manifest_url (VARCHAR)__

CDN URL for master.m3u8; set when transcoding completes

__thumbnail_url (VARCHAR)__

CDN URL for thumbnail image

__duration_seconds (INT)__

Video length; extracted during transcoding

**status (ENUM)**

"uploading", "processing", "ready", "deleted"

__view_count (BIGINT)__

Denormalised; flushed from Redis every 5 minutes; eventual consistency

__created_at (TIMESTAMPTZ)__

Publication time; used for chronological sorting in channel page

### Step 5: API Design
**Component**

**Role**

**POST /api/v1/upload/initiate**

Body: {title, description, duration}. Returns: {videoId, uploadUrl (GCS resumable)}. Client uploads directly to GCS.

**GET /api/v1/videos/{videoId}**

Returns video metadata + hlsManifestUrl + thumbnailUrl. Client player uses hlsManifestUrl for streaming.

**GET /api/v1/search**

Query: ?q={query}&page=1&limit=20. Returns: [{videoId, title, channelName, thumbnailUrl, viewCount, duration}].

**POST /api/v1/videos/{videoId}/view**

Increments view count (fire-and-forget; async). Also records watch event for recommendation pipeline.

**GET /api/v1/users/{userId}/feed**

Returns recommended videos. Backed by precomputed Redis list; refreshed every 30 minutes by ML pipeline.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Resumable chunked upload (client → GCS directly) instead of streaming through our server**

**Why**

A 500MB video upload through our Upload Service would require our servers to buffer the entire file, consuming 139MB/sec of inbound bandwidth. GCS resumable upload URLs offload this to Google's infrastructure, which is purpose-built for it. If the upload is interrupted (mobile network drop), the client resumes from the last chunk — no re-upload from scratch.

**Trade-off**

Upload Service must initiate the GCS session and manage the upload_session_id. If GCS rejects chunks (quota, auth), we need to handle GCS errors and translate them back to the client.

**Alternative**

Direct-to-S3 multipart upload (AWS) is the equivalent on AWS. Both work. The key principle is the same: don't proxy large files through your application servers.

**DECISION**

**Kafka-driven async transcoding instead of synchronous**

**Why**

Transcoding a 30-minute video at three resolutions takes 5–30 minutes of compute. Doing this synchronously while the client waits is not viable. Kafka decouples the upload confirmation (immediate) from the transcoding completion (async). The client receives 202 Accepted instantly; a push notification arrives when the video is ready.

**Trade-off**

Users do not see their video immediately after upload (processing delay). Must show a "processing" state in the UI. If transcoding fails, we need a retry mechanism and dead-letter queue in Kafka.

**Alternative**

Synchronous transcoding via a Lambda/Cloud Function triggered by GCS event. Works at low scale but cannot maintain SLAs under high load — you cannot horizontally scale synchronous processing fast enough.

### Step 7: Bottlenecks & How to Address Them
- Transcoding compute cost: 500 hr/min of video at 5x transcoding overhead = 2,500 CPU-hours/min of compute. Use Kubernetes autoscaling for FFmpeg Worker pods — scale from 10 to 1,000 pods within minutes based on Kafka consumer lag. Use preemptible VMs to cut cost by 80%.
- CDN cache miss for new video: First viewer after upload hits GCS (200–500ms latency). Pre-warm CDN on transcoding completion: after segments are ready, send HEAD requests to CDN edge nodes for the most popular PoPs. This triggers CDN to pull and cache segments proactively.
- View count accuracy at 57K concurrent streams: Redis INCR is atomic and handles 1M ops/sec. Flush to PostgreSQL every 5 minutes with a background Kafka consumer. For exact counts (legal/monetization), maintain a separate append-only ledger (one row per view event in BigQuery) and use that for billing.
- Hot video causing CDN cache stampede: A viral video released at the same time causes millions of simultaneous first-access requests before CDN warms up. Solution: staggered release with CDN pre-warming, rate limit the CDN origin pull to max 1,000 requests/sec per video (CDN request coalescing).

### Interview Q&A
**Q: **How does Hotstar handle 25 million concurrent viewers for IPL? How is that different from this design?

**A: **Scale difference: 25M concurrent = 25M * 3Mbps = 75Tbps outbound. No single CDN can serve this from origin — they pre-position content aggressively. Key differences: (1) ABR segments for a live event are identical for all users — perfect CDN cache objects. (2) Hotstar uses anycast CDN routing + ISP peering (Jio, Airtel host edge CDN nodes) to minimise hops. (3) WebRTC for sub-second latency is not used — HLS with 6-second segments (6s delay) is the standard. (4) Ad insertion is done server-side (SSAI) to avoid ad blockers — same CDN infrastructure delivers personalized ad segments.

**Q: **How would you design the video recommendation system at a high level?

**A: **Three-stage pipeline: (1) Candidate generation: ML model (matrix factorisation or two-tower DNN) trained on watch history produces top-500 video candidates per user. Runs in BigQuery overnight. (2) Ranking: lightweight gradient-boosted model scores the 500 candidates using real-time signals (current session, trending, recency). Runs at query time. (3) Filtering: remove already-watched videos, apply content policies. Results cached in Redis per user with 30-minute TTL. The key insight: generation is offline and expensive; ranking is online and fast.

## 8. Design Uber / Ride Sharing
**Difficulty**

Advanced

**Asked At**

Uber, Google, Amazon, Swiggy, Zomato, Rapido

**Time Budget**

50–60 min

**Core Concepts Tested**

- Geospatial indexing: Geohash and QuadTree for driver location lookup
- Real-time location updates via WebSocket
- Driver-rider matching algorithm and state machine
- ETA computation and surge pricing (high level)
- Consistency requirements: trip state machine must be ACID

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- What is the scope: passenger app, driver app, or both sides of the marketplace?
- Ride types: economy, premium, pool? (Pool changes matching complexity significantly)
- Real-time location tracking during ride, or just at dispatch?
- Do we need surge pricing and ETA computation?
- Geographic scope: one city, one country, global?
- Expected scale: active drivers, concurrent ride requests?

**Assumptions (After Clarification)**

- Functional: Rider requests ride; nearby drivers shown; driver accepts; real-time location tracking; payment on trip completion; driver/rider rating
- Economy rides only (no pool). Surge pricing: yes (high-level). ETA: yes (approximate).
- 1M active drivers in peak hour; 500K concurrent ride requests at peak; India-wide (mix of Tier 1 and Tier 2 cities)
- Non-functional: Driver location update latency < 5s; match found < 10s; ride status update < 2s; 99.9% availability

### Step 2: Capacity Estimation
**Component**

**Role**

**Driver location updates**

1M drivers * 1 update/5sec = 200K location writes/sec to Redis

**Ride requests**

500K concurrent requests; matching runs every 5s → 100K matching operations/sec

**Location storage**

Each driver: (lat, lng, driverId, timestamp) = ~50 bytes; 1M drivers = 50MB in memory (trivial for Redis)

**Trip data storage**

500K trips/peak * 86400 = 43B trips/year; each trip record ~2KB → ~86TB/year; sharded PostgreSQL or Cassandra

**WebSocket connections**

1M drivers + 500K active riders = 1.5M persistent WebSocket connections for real-time updates

### Step 3: High-Level Design
**Core Components**

**Component**

**Role**

**Location Service**

Receives driver location updates (WebSocket); writes to Redis Geo (GEOADD); publishes location events to Kafka for trip tracking

**Redis Geo Index**

Stores current driver locations using Redis GEOADD/GEORADIUS; enables O(log N) radius search for nearby drivers; ~50MB for 1M drivers

**Matching Service**

Core of the system: finds available drivers near a ride request; applies matching algorithm; sends offer to best-matched driver; handles accept/decline

**Trip Service**

Manages trip state machine (REQUESTED → MATCHED → DRIVER_EN_ROUTE → IN_PROGRESS → COMPLETED); ACID in PostgreSQL

**ETA Service**

Computes ETA using road network graph (OSRM/Google Maps API); considers real-time traffic; returns pickup ETA to rider

**Surge Pricing Service**

Computes demand/supply ratio per geohash zone; returns surge multiplier; recalculates every 5 minutes

**Notification Service**

Push notifications to driver app (new ride offer); rider app (driver accepted, driver arrived)

**Payment Service**

Processes payment on trip completion; integrates Razorpay; idempotency key = trip_id

**Geohashing for Driver Location — Deep Dive**

*The core geospatial challenge: given a rider at (lat=12.97, lng=77.59) in Bengaluru, find all available drivers within 5km in under 100ms. Geohashing is the solution.*

- Geohash divides the Earth into a hierarchical grid. A geohash of precision 6 (~1.2km x 0.6km cell) is a 6-character string like "tdr1wu".
- All drivers in the same geohash cell are stored together. To find nearby drivers, search the driver's cell + 8 adjacent cells (3x3 grid).
- Redis Geo (using GEORADIUS command) does this natively — GEORADIUS drivers:available 77.59 12.97 5 km ASC COUNT 10 — returns 10 nearest available drivers within 5km in O(log N + M).
- Driver updates their geohash on each location update: GEOADD drivers:available 77.591 12.971 driver_123
- On driver acceptance or going offline: ZREM drivers:available driver_123 removes from the geo index

**Trip State Machine**

**State**

**Trigger**

**Actions**

REQUESTED

Rider submits request

Create trip record; enter matching loop

MATCHING

System assigns matching job

Search Redis Geo; send offer to nearest available driver

MATCHED

Driver accepts

Lock trip to driver; notify rider; start ETA polling

DRIVER_EN_ROUTE

Driver starts driving to pickup

Stream driver location to rider via WebSocket

ARRIVED

Driver marks arrival

Notify rider; start 2-minute arrival timer

IN_PROGRESS

Rider enters car; driver starts trip

Record start_location and start_time; stream location to rider

COMPLETED

Driver ends trip

Compute fare; charge via Razorpay; prompt ratings

CANCELLED

Either party cancels

Apply cancellation fee if applicable; release driver to matching pool

### Step 4: Data Modelling
**Table: trips (PostgreSQL — ACID critical)**

**Component**

**Role**

__trip_id (UUID PK)__

Globally unique; used as idempotency key for payment

__rider_id (BIGINT FK)__

INDEX for rider trip history

__driver_id (BIGINT FK)__

INDEX for driver trip history; NULL until matched

**status (ENUM)**

One of the state machine states above; transitions are atomic DB updates

__pickup_lat/lng (DECIMAL)__

Rider's requested pickup coordinates

__dropoff_lat/lng (DECIMAL)__

Rider's requested dropoff coordinates

__start_time / end_time__

Actual trip start and end timestamps

__fare_amount (DECIMAL)__

Computed on completion: base_fare + distance_fare + surge_multiplier

__surge_multiplier (DECIMAL)__

Captured at request time (snapshot of current surge)

__route_polyline (TEXT)__

Encoded route taken; for display and fare disputes

__created_at (TIMESTAMPTZ)__

Request timestamp

### Step 5: API Design
**Component**

**Role**

**POST /api/v1/rides/request**

Body: {pickupLat, pickupLng, dropoffLat, dropoffLng}. Returns: {tripId, estimatedFare, etaSeconds, surgeMultiplier}. Starts matching.

**GET /api/v1/rides/{tripId}/status**

Returns: {status, driverLocation?, etaSeconds?}. Polled by client (or pushed via WebSocket).

**POST /api/v1/rides/{tripId}/cancel**

Cancels trip if in REQUESTED/MATCHED/DRIVER_EN_ROUTE state. Returns: {cancellationFee}.

**WebSocket /ws/driver/location**

Driver app streams location: {lat, lng, bearing, speed} every 5 seconds. Server writes to Redis Geo.

**WebSocket /ws/trips/{tripId}/track**

Rider subscribes to live driver location during DRIVER_EN_ROUTE and IN_PROGRESS states.

**POST /api/v1/rides/{tripId}/rate**

Body: {rating: 1-5, comment?}. Updates both driver and rider rating tables.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Redis Geo for driver location (not PostgreSQL PostGIS)**

**Why**

Redis Geo stores location in a sorted set with geohash-encoded score. GEORADIUS queries return results in microseconds in-memory. PostgreSQL PostGIS is powerful but adds DB load for every 200K/sec location update and every matching query. Redis keeps location data hot in memory where it belongs — this is ephemeral data (we don't need history, just current position).

**Trade-off**

Redis is a cache; location data is lost on restart (though we can persist with AOF). But driver location is re-sent every 5 seconds — a brief Redis outage just means 5 seconds of stale positions, which is acceptable. The source of truth for completed trip routes is the trip_locations table in PostgreSQL.

**Alternative**

Apache Cassandra with a custom geospatial plugin, or ElasticSearch with geo_point field type. Elasticsearch GEORADIUS-equivalent works well and adds full-text search for POI lookup. For Uber's scale, a custom H3 hexagonal grid (Uber's open-source library) provides more uniform cell sizes than geohash.

**DECISION**

**Matching with 5-second polling loop instead of event-driven**

**Why**

The Matching Service runs every 5 seconds and tries to match unmatched ride requests with available drivers. This batch approach simplifies the algorithm: you can consider all unmatched requests and all available drivers holistically, optimising for global matching quality (not just first-come-first-served). Event-driven matching (trigger on each new request) is faster but optimises locally.

**Trade-off**

A rider waits up to 5 seconds before the first match attempt. For high-demand periods, this may mean 10–15 seconds total to match. Alternative: trigger matching immediately on request arrival for the first attempt, then retry every 5 seconds.

**Alternative**

Event-driven matching on every request: faster first match, simpler code. Chosen by some startups. The trade-off is suboptimal global assignment (a driver might be matched to a request 1km away when a request 100m away arrives 1 second later).

### Step 7: Bottlenecks & How to Address Them
- Redis Geo as single point of failure for matching: Matching cannot proceed if Redis is unavailable. Use Redis Sentinel with automatic failover (< 30s). For multi-region India (Mumbai, Delhi, Bengaluru data centres), each region has its own Redis Geo instance — drivers and riders are partitioned by city, so cross-region matching is not needed.
- Matching service bottleneck at 100K ops/sec: Each matching operation reads Redis (GEORADIUS), applies logic, and writes trip status. Horizontally scale Matching Service pods; partition matching by city/geohash zone to avoid cross-pod coordination. Each pod owns a set of geohash zones.
- Driver location update hot key: All 1M drivers writing to the same Redis key "drivers:available". This is a Sorted Set — Redis handles concurrent ZADDs efficiently. Shard by city: drivers:available:bangalore, drivers:available:mumbai. Matching Service queries the right city shard.
- ETA computation at 100K req/sec: Calling Google Maps API at this rate costs millions per day. Cache ETA for (origin_geohash, destination_geohash) pairs with 5-minute TTL. For popular corridors (airport to city centre), ETAs are stable — cache hit rates > 90%.

### Interview Q&A
**Q: **How does surge pricing work technically?

**A: **Every 5 minutes, the Surge Pricing Service queries: (1) demand = count of ride requests in each geohash zone in last 10 minutes; (2) supply = count of available drivers in each geohash zone. Surge ratio = demand / supply. If ratio > 1.5, apply surge multiplier (e.g. 1.5x). If > 2.0, apply 2x. Multiplier is stored in Redis: SETEX surge:geohash_xyz 300 "1.5". When a ride is requested, the Matching Service reads the surge for the rider's geohash and applies it to the fare estimate. The surge_multiplier is snapshotted into the trip record at request time — it doesn't change after the trip starts.

**Q: **How do you handle a driver who goes offline mid-trip (app crash, network loss)?

**A: **Trip state is in PostgreSQL (ACID). The trip is IN_PROGRESS — driver going offline doesn't change this. Chat server / WebSocket server detects the disconnect (heartbeat timeout within 30s). A "driver offline" event is published. The rider app shows "Driver connection lost" but the trip continues — the driver's last known location is displayed. If the driver doesn't reconnect within 5 minutes, the system triggers a manual review flow and may offer the rider a free ride. On driver app restart, it reconnects, fetches current trip state, and resumes location streaming.

## 9. Design Google Drive / Dropbox (File Storage & Sync)
**Difficulty**

Advanced

**Asked At**

Google, Dropbox, Microsoft, Amazon

**Time Budget**

45–55 min

**Core Concepts Tested**

- Chunked upload for large files and resumable upload
- Block-level deduplication to save storage
- Multi-device sync: change notification and conflict resolution
- File versioning and recovery
- Access control: shared folders, permission levels

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- Upload, download, sync across devices — what else? Sharing, collaboration, search?
- What is the maximum file size? (Dropbox: 2GB, Google Drive: 5TB)
- Is offline support required (edit locally, sync when online)?
- File versioning: how many versions to keep?
- Sharing: view-only, comment, edit permissions?
- Expected scale: DAU, total storage under management?

**Assumptions (After Clarification)**

- Functional: Upload/download files; sync across devices; share with view/edit permissions; file history (30 versions)
- Max file size: 5GB; 500M DAU; avg 5GB storage per user → 2.5PB total storage
- Non-functional: Upload/download speed limited by client bandwidth; sync latency < 30s; 99.999% durability; 99.9% availability

### Step 2: Capacity Estimation
**Component**

**Role**

**Total storage**

500M users * 5GB = 2.5PB; with 3x replication = 7.5PB

**Upload QPS**

500M DAU * 2 file changes/day / 86400 = ~11,600 writes/sec

**Download QPS**

10:1 read:write → ~116,000 downloads/sec

**Chunk size**

4MB chunks per file; 1GB file = 256 chunks

**Metadata size**

Each file: ~1KB metadata; 500M users * 1000 files/user = 500B rows → 500TB of metadata (use Cassandra or sharded PostgreSQL)

### Step 3: High-Level Design
**Core Components**

**Component**

**Role**

**Upload Service**

Receives file chunks from clients; verifies checksums; stores in GCS; detects duplicates via chunk fingerprint

**Block Store (GCS)**

Stores file chunks (blocks); keyed by SHA-256 hash of chunk content; global deduplication via content-addressing

**Metadata Service**

Stores file tree structure: folders, files, versions, permissions; Cassandra for scale

**Sync Service**

Long-polling or WebSocket endpoint; notifies connected devices when files change; clients pull delta changes

**Delta Sync Engine**

On reconnect or change detection, computes which blocks changed; only uploads/downloads changed blocks (not entire files)

**Notification Service**

Kafka-driven: on file change, fan-out notifications to all devices of the owner and shared users

**Search Service**

Elasticsearch index on file names, folder paths, text content (for Google Drive-style full-text search)

**Conflict Resolution Service**

Detects concurrent edits (same file modified on two devices offline); creates a conflict copy ("file (Conflict 2024-07-01).docx")

**Block-Level Deduplication — How It Works**

*Instead of storing files as whole objects, we split each file into fixed-size blocks (4MB each) and compute the SHA-256 hash of each block. Two identical files — or two files that share a common section (e.g. two versions of a document where only one paragraph changed) — share blocks in storage.*

1. Client splits file into 4MB blocks
2. For each block, compute SHA-256 hash (block fingerprint)
3. Client sends list of block hashes to Upload Service: POST /upload/check {hashes: [...]}
4. Server checks GCS: which hashes already exist? Returns list of missing blocks.
5. Client uploads ONLY the missing blocks (delta upload). A 1GB file where only 4MB changed = one block uploaded.
6. Metadata record updated: file_id → [blockHash1, blockHash2, ..., blockHashN] (ordered list of block hashes)
7. On download: fetch block list from Metadata; fetch each block from GCS by hash; reassemble file

**Multi-Device Sync Flow**

1. Alice edits "Report.docx" on her laptop offline
2. Laptop comes online; Sync Client detects local change (OS file watcher event)
3. Sync Client computes diff: which blocks changed vs. last known version
4. Uploads only changed blocks; updates metadata (new version v5)
5. Sync Service publishes "file.updated" event to Kafka: {fileId, userId, version: 5}
6. Notification Service fans out to all Alice's devices: phone, desktop
7. Phone's Sync Client receives notification; downloads only the changed blocks
8. Phone reassembles the updated file from cached blocks + new blocks

### Step 4: Data Modelling
__Table: files (Cassandra — partitioned by owner_id)__

**Component**

**Role**

__file_id (UUID)__

Globally unique; partition key together with owner_id

__owner_id (UUID)__

Owner of the file; partition key

__parent_folder_id (UUID)__

For folder tree structure; NULL for root

**name (VARCHAR)**

File name; indexed for search

**version (INT)**

Current version number; incremented on each edit

__block_hashes (LIST<TEXT>)__

Ordered list of SHA-256 block hashes; defines file content

__size_bytes (BIGINT)__

Total file size

**checksum (VARCHAR)**

SHA-256 of entire file; for integrity verification

__created_at / updated_at__

Timestamps

__Table: file_versions (Version History)__

**Component**

**Role**

__file_id (UUID)__

FK to files

**version (INT)**

Version number (clustering key)

__block_hashes (LIST<TEXT>)__

Snapshot of block list at this version

__modified_by (UUID)__

Who made this change

__created_at (TIMESTAMP)__

When this version was created

**comment (TEXT)**

Optional version note ("added Q3 data")

**Table: blocks (GCS Object, not DB)**

- Key: gs://blocks/{sha256Hash} — content-addressed storage
- Value: binary block content (4MB max)
- Deduplication: two files sharing a block reference the same GCS object — one physical copy
- Deletion: block deleted only when reference count reaches zero (tracked via blocks_refcount table)

### Step 5: API Design
**Component**

**Role**

**POST /api/v1/upload/check**

Body: {blockHashes: []}. Returns: {missingHashes: []} — only upload these blocks.

**PUT /api/v1/blocks/{hash}**

Upload a single 4MB block. Idempotent: same hash = same content. Returns 200 if already exists.

**POST /api/v1/files**

Create file record: {name, parentFolderId, blockHashes, sizeBytes, checksum}. Returns: {fileId, version: 1}.

**GET /api/v1/files/{fileId}**

Returns file metadata + blockHashes. Client fetches each block from /blocks/{hash}.

**GET /api/v1/files/{fileId}/changes?since={version}**

Returns changes since version N. Used by Sync Client on reconnect.

**POST /api/v1/files/{fileId}/share**

Body: {email, permission: "view"|"edit"}. Adds to file_permissions table.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Content-addressed block storage (SHA-256 hash as key)**

**Why**

Two identical blocks — regardless of which file they belong to — are stored once. This is global deduplication. A company where all employees have the same OS image file (e.g. a base Docker image) stores it once instead of N times. Industry data suggests deduplication ratios of 3–5x for enterprise storage.

**Trade-off**

Computing SHA-256 on the client for every 4MB block adds CPU overhead. On a slow mobile device processing a 1GB file (256 blocks), this can take 2–3 seconds. Mitigation: compute in a background thread; show upload progress. Also, content-addressed storage makes encryption more complex — two clients with the same block but different encryption keys cannot share the block.

**Alternative**

File-level deduplication (hash the entire file): simpler but misses partial matches. Block-level gives better dedup ratios but more complexity. Some systems (like rsync) use rolling checksums for byte-level dedup — overkill for most file storage use cases.

**DECISION**

**Conflict copy instead of automatic merge for concurrent edits**

**Why**

When two devices modify the same file while offline and both sync simultaneously, automatic merge is only feasible for certain file types (plain text via 3-way diff). For binary files (PDFs, Excel, .docx), auto-merge would produce a corrupt file. Creating a conflict copy ("Report (Alice's conflicted copy 2024-07-01).docx") is safe and transparent.

**Trade-off**

Conflict copies clutter the user's folder if they frequently edit offline. Users must manually resolve conflicts. This is a UX problem, not a technical one. Dropbox uses this approach; Google Docs avoids it entirely by using OT (Operational Transformation) for real-time collaboration.

**Alternative**

Operational Transformation (OT) or CRDT (Conflict-free Replicated Data Type) for automatic merge. Google Docs uses OT. This requires changes to be represented as operations (insert character at position X) not file snapshots — redesigns the entire sync protocol. Out of scope for a standard interview answer.

### Step 7: Bottlenecks & How to Address Them
- Metadata at 500B rows: Cassandra partitioned by owner_id distributes file metadata across nodes. A user's entire file tree is in one partition (co-located), enabling fast folder listing queries. Cross-user queries (search all files shared with me) use a separate inverted index: file_permissions table indexed by grantee_id.
- Block reference counting for deletion: When a file is deleted, decrement reference count for each block. When count reaches zero, delete from GCS. Race condition: two files deleted simultaneously, both try to delete the last reference. Use Redis DECR atomically; if result = 0, enqueue GCS delete to a cleanup worker.
- Large file upload interruption: Network drops mid-upload of a 5GB file. Solution: resumable upload session. Client maintains local state: which blocks have been confirmed uploaded. On reconnect, re-call POST /upload/check — server returns list of still-missing blocks. Client only re-uploads the failed ones. No need to restart from scratch.
- Notification fanout for shared folders: Alice shares a folder with 1000 people; every file change in the folder triggers 1000 notifications. Same celebrity problem as social feeds. Cap notification recipients at 100 for large shared folders; remaining users poll for changes on next app open.

### Interview Q&A
**Q: **How does Sync Client detect local file changes on the desktop?

**A: **OS-provided file system events: inotify on Linux, FSEvents on macOS, ReadDirectoryChangesW on Windows. The Sync Client daemon registers a watch on the Dropbox folder. When any file changes, an event fires with the changed file path. The daemon computes the block diff and uploads changed blocks. For offline changes (laptop in airplane mode), the daemon queues changes and processes them on reconnect. This is exactly how Dropbox works — their early client used polling (inefficient); later switched to OS events.

**Q: **How would you implement file search, including searching inside document contents?

**A: **Two layers: (1) Metadata search (file name, folder path): Elasticsearch index updated on every file create/rename/move event via Kafka. Fast, sub-100ms. (2) Full-text search (inside .docx, .pdf, .txt): On upload, a content extraction worker (Apache Tika) extracts text and indexes it in Elasticsearch. Elasticsearch handles the inverted index. Search is scoped to files the user owns or has access to — Elasticsearch query includes a user_id filter. For 2.5PB of files, full-text indexing only extracts text (not binary), so the text index is ~5–10% of original size.

## 10. Design a Notification System
**Difficulty**

Intermediate

**Asked At**

Amazon, Google, Razorpay, Swiggy, Zepto, PhonePe

**Time Budget**

40–45 min

**Core Concepts Tested**

- Multi-channel delivery: push (APNs/FCM), email (SES), SMS (Twilio/MSG91)
- Kafka-based fan-out for decoupling senders from delivery channels
- Guaranteed delivery with at-least-once semantics
- User preference management: opt-out, frequency capping
- Delivery tracking and failure retry with exponential backoff

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- Which channels are in scope: push notification, email, SMS, in-app?
- Is delivery guaranteed (at-least-once) or best-effort? What's the SLA?
- Do users have preferences — can they opt out of specific notification types?
- Is this a transactional notification system (OTP, order confirmation) or marketing (bulk campaigns)?
- Expected scale: notifications per day?
- Frequency capping: max N notifications per user per day?

**Assumptions (After Clarification)**

- Channels: push (iOS APNs + Android FCM), email (SES), SMS (Twilio/MSG91)
- Both transactional (OTP, order updates) and marketing notifications
- At-least-once delivery guarantee for transactional; best-effort for marketing
- User preferences: per-channel opt-out; frequency cap: max 5 marketing notifications/day/user
- Scale: 10M notifications/day total; peak: 50K/sec (e.g. Swiggy sending "Your order is out for delivery" to 50K simultaneous deliveries)

### Step 2: Capacity Estimation
**Component**

**Role**

**Total volume**

10M notifications/day; peak 50K/sec

**Push (70%)**

7M push/day via APNs/FCM; APNs max throughput ~30M/day per connection pool

**Email (20%)**

2M emails/day via SES; SES handles 100+ emails/sec per account

**SMS (10%)**

1M SMS/day; Twilio SMS ~$0.0075/SMS in India (use MSG91 for cost: ~₹0.15/SMS)

**Notification metadata**

~1KB per record; 10M/day * 365 = 3.65B rows/year → Cassandra with TTL 90 days

### Step 3: High-Level Design
**Core Components**

**Component**

**Role**

**Notification API Service**

Entry point: receives notification requests from internal services (Order Service, Payment Service); validates; publishes to Kafka

**Kafka (notification.requests)**

Central message bus; decouples senders from delivery workers; topics per channel: notification.push, notification.email, notification.sms

**Preference Service**

Checks user opt-out status and frequency cap before delivery; Redis cache of user preferences (updated nightly from PostgreSQL)

**Push Delivery Worker**

Consumes notification.push; calls APNs/FCM; handles token refresh; logs delivery status

**Email Delivery Worker**

Consumes notification.email; renders template (Jinja2/Handlebars); sends via AWS SES; tracks opens/clicks via pixel

**SMS Delivery Worker**

Consumes notification.sms; calls MSG91 or Twilio API; handles DND (Do Not Disturb) registry check (India-specific TRAI requirement)

**Delivery Tracker (Cassandra)**

Stores notification delivery status: sent, delivered, failed, opened; queried for analytics and retry decisions

**Retry Service**

Consumes failed notifications from DLQ (Dead Letter Queue); applies exponential backoff; retries up to 5 times; escalates to fallback channel if all retries fail

**Scheduler Service**

For scheduled notifications (e.g. "Remind me at 9am"): stores scheduled jobs in PostgreSQL; cron worker publishes to Kafka at the scheduled time

**Notification Flow — Order Delivery Update (Swiggy-style)**

1. Order Service: driver marks order "Out for Delivery" → calls Notification API: POST /notify {userId, type: "ORDER_DELIVERY", orderId, templateId: "out_for_delivery"}
2. Notification API validates request, fetches user preferences from Preference Service (Redis)
3. If user has opted out of push OR exceeded daily cap: skip push, try email only
4. Publishes to Kafka topic notification.push: {userId, fcmToken, title, body, data: {orderId}}
5. Also publishes to notification.in_app for in-app badge/banner
6. Push Delivery Worker consumes from notification.push → sends to FCM API → logs status to Cassandra
7. FCM delivers to device; device ACKs FCM; FCM sends delivery receipt to our webhook endpoint
8. Delivery Tracker updates Cassandra: status = DELIVERED

### Step 4: Data Modelling
__Table: notification_log (Cassandra — high write throughput)__

**Component**

**Role**

__notification_id (UUID)__

Unique ID per notification attempt; partition key

__user_id (BIGINT)__

Recipient; secondary INDEX for "all notifications for user X" queries

**channel (TEXT)**

"push", "email", "sms", "in_app"

**type (TEXT)**

"ORDER_UPDATE", "PAYMENT_SUCCESS", "PROMO", "OTP" — used for preference filtering

**status (TEXT)**

"QUEUED", "SENT", "DELIVERED", "FAILED", "OPENED"

__template_id (VARCHAR)__

Reference to notification template; content rendered at send time

**payload (TEXT)**

JSON blob: {orderId, amount, etc.} — template variables

__sent_at (TIMESTAMP)__

When we sent to APNs/FCM/SES

__delivered_at (TIMESTAMP)__

When APNs/FCM confirmed delivery to device

__retry_count (INT)__

Number of retry attempts; max 5

__Table: user_preferences (PostgreSQL + Redis Cache)__

**Component**

**Role**

__user_id (BIGINT PK)__

One row per user

__push_enabled (BOOLEAN)__

Global push opt-in/out

__email_enabled (BOOLEAN)__

Global email opt-in/out

__sms_enabled (BOOLEAN)__

Global SMS opt-in/out; also subject to TRAI DND registry

__marketing_enabled (BOOLEAN)__

Opt-out of non-transactional notifications

__daily_cap (INT)__

Max marketing notifications per day; default 5

__quiet_hours_start/end (TIME)__

Do not disturb window; e.g. 22:00–08:00; no push during this window

### Step 5: API Design
**Component**

**Role**

**POST /api/v1/notify**

Internal API (service-to-service): {userId, type, templateId, payload, channels?: []}. Returns: {notificationId}. 202 Accepted.

**POST /api/v1/notify/bulk**

Marketing campaigns: {userIds: [], type, templateId, payload, scheduledAt?}. Returns: {jobId}. Async processing.

**GET /api/v1/notifications/{userId}**

In-app notification centre: list of recent notifications with read/unread status. Paginated.

**PUT /api/v1/users/{userId}/preferences**

Update user notification preferences: {pushEnabled, emailEnabled, marketingEnabled, quietHoursStart}.

**POST /api/v1/webhooks/fcm/delivery**

FCM delivery receipt webhook. Updates Cassandra: status=DELIVERED. Called by FCM server.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Kafka as the central bus with per-channel topics, not direct API calls from Notification Service to APNs/FCM/SES**

**Why**

Without Kafka: if APNs is slow or down, the Order Service call to Notification API would block or fail. With Kafka: Order Service publishes and returns immediately. Delivery is decoupled — APNs downtime doesn't affect order processing. Kafka also provides natural buffering for peak load (50K/sec spike) and enables at-least-once delivery via consumer offset management.

**Trade-off**

Kafka adds infrastructure complexity and latency (typically 10–100ms added to delivery path). For true real-time notifications (OTP where every millisecond counts), you might bypass Kafka and call the SMS provider directly, falling back to Kafka for retry.

**Alternative**

AWS SQS with separate queues per channel: simpler than Kafka, managed service, but less throughput and no consumer group semantics. Good choice for < 10K notifications/sec; Kafka preferred above that.

**DECISION**

**Preference check via Redis cache (not DB read on every notification)**

**Why**

50K notifications/sec; each requires a preference check. A PostgreSQL read on every notification at 50K/sec would overwhelm the DB. Redis cache of user preferences (refreshed every 5 minutes or on preference update) handles this at sub-millisecond latency. Cache miss falls back to PostgreSQL and populates cache.

**Trade-off**

Stale preferences for up to 5 minutes. If a user opts out and a notification is sent within 5 minutes, it still goes through. For opt-out, send an immediate cache invalidation (DEL user:{userId}:prefs) when preference is updated — this ensures instant opt-out with minimal complexity.

**Alternative**

Read-your-writes with Redis write-through: update preference in both PostgreSQL and Redis atomically (in a DB transaction with an after-commit hook). Adds complexity but eliminates the stale window.

### Step 7: Bottlenecks & How to Address Them
- APNs/FCM rate limits: Apple APNs allows ~30M notifications/day per certificate. For 7M push/day, we're well within limits. But for a marketing blast (send to 100M users simultaneously), we need to throttle our Kafka consumer to APNs's rate limit. Use token bucket on the Push Delivery Worker: max 5,000 APNs calls/sec per worker pod.
- Invalid device tokens causing failures: Users uninstall the app; their FCM token becomes invalid. FCM returns "InvalidRegistration" error. Push Delivery Worker must catch this, delete the token from the user's device registry, and not retry. Accumulating dead tokens wastes API quota.
- India TRAI DND compliance for SMS: India's Telecom Regulatory Authority requires checking the DND registry before sending marketing SMS. We must maintain a local DND blocklist (updated daily from TRAI API) or use a TRAI-compliant SMS provider (MSG91, Exotel do this automatically). Transactional SMS (OTP, order updates) is exempt from DND.
- Notification storm on system event: A major outage (Swiggy backend down for 30 minutes) causes 5M orders to transition to "delayed" state simultaneously, triggering 5M notifications at once. Solution: rate limiting at Notification API level — max 50K notifications/sec enqueued to Kafka; excess queued in a temporary overflow table with delayed processing.

### Interview Q&A
**Q: **How do you handle the case where a user's push notification fails but email and SMS succeed?

**A: **Each channel is tracked independently in notification_log. Push failure triggers retry with exponential backoff (1s, 2s, 4s, 8s, 16s — max 5 retries, ~30s total). If push still fails after retries (e.g. device offline for days), we check the notification's fallback_channels list: if email is in the list, enqueue to notification.email. Fallback channel selection is configured per notification type: OTP always falls back to SMS; marketing notifications do not fall back (we just log the failure).

**Q: **How would you design a "digest" notification — e.g. a weekly summary email instead of 100 individual emails?

**A: **Two approaches: (1) Batch aggregation: a nightly Scheduler job queries notification_log for all notifications of type MARKETING for each user in the past week, renders a digest template, sends one email. (2) Deferred delivery: instead of delivering immediately, store notifications in a digest_queue table keyed by (userId, digest_period). On the scheduled delivery time (e.g. Sunday 10am), the Scheduler Service reads all queued notifications for that period, renders the digest, and sends. Option 2 is more flexible and is how email digest features work at Slack, LinkedIn, and Swiggy.

## 11. Design Search Autocomplete (Typeahead)
**Difficulty**

Intermediate

**Asked At**

Google, Amazon, Flipkart, Swiggy

**Time Budget**

35–40 min

**Core Concepts Tested**

- Trie data structure for prefix matching
- Top-K retrieval by frequency for ranking suggestions
- Redis sorted set for caching top completions per prefix
- Offline aggregation vs real-time updates
- Sub-100ms response time requirement

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- What is the scope: web search autocomplete, or product search on e-commerce?
- How many suggestions to return per query? (Google returns 10)
- Is personalisation required (user-specific history mixed with global frequency)?
- How fast should suggestions update after new search trends emerge?
- Max prefix length to support? (Google handles up to ~100 characters)

**Assumptions (After Clarification)**

- E-commerce product search autocomplete (Flipkart/Amazon style)
- 5 suggestions per query; ranked by search frequency (global, not personalised)
- 10M DAU; 10 keystrokes per search session; 100K prefix queries/sec
- Suggestion freshness: updated daily (trending terms reflected within 24 hours)
- Response latency: < 100ms p99

### Step 2: Capacity Estimation
**Component**

**Role / Detail**

**Prefix query QPS**

10M DAU * 5 searches * 10 keystrokes / 86400 = ~5,787 QPS (round to 6K QPS)

**Peak QPS**

5x peak multiplier → 30K QPS (prime time shopping: Flipkart Big Billion Day)

**Trie size**

~5M unique search terms; avg term length 15 chars; compressed Trie = ~200MB

**Redis top-K cache**

For each of ~1M active prefixes: 5 suggestions * ~50 bytes = ~250MB

**Search log volume**

10M * 5 searches/day = 50M events/day → batch processed nightly for frequency counts

### Step 3: High-Level Design
**Core Components**

**Component**

**Role / Detail**

**Autocomplete Service**

Stateless Go microservice; receives prefix query; checks Redis cache; falls back to Trie Service; returns top-5 suggestions

**Redis Cache (Sorted Set)**

Key: autocomplete:{prefix}; Value: sorted set of {term, score=frequency}; ZREVRANGE returns top-5; TTL: 1 hour

**Trie Service**

Maintains an in-memory compressed Trie; loaded from GCS on startup; refreshed daily; O(P+K) lookups (P=prefix length, K=results)

**Search Log Aggregator (Kafka)**

Every user search writes an event to Kafka: {searchTerm, userId, timestamp}; consumed by Aggregation Worker

**Aggregation Worker (Spark/BigQuery)**

Nightly batch job: reads Kafka/BigQuery; counts term frequency; produces new Trie snapshot; uploads to GCS; triggers Trie Service reload

**CDN / Edge Cache**

For the most common prefixes (single letters, top bigrams), cache at CDN level — "i" returns the same 5 suggestions for all users in the same region

**Trie Data Structure — Internals**

*A Trie (prefix tree) stores strings character by character. Each node represents a character; the path from root to a node spells a prefix. Leaf nodes (or nodes marked as terminal) represent complete words with their frequency score.*

- For "iphone 13": root → i → p → h → o → n → e → (space) → 1 → 3 [frequency: 50,000]
- Query for prefix "iph" traverses 3 nodes, then DFS/BFS collects all terms under "iph" node, returns top-5 by frequency
- Compression: merge single-child nodes — "iphone" is stored as one node "iphone" not 6 separate character nodes (Patricia Trie / Radix Tree)
- In-memory footprint: 5M terms at avg 15 chars with Patricia Trie = ~200MB — fits in one 256MB Go process

**Redis Top-K Cache — The Query Path**

1. Client types "iph" → GET autocomplete:iph from Redis
2. Cache hit: ZREVRANGE autocomplete:iph 0 4 WITHSCORES → returns ["iphone 14", "iphone 13", "iphone case", "iphone 15", "iphone charger"]
3. Cache miss (cold start or eviction): Autocomplete Service queries Trie Service → Trie returns top-5 → populate Redis cache → return results
4. Cache TTL: 1 hour. Popular prefixes stay warm; obscure prefixes evict naturally.

### Step 4: Data Modelling
**Trie Node Structure (In-Memory, Go)**

type TrieNode struct {

    children  map[rune]*TrieNode

    isEnd     bool

    frequency int64   // 0 if not a complete term

    topK      []string // cached top-5 completions for this prefix

}

**Redis Key Schema**

**Component**

**Role / Detail**

**autocomplete:{prefix}**

Sorted Set. Members = search terms. Scores = search frequency. ZREVRANGE for top-K.

**autocomplete:meta**

Hash. Fields: last_updated (timestamp of last Trie rebuild), trie_version (int).

__BigQuery Table: search_events (for offline aggregation)__

**Component**

**Role / Detail**

__search_term (STRING)__

Normalised search term (lowercase, trimmed)

__search_date (DATE)__

Partition column; BigQuery partition pruning on daily aggregations

__user_id (STRING)__

For personalisation (future: per-user frequency table)

__result_clicked (BOOLEAN)__

Did the user click a result? Used for quality weighting: clicked terms ranked higher than searched-but-abandoned

### Step 5: API Design
**Component**

**Role / Detail**

**GET /api/v1/autocomplete**

Query: ?q={prefix}&limit=5. Returns: {suggestions: [{term, frequency}]}. Must respond in < 100ms.

**POST /api/v1/search**

Logs a completed search event to Kafka. Body: {term, resultClicked, sessionId}. 202 Accepted. Fire-and-forget.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Redis sorted set as the cache layer over the Trie, not direct Trie query on every request**

**Why**

A Trie lookup for "a" (single character) must traverse potentially millions of terms to find top-5 by frequency. This DFS can take 10–50ms. Redis ZREVRANGE is O(log N + K) regardless of vocabulary size. The Trie is used only on cache miss (rare for popular prefixes). This two-tier approach gives sub-1ms response for 99% of queries.

**Trade-off**

Cold start problem: empty Redis cache means every query hits the Trie for the first few minutes after deployment. Solution: warm the cache on startup by pre-computing top-1M prefix results and loading them into Redis.

**Alternative**

Store topK directly in each Trie node (precomputed during build). Query is O(P) — traverse prefix, read topK array from node. No Redis needed. Simpler, but topK is static until next rebuild; Redis cache allows freshness without full rebuilds.

### Step 7: Bottlenecks & How to Address Them
- Single-character prefix "a" is a hot key: millions of queries/sec for "a", "i", "s" prefixes. Solutions: (1) CDN-cache the response for single-char prefixes (same for all users, safe to cache at edge); (2) use Redis read replicas; (3) in-process LRU cache in Autocomplete Service — top-100 prefixes cached in-memory per pod.
- Trie rebuild causes downtime: Daily Trie reload from GCS takes 30–60 seconds during which the Trie Service is unavailable. Solution: blue-green Trie Services. Load new Trie into standby pods; health check passes; route traffic to new pods; terminate old pods. Zero downtime.
- Trending terms lag (24h refresh): A product goes viral (e.g. "iPhone 16 leak") and doesn't appear in autocomplete for 24 hours. Solution: stream near-real-time updates via a second Kafka consumer that counts searches in the last 1 hour and updates Redis directly with boosted scores. Trie still rebuilt daily for the full vocabulary.

### Interview Q&A
**Q: **How would you add personalisation — e.g. show the user's own past searches first?

**A: **Two-stage approach: (1) query global Redis cache for top-5 suggestions; (2) query a per-user recent_searches list (Redis List, max 20 entries, RPUSH on each search). Merge: items in the user's history matching the prefix go to the top; remaining slots filled by global top-K. The user's history is ephemeral (Redis TTL 30 days) and small — no Trie lookup needed for personalisation.

**Q: **How do you handle search terms in multiple languages (Hindi, Tamil, Telugu)?

**A: **Unicode-aware Trie: each character in the Trie is a Unicode code point, not a byte. The Trie supports any script. The challenge is keyboard input — users typing Hindi on a phonetic keyboard might search "chai" or "चाय". Transliteration mapping: maintain a phonetic-to-unicode map and index both forms. Elasticsearch's analysis pipeline handles this natively if using ES for autocomplete.

## 12. Design a Web Crawler
**Difficulty**

Intermediate

**Asked At**

Google, Amazon, Microsoft (Bing)

**Time Budget**

40–45 min

**Core Concepts Tested**

- URL frontier: priority queue + scheduling
- Bloom filter for URL deduplication at scale
- Politeness: rate limiting per domain (robots.txt compliance)
- Distributed crawling with fault tolerance
- Content deduplication via page fingerprinting

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- Is this a general-purpose web crawler or domain-specific (e.g. crawl only .in TLDs)?
- What is the target crawl rate? Pages per second?
- Is robots.txt compliance required?
- How fresh should crawled content be? (Recrawl frequency)
- What is the output? Raw HTML stored in GCS? Structured data for search indexing?
- Budget for storage and bandwidth?

**Assumptions (After Clarification)**

- General-purpose crawler for a search engine; crawl 1B pages in 30 days
- Robots.txt compliance required; max 1 request/sec per domain (politeness)
- Recrawl frequency: popular pages every 24 hours, others weekly
- Output: raw HTML stored in GCS; URL and metadata in Cassandra for the indexing pipeline
- Non-functional: 99.9% fault tolerance (crawler pod failure doesn't lose work); deduplicate URLs and content

### Step 2: Capacity Estimation
**Component**

**Role / Detail**

**Target rate**

1B pages / 30 days / 86400 = ~385 pages/sec → round to 400 pages/sec

**Avg page size**

500KB HTML → 400 * 500KB = 200MB/sec download bandwidth

**HTML storage**

1B pages * 500KB = 500TB in GCS

**URL storage**

1B URLs * avg 100 bytes = 100GB → Cassandra or Redis Bloom filter

**Bloom filter size**

For 10B URLs (future scale), 10B * 10 bits/element ≈ 12.5GB (1% false positive rate). Fits in memory.

**DNS lookups**

400 pages/sec * unique domains → DNS cache critical (TTL 600s)

### Step 3: High-Level Design
**Core Components**

**Component**

**Role / Detail**

**URL Frontier**

Priority queue of URLs to crawl; implemented as Kafka topics (one per priority level) + a scheduler; manages recrawl scheduling

**URL Filter**

Two checks: (1) Bloom filter for deduplication (already crawled?); (2) robots.txt cache (allowed to crawl?)

**Fetcher Worker**

Downloads HTML from target URLs; respects politeness (1 req/sec per domain); writes HTML to GCS; publishes to Kafka

**DNS Resolver Cache**

Local DNS cache per Fetcher pod; TTL 600s; avoids 400 DNS lookups/sec being routed to external DNS servers

**HTML Parser / Link Extractor**

Parses fetched HTML; extracts new URLs; filters (normalises, deduplicates via Bloom filter); publishes new URLs to URL Frontier Kafka topic

**Bloom Filter (Redis)**

12.5GB bit array in Redis; SET bit on URL hash on first crawl; CHECK before adding URL to frontier

**Cassandra (Crawl State)**

Stores: URL, last_crawl_time, next_crawl_time, http_status, content_hash; used for recrawl scheduling

**Content Fingerprinter**

Computes SimHash of page content; detects near-duplicate pages (same content, different URLs); avoids indexing duplicates

**Crawl Flow**

1. Scheduler reads Cassandra for URLs where next_crawl_time <= NOW(); publishes to Kafka URL Frontier
2. Fetcher Worker consumes from Kafka; checks URL Filter (Bloom filter + robots.txt cache)
3. If allowed: fetch HTML with HTTP client; respect rate limit (1 req/sec per domain via token bucket per domain)
4. Store raw HTML in GCS: gs://crawl/{domain}/{urlHash}.html
5. Compute content SimHash; check Cassandra for near-duplicates; log as duplicate if SimHash distance < threshold
6. Publish fetched URL metadata to Kafka: {url, gcsPath, httpStatus, contentHash, crawledAt}
7. HTML Parser consumes from Kafka; extracts links; filters and normalises; checks Bloom filter; publishes new URLs to Frontier
8. Cassandra updated: url record with new last_crawl_time, next_crawl_time

### Step 4: Data Modelling
__Table: crawl_state (Cassandra)__

**Component**

**Role / Detail**

__url_hash (VARCHAR 64)__

SHA-256 of normalised URL; partition key; avoids storing full URL as key

**url (TEXT)**

Full URL string

**domain (VARCHAR)**

Extracted domain; for politeness grouping and domain-level rate limiting

__last_crawled_at (TIMESTAMP)__

When we last fetched this URL

__next_crawl_at (TIMESTAMP)__

Scheduled time for next crawl; computed based on page change frequency

__http_status (INT)__

Last HTTP response code; 404 → deprioritise; 301/302 → follow redirects

__content_hash (VARCHAR)__

SimHash of last crawled content; if unchanged on next crawl, skip re-indexing

**priority (INT)**

1=high (popular pages), 5=low (long-tail); determines which Kafka partition/topic

### Step 5: API Design
A crawler is primarily event-driven (no external-facing REST API). Internal control surface:

**Component**

**Role / Detail**

**POST /admin/v1/seed**

Add seed URLs to the crawl frontier. Body: {urls: [], priority: 1}. Triggers initial crawl.

**GET /admin/v1/status**

Dashboard: pages crawled, queue depth, error rate, pages/sec. For operational monitoring.

**POST /admin/v1/recrawl**

Force-recrawl a specific URL immediately. For manual testing or priority override.

**GET /admin/v1/robots/{domain}**

Returns cached robots.txt rules for a domain. For debugging crawl blockers.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Bloom filter for URL deduplication (not a DB EXIST check)**

**Why**

10B URLs in a DB with an index requires 100GB+ of index space; EXIST queries at 400/sec are expensive. A Bloom filter stores 10B URLs in 12.5GB of RAM with O(1) lookups. It has a 1% false positive rate — occasionally, a new URL is incorrectly identified as already crawled. This is acceptable: we miss 1% of new pages, which are recrawled on the next scheduled run.

**Trade-off**

1% false positive rate = 1% of new URLs never get crawled in the current cycle. This is tolerable for a search engine (slightly stale coverage is acceptable). For a financial auditor crawling all pages, false positives are unacceptable — use a DB-backed set instead.

**Alternative**

Use a distributed Redis set (SADD + SISMEMBER): exact deduplication but O(1) per operation and requires one Redis round-trip per URL. At 10B URLs, the set is ~500GB in Redis — expensive but exact.

### Step 7: Bottlenecks & How to Address Them
- Politeness compliance at scale: 400 pages/sec across many domains; must limit to 1 req/sec per domain. Per-domain token bucket in Redis (INCR with 1-second TTL). Fetcher Worker checks domain bucket before fetching. If bucket is full, push URL back to Kafka with a delay (Kafka scheduled delivery or a delay queue).
- DNS bottleneck: 400 unique domain lookups/sec overwhelms standard DNS. Solution: in-process DNS cache per Fetcher pod (Go dnscache library); cache results for 10 minutes. For a fleet of 50 Fetcher pods, maintain a shared Redis DNS cache to avoid redundant lookups across pods.
- Fetcher pod failure loses in-flight URLs: Kafka commit offset only after successful GCS write + Cassandra update. On pod restart, Kafka redelivers uncommitted messages. Fetcher is idempotent: re-fetching a page and re-writing to GCS is safe (same content, same GCS path).

### Interview Q&A
**Q: **How do you handle dynamic pages (JavaScript-rendered content that plain HTTP fetch cannot see)?

**A: **Two-tier fetching: (1) plain HTTP fetch for static pages (fast, cheap); (2) headless Chrome (Puppeteer/Playwright) for pages that return near-empty HTML (detected by: HTML body < 5KB or contains "requires JavaScript" marker). Headless Chrome is 10x slower and 50x more expensive — use it only when necessary. Determine which pages need it by sampling and heuristics. Google uses a two-queue system: "crawl queue" (plain HTTP) and "render queue" (headless Chrome).

**Q: **How would you prioritise which URLs to crawl first?

**A: **Multiple signals: (1) PageRank-like importance: URLs from high-authority domains (bbc.com, ndtv.com) get high priority; (2) freshness: news articles crawled every hour; Wikipedia crawled weekly; (3) link depth: seed URLs crawled first, then depth-1 links, etc.; (4) change frequency: if a page's content changed every crawl for the last 10 crawls, increase frequency. These signals combine into a priority score that determines which Kafka partition the URL goes to (5 partitions = 5 priority levels). High-priority partition has more Fetcher consumers.

## 13. Design a Distributed Cache (Design Redis)
**Difficulty**

Advanced

**Asked At**

Google, Amazon, Stripe, Razorpay

**Time Budget**

45–55 min

**Core Concepts Tested**

- Consistent hashing for data distribution across nodes
- LRU eviction policy and cache sizing
- Leader-follower replication for high availability
- Cache invalidation strategies
- Cluster membership via gossip protocol

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- Is this a distributed cache (multi-node) or a single-node in-memory store?
- What operations must be supported: GET, SET, DELETE, TTL, what data types?
- Consistency requirement: eventual consistency (replicas may lag) or strong consistency?
- What is the scale: how many nodes, what total memory capacity?
- What eviction policy when memory is full? LRU, LFU, random?
- Is persistence required, or pure in-memory (data loss on restart is OK)?

**Assumptions (After Clarification)**

- Distributed cache: 10 nodes, 256GB total memory; horizontally scalable
- Operations: GET, SET (with TTL), DELETE, EXISTS; string values (no complex data types for scope)
- Eventual consistency: replicas lag by < 100ms; strong consistency not required
- Eviction: LRU (Least Recently Used)
- No persistence (in-memory only); node restart means data loss for that node
- Non-functional: GET/SET < 1ms p99; 99.99% availability; automatic failover

### Step 2: Capacity Estimation
**Component**

**Role / Detail**

**Total capacity**

10 nodes * 25.6GB each = 256GB cache space

**Replication factor**

RF=2: each key stored on 2 nodes (primary + 1 replica); effective capacity = 128GB unique keys

**Operations**

Each node handles ~100K ops/sec (Redis-level throughput); total cluster: 1M ops/sec

**Key size**

Avg key: 50 bytes; avg value: 500 bytes; 128GB / 550 bytes = ~230M cached keys

### Step 3: High-Level Design
**Core Components**

**Component**

**Role / Detail**

**Cache Node**

Single process; in-memory hash map (key → value); LRU linked list; event loop (single-threaded like Redis); handles GET/SET/DEL

**Consistent Hash Ring**

Virtual ring of 2^32 positions; each node owns a range; key maps to node via hash(key) % ring; adding/removing nodes only remaps a fraction of keys

**Client Library (Go)**

Knows the ring topology; hashes key to determine primary node; sends request directly to correct node; no routing proxy

**Replication (Leader-Follower)**

Each partition has one leader and one follower; writes go to leader; leader replicates async to follower; follower serves reads (eventual consistency)

**Gossip Protocol**

Each node periodically sends heartbeat to 3 random peers; propagates node liveness info; cluster converges on membership state within seconds

**Sentinel / Coordinator**

Monitors leader health; triggers leader election when primary fails; uses Raft or simple majority vote among Sentinels

**Consistent Hashing — Deep Dive**

*Problem: naive approach (hash(key) % numNodes) means adding one node invalidates ALL keys (new modulus). Consistent hashing maps both keys and nodes to the same hash ring; only 1/N fraction of keys need to move when a node is added/removed.*

- Each node is hashed to M virtual nodes (M=150) on the ring — prevents uneven data distribution when physical nodes have different capacities
- Key lookup: hash(key) → find the first virtual node clockwise on the ring → that node is responsible for the key
- Node addition: new node claims the key range from the previous node to itself; only those keys must be moved
- Node removal: keys previously owned by the removed node go to the next node clockwise
- Replication: key is replicated to the next N-1 nodes clockwise after the primary node

### Step 4: Data Modelling
**In-Memory Data Structures (per node)**

**Component**

**Role / Detail**

**HashMap<string, CacheEntry>**

O(1) GET and SET; key → CacheEntry struct

**CacheEntry struct**

{value: []byte, expiresAt: time.Time, lruNode: *ListNode}

**LRU Doubly-Linked List**

MRU (most recently used) at head; LRU at tail; on eviction, remove tail; on access, move node to head

**MinHeap (TTL Expiry)**

Priority queue by expiresAt; background goroutine pops expired entries and deletes them from HashMap

**LRU Eviction Algorithm (O(1))**

type LRUCache struct {

    cap   int

    cache map[string]*ListNode  // O(1) lookup

    head  *ListNode              // most recently used

    tail  *ListNode              // least recently used

}

func (c *LRUCache) Get(key string) (string, bool) {

    if node, ok := c.cache[key]; ok {

        c.moveToHead(node)  // O(1): unlink + relink at head

        return node.value, true

    }

    return "", false

}

func (c *LRUCache) Set(key, value string) {

    if len(c.cache) >= c.cap {

        delete(c.cache, c.tail.key)  // evict LRU

        c.removeTail()

    }

    node := &ListNode{key: key, value: value}

    c.cache[key] = node

    c.addToHead(node)

}

### Step 5: API Design
**Component**

**Role / Detail**

**GET {key}**

Returns value if key exists and not expired. Returns nil if not found. O(1).

**SET {key} {value} EX {seconds}**

Stores key-value with optional TTL. Overwrites existing. Returns OK.

**DEL {key}**

Removes key. Returns 1 if deleted, 0 if not found.

**EXISTS {key}**

Returns 1 if key exists (and not expired), 0 otherwise.

**INCR {key}**

Atomically increment integer value. Used for rate limiting and counters.

**CLUSTER INFO**

Returns cluster topology: nodes, ring positions, replication state. Admin only.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Single-threaded event loop per node (like Redis) instead of multi-threaded with locks**

**Why**

A single-threaded event loop eliminates lock contention on the HashMap and LRU list. All operations are serialised — no race conditions, no deadlocks. Since cache operations are microsecond-scale (in-memory), the single thread can handle 100K+ ops/sec on a modern CPU. CPU is rarely the bottleneck; network I/O is.

**Trade-off**

Cannot utilise multiple CPU cores for key-value operations. Workaround: run multiple Cache Node processes on one machine, each on a different port and CPU core. The client library shards across these processes. This is exactly what Redis 6.0+ does with I/O threading.

**Alternative**

Multi-threaded with fine-grained locking (per-shard locks on the HashMap): allows parallelism but adds lock overhead and complexity. Memcached uses this approach — it can utilise all CPU cores directly.

### Step 7: Bottlenecks & How to Address Them
- Hot key problem: one key receives 90% of all requests, saturating one node. Solutions: (1) client-side read replication — duplicate hot key to multiple nodes (hot_key_1, hot_key_2, ...) and randomly select one on each GET; (2) local in-process cache in the client library for the hottest N keys; (3) Redis Cluster built-in hot key detection (logs warning when a key exceeds threshold ops/sec).
- Cache stampede (thundering herd): popular key expires; all clients simultaneously miss cache and query the DB. Solution: probabilistic early expiration — start refreshing the key when TTL drops below 10% of original, using a probabilistic check that only 1% of requests trigger the refresh. Also: mutex-based single-flight (Go singleflight package) — only one goroutine per key queries DB; others wait for the result.
- Gossip convergence delay: with 10 nodes, gossip propagates membership changes in O(log N) = 3–4 gossip rounds = ~1 second. During this window, some clients may route to a failed node. Mitigation: client library retries on connection failure and re-reads cluster topology.

### Interview Q&A
**Q: **How does cache invalidation work when the underlying DB data changes?

**A: **Three strategies: (1) Cache-aside (lazy invalidation): application reads DB, writes to cache. On DB update, application calls DEL on the cache key. Next read misses and repopulates. Simple but leaves a stale window between DB update and cache DEL. (2) Write-through: application writes to both DB and cache atomically. Cache is always consistent. Adds latency to writes. (3) Write-behind (write-back): application writes to cache only; cache asynchronously writes to DB. Fastest writes but risk of data loss if cache fails before flushing. For most use cases, cache-aside with a short TTL is the pragmatic choice.

**Q: **How do you handle a leader node failure in the cluster?

**A: **Sentinel nodes (3 sentinels for quorum) continuously monitor leaders via heartbeat. If 2 of 3 sentinels detect a leader as unreachable for > 5 seconds, they trigger a leader election. The follower with the most up-to-date replication log is promoted to leader. Clients are notified via gossip: they re-read the cluster topology and route to the new leader. Writes during the ~5-second failover window are lost (follower was async — may be slightly behind). This is the availability-over-consistency trade-off accepted in eventual consistency systems.

## 14. Design a Payment System (Razorpay-style)
**Difficulty**

Advanced

**Asked At**

Razorpay, PhonePe, Stripe, Amazon Pay, Zepto

**Time Budget**

55–60 min

**Core Concepts Tested**

- Idempotency keys: preventing duplicate charges from retries
- The Saga pattern for distributed transactions across microservices
- Ledger as an append-only table (immutable financial records)
- Webhook delivery with retry and exponential backoff
- ACID guarantees for payment state transitions
- Reconciliation: matching our records against bank/UPI records

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- What payment methods: card, UPI, net banking, wallet?
- P2P (PhonePe) or payment gateway for merchants (Razorpay)?
- What is the transaction volume: peak TPS?
- Is international currency support needed?
- What is the reconciliation requirement — daily settlement with banks?
- What compliance frameworks apply: PCI-DSS for cards, RBI guidelines for UPI?

**Assumptions (After Clarification)**

- Payment gateway (Razorpay-style): merchants integrate our SDK; customers pay on merchant checkout
- Payment methods: UPI, cards (credit/debit), wallets; India-only; INR only
- Scale: 10K TPS peak (Flipkart Big Billion Day, IPL ticket sale)
- Non-functional: Payment confirmation < 3 seconds; exactly-once charge guarantee; PCI-DSS Level 1 compliance for card data; 99.999% availability

### Step 2: Capacity Estimation
**Component**

**Role / Detail**

**Peak TPS**

10,000 transactions/sec

**Avg transaction size**

Payment record: ~2KB; 10K TPS * 86400 = 864M transactions/day → 1.7TB/day of payment records

**Ledger entries**

Each payment creates 2+ ledger entries (debit customer, credit merchant escrow); 20K entries/sec → Cassandra

**Database IOPS**

PostgreSQL for payment state machine; 10K TPS with 5 DB writes each = 50K IOPS; needs high-IOPS SSD (GCP Cloud SQL with 100K IOPS)

**Webhook deliveries**

10K payments/sec → 10K merchant webhook calls/sec; must be queued (Kafka) and retried on failure

### Step 3: High-Level Design
**Core Components**

**Component**

**Role / Detail**

**Payment API Service**

Entry point: receives payment initiation from merchant; validates; generates payment_id and idempotency_key; returns payment_url to merchant

**Order Service**

Manages order state: CREATED → PAYMENT_INITIATED → PAYMENT_CONFIRMED → FULFILLED; publishes to Kafka on state changes

**Payment Processing Service**

Calls bank/UPI PSP APIs (NPCI for UPI, card networks for cards); handles async payment confirmation; updates payment status

**Ledger Service**

Append-only ledger: records every debit and credit; never UPDATE or DELETE a ledger entry; Cassandra for write throughput

**Idempotency Store (Redis)**

Maps idempotency_key → {paymentId, response, status}; TTL 24 hours; prevents duplicate charges on retry

**Webhook Delivery Service**

Kafka consumer: reads payment.completed events; calls merchant webhook with retry; exponential backoff; up to 25 retries over 72 hours

**Reconciliation Service**

Daily batch: fetches settlement report from NPCI/bank; compares against our ledger; flags mismatches for manual review

**Vault (Card Data)**

PCI-DSS compliant tokenisation: stores card numbers encrypted; our systems only handle tokens; actual card data never in our main DB

**Idempotency Key — Deep Dive (Most-Asked Indian Fintech Question)**

*The Problem: A merchant's server calls POST /payment. Network timeout. Did the payment go through? The merchant retries. Without idempotency, the customer gets charged twice.*

*The Solution: Merchant generates a UUID (idempotency_key) per payment attempt. Sends it in the request header: X-Idempotency-Key: {uuid}.*

1. Payment API receives request with idempotency_key
2. Check Redis: GET idempotency:{key} → cache hit: return the stored response immediately (no processing)
3. Cache miss: SET idempotency:{key} "IN_PROGRESS" NX PX 30000 (atomic SETNX, 30s TTL) → if SET fails, another instance is processing this key (use distributed lock, return 409 Conflict)
4. Process payment (call PSP, update DB)
5. On completion (success or failure): SET idempotency:{key} {serialised response} EX 86400 (24h TTL)
6. Return response to merchant — same response for all retries with this key

- Critical: the idempotency key is generated by the MERCHANT, not our system. This ensures that even if our API is down and the merchant retries with a new connection, the same key prevents duplicate processing.
- Razorpay's actual implementation: idempotency keys stored in PostgreSQL (not just Redis) for durability — Redis is the fast path, PostgreSQL is the source of truth

**Saga Pattern for Payment Flow**

*A payment touches multiple services: Order → Payment → Ledger → Notification. If any step fails, we must roll back. But we cannot do distributed transactions (2PC is too slow and fragile). The Saga pattern uses compensating transactions.*

**Component**

**Role / Detail**

**Step 1: Order Service**

RESERVE inventory (action). Compensating: RELEASE inventory on failure.

**Step 2: Payment Service**

CHARGE customer via PSP (action). Compensating: REFUND via PSP on downstream failure.

**Step 3: Ledger Service**

RECORD debit/credit entries (action). Compensating: REVERSE entries (new entries, not delete — ledger is append-only).

**Step 4: Notification Service**

SEND confirmation email/SMS (action). Compensating: SEND failure notification. (No real rollback needed for notifications.)

- Choreography Saga (used here): each service publishes events; next service listens and acts; on failure, publishes a failure event; upstream services execute compensating transactions
- Orchestration Saga: a central Payment Orchestrator calls each service sequentially; simpler to understand but single point of failure for the workflow

**Ledger — Append-Only Design**

*Financial systems must never UPDATE or DELETE payment records. Every state change creates a new ledger entry. This provides a complete audit trail and makes reconciliation unambiguous.*

**Component**

**Role / Detail**

__entry_id (UUID PK)__

Each row is immutable once written

__payment_id (UUID)__

Which payment this entry belongs to

__entry_type (ENUM)__

"DEBIT_CUSTOMER", "CREDIT_MERCHANT_ESCROW", "DEBIT_ESCROW", "CREDIT_MERCHANT", "REFUND_DEBIT", "REFUND_CREDIT"

**amount (DECIMAL 15,2)**

Always positive; entry_type determines direction

**currency (CHAR 3)**

"INR" for India-only scope

__account_id (UUID)__

Customer wallet, merchant escrow, or merchant settlement account

__created_at (TIMESTAMPTZ)__

Immutable; set on insert; never updated

__reference_id (VARCHAR)__

External reference: UTR number for UPI, ARN for cards

**Webhook Delivery with Retry**

Merchants depend on webhooks to confirm payment and fulfil orders. Delivery must be reliable even if the merchant's server is temporarily down. Razorpay retries webhooks 25 times over 72 hours.

1. Payment.Completed event published to Kafka: {paymentId, merchantId, amount, status}
2. Webhook Delivery Worker consumes: looks up merchant's webhook URL from config; sends POST with HMAC-signed payload
3. Merchant server must return 200 OK within 5 seconds (timeout)
4. On failure (non-200 or timeout): mark attempt as failed; schedule retry with exponential backoff: 1min, 5min, 30min, 2hr, 8hr, ...
5. Retry state stored in PostgreSQL: {paymentId, attempt, nextRetryAt, status}; Retry Scheduler polls this table
6. After 25 failures: mark as PERMANENTLY_FAILED; alert merchant via email; provide dashboard to manually trigger replay
7. Signature verification: merchant validates each webhook with HMAC-SHA256(payload, merchantSecret) — prevents spoofed webhooks

### Step 4: Data Modelling
**Table: payments (PostgreSQL — ACID)**

**Component**

**Role / Detail**

__payment_id (UUID PK)__

Globally unique; used as idempotency reference throughout the system

__order_id (UUID FK)__

Which order this payment is for

__merchant_id (UUID FK)__

Which merchant received payment

__customer_id (UUID FK)__

Payer; may be anonymous for guest checkout (nullable)

**amount (DECIMAL 15,2)**

Always in paise for INR (integer arithmetic avoids floating-point errors: Rs 100 = 10000 paise)

**currency (CHAR 3)**

"INR"

**method (ENUM)**

"UPI", "CARD", "NET_BANKING", "WALLET"

**status (ENUM)**

"INITIATED", "PROCESSING", "AUTHORIZED", "CAPTURED", "FAILED", "REFUNDED"

__psp_reference (VARCHAR)__

External payment processor's transaction ID (NPCI UTR for UPI)

__idempotency_key (VARCHAR)__

Merchant-supplied; UNIQUE INDEX; enforced at DB level as second safety net

__created_at / updated_at__

Timestamps; updated_at changes on status transition

__failure_reason (TEXT)__

PSP error code and message on FAILED status

### Step 5: API Design
**Component**

**Role / Detail**

**POST /v1/payments**

Merchant initiates: {orderId, amount, currency, method, callbackUrl}. Header: X-Idempotency-Key. Returns: {paymentId, paymentUrl, status: "INITIATED"}.

**GET /v1/payments/{paymentId}**

Poll payment status. Returns: {paymentId, status, amount, pspReference, createdAt}. Used by merchant to check status after webhook timeout.

**POST /v1/payments/{paymentId}/refund**

Full or partial refund: {amount, reason}. Idempotent. Creates new Saga: REFUND_INITIATED. Returns: {refundId, status}.

**POST /v1/webhooks/upi/callback**

NPCI/PSP sends payment confirmation here. Authenticated by IP allowlist + HMAC. Updates payment status and triggers Saga continuation.

**GET /v1/merchant/settlements**

Settlement dashboard: daily settlement amounts, pending, processed. Returns paginated settlement records.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Store amounts in paise (integer), not rupees (decimal)**

**Why**

Floating-point arithmetic is dangerous for money. 0.1 + 0.2 = 0.30000000000000004 in IEEE 754. Storing amounts as integers (paise = 1/100 rupee) allows all arithmetic to be integer addition/subtraction. No rounding errors. Rs 100.50 = 10050 paise. Divide by 100 only for display. This is how Razorpay, Stripe (stores in cents), and all serious payment systems work.

**Trade-off**

Amount displayed to users must be divided by 100 and formatted. Bug risk if a developer forgets the conversion. Mitigate with strong typing (type Paise int64 in Go) and a helper function Amount.ToRupees().

**Alternative**

DECIMAL(15,2) in PostgreSQL also avoids floating-point issues. But integer paise is simpler and faster for comparisons, and prevents the possibility of storing fractional paise.

**DECISION**

**Append-only ledger (never UPDATE or DELETE financial records)**

**Why**

Financial audit trail: every debit and credit is an immutable record. If Rs 500 was charged incorrectly and refunded, the ledger shows: DEBIT Rs 500, CREDIT Rs 500 (refund) — two entries, full history. With UPDATE, the original charge could be silently modified. Regulators (RBI, SEBI) require immutable transaction logs. Forensic analysis after a breach or fraud is only possible with immutable records.

**Trade-off**

The ledger table grows forever (no UPDATEs or DELETEs). At 20K entries/sec, it's 1.7B entries/day. Partition by created_at month; archive to cold storage (GCS/BigQuery) after 12 months. Queries for current-month data are fast on hot partition.

**Alternative**

Updatable status table (payments table) for operational queries (what is the current status of payment X?) PLUS separate append-only event_log for audit. This is the CQRS pattern — separate read model from write/audit model. More complex but cleaner.

### Step 7: Bottlenecks & How to Address Them
- PostgreSQL at 10K TPS with 50K IOPS: Use GCP Cloud SQL with 100K IOPS SSD, pgBouncer connection pooler (payment API has 100+ pods each wanting 10 DB connections = 1000 connections, too many for PG), and read replicas for non-critical reads. For extreme scale, shard payments table by merchant_id.
- NPCI/UPI API rate limits: NPCI limits per-participant transaction rate. Batch UPI payment requests if under threshold; queue excess in Redis and retry. Monitor NPCI latency — if > 2 seconds, surface "bank is slow" message to user (better than silent timeout).
- Reconciliation at 864M transactions/day: Daily settlement report from NPCI has millions of rows. Compare against our Cassandra ledger in Apache Spark (BigQuery if on GCP). Match by UTR number. Flag: payments in our DB with no NPCI record (double-charge risk) and NPCI records not in our DB (missed payments).
- Fraud detection: payment_processor must check: (1) velocity checks via Redis (user made > 5 failed payments in last hour); (2) amount anomaly (payment 10x larger than user's typical transaction); (3) geolocation mismatch (card registered in Mumbai, payment attempted from IP in Kyiv). Kafka Streams for real-time fraud scoring.

### Interview Q&A
**Q: **A merchant's webhook is failing. How do you tell the merchant what happened?

**A: **Three mechanisms: (1) Real-time: webhook attempt log in Razorpay dashboard — merchant can see each attempt, the response code, response body, and next retry time. (2) Email alert: after 5 consecutive failures, send email to merchant's registered contact. (3) Manual replay: dashboard button "Resend Webhook" for each payment — useful after the merchant's server is back up. Razorpay's actual design: webhook_delivery_logs table stores every attempt with request/response body for debugging. This is what merchants use when they call support.

**Q: **How does UPI payment confirmation work in your system?

**A: **UPI is asynchronous. Flow: (1) User scans QR / enters UPI ID → initiates payment in their UPI app (GPay, PhonePe); (2) NPCI processes the payment between user's bank and merchant's bank; (3) NPCI sends a callback to our webhook: POST /v1/webhooks/upi/callback {utr, status, amount}; (4) We validate the UTR, match against our pending payment, update status to CAPTURED; (5) Saga continues: ledger entry recorded, merchant webhook triggered. The key insight: we never directly talk to the user's bank — NPCI is the intermediary. This is why UPI payments can take 30 seconds to confirm (bank processing + NPCI + our callback).

## 15. Design a Ticket Booking System (BookMyShow / IPL)
**Difficulty**

Advanced

**Asked At**

Flipkart, BookMyShow, Hotstar, Amazon

**Time Budget**

55–60 min

**Core Concepts Tested**

- Concurrency control: preventing double-booking under extreme load
- Optimistic vs pessimistic locking vs Redis-based seat locks
- Seat reservation timeout: releasing held seats if payment doesn't complete
- Queue-based traffic shaping for flash sales (10K seats, 5M concurrent users)
- Idempotent booking confirmation

### Step 1: Clarify Requirements (5 minutes)
**Questions to Ask the Interviewer**

- Events: movies, concerts, or sports (IPL)? Each has different seat selection complexity.
- Is seat selection mandatory, or can we assign seats automatically?
- What is the booking window: can seats be booked weeks in advance or only day-of?
- What is the peak load scenario? (IPL Final: 100K seats, 10M concurrent users at release)
- Payment integration: should booking be confirmed before or after payment?
- Are there booking limits per user? (Anti-scalping: max 4 tickets per user per event)

**Assumptions (After Clarification)**

- IPL ticket booking: stadium with 50,000 seats; 5M users try to book simultaneously at 10:00 AM
- Seat selection required (users pick specific seats from a seating map)
- Booking flow: select seats → hold for 10 minutes → complete payment → confirm booking
- Anti-scalping: max 4 tickets per user per event
- Non-functional: No double-booking under any circumstance; system handles 5M concurrent users; booking confirmation in < 5 seconds

### Step 2: Capacity Estimation
**Component**

**Role / Detail**

**Concurrent users (peak)**

5M users hitting "book" at 10:00:00 AM — this is a flash sale scenario

**Available seats**

50,000 seats for an IPL match; all claimed within minutes

**Seat hold duration**

10 minutes; after which held seats are released back to the pool

**Booking DB writes**

50,000 confirmed bookings → small volume; the challenge is the 5M concurrent lock requests

**Queue depth (traffic shaping)**

5M requests arrive; 50,000 seats → 4.95M users will be disappointed. Queue prevents thundering herd on DB.

**Redis seat lock memory**

50,000 seats * (seatId ~10 bytes + userId ~8 bytes) = ~1MB per event — trivially small

### Step 3: High-Level Design — The Concurrency Problem
*The central challenge: 5,000,000 users simultaneously request the same 50,000 seats. Without proper concurrency control, multiple users could book the same seat. With naive locking, the database collapses under 5M concurrent connections.*

**Three Approaches to Seat Locking**

**Approach**

**Mechanism**

**Pros**

**Cons**

Pessimistic Locking

SELECT ... FOR UPDATE locks the seat row; no other transaction can read/write until commit

Prevents double-booking; simple

Deadlocks at scale; 5M concurrent locks collapse PostgreSQL; unacceptable for flash sale

Optimistic Locking

version field on seat; UPDATE SET status=HELD WHERE id=X AND version=V; check affected rows

No DB locks; high throughput; handles low contention well

At 5M concurrent users, 99.99% of updates fail (version mismatch); massive retry storm; unacceptable for flash sale

Redis Seat Lock (Recommended)

SETNX seat:{seatId} {userId} PX 600000; if returns 1, lock acquired; 0, seat taken

Sub-millisecond; no DB involved; atomic; 1M ops/sec throughput; TTL handles timeout

Redis is single point of failure; must handle Redis failover; eventual consistency with DB after Redis lock

**Core Components**

**Component**

**Role / Detail**

**Virtual Waiting Queue**

At 10:00 AM, all 5M incoming requests are queued (Redis queue or Kafka). Users are admitted in batches of 500/second. Shows user their position in queue. Prevents thundering herd on booking service.

**Seat Availability Service**

Real-time view of available/held/booked seats. Redis Bitmap (one bit per seatId: 0=available, 1=held/booked). BITCOUNT for available count. Updated atomically.

**Booking Service**

Core: attempts Redis SETNX lock for selected seats; on success, writes HOLD record to PostgreSQL; starts 10-minute hold timer; initiates payment flow

**Payment Service**

Integrated with Razorpay; processes payment for held seats; on success triggers booking confirmation; on failure releases Redis lock

**Reservation Expiry Worker**

Polls or uses Redis keyspace notifications for expired seat locks; releases seats back to pool (UPDATE seat status to AVAILABLE); sends "session expired" notification to user

**Booking Confirmation Service**

On payment success: writes confirmed booking to PostgreSQL; generates booking_id and QR code; sends confirmation email/SMS via Notification Service

**Seat Locking Flow — The Redis SETNX Approach**

1. User selects seats A1, A2 from seating map
2. Booking Service: SETNX seat:event123:A1 {userId:abc, heldAt:...} PX 600000 (10min TTL)
3. Repeat for seat A2. If any SETNX returns 0 (seat taken): rollback — DEL all acquired locks; return "seat unavailable" to user
4. Both SETNXs return 1: seats are held. Write to PostgreSQL: INSERT INTO seat_holds (event_id, seat_ids, user_id, expires_at)
5. Return hold_id to client; client proceeds to payment page
6. User completes Razorpay payment within 10 minutes
7. On payment success: UPDATE seat_holds SET status=CONFIRMED; INSERT INTO bookings; DEL Redis keys (not needed — TTL would expire them anyway, but explicit delete is cleaner)
8. On payment failure: DEL Redis keys; mark seat_hold as EXPIRED; seats immediately available again
9. On user abandonment (no payment within 10 minutes): Redis TTL expires the keys; Reservation Expiry Worker detects expired hold in PostgreSQL; releases seats

### Step 4: Data Modelling
**Table: seats (PostgreSQL)**

**Component**

**Role / Detail**

__seat_id (VARCHAR PK)__

e.g. "A1", "B12"; unique per event+venue combination

__event_id (UUID FK)__

Which event this seat belongs to

**status (ENUM)**

"AVAILABLE", "HELD", "BOOKED" — eventual consistency with Redis; Redis is source of truth during booking window

__price_tier (ENUM)__

"PREMIUM", "GOLD", "SILVER", "GENERAL" — determines price

**version (INT)**

For optimistic locking as a fallback on Redis failure

**Table: bookings (PostgreSQL — immutable after creation)**

**Component**

**Role / Detail**

__booking_id (UUID PK)__

Globally unique; printed on ticket QR code

__event_id (UUID FK)__

Which event

__user_id (UUID FK)__

Who booked

__seat_ids (TEXT[])__

Array of booked seat IDs (e.g. ["A1", "A2"])

__total_amount (INT)__

In paise; sum of seat prices + convenience fee

__payment_id (UUID FK)__

FK to payments table; idempotency anchor

**status (ENUM)**

"CONFIRMED", "CANCELLED", "TRANSFERRED"

__booking_time (TIMESTAMPTZ)__

Immutable; when booking was confirmed (after payment)

__qr_token (VARCHAR)__

Signed JWT token for QR code; validated at venue entry

### Step 5: API Design
**Component**

**Role / Detail**

**GET /api/v1/events/{eventId}/seats**

Returns seating map with availability. Uses Redis Bitmap for seat status. Refreshed every 5 seconds for clients.

**POST /api/v1/bookings/hold**

Body: {eventId, seatIds, userId}. Returns: {holdId, expiresAt} on success. Returns 409 if any seat taken. Redis SETNX.

**POST /api/v1/bookings/{holdId}/pay**

Initiates payment for held seats. Returns: Razorpay payment URL. Must complete within 10 minutes.

**POST /api/v1/bookings/{holdId}/confirm**

Called after Razorpay webhook confirms payment. Creates booking record. Returns: {bookingId, qrToken}.

**GET /api/v1/bookings/{bookingId}**

Returns booking details and QR token. Used for ticket display.

**DELETE /api/v1/bookings/{bookingId}**

Cancel booking (if event is > 24 hours away). Initiates refund. Updates seat status to AVAILABLE.

### Step 6: Key Design Decisions & Trade-offs
**DECISION**

**Virtual waiting queue to throttle 5M users instead of directly hitting booking service**

**Why**

At 10:00 AM, 5M HTTP requests hitting the Booking Service simultaneously would cause: (1) DB connection pool exhaustion; (2) Redis overwhelmed; (3) cascading failures. A virtual queue (Kafka or Redis List) absorbs the spike. Users are admitted at a controlled rate (e.g. 500/sec = 50,000 seats filled in 100 seconds). Users see their queue position — this reduces user frustration even when they have to wait.

**Trade-off**

Adding a queue increases booking latency for the user. A user might wait 5–10 minutes in the queue. For in-demand events, this is unavoidable — seats are scarce. The queue doesn't change the outcome (50K seats are still gone in minutes) but prevents the system from crashing.

**Alternative**

No queue, just horizontal scaling: throw 10,000 Booking Service pods at the problem. Redis and PostgreSQL can handle the load if scaled enough. But this is very expensive for a 10-minute peak, and scaling 10,000 pods in seconds is not feasible on Kubernetes.

**DECISION**

**Redis SETNX for seat locking, with PostgreSQL as the persistent store**

**Why**

Redis SETNX is atomic (no race condition) and processes at 1M ops/sec per node — handling 5M concurrent seat lock attempts is trivial for Redis. The TTL (10 minutes) automatically handles user abandonment without a cleanup job. PostgreSQL is the durable store — Redis key expiry triggers a background job that syncs seat status to PostgreSQL.

**Trade-off**

Redis failure causes a brief period where seat availability is unknown. Mitigation: Redis Sentinel with < 30s failover. During failover, reject new booking attempts (serve a "high demand" page). The pessimistic fallback: on Redis unavailability, fall back to PostgreSQL SELECT FOR UPDATE for a degraded-but-functional booking flow.

**Alternative**

Database-only optimistic locking (version field): simpler architecture, no Redis dependency. Works fine for low-traffic events. For IPL Final (5M concurrent), the retry storm from failed optimistic locks would be devastating — 4,999,950 concurrent retries all competing for 50,000 row updates.

### Step 7: Bottlenecks & How to Address Them
- Seat availability read storm: 5M users all loading the seating map at 9:59 AM. Cache the seating map in Redis as a Bitmap (one bit per seat; 50,000 seats = 6.25KB). GETBIT seat:event123:bitmap {seatIndex} for individual seat status. The entire map is returned as one 6KB Redis GET. CDN-cache the rendered seating map image for 5-second intervals — users see a slightly stale map (acceptable: seat status changes too fast for real-time accuracy at this scale).
- Anti-scalping enforcement: max 4 tickets per user per event. Check before seat hold: Redis SETNX user_limit:event123:userId counter; INCR and compare to 4. If > 4, reject. This check must be atomic with the seat lock (Lua script in Redis for both checks in one atomic operation).
- QR code forgery at venue entry: QR code contains a signed JWT: {bookingId, seatId, eventId, exp}. Signed with a venue-specific private key. Venue entry scanner validates signature (no network call needed for validation). Revoked bookings (cancellations) published to a local blocklist on each scanner via Kafka — scanners download blocklist on startup and as events arrive.
- Queue position fairness: users who enter the queue simultaneously should be served in FIFO order. Redis LPUSH (enqueue) + BRPOP (dequeue with blocking) is FIFO. Add a request_time field for additional fairness audit. Monitor queue depth and admission rate — if queue depth grows faster than depletion rate, alert and scale Booking Service.

### Interview Q&A
**Q: **What happens if a user holds seats but the payment service crashes before they can pay?

**A: **The Redis seat lock has a 10-minute TTL. If the payment service crashes, the user cannot complete payment within 10 minutes. The Redis key expires automatically, releasing the seats. The Reservation Expiry Worker detects the expired seat_hold in PostgreSQL (WHERE expires_at < NOW() AND status=HELD) and marks it as EXPIRED. The seats are returned to AVAILABLE status in both Redis and PostgreSQL. The user receives a "Your session has expired" notification and must re-enter the queue if seats remain. Crucially, no money was charged — payment had not started yet (or was explicitly cancelled by the PSP on timeout).

**Q: **How would you scale this for a scenario like IRCTC, where 1 crore (10M) users hit at 10 AM simultaneously for Tatkal tickets?

**A: **Three additional layers beyond our design: (1) Larger virtual queue capacity: Redis List can hold 10M entries. Queue admission rate must match ticket inventory depletion rate — for 5,000 Tatkal seats, admit 50/sec so all seats clear in 100 seconds. (2) Regional queuing: users in North India queue on North India servers; only seat confirmation crosses regions. (3) Pre-registration: require users to register (Aadhaar verification) 24 hours before booking window opens. Non-registered users cannot enter the queue. This reduces fraud and load simultaneously. IRCTC actually uses a virtual queue with captcha and position tracking since 2021.

## Case Study Quick Reference
*Use this table before an interview to quickly identify which concepts a given system design question tests. Cross-reference with Tracks 1–4 for deep dives into individual concepts.*

**#**

**System**

**Key Concepts**

**The #1 Interview Curveball**

**1**

**URL Shortener**

Base62 encoding, KV store, Redis cache, 301 vs 302

*"How do you generate IDs without collision at 12K writes/sec?"*

**2**

**Rate Limiter**

Sliding window counter, Redis Lua scripts, token bucket

*"What if Redis goes down mid-request?"*

**3**

**Pastebin**

Object storage vs DB, CDN, expiry cleanup, content dedup

*"How do you ensure deleted content is gone from CDN?"*

**4**

**Instagram**

Media upload pipeline, CDN, fan-out (push/pull)

*"How do you handle a celebrity with 50M followers posting?"*

**5**

**Twitter Feed**

Fan-out on write vs read vs hybrid, Redis sorted set, Kafka

*"Explain the celebrity problem and your exact hybrid solution"*

**6**

**WhatsApp Chat**

WebSocket, Cassandra, delivery receipts, presence heartbeat

*"How does group chat fan-out work at 500 members scale?"*

**7**

**YouTube**

Chunked upload, HLS transcoding pipeline, CDN, Kafka async

*"How do you handle a video going viral immediately after upload?"*

**8**

**Uber**

Geohash/Redis Geo, trip state machine, matching, surge pricing

*"Walk me through the driver going offline mid-trip"*

**9**

**Google Drive**

Block-level dedup, SHA-256 content addressing, delta sync

*"How does conflict resolution work with two offline edits?"*

**10**

**Notifications**

Kafka fan-out, APNs/FCM/SES, retry with backoff, preferences

*"TRAI DND compliance for India SMS — how do you handle it?"*

**11**

**Autocomplete**

Trie, Redis sorted set top-K, offline frequency aggregation

*"How do trending searches (last 1 hour) update suggestions?"*

**12**

**Web Crawler**

URL frontier, Bloom filter dedup, politeness, robots.txt

*"How do you crawl JavaScript-heavy SPAs?"*

**13**

**Redis Design**

Consistent hashing, LRU eviction, gossip, leader-follower

*"What causes a cache stampede and how do you prevent it?"*

**14**

**Payment System**

Idempotency key, Saga pattern, append-only ledger, webhooks

*"Walk me through the full lifecycle of a failed UPI payment"*

**15**

**Ticket Booking**

Redis SETNX seat lock, virtual queue, pessimistic vs optimistic

*"10M users, 50K seats, 10:00 AM — take me through your design"*

**End of Track 5: System Design in Practice — Case Studies**

*Gautham Gokulakonda | System Design Self-Study Series | All 5 Tracks Complete*

