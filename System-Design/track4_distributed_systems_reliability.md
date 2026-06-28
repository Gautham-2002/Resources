# Track 4: Distributed Systems & Reliability — System Design Study Guide
### System Design Self-Study Series for Gautham Gokulakonda

---

> **Why this track matters:** This is the track where senior engineers separate from mid-level ones. Anyone can describe a happy path. Senior engineers think about what breaks, when it breaks, and how to build systems that survive it. FAANG interviewers probe exactly this. Indian fintech companies (Razorpay, PhonePe) are obsessed with distributed transaction correctness and idempotency. Master this track and you can talk at the level of someone who has built and operated production systems at scale.

---

## 1. Consistency Models (Beyond CAP)

### What It Is

CAP theorem is a starting point, not the end of the conversation. In practice, the real question isn't "consistent or not?" — it's *what kind* of consistency guarantee does your system provide, and what do you pay for it?

---

### Strong Consistency

**What it is:** Every read returns the most recent write, no exceptions. Every node sees the same value at the same time.

**Why it exists / What problem it solves:** Some operations simply cannot tolerate stale reads. Bank balances, inventory counts, seat reservations — if two nodes return different values for the same key, the system produces wrong answers. Strong consistency prevents that.

**How it works:**
- Writes are not acknowledged until all (or a quorum of) nodes confirm the write
- Reads go through the same quorum — you can't read from a lagging replica
- Typically requires coordination: distributed locks, two-phase commit, or consensus protocols like Raft

**Why not just always use it?** Every write must propagate and be acknowledged before returning. Across data centers, this adds hundreds of milliseconds of latency. Under a network partition, you must choose: block until connectivity is restored (strong consistency) or respond with possibly stale data (availability).

**Real-world examples:** PostgreSQL transactions within a single node, Google Spanner (globally), CockroachDB.

**Interview Q&A:**
- Q: What is strong consistency and what does it cost?
  A: Strong consistency guarantees every read reflects the most recent write. The cost is latency — you need coordination across nodes before acknowledging a write. In a multi-region deployment, that coordination crosses oceans. For most systems, strong consistency everywhere is overkill. The better question is: which specific operations in your system require it? A payment debit does. A user's "last seen" timestamp probably doesn't.

---

### Eventual Consistency

**What it is:** All nodes will *eventually* converge to the same value — but in the interim, different nodes can return different values.

**Why it exists / What problem it solves:** Availability and low latency at global scale. If you can tolerate brief inconsistency, you don't need coordination before returning a response.

**How it works:**
- Writes go to one node (or a small set) and propagate asynchronously to replicas
- Reads may return stale data during the propagation window
- "Eventually" typically means milliseconds to seconds under normal conditions, but has no hard upper bound

**What "eventually" means in practice:** Under normal conditions, DynamoDB replicates across replicas in single-digit milliseconds. But under network partitions or overloaded nodes, it can take much longer. There is no guarantee.

**Real-world examples:** DNS (TTL-based propagation), DynamoDB (default mode), Cassandra (default), Amazon S3 (for read-after-write in certain configurations).

**Interview Q&A:**
- Q: What is eventual consistency? When is it acceptable?
  A: Eventual consistency means replicas will converge to the same value, but not immediately. It's acceptable when: (a) brief staleness doesn't affect correctness — showing a user slightly outdated follower count is fine, (b) the system needs to remain available during network partitions, and (c) low write latency is critical. I'd use it for social feed updates, view counters, DNS records, and search indexes. I'd never use it for financial balances or seat reservation counts.

---

### Causal Consistency

**What it is:** If operation A causally precedes operation B (A caused B), then any node that has seen B has also seen A.

**Why it exists:** Middle ground between strong and eventual. Strong consistency is expensive; pure eventual consistency can produce nonsensical orderings. Causal consistency preserves the logical order of operations without requiring global coordination.

**How it works:**
- Each operation carries a causal dependency vector (vector clock or similar)
- A node won't deliver a message until all causally prior messages are delivered
- Operations with no causal relationship can be seen in any order

**Real-world example:** If Alice posts a message, then Bob replies to it, causal consistency ensures you never see Bob's reply without first seeing Alice's message — even if you're on a different node.

---

### Read-Your-Writes Consistency

**What it is:** After you write a value, any subsequent read *by the same client* will see that write.

**Why it exists / What problem it solves:** Without this, a user updates their profile photo and refreshes the page — and sees the old photo. Terrible UX. The user thinks the save failed.

**How it works:**
- Route the user's reads to the same replica they wrote to, OR
- Tag the write with a logical timestamp; only serve reads from replicas that have caught up to that timestamp
- Sticky sessions: load balancer pins a user to one node

**Real-world examples:** Twitter ensures you always see your own tweet. Most profile/settings UIs implement this.

---

### Monotonic Read Consistency

**What it is:** If you read value X at time T, any future read will return X or something newer — never something older.

**Why it exists:** Without it, you might see a friend's status update and then, on the next refresh, see an older version because you got routed to a lagging replica. It makes the system feel like it's going backwards in time.

**How it works:** Track which replica version the client has read; route subsequent reads to replicas that have at least that version.

---

### Consistency Models Comparison

| Model | Guarantee | Latency | Availability |
|-------|-----------|---------|--------------|
| Strong | Always latest write | High (coordination) | Low (blocks on partition) |
| Causal | Ordered by causality | Medium | Medium |
| Read-your-writes | You see your own writes | Low-medium | High |
| Monotonic read | Never go backwards | Low-medium | High |
| Eventual | Converges eventually | Lowest | Highest |

---

### How to Discuss Consistency in an Interview

Don't recite definitions. Instead, reason like this:

1. **Identify the operation** — what data are we reading/writing?
2. **Ask what staleness costs** — incorrect payment vs. slightly old feed item
3. **State the trade-off explicitly** — "I'd use eventual consistency here because users can tolerate seeing a 2-second-old count, and it gives us much better write throughput"
4. **Know the tools** — DynamoDB lets you choose: eventually consistent reads are 50% cheaper; strongly consistent reads cost more

> **Key insight:** Consistency is not binary. You design different consistency levels *per operation type* within the same system. A payment debit needs strong consistency. The transaction history page can tolerate eventual consistency.

---

## 2. Distributed Transactions

### Why Transactions Are Hard Across Services

Within a single database, ACID transactions are well-understood. The database keeps a write-ahead log, manages locks, and can roll back atomically. Across multiple databases or services, there's no shared transaction log. Service A and Service B have their own databases. If Service A succeeds and Service B fails, your data is permanently inconsistent — and there's no automatic rollback.

**The classic scenario at Deepta AI:** A student application submission:
1. Write application record to `applications-db`
2. Deduct one application credit from `billing-db`
3. Send a confirmation event to `notifications-service`

Any one of these can fail. Without a distributed transaction strategy, you might charge a student without recording the application.

---

### Two-Phase Commit (2PC)

**What it is:** A protocol that ensures all participants in a distributed transaction either all commit or all abort.

**How it works:**
- **Phase 1 — Prepare:** A coordinator sends a `PREPARE` message to all participants. Each participant writes to a redo log and votes `YES` (I can commit) or `NO` (I need to abort).
- **Phase 2 — Commit/Abort:** If all vote YES, coordinator sends `COMMIT`. If any vote NO, coordinator sends `ABORT`. Participants act accordingly.

**Why 2PC is problematic:**
- **Blocking:** If the coordinator crashes after Phase 1, participants are stuck holding locks indefinitely. They cannot commit or abort on their own — they must wait for the coordinator to recover.
- **Not partition-tolerant:** During a network partition, participants can't reach the coordinator and remain blocked.
- **Performance:** Every write crosses the network twice. Locks are held across the network roundtrip.

**When to use 2PC:** Only within a single database system (PostgreSQL uses it internally for XA transactions) or in tightly controlled internal systems where you can tolerate blocking. Almost never the right answer for microservices.

---

### Three-Phase Commit (3PC)

An improvement that adds a `PRE-COMMIT` phase to eliminate the blocking problem of 2PC. In theory. In practice, it's still vulnerable to network partitions and is rarely implemented in production systems. Mention it exists; don't go deeper unless asked.

---

### Saga Pattern ⭐ (The Industry Standard)

**What it is:** A sequence of local transactions, each in their own service, where each step publishes an event or calls a command. If any step fails, compensating transactions undo the previous steps.

**Why it exists / What problem it solves:** Avoids the blocking and coordinator-crash problems of 2PC. Achieves eventual consistency across services without distributed locks.

**The key insight:** Instead of one big atomic transaction, you have a series of smaller transactions. The "rollback" is explicit: you write a compensating transaction (a business-level undo operation) for each step.

---

#### Choreography-Based Saga

**How it works:**
- No central coordinator
- Each service listens for events and reacts by performing its local transaction and emitting the next event
- Example: `OrderCreated` → Payment Service listens → `PaymentProcessed` → Inventory Service listens → `InventoryReserved`

```
OrderService          PaymentService       InventoryService
     |                      |                     |
  Create Order              |                     |
     | → OrderCreated ───→  |                     |
     |                  Process Payment           |
     |                      | → PaymentProcessed ─→
     |                      |                  Reserve Stock
```

**Compensating events (on failure):**
- If InventoryService fails → emits `ReservationFailed` → PaymentService listens → refunds → emits `PaymentRefunded`

**Trade-offs:**
| Pros | Cons |
|------|------|
| Loose coupling — services don't know about each other | Hard to track overall saga state — no single source of truth |
| High autonomy | Difficult to debug — events are scattered across services |
| Easy to add new participants | Risk of cycles if event handling isn't careful |

**When to choose:** When you have genuinely independent services that shouldn't know about each other. Good for simple, short sagas.

---

#### Orchestration-Based Saga

**How it works:**
- A central orchestrator (a dedicated service or process) tells each service what to do via commands
- The orchestrator tracks the state of the entire saga
- Each service responds with success or failure; the orchestrator decides the next step

```
                    SagaOrchestrator
                         |
         ┌───────────────┼───────────────┐
         ↓               ↓               ↓
  OrderService    PaymentService  InventoryService
  (Step 1)         (Step 2)         (Step 3)
```

The orchestrator is a state machine. It knows: "We're in state PAYMENT_PENDING. Payment succeeded → move to INVENTORY_PENDING. Payment failed → trigger OrderCancelled."

**Trade-offs:**
| Pros | Cons |
|------|------|
| Centralized visibility — one place to track saga state | Orchestrator is a potential bottleneck/single point of failure |
| Easier to debug and reason about | Orchestrator needs to be highly available |
| Explicit compensation logic in one place | Can create coupling — orchestrator knows about all services |

**When to choose:** For complex, multi-step business processes (payment flows, order fulfillment, onboarding). The explicit state machine makes it much easier to debug production incidents.

> **For Razorpay/PhonePe interviews:** Orchestration-based sagas are the dominant pattern in fintech. A payment involves: initiate → debit source account → credit destination account → notify both parties → update ledger. This has clear compensation steps and the orchestrator holds the state. If the debit succeeded but credit failed, you need an explicit "reverse debit" compensating transaction. This is not optional in a payment system.

---

#### Compensating Transactions

A compensating transaction is a business-level undo. It's not a database rollback — it's a new transaction that semantically reverses the effect of a previous one.

**Important:** Compensating transactions may not fully restore the original state. If you sent a confirmation email, you can't "un-send" it. The best you can do is send a cancellation email. Design your sagas with this in mind.

---

### When to Use 2PC vs Saga

| Scenario | Use |
|----------|-----|
| Same database, multiple tables | 2PC (native ACID) |
| Multiple services, multiple databases | Saga |
| Short transaction, tight latency requirements, internal systems | 2PC (XA) |
| Long-running business processes | Saga |
| Microservices architecture | Saga (almost always) |

---

**Interview Q&A:**
- Q: How do you handle distributed transactions across multiple microservices?
  A: I avoid 2PC in microservices because it introduces blocking and is vulnerable to coordinator failures. Instead, I use the Saga pattern — a sequence of local transactions with compensating transactions for failures. For complex flows like payment processing, I prefer orchestration-based Sagas: a central orchestrator coordinates the steps as a state machine, which makes the flow debuggable and gives me a single place to track saga state. Each step is idempotent so I can safely retry on transient failures.

- Q: Choreography vs Orchestration — which would you choose?
  A: It depends on the complexity and coupling requirements. Choreography is great for loose coupling in simple workflows — each service just reacts to events without knowing about others. But for complex, multi-step business processes — like payment flows at Razorpay — I'd choose orchestration. The orchestrator gives me explicit state tracking, easier debugging when something goes wrong in production, and a clear place to put compensation logic. The slight coupling cost is worth it for operational clarity in a fintech context.

---

## 3. Consensus Algorithms

### Why Consensus Is Hard

In a distributed system, multiple nodes must agree on a single value — even when some nodes crash, messages are delayed, or the network partitions. This is the **consensus problem**.

The hardest case: a **split-brain** scenario where a network partition splits your cluster into two groups, both of which think they're the leader and start accepting writes independently. When the partition heals, you have two divergent histories and no way to merge them correctly.

**FLP Impossibility Theorem:** In an asynchronous system where even one node can fail, it's impossible to guarantee consensus in finite time. Real consensus algorithms work around this by making assumptions (timeouts, bounded message delays).

---

### Paxos

The original consensus algorithm, published by Leslie Lamport. Foundational to understanding why consensus is hard.

**Conceptual understanding (not implementation):**
- A **Proposer** proposes a value
- **Acceptors** vote on the proposal
- A **Learner** learns the chosen value
- A value is chosen when a majority (quorum) of acceptors accept it
- Two phases: Prepare (get promises) → Accept (propose value)

**Why not just use Paxos?** It's notoriously difficult to understand, implement correctly, and reason about. Multi-Paxos (for sequences of decisions) adds even more complexity. Most systems that use Paxos in practice use it in modified, specialized forms.

---

### Raft

**What it is:** A consensus algorithm designed to be understandable — it achieves the same guarantees as Multi-Paxos but with a clearer structure.

**How it works:**

1. **Leader Election:**
   - Nodes start as **Followers**
   - If a Follower doesn't hear from a Leader within an **election timeout** (randomized, e.g., 150-300ms), it becomes a **Candidate**
   - A Candidate votes for itself and requests votes from other nodes
   - If it gets a majority of votes, it becomes the **Leader**
   - The randomized timeout prevents multiple nodes from starting elections simultaneously

2. **Log Replication:**
   - All writes go to the Leader
   - The Leader appends the write to its log and sends it to all Followers
   - Once a majority of Followers acknowledge the write, the Leader **commits** it
   - Committed entries are applied to the state machine (the actual data store)
   - The Leader then notifies Followers that the entry is committed; they apply it too

3. **Term Numbers:**
   - Each election starts a new **term** (a monotonically increasing integer)
   - Terms prevent stale leaders from causing issues — a node ignores messages from lower-term leaders

```
Leader                    Followers (F1, F2)
  |                             |
  |← Client Write "x=5"        |
  |                             |
  |──── AppendEntries ─────────→|
  |                             | (write to log, not committed yet)
  |←─── Acknowledgment ─────────|
  |                             |
  | (majority acked → commit)   |
  |──── Commit Notification ───→|
  |←─── Applied                 |
  |                             |
  |→ Respond to Client          |
```

**Where Raft is used:**
- **etcd** — the Kubernetes state store (all cluster state: pods, services, secrets)
- **CockroachDB** — each range (shard) runs Raft
- **Kafka KRaft** — replaced ZooKeeper with Raft for Kafka's metadata
- **TiKV** — distributed key-value store underlying TiDB

> **Key insight:** You don't implement Raft in a system design interview. You cite it. "The partition leaders in Kafka are elected using a Raft-based protocol in KRaft mode, which gives us a leader per partition and log replication to followers."

**Interview Q&A:**
- Q: What is the Raft consensus algorithm and where is it used?
  A: Raft is a consensus algorithm that ensures nodes in a distributed cluster agree on the same sequence of operations, even when nodes fail or the network partitions. It works by electing a leader via randomized timeouts, replicating writes through the leader to a majority quorum before committing, and using term numbers to prevent stale leaders. It's used in etcd (Kubernetes' state store), CockroachDB for range-level replication, and Kafka's KRaft mode. I think of it as the algorithm that makes "distributed systems agree on who's in charge and what happened."

---

## 4. Leader Election

**What it is:** A process by which distributed nodes agree on one node that will act as the "primary" or "leader" for a specific function.

**Why it exists / What problem it solves:** In distributed systems, many operations need a single authoritative node: primary DB writes, distributed cron jobs (only one node should run the job), Kafka partition leadership. Without a leader, multiple nodes might perform the same write, leading to conflicts.

**The core problem it prevents: Split-Brain.** Two nodes both think they're the leader and start accepting writes. When the partition heals, there's no safe way to merge the divergent state.

---

### ZooKeeper-Based Leader Election (Ephemeral Nodes)

**How it works:**
1. All candidate nodes try to create the same **ephemeral sequential node** in ZooKeeper (e.g., `/election/leader-0000000001`)
2. ZooKeeper assigns sequential IDs; all nodes list the children of `/election`
3. The node with the **lowest sequence number** is the leader
4. All other nodes watch the node *just below them* in the sequence (not the leader directly — avoids thundering herd)
5. When the leader crashes, its **ephemeral node** is automatically deleted by ZooKeeper (because the session dies)
6. The node watching the deleted node becomes the leader

**Key property of ephemeral nodes:** They only exist as long as the session that created them is alive. When a node crashes or disconnects, ZooKeeper automatically removes its ephemeral nodes. This is how distributed systems detect failures without explicit heartbeats.

---

### etcd-Based Leader Election (Raft Leases)

**How it works:**
- etcd is itself a Raft consensus cluster
- Services use etcd's `election` API or distributed locking to elect a leader
- The leader holds a **lease** — a time-bounded lock with a TTL
- The leader must renew its lease periodically by sending heartbeats to etcd
- If it fails to renew, the lease expires, and another node can acquire it

---

### Lease-Based Leader Election (Simpler Approach)

Instead of ZooKeeper or etcd, use Redis:
1. Leader tries to set a key with `SET leader-lock <node-id> NX EX 30` (set if not exists, expires in 30s)
2. If it gets the lock, it's the leader and must refresh every ~10s
3. If it fails to refresh (node crashed), the key expires and another node can acquire it

**Risk:** If the leader is slow (GC pause, network latency) and fails to refresh in time, a new leader is elected. Now you briefly have two leaders. Design your system to handle this (e.g., lease-based writes that check the lease is still valid before committing).

---

### Use Cases

| Use Case | Leader Controls |
|----------|----------------|
| Kafka partition | Which broker accepts writes for a partition |
| PostgreSQL replication | Which node is the primary (accepts writes) |
| Distributed cron | Which pod runs the scheduled job |
| Shard management | Which node owns which shard |

**Interview Q&A:**
- Q: How would you implement distributed leader election for a cron job that must run on exactly one instance?
  A: I'd use a Redis lease. When a pod starts, it tries `SET cron-leader <pod-id> NX EX 30`. The pod that succeeds is the leader and runs the job. It refreshes the lease every 10 seconds. If it crashes, the key expires in 30 seconds and another pod acquires it. This is simple, battle-tested, and works well in Kubernetes where pods can die at any time. The main risk is false leader expiry during GC pauses, so I'd set the TTL conservatively and make the job idempotent so double-execution isn't catastrophic.

---

## 5. Fault Tolerance & Failure Modes

> **The mindset shift:** Junior engineers design for the happy path and hope it works. Senior engineers assume everything will fail and design so the system degrades gracefully.

### Types of Failures

| Type | Description | Example |
|------|-------------|---------|
| Crash failure | Node stops completely | Pod OOM killed, process crash |
| Omission failure | Node stops sending/receiving messages | Firewall drops packets silently |
| Timing failure | Node responds, but too slowly | GC pause, disk I/O spike |
| Byzantine failure | Node behaves incorrectly or maliciously | Bug causing wrong responses, hardware bit flip |
| Network partition | Network split prevents nodes from communicating | Data center link failure |

In practice, most failures are crash failures, omission failures, and timing failures. Byzantine failures (nodes lying) are rare in trusted internal systems.

---

### Timeout + Retry

**What it is:** The most basic fault tolerance pattern. If a request doesn't succeed in N milliseconds, retry it.

**How it works:**
- Set a timeout on all outbound calls (never call a dependency with an infinite timeout)
- On timeout or transient error, retry up to N times

**When retries make things worse:** Under load, a downstream service starts timing out. Every timeout triggers a retry. Now you're sending 3x the traffic to an already-overloaded service. This is a **retry storm** — retries amplify the problem they're trying to solve.

**Solution:** Exponential backoff with jitter.

---

### Exponential Backoff with Jitter

**What it is:** After each failed attempt, wait longer before the next retry. Add randomness (jitter) to prevent all clients from retrying at the same time.

**How it works:**
```
Wait = base_delay * 2^attempt + random_jitter

Attempt 1: wait 1s + jitter(0-0.5s)
Attempt 2: wait 2s + jitter(0-0.5s)
Attempt 3: wait 4s + jitter(0-0.5s)
Attempt 4: wait 8s + jitter(0-0.5s)
(capped at max_delay, e.g., 30s)
```

**Why jitter matters:** Without jitter, every client that got a 429 at time T waits exactly 2 seconds and retries at T+2 simultaneously — causing another spike. With jitter, retries spread out over a window, smoothing load.

```go
// Go example
func retryWithBackoff(ctx context.Context, fn func() error) error {
    maxRetries := 5
    baseDelay := 100 * time.Millisecond
    maxDelay := 30 * time.Second

    for attempt := 0; attempt < maxRetries; attempt++ {
        if err := fn(); err == nil {
            return nil
        }
        delay := time.Duration(float64(baseDelay) * math.Pow(2, float64(attempt)))
        jitter := time.Duration(rand.Int63n(int64(delay / 2)))
        sleep := min(delay+jitter, maxDelay)
        select {
        case <-time.After(sleep):
        case <-ctx.Done():
            return ctx.Err()
        }
    }
    return fmt.Errorf("max retries exceeded")
}
```

---

### Circuit Breaker Pattern ⭐

**What it is:** A state machine that wraps calls to a dependency. When the dependency is failing, the circuit "opens" and subsequent calls immediately fail (without even trying), giving the dependency time to recover.

**Why it exists / What problem it solves:** Cascading failures. If Service A calls Service B, and Service B starts timing out at 5 seconds each, Service A's threads/goroutines pile up waiting for B. Soon A runs out of capacity and starts timing out too. Service C, which calls A, now starts timing out. The entire system fails because of one overloaded downstream service.

**The three states:**

```
          Failures exceed threshold
CLOSED ─────────────────────────────→ OPEN
  ↑                                     |
  │                                     | After timeout window
  │          Success in trial           ↓
  └──────────────────────────────── HALF-OPEN
                                        |
                             Failure in trial
                                        |
                                        ↓
                                      OPEN (reset timer)
```

**State Machine Details:**

| State | Behavior | Transition |
|-------|----------|------------|
| **Closed** | All requests pass through. Track failure rate | → Open when failures exceed threshold (e.g., 50% in last 60s) |
| **Open** | All requests fail immediately (fast fail). No calls made to dependency | → Half-Open after timeout (e.g., 30s) |
| **Half-Open** | Allow a small number of trial requests through | → Closed if trials succeed; → Open if trial fails |

**Why fast-fail matters:** When the circuit is open, instead of waiting 5 seconds for each call to time out, you fail in microseconds. Your thread pool isn't exhausted. You can return a degraded response (cached data, error message) immediately.

**Real implementations:**
- **Hystrix** (Netflix, Java) — the original, now in maintenance mode
- **Resilience4j** (Java) — the modern replacement
- **Go:** No standard library — implement with a library or custom state machine

```go
// Simplified circuit breaker concept in Go
type CircuitBreaker struct {
    state       string // "closed", "open", "half-open"
    failures    int
    threshold   int
    lastFailure time.Time
    timeout     time.Duration
    mu          sync.Mutex
}

func (cb *CircuitBreaker) Call(fn func() error) error {
    cb.mu.Lock()
    defer cb.mu.Unlock()

    switch cb.state {
    case "open":
        if time.Since(cb.lastFailure) > cb.timeout {
            cb.state = "half-open"
        } else {
            return errors.New("circuit breaker open") // fast fail
        }
    }

    err := fn()
    if err != nil {
        cb.failures++
        cb.lastFailure = time.Now()
        if cb.failures >= cb.threshold {
            cb.state = "open"
        }
        return err
    }
    // Success
    cb.failures = 0
    cb.state = "closed"
    return nil
}
```

**Interview Q&A:**
- Q: What is a circuit breaker and when would you open it?
  A: A circuit breaker is a fault tolerance pattern modeled on the electrical circuit breaker. It wraps calls to a dependency and tracks the failure rate. When failures exceed a threshold — say, 50% of requests in the last 60 seconds — the circuit opens. In the open state, all requests fail immediately without even attempting the downstream call. After a configurable timeout (say 30 seconds), it enters half-open and allows a small number of trial requests. If they succeed, the circuit closes; if not, it reopens. I'd open the circuit when: the error rate exceeds a threshold, or latency exceeds an SLO. The key benefit is preventing cascading failures — an overloaded service doesn't take down the services that depend on it.

- Q: What happens when a circuit breaker is open? What does it mean for the system?
  A: When open, calls to the protected dependency fail immediately — no network call is made, so threads aren't blocked. The system needs a fallback: return a cached response, return a default value, return a user-facing error, or queue the request for later processing. The critical point is that the rest of the system stays functional. Only the feature that depends on the failing service degrades, not the entire platform. This is by design: the circuit breaker is your bulkhead.

---

### Bulkhead Pattern

**What it is:** Isolate resources (thread pools, connection pools, semaphores) per dependency, so a failure in one doesn't exhaust resources for others.

**Named after ship bulkheads:** A bulkhead divides a ship's hull into compartments. If one compartment floods, the others remain dry. The ship doesn't sink.

**How it works:**
- Instead of one shared thread pool for all outbound calls, allocate separate pools per downstream service
- If the payment service is slow and fills up its thread pool, the notification service pool is unaffected

**Real-world example:** In Hystrix/Resilience4j, each command group gets its own thread pool. You configure: "PaymentService: max 20 threads. NotificationService: max 10 threads." Exhausting one doesn't affect the other.

---

### At-Least-Once vs Exactly-Once Delivery

| Model | Guarantee | Risk | Mitigation |
|-------|-----------|------|------------|
| At-most-once | Delivered 0 or 1 times | Message loss | Accept loss (telemetry, analytics) |
| At-least-once | Delivered 1 or more times | Duplicates | Idempotency |
| Exactly-once | Delivered exactly once | Hard to implement | Kafka transactions + idempotent consumers |

**The hard truth:** Exactly-once at the messaging layer is achievable (Kafka supports it) but expensive. In practice, most systems use **at-least-once delivery + idempotent consumers**, which achieves the same effect at lower cost.

---

## 6. Distributed Locking

**What it is:** A mechanism to ensure that, across multiple service instances, only one instance can perform a critical operation at a time.

**Why you need it:** Multiple pod instances processing the same job queue, race conditions on shared resources (two instances both trying to allocate the same seat), preventing double-charging a customer.

---

### Redis-Based Distributed Locking

**Simple approach — SETNX + EXPIRE:**
```
SET lock:resource <unique-id> NX EX 30
```
- `NX` = only set if key doesn't exist
- `EX 30` = expire in 30 seconds (prevents deadlock if the holder crashes)
- `<unique-id>` = the holder's identity (so you don't release someone else's lock)

**Releasing the lock (atomic check-and-delete via Lua):**
```lua
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
```
You must check that you still own the lock before deleting it — otherwise, you might delete a lock acquired by a different instance after yours expired.

---

### Redlock Algorithm

A more robust approach for distributed Redis clusters (not a single node):
- Write the lock to N independent Redis nodes (typically 5)
- The lock is acquired if you successfully write to a majority (N/2 + 1) within a time window
- The effective TTL is the original TTL minus the elapsed acquisition time

**Why it's controversial:** Martin Kleppmann published a critique arguing Redlock isn't safe under certain timing assumptions (GC pauses can cause a node to think it still holds a lock while the TTL has expired elsewhere). The Redlock debate is worth knowing for FAANG interviews.

---

### The Risks of Distributed Locking

| Risk | What Happens | Mitigation |
|------|-------------|------------|
| Lock expiry during long operation | Process holds the lock, but TTL expires; another process acquires it — two processes run simultaneously | Set TTL longer than max expected operation time; use fencing tokens |
| Network partition | Lock holder can't reach Redis to refresh; thinks it lost the lock | Design operations to be safe if briefly "double-executed" |
| Redis failure | Single Redis node fails; lock is unavailable | Redis Sentinel or Cluster for HA |

**Fencing tokens:** When the lock server (etcd, ZooKeeper) grants a lock, it includes a monotonically increasing token. The resource server rejects requests with a lower token than the last seen. This ensures an expired lock holder can't write after a new holder has started.

---

### When to Avoid Distributed Locks

> **Prefer idempotency + deduplication over distributed locks wherever possible.**

Distributed locks are:
- Hard to get right
- Can become single points of failure
- Add latency (extra network round trip per operation)

If you can make the operation **idempotent** (safe to run multiple times) and deduplicate at the database level (unique constraint on an idempotency key), you don't need a distributed lock at all. The database provides the conflict detection.

**Interview Q&A:**
- Q: How would you implement a distributed lock? What are the risks?
  A: I'd use Redis with `SET key <uuid> NX EX <ttl>`, releasing it with a Lua script that checks ownership before deleting. The risks are: (1) lock expiry — if the operation takes longer than the TTL, another instance acquires the lock while the original is still running; mitigate by setting generous TTLs and using fencing tokens, (2) Redis unavailability — mitigate with Redis Sentinel/Cluster for HA. But my preferred approach is to avoid distributed locks entirely when possible. Idempotency + database unique constraints on an idempotency key gives you the same conflict detection without the operational complexity of managing distributed lock state.

---

## 7. Idempotency (Deep Dive) ⭐

**What it is:** An operation is idempotent if calling it multiple times produces the same result as calling it once. `f(f(x)) = f(x)`.

**Why it's the most important property in distributed systems:**

In distributed systems, you can't know if a request succeeded or failed. The network might drop the response even if the server processed the request. The client times out and retries. Without idempotency, the retry causes a double charge, a duplicate email, or a corrupted record. With idempotency, retrying is safe.

> **Idempotency is the foundation of safe retries. Without it, fault tolerance patterns (circuit breakers, retries, Sagas) can make things worse.**

---

### Stripe's Idempotency Key Model

When a client makes a request, it generates a unique idempotency key (UUID) and includes it in the request header: `Idempotency-Key: <uuid>`.

The server:
1. Checks if the key exists in a `idempotency_keys` table
2. If it does: return the stored response (without re-processing)
3. If it doesn't: process the request, store the key + response, return response

```sql
CREATE TABLE idempotency_keys (
    key          UUID PRIMARY KEY,
    response     JSONB NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMP NOT NULL
);
```

The `UNIQUE` constraint on `key` ensures two concurrent requests with the same key can't both insert — one will get a constraint violation and wait for the other to complete.

---

### Implementing Idempotency at the Database Level

For payment operations:
```sql
CREATE TABLE payments (
    id                UUID PRIMARY KEY,
    idempotency_key   UUID UNIQUE NOT NULL,
    amount            BIGINT NOT NULL,
    status            TEXT NOT NULL,
    created_at        TIMESTAMP NOT NULL
);
```

The `UNIQUE NOT NULL` on `idempotency_key` means a retry with the same key will hit a unique constraint violation — which you catch and handle by returning the existing payment record.

---

### Idempotency in Kafka

Kafka's transactional API provides exactly-once semantics:
- **Idempotent producer:** Each message has a sequence number; the broker deduplicates at-least-once delivery on the producer side
- **Transactional producer:** A batch of messages is either all committed or none — across multiple partitions
- **Transactional consumer:** Reads only committed messages (no uncommitted writes from failed transactions)

```go
// Go: idempotent Kafka producer config
config := sarama.NewConfig()
config.Producer.Idempotent = true
config.Producer.RequiredAcks = sarama.WaitForAll
config.Net.MaxOpenRequests = 1 // Required for idempotent producer
```

---

### Idempotency vs Retries — Why You Need Both

| Without idempotency | With idempotency |
|--------------------|-----------------|
| Retry = potential duplicate action | Retry = safe, same result |
| At-least-once delivery = at-least-once execution | At-least-once delivery = exactly-once effect |
| Circuit breaker retry causes double charge | Circuit breaker retry is safe |

**Interview Q&A:**
- Q: How do you implement idempotency in a payment API?
  A: I follow Stripe's model. The client generates a UUID and sends it as an `Idempotency-Key` header. On the server, before processing, I check a `idempotency_keys` table. If the key exists, I return the stored response without re-processing. If not, I process the payment in a transaction that atomically creates the payment record and inserts the idempotency key — the `UNIQUE` constraint on the key means two concurrent retries can't both succeed. The stored response is returned for any subsequent retry with the same key, even if the client changes the request body. Keys expire after 24 hours. This ensures a payment is never charged twice, regardless of network failures or client retries.

---

## 8. Service Discovery

**The problem:** In a microservices architecture, services scale up and down dynamically. Pods restart, IPs change. Service A needs to call Service B — but how does it know where Service B is?

---

### Client-Side Discovery

**How it works:**
1. Services register themselves with a service registry (Consul, Eureka) when they start
2. Service A queries the registry to get a list of available instances of Service B
3. Service A picks one (load balancing) and calls it directly

**Trade-offs:**
- Simple; the client controls load balancing strategy
- Client libraries must be written for each language
- Registry is a dependency that must be highly available

---

### Server-Side Discovery (Kubernetes Native)

**How it works:**
1. A load balancer or proxy sits in front of the service instances
2. Service A sends requests to the load balancer's address
3. The load balancer looks up healthy instances and forwards the request

**In Kubernetes:** This is a **Service**. You create a Service that selects pods by label. kube-proxy maintains iptables/IPVS rules that route traffic to healthy pods. The Service has a stable ClusterIP and DNS name. Pods can come and go; the Service IP stays the same.

```yaml
# Kubernetes Service example
apiVersion: v1
kind: Service
metadata:
  name: payment-service
spec:
  selector:
    app: payment-service      # routes to pods with this label
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP             # internal only
```

Service A can call `http://payment-service/charge` — Kubernetes DNS resolves this to the ClusterIP, kube-proxy routes to a healthy pod.

---

### DNS-Based Service Discovery

**The simplest approach in Kubernetes:**
- Every Service gets a DNS entry: `<service-name>.<namespace>.svc.cluster.local`
- DNS is already the standard way services find each other in Kubernetes
- CoreDNS runs in the cluster and resolves these names

**For GCP:** Cloud Run services get URLs; GKE uses Kubernetes DNS. In GCP, you can also use **Cloud Service Directory** as a managed registry.

---

### Service Mesh (Istio, Linkerd)

**What it is:** A dedicated infrastructure layer for service-to-service communication, implemented as sidecar proxies (Envoy) injected into each pod.

**How it works:**
- Every pod gets a sidecar proxy (Envoy)
- All traffic in and out of the pod goes through the proxy
- The control plane (Istiod) configures the proxies with service discovery data, routing rules, retry policies, mTLS certificates

**What you get for free:**
- Automatic load balancing with health awareness
- Retries, timeouts, circuit breakers — without code changes
- mTLS between services (encryption + mutual authentication)
- Distributed tracing (auto-inject trace headers)
- Traffic splitting for canary deployments

**The cost:** Operational complexity. The sidecar proxy adds latency (small but nonzero), memory overhead, and the control plane is another system to operate.

**When to use a service mesh:** When you have many services and want to enforce consistent retry/circuit breaker/mTLS policies without each service implementing them in code. Strong choice for large Kubernetes deployments on GCP.

**Interview Q&A:**
- Q: How do services discover each other in a microservices architecture?
  A: In Kubernetes, I rely on DNS-based discovery through Services. Each service gets a stable DNS name, and kube-proxy routes traffic to healthy pods — this is server-side discovery. For cross-namespace or cross-cluster calls, I'd use a service mesh like Istio on GCP, which gives me built-in load balancing, mTLS, and retry/circuit breaker policies without modifying application code. If I needed to build client-side discovery outside Kubernetes, I'd use Consul as the registry. The key is that services should never hardcode IPs — they should use DNS names or a registry so the infrastructure can scale pods up/down without application changes.

---

## 9. Health Checks and Readiness

### Liveness vs Readiness Probes (Kubernetes)

| Probe | Question It Answers | Action on Failure |
|-------|--------------------|--------------------|
| **Liveness** | Is the pod alive? (not deadlocked/crashed) | Kubernetes restarts the pod |
| **Readiness** | Is the pod ready to serve traffic? | Kubernetes removes it from the Service's endpoints (stops sending traffic) |
| **Startup** | Has the pod finished starting up? | Prevents liveness/readiness from firing during slow startup |

**Critical distinction:** A pod can be **live** (not deadlocked) but **not ready** (database connection not established yet). During startup, a pod should fail readiness but pass liveness. Once ready, it's added to the load balancer pool.

**What health checks should verify:**
- Database connectivity (can we query the DB?)
- Critical downstream dependencies (Kafka, Redis)
- NOT: every dependency — if a non-critical service is down, don't mark yourself unready

```go
// Go health check handler
http.HandleFunc("/healthz/live", func(w http.ResponseWriter, r *http.Request) {
    // Just check the process is alive
    w.WriteHeader(http.StatusOK)
})

http.HandleFunc("/healthz/ready", func(w http.ResponseWriter, r *http.Request) {
    // Check critical dependencies
    if err := db.PingContext(r.Context()); err != nil {
        w.WriteHeader(http.StatusServiceUnavailable)
        return
    }
    w.WriteHeader(http.StatusOK)
})
```

```yaml
# Kubernetes probe config
livenessProbe:
  httpGet:
    path: /healthz/live
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /healthz/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

### SLA vs SLO vs SLI

| Term | Definition | Who Uses It | Example |
|------|------------|-------------|---------|
| **SLI** (Service Level Indicator) | The metric you measure | Engineering | 99th percentile request latency |
| **SLO** (Service Level Objective) | The target for the metric | Engineering + Product | p99 latency < 200ms, 99.9% of the time |
| **SLA** (Service Level Agreement) | Contractual commitment with penalties | Business + Customers | "99.9% uptime; if below, 10% credit on invoice" |

**Key relationships:**
- SLI is the measurement
- SLO is the internal target (tighter than the SLA — gives you headroom)
- SLA is what you commit to externally; breaching it costs money

**Error budget:** If your SLO is 99.9% availability, you have a 0.1% error budget — about 43 minutes of downtime per month. Engineering teams track error budget consumption to decide whether to ship new features (consumes budget via risk) or focus on reliability.

**Interview Q&A:**
- Q: What is the difference between an SLA, SLO, and SLI?
  A: SLI is the metric — what you actually measure, like p99 latency or error rate. SLO is the target — "p99 latency must be under 200ms 99.9% of the time." SLA is the contractual commitment to customers with business consequences for breaching it. In practice, you set your SLO tighter than your SLA to give yourself headroom — if your SLA commits to 99.9% uptime, you internally target 99.95% so you have buffer before you breach the contract. The error budget concept flows from SLOs: if you have a 0.1% error budget for the month, teams track burn rate to decide when to freeze risky releases.

---

## 10. Observability — The Three Pillars

> **Key insight:** You cannot debug a distributed system you cannot observe. Observability is not an afterthought — it's a design requirement that you bake in from day one.

### Metrics

**What they are:** Numeric measurements sampled over time. CPU usage, memory, request rate, error rate, latency percentiles.

**The Four Golden Signals (Google SRE):**

| Signal | What It Measures | Example |
|--------|-----------------|---------|
| **Latency** | How long requests take | p50, p95, p99 of HTTP response time |
| **Traffic** | How much demand the system is under | Requests per second |
| **Errors** | Rate of failed requests | 5xx error rate |
| **Saturation** | How full your service is | CPU %, memory %, queue depth |

**Prometheus + Grafana:**
- **Prometheus** scrapes metrics from `/metrics` endpoints on your pods (pull model)
- Stores time-series data locally with a 15-day default retention
- **Grafana** queries Prometheus and renders dashboards
- Alert rules in Prometheus → AlertManager → PagerDuty/Slack

```go
// Go: expose a Prometheus metric
import "github.com/prometheus/client_golang/prometheus"

var httpDuration = prometheus.NewHistogramVec(
    prometheus.HistogramOpts{
        Name:    "http_request_duration_seconds",
        Help:    "HTTP request duration",
        Buckets: prometheus.DefBuckets,
    },
    []string{"handler", "method", "status"},
)

// In your handler:
timer := prometheus.NewTimer(httpDuration.WithLabelValues("/api/apply", "POST", "200"))
defer timer.ObserveDuration()
```

---

### Logging

**What it is:** Discrete events with context — "user X submitted application Y at time T."

**Structured vs unstructured:**

| Type | Example | Problem |
|------|---------|---------|
| Unstructured | `"Error processing request from 1.2.3.4"` | Hard to query, can't filter by field |
| Structured | `{"level":"error","user_id":"u123","error":"db timeout","trace_id":"abc"}` | Queryable, filterable, machine-readable |

At scale, unstructured logs are nearly useless. You can't write a query that extracts "all errors for user_id u123." Structured logs (JSON) let you filter, aggregate, and correlate.

**Correlation IDs:** Generate a unique `trace_id` (or `request_id`) at the edge (API gateway or first service). Pass it through every downstream call as a header. Log it in every log line. Now you can query all logs across all services for a single user request.

**ELK / EFK Stack:**
- **Elasticsearch:** Stores and indexes logs
- **Logstash / Fluentd:** Ships and transforms logs from pods to Elasticsearch
- **Kibana:** Queries and visualizes logs
- In Kubernetes: Fluentd runs as a DaemonSet and ships pod logs to Elasticsearch

---

### Distributed Tracing

**What it is:** Following a single request as it travels across multiple services — each hop recorded as a **span**.

**Why it matters:** A user request to `/apply` might fan out to: API Gateway → Application Service → Document Service → Notification Service. If it's slow, which service is the bottleneck? You can't tell from logs alone.

**Core concepts:**

| Concept | Definition |
|---------|------------|
| **Trace** | The entire journey of one request, end-to-end |
| **Span** | A single operation within a trace (one service call, one DB query) |
| **Parent span** | The span that triggered the current span |
| **Trace ID** | Unique ID for the entire trace; propagated in HTTP headers |

```
Trace: user clicks "Submit Application"
  ├── Span: API Gateway (5ms)
  ├── Span: Application Service (200ms)
  │     ├── Span: PostgreSQL INSERT (50ms)
  │     └── Span: Kafka Produce (10ms)
  └── Span: Notification Service (80ms)
```

**OpenTelemetry:** The standard for instrumentation. Language-specific SDKs instrument your code (or do it automatically). Traces are exported to Jaeger (open-source) or Google Cloud Trace (managed on GCP).

```go
// Go: OpenTelemetry trace span
tracer := otel.Tracer("application-service")
ctx, span := tracer.Start(ctx, "create-application")
defer span.End()

span.SetAttributes(attribute.String("user.id", userID))
```

**Interview Q&A:**
- Q: What is distributed tracing and why is it important?
  A: Distributed tracing records the path of a single request as it flows through multiple services. Each service creates a "span" — a timed record of the work it did — and links it to the parent span via a shared trace ID propagated in HTTP headers. When I look at a trace in Jaeger, I see a waterfall: which services were called, in what order, how long each took, and where errors occurred. Without this, debugging latency issues in microservices is nearly impossible — you can see that p99 latency spiked, but you can't tell if it's the database, a downstream service, or your own code. I use OpenTelemetry for instrumentation on GCP because it's vendor-neutral and exports to Cloud Trace.

---

### Alert Fatigue

**The danger:** If every metric has an alert, oncall engineers get paged constantly. Most alerts are noise. Engineers start ignoring them. When a real incident happens, it gets missed.

**Solution:** Alert only on symptoms, not causes. Alert on the **four golden signals**:
- Error rate exceeds X% → user-facing impact
- p99 latency exceeds Y ms → user-facing impact
- Don't alert on CPU at 80% if users aren't affected

**Page for:** Things that require human action RIGHT NOW.
**Ticket for:** Things that should be investigated but aren't urgent.

---

## 11. Gossip Protocol

**What it is:** A peer-to-peer communication protocol where nodes periodically share state information with a small random set of peers. Information spreads exponentially through the cluster.

**How it works:**
1. Each node maintains a list of known nodes and their state (alive, dead, joining)
2. Every T milliseconds, each node selects K random peers and shares its state
3. Peers merge the received state with their own view
4. Information about a new node or a dead node propagates through the cluster in O(log N) rounds

**Why it works:** Similar to how gossip spreads in a social network. If you tell 3 people, and each of them tells 3 more people, the information reaches everyone exponentially fast.

**Used in:**
- **Cassandra** — cluster membership and schema changes
- **Redis Cluster** — node state propagation, failure detection
- **Consul** — node health and service registration (uses SWIM protocol, a gossip variant)
- **Amazon DynamoDB** — membership protocol

**Why not use a central registry?**
- Central registry = single point of failure
- Under large cluster sizes (1000s of nodes), a central registry becomes a bottleneck
- Gossip is O(log N) and fully decentralized

---

## 12. Geo-Distribution and Multi-Region

### Why Multi-Region

| Reason | What It Buys |
|--------|-------------|
| **Latency** | Users in India get data from Mumbai region, not US-East |
| **Availability** | One region fails → traffic routed to another |
| **Compliance** | Data residency laws require data to stay in a country |
| **Disaster recovery** | Independent failure domains |

---

### Active-Active vs Active-Passive

| Model | Active-Active | Active-Passive |
|-------|--------------|----------------|
| Write handling | Multiple regions accept writes simultaneously | Only primary region accepts writes |
| Read handling | Each region serves reads locally | Both serve reads |
| Consistency | Harder — concurrent writes can conflict | Simpler — one writer |
| Failover | Instant — traffic shifts to healthy region | Requires promotion of passive to active |
| Use case | Ultra-low latency globally, reads >> writes | Disaster recovery, simpler consistency model |
| Example | Cassandra multi-DC, DynamoDB Global Tables | PostgreSQL with streaming replication |

---

### Conflict Resolution in Multi-Region Writes

When two regions accept writes to the same data concurrently:

| Strategy | How It Works | Risk |
|----------|-------------|------|
| **Last-Write-Wins (LWW)** | Higher timestamp wins | Clock skew can cause data loss |
| **Vector clocks** | Track causal history; detect concurrent writes | Requires application-level merge |
| **CRDTs** | Data structures designed to merge automatically (counters, sets) | Limited to certain data types |
| **Application-level merge** | Custom business logic decides the winner | Most flexible, most work |

**For most FAANG interviews:** Active-Passive + read replicas in each region is the safe answer. Active-Active is only worth the complexity if latency requirements demand writes from multiple regions.

---

### Geo-Routing

**How users reach the nearest region:**
- **GeoDNS:** DNS resolver returns different IPs based on the requester's IP geolocation. Route53, Cloud DNS support this.
- **Anycast:** Same IP is advertised from multiple locations; BGP routing naturally sends users to the nearest one. Used by Cloudflare, Google's global load balancers.
- **GCP Global Load Balancer:** Single Anycast IP, routes to the nearest healthy backend pool.

**Interview Q&A:**
- Q: How would you design a system that is resilient to a full data center failure?
  A: I'd deploy to at least two GCP regions in Active-Passive mode to start. The primary region accepts all writes; the secondary has read replicas that are continuously syncing via async replication. I'd use GCP's Global Load Balancer with health checks — if the primary region's health check fails, the load balancer automatically routes traffic to the secondary. For the database, I'd use Cloud SQL with cross-region read replicas, and a runbook to promote the replica if the primary goes down. The RPO is bounded by the replication lag (typically seconds). The RTO depends on how fast the failover automation runs — typically minutes. For zero RPO and near-zero RTO, I'd move to a distributed SQL database like Spanner, which is multi-region by design.

---

## 13. Disaster Recovery

### RTO and RPO

| Metric | Definition | Example |
|--------|------------|---------|
| **RTO** (Recovery Time Objective) | How long can the system be down before it causes unacceptable business impact? | RTO = 1 hour means you must restore service within 1 hour |
| **RPO** (Recovery Point Objective) | How much data loss is acceptable? How far back can you restore from? | RPO = 15 minutes means you can lose at most 15 minutes of data |

**The trade-off:** Lower RTO/RPO = higher cost. Zero RPO requires synchronous replication across regions, which adds latency to every write.

---

### Standby Strategies

| Strategy | What It Is | RTO | RPO | Cost |
|----------|-----------|-----|-----|------|
| **Cold standby** | Infrastructure defined in IaC; must be provisioned and restored from backup | Hours | Hours | Lowest |
| **Warm standby** | Infrastructure running but at reduced scale; restore from recent backup | Minutes | Minutes | Medium |
| **Hot standby** | Full-capacity replica running in sync; instant failover | Seconds | Near-zero | Highest |

**In Kubernetes on GCP:** Warm standby is achievable relatively cheaply — keep a scaled-down cluster in a second region, with database replicas syncing. On failure, scale up the cluster and promote the replica.

---

### Backup Strategies

| Type | How It Works | RPO |
|------|-------------|-----|
| **Full backup** | Complete snapshot of all data | Up to 24h (if daily) |
| **Incremental backup** | Only changes since last backup | Shorter; combine with full |
| **Continuous / WAL archiving** | PostgreSQL WAL shipped to object storage constantly | Seconds to minutes |

**For PostgreSQL on GCP:** Cloud SQL automated backups + point-in-time recovery (WAL archiving). You can restore to any point in the last 7 days.

---

### Chaos Engineering

**What it is:** Deliberately injecting failures into production systems to discover weaknesses before they cause incidents.

**The philosophy:** If failure is inevitable (and it is), you'd rather discover your failure modes in a controlled experiment than in a real incident at 3am.

**Netflix Chaos Monkey:** Randomly terminates pods in production to ensure services are resilient to instance failures. If your services can't survive random pod termination in production, they're not truly resilient.

**Levels of chaos:**
1. Kill random pods (basic — ensures restarts work)
2. Introduce network latency between services (tests timeouts, circuit breakers)
3. Kill an entire region (tests multi-region failover)
4. Exhaust CPU/memory on nodes (tests resource limits)

**In Kubernetes:** Tools like **Chaos Mesh** or **LitmusChaos** let you define chaos experiments as Kubernetes CRDs.

---

## Quick Revision Cheatsheet

### Consistency Models
| Model | Real Use |
|-------|---------|
| Strong | Bank balance, seat booking |
| Eventual | DNS, social feed, view counts |
| Read-your-writes | Profile updates, settings |
| Causal | Social posts + replies ordering |

### Distributed Transactions
- **2PC:** Blocks on coordinator failure. Don't use across microservices.
- **Saga:** Sequence of local txns + compensating txns. Industry standard.
- **Choreography:** Events. Loose coupling. Hard to track.
- **Orchestration:** Central state machine. Easier to debug. Preferred for fintech.

### Consensus & Leader Election
- **Raft:** Leader election → log replication → commit to quorum. Used in etcd, CockroachDB, Kafka KRaft.
- **Leader election with Redis:** `SET key uuid NX EX 30` + periodic refresh.
- **Ephemeral nodes in ZooKeeper:** Auto-deleted on session death.

### Fault Tolerance Patterns
- **Retry + Exponential Backoff + Jitter:** Never retry without these three together.
- **Circuit Breaker states:** Closed (normal) → Open (fast fail) → Half-Open (trial) → Closed or Open.
- **Bulkhead:** Separate thread pools per dependency.
- **Idempotency:** The foundation. Without it, retries cause harm.

### Idempotency Implementation
1. Client generates UUID idempotency key
2. Server checks `idempotency_keys` table before processing
3. If exists: return stored response
4. If not: process + insert key atomically (UNIQUE constraint prevents duplicates)
5. Expire keys after 24h

### Distributed Locking
```
SET lock:key <uuid> NX EX <ttl>     # Acquire
Lua script: get-then-delete          # Release safely
```
Prefer idempotency over locks whenever possible.

### Service Discovery in Kubernetes
- **DNS-based:** `service-name.namespace.svc.cluster.local` — default, free, works automatically.
- **Service + kube-proxy:** Server-side discovery; stable ClusterIP; pods come and go.
- **Service mesh (Istio):** Sidecar proxies; adds mTLS, retries, circuit breakers, tracing.

### SLI / SLO / SLA
```
SLI = metric (p99 latency: 180ms)
SLO = target (p99 < 200ms, 99.9% of time)
SLA = contract (99.9% uptime; breach → 10% credit)
Error budget = 100% - SLO% = how much you can burn
```

### Observability Pillars
| Pillar | Tool | Purpose |
|--------|------|---------|
| Metrics | Prometheus + Grafana | Are we healthy? (Four Golden Signals) |
| Logs | ELK/EFK + correlation IDs | What happened? |
| Traces | OpenTelemetry + Jaeger | Where is it slow? |

### Four Golden Signals
1. **Latency** — how long?
2. **Traffic** — how much?
3. **Errors** — how often failing?
4. **Saturation** — how full?

### Multi-Region
| Model | When to Use |
|-------|------------|
| Active-Passive | DR, simpler consistency |
| Active-Active | Global ultra-low latency |

**Conflict resolution:** LWW (simple, risk of loss) → Vector clocks (causal) → CRDTs (auto-merge) → App-level merge (most flexible)

### DR Targets
```
RTO = max downtime tolerated
RPO = max data loss tolerated
Hot standby → lowest RTO/RPO, highest cost
Cold standby → highest RTO/RPO, lowest cost
```

### Gossip Protocol
- Nodes share state with random peers periodically
- O(log N) propagation — scales without central coordinator
- Used in: Cassandra, Redis Cluster, Consul

---

*Track 4 of 5 — Distributed Systems & Reliability*
*System Design Self-Study Series for Gautham Gokulakonda*
