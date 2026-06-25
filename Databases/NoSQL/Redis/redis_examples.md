# Redis Practical Examples: Ready-to-Run Commands

This document provides 200+ copy-paste ready Redis commands organized by data type and use case.

---

## SETUP & CONNECTION

```bash
# Start Redis server
redis-server

# Or with configuration
redis-server --port 6379 --bind 127.0.0.1

# Connect with CLI
redis-cli

# Connect to remote server
redis-cli -h redis.example.com -p 6379 -a password

# Test connection
PING
# Returns: PONG

# Check Redis info
INFO
INFO memory
INFO stats
INFO keyspace
```

---

## STRING OPERATIONS (Key-Value)

### Basic String Commands

```redis
# Set and get
SET mykey "Hello"              # Set value
GET mykey                      # Get: "Hello"
SET mykey "World"              # Overwrite: "World"
GET mykey                      # Get: "World"

# Set only if not exists
SETNX newkey "Value"           # Set if not exists
SETNX newkey "NewValue"        # Returns 0 (already exists)

# Set with expiration
SETEX tempkey 3600 "expires in 1 hour"
PSETEX tempkey 1000 "expires in 1 second"

# Get and set atomically
GETSET mykey "NewValue"        # Returns: "World", sets to "NewValue"

# Multiple operations
MSET k1 "v1" k2 "v2" k3 "v3"   # Set multiple keys
MGET k1 k2 k3                  # Get multiple: ["v1", "v2", "v3"]
MSETNX k4 "v4" k5 "v5"         # Set multiple if all don't exist

# Key properties
STRLEN mykey                   # Length of string
APPEND mykey " World"          # Append: "NewValue World"
GETRANGE mykey 0 7             # Substring: "NewValu"
SETRANGE mykey 0 "Updated"     # Replace from index 0
```

### Numeric Operations

```redis
# Counters
SET counter 0
INCR counter                   # 1
INCR counter                   # 2
INCRBY counter 5               # 7
DECR counter                   # 6
DECRBY counter 2               # 4
INCRBYFLOAT counter 1.5        # 5.5

# Real-world: Page views
INCR page:views                # 1
INCR page:views                # 2
INCR page:views:today          # 1
INCRBY page:views:today 1      # 2

# Real-world: API rate limiting
INCR api:calls:user:123        # 1st call
INCR api:calls:user:123        # 2nd call
GET api:calls:user:123         # Check: "2"
EXPIRE api:calls:user:123 60   # Reset every 60 seconds
```

### Bit Operations

```redis
# Set bits
SETBIT active_users 0 1        # User 0 active
SETBIT active_users 1 1        # User 1 active
SETBIT active_users 5 1        # User 5 active

# Get bits
GETBIT active_users 0          # 1 (active)
GETBIT active_users 2          # 0 (inactive)
GETBIT active_users 5          # 1 (active)

# Count set bits
BITCOUNT active_users          # 3 (three users active)

# Find first set bit
BITPOS active_users 1          # 0 (first active user)

# Bit operations between keys
SETBIT mask:a 0 1
SETBIT mask:a 1 0
SETBIT mask:a 2 1
SETBIT mask:b 0 0
SETBIT mask:b 1 1
SETBIT mask:b 2 1

BITOP AND result mask:a mask:b # AND operation
BITCOUNT result                # Count set bits: 1

# Real-world: Daily active users (125 KB for 1M users!)
SETBIT dau:2024-01-15 12345 1  # Mark user 12345 active today
BITCOUNT dau:2024-01-15        # Count daily active: 12345+
```

---

## EXPIRATION & KEY MANAGEMENT

```redis
# Set expiration
SET mykey "value"
EXPIRE mykey 3600              # Expire in 1 hour
PEXPIRE mykey 1000             # Expire in 1000 milliseconds
EXPIREAT mykey 1704067200      # Expire at Unix timestamp
PEXPIREAT mykey 1704067200000  # Expire at Unix timestamp (ms)

# Check expiration
TTL mykey                       # Seconds to live: 3599
PTTL mykey                      # Milliseconds to live: 3599000
TTL nonexistent                 # -2 (doesn't exist)
TTL persistent                  # -1 (no expiration)

# Remove expiration
PERSIST mykey                   # Remove TTL, live forever

# Real-world: Session expiration
SETEX "session:user:abc123" 86400 '{"user_id": 123, "ip": "1.2.3.4"}'
# Session expires in 1 day

# Real-world: Temporary files
SETEX "upload:temp:file123" 1800 "file_content"
# Delete temp file after 30 min
```

### Key Operations

```redis
# Check existence
EXISTS mykey                   # 1 (exists)
EXISTS nonexistent             # 0 (doesn't exist)
EXISTS key1 key2 key3          # 2 (two exist)

# Get key type
TYPE mykey                     # "string"
TYPE mylist                    # "list"
TYPE myset                     # "set"
TYPE myzset                    # "zset"
TYPE myhash                    # "hash"

# Delete keys
DEL mykey                      # Delete one
DEL key1 key2 key3             # Delete multiple: 3
UNLINK mykey                   # Async delete (returns immediately)

# Rename keys
RENAME oldkey newkey           # Rename
RENAMENX oldkey newkey         # Rename only if newkey doesn't exist

# Find keys (SLOW - avoid in production!)
KEYS *                         # All keys
KEYS user:*                    # Keys starting with "user:"
KEYS *:name                    # Keys ending with ":name"

# Iterate keys (safe, for large keyspaces)
SCAN 0                         # Cursor 0
SCAN 0 MATCH "user:*"          # Pattern match
SCAN 0 COUNT 100               # Hint: 100 keys per iteration
```

---

## LIST OPERATIONS (Ordered Collections)

### Basic List Operations

```redis
# Create list
LPUSH tasks "task1"            # [task1]
LPUSH tasks "task2"            # [task2, task1]
LPUSH tasks "task3"            # [task3, task2, task1]

# Or from right
RPUSH tasks "task4"            # [task3, task2, task1, task4]

# Get length
LLEN tasks                     # 4

# Read list
LRANGE tasks 0 -1              # All: [task3, task2, task1, task4]
LRANGE tasks 0 1               # First 2: [task3, task2]
LRANGE tasks -2 -1             # Last 2: [task1, task4]
LINDEX tasks 0                 # First: "task3"
LINDEX tasks -1                # Last: "task4"

# Remove from left
LPOP tasks                     # Remove and return: "task3"
# Now: [task2, task1, task4]

# Remove from right
RPOP tasks                     # Remove and return: "task4"
# Now: [task2, task1]

# Trim (keep only range)
LTRIM tasks 0 0                # Keep only first: [task2]
```

### List Manipulation

```redis
# Insert before/after element
RPUSH mylist "a" "b" "d"       # [a, b, d]
LINSERT mylist BEFORE "d" "c"  # [a, b, c, d]
LINSERT mylist AFTER "b" "x"   # [a, b, x, c, d]

# Set element at index
LSET mylist 0 "A"              # [A, b, x, c, d]
LSET mylist -1 "D"             # [A, b, x, c, D]

# Remove element by value
LREM mylist 1 "x"              # Remove 1 occurrence of "x"
LREM mylist -1 "b"             # Remove 1 occurrence from right
LREM mylist 0 "x"              # Remove all occurrences

# Pop with blocking
BLPOP mylist 5                 # Wait up to 5 sec for item
BRPOP mylist 5                 # Wait up to 5 sec from right
BRPOPLPUSH source dest 5       # Pop right from source, push left to dest
```

### Real-world: Job Queue

```redis
# Producer: Add job to queue
LPUSH "queue:send_email" '{"to":"alice@example.com","subject":"Hello"}'
LPUSH "queue:send_email" '{"to":"bob@example.com","subject":"Hi"}'

# Consumer: Process jobs (blocking)
BRPOP "queue:send_email" 5     # Wait 5 sec for job
# Process job...
# If success:
LPUSH "queue:completed" (job)
# If failure:
LPUSH "queue:failed" (job)

# Monitor queue length
LLEN "queue:send_email"        # How many jobs waiting?

# Check completed jobs
LRANGE "queue:completed" 0 -1  # All completed
LRANGE "queue:completed" 0 9   # Last 10 completed

# Check failed jobs
LRANGE "queue:failed" 0 -1     # All failed
```

### Real-world: Recent Activity Feed

```redis
# User posts activity
LPUSH "feed:user:123" '{"id":1,"type":"post","content":"Hello"}'
LPUSH "feed:user:123" '{"id":2,"type":"like","post_id":5}'
LPUSH "feed:user:123" '{"id":3,"type":"comment","post_id":7}'

# Get recent 10 activities
LRANGE "feed:user:123" 0 9     # Newest first

# Trim to keep only last 100
LTRIM "feed:user:123" 0 99
```

---

## SET OPERATIONS (Unique Collections)

### Basic Set Operations

```redis
# Add to set
SADD tags "python"             # {python}
SADD tags "redis"              # {python, redis}
SADD tags "database"           # {python, redis, database}

# Try to add duplicate
SADD tags "python"             # Returns 0 (already exists)

# Get set size
SCARD tags                     # 3

# Get all members
SMEMBERS tags                  # [python, redis, database]

# Check membership
SISMEMBER tags "python"        # 1 (true)
SISMEMBER tags "javascript"    # 0 (false)

# Remove members
SREM tags "python"             # Remove: {redis, database}
SREM tags "redis" "database"   # Remove multiple: {}

# Random members
SRANDMEMBER tags 2             # 2 random members (may repeat)
SPOP tags                      # Remove and return random
```

### Set Operations (Union, Intersection, Difference)

```redis
# Setup
SADD users:online "alice"
SADD users:online "bob"
SADD users:online "carol"

SADD users:active "bob"
SADD users:active "carol"
SADD users:active "david"

# Intersection (who is online AND active?)
SINTER users:online users:active       # {bob, carol}

# Union (who is online OR active?)
SUNION users:online users:active       # {alice, bob, carol, david}

# Difference (who is online BUT NOT active?)
SDIFF users:online users:active        # {alice}

# Store results
SINTERSTORE result users:online users:active
# Store intersection in 'result'

SUNIONSTORE result users:online users:active
# Store union in 'result'

SDIFFSTORE result users:online users:active
# Store difference in 'result'
```

### Real-world: Unique Visitors

```redis
# Track unique visitors per day
SADD "visitors:2024-01-15" "user:123"
SADD "visitors:2024-01-15" "user:456"
SADD "visitors:2024-01-15" "user:123"  # Returns 0 (duplicate)

# Count unique visitors
SCARD "visitors:2024-01-15"             # 2

# Find common visitors (both days)
SADD "visitors:2024-01-16" "user:456"
SADD "visitors:2024-01-16" "user:789"

SINTER "visitors:2024-01-15" "visitors:2024-01-16"
# {user:456} (only user:456 visited both days)

# Find all visitors (any day)
SUNION "visitors:2024-01-15" "visitors:2024-01-16"
# {user:123, user:456, user:789}
```

### Real-world: Friend Lists

```redis
# Add friends
SADD "friends:alice" "bob" "carol" "david"
SADD "friends:bob" "alice" "carol" "eve"

# Get friend count
SCARD "friends:alice"                  # 3

# Get friends
SMEMBERS "friends:alice"               # [bob, carol, david]

# Check if friend
SISMEMBER "friends:alice" "bob"        # 1 (yes)
SISMEMBER "friends:alice" "eve"        # 0 (no)

# Find common friends
SINTER "friends:alice" "friends:bob"   # [bob, carol]

# Friend suggestions (friends of friends who aren't friends)
# Complex: Need Lua script
```

---

## SORTED SET OPERATIONS (Ranked Collections)

### Basic Sorted Set Operations

```redis
# Add members with scores
ZADD leaderboard 100 "alice"
ZADD leaderboard 95 "bob"
ZADD leaderboard 105 "carol"
ZADD leaderboard 88 "david"

# Get count
ZCARD leaderboard               # 4

# Get score
ZSCORE leaderboard "alice"      # 100
ZSCORE leaderboard "bob"        # 95

# Get rank (low to high)
ZRANK leaderboard "bob"         # 0 (lowest score)
ZRANK leaderboard "alice"       # 1
ZRANK leaderboard "carol"       # 3 (highest score)

# Get rank reverse (high to low)
ZREVRANK leaderboard "carol"    # 0 (highest score)
ZREVRANK leaderboard "bob"      # 3 (lowest score)

# Get range by rank (low to high)
ZRANGE leaderboard 0 -1         # [bob, alice, david, carol]
ZRANGE leaderboard 0 1          # [bob, alice]

# Get range by rank (high to low)
ZREVRANGE leaderboard 0 -1      # [carol, david, alice, bob]
ZREVRANGE leaderboard 0 2       # Top 3: [carol, david, alice]

# Get with scores
ZRANGE leaderboard 0 -1 WITHSCORES
# [bob, 95, alice, 100, david, 88, carol, 105]
```

### Range by Score

```redis
# Get members in score range
ZRANGEBYSCORE leaderboard 90 105       # [bob, alice, carol]
ZRANGEBYSCORE leaderboard 90 100       # [bob, alice]
ZRANGEBYSCORE leaderboard -inf 100    # Everything up to 100

# With scores
ZRANGEBYSCORE leaderboard 90 105 WITHSCORES

# Count in range
ZCOUNT leaderboard 90 105              # 3
ZCOUNT leaderboard 95 95               # 1

# Remove by range
ZREMRANGEBYSCORE leaderboard 90 100    # Remove in range
ZREMRANGEBYRANK leaderboard 0 1        # Remove by rank (first 2)
```

### Increment Scores

```redis
# Increment score
ZINCRBY leaderboard 5 "bob"            # bob's score: 100
ZINCRBY leaderboard -10 "alice"        # alice's score: 90

# After increments, get leaderboard
ZREVRANGE leaderboard 0 -1 WITHSCORES
# [carol, 105, bob, 100, alice, 90, david, 88]
```

### Real-world: Leaderboard

```redis
# Player makes high score
ZADD "game:123:leaderboard" 9500 "alice"
ZADD "game:123:leaderboard" 8700 "bob"
ZADD "game:123:leaderboard" 9200 "carol"
ZADD "game:123:leaderboard" 7600 "david"

# Get top 10
ZREVRANGE "game:123:leaderboard" 0 9 WITHSCORES
# [alice, 9500, carol, 9200, bob, 8700, david, 7600]

# Get player rank
ZREVRANK "game:123:leaderboard" "alice"  # 0 (first place)
ZREVRANK "game:123:leaderboard" "david"  # 3 (fourth place)

# Player scores
ZSCORE "game:123:leaderboard" "alice"    # 9500

# Update score (new game)
ZINCRBY "game:123:leaderboard" 500 "bob"
# bob's score now: 9200

# Players in score range
ZRANGEBYSCORE "game:123:leaderboard" 9000 9500 WITHSCORES
# [alice, 9500, carol, 9200, bob, 9200]
```

### Real-world: Top Products

```redis
# Add products with rating
ZADD "products:rating" 4.5 "product:1"
ZADD "products:rating" 4.2 "product:2"
ZADD "products:rating" 4.8 "product:3"
ZADD "products:rating" 3.9 "product:4"

# Get top rated
ZREVRANGE "products:rating" 0 4 WITHSCORES
# Top 5 products

# Count highly rated (4+ stars)
ZCOUNT "products:rating" 4.0 5.0
```

### Real-world: Time-based Ranking

```redis
# Activity timestamps (milliseconds)
ZADD "trending:posts" 1704067200000 "post:1"
ZADD "trending:posts" 1704067300000 "post:2"
ZADD "trending:posts" 1704067400000 "post:3"

# Get posts from last hour
ZREVRANGEBYSCORE "trending:posts" $(date +%s)000 $(date -d '1 hour ago' +%s)000
```

---

## HASH OPERATIONS (Nested Objects)

### Basic Hash Operations

```redis
# Set single field
HSET user:1 name "Alice"
HSET user:1 email "alice@example.com"
HSET user:1 age 30

# Set multiple fields
HMSET user:1 name Alice email alice@example.com age 30

# Or in one command (Redis 4.0+)
HSET user:1 name Alice email alice@example.com age 30 city NYC

# Get single field
HGET user:1 name                # "Alice"
HGET user:1 email               # "alice@example.com"

# Get multiple fields
HMGET user:1 name email age     # [Alice, alice@example.com, 30]

# Get all
HGETALL user:1
# [name, Alice, email, alice@example.com, age, 30, city, NYC]

# Get field count
HLEN user:1                     # 4

# Get all field names
HKEYS user:1                    # [name, email, age, city]

# Get all values
HVALS user:1                    # [Alice, alice@example.com, 30, NYC]

# Check field exists
HEXISTS user:1 name             # 1 (yes)
HEXISTS user:1 phone            # 0 (no)

# Get string length of field value
HSTRLEN user:1 name             # 5 (length of "Alice")
```

### Increment Hash Fields

```redis
# Integer increment
HINCRBY user:1 age 1            # age: 31
HINCRBY user:1 age -2           # age: 29

# Float increment
HINCRBYFLOAT user:1 salary 1.5  # salary: 50000.5
```

### Delete Hash Fields

```redis
# Delete single field
HDEL user:1 city                # Remove 'city' field

# Delete multiple fields
HDEL user:1 age city            # Remove 'age' and 'city'
```

### Real-world: User Profile

```redis
# Store user profile
HMSET "user:123" \
  id 123 \
  name "Alice Johnson" \
  email "alice@example.com" \
  phone "+1-555-1234" \
  created_at "2024-01-15" \
  premium true \
  views 1250

# Get profile
HGETALL "user:123"

# Get specific fields
HMGET "user:123" name email phone

# Update field
HSET "user:123" views 1251

# Increment views
HINCRBY "user:123" views 1      # Views: 1252

# Check if premium
HGET "user:123" premium         # "true"
```

### Real-world: Product Details

```redis
# Store product
HMSET "product:laptop-001" \
  id "laptop-001" \
  name "MacBook Pro 16\"" \
  price 2499.99 \
  stock 50 \
  rating 4.8 \
  reviews 250 \
  color "Space Gray"

# Get product details
HGETALL "product:laptop-001"

# Check stock
HGET "product:laptop-001" stock     # "50"

# Decrease stock
HINCRBY "product:laptop-001" stock -1  # Stock: 49

# Get price
HGET "product:laptop-001" price     # "2499.99"
```

---

## HyperLogLog OPERATIONS (Cardinality)

```redis
# Add elements
PFADD "hll:visitors:2024-01-15" "user:123"
PFADD "hll:visitors:2024-01-15" "user:456"
PFADD "hll:visitors:2024-01-15" "user:789"
PFADD "hll:visitors:2024-01-15" "user:123"  # Duplicate

# Count unique (approximate)
PFCOUNT "hll:visitors:2024-01-15"           # ~3 (exact in this case)

# Add many at once
PFADD "hll:visitors" user1 user2 user3 user4 user5 user6

# Count
PFCOUNT "hll:visitors"                      # ~6

# Merge multiple HyperLogLogs
PFADD "hll:visitors:2024-01-15" u1 u2 u3
PFADD "hll:visitors:2024-01-16" u3 u4 u5
PFMERGE "hll:visitors:week" "hll:visitors:2024-01-15" "hll:visitors:2024-01-16"
PFCOUNT "hll:visitors:week"                 # ~5

# Real-world: Millions of unique visitors in 12 KB!
PFADD "hll:visitors:daily" (1000000 unique IDs)
PFCOUNT "hll:visitors:daily"                # ~1,000,000 (± 10,000)
```

---

## TRANSACTIONS & PIPELINING

### Transactions (MULTI/EXEC)

```redis
# Simple transaction
MULTI
SET key1 value1
SET key2 value2
GET key1
EXEC
# Returns: [OK, OK, value1]

# Transaction with error checking
MULTI
INCR counter                   # Queued
SET tempkey "value"            # Queued
EXEC                           # Both execute atomically

# Discard transaction
MULTI
SET key1 value1
DISCARD                        # Cancel transaction
GET key1                       # Still returns old value

# Watch (optimistic locking)
WATCH mykey                    # Watch for changes
# ... do other operations ...
MULTI
SET mykey newvalue
EXEC
# If mykey changed between WATCH and EXEC, transaction aborts

# Real-world: Atomic transfer
MULTI
INCR balance:alice:-100        # Decrease Alice
INCR balance:bob:+100          # Increase Bob
EXEC                           # Both succeed or both fail
```

### Pipelining

```redis
# Without pipelining (3 network round trips)
SET key1 val1
SET key2 val2
SET key3 val3

# With pipelining (1 network round trip)
# Client sends all 3 commands at once, server processes, returns all 3 results

# Python example:
pipe = redis.pipeline()
pipe.set('key1', 'val1')
pipe.set('key2', 'val2')
pipe.get('key1')
results = pipe.execute()
# results = [True, True, 'val1']

# Bash with redis-cli
redis-cli --pipe < commands.txt

# Manual with netcat:
(echo -e "SET key1 val1\r\nSET key2 val2\r\n") | nc localhost 6379
```

---

## PUB/SUB MESSAGING

```redis
# Subscriber (client 1)
SUBSCRIBE notifications           # Listen on channel
# Waits... receives messages

# Subscriber (client 2)
SUBSCRIBE notifications           # Also listening
SUBSCRIBE alerts                  # Multiple channels

# Publisher (client 3)
PUBLISH notifications "Hello World"
# Returns: 2 (two subscribers received)

PUBLISH alerts "Critical error!"
# Returns: 1 (one subscriber on alerts)

# Pattern subscription (client 1)
PSUBSCRIBE notification:*         # Listen to pattern
PSUBSCRIBE alert:*
PUNSUBSCRIBE notification:*       # Unsubscribe pattern

# Publish to pattern
PUBLISH notification:user:123 "User 123 alert"
# Clients matching pattern receive

# Real-world: Real-time notifications
# Subscriber
SUBSCRIBE "notifications:user:123"
# Gets: {type: subscribe, channel: notifications:user:123}

# Publisher
PUBLISH "notifications:user:123" '{"type": "new_order", "order_id": 456}'

# WARNING: Pub/Sub is fire-and-forget
# - No message persistence
# - Offline subscribers miss messages
# Solution: Use Redis Streams for persistence
```

---

## STREAMS (Append-Only Logs)

```redis
# Add entry to stream
XADD "events" "*" "user" "alice" "action" "login"
# Returns: "1704067200000-0" (timestamp-sequence)

# Add multiple entries
XADD "events" "*" "user" "bob" "action" "purchase"
XADD "events" "*" "user" "carol" "action" "logout"

# Get stream length
XLEN "events"                                      # 3

# Get all entries
XRANGE "events" - +                              # All from start to end
XRANGE "events" 1704067200000-0 +                # From timestamp onwards

# Get latest entries (reverse)
XREVRANGE "events" + -                           # Latest first
XREVRANGE "events" + - COUNT 10                  # Latest 10

# Read with blocking
XREAD COUNT 10 STREAMS "events" 0
# Read 10 from start

XREAD BLOCK 1000 COUNT 10 STREAMS "events" $
# Block 1 second waiting for new entries from current position

# Consumer group (for scaling)
XGROUP CREATE "events" "group1" $
# Create consumer group

XREADGROUP GROUP "group1" "consumer1" STREAMS "events" >
# Consumer reads from group (load balanced)

# Real-world: Event log
XADD "app:logs" "*" "level" "error" "message" "Database connection failed"
XADD "app:logs" "*" "level" "info" "message" "Server started"

# Get recent errors
XRANGE "app:logs" - + MATCH "*error*"
```

---

## LUA SCRIPTING

```redis
# Simple script
EVAL "return redis.call('set', KEYS[1], ARGV[1])" 1 mykey myvalue
# Set mykey to myvalue using Lua

# Script with conditional logic
EVAL "
if redis.call('exists', KEYS[1]) == 1 then
  return redis.call('get', KEYS[1])
else
  return nil
end
" 1 mykey

# Rate limiting script
local count = redis.call('incr', KEYS[1])
if count == 1 then
  redis.call('expire', KEYS[1], ARGV[1])
end
if count <= tonumber(ARGV[2]) then
  return 1
else
  return 0
end

# Execute:
EVAL "(script)" 1 "rate:user:123" 60 100
# 1 = allow, 0 = deny

# Script with loops
EVAL "
local result = {}
for i=1,3 do
  table.insert(result, redis.call('get', KEYS[i]))
end
return result
" 3 key1 key2 key3

# Register script (for reuse)
SCRIPT LOAD "return redis.call('get', KEYS[1])"
# Returns: "abc123def..." (SHA)

EVALSHA "abc123def..." 1 mykey
# Execute by SHA instead of reloading script
```

---

## PRACTICAL EXAMPLES

### Rate Limiting (Token Bucket)

```redis
# Configuration
RATE_LIMIT = 100 requests/minute

# Middleware
function check_rate_limit(user_id):
  key = "rate:" + user_id + ":" + current_minute()
  count = REDIS.INCR(key)
  if count == 1:
    REDIS.EXPIRE(key, 60)
  return count <= 100

# Usage
if check_rate_limit(user_id):
  process_request()
else:
  return 429  # Too Many Requests
```

### Distributed Locking

```redis
# Acquire lock
SET "lock:resource" "client_id_123" NX EX 30
# NX = only set if not exists
# EX = expire in 30 seconds

# If returns OK: you have the lock!
# Do critical work...

# Release lock
# IMPORTANT: Verify it's still your lock
if REDIS.GET("lock:resource") == "client_id_123":
  REDIS.DEL("lock:resource")
```

### Session Management

```redis
# Login
token = generate_token()
HSET "session:" + token "user_id" 123 "ip" "1.2.3.4" "created_at" now()
EXPIRE "session:" + token 86400  # 1 day

# Request with token
user_data = HGETALL "session:" + token
if user_data:
  EXPIRE "session:" + token 86400  # Refresh TTL
  proceed_with_request()
else:
  redirect_to_login()

# Logout
DEL "session:" + token
```

### Caching (Cache-Aside)

```redis
# Get with cache
function get_user(user_id):
  cached = GET "cache:user:" + user_id
  if cached:
    return JSON.parse(cached)
  
  user = database.query("SELECT * FROM users WHERE id = ?", user_id)
  SETEX "cache:user:" + user_id 3600 JSON.stringify(user)
  return user

# Update
function update_user(user_id, data):
  database.update(user_id, data)
  DEL "cache:user:" + user_id  # Invalidate cache
```

### Leaderboard

```redis
# Record score
ZADD "leaderboard:game:123" 9500 "alice"
ZADD "leaderboard:game:123" 8700 "bob"

# Get top 10
ZREVRANGE "leaderboard:game:123" 0 9 WITHSCORES

# Get player rank
rank = ZREVRANK "leaderboard:game:123" "alice"
# rank + 1 = position (0-indexed)
```

### Activity Feed

```redis
# Post activity
LPUSH "feed:user:123" '{"id":123,"type":"post",...}'

# Get recent 20
LRANGE "feed:user:123" 0 19

# Trim old items (keep last 100)
LTRIM "feed:user:123" 0 99
```

### Real-time Counter

```redis
# Page views
INCR "page:123:views"           # Atomic increment

# Get views
GET "page:123:views"

# Multiple counters
MGET "page:1:views" "page:2:views" "page:3:views"
```

---

## USEFUL UTILITY COMMANDS

```redis
# Server info
PING                           # Test connection
INFO                           # Full server info
INFO memory                    # Memory stats
INFO stats                     # Operation stats
INFO keyspace                  # Database summary

# Monitor commands (debugging)
MONITOR                        # Show all commands (SLOW!)
SLOWLOG GET 10                 # Show 10 slowest commands
SLOWLOG LEN                    # Slowest log size

# Key expiration analysis
RANDOMKEY                      # Get random key
DUMP key                       # Serialize key
RESTORE key 0 (serialized)     # Deserialize key

# Memory analysis
MEMORY USAGE key               # Key memory usage
MEMORY STATS                   # Memory breakdown

# Database operations
SELECT 0                       # Select database 0
SELECT 1                       # Select database 1
DBSIZE                         # Key count
FLUSHDB                        # Delete all keys in DB
FLUSHALL                       # Delete all keys in all DBs
RANDOMKEY                      # Random key
SAVE                           # Blocking save (RDB)
BGSAVE                         # Background save
LASTSAVE                       # Last save timestamp

# Client management
CLIENT LIST                    # Connected clients
CLIENT GETNAME                 # Client name
CLIENT SETNAME myclient        # Set client name
CLIENT KILL 127.0.0.1:6379    # Disconnect client

# Configuration
CONFIG GET maxmemory           # Get config
CONFIG SET maxmemory 2gb       # Set config
CONFIG REWRITE                 # Save to file

# Cleanup
KEYS *                         # All keys (SLOW!)
SCAN 0                         # Safe iteration
```

---

## PERFORMANCE TIPS

```redis
# 1. Use PIPELINE for multiple commands
# 3 commands with pipeline = 1 round trip (not 3)

# 2. Avoid KEYS in production
KEYS *                         # SLOW - scans all keys
SCAN 0                         # FAST - iterates safely

# 3. Use MGET/MSET for multiple keys
MGET key1 key2 key3            # 1 round trip
GET key1; GET key2; GET key3   # 3 round trips

# 4. Use appropriate data types
ZADD for leaderboards (not SET)
LPUSH for queues (not SET)
HSET for objects (not multiple STRINGs)

# 5. Set expiration on temporary data
SETEX "temp:123" 3600 value    # Auto-delete after 1 hour

# 6. Use UNLINK instead of DEL for large keys
DEL bigkey                     # Blocks
UNLINK bigkey                  # Async delete

# 7. Avoid large values
# Use compression, pagination
# Not: SET key (1 MB JSON)
# But: Split into smaller chunks

# 8. Use connection pooling
# Not: New connection per request
# But: Pool of persistent connections
```

---

## QUICK REFERENCE

```
STRING      SET, GET, INCR, APPEND, SETEX
LIST        LPUSH, RPUSH, LPOP, RPOP, LRANGE
SET         SADD, SREM, SMEMBERS, SINTER, SUNION
ZSET        ZADD, ZREM, ZRANGE, ZRANK, ZSCORE
HASH        HSET, HGET, HMGET, HGETALL
HYPERLOGLOG PFADD, PFCOUNT, PFMERGE
STREAM      XADD, XRANGE, XREAD
BIT         SETBIT, GETBIT, BITCOUNT

KEY OPS     EXISTS, DEL, EXPIRE, TTL, SCAN
TRANS       MULTI, EXEC, WATCH
SCRIPT      EVAL, EVALSHA, SCRIPT
PUBSUB      SUBSCRIBE, PUBLISH, PSUBSCRIBE
```

This covers all major Redis commands and practical patterns!
