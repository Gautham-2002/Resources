# Track 2: Storage & Data — System Design Study Guide
### System Design Self-Study Series for Gautham Gokulakonda

> This is Track 2 of 5. It covers everything about where and how data lives. This is the most frequently deep-dived topic in FAANG and Indian unicorn interviews. Breadth first — but with enough depth to answer *why*, not just *what*.

---

## Table of Contents
1. [SQL Databases (Relational)](#1-sql-databases-relational)
2. [NoSQL Databases — Types and Use Cases](#2-nosql-databases--types-and-use-cases)
3. [CAP Theorem](#3-cap-theorem)
4. [Indexing](#4-indexing)
5. [Database Replication](#5-database-replication)
6. [Database Sharding](#6-database-sharding)
7. [Consistent Hashing](#7-consistent-hashing)
8. [SQL vs NoSQL — The Decision Framework](#8-sql-vs-nosql--the-decision-framework)
9. [Object Storage](#9-object-storage)
10. [Search Engines (Elasticsearch / OpenSearch)](#10-search-engines-elasticsearch--opensearch)
11. [Data Modelling Fundamentals](#11-data-modelling-fundamentals)
12. [Database Connection Pooling](#12-database-connection-pooling)
13. [Quick Revision Cheatsheet](#quick-revision-cheatsheet)

---

## 1. SQL Databases (Relational)

**What it is:** A relational database stores data in tables with defined schemas, where relationships between tables are expressed via foreign keys and enforced at the database level.

**Why it exists / What problem it solves:** Before relational databases, data was stored in hierarchical or flat-file formats that made querying relationships extremely difficult. The relational model (Codd, 1970) brought a principled way to represent and query any relationship via SQL, and ACID properties gave us the correctness guarantees that financial and transactional systems need.

---

### ACID Properties

These are the four guarantees a transactional database makes. Know them cold — they come up in every payment/booking system discussion.

| Property | What it means | Why it matters |
|----------|--------------|----------------|
| **Atomicity** | A transaction either fully succeeds or fully rolls back. No partial writes. | Prevents half-deducted balances. |
| **Consistency** | After every transaction, the database moves from one valid state to another. All constraints, triggers, and rules hold. | Your foreign keys and CHECK constraints are always respected. |
| **Isolation** | Concurrent transactions don't see each other's intermediate state (to the degree configured). | Prevents dirty reads, phantom reads. |
| **Durability** | Once committed, the data survives crashes. It's on disk (WAL journal). | You can trust that a confirmed payment actually persisted. |

---

### Isolation Levels

Isolation is a dial, not a switch. Higher isolation = more correctness, more lock contention, lower throughput.

| Level | Dirty Read | Non-Repeatable Read | Phantom Read | Use When |
|-------|-----------|---------------------|-------------|----------|
| Read Uncommitted | ✅ Possible | ✅ Possible | ✅ Possible | Almost never — you can read uncommitted garbage |
| Read Committed | ❌ Prevented | ✅ Possible | ✅ Possible | Default in PostgreSQL; good for most OLTP |
| Repeatable Read | ❌ Prevented | ❌ Prevented | ✅ Possible | When same row must look identical across reads in one txn |
| Serializable | ❌ Prevented | ❌ Prevented | ❌ Prevented | Financial systems, seat bookings — full isolation |

> **Key insight:** PostgreSQL's default is Read Committed. MySQL's default is Repeatable Read. This matters in practice because phantom reads can bite you in MySQL at the "safe-sounding" default level.

**Glossary of anomalies:**
- **Dirty read:** You read a row that another transaction modified but hasn't committed yet. That transaction rolls back — you read garbage.
- **Non-repeatable read:** You read a row twice in a transaction. Between reads, another transaction updates it. You see two different values.
- **Phantom read:** You run a range query twice. Between reads, another transaction inserts rows matching your range. The set of rows changes.

---

### Transactions — When They're Critical

Use explicit transactions when:
- **Multiple rows must change atomically** — debit account A, credit account B.
- **Read-then-write patterns** — check seat availability, then book it.
- **Cascading updates** — updating an order and its line items together.

```sql
BEGIN;
  UPDATE accounts SET balance = balance - 500 WHERE id = 1;
  UPDATE accounts SET balance = balance + 500 WHERE id = 2;
COMMIT;
-- If anything fails between BEGIN and COMMIT, both changes roll back.
```

**Interview Q&A:**

- **Q: You have a booking system with 10,000 simultaneous seat reservations. How do you prevent double-booking?** *(Flipkart interview)*

  A: Use a `SELECT FOR UPDATE` (pessimistic locking) within a transaction at Serializable isolation. When a user picks a seat, lock that row: `SELECT * FROM seats WHERE id = $1 AND status = 'available' FOR UPDATE`. Then update if the lock succeeds. At 10k concurrent users, you also want to reduce lock contention by: (1) sharding the seat table by event/show, (2) using an idempotency key so retries don't double-book, (3) setting a short lock timeout with a friendly error. Alternatively, use optimistic locking with a `version` column — attempt the update, check rows_affected = 1, retry on conflict. Optimistic locking is better when conflicts are rare (open-seat scenario); pessimistic is better when conflicts are frequent (flash sale, last-few-seats scenario).

---

### PostgreSQL — MVCC (Multi-Version Concurrency Control)

**What it is:** Instead of using read locks, PostgreSQL keeps multiple versions of each row. Each transaction sees a snapshot of the database as of its start time.

**Why it matters in interviews:** This is why PostgreSQL is better than MySQL for read-heavy workloads with concurrent writes.

**How MVCC works:**
- Every row has `xmin` (transaction ID that created it) and `xmax` (transaction ID that deleted/updated it).
- A SELECT sees rows where `xmin ≤ current_txn_id < xmax`.
- Writers create new row versions; readers see the old version simultaneously.
- No reader blocks writer, no writer blocks reader.

**The cost:** Dead row versions accumulate. PostgreSQL's `VACUUM` process cleans them up. Neglecting VACUUM on high-write tables causes table bloat and slower scans — a real operational concern at scale.

> **MVCC vs locking:** MySQL (InnoDB) also uses MVCC. The difference is that PostgreSQL's implementation is more granular and its MVCC is used at every isolation level. The result: PostgreSQL handles read-heavy concurrent workloads better with less lock contention.

---

### When to Choose SQL

- Data has a defined, stable schema with enforced constraints
- You need multi-row ACID transactions (financial, inventory)
- Complex joins across multiple entities (reporting, analytics with known schemas)
- You need strong consistency as a baseline
- Team already knows SQL and query optimization

**Interview Q&A:**

- **Q: How would you handle a read-heavy workload on a PostgreSQL database?**

  A: Several layers: First, add read replicas and route all SELECT queries to replicas via a connection pooler (PgBouncer) or application logic. Second, ensure proper indexing — run EXPLAIN ANALYZE on slow queries and add missing indexes. Third, use Redis for frequently-read, rarely-changed data (user sessions, config). Fourth, consider connection pooling to prevent connection exhaustion (PgBouncer in transaction mode). Fifth, if reads are still bottlenecked, evaluate denormalization for the hottest query paths — accept some redundancy to avoid expensive joins. If all else fails and you're at true write-scale limits, consider sharding or migrating the hot data to a purpose-fit store.

---

## 2. NoSQL Databases — Types and Use Cases

**What it is:** Non-relational databases that sacrifice some SQL features (joins, ACID, fixed schema) to gain horizontal scalability, schema flexibility, or specialized access patterns.

**Why they exist:** SQL databases scale reads (replicas) well but struggle to scale writes horizontally — sharding SQL is hard and limited. NoSQL databases were designed from the ground up for distributed writes. Also, not all data fits neatly into rows and tables.

---

### Key-Value Stores (Redis, DynamoDB)

**What it is:** The simplest possible data model — a key maps to a value. O(1) reads and writes.

**Use cases:**
- **Caching** — session data, API responses, frequently-read config (Redis)
- **Feature flags** — `feature:dark_mode:user:123 = true`
- **Rate limiting** — `rate:ip:1.2.3.4 = 47` (Redis INCR + TTL)
- **Shopping carts** — keyed by user ID, value is a serialized cart (DynamoDB)
- **Primary database for simple entities** — DynamoDB used at Amazon for orders (simple get-by-key patterns)

**Redis-specific:** In-memory, sub-millisecond latency. Supports data structures beyond strings (lists, sets, sorted sets, hashes, streams). Sorted sets are perfect for leaderboards and time-windowed rate limiting.

**DynamoDB-specific:** Managed AWS service, persistent, scales to petabytes. Each item keyed by partition key (+ optional sort key). No joins — queries are either by key or by secondary index.

**Trade-off:** No ad hoc queries. You must know your access patterns upfront. No joins. If your data model changes, you may need to rebuild indexes.

---

### Document Stores (MongoDB, Firestore)

**What it is:** Stores semi-structured documents (typically JSON/BSON). Each document can have a different shape within the same collection.

**Use cases:**
- **User profiles** — each user may have different optional attributes
- **Product catalogs** — electronics have voltage specs; clothes have sizes/colors — different shapes
- **CMS / content** — blog posts with variable metadata
- **Mobile app backends** — Firestore is optimized for real-time sync to clients

**Strengths:**
- Schema flexibility — add fields without migrations
- Hierarchical data modelled naturally (nested documents)
- Good horizontal sharding support (MongoDB auto-sharding)

**Trade-off:** Joins are expensive (aggregation pipelines). Transactions exist in MongoDB 4.0+ but are costlier than Postgres. Consistency is configurable but defaults to eventual in replica sets.

---

### Wide-Column Stores (Cassandra, HBase)

**What it is:** Data is stored in tables, but each row can have a different set of columns. Internally, data is stored column-family-by-column-family on disk, making column-scoped queries very fast.

**Why the column layout helps:** If you need to read one column across millions of rows (e.g., all timestamps for a user's events), a columnar layout reads only that column from disk instead of full rows. Massively reduces I/O.

**Use cases:**
- **Time-series data** — IoT sensor readings, metrics, event logs
- **User activity feeds** — partition by user_id, cluster by timestamp
- **Messaging apps** — partition by conversation_id, cluster by message_timestamp
- **Netflix** uses Cassandra for watch history (billions of rows, high write throughput)

**Cassandra's write model:**
- Writes go to an in-memory memtable and WAL (commit log), then flush to SSTables on disk
- No in-place updates — writes are always appends (SSTable is immutable)
- Compaction merges SSTables periodically
- This is why Cassandra handles insane write throughput — writes never block on disk seeks

**Trade-off:** No joins. No ad hoc queries (must query by partition key). Denormalization is required. Reads that don't hit the partition key require a full scan. Strong consistency is possible but reduces availability (tunable consistency: ONE, QUORUM, ALL).

**Interview Q&A:**
- **Q: How does Cassandra handle high write throughput?**

  A: Cassandra's write path is optimized for throughput. Writes go to a commit log (for durability) and an in-memory memtable simultaneously — both are sequential writes. Once the memtable fills, it's flushed to an immutable SSTable on disk. No random disk seeks, no locking individual rows. Write throughput is bounded by network and commit log I/O, not random disk access. Add multiple nodes with consistent hashing for partition distribution, and writes scale linearly with cluster size. Tunable consistency (QUORUM vs ONE) lets you trade off write latency for consistency.

---

### Graph Databases (Neo4j)

**What it is:** Data is stored as nodes (entities) and edges (relationships), each with properties. Traversal queries are first-class.

**Use cases:**
- **Fraud detection** — "find all accounts within 3 hops of this fraudulent account"
- **Social networks** — friends-of-friends, mutual connections
- **Recommendation engines** — users who liked X also liked Y (collaborative filtering)
- **Knowledge graphs** — semantic relationships between entities

**Why not SQL for this:** A "friends of friends" query in SQL requires multiple self-joins that become exponentially expensive as hop count increases. Graph DBs traverse edges natively in O(hops), not O(rows).

---

### Time-Series Databases (InfluxDB, TimescaleDB)

**What it is:** Optimized for time-stamped data — metrics, monitoring, IoT readings.

**Why regular DBs struggle:** Metrics generate millions of writes per second. Time-series queries are patterns like "avg CPU over last 1hr, per 5m bucket" — hard to express efficiently in SQL, expensive to aggregate in real-time. Regular tables bloat fast.

**How they solve it:**
- Data is append-only (no updates)
- Automatic downsampling — compact old data (1-second → 1-minute → 1-hour resolution)
- Retention policies — automatically delete data older than X days
- Columnar storage for the value column
- **TimescaleDB** is PostgreSQL + time-series optimizations (hypertables), so you keep SQL query syntax

---

### NoSQL Comparison Table

| Type | Examples | Data Model | Best For | Avoid When |
|------|---------|------------|----------|-----------|
| Key-Value | Redis, DynamoDB | key → blob | Caching, sessions, simple entities | Complex queries, joins |
| Document | MongoDB, Firestore | JSON documents | Flexible schemas, hierarchical data | Strong consistency, complex joins |
| Wide-Column | Cassandra, HBase | Partition key + columns | High-write, time-series, IoT | Ad hoc queries, joins |
| Graph | Neo4j, Amazon Neptune | Nodes + edges | Relationship traversal, fraud, social | Simple tabular data |
| Time-Series | InfluxDB, TimescaleDB | Timestamp + metrics | Monitoring, IoT, analytics | Transactional data |

---

## 3. CAP Theorem

**What it is:** In a distributed system, during a network partition (some nodes can't talk to others), you can only guarantee **two of three**: Consistency, Availability, Partition Tolerance.

**Why this matters:** Every distributed database makes a choice about what to sacrifice when the network misbehaves. Understanding this helps you select the right database and defend your choice in interviews.

---

### The Three Properties

- **Consistency (C):** Every read sees the most recent write (or an error). All nodes agree on the same data at the same moment.
- **Availability (A):** Every request receives a response — not necessarily the latest data, but always a response (no timeouts/errors).
- **Partition Tolerance (P):** The system continues operating even if some messages between nodes are lost or delayed.

---

### The Key Insight: P Is Not Optional

> **You cannot build a useful distributed system without Partition Tolerance.** Networks fail. Nodes go down. Packets get dropped. You don't *choose* P — you accept it as a fact of distributed systems. The real choice is: when a partition happens, do you sacrifice **C** or **A**?

This means CAP is really a binary choice: **CP or AP**.

- **CP (Consistency + Partition Tolerance):** When a partition occurs, some nodes refuse to serve requests to avoid returning stale data. The system becomes partially unavailable. Examples: **HBase, Zookeeper, etcd, MongoDB (by default)**.

- **AP (Availability + Partition Tolerance):** When a partition occurs, all nodes continue serving requests but may return stale data. The system is always available but eventually consistent. Examples: **Cassandra, DynamoDB (default), CouchDB**.

---

### Real-World Mapping

| Database | CAP Choice | Why |
|----------|-----------|-----|
| DynamoDB | AP (default) | Returns cached data during partitions; eventual consistency default |
| Cassandra | AP (tunable) | Can tune to CP with QUORUM reads, but defaults to AP |
| HBase | CP | Built on HDFS + Zookeeper — strong consistency, may reject during partition |
| Zookeeper | CP | Leader election coordination — must be consistent |
| MongoDB | CP (default) | Writes go to primary only; replicas may lag |
| CouchDB | AP | Designed for offline-first sync |

---

### PACELC — The Nuanced Extension

CAP only talks about what happens *during a partition*. Eric Brewer's PACELC extends it: **even without partitions, you still trade off Latency vs Consistency**.

**PACELC reads as:** If Partition (P), choose between Availability (A) and Consistency (C). Else (E), choose between Latency (L) and Consistency (C).

| Database | Partition? | Else? |
|---------|-----------|------|
| DynamoDB | AP | EL (low latency, eventual consistency) |
| Cassandra | AP | EL (configurable) |
| PostgreSQL | CP | EC (prioritizes consistency even at latency cost) |
| Spanner (Google) | CP | EC (uses TrueTime to achieve this with low latency) |

> **Why PACELC matters in interviews:** When a system designer says "we use eventual consistency," they should be asked: "even without partitions?" The answer reveals whether they truly understand the latency-consistency tradeoff they're making on every single request, not just during failures.

**Interview Q&A:**

- **Q: What is the CAP theorem and what does it mean in practice?**

  A: CAP says a distributed system can only guarantee two of Consistency, Availability, and Partition Tolerance simultaneously — but only when a partition occurs. In practice, partition tolerance isn't optional: networks fail, so you must tolerate partitions. The real choice is: when a partition happens, do you stop serving requests to remain consistent (CP), or keep serving requests with potentially stale data (AP)? DynamoDB defaults to AP — every node responds, data may be stale. Zookeeper is CP — it refuses requests during a partition to maintain coordination correctness. In interviews, I'd extend this to PACELC: even without partitions, you're trading latency for consistency on every request. Cassandra with QUORUM reads is slower than ONE, but more consistent. The right choice depends on the domain — financial transactions need CP; social feeds can tolerate AP.

---

## 4. Indexing

**What it is:** A data structure separate from the table that allows the database to find rows without scanning the entire table.

**Why it exists:** Without an index, every query requires a full table scan — O(n) for n rows. An index reduces this to O(log n) for B-tree or O(1) for hash.

**The cost:** Indexes take space and slow down writes (every INSERT/UPDATE/DELETE must update all indexes on that table). This is the fundamental trade-off.

---

### B-Tree Indexes

**The default index type** in PostgreSQL. A balanced binary search tree where leaf nodes contain the actual row pointers.

**How it works:**
- Data is sorted in the index
- A search traverses from root to leaf: O(log n)
- Supports equality (`=`), range (`>`, `<`, `BETWEEN`), prefix LIKE (`'foo%'`)
- Works for composite indexes (multiple columns)

**When it's ideal:** Most general-purpose queries — user lookups, range queries on dates, ORDER BY clauses.

---

### Hash Indexes

**What it is:** A hash table mapping each key value to a row pointer.

**When it's better than B-tree:** Only for equality lookups (`=`). O(1) vs O(log n) for B-tree.

**Critical limitation:** Cannot do range queries (`>`, `<`, `BETWEEN`). Cannot sort. In PostgreSQL, B-tree is almost always preferred because it handles equality AND range queries.

---

### Composite Indexes — Column Order Matters

A composite index on `(a, b, c)` is also usable as an index on `(a)` or `(a, b)`, but **not** on `(b)` or `(b, c)` alone.

```sql
-- Index on (user_id, created_at)
-- This query uses the index:
SELECT * FROM orders WHERE user_id = 5 AND created_at > '2024-01-01';

-- This also uses the index (prefix match on user_id):
SELECT * FROM orders WHERE user_id = 5;

-- This does NOT use the index efficiently (missing leading column):
SELECT * FROM orders WHERE created_at > '2024-01-01';
```

**Rule:** Put the highest-cardinality column first if it appears in most queries. Put equality conditions before range conditions.

---

### Covering Indexes

If all columns needed by a query are in the index, PostgreSQL can answer the query from the index alone — no table access needed. This is called an **index-only scan**.

```sql
-- Table: orders(id, user_id, status, total, created_at)
-- Query: SELECT status, total FROM orders WHERE user_id = 5;
-- Covering index: (user_id, status, total)
-- PostgreSQL never touches the table — reads only from the index
```

This is a significant performance win for read-heavy queries.

---

### Full-Text Indexes vs LIKE Queries

`LIKE '%foo%'` on a regular column is a full table scan — the leading `%` prevents index use.

For full-text search:
- PostgreSQL has built-in `tsvector`/`tsquery` + GIN indexes — good for simple English text search
- Elasticsearch/OpenSearch for complex relevance scoring, multi-field search, autocomplete at scale

```sql
-- Full-text search in PostgreSQL
CREATE INDEX idx_fts ON articles USING GIN(to_tsvector('english', content));
SELECT * FROM articles WHERE to_tsvector('english', content) @@ to_tsquery('postgres & index');
```

---

### When NOT to Index

- **Low cardinality columns** — indexing `status` with 3 possible values ('active', 'inactive', 'deleted') is wasteful. The DB will likely scan the table anyway.
- **Write-heavy tables with few reads** — indexes slow down every INSERT/UPDATE/DELETE.
- **Very small tables** — a full scan of 100 rows is faster than index overhead.
- **Columns never used in WHERE/JOIN/ORDER BY** — the index will never be used.

---

### The N+1 Query Problem

```python
# N+1: fetches 1 query for orders, then N queries for each user
orders = db.query("SELECT * FROM orders LIMIT 100")
for order in orders:
    user = db.query("SELECT * FROM users WHERE id = %s", order.user_id)
```

**Solution:** Use a JOIN or batch fetch:
```sql
SELECT o.*, u.name FROM orders o JOIN users u ON o.user_id = u.id LIMIT 100;
```
An index on `orders.user_id` speeds up the join dramatically.

---

### EXPLAIN ANALYZE

```sql
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 5 AND status = 'pending';
```

Look for:
- `Seq Scan` on large tables → missing index
- `Index Scan` → index found, good
- `Index Only Scan` → covering index, best
- High `rows=` estimate with small actual rows → stale statistics (run `ANALYZE`)
- High `cost=` → expensive operation, candidate for optimization

**Interview Q&A:**

- **Q: What is an index and when should you NOT add one?**

  A: An index is a separate data structure (usually a B-tree) that lets the database find rows without scanning the entire table — trading write overhead and storage for faster reads. You shouldn't add an index when: (1) the column has very low cardinality (like a boolean or 3-value status — the DB may skip the index and scan anyway), (2) the table is write-heavy and rarely read (every write pays index maintenance cost), (3) the table is small enough that a full scan is faster than index overhead, or (4) the column is never used in WHERE/JOIN/ORDER BY clauses. In PostgreSQL, I use EXPLAIN ANALYZE to spot missing indexes — if I see a Seq Scan on a large table for a query I know is frequent, that's the signal to add one.

---

## 5. Database Replication

**What it is:** Keeping copies of the database on multiple servers (replicas), synchronized with the primary.

**Why it exists:** Two reasons: (1) **High availability** — if the primary fails, a replica can be promoted. (2) **Read scaling** — route read queries to replicas, freeing the primary for writes.

---

### Primary-Replica (Master-Slave) Replication

**How it works:**
1. All writes go to the **primary**.
2. Primary writes to its Write-Ahead Log (WAL).
3. Replicas stream the WAL and apply changes.
4. Reads can be served from replicas.

This is the most common setup in production PostgreSQL. AWS RDS, Cloud SQL, and most managed databases support this out of the box.

---

### Synchronous vs Asynchronous Replication

| Mode | How It Works | Latency | Risk |
|------|-------------|---------|------|
| **Synchronous** | Primary waits for replica to confirm write before acknowledging the client | Higher (network RTT to replica) | No data loss on failover |
| **Asynchronous** | Primary acknowledges client immediately; replica catches up in background | Lower | Replica may lag — recent writes can be lost if primary crashes before replica syncs |

**PostgreSQL setting:** `synchronous_standby_names = '*'` enables sync replication. For most apps, async is fine with a small RPO (Recovery Point Objective) risk.

---

### Replication Lag and Read-Your-Writes Consistency

**Replication lag:** The delay between when a write commits on the primary and when it's visible on the replica. Can range from milliseconds to seconds under load.

**Problem:** A user updates their profile, then immediately reads it — if routed to a lagging replica, they see the old profile. This is a bad UX pattern known as a **stale read**.

**Solutions:**
- **Read-your-writes consistency:** Route reads to the primary for a short window after a write (e.g., 1 second, or until the replica confirms it has the write's LSN).
- **Track replica lag:** Most ORMs and connection poolers expose replica lag. Route to primary if lag > threshold.
- **Sticky routing:** For a session that just wrote, pin reads to primary for that session.

---

### Multi-Primary (Active-Active) Replication

**What it is:** Multiple nodes accept writes simultaneously.

**The problem:** If two nodes accept conflicting writes to the same row, you get a **write conflict**. The system must resolve it (last-write-wins, application-level merge, user-visible conflict).

**When to use:** Geographically distributed systems where latency to a single primary is too high (e.g., write from both EU and US data centers). CockroachDB, Google Spanner, and Cassandra handle this via consensus protocols.

**For most systems:** Avoid multi-primary unless you have a strong reason — conflict resolution is complex and error-prone.

---

### Failover

When the primary fails:
1. A replica is promoted to primary.
2. Other replicas repoint to the new primary.
3. Clients reconnect (via a virtual IP or DNS update).

**Tools:** Patroni (PostgreSQL HA), AWS RDS Multi-AZ (automatic failover), PgBouncer (connection pooling with failover routing).

**Interview Q&A:**

- **Q: What's the difference between replication and sharding?**

  A: Replication creates copies of the same data on multiple nodes — it solves availability and read scaling. Every replica has the full dataset. Sharding splits data across multiple nodes — each shard holds a subset of the data. It solves write scaling and storage limits. They're complementary: in a large system, you shard writes across N primary nodes, and each primary has its own replica set for availability. Twitter uses this pattern — tweets are sharded by user ID, and each shard is replicated for HA.

---

## 6. Database Sharding

**What it is:** Horizontally splitting data across multiple database servers (shards), where each shard holds a disjoint subset of the rows.

**Why sharding:** A single database node has physical limits on storage, memory, and write throughput. When you exceed them, you shard. This is one of the hardest engineering problems in backend systems.

---

### Horizontal Sharding vs Vertical Partitioning

| Type | What it does | Example |
|------|-------------|---------|
| **Horizontal sharding** | Splits rows across multiple databases | Users 1-1M on shard 1, 1M-2M on shard 2 |
| **Vertical partitioning** | Splits columns or tables across databases | Orders DB, User DB, Product DB as separate services |

Vertical partitioning is what microservices do naturally (each service owns its DB). Horizontal sharding is for when one service's data outgrows one machine.

---

### Sharding Strategies

#### Range-Based Sharding

Assign rows to shards by a range of the shard key.

```
Shard 1: user_id 1 - 1,000,000
Shard 2: user_id 1,000,001 - 2,000,000
Shard 3: user_id 2,000,001 - 3,000,000
```

**Pros:** Simple. Range queries (get all users in a region) stay on one shard.
**Cons:** Hot spots — if all new signups get sequential IDs, shard 3 gets all writes while shards 1-2 are idle. This is catastrophic for write scaling.

#### Hash-Based Sharding

Apply a hash function to the shard key and mod by the number of shards.

```
shard_id = hash(user_id) % num_shards
```

**Pros:** Even distribution — no hot spots.
**Cons:** Range queries scatter across all shards (scatter-gather problem). Adding a shard requires remapping ~all keys (consistent hashing solves this — see Section 7).

#### Directory-Based Sharding

Maintain a lookup table: `shard_key → shard_id`.

**Pros:** Maximum flexibility — move rows between shards, change strategy without rehashing.
**Cons:** The directory becomes a **single point of failure and bottleneck**. Must be cached heavily (Redis) or replicated. Every query needs a directory lookup.

---

### The Shard Key Decision — The Hardest Part

> **The shard key is the single most important decision in a sharding design. Get it wrong and you'll suffer hot spots, cross-shard queries, or a painful resharding.**

**Good shard key properties:**
1. **High cardinality** — enough distinct values to spread data evenly.
2. **Monotonically non-increasing** — avoid sequential IDs; they concentrate writes on one shard.
3. **Query alignment** — most queries should be resolvable on a single shard.
4. **Immutable** — changing the shard key for a row requires moving it across shards.

**Common examples:**

| System | Bad Shard Key | Good Shard Key | Why |
|--------|--------------|----------------|-----|
| Twitter | timestamp | user_id | Tweets by a user stay together; no hot shard |
| Swiggy | city | restaurant_id or order_id | More granularity; city can be too coarse |
| WhatsApp | user_id | conversation_id | Messages in a conversation stay on one shard |
| Payments | transaction date | user_id or merchant_id | Date concentrates writes on today's shard |

---

### Cross-Shard Queries — The Problem

Once you shard, joins across shards become network calls instead of in-DB joins.

```sql
-- On a single DB, this is a simple JOIN:
SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE u.region = 'IN';

-- With sharding: users may be on shard 1, orders on shard 2.
-- You now need an application-level join: fetch from both, merge in memory.
```

**Mitigations:**
- **Co-location:** If users and orders share the same shard key (user_id), keep both on the same shard.
- **Denormalization:** Embed user data in the orders table to avoid the cross-shard join.
- **Scatter-gather:** Query all shards in parallel, merge results in the application layer (works but is expensive).
- **Analytics:** Move cross-shard analytical queries to a data warehouse (BigQuery, Redshift) that can join across all shards.

---

### Resharding — The Nightmare Scenario

When you add shards, all existing data must be re-partitioned. For a hash-based scheme with `N` shards → `N+1` shards, ~50% of data moves. This is **online resharding** — one of the hardest operations in distributed systems.

**How to avoid it:**
- Over-shard from the start: if you think you'll need 10 shards, use 1000 virtual shards mapped to 10 physical shards. Adding physical nodes just remaps virtual → physical mapping.
- Use consistent hashing (Section 7) to minimize data movement on rebalancing.

**Interview Q&A:**

- **Q: How does database sharding work and what is the hardest part?**

  A: Sharding splits rows across multiple database servers, each holding a subset of data. You pick a shard key, apply a function (range or hash), and route each row to the corresponding shard. The hardest part is the shard key choice. A bad key creates hot spots — one shard gets all the writes while others sit idle. For example, sharding by timestamp means today's shard absorbs all writes. Sharding by user_id distributes evenly but makes multi-user queries scatter across shards. The second hardest part is resharding — when you outgrow N shards and need N+M, you must migrate data while the system is live, which is operationally brutal. Consistent hashing with virtual nodes mitigates this by minimizing the fraction of data that moves when adding nodes.

---

## 7. Consistent Hashing

**What it is:** A hashing scheme that minimizes data movement when nodes are added or removed from a distributed system.

**Why it exists:** Naive modular hashing (`hash(key) % N`) breaks catastrophically when N changes — almost every key maps to a different node, causing a full data reshuffle.

---

### The Problem With Naive Hashing

```
5 nodes: hash(key) % 5 → node assignment
Add 1 node: hash(key) % 6 → ~83% of keys now map to different nodes
```

This means a cache invalidation storm, or in a database context, massive data migration.

---

### How Consistent Hashing Works

**The ring model:**

1. Map node identifiers to positions on a circle (0 to 2^32 − 1) using a hash function.
2. Map each key to a position on the same circle.
3. A key is assigned to the **first node clockwise** from its position on the ring.
4. When a node is added: it takes ownership of a contiguous arc of the ring — only keys in that arc move. The rest are unaffected.
5. When a node is removed: its keys move to the next node clockwise — only that node's keys are affected.

**Result:** Adding or removing one node moves only `1/N` of keys, not `(N-1)/N`.

---

### Virtual Nodes — Why They're Needed

With a small number of real nodes, hashing node IDs to the ring creates uneven distribution (some arcs are longer than others → some nodes hold more data).

**Solution:** Each physical node is assigned multiple positions on the ring (virtual nodes or "vnodes"). The physical node owns data from all its virtual node arcs.

- Amazon DynamoDB uses 128 virtual nodes per physical node
- Cassandra uses 256 virtual tokens per node by default

**Result:** Even distribution even with few physical nodes. When a node leaves, its keys distribute to many remaining nodes (not just one), preventing a single node from becoming hot.

---

### Where Consistent Hashing Is Used

| System | Role |
|--------|------|
| Kafka | Partition assignment across brokers |
| Redis Cluster | Key-to-slot mapping across cluster nodes |
| Cassandra | Token ring for partition distribution |
| CDNs | Route user request to nearest cache server |
| Memcached client libraries | Client-side key routing to cache nodes |
| Load balancers | Sticky routing (same client → same backend) |

**Interview Q&A:**

- **Q: What is consistent hashing and why is it used?**

  A: Consistent hashing solves the problem of distributing keys across nodes in a way that minimizes reshuffling when nodes are added or removed. Naive hashing (`key % N`) remaps almost all keys when N changes — catastrophic for caches and distributed stores. Consistent hashing places both nodes and keys on a circular hash ring. A key maps to the first node clockwise from its hash position. Adding a node only affects keys in one arc of the ring — roughly `1/N` of keys move instead of `(N-1)/N`. Virtual nodes improve uniformity by giving each physical node multiple ring positions. It's used in Cassandra, Redis Cluster, Kafka partition assignment, and CDN routing. The key insight is: the system can rebalance without global reshuffling.

---

## 8. SQL vs NoSQL — The Decision Framework

**Not "which is better" — but "which fits the requirements."** The answer depends on five dimensions. Settle these before choosing a DB.

---

### Decision Matrix

| Dimension | Lean SQL | Lean NoSQL |
|-----------|---------|-----------|
| **Schema** | Stable, well-defined schema | Flexible, evolving, or sparse |
| **Consistency** | Strong ACID required | Eventual consistency acceptable |
| **Scale pattern** | Read-heavy (scale with replicas) | Write-heavy (need horizontal write scale) |
| **Query complexity** | Complex joins, aggregations | Simple key-based or document-scoped lookups |
| **Transaction need** | Multi-row ACID transactions | Single-entity or idempotent operations |

---

### The Hybrid Approach

Real systems use both. The pattern is:
- **SQL for the source of truth** — transactional data, financial records, core entities
- **NoSQL for operational layer** — Redis for caching, Cassandra for high-write events, Elasticsearch for search

**Real examples:**

| Company | SQL Usage | NoSQL Usage |
|---------|-----------|------------|
| Uber | MySQL (trips, drivers) | Cassandra (location history) |
| Instagram | PostgreSQL (users, posts) | Cassandra (feeds, activity) |
| Swiggy | MySQL (orders, restaurants) | Redis (sessions, rate limiting) + Elasticsearch (search) |
| Netflix | MySQL (billing) | Cassandra (viewing history), Elasticsearch (title search) |

---

### Twitter-Like System Schema Design

A classic FAANG interview question. The key insight is that Twitter is **read-heavy** (100:1 read/write ratio), so you optimize for reads.

**Core entities:**

```sql
-- Users
CREATE TABLE users (
  id BIGINT PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  display_name TEXT,
  bio TEXT,
  created_at TIMESTAMP
);

-- Tweets
CREATE TABLE tweets (
  id BIGINT PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  content TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  reply_to_id BIGINT REFERENCES tweets(id),
  retweet_count INT DEFAULT 0,
  like_count INT DEFAULT 0
);

-- Follows
CREATE TABLE follows (
  follower_id BIGINT REFERENCES users(id),
  followee_id BIGINT REFERENCES users(id),
  created_at TIMESTAMP,
  PRIMARY KEY (follower_id, followee_id)
);
```

**The Fan-out problem:** When a celebrity with 10M followers tweets, generating their home feed for all followers naively requires writing 10M records. Solutions:
- **Fan-out on write (push):** Pre-compute feeds. Write the tweet to all followers' feed tables. Read is O(1). Write is expensive.
- **Fan-out on read (pull):** At read time, fetch tweets from all followed users and merge. Read is expensive.
- **Hybrid:** Fan-out on write for normal users (<10k followers). Fan-out on read for celebrities. Twitter uses this.

For storage of tweets: PostgreSQL (with sharding by user_id) for writes, with a Redis-backed feed cache for reads.

**Interview Q&A:**

- **Q: How would you design the database schema for a Twitter-like system?**

  A: Core tables: users, tweets, follows, likes. The key design challenge is the fan-out problem for home feeds. I'd use PostgreSQL sharded by user_id for tweets and users — this keeps a user's data co-located. For home feeds, I'd use a hybrid fan-out: for normal users, pre-write their tweets to all followers' feed tables in Cassandra (partition by follower_id, cluster by tweet_created_at — this makes reading a user's feed a single partition read). For celebrities (10M+ followers), use pull-on-read at query time and merge. Likes and retweet counts are Redis counters, persisted to PostgreSQL asynchronously. Elasticsearch for full-text tweet search. This avoids the N+1 join problem on every feed render.

- **Q: SQL vs NoSQL — how do you decide which to use?**

  A: I evaluate five things: schema stability, consistency requirements, scale pattern, query complexity, and transaction needs. If the data has a well-defined schema, requires multi-row ACID transactions (payments, bookings), and needs complex joins — SQL. If the schema is flexible, writes need to scale horizontally (millions per second), and queries are key-based lookups — NoSQL. In practice, most systems use both: PostgreSQL as the transactional source of truth, Redis for caching, Cassandra for high-write event data, Elasticsearch for search. The mistake is treating this as "SQL OR NoSQL" instead of "SQL AND the right NoSQL for each access pattern."

---

## 9. Object Storage

**What it is:** A storage system that stores data as discrete objects (files + metadata + unique ID), accessible via HTTP APIs (typically S3-compatible). Not a filesystem, not a block device.

**Why it exists / What problem it solves:** Traditional file systems don't scale to petabytes and aren't designed for concurrent access from thousands of services. Object storage is infinitely scalable (in practice), cheap, and accessible via simple HTTP PUT/GET.

---

### Storage Type Comparison

| Type | Abstraction | Examples | Use Cases |
|------|------------|---------|-----------|
| **Block Storage** | Raw disk blocks, mounted as volumes | AWS EBS, GCP Persistent Disk | OS boot volumes, databases requiring IOPS |
| **File Storage** | Hierarchical filesystem | AWS EFS, NFS | Shared filesystems, legacy app dependencies |
| **Object Storage** | Flat namespace, key → object | S3, GCS, Cloudflare R2, MinIO | Images, videos, backups, ML weights, logs |

---

### Why S3-Compatible APIs Won

Amazon S3 defined the API standard (PUT, GET, DELETE, multipart upload, presigned URLs). Almost every object storage system — GCS, Cloudflare R2, MinIO, Backblaze — supports the same API. This means you can write code against the S3 SDK and switch providers with a config change.

---

### Pre-Signed URLs

Allow clients to directly upload/download objects from object storage without routing through your backend server.

**Upload flow without pre-signed URLs (bad):**
```
Client → Your API → S3  (your server is a proxy, burns bandwidth and CPU)
```

**Upload flow with pre-signed URLs (correct):**
```
1. Client → Your API: "I want to upload a profile photo"
2. Your API → S3: Generate a pre-signed PUT URL (expires in 5 minutes)
3. Your API → Client: "Here's the pre-signed URL"
4. Client → S3: PUT (directly, securely, with size and type limits)
5. Client → Your API: "I uploaded it, here's the object key"
```

This pattern keeps your servers stateless and reduces bandwidth costs dramatically. Deepta AI likely uses this (or should) for any document/photo uploads from students.

---

### Object Storage vs Database vs File System

| Factor | Object Storage | Database | File System |
|--------|--------------|---------|------------|
| For large blobs (images, video) | ✅ | ❌ (DB bloat) | ⚠️ (doesn't scale) |
| For structured queryable data | ❌ | ✅ | ❌ |
| For shared mounts between services | ❌ | ❌ | ✅ (NFS/EFS) |
| Infinite scale | ✅ | ❌ | ❌ |
| HTTP-native access | ✅ | ❌ | ❌ |

**Rule:** Store large blobs in object storage; store metadata (filename, size, owner, object key) in your PostgreSQL DB.

---

### Lifecycle Policies and Versioning

**Lifecycle policies:** Automatically transition objects between storage tiers or delete old objects.
- Move objects older than 30 days to cheaper "cold" storage (S3 Glacier, GCS Nearline)
- Delete log objects after 90 days

**Versioning:** Retains every version of an object. Deleted objects are soft-deleted (can recover). Useful for audit trails, accidental deletion recovery.

**Multi-region replication:** Automatically copy objects to another region for DR or latency reduction.

---

## 10. Search Engines (Elasticsearch / OpenSearch)

**What it is:** A distributed search and analytics engine built on Apache Lucene, designed for full-text search, log analytics, and autocomplete at scale.

**Why you can't use a regular DB for full-text search at scale:** SQL `LIKE '%keyword%'` is a full table scan — O(n) with no index support for infix matches. Even PostgreSQL's `tsvector` GIN index works for moderate scale, but ranking relevance, multi-field search, fuzzy matching, and faceted filtering push the limits quickly.

---

### The Inverted Index

The fundamental data structure powering full-text search.

**How it works:**
- For each document, tokenize its text into terms: "Swiggy delivers food fast" → ["swiggy", "delivers", "food", "fast"]
- For each term, maintain a list of document IDs that contain it
- At query time: "food AND fast" → intersect the two posting lists

```
term: "food"    → [doc1, doc3, doc7, doc42]
term: "fast"    → [doc3, doc7, doc99]
intersection    → [doc3, doc7]
```

Posting lists also store term frequency (for relevance ranking) and positions (for phrase matching). This is O(1) per term lookup + O(k) merge, where k is the result set size — far faster than full table scans.

---

### Elasticsearch Architecture

- **Document:** A JSON object, analogous to a row
- **Index:** A collection of documents with a mapping (schema), analogous to a table
- **Shard:** An index is split into shards (Lucene instances). Each shard is an independent search engine.
- **Replica shard:** A copy of a primary shard, for HA and read scaling

When you query an index with 5 shards, Elasticsearch queries all 5 in parallel and merges results — this is the scatter-gather pattern applied to search.

---

### When to Use Elasticsearch

| Use Case | Why ES |
|----------|--------|
| Full-text product/content search | Inverted index, relevance scoring |
| Log analytics (ELK stack) | Fast ingestion, aggregations over time |
| Autocomplete | Edge N-gram tokenization |
| Geospatial queries | Geo-distance filters |
| Faceted search (filter by category + price + rating) | Aggregations + filters |

---

### Syncing Elasticsearch With Your Primary DB

Elasticsearch is **not** a primary database — it's eventually consistent, doesn't support ACID transactions, and is optimized for reads, not the source of truth.

**Common sync strategies:**

| Strategy | How | Trade-offs |
|----------|-----|-----------|
| **Dual-write** | Application writes to DB and ES simultaneously | Simple, but failure in one leaves them inconsistent |
| **CDC (Change Data Capture)** | Debezium reads PostgreSQL WAL and streams changes to ES via Kafka | Reliable, decoupled, slight lag |
| **Kafka consumer** | App publishes events to Kafka; a consumer writes to ES | Decoupled, replayable, standard pattern |
| **Batch sync** | Periodic full or incremental export from DB to ES | Simple, high lag, not real-time |

**Recommended pattern for production:** CDC with Kafka. Debezium watches the PostgreSQL WAL, publishes change events to Kafka, and an Elasticsearch consumer applies them. Lag is typically < 1 second; events are replayable if ES goes down.

**Interview Q&A:**

- **Q: How would you design a system that needs full-text search?**

  A: Full-text search at scale requires an inverted index — standard SQL can't do it efficiently. I'd keep PostgreSQL as the source of truth for structured data, and sync a subset of fields to Elasticsearch for search. For sync, I'd use CDC: Debezium captures PostgreSQL WAL changes, publishes to Kafka, and an Elasticsearch consumer applies them — usually under 1 second of lag. For the search API, queries hit Elasticsearch directly. Important caveats: Elasticsearch is eventually consistent (stale results possible), isn't ACID, and shouldn't store anything not replicated from the primary DB. For Swiggy-style restaurant search, I'd index restaurant name, cuisine tags, location (geo-point), and rating into ES. Autocomplete uses an edge N-gram analyzer on the name field.

---

## 11. Data Modelling Fundamentals

**What it is:** The process of defining how data is structured, stored, and related — the foundation of every database design.

---

### Normalization vs Denormalization

**Normalization:** Eliminate redundancy by splitting data into separate tables with foreign key references. Every piece of data lives in one place.

| Form | Rule |
|------|------|
| 1NF | No repeating groups; each cell is atomic |
| 2NF | No partial dependency on composite PK |
| 3NF | No transitive dependency (non-key column depends only on PK) |

**Benefits:** No update anomalies (update a user's name in one place). Storage efficiency.

**Denormalization:** Deliberately duplicate data to avoid expensive joins. Accept redundancy for read performance.

**When to denormalize:**
- Read-heavy systems where join cost dominates
- Data that changes rarely (e.g., embedding a user's name into order records)
- NoSQL systems where joins aren't possible (required in Cassandra, DynamoDB)
- Reporting / analytics tables (OLAP — wide denormalized fact tables are the norm)

---

### Relationship Modelling

**1:1 (One to One):**
```sql
-- User has one profile
CREATE TABLE user_profiles (
  user_id BIGINT PRIMARY KEY REFERENCES users(id),
  bio TEXT,
  avatar_url TEXT
);
```

**1:N (One to Many):**
```sql
-- One restaurant has many menu items
CREATE TABLE menu_items (
  id BIGINT PRIMARY KEY,
  restaurant_id BIGINT NOT NULL REFERENCES restaurants(id),
  name TEXT,
  price NUMERIC(10,2)
);
-- Index restaurant_id for fast fetch-all-by-restaurant
CREATE INDEX idx_menu_restaurant ON menu_items(restaurant_id);
```

**N:N (Many to Many):** Use a junction table.
```sql
-- Orders can have many items; items appear in many orders
CREATE TABLE order_items (
  order_id BIGINT REFERENCES orders(id),
  menu_item_id BIGINT REFERENCES menu_items(id),
  quantity INT,
  unit_price NUMERIC(10,2),  -- snapshot price at order time, NOT a foreign key to current price
  PRIMARY KEY (order_id, menu_item_id)
);
```

> **Key insight:** In `order_items`, store `unit_price` as a snapshot, not as a reference to the current price. If you update the menu price, historical order totals must not change. This is a common data modelling mistake.

---

### Embedding vs Referencing in Document Stores

In MongoDB/Firestore, you choose between embedding sub-documents or referencing them by ID.

**Embed when:**
- The sub-document is owned by the parent (address in a user document)
- You always fetch them together
- The sub-document doesn't change independently at high frequency

**Reference when:**
- The sub-document is shared across many parents (e.g., a product referenced by many orders)
- The sub-document is large and often not needed
- The relationship is N:N

```json
// Embedding (good for address):
{
  "user_id": 1,
  "name": "Gautham",
  "address": { "city": "Hyderabad", "pin": "500001" }
}

// Referencing (good for shared product):
{
  "order_id": 99,
  "items": [{ "product_id": "prod_42", "qty": 2 }]
}
```

---

### Enum vs Foreign Key

Classic Indian unicorn interview topic. Should `order.status` be an enum or a foreign key to a `statuses` table?

| Approach | Pros | Cons |
|----------|------|------|
| **Enum (DB-level)** | Fast (no join), enforced by DB | Changing values requires `ALTER TABLE` (expensive on large tables) |
| **VARCHAR + CHECK constraint** | Simpler schema | No type safety at DB level |
| **Foreign key to statuses table** | Easy to add new statuses, add metadata (description, display name) | Requires JOIN; overkill for stable enumerations |
| **Application-level constant** | Flexible | No DB enforcement, risk of invalid values |

**Rule of thumb:** Use a DB enum or CHECK constraint for truly stable, small sets (e.g., `gender`, `payment_method`). Use a foreign key lookup table when the set grows, needs metadata, or is managed by non-engineers (e.g., `order_status`, `onboarding_stage`). For Deepta AI's onboarding stages — a lookup table is the right call: stages are managed by business logic and will evolve.

---

### Swiggy Order Management Data Model

**Interview Q&A:**

- **Q: Design the data model for Swiggy's order management system.** *(Indian unicorn style)*

  A:

```sql
-- Core entities
CREATE TABLE customers (
  id BIGINT PRIMARY KEY,
  phone VARCHAR(15) UNIQUE NOT NULL,
  name TEXT,
  created_at TIMESTAMP
);

CREATE TABLE restaurants (
  id BIGINT PRIMARY KEY,
  name TEXT NOT NULL,
  city VARCHAR(50),
  lat FLOAT, lng FLOAT,
  is_active BOOLEAN DEFAULT true
);

CREATE TABLE menu_items (
  id BIGINT PRIMARY KEY,
  restaurant_id BIGINT REFERENCES restaurants(id),
  name TEXT,
  price NUMERIC(10,2),
  is_available BOOLEAN,
  category TEXT
);

CREATE TABLE delivery_agents (
  id BIGINT PRIMARY KEY,
  name TEXT,
  phone VARCHAR(15),
  city VARCHAR(50),
  is_available BOOLEAN
);

-- Order lifecycle
CREATE TABLE orders (
  id BIGINT PRIMARY KEY,
  customer_id BIGINT REFERENCES customers(id),
  restaurant_id BIGINT REFERENCES restaurants(id),
  agent_id BIGINT REFERENCES delivery_agents(id),
  status TEXT CHECK (status IN ('placed','accepted','preparing','picked_up','delivered','cancelled')),
  total_amount NUMERIC(10,2),
  delivery_address JSONB,           -- snapshot of address at order time
  placed_at TIMESTAMP,
  delivered_at TIMESTAMP
);

CREATE TABLE order_items (
  order_id BIGINT REFERENCES orders(id),
  menu_item_id BIGINT REFERENCES menu_items(id),
  quantity INT,
  unit_price NUMERIC(10,2),         -- snapshot of price at order time
  PRIMARY KEY (order_id, menu_item_id)
);

CREATE TABLE order_status_history (
  id BIGINT PRIMARY KEY,
  order_id BIGINT REFERENCES orders(id),
  status TEXT,
  changed_at TIMESTAMP,
  changed_by TEXT                   -- 'customer', 'restaurant', 'system'
);
```

Key design decisions: `unit_price` snapshot in `order_items` (price changes shouldn't affect historical orders). `delivery_address` as JSONB (snapshot, not FK to address table — customer may move). Status history as a separate table (audit trail, no destructive updates to orders). `order_status_history` is append-only — never update or delete rows. Sharding: shard `orders` by `customer_id` for user-facing APIs, or by `restaurant_id` for restaurant-facing APIs — pick based on dominant access pattern.

---

## 12. Database Connection Pooling

**What it is:** A pool of pre-established database connections reused across application requests, rather than opening a new connection per request.

**Why raw connections are expensive:** Opening a TCP connection + TLS handshake + PostgreSQL authentication + process fork on the DB side takes ~10–50ms. For a high-throughput service, this adds up catastrophically. PostgreSQL also has a hard limit on concurrent connections (default: 100, configurable to ~5000 with memory cost).

---

### How Connection Pools Work

A connection pooler (PgBouncer, HikariCP) maintains N persistent connections to PostgreSQL. When an application request needs a DB connection:
1. Borrow an idle connection from the pool
2. Execute the query
3. Return the connection to the pool (not closed — reused)

This amortizes the connection setup cost. 100 app instances each with 10 pool connections = 1000 connections to Postgres, not 1 per request (which could be 10,000+).

---

### PgBouncer Modes

| Mode | How It Works | Best For |
|------|-------------|---------|
| **Session pooling** | One server conn per client session | Lowest compatibility risk |
| **Transaction pooling** | Server conn released after each transaction | Best for stateless apps — most efficient |
| **Statement pooling** | Released after each statement | Rarely used; breaks multi-statement transactions |

**Transaction pooling is the recommended mode** for most Go/Python microservices with short-lived transactions.

---

### Pool Size Formula

From the HikariCP documentation (derived from empirical benchmarks):

```
pool_size = (core_count × 2) + effective_spindle_count
```

- `core_count`: physical CPU cores on the DB server
- `effective_spindle_count`: number of disk spindles (1 for SSD)

For a 4-core DB server with SSD: `pool_size = (4 × 2) + 1 = 9`

**Counterintuitive truth:** More connections than this formula suggests often makes performance *worse* — threads contend on locks, and the PostgreSQL process manager overhead grows. This is especially true for OLTP workloads. Start here, tune up carefully.

---

### Connection Pool Exhaustion

When all connections in the pool are busy and a new request arrives:
- **Queue the request** — wait for a connection to free up (configurable timeout)
- **Fail fast** — return an error immediately if queue is full

**Symptoms:** `HikariPool connection timeout`, requests queuing, p99 latency spikes.

**Solutions:**
- Identify slow queries holding connections too long (EXPLAIN ANALYZE)
- Increase pool size (within the formula bounds)
- Add PgBouncer in front of PostgreSQL if connection count is the bottleneck
- Ensure transactions are as short as possible (don't do HTTP calls inside DB transactions)

---

## Quick Revision Cheatsheet

**SQL / ACID:**
- Atomicity = all or nothing; Consistency = valid state always; Isolation = transactions don't see each other mid-flight; Durability = committed = on disk
- Isolation levels: Read Uncommitted → Read Committed (PG default) → Repeatable Read (MySQL default) → Serializable
- MVCC = no read locks in PostgreSQL; readers and writers don't block each other; dead tuples cleaned by VACUUM

**NoSQL Types:**
- Key-Value (Redis, DynamoDB): caching, sessions, simple lookups
- Document (MongoDB): flexible schema, hierarchical data
- Wide-Column (Cassandra): high-write, time-series — writes are appends to SSTable
- Graph (Neo4j): relationship traversal — fraud, social graphs
- Time-Series (InfluxDB, TimescaleDB): metrics, IoT — auto-downsample + retention

**CAP Theorem:**
- P is not optional — networks partition; real choice is C vs A
- CP: consistent but may reject during partition (Zookeeper, HBase, MongoDB)
- AP: always available but may return stale data (Cassandra, DynamoDB)
- PACELC: even without partitions, you choose Latency vs Consistency on every request

**Indexing:**
- B-tree = default, supports equality + range; Hash = equality only, O(1)
- Composite index: leading column must appear in WHERE clause
- Covering index = index-only scan, no table access
- Don't index: low-cardinality columns, write-heavy tables with rare reads
- Spot missing index via EXPLAIN ANALYZE → Seq Scan on large table = bad

**Replication:**
- Primary → replicas via WAL streaming
- Sync replication: no data loss, higher latency; Async: lower latency, small data loss window
- Replication lag → stale reads → read-your-writes pattern to mitigate
- Multi-primary: solves geo-write latency, adds write conflict complexity

**Sharding:**
- Shard key decision is the hardest part — high cardinality, query-aligned, immutable
- Range sharding: simple, hot spots; Hash sharding: even, breaks range queries
- Cross-shard joins require scatter-gather or denormalization
- Resharding = massive operational pain; over-shard early + virtual shards to mitigate

**Consistent Hashing:**
- Ring model: key maps to first node clockwise
- Adding/removing one node → only 1/N keys move
- Virtual nodes: each physical node owns multiple ring positions → even distribution
- Used in: Cassandra, Redis Cluster, Kafka, CDNs

**SQL vs NoSQL:**
- SQL: stable schema, ACID transactions, complex joins, financial data
- NoSQL: schema flexibility, horizontal write scale, simple access patterns
- Real systems use both — don't treat it as either/or

**Object Storage:**
- S3-compatible = the standard API (GCS, R2, MinIO all compatible)
- Pre-signed URLs: client uploads directly to S3, server never proxies the bytes
- Store blobs in object storage, metadata in PostgreSQL

**Elasticsearch:**
- Inverted index: term → list of doc IDs — makes text search O(1) per term
- Not a primary DB: eventually consistent, no ACID
- Sync from PostgreSQL via CDC (Debezium + Kafka) — sub-second lag, replayable

**Data Modelling:**
- Normalization = no redundancy, easy updates; Denormalization = redundancy for read speed
- Snapshot prices in order_items — historical orders must not be affected by price changes
- Enum vs FK: use enum/check for stable small sets; FK lookup table for evolving business-managed enumerations
- Embedding in MongoDB: for owned, always-together data; Referencing: for shared or large sub-documents

**Connection Pooling:**
- Pool size formula: `(cores × 2) + spindles` — more is not always better
- PgBouncer transaction mode: most efficient for stateless OLTP services
- Connection exhaustion symptom: p99 spikes, timeout errors — fix slow queries first, then tune pool

---

*Track 2 complete. Next: Track 3 — Networking & Communication (REST, gRPC, WebSockets, GraphQL, API design).*
