# Part 6.1: Database Fundamentals

## What You'll Learn

- The SQL vs NoSQL decision framework — how to choose the right database for the job
- ACID properties in depth — what each one guarantees, how it works internally
- Connection pooling — why it exists, how to size it, what pool exhaustion looks like
- Database schema design — normalization, denormalization, soft deletes, audit tables
- Full implementations in Go (pgx), Node.js (pg/Prisma), Python (SQLAlchemy/asyncpg)

---

## Table of Contents

1. [SQL vs NoSQL Decision Framework](#1-sql-vs-nosql-decision-framework)
   - 1.1 When to Use PostgreSQL
   - 1.2 When to Use MongoDB
   - 1.3 When to Use Redis
   - 1.4 When to Use Elasticsearch
   - 1.5 Polyglot Persistence
   - 1.6 Decision Table
2. [ACID Properties (Deep)](#2-acid-properties-deep)
   - 2.1 Atomicity
   - 2.2 Consistency
   - 2.3 Isolation
   - 2.4 Durability
   - 2.5 What NoSQL Gives Up
3. [Connection Pooling](#3-connection-pooling)
   - 3.1 Why It Exists
   - 3.2 Pool Sizing Formula
   - 3.3 Pool Exhaustion
   - 3.4 Connection Lifecycle
   - 3.5 PgBouncer
4. [Database Schemas](#4-database-schemas)
   - 4.1 Normalization (1NF → 3NF)
   - 4.2 Denormalization
   - 4.3 Foreign Keys and Referential Integrity
   - 4.4 Soft Deletes vs Hard Deletes
   - 4.5 Audit Tables
5. [Implementation Examples](#5-implementation-examples)
   - Go + pgx
   - Node.js + pg
   - Python + SQLAlchemy (asyncpg)
6. [Common Patterns & Best Practices](#common-patterns--best-practices)
7. [Common Pitfalls](#common-pitfalls)
8. [Interview Questions & Answers](#interview-questions--answers)
9. [Resources](#resources)

---

## 1. SQL vs NoSQL Decision Framework

The single most common interview question about databases is "when would you use SQL vs NoSQL?" The honest answer is that PostgreSQL should be your default choice for most backend applications. Move away from it only when you have a specific, justified reason.

> **Data point:** In the 2025 Stack Overflow Developer Survey, PostgreSQL was used by 58.2% of professional developers — more than any other database.

### 1.1 When to Use PostgreSQL (SQL)

Choose PostgreSQL when:

- **Structured data with known schema** — users, orders, products, invoices
- **Complex relationships** — foreign keys, JOINs across multiple entities
- **ACID required** — financial transactions, inventory, anything where partial writes are catastrophic
- **Complex querying** — aggregate reports, multi-table JOINs, window functions, CTEs
- **Strong consistency required** — you need reads to see the latest committed write
- **You're unsure** — PostgreSQL handles surprisingly large scale (100M+ rows, billions with partitioning) before you need to look elsewhere

**Strengths of PostgreSQL you should mention in interviews:**
- JSONB column type — stores and indexes JSON; blurs the SQL/NoSQL line
- Full-text search (tsvector/tsquery) — good enough for many search use cases
- Row-level security — policy-based access control at the database layer
- Logical replication, partitioning, read replicas
- MVCC (Multi-Version Concurrency Control) — readers never block writers

### 1.2 When to Use MongoDB (NoSQL / Document)

Choose MongoDB when:

- **Flexible/evolving schema** — product catalogs with different attributes per category, CMS content
- **Hierarchical document data** — data that naturally nests (blog post with comments, embedded addresses)
- **Horizontal write scaling** — sharding across many nodes (though PostgreSQL with Citus handles this too)
- **Schema-per-tenant** — multi-tenant SaaS where each tenant has different fields

**What MongoDB sacrifices:**
- No multi-document ACID transactions by default (4.0+ added them but with limitations)
- No JOINs — you either embed or do application-level joins
- Schema flexibility can become schema chaos without discipline

**When people choose MongoDB but shouldn't:**
- "We might need a flexible schema" — premature optimization; PostgreSQL JSONB handles this
- "We need to scale" — at most startup/mid-size scale, PostgreSQL with a read replica handles millions of users

### 1.3 When to Use Redis

Redis is an in-memory data structure store. Use it for:

| Use Case | Pattern |
|----------|---------|
| **Session storage** | `SET session:{token} {user_json} EX 3600` |
| **Caching** | Cache DB query results with TTL |
| **Rate limiting** | `INCR rate:{ip} EX 60` |
| **Pub/Sub** | Real-time notifications, event fan-out |
| **Distributed locks** | Redlock algorithm |
| **Leaderboards** | Sorted sets (`ZADD`, `ZRANK`) |
| **Job queues** | BullMQ (Node), asynq (Go), Celery (Python) |

**What Redis is NOT:**
- Not a primary database — data can be lost on restart (unless RDB/AOF persistence is configured)
- Not for complex queries — it's key-based access, not relational

### 1.4 When to Use Elasticsearch

Use Elasticsearch when:

- **Full-text search** with relevance scoring, fuzzy matching, synonyms, autocomplete
- **Log analytics** — the ELK stack (Elasticsearch, Logstash, Kibana)
- **Time-series analytics** — aggregations over large datasets with complex filters
- **Faceted search** — e-commerce product search with multiple filter dimensions

**What Elasticsearch is NOT:**
- Not a source of truth — it's a search index over data that lives in your primary DB
- Not ACID — eventual consistency, no transactions
- Operationally complex — sharding, mapping management, JVM tuning

### 1.5 Polyglot Persistence

Large systems use multiple databases, each for what it does best:

```
                   ┌─────────────────────────────────────────┐
                   │           Application Layer             │
                   └────┬──────────┬──────────┬─────────────┘
                        │          │          │
              ┌─────────▼──┐  ┌────▼────┐  ┌─▼────────────┐
              │ PostgreSQL │  │  Redis  │  │Elasticsearch │
              │            │  │         │  │              │
              │ Users      │  │Sessions │  │Product search│
              │ Orders     │  │Cache    │  │Log analytics │
              │ Payments   │  │RateLimit│  │Audit trail   │
              │ Products   │  │PubSub   │  │search        │
              └────────────┘  └─────────┘  └──────────────┘
```

The cost of polyglot persistence: operational complexity. Each database has its own backup strategy, scaling model, monitoring, and expertise requirement. Don't add a new database unless the benefit clearly outweighs this cost.

### 1.6 Decision Table: Access Pattern → Database Choice

| Access Pattern | Best Choice | Why |
|----------------|-------------|-----|
| Complex relational queries with JOINs | PostgreSQL | Native JOIN support, query planner |
| Read a single document by ID | PostgreSQL or MongoDB | Both handle this fine |
| Full-text search with ranking | Elasticsearch or PG full-text | ES for complex; PG for simple |
| Cache a computation result | Redis | In-memory, TTL-native |
| Store user session state | Redis | Fast access, automatic expiry |
| High-cardinality time-series metrics | InfluxDB / TimescaleDB | Purpose-built for time-series |
| Flexible schema per record | MongoDB or PG JSONB | Both work; PG preferred if relational needs exist |
| Geospatial queries | PostgreSQL + PostGIS | Best-in-class spatial support |
| Graph traversal (social network) | Neo4j or PG recursive CTEs | Neo4j for complex graphs |
| Write-heavy append-only log | Kafka / Cassandra | Designed for sequential writes |

---

## 2. ACID Properties (Deep)

ACID is the set of properties that guarantee database transactions are processed reliably. Understanding each property at the implementation level is critical for senior interviews.

```
A — Atomicity     : All operations in a transaction succeed, or none do
C — Consistency   : A transaction brings the database from one valid state to another
I — Isolation     : Concurrent transactions don't interfere with each other
D — Durability    : Committed transactions survive crashes
```

### 2.1 Atomicity

**What it guarantees:** A transaction is an all-or-nothing unit. If any statement in the transaction fails, all preceding changes are undone (rolled back).

**How it works internally:**

PostgreSQL implements atomicity via an **undo log** (logically; technically via MVCC and the transaction status in `pg_clog`/`pg_xact`). When you start a transaction, every change is tagged with your transaction ID (XID). If the transaction aborts, those row versions are marked as invalid and become invisible to future reads.

```
BEGIN;
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;  -- debit
  UPDATE accounts SET balance = balance + 100 WHERE id = 2;  -- credit
COMMIT;
```

If the second UPDATE fails (e.g., account 2 doesn't exist), the first UPDATE is rolled back. The database is never in a state where account 1 is debited but account 2 is not credited.

**Savepoints — partial rollback:**

```sql
BEGIN;
  INSERT INTO orders (id, user_id, total) VALUES (1, 42, 100.00);
  SAVEPOINT order_created;

  INSERT INTO order_items (order_id, product_id, qty) VALUES (1, 7, 2);
  SAVEPOINT items_added;

  -- This fails (invalid product)
  INSERT INTO order_items (order_id, product_id, qty) VALUES (1, 999, 1);

  -- Roll back only to the savepoint, keeping the order and first item
  ROLLBACK TO SAVEPOINT items_added;

COMMIT; -- commits the order + first item only
```

Savepoints are useful when you want to attempt risky operations within a transaction without aborting the entire unit of work.

### 2.2 Consistency

**What it guarantees:** A transaction can only bring the database from one valid state to another valid state. It cannot leave data in a state that violates defined invariants.

**How it's enforced:**

Consistency is maintained through database constraints:

| Constraint Type | Example |
|----------------|---------|
| NOT NULL | `email TEXT NOT NULL` — email can never be null |
| UNIQUE | `UNIQUE(email)` — no two users share an email |
| CHECK | `CHECK (price > 0)` — price must be positive |
| FOREIGN KEY | `REFERENCES users(id)` — referenced user must exist |
| TRIGGER | Custom logic (e.g., balance can never go negative) |
| Domain type | `CREATE DOMAIN positive_int AS INT CHECK (VALUE > 0)` |

If a transaction violates any constraint, it is rolled back and the database remains in its previous valid state.

```sql
-- This transaction fails because of the CHECK constraint
BEGIN;
  INSERT INTO products (name, price) VALUES ('Widget', -10.00);
  -- ERROR: new row for relation "products" violates check constraint "products_price_check"
ROLLBACK; -- automatic on constraint violation
```

**Note:** Consistency in ACID is application-defined (you set the constraints). The database enforces them; you define what "valid" means.

### 2.3 Isolation

**What it guarantees:** Concurrent transactions execute as if they were serial (one after the other), at some level.

This is the most nuanced ACID property. It has four levels (covered in depth in Part 6.2), but briefly:

- **Read Uncommitted**: Can see uncommitted changes from other transactions (dirty reads)
- **Read Committed**: Only see committed changes (default in PostgreSQL)
- **Repeatable Read**: Re-reading the same row gives the same result within a transaction
- **Serializable**: Full serializability — results are equivalent to some serial execution order

**PostgreSQL's default is Read Committed.** Most applications run here, which means two reads of the same row in the same transaction can return different values if another transaction commits between them.

### 2.4 Durability

**What it guarantees:** Once a transaction commits, it stays committed even if the system crashes immediately after.

**How it works — Write-Ahead Logging (WAL):**

```
PostgreSQL Durability Stack
────────────────────────────────────────────────────────────
                                                            
  Application                                              
       │                                                    
       │ COMMIT                                             
       ▼                                                    
  PostgreSQL Process                                        
       │                                                    
       │ 1. Write change to WAL buffer (in memory)          
       │ 2. fsync() WAL buffer to WAL file on disk          
       │    (this is what makes it durable)                 
       │ 3. Return "commit successful" to client            
       │                                                    
       │ (later, async)                                     
       │ 4. Checkpoint: write dirty pages from             
       │    shared_buffers to actual data files             
       ▼                                                    
  Disk                                                      
  ├── WAL files (pg_wal/) — sequential writes, very fast   
  └── Data files (base/) — random writes, written lazily   
```

**The key insight:** When you commit, PostgreSQL only guarantees that the WAL is flushed to disk (`fsync`). The actual data files may still be in memory. If the server crashes after a commit:

1. PostgreSQL restarts and reads the WAL
2. It replays any WAL records not yet reflected in data files (redo)
3. It rolls back any uncommitted transactions (undo)

This is why WAL enables durability without every write being a full data-file write (which would be catastrophically slow for random I/O).

**fsync = true (never turn this off in production):**

Setting `fsync = off` in `postgresql.conf` makes writes ~10x faster but makes commits not durable. A power failure can corrupt the entire database cluster. This is tempting for development but catastrophic in production.

**What about cloud databases?**

AWS RDS, Google Cloud SQL, and similar managed databases handle WAL and durability for you, and write WAL to multiple availability zones before confirming a commit. This provides durability even against entire AZ failures.

### 2.5 What NoSQL Gives Up

Different NoSQL systems make different trade-offs:

| Database | What ACID Properties It Gives Up | Why |
|----------|----------------------------------|-----|
| **MongoDB (before 4.0)** | Atomicity across documents, Isolation | Document-level atomicity only; no multi-doc transactions |
| **MongoDB (4.0+)** | Full Serializable isolation not default | Performance; transactions are opt-in |
| **Cassandra** | Atomicity across partitions, Isolation, strong Consistency | Designed for AP (Available, Partition-tolerant) — prioritizes availability over consistency |
| **Redis** | Durability (default) | In-memory; data loss on restart unless persistence configured |
| **DynamoDB** | Strong Consistency (default is eventual) | Globally distributed; eventual consistency is the performance default |
| **Elasticsearch** | All four (it's a search index, not a primary store) | Not designed for transactional workloads |

**CAP Theorem context:**

```
        Consistency (C)
           /\
          /  \
         /    \
        /  CA  \   ← Traditional RDBMS (PostgreSQL, MySQL)
       /        \   (partition tolerance sacrificed — single node assumed)
      /____CA____\
     /     |      \
    / CP   |   AP  \
   /       |        \
Partition  |  Availability
Tolerance (P)

CP: Consistent + Partition Tolerant (HBase, ZooKeeper, Etcd)
    → Choose consistency; become unavailable during partition

AP: Available + Partition Tolerant (Cassandra, DynamoDB, CouchDB)
    → Stay available; accept stale/inconsistent reads during partition
```

> **Interview answer on CAP:** CAP is a theoretical model. In practice, network partitions are rare but unavoidable at scale. Most databases let you tune the C-A trade-off per operation (e.g., DynamoDB's `ConsistentRead` parameter). PostgreSQL with synchronous replication prioritizes C over A.

---

## 3. Connection Pooling

### 3.1 Why It Exists

Every PostgreSQL connection is an operating system process (~5-10MB RAM). Establishing a TCP connection + authentication handshake takes 5-50ms. If every HTTP request created and destroyed a DB connection, your application would be crushingly slow and your DB would run out of processes quickly.

```
Without connection pooling:
HTTP Request → TCP connect (5ms) → TLS handshake → auth → query → TCP close

With connection pooling:
HTTP Request → acquire idle connection (< 1ms) → query → return connection to pool
```

A typical PostgreSQL instance can handle 100–500 connections before it runs out of memory and process table entries. An application with 50 pods, each holding 20 connections, uses 1000 connections — already past the PostgreSQL limit.

**The solution:** A connection pool (or a proxy like PgBouncer) maintains a fixed number of long-lived connections to the database and hands them to application threads/goroutines on demand.

### 3.2 Pool Sizing Formula

The most widely cited formula (from the HikariCP team / Brian Goetz):

```
pool_size = (number_of_cores * 2) + effective_spindle_count
```

Where:
- `number_of_cores` = CPU cores available to the database server
- `effective_spindle_count` = number of physical hard disks (1 for SSD, irrelevant for cloud)

**Why this formula?** A connection can be:
1. Executing a query (CPU-bound)
2. Waiting for disk I/O
3. Waiting for network I/O

With `cores * 2` connections, you can have one connection per core executing + one per core waiting for I/O. Adding more connections doesn't increase throughput; it only adds context-switching overhead and memory consumption.

**Practical examples:**

| Server | Cores | SSDs | Formula Result | Recommended Pool |
|--------|-------|------|----------------|-----------------|
| t3.medium (2 vCPU) | 2 | 1 (EBS) | 2×2+1 = 5 | 5-10 |
| m5.xlarge (4 vCPU) | 4 | 1 (EBS) | 4×2+1 = 9 | 9-20 |
| m5.4xlarge (16 vCPU) | 16 | 1 (EBS) | 16×2+1 = 33 | 33-50 |

**Per-application-node sizing:**

If your total pool should be 50 connections and you run 10 pods, each pod's pool should be `50 / 10 = 5` connections.

### 3.3 Pool Exhaustion

Pool exhaustion happens when all connections are in use and a new request needs one.

```
Pool (10 connections):
┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐
│C1│C2│C3│C4│C5│C6│C7│C8│C9│C10│  ← all in use (10/10)
└──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘
         ↓
New request tries to acquire connection
         ↓
  Waits in queue (for up to pool_timeout)
         ↓
  If no connection freed in time → Error: "pool exhausted" / "connection timeout"
```

**Symptoms in production:**
- P99 latency suddenly spikes (requests are queuing for connections)
- Errors like `pgx: pool exhausted`, `ECONNREFUSED`, `connection timeout`
- Database CPU is low but application is slow (queuing problem, not computation)

**How to detect:** Monitor `pool.acquired`, `pool.idle`, `pool.waiting` metrics. Set alerts when `pool.waiting > 0` for more than a few seconds.

**How to fix:**
1. Increase pool size (check DB memory first)
2. Reduce query duration (slow queries hold connections longer)
3. Add a read replica and route reads there (reduces write DB load)
4. Add PgBouncer in front of PostgreSQL (multiplexes many app connections to few DB connections)

### 3.4 Connection Lifecycle

```
┌──────────────────────────────────────────────────────────┐
│ Connection Pool Lifecycle                                │
│                                                          │
│  Startup:                                                │
│  Pool creates min_connections on initialization         │
│                                                          │
│  On request:                                             │
│  1. acquire()  → get idle connection from pool          │
│                  (if none, wait up to pool_timeout)     │
│                  (if pool not at max, create new one)   │
│                                                          │
│  2. use        → execute query on connection            │
│                                                          │
│  3. release()  → return to pool (don't close!)          │
│                                                          │
│  Health checks:                                          │
│  Pool periodically sends SELECT 1 to idle connections   │
│  to detect and replace stale/broken connections         │
│                                                          │
│  Shutdown:                                               │
│  Pool closes all connections gracefully                  │
└──────────────────────────────────────────────────────────┘
```

**Critical rule:** Always release connections back to the pool, even on error. In Go, use `defer pool.Release(conn)`. In Python, use a context manager (`async with pool.acquire() as conn`). Failing to release causes pool exhaustion.

### 3.5 PgBouncer

PgBouncer is a lightweight connection pooler that sits between your application and PostgreSQL.

```
┌───────────────┐     ┌───────────────┐     ┌──────────────┐
│  App Pod 1    │─────│               │─────│              │
│  App Pod 2    │─────│   PgBouncer   │─────│  PostgreSQL  │
│  App Pod 3    │─────│               │─────│              │
│  App Pod 4    │─────│  50 app conns │     │  10 real     │
│  ...          │─────│  → 10 DB conns│     │  connections │
│  App Pod 50   │─────│               │─────│              │
└───────────────┘     └───────────────┘     └──────────────┘
```

**Why PgBouncer when you already have a connection pool in your app?**

Your application pool holds, say, 5 connections per pod × 50 pods = 250 connections to PostgreSQL. PostgreSQL struggles with 250 concurrent connections (memory, process overhead). PgBouncer multiplexes those 250 application connections to 10–20 real PostgreSQL connections.

**PgBouncer pool modes:**

| Mode | How It Works | Overhead | Use Case |
|------|-------------|----------|----------|
| **Session mode** | One real connection per client session; connection returned to pool when client disconnects | Minimal | Persistent app connections |
| **Transaction mode** | Real connection held only for the duration of a transaction; returned immediately after `COMMIT`/`ROLLBACK` | Low | Most web applications |
| **Statement mode** | Real connection held only for one statement; returned after each statement | Very low | Read-only queries, simple apps |

> **Transaction mode is the most common** for web applications. A single real connection can serve many application requests as long as they're not in the middle of a transaction. Note: transaction mode breaks some PostgreSQL features (prepared statements, `SET` variables, advisory locks) — check your application for compatibility.

**When to use PgBouncer:**
- Many application pods connecting to one PostgreSQL instance
- Connection count at PostgreSQL is regularly > 100
- You're hitting `FATAL: sorry, too many clients` from PostgreSQL

---

## 4. Database Schemas

### 4.1 Normalization (1NF → 3NF)

Normalization is the process of structuring a relational database to reduce data redundancy and improve integrity.

**Un-normalized table (problem):**

```
orders table (problematic):
┌──────────┬──────────┬────────────────────────┬──────────────────────────────────────┐
│ order_id │ customer │ customer_email          │ items                                │
├──────────┼──────────┼────────────────────────┼──────────────────────────────────────┤
│ 1        │ Alice    │ alice@example.com       │ Widget x2, Gadget x1                 │
│ 2        │ Alice    │ alice@example.com       │ Widget x1                            │
│ 3        │ Bob      │ bob@example.com         │ Gadget x3, Gizmo x2, Thingamajig x1  │
└──────────┴──────────┴────────────────────────┴──────────────────────────────────────┘
```

Problems: `customer_email` is duplicated; updating Alice's email requires touching all her rows. The `items` column stores multiple values, making it impossible to query by product.

**First Normal Form (1NF):** Each column contains atomic (indivisible) values; no repeating groups.

```sql
-- After 1NF: items moved to separate rows
CREATE TABLE order_items (
    order_id   INT,
    product    TEXT,
    quantity   INT
);
```

**Second Normal Form (2NF):** Must be in 1NF. Every non-key attribute must depend on the whole primary key (no partial dependencies).

Only applies when there's a composite key. If `order_items` had a composite key `(order_id, product)` and `product_price` depended only on `product` (not the full composite key), that's a partial dependency — violates 2NF.

```sql
-- 2NF: product details extracted to products table
CREATE TABLE products (
    id    SERIAL PRIMARY KEY,
    name  TEXT NOT NULL,
    price NUMERIC(10,2) NOT NULL
);

CREATE TABLE order_items (
    order_id   INT REFERENCES orders(id),
    product_id INT REFERENCES products(id),
    quantity   INT,
    PRIMARY KEY (order_id, product_id)
);
```

**Third Normal Form (3NF):** Must be in 2NF. No transitive dependencies — non-key attributes must not depend on other non-key attributes.

```sql
-- Violation: customer_zip_code → customer_city (transitive dependency)
-- customer_id → customer_zip_code → customer_city

-- Fix: extract address to separate table
CREATE TABLE customers (
    id    SERIAL PRIMARY KEY,
    name  TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE addresses (
    id          SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    street      TEXT,
    city        TEXT,
    zip_code    TEXT
);
```

**Summary of normalization goals:**

| Normal Form | Rule | What It Prevents |
|-------------|------|-----------------|
| 1NF | Atomic values, no repeating groups | Multi-valued columns, non-queryable data |
| 2NF | No partial key dependencies | Duplicate data when composite key used |
| 3NF | No transitive dependencies | Update anomalies (change city in one place, not all) |

### 4.2 Denormalization

**Why denormalize?** In read-heavy, performance-sensitive scenarios, joins are expensive. Denormalization trades write complexity for read speed by pre-computing join results.

**When denormalization is appropriate:**
- Analytics and reporting queries (reads millions of rows, joins slow)
- Event sourcing / audit logs (append-only, no updates)
- NoSQL documents (MongoDB embeds related data to avoid lookups)
- Read models in CQRS (write model is normalized; read model is denormalized for specific queries)

**Example — denormalized order summary:**

```sql
-- Normalized (3 table join for order total display):
SELECT o.id, c.name, SUM(oi.quantity * p.price) as total
FROM orders o
JOIN customers c ON c.id = o.customer_id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
GROUP BY o.id, c.name;

-- Denormalized (single row read):
CREATE TABLE order_summaries (
    order_id       INT PRIMARY KEY,
    customer_name  TEXT,  -- duplicated from customers
    customer_email TEXT,  -- duplicated from customers
    total_amount   NUMERIC(10,2),  -- pre-computed
    item_count     INT
);
```

**The cost:** When a customer changes their name, you must update both `customers` and all their `order_summaries`. This is the write-amplification trade-off. Use a database trigger or application-level event to keep denormalized data in sync.

### 4.3 Foreign Keys and Referential Integrity

Foreign keys enforce that a relationship between two tables is always valid. You cannot have an order with a `customer_id` that doesn't exist in the `customers` table.

```sql
CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

**ON DELETE behaviors:**

| Behavior | What Happens When Parent Row is Deleted |
|----------|----------------------------------------|
| `RESTRICT` | Prevent deletion if any child rows exist |
| `CASCADE` | Automatically delete all child rows |
| `SET NULL` | Set child FK to NULL |
| `SET DEFAULT` | Set child FK to its default value |
| `NO ACTION` | Same as RESTRICT (default) |

**When to use each:**
- `CASCADE` — when children can't exist without parent (order items → order)
- `RESTRICT` — when deletion should be explicitly handled (customer with active orders)
- `SET NULL` — when child can optionally exist without parent (post author deleted → author_id = NULL)

**Caution with foreign keys at scale:** At very high insert rates (100K+ rows/sec), foreign key checks add overhead. Some high-scale systems disable FK enforcement and enforce referential integrity at the application layer. This is a valid trade-off but requires strict discipline.

### 4.4 Soft Deletes vs Hard Deletes

**Hard delete:** `DELETE FROM orders WHERE id = 1` — row is gone permanently.

**Soft delete:** Mark the row as deleted with a timestamp, but keep the data:

```sql
ALTER TABLE orders ADD COLUMN deleted_at TIMESTAMPTZ;

-- Soft delete
UPDATE orders SET deleted_at = NOW() WHERE id = 1;

-- Query (always filter deleted rows):
SELECT * FROM orders WHERE deleted_at IS NULL;
```

**Pros of soft deletes:**
- Data recovery (accidental deletion)
- Audit trail (when was it deleted?)
- Referential integrity (order items still reference the soft-deleted order)
- Compliance (GDPR requires the ability to show what was deleted and when)

**Cons of soft deletes:**
- Every query must include `WHERE deleted_at IS NULL` — easy to forget
- Indexes on `deleted_at` needed for performance
- Database grows indefinitely (need archival strategy)
- Complicates UNIQUE constraints — soft-deleted rows still occupy unique values

**Fix for UNIQUE constraint with soft deletes:**

```sql
-- Partial unique index: only enforces uniqueness among non-deleted rows
CREATE UNIQUE INDEX users_email_unique
ON users (email)
WHERE deleted_at IS NULL;
```

**Fix for query safety — use a view or Row-Level Security:**

```sql
-- View that automatically excludes soft-deleted rows
CREATE VIEW active_orders AS
    SELECT * FROM orders WHERE deleted_at IS NULL;

-- Application always queries the view, not the base table
SELECT * FROM active_orders WHERE customer_id = 42;
```

**GDPR and soft deletes:** For compliance, you may need to anonymize data on soft delete rather than preserve it fully. A common pattern: on soft delete, clear PII fields but keep the row for referential integrity.

```sql
UPDATE users
SET
    email      = 'deleted-' || id || '@example.com',
    name       = 'Deleted User',
    phone      = NULL,
    deleted_at = NOW()
WHERE id = $1;
```

### 4.5 Audit Tables

An audit table tracks every change to a critical table's data — who changed what, when, and from what value to what value.

**Approach 1 — Triggers (database-level):**

```sql
CREATE TABLE orders_audit (
    audit_id    SERIAL PRIMARY KEY,
    order_id    INT NOT NULL,
    operation   TEXT NOT NULL,          -- INSERT, UPDATE, DELETE
    changed_by  TEXT,                   -- application user (from session var)
    changed_at  TIMESTAMPTZ DEFAULT NOW(),
    old_data    JSONB,                  -- previous row values
    new_data    JSONB                   -- new row values
);

CREATE OR REPLACE FUNCTION audit_orders()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO orders_audit (order_id, operation, new_data)
        VALUES (NEW.id, 'INSERT', row_to_json(NEW)::JSONB);
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO orders_audit (order_id, operation, old_data, new_data)
        VALUES (NEW.id, 'UPDATE', row_to_json(OLD)::JSONB, row_to_json(NEW)::JSONB);
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO orders_audit (order_id, operation, old_data)
        VALUES (OLD.id, 'DELETE', row_to_json(OLD)::JSONB);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER orders_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH ROW EXECUTE FUNCTION audit_orders();
```

**Approach 2 — Application-level event sourcing:**

The application emits domain events (`OrderUpdated`, `OrderCancelled`) that are appended to an immutable event store. This gives you audit history AND the ability to replay events to rebuild state — more powerful but more complex.

**Approach 3 — Temporal tables (PostgreSQL 12+ with extensions or application patterns):**

Store every version of a row with validity intervals:

```sql
CREATE TABLE orders (
    id          INT,
    status      TEXT,
    total       NUMERIC(10,2),
    valid_from  TIMESTAMPTZ DEFAULT NOW(),
    valid_to    TIMESTAMPTZ DEFAULT 'infinity',
    PRIMARY KEY (id, valid_from)
);

-- To "update" a row: close the old version and insert a new one
UPDATE orders SET valid_to = NOW() WHERE id = 1 AND valid_to = 'infinity';
INSERT INTO orders (id, status, total, valid_from, valid_to)
VALUES (1, 'shipped', 99.99, NOW(), 'infinity');

-- Query current state
SELECT * FROM orders WHERE id = 1 AND valid_to = 'infinity';

-- Query historical state (what was this order's status on a specific date?)
SELECT * FROM orders
WHERE id = 1
AND valid_from <= '2025-01-15' AND valid_to > '2025-01-15';
```

---

## 5. Implementation Examples

### Go + pgx

#### Connection Pool Setup

```go
// db/postgres.go
package db

import (
    "context"
    "fmt"
    "time"

    "github.com/jackc/pgx/v5/pgxpool"
)

type Config struct {
    Host     string
    Port     int
    User     string
    Password string
    DBName   string
    // Pool sizing: (cpu_cores * 2) + disk_spindles per formula
    // Divide total desired connections by number of application pods
    MaxConns          int32
    MinConns          int32
    MaxConnLifetime   time.Duration
    MaxConnIdleTime   time.Duration
    HealthCheckPeriod time.Duration
}

func NewPool(ctx context.Context, cfg Config) (*pgxpool.Pool, error) {
    dsn := fmt.Sprintf(
        "postgres://%s:%s@%s:%d/%s?sslmode=require",
        cfg.User, cfg.Password, cfg.Host, cfg.Port, cfg.DBName,
    )

    poolCfg, err := pgxpool.ParseConfig(dsn)
    if err != nil {
        return nil, fmt.Errorf("parsing pool config: %w", err)
    }

    // Pool sizing — adjust per your DB server's CPU cores
    poolCfg.MaxConns = cfg.MaxConns                       // e.g., 10
    poolCfg.MinConns = cfg.MinConns                       // e.g., 2 (keep warm)
    poolCfg.MaxConnLifetime = cfg.MaxConnLifetime         // e.g., 1 hour
    poolCfg.MaxConnIdleTime = cfg.MaxConnIdleTime         // e.g., 30 minutes
    poolCfg.HealthCheckPeriod = cfg.HealthCheckPeriod     // e.g., 1 minute

    // AfterConnect hook — set search_path, run SET commands
    poolCfg.AfterConnect = func(ctx context.Context, conn *pgx.Conn) error {
        _, err := conn.Exec(ctx, "SET statement_timeout = '30s'")
        return err
    }

    pool, err := pgxpool.NewWithConfig(ctx, poolCfg)
    if err != nil {
        return nil, fmt.Errorf("creating pool: %w", err)
    }

    // Verify connectivity at startup
    if err := pool.Ping(ctx); err != nil {
        return nil, fmt.Errorf("pinging database: %w", err)
    }

    return pool, nil
}

// DefaultConfig returns sensible defaults for a t3.medium DB (2 cores).
func DefaultConfig(host, user, pass, dbname string) Config {
    return Config{
        Host:              host,
        Port:              5432,
        User:              user,
        Password:          pass,
        DBName:            dbname,
        MaxConns:          10,              // (2*2)+1=5, doubled for safety
        MinConns:          2,
        MaxConnLifetime:   time.Hour,
        MaxConnIdleTime:   30 * time.Minute,
        HealthCheckPeriod: time.Minute,
    }
}
```

#### CRUD with Soft Delete

```go
// store/orders.go
package store

import (
    "context"
    "errors"
    "time"

    "github.com/google/uuid"
    "github.com/jackc/pgx/v5"
    "github.com/jackc/pgx/v5/pgxpool"
)

var ErrNotFound = errors.New("not found")

type Order struct {
    ID        uuid.UUID  `db:"id"`
    UserID    uuid.UUID  `db:"user_id"`
    Status    string     `db:"status"`
    Total     float64    `db:"total"`
    CreatedAt time.Time  `db:"created_at"`
    UpdatedAt time.Time  `db:"updated_at"`
    DeletedAt *time.Time `db:"deleted_at"` // nil = active
}

type OrderStore struct {
    pool *pgxpool.Pool
}

func NewOrderStore(pool *pgxpool.Pool) *OrderStore {
    return &OrderStore{pool: pool}
}

// FindByID fetches an active (non-deleted) order by ID.
func (s *OrderStore) FindByID(ctx context.Context, id uuid.UUID) (*Order, error) {
    const q = `
        SELECT id, user_id, status, total, created_at, updated_at, deleted_at
        FROM orders
        WHERE id = $1
          AND deleted_at IS NULL   -- enforce soft-delete filter
    `
    rows, err := s.pool.Query(ctx, q, id)
    if err != nil {
        return nil, fmt.Errorf("FindByID query: %w", err)
    }
    order, err := pgx.CollectOneRow(rows, pgx.RowToStructByName[Order])
    if errors.Is(err, pgx.ErrNoRows) {
        return nil, ErrNotFound
    }
    return &order, err
}

// FindByUserID returns all active orders for a user.
func (s *OrderStore) FindByUserID(ctx context.Context, userID uuid.UUID) ([]Order, error) {
    const q = `
        SELECT id, user_id, status, total, created_at, updated_at, deleted_at
        FROM orders
        WHERE user_id = $1
          AND deleted_at IS NULL
        ORDER BY created_at DESC
    `
    rows, err := s.pool.Query(ctx, q, userID)
    if err != nil {
        return nil, fmt.Errorf("FindByUserID query: %w", err)
    }
    return pgx.CollectRows(rows, pgx.RowToStructByName[Order])
}

// Create inserts a new order.
func (s *OrderStore) Create(ctx context.Context, userID uuid.UUID, total float64) (*Order, error) {
    const q = `
        INSERT INTO orders (id, user_id, status, total)
        VALUES ($1, $2, 'pending', $3)
        RETURNING id, user_id, status, total, created_at, updated_at, deleted_at
    `
    rows, err := s.pool.Query(ctx, q, uuid.New(), userID, total)
    if err != nil {
        return nil, fmt.Errorf("Create query: %w", err)
    }
    order, err := pgx.CollectOneRow(rows, pgx.RowToStructByName[Order])
    return &order, err
}

// SoftDelete marks an order as deleted without removing the row.
func (s *OrderStore) SoftDelete(ctx context.Context, id uuid.UUID) error {
    const q = `
        UPDATE orders
        SET deleted_at = NOW(), updated_at = NOW()
        WHERE id = $1
          AND deleted_at IS NULL   -- idempotent: don't error on already-deleted
    `
    result, err := s.pool.Exec(ctx, q, id)
    if err != nil {
        return fmt.Errorf("SoftDelete exec: %w", err)
    }
    if result.RowsAffected() == 0 {
        return ErrNotFound
    }
    return nil
}
```

---

### Node.js + pg

#### Connection Pool Setup

```javascript
// db/pool.js
const { Pool } = require('pg');

/**
 * Creates a pg connection pool with recommended settings.
 * pool_size formula: (cpu_cores * 2) + 1 (for SSD)
 * Divide by number of app instances for per-instance size.
 */
function createPool(config = {}) {
  const pool = new Pool({
    host:     config.host     || process.env.PGHOST,
    port:     config.port     || parseInt(process.env.PGPORT || '5432'),
    user:     config.user     || process.env.PGUSER,
    password: config.password || process.env.PGPASSWORD,
    database: config.database || process.env.PGDATABASE,
    ssl: { rejectUnauthorized: true },

    // Pool settings
    max:            config.max            || 10,    // maximum pool size
    min:            config.min            || 2,     // minimum idle connections
    idleTimeoutMillis:   config.idleTimeout   || 30_000,  // close idle connections after 30s
    connectionTimeoutMillis: config.connTimeout || 5_000,  // error if no conn in 5s

    // Statement timeout — prevent runaway queries from hogging connections
    statement_timeout: 30_000,
  });

  // Validate connectivity at startup
  pool.on('connect', (client) => {
    client.query("SET statement_timeout = '30s'");
  });

  pool.on('error', (err) => {
    console.error('Unexpected error on idle client', err);
  });

  return pool;
}

module.exports = { createPool };
```

#### CRUD with Soft Delete

```javascript
// store/orderRepository.js

class OrderRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async findById(id) {
    const { rows } = await this.pool.query(
      `SELECT id, user_id, status, total, created_at, updated_at
       FROM orders
       WHERE id = $1
         AND deleted_at IS NULL`,
      [id]
    );
    return rows[0] || null;
  }

  async findByUserId(userId) {
    const { rows } = await this.pool.query(
      `SELECT id, user_id, status, total, created_at, updated_at
       FROM orders
       WHERE user_id = $1
         AND deleted_at IS NULL
       ORDER BY created_at DESC`,
      [userId]
    );
    return rows;
  }

  async create({ userId, total }) {
    const { rows } = await this.pool.query(
      `INSERT INTO orders (user_id, status, total)
       VALUES ($1, 'pending', $2)
       RETURNING id, user_id, status, total, created_at, updated_at`,
      [userId, total]
    );
    return rows[0];
  }

  async updateStatus(id, status) {
    const { rows, rowCount } = await this.pool.query(
      `UPDATE orders
       SET status = $2, updated_at = NOW()
       WHERE id = $1
         AND deleted_at IS NULL
       RETURNING id, status, updated_at`,
      [id, status]
    );
    if (rowCount === 0) throw new Error('Order not found');
    return rows[0];
  }

  /**
   * Soft delete — marks deleted_at without removing the row.
   * Returns true if deleted, false if already deleted or not found.
   */
  async softDelete(id) {
    const { rowCount } = await this.pool.query(
      `UPDATE orders
       SET deleted_at = NOW(), updated_at = NOW()
       WHERE id = $1
         AND deleted_at IS NULL`,
      [id]
    );
    return rowCount > 0;
  }

  /**
   * Hard delete — only use for non-sensitive data or GDPR erasure.
   */
  async hardDelete(id) {
    const { rowCount } = await this.pool.query(
      'DELETE FROM orders WHERE id = $1',
      [id]
    );
    return rowCount > 0;
  }
}

module.exports = { OrderRepository };
```

---

### Python + SQLAlchemy (asyncpg)

#### Connection Pool Setup

```python
# db/database.py
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from config import Settings


def create_engine(settings: Settings):
    """
    Create an async SQLAlchemy engine with correct pool settings.
    Pool formula: (cpu_cores * 2) + 1, divided by number of app pods.
    """
    return create_async_engine(
        # asyncpg driver for PostgreSQL
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=settings.db_echo,          # set True to log all SQL in development

        # Pool configuration
        pool_size=settings.db_pool_size,          # e.g., 10
        max_overflow=settings.db_max_overflow,    # extra connections allowed during spikes, e.g., 5
        pool_pre_ping=True,                       # ping before use — detects stale connections
        pool_recycle=3600,                        # recycle connections after 1 hour (avoids server-side timeouts)
        pool_timeout=5,                           # raise after 5s waiting for pool connection

        # Connection args passed to asyncpg
        connect_args={
            "statement_cache_size": 0,    # required for PgBouncer transaction mode
            "command_timeout": 30,        # query timeout in seconds
        },

        poolclass=AsyncAdaptedQueuePool,
    )


# Application-wide engine (created once on startup)
_engine = None
_SessionLocal = None


def init_db(settings: Settings) -> None:
    global _engine, _SessionLocal
    _engine = create_engine(settings)
    _SessionLocal = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,   # don't expire instances after commit (safer for async)
        autocommit=False,
        autoflush=False,
    )


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency / context manager that yields a database session."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

#### Models and CRUD with Soft Delete

```python
# models/order.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )


# store/order_repository.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.order import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, order_id: uuid.UUID) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .where(Order.deleted_at.is_(None))   # soft-delete filter
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_user_id(self, user_id: uuid.UUID) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .where(Order.deleted_at.is_(None))
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, user_id: uuid.UUID, total: float) -> Order:
        order = Order(user_id=user_id, total=total, status="pending")
        self.session.add(order)
        await self.session.flush()   # get the auto-generated id before commit
        await self.session.refresh(order)
        return order

    async def soft_delete(self, order_id: uuid.UUID) -> bool:
        """
        Marks the order as deleted. Returns True if deleted, False if not found.
        """
        stmt = (
            update(Order)
            .where(Order.id == order_id)
            .where(Order.deleted_at.is_(None))
            .values(
                deleted_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            .returning(Order.id)
        )
        result = await self.session.execute(stmt)
        return result.first() is not None
```

#### FastAPI Dependency Injection

```python
# dependencies.py
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_session
from store.order_repository import OrderRepository


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session() as session:
        yield session


async def get_order_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> OrderRepository:
    return OrderRepository(session)


# Usage in router:
# @router.get("/orders/{id}")
# async def get_order(
#     order_id: UUID,
#     repo: Annotated[OrderRepository, Depends(get_order_repo)],
# ): ...
```

---

## Common Patterns & Best Practices

### 1. Always Index Foreign Keys
PostgreSQL does not automatically create indexes on foreign key columns. An un-indexed FK means every JOIN or cascade operation does a sequential scan.

```sql
-- After every FK definition:
CREATE INDEX CONCURRENTLY idx_orders_customer_id ON orders (customer_id);
CREATE INDEX CONCURRENTLY idx_order_items_order_id ON order_items (order_id);
```

### 2. Use `RETURNING` to Avoid a Round-Trip
After `INSERT`, `UPDATE`, or `DELETE`, use `RETURNING` to get the modified row without a separate `SELECT`:

```sql
INSERT INTO orders (user_id, total) VALUES ($1, $2)
RETURNING id, created_at;  -- no second SELECT needed
```

### 3. Prefer `TIMESTAMPTZ` Over `TIMESTAMP`
Always store timestamps with timezone. `TIMESTAMP` stores the literal value without any timezone context; `TIMESTAMPTZ` stores UTC internally and converts on retrieval based on session timezone.

```sql
-- Wrong: ambiguous when read from different timezones
created_at TIMESTAMP

-- Right: always stored as UTC, unambiguous
created_at TIMESTAMPTZ DEFAULT NOW()
```

### 4. Use `gen_random_uuid()` for Primary Keys
UUIDs as primary keys avoid the need for a centralized sequence generator (important in distributed systems) and prevent ID enumeration attacks.

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

For insert-heavy workloads, use UUIDv7 (time-ordered) or `ULID` to preserve B-tree locality and avoid index fragmentation.

### 5. Connection Errors Are Transient — Use Retry with Backoff
Network glitches cause connection drops. Wrap DB calls with retry logic for connection errors (but not for business logic errors like constraint violations).

```go
func queryWithRetry(ctx context.Context, pool *pgxpool.Pool, fn func(*pgxpool.Pool) error) error {
    backoff := 100 * time.Millisecond
    for attempt := 0; attempt < 3; attempt++ {
        err := fn(pool)
        if err == nil {
            return nil
        }
        var pgErr *pgconn.PgError
        if errors.As(err, &pgErr) {
            // Don't retry constraint violations, invalid input, etc.
            return err
        }
        // Retry on connection errors
        time.Sleep(backoff)
        backoff *= 2
    }
    return fmt.Errorf("all retries exhausted")
}
```

### 6. Migrations Should Be Forward-Only
Use a migration tool (golang-migrate, Flyway, Alembic) that tracks which migrations have been applied. Never modify an applied migration — always write a new one. This makes deployments predictable and rollbacks explicit.

---

## Common Pitfalls

### Pitfall 1: Opening a New Connection Per Query
```python
# Bug: creates a new connection on every request
async def get_order(id):
    conn = await asyncpg.connect(DATABASE_URL)  # new TCP connection every time
    row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", id)
    await conn.close()
    return row

# Fix: use a connection pool
async def get_order(id):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM orders WHERE id = $1", id)
```

### Pitfall 2: Forgetting Soft Delete Filters
Developers add new queries without adding `AND deleted_at IS NULL`. The fix: use a view or a repository layer that always applies the filter, so it can't be forgotten.

### Pitfall 3: N+1 Query Problem
```javascript
// N+1: 1 query for orders + N queries for each order's user
const orders = await db.query('SELECT * FROM orders');
for (const order of orders) {
    order.user = await db.query('SELECT * FROM users WHERE id = $1', [order.user_id]);
}

// Fix: JOIN in a single query
const orders = await db.query(`
    SELECT o.*, u.name as user_name, u.email as user_email
    FROM orders o
    JOIN users u ON u.id = o.user_id
    WHERE o.deleted_at IS NULL
`);
```

### Pitfall 4: Not Setting `pool_pre_ping = True`
After a connection has been idle for several hours, the database server may have closed it. Without pre-ping, your application gets an error on the first query. With `pool_pre_ping`, the pool detects and replaces broken connections automatically.

### Pitfall 5: Storing Passwords in Plain Text
Always hash passwords with bcrypt or Argon2. Never store plain text. This is not specifically a database issue but it's the most catastrophic schema design mistake.

### Pitfall 6: Ignoring Write-Ahead Log Disk Space
WAL files accumulate under high write load. Monitor `pg_wal` directory size. If WAL fills the disk, PostgreSQL stops. Set `max_wal_size` appropriately and ensure your monitoring alerts on disk usage.

---

## Interview Questions & Answers

### Q1: What is ACID and which NoSQL databases give it up?

**Answer:**
ACID stands for Atomicity (transactions succeed or fail completely), Consistency (transactions leave the DB in a valid state), Isolation (concurrent transactions don't interfere with each other), and Durability (committed transactions survive crashes).

PostgreSQL implements full ACID. WAL (Write-Ahead Logging) provides durability — changes are written to WAL and fsynced to disk before a commit is acknowledged, so they survive crashes. MVCC provides isolation without read locks.

NoSQL databases give up different parts depending on their design:
- **Cassandra** gives up consistency (AP system — during partitions, it prefers availability and returns potentially stale data).
- **Redis** (default config) gives up durability — in-memory only, data lost on restart unless RDB/AOF persistence is configured.
- **MongoDB pre-4.0** gave up atomicity across documents — only single-document operations were atomic.
- **DynamoDB** defaults to eventual consistency, though it offers strong consistency as an option (at higher latency and cost).

The CAP theorem tells us you can only guarantee two of Consistency, Availability, Partition Tolerance at once. PostgreSQL is a CA system (sacrifices partition tolerance by assuming a single node). Distributed systems must choose CP or AP.

---

### Q2: How do you choose between SQL and NoSQL?

**Answer:**
My default is PostgreSQL for new projects. The reasons: relational integrity, ACID transactions, mature tooling, and JSONB for flexible schemas mean it can handle 95% of use cases at startup-to-mid-scale.

I'd consider NoSQL when I have a specific, justified reason:

**MongoDB** when I have genuinely document-hierarchical data that doesn't benefit from normalization, or when schema evolution is so rapid that managing migrations is a bottleneck.

**Redis** is always in the stack, but as a cache and session store, not a primary database.

**Elasticsearch** when I need full-text search with relevance scoring beyond what PostgreSQL's tsvector can handle.

The question I ask is: "What's the access pattern?" If the primary access is by ID or simple filters, PostgreSQL is fine. If it's full-text search, I add Elasticsearch as a read index over PostgreSQL. If it's real-time leaderboards or pub/sub, Redis.

---

### Q3: What is connection pooling and why is it necessary?

**Answer:**
Every PostgreSQL connection is an OS process consuming ~5-10MB RAM, and establishing a connection requires a TCP handshake + TLS + authentication — 5-50ms overhead. Without pooling, a web server handling 1000 req/s would create and destroy 1000 connections per second, crushing the database with process overhead and memory.

Connection pooling maintains a fixed number of long-lived database connections and hands them to application threads/goroutines on demand. When a request finishes, the connection is returned to the pool (not closed) for reuse.

Pool sizing follows the formula `(cpu_cores × 2) + disk_spindles`. Adding more connections beyond this doesn't increase throughput — it only adds context-switching overhead. In a multi-pod deployment, divide total target connections by the number of pods.

Pool exhaustion (all connections in use, new requests queuing) is diagnosed by monitoring `pool.waiting > 0`. The fixes are: increase pool size, add PgBouncer to multiplex many app connections to fewer DB connections, or reduce query duration to release connections faster.

---

### Q4: What is PgBouncer and when would you use it?

**Answer:**
PgBouncer is a lightweight connection pooler that sits between your application and PostgreSQL. It accepts many application connections and multiplexes them to a smaller number of real PostgreSQL connections. For example, 50 pods each holding 20 connections = 1000 app connections, multiplexed by PgBouncer to 20 real PostgreSQL connections.

Use PgBouncer when your total application connection count exceeds PostgreSQL's comfortable limit (~100-300 connections), which happens in microservices or when you scale to many pods.

PgBouncer has three modes: session (connection per client session), transaction (connection held only during a transaction — most common), and statement (connection per statement). Transaction mode is most efficient but requires care — it breaks PostgreSQL features that rely on persistent connection state (prepared statements without PgBouncer-level caching, `SET` variables, advisory locks).

---

### Q5: How do you handle soft deletes?

**Answer:**
A soft delete adds a `deleted_at TIMESTAMPTZ` column to the table. Instead of `DELETE FROM orders WHERE id = $1`, you run `UPDATE orders SET deleted_at = NOW() WHERE id = $1`. The row stays in the database — visible to admin queries, audit trails, and foreign key references — but excluded from normal queries.

Every query against the table must include `WHERE deleted_at IS NULL`. To make this foolproof, I use a view or a repository layer that always applies this filter, so it can't be accidentally omitted by a developer writing a new query.

For UNIQUE constraints, I add a partial unique index: `CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL`. This enforces uniqueness only among non-deleted rows, allowing the same email to be "re-registered" after a soft delete.

For GDPR compliance, soft delete isn't enough on its own — you need to anonymize PII fields on deletion while keeping the row skeleton for referential integrity.

---

### Q6: What is WAL and how does it guarantee durability?

**Answer:**
WAL (Write-Ahead Logging) is PostgreSQL's mechanism for durable writes. The principle: before any change is written to the actual data files, it's first written to the WAL (a sequential append-only log on disk) and fsynced. Only after the WAL is safely on disk does PostgreSQL acknowledge the commit to the client.

Why is this durable? If the server crashes immediately after commit, the data files might not reflect the change (because data file writes are batched and async). But the WAL is there. On restart, PostgreSQL replays the WAL, applying any changes not yet reflected in data files (redo). Uncommitted transactions are rolled back.

The performance insight: WAL is sequential append (fast for all storage types). Data file writes are random I/O (slow on HDDs, acceptable on SSDs). By making the critical durability path sequential (WAL), PostgreSQL achieves good write throughput without making every commit wait for random I/O.

`fsync = off` disables WAL-to-disk flushing, making writes much faster — but a crash can corrupt the entire cluster. Never use this in production.

---

## Resources

- [PostgreSQL Documentation — Connection Pooling](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [PgBouncer Documentation](https://www.pgbouncer.org/usage.html)
- [pgx — PostgreSQL Driver for Go](https://github.com/jackc/pgx)
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Designing Data-Intensive Applications (Kleppmann) — Chapter 2 & 7](https://dataintensive.net/)
- [The Internals of PostgreSQL — WAL](https://www.interdb.jp/pg/pgsql09.html)
- [HikariCP Pool Sizing — About Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)
- [OWASP — SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

---

**Next:** [Part 6.2: Transactions & Isolation Levels](./06-transactions-isolation-levels.md)
