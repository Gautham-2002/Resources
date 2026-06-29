# Part 7.2: Sharding, Replication & Connection Pooling

## What You'll Learn
- How read replicas work, what replication lag means, and when NOT to read from a replica
- Synchronous vs asynchronous replication and their durability/latency trade-offs
- Database sharding: why you need it, how to choose a shard key, and the resharding problem
- Range-based, hash-based, and directory-based sharding — trade-offs and failure modes
- Consistent hashing and how it minimizes data movement during resharding
- PostgreSQL table partitioning vs application-level sharding
- PgBouncer connection pooling modes and how to size your pool
- Application-level read/write splitting

---

## Table of Contents
1. [Read Replicas](#1-read-replicas)
   - Why Replicas Exist
   - Replication Lag
   - Sync vs Async Replication
   - Application-Level Read/Write Splitting
   - When NOT to Read from a Replica
2. [Database Sharding](#2-database-sharding)
   - What Sharding Is and Why You Do It
   - Horizontal vs Vertical Partitioning
   - Shard Key Selection
   - Range-Based Sharding
   - Hash-Based Sharding
   - Directory-Based Sharding
   - The Resharding Problem
   - Consistent Hashing
   - Cross-Shard Queries
   - Application-Level vs Middleware Sharding
   - Multi-Tenancy as Sharding
3. [PostgreSQL Table Partitioning](#3-postgresql-table-partitioning)
4. [Advanced Connection Pooling with PgBouncer](#4-advanced-connection-pooling-with-pgbouncer)
5. [Implementation Examples](#5-implementation-examples)
   - Go + Chi
   - Node.js + Express
   - Python + FastAPI
6. [Common Patterns & Best Practices](#6-common-patterns--best-practices)
7. [Common Pitfalls](#7-common-pitfalls)
8. [Interview Questions & Model Answers](#8-interview-questions--model-answers)
9. [Resources](#9-resources)

---

## 1. Read Replicas

### Why Replicas Exist

A **read replica** (also called a standby or secondary) is a copy of the primary database that continuously receives and applies changes from the primary. Read replicas exist for three primary reasons:

**1. Read scaling:**
Your primary database handles writes and reads. As your read load grows (reporting queries, user-facing reads, analytics), the primary gets saturated. Read replicas allow you to distribute read queries across multiple servers. With 3 replicas, your read capacity is roughly 4× the primary (the primary still handles writes plus some reads).

**2. Geographic distribution:**
Users in Sydney querying a database hosted in US-East have 200ms+ of latency just in network round-trips. A read replica in the AP-Southeast region brings latency down to ~5ms for reads. Writes still go to the primary.

**3. Operational safety:**
Replicas serve as live backups. If the primary fails, a replica can be promoted to primary (with some manual/automated failover logic). Replicas also isolate heavy analytical queries — a slow reporting query on a replica can't impact production on the primary.

### PostgreSQL Streaming Replication

PostgreSQL uses **streaming replication** as its primary HA/replica mechanism:

1. **WAL (Write-Ahead Log):** Every change to a PostgreSQL database is first written as a WAL record. The WAL is a sequential, append-only log on disk.
2. **WAL Sender (primary):** A background process on the primary streams WAL segments to connected standbys over TCP.
3. **WAL Receiver (standby):** Receives WAL, writes it to disk, and signals the standby's recovery process to apply it.
4. **Recovery process:** Applies WAL records to the standby's data files, keeping the replica consistent with the primary.

The replica is in continuous recovery mode. All queries to the replica see a consistent state up to the last applied WAL record.

```
Primary DB                Standby DB
-----------               -----------
WAL file ──WAL Sender──►  WAL Receiver → WAL file
                                          ↓
                                       Recovery (apply)
                                          ↓
                                       Data files
```

### Replication Lag

**Replication lag** is the delay between a write being committed on the primary and that write becoming visible on the replica.

**Sources of lag:**
1. **Network latency:** WAL records must travel over the network. This is typically 1-5ms for same-datacenter replicas but can be 100-200ms for cross-region.
2. **Apply latency:** The standby must write WAL to disk, then apply it. On busy replicas, this can queue up.
3. **Long-running queries:** PostgreSQL must not garbage-collect WAL records that an in-progress replica query might need. A long read on the replica can cause `replication_slot` lag.
4. **Hot standby conflict:** A query on the replica might conflict with WAL being applied (e.g., the primary VACUUMs a row the replica query is reading). PostgreSQL cancels the replica query or pauses WAL apply.

**Measuring lag:**
```sql
-- On the primary: see lag for all connected replicas
SELECT
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    write_lag,      -- time to write WAL to standby disk
    flush_lag,      -- time to fsync WAL on standby
    replay_lag,     -- time to apply WAL on standby
    sync_state      -- async, sync, quorum
FROM pg_stat_replication;

-- On the replica: see how far behind it is
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;

-- Also useful: LSN-based lag
SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), pg_last_wal_replay_lsn()) AS lag_bytes;
```

**Consequences of lag:**
- A user writes a record (primary), immediately reads it back (replica) — doesn't see it yet. Classic "read-your-writes" violation.
- Reporting dashboard reads data 30 seconds old — usually acceptable.
- Fraud detection reads stale account balance — dangerous.

Typical same-datacenter async lag: 10-200ms under normal load. Under heavy write pressure, it can reach seconds or minutes.

### Sync vs Async Replication

**Asynchronous Replication (default):**
- The primary commits the transaction **immediately** after writing to its own WAL. It does NOT wait for the replica to confirm receipt.
- The WAL is sent to replicas in the background.
- **Latency:** Write latency is unaffected — single disk write + client ACK.
- **Durability risk:** If the primary crashes immediately after commit but before the WAL is sent to any replica, you lose that transaction. This is the "async replication durability gap."
- **Use case:** Acceptable for most OLTP workloads where losing 1-2 seconds of writes is tolerable.

**Synchronous Replication:**
```sql
-- postgresql.conf
synchronous_standby_names = 'FIRST 1 (standby1, standby2)'
-- or for quorum commit:
synchronous_standby_names = 'ANY 2 (standby1, standby2, standby3)'
```
- The primary waits for at least one synchronous standby to acknowledge that WAL has been written to disk before committing to the client.
- **Latency:** Write latency increases by at least one network round-trip to the standby (~1-5ms same DC, ~50-200ms cross-region). This is significant at high write volumes.
- **Durability:** No committed transaction can be lost even if the primary fails immediately after — the standby has the WAL.
- **Availability risk:** If the synchronous standby goes down, the primary blocks waiting for it (unless `synchronous_commit = remote_write` or timeout is configured).

**Semi-Synchronous (practical middle ground):**
```sql
-- In practice, most teams use:
synchronous_commit = remote_write  -- primary waits for WAL to reach standby's OS buffers, not fsync
-- This provides protection against most crash scenarios with lower latency than full sync
```

**Decision matrix:**

| Requirement | Use |
|---|---|
| Financial transactions, zero data loss | Synchronous replication |
| High write throughput, tolerate ~1s data loss | Async replication |
| Read scaling only | Async replica(s) |
| Geographic distribution | Async cross-region + sync within DC |

### Application-Level Read/Write Splitting

To use replicas, your application must route reads to replicas and writes to the primary. This is called **read/write splitting**.

**Strategies:**
1. **Application-level routing:** Your database connection layer explicitly chooses primary vs replica based on the query type. Most control, requires explicit code.
2. **Proxy-level routing:** Tools like ProxySQL (MySQL), PgPool-II (PostgreSQL), or RDS Proxy automatically route queries.
3. **ORM support:** Some ORMs have built-in read/write splitting (Rails `ActiveRecord`, Prisma with read replicas).

**Application-level pattern:**
```go
// Two connection pools: primary (R/W) and replica (R)
type DB struct {
    primary *pgxpool.Pool
    replica *pgxpool.Pool
}

func (db *DB) ReadDB() *pgxpool.Pool {
    return db.replica
}

func (db *DB) WriteDB() *pgxpool.Pool {
    return db.primary
}

// Write operations always go to primary
func (db *DB) CreateOrder(ctx context.Context, order Order) error {
    _, err := db.WriteDB().Exec(ctx,
        "INSERT INTO orders (user_id, status, total) VALUES ($1, $2, $3)",
        order.UserID, order.Status, order.Total,
    )
    return err
}

// Read operations go to replica
func (db *DB) GetPublicProducts(ctx context.Context) ([]Product, error) {
    rows, err := db.ReadDB().Query(ctx,
        "SELECT id, name, price FROM products WHERE active = true",
    )
    // ...
    return products, err
}
```

### When NOT to Read from a Replica

This is a critical judgment call. Always use the primary for:

**1. Read-your-writes scenarios:**
After a user updates their profile, the next request should show the updated profile. If you read from a replica with 200ms lag, you'll show the old data. Solutions: (a) always read from primary after writes, (b) track a session token with the LSN of the last write and wait until the replica has caught up past that LSN, (c) sticky sessions — route the same user to the primary for a short window after a write.

**2. Financial/inventory operations:**
Checking account balance before a withdrawal, checking inventory before a purchase. If the replica shows $500 but the primary is $0 (due to a concurrent withdrawal), you've just approved an overdraft. Always read the authoritative state from the primary.

**3. Within the same transaction:**
If you start a transaction on the primary, all reads in that transaction must also go to the primary. You cannot read from a replica mid-transaction.

**4. Admin operations:**
User management, audit queries, configuration reads — use primary to avoid acting on stale state.

**5. Immediately after a write:**
If you write to the primary and immediately redirect to a page that reads the same data, read from the primary or implement LSN-based consistency tracking.

---

## 2. Database Sharding

### What Sharding Is and Why You Do It

**Sharding** is horizontal partitioning of data across multiple independent database servers (shards), where each shard holds a subset of the data.

**Why sharding exists — the scaling wall:**
A single PostgreSQL server can handle:
- ~10,000-50,000 simple queries per second
- Up to ~32TB practical storage (before index management becomes painful)
- Limited by a single machine's CPU, RAM, and I/O

When you hit this wall, you have options:
1. **Vertical scaling:** Bigger server. Expensive, limited ceiling.
2. **Read replicas:** Scales reads, not writes.
3. **Caching:** Reduces DB load for reads. Doesn't help writes.
4. **Sharding:** Splits both reads AND writes across multiple machines. Linear scalability.

**Sharding vs replication:**
| | Replication | Sharding |
|---|---|---|
| Purpose | Read scaling, HA | Write scaling, storage scaling |
| Each node has... | Full copy of all data | A subset of data |
| Write throughput | Limited to primary | Scales with shard count |
| Cross-record queries | Easy | Hard (cross-shard joins) |

### Horizontal vs Vertical Partitioning

**Vertical partitioning:** Split a single table into multiple tables or databases by column groups. Put frequently accessed columns (`id`, `email`, `name`) in a hot table and rarely accessed large columns (`bio`, `preferences_json`, `avatar_blob`) in a cold table. Both tables live on the same server (usually). This is primarily about I/O efficiency, not scaling.

**Horizontal partitioning (sharding):** Split rows across multiple servers. User IDs 1-1M go to shard 1, IDs 1M-2M to shard 2, etc. This is true scaling.

### Shard Key Selection

The shard key is the **most important design decision** in a sharded system. A bad shard key causes hotspots, cross-shard queries, and operational nightmares.

**Requirements for a good shard key:**
1. **High cardinality:** Many distinct values, so data distributes across shards. A boolean column is terrible (only 2 shards possible). `user_id` (millions of values) is excellent.
2. **Uniform distribution:** Values should be roughly evenly distributed. Sequential auto-increment IDs with hash sharding distribute well. IDs that are assigned geographically (all US users have IDs 1-10M, all India users 10M-20M) may hotspot.
3. **Colocation of related data:** Queries that often access related data together should be on the same shard. If you frequently JOIN orders with users, shard both by `user_id` so user 42's orders and user 42's account are on the same shard — no cross-shard join needed.
4. **Write distribution:** Avoid shard keys where a "viral" event causes one shard to receive disproportionate writes. A tweet's `tweet_id` as shard key could cause a viral tweet's replies to hammer one shard.
5. **Query routing simplicity:** You should be able to determine the target shard from the query parameters without a lookup. `user_id` is ideal — every operation that includes `user_id` can be immediately routed.

**Classic bad shard keys:**
- `timestamp` / `created_at` — all new writes go to the latest shard (hotspot). Old shards are cold.
- `country` — a US vs India traffic split might be 80/20, creating an unbalanced shard.
- `user_type` — if you have 2 user types, you have 2 shards. Not scalable.
- Auto-increment primary key with range sharding — new inserts always go to the "current" shard.

**Classic good shard keys:**
- `user_id` — high cardinality, uniform distribution, natural colocates user data
- `tenant_id` (for B2B SaaS) — each business is a tenant, data is naturally grouped
- `order_id` / `session_id` — high cardinality, if queries are per-order/per-session

### Range-Based Sharding

Divide the key space into ranges. Shard 1 holds user_ids 1–1,000,000, Shard 2 holds 1,000,001–2,000,000, etc.

```
Shard 1: user_id [1, 1,000,000)
Shard 2: user_id [1,000,000, 2,000,000)
Shard 3: user_id [2,000,000, 3,000,000)
```

**Routing logic:**
```python
def get_shard(user_id: int) -> int:
    SHARD_SIZE = 1_000_000
    return (user_id - 1) // SHARD_SIZE  # shard index
```

**Advantages:**
- Range queries across shards are easy: "Get all orders between dates" — only need to query shards whose range overlaps the date range.
- Data locality: related data (sequential IDs) is on the same shard.

**Disadvantages:**
- **Hotspot risk:** If user acquisition is sequential (users sign up in order), all new users go to the latest shard. Shard N is hot, older shards are cold.
- **Uneven data:** Some shards may fill up faster (e.g., power users generate more data).
- **Rebalancing:** When a shard fills up, you must split it and migrate data — operationally painful.

### Hash-Based Sharding

Apply a hash function to the shard key modulo the shard count:

```python
def get_shard(user_id: int, num_shards: int) -> int:
    return hash(user_id) % num_shards
```

**Advantages:**
- Uniform distribution — hash functions spread keys evenly.
- Eliminates insertion hotspot — new keys go to random shards.
- Simple routing.

**Disadvantages:**
- **No range queries across shards:** `WHERE user_id BETWEEN 1000 AND 2000` requires querying ALL shards — you don't know which shards have those IDs.
- **The resharding problem:** If you add or remove shards, `hash(key) % num_shards` changes for almost every key. You must migrate ~(N-1)/N of your data. Catastrophic for large datasets.

**Example of resharding problem:**
- 4 shards: `user_id=1000` → `1000 % 4 = 0` → Shard 0
- Add shard, now 5 shards: `user_id=1000` → `1000 % 5 = 0` → Shard 0 (lucky, same)
- But `user_id=1001` → `1001 % 4 = 1` → Shard 1 (old) vs `1001 % 5 = 1` → Shard 1 (same)
- `user_id=1002` → `1002 % 4 = 2` → Shard 2 (old) vs `1002 % 5 = 2` → Shard 2 (same)
- `user_id=1003` → `1003 % 4 = 3` → Shard 3 (old) vs `1003 % 5 = 3` → Shard 3 (same)
- `user_id=1004` → `1004 % 4 = 0` → Shard 0 (old) vs `1004 % 5 = 4` → **Shard 4 (DIFFERENT!)**

On average, `(n-1)/n` of all records need to move when you add 1 shard out of n. With millions of records, this is a multi-day migration with zero-downtime requirements.

### Directory-Based Sharding

Maintain a **lookup table** (a "directory") that maps each shard key (or range) to a shard server.

```
lookup_table:
  tenant_id=acme      → shard3
  tenant_id=globex    → shard1
  tenant_id=initech   → shard3
  tenant_id=umbrella  → shard2
```

**Routing:**
```python
# Check lookup table before every query
def get_shard(tenant_id: str) -> ShardConnection:
    shard_name = lookup_table.get(tenant_id)  # often cached in Redis
    return shard_connections[shard_name]
```

**Advantages:**
- Maximum flexibility: move any key to any shard by updating the directory
- Easy to rebalance: no data migration logic needed — update the directory, migrate the data, update the directory again
- Supports heterogeneous shards: large tenants on dedicated shards, small tenants co-located

**Disadvantages:**
- **Extra lookup hop:** Every query needs to consult the directory before reaching the data shard. Mitigated by aggressive caching.
- **Directory is a single point of failure:** If the directory is unavailable, the entire system stops. Requires HA setup.
- **Operational complexity:** Maintaining the directory, cache invalidation, migration tooling.

**When to use:** Multi-tenant SaaS where tenants have wildly different sizes (e.g., a enterprise customer with 10M rows vs a small business with 100 rows).

### The Resharding Problem & Consistent Hashing

Consistent hashing solves the resharding problem. Instead of `hash(key) % N` (where N changes), consistent hashing places both servers AND keys on a virtual ring (0 to 2^32).

**The ring:**
```
          0
     S1 (hash("shard1"))
     K1 (hash("user:1001"))  → goes to S1 (next clockwise server)
     S2 (hash("shard2"))
     K2 (hash("user:2034"))  → goes to S2
     S3 (hash("shard3"))
     2^32
```

**Routing rule:** A key is assigned to the first server clockwise from the key's position on the ring.

**Adding a shard:**
When you add Shard 4 at a position between S2 and S3 on the ring, only keys that were previously assigned to S3 (those between S2 and S4's new position) need to move to S4. All other keys are unaffected. On average, only `1/N` of keys move when adding 1 shard to an N-shard ring — not `(N-1)/N`.

**Virtual nodes:**
Each physical shard is represented by multiple virtual nodes (e.g., 150 virtual nodes per shard) spread around the ring. This ensures even distribution even with few physical shards and smooths out the distribution of keys transferred when adding/removing shards.

```python
import hashlib
from bisect import insort, bisect_right

class ConsistentHashRing:
    def __init__(self, nodes: list[str], virtual_nodes: int = 150):
        self.ring = {}  # hash → node
        self.sorted_keys = []
        self.virtual_nodes = virtual_nodes
        for node in nodes:
            self.add_node(node)

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node: str):
        for i in range(self.virtual_nodes):
            h = self._hash(f"{node}:{i}")
            self.ring[h] = node
            insort(self.sorted_keys, h)

    def remove_node(self, node: str):
        for i in range(self.virtual_nodes):
            h = self._hash(f"{node}:{i}")
            del self.ring[h]
            self.sorted_keys.remove(h)

    def get_node(self, key: str) -> str:
        h = self._hash(key)
        idx = bisect_right(self.sorted_keys, h) % len(self.sorted_keys)
        return self.ring[self.sorted_keys[idx]]
```

### Cross-Shard Queries

Cross-shard queries are the biggest operational pain in sharded systems.

**The problem:**
```sql
-- Easy in a single DB:
SELECT u.name, COUNT(o.id) AS order_count
FROM users u
JOIN orders o ON o.user_id = u.id
GROUP BY u.id
ORDER BY order_count DESC
LIMIT 10;

-- In a sharded system with users on 4 shards:
-- You must query all 4 shards, then merge/sort/aggregate in application layer
```

**Strategies:**
1. **Colocation:** Design shard keys to keep related data on the same shard. If users and orders are both sharded by `user_id`, `user 42` and `order 42's orders` are always on the same shard — no cross-shard JOIN needed.

2. **Scatter-gather:** Query all shards in parallel, aggregate results in the application layer. Works for simple aggregations but loses the efficiency of a single DB.

3. **Denormalization:** Store redundant data to avoid cross-shard lookups. Store `user_name` in the orders table so you never need to JOIN to users.

4. **Global tables:** Small, rarely-written reference tables (countries, categories) are replicated to every shard. Joins to them work per-shard.

5. **Application-level joins:** Fetch from multiple shards, merge in code. Acceptable for low-cardinality joins.

### Application-Level vs Middleware Sharding

**Application-level sharding:** Your code contains the routing logic. You maintain multiple connection pools (one per shard) and explicitly choose which pool to use based on the shard key.

```go
// Application-level shard routing
func (s *ShardedDB) GetShard(userID int) *pgxpool.Pool {
    shardIndex := s.hashRing.GetNode(fmt.Sprintf("user:%d", userID))
    return s.shards[shardIndex]
}
```

**Pros:** Full control, no external dependency, easy to customize routing logic.
**Cons:** Every service must implement routing; schema migrations must be applied to all shards.

**Middleware sharding — Vitess:**
[Vitess](https://vitess.io/) is an open-source database clustering system for MySQL, developed at YouTube. It sits between your application and MySQL, handling:
- Transparent query routing to the correct shard
- Connection pooling across all shards
- Schema migrations applied across all shards
- Resharding workflows
- Query rewriting to add shard hints

Vitess is used by Slack, GitHub, Square, and YouTube at massive scale.

**Middleware sharding — Citus (now part of PostgreSQL):**
[Citus](https://www.citusdata.com/) extends PostgreSQL to distribute tables across nodes. You declare a distribution column (`SELECT create_distributed_table('orders', 'user_id')`), and Citus automatically:
- Routes queries to the correct shard
- Handles co-location of related tables
- Allows cross-shard queries (aggregated at the coordinator node)

Citus is now maintained as an open-source extension included with Azure Database for PostgreSQL.

### Multi-Tenancy as a Form of Sharding

In B2B SaaS, **tenant-based sharding** is extremely common and is effectively directory-based sharding where each tenant is a shard key.

**Three models:**

1. **Shared schema, shared tables (row-level isolation):**
   - All tenants in the same tables, with a `tenant_id` column + row-level security (RLS)
   - Simplest to operate, least isolation
   - Risk: One large tenant's queries can degrade performance for others

2. **Shared database, separate schema per tenant:**
   - Each tenant has their own PostgreSQL schema (`tenant_acme.orders`, `tenant_globex.orders`)
   - Better isolation, easy to move a tenant to a new server
   - PostgreSQL supports many schemas efficiently

3. **Separate database per tenant:**
   - True isolation, easy compliance (GDPR data deletion is `DROP DATABASE`)
   - Operationally heavy: N databases to maintain, migrate, monitor
   - Platforms like PlanetScale and Neon make this more manageable

---

## 3. PostgreSQL Table Partitioning

**Partitioning** is NOT the same as sharding. Partitioning splits a table into multiple physical partitions on the **same server**. It's about query performance and manageability, not scalability across servers.

### Types of Partitioning

**Range partitioning** (most common for time-series):
```sql
-- Create partitioned table
CREATE TABLE events (
    id          BIGSERIAL,
    user_id     INT NOT NULL,
    event_type  VARCHAR(50),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload     JSONB
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE events_2024_01 PARTITION OF events
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE events_2024_02 PARTITION OF events
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Add indexes per partition (smaller, faster)
CREATE INDEX ON events_2024_01 (user_id, created_at);
CREATE INDEX ON events_2024_02 (user_id, created_at);

-- Automate with pg_partman extension
```

**List partitioning:**
```sql
CREATE TABLE orders (
    id       BIGSERIAL,
    region   VARCHAR(20) NOT NULL,
    status   VARCHAR(20),
    ...
) PARTITION BY LIST (region);

CREATE TABLE orders_us PARTITION OF orders FOR VALUES IN ('us-east', 'us-west');
CREATE TABLE orders_eu PARTITION OF orders FOR VALUES IN ('eu-west', 'eu-central');
CREATE TABLE orders_ap PARTITION OF orders FOR VALUES IN ('ap-south', 'ap-east');
```

**Hash partitioning:**
```sql
CREATE TABLE users (
    id    BIGSERIAL,
    email VARCHAR(255),
    ...
) PARTITION BY HASH (id);

CREATE TABLE users_0 PARTITION OF users FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE users_1 PARTITION OF users FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE users_2 PARTITION OF users FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE users_3 PARTITION OF users FOR VALUES WITH (MODULUS 4, REMAINDER 3);
```

### Partition Pruning

The main performance benefit of partitioning. When a query has a WHERE clause on the partition key, PostgreSQL's planner prunes partitions that cannot contain matching rows and scans only relevant partitions.

```sql
-- Query for January events — only scans events_2024_01
EXPLAIN SELECT * FROM events WHERE created_at >= '2024-01-01' AND created_at < '2024-02-01';
-- Seq Scan on events_2024_01 (partition pruning eliminates all other partitions)

-- No pruning — scans all partitions
EXPLAIN SELECT * FROM events WHERE user_id = 42;
```

**Constraint exclusion** must be enabled (it is by default in modern PostgreSQL):
```sql
SET enable_partition_pruning = on;  -- default
```

### Partitioning Benefits

1. **Query pruning:** Time-bounded queries only scan relevant partitions
2. **Faster VACUUM:** VACUUM operates per-partition — small, focused cleanup
3. **Archival:** `DETACH PARTITION` + `ALTER TABLE ... RENAME` to archive old data instantly without DELETE
4. **Index size:** Each partition has its own smaller indexes — fits in memory, faster
5. **Parallel query:** Multiple partitions can be scanned in parallel by parallel workers

```sql
-- Archive January data: detach and rename (instant, no data movement)
ALTER TABLE events DETACH PARTITION events_2024_01;
ALTER TABLE events_2024_01 RENAME TO events_archive_2024_01;
-- Now move to cold storage or S3 via pg_dump
```

---

## 4. Advanced Connection Pooling with PgBouncer

### PgBouncer Modes

PgBouncer sits between your application and PostgreSQL, maintaining a small pool of actual PostgreSQL connections while accepting many more application connections.

**Session Mode:**
- 1 client connection holds 1 server connection for the entire session
- No real multiplexing — functionally identical to connecting directly
- Useful only when your client library can't manage a pool itself
- `max_client_conn` limit applies, but no sharing benefit

**Transaction Mode (most common in production):**
- A server connection is assigned to a client only for the duration of a transaction
- Between transactions, the server connection is returned to the pool
- A single server connection can serve hundreds of clients that have low transaction frequency
- **Limitations:** PostgreSQL session-level features don't work across transactions:
  - `SET` commands — don't persist between transactions
  - `PREPARE` / `EXECUTE` for prepared statements — scoped to session
  - Advisory locks — session-scoped, not transaction-scoped
  - `LISTEN`/`NOTIFY` — requires session mode

**Statement Mode:**
- Server connection is returned to pool after each statement, even within a multi-statement transaction
- This breaks transaction atomicity — rarely used
- Only safe for non-transactional workloads (e.g., analytics queries)

### Connection Pool Sizing

**The formula:**
```
optimal_pool_size = num_cores × (1 + wait_time / service_time)

More practical rule of thumb (PostgreSQL):
pool_size = 2 × num_CPUs + num_disks

Example: 8-core server with SSD:
pool_size = 2 × 8 + 1 ≈ 17 connections
```

**Why small pools outperform large pools:**
Each PostgreSQL connection is a forked OS process with ~5-10MB of memory overhead. At 500 connections: 2.5-5GB of RAM just for connection overhead, plus context-switching overhead. PostgreSQL performs best with 20-100 active connections. PgBouncer absorbs the application's "need" for many connections and serializes them through a small pool.

**PgBouncer configuration:**
```ini
# /etc/pgbouncer/pgbouncer.ini
[databases]
mydb = host=primary_postgres port=5432 dbname=mydb

[pgbouncer]
pool_mode = transaction
max_client_conn = 5000      # how many app connections PgBouncer accepts
default_pool_size = 20      # server connections per database per user
min_pool_size = 5           # minimum idle server connections
reserve_pool_size = 5       # extra connections for brief spikes
reserve_pool_timeout = 5    # wait before using reserve pool
server_idle_timeout = 600   # close idle server connections after 10m
client_idle_timeout = 0     # don't close idle clients (connection borrow time)
auth_type = scram-sha-256
```

### Read/Write Splitting at Pool Level

Configure two PgBouncer instances — one pointing to the primary, one to the replica:

```ini
# pgbouncer-primary.ini (port 6432)
[databases]
mydb = host=pg-primary port=5432 dbname=mydb

# pgbouncer-replica.ini (port 6433)
[databases]
mydb = host=pg-replica port=5432 dbname=mydb
```

Your application connects to `localhost:6432` for writes and `localhost:6433` for reads. You could also use HAProxy to route based on SQL patterns (less reliable than application-level routing).

---

## 5. Implementation Examples

### Go + Chi: Read/Write Splitting & Shard Routing

```go
package database

import (
    "context"
    "errors"
    "fmt"
    "hash/fnv"
    "log"
    "sort"
    "sync"

    "github.com/go-chi/chi/v5"
    "github.com/jackc/pgx/v5/pgxpool"
)

// ─── Read/Write Split DB ───────────────────────────────────────────────────────

type ReplicaAwareDB struct {
    primary  *pgxpool.Pool
    replicas []*pgxpool.Pool
    mu       sync.RWMutex
    rrIndex  int // round-robin index
}

func NewReplicaAwareDB(primaryDSN string, replicaDSNs []string) (*ReplicaAwareDB, error) {
    primary, err := pgxpool.New(context.Background(), primaryDSN)
    if err != nil {
        return nil, fmt.Errorf("connect to primary: %w", err)
    }

    replicas := make([]*pgxpool.Pool, 0, len(replicaDSNs))
    for _, dsn := range replicaDSNs {
        r, err := pgxpool.New(context.Background(), dsn)
        if err != nil {
            log.Printf("warn: failed to connect to replica %s: %v", dsn, err)
            continue // degrade gracefully
        }
        replicas = append(replicas, r)
    }

    return &ReplicaAwareDB{primary: primary, replicas: replicas}, nil
}

// Replica returns a replica using round-robin, falls back to primary if none available
func (db *ReplicaAwareDB) Replica() *pgxpool.Pool {
    db.mu.Lock()
    defer db.mu.Unlock()
    if len(db.replicas) == 0 {
        return db.primary // fallback
    }
    pool := db.replicas[db.rrIndex%len(db.replicas)]
    db.rrIndex++
    return pool
}

func (db *ReplicaAwareDB) Primary() *pgxpool.Pool {
    return db.primary
}

// ─── Consistent Hash Ring ─────────────────────────────────────────────────────

const virtualNodes = 150

type HashRing struct {
    ring        map[uint32]*pgxpool.Pool
    sortedHashes []uint32
    shards      map[string]*pgxpool.Pool
}

func NewHashRing(shards map[string]string) (*HashRing, error) {
    r := &HashRing{
        ring:   make(map[uint32]*pgxpool.Pool),
        shards: make(map[string]*pgxpool.Pool),
    }
    for name, dsn := range shards {
        pool, err := pgxpool.New(context.Background(), dsn)
        if err != nil {
            return nil, fmt.Errorf("connect shard %s: %w", name, err)
        }
        r.shards[name] = pool
        r.addNode(name, pool)
    }
    return r, nil
}

func (r *HashRing) addNode(name string, pool *pgxpool.Pool) {
    for i := 0; i < virtualNodes; i++ {
        h := r.hash(fmt.Sprintf("%s:%d", name, i))
        r.ring[h] = pool
        r.sortedHashes = append(r.sortedHashes, h)
    }
    sort.Slice(r.sortedHashes, func(i, j int) bool {
        return r.sortedHashes[i] < r.sortedHashes[j]
    })
}

func (r *HashRing) hash(key string) uint32 {
    h := fnv.New32a()
    h.Write([]byte(key))
    return h.Sum32()
}

func (r *HashRing) GetShard(key string) *pgxpool.Pool {
    h := r.hash(key)
    idx := sort.Search(len(r.sortedHashes), func(i int) bool {
        return r.sortedHashes[i] >= h
    })
    if idx >= len(r.sortedHashes) {
        idx = 0
    }
    return r.ring[r.sortedHashes[idx]]
}

// ─── Service layer using shard routing ────────────────────────────────────────

type OrderService struct {
    ring *HashRing
    db   *ReplicaAwareDB
}

func (s *OrderService) CreateOrder(ctx context.Context, userID int, amount float64) error {
    shard := s.ring.GetShard(fmt.Sprintf("user:%d", userID))
    _, err := shard.Exec(ctx,
        "INSERT INTO orders (user_id, total_amount, status) VALUES ($1, $2, 'pending')",
        userID, amount,
    )
    return err
}

func (s *OrderService) GetUserOrders(ctx context.Context, userID int) ([]Order, error) {
    // Reads can go to replica IF your app can tolerate slight staleness
    // For order history, slight lag is usually acceptable
    shard := s.ring.GetShard(fmt.Sprintf("user:%d", userID))
    rows, err := shard.Query(ctx,
        "SELECT id, total_amount, status, created_at FROM orders WHERE user_id = $1 ORDER BY created_at DESC LIMIT 50",
        userID,
    )
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    var orders []Order
    for rows.Next() {
        var o Order
        if err := rows.Scan(&o.ID, &o.TotalAmount, &o.Status, &o.CreatedAt); err != nil {
            return nil, err
        }
        orders = append(orders, o)
    }
    return orders, rows.Err()
}

type Order struct {
    ID          int
    TotalAmount float64
    Status      string
    CreatedAt   string
}

// ─── Chi Router wiring ────────────────────────────────────────────────────────

func SetupRoutes(r *chi.Mux, svc *OrderService) {
    r.Get("/users/{userID}/orders", func(w http.ResponseWriter, req *http.Request) {
        // route handler
    })
}
```

---

### Node.js + Express: Read/Write Split

```javascript
const { Pool } = require('pg');

// Two connection pools: write → primary, read → replica
const primaryPool = new Pool({
  host: process.env.DB_PRIMARY_HOST,
  port: 5432,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  max: 20,                   // max connections in pool
  idleTimeoutMillis: 30000,  // close idle connections after 30s
  connectionTimeoutMillis: 2000,
});

const replicaPool = new Pool({
  host: process.env.DB_REPLICA_HOST,
  port: 5432,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  max: 40,       // replicas can handle more read connections
  idleTimeoutMillis: 30000,
});

// Utility: auto-select pool based on operation type
function db(readonly = false) {
  return readonly ? replicaPool : primaryPool;
}

// Always use primary for writes
async function createUser(name, email) {
  const result = await db(false).query(
    'INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id',
    [name, email]
  );
  return result.rows[0];
}

// Can use replica for reads (tolerate eventual consistency)
async function getProducts(category) {
  const result = await db(true).query(
    'SELECT id, name, price FROM products WHERE category = $1 AND active = true ORDER BY name',
    [category]
  );
  return result.rows;
}

// Must use primary for read-your-writes scenarios
async function getUserAfterUpdate(userId, newEmail) {
  await db(false).query(
    'UPDATE users SET email = $1 WHERE id = $2',
    [newEmail, userId]
  );
  // Read from PRIMARY — we just wrote to it, need consistent read
  const result = await db(false).query(
    'SELECT * FROM users WHERE id = $1',
    [userId]
  );
  return result.rows[0];
}

// Shard routing (application-level)
const shardPools = {
  shard0: new Pool({ host: process.env.SHARD0_HOST, /* ... */ }),
  shard1: new Pool({ host: process.env.SHARD1_HOST, /* ... */ }),
  shard2: new Pool({ host: process.env.SHARD2_HOST, /* ... */ }),
  shard3: new Pool({ host: process.env.SHARD3_HOST, /* ... */ }),
};

function getShardForUser(userId) {
  // Simple modulo sharding — replace with consistent hash in production
  const shardIndex = userId % Object.keys(shardPools).length;
  return shardPools[`shard${shardIndex}`];
}

async function createOrder(userId, amount) {
  const shard = getShardForUser(userId);
  const result = await shard.query(
    'INSERT INTO orders (user_id, total_amount, status) VALUES ($1, $2, $3) RETURNING id',
    [userId, amount, 'pending']
  );
  return result.rows[0];
}

// Express middleware to attach DB pools to request
function dbMiddleware(req, res, next) {
  req.db = {
    write: primaryPool,
    read: replicaPool,
    shardFor: (userId) => getShardForUser(userId),
  };
  next();
}

const express = require('express');
const app = express();
app.use(express.json());
app.use(dbMiddleware);

app.post('/orders', async (req, res) => {
  try {
    const { userId, amount } = req.body;
    const order = await createOrder(userId, amount);
    res.status(201).json(order);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
```

---

### Python + FastAPI: Partitioned Table + Replica Routing

```python
from __future__ import annotations
import os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from fastapi import FastAPI, Depends, HTTPException
import asyncio

# ─── Two engine setup: primary + replica ──────────────────────────────────────

PRIMARY_DSN   = os.environ["PRIMARY_DATABASE_URL"]
REPLICA_DSN   = os.environ.get("REPLICA_DATABASE_URL", PRIMARY_DSN)  # fallback to primary

primary_engine = create_async_engine(
    PRIMARY_DSN,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # verify connection alive before using
    echo=False,
)

replica_engine = create_async_engine(
    REPLICA_DSN,
    pool_size=40,        # replicas get more read connections
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)

PrimarySession = async_sessionmaker(primary_engine, expire_on_commit=False)
ReplicaSession  = async_sessionmaker(replica_engine,  expire_on_commit=False)

# ─── Dependency injection for write vs read sessions ──────────────────────────

async def get_write_session():
    """Always routes to primary — use for writes and read-your-writes."""
    async with PrimarySession() as session:
        yield session

async def get_read_session():
    """Routes to replica — use for reads tolerant of slight staleness."""
    async with ReplicaSession() as session:
        yield session

# ─── Partition management helper ──────────────────────────────────────────────

PARTITION_SETUP_SQL = """
-- Partitioned events table (run once during schema migration)
CREATE TABLE IF NOT EXISTS events (
    id          BIGSERIAL,
    user_id     INT NOT NULL,
    event_type  VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload     JSONB DEFAULT '{}',
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Helper function to create monthly partitions automatically
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name TEXT, year INT, month INT)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    partition_name := format('%s_%s_%s', table_name, year, lpad(month::TEXT, 2, '0'));
    start_date := make_date(year, month, 1);
    end_date := start_date + INTERVAL '1 month';
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I 
         FOR VALUES FROM (%L) TO (%L)',
        partition_name, table_name, start_date, end_date
    );
    
    -- Index on the partition
    EXECUTE format(
        'CREATE INDEX IF NOT EXISTS %I ON %I (user_id, created_at)',
        partition_name || '_uid_cat_idx', partition_name
    );
END;
$$ LANGUAGE plpgsql;
"""

async def setup_partitions(session: AsyncSession, year: int, months: list[int]):
    """Create partitions for the given months. Call during maintenance or at startup."""
    for month in months:
        await session.execute(
            text("SELECT create_monthly_partition('events', :year, :month)"),
            {"year": year, "month": month}
        )
    await session.commit()

# ─── Replication lag check ─────────────────────────────────────────────────────

async def get_replication_lag_seconds(session: AsyncSession) -> Optional[float]:
    """
    Check replication lag in seconds.
    Returns None if running on primary (no lag concept).
    """
    try:
        result = await session.execute(
            text("SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))")
        )
        return result.scalar()
    except Exception:
        return None

# ─── FastAPI routes ────────────────────────────────────────────────────────────

app = FastAPI()

@app.get("/events")
async def list_events(
    user_id: int,
    start: str,
    end: str,
    session: AsyncSession = Depends(get_read_session)
):
    """Uses partition pruning — only scans relevant monthly partitions."""
    result = await session.execute(
        text("""
            SELECT id, event_type, created_at, payload
            FROM events
            WHERE user_id = :user_id
              AND created_at >= :start::timestamptz
              AND created_at <  :end::timestamptz
            ORDER BY created_at DESC
            LIMIT 100
        """),
        {"user_id": user_id, "start": start, "end": end}
    )
    return [dict(row._mapping) for row in result]

@app.post("/events")
async def create_event(
    user_id: int,
    event_type: str,
    payload: dict,
    session: AsyncSession = Depends(get_write_session)  # writes → primary
):
    result = await session.execute(
        text("""
            INSERT INTO events (user_id, event_type, payload)
            VALUES (:user_id, :event_type, :payload::jsonb)
            RETURNING id, created_at
        """),
        {"user_id": user_id, "event_type": event_type, "payload": str(payload)}
    )
    await session.commit()
    row = result.one()
    return {"id": row.id, "created_at": row.created_at}

@app.get("/health/replication")
async def replication_health(session: AsyncSession = Depends(get_read_session)):
    """Health check endpoint to monitor replica lag."""
    lag = await get_replication_lag_seconds(session)
    if lag is None:
        return {"status": "primary", "lag_seconds": 0}
    status = "healthy" if lag < 5 else "lagging" if lag < 30 else "critical"
    return {"status": status, "lag_seconds": lag}
```

---

## 6. Common Patterns & Best Practices

**Replication:**
- Always connect to primary for transactions that include writes AND subsequent reads of the same data
- Implement circuit-breaker on replicas: fall back to primary if replica lag exceeds threshold
- Use `pg_last_xact_replay_timestamp()` to monitor replica freshness from within the app
- Monitor `replication_slot` lag — stale slots block VACUUM on the primary

**Sharding:**
- Design your data model for sharding from day 1 — retrofitting is painful
- Shard by `user_id` for user-centric apps — colocates all user data
- Add a `shard_id` column to every table that doesn't naturally contain the shard key
- Use consistent hashing in your routing layer even if you only have 2 shards — future resharding will be ~1/N instead of catastrophic

**Partitioning:**
- Always partition high-volume append-only tables (events, logs, audit trails, metrics)
- Create partitions ahead of time — don't let the default partition fill up
- Use `pg_partman` extension to automate partition creation and retention
- Set `partition_pruning = on` (default) and always include partition key in WHERE clauses

**Connection pooling:**
- Never connect directly from application to PostgreSQL in production — always use PgBouncer
- Transaction mode is almost always the right choice
- Tune `pool_size` empirically — watch `pg_stat_activity` for queue depth
- Set `pool_pre_ping` or `server_idle_timeout` to recycle stale connections

---

## 7. Common Pitfalls

| Pitfall | Problem | Fix |
|---|---|---|
| Reading from replica after write | Read-your-writes violation (stale data) | Route post-write reads to primary |
| Using timestamp as shard key | All writes go to latest shard (hotspot) | Use user_id or tenant_id as shard key |
| `hash(key) % N` sharding | Resharding moves `(N-1)/N` of data | Use consistent hashing |
| Cross-shard JOINs | Requires scatter-gather, extremely slow | Colocate related tables on same shard key |
| No FK indexes in sharded DB | Lookups can't use FKs across shards anyway, but within-shard FKs still need indexes | Index all FK columns |
| Missing partition on partitioned table | Inserts fail or go to `DEFAULT` partition | Automate partition creation with pg_partman |
| Long-running replica queries | Blocks WAL apply, causes lag to grow | Set `statement_timeout` on replica |
| Session-level features in transaction-pool mode | PgBouncer transaction mode doesn't persist SET, advisory locks | Use prepared statements via pgbouncer `server_reset_query` or switch to session mode |
| Forgetting to ANALYZE after bulk load | Planner uses stale stats, picks bad plan | Run ANALYZE after bulk inserts |
| Replication slot accumulation | Stale slots hold WAL files, primary disk fills | Monitor `pg_replication_slots`, drop unused slots |

---

## 8. Interview Questions & Model Answers

**Q: What is database sharding and when would you use it?**

Sharding is horizontal partitioning of data across multiple independent database servers, where each server (shard) holds a mutually exclusive subset of the data. You use sharding when a single database server can no longer handle your write throughput or storage requirements — read replicas and caching are exhausted. Typical triggers: write throughput exceeding 50K QPS, storage exceeding ~5-10TB where index maintenance degrades, or global latency requirements that require data to be physically close to users in multiple regions.

**Q: How do you choose a shard key? What makes a bad shard key?**

A good shard key must be: (1) high cardinality — many distinct values for even distribution, (2) uniformly distributed — values spread evenly across the key space, (3) colocate frequently-accessed related data — queries that JOIN should be on the same shard, (4) present in most queries — so routing is O(1) without a lookup. Bad shard keys: `created_at` (all new writes go to the latest shard — hotspot), `status` or `type` (low cardinality — only 2-5 shards possible), `country` (uneven distribution — US traffic dominates), sequential auto-increment IDs with range sharding (same as `created_at` — always hits the last shard). `user_id` is the canonical good shard key for user-centric apps.

**Q: What is consistent hashing and how does it help with resharding?**

Consistent hashing places both servers and keys on a virtual ring (hash space 0 to 2^32). A key is assigned to the first server clockwise from the key's hash position. When you add a server, only the keys in the arc between the new server and its predecessor need to move — roughly `1/N` of total keys. With simple modulo sharding (`hash(key) % N`), adding one shard to N means recalculating `hash(key) % (N+1)` for all keys — and roughly `(N-1)/N` of keys land on a different shard than before. Virtual nodes (150+ per physical shard) ensure even distribution across few physical shards.

**Q: What is replication lag and when is it a problem?**

Replication lag is the delay between a write being committed on the primary and becoming visible on the replica. It stems from network transit time + WAL apply time. In same-datacenter async replication, typical lag is 10-200ms; cross-region can be seconds. It's a problem in: (1) read-your-writes scenarios — user updates profile, reads it back from replica, sees old data; (2) financial operations — reading account balance from replica before a debit; (3) inventory checks — replica shows 1 item in stock but primary shows 0 (already sold). Solution: route these queries to the primary, or implement LSN-based consistency tracking (record the LSN after each write, wait until replica catches up past that LSN before reading from it).

**Q: What is the difference between sharding and partitioning?**

Sharding distributes data across multiple physical servers — primarily for write scalability and storage limits. Each shard is an independent database. Partitioning divides a table into multiple physical pieces on the **same server** — primarily for query performance (partition pruning) and manageability (easier archival, targeted VACUUM). Partitioning doesn't give you more write capacity or more total storage (you still have one server). You can combine both: shard at the application level for scalability, then partition each shard's large tables for query performance.

**Q: When should you NOT read from a replica?**

Never read from a replica when: (1) you just performed a write and need to read the same data back (read-your-writes consistency); (2) the operation has financial or inventory implications where stale data leads to incorrect decisions; (3) within a database transaction — all statements in a transaction must use the same connection/server; (4) for admin or configuration reads where acting on stale state causes correctness issues; (5) when your SLA requires read-after-write consistency and you can't implement LSN-tracking. As a rule: replicas are for data where eventual consistency is acceptable and incorrect reads don't cause monetary or data integrity problems.

**Q: What is Vitess and what problem does it solve?**

Vitess is an open-source database clustering system for MySQL, originally developed at YouTube to scale their MySQL infrastructure to billions of rows. It solves the operational complexity of sharding by: (1) acting as a transparent proxy — applications connect to Vitess as if it were a single MySQL server; (2) automatically routing queries to the correct shard based on the vindex (shard key); (3) managing schema migrations across all shards atomically; (4) providing built-in connection pooling (VTGate + VTTablet); (5) supporting online resharding workflows that move data without downtime. It's used by Slack, Square, GitHub, and PlanetScale (which is built on top of Vitess).

---

## 9. Resources

- [Vitess Documentation](https://vitess.io/docs/)
- [Citus Data (PostgreSQL Sharding)](https://docs.citusdata.com/)
- [PostgreSQL Streaming Replication](https://www.postgresql.org/docs/current/warm-standby.html)
- [PostgreSQL Table Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [PgBouncer Documentation](https://www.pgbouncer.org/config.html)
- [pg_partman Extension](https://github.com/pgpartman/pg_partman) — automate partition maintenance
- [Consistent Hashing Explained](https://highscalability.com/consistent-hashing/)
- [Designing Data-Intensive Applications](https://dataintensive.net/) — Martin Kleppmann — Ch. 5 (Replication), Ch. 6 (Partitioning)
- [AWS RDS Read Replicas Best Practices](https://aws.amazon.com/blogs/database/best-practices-for-amazon-rds-read-replicas/)

---

**Next:** [Part 8.1: Caching Strategies](../part-08/08-caching-strategies.md)
