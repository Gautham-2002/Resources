# Redis Mastery: From Fundamentals to Advanced Patterns

## Part 1: Redis Philosophy & Architecture

### What is Redis?

Redis is an in-memory data structure store that functions as a database, cache, message broker, and real-time engine. Unlike PostgreSQL (disk-based relational) and MongoDB (disk-based document), Redis keeps **everything in RAM**.

**Redis stands for:** Remote Dictionary Server

### Why Redis Stands Out

1. **Blazingly Fast**: Sub-millisecond latencies (microseconds for simple operations)
   - In-memory storage (no disk I/O)
   - Optimized C implementation
   - Single-threaded (no lock contention)

2. **Data Structure Server**: Not just key-value, but rich data types
   - Strings (simple values)
   - Lists (ordered collections)
   - Sets (unique values)
   - Sorted Sets (weighted rankings)
   - Hashes (nested objects)
   - Streams (append-only logs)
   - Bitmaps (bit operations)
   - HyperLogLog (cardinality estimation)
   - Geospatial indexes

3. **Persistence Options**: Choose your trade-off
   - RDB: Snapshots (fast, risk data loss between snapshots)
   - AOF: Append-Only File (slower, safer)
   - Hybrid: Both

4. **Replication**: Master-slave replication for high availability
5. **Pub/Sub**: Real-time messaging
6. **Transactions**: Multi-command atomicity (not as strong as ACID)
7. **Scripting**: Lua scripting for complex operations

### When Redis Wins

| Use Case | Why Redis | Alternative |
|----------|-----------|-------------|
| **Caching** | Ultra-fast, automatic expiration | Memcached (simpler) |
| **Sessions** | Store user sessions in-memory | Database (slower) |
| **Real-time counters** | Atomic increments, instant results | Database (requires lock) |
| **Leaderboards** | Sorted sets built-in | Database with sorting |
| **Rate limiting** | Fast checks, sliding windows | Database (too slow) |
| **Job queues** | Lists + blocking operations | RabbitMQ (more features) |
| **Real-time analytics** | HyperLogLog for cardinality | Database (expensive) |
| **Pub/Sub messaging** | Lightweight, fast | Kafka (persistent) |
| **Full-text search** | Not built-in, use Elasticsearch | Elasticsearch |
| **Transactions** | Multi-key atomicity | PostgreSQL (stronger) |

### Redis vs Memcached

| Feature | Redis | Memcached |
|---------|-------|----------|
| **Data types** | 8+ types | Strings only |
| **Persistence** | RDB, AOF | None (cache only) |
| **Replication** | Built-in | No |
| **Pub/Sub** | Yes | No |
| **Transactions** | Yes | No |
| **Scripting** | Lua | No |
| **Speed** | Slightly slower | Slightly faster |
| **Memory efficiency** | Good | Better |
| **Use case** | Database + cache | Cache only |

**Use Memcached for:** Simple string caching where you don't care about data loss  
**Use Redis for:** Complex operations, persistence, or data structure needs

---

## Part 2: Redis Architecture Explained

### Single-Threaded Model

```
Client 1 ─┐
Client 2 ─┤
Client 3 ─┼─> [Single Event Loop] ─> [Memory]
Client N ─┤    (No locks needed!)
```

**Implications:**
- ✅ No race conditions (atomic operations)
- ✅ No lock contention (super fast)
- ❌ One slow command blocks everyone
- ❌ Can't use all CPU cores (single-threaded)

**Modern Redis (6.0+):** Multi-threaded I/O (networking), but command execution still single-threaded

### Memory Management

Redis stores everything in RAM. This means:

**Advantages:**
- Microsecond latencies
- Consistent performance
- No disk I/O bottlenecks

**Challenges:**
- Cost: RAM is expensive
- Limit: Data must fit in memory
- Loss: Crash means data loss (without persistence)

**Solutions:**
- Persistence: RDB or AOF
- Replication: Backup to another server
- Cluster: Shard data across servers
- Eviction policy: Automatically remove old data

### Persistence: RDB vs AOF

**RDB (Redis Database Snapshot)**
```
At intervals (e.g., every 5 minutes), save entire dataset to disk

Save entire memory snapshot (fork + copy on write)
├── Fast to write (sequential disk writes)
├── Small file size (compact)
├── Fast to restore (load snapshot into RAM)
├── But: Loses data between snapshots
└── Example: Crash happens, lose 5 minutes of data
```

**AOF (Append-Only File)**
```
Log every command that modifies data

Write every command: SET key value, INCR counter, etc.
├── Slow to write (more I/O)
├── Large file size (every command logged)
├── Fast to restore (replay all commands)
├── And: No data loss (every command persisted)
└── But: Slower than RDB
```

**Hybrid (Modern approach):**
```
Use RDB for snapshots + AOF for durability
├── Load RDB (fast)
├── Then replay AOF commands since last snapshot (fills gap)
└── Best of both worlds
```

---

## Part 3: Redis Data Types Deep Dive

### 1. Strings (Binary-Safe)

The most basic type. Stores anything from simple text to serialized JSON or binary data.

```
Key: "user:1:name"    Value: "Alice"
Key: "counter"        Value: "42"
Key: "session:abc"    Value: (JSON blob)
```

**Common operations:**
- `SET key value` - Set value
- `GET key` - Get value
- `INCR key` - Increment by 1
- `DECR key` - Decrement by 1
- `INCRBY key 5` - Increment by 5
- `APPEND key " suffix"` - Append to string
- `GETRANGE key 0 5` - Get substring
- `STRLEN key` - Get length
- `SETEX key 3600 value` - Set with expiration (3600 seconds)
- `MSET key1 val1 key2 val2` - Multiple set
- `MGET key1 key2 key3` - Multiple get

**Use cases:**
- User profile data
- Configuration values
- Counters (page views, API calls)
- Rate limiting tokens

---

### 2. Lists (Ordered Collections)

Ordered, mutable sequences. Think of them as queues or stacks.

```
Key: "queue:tasks"
Value: [Task1, Task2, Task3, ...]  (Left = Head, Right = Tail)

Operations:
  LPUSH (add to left)   RPUSH (add to right)
  LPOP (remove left)    RPOP (remove right)
  LLEN (length)         LRANGE (get range)
```

**Operations:**
- `LPUSH list value` - Add to left (head)
- `RPUSH list value` - Add to right (tail)
- `LPOP list` - Remove and return from left
- `RPOP list` - Remove and return from right
- `LLEN list` - List length
- `LRANGE list 0 -1` - Get all elements
- `LRANGE list 0 10` - Get first 11
- `LTRIM list 0 10` - Keep only first 11
- `BLPOP list timeout` - Blocking pop (wait for data)
- `LINDEX list 0` - Get element at index
- `LSET list 0 value` - Set element at index

**Use cases:**
- Job queues (LPUSH producer, RPOP consumer)
- Activity feeds (newest at left)
- Undo stacks (push, pop)
- Rate limiting sliding window

**Performance:**
- Push/Pop: O(1) - always fast
- Get range: O(N) - slower for large ranges
- Index access: O(N) - slow (scan from head)

---

### 3. Sets (Unique Values)

Unordered collections of unique members. No duplicates.

```
Key: "user:1:tags"
Value: {premium, vip, loyal}  (no order, no duplicates)
```

**Operations:**
- `SADD set member` - Add member
- `SREM set member` - Remove member
- `SCARD set` - Set size (cardinality)
- `SMEMBERS set` - Get all members
- `SISMEMBER set member` - Check if member exists
- `SINTER set1 set2` - Intersection
- `SUNION set1 set2` - Union
- `SDIFF set1 set2` - Difference
- `SPOP set` - Remove and return random
- `SRANDMEMBER set 3` - Get 3 random members

**Use cases:**
- Tags and categories
- Unique visitors (check if user already counted)
- Friend lists
- Blocking/allow lists
- Finding common elements

**Performance:**
- Add/Remove: O(1)
- Member check: O(1)
- Union/Intersection: O(N+M)

---

### 4. Sorted Sets (Ranked Collections)

Sets with scores. Automatically ordered by score.

```
Key: "leaderboard:games"
Value: {
  alice: 9500,     (score=9500)
  bob: 8700,       (score=8700)
  carol: 9200      (score=9200)
}

Sorted by score: alice (9500), carol (9200), bob (8700)
```

**Operations:**
- `ZADD set score member` - Add member with score
- `ZREM set member` - Remove member
- `ZSCORE set member` - Get member's score
- `ZCARD set` - Count members
- `ZRANGE set 0 -1` - Get all (low to high score)
- `ZREVRANGE set 0 -1` - Get all (high to low score)
- `ZRANGE set 0 9 WITHSCORES` - Get with scores
- `ZRANK set member` - Get rank (0-indexed)
- `ZREVRANK set member` - Get reverse rank
- `ZCOUNT set 1000 5000` - Count in score range
- `ZRANGEBYSCORE set 1000 5000` - Get by score range
- `ZINCRBY set 10 member` - Increment score

**Use cases:**
- Leaderboards (sort by score)
- Top products (sort by rating)
- Latest posts (sort by timestamp)
- Priority queues (sort by priority)
- Rate limiting (timestamps as scores)

**Performance:**
- Add/Remove: O(log N)
- Range: O(log N + M) where M is result size
- Rank lookup: O(log N)

---

### 5. Hashes (Nested Objects)

Maps with field-value pairs. Like nested objects.

```
Key: "user:1"
Value: {
  name: "Alice",
  email: "alice@example.com",
  age: 30,
  created_at: "2024-01-15"
}
```

**Operations:**
- `HSET hash field value` - Set field
- `HGET hash field` - Get field value
- `HMSET hash f1 v1 f2 v2` - Set multiple fields
- `HMGET hash f1 f2 f3` - Get multiple fields
- `HGETALL hash` - Get all fields and values
- `HDEL hash field` - Delete field
- `HEXISTS hash field` - Check if field exists
- `HLEN hash` - Count fields
- `HKEYS hash` - Get all field names
- `HVALS hash` - Get all values
- `HINCRBY hash field 1` - Increment numeric field
- `HSTRLEN hash field` - String length of field

**Use cases:**
- User profiles
- Product details
- Configuration objects
- Session data

**Performance:**
- Set/Get field: O(1)
- Get all: O(N) where N is field count
- Increment: O(1)

---

### 6. Streams (Append-Only Logs)

New type (Redis 5.0+). Like a log file with automatic IDs.

```
Key: "events:stream"
Value: [
  {id: 1234567-0, data: {user: "alice", action: "login"}},
  {id: 1234567-1, data: {user: "bob", action: "purchase"}},
  ...
]
```

**Operations:**
- `XADD stream * field value` - Add entry (auto ID)
- `XLEN stream` - Stream length
- `XRANGE stream - +` - Get all
- `XRANGE stream 0-0 1000-0` - Get range by ID
- `XREAD COUNT 10 STREAMS stream 0` - Read (blocking)
- `XGROUP CREATE stream group $` - Consumer group
- `XREADGROUP GROUP group consumer STREAMS stream >` - Read with consumer group

**Use cases:**
- Event logging
- Activity feeds
- IoT sensor data
- Distributed logs

---

### 7. Bitmaps (Bit Operations)

Strings where you can manipulate individual bits.

```
Key: "active_users_today"
Value: (bitmap where each bit = 1 user)
  Bit 1 set = user 1 is active
  Bit 5 set = user 5 is active
```

**Operations:**
- `SETBIT key offset 1` - Set bit to 1
- `GETBIT key offset` - Get bit value
- `BITCOUNT key` - Count set bits
- `BITPOS key 1` - Find first set bit
- `BITOP AND dest key1 key2` - Bitwise AND
- `BITOP OR dest key1 key2` - Bitwise OR

**Use cases:**
- Daily active users (memory efficient)
- Real-time analytics
- Boolean flags
- Bloom filters

**Memory efficiency:**
- 1 million users = ~125 KB (not 1 million keys!)

---

### 8. HyperLogLog (Cardinality Estimation)

Probabilistic data structure for counting unique items.

```
Key: "unique_visitors:today"
Value: (compact representation of ~100 million items)
```

**Operations:**
- `PFADD hll element` - Add element
- `PFCOUNT hll` - Count unique elements (approximate)
- `PFMERGE dest hll1 hll2` - Merge multiple HyperLogLogs

**Use cases:**
- Count unique visitors (don't need exact count)
- Unique IP addresses
- Unique search queries

**Memory efficiency:**
- Fixed size: ~12 KB per HyperLogLog
- Accuracy: ~1% error
- Trade-off: Memory vs Accuracy

---

## Part 4: Basic Commands & Operations

### Key Operations

```redis
# Create/Modify keys
SET mykey "Hello"              # Set string value
MSET k1 v1 k2 v2              # Set multiple keys
SET mykey "World" EX 3600      # Set with expiration (1 hour)
SETNX mykey "Hello"            # Set only if not exists
INCR counter                   # Increment number
APPEND mykey " World"          # Append to string

# Read keys
GET mykey                      # Get value
MGET k1 k2 k3                  # Get multiple values
GETRANGE mykey 0 4             # Get substring
STRLEN mykey                   # Get length

# Delete/Expire
DEL mykey                      # Delete key
UNLINK mykey                   # Delete key (async)
EXPIRE mykey 3600              # Set expiration (1 hour)
TTL mykey                      # Get time to live
PTTL mykey                     # Get time in milliseconds
PERSIST mykey                  # Remove expiration

# Check keys
EXISTS mykey                   # Check if exists
TYPE mykey                     # Get key type
KEYS pattern                   # Find keys matching pattern (SLOW!)
SCAN cursor MATCH pattern      # Iterate keys (faster)

# Database operations
FLUSHDB                        # Delete all keys in database
FLUSHALL                       # Delete all keys in all databases
DBSIZE                         # Count keys
SELECT 0                       # Select database 0
```

### String Operations

```redis
# Strings (covered above)
SET user:1:name "Alice"        # Set
GET user:1:name                # Get: "Alice"
APPEND user:1:name " Johnson"  # Append
STRLEN user:1:name             # Length: 14
GETRANGE user:1:name 0 4       # Substring: "Alice"

# Numeric strings
INCR page:views                # Increment: 1
INCR page:views                # Increment: 2
INCRBY page:views 10           # Add 10: 12
DECR page:views                # Decrement: 11
DECRBY page:views 5            # Subtract 5: 6

# Multiple operations
MSET u1 Alice u2 Bob u3 Carol  # Set 3 keys
MGET u1 u2 u3                  # Get 3 keys: [Alice, Bob, Carol]

# With expiration
SETEX temp_token 3600 "abc123" # Set with 1 hour expiration
PSETEX temp_token 1000 "xyz"   # Set with 1000ms expiration
```

### List Operations

```redis
# Creating lists
LPUSH tasks "task1"            # [task1]
LPUSH tasks "task2"            # [task2, task1]
RPUSH tasks "task3"            # [task2, task1, task3]

# Reading
LLEN tasks                      # Length: 3
LRANGE tasks 0 -1              # All: [task2, task1, task3]
LINDEX tasks 0                 # First: task2
LINDEX tasks -1                # Last: task3

# Popping
LPOP tasks                     # Remove from left: task2
RPOP tasks                     # Remove from right: task3
# Now: [task1]

# Trimming
LTRIM tasks 0 5                # Keep first 6
LTRIM tasks 1 -1               # Remove first

# Blocking (wait for data)
BLPOP tasks 5                  # Wait up to 5 sec for item
```

### Set Operations

```redis
# Adding to sets
SADD tags "python"             # {python}
SADD tags "redis"              # {python, redis}
SADD tags "database"           # {python, redis, database}

# Reading
SCARD tags                     # Size: 3
SMEMBERS tags                  # All: [python, redis, database]
SISMEMBER tags "python"        # Is member? true
SISMEMBER tags "javascript"    # Is member? false

# Removing
SREM tags "python"             # Remove: {redis, database}
SPOP tags                      # Remove random: {redis}
SRANDMEMBER tags 5             # Get 5 random (with duplicates)

# Set operations
SADD users:online "alice"
SADD users:online "bob"
SADD users:active "bob"
SADD users:active "carol"

SINTER users:online users:active      # Intersection: {bob}
SUNION users:online users:active      # Union: {alice, bob, carol}
SDIFF users:online users:active       # Difference: {alice}
SINTERSTORE dest u:o u:a             # Intersection, store in dest
```

### Sorted Set Operations

```redis
# Adding to sorted set
ZADD leaderboard 100 "alice"
ZADD leaderboard 95 "bob"
ZADD leaderboard 105 "carol"

# Reading
ZCARD leaderboard              # Count: 3
ZSCORE leaderboard "alice"     # Score: 100
ZRANK leaderboard "bob"        # Rank (lowest first): 1
ZREVRANK leaderboard "bob"     # Reverse rank: 1

# Range queries
ZRANGE leaderboard 0 -1        # All (low→high): [bob, alice, carol]
ZREVRANGE leaderboard 0 -1     # All (high→low): [carol, alice, bob]
ZREVRANGE leaderboard 0 2 WITHSCORES  # Top 3 with scores

# Range by score
ZRANGEBYSCORE leaderboard 95 105  # Between 95-105: [bob, alice, carol]
ZCOUNT leaderboard 95 105         # Count in range: 3

# Incrementing scores
ZINCRBY leaderboard 5 "bob"    # bob's score: 100
ZREVRANGE leaderboard 0 -1     # [bob, carol, alice]
```

### Hash Operations

```redis
# Setting fields
HSET user:1 name "Alice"
HSET user:1 email "alice@example.com"
HSET user:1 age 30

# Or multiple at once
HMSET user:1 name Alice email alice@example.com age 30

# Getting fields
HGET user:1 name              # "Alice"
HMGET user:1 name email       # [Alice, alice@example.com]
HGETALL user:1                # {name: Alice, email: ..., age: 30}

# Field operations
HLEN user:1                   # Count fields: 3
HKEYS user:1                  # Field names: [name, email, age]
HVALS user:1                  # Values: [Alice, alice@example.com, 30]
HEXISTS user:1 name           # Field exists? true
HDEL user:1 age               # Delete field

# Numeric fields
HINCRBY user:1 age 1          # Increment age by 1
HINCRBYFLOAT user:1 salary 1.5  # Increment by float
```

---

## Part 5: Advanced Patterns

### Pattern 1: Caching (Cache-Aside)

```
Application needs data:
1. Check Redis (fast)
   - If exists (HIT): return from Redis
   - If missing (MISS): continue to step 2
2. Query database (slow)
3. Store in Redis for next time
4. Return to user

Code:
function getUser(userId):
    cached = REDIS.GET("user:" + userId)
    if cached:
        return JSON.parse(cached)
    
    user = DATABASE.query("SELECT * FROM users WHERE id = ?", userId)
    REDIS.SETEX("user:" + userId, 3600, JSON.stringify(user))
    return user
```

**Trade-offs:**
- ✅ Faster response time
- ✅ Reduces database load
- ❌ Possible stale data (cache older than DB)
- ❌ Cache invalidation complexity

---

### Pattern 2: Rate Limiting (Sliding Window)

```
User makes API request:
1. Get current count: REDIS.GET("rate:" + userId)
2. Check if limit exceeded (e.g., 100 requests/minute)
3. If not exceeded:
   - Increment: REDIS.INCR("rate:" + userId)
   - Set expiration if first request: REDIS.EXPIRE("rate:" + userId, 60)
   - Allow request
4. If exceeded:
   - Reject with 429 Too Many Requests

Code (Lua script for atomicity):
local current = redis.call('incr', KEYS[1])
if current == 1 then
  redis.call('expire', KEYS[1], ARGV[1])
end
if current <= tonumber(ARGV[2]) then
  return 1  -- Allow
else
  return 0  -- Deny
end

Redis call:
EVAL "script" 1 "rate:user:123" 60 100
  (60 = expire seconds, 100 = limit)
```

---

### Pattern 3: Session Storage

```
User logs in:
1. Generate session token: token = random()
2. Store session data: REDIS.HSET("session:" + token, "user_id", 123, "ip", "1.2.3.4", "created_at", now())
3. Set expiration: REDIS.EXPIRE("session:" + token, 3600)
4. Return token to client

User makes request with token:
1. Check session: REDIS.HGETALL("session:" + token)
2. If exists and valid:
   - Refresh TTL: REDIS.EXPIRE("session:" + token, 3600)
   - Allow request
3. If expired or missing:
   - Redirect to login

Code:
SESSION_KEY = "session:" + token
user_data = REDIS.HGETALL(SESSION_KEY)
if user_data:
  REDIS.EXPIRE(SESSION_KEY, 3600)  # Refresh
  return user_data
else:
  redirect_to_login()
```

---

### Pattern 4: Job Queue

```
Producer:
LPUSH "queue:jobs" JSON.stringify({type: "email", to: "alice@example.com", subject: "Hello"})

Consumer:
while True:
  job = REDIS.BLPOP("queue:jobs", timeout=1)  # Block until job arrives
  if job:
    process(job)
    if success:
      REDIS.LPUSH("queue:completed", job)
    else:
      REDIS.LPUSH("queue:failed", job)

Code:
BLPOP queue:jobs 1  # Wait 1 second for job
# Returns: [queue:jobs, "{job_data}"]
```

---

### Pattern 5: Leaderboard

```
Player makes high score:
ZADD "leaderboard:game:123" 9500 "alice"
ZADD "leaderboard:game:123" 8700 "bob"
ZADD "leaderboard:game:123" 9200 "carol"

Get top 10:
ZREVRANGE "leaderboard:game:123" 0 9 WITHSCORES
# Returns: [carol, 9200, alice, 9500, bob, 8700] (high to low)

Get player rank:
ZREVRANK "leaderboard:game:123" "alice"  # Returns: 0 (first place)

Increment score:
ZINCRBY "leaderboard:game:123" 100 "bob"  # bob's score now 8800
```

---

### Pattern 6: Real-time Analytics

```
Track page views:
INCR "page:views"           # Total: 1
INCR "page:views:today"     # Today: 1
INCR "page:views:2024-01"   # This month: 1
SADD "unique:visitors"      # Unique: {user_123}
PFADD "hll:visitors"        # Approximate unique

Get stats:
GET "page:views"            # 1000
GET "page:views:today"      # 150
SCARD "unique:visitors"     # 500
PFCOUNT "hll:visitors"      # ~502 (approx)
```

---

### Pattern 7: Pub/Sub Messaging

```
Subscriber (listener):
SUBSCRIBE "notifications:channel"
# Waits for messages...
# Receives: "Hello World"

Publisher (sender):
PUBLISH "notifications:channel" "Hello World"
# Returns: 1 (number of subscribers)

Code:
# Subscriber
def listen():
  redis = Redis()
  pubsub = redis.pubsub()
  pubsub.subscribe("notifications")
  for message in pubsub.listen():
    print(message['data'])

# Publisher
redis.publish("notifications", "New order received")

# Warning: Pub/Sub is fire-and-forget
# - No persistence
# - No offline subscribers
# Use Streams for persistence
```

---

### Pattern 8: Bloom Filter

```
Check if email ever saw (memory efficient):
SETBIT "emails:seen:2024-01" 1000 1  # Mark email 1000 as seen
GETBIT "emails:seen:2024-01" 1000    # Check: 1 (seen)
GETBIT "emails:seen:2024-01" 2000    # Check: 0 (not seen)

Memory efficient for millions:
1 million emails = ~125 KB (not 1 million records!)

Trade-off:
- ✅ Tiny memory footprint
- ✅ O(1) operations
- ❌ Can't delete (set bits, not unset)
- ❌ Only store presence, not data
```

---

### Pattern 9: Distributed Lock

```
Acquire lock:
SET "lock:resource" "client_id" NX EX 30
# NX = only set if not exists
# EX = expire in 30 seconds

If returned "OK":
  You have the lock! Do work...
  DEL "lock:resource"  # Release when done

If returned nil:
  Someone else has it, try again later

Better approach (Lua script):
redis.call('SET', KEYS[1], ARGV[1], 'NX', 'EX', ARGV[2])

Redlock (multiple Redis servers):
- Acquire lock on N/2+1 servers
- If successful, you have the lock
- If failed, release all partial locks
```

---

## Part 6: Advanced Features

### Transactions (MULTI/EXEC)

```
Start transaction:
MULTI
SET key1 value1
INCR key2
GET key1
EXEC

# All commands execute atomically
# Either all succeed or all fail
# No other client can interfere

Practical example:
MULTI
INCR balance:alice:-100
INCR balance:bob:+100
EXEC
# Transfer is atomic
```

### Pipelining (Batch Commands)

```
Without pipelining:
SET key1 val1
SET key2 val2
SET key3 val3
# 3 network round trips

With pipelining:
PIPE = redis.pipeline()
PIPE.set('key1', 'val1')
PIPE.set('key2', 'val2')
PIPE.set('key3', 'val3')
PIPE.execute()
# 1 network round trip (much faster!)
```

### Lua Scripting

```
Script execution is atomic:
SCRIPT:
local count = redis.call('INCR', KEYS[1])
if count > tonumber(ARGV[1]) then
  return 0  -- Limit exceeded
else
  return 1  -- Allow
end

Execute:
EVAL "script" 1 "counter" 100
# Returns: 1 or 0

Benefits:
- Atomic execution
- Reduce network round trips
- Complex logic in Redis
```

---

## Part 7: Persistence & High Availability

### RDB (Snapshots)

```
Configuration:
SAVE 900 1          # Save if 1+ changes in 900 sec
SAVE 300 10         # Save if 10+ changes in 300 sec
SAVE 60 10000       # Save if 10k+ changes in 60 sec

Trigger manually:
SAVE                # Blocking save (locks Redis)
BGSAVE              # Background save (async)

Restore:
# Automatic on startup
redis-server will load dump.rdb if exists
```

### AOF (Append-Only File)

```
Configuration:
appendonly yes
appendfsync everysec  # Fsync every second (balance)

Options:
appendfsync always    # Fsync every write (safe, slow)
appendfsync everysec  # Fsync every second (default)
appendfsync no        # OS decides when to fsync (fast, risky)

Rewrite (compress AOF):
BGREWRITEAOF          # Compact the AOF file
# Useful: AOF file can grow large
```

### Replication

```
Primary (Master):
# Default behavior, accepts writes

Secondary (Slave):
REPLICAOF primary.host primary.port
# Syncs with primary, reads only

Failover:
If primary crashes, promote slave:
REPLICAOF NO ONE     # Slave becomes master

Cluster:
Multiple nodes with automatic failover
CLUSTER MEET, CLUSTER ADDSLOTS, etc.
```

---

## Part 8: Key Design Patterns

### Naming Conventions

```
Good naming makes relationships clear:

User data:
user:1:name            # User 1 name
user:1:email           # User 1 email
user:1:profile         # User 1 profile hash

Posts:
post:1:content         # Post 1 content
post:1:likes           # Post 1 like count
post:1:comments        # Post 1 comment list

Counters:
counter:page_views
counter:api_calls
counter:error_404

Sessions:
session:abc123         # Session token

Relationships:
user:1:posts           # Posts by user 1
user:1:followers       # Followers of user 1
post:1:liked_by        # Users who liked post 1
```

### Key Expiration Strategy

```
Short-lived (cache):
SETEX "cache:user:1" 3600 data     # 1 hour

Medium-lived (session):
SETEX "session:token" 86400 data   # 1 day

Long-lived (reference):
SET "reference:data" data          # No expiration

Auto-expire with pattern:
SETEX "temp:upload:123" 1800 data  # 30 min temp file
SETEX "otp:user:123" 300 data      # 5 min OTP

Sliding expiration:
On each access, reset TTL:
EXPIRE "session:token" 3600        # Extends session
```

---

## Part 9: Memory Management

### Memory Monitoring

```
Check memory:
INFO memory
# Shows: used_memory, peak_memory, fragmentation ratio

Key space analysis:
DBSIZE                # Total keys
SCAN 0                # Iterate all keys (slowly)
DEBUG OBJECT key      # See key size and encoding

Find large keys:
redis-cli --bigkeys   # Find keys using memory
```

### Eviction Policies

```
When memory limit reached, Redis evicts keys:

LRU (Least Recently Used):
maxmemory-policy allkeys-lru
# Remove least recently used key

LFU (Least Frequently Used):
maxmemory-policy allkeys-lfu
# Remove least frequently used key

Random:
maxmemory-policy allkeys-random
# Remove random key

TTL-based:
maxmemory-policy volatile-ttl
# Remove key with shortest TTL

No eviction:
maxmemory-policy noeviction
# Reject writes when full (safest for critical data)

Configuration:
maxmemory 2gb                    # Set memory limit
maxmemory-policy allkeys-lru     # Set policy
```

---

## Part 10: Performance Tuning

### Optimization Tips

```
1. Use appropriate data types
   ✅ Sorted set for leaderboard
   ❌ String storing CSV (hard to query)

2. Avoid KEYS (slow O(N) scan)
   ✅ SCAN cursor (iterates safely)
   ✅ Use naming patterns (hash tags)
   ❌ KEYS pattern (locks Redis)

3. Batch operations
   ✅ PIPELINE multiple commands
   ✅ MGET/MSET for multiple keys
   ❌ GET key1, GET key2, ... (round trips)

4. Use expiration
   ✅ Set TTL on temporary data
   ❌ Let data accumulate forever

5. Choose right persistence
   ✅ RDB + AOF for important data
   ✅ AOF only for high-volume
   ❌ No persistence for cache-only

6. Monitor connections
   ✅ Connection pooling
   ❌ New connection per request

7. Use Lua scripts
   ✅ Complex logic atomically
   ❌ Multiple commands without script
```

### Benchmarking

```
Measure throughput:
redis-benchmark -h localhost -p 6379 -n 1000000 -c 50
# 1 million requests, 50 connections

Measure specific command:
redis-benchmark -h localhost -p 6379 -t set,get -n 1000000
# Test SET and GET

Measure latency:
redis-cli --latency -h localhost -p 6379
# Shows latency over time
```

---

## Part 11: Common Use Cases

### Use Case 1: Web Cache

```
Caching strategy:
- Cache expensive queries (1 hour TTL)
- Cache static HTML (24 hour TTL)
- Cache API responses (15 min TTL)

Implementation:
def get_user_posts(user_id):
  cache_key = f"user:{user_id}:posts"
  
  # Try cache
  posts = REDIS.GET(cache_key)
  if posts:
    return JSON.parse(posts)
  
  # Cache miss, query DB
  posts = DB.query("SELECT * FROM posts WHERE user_id = ?", user_id)
  
  # Store in cache
  REDIS.SETEX(cache_key, 3600, JSON.stringify(posts))
  return posts

Cache invalidation:
When user creates new post:
DELETE REDIS key "user:{user_id}:posts"
# Next request fetches fresh data
```

### Use Case 2: Real-time Notifications

```
Architecture:
Producer (new data) → Redis Pub/Sub → Consumer (clients)

Code:
# Client listens
SUBSCRIBE notifications:user:123

# Server publishes
PUBLISH notifications:user:123 {"type": "new_order", "order_id": 456}

# Client receives immediately
# (Requires WebSocket or long-polling)
```

### Use Case 3: Rate Limiting (API)

```
Limit: 100 requests per minute per user

Per request:
1. INCR api:rate:user:123:2024-01-15-14-30
2. If count > 100: reject with 429
3. EXPIRE key 60 seconds

Benefits:
- Sub-millisecond check
- Distributed across servers (shared Redis)
- Sliding window (reset every minute)
```

### Use Case 4: Task Queue

```
Job producer:
LPUSH "queue:send_email" {
  "to": "alice@example.com",
  "subject": "Hello",
  "body": "..."
}

Worker:
while True:
  job = BLPOP "queue:send_email" 5
  if job:
    try:
      send_email(job)
      LPUSH "queue:completed" job
    except:
      LPUSH "queue:failed" job

Multiple workers:
- All BLPOP same queue
- Redis distributes jobs
- Each job processed once
```

---

## Summary: Redis Strengths & Limitations

### Strengths ✅

1. **Speed**: Sub-millisecond latencies
2. **Data structures**: Rich types for different use cases
3. **Simplicity**: Easy to learn and use
4. **Flexibility**: Works as cache, database, queue, pub/sub
5. **Persistence**: Optional, configurable
6. **Replication**: High availability
7. **Lua scripting**: Complex operations

### Limitations ❌

1. **Memory-bound**: Data must fit in RAM
2. **Single-threaded**: One slow command blocks all
3. **Persistence overhead**: RDB/AOF adds latency
4. **No complex queries**: No SQL, no joins
5. **Limited transactions**: Not full ACID
6. **Fire-and-forget pub/sub**: No persistence, no offline subscribers
7. **Requires monitoring**: Memory leaks can be catastrophic

---

## Redis vs Other Tools

| Use Case | Redis | Alternative | Why |
|----------|-------|-------------|-----|
| **Caching** | ✅ | Memcached | Rich features, persistence |
| **Sessions** | ✅ | Database | Much faster |
| **Rate limiting** | ✅ | Database | Atomic increments |
| **Counters** | ✅ | Database | Real-time, accurate |
| **Leaderboards** | ✅ | Database | Sorted set built-in |
| **Job queue** | ✅ | RabbitMQ | Simpler, in-memory |
| **Pub/Sub** | ⚠️ | Kafka | Kafka persists, Redis doesn't |
| **Streams** | ✅ | Kafka | Lightweight, simpler |
| **Transactions** | ⚠️ | PostgreSQL | PostgreSQL has ACID |
| **Complex queries** | ❌ | PostgreSQL | SQL needed |

---

## Quick Cheat Sheet

```
# Connection
redis-cli              # CLI
redis-cli -h host -p port

# Keys
SET key value
GET key
DEL key
EXISTS key
EXPIRE key 3600
TTL key

# Strings
INCR counter
DECR counter
APPEND key " suffix"
STRLEN key

# Lists
LPUSH list value
RPUSH list value
LPOP list
RPOP list
LRANGE list 0 -1
BLPOP list timeout

# Sets
SADD set member
SREM set member
SMEMBERS set
SINTER set1 set2
SUNION set1 set2

# Sorted Sets
ZADD zset score member
ZRANGE zset 0 -1
ZREVRANGE zset 0 -1
ZRANK zset member
ZSCORE zset member

# Hashes
HSET hash field value
HGET hash field
HGETALL hash
HDEL hash field
HINCRBY hash field 1

# Transactions
MULTI
command1
command2
EXEC

# Pub/Sub
SUBSCRIBE channel
PUBLISH channel message

# Server
PING
INFO
DBSIZE
FLUSHDB
```

This covers Redis fundamentally. You now understand:
- Architecture and philosophy
- All major data types
- Common patterns
- Performance considerations
- When to use Redis
- Real-world examples

Let's move to practical examples in the next document!
