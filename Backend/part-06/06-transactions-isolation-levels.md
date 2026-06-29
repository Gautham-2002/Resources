# Part 6.2: Transactions & Isolation Levels

## What You'll Learn

- How transactions work: BEGIN / COMMIT / ROLLBACK / SAVEPOINT
- Distributed transactions: two-phase commit, and why the Saga pattern exists
- Optimistic vs pessimistic locking, and when to use each
- SELECT FOR UPDATE — row-level locks and deadlocks
- All four isolation levels with concrete anomaly examples
- The famous isolation matrix table (dirty reads, non-repeatable reads, phantom reads, write skew)
- PostgreSQL's MVCC — how it eliminates read locks without sacrificing correctness
- Practical patterns: deadlock retry, optimistic locking with version columns, avoiding the check-then-act anti-pattern
- Full implementations in Go (pgx), Node.js (pg), Python (SQLAlchemy)

---

## Table of Contents

1. [Transactions — Fundamentals](#1-transactions--fundamentals)
   - 1.1 BEGIN / COMMIT / ROLLBACK
   - 1.2 Savepoints
   - 1.3 Multi-Statement Transactions
2. [Distributed Transactions](#2-distributed-transactions)
   - 2.1 Two-Phase Commit (2PC)
   - 2.2 Why 2PC is Problematic
   - 2.3 Saga Pattern (Preview)
3. [Locking](#3-locking)
   - 3.1 Pessimistic Locking — SELECT FOR UPDATE
   - 3.2 Optimistic Locking — Version Columns
   - 3.3 Deadlocks — Cause, Detection, Prevention
   - 3.4 Long-Running Transactions
4. [Isolation Levels (Deep)](#4-isolation-levels-deep)
   - 4.1 Read Uncommitted
   - 4.2 Read Committed
   - 4.3 Repeatable Read
   - 4.4 Serializable
   - 4.5 The Isolation Level Matrix
   - 4.6 Concrete Anomaly Examples
5. [PostgreSQL Specifics](#5-postgresql-specifics)
   - 5.1 MVCC — Multi-Version Concurrency Control
   - 5.2 Snapshot Isolation
   - 5.3 Setting Isolation Level Per Transaction
   - 5.4 PostgreSQL's Surprising Read Committed Behavior
6. [Practical Patterns](#6-practical-patterns)
   - 6.1 When to Use Serializable
   - 6.2 Deadlock Retry Logic
   - 6.3 The Check-Then-Act Anti-Pattern
   - 6.4 Optimistic Locking Pattern
7. [Implementation Examples](#7-implementation-examples)
   - Go + pgx
   - Node.js + pg
   - Python + SQLAlchemy
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Interview Questions & Answers](#interview-questions--answers)
11. [Resources](#resources)

---

## 1. Transactions — Fundamentals

### 1.1 BEGIN / COMMIT / ROLLBACK

A transaction is a sequence of SQL statements treated as a single unit of work. Either all statements succeed (COMMIT), or all are undone (ROLLBACK).

```sql
BEGIN;                              -- start transaction

UPDATE accounts
SET balance = balance - 500
WHERE id = 'acc_alice';

UPDATE accounts
SET balance = balance + 500
WHERE id = 'acc_bob';

COMMIT;                             -- make both changes permanent
```

If the second UPDATE fails (e.g., `acc_bob` doesn't exist), the database error causes the transaction to enter an error state. Any further commands in the transaction return `ERROR: current transaction is aborted`. You must ROLLBACK to clean up.

```sql
BEGIN;

UPDATE accounts SET balance = balance - 500 WHERE id = 'acc_alice';
-- ERROR: column "invalid" does not exist (hypothetical mistake)

-- Transaction is now aborted. You cannot run more queries.
ROLLBACK;  -- undo the first UPDATE as well
```

**Autocommit behavior:**

In PostgreSQL, each statement outside a `BEGIN` block is implicitly wrapped in its own transaction (`AUTOCOMMIT = ON` by default in psql and most drivers). This means a standalone `UPDATE` is automatically committed immediately.

Most application database drivers operate differently:
- `pg` (Node.js): autocommit mode by default; wrap in `client.query('BEGIN')` for multi-statement transactions
- `pgx` (Go): each `Exec`/`Query` is auto-committed unless you explicitly begin a `Tx`
- SQLAlchemy: by default wraps everything in a transaction that you must `session.commit()` or `session.rollback()`

**Implicit vs explicit transactions:**

```python
# SQLAlchemy implicit transaction (session auto-begins)
order = session.get(Order, order_id)
order.status = "shipped"
await session.commit()   # commits the implicit transaction

# Explicit transaction
async with session.begin():
    order = await session.get(Order, order_id)
    order.status = "shipped"
    # auto-committed on exiting the `begin()` context manager
```

### 1.2 Savepoints

A savepoint is a named point within a transaction that you can roll back to without aborting the entire transaction.

```sql
BEGIN;

INSERT INTO orders (id, user_id, total) VALUES (1, 42, 99.99);
SAVEPOINT order_inserted;

INSERT INTO order_items (order_id, product_id, qty) VALUES (1, 10, 2);
SAVEPOINT item_1_inserted;

-- Attempt to insert a second item — might fail due to stock check
INSERT INTO order_items (order_id, product_id, qty) VALUES (1, 99, 1);
-- Suppose this fails: product 99 is out of stock

-- Roll back ONLY the failed item insert, keep everything before the savepoint
ROLLBACK TO SAVEPOINT item_1_inserted;

-- Continue with the rest of the order
UPDATE orders SET status = 'partial' WHERE id = 1;

COMMIT;  -- commits the order + first item, not the failed second item
```

**When savepoints are useful:**
- Bulk insert with error skipping — insert records one by one; on constraint violation, rollback to savepoint and continue
- Nested service calls where an inner operation might fail without invalidating the outer operation
- Complex multi-step workflows where partial completion is valid

**Savepoint overhead:** Savepoints add some overhead (PostgreSQL must track the savepoint state). Don't use them unless you actually need partial rollback.

**Released savepoints:**

```sql
SAVEPOINT sp1;
-- ... do work ...
RELEASE SAVEPOINT sp1;  -- declare "I don't need to roll back to here anymore"
                        -- reduces memory overhead for long transactions with many savepoints
```

### 1.3 Multi-Statement Transactions

Transactions can span as many statements as needed, but longer transactions have costs:

```sql
BEGIN;

-- 1. Reserve inventory
UPDATE products
SET stock = stock - $qty
WHERE id = $product_id AND stock >= $qty;

-- Check if update succeeded (stock was available)
-- (Application layer checks affected rows)

-- 2. Create the order
INSERT INTO orders (user_id, product_id, qty, total)
VALUES ($user_id, $product_id, $qty, $price * $qty)
RETURNING id;

-- 3. Charge the payment (application-level: call payment API)
-- If payment fails, ROLLBACK here

-- 4. Create shipping record
INSERT INTO shipments (order_id, address, status)
VALUES ($order_id, $address, 'pending');

COMMIT;
```

**The transaction boundary problem with external services:**

Once you call an external API (payment processor, email service) inside a transaction, you can no longer cleanly rollback if the external call succeeds but a later DB step fails. The external action is not part of the transaction. This is a fundamental challenge that motivates the Saga pattern.

---

## 2. Distributed Transactions

When a transaction needs to span multiple databases or services (e.g., update the `orders` DB and the `inventory` DB atomically), you can't use a single `BEGIN/COMMIT`. This is the distributed transaction problem.

### 2.1 Two-Phase Commit (2PC)

2PC is the classic solution. It uses a coordinator to orchestrate the commit across all participating nodes.

```
Phase 1 — Prepare:
Coordinator ──► Participant A: "Can you commit?"
Coordinator ──► Participant B: "Can you commit?"
                                    │
              ◄── A: "Yes, prepared" │
              ◄── B: "Yes, prepared" │
                   (Both have written to WAL, ready to commit)

Phase 2 — Commit:
Coordinator ──► Participant A: "Commit!"
Coordinator ──► Participant B: "Commit!"
              ◄── A: "Done"
              ◄── B: "Done"
```

**If any participant says "No" in Phase 1:** Coordinator sends `ROLLBACK` to all participants.

**If coordinator crashes between Phase 1 and Phase 2:** Participants are stuck in "prepared" state — they've promised to commit but have not received the instruction. They hold their locks indefinitely. This is the **blocking problem** of 2PC.

### 2.2 Why 2PC is Problematic

| Problem | Description |
|---------|-------------|
| **Blocking on coordinator failure** | Participants in "prepared" state hold locks waiting for the coordinator to recover |
| **Latency** | Two network round-trips (prepare + commit) for every transaction |
| **Single point of failure** | Coordinator failure blocks all in-flight transactions |
| **Scalability** | Each participant holds locks longer (until 2PC completes), reducing concurrency |

PostgreSQL supports 2PC via `PREPARE TRANSACTION` / `COMMIT PREPARED`, but it's rarely used directly in application code. XA transactions (used by Java EE application servers) implement 2PC.

### 2.3 Saga Pattern (Preview)

The Saga pattern avoids distributed transactions by breaking a distributed operation into a sequence of local transactions, each with a compensating transaction for rollback.

```
Order Saga:
Step 1: Reserve inventory    → Compensating: Release inventory
Step 2: Charge payment       → Compensating: Refund payment
Step 3: Create order record  → Compensating: Cancel order record
Step 4: Send confirmation    → (best-effort, no compensation needed)

If Step 3 fails:
  ← Run Step 2 compensation: Refund payment
  ← Run Step 1 compensation: Release inventory
```

There are two Saga implementation styles:
- **Choreography**: Each service publishes events; other services react to events (no central coordinator)
- **Orchestration**: A Saga orchestrator (a service or workflow engine) explicitly invokes each step and compensation

Sagas trade atomicity for availability. The system is never in an atomic locked state — intermediate states exist. This requires careful design of compensating actions and idempotency.

---

## 3. Locking

### 3.1 Pessimistic Locking — SELECT FOR UPDATE

`SELECT FOR UPDATE` acquires a row-level exclusive lock when reading, preventing other transactions from modifying (or SELECT FOR UPDATE-ing) the same rows until the lock is released on commit/rollback.

```sql
BEGIN;

-- Lock the product row: no one else can modify this row until we COMMIT
SELECT id, stock
FROM products
WHERE id = $1
FOR UPDATE;   -- row is now locked

-- Use the result in application logic to check stock
-- ... application checks if stock >= qty ...

-- Safely decrement stock (no concurrent transaction can have modified it)
UPDATE products SET stock = stock - $qty WHERE id = $1;

COMMIT;  -- lock released
```

**Variants:**

| Variant | Behavior |
|---------|----------|
| `FOR UPDATE` | Exclusive lock — no concurrent reads-for-update or writes |
| `FOR NO KEY UPDATE` | Weaker exclusive lock — allows concurrent FK checks |
| `FOR SHARE` | Shared lock — allows concurrent reads but prevents writes |
| `FOR KEY SHARE` | Weakest — only prevents DELETE and SELECT FOR UPDATE |
| `NOWAIT` | Fails immediately if row is locked (instead of waiting) |
| `SKIP LOCKED` | Skips locked rows instead of waiting — useful for queue processing |

**SKIP LOCKED — job queue pattern:**

```sql
-- Multiple workers processing a job queue without conflicts
BEGIN;
SELECT id, payload
FROM jobs
WHERE status = 'pending'
ORDER BY created_at
LIMIT 1
FOR UPDATE SKIP LOCKED;   -- skip any rows locked by other workers

-- Process the job...
UPDATE jobs SET status = 'processing', worker_id = $worker_id WHERE id = $job_id;
COMMIT;
```

### 3.2 Optimistic Locking — Version Columns

Optimistic locking assumes conflicts are rare. Instead of locking a row on read, you check whether it was modified by the time you write. If it was, retry.

**Implementation with a `version` column:**

```sql
CREATE TABLE products (
    id      UUID PRIMARY KEY,
    stock   INT NOT NULL,
    version INT NOT NULL DEFAULT 1   -- incremented on every update
);

-- Read:
SELECT id, stock, version FROM products WHERE id = $1;
-- Returns: { id: 'p1', stock: 100, version: 5 }

-- Write (include version in WHERE clause):
UPDATE products
SET stock = $new_stock, version = version + 1
WHERE id = $1
  AND version = $expected_version;   -- only update if version hasn't changed

-- Check affected rows:
-- If rowsAffected == 1: success (no concurrent modification)
-- If rowsAffected == 0: conflict — someone else updated it; retry
```

**When to use pessimistic vs optimistic:**

| Scenario | Recommendation | Reason |
|----------|----------------|--------|
| Bank account balance update | Pessimistic (SELECT FOR UPDATE) | Conflicts very likely under load |
| Product stock decrement | Pessimistic | Inventory is contended resource |
| User profile update | Optimistic | Conflicts rare; lock overhead not worth it |
| Document editing (long sessions) | Optimistic | Can't hold a lock for hours |
| Job queue processing | SELECT FOR UPDATE SKIP LOCKED | Designed for exactly this pattern |
| Report generation (read-heavy) | Neither | MVCC handles read isolation |

### 3.3 Deadlocks — Cause, Detection, Prevention

A deadlock occurs when two (or more) transactions each hold a lock the other needs, creating a circular wait.

```
Transaction T1:                     Transaction T2:
LOCK row A (success)                LOCK row B (success)
LOCK row B (waiting for T2)         LOCK row A (waiting for T1)
    ↑                                   ↑
    └───────────── circular wait ───────┘
```

**Concrete example — transfers:**

```
T1: Transfer $100 from account A to account B
    → LOCK account A
    → waiting to LOCK account B (held by T2)

T2: Transfer $100 from account B to account A
    → LOCK account B
    → waiting to LOCK account A (held by T1)
```

**PostgreSQL deadlock detection:**

PostgreSQL detects deadlocks automatically using a background process. When a deadlock is detected, PostgreSQL aborts one of the transactions (the one with lower cost), and the other proceeds. You'll see:

```
ERROR: deadlock detected
DETAIL: Process 12345 waits for ShareLock on transaction 6789;
        blocked by process 23456.
        Process 23456 waits for ShareLock on transaction 12345;
        blocked by process 12345.
HINT: See server log for query details.
```

**Prevention strategies:**

1. **Consistent lock ordering:** Always acquire locks in the same order across all transactions. In the transfers example: always lock the lower account ID first.

```sql
-- Always lock lower ID first
SELECT * FROM accounts
WHERE id IN ($id1, $id2)
ORDER BY id
FOR UPDATE;
```

2. **Short transactions:** The shorter your transactions, the shorter the lock hold time, the lower the deadlock probability.

3. **Reduce lock scope:** Use `FOR NO KEY UPDATE` or `FOR SHARE` instead of `FOR UPDATE` when you don't need exclusive locks.

4. **Retry on deadlock:** Application code must handle `pgconn.PgError` code `40P01` (deadlock) and retry.

### 3.4 Long-Running Transactions — Why They're Dangerous

Long-running transactions in PostgreSQL cause several serious problems:

**1. Table bloat (VACUUM blocking):**

PostgreSQL's MVCC creates new row versions on every update. Old row versions (dead tuples) are cleaned up by `VACUUM`. But `VACUUM` cannot remove any dead tuple that's still visible to any open transaction. A transaction open for hours prevents vacuum from cleaning up, causing table bloat.

```
T1: BEGIN; -- opens transaction, gets snapshot
    ... forgets to commit for 2 hours ...

VACUUM: cannot remove dead tuples visible to T1's snapshot
Result: dead tuples accumulate → table bloat → slower full scans
```

**2. Lock accumulation:**

Long transactions hold all acquired locks until commit. Other transactions wanting those rows must wait.

**3. Replication lag:**

In hot standby mode, PostgreSQL replication can lag because the replica must keep data consistent with all open transactions on the primary.

**Best practice:** Set `statement_timeout` and `idle_in_transaction_session_timeout` to kill runaway transactions:

```sql
-- Kill any statement running longer than 30 seconds
SET statement_timeout = '30s';

-- Kill sessions that have been idle inside a transaction for longer than 5 minutes
SET idle_in_transaction_session_timeout = '5min';
```

---

## 4. Isolation Levels (Deep)

Isolation levels define how much a transaction is isolated from the effects of other concurrent transactions. There are four standard levels (SQL-92), each preventing some anomalies but allowing others.

### 4.1 Read Uncommitted

The weakest isolation level. Transactions can read uncommitted data from other transactions (dirty reads).

**PostgreSQL note:** PostgreSQL does not actually implement Read Uncommitted — it silently upgrades it to Read Committed. PostgreSQL's MVCC makes dirty reads impossible without significant performance cost.

### 4.2 Read Committed

The default in PostgreSQL. A query sees only data committed before the query began (not before the transaction began).

**Key property:** Each statement gets a fresh snapshot of committed data, but different statements in the same transaction can see different data.

```
Transaction T1:                     Transaction T2:
BEGIN;
SELECT balance FROM accounts
WHERE id = 1;  -- sees $100

                                    BEGIN;
                                    UPDATE accounts
                                    SET balance = 200
                                    WHERE id = 1;
                                    COMMIT;

-- T1 runs same query AGAIN
SELECT balance FROM accounts
WHERE id = 1;  -- sees $200 (T2 committed between the two reads!)
COMMIT;
```

This is a **non-repeatable read** — same query, same transaction, different result. Read Committed allows this. It's the trade-off for better concurrency.

### 4.3 Repeatable Read

Once a transaction reads a row, it will always see the same version of that row (even if other transactions commit changes to it).

```
Transaction T1 (Repeatable Read):   Transaction T2:
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SELECT balance FROM accounts
WHERE id = 1;  -- sees $100

                                    BEGIN;
                                    UPDATE accounts
                                    SET balance = 200
                                    WHERE id = 1;
                                    COMMIT;

SELECT balance FROM accounts
WHERE id = 1;  -- STILL sees $100 (snapshot from start of T1)
COMMIT;
```

**No non-repeatable reads.** But Phantom Reads are still possible in standard SQL — a re-executed query that returns a set of rows can return more/fewer rows if another transaction inserted/deleted rows matching the query's `WHERE` clause.

**PostgreSQL note:** PostgreSQL's Repeatable Read also prevents phantom reads (unlike the SQL standard which only requires it at Serializable). PostgreSQL uses MVCC snapshots, and the snapshot is taken at the start of the first statement in the transaction — preventing both non-repeatable reads and phantom reads.

### 4.4 Serializable

The strongest isolation level. Transactions execute as if they ran serially, one after another. No concurrency anomalies of any kind.

PostgreSQL implements Serializable via **Serializable Snapshot Isolation (SSI)** — a novel algorithm that allows true concurrency while detecting and aborting transactions that would violate serializable execution. When a violation is detected, PostgreSQL returns:

```
ERROR: could not serialize access due to read/write dependencies among transactions
HINT: The transaction might succeed if retried.
```

Application code must be prepared to retry transactions aborted due to serialization failures.

**Performance:** Serializable has a small overhead (~3-5% throughput reduction in pg benchmarks for typical workloads). For high-contention workloads with many concurrent transactions touching the same data, the retry overhead can be significant.

### 4.5 The Isolation Level Matrix

| Isolation Level | Dirty Read | Non-Repeatable Read | Phantom Read | Write Skew |
|----------------|:-----------:|:-------------------:|:------------:|:----------:|
| Read Uncommitted | Possible | Possible | Possible | Possible |
| Read Committed | Prevented | Possible | Possible | Possible |
| Repeatable Read | Prevented | Prevented | Possible (PG: No) | Possible |
| Serializable | Prevented | Prevented | Prevented | Prevented |

> **For PostgreSQL specifically:**
> - Read Uncommitted is treated as Read Committed (MVCC)
> - Repeatable Read prevents phantom reads (beyond the SQL standard)
> - Serializable uses SSI — prevents all anomalies including write skew

### 4.6 Concrete Anomaly Examples

#### Dirty Read (prevented at Read Committed and above)

```
T1 reads data written by T2 before T2 commits.
If T2 rolls back, T1 has read "ghost" data that never existed.

T1:                              T2:
BEGIN;                           BEGIN;
                                 UPDATE products SET price = 0 WHERE id = 1;
SELECT price FROM products
WHERE id = 1;  -- reads $0 (!)    -- T2 has not committed yet
                                 ROLLBACK; -- T2 rolls back
-- T1 used price = $0 in a calculation, but that price never officially existed
```

#### Non-Repeatable Read (prevented at Repeatable Read and above)

```
T1 reads a row twice; T2 commits an update between the two reads.

T1 (Read Committed):             T2:
BEGIN;
SELECT stock FROM products
WHERE id = 1;  -- stock = 50

                                 BEGIN;
                                 UPDATE products SET stock = 30 WHERE id = 1;
                                 COMMIT;

SELECT stock FROM products
WHERE id = 1;  -- stock = 30 (!!)
-- T1 sees different value for same row in same transaction
```

#### Phantom Read (prevented at Serializable; PG's Repeatable Read also prevents it)

```
T1 runs a query twice; T2 inserts rows matching T1's filter between the two queries.

T1 (Repeatable Read standard SQL):  T2:
BEGIN;
SELECT COUNT(*) FROM orders
WHERE user_id = 42;  -- returns 5

                                    BEGIN;
                                    INSERT INTO orders (user_id, total)
                                    VALUES (42, 99.99);
                                    COMMIT;

SELECT COUNT(*) FROM orders
WHERE user_id = 42;  -- returns 6 (!) in standard SQL Repeatable Read
                                    -- BUT: PostgreSQL Repeatable Read returns 5
                                    -- PostgreSQL uses full snapshot isolation
COMMIT;
```

#### Write Skew (prevented only at Serializable)

Write skew is the subtlest anomaly. Two transactions each read some data, make a decision based on what they read, and write changes — but the combined effect violates an invariant that each transaction individually verified.

**Classic example — On-call doctors:**

A hospital requires at least one doctor to be on-call at all times. There are currently 2 doctors on-call (Alice and Bob).

```
T1 (Alice taking a break):          T2 (Bob taking a break):
BEGIN;                               BEGIN;
SELECT COUNT(*) FROM on_call
WHERE on_shift = true;               SELECT COUNT(*) FROM on_call
-- returns 2 (Alice + Bob)           WHERE on_shift = true;
                                     -- returns 2 (Alice + Bob)

-- Count >= 2, safe for Alice       -- Count >= 2, safe for Bob
-- to take a break                  -- to take a break

UPDATE on_call                       UPDATE on_call
SET on_shift = false                 SET on_shift = false
WHERE doctor = 'Alice';              WHERE doctor = 'Bob';

COMMIT;                              COMMIT;

-- RESULT: 0 doctors on-call! Invariant violated.
-- Each transaction independently verified the constraint,
-- but their combined effect breaks it.
```

Neither transaction reads uncommitted data. Neither reads stale data (both read 2, both committed before the other's write). But the combined effect is wrong.

**Other write skew examples:**
- Double-booking: two users book the last seat on a flight concurrently
- Overdraft: two concurrent withdrawals, each checking sufficient balance independently
- Unique username: two users register the same username simultaneously (must use DB UNIQUE constraint)

**Fix:** Use Serializable isolation or explicit locking (`SELECT FOR UPDATE` on all rows being checked):

```sql
-- Serializable (PostgreSQL will detect and abort one transaction)
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SELECT COUNT(*) FROM on_call WHERE on_shift = true FOR UPDATE;
-- ... check count >= 2 ...
UPDATE on_call SET on_shift = false WHERE doctor = 'Alice';
COMMIT;
```

#### Lost Update (can occur at Read Committed)

```
T1 and T2 both read a value, both compute a new value, both write — one overwrites the other.

T1:                                 T2:
SELECT views FROM posts
WHERE id = 1;  -- views = 100

                                    SELECT views FROM posts
                                    WHERE id = 1;  -- views = 100

UPDATE posts SET views = 101
WHERE id = 1;

                                    UPDATE posts SET views = 101
                                    WHERE id = 1;
                                    -- Overwrites T1's write; net result is 101
                                    -- Should be 102 (both increments counted)
COMMIT;                             COMMIT;
```

Fix using atomic update (never read-then-write when incrementing):

```sql
-- Atomic: always use this pattern for increments
UPDATE posts SET views = views + 1 WHERE id = 1;
```

Or use `SELECT FOR UPDATE` if you must read the value first.

---

## 5. PostgreSQL Specifics

### 5.1 MVCC — Multi-Version Concurrency Control

PostgreSQL never overwrites a row in place. Every `UPDATE` creates a new version of the row (a new "tuple") and marks the old version as expired. Every `DELETE` marks the row as expired. Reads see the appropriate version based on their snapshot.

```
Row in heap (simplified):
┌──────────────────────────────────────────────────────────────────┐
│ xmin=100  xmax=∞    data: { stock: 100 }  ← current live version │
└──────────────────────────────────────────────────────────────────┘

After UPDATE by transaction 200:
┌──────────────────────────────────────────────────────────────────┐
│ xmin=100  xmax=200  data: { stock: 100 }  ← dead (expired by T200)│
│ xmin=200  xmax=∞    data: { stock: 90 }   ← new live version     │
└──────────────────────────────────────────────────────────────────┘
```

**xmin** = transaction ID that created this row version
**xmax** = transaction ID that deleted/updated this row version (∞ = still live)

**How a reader sees consistent data:**

Every transaction gets a snapshot at its start point. The snapshot records:
- The current XID (transaction ID)
- All in-progress XIDs (transactions started but not committed)

A row version is visible to a transaction's snapshot if:
- `xmin` committed before the snapshot, AND
- `xmax` is either ∞ (not deleted) OR `xmax` started after the snapshot (so the deletion is "in the future")

**Why MVCC is great:**

- **Readers never block writers** — reading a row doesn't lock it
- **Writers never block readers** — writing a new version doesn't prevent reads of the old version
- Only writer-writer conflicts require actual locking
- This is fundamentally different from lock-based isolation (MySQL with row locks) where a reader can block a writer

**The cost of MVCC — dead tuple accumulation:**

Dead tuples (old row versions) accumulate in the heap. `VACUUM` removes them, but it can only remove versions that no open transaction can see. Long-running transactions prevent vacuum → table bloat.

```
Autovacuum settings (postgresql.conf):
autovacuum = on                        -- always on in production
autovacuum_vacuum_scale_factor = 0.05  -- vacuum when 5% of table is dead tuples
autovacuum_analyze_scale_factor = 0.02 -- analyze when 2% of rows changed
```

### 5.2 Snapshot Isolation

PostgreSQL's Repeatable Read and Serializable modes use **snapshot isolation**. The snapshot is taken at the start of the first statement in the transaction (for Repeatable Read) or at the start of the transaction (for Serializable). All reads in the transaction see the state of the database as it was at snapshot time.

This is why PostgreSQL's Repeatable Read prevents phantom reads — new rows inserted by other transactions after the snapshot are invisible.

### 5.3 Setting Isolation Level Per Transaction

```sql
-- Default (Read Committed) — most transactions
BEGIN;
SELECT ...;
COMMIT;

-- Repeatable Read — for consistent multi-statement reads
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SELECT ...;  -- snapshot taken here
SELECT ...;  -- sees same data
COMMIT;

-- Serializable — for financial/inventory operations
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SELECT stock FROM products WHERE id = $1 FOR UPDATE;
UPDATE products SET stock = stock - $qty WHERE id = $1;
INSERT INTO orders ...;
COMMIT;
-- May fail with: ERROR: could not serialize access...
-- Application must retry
```

Setting globally (for a session):

```sql
SET default_transaction_isolation = 'repeatable read';
```

### 5.4 PostgreSQL's Surprising Read Committed Behavior

A subtlety that trips up experienced engineers: in Read Committed, a `SELECT` and a concurrent `UPDATE ... WHERE` in the same transaction can see different snapshots.

```sql
-- Session 1 (T1):
BEGIN;  -- isolation: Read Committed

SELECT COUNT(*) FROM orders WHERE status = 'pending';
-- returns 10

-- Session 2 (T2) commits between T1's queries:
-- UPDATE orders SET status = 'processing' WHERE status = 'pending';

UPDATE orders
SET processed_at = NOW()
WHERE status = 'pending';
-- This UPDATE sees T2's committed changes — re-evaluates WHERE on current data
-- Returns rowsAffected = 0 (all orders already moved to 'processing' by T2)

COMMIT;
```

The `UPDATE`'s `WHERE` clause was re-evaluated against the latest committed state, not T1's snapshot. This can cause surprising behavior where a `SELECT` sees one set of rows but a subsequent `UPDATE WHERE` in the same transaction acts on a different set.

---

## 6. Practical Patterns

### 6.1 When to Use Serializable

Use Serializable isolation when:

| Scenario | Why Serializable |
|----------|------------------|
| Financial double-spend prevention | Write skew can allow two concurrent withdrawals to both succeed even when only one should |
| Inventory reservation (accurate) | Without serializable, two buyers can both "successfully" book the last item |
| Constraint enforcement requiring read+write | Check-then-act where the check and act must be atomic |
| Voting/counting with uniqueness | Prevent duplicate votes even under concurrent load |

**Do NOT use Serializable:**
- For all transactions by default — it's overkill for most operations and adds retry complexity
- When simple atomic updates suffice (use `UPDATE counter SET val = val + 1` instead)
- For read-only transactions (reads at Serializable add overhead but no concurrency benefit for reads-only)

### 6.2 Deadlock Retry Logic

Application code must handle deadlock errors (PostgreSQL error code `40P01`) and serialization failures (code `40001`) with automatic retry:

```go
// Go — retry transaction on deadlock or serialization failure
func withRetry(ctx context.Context, pool *pgxpool.Pool, maxRetries int, fn func(pgx.Tx) error) error {
    for attempt := 0; attempt < maxRetries; attempt++ {
        err := withTx(ctx, pool, fn)
        if err == nil {
            return nil
        }

        var pgErr *pgconn.PgError
        if errors.As(err, &pgErr) {
            switch pgErr.Code {
            case "40P01": // deadlock_detected
                slog.Warn("deadlock detected, retrying", "attempt", attempt+1)
                time.Sleep(time.Duration(attempt+1) * 50 * time.Millisecond)
                continue
            case "40001": // serialization_failure
                slog.Warn("serialization failure, retrying", "attempt", attempt+1)
                time.Sleep(time.Duration(attempt+1) * 50 * time.Millisecond)
                continue
            }
        }
        return err // non-retryable error
    }
    return fmt.Errorf("max retries exceeded after %d attempts", maxRetries)
}

func withTx(ctx context.Context, pool *pgxpool.Pool, fn func(pgx.Tx) error) error {
    tx, err := pool.Begin(ctx)
    if err != nil {
        return err
    }
    defer tx.Rollback(ctx) // no-op if already committed

    if err := fn(tx); err != nil {
        return err
    }
    return tx.Commit(ctx)
}
```

**Jitter on retry:**

Add random jitter to retry delays to prevent "thundering herd" — all retrying transactions waiting the same amount and then all colliding again:

```go
jitter := time.Duration(rand.Int63n(50)) * time.Millisecond
time.Sleep(baseDelay + jitter)
```

### 6.3 The Check-Then-Act Anti-Pattern

A very common bug: check a condition in one statement, act on it in another — without any locking. The check can become stale between the check and the act.

**Anti-pattern:**

```go
// Bug: check and act are separate statements; not atomic
stock, _ := db.QueryRow(ctx, "SELECT stock FROM products WHERE id = $1", productID).Scan(&stock)
if stock < qty {
    return ErrInsufficientStock
}
// TOCTOU gap: another goroutine can decrement stock here
_, _ = db.Exec(ctx, "UPDATE products SET stock = stock - $1 WHERE id = $2", qty, productID)
```

**Fix 1 — Atomic conditional update:**

```sql
-- Returns affected rows = 0 if stock insufficient (WHERE condition failed)
UPDATE products
SET stock = stock - $qty
WHERE id = $1
  AND stock >= $qty   -- atomic check-and-update
RETURNING stock;
```

If `rowsAffected == 0`, the stock was insufficient. This is the simplest fix.

**Fix 2 — SELECT FOR UPDATE:**

```sql
BEGIN;
SELECT stock FROM products WHERE id = $1 FOR UPDATE;
-- Application checks stock
UPDATE products SET stock = stock - $qty WHERE id = $1;
COMMIT;
```

**Fix 3 — Serializable isolation:**

Let PostgreSQL detect if the check became stale due to concurrent modification.

### 6.4 Optimistic Locking Pattern

Optimistic locking is effective when you want to avoid database locks but still detect concurrent modifications:

```sql
-- Table with version column
CREATE TABLE documents (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title   TEXT,
    content TEXT,
    version INT NOT NULL DEFAULT 1
);

-- Read phase (no lock):
SELECT id, title, content, version FROM documents WHERE id = $1;
-- Returns: { id: 'doc1', title: 'Draft', version: 3 }

-- Write phase (include version in WHERE):
UPDATE documents
SET title = $new_title, content = $new_content, version = version + 1
WHERE id = $1
  AND version = $expected_version;   -- optimistic lock check

-- Check rowsAffected:
-- 1 → success
-- 0 → conflict (someone else updated it); retry or surface error to user
```

**Using `updated_at` as optimistic lock (alternative):**

```sql
UPDATE documents
SET content = $new_content, updated_at = NOW()
WHERE id = $1
  AND updated_at = $last_seen_updated_at;
```

**Handling conflicts in application:**

```go
result, err := tx.Exec(ctx,
    `UPDATE documents SET content = $1, version = version + 1
     WHERE id = $2 AND version = $3`,
    newContent, docID, expectedVersion,
)
if err != nil { return err }
if result.RowsAffected() == 0 {
    return ErrConflict  // application should reload and retry, or notify user
}
```

---

## 7. Implementation Examples

### Go + pgx

#### Explicit Transaction with Isolation Level

```go
// store/transaction.go
package store

import (
    "context"
    "errors"
    "fmt"
    "log/slog"
    "math/rand"
    "time"

    "github.com/jackc/pgx/v5"
    "github.com/jackc/pgx/v5/pgconn"
    "github.com/jackc/pgx/v5/pgxpool"
)

// TransferFunds moves money between accounts atomically at Serializable isolation.
// Retries on deadlock or serialization failure.
func TransferFunds(ctx context.Context, pool *pgxpool.Pool, fromID, toID string, amount float64) error {
    return retryOnConflict(ctx, 5, func() error {
        return withTx(ctx, pool, pgx.TxOptions{
            IsoLevel: pgx.Serializable,
        }, func(tx pgx.Tx) error {
            // Lock both rows in a consistent order (lower ID first) to prevent deadlocks
            var ids []string
            if fromID < toID {
                ids = []string{fromID, toID}
            } else {
                ids = []string{toID, fromID}
            }

            // Acquire locks in order
            var fromBalance, toBalance float64
            rows, err := tx.Query(ctx,
                `SELECT id, balance FROM accounts WHERE id = ANY($1) ORDER BY id FOR UPDATE`,
                ids,
            )
            if err != nil {
                return fmt.Errorf("locking accounts: %w", err)
            }

            balances := make(map[string]float64)
            for rows.Next() {
                var id string
                var bal float64
                if err := rows.Scan(&id, &bal); err != nil {
                    return err
                }
                balances[id] = bal
            }
            rows.Close()

            fromBalance = balances[fromID]
            _ = toBalance // used for validation

            if fromBalance < amount {
                return ErrInsufficientFunds
            }

            // Debit source
            _, err = tx.Exec(ctx,
                `UPDATE accounts SET balance = balance - $1, updated_at = NOW() WHERE id = $2`,
                amount, fromID,
            )
            if err != nil {
                return fmt.Errorf("debiting account: %w", err)
            }

            // Credit destination
            _, err = tx.Exec(ctx,
                `UPDATE accounts SET balance = balance + $1, updated_at = NOW() WHERE id = $2`,
                amount, toID,
            )
            if err != nil {
                return fmt.Errorf("crediting account: %w", err)
            }

            // Audit record
            _, err = tx.Exec(ctx,
                `INSERT INTO transfers (from_id, to_id, amount) VALUES ($1, $2, $3)`,
                fromID, toID, amount,
            )
            return err
        })
    })
}

// withTx runs fn inside a transaction with the given options.
// Automatically rolls back if fn returns an error.
func withTx(ctx context.Context, pool *pgxpool.Pool, opts pgx.TxOptions, fn func(pgx.Tx) error) error {
    tx, err := pool.BeginTx(ctx, opts)
    if err != nil {
        return fmt.Errorf("beginning transaction: %w", err)
    }
    defer tx.Rollback(ctx) // no-op after Commit

    if err := fn(tx); err != nil {
        return err
    }
    return tx.Commit(ctx)
}

// retryOnConflict retries fn on deadlock or serialization failure with exponential backoff + jitter.
func retryOnConflict(ctx context.Context, maxAttempts int, fn func() error) error {
    baseDelay := 50 * time.Millisecond

    for attempt := 0; attempt < maxAttempts; attempt++ {
        err := fn()
        if err == nil {
            return nil
        }

        var pgErr *pgconn.PgError
        if errors.As(err, &pgErr) {
            switch pgErr.Code {
            case "40P01": // deadlock_detected
                slog.WarnContext(ctx, "deadlock detected, retrying",
                    "attempt", attempt+1, "maxAttempts", maxAttempts)
            case "40001": // serialization_failure
                slog.WarnContext(ctx, "serialization failure, retrying",
                    "attempt", attempt+1, "maxAttempts", maxAttempts)
            default:
                return err // not a retryable error
            }

            // Exponential backoff with jitter
            delay := baseDelay * time.Duration(1<<attempt)
            jitter := time.Duration(rand.Int63n(int64(delay / 2)))
            select {
            case <-ctx.Done():
                return ctx.Err()
            case <-time.After(delay + jitter):
            }
            continue
        }

        return err
    }
    return fmt.Errorf("transaction failed after %d attempts", maxAttempts)
}
```

#### Optimistic Locking with Version Column

```go
// store/document_store.go

type Document struct {
    ID      string
    Title   string
    Content string
    Version int
}

var ErrConflict = errors.New("document was modified by another user")

func (s *DocumentStore) Update(ctx context.Context, doc Document) error {
    result, err := s.pool.Exec(ctx,
        `UPDATE documents
         SET title = $1, content = $2, version = version + 1, updated_at = NOW()
         WHERE id = $3
           AND version = $4`,   // optimistic lock: fail if version changed
        doc.Title, doc.Content, doc.ID, doc.Version,
    )
    if err != nil {
        return fmt.Errorf("updating document: %w", err)
    }
    if result.RowsAffected() == 0 {
        return ErrConflict // another transaction updated this document
    }
    return nil
}
```

---

### Node.js + pg

#### Explicit Transaction with Isolation Level

```javascript
// store/transferService.js
const { Pool } = require('pg');

const DEADLOCK_CODE          = '40P01';
const SERIALIZATION_FAIL_CODE = '40001';

/**
 * Transfers funds between two accounts atomically at Serializable isolation.
 * Retries on deadlock or serialization failure.
 */
async function transferFunds(pool, fromId, toId, amount, maxRetries = 5) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await runTransfer(pool, fromId, toId, amount);
    } catch (err) {
      if (
        err.code === DEADLOCK_CODE ||
        err.code === SERIALIZATION_FAIL_CODE
      ) {
        const delay = Math.pow(2, attempt) * 50 + Math.random() * 50;
        console.warn(`Transaction conflict (attempt ${attempt + 1}), retrying in ${delay}ms`);
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }
      throw err; // non-retryable
    }
  }
  throw new Error(`Transaction failed after ${maxRetries} attempts`);
}

async function runTransfer(pool, fromId, toId, amount) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE');

    // Lock both rows in consistent order to prevent deadlocks
    const [id1, id2] = [fromId, toId].sort();
    const { rows: accounts } = await client.query(
      `SELECT id, balance FROM accounts WHERE id = ANY($1) ORDER BY id FOR UPDATE`,
      [[id1, id2]]
    );

    const accountMap = Object.fromEntries(accounts.map((a) => [a.id, a]));
    const fromAccount = accountMap[fromId];

    if (!fromAccount || parseFloat(fromAccount.balance) < amount) {
      throw new Error('Insufficient funds');
    }

    await client.query(
      'UPDATE accounts SET balance = balance - $1, updated_at = NOW() WHERE id = $2',
      [amount, fromId]
    );

    await client.query(
      'UPDATE accounts SET balance = balance + $1, updated_at = NOW() WHERE id = $2',
      [amount, toId]
    );

    await client.query(
      'INSERT INTO transfers (from_id, to_id, amount) VALUES ($1, $2, $3)',
      [fromId, toId, amount]
    );

    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release(); // always return connection to pool
  }
}

module.exports = { transferFunds };
```

#### Optimistic Locking

```javascript
// store/documentRepository.js

class DocumentRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async findById(id) {
    const { rows } = await this.pool.query(
      'SELECT id, title, content, version, updated_at FROM documents WHERE id = $1',
      [id]
    );
    return rows[0] || null;
  }

  /**
   * Updates a document using optimistic locking.
   * Returns true on success, throws ConflictError if version mismatch.
   */
  async update(id, { title, content, expectedVersion }) {
    const { rowCount } = await this.pool.query(
      `UPDATE documents
       SET title = $1, content = $2, version = version + 1, updated_at = NOW()
       WHERE id = $3 AND version = $4`,
      [title, content, id, expectedVersion]
    );

    if (rowCount === 0) {
      throw Object.assign(new Error('Document was modified concurrently'), {
        code: 'CONFLICT',
        status: 409,
      });
    }

    return true;
  }
}

module.exports = { DocumentRepository };
```

---

### Python + SQLAlchemy

#### Explicit Transaction with Isolation Level

```python
# store/transfer_service.py
from __future__ import annotations

import asyncio
import logging
import random
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DEADLOCK_CODES = {"40P01", "40001"}   # deadlock_detected, serialization_failure


async def transfer_funds(
    session: AsyncSession,
    from_id: str,
    to_id: str,
    amount: Decimal,
    max_retries: int = 5,
) -> None:
    """
    Transfer funds between accounts at Serializable isolation.
    Retries automatically on deadlock or serialization failure.
    """
    for attempt in range(max_retries):
        try:
            await _run_transfer(session, from_id, to_id, amount)
            return
        except OperationalError as exc:
            pg_code = getattr(exc.orig, "pgcode", None)
            if pg_code in DEADLOCK_CODES:
                delay = (2 ** attempt) * 0.05 + random.uniform(0, 0.05)
                logger.warning(
                    "Transaction conflict (attempt %d/%d), retrying in %.2fs",
                    attempt + 1, max_retries, delay,
                )
                await asyncio.sleep(delay)
                await session.rollback()
                continue
            raise  # non-retryable error

    raise RuntimeError(f"Transaction failed after {max_retries} attempts")


async def _run_transfer(
    session: AsyncSession,
    from_id: str,
    to_id: str,
    amount: Decimal,
) -> None:
    async with session.begin():
        # Set isolation level for this transaction
        await session.execute(
            text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
        )

        # Lock both rows in consistent order (prevent deadlocks)
        id_order = sorted([from_id, to_id])
        result = await session.execute(
            text("""
                SELECT id, balance
                FROM accounts
                WHERE id = ANY(:ids)
                ORDER BY id
                FOR UPDATE
            """),
            {"ids": id_order},
        )
        accounts = {row.id: row for row in result.fetchall()}

        from_account = accounts.get(from_id)
        if from_account is None:
            raise ValueError(f"Account {from_id} not found")

        if Decimal(str(from_account.balance)) < amount:
            raise ValueError("Insufficient funds")

        # Debit
        await session.execute(
            text("""
                UPDATE accounts
                SET balance = balance - :amount, updated_at = NOW()
                WHERE id = :id
            """),
            {"amount": amount, "id": from_id},
        )

        # Credit
        await session.execute(
            text("""
                UPDATE accounts
                SET balance = balance + :amount, updated_at = NOW()
                WHERE id = :id
            """),
            {"amount": amount, "id": to_id},
        )

        # Audit
        await session.execute(
            text("""
                INSERT INTO transfers (from_id, to_id, amount)
                VALUES (:from_id, :to_id, :amount)
            """),
            {"from_id": from_id, "to_id": to_id, "amount": amount},
        )
        # session.begin() context manager auto-commits on exit
```

#### Optimistic Locking

```python
# store/document_repository.py
from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class Document:
    id: uuid.UUID
    title: str
    content: str
    version: int


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, doc_id: uuid.UUID) -> Document | None:
        result = await self.session.execute(
            text("SELECT id, title, content, version FROM documents WHERE id = :id"),
            {"id": doc_id},
        )
        row = result.fetchone()
        if row is None:
            return None
        return Document(id=row.id, title=row.title, content=row.content, version=row.version)

    async def update(
        self,
        doc_id: uuid.UUID,
        title: str,
        content: str,
        expected_version: int,
    ) -> Document:
        """
        Update document using optimistic locking.
        Raises HTTP 409 if the version doesn't match (concurrent modification).
        """
        result = await self.session.execute(
            text("""
                UPDATE documents
                SET title = :title,
                    content = :content,
                    version = version + 1,
                    updated_at = NOW()
                WHERE id = :id
                  AND version = :expected_version
                RETURNING id, title, content, version
            """),
            {
                "title": title,
                "content": content,
                "id": doc_id,
                "expected_version": expected_version,
            },
        )
        row = result.fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document was modified by another request. Please reload and try again.",
            )

        return Document(id=row.id, title=row.title, content=row.content, version=row.version)
```

---

## Common Patterns & Best Practices

### 1. Default to Read Committed, Upgrade When Needed
Start with the default (Read Committed). Move to Repeatable Read when you need consistent multi-read snapshots. Move to Serializable only when you have write-skew scenarios. Most CRUD operations don't need anything above Read Committed.

### 2. Atomic Updates Over Read-Then-Write
```sql
-- Wrong (race condition):
-- Application reads count, adds 1, writes back
-- Two concurrent reads both get 5, both write 6; should be 7

-- Right (atomic):
UPDATE posts SET view_count = view_count + 1 WHERE id = $1;
UPDATE carts SET item_count = item_count + 1 WHERE id = $1 AND product_id = $2;
```

### 3. Use `INSERT ... ON CONFLICT` for Upserts
```sql
-- Atomic upsert — no race between check-if-exists and insert
INSERT INTO user_preferences (user_id, key, value)
VALUES ($1, $2, $3)
ON CONFLICT (user_id, key)
DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();
```

### 4. Keep Transactions Short
- Fetch data outside the transaction if possible (only hold the transaction for the write phase)
- Don't make external API calls inside a transaction
- Avoid user input or long computations between BEGIN and COMMIT

### 5. Consistent Lock Ordering
When acquiring multiple row locks, always lock in a predictable order (e.g., by ascending ID). This prevents circular wait and eliminates the most common class of deadlocks.

### 6. Monitor Transaction Duration
Set up monitoring for long-running transactions:

```sql
-- Query to find long-running transactions (run this in your monitoring):
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > INTERVAL '5 minutes'
  AND state != 'idle';
```

### 7. Test Concurrency Explicitly
Don't assume your transaction logic is correct without testing it under concurrent load. Use tools like `pgbench` or write concurrent integration tests that fire multiple goroutines/threads at the same endpoint simultaneously.

---

## Common Pitfalls

### Pitfall 1: Forgetting to Handle Serialization Failures
At Serializable isolation, PostgreSQL can abort your transaction with a serialization failure. If your application doesn't catch `40001` and retry, those transactions fail silently (from the user's perspective, they get a 500 error).

### Pitfall 2: BEGIN inside a Loop
```go
// Bug: beginTx and commit inside a loop — if the loop's 100th iteration fails,
// you might try to commit a transaction that's been rolled back
for _, item := range items {
    tx.Exec(ctx, "INSERT INTO ...", item)  // if this panics, tx is in aborted state
}
tx.Commit(ctx) // may succeed or fail unpredictably
```

Check transaction state after every statement or use `pgx.Batch` for bulk inserts.

### Pitfall 3: Deadlock from Unordered Lock Acquisition
The most common deadlock: two transactions lock the same set of rows in different order. Always enforce a canonical ordering (sort IDs ascending before locking).

### Pitfall 4: Using Transactions for Non-Database Operations
```go
tx, _ := pool.BeginTx(ctx, opts)
tx.Exec(ctx, "UPDATE orders SET status = 'shipped'")
sendEmail(customer.Email, "Your order shipped!")  // external call inside tx!
tx.Commit(ctx)
```
If `sendEmail` takes 5 seconds, the transaction holds locks for 5 seconds, blocking all other transactions on this order. Move external calls outside the transaction.

### Pitfall 5: Optimistic Locking Without Retry or User Feedback
When an optimistic lock conflict occurs (version mismatch), you must either retry automatically (safe for background operations) or inform the user to reload and resubmit (for user-facing forms).

### Pitfall 6: Long Transactions on Highly-Contended Tables
A single long-running transaction on a frequently updated table (like `user_sessions`) can block vacuum and cause autovacuum to continuously fail, leading to table bloat and eventually transaction ID wraparound — a catastrophic PostgreSQL condition requiring downtime to fix. Monitor `pg_stat_activity` for long transactions and set `idle_in_transaction_session_timeout`.

### Pitfall 7: Relying on Read-Your-Own-Writes Within the Same Transaction
In distributed systems with read replicas, a write on the primary might not be visible on a replica used for subsequent reads within what looks like the same logical flow. This is not a PostgreSQL transaction issue — it's a replication lag issue. Solution: route read-after-write queries to the primary, or use synchronous replication.

---

## Interview Questions & Answers

### Q1: Explain the four transaction isolation levels

**Answer:**
SQL defines four isolation levels, each preventing different concurrency anomalies:

**Read Uncommitted** — the weakest level. Transactions can read uncommitted (dirty) data from concurrent transactions. PostgreSQL doesn't actually implement this; it silently uses Read Committed instead.

**Read Committed** — transactions only see data committed before each query began. This prevents dirty reads. But running the same query twice in the same transaction can return different results if another transaction commits between the two reads (non-repeatable read). This is PostgreSQL's default.

**Repeatable Read** — the snapshot is taken at the start of the first statement. Any row read at the start will return the same value throughout the transaction, even if other transactions commit changes. This prevents non-repeatable reads. In standard SQL, phantom reads (a re-executed query returning different rows due to inserts/deletes by other transactions) are still possible. PostgreSQL's implementation of Repeatable Read actually also prevents phantoms.

**Serializable** — the strongest level. Transactions execute as if they were serial (one at a time). This prevents all anomalies including write skew. In PostgreSQL, this is implemented via Serializable Snapshot Isolation (SSI), which detects and aborts transactions that would violate serializable execution. Application code must be prepared to retry aborted transactions.

---

### Q2: What is a dirty read? Give a concrete example.

**Answer:**
A dirty read occurs when a transaction reads data that has been modified by another transaction that hasn't committed yet. If the other transaction rolls back, the reading transaction used data that never officially existed.

Example: An e-commerce system processes a refund. Transaction T2 updates the account balance from $100 to $150 (the refund) but hasn't committed. Transaction T1 reads the balance and sees $150 — proceeds to charge the customer $50 based on a "high balance" discount. T2 then rolls back (the refund was processed in error). The system has now given a discount based on a balance that never actually existed.

Dirty reads are prevented at Read Committed and above. PostgreSQL prevents them at all levels because MVCC means every read sees a snapshot of committed data — uncommitted row versions are simply never returned.

---

### Q3: What is write skew? What isolation level prevents it?

**Answer:**
Write skew is when two concurrent transactions each read a set of data, make independent decisions based on that data, and each write changes that don't individually violate constraints — but the combined result of both commits does violate a constraint.

Classic example: Hospital on-call doctors. Rule: at least one doctor must be on-call. Two doctors are on-call. Transactions T1 (Alice taking a break) and T2 (Bob taking a break) both read "2 doctors on-call" and both conclude it's safe to remove themselves. Both commit. Result: 0 doctors on-call — the invariant is violated.

Neither transaction read uncommitted data, neither had stale reads — they each saw a consistent state. But their combined effect broke the invariant.

Only **Serializable** isolation prevents write skew. At lower levels (including Repeatable Read), write skew is possible. The fix is either: use `BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE` (and retry on serialization failure), or use `SELECT FOR UPDATE` to explicitly lock all rows being checked (preventing the other transaction from passing the check while yours is running).

---

### Q4: What is MVCC and why does PostgreSQL use it?

**Answer:**
MVCC (Multi-Version Concurrency Control) is PostgreSQL's method of implementing isolation without read locks. Instead of locking rows when reading them, PostgreSQL maintains multiple versions of each row. When a transaction reads a row, it sees the version that was committed before the transaction's snapshot time. Concurrent writes create new row versions; old versions remain visible to transactions that started before the update.

The key benefit: **readers never block writers, and writers never block readers**. Only writer-writer conflicts require actual locking. This is fundamentally different from systems like MySQL with MyISAM (table-level locks) where a read could block a write.

The cost: dead row versions (old versions that are no longer visible to any active transaction) accumulate in the heap and must be cleaned up by `VACUUM`. Long-running transactions prevent vacuum from removing dead tuples, causing table bloat. This is why PostgreSQL's `idle_in_transaction_session_timeout` is important — to kill transactions that are holding open a snapshot unnecessarily.

---

### Q5: What causes a deadlock? How do you prevent it?

**Answer:**
A deadlock occurs when two or more transactions are each waiting for a lock held by the other, creating a circular dependency. Transaction T1 holds lock on row A and waits for row B; Transaction T2 holds lock on row B and waits for row A. Both are stuck indefinitely.

**Prevention strategies:**

1. **Consistent lock ordering** — if every transaction always acquires locks on rows A and B in the same order (e.g., by ascending ID), circular waits can't form. This is the most effective prevention.

2. **Short transactions** — the shorter transactions are, the shorter locks are held, and the lower the probability of a circular wait forming.

3. **Weaker lock modes** — use `FOR NO KEY UPDATE` or `FOR SHARE` instead of `FOR UPDATE` when you don't need an exclusive lock.

4. **Handle deadlocks in code** — PostgreSQL automatically detects deadlocks and aborts one of the transactions (error code `40P01`). Application code must catch this error and retry. Deadlocks cannot be completely eliminated, only minimized.

---

### Q6: When would you use SELECT FOR UPDATE?

**Answer:**
`SELECT FOR UPDATE` acquires an exclusive row-level lock when reading a row, preventing other transactions from modifying (or acquiring `FOR UPDATE` locks on) the same row until your transaction commits.

Use it when:

1. **Check-then-act patterns** that need atomicity — read account balance, verify sufficient funds, then debit. Without `FOR UPDATE`, a concurrent transaction could debit the same balance between your check and your write.

2. **Pessimistic inventory reservation** — lock a product row before decrementing stock to ensure you're not working with stale data while another transaction also decrements.

3. **Job queue processing** — combined with `SKIP LOCKED`, it lets multiple workers pull jobs without conflicts. Each worker locks a different row.

Avoid it when conflicts are rare — use optimistic locking (version columns) instead, which has less overhead in low-contention scenarios. Also avoid it for long operations; holding `FOR UPDATE` locks for multiple seconds or during external API calls blocks all other transactions needing those rows.

---

### Q7: What is optimistic locking vs pessimistic locking?

**Answer:**
Both are strategies to handle concurrent modifications to the same data, with different trade-offs.

**Pessimistic locking** assumes conflicts are likely. It acquires an exclusive lock when reading data and holds it until the transaction commits. `SELECT FOR UPDATE` is PostgreSQL's mechanism. No concurrent transaction can modify the locked rows. Safe but reduces concurrency — other transactions must wait. Use it for high-contention resources like account balances and inventory counts.

**Optimistic locking** assumes conflicts are rare. It doesn't acquire any database lock. Instead, it records the data's version at read time, then at write time, it checks whether the version has changed. If it has (another transaction modified it), the write is rejected and the application retries. Usually implemented with a `version INT` column that's incremented on every update. Lower overhead in low-contention scenarios. Requires application-level retry logic and user feedback on conflict. Use it for user-facing edits (documents, profiles, settings) where conflicts are infrequent.

---

## Resources

- [PostgreSQL Documentation — Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL Documentation — Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [The Internals of PostgreSQL — Concurrency Control](https://www.interdb.jp/pg/pgsql05.html)
- [Designing Data-Intensive Applications (Kleppmann) — Chapter 7: Transactions](https://dataintensive.net/)
- [A Critique of ANSI SQL Isolation Levels (Berenson et al.)](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-95-51.pdf)
- [Serializable Snapshot Isolation in PostgreSQL](https://drkp.net/papers/ssi-vldb12.pdf)
- [pgx — PostgreSQL Driver for Go](https://github.com/jackc/pgx)
- [Saga Pattern — Microsoft Azure Architecture](https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/saga/saga)

---

**Next:** [Part 7.1: Indexing & Query Optimization](../part-07/07-indexing-query-optimization.md)
