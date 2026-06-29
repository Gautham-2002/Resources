# Part 7.1: Indexing & Query Optimization

## What You'll Learn
- How B-tree, Hash, GIN, BRIN, partial, composite, covering, and expression indexes work internally
- The leftmost prefix rule and how composite indexes are selected by the query planner
- How to read and interpret `EXPLAIN` and `EXPLAIN ANALYZE` output
- The N+1 problem — why it kills performance and how to eliminate it
- ORM vs raw SQL trade-offs for production systems
- Practical index creation and query tuning in Go (pgx), Node.js (Prisma/Knex), Python (SQLAlchemy)

---

## Table of Contents
1. [Index Internals](#1-index-internals)
   - B-tree Index
   - Hash Index
   - GIN Index
   - BRIN Index
   - Partial Index
   - Composite Index & the Leftmost Prefix Rule
   - Covering Index (INCLUDE columns)
   - Expression Index
   - Bitmap Index Scan vs Sequential Scan vs Index Scan
2. [Query Optimization](#2-query-optimization)
   - EXPLAIN and EXPLAIN ANALYZE
   - Seq Scan vs Index Scan vs Index Only Scan vs Bitmap Heap Scan
   - Reading Cost Estimates
   - Statistics: ANALYZE, pg_stats, and Planner Decisions
   - Avoiding Function Calls on Indexed Columns
   - Index Bloat: UPDATEs, DELETEs, REINDEX
3. [The N+1 Problem](#3-the-n1-problem)
4. [ORM vs Raw SQL](#4-orm-vs-raw-sql)
5. [Implementation Examples](#5-implementation-examples)
   - Go + pgx
   - Node.js + Prisma/Knex
   - Python + SQLAlchemy
6. [Common Patterns & Best Practices](#6-common-patterns--best-practices)
7. [Common Pitfalls](#7-common-pitfalls)
8. [Interview Questions & Model Answers](#8-interview-questions--model-answers)
9. [Resources](#9-resources)

---

## 1. Index Internals

### B-tree Index

A **B-tree (Balanced Tree)** is the default and most common index type in PostgreSQL (and virtually every relational database). Understanding it deeply is essential for any senior backend interview.

**Structure:**
- A B-tree is a self-balancing tree where every leaf is at the same depth.
- Each internal node contains keys and pointers to child nodes.
- Leaf nodes contain the actual indexed key values and pointers (TIDs — tuple IDs) back to the actual heap rows.
- The tree is kept balanced on every insert, update, and delete. PostgreSQL splits or merges nodes as needed.

**Complexity:**
- Lookup: **O(log n)** — travel from root to leaf
- Insert: **O(log n)** — find position and potentially split
- Range scan: **O(log n + k)** where k is the number of matching rows — after finding the start key, you scan leaf nodes sequentially because they're linked

**Why B-tree for range queries?**
Because leaf nodes are linked in a doubly-linked list. Once you reach the first matching key via tree traversal, you just walk forward through the linked leaves. This is why `BETWEEN`, `>`, `<`, `ORDER BY`, and `LIKE 'prefix%'` queries all benefit from B-tree indexes.

**Physical layout:**
```
Root: [50 | 100 | 150]
       /     |      \     \
[10,20,30] [60,70,80] [110,120] [160,180]
   ...           ...
```

Every page (PostgreSQL's default: 8KB) stores as many keys as fit. The tree height stays low even for millions of rows — a table with 1 billion rows typically has a B-tree of depth 4-5.

**When B-tree is used:**
- Equality: `WHERE id = 42`
- Range: `WHERE created_at BETWEEN '2024-01-01' AND '2024-12-31'`
- Pattern prefix: `WHERE email LIKE 'john%'` (but NOT `'%john'`)
- Sorting: `ORDER BY last_name` can use index to avoid sort
- Inequality: `WHERE age > 18`

**When B-tree is NOT ideal:**
- Full-text search (use GIN)
- Array containment (use GIN)
- Very large sequential scans of numeric data (BRIN may be smaller)
- Pure equality on high-write columns (Hash index)

---

### Hash Index

A **Hash index** uses a hash function to map keys to bucket locations. It is O(1) for equality lookups.

**Structure:**
- Keys are hashed into buckets. Each bucket stores pointers to rows with that hash value.
- No ordering is maintained — the index is fundamentally unordered.

**PostgreSQL history:**
- Before PostgreSQL 10: Hash indexes were NOT WAL-logged and were not crash-safe. They had to be manually rebuilt after a crash. Almost nobody used them in production.
- **PostgreSQL 10+**: Hash indexes are now fully WAL-logged and crash-safe. They are a viable option.

**Use case:** Strict equality only — `WHERE id = 42`. Cannot be used for `>`, `<`, `BETWEEN`, `LIKE`, or `ORDER BY`.

**Compared to B-tree for equality:**
- Hash is theoretically faster for pure equality (O(1) vs O(log n))
- In practice, B-trees are already very fast (3-5 levels deep) and the difference is often negligible
- Hash indexes do not support range queries or sorting — they are a specialized tool
- Hash indexes are generally smaller than B-tree for the same data

**Interview tip:** Most interviewers expect you to know that Hash indexes exist, their limitation to equality only, and the historical pre-PG10 reliability issue.

---

### GIN Index (Generalized Inverted Index)

**GIN** is designed for cases where a single indexed item maps to multiple values — such as full-text search tokens, array elements, or JSONB keys.

**Structure:**
- An inverted index: a mapping from each **element/token** → list of rows containing it
- Think of it like the index at the back of a textbook: "Chapter 3, Chapter 7, Chapter 12" under the word "cache"

**Use cases:**
1. **Full-text search:** `tsvector` columns — `WHERE document @@ to_tsquery('postgresql & index')`
2. **Arrays:** `WHERE tags @> ARRAY['golang', 'backend']` (array contains)
3. **JSONB:** `WHERE data @> '{"status": "active"}'`
4. **`pg_trgm` extension:** Trigram-based LIKE/ILIKE search — `WHERE name ILIKE '%garcia%'`

**Performance characteristics:**
- Reads: Fast — especially for containment queries
- Writes: Slow — GIN indexes are expensive to update. Every inserted/updated row may touch many index entries (one per token/element).
- **Fastupdate:** PostgreSQL buffers GIN updates in a "pending list" and applies them in bulk. This speeds up writes but can cause a pause during the bulk flush. You can disable fastupdate for more predictable latency.

```sql
-- Full-text search index
CREATE INDEX idx_articles_fts ON articles USING GIN (to_tsvector('english', title || ' ' || body));

-- JSONB containment
CREATE INDEX idx_users_data ON users USING GIN (metadata);

-- Array containment
CREATE INDEX idx_posts_tags ON posts USING GIN (tags);

-- Trigram for ILIKE search (requires pg_trgm extension)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_products_name_trgm ON products USING GIN (name gin_trgm_ops);
```

---

### BRIN Index (Block Range INdex)

**BRIN** is a tiny index for very large tables where the data has a natural physical ordering correlated with insertion order.

**Structure:**
- Divides the table into ranges of physical disk blocks (default: 128 pages per range)
- For each range, stores only the **min** and **max** value of the indexed column
- Extremely compact — a BRIN index on a billion-row table might be just a few KB

**When BRIN works well:**
- Time-series data: `created_at` on an events table where rows are inserted in chronological order
- Sequential IDs: if `id` correlates with physical insertion order (before VACUUM rearranges things)
- IoT sensor data: `timestamp` on readings table

**When BRIN does NOT work:**
- Data that is randomly distributed across pages (no physical ordering correlation)
- High-cardinality data with frequent updates that scatter rows across pages

**Trade-off:**
- A BRIN index might allow the planner to skip entire block ranges — very efficient
- But it's not as precise as B-tree; the planner still has to scan all rows in the qualifying block ranges
- Use BRIN when the table is huge and a B-tree index would itself be too large or too slow to maintain

```sql
-- BRIN on a time-series events table
CREATE INDEX idx_events_created_brin ON events USING BRIN (created_at);

-- Custom pages_per_range (smaller = more precise but larger index)
CREATE INDEX idx_sensor_ts_brin ON sensor_readings USING BRIN (timestamp) WITH (pages_per_range = 32);
```

---

### Partial Index

A **partial index** is a B-tree (or other type) index with a `WHERE` clause — it only indexes rows that satisfy the predicate.

**Why use partial indexes?**
- Smaller index → faster reads and writes
- Index only the "interesting" subset of rows
- Classic example: index only active/unprocessed rows

```sql
-- Only index users who are active (not deleted/suspended)
CREATE INDEX idx_users_active_email ON users (email) WHERE deleted_at IS NULL;

-- Only index unprocessed jobs in a jobs queue
CREATE INDEX idx_jobs_pending ON jobs (created_at) WHERE status = 'pending';

-- Only index high-value orders
CREATE INDEX idx_orders_large ON orders (user_id, created_at) WHERE total_amount > 10000;
```

**Query planner behavior:**
The planner will only use a partial index if the query's WHERE clause is compatible with the index's predicate. For the partial index on active users:
- `SELECT * FROM users WHERE deleted_at IS NULL AND email = 'x@y.com'` → uses partial index ✓
- `SELECT * FROM users WHERE email = 'x@y.com'` → may NOT use partial index (predicate not guaranteed) ✗

**Production impact:** If your `users` table has 10M rows and only 500K are active, a partial index on active users is 20× smaller than a full index. Massive win.

---

### Composite Index & the Leftmost Prefix Rule

A **composite index** (multi-column index) indexes multiple columns together. The order of columns in the index definition is critical.

```sql
CREATE INDEX idx_orders_user_status_date ON orders (user_id, status, created_at);
```

**The Leftmost Prefix Rule:**
The query planner can use this index for queries that filter on a **prefix** of the indexed columns from the left side:

| Query Filter | Uses Index? | Notes |
|---|---|---|
| `WHERE user_id = 1` | ✓ | Leftmost prefix |
| `WHERE user_id = 1 AND status = 'paid'` | ✓ | First two columns |
| `WHERE user_id = 1 AND status = 'paid' AND created_at > '2024-01-01'` | ✓ | All three columns |
| `WHERE status = 'paid'` | ✗ | Skips leftmost (user_id) |
| `WHERE status = 'paid' AND created_at > '2024-01-01'` | ✗ | Skips leftmost |
| `WHERE user_id = 1 AND created_at > '2024-01-01'` | Partial ✓ | Uses user_id, can't use created_at efficiently |

**Why does order matter?**
Think of it like a phone book sorted by (last_name, first_name). You can find everyone named "Smith" because last_name is the primary sort. But you cannot efficiently find everyone named "John" without scanning the entire book — first_name is only ordered within each last_name group.

**Column order strategy:**
1. **Equality columns first** — columns used with `=` should come before range columns
2. **High cardinality first** — high selectivity columns prune more rows early
3. **Range or sort columns last** — `>`, `<`, `BETWEEN`, `ORDER BY` columns go at the end
4. Consider the queries you actually run — design indexes for query patterns

**Example design thought process:**
```sql
-- Query: find paid orders for user 42 in the last month, ordered by date
SELECT * FROM orders 
WHERE user_id = 42 AND status = 'paid' AND created_at > NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;

-- Best index: equality columns first, range column last
CREATE INDEX idx_orders_uid_status_cat ON orders (user_id, status, created_at);
-- This index serves the WHERE and eliminates a sort step for ORDER BY
```

---

### Covering Index (INCLUDE Columns)

An **index-only scan** is when PostgreSQL can answer a query entirely from the index without touching the heap (the actual table). This is extremely fast.

For an index-only scan to work, all columns referenced in the query (SELECT, WHERE, ORDER BY) must be in the index.

**INCLUDE columns (PostgreSQL 11+):**
```sql
-- We want: SELECT email, created_at FROM users WHERE user_id = 42
-- Standard index on user_id requires a heap fetch to get email and created_at
CREATE INDEX idx_users_id ON users (user_id);

-- Covering index: INCLUDE stores extra columns in leaf pages without affecting sort order
CREATE INDEX idx_users_id_covering ON users (user_id) INCLUDE (email, created_at);
-- Now the query can be answered entirely from the index
```

**INCLUDE vs adding to key columns:**
- Adding `email` as a key column (e.g., `CREATE INDEX ON users(user_id, email)`) would also work for index-only scans but changes the index sort order and affects which queries can use the leftmost prefix rule.
- `INCLUDE` columns are stored only in leaf pages — they don't affect the B-tree sort structure and are not usable in WHERE/ORDER BY.
- Use `INCLUDE` when you want extra columns for index-only scans without affecting the tree's sorting properties.

**Visibility map:**
For an index-only scan to work, PostgreSQL also needs to verify that the heap rows are "visible" (not hidden by an ongoing transaction). It uses the **visibility map** — a bitmap that tracks which heap pages are all-visible. If the visibility map shows a page is all-visible, the index-only scan truly avoids the heap. If not (e.g., after a bulk update before VACUUM runs), it falls back to a bitmap heap scan. This is why index-only scans may not perform as expected right after heavy writes — run `VACUUM` to update the visibility map.

---

### Expression Index

An **expression index** (also called a functional index) indexes the result of a function or expression applied to one or more columns.

```sql
-- Common case: case-insensitive email lookup
-- WITHOUT expression index, this can't use a regular index on email:
SELECT * FROM users WHERE lower(email) = lower('John@Example.com');

-- WITH expression index:
CREATE INDEX idx_users_lower_email ON users (lower(email));
-- Now the above query uses this index

-- Another example: extract year from timestamp
CREATE INDEX idx_events_year ON events (EXTRACT(YEAR FROM created_at));
-- Serves: WHERE EXTRACT(YEAR FROM created_at) = 2024

-- JSON field extraction
CREATE INDEX idx_orders_metadata_country ON orders ((metadata->>'country'));
```

**Critical rule:** The expression in your `WHERE` clause must **exactly match** the expression used in the `CREATE INDEX` statement. The planner won't infer equivalence:
```sql
-- Index: lower(email)
-- ✓ Uses index: WHERE lower(email) = 'john@example.com'
-- ✗ No index:   WHERE email = 'John@Example.com'  (different expression)
-- ✗ No index:   WHERE LOWER(email) = ...  (different casing — actually fine in PG, but exact expression match required)
```

---

### Bitmap Index Scan vs Sequential Scan vs Index Scan

The query planner chooses between several scan strategies. Understanding why each is chosen is essential.

**Sequential Scan (Seq Scan):**
- Reads the entire table from start to finish
- O(n) — proportional to table size
- Favored when: the query will return a large fraction of the table (>5-10% of rows), the table is small, statistics show low selectivity
- Always the fallback when no usable index exists

**Index Scan:**
- Traverses the B-tree to find matching entries, then fetches each heap row individually via TID
- Best for: highly selective queries returning few rows (e.g., `WHERE id = 42`)
- Can be expensive for: queries returning many rows because each row requires a random I/O to the heap (random disk seeks are expensive on HDD, less so on SSD)
- Order: returns rows in index order, which can satisfy `ORDER BY` without a sort step

**Index Only Scan:**
- Like Index Scan but never touches the heap
- Requires all needed columns to be in the index (covering index) and visibility map to be current
- Fastest scan type for eligible queries

**Bitmap Index Scan → Bitmap Heap Scan:**
This is a two-phase approach for medium-selectivity queries:

Phase 1 — **Bitmap Index Scan:** Scan the index and build an in-memory bitmap of which heap pages/rows match. Each bit represents one heap block (lossy bitmap) or one row (exact bitmap).

Phase 2 — **Bitmap Heap Scan:** Walk through the heap in physical page order (not random order), reading only the pages flagged in the bitmap. Rechecks conditions row by row.

Why is this faster for medium selectivity?
- It converts random I/O (index scan's per-row heap fetch) into sequential I/O (reading heap pages in order)
- Multiple indexes can be combined with `BitmapAnd` / `BitmapOr` operations — the planner might use one index for `user_id` and another for `status`, combine the bitmaps, then do one pass over the heap

```
Query: WHERE user_id = 42 AND status = 'paid'
Plan:
  -> Bitmap Heap Scan on orders
       -> BitmapAnd
            -> Bitmap Index Scan on idx_orders_user_id
            -> Bitmap Index Scan on idx_orders_status
```

**Decision heuristic (simplified):**
- 0-1% matching rows → Index Scan (few heap fetches, random I/O acceptable)
- 1-10% matching rows → Bitmap Index Scan (batch heap fetches, sequential I/O)
- >10% matching rows → Sequential Scan (just read everything, less overhead)

---

## 2. Query Optimization

### EXPLAIN and EXPLAIN ANALYZE

`EXPLAIN` shows the **query plan** — what the planner *intends* to do. `EXPLAIN ANALYZE` actually **executes** the query and shows what *actually happened*.

**EXPLAIN output:**
```sql
EXPLAIN SELECT * FROM orders WHERE user_id = 42;
```
```
                                QUERY PLAN
--------------------------------------------------------------------------
 Index Scan using idx_orders_user_id on orders  (cost=0.42..8.44 rows=1 width=64)
   Index Cond: (user_id = 42)
```

**Reading cost estimates:**
`cost=0.42..8.44`
- `0.42` = **startup cost** — cost to get the first row (tree traversal, sort initialization, etc.)
- `8.44` = **total cost** — estimated cost to return all rows
- Cost is in arbitrary units (not milliseconds). The default: sequential page read = 1.0, random page read = 4.0 (configurable via `seq_page_cost`, `random_page_cost`).

`rows=1` — planner estimates 1 row returned. Accuracy depends on statistics freshness.

`width=64` — estimated average row size in bytes.

**EXPLAIN ANALYZE output:**
```sql
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 42;
```
```
Index Scan using idx_orders_user_id on orders
  (cost=0.42..8.44 rows=1 width=64)
  (actual time=0.083..0.091 rows=3 loops=1)
  Index Cond: (user_id = 42)
Planning Time: 0.187 ms
Execution Time: 0.115 ms
```

Key new fields:
- `actual time=0.083..0.091` — real startup and end time in milliseconds
- `rows=3` — actual rows returned (planner estimated 1, got 3 — mild mismatch, fine)
- `loops=1` — how many times this node was executed (for nested loops this can be high)

**Critical: EXPLAIN ANALYZE actually runs the query.** For destructive queries, wrap in a transaction and roll back:
```sql
BEGIN;
EXPLAIN ANALYZE DELETE FROM orders WHERE user_id = 42;
ROLLBACK;
```

**EXPLAIN ANALYZE options (PostgreSQL 13+):**
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT ...;
```
- `BUFFERS` — shows cache hits vs disk reads. `shared hit=X` means X pages found in PostgreSQL's shared buffer cache (good). `shared read=X` means X pages were read from disk (I/O).
- `FORMAT JSON` or `FORMAT TEXT` — machine-readable vs human-readable output

**Visual tools:** Use [explain.depesz.com](https://explain.depesz.com/) or [explain.dalibo.com](https://explain.dalibo.com/) to paste EXPLAIN ANALYZE output and get a visual breakdown.

---

### Statistics: ANALYZE, pg_stats, and Planner Decisions

The query planner uses statistics to estimate row counts. Wrong estimates → bad plans.

**How statistics are gathered:**
- `ANALYZE` samples table data and updates `pg_statistic` / `pg_stats`
- `autovacuum` runs `ANALYZE` automatically based on thresholds
- Manual: `ANALYZE orders;` or `ANALYZE VERBOSE orders;`

**What statistics are stored in pg_stats:**
```sql
SELECT attname, n_distinct, most_common_vals, histogram_bounds, correlation
FROM pg_stats 
WHERE tablename = 'orders' AND attname = 'status';
```
- `n_distinct`: number of distinct values (-1 means nearly as many distinct values as rows)
- `most_common_vals` / `most_common_freqs`: top values and their frequency (e.g., status='paid' appears 60% of the time)
- `histogram_bounds`: bucket boundaries for estimating range selectivity
- `correlation`: how well the physical row order correlates with column order (1.0 = perfectly correlated, -1 = perfectly inverse, 0 = random). High correlation favors index scan over bitmap scan.

**Increasing statistics target:**
By default, PostgreSQL samples 300 rows per column. For skewed distributions, increase the target:
```sql
ALTER TABLE orders ALTER COLUMN user_id SET STATISTICS 500;
ANALYZE orders;
```

**When estimates go wrong:**
If `rows=1` in EXPLAIN but `rows=10000` in ANALYZE, the planner made a terrible estimate:
- Run `ANALYZE` — statistics may be stale
- Increase statistics target for that column
- Check for correlated columns (use extended statistics: `CREATE STATISTICS`)

---

### Avoiding Function Calls on Indexed Columns in WHERE

This is one of the most common mistakes that kills index usage:

```sql
-- Index exists on: users(created_at)

-- ✗ BREAKS index usage — function call on indexed column
SELECT * FROM users WHERE DATE(created_at) = '2024-01-15';
SELECT * FROM users WHERE EXTRACT(YEAR FROM created_at) = 2024;
SELECT * FROM users WHERE TO_CHAR(created_at, 'YYYY-MM') = '2024-01';

-- ✓ Preserves index usage — transform the constant instead
SELECT * FROM users WHERE created_at >= '2024-01-15' AND created_at < '2024-01-16';
SELECT * FROM users WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';
SELECT * FROM users WHERE created_at >= '2024-01-01' AND created_at < '2024-02-01';
```

**Why?** PostgreSQL cannot use the index on `created_at` to answer `DATE(created_at) = '2024-01-15'` because the index stores values of `created_at`, not `DATE(created_at)`. The planner would have to evaluate `DATE(created_at)` for every row — a sequential scan.

The fix: rewrite the predicate to operate on the column directly, transforming the constant.

**Other common cases:**
```sql
-- ✗ BREAKS: implicit type conversion
SELECT * FROM users WHERE id = '42';  -- if id is integer and '42' is text

-- ✓ FIX: use correct type
SELECT * FROM users WHERE id = 42;

-- ✗ BREAKS: wrapping column in function
SELECT * FROM users WHERE UPPER(last_name) = 'SMITH';

-- ✓ FIX 1: expression index
CREATE INDEX idx_users_upper_last_name ON users (UPPER(last_name));
-- ✓ FIX 2: store data normalized and query with same case
```

---

### Index Bloat: UPDATEs, DELETEs, REINDEX

**How PostgreSQL handles UPDATEs:**
PostgreSQL uses MVCC (Multi-Version Concurrency Control). An `UPDATE` does NOT modify a row in place — it:
1. Marks the old row version as "dead" (invisible to new transactions)
2. Inserts a new row version

This means every UPDATE creates a new index entry (pointing to the new heap tuple) AND leaves behind the old index entry (pointing to the dead tuple). The old entry is eventually removed by `VACUUM`.

**Index bloat:**
If VACUUM can't keep up (high update rate, autovacuum disabled, long-running transactions blocking VACUUM), dead index entries accumulate. This is **index bloat**.

Consequences:
- Index becomes larger → more I/O to traverse
- Index scan becomes slower → planner may prefer seq scan
- Write performance degrades

**Measuring index bloat:**
```sql
-- Check index size vs table size
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;

-- More detailed bloat estimate using pgstattuple extension
CREATE EXTENSION IF NOT EXISTS pgstattuple;
SELECT * FROM pgstatindex('idx_orders_user_id');
-- dead_tuple_percent > 20% indicates significant bloat
```

**Fixing index bloat:**
```sql
-- REINDEX CONCURRENTLY (PostgreSQL 12+) — rebuilds without locking reads/writes
REINDEX INDEX CONCURRENTLY idx_orders_user_id;
REINDEX TABLE CONCURRENTLY orders;  -- rebuilds all indexes on a table

-- Or use pg_repack extension for online table + index reorganization
```

**Prevention:**
- Tune autovacuum for high-write tables: lower `autovacuum_vacuum_scale_factor`
- Avoid long-running idle transactions (they block VACUUM)
- Monitor `pg_stat_user_tables.n_dead_tup`

---

## 3. The N+1 Problem

### What It Is

The N+1 problem occurs when code issues **1 query to fetch a list of N items**, then **N additional queries** to fetch related data for each item.

**Classic example:** Fetch 100 users and their order counts.

```python
# BAD — N+1 pattern
users = db.query("SELECT * FROM users LIMIT 100")  # 1 query

for user in users:
    count = db.query(
        "SELECT COUNT(*) FROM orders WHERE user_id = ?", user.id
    )  # 100 more queries!
    user.order_count = count

# Total: 101 database round-trips
```

**Why it's deadly:**
Each database round-trip involves:
- Network latency (even on localhost: ~0.1-1ms per round-trip)
- Connection acquisition from pool
- Query parsing and planning
- Disk I/O

101 queries × 1ms = 101ms minimum just in latency overhead, ignoring actual execution.
At 1000 users: 1001 queries ≈ 1 full second just in network overhead.
At scale (10K concurrent requests each doing N+1): you saturate your connection pool instantly.

### How to Solve It

**Solution 1: JOIN**
```sql
-- One query, complete data
SELECT u.*, COUNT(o.id) AS order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
GROUP BY u.id
LIMIT 100;
```

**Solution 2: Batch query (IN clause)**
```sql
-- Query 1: fetch users
SELECT * FROM users LIMIT 100;

-- Query 2: fetch all their orders in one shot
SELECT user_id, COUNT(*) as order_count 
FROM orders 
WHERE user_id IN (1, 2, 3, ..., 100)
GROUP BY user_id;

-- Application: merge the two result sets
```

**Solution 3: Eager loading (ORM-level)**
Most ORMs support explicit eager loading:
```python
# SQLAlchemy: joinedload or subqueryload
users = session.query(User).options(
    joinedload(User.orders)
).limit(100).all()
# Result: 1 JOIN query (or 1 + 1 with subqueryload)

# Bad: lazy loading triggers N+1
users = session.query(User).limit(100).all()
for user in users:
    print(user.orders)  # Each access triggers a SELECT — N+1!
```

---

## 4. ORM vs Raw SQL

### ORM Benefits
- **DRY**: Define schema once as model classes; migrations are generated
- **Type safety**: Column types map to language types; compile-time errors
- **Portability**: Switch databases with minimal code change (in theory)
- **Security**: Parameterized queries by default — prevents SQL injection
- **Productivity**: Relationship traversal, built-in pagination, automatic timestamping

### ORM Pitfalls

**1. Implicit lazy loading → N+1**
```python
# SQLAlchemy with lazy loading (default)
for post in session.query(Post).all():
    print(post.author.name)  # Each access: SELECT * FROM users WHERE id = ?
```

**2. Overfetching**
ORMs often SELECT all columns (`SELECT *`) even when you need two:
```python
# Fetches all 20 columns when you only need 2
users = session.query(User).filter_by(active=True).all()
for u in users:
    print(u.email)  # Only needed email and id
```

**3. Hard to optimize**
Complex queries with window functions, CTEs, lateral joins, or custom aggregations are awkward or impossible to express in ORM query builders.

**4. Migration complexity**
ORM migrations (Alembic, Flyway) can be fragile for large schema changes. Adding a column to a 500M row table requires careful planning independent of what the ORM generates.

### When to Drop to Raw SQL

- Complex aggregations with GROUP BY / HAVING / ROLLUP
- Window functions (ROW_NUMBER, RANK, LAG/LEAD)
- CTEs (WITH clauses) for recursive queries
- Bulk upserts (INSERT ... ON CONFLICT)
- Performance-critical paths where EXPLAIN shows ORM generating suboptimal plans
- Cross-table operations that don't map to ORM model boundaries

### Using EXPLAIN with ORM Queries

Always check what SQL your ORM is generating and whether it's using indexes:

```python
# SQLAlchemy: echo mode
engine = create_engine(DATABASE_URL, echo=True)

# Or get the compiled SQL
query = session.query(User).filter(User.email == 'test@example.com')
print(query.statement.compile(dialect=postgresql.dialect()))

# Then run EXPLAIN ANALYZE on that SQL in psql
```

---

## 5. Implementation Examples

### Go + pgx

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/jackc/pgx/v5/pgxpool"
)

// Schema setup — run these in your migrations
const createIndexesSQL = `
-- Composite index: user lookups + status filtering + date range
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_uid_status_cat
    ON orders (user_id, status, created_at DESC);

-- Partial index: only pending jobs (avoids indexing completed/failed rows)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_pending_created
    ON jobs (created_at)
    WHERE status = 'pending';

-- Covering index: profile lookups — all needed columns in index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_covering
    ON users (email) INCLUDE (id, name, created_at)
    WHERE deleted_at IS NULL;

-- Expression index: case-insensitive email
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_lower_email
    ON users (lower(email));
`

type DB struct {
    pool *pgxpool.Pool
}

// N+1 BAD — each user triggers a separate query
func (db *DB) GetUsersWithOrderCountBad(ctx context.Context) error {
    rows, err := db.pool.Query(ctx, "SELECT id, name FROM users LIMIT 100")
    if err != nil {
        return err
    }
    defer rows.Close()

    type UserRow struct {
        ID   int
        Name string
    }
    var users []UserRow
    for rows.Next() {
        var u UserRow
        if err := rows.Scan(&u.ID, &u.Name); err != nil {
            return err
        }
        users = append(users, u)
    }

    // N additional queries — DO NOT DO THIS
    for _, u := range users {
        var count int
        err := db.pool.QueryRow(ctx,
            "SELECT COUNT(*) FROM orders WHERE user_id = $1", u.ID,
        ).Scan(&count)
        if err != nil {
            return err
        }
        fmt.Printf("User %s has %d orders\n", u.Name, count)
    }
    return nil
}

// N+1 FIXED — single JOIN query
func (db *DB) GetUsersWithOrderCountGood(ctx context.Context) ([]UserWithCount, error) {
    const q = `
        SELECT 
            u.id, 
            u.name, 
            COUNT(o.id) AS order_count,
            COALESCE(SUM(o.total_amount), 0) AS total_spent
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.id AND o.status = 'paid'
        WHERE u.deleted_at IS NULL
        GROUP BY u.id, u.name
        ORDER BY total_spent DESC
        LIMIT 100
    `
    rows, err := db.pool.Query(ctx, q)
    if err != nil {
        return nil, fmt.Errorf("query users with counts: %w", err)
    }
    defer rows.Close()

    var results []UserWithCount
    for rows.Next() {
        var r UserWithCount
        if err := rows.Scan(&r.ID, &r.Name, &r.OrderCount, &r.TotalSpent); err != nil {
            return nil, err
        }
        results = append(results, r)
    }
    return results, rows.Err()
}

type UserWithCount struct {
    ID         int
    Name       string
    OrderCount int
    TotalSpent float64
}

// Using EXPLAIN ANALYZE to check query plans
func (db *DB) ExplainQuery(ctx context.Context, query string, args ...any) (string, error) {
    explainQuery := "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " + query
    var plan string
    err := db.pool.QueryRow(ctx, explainQuery, args...).Scan(&plan)
    return plan, err
}

// Batch fetch to avoid N+1 without JOIN
func (db *DB) GetOrderCountsForUsers(ctx context.Context, userIDs []int) (map[int]int, error) {
    const q = `
        SELECT user_id, COUNT(*) AS order_count
        FROM orders
        WHERE user_id = ANY($1)
        GROUP BY user_id
    `
    rows, err := db.pool.Query(ctx, q, userIDs)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    counts := make(map[int]int)
    for rows.Next() {
        var userID, count int
        if err := rows.Scan(&userID, &count); err != nil {
            return nil, err
        }
        counts[userID] = count
    }
    return counts, rows.Err()
}
```

---

### Node.js + Express (Prisma + Knex)

```javascript
// migrations/20240115_add_indexes.sql
/*
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_uid_status_cat
    ON orders (user_id, status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_lower_email
    ON users (lower(email));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_pending
    ON jobs (created_at)
    WHERE status = 'pending';
*/

// --- Using Prisma ---
// schema.prisma
/*
model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  name      String
  orders    Order[]
  deletedAt DateTime? @map("deleted_at")

  @@index([email])  // Prisma index declaration
}

model Order {
  id          Int      @id @default(autoincrement())
  userId      Int      @map("user_id")
  status      String
  totalAmount Decimal  @map("total_amount")
  createdAt   DateTime @default(now()) @map("created_at")
  user        User     @relation(fields: [userId], references: [id])

  @@index([userId, status, createdAt])  // composite index
}
*/

// N+1 BAD — Prisma lazy loading equivalent
async function getUsersWithOrdersBad(prisma) {
  const users = await prisma.user.findMany({ take: 100 });

  // N additional queries — each for loop iteration hits the DB
  for (const user of users) {
    const orderCount = await prisma.order.count({
      where: { userId: user.id },
    });
    console.log(`${user.name}: ${orderCount} orders`);
  }
}

// N+1 FIXED — Prisma include (eager load)
async function getUsersWithOrdersGood(prisma) {
  const users = await prisma.user.findMany({
    take: 100,
    where: { deletedAt: null },
    include: {
      _count: {
        select: { orders: true },
      },
      // If you need actual orders:
      // orders: { where: { status: 'paid' }, select: { id: true, totalAmount: true } }
    },
    orderBy: { createdAt: 'desc' },
  });
  // Prisma generates: SELECT with a subquery or JOIN — 1 or 2 queries total
  return users;
}

// N+1 FIXED — Raw SQL with Knex for complex aggregation
const knex = require('knex')({ client: 'pg', connection: process.env.DATABASE_URL });

async function getUsersWithTotalSpent() {
  return knex('users as u')
    .select(
      'u.id',
      'u.name',
      knex.raw('COUNT(o.id) AS order_count'),
      knex.raw('COALESCE(SUM(o.total_amount), 0) AS total_spent')
    )
    .leftJoin('orders as o', function () {
      this.on('o.user_id', '=', 'u.id').andOn(
        knex.raw("o.status = 'paid'")
      );
    })
    .whereNull('u.deleted_at')
    .groupBy('u.id', 'u.name')
    .orderBy('total_spent', 'desc')
    .limit(100);
}

// EXPLAIN ANALYZE helper
async function explainQuery(knex, queryBuilder) {
  const { sql, bindings } = queryBuilder.toSQL().toNative();
  const result = await knex.raw(
    `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) ${sql}`,
    bindings
  );
  console.log(result.rows.map(r => r['QUERY PLAN']).join('\n'));
}

// Express route with proper index usage
const express = require('express');
const router = express.Router();

router.get('/users', async (req, res) => {
  try {
    // This query uses idx_users_lower_email expression index
    const { email } = req.query;
    if (email) {
      const user = await knex('users')
        .whereRaw('lower(email) = lower(?)', [email])
        .whereNull('deleted_at')
        .first();
      return res.json(user);
    }

    // This uses idx_orders_uid_status_cat composite index
    const orders = await knex('orders')
      .where({ user_id: req.user.id, status: 'paid' })
      .where('created_at', '>', knex.raw("NOW() - INTERVAL '30 days'"))
      .orderBy('created_at', 'desc');

    res.json(orders);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
```

---

### Python + FastAPI (SQLAlchemy)

```python
from __future__ import annotations
from typing import Any
from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, ForeignKey,
    Index, func, text, select, and_, case
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship, selectinload, joinedload
from fastapi import FastAPI, Depends

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    orders = relationship("Order", back_populates="user", lazy="raise")
    # lazy="raise" prevents accidental lazy loading — forces explicit eager loading

    __table_args__ = (
        # Expression index for case-insensitive email lookup
        Index("idx_users_lower_email", func.lower(email)),
        # Partial index: only active users
        Index(
            "idx_users_email_active",
            email,
            postgresql_where=text("deleted_at IS NULL")
        ),
    )

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="orders")

    __table_args__ = (
        # Composite index: user + status + date (leftmost prefix rule)
        Index("idx_orders_uid_status_cat", "user_id", "status", "created_at"),
    )

# ─── N+1 BAD — lazy loading triggers per-user query ───────────────────────────
async def get_users_bad(session: AsyncSession) -> list[dict]:
    result = await session.execute(select(User).limit(100))
    users = result.scalars().all()

    data = []
    for user in users:
        # Each of these triggers: SELECT COUNT(*) FROM orders WHERE user_id = ?
        count_result = await session.execute(
            select(func.count()).where(Order.user_id == user.id)
        )
        data.append({"user": user.name, "orders": count_result.scalar()})
    return data  # 101 queries total

# ─── N+1 FIXED — joinedload / selectinload ────────────────────────────────────
async def get_users_with_orders_joinedload(session: AsyncSession):
    """Single JOIN query — good for small result sets."""
    result = await session.execute(
        select(User)
        .options(joinedload(User.orders))
        .where(User.deleted_at.is_(None))
        .limit(100)
    )
    # Returns User objects with orders pre-populated — no extra queries
    return result.unique().scalars().all()

async def get_users_with_orders_selectinload(session: AsyncSession):
    """Two queries total — better for large collections (avoids Cartesian product)."""
    result = await session.execute(
        select(User)
        .options(selectinload(User.orders))
        .where(User.deleted_at.is_(None))
        .limit(100)
    )
    # Query 1: SELECT * FROM users ... LIMIT 100
    # Query 2: SELECT * FROM orders WHERE user_id IN (1,2,...,100)
    return result.scalars().all()

# ─── N+1 FIXED — aggregate JOIN ────────────────────────────────────────────────
async def get_users_with_stats(session: AsyncSession) -> list[dict[str, Any]]:
    """Single query with aggregation — most efficient."""
    stmt = (
        select(
            User.id,
            User.name,
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_spent"),
        )
        .outerjoin(Order, and_(Order.user_id == User.id, Order.status == "paid"))
        .where(User.deleted_at.is_(None))
        .group_by(User.id, User.name)
        .order_by(text("total_spent DESC"))
        .limit(100)
    )
    result = await session.execute(stmt)
    return [row._asdict() for row in result]

# ─── EXPLAIN helper ───────────────────────────────────────────────────────────
async def explain_query(session: AsyncSession, stmt) -> str:
    """Run EXPLAIN ANALYZE on any SQLAlchemy select statement."""
    compiled = stmt.compile(dialect=session.bind.dialect)
    explain_sql = text(
        f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {compiled}"
    )
    result = await session.execute(explain_sql)
    lines = [row[0] for row in result]
    return "\n".join(lines)

# ─── FastAPI routes ───────────────────────────────────────────────────────────
app = FastAPI()

async def get_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with AsyncSession(engine) as session:
        yield session

@app.get("/users/stats")
async def users_stats(session: AsyncSession = Depends(get_session)):
    return await get_users_with_stats(session)

@app.get("/users/search")
async def search_user(email: str, session: AsyncSession = Depends(get_session)):
    # Uses idx_users_lower_email expression index
    result = await session.execute(
        select(User).where(
            func.lower(User.email) == email.lower(),
            User.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()
```

---

## 6. Common Patterns & Best Practices

**Index design checklist:**
1. Index every foreign key column (PostgreSQL does NOT do this automatically)
2. Index columns used in `WHERE`, `JOIN ON`, `ORDER BY`, `GROUP BY`
3. Put high-selectivity columns first in composite indexes
4. Equality columns before range columns in composites
5. Use partial indexes for filtered subsets (active records, pending queues)
6. Use covering indexes (`INCLUDE`) for frequently-executed read-only queries
7. Use expression indexes when you always query with a function (e.g., `lower(email)`)

**Index maintenance:**
```sql
-- Check unused indexes (candidates for removal)
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelname NOT LIKE 'pk_%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check index hit rates
SELECT 
    relname, 
    100 * idx_scan / NULLIF(seq_scan + idx_scan, 0) AS index_usage_pct
FROM pg_stat_user_tables
ORDER BY index_usage_pct ASC;
```

**Query patterns to always check:**
- `SELECT *` → select only needed columns
- ORM queries in loops → eager load or batch
- No `LIMIT` on large tables → always paginate
- Functions in WHERE on indexed columns → rewrite predicate
- Missing WHERE on soft-deleted records → partial index + always include in WHERE

---

## 7. Common Pitfalls

| Pitfall | Problem | Fix |
|---|---|---|
| `WHERE DATE(created_at) = ?` | Breaks index on `created_at` | Rewrite as range: `>= date AND < date + 1` |
| ORM lazy loading in loops | N+1 queries | Use `joinedload` / `selectinload` / `include` |
| Indexing every column | Slows writes, wastes space | Index strategically for actual query patterns |
| Missing FK indexes | Every FK lookup is a seq scan | `CREATE INDEX ON child_table(fk_column)` |
| Index not used after ANALYZE | Stale statistics | Run `ANALYZE table_name` |
| `SELECT *` with covering index | Fetches heap anyway | Select only indexed columns for index-only scan |
| `REINDEX` in production | Locks table for duration | Use `REINDEX CONCURRENTLY` (PG12+) |
| Adding index without CONCURRENTLY | Locks writes | `CREATE INDEX CONCURRENTLY` |
| Forgetting `NULLS LAST` | NULLs sort to top, index may not help ORDER BY | `CREATE INDEX ON t (col DESC NULLS LAST)` |
| Index on boolean column | Nearly useless (only 2 values) | Use partial index instead |

---

## 8. Interview Questions & Model Answers

**Q: What is a composite index and explain the leftmost prefix rule?**

A composite index indexes multiple columns together, stored in left-to-right sort order. The leftmost prefix rule means the query planner can only use the index if the query filters on the leading columns of the index. For an index on `(user_id, status, created_at)`, queries filtering on `user_id` or `user_id + status` can use it, but a query filtering only on `status` cannot — because without constraining the first column, the planner cannot determine which part of the B-tree to descend into. Think of a phone book sorted by (last_name, first_name): you can efficiently find all Smiths, but you can't efficiently find all Johns without scanning everything.

**Q: What is the N+1 problem and how do you solve it?**

N+1 occurs when you fetch N records in one query, then execute an additional query for each record. For example, fetch 100 users then loop and query each user's order count — 101 queries. It's deadly because even at 1ms per query, 101 queries = 101ms minimum. Solutions: (1) JOIN the related table in the original query with aggregation, (2) fetch all related records in a second batch query using `WHERE id IN (...)`, (3) use ORM eager loading (`joinedload`, `include`, `preload`) which generates the batch query automatically.

**Q: When would you use a partial index?**

When a significant portion of the table never needs to be indexed. Classic cases: index only active users where `deleted_at IS NULL` (if 80% of users are deleted, the partial index is 5× smaller), index only pending jobs where `status = 'pending'` (once completed, jobs leave the index), or index only large orders where `total > 10000`. The query must include the index predicate in its WHERE clause for the planner to use the partial index.

**Q: What is a covering index?**

An index that contains all columns needed to answer a query — allowing an index-only scan that never touches the heap (actual table rows). In PostgreSQL, use `INCLUDE` to add non-key columns to a B-tree's leaf pages: `CREATE INDEX ON users (email) INCLUDE (id, name)`. An index-only scan on a covering index is the fastest possible read path because it avoids a round-trip to the heap entirely. It requires the visibility map to confirm the heap pages are all-visible; run VACUUM to keep the visibility map current.

**Q: What does EXPLAIN ANALYZE tell you that EXPLAIN doesn't?**

`EXPLAIN` shows the query plan with cost *estimates* based on statistics — what the planner *thinks* will happen. `EXPLAIN ANALYZE` actually **executes** the query and shows `actual time` and `actual rows`. This reveals: (1) mismatches between estimated and actual row counts (indicating stale statistics), (2) actual execution time in milliseconds, (3) how many times each plan node ran (loops), (4) with `BUFFERS`: how many pages were served from cache vs read from disk. Stale stats causing the planner to expect 1 row but get 10,000 is a common source of bad query plans.

**Q: Why can putting a function call on a column in WHERE break index usage?**

The index stores the raw column values. If you write `WHERE DATE(created_at) = '2024-01-15'`, PostgreSQL has to evaluate `DATE(created_at)` for every row to compare it — it cannot use the B-tree on `created_at` to jump directly to matching rows because the index doesn't contain `DATE(created_at)` values. The fix is to rewrite the predicate as a range on the original column: `WHERE created_at >= '2024-01-15' AND created_at < '2024-01-16'`. Alternatively, create an expression index: `CREATE INDEX ON events (DATE(created_at))` — then `WHERE DATE(created_at) = ?` will use it.

**Q: How does a B-tree index work internally?**

A B-tree is a self-balancing tree where all leaves are at the same depth. Internal nodes contain separator keys and pointers to child nodes. Leaf nodes contain the actual indexed values alongside TIDs (heap row pointers). The leaves are linked in a doubly-linked list, enabling efficient range scans after the initial tree traversal. For a lookup of value V: start at the root, at each internal node binary-search the separator keys to determine which child pointer to follow, descend to the leaf, find V (or report not found). For a range query: find the start value via tree traversal, then scan forward through linked leaves until the range is exhausted. Insert and delete maintain balance by splitting/merging nodes as needed. Typical depth for hundreds of millions of rows is 4-5 levels.

---

## 9. Resources

- [PostgreSQL Documentation: Indexes](https://www.postgresql.org/docs/current/indexes.html)
- [PostgreSQL Documentation: Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- [Use the Index, Luke](https://use-the-index-luke.com/) — The definitive guide to SQL indexing
- [explain.depesz.com](https://explain.depesz.com/) — EXPLAIN ANALYZE visualizer
- [pganalyze Index Advisor](https://pganalyze.com/index-advisor) — Automated index recommendations
- [The Art of PostgreSQL](https://theartofpostgresql.com/) — Dimitri Fontaine
- [High Performance PostgreSQL for Rails](https://pragprog.com/titles/aapsql/high-performance-postgresql-for-rails/) — Andrew Atkinson

---

**Next:** [Part 7.2: Sharding, Replication & Connection Pooling](./07-sharding-replication-pooling.md)
