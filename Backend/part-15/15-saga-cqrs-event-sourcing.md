# Part 15.2: Saga, CQRS & Event Sourcing

## What You'll Learn

- Why distributed transactions are fundamentally hard and why 2PC fails at scale
- The Saga pattern: choreography vs orchestration with real examples
- Compensating transactions and how to design robust rollbacks
- CQRS — separating writes from reads to optimize each independently
- Event Sourcing — storing events instead of current state, with full audit trails
- How CQRS and Event Sourcing work together
- Production-ready implementations in Go, Node.js, and Python

---

## Table of Contents

1. [The Distributed Transaction Problem](#1-the-distributed-transaction-problem)
2. [Two-Phase Commit (2PC)](#2-two-phase-commit-2pc)
3. [The Saga Pattern](#3-the-saga-pattern)
4. [Choreography-Based Saga](#4-choreography-based-saga)
5. [Orchestration-Based Saga](#5-orchestration-based-saga)
6. [Compensating Transactions](#6-compensating-transactions)
7. [CQRS — Command Query Responsibility Segregation](#7-cqrs)
8. [Event Sourcing](#8-event-sourcing)
9. [CQRS + Event Sourcing Combined](#9-cqrs--event-sourcing-combined)
10. [How It Works Internally (ASCII Diagrams)](#10-how-it-works-internally)
11. [Implementation Examples](#11-implementation-examples)
12. [Common Patterns & Best Practices](#12-common-patterns--best-practices)
13. [Common Pitfalls](#13-common-pitfalls)
14. [Interview Questions & Answers](#14-interview-questions--answers)
15. [Resources](#15-resources)

---

## 1. The Distributed Transaction Problem

In a monolith, a database transaction gives you ACID guarantees:

```sql
BEGIN;
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;
  UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;  -- both succeed or both fail, atomically
```

In microservices, different operations are in different services with different databases. There is **no shared transaction manager**. You cannot do:

```
BEGIN DISTRIBUTED TRANSACTION  ← this doesn't work across services
  Order Service: INSERT INTO orders ...
  Payment Service: UPDATE payments ...
  Inventory Service: UPDATE inventory ...
COMMIT  ← you cannot atomically commit across 3 different DBs
```

**The core tension:** Business operations (place order, transfer money) often span multiple services, but distributed systems cannot guarantee atomicity across service boundaries without specialized (and expensive) coordination protocols.

**What can go wrong:**

```
Step 1: Order Service creates order (SUCCESS)
Step 2: Payment Service charges customer (SUCCESS)
Step 3: Inventory Service reserves items (FAILS — out of stock)

Now you have:
- An order in "pending" state in orders_db
- Money charged from customer in payments_db
- No reservation in inventory_db

System is in an INCONSISTENT state.
Who cleans up? How?
```

---

## 2. Two-Phase Commit (2PC)

2PC is a classical protocol for distributed atomic transactions. It involves a coordinator and multiple participant nodes.

### Phase 1 — Prepare (Voting)

```
Coordinator
    │
    ├── "Can you commit?" ──────────► Order DB
    │                                  └── "YES (I've locked rows)"
    │
    ├── "Can you commit?" ──────────► Payment DB
    │                                  └── "YES (I've locked rows)"
    │
    └── "Can you commit?" ──────────► Inventory DB
                                       └── "NO (out of stock)"
```

### Phase 2 — Commit or Rollback

```
If ALL vote YES:
    Coordinator ──► "COMMIT" ──► Order DB
    Coordinator ──► "COMMIT" ──► Payment DB
    Coordinator ──► "COMMIT" ──► Inventory DB

If ANY vote NO:
    Coordinator ──► "ROLLBACK" ──► Order DB
    Coordinator ──► "ROLLBACK" ──► Payment DB
    (Inventory already said NO, nothing to rollback)
```

### Why 2PC Fails in Microservices

**1. Blocking protocol — locks are held through both phases:**

During the prepare phase, each participant locks the relevant rows. If the coordinator crashes between Phase 1 and Phase 2, the locks are held indefinitely. Other transactions that need those rows are blocked. In a high-traffic system, this is catastrophic.

```
Phase 1 complete (all voted YES, rows locked)
Coordinator CRASHES
    │
    ▼ Participants wait for Phase 2...
    │ ...still waiting...
    │ ...rows still locked...
    │ ...other transactions piling up...
    └── System grinds to a halt
```

**2. Single point of failure:** The coordinator is a bottleneck. Its failure freezes all in-flight transactions.

**3. Availability vs Consistency (CAP theorem):** 2PC sacrifices availability for consistency. In a network partition, the coordinator can't reach participants → transaction blocked. For internet-scale systems, availability is often more valuable than strict consistency.

**4. Not supported by most modern infrastructure:** Cloud databases (DynamoDB, Cassandra), message queues, and external APIs don't participate in 2PC. You can't 2PC across a DB and Kafka.

**5. Performance:** 2PC requires multiple round trips and lock acquisition. At high throughput, this becomes a serious bottleneck.

---

## 3. The Saga Pattern

A Saga is a sequence of local transactions. Each local transaction updates data within a single service and publishes an event or message to trigger the next step. If a step fails, the saga executes compensating transactions to undo the completed steps.

**Key insight:** Instead of one atomic distributed transaction, you have multiple atomic local transactions with compensation for failure.

```
SAGA = [T1, T2, T3, ..., Tn]
Where each Ti is a local transaction in one service.

On success: T1 → T2 → T3 → ... → Tn (all succeed)

On failure at Ti:
  Execute compensating transactions:
  C(i-1) → C(i-2) → ... → C1

Where C(j) undoes the effect of Tj.
```

### Key Properties

- **Eventual consistency** — the system will be consistent eventually, not immediately
- **Local transactions** — each step is an atomic transaction within one service
- **No distributed locks** — no blocking, no single point of failure
- **Compensation over rollback** — you undo effects semantically, not at the DB level

### Order Placement Saga Example

```
HAPPY PATH (all steps succeed):
┌─────────────────────────────────────────────────────────────────┐
│ 1. Order Svc    → Create order (status: PENDING)               │
│ 2. Payment Svc  → Reserve payment (deduct from account)        │
│ 3. Inventory Svc→ Reserve items (decrement stock)              │
│ 4. Shipping Svc → Create shipment record                       │
│ 5. Order Svc    → Confirm order (status: CONFIRMED)            │
└─────────────────────────────────────────────────────────────────┘

FAILURE AT STEP 3 (Inventory out of stock):
┌─────────────────────────────────────────────────────────────────┐
│ 1. Order Svc    → Create order (status: PENDING)    ✓          │
│ 2. Payment Svc  → Reserve payment                   ✓          │
│ 3. Inventory Svc→ Reserve items                     ✗ FAILS    │
│                                                                 │
│ COMPENSATION (in reverse order):                               │
│ 3. Inventory Svc→ N/A (nothing reserved)                       │
│ 2. Payment Svc  → Release reserved payment         ◄── undo   │
│ 1. Order Svc    → Cancel order (status: CANCELLED) ◄── undo   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Choreography-Based Saga

In choreography, there is **no central coordinator**. Each service knows what to do after its step completes. Services communicate via events.

```
Order Service          Event Bus           Payment Service        Inventory Service
     │                    │                     │                      │
     │── OrderCreated ───►│                     │                      │
     │   {orderId,total}  │                     │                      │
     │                    │── OrderCreated ────►│                      │
     │                    │                     │── reserve payment    │
     │                    │                     │── PaymentReserved ──►│
     │                    │                     │   or                 │
     │                    │                     │── PaymentFailed ────►│ (triggers compensation)
     │                    │                     │                      │── reserve inventory
     │                    │◄── InventoryReserved─────────────────────  │
     │◄── InventoryReserved│                    │                      │
     │  (Order Svc listens │                    │                      │
     │   and confirms)     │                    │                      │
     │── OrderConfirmed ──►│                    │                      │
```

**Pros:**
- No central coordinator → no single point of failure
- Services are loosely coupled; they only know about events, not other services
- Simple to add new services that react to existing events (open/closed principle)

**Cons:**
- **Hard to see the overall flow** — you must read multiple services' event handlers to understand the full saga
- **Distributed debugging** — when a saga fails, piecing together what happened requires correlating events across services
- **Risk of cyclic dependencies** — Service A listens to Service B's events, B listens to C, C listens to A → logic loops
- **Difficult to add new steps** — adding a step mid-saga requires careful event sequencing

---

## 5. Orchestration-Based Saga

In orchestration, a central **Saga Orchestrator** (also called Process Manager) controls the saga flow. It tells each service what to do and tracks the overall state.

```
┌─────────────────────────────────────────────────────────────┐
│                     SAGA ORCHESTRATOR                       │
│                                                             │
│  State machine:                                             │
│  STARTED → PAYMENT_PENDING → INVENTORY_PENDING →           │
│  SHIPPING_PENDING → COMPLETED                               │
│  (or any step → COMPENSATING → CANCELLED)                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
    Payment Svc          Inventory Svc         Shipping Svc
  (receives command,    (receives command,    (receives command,
   sends reply)          sends reply)          sends reply)
```

**Orchestrator flow:**

```
1. Orchestrator sends ReservePaymentCommand to Payment Service
2. Payment Service replies: PaymentReservedEvent OR PaymentFailedEvent
3. If success: Orchestrator sends ReserveInventoryCommand to Inventory Service
4. Inventory Service replies: InventoryReservedEvent OR InventoryFailedEvent
5. If success: Orchestrator sends CreateShipmentCommand to Shipping Service
6. If success: Orchestrator sends ConfirmOrderCommand to Order Service

On failure at step 4:
1. Orchestrator sends ReleasePaymentCommand to Payment Service (compensation)
2. Payment Service replies: PaymentReleasedEvent
3. Orchestrator sends CancelOrderCommand to Order Service (compensation)
4. Saga ends in CANCELLED state
```

**Pros:**
- **Saga flow is visible in one place** — you can read the orchestrator code and understand the entire flow
- **Easier to monitor** — the orchestrator knows what state each saga is in; you can build a dashboard
- **Easier to add steps** — modify the orchestrator, not multiple services

**Cons:**
- **Orchestrator becomes a central piece** — if it's down, sagas can't progress (but sagas can pause and resume)
- **Risk of becoming a smart orchestrator** — business logic creeping into the orchestrator
- **More services to maintain** — the orchestrator is a service itself

**When to choose which:**

| Criterion                         | Choreography     | Orchestration    |
|-----------------------------------|------------------|------------------|
| Number of steps                   | 3–4 steps        | 5+ steps         |
| Need to track saga state          | No               | Yes              |
| Team familiarity                  | Event-driven     | Traditional      |
| Debugging/observability priority  | Lower            | Higher           |
| Adding new step in future         | Harder           | Easier           |

---

## 6. Compensating Transactions

A compensating transaction semantically reverses the effect of a completed transaction. This is NOT a database rollback — the original transaction committed successfully. Compensation is a new forward transaction that undoes the business effect.

### Characteristics of Good Compensating Transactions

1. **Idempotent** — can be called multiple times safely (network retries)
2. **Non-failing** — should always succeed (or retry indefinitely); a compensation that fails leaves the system in a worse state
3. **Semantically correct** — may not perfectly reverse the original (e.g., "cancel order" is different from "order never existed")

### Designing Compensation for Each Step

| Step                         | Forward Transaction          | Compensating Transaction           |
|------------------------------|------------------------------|------------------------------------|
| Create Order                 | INSERT INTO orders           | UPDATE orders SET status=CANCELLED |
| Reserve Payment              | Deduct from user account     | Refund to user account             |
| Reserve Inventory            | Decrement stock quantity     | Increment stock quantity           |
| Create Shipment              | INSERT INTO shipments        | UPDATE shipments SET status=CANCELLED |
| Send Confirmation Email      | Send email (can't unsend!)   | Send cancellation email            |

**The email problem:** Sending an email cannot be undone. Once sent, you can only send another email ("sorry, your order was cancelled"). This is fine — compensating transactions don't need to be perfect reversals, just semantically appropriate.

### Saga State Machine

```
         ┌──────────┐
         │  STARTED │
         └────┬─────┘
              │ payment reserved
              ▼
    ┌──────────────────┐
    │ PAYMENT_RESERVED │◄──── PaymentReservedEvent
    └─────────┬────────┘
              │ inventory reserved
              ▼
  ┌────────────────────────┐
  │ INVENTORY_RESERVED     │◄──── InventoryReservedEvent
  └────────────┬───────────┘
               │ shipment created
               ▼
    ┌─────────────────┐
    │ SHIPMENT_CREATED│◄──── ShipmentCreatedEvent
    └────────┬────────┘
             │ order confirmed
             ▼
       ┌──────────┐
       │COMPLETED │
       └──────────┘

Any step failure:
    ─────────────────────────────►┌──────────────────┐
                                  │   COMPENSATING   │
                                  └────────┬─────────┘
                                           │ all compensations done
                                           ▼
                                    ┌──────────┐
                                    │CANCELLED │
                                    └──────────┘
```

---

## 7. CQRS

**Command Query Responsibility Segregation** separates the model for reading data from the model for writing data.

### The Core Idea

In traditional CRUD:
- The same model handles both reads and writes
- Queries and updates contend on the same DB tables
- The model is a compromise — not perfectly optimized for either

With CQRS:
- **Commands** change state: `CreateOrder`, `UpdateUser`, `CancelOrder`
- **Queries** read state: `GetOrder`, `ListOrders`, `SearchProducts`
- **Write model** (Command side): optimized for consistency, validation, domain rules
- **Read model** (Query side): optimized for query performance, denormalized, pre-computed

```
         ┌─────────────────────────────────────────────┐
         │                APPLICATION                   │
         └──────────────────────┬──────────────────────┘
                                │
               ┌────────────────┴───────────────────┐
               │                                    │
               ▼                                    ▼
      ┌──────────────┐                    ┌──────────────────┐
      │   COMMANDS   │                    │    QUERIES       │
      │              │                    │                  │
      │ CreateOrder  │                    │ GetOrderById     │
      │ CancelOrder  │                    │ ListUserOrders   │
      │ UpdateUser   │                    │ SearchProducts   │
      └──────┬───────┘                    └────────┬─────────┘
             │                                     │
             ▼                                     ▼
    ┌──────────────────┐                  ┌──────────────────┐
    │   WRITE MODEL    │                  │   READ MODEL     │
    │  (Domain logic,  │                  │  (Denormalized,  │
    │   validations,   │                  │   joins pre-done,│
    │   aggregates)    │                  │   fast queries)  │
    └──────┬───────────┘                  └────────┬─────────┘
           │                                       │
           ▼                                       ▼
    ┌──────────────┐   sync/async event   ┌──────────────────┐
    │  Write DB    │ ──────────────────► │    Read DB        │
    │ (PostgreSQL) │  (projection update) │  (PostgreSQL or  │
    │  normalized  │                      │  Elasticsearch   │
    │  ACID        │                      │  or Redis)       │
    └──────────────┘                      └──────────────────┘
```

### Simple CQRS (Same DB, Different Code Paths)

The simplest form of CQRS doesn't require separate databases. It just separates the code:

```go
// Write side: validates and mutates
type CreateOrderCommand struct {
    UserID  string
    Items   []OrderItem
    Total   float64
}

type OrderCommandHandler struct {
    db *sql.DB
}

func (h *OrderCommandHandler) Handle(ctx context.Context, cmd CreateOrderCommand) (string, error) {
    // Domain validation
    if cmd.Total <= 0 {
        return "", errors.New("total must be positive")
    }
    if len(cmd.Items) == 0 {
        return "", errors.New("order must have items")
    }
    
    // Persist through domain model
    order := NewOrder(cmd.UserID, cmd.Items, cmd.Total)
    return h.db.insertOrder(ctx, order)
}

// Read side: just queries, no domain logic
type OrderQueryHandler struct {
    db *sql.DB
}

func (h *OrderQueryHandler) GetByID(ctx context.Context, orderID string) (*OrderView, error) {
    // Optimized query with joins, computed fields
    return h.db.queryOrderView(ctx, orderID)
}

func (h *OrderQueryHandler) ListByUser(ctx context.Context, userID string, page, limit int) ([]OrderSummary, error) {
    return h.db.queryOrdersByUser(ctx, userID, page, limit)
}
```

### Advanced CQRS (Separate Databases)

For high-scale systems, separate the write DB from the read DB:

| Concern               | Write DB (PostgreSQL)           | Read DB                         |
|-----------------------|---------------------------------|---------------------------------|
| Data model            | Normalized, 3NF                 | Denormalized, pre-joined views  |
| Optimized for         | ACID, write throughput          | Query speed, full-text search   |
| Consistency           | Immediate                       | Eventual (few ms to seconds)    |
| Scale pattern         | Vertical                        | Horizontal read replicas        |
| Example use           | Order creation, payment         | Order history page, search      |

**Consistency warning:** After a write, a read from the read DB may return stale data for a few milliseconds. The UI must handle this (e.g., "optimistic update" — show what was just submitted while the projection catches up).

### When to Use CQRS

**Good fit:**
- Complex domain with many different read requirements (dashboards, reports, detail pages)
- Read/write ratio is very skewed (e.g., 100:1 reads to writes)
- Different teams own reads vs writes
- Need to query data in ways that don't match the write model (e.g., full-text search on orders)

**Bad fit:**
- Simple CRUD with basic query needs (don't over-engineer)
- Team unfamiliar with eventual consistency patterns
- Strong consistency required for reads immediately after writes

---

## 8. Event Sourcing

### What Is Event Sourcing?

Instead of storing the current state of an entity, you store the **sequence of events** that led to that state. The current state is derived by replaying events.

```
TRADITIONAL (store state):
┌──────────────────────────────────────────┐
│              orders table                │
│                                          │
│ id  | status    | total | updated_at     │
│ 123 | CONFIRMED | 99.99 | 2024-01-15     │
└──────────────────────────────────────────┘
(history is lost — you can't know how it got here)

EVENT SOURCING (store events):
┌──────────────────────────────────────────────────────────────────┐
│                         events table                             │
│                                                                  │
│ id | aggregate_id | type                | payload         | ts  │
│  1 | order-123    | OrderCreated        | {items, total}  │ ... │
│  2 | order-123    | PaymentReserved     | {amount, txn}   │ ... │
│  3 | order-123    | InventoryReserved   | {items}         │ ... │
│  4 | order-123    | OrderConfirmed      | {}              │ ... │
└──────────────────────────────────────────────────────────────────┘
Current state of order-123 = replay events 1→4
```

### How State Reconstruction Works

```go
// Events define what happened
type OrderCreated struct {
    OrderID string
    UserID  string
    Items   []Item
    Total   float64
}

type PaymentReserved struct {
    OrderID   string
    PaymentID string
    Amount    float64
}

type OrderConfirmed struct {
    OrderID string
}

// The aggregate applies events to rebuild state
type Order struct {
    ID      string
    UserID  string
    Items   []Item
    Total   float64
    Status  string
    events  []Event  // uncommitted events
}

func (o *Order) Apply(event Event) {
    switch e := event.(type) {
    case OrderCreated:
        o.ID = e.OrderID
        o.UserID = e.UserID
        o.Items = e.Items
        o.Total = e.Total
        o.Status = "PENDING"
    case PaymentReserved:
        o.Status = "PAYMENT_RESERVED"
    case OrderConfirmed:
        o.Status = "CONFIRMED"
    }
}

// Reconstruct from event stream
func LoadOrder(events []Event) *Order {
    order := &Order{}
    for _, event := range events {
        order.Apply(event)
    }
    return order
}
```

### Snapshots

Replaying 100,000 events on every load is expensive. Snapshots save a point-in-time state to avoid full replay.

```
Events 1-100: replay from scratch
Events 101-200: replay from scratch
...
Events 1000-1100: replay from scratch (getting slow)

WITH SNAPSHOTS:
At event 1000: save snapshot of current state
At event 1100: load snapshot + replay events 1001-1100 only

Snapshot strategy:
- Every N events (e.g., every 100 events, save snapshot)
- Time-based (save snapshot every hour)
- On demand (manually triggered)
```

### Advantages of Event Sourcing

1. **Full audit trail** — every change is recorded with who did it, when, and why
2. **Time travel** — reconstruct state at any point in the past (replay up to event N)
3. **Event replay for new features** — create a new read model by replaying all historical events
4. **Integration events** — events are first-class; downstream services consume them naturally
5. **Debugging** — when a bug occurs, reproduce it exactly by replaying the exact event sequence

### Disadvantages of Event Sourcing

1. **Complex querying** — you can't `SELECT * FROM orders WHERE status = 'PENDING'` directly; you need a projection
2. **Storage growth** — events accumulate forever; old snapshots help but storage grows
3. **Eventual consistency** — read models are updated asynchronously
4. **Schema evolution** — events are immutable; if you change the `OrderCreated` schema, old events still have the old schema → upcasting needed
5. **Steep learning curve** — most teams are unfamiliar; operational complexity is high

### Event Versioning and Upcasting

Events are written once and must be readable forever. When the schema changes, use "upcasters" to upgrade old events to the new schema.

```go
// v1 of OrderCreated (original)
type OrderCreatedV1 struct {
    OrderID string
    UserID  string
    Total   float64
}

// v2 adds currency field
type OrderCreatedV2 struct {
    OrderID  string
    UserID   string
    Total    float64
    Currency string  // new field
}

// Upcaster: converts V1 to V2 during deserialization
func UpcasterV1toV2(v1 OrderCreatedV1) OrderCreatedV2 {
    return OrderCreatedV2{
        OrderID:  v1.OrderID,
        UserID:   v1.UserID,
        Total:    v1.Total,
        Currency: "USD",  // default for all old events
    }
}
```

---

## 9. CQRS + Event Sourcing Combined

CQRS and Event Sourcing are independent patterns, but they complement each other naturally.

```
                          ┌─────────────────────────────┐
                          │   Command (PlaceOrder)       │
                          └──────────────┬───────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────────┐
                          │   Command Handler             │
                          │   1. Load aggregate from      │
                          │      event store              │
                          │   2. Execute domain logic     │
                          │   3. Emit new events          │
                          └──────────────┬───────────────┘
                                         │ append events
                                         ▼
                          ┌──────────────────────────────┐
                          │       EVENT STORE             │
                          │   (append-only log of events) │
                          └──────────────┬───────────────┘
                                         │ events published
                                         ▼
                          ┌──────────────────────────────┐
                          │     EVENT HANDLERS            │
                          │  (projections / read models)  │
                          │                               │
                          │  OrderListProjection →        │
                          │    updates orders_list table  │
                          │                               │
                          │  OrderDetailProjection →      │
                          │    updates order_detail table │
                          │                               │
                          │  SearchProjection →           │
                          │    updates Elasticsearch      │
                          └──────────────┬───────────────┘
                                         │
                    ┌────────────────────┼─────────────────────┐
                    ▼                    ▼                     ▼
           ┌──────────────┐   ┌──────────────────┐  ┌──────────────────┐
           │  orders_list │   │  order_detail    │  │  Elasticsearch   │
           │  table       │   │  table           │  │  (search index)  │
           │  (for list   │   │  (for detail     │  │  (for full-text  │
           │   page)      │   │   page)          │  │   search)        │
           └──────────────┘   └──────────────────┘  └──────────────────┘
                    ▲                    ▲                     ▲
                    │                   │                      │
                    └────────────────────┴──────────────────────┘
                                    QUERIES
                         (GetOrderList, GetOrderDetail, SearchOrders)
```

**Key insight:** The event store is the source of truth. Read models are derived, disposable, and rebuildable. If a read model gets corrupted or you add a new one, just replay all events from the beginning.

---

## 10. How It Works Internally

### Order Placement Orchestration Saga (Full Flow)

```
Client             Order Svc        Saga Orchestrator      Payment Svc       Inventory Svc
  │                    │                    │                    │                  │
  │── POST /orders ───►│                    │                    │                  │
  │                    │── StartSaga ───────►│                    │                  │
  │                    │   {orderId,total}   │── ReservePayment──►│                  │
  │                    │                    │   Command           │── deduct amount  │
  │                    │                    │                    │── PaymentReserved►│
  │                    │                    │◄── PaymentReserved ─│                  │
  │                    │                    │── ReserveInventory──────────────────►  │
  │                    │                    │   Command           │                  │── check stock
  │                    │                    │                    │     InventoryReserved
  │                    │                    │◄───────────────────────────────────── │
  │                    │                    │── ConfirmOrder ────►│                  │
  │                    │◄── OrderConfirmed ─│                    │                  │
  │◄── 201 Created ────│                    │                    │                  │
  │   {orderId}        │                    │                    │                  │

FAILURE PATH (Inventory fails):
  │                    │                    │── ReserveInventory──────────────────►  │
  │                    │                    │                    │                  │── OUT OF STOCK
  │                    │                    │◄── InventoryFailed ─────────────────── │
  │                    │                    │── ReleasePayment ──►│                  │
  │                    │                    │                    │── refund amount   │
  │                    │                    │◄── PaymentReleased  │                  │
  │                    │                    │── CancelOrder ─────►│                  │
  │                    │◄── OrderCancelled ─│                    │                  │
  │◄── 409 Conflict ───│                    │                    │                  │
  │   {error: out of   │                    │                    │                  │
  │    stock}          │                    │                    │                  │
```

### Event Sourcing — State Reconstruction

```
Event Store (orders stream):

position │ aggregate_id │ type                 │ version
─────────┼──────────────┼──────────────────────┼─────────
    1    │  order-123   │ OrderCreated          │    1
    2    │  order-123   │ PaymentReserved       │    2
    3    │  order-456   │ OrderCreated          │    1  (different order)
    4    │  order-123   │ InventoryReserved     │    3
    5    │  order-123   │ OrderConfirmed        │    4

To load order-123:
SELECT * FROM events
WHERE aggregate_id = 'order-123'
ORDER BY version ASC;
→ returns positions 1, 2, 4, 5
→ replay: Apply(OrderCreated) → Apply(PaymentReserved) → Apply(InventoryReserved) → Apply(OrderConfirmed)
→ final state: Order{status: CONFIRMED, ...}
```

---

## 11. Implementation Examples

### Go + Chi Router

**Orchestration-based Saga:**

```go
// saga/orchestrator.go
package saga

import (
    "context"
    "fmt"
    "log/slog"
    "time"
)

type SagaState string

const (
    SagaStarted              SagaState = "STARTED"
    SagaPaymentPending       SagaState = "PAYMENT_PENDING"
    SagaPaymentReserved      SagaState = "PAYMENT_RESERVED"
    SagaInventoryPending     SagaState = "INVENTORY_PENDING"
    SagaInventoryReserved    SagaState = "INVENTORY_RESERVED"
    SagaCompleted            SagaState = "COMPLETED"
    SagaCompensating         SagaState = "COMPENSATING"
    SagaCancelled            SagaState = "CANCELLED"
)

type OrderSagaData struct {
    SagaID    string
    OrderID   string
    UserID    string
    Total     float64
    Items     []Item
    State     SagaState
    PaymentID string
    CreatedAt time.Time
    UpdatedAt time.Time
}

type OrderSagaOrchestrator struct {
    sagaRepo    SagaRepository
    paymentSvc  PaymentServiceClient
    inventorySvc InventoryServiceClient
    orderSvc    OrderServiceClient
    logger      *slog.Logger
}

func (o *OrderSagaOrchestrator) Start(ctx context.Context, data OrderSagaData) error {
    data.State = SagaPaymentPending
    data.CreatedAt = time.Now()
    
    if err := o.sagaRepo.Save(ctx, data); err != nil {
        return fmt.Errorf("saving saga: %w", err)
    }
    
    return o.executeStep(ctx, data)
}

func (o *OrderSagaOrchestrator) executeStep(ctx context.Context, data OrderSagaData) error {
    switch data.State {
    case SagaPaymentPending:
        return o.reservePayment(ctx, data)
    case SagaPaymentReserved:
        return o.reserveInventory(ctx, data)
    case SagaInventoryReserved:
        return o.confirmOrder(ctx, data)
    case SagaCompensating:
        return o.compensate(ctx, data)
    default:
        o.logger.Warn("unknown saga state", "state", data.State)
        return nil
    }
}

func (o *OrderSagaOrchestrator) reservePayment(ctx context.Context, data OrderSagaData) error {
    result, err := o.paymentSvc.ReservePayment(ctx, ReservePaymentRequest{
        SagaID:  data.SagaID,
        OrderID: data.OrderID,
        UserID:  data.UserID,
        Amount:  data.Total,
    })
    
    if err != nil {
        o.logger.Error("payment reservation failed", "sagaID", data.SagaID, "err", err)
        data.State = SagaCompensating
        if saveErr := o.sagaRepo.Save(ctx, data); saveErr != nil {
            return fmt.Errorf("saving compensating state: %w", saveErr)
        }
        return o.compensate(ctx, data)
    }
    
    data.State = SagaPaymentReserved
    data.PaymentID = result.PaymentID
    if err := o.sagaRepo.Save(ctx, data); err != nil {
        return fmt.Errorf("saving payment reserved state: %w", err)
    }
    
    return o.reserveInventory(ctx, data)
}

func (o *OrderSagaOrchestrator) reserveInventory(ctx context.Context, data OrderSagaData) error {
    _, err := o.inventorySvc.ReserveItems(ctx, ReserveItemsRequest{
        SagaID:  data.SagaID,
        OrderID: data.OrderID,
        Items:   data.Items,
    })
    
    if err != nil {
        o.logger.Error("inventory reservation failed", "sagaID", data.SagaID, "err", err)
        data.State = SagaCompensating
        _ = o.sagaRepo.Save(ctx, data)
        return o.compensate(ctx, data)
    }
    
    data.State = SagaInventoryReserved
    _ = o.sagaRepo.Save(ctx, data)
    return o.confirmOrder(ctx, data)
}

func (o *OrderSagaOrchestrator) confirmOrder(ctx context.Context, data OrderSagaData) error {
    if err := o.orderSvc.ConfirmOrder(ctx, data.OrderID); err != nil {
        return fmt.Errorf("confirming order: %w", err)
    }
    
    data.State = SagaCompleted
    data.UpdatedAt = time.Now()
    return o.sagaRepo.Save(ctx, data)
}

func (o *OrderSagaOrchestrator) compensate(ctx context.Context, data OrderSagaData) error {
    // Release payment if it was reserved
    if data.PaymentID != "" {
        if err := o.paymentSvc.ReleasePayment(ctx, data.PaymentID); err != nil {
            o.logger.Error("compensation: release payment failed", 
                "sagaID", data.SagaID, "paymentID", data.PaymentID, "err", err)
            // Retry compensation — don't return error, schedule retry
        }
    }
    
    // Cancel the order
    if err := o.orderSvc.CancelOrder(ctx, data.OrderID); err != nil {
        o.logger.Error("compensation: cancel order failed", "sagaID", data.SagaID, "err", err)
    }
    
    data.State = SagaCancelled
    data.UpdatedAt = time.Now()
    return o.sagaRepo.Save(ctx, data)
}
```

**Event Sourcing — Order Aggregate:**

```go
// domain/order_aggregate.go
package domain

import (
    "errors"
    "fmt"
    "time"
)

// Events
type Event interface {
    EventType() string
    AggregateID() string
    Version() int
}

type OrderCreated struct {
    id        string
    version   int
    OrderID   string
    UserID    string
    Items     []Item
    Total     float64
    OccurredAt time.Time
}
func (e OrderCreated) EventType() string  { return "order.created" }
func (e OrderCreated) AggregateID() string { return e.OrderID }
func (e OrderCreated) Version() int       { return e.version }

type OrderConfirmed struct {
    id        string
    version   int
    OrderID   string
    OccurredAt time.Time
}
func (e OrderConfirmed) EventType() string  { return "order.confirmed" }
func (e OrderConfirmed) AggregateID() string { return e.OrderID }
func (e OrderConfirmed) Version() int       { return e.version }

type OrderCancelled struct {
    id        string
    version   int
    OrderID   string
    Reason    string
    OccurredAt time.Time
}
func (e OrderCancelled) EventType() string  { return "order.cancelled" }
func (e OrderCancelled) AggregateID() string { return e.OrderID }
func (e OrderCancelled) Version() int       { return e.version }

// Aggregate
type Order struct {
    ID      string
    UserID  string
    Items   []Item
    Total   float64
    Status  string
    Version int
    
    uncommittedEvents []Event
}

// Apply mutates aggregate state from an event — no side effects, deterministic
func (o *Order) Apply(event Event) error {
    switch e := event.(type) {
    case OrderCreated:
        o.ID = e.OrderID
        o.UserID = e.UserID
        o.Items = e.Items
        o.Total = e.Total
        o.Status = "PENDING"
        o.Version = e.Version()
    case OrderConfirmed:
        if o.Status != "PAYMENT_RESERVED" && o.Status != "INVENTORY_RESERVED" {
            return fmt.Errorf("cannot confirm order in status %s", o.Status)
        }
        o.Status = "CONFIRMED"
        o.Version = e.Version()
    case OrderCancelled:
        if o.Status == "CONFIRMED" {
            return errors.New("cannot cancel a confirmed order")
        }
        o.Status = "CANCELLED"
        o.Version = e.Version()
    default:
        return fmt.Errorf("unknown event type: %T", event)
    }
    return nil
}

// Raise records an event to be emitted
func (o *Order) Raise(event Event) {
    o.Apply(event)
    o.uncommittedEvents = append(o.uncommittedEvents, event)
}

// Load reconstructs an aggregate from its event history
func LoadOrder(events []Event) (*Order, error) {
    order := &Order{}
    for _, event := range events {
        if err := order.Apply(event); err != nil {
            return nil, fmt.Errorf("applying event %s: %w", event.EventType(), err)
        }
    }
    return order, nil
}

// Business methods
func (o *Order) Confirm() error {
    if o.Status != "INVENTORY_RESERVED" {
        return fmt.Errorf("cannot confirm: current status is %s", o.Status)
    }
    o.Raise(OrderConfirmed{
        OrderID:    o.ID,
        OccurredAt: time.Now().UTC(),
        version:    o.Version + 1,
    })
    return nil
}

func (o *Order) Cancel(reason string) error {
    if o.Status == "CONFIRMED" {
        return errors.New("confirmed orders cannot be cancelled")
    }
    o.Raise(OrderCancelled{
        OrderID:    o.ID,
        Reason:     reason,
        OccurredAt: time.Now().UTC(),
        version:    o.Version + 1,
    })
    return nil
}
```

---

### Node.js + Express

**CQRS with separate command and query handlers:**

```javascript
// orders/commands/create-order.handler.js
const { v4: uuidv4 } = require('uuid');
const EventBus = require('../../infrastructure/event-bus');

class CreateOrderHandler {
  constructor(orderRepository, eventBus) {
    this.orderRepository = orderRepository;
    this.eventBus = eventBus;
  }

  async handle(command) {
    const { userId, items, total, shippingAddress } = command;

    // Validation (domain logic)
    if (!items || items.length === 0) {
      throw new Error('Order must have at least one item');
    }
    if (total <= 0) {
      throw new Error('Order total must be positive');
    }

    const orderId = uuidv4();
    const order = {
      id: orderId,
      userId,
      items,
      total,
      shippingAddress,
      status: 'PENDING',
      createdAt: new Date(),
    };

    // Write to write DB
    await this.orderRepository.save(order);

    // Publish domain event (for projections and other consumers)
    await this.eventBus.publish('orders', {
      eventType: 'order.created',
      aggregateId: orderId,
      payload: order,
      occurredAt: new Date().toISOString(),
    });

    return { orderId };
  }
}

// orders/queries/get-order.handler.js
class GetOrderHandler {
  constructor(orderReadRepository) {
    this.orderReadRepository = orderReadRepository;
  }

  async handle(query) {
    const { orderId, userId } = query;

    // Query read model (potentially different DB)
    const order = await this.orderReadRepository.findById(orderId);

    if (!order) {
      throw new NotFoundError(`Order ${orderId} not found`);
    }

    // Authorization check
    if (order.userId !== userId) {
      throw new ForbiddenError('You can only view your own orders');
    }

    return order;
  }
}

// orders/projections/order-list.projection.js
// This runs as a background service consuming events
class OrderListProjection {
  constructor(readDb) {
    this.readDb = readDb;
  }

  async onOrderCreated(event) {
    const { payload } = event;
    await this.readDb.query(
      `INSERT INTO order_list_view (id, user_id, status, total, item_count, created_at)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (id) DO NOTHING`,
      [payload.id, payload.userId, payload.status, payload.total, payload.items.length, payload.createdAt]
    );
  }

  async onOrderConfirmed(event) {
    await this.readDb.query(
      `UPDATE order_list_view SET status = 'CONFIRMED' WHERE id = $1`,
      [event.aggregateId]
    );
  }

  async onOrderCancelled(event) {
    await this.readDb.query(
      `UPDATE order_list_view SET status = 'CANCELLED' WHERE id = $1`,
      [event.aggregateId]
    );
  }
}

// orders/routes.js — Express routes wiring commands and queries
const express = require('express');
const router = express.Router();

// COMMAND route
router.post('/', async (req, res) => {
  try {
    const result = await createOrderHandler.handle({
      userId: req.headers['x-user-id'],
      items: req.body.items,
      total: req.body.total,
      shippingAddress: req.body.shippingAddress,
    });
    res.status(201).json(result);
  } catch (err) {
    if (err.message.includes('must have')) {
      return res.status(400).json({ error: err.message });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

// QUERY route
router.get('/:orderId', async (req, res) => {
  try {
    const order = await getOrderHandler.handle({
      orderId: req.params.orderId,
      userId: req.headers['x-user-id'],
    });
    res.json(order);
  } catch (err) {
    if (err instanceof NotFoundError) return res.status(404).json({ error: err.message });
    if (err instanceof ForbiddenError) return res.status(403).json({ error: err.message });
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;
```

---

### Python + FastAPI

**Event Sourcing with aggregate and event store:**

```python
# domain/order_aggregate.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any
from enum import Enum
import uuid

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAYMENT_RESERVED = "PAYMENT_RESERVED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    aggregate_id: str = ""
    event_type: str = ""
    version: int = 0
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    payload: dict = field(default_factory=dict)

@dataclass
class OrderCreatedEvent(DomainEvent):
    event_type: str = "order.created"

@dataclass
class PaymentReservedEvent(DomainEvent):
    event_type: str = "order.payment_reserved"

@dataclass
class OrderConfirmedEvent(DomainEvent):
    event_type: str = "order.confirmed"

@dataclass
class OrderCancelledEvent(DomainEvent):
    event_type: str = "order.cancelled"

class Order:
    def __init__(self):
        self.id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.items: List[dict] = []
        self.total: float = 0.0
        self.status: Optional[OrderStatus] = None
        self.version: int = 0
        self._uncommitted_events: List[DomainEvent] = []

    def _apply(self, event: DomainEvent) -> None:
        """Apply an event to mutate state. Pure, no side effects."""
        if isinstance(event, OrderCreatedEvent):
            self.id = event.aggregate_id
            self.user_id = event.payload["user_id"]
            self.items = event.payload["items"]
            self.total = event.payload["total"]
            self.status = OrderStatus.PENDING
            self.version = event.version
        elif isinstance(event, PaymentReservedEvent):
            self.status = OrderStatus.PAYMENT_RESERVED
            self.version = event.version
        elif isinstance(event, OrderConfirmedEvent):
            self.status = OrderStatus.CONFIRMED
            self.version = event.version
        elif isinstance(event, OrderCancelledEvent):
            self.status = OrderStatus.CANCELLED
            self.version = event.version

    def _raise(self, event: DomainEvent) -> None:
        """Record and apply an event."""
        self._apply(event)
        self._uncommitted_events.append(event)

    @classmethod
    def create(cls, order_id: str, user_id: str, items: list, total: float) -> "Order":
        if not items:
            raise ValueError("Order must have at least one item")
        if total <= 0:
            raise ValueError("Order total must be positive")

        order = cls()
        order._raise(OrderCreatedEvent(
            aggregate_id=order_id,
            version=1,
            payload={"user_id": user_id, "items": items, "total": total},
        ))
        return order

    @classmethod
    def load_from_history(cls, events: List[DomainEvent]) -> "Order":
        order = cls()
        for event in events:
            order._apply(event)
        return order

    def confirm(self) -> None:
        if self.status != OrderStatus.PAYMENT_RESERVED:
            raise ValueError(f"Cannot confirm order in status {self.status}")
        self._raise(OrderConfirmedEvent(
            aggregate_id=self.id,
            version=self.version + 1,
        ))

    def cancel(self, reason: str) -> None:
        if self.status == OrderStatus.CONFIRMED:
            raise ValueError("Cannot cancel a confirmed order")
        self._raise(OrderCancelledEvent(
            aggregate_id=self.id,
            version=self.version + 1,
            payload={"reason": reason},
        ))

    def pop_uncommitted_events(self) -> List[DomainEvent]:
        events = self._uncommitted_events.copy()
        self._uncommitted_events.clear()
        return events


# infrastructure/event_store.py
import asyncpg
from typing import List
import json

class PostgresEventStore:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def append(self, events: List[DomainEvent], expected_version: int) -> None:
        """
        Append events with optimistic concurrency check.
        expected_version: the version we think the aggregate is at.
        If another process wrote events since we loaded, this fails.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Check current version (optimistic lock)
                if events:
                    current = await conn.fetchval(
                        "SELECT MAX(version) FROM events WHERE aggregate_id = $1",
                        events[0].aggregate_id
                    )
                    current_version = current or 0
                    if current_version != expected_version:
                        raise ConcurrencyError(
                            f"Expected version {expected_version}, got {current_version}"
                        )

                for event in events:
                    await conn.execute(
                        """INSERT INTO events
                           (event_id, aggregate_id, event_type, version, payload, occurred_at)
                           VALUES ($1, $2, $3, $4, $5, $6)""",
                        event.event_id,
                        event.aggregate_id,
                        event.event_type,
                        event.version,
                        json.dumps(event.payload),
                        event.occurred_at,
                    )

    async def load(self, aggregate_id: str) -> List[DomainEvent]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT event_type, version, payload, occurred_at
                   FROM events
                   WHERE aggregate_id = $1
                   ORDER BY version ASC""",
                aggregate_id,
            )
            return [_deserialize_event(row) for row in rows]


# FastAPI endpoints
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

app = FastAPI()

class PlaceOrderRequest(BaseModel):
    items: list[dict]
    total: float
    shipping_address: str

@app.post("/orders", status_code=201)
async def place_order(
    request: PlaceOrderRequest,
    x_user_id: str = Header(...),
):
    order_id = str(uuid.uuid4())

    # Create aggregate (raises events internally)
    try:
        order = Order.create(
            order_id=order_id,
            user_id=x_user_id,
            items=request.items,
            total=request.total,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Persist events
    events = order.pop_uncommitted_events()
    await event_store.append(events, expected_version=0)

    # Publish to message broker for projections
    for event in events:
        await kafka_producer.send("orders", value=event.__dict__)

    return {"order_id": order_id}

@app.get("/orders/{order_id}")
async def get_order(order_id: str, x_user_id: str = Header(...)):
    # Load from read model (projection), NOT from event store
    # (event store is for writes; read from denormalized view)
    order = await order_read_repo.find_by_id(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if order["user_id"] != x_user_id:
        raise HTTPException(403, "Forbidden")
    return order
```

---

## 12. Common Patterns & Best Practices

### Saga Timeout and Dead Letter Queue

Sagas can get stuck if a service is down. Always implement timeouts and a dead letter queue for stuck sagas.

```go
// Scheduled job that checks for stuck sagas
func (o *SagaMonitor) CheckStuckSagas(ctx context.Context) error {
    stuck, err := o.sagaRepo.FindStuck(ctx, 30*time.Minute)
    for _, saga := range stuck {
        o.logger.Warn("stuck saga detected", "sagaID", saga.SagaID, "state", saga.State)
        // Alert on-call, trigger compensation, or move to dead letter queue
        o.alerting.Notify(fmt.Sprintf("Saga %s stuck in state %s for >30min", 
            saga.SagaID, saga.State))
    }
    return err
}
```

### Idempotent Event Handlers

Event handlers (projections) may receive the same event more than once (at-least-once delivery). Make them idempotent.

```sql
-- Use INSERT ... ON CONFLICT DO NOTHING to handle duplicates
INSERT INTO order_list_view (id, user_id, status, total, created_at)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (id) DO NOTHING;

-- Or track processed event IDs
INSERT INTO processed_events (event_id, processed_at)
VALUES ($1, NOW())
ON CONFLICT (event_id) DO NOTHING
RETURNING event_id;
-- If RETURNING returns no rows, event was already processed → skip
```

### Outbox Pattern

The "dual write problem": after saving to DB and before publishing to Kafka, the process crashes. The event is lost.

```
PROBLEM:
1. Save order to orders table ✓
2. Publish OrderCreated to Kafka ✗ CRASH
→ DB has order, Kafka has no event → projection never updated

SOLUTION (Outbox Pattern):
1. In the SAME DB transaction:
   - Save order to orders table
   - Save OrderCreated to outbox table
2. Background poller reads from outbox table
3. Publishes to Kafka
4. Deletes from outbox table (or marks as published)
→ Atomic: either both succeed or both fail
```

```go
// Transaction with outbox
func (r *OrderRepository) CreateOrderWithOutbox(ctx context.Context, order Order, events []Event) error {
    return r.db.WithTransaction(ctx, func(tx *sql.Tx) error {
        // 1. Save order
        if _, err := tx.ExecContext(ctx, "INSERT INTO orders ...", order); err != nil {
            return err
        }
        
        // 2. Save events to outbox (same transaction!)
        for _, event := range events {
            payload, _ := json.Marshal(event)
            if _, err := tx.ExecContext(ctx,
                "INSERT INTO outbox (event_id, topic, payload, created_at) VALUES ($1, $2, $3, NOW())",
                event.ID, "orders", payload,
            ); err != nil {
                return err
            }
        }
        return nil
    })
}
```

---

## 13. Common Pitfalls

### 1. Forgetting to Design Compensating Transactions

Teams implement the happy path saga and forget to design compensations. When failures happen in production, the system is in an inconsistent state with no recovery path.

**Fix:** For every step in the saga, define the compensating transaction before writing the code. Write it down explicitly.

### 2. Non-Idempotent Compensation

A compensating transaction that fails on retry makes things worse. "Release payment" is called twice → payment refunded twice.

**Fix:** Every compensating transaction must be idempotent. Use idempotency keys with the payment provider. Track compensation state.

### 3. CQRS Everywhere

Not every service needs CQRS. Applying it to a simple User CRUD service adds complexity with no benefit.

**Fix:** Use CQRS only when the write model and read model are fundamentally different (complex domain, very different query patterns, high scale).

### 4. Event Sourcing Without Snapshots

Rebuilding state by replaying 500,000 events every time is unusably slow.

**Fix:** Implement snapshots from day one if event volume is expected to be high. Common threshold: take a snapshot every 100–500 events.

### 5. Not Versioning Events

Adding a required field to an existing event type without versioning breaks old event replay.

**Fix:** Always version events. Use `event_type: "order.created.v2"` or a `schema_version` field. Write upcasters for each version transition.

### 6. Using Event Sourcing for Everything

Event Sourcing is complex. Using it for a user registration form is overkill.

**Fix:** Use Event Sourcing for aggregates that have complex business logic, need full audit trails, or where time travel is genuinely useful.

---

## 14. Interview Questions & Answers

**Q: What is the Saga pattern and when do you use it?**

A Saga is a sequence of local transactions, each within a single service, that together implement a distributed business process. When a step fails, compensating transactions undo the effects of completed steps. Use Sagas when you need to coordinate operations across multiple services and 2PC is not an option (which is almost always in microservices). The classic use case is "place order" — creating an order, reserving payment, and reserving inventory across three separate services.

---

**Q: What is the difference between choreography and orchestration-based sagas?**

In **choreography**, services react to events published by other services. There's no central coordinator — each service knows what to do when it sees a specific event. Simple and loosely coupled, but the overall flow is implicit and distributed across multiple services.

In **orchestration**, a central Saga Orchestrator explicitly tells each service what to do in sequence and tracks overall saga state. The flow is explicit and visible in one place, easier to monitor, but the orchestrator is a central component that must be reliable. For complex sagas with 5+ steps or where you need visibility into saga state, orchestration is usually better.

---

**Q: What are compensating transactions?**

A compensating transaction semantically reverses the business effect of a completed local transaction. When saga step N fails, compensating transactions for steps N-1, N-2, etc. are executed to restore business consistency. Key properties: idempotent (calling twice is safe), should always succeed (or retry indefinitely), and semantically appropriate (not necessarily a perfect technical reverse — "cancel order" not "delete order").

---

**Q: What is CQRS and what problem does it solve?**

CQRS separates the model used for changing state (commands) from the model used for querying state (queries). The write model is optimized for domain consistency and business rules. The read model is optimized for query performance — denormalized, pre-joined, potentially in a different database (Elasticsearch for search, Redis for caching). It solves the problem where a single model must compromise between optimal write structure (normalized, ACID) and optimal read structure (denormalized, fast queries). At high scale, you can scale the read side independently (read replicas, caching) without touching the write side.

---

**Q: What is Event Sourcing? What are the trade-offs?**

Event Sourcing stores the sequence of events that caused state changes, rather than the current state. Current state is reconstructed by replaying events. 

**Pros:** Complete audit trail; time travel (reconstruct state at any point); new read models can be built by replaying history; events as integration points.

**Cons:** Complex querying (can't `SELECT * WHERE status = 'PENDING'` directly); storage growth; eventual consistency between write and read sides; schema evolution is hard (old events must still be deserializable); steep learning curve.

---

**Q: Why is Event Sourcing combined with CQRS so often?**

Event Sourcing makes reads difficult — the write side stores events, not current state. CQRS solves this by introducing a separate read model (projection) that consumes events and materializes current state in a query-friendly format. The event store is the source of truth; projections are derived. If a projection is corrupted or you need a new read model, replay all events from the event store. They're not required together, but they complement each other naturally.

---

**Q: How do you handle schema evolution in Event Sourcing?**

Events are immutable and must be deserializable forever. When the schema changes:

1. **Additive changes** (new optional field): add a default in the deserializer for old events
2. **Rename/restructure**: use "upcasting" — read the old schema version, transform it to the new version during deserialization
3. **Version the event type**: `order.created.v1` vs `order.created.v2`; register an upcaster from v1 to v2
4. **Never delete event types** — you may need to replay old events years later

The general rule: events must be append-only and backward-compatible. Treat them like a public API.

---

## 15. Resources

- [Chris Richardson — Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Microsoft — CQRS Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)
- [Martin Fowler — Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)
- [Martin Fowler — CQRS](https://martinfowler.com/bliki/CQRS.html)
- [Vaughn Vernon — Implementing Domain-Driven Design](https://www.informit.com/store/implementing-domain-driven-design-9780321834577)
- [Greg Young — CQRS and Event Sourcing (original talk)](https://www.youtube.com/watch?v=JHGkaShoyNs)
- [EventStoreDB Documentation](https://developers.eventstore.com/)
- [Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)

---

**Next:** [Part 16.1: Deployment & Docker](../part-16/16-deployment-docker-cicd.md)
