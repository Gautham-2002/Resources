# Part 9.2: Event-Driven Architecture Patterns

## What You'll Learn
- Events vs commands vs queries — semantic and architectural difference
- Event schema design — what belongs in an event, envelope pattern, versioning
- The dual-write problem and why it breaks distributed systems
- Transactional Outbox Pattern — the definitive solution to dual-write
- Saga Pattern — distributed transactions without 2PC
- Choreography vs orchestration — when to use each
- Compensating transactions — how rollback works in distributed systems
- Change Data Capture (CDC) with Debezium
- Event Sourcing — storing events instead of state
- CQRS combined with Event Sourcing
- Full code: Go, Node.js, Python — outbox publisher, saga participant, event formats

## Table of Contents
1. [Event-Driven Architecture Overview](#event-driven-architecture-overview)
2. [Events vs Commands vs Queries](#events-vs-commands-vs-queries)
3. [Event Types](#event-types)
4. [Event Schema Design](#event-schema-design)
5. [Event Versioning](#event-versioning)
6. [The Dual-Write Problem](#the-dual-write-problem)
7. [Transactional Outbox Pattern](#transactional-outbox-pattern)
8. [Saga Pattern](#saga-pattern)
9. [Choreography-Based Saga](#choreography-based-saga)
10. [Orchestration-Based Saga](#orchestration-based-saga)
11. [Compensating Transactions](#compensating-transactions)
12. [Change Data Capture (CDC)](#change-data-capture-cdc)
13. [Event Sourcing](#event-sourcing)
14. [CQRS + Event Sourcing](#cqrs--event-sourcing)
15. [Implementation Examples](#implementation-examples)
16. [Common Patterns & Best Practices](#common-patterns--best-practices)
17. [Common Pitfalls](#common-pitfalls)
18. [Interview Questions](#interview-questions)
19. [Resources](#resources)

---

## Event-Driven Architecture Overview

In an event-driven architecture (EDA), services communicate by producing and consuming **events**. Events are immutable records of things that happened. Services don't call each other directly — they react to events.

```
Traditional (synchronous):
  OrderService ──HTTP──> PaymentService ──HTTP──> InventoryService
  Tight coupling. If any service is slow/down, the whole flow is blocked.

Event-Driven (asynchronous):
  OrderService publishes "order.created"
  PaymentService subscribes → processes payment → publishes "payment.processed"
  InventoryService subscribes to "order.created" → reserves stock
  EmailService subscribes to "payment.processed" → sends receipt

Each service is autonomous. Failure in one doesn't cascade synchronously.
New services can join by subscribing to existing topics.
```

EDA enables:
- **Loose coupling**: Services don't know about each other
- **Scalability**: Services scale independently
- **Resilience**: Failure in one service doesn't immediately affect others
- **Auditability**: The stream of events is a historical record
- **Replayability**: New services can catch up by consuming historical events

---

## Events vs Commands vs Queries

These three messaging patterns look similar but have fundamentally different semantics.

### Events

An event records something that **already happened**. It's a fact. Past tense.

```
Examples:
  order.created       — an order was placed
  payment.failed      — a payment attempt failed
  user.email.verified — a user verified their email address
  inventory.depleted  — a product ran out of stock
```

Properties of events:
- **Immutable**: happened in the past, cannot be changed
- **Broadcast**: any interested party can consume
- **No expected action**: the publisher doesn't know or care who reacts
- **No response**: fire and forget
- **Named in past tense**: `OrderCreated`, `PaymentFailed`

### Commands

A command is a **request for something to happen**. It's an instruction. Future tense.

```
Examples:
  ProcessPayment       — please process this payment
  SendEmailNotification — please send this email
  ReserveInventory      — please reserve these items
```

Properties of commands:
- **Mutable intent**: may be rejected or fail
- **Directed**: sent to a specific service
- **Has a handler**: exactly one service processes it
- **May return a response**: success/failure
- **Named in imperative**: `ProcessPayment`, `SendEmail`

### Queries

A query **requests information** without side effects. Read-only.

```
Examples:
  GetOrderStatus     — what is the status of order 123?
  GetInventoryCount  — how many units of product X are available?
```

In event-driven systems, queries are typically synchronous HTTP/gRPC calls, not messages. Mixing query responses into event streams creates complexity without benefit.

### Why the Distinction Matters

```
Bad: using events as implicit commands
  OrderService publishes "order.created"
  PaymentService interprets it as "process payment now"
  
  Problem: What if payment fails? OrderService has already published an event
  saying the order was created. The event is a lie — the order isn't really complete.

Good: explicit event flow
  OrderService: validates order → saves to DB in "pending" state
  OrderService publishes "order.pending" (true fact)
  PaymentService receives "order.pending" → processes payment → publishes "payment.processed" OR "payment.failed"
  OrderService subscribes to payment results → updates order status
```

---

## Event Types

### Domain Events

Represent significant things that happened within a bounded context. Internal to a service/domain.

```json
{
  "event_id": "evt-a1b2c3",
  "event_type": "OrderItemAdded",
  "aggregate_id": "order-456",
  "aggregate_type": "Order",
  "occurred_at": "2024-01-15T10:30:00Z",
  "data": {
    "product_id": "prod-789",
    "quantity": 2,
    "unit_price": 29.99
  }
}
```

Domain events are the internal language of a service. They may not be published externally.

### Integration Events

Published to shared message buses for other services to consume. These cross bounded context boundaries.

```json
{
  "event_id": "evt-x9y8z7",
  "event_type": "order.created",
  "source_service": "order-service",
  "schema_version": "1.2",
  "published_at": "2024-01-15T10:30:05Z",
  "correlation_id": "req-abc123",
  "data": {
    "order_id": "order-456",
    "user_id": "user-101",
    "total_amount": 59.98,
    "items": [
      {"product_id": "prod-789", "quantity": 2, "unit_price": 29.99}
    ]
  }
}
```

Integration events should be carefully versioned — many services depend on them.

### CDC Events (Change Data Capture)

Generated automatically from database changes. Represent database row-level changes.

```json
{
  "source": {
    "db": "ecommerce",
    "table": "orders",
    "ts_ms": 1705312205000,
    "op": "c"
  },
  "before": null,
  "after": {
    "id": "order-456",
    "user_id": "user-101",
    "status": "created",
    "total_amount": 59.98,
    "created_at": "2024-01-15T10:30:05Z"
  }
}
```

CDC events are raw data changes. They're useful for syncing read models, caches, search indexes, and analytics.

---

## Event Schema Design

### The Envelope Pattern

Every event should have a consistent outer structure (envelope) regardless of the event type. The envelope carries routing/metadata, the data carries the business payload.

```json
{
  "envelope": {
    "event_id": "uuid-v4",
    "event_type": "order.created",
    "schema_version": "2.0",
    "source_service": "order-service",
    "published_at": "2024-01-15T10:30:05.123Z",
    "correlation_id": "tracing-id-from-request",
    "causation_id": "event-that-triggered-this",
    "aggregate_id": "order-456",
    "aggregate_type": "Order"
  },
  "data": {
    "order_id": "order-456",
    "user_id": "user-101",
    "total_amount": 59.98
  }
}
```

**What to include in every event:**
- `event_id`: UUID for deduplication (idempotency key)
- `event_type`: string identifier for routing/handling
- `schema_version`: for backward compatibility
- `published_at`: when the event was published (not when it happened)
- `occurred_at`: when the business action happened (may differ from published_at)
- `correlation_id`: trace ID for distributed tracing (follow through entire flow)
- `causation_id`: ID of event/request that caused this event (causal chain)

**What NOT to include:**
- Sensitive PII that doesn't need to flow through the bus
- Large binary data (put in object storage, include reference URL)
- Implementation details of the source service

### Event Size

Keep events small — include identifiers, not full objects. Consumers can fetch details if needed. Exceptions: when consumers would need to call back to the source service to get data, denormalize key fields into the event to avoid chatty communication.

---

## Event Versioning

Events, once published, are consumed by multiple services. You can't change the schema without coordinating all consumers. Use versioning.

### Backward Compatible Changes (safe — consumers don't need to update)

- Adding new optional fields with defaults
- Adding new event types

```json
// v1
{"order_id": "123", "amount": 59.98}

// v2 — backward compatible (new optional field)
{"order_id": "123", "amount": 59.98, "currency": "USD"}

// v1 consumers ignore "currency" field → still works
```

### Breaking Changes (requires coordination)

- Removing fields
- Renaming fields
- Changing field types

**Strategy 1: Schema version field**
Include `schema_version` in the envelope. Consumers check version and handle accordingly.

**Strategy 2: Parallel publishing**
During migration, publish both v1 and v2 events. Migrate consumers to v2, then stop publishing v1.

**Strategy 3: Schema Registry (Avro/Protobuf)**
Confluent Schema Registry enforces compatibility rules (backward, forward, full). Producers can't publish a breaking schema change.

---

## The Dual-Write Problem

This is one of the most critical patterns to understand in distributed systems.

### The Problem

Consider an `OrderService` that must:
1. Write the new order to its PostgreSQL database
2. Publish an `order.created` event to Kafka

These are two separate systems. There is no atomic transaction that spans both.

```
Scenario A: DB write succeeds, Kafka publish fails
  - Order is in the database
  - No event was published
  - PaymentService never charges the customer
  - Order sits forever in "created" state, customer never gets confirmation
  RESULT: inconsistency — order exists but downstream processing never happens

Scenario B: Kafka publish succeeds, DB write fails (or rolls back)
  - Event was published
  - Order is NOT in the database
  - PaymentService tries to charge for an order that doesn't exist
  - InventoryService reserves stock for a non-existent order
  RESULT: ghost transactions — downstream side effects from a non-existent order
```

### Why You Can't Just Order the Operations

```
Publish first, then DB write:
  publish("order.created") → DB crash before write → ghost event ✗

DB write first, then publish:
  DB write → process crash before publish → orphaned DB record ✗

DB write + publish in a try/catch:
  publish() might fail after DB.commit() → missed event ✗
  Two-phase attempt is still not atomic
```

This is the fundamental problem. The solution is the **Transactional Outbox Pattern**.

---

## Transactional Outbox Pattern

### Core Idea

Write the event to the **same database transaction** as the business data. A separate process reads the outbox and publishes to Kafka. Since both the business write and the outbox write happen in a single transaction, they're atomic — either both succeed or both fail.

```
Traditional (broken):
  app ──transaction──► DB (order record)
  app ──publish──────► Kafka (order.created event)
  (two operations, not atomic)

Outbox pattern:
  app ──transaction──► DB (order record + outbox record)  ← single atomic TX
  publisher ──────────► reads outbox ──► publishes to Kafka ──► marks as published
```

### Outbox Table Schema

```sql
CREATE TABLE outbox_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(100) NOT NULL,  -- 'Order', 'Payment'
    aggregate_id  VARCHAR(100) NOT NULL,   -- '456'
    event_type    VARCHAR(100) NOT NULL,   -- 'order.created'
    schema_version VARCHAR(10) NOT NULL DEFAULT '1.0',
    payload       JSONB NOT NULL,          -- the full event
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at  TIMESTAMPTZ,             -- null = not yet published
    published     BOOLEAN NOT NULL DEFAULT false,
    attempts      INT NOT NULL DEFAULT 0,
    last_error    TEXT
);

CREATE INDEX outbox_unpublished ON outbox_events (created_at)
WHERE published = false;
```

### The Publisher Process

A separate process (or background goroutine) polls the outbox table:

```
Publisher loop:
  1. SELECT * FROM outbox_events WHERE published = false ORDER BY created_at LIMIT 100
  2. For each row:
     a. Publish to Kafka
     b. On success: UPDATE outbox_events SET published=true, published_at=now() WHERE id=?
     c. On failure: UPDATE outbox_events SET attempts=attempts+1, last_error=? WHERE id=?
  3. Sleep 100ms, repeat
```

This guarantees **at-least-once publishing**: if Kafka is down, the outbox accumulates entries. When Kafka recovers, the publisher drains the backlog. Messages may be published more than once (publisher crashes after publishing but before marking as published), so consumers must be idempotent.

### Polling Outbox vs CDC-Based Outbox

**Polling outbox:**
- Application polls the DB table on a timer
- Simple to implement, no extra infrastructure
- Adds DB load from polling queries
- Latency: polling interval (typically 100ms-1s)

**CDC-based outbox (Debezium):**
- Debezium watches the Postgres WAL (Write-Ahead Log)
- Every insert to the outbox table immediately generates a Kafka event
- Near-real-time latency (~milliseconds)
- No polling load on the database
- More infrastructure: Debezium + Kafka Connect cluster
- Recommended for high-throughput or latency-sensitive scenarios

```
CDC Outbox Architecture:

  App ──TX──► [orders table] + [outbox_events table]
                                      │
                               PostgreSQL WAL
                                      │
                                  Debezium
                            (Kafka Connect source)
                                      │
                              Kafka: outbox.events
                                      │
                           ┌──────────┴──────────┐
                     order.created          payment.created
                     (topic routing          (topic routing
                      via SMT)                via SMT)
```

Debezium's **Single Message Transform (SMT)** routes outbox events to the correct Kafka topic based on the `aggregate_type` field in the outbox row.

---

## Saga Pattern

### What is a Saga?

A **saga** is a sequence of local transactions, each published as an event or message, where each step either completes successfully or triggers a **compensating transaction** to undo previous steps.

Sagas replace distributed two-phase commit (2PC). 2PC requires all participants to hold locks during the coordination phase — catastrophic for performance at scale. Sagas achieve eventual consistency without distributed locks.

```
Without Saga (2PC — don't do this at scale):
  Coordinator → Phase 1: PREPARE (all participants lock resources)
  Coordinator → Phase 2: COMMIT (all commit) or ROLLBACK (all roll back)
  If coordinator crashes between phases → participants hold locks forever → deadlock

With Saga:
  Each service does its local transaction independently
  Failure triggers compensating transactions (undo)
  No locks held across service boundaries
  Eventually consistent — not immediately consistent
```

---

## Choreography-Based Saga

Each service listens for events and decides what to do next. No central coordinator. Services react to each other.

### Order Placement Example

```
Happy path:
  1. OrderService creates order → publishes "order.created"
  2. PaymentService receives "order.created" → charges card → publishes "payment.processed"
  3. InventoryService receives "payment.processed" → reserves stock → publishes "inventory.reserved"
  4. ShippingService receives "inventory.reserved" → schedules shipment → publishes "shipment.scheduled"
  5. OrderService receives "shipment.scheduled" → marks order as confirmed → publishes "order.confirmed"

Failure path (payment fails):
  1. OrderService creates order → publishes "order.created"
  2. PaymentService receives "order.created" → card declined → publishes "payment.failed"
  3. OrderService receives "payment.failed" → marks order as cancelled → publishes "order.cancelled"
  4. InventoryService receives "order.cancelled" → no action needed (never reserved stock)

Failure path (inventory fails after payment):
  1. OrderService creates order → publishes "order.created"
  2. PaymentService → charges card → publishes "payment.processed"
  3. InventoryService receives "payment.processed" → out of stock → publishes "inventory.reservation.failed"
  4. PaymentService receives "inventory.reservation.failed" → COMPENSATE → refunds charge → publishes "payment.refunded"
  5. OrderService receives "inventory.reservation.failed" → cancels order
```

```
Choreography Flow Diagram:

OrderService  PaymentService  InventoryService  ShippingService
     │               │               │                │
     │──order.created──►             │                │
     │               │──payment      │                │
     │               │  .processed──►│                │
     │               │               │──inventory     │
     │               │               │  .reserved────►│
     │               │               │                │──shipment
     │               │               │                │  .scheduled
     │◄──────────────────────────────────────────────── (OrderService
     │                                                    updates status)
```

### When to Use Choreography

- **Simple flows**: 2-3 steps, few services
- **Loose coupling is paramount**: services truly shouldn't know each other
- **Independent teams**: teams don't want a shared orchestrator dependency
- **Well-defined event contracts**: everyone agrees on event types and schemas

### Downsides of Choreography

- **Hard to debug**: no central view of the saga's progress. Which step are we on? Hard to answer without distributed tracing.
- **Cyclic dependencies**: Service A reacts to B, B reacts to C, C might react to A — easy to create cycles
- **Difficult to change**: adding a new step requires modifying multiple services
- **State is implicit**: you can't easily ask "what is the current state of saga for order-456?"

---

## Orchestration-Based Saga

A central **orchestrator** tells each service what to do next and handles the saga state machine explicitly.

```
Orchestration Flow Diagram:

                    ┌─────────────────────────┐
                    │    OrderSagaOrchestrator │
                    │   (saga state machine)   │
                    └─────────┬───────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
  PaymentService       InventoryService    ShippingService
  (receives commands,   (receives commands,  (receives commands,
   publishes results)    publishes results)   publishes results)

Step 1: Orchestrator → PaymentService: "ProcessPayment(order-456, $59.98)"
Step 2: PaymentService → Orchestrator: "PaymentSucceeded(order-456)"
Step 3: Orchestrator → InventoryService: "ReserveInventory(order-456, items)"
Step 4: InventoryService → Orchestrator: "InventoryReserved(order-456)"
Step 5: Orchestrator → ShippingService: "ScheduleShipment(order-456)"
Step 6: ShippingService → Orchestrator: "ShipmentScheduled(order-456)"
Step 7: Orchestrator marks saga complete
```

### Orchestrator as a State Machine

```
Saga States:
  PENDING_PAYMENT → PAYMENT_SUCCEEDED → PENDING_INVENTORY →
  INVENTORY_RESERVED → PENDING_SHIPMENT → COMPLETED

  PENDING_PAYMENT → PAYMENT_FAILED → CANCELLED
  PENDING_INVENTORY → INVENTORY_FAILED → COMPENSATING_PAYMENT → CANCELLED
```

The orchestrator persists saga state to a database. If it crashes, it resumes from the last persisted state.

### When to Use Orchestration

- **Complex flows**: 4+ services, complex conditional logic
- **Visibility needed**: easy to query "where is order-456 in the saga?"
- **Centralized error handling**: one place to handle all failure cases
- **Audit/compliance**: need a complete record of what happened and when

### Downsides of Orchestration

- **Single point of failure**: if the orchestrator service goes down, no sagas progress (mitigated by multiple instances + state in DB)
- **Coupling**: all services must integrate with the orchestrator
- **Orchestrator becomes a bottleneck**: high throughput orchestrators need careful scaling

---

## Compensating Transactions

A compensating transaction **reverses the effect** of a previously committed local transaction. Unlike database rollbacks (which undo uncommantted changes), compensating transactions are new operations that semantically undo a committed operation.

### Examples

| Forward Action | Compensating Action |
|---|---|
| Charge credit card | Refund credit card |
| Reserve inventory | Release inventory reservation |
| Create shipment | Cancel shipment |
| Send email | Cannot undo (best effort: send apology) |
| Update loyalty points | Reverse loyalty point update |
| Mark order as processing | Mark order as cancelled |

### Compensating Transaction Challenges

**1. Not all actions are compensable**
Sending an email, sending an SMS, or making an external API call may be impossible to reverse. Design your saga to place non-compensable steps last (if compensation is needed, those steps haven't happened yet).

**2. Compensation order matters**
Compensation must happen in reverse order of the original steps. If Step 3 depends on the result of Step 2, compensating Step 2 must happen before compensating Step 3 (though since we're going backwards, this usually means compensating Step 3, then Step 2, then Step 1).

**3. Compensation may also fail**
The compensation operation (refund) may fail too. You need retry logic and DLQ for compensation failures. In practice, these are often handled by human intervention workflows.

---

## Change Data Capture (CDC)

### What is CDC?

CDC captures every change (INSERT, UPDATE, DELETE) made to a database and streams those changes as events. Instead of polling the database for changes, CDC watches the database's internal change log (WAL in PostgreSQL, binlog in MySQL).

```
Without CDC (polling):
  Every 5 seconds: SELECT * FROM orders WHERE updated_at > last_poll_time
  Problems: delays, load on DB, might miss rapid updates, needs updated_at column

With CDC (Debezium):
  PostgreSQL WAL ──► Debezium ──► Kafka
  Every row change appears as an event within milliseconds
  No polling. No missed updates. No DB load from queries.
```

### Debezium Architecture

Debezium is a Kafka Connect source connector. It reads the database WAL and translates each change into a Kafka message.

```
┌────────────────────────────────────────────────────────┐
│                      PostgreSQL                         │
│                                                         │
│  orders table:                                          │
│  id=456, status='created' → UPDATE status='shipped'    │
│                    │                                    │
│                    ▼                                    │
│               WAL (Write-Ahead Log)                     │
│    [LSN:1234] UPDATE orders SET status='shipped'...    │
└───────────────────┬────────────────────────────────────┘
                    │
                 Debezium
           (reads WAL via logical replication)
                    │
                    ▼
         Kafka: dbserver1.public.orders
         {
           "before": {"id": "456", "status": "created"},
           "after":  {"id": "456", "status": "shipped"},
           "source": {"op": "u", "ts_ms": 1705312205000}
         }
```

### CDC Use Cases

**1. Cache invalidation**: When a DB row changes, invalidate or update the corresponding Redis key.

**2. Search index sync**: When products are updated in PostgreSQL, automatically update Elasticsearch.

**3. Audit log**: Every change to any row becomes an immutable audit entry.

**4. Event sourcing bootstrap**: Backfill historical data into a new event-sourced service.

**5. Cross-service data sync**: Replicate data from one service's DB to another service's read model without direct coupling.

**6. Outbox pattern (CDC variant)**: As described in the Transactional Outbox section — Debezium watches the outbox table and publishes to Kafka.

### Setting Up Debezium with PostgreSQL

PostgreSQL requires logical replication enabled (`wal_level=logical`). Debezium uses a replication slot to read the WAL.

```json
// Debezium connector config (POST to Kafka Connect REST API)
{
  "name": "orders-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "secret",
    "database.dbname": "ecommerce",
    "database.server.name": "dbserver1",
    "table.include.list": "public.orders,public.outbox_events",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_slot",
    "publication.name": "debezium_publication",
    "heartbeat.interval.ms": "1000",
    "transforms": "outbox",
    "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
    "transforms.outbox.table.expand.json.payload": "true"
  }
}
```

---

## Event Sourcing

### The Core Idea

Instead of storing the **current state** of an entity, event sourcing stores the **sequence of events** that led to the current state. The current state is derived by replaying events.

```
Traditional (state storage):
  orders table:
  id=456, status='shipped', amount=59.98, updated_at=...
  (only current state — history is gone)

Event Sourcing:
  order_events stream:
  [1] OrderCreated    {orderId: 456, userId: 101, amount: 59.98}
  [2] PaymentCharged  {orderId: 456, amount: 59.98, cardLast4: 1234}
  [3] InventoryPicked {orderId: 456, warehouseId: 7}
  [4] OrderShipped    {orderId: 456, trackingId: "UPS-123"}

  Current state = replay all events:
  status = "shipped" (from last event)
  amount = 59.98 (from OrderCreated)
  Full history preserved!
```

### Rebuilding State from Events

```go
// Pseudo-code for rebuilding Order state from events
type Order struct {
    ID     string
    Status string
    Amount float64
    Items  []Item
}

func RebuildOrder(events []Event) Order {
    order := Order{}
    for _, event := range events {
        switch event.Type {
        case "OrderCreated":
            order.ID = event.Data["order_id"]
            order.Amount = event.Data["amount"]
            order.Status = "created"
        case "PaymentCharged":
            order.Status = "paid"
        case "OrderShipped":
            order.Status = "shipped"
        case "OrderCancelled":
            order.Status = "cancelled"
        }
    }
    return order
}
```

### Snapshots

For entities with many events, replaying all events on every read is slow. Snapshots periodically capture the current state after N events. On rebuild, start from the latest snapshot, then replay only events after the snapshot.

```
Snapshot at event 1000:
  Snapshot: {id: 456, status: "paid", amount: 59.98, ...at event 1000}
  
  To rebuild current state:
  1. Load snapshot (at event 1000)
  2. Load events 1001 through current
  3. Replay events 1001+
  
  Much faster than replaying all 1000+ events every time.
```

### Trade-offs

| | State Storage | Event Sourcing |
|---|---|---|
| **Query simplicity** | Simple SQL queries | Complex — need projections |
| **Write simplicity** | Simple upsert | Append event, rebuild state |
| **History** | Gone on update | Full history preserved |
| **Audit** | Extra work | Built-in |
| **Debugging** | Hard to know what happened | Replay events to any point |
| **Storage** | Small (current state only) | Grows forever (append-only) |
| **Schema evolution** | Easier | Hard — event schemas are immutable |
| **Eventual consistency** | Immediate | Must manage projections |

Event sourcing is complex. Don't use it unless you have a genuine need for full event history, audit trails, or temporal queries (what was the state at time T?).

---

## CQRS + Event Sourcing

**CQRS** (Command Query Responsibility Segregation) separates the write model from the read model.

```
CQRS Architecture:

Write Side (Commands):
  HTTP POST /orders ──► OrderCommandHandler ──► validate ──► append events to event store

Event Store ──► publishes events ──► Projectors

Read Side (Queries):
  HTTP GET /orders/456 ──► OrderQueryHandler ──► reads from read model (projected DB)

Projectors listen to events and update optimized read models:
  order.created ──► projector ──► UPDATE orders_read_model SET status='created' WHERE id=456
  order.shipped ──► projector ──► UPDATE orders_read_model SET status='shipped' WHERE id=456
```

The write side (event store) is optimized for appends. The read side is optimized for queries — you can have multiple read models for different use cases (e.g., one for the customer-facing API, another for the analytics dashboard, another for the admin panel).

The downside: **eventual consistency**. After writing an event, the read model may lag by milliseconds. For most UIs this is acceptable (show a "processing" state). For some use cases (financial balance), you need stronger guarantees.

---

## Implementation Examples

### How It Works Internally (ASCII Diagram)

```
Complete Event-Driven Order Flow with Outbox:

  ┌──────────────────────────────────────────────────────────────┐
  │  OrderService                                                 │
  │                                                              │
  │  BEGIN TRANSACTION                                           │
  │  INSERT INTO orders (id, status, amount) VALUES (...)        │
  │  INSERT INTO outbox_events (event_type, payload) VALUES (...) │
  │  COMMIT                                 ← atomic!            │
  │                                                              │
  │  [background goroutine/thread]                               │
  │  SELECT * FROM outbox_events WHERE published=false           │
  │  → Publish to Kafka                                          │
  │  → UPDATE outbox SET published=true                          │
  └──────────────────────────────────────────────────────────────┘
              │
         Kafka: order.created
              │
    ┌─────────┴──────────┬──────────────────┐
    ▼                    ▼                  ▼
PaymentService    InventoryService    EmailService
(processes payment) (reserves stock) (sends confirmation)
    │
    ▼
payment.processed OR payment.failed
    │
OrderSagaOrchestrator (or choreography)
```

---

### Go + Chi Router

```go
package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

// =====================
// OUTBOX TABLE SCHEMA (run this once):
// CREATE TABLE outbox_events (
//   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
//   aggregate_type VARCHAR(100) NOT NULL,
//   aggregate_id VARCHAR(100) NOT NULL,
//   event_type VARCHAR(100) NOT NULL,
//   payload JSONB NOT NULL,
//   published BOOLEAN NOT NULL DEFAULT false,
//   created_at TIMESTAMPTZ NOT NULL DEFAULT now()
// );
// =====================

type OutboxEvent struct {
	ID            string          `json:"id"`
	AggregateType string          `json:"aggregate_type"`
	AggregateID   string          `json:"aggregate_id"`
	EventType     string          `json:"event_type"`
	Payload       json.RawMessage `json:"payload"`
	Published     bool            `json:"published"`
	CreatedAt     time.Time       `json:"created_at"`
}

type Order struct {
	ID     string
	UserID string
	Amount float64
	Status string
}

// CreateOrderWithOutbox creates an order and an outbox entry in a single transaction
func CreateOrderWithOutbox(ctx context.Context, db *sql.DB, userID string, amount float64) (string, error) {
	orderID := uuid.New().String()
	eventID := uuid.New().String()

	event := map[string]interface{}{
		"event_id":   eventID,
		"event_type": "order.created",
		"order_id":   orderID,
		"user_id":    userID,
		"amount":     amount,
		"created_at": time.Now().UTC().Format(time.RFC3339),
	}
	eventPayload, err := json.Marshal(event)
	if err != nil {
		return "", fmt.Errorf("failed to marshal event: %w", err)
	}

	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return "", fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback() // no-op if committed

	// Step 1: Insert the order
	_, err = tx.ExecContext(ctx,
		`INSERT INTO orders (id, user_id, amount, status, created_at)
		 VALUES ($1, $2, $3, 'created', now())`,
		orderID, userID, amount,
	)
	if err != nil {
		return "", fmt.Errorf("failed to insert order: %w", err)
	}

	// Step 2: Insert outbox event (same transaction — atomic!)
	_, err = tx.ExecContext(ctx,
		`INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type, payload)
		 VALUES ($1, $2, $3, $4)`,
		"Order", orderID, "order.created", eventPayload,
	)
	if err != nil {
		return "", fmt.Errorf("failed to insert outbox event: %w", err)
	}

	// Both writes committed atomically
	if err := tx.Commit(); err != nil {
		return "", fmt.Errorf("failed to commit transaction: %w", err)
	}

	log.Printf("Created order %s with outbox entry", orderID)
	return orderID, nil
}

// OutboxPublisher polls the outbox table and publishes events to Kafka
type OutboxPublisher struct {
	db       *sql.DB
	producer KafkaProducer // interface to your Kafka producer
}

type KafkaProducer interface {
	Publish(topic string, key string, value []byte) error
}

func (p *OutboxPublisher) Run(ctx context.Context) {
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			log.Println("OutboxPublisher: context cancelled, stopping")
			return
		case <-ticker.C:
			if err := p.publishPendingEvents(ctx); err != nil {
				log.Printf("OutboxPublisher: error publishing events: %v", err)
			}
		}
	}
}

func (p *OutboxPublisher) publishPendingEvents(ctx context.Context) error {
	// Select up to 100 unpublished events, ordered by creation time
	rows, err := p.db.QueryContext(ctx,
		`SELECT id, aggregate_type, aggregate_id, event_type, payload
		 FROM outbox_events
		 WHERE published = false
		 ORDER BY created_at
		 LIMIT 100
		 FOR UPDATE SKIP LOCKED`, // skip rows locked by other publisher instances
	)
	if err != nil {
		return err
	}
	defer rows.Close()

	var events []OutboxEvent
	for rows.Next() {
		var e OutboxEvent
		if err := rows.Scan(&e.ID, &e.AggregateType, &e.AggregateID, &e.EventType, &e.Payload); err != nil {
			return err
		}
		events = append(events, e)
	}

	for _, event := range events {
		topic := eventTypeToTopic(event.EventType)
		if err := p.producer.Publish(topic, event.AggregateID, event.Payload); err != nil {
			log.Printf("Failed to publish event %s: %v", event.ID, err)
			// Don't mark as published — retry on next poll
			continue
		}

		// Mark as published only after successful Kafka publish
		_, err := p.db.ExecContext(ctx,
			`UPDATE outbox_events SET published=true, published_at=now() WHERE id=$1`,
			event.ID,
		)
		if err != nil {
			log.Printf("Failed to mark event %s as published: %v", event.ID, err)
		}
	}
	return nil
}

func eventTypeToTopic(eventType string) string {
	topicMap := map[string]string{
		"order.created":      "order.created",
		"payment.processed":  "payment.processed",
		"payment.failed":     "payment.failed",
	}
	if topic, ok := topicMap[eventType]; ok {
		return topic
	}
	return "unknown-events"
}

// =====================
// SIMPLE CHOREOGRAPHY SAGA
// =====================

// SagaStep represents one step in a choreography saga
type SagaStep struct {
	ServiceName string
	EventType   string
	Handler     func(event map[string]interface{}) error
	OnFailure   func(event map[string]interface{}) error // compensating transaction
}

// Example: OrderSaga in choreography style
// Each service handles its own SagaStep

func handleOrderCreated(event map[string]interface{}) error {
	log.Printf("[PaymentService] Processing payment for order %v", event["order_id"])
	// Call payment gateway
	// On success: publish payment.processed
	// On failure: publish payment.failed
	return nil
}

func compensatePayment(event map[string]interface{}) error {
	log.Printf("[PaymentService] Refunding payment for order %v", event["order_id"])
	// Issue refund
	return nil
}
```

---

### Node.js + Express

```javascript
// outbox.js — Transactional Outbox with PostgreSQL
const { Pool } = require('pg');
const { v4: uuidv4 } = require('uuid');

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// =====================
// OUTBOX: WRITE (within business transaction)
// =====================

async function createOrderWithOutbox(userId, amount, items) {
  const client = await pool.connect();
  
  try {
    await client.query('BEGIN');
    
    const orderId = uuidv4();
    
    // Insert order
    await client.query(
      `INSERT INTO orders (id, user_id, amount, status, created_at)
       VALUES ($1, $2, $3, 'created', now())`,
      [orderId, userId, amount]
    );
    
    // Insert outbox event — SAME TRANSACTION
    const eventPayload = {
      event_id: uuidv4(),
      event_type: 'order.created',
      order_id: orderId,
      user_id: userId,
      amount,
      items,
      created_at: new Date().toISOString(),
    };
    
    await client.query(
      `INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type, payload)
       VALUES ($1, $2, $3, $4)`,
      ['Order', orderId, 'order.created', JSON.stringify(eventPayload)]
    );
    
    await client.query('COMMIT');
    console.log(`Created order ${orderId} with outbox entry`);
    return orderId;
    
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}

// =====================
// OUTBOX: PUBLISHER PROCESS
// =====================

class OutboxPublisher {
  constructor(kafkaProducer, pollIntervalMs = 100) {
    this.producer = kafkaProducer;
    this.pollIntervalMs = pollIntervalMs;
    this.running = false;
  }

  start() {
    this.running = true;
    this.poll();
  }

  stop() {
    this.running = false;
  }

  async poll() {
    while (this.running) {
      try {
        await this.publishPendingEvents();
      } catch (err) {
        console.error('OutboxPublisher error:', err);
      }
      await new Promise(resolve => setTimeout(resolve, this.pollIntervalMs));
    }
  }

  async publishPendingEvents() {
    const client = await pool.connect();
    try {
      // FOR UPDATE SKIP LOCKED: multiple publisher instances don't double-publish
      const { rows } = await client.query(`
        SELECT id, aggregate_type, aggregate_id, event_type, payload
        FROM outbox_events
        WHERE published = false
        ORDER BY created_at
        LIMIT 100
        FOR UPDATE SKIP LOCKED
      `);

      for (const row of rows) {
        const topic = this.eventTypeToTopic(row.event_type);
        
        try {
          await this.producer.send({
            topic,
            messages: [{
              key: row.aggregate_id,
              value: JSON.stringify(row.payload),
              headers: { 'event-type': row.event_type },
            }],
          });

          // Mark as published after successful send
          await client.query(
            `UPDATE outbox_events SET published = true, published_at = now() WHERE id = $1`,
            [row.id]
          );
        } catch (err) {
          console.error(`Failed to publish event ${row.id}:`, err);
          // Leave published=false, will retry on next poll
        }
      }
    } finally {
      client.release();
    }
  }

  eventTypeToTopic(eventType) {
    return eventType; // or use a mapping
  }
}

// =====================
// CHOREOGRAPHY SAGA PARTICIPANT
// =====================

// PaymentService: listens to order.created, publishes payment.processed or payment.failed
async function handleOrderCreated(event) {
  const { order_id, amount, user_id } = event;
  
  let paymentSucceeded = false;
  
  try {
    // Process payment (call payment gateway)
    const result = await chargeCard(user_id, amount);
    paymentSucceeded = true;
    
    // Save payment record + outbox event in single transaction
    const paymentEvent = {
      event_id: uuidv4(),
      event_type: 'payment.processed',
      order_id,
      payment_id: result.paymentId,
      amount,
      processed_at: new Date().toISOString(),
    };
    
    await savePaymentWithOutbox(paymentEvent);
    
  } catch (err) {
    console.error(`Payment failed for order ${order_id}:`, err);
    
    // Publish failure event
    const failureEvent = {
      event_id: uuidv4(),
      event_type: 'payment.failed',
      order_id,
      error_code: err.code || 'PAYMENT_DECLINED',
      error_message: err.message,
      failed_at: new Date().toISOString(),
    };
    
    await saveFailureWithOutbox(failureEvent);
  }
}

// Stubs for example clarity
async function chargeCard(userId, amount) { return { paymentId: uuidv4() }; }
async function savePaymentWithOutbox(event) { /* similar to createOrderWithOutbox */ }
async function saveFailureWithOutbox(event) { /* similar to createOrderWithOutbox */ }

module.exports = { createOrderWithOutbox, OutboxPublisher, handleOrderCreated };
```

---

### Python + FastAPI

```python
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
import asyncpg
from fastapi import FastAPI

app = FastAPI()

# =====================
# OUTBOX: WRITE (within business transaction)
# =====================

async def create_order_with_outbox(
    conn: asyncpg.Connection,
    user_id: str,
    amount: float,
    items: list,
) -> str:
    """Create an order and outbox event atomically."""
    order_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())

    event_payload = {
        "event_id": event_id,
        "event_type": "order.created",
        "order_id": order_id,
        "user_id": user_id,
        "amount": amount,
        "items": items,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    async with conn.transaction():
        # Insert order
        await conn.execute(
            """
            INSERT INTO orders (id, user_id, amount, status, created_at)
            VALUES ($1, $2, $3, 'created', now())
            """,
            order_id, user_id, amount,
        )

        # Insert outbox event — SAME TRANSACTION (atomic!)
        await conn.execute(
            """
            INSERT INTO outbox_events
                (aggregate_type, aggregate_id, event_type, payload)
            VALUES ($1, $2, $3, $4)
            """,
            "Order", order_id, "order.created", json.dumps(event_payload),
        )

    return order_id


# =====================
# OUTBOX: PUBLISHER
# =====================

class OutboxPublisher:
    def __init__(self, db_pool: asyncpg.Pool, kafka_producer, poll_interval: float = 0.1):
        self.db_pool = db_pool
        self.producer = kafka_producer
        self.poll_interval = poll_interval
        self.running = False

    async def start(self):
        self.running = True
        await self._run()

    async def stop(self):
        self.running = False

    async def _run(self):
        while self.running:
            try:
                await self._publish_pending_events()
            except Exception as e:
                print(f"OutboxPublisher error: {e}")
            await asyncio.sleep(self.poll_interval)

    async def _publish_pending_events(self):
        async with self.db_pool.acquire() as conn:
            # SKIP LOCKED: safe for multiple publisher instances
            rows = await conn.fetch(
                """
                SELECT id, aggregate_type, aggregate_id, event_type, payload
                FROM outbox_events
                WHERE published = false
                ORDER BY created_at
                LIMIT 100
                FOR UPDATE SKIP LOCKED
                """
            )

            for row in rows:
                topic = row["event_type"]
                key = row["aggregate_id"]
                payload = row["payload"]

                try:
                    await self.producer.send_and_wait(
                        topic=topic,
                        key=key.encode(),
                        value=payload.encode() if isinstance(payload, str) else json.dumps(payload).encode(),
                    )

                    # Mark as published only after successful Kafka write
                    await conn.execute(
                        "UPDATE outbox_events SET published=true, published_at=now() WHERE id=$1",
                        row["id"],
                    )
                except Exception as e:
                    print(f"Failed to publish outbox event {row['id']}: {e}")
                    # Don't mark published — retry on next poll


# =====================
# SAGA EVENT MESSAGE FORMAT
# =====================

def make_event(
    event_type: str,
    aggregate_id: str,
    aggregate_type: str,
    data: dict,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
) -> dict:
    """Standard event envelope used across all saga participants."""
    return {
        "envelope": {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "schema_version": "1.0",
            "source_service": "order-service",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "aggregate_id": aggregate_id,
            "aggregate_type": aggregate_type,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "causation_id": causation_id,
        },
        "data": data,
    }


# Usage example
order_created_event = make_event(
    event_type="order.created",
    aggregate_id="order-456",
    aggregate_type="Order",
    data={
        "order_id": "order-456",
        "user_id": "user-101",
        "amount": 59.98,
        "items": [{"product_id": "prod-789", "quantity": 2}],
    },
    correlation_id="req-trace-abc123",
)


# =====================
# CHOREOGRAPHY SAGA PARTICIPANT (Python/FastAPI)
# =====================

async def handle_order_created(event: dict, db_pool: asyncpg.Pool, producer):
    """PaymentService reaction to order.created event."""
    envelope = event["envelope"]
    data = event["data"]
    order_id = data["order_id"]

    try:
        # Attempt payment
        payment_id = await charge_card(data["user_id"], data["amount"])

        # Build success event and save to outbox (same transaction as payment record)
        async with db_pool.acquire() as conn:
            payment_event = make_event(
                event_type="payment.processed",
                aggregate_id=order_id,
                aggregate_type="Order",
                data={
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "amount": data["amount"],
                },
                correlation_id=envelope.get("correlation_id"),
                causation_id=envelope["event_id"],
            )

            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO payments (id, order_id, amount, status) VALUES ($1, $2, $3, 'charged')",
                    payment_id, order_id, data["amount"],
                )
                await conn.execute(
                    "INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type, payload) VALUES ($1, $2, $3, $4)",
                    "Order", order_id, "payment.processed", json.dumps(payment_event),
                )

    except Exception as e:
        print(f"Payment failed for order {order_id}: {e}")
        # Save failure event to outbox
        async with db_pool.acquire() as conn:
            failure_event = make_event(
                event_type="payment.failed",
                aggregate_id=order_id,
                aggregate_type="Order",
                data={"order_id": order_id, "error": str(e)},
                correlation_id=envelope.get("correlation_id"),
                causation_id=envelope["event_id"],
            )
            await conn.execute(
                "INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type, payload) VALUES ($1, $2, $3, $4)",
                "Order", order_id, "payment.failed", json.dumps(failure_event),
            )


async def charge_card(user_id: str, amount: float) -> str:
    """Stub: charge the user's card, return payment_id."""
    return str(uuid.uuid4())
```

---

## Common Patterns & Best Practices

### Pattern 1: Correlation ID Threading

Every event should carry a `correlation_id` that starts at the origin request and propagates through every downstream event. This enables distributed tracing — you can trace an entire saga from start to finish by filtering on one correlation ID.

```
HTTP Request arrives → correlation_id = new UUID
order.created event → carries correlation_id
payment.processed event → same correlation_id
inventory.reserved event → same correlation_id

Searching logs for correlation_id shows the complete flow.
```

### Pattern 2: Idempotency Keys in Events

Every event carries a unique `event_id` (UUID). Each consumer uses this to deduplicate. Without event IDs, at-least-once delivery causes duplicate processing.

### Pattern 3: Make Compensating Transactions Explicit

Document compensating transactions for every step in a saga. Store compensation parameters in the saga state (orchestrator) or in the original event (choreography). Compensation that needs data from the original step must receive that data in the failure event.

### Pattern 4: Timeout Handling

Sagas need timeout logic. If `payment.processed` isn't received within 30 seconds, assume payment failed and trigger compensation. Orchestrators handle this naturally. Choreography-based sagas need a separate timeout/monitoring service.

### Pattern 5: Idempotent Saga Steps

Saga steps must be idempotent — they may be retried. Charging a card twice is catastrophic. Use idempotency keys with your payment provider and check if the step has already been executed before proceeding.

---

## Common Pitfalls

**1. Dual write without the outbox pattern**
Writing to DB and publishing to Kafka without a transaction is a race condition. Use the outbox pattern. Always.

**2. Choreography for complex flows**
Choreography with 5+ services becomes a debugging nightmare. Hard to trace, hard to change. Switch to orchestration beyond 3-4 services.

**3. No compensating transactions**
If any step in a saga can fail, you need compensating transactions for all previous steps. Designing compensation before implementation (not after) is essential.

**4. Ignoring event ordering in CDC**
CDC events for the same row may arrive out of order in different Kafka partitions if the partitioner is wrong. Ensure CDC events for the same aggregate ID go to the same partition.

**5. Storing too much in events**
Including entire objects in events creates coupling between schemas. Include identifiers and key data. Consumers fetch additional details if needed.

**6. Not versioning events**
The first time you need to add a breaking field to an event and you haven't versioned it, you'll have a very bad day. Version from day one.

**7. Forgetting the outbox publisher is a single point of failure**
Run multiple outbox publisher instances with `FOR UPDATE SKIP LOCKED` or use Debezium (which is fault-tolerant and distributed).

---

## Interview Questions

**Q: What is the dual-write problem and how does the Transactional Outbox Pattern solve it?**

A: The dual-write problem: writing to a database and publishing to a message queue are two separate operations — no atomic transaction spans both. If the service crashes between them, one operation succeeds and the other fails, causing inconsistency. The Outbox Pattern solves this by writing the event to an `outbox_events` table **in the same database transaction** as the business data. A separate publisher process reads unpublished events and publishes them to Kafka. Both the business write and outbox write commit atomically. The publisher may re-publish on crash (at-least-once), so consumers must be idempotent.

**Q: What is the difference between choreography and orchestration sagas?**

A: Choreography: services react autonomously to each other's events. No central coordinator. Loose coupling but difficult to trace and debug. Best for simple flows (2-3 services). Orchestration: a central orchestrator sends commands to services and tracks the saga state machine. Easy to trace (central state), easy to add steps, but adds coupling to the orchestrator. Best for complex flows (4+ services) or when visibility into saga progress is needed.

**Q: What is a compensating transaction? Give an example.**

A: A compensating transaction semantically reverses a previously committed local transaction. Unlike a database rollback (which undoes uncommitted changes), compensation is a new operation applied to already-committed state. Example: if Step 2 (charge card) succeeded and Step 3 (reserve inventory) fails, the compensating transaction for Step 2 is "issue refund." Compensation must execute in reverse order. Not all actions are compensable — sending an email cannot be unsent (design non-compensable steps last in the saga).

**Q: What is CDC and when would you use Debezium?**

A: CDC (Change Data Capture) captures database changes (INSERT/UPDATE/DELETE) as events by reading the database's write-ahead log, rather than polling tables. Debezium is an open-source Kafka Connect connector that reads PostgreSQL WAL or MySQL binlog and publishes change events to Kafka. Use it for: cache invalidation, syncing search indexes, cross-service data replication, event-sourcing bootstrap, or the CDC-based variant of the Transactional Outbox Pattern. Advantages over polling: near-real-time, no missed updates, no extra DB load from queries.

**Q: What are the trade-offs of Event Sourcing?**

A: Event sourcing stores events instead of current state. Benefits: complete audit trail, full history, ability to replay and debug, temporal queries (state at time T), natural fit for CQRS. Trade-offs: complex query patterns (need projections/read models), storage grows unboundedly (append-only), schema evolution is hard (old events must always be valid), eventual consistency for read models, steep learning curve. Don't use event sourcing unless you have a genuine requirement for full history — it adds significant complexity.

**Q: How do you ensure exactly-once processing in a choreography saga?**

A: Each saga participant must be idempotent. Every event carries a unique `event_id`. Before processing, check if this event has already been handled (using a processed_events table or Redis dedup). All saga steps must be idempotent operations (upserts, SET operations, not increments). The Transactional Outbox ensures at-least-once publishing. At-least-once publishing + idempotent consumers = effectively exactly-once semantics from a business logic perspective, without the complexity of Kafka's transactional exactly-once API.

---

## Resources

- [Microservices Patterns — Chris Richardson (Saga, Outbox, CQRS)](https://microservices.io/patterns/)
- [Debezium Documentation](https://debezium.io/documentation/)
- [Designing Event-Driven Systems — Ben Stopford (Confluent)](https://www.confluent.io/designing-event-driven-systems/)
- [Event Sourcing Pattern — Microsoft Architecture Patterns](https://docs.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- [Transactional Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)

---

**Next:** [Part 10.1: Go Concurrency — Goroutines, Channels & Context](../part-10/10-concurrency-go-goroutines.md)
