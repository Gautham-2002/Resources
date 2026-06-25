# Redis: Comparison, Learning Path & Advanced Concepts

## Part 1: Redis vs Other In-Memory Stores

### Redis vs Memcached

| Feature | Redis | Memcached |
|---------|-------|-----------|
| **Data types** | 8+ (Strings, Lists, Sets, etc.) | Strings only |
| **Persistence** | RDB, AOF | None (volatile) |
| **Replication** | Built-in | External (using tools) |
| **Pub/Sub** | Yes | No |
| **Transactions** | Multi-key atomic | No |
| **Scripting** | Lua | No |
| **Memory efficiency** | Good | Slightly better |
| **Speed** | Very fast | Slightly faster |
| **Use case** | Cache + database | Cache only |
| **Setup** | More complex | Simple |

**When to choose:**
- **Redis**: Need data structures, persistence, or transactions
- **Memcached**: Simple string cache, pure performance, distributed by design

---

### Redis vs PostgreSQL (In-Memory Table)

Redis can do some things PostgreSQL does, but trades off differently:

| Feature | Redis | PostgreSQL |
|---------|-------|-----------|
| **Speed** | Microseconds | Milliseconds (with caching) |
| **Query language** | Redis commands | SQL (more powerful) |
| **Persistence** | Optional | Default |
| **ACID** | Partial (single-threaded) | Full ACID |
| **Data volume** | RAM limited | Disk-based (unlimited) |
| **Backups** | Snapshots | Point-in-time recovery |
| **Consistency** | Immediate | Transactional |
| **Transactions** | Multi-key | Multi-table |

**When to choose:**
- **Redis**: Real-time cache, fast counters, queues
- **PostgreSQL**: Complex queries, large datasets, strict consistency

---

### Redis vs Kafka (Message Queue)

Both are different for different reasons:

| Feature | Redis | Kafka |
|---------|-------|-------|
| **Persistence** | Optional | Default (append-only log) |
| **Throughput** | 100k+ ops/sec | 1M+ ops/sec |
| **Retention** | Configurable | Long-term retention |
| **Consumer groups** | Streams (new) | Native | 
| **Ordering** | Per-key guaranteed | Per-partition guaranteed |
| **Use case** | Job queue, real-time | Event streaming, data pipelines |
| **Complexity** | Simple | Complex |
| **Setup** | Single server OK | Cluster recommended |

**When to choose:**
- **Redis**: Simple job queue, notifications, real-time features
- **Kafka**: High-volume streaming, durable audit log, multiple consumers

---

## Part 2: Redis Architecture Deep Dive

### Memory Management

**Memory Types in Redis:**

```
Total Memory = User Data + Metadata + Overhead
                  └─ Keys              └─ Key pointers
                  └─ Values              └─ Encoding info
                  └─ Indexes              └─ Replication

Typical overhead: 10-50% above user data
```

**Memory Optimization:**

```
# Monitor memory
INFO memory

# Results show:
used_memory: 1048576            # Actual memory usage
used_memory_human: "1.00M"      # Human readable
used_memory_rss: 2097152        # Resident set size
mem_fragmentation_ratio: 1.2    # Fragmentation (>1 is bad)

# If fragmentation > 1.5:
redis-cli --latency             # Might be slow
```

**Eviction Policies:**

When memory limit is reached, Redis evicts keys based on policy:

```
# maxmemory-policy options:

1. noeviction         # Reject writes (default, safest)
2. allkeys-lru        # Remove least recently used
3. allkeys-lfu        # Remove least frequently used
4. allkeys-random     # Remove random
5. volatile-lru       # LRU among keys with TTL
6. volatile-lfu       # LFU among keys with TTL
7. volatile-random    # Random among keys with TTL
8. volatile-ttl       # Remove keys with shortest TTL
```

**Configuration:**

```
# Redis config
maxmemory 2gb                   # 2 GB limit
maxmemory-policy allkeys-lru    # LRU eviction

# Or set at runtime
CONFIG SET maxmemory 2gb
CONFIG SET maxmemory-policy allkeys-lru
CONFIG REWRITE                  # Save to file
```

---

### Replication & High Availability

**Master-Slave Replication:**

```
Master (writes):
├─ SET key value
├─ LPUSH list value
└─ (All changes)
   │
   ├─ Sync to Slave 1
   ├─ Sync to Slave 2
   └─ Sync to Slave 3

Slaves (read-only):
├─ Slave 1: [replica of data]
├─ Slave 2: [replica of data]
└─ Slave 3: [replica of data]
```

**Setup:**

```
# Slave configuration
REPLICAOF master.host master.port

# Or in config file:
replicaof 192.168.1.100 6379

# Master can disable writes:
REPLICAOF NO ONE    # Slave becomes master
```

**Failover (Manual):**

```
# If master crashes:
1. Promote slave: REPLICAOF NO ONE
2. Update clients to point to new master
3. Restart old master as slave (if recovered)
```

**Automatic Failover (Sentinel):**

```
# Sentinel monitors master
# If master crashes:
# 1. Detects failure (5 second timeout)
# 2. Gets slave consensus
# 3. Promotes best slave to master
# 4. Redirects clients automatically

# Requires Sentinel running separately
# More complex, more reliable
```

**Cluster (Distributed Redis):**

```
Data automatically sharded across nodes:

┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Cluster 1   │  │ Cluster 2   │  │ Cluster 3   │
│ Slots 0-5461│  │ Slots 5462- │  │ Slots 10923-│
├─ Keys A-F  │  ├─ Keys G-M  │  ├─ Keys N-Z  │
└─────────────┘  └─────────────┘  └─────────────┘

Benefits:
✅ Automatic failover (replica slaves)
✅ Horizontal scaling (add more nodes)
✅ Data sharding (split load)

Trade-offs:
❌ More complex
❌ Some commands don't work (MGET across slots)
❌ Client needs cluster-aware driver
```

---

### Persistence Strategies

**RDB (Snapshots):**

```
SAVE 900 1          # Save if ≥1 change in 900s
SAVE 300 10         # Save if ≥10 changes in 300s
SAVE 60 10000       # Save if ≥10k changes in 60s

# Triggers:
1. On timer (e.g., every 5 min)
2. SAVE command (blocks all operations)
3. BGSAVE command (background, non-blocking)
4. Server shutdown

# Pros:
✅ Compact file (smaller than AOF)
✅ Fast to create (COW on fork)
✅ Fast to restore (load entire snapshot)

# Cons:
❌ Data loss between snapshots (5 min data)
❌ Blocking if not BGSAVE
❌ Large memory spike during snapshot
```

**AOF (Append-Only File):**

```
# Every command is written to file:
SET key value
INCR counter
LPUSH list item
...

# Fsync options:
appendfsync always   # After every write (safest, slowest)
appendfsync everysec # Every second (recommended)
appendfsync no       # OS decides (fastest, risky)

# Rewrite (compact AOF):
BGREWRITEAOF         # Compress large AOF files

# Pros:
✅ Every command persisted (minimal data loss)
✅ Can recover to any point in time
✅ Readable format (can inspect/edit)

# Cons:
❌ Larger file size than RDB
❌ Slower writes
❌ Longer restore time (replay all commands)
```

**Hybrid (RDB + AOF):**

```
# Best of both worlds:
1. BGSAVE every 5 minutes → dump.rdb
2. Write commands to AOF simultaneously

# On restart:
1. Load RDB (fast)
2. Replay AOF since last RDB (fills gap)
3. Combined = fast recovery + minimal data loss

# Configuration:
save 900 1                   # RDB
appendonly yes               # AOF
appendfsync everysec         # Fsync every second
```

---

## Part 3: Advanced Patterns & Techniques

### Pattern: Distributed Rate Limiting

**Problem:** Limit API calls across distributed servers

**Solution: Sliding Window with Redis**

```
# Configure: 100 requests per minute

# Client makes request:
request_count = redis.call('INCR', 'rate:' + user_id)
if request_count == 1:
  redis.call('EXPIRE', 'rate:' + user_id, 60)
end
if request_count <= 100:
  return 'OK'
else
  return '429 Too Many Requests'
end

# Usage:
EVAL (script) 1 rate:user:123 60 100
# Returns: 1 (OK) or 0 (denied)
```

**Better: Token Bucket**

```
# Pre-computed tokens, refill over time

ZADD rate:user:123 (now) "token1"
ZADD rate:user:123 (now) "token2"
... (100 tokens)

ZRANGE rate:user:123 0 99  # Get oldest 100
if size < 100:
  return 'OK'
else
  return 'Too Many Requests'
```

---

### Pattern: Distributed Locks

**Problem:** Ensure only one process runs critical section

**Solution: SET with NX and EX**

```
# Acquire lock
lock = SET "lock:" + resource_id "client:" + uuid \
           NX EX 30
if lock == "OK":
  # You have the lock! (30 second timeout)
  do_critical_work()
  
  # Release lock (IMPORTANT: verify it's yours)
  if GET "lock:" + resource_id == "client:" + uuid:
    DEL "lock:" + resource_id
else:
  # Someone else has it
  return 'Failed to acquire lock'
```

**Problem:** What if client crashes without releasing?

**Solution:** Timeout (EX 30) ensures auto-release

**Better: Redlock (Multiple Redis)**

```
# Acquire lock on N/2+1 servers
acquired = 0
for server in [server1, server2, server3]:
  if SET "lock:" + resource_id uuid NX EX 30:
    acquired += 1
    
if acquired > 1:  # 2 out of 3
  # You have majority, safe to proceed
  do_critical_work()
  # Release on all servers
```

---

### Pattern: Cache Warming

**Problem:** Cold cache on startup, slow first requests

**Solution: Preload common data**

```
# On startup:
function warm_cache():
  # Get top products
  products = DB.query("SELECT * FROM products LIMIT 1000")
  for product in products:
    SETEX "product:" + product.id 3600 \
          JSON.stringify(product)
  
  # Get top users
  users = DB.query("SELECT * FROM users LIMIT 10000")
  for user in users:
    SETEX "user:" + user.id 3600 \
          JSON.stringify(user)
  
  log("Cache warmed with " + count + " items")

# Run on startup or scheduled
```

---

### Pattern: Bulk Import/Export

**Problem:** Need to migrate data to/from Redis

**Solution: Use PIPE protocol**

```
# Export (read from Redis, write to file)
redis-cli --rdb /tmp/dump.rdb --pipe < export.txt

# Or programmatically:
import redis
from redis.connection import dump_protocol

client = redis.Redis()
for key in client.keys('*'):
  value = client.get(key)
  print(dump_protocol(key, value))

# Import:
redis-cli --pipe < import.txt

# Or:
redis-cli --csv "GET *" > data.csv
```

---

### Pattern: Feature Flags

**Problem:** Enable/disable features without code deploy

**Solution: Redis flags**

```
# Set flags
HSET "features" "dark_mode" "true"
HSET "features" "beta_api" "true"
HSET "features" "debug_logs" "false"

# Check flag
def is_feature_enabled(feature):
  return HGET("features", feature) == "true"

# Usage
if is_feature_enabled("dark_mode"):
  apply_dark_theme()

if is_feature_enabled("beta_api"):
  use_new_api()
```

---

### Pattern: Geo-location Indexing

**Problem:** Find nearby users/locations

**Solution: Geospatial indexes**

```
# Add locations
GEOADD "locations" 13.361389 38.115556 "Palermo"
GEOADD "locations" 15.087269 37.502669 "Catania"

# Find within radius
GEORADIUS "locations" 15 37 200 km WITHDIST
# Finds all cities within 200 km of (15, 37)

# Distance between
GEODIST "locations" "Palermo" "Catania"
# Returns: 166 km

# Real-world: Find nearby restaurants
GEOADD "restaurants" latitude longitude "restaurant_id"
GEORADIUS "restaurants" user_lat user_lng 5 km
```

---

## Part 4: Monitoring & Troubleshooting

### Key Metrics to Monitor

```
# Memory
used_memory                 # Total memory used
mem_fragmentation_ratio     # > 1.5 is bad (causes eviction)
maxmemory                   # Configured limit
evicted_keys                # Keys removed due to memory

# Performance
ops_per_sec                 # Throughput
instantaneous_ops_per_sec   # Current throughput
total_commands_processed    # Total commands

# Connections
connected_clients           # Number of clients
client_recent_max_input_buf # Largest input buffer
client_recent_max_output_buf # Largest output buffer

# Replication
role                       # master or slave
connected_slaves           # Number of slave connections
replication_offset         # Sync position

# CPU
cpu_sys                    # System CPU
cpu_user                   # User CPU
cpu_time_in_microseconds   # Total CPU time
```

### Common Issues & Solutions

**Issue 1: High Memory Usage**

```
# Check what's using memory:
MEMORY DOCTOR               # Detailed memory report

# Find large keys:
redis-cli --bigkeys         # Find largest keys

# Solutions:
1. Increase maxmemory
2. Evict old data (set TTL)
3. Compress values (JSON -> MessagePack)
4. Use smaller data types (HYPERLOGLOG instead of SET)
5. Delete unused keys

# Clean up:
FLUSHDB                     # Delete all (careful!)
FLUSHALL                    # Delete all DBs (careful!)
```

**Issue 2: Slow Performance**

```
# Check slowlog:
SLOWLOG GET 10              # 10 slowest commands
SLOWLOG LEN                 # Number of slow commands
SLOWLOG RESET               # Clear slowlog

# Common causes:
1. KEYS command (O(N)) - use SCAN instead
2. Large LPUSH/LPOP - smaller operations
3. MGET all million keys - page through
4. Blocking operations with timeout - use 0

# Examples of slow:
KEYS *                      # SLOW - scans all
SCAN 0                      # FAST - iterates

# Solutions:
1. Use appropriate commands
2. Add indexes (proper key naming)
3. Use PIPELINE for batches
4. Monitor with SLOWLOG
5. Increase slowlog-threshold-microseconds
```

**Issue 3: Replication Lag**

```
# Check replication:
INFO replication            # Shows master/slave status

# If slave is lagging:
# Check network between master and slave
# Check slave CPU/memory

# Solutions:
1. Increase slave disk I/O
2. Reduce write throughput to master
3. Use PSYNC (partial resync) instead of SYNC
4. Check network latency

# Commands:
ROLE                        # Current role
REPLICAOF NO ONE           # Disconnect from master
REPLICAOF host port        # Connect to master
```

**Issue 4: High Memory Fragmentation**

```
# Check fragmentation:
INFO memory | grep fragmentation

# If mem_fragmentation_ratio > 1.5:

# Solutions:
1. Restart Redis gracefully
   - Takes down service temporarily
   - But compacts memory

2. Use BGSAVE then restart
   - More time but better

3. Monitor and prevent:
   - Set activerehashing to help (default yes)
   - Avoid large batch deletes
   - Use UNLINK instead of DEL for large keys
```

---

## Part 5: Learning Path

### Week 1: Fundamentals
- [ ] Read redis_mastery_guide.md Part 1-2
- [ ] Learn about data types (String, List, Set, Hash, ZSet)
- [ ] Install Redis locally
- [ ] Run first commands
- [ ] Understand persistence (RDB vs AOF)

**Time:** 2-3 hours/day, 5 days

### Week 2: Data Types & Operations
- [ ] Master each data type
- [ ] Run 100+ examples from redis_examples.md
- [ ] Build small projects:
  - Counter (INCR)
  - Queue (LPUSH/RPOP)
  - Leaderboard (ZADD/ZRANGE)
  - Session storage (HSET/HGETALL)
- [ ] Understand TTL and expiration

**Time:** 3-4 hours/day, 5 days

### Week 3: Advanced Patterns
- [ ] Transactions (MULTI/EXEC)
- [ ] Pub/Sub messaging
- [ ] Rate limiting
- [ ] Caching strategies
- [ ] Lua scripting basics

**Time:** 3-4 hours/day, 5 days

### Week 4: Production & Scaling
- [ ] High availability (replication)
- [ ] Persistence strategies
- [ ] Monitoring and debugging
- [ ] Performance optimization
- [ ] Build production project

**Time:** 4-5 hours/day, 5 days

---

## Part 6: Redis Checklist

### Before Using Redis

- [ ] Does your use case need Redis? (caching, counters, queues, real-time)
- [ ] Will all data fit in RAM?
- [ ] Is eventual consistency OK?
- [ ] Have you sized memory correctly?

### Before Going to Production

- [ ] Persistence strategy decided (RDB, AOF, or hybrid)?
- [ ] Replication configured?
- [ ] Memory limit and eviction policy set?
- [ ] Monitoring in place (memory, CPU, connections)?
- [ ] Backup strategy defined?
- [ ] Failover plan documented?
- [ ] Connection pooling configured?
- [ ] Keys have appropriate TTL?
- [ ] Slowlog threshold set?
- [ ] Have you load tested?

### Data Design Checklist

- [ ] Key naming convention consistent?
- [ ] Keys expire when appropriate?
- [ ] Using correct data type per use case?
- [ ] Values not too large (>1MB)?
- [ ] Indexes defined for hot keys?
- [ ] Related data properly namespaced?

### Performance Checklist

- [ ] Using PIPELINE for batches?
- [ ] Using MGET/MSET for multiple keys?
- [ ] Not using KEYS in production?
- [ ] Appropriate data types (ZSET for leaderboards)?
- [ ] TTL prevents unbounded growth?
- [ ] Slowlog monitored regularly?
- [ ] Memory fragmentation < 1.2?

---

## Summary: When to Use Redis

### Perfect Fit for Redis ✅
- Caching (huge speed boost)
- Real-time counters (page views, API calls)
- Rate limiting (sub-millisecond checks)
- Session storage (fast, distributed)
- Job queues (simple, reliable)
- Leaderboards (native sorted sets)
- Real-time features (Pub/Sub)
- Temporary data (auto-expire)

### Not Ideal for Redis ❌
- Large datasets (won't fit in RAM)
- Complex queries (no SQL)
- Strong ACID transactions (single-threaded limits)
- Durable event log (use Kafka instead)
- Full-text search (use Elasticsearch)

### Redis + Other Tools

**Recommended Stack:**
```
PostgreSQL (structured data)
├─ For: Customer records, transactions, complex queries
└─ Persistence: Durable, queryable, ACID

Redis (cache + real-time)
├─ For: Caching, counters, sessions, queues
└─ Speed: Microseconds, atomic operations

Elasticsearch (search)
├─ For: Full-text search, log analysis
└─ Features: Relevance, analysis, aggregation

Kafka (streams)
├─ For: High-volume event streaming
└─ Durability: Append-only, unlimited retention
```

---

## Next Steps

1. **Install Redis:** `brew install redis` or `apt-get install redis-server`
2. **Run examples:** Copy-paste from redis_examples.md
3. **Build a project:** Caching, counters, or queue
4. **Deploy:** Configure persistence, replication, monitoring
5. **Optimize:** Use slowlog, monitor memory, tune performance
6. **Learn more:** Check Redis official docs, redis.io

---

You now understand Redis at an expert level. The remaining skill is hands-on practice building real systems!
