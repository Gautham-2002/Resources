# Part 9.1: Message Queues & Kafka Internals

## What You'll Learn
- Why message queues exist and what problems they solve
- Kafka's architecture as a distributed commit log — not a traditional queue
- Topics, partitions, producers, consumers, consumer groups, offsets
- Delivery semantics: at-most-once, at-least-once, exactly-once
- Producer ack modes, compression, batching
- Consumer group rebalancing — what it is and what goes wrong
- Replication, ISR, KRaft (Zookeeper-free Kafka 3.x)
- Log compaction vs log retention
- RabbitMQ vs Kafka vs SQS — when to use each
- Dead Letter Queues — poison messages and failure handling
- Full code: Go (sarama), Node.js (kafkajs), Python (aiokafka/confluent-kafka)

## Table of Contents
1. [Why Message Queues?](#why-message-queues)
2. [Kafka as a Distributed Commit Log](#kafka-as-a-distributed-commit-log)
3. [Topics and Partitions](#topics-and-partitions)
4. [Producers — Batching, Acks, Compression](#producers)
5. [Consumers and Consumer Groups](#consumers-and-consumer-groups)
6. [Consumer Offsets](#consumer-offsets)
7. [Brokers, Replication, and ISR](#brokers-replication-and-isr)
8. [KRaft — Kafka Without Zookeeper](#kraft)
9. [Log Compaction vs Log Retention](#log-compaction-vs-log-retention)
10. [Consumer Group Rebalancing](#consumer-group-rebalancing)
11. [Kafka Connect and Kafka Streams](#kafka-connect-and-kafka-streams)
12. [Delivery Semantics](#delivery-semantics)
13. [Idempotent Consumers](#idempotent-consumers)
14. [RabbitMQ vs Kafka vs SQS](#rabbitmq-vs-kafka-vs-sqs)
15. [Dead Letter Queues](#dead-letter-queues)
16. [Implementation Examples](#implementation-examples)
17. [Common Patterns & Best Practices](#common-patterns--best-practices)
18. [Common Pitfalls](#common-pitfalls)
19. [Interview Questions](#interview-questions)
20. [Resources](#resources)

---

## Why Message Queues?

Before message queues, services called each other directly — synchronous HTTP or RPC. This creates tight coupling: if the downstream service is slow, the caller is slow. If the downstream service crashes, the caller fails. Message queues break that coupling.

### Decoupling Producers and Consumers

The producer doesn't know or care which service consumes its messages. It publishes to a topic/queue and moves on. New consumers can be added without touching the producer. This is the foundation of the microservices event bus.

```
Without MQ (tight coupling):
  Order Service ──HTTP──> Email Service
                       ──HTTP──> Inventory Service
                       ──HTTP──> Analytics Service
  If any one fails, order placement fails.

With MQ (loose coupling):
  Order Service ──publish──> [order.created topic]
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Email Service  Inventory Service  Analytics
              (consumes)      (consumes)         (consumes)
  Order Service doesn't wait. Each consumer is independent.
```

### Async Processing

Don't make users wait for work that can happen in the background. When a user places an order:
- **Immediate response needed**: deduct inventory, create order record
- **Can be async**: send confirmation email, generate invoice PDF, update analytics dashboard, trigger recommendation recompute

The user gets a response in ~50ms. Background workers process the event over the next seconds/minutes.

### Load Leveling

Traffic spikes don't propagate to backend services. During a flash sale, the Order Service might receive 10,000 requests/second. The downstream Inventory Service might only handle 500/second. A queue absorbs the burst — the queue depth grows during the spike, then drains as the consumer catches up.

```
Traffic Spike Scenario:
Time:    00:00  00:01  00:02  00:03  00:04
RPS in:  1000   8000   9000   4000   1000
Queue:   ~0     7000   15000  18000  12000
Consumer: 1000  1000   1000   1000   5000  (scales out as queue grows)

Without queue: 8000 RPS hits Inventory Service → OOM → crash → total failure
With queue: queue buffers the spike, consumer processes at its own pace
```

### Reliability — Messages Survive Restarts

A message in Kafka is written to disk on the broker. If the consumer service crashes mid-processing, the message isn't lost — it's still in the topic. When the service restarts, it picks up from where it left off (the last committed offset).

### Fan-out — One Event, Multiple Consumers

One event published to a Kafka topic can be consumed independently by many consumer groups. Each consumer group gets its own cursor (offset) through the topic. An `order.created` event might be consumed simultaneously by:
- The email consumer group (sends confirmation)
- The warehouse consumer group (triggers picking)
- The analytics consumer group (updates dashboards)
- The fraud consumer group (runs fraud checks)

Each group progresses at its own pace, neither blocking nor aware of the others.

---

## Kafka as a Distributed Commit Log

Kafka is fundamentally different from traditional message queues (RabbitMQ, SQS, ActiveMQ). Traditional queues are like a task list — a message is consumed and deleted. Kafka is a **distributed, append-only, ordered log**.

### What is a Commit Log?

A commit log is a data structure where records are:
1. Appended in order to the end
2. Never modified in place
3. Identified by an offset (sequential integer position)
4. Retained for a configurable period

This model is borrowed from database WALs (Write-Ahead Logs) and journaling filesystems.

```
Kafka Topic Partition — append-only log:

offset:   0      1      2      3      4      5      6
         ┌────┬──────┬──────┬──────┬──────┬──────┬──────┐
         │msg │ msg  │ msg  │ msg  │ msg  │ msg  │ msg  │──► new writes
         └────┴──────┴──────┴──────┴──────┴──────┴──────┘
                          ▲                    ▲
                    Consumer A             Consumer B
                    (at offset 2)          (at offset 5)
                    reading at own pace     reading at own pace

Traditional Queue:
         ┌────┬──────┬──────┬──────┐
         │msg │ msg  │ msg  │ msg  │
         └────┴──────┴──────┴──────┘
         Consumer takes message → message is deleted
         No replay. No second consumer seeing same messages.
```

### Why This Matters

- **Replay**: You can re-read past events. Rewind a consumer to offset 0 and replay everything. This is invaluable for backfilling a new service, recovering from a bug, or auditing.
- **Multiple consumer groups**: Each group maintains its own offset, reads independently.
- **Decoupled consumption rate**: Fast producers and slow consumers don't fight over messages.
- **Audit log**: The log IS the source of truth for what happened.

---

## Topics and Partitions

### Topics

A topic is a logical category for messages — like a table in a database but for events. `user.signup`, `order.created`, `payment.processed`. Producers publish to topics, consumers subscribe to topics.

### Partitions

Each topic is split into one or more partitions. Partitions are the unit of parallelism in Kafka.

```
Topic: order.created (4 partitions)

Partition 0: [msg0] [msg4] [msg8] ...
Partition 1: [msg1] [msg5] [msg9] ...
Partition 2: [msg2] [msg6] [msg10] ...
Partition 3: [msg3] [msg7] [msg11] ...

Each partition is an independent ordered log.
Messages within a partition are strictly ordered.
Messages across partitions have NO guaranteed order.
```

### Partition Assignment

The producer decides which partition a message goes to using a **partitioner**:
- **Default**: hash(key) % numPartitions — same key always goes to same partition
- **Round-robin**: when no key is set — distributes messages evenly
- **Custom**: implement your own partitioner

Using message keys is critical for ordering. If you want all events for `order_id=123` to be processed in order, use `order_id` as the Kafka message key. All messages with that key land in the same partition and are processed sequentially.

```
Key-based partitioning ensures per-entity ordering:

order_id=101 ──► hash("101") % 4 = 1 ──► Partition 1
order_id=102 ──► hash("102") % 4 = 2 ──► Partition 2
order_id=101 ──► hash("101") % 4 = 1 ──► Partition 1 (same partition, ordered)

Consumer for Partition 1 sees: all events for order 101 in order.
```

### Ordering Guarantees

- **Within a partition**: total ordering — messages are delivered in the order they were produced
- **Across partitions**: NO ordering guarantee
- If you need global ordering, use 1 partition — but you lose parallelism
- For most use cases, per-entity ordering (using key) is sufficient

---

## Producers

### Batching

Kafka producers don't send one message at a time. They batch messages for efficiency:

- `linger.ms` (default 0): Wait this many ms to batch more messages before sending. Setting to 5-10ms dramatically increases throughput at the cost of small latency.
- `batch.size` (default 16KB): Max batch size. Producer sends when batch is full or linger.ms expires.
- `buffer.memory` (default 32MB): Total memory for buffering. If full, `send()` blocks or throws.

```
Producer batching timeline:

t=0ms:   msg1 arrives → starts batch, starts linger timer
t=3ms:   msg2 arrives → added to batch
t=5ms:   linger.ms expires → batch (msg1+msg2) sent to broker
t=5ms:   msg3 arrives → starts new batch

Without linger.ms: 3 separate network round trips
With linger.ms=5: 1 network round trip, ~3x throughput
```

### Acks — Acknowledgment Modes

`acks` controls when the producer considers a write successful:

**`acks=0` (fire and forget)**
- Producer sends message, doesn't wait for any acknowledgment
- Fastest, zero latency overhead
- Message can be lost if broker crashes before writing to disk
- Use case: metrics, logs where some loss is acceptable

**`acks=1` (leader only)**
- Producer waits for the partition leader to acknowledge the write
- Moderate latency, good throughput
- Risk: if leader crashes after ack but before replication, message is lost
- Default for many workloads

**`acks=all` or `acks=-1` (all ISR)**
- Producer waits for all in-sync replicas to acknowledge the write
- Safest — message is only confirmed when written to all ISRs
- Higher latency (network round trip to replicas)
- Combined with `min.insync.replicas=2` this is the strongest durability guarantee
- Use case: financial transactions, audit logs, anything where loss is unacceptable

```
acks=all flow:

Producer ──send──► Leader Broker
                      │
                      ├──replicate──► Replica 1 ──ack──►┐
                      ├──replicate──► Replica 2 ──ack──►┤
                      │                                  │
                      └──────────────────────────────────┘
                             All replicas acked
                                    │
                             Leader sends ack back to Producer
```

### Compression

Kafka supports message compression. Compression is done at the batch level (very efficient):
- **lz4**: Best speed, moderate compression. Default choice for most workloads.
- **snappy**: Similar to lz4, Google's algorithm.
- **gzip**: Best compression ratio, higher CPU cost. Good for archival, cost reduction.
- **zstd**: Excellent balance of compression ratio and speed. Preferred for new deployments.

Compression reduces network bandwidth and disk usage, often by 5-10x for JSON messages. The broker stores messages compressed. The consumer decompresses.

---

## Consumers and Consumer Groups

### Consumer Groups

A **consumer group** is a set of consumers that collaborate to consume a topic. Kafka distributes partitions across the consumers in a group.

```
Topic: order.created (4 partitions)
Consumer Group: order-processor (2 consumers)

Consumer 1 ──reads──► Partition 0
                    ──reads──► Partition 1
Consumer 2 ──reads──► Partition 2
                    ──reads──► Partition 3

Key rule: Each partition is assigned to exactly ONE consumer within a group.
```

**Scaling rule**: You can only parallelize up to the number of partitions. If you have 4 partitions and 5 consumers in one group, one consumer will be idle. Plan partition count ahead of time (more is better — you can't reduce partitions).

### Multiple Consumer Groups

Different consumer groups read the same topic independently. Each group has its own offset per partition.

```
Topic: order.created (4 partitions)

Group: email-service    → reads all 4 partitions (sends emails)
Group: warehouse-service → reads all 4 partitions (triggers picking)
Group: analytics-service → reads all 4 partitions (updates dashboards)

None of these groups know about each other. No coordination needed.
```

---

## Consumer Offsets

An **offset** is a sequential integer that identifies a message's position in a partition. Offset 0 is the first message, offset 1 is the second, etc.

Consumers track their position in each partition using offsets. This offset is **committed** back to Kafka (stored in the `__consumer_offsets` internal topic).

### Auto-commit vs Manual Commit

**Auto-commit** (default, `enable.auto.commit=true`):
- Kafka automatically commits the last polled offset every `auto.commit.interval.ms` (default 5s)
- Easy but dangerous: if consumer crashes after polling but before processing, the offset is committed (message appears "processed") but was never actually processed → **message loss**

**Manual commit** (recommended for at-least-once):
- Call `consumer.commitSync()` or `consumer.commitAsync()` only after successfully processing
- If consumer crashes before commit, it re-reads from the last committed offset on restart → **message delivered at least once**

```
Auto-commit risk:
  t=0: Consumer polls batch [offset 10, 11, 12, 13, 14]
  t=1: Consumer starts processing offset 10
  t=3: Auto-commit fires → commits offset 14 (last polled)
  t=4: Consumer crashes while processing offset 11
  t=5: Consumer restarts, starts from offset 15
  Result: offsets 11, 12, 13, 14 were never processed. LOST.

Manual commit (at-least-once):
  t=0: Consumer polls batch [offset 10, 11, 12, 13, 14]
  t=1-5: Consumer processes offset 10 successfully
  t=5: Consumer calls commitSync(offset=11)
  t=6: Consumer processes offset 11 successfully, crashes
  t=7: Consumer restarts, reads from offset 11 (last committed)
  t=8: Consumer processes offset 11 again → duplicate, but not lost
```

### Offset Reset Policy

`auto.offset.reset` controls what happens when a consumer group has no committed offset (new group) or the committed offset is out of range:
- `earliest`: Start from the beginning of the partition
- `latest` (default): Start from the newest messages only
- `none`: Throw an exception

---

## Brokers, Replication, and ISR

### Brokers

A Kafka cluster is made of multiple **brokers** (servers). Each broker hosts some partitions. Brokers are identified by numeric IDs (0, 1, 2...).

### Replication

Each partition has one **leader** and zero or more **followers** (replicas). The replication factor determines how many copies of each partition exist across brokers.

```
Topic: orders, Partition 0, Replication Factor 3

Broker 1: Partition 0 LEADER ──replicate──► Broker 2: Partition 0 follower
                             ──replicate──► Broker 3: Partition 0 follower

All reads and writes go to the LEADER.
Followers pull from leader and stay in sync.
If leader dies, a follower is elected as new leader.
```

### ISR — In-Sync Replicas

The **ISR** is the set of replicas that are "in sync" with the leader — they have replicated all messages within `replica.lag.time.max.ms` (default 30s).

- If `acks=all`, the producer waits for all ISR members to acknowledge
- `min.insync.replicas=2` means at least 2 replicas must be in ISR for writes to succeed
- If a replica falls too far behind, it's removed from ISR (under-replicated) — an alert should fire
- Replication factor 3 + min.insync.replicas=2 is the standard production config

```
ISR Health Scenarios:

Healthy: Leader + 2 followers in ISR → acks=all succeeds
1 broker down: Leader + 1 follower in ISR, min.insync.replicas=2 → still works
2 brokers down: Only leader in ISR, min.insync.replicas=2 → writes FAIL (partition unavailable)

This is the availability/durability tradeoff. You choose to be consistent (refuse writes)
rather than accept data that might be lost.
```

---

## KRaft — Kafka Without Zookeeper

Prior to Kafka 2.8, Kafka required **Zookeeper** for cluster metadata management (leader election, broker registry, topic config). Zookeeper was a separate system to operate — extra complexity.

**KRaft** (Kafka Raft) replaces Zookeeper with a Raft-based metadata quorum built into Kafka itself. Available since Kafka 2.8, production-ready from Kafka 3.3, Zookeeper removal complete in Kafka 4.0.

### Benefits of KRaft
- No separate Zookeeper cluster to manage
- Faster controller failover (milliseconds instead of 30+ seconds)
- Supports millions of partitions (Zookeeper had practical limits around 200k)
- Simpler operational model

### How KRaft Works
- A subset of brokers (typically 3-5) act as **controllers**
- Controllers form a Raft quorum, elect a leader, maintain metadata log
- Other brokers are regular brokers that pull metadata from controllers
- One node can be both a controller and a broker (small clusters) or roles can be separated

---

## Log Compaction vs Log Retention

Kafka offers two strategies for managing partition data:

### Log Retention (time or size based)

Default behavior. Messages are deleted after a configured retention period.
- `log.retention.hours=168` (default 7 days)
- `log.retention.bytes=-1` (no size limit by default)
- Good for event streams where old events are no longer useful

### Log Compaction

For topics that represent the **latest state** of keys (like a key-value changelog), log compaction retains the latest value for each key and deletes older duplicates.

```
Before compaction (key: value):
  offset 0: user:1 → {"name": "Alice", "email": "old@example.com"}
  offset 1: user:2 → {"name": "Bob"}
  offset 2: user:1 → {"name": "Alice", "email": "new@example.com"}
  offset 3: user:3 → {"name": "Charlie"}
  offset 4: user:1 → {"name": "Alice", "email": "final@example.com"}

After compaction:
  offset 1: user:2 → {"name": "Bob"}           (still latest)
  offset 3: user:3 → {"name": "Charlie"}        (still latest)
  offset 4: user:1 → {"name": "Alice", "email": "final@example.com"} (latest)
  Offsets 0 and 2 deleted (superseded by offset 4 for user:1)
```

Use cases for compaction:
- Database change stream (CDC) — latest row state per primary key
- Configuration updates — latest config per service
- User profile events — latest profile state

A **tombstone** (null value message) signals deletion — the compactor eventually removes the key.

---

## Consumer Group Rebalancing

### What Triggers a Rebalance

A consumer group **rebalance** redistributes partition assignments among group members. It's triggered when:
- A new consumer joins the group
- An existing consumer leaves (graceful shutdown or crash)
- A consumer misses heartbeats (session timeout exceeded)
- Topic partition count changes
- Consumer calls `unsubscribe()`

### The Rebalance Process

During a rebalance, **all consumers in the group stop processing** while partition assignments are recalculated. This is the "stop the world" phase.

```
Before rebalance (3 consumers, 6 partitions):
  C1: P0, P1
  C2: P2, P3
  C3: P4, P5

C3 crashes → rebalance triggered:
  All consumers: STOP PROCESSING
  Group coordinator: recalculate assignments
  C1: P0, P1, P4
  C2: P2, P3, P5
  All consumers: RESUME PROCESSING

During rebalance: zero throughput for this consumer group.
```

### Problems with Rebalancing

**1. Frequent rebalances due to slow processing**: If a consumer takes longer to process a batch than `max.poll.interval.ms` (default 5 minutes), Kafka considers it dead and triggers a rebalance. Solution: tune `max.poll.interval.ms` or process faster, or reduce `max.poll.records`.

**2. Rebalance storms**: In large consumer groups, a single slow consumer triggers a rebalance for all consumers. Common in deployments with many pods.

**3. Offset commit before rebalance**: Uncommitted offsets are lost during a rebalance — the new consumer starts from the last committed offset. Messages since last commit are reprocessed. Your consumer must handle this idempotently.

### Cooperative Rebalancing (Incremental)

Kafka 2.4+ introduced **cooperative rebalancing** (COOPERATIVE_STICKY assignor). Instead of revoking all partitions and reassigning, only the partitions that need to move are revoked. Consumers keep their other partitions and continue processing during the rebalance. This dramatically reduces stop-the-world time.

Set `partition.assignment.strategy=CooperativeStickyAssignor` to enable.

---

## Kafka Connect and Kafka Streams

### Kafka Connect

A framework for streaming data **between Kafka and external systems** without writing custom producers/consumers.

- **Source connectors**: Pull data from external systems into Kafka topics
  - Debezium MySQL source connector: reads MySQL binlog → publishes CDC events to Kafka
  - JDBC source connector: polls a database table for new rows
  - S3 source connector: reads files from S3

- **Sink connectors**: Push data from Kafka topics to external systems
  - Elasticsearch sink: Kafka → Elasticsearch index
  - S3 sink: Kafka → S3 files (data lake)
  - JDBC sink: Kafka → database table

Kafka Connect runs as a cluster of **workers**, handles fault tolerance, partition assignment, and offset tracking. You deploy a connector by posting a JSON config via REST API.

### Kafka Streams

A Java/Scala library for building **stream processing applications** on top of Kafka. Not a separate cluster — runs inside your application.

Capabilities:
- Stateless transformations: filter, map, flatMap
- Stateful operations: aggregations, joins, windowing
- KTable: a materialized view of a topic (latest value per key)
- KStream: unbounded stream of records
- State stores: local RocksDB or in-memory stores backed by changelog topics

```
Example Kafka Streams topology:

orders KStream
  .filter(order -> order.amount > 100)
  .mapValues(order -> enrichWithCustomerData(order))
  .groupByKey()
  .windowedBy(TimeWindows.of(Duration.ofMinutes(5)))
  .count()
  .toStream()
  .to("order-counts-per-5min")
```

For Go/Node/Python: use Faust (Python), kafka-streams equivalent libraries, or process-and-publish patterns since Kafka Streams is JVM-only.

---

## Delivery Semantics

### At-Most-Once (Fire and Forget)

Messages may be lost, never duplicated.

Config: `acks=0`, no retries.

The producer sends the message and moves on. If the broker is down or the network blips, the message is gone.

Use cases: Metrics collection, real-time analytics where occasional data points don't matter. Log aggregation where some log loss is acceptable.

```
At-most-once:
  Producer ──send──► [network error] ──► message LOST
  Producer doesn't retry, doesn't know about failure
```

### At-Least-Once (Retry on Failure)

Messages are never lost, but may be delivered multiple times.

Config: `acks=1` or `acks=all`, `retries > 0` (default in new clients: 2147483647), `enable.idempotence=false`.

The producer retries on failure. The consumer commits offsets only after processing. If processing fails, the consumer re-reads the message.

Use cases: Most business-critical workloads. Pair with idempotent consumers.

```
At-least-once duplicate scenario:
  Producer sends msg → broker writes → network drops → producer doesn't get ack
  Producer retries → broker writes AGAIN → 2 copies of the same message in partition
  Consumer processes both copies
```

### Exactly-Once (Idempotent Producers + Transactions)

Messages are delivered exactly once. Technically very complex.

**Idempotent producers** (`enable.idempotence=true`):
- Producer gets a ProducerID (PID) and sequence number per partition
- Broker deduplicates retries using PID + sequence number
- Eliminates duplicates from producer retries
- Automatically sets `acks=all`, `retries=MAX_INT`, `max.in.flight.requests.per.connection=5`

**Transactional API** (for Kafka-to-Kafka exactly-once):
- Producer wraps multiple partition writes in a transaction
- Consumers with `isolation.level=read_committed` skip uncommitted/aborted messages
- Used in Kafka Streams applications
- Complex to implement correctly in custom code

```
Exactly-once producer:
  producer.initTransactions()
  producer.beginTransaction()
  producer.send(record1)
  producer.send(record2)
  producer.sendOffsetsToTransaction(offsets, groupMetadata) // consume+produce atomically
  producer.commitTransaction() // or abortTransaction()
```

---

## Idempotent Consumers

Even with exactly-once producers, your consumer-side processing must be idempotent if you want true exactly-once semantics end-to-end (Kafka to your database).

An idempotent consumer processes the same message multiple times without causing duplicate side effects.

### Techniques

**1. Database unique constraint / upsert**
```sql
INSERT INTO processed_events (event_id, order_id, status)
VALUES ($1, $2, $3)
ON CONFLICT (event_id) DO NOTHING;
-- event_id is a UUID in the Kafka message
-- duplicate processing = duplicate INSERT = conflict = silently ignored
```

**2. Idempotency key in message**
Every event carries a UUID `eventId`. Before processing:
1. Check if `eventId` exists in a `processed_events` table
2. If exists: skip (already processed)
3. If not: process and insert `eventId`

This is the **checksum/dedup table pattern**. The dedup table can be Redis (faster, TTL-based) or a database table.

**3. At-least-once + idempotent operations**
Design operations to be naturally idempotent:
- Setting a field to a value: `UPDATE orders SET status='SHIPPED'` — safe to run twice
- Inserting with ON CONFLICT: safe to run twice
- Incrementing a counter: NOT idempotent — `UPDATE orders SET quantity=quantity+1` fails

**4. Optimistic locking / version check**
Include a version number in the event. Only apply if the current version matches.

```
Event: { eventId: "uuid-123", orderId: "456", status: "SHIPPED", version: 5 }
SQL: UPDATE orders SET status='SHIPPED', version=6 WHERE order_id='456' AND version=5
     -- If version doesn't match (already updated), rows affected = 0 → skip
```

---

## RabbitMQ vs Kafka vs SQS

| Feature | Kafka | RabbitMQ | AWS SQS |
|---|---|---|---|
| **Model** | Distributed append-only log | AMQP message broker | Managed cloud queue |
| **Retention** | Configurable (days/forever) | Until consumed (or TTL) | Until consumed (max 14 days) |
| **Ordering** | Per partition | Per queue | FIFO queues (limited) |
| **Throughput** | Millions msgs/sec | Hundreds of thousands/sec | ~3000 msg/sec standard, 3000 FIFO |
| **Replay** | Yes (seek to any offset) | No (once consumed, gone) | No |
| **Consumer model** | Pull (consumers poll) | Push (broker pushes) | Pull |
| **Routing** | By topic/partition key | Flexible (exchanges, bindings, routing keys) | Basic (1 queue) |
| **Persistence** | Always (log-based) | Optional (durable queues) | Always |
| **Ops complexity** | High (cluster, ZK/KRaft) | Medium (cluster optional) | Zero (fully managed) |
| **Best for** | Event streaming, audit log, CDC, high throughput | Task queues, RPC, complex routing, low latency | Serverless, AWS-native, simple decoupling |

### When to Choose Each

**Choose Kafka when:**
- You need event replay (new service needs historical data)
- High throughput (millions of events/sec)
- Multiple consumer groups reading the same data independently
- Audit trail / event sourcing
- Building a data pipeline (Kafka → Spark/Flink/ClickHouse)
- CDC (Debezium reads MySQL/Postgres WAL → Kafka)

**Choose RabbitMQ when:**
- Complex routing logic (fanout, direct, topic, header exchanges)
- Per-message TTL, priority queues
- Low-latency task distribution
- You need request-reply (RPC over queue)
- Small team, simpler ops than Kafka

**Choose SQS when:**
- AWS-native stack, serverless (Lambda consumers)
- You don't want to manage queue infrastructure
- Standard queue: best-effort ordering, at-least-once delivery
- FIFO queue: exactly-once, ordered, but lower throughput
- Simple use case: decouple two services, don't need replay

---

## Dead Letter Queues

### The Poison Message Problem

A **poison message** is a message that consistently causes the consumer to fail. Examples:
- Malformed JSON that crashes the deserializer
- A message that triggers a bug in business logic
- A message that references a resource that no longer exists (referential integrity violation)

Without a DLQ strategy, the consumer retries forever, blocking the entire partition.

```
Poison message scenario (no DLQ):
  Partition 0: [msg0][msg1][POISON][msg3][msg4]...
  
  Consumer processes msg0 ✓
  Consumer processes msg1 ✓
  Consumer processes POISON → exception → retry
  Consumer processes POISON → exception → retry (again)
  Consumer processes POISON → exception → retry (again)
  ... infinite retry loop ...
  msg3, msg4, and all subsequent messages are NEVER processed.
  Partition is stuck.
```

### DLQ Pattern

After N failed attempts, route the message to a **Dead Letter Queue** (separate topic in Kafka, or DLQ in RabbitMQ/SQS). Processing continues for subsequent messages.

```
DLQ flow:
  Consumer processes POISON → exception
  Retry 1: exception
  Retry 2: exception
  Max retries (3) reached:
    → Publish to "order.created.DLQ" topic with:
        - Original message
        - Error details
        - Attempt count
        - Timestamp
    → Commit offset → continue processing msg3, msg4...

DLQ consumers/alerts:
  - Alert when DLQ depth > 0
  - Developer investigates root cause
  - Fix bug, potentially replay DLQ messages back to original topic
```

### DLQ Message Envelope

When publishing to DLQ, include context for debugging:
```json
{
  "originalTopic": "order.created",
  "originalPartition": 0,
  "originalOffset": 42,
  "originalKey": "order-101",
  "originalValue": "<original message bytes>",
  "errorMessage": "NullPointerException: order.customerId is null",
  "errorStackTrace": "...",
  "failedAttempts": 3,
  "firstFailedAt": "2024-01-15T10:30:00Z",
  "lastFailedAt": "2024-01-15T10:30:45Z"
}
```

### Alerting on DLQ Depth

Monitor DLQ depth as a key operational metric:
- Alert when DLQ has > 0 messages (P2/P3 alert — needs investigation)
- Alert when DLQ grows faster than 10/min (P1 — active bug in production)
- Dashboard: DLQ depth over time per topic

---

## Implementation Examples

### How It Works Internally (ASCII Diagram)

```
Full Kafka Architecture:

┌─────────────────────────────────────────────────────────────────┐
│                        Kafka Cluster                             │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                    │
│  │ Broker 1 │   │ Broker 2 │   │ Broker 3 │                    │
│  │          │   │          │   │          │                    │
│  │ P0 LEAD  │   │ P0 REPLI │   │ P0 REPLI │  ← topic: orders  │
│  │ P1 REPLI │   │ P1 LEAD  │   │ P1 REPLI │                    │
│  │ P2 REPLI │   │ P2 REPLI │   │ P2 LEAD  │                    │
│  └──────────┘   └──────────┘   └──────────┘                    │
│       │                │               │                        │
│  ┌────┴────────────────┴───────────────┴─────┐                 │
│  │           KRaft Controller Quorum          │                 │
│  │     (metadata, leader election, config)    │                 │
│  └────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
         ▲                              │
    producers                      consumers
  (write to leader)           (read from leader, via group coordinator)
```

---

### Go + Chi Router (with sarama)

```go
package main

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/IBM/sarama"
)

// OrderEvent is the message payload
type OrderEvent struct {
	EventID   string    `json:"event_id"`
	OrderID   string    `json:"order_id"`
	UserID    string    `json:"user_id"`
	Amount    float64   `json:"amount"`
	CreatedAt time.Time `json:"created_at"`
}

// =====================
// PRODUCER
// =====================

func newProducer(brokers []string) (sarama.SyncProducer, error) {
	config := sarama.NewConfig()
	
	// Durability: wait for all ISR to acknowledge
	config.Producer.RequiredAcks = sarama.WaitForAll
	
	// Idempotent producer: deduplicates retries at broker level
	config.Producer.Idempotent = true
	config.Net.MaxOpenRequests = 1 // required for idempotent
	
	// Retry configuration
	config.Producer.Retry.Max = 5
	config.Producer.Retry.Backoff = 100 * time.Millisecond
	
	// Compression: lz4 for speed
	config.Producer.Compression = sarama.CompressionLZ4
	
	// Batching: wait up to 10ms to fill batches
	config.Producer.Flush.Frequency = 10 * time.Millisecond
	config.Producer.Flush.MaxMessages = 100
	
	// Return successes so SyncProducer can confirm
	config.Producer.Return.Successes = true
	config.Producer.Return.Errors = true

	return sarama.NewSyncProducer(brokers, config)
}

func publishOrderEvent(producer sarama.SyncProducer, event OrderEvent) error {
	payload, err := json.Marshal(event)
	if err != nil {
		return err
	}

	msg := &sarama.ProducerMessage{
		Topic: "order.created",
		Key:   sarama.StringEncoder(event.OrderID), // same key → same partition → ordered
		Value: sarama.ByteEncoder(payload),
		Headers: []sarama.RecordHeader{
			{Key: []byte("event_type"), Value: []byte("order.created")},
			{Key: []byte("event_id"), Value: []byte(event.EventID)},
		},
	}

	partition, offset, err := producer.SendMessage(msg)
	if err != nil {
		return err
	}
	log.Printf("Published order event: partition=%d, offset=%d", partition, offset)
	return nil
}

// =====================
// CONSUMER (with manual offset commit and DLQ)
// =====================

type OrderConsumer struct {
	ready  chan bool
	db     *DeduplicationStore // tracks processed event IDs
}

// DeduplicationStore is a stub for your actual idempotency store
type DeduplicationStore struct {
	mu   sync.Mutex
	seen map[string]bool
}

func (d *DeduplicationStore) IsProcessed(eventID string) bool {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.seen[eventID]
}

func (d *DeduplicationStore) MarkProcessed(eventID string) {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.seen[eventID] = true
}

// Setup is called once per rebalance, before consuming starts
func (c *OrderConsumer) Setup(session sarama.ConsumerGroupSession) error {
	close(c.ready)
	return nil
}

// Cleanup is called once per rebalance, after consuming stops
func (c *OrderConsumer) Cleanup(sarama.ConsumerGroupSession) error {
	return nil
}

// ConsumeClaim processes messages from one partition
func (c *OrderConsumer) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for {
		select {
		case msg, ok := <-claim.Messages():
			if !ok {
				return nil // channel closed, partition revoked
			}
			c.processMessage(session, msg)

		case <-session.Context().Done():
			return nil
		}
	}
}

func (c *OrderConsumer) processMessage(session sarama.ConsumerGroupSession, msg *sarama.ConsumerMessage) {
	var event OrderEvent
	if err := json.Unmarshal(msg.Value, &event); err != nil {
		log.Printf("ERROR: failed to deserialize message at offset %d: %v", msg.Offset, err)
		// Malformed message — send to DLQ, don't retry forever
		sendToDLQ(msg, err)
		session.MarkMessage(msg, "") // commit and move on
		return
	}

	// Idempotency check — skip already-processed events
	if c.db.IsProcessed(event.EventID) {
		log.Printf("SKIP: event %s already processed (duplicate)", event.EventID)
		session.MarkMessage(msg, "")
		return
	}

	// Business logic
	if err := processOrder(event); err != nil {
		log.Printf("ERROR: failed to process order %s: %v", event.OrderID, err)
		// For retryable errors: don't commit, let rebalance/restart retry
		// For poison messages (non-retryable): send to DLQ and commit
		if isPoisonMessage(err) {
			sendToDLQ(msg, err)
			session.MarkMessage(msg, "")
		}
		return
	}

	// Mark as processed in idempotency store
	c.db.MarkProcessed(event.EventID)

	// Commit offset — only after successful processing (manual commit = at-least-once)
	session.MarkMessage(msg, "")
}

func runConsumer(brokers []string, groupID string) {
	config := sarama.NewConfig()
	config.Version = sarama.V3_0_0_0
	config.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{
		sarama.NewBalanceStrategyRoundRobin(),
	}
	// Manual offset management
	config.Consumer.Offsets.AutoCommit.Enable = false
	config.Consumer.Offsets.Initial = sarama.OffsetNewest
	// Must be > max time to process a batch
	config.Consumer.Group.Session.Timeout = 30 * time.Second
	config.Consumer.Group.Heartbeat.Interval = 3 * time.Second

	client, err := sarama.NewConsumerGroup(brokers, groupID, config)
	if err != nil {
		log.Fatalf("Error creating consumer group: %v", err)
	}
	defer client.Close()

	consumer := &OrderConsumer{
		ready: make(chan bool),
		db:    &DeduplicationStore{seen: make(map[string]bool)},
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	wg := &sync.WaitGroup{}
	wg.Add(1)
	go func() {
		defer wg.Done()
		for {
			if err := client.Consume(ctx, []string{"order.created"}, consumer); err != nil {
				log.Printf("Error from consumer: %v", err)
			}
			if ctx.Err() != nil {
				return
			}
			consumer.ready = make(chan bool) // reset for next rebalance
		}
	}()

	<-consumer.ready // wait until first rebalance is complete
	log.Println("Consumer ready")

	sigterm := make(chan os.Signal, 1)
	signal.Notify(sigterm, syscall.SIGINT, syscall.SIGTERM)
	<-sigterm

	cancel()
	wg.Wait()
}

func processOrder(event OrderEvent) error        { return nil } // stub
func isPoisonMessage(err error) bool             { return false } // stub
func sendToDLQ(msg *sarama.ConsumerMessage, err error) { // stub
	log.Printf("DLQ: sending message at offset %d to DLQ: %v", msg.Offset, err)
}

func main() {
	brokers := []string{"localhost:9092"}
	
	producer, err := newProducer(brokers)
	if err != nil {
		log.Fatalf("Failed to create producer: %v", err)
	}
	defer producer.Close()

	// Publish a test event
	publishOrderEvent(producer, OrderEvent{
		EventID:   "evt-123",
		OrderID:   "ord-456",
		UserID:    "usr-789",
		Amount:    99.99,
		CreatedAt: time.Now(),
	})

	runConsumer(brokers, "order-processor")
}
```

---

### Node.js + Express (with kafkajs)

```javascript
// kafka.js — production-ready KafkaJS setup
const { Kafka, logLevel, CompressionTypes } = require('kafkajs');
const { v4: uuidv4 } = require('uuid');

const kafka = new Kafka({
  clientId: 'order-service',
  brokers: ['localhost:9092'],
  logLevel: logLevel.WARN,
  retry: {
    initialRetryTime: 100,
    retries: 8,
    factor: 2,
    multiplier: 1.5,
    maxRetryTime: 30000,
  },
});

// =====================
// PRODUCER
// =====================

async function createProducer() {
  const producer = kafka.producer({
    // Idempotent producer: exactly-once at producer level
    idempotent: true,
    // With idempotent=true, acks is automatically set to -1 (all)
    transactionTimeout: 30000,
    allowAutoTopicCreation: false,
  });

  await producer.connect();
  return producer;
}

async function publishOrderEvent(producer, order) {
  const event = {
    eventId: uuidv4(),  // unique ID for idempotency
    eventType: 'order.created',
    orderid: order.id,
    userId: order.userId,
    amount: order.amount,
    createdAt: new Date().toISOString(),
  };

  try {
    const result = await producer.send({
      topic: 'order.created',
      compression: CompressionTypes.LZ4,
      messages: [
        {
          key: order.id,  // key = orderId → ensures ordering per order
          value: JSON.stringify(event),
          headers: {
            'event-type': 'order.created',
            'event-id': event.eventId,
            'content-type': 'application/json',
          },
        },
      ],
    });
    console.log('Published:', result);
    return event.eventId;
  } catch (error) {
    console.error('Failed to publish event:', error);
    throw error;
  }
}

// =====================
// CONSUMER (manual commit + idempotency)
// =====================

// In-memory dedup store (use Redis in production with TTL)
const processedEvents = new Set();

async function createConsumer(groupId) {
  const consumer = kafka.consumer({
    groupId,
    // If no committed offset exists, start from beginning (for replay capability)
    fromBeginning: false,
    // Max time between polls — must be > your batch processing time
    maxWaitTimeInMs: 5000,
    // Min bytes to fetch per request (increases throughput at cost of latency)
    minBytes: 1,
    maxBytes: 5 * 1024 * 1024, // 5MB
  });

  await consumer.connect();
  return consumer;
}

async function runConsumer() {
  const consumer = await createConsumer('order-processor');
  const dlqProducer = await createProducer();

  await consumer.subscribe({ topic: 'order.created', fromBeginning: false });

  // eachBatch gives us control over offset commits
  await consumer.run({
    // Disable auto commit — we commit manually after processing
    autoCommit: false,
    eachBatch: async ({ batch, resolveOffset, heartbeat, commitOffsetsIfNecessary, isRunning, isStale }) => {
      for (const message of batch.messages) {
        if (!isRunning() || isStale()) break; // consumer is shutting down or partition revoked

        let event;
        try {
          event = JSON.parse(message.value.toString());
        } catch (err) {
          // Malformed message → DLQ, don't retry
          await sendToDLQ(dlqProducer, batch.topic, batch.partition, message, err);
          resolveOffset(message.offset);
          await heartbeat();
          continue;
        }

        // Idempotency check
        if (processedEvents.has(event.eventId)) {
          console.log(`Skipping duplicate event: ${event.eventId}`);
          resolveOffset(message.offset);
          continue;
        }

        let retries = 0;
        const maxRetries = 3;
        let processed = false;

        while (retries < maxRetries && !processed) {
          try {
            await processOrder(event);
            processedEvents.add(event.eventId); // mark as processed
            processed = true;
          } catch (err) {
            retries++;
            if (retries >= maxRetries) {
              console.error(`Max retries for event ${event.eventId}, sending to DLQ`);
              await sendToDLQ(dlqProducer, batch.topic, batch.partition, message, err);
              processed = true; // don't retry further
            } else {
              await new Promise(resolve => setTimeout(resolve, 100 * Math.pow(2, retries)));
            }
          }
        }

        // Mark this offset as processed — commit when resolveOffset is called
        resolveOffset(message.offset);
        
        // Send heartbeat to prevent session timeout during long batches
        await heartbeat();
      }

      // Commit all resolved offsets for this batch
      await commitOffsetsIfNecessary();
    },
  });

  // Graceful shutdown
  process.on('SIGINT', async () => {
    console.log('Shutting down consumer...');
    await consumer.disconnect();
    await dlqProducer.disconnect();
    process.exit(0);
  });
}

async function sendToDLQ(producer, originalTopic, partition, message, error) {
  const dlqMessage = {
    originalTopic,
    originalPartition: partition,
    originalOffset: message.offset,
    originalKey: message.key?.toString(),
    originalValue: message.value?.toString(),
    errorMessage: error.message,
    errorStack: error.stack,
    failedAt: new Date().toISOString(),
  };

  await producer.send({
    topic: `${originalTopic}.DLQ`,
    messages: [{ value: JSON.stringify(dlqMessage) }],
  });
}

async function processOrder(event) {
  // Your business logic here
  console.log(`Processing order: ${event.orderId}`);
}

module.exports = { createProducer, publishOrderEvent, runConsumer };
```

---

### Python + FastAPI (with aiokafka)

```python
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError
from fastapi import FastAPI, BackgroundTasks
import redis.asyncio as aioredis

app = FastAPI()

# =====================
# PRODUCER
# =====================

_producer: AIOKafkaProducer | None = None

async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers="localhost:9092",
            # Durability: wait for all ISR replicas
            acks="all",
            # Idempotent producer
            enable_idempotence=True,
            # Compression
            compression_type="lz4",
            # Batching: wait 10ms to fill batches
            linger_ms=10,
            # Serialization
            value_serializer=lambda v: json.dumps(v).encode(),
            key_serializer=lambda k: k.encode() if k else None,
            # Retry on transient errors
            request_timeout_ms=30000,
            retry_backoff_ms=100,
        )
        await _producer.start()
    return _producer


@app.post("/orders")
async def create_order(order: dict, background_tasks: BackgroundTasks):
    # Handle HTTP request synchronously (fast path)
    order_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    
    # Save to DB (not shown)
    
    # Publish event async — don't block HTTP response
    background_tasks.add_task(publish_order_event, order_id, event_id, order)
    
    return {"order_id": order_id, "status": "created"}


async def publish_order_event(order_id: str, event_id: str, order: dict):
    producer = await get_producer()
    
    event = {
        "event_id": event_id,
        "event_type": "order.created",
        "order_id": order_id,
        "user_id": order.get("user_id"),
        "amount": order.get("amount"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    try:
        record_metadata = await producer.send_and_wait(
            topic="order.created",
            key=order_id,  # same key → same partition → ordered
            value=event,
            headers=[
                ("event-type", b"order.created"),
                ("event-id", event_id.encode()),
            ],
        )
        print(f"Published: partition={record_metadata.partition}, offset={record_metadata.offset}")
    except KafkaError as e:
        print(f"Failed to publish event {event_id}: {e}")
        # In production: store to outbox table for retry


# =====================
# CONSUMER (manual commit + Redis dedup)
# =====================

async def run_consumer():
    redis = aioredis.from_url("redis://localhost:6379")
    dlq_producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9092",
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await dlq_producer.start()

    consumer = AIOKafkaConsumer(
        "order.created",
        bootstrap_servers="localhost:9092",
        group_id="order-processor",
        # Manual offset commit — at-least-once delivery
        enable_auto_commit=False,
        auto_offset_reset="earliest",  # replay from beginning if new group
        # Deserialize JSON
        value_deserializer=lambda v: json.loads(v.decode()),
        # Fetch settings
        max_poll_records=50,
        fetch_max_wait_ms=500,
        session_timeout_ms=30000,
        heartbeat_interval_ms=3000,
    )
    await consumer.start()

    try:
        async for msg in consumer:
            await process_message(consumer, dlq_producer, redis, msg)
    finally:
        await consumer.stop()
        await dlq_producer.stop()
        await redis.close()


async def process_message(
    consumer: AIOKafkaConsumer,
    dlq_producer: AIOKafkaProducer,
    redis: aioredis.Redis,
    msg: Any,
):
    event = msg.value
    event_id = event.get("event_id")

    if not event_id:
        # Malformed: send to DLQ
        await send_to_dlq(dlq_producer, msg, "Missing event_id")
        await consumer.commit({
            msg.partition: msg.offset + 1  # commit next offset to read
        })
        return

    # Idempotency check using Redis (TTL = 24 hours)
    dedup_key = f"processed_event:{event_id}"
    already_processed = await redis.get(dedup_key)
    if already_processed:
        print(f"Skipping duplicate event: {event_id}")
        await consumer.commit({msg.partition: msg.offset + 1})
        return

    # Process with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await process_order(event)
            
            # Mark as processed in Redis with 24h TTL
            await redis.setex(dedup_key, 86400, "1")
            
            # Commit offset AFTER successful processing (at-least-once guarantee)
            await consumer.commit({msg.partition: msg.offset + 1})
            return

        except Exception as e:
            print(f"Attempt {attempt + 1} failed for event {event_id}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(0.1 * (2 ** attempt))  # exponential backoff
            else:
                # Exhausted retries — send to DLQ
                await send_to_dlq(dlq_producer, msg, str(e))
                await consumer.commit({msg.partition: msg.offset + 1})


async def process_order(event: dict):
    """Business logic for processing an order event."""
    print(f"Processing order: {event.get('order_id')}")
    # DB operations, downstream calls, etc.


async def send_to_dlq(producer: AIOKafkaProducer, msg: Any, error_msg: str):
    dlq_payload = {
        "original_topic": msg.topic,
        "original_partition": msg.partition,
        "original_offset": msg.offset,
        "original_key": msg.key.decode() if msg.key else None,
        "original_value": msg.value,
        "error_message": error_msg,
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }
    await producer.send_and_wait(
        topic=f"{msg.topic}.DLQ",
        value=dlq_payload,
    )
    print(f"Sent to DLQ: partition={msg.partition}, offset={msg.offset}")


@app.on_event("startup")
async def startup():
    asyncio.create_task(run_consumer())


@app.on_event("shutdown")
async def shutdown():
    global _producer
    if _producer:
        await _producer.stop()
```

---

## Common Patterns & Best Practices

### Pattern 1: Partition Key Strategy

Always think carefully about your partition key:
- **Order events**: key = `order_id` — all events for one order in same partition, ordered
- **User events**: key = `user_id` — all events for one user in same partition
- **No ordering needed**: no key (null) — round-robin distribution, max throughput

A bad partition key causes **hot partitions** — one partition gets all the traffic while others sit idle. Never use a high-cardinality key that maps to a single value (e.g., don't use `event_type` as key if all events are the same type).

### Pattern 2: Topic Naming Convention

Consistent naming reduces confusion:
```
<domain>.<entity>.<verb>
order.created
order.cancelled
order.shipped
payment.processed
payment.failed
user.signup
user.profile.updated

DLQs follow parent topic:
order.created.DLQ
payment.processed.DLQ
```

### Pattern 3: Schema Registry

Use Confluent Schema Registry with Avro or Protobuf:
- Enforces schema compatibility (backward, forward, full)
- Prevents producers from publishing malformed events
- Consumers always know the schema version
- Compact binary format (vs verbose JSON)

### Pattern 4: Consumer Lag Monitoring

Consumer lag = (latest offset in partition) - (consumer's current offset). High lag = consumer is falling behind producers.

Expose consumer lag as a metric. Alert when lag exceeds SLA threshold (e.g., > 10,000 messages = more than 1 minute of work pending).

### Pattern 5: Graceful Shutdown

Always implement graceful shutdown for consumers:
1. Stop accepting new messages (unsubscribe or drain)
2. Finish processing current batch
3. Commit all pending offsets
4. Close consumer connection

Without graceful shutdown, in-progress messages may need to be reprocessed after restart.

---

## Common Pitfalls

**1. Setting `enable.auto.commit=true` for critical workloads**
Auto-commit advances the offset on a timer, not after processing. Messages polled but not yet processed will be marked as consumed on crash. Data loss in disguise.

**2. Not planning partition count upfront**
You cannot reduce partitions. Plan for future scale. A common heuristic: partitions = target consumers × 3 (allows scaling). For high-throughput topics, start with 12-24 partitions.

**3. Ignoring consumer group rebalancing latency**
If rebalances happen frequently (slow consumers, frequent deploys), throughput suffers significantly. Use cooperative sticky rebalancing and tune session timeouts.

**4. Using Kafka as a queue for single-consumer use cases**
If only one service ever consumes a topic and replay isn't needed, SQS or RabbitMQ may be simpler.

**5. Not handling duplicate messages**
At-least-once delivery means duplicates are possible. Every consumer must be idempotent. This is not optional.

**6. Unbounded retry loops causing partition stalls**
Without a DLQ, a poison message retried forever blocks the entire partition. Always implement a max-retry + DLQ pattern.

**7. Producing without checking ack errors**
`producer.send()` in many libraries is async. If you don't check errors or use `send_and_wait`, you may silently lose messages.

**8. Small `max.poll.interval.ms` with slow processing**
If your business logic is slow (database queries, external API calls), `max.poll.interval.ms` (default 5 min) may expire. Kafka assumes the consumer is dead and triggers a rebalance. Tune this value or reduce `max.poll.records`.

---

## Interview Questions

**Q: Why is Kafka a "commit log" and not a traditional message queue?**

A: Kafka is an append-only, ordered log where messages are identified by offsets and retained for a configurable period regardless of consumption. Traditional queues delete messages upon consumption. Kafka's log model enables: (1) message replay — consumers can seek to any past offset; (2) multiple consumer groups reading the same data independently; (3) audit trail — the log is a historical record. Traditional queues are task-distribution systems; Kafka is an event log.

**Q: What ordering guarantees does Kafka provide?**

A: Kafka guarantees ordering only **within a single partition**. Messages produced to partition N are consumed in the order they were produced. There is no ordering guarantee across partitions. To preserve ordering for related events (e.g., all events for the same order), use the entity ID as the partition key — the hash function maps the key to the same partition consistently.

**Q: What is consumer group rebalancing and what can go wrong?**

A: A rebalance redistributes topic partition assignments among the consumers in a group. It's triggered when consumers join/leave/crash or topic partitions change. During a rebalance, **all consumers stop processing** — this is a "stop the world" event. Problems: (1) frequent rebalances due to `max.poll.interval.ms` expiry on slow consumers — throughput drops; (2) uncommitted offsets before rebalance cause message reprocessing; (3) in large consumer groups, a single slow consumer triggers disruption for all. Mitigation: cooperative sticky rebalancing, tune poll intervals, ensure idempotent processing.

**Q: What is the difference between at-least-once and exactly-once delivery?**

A: At-least-once: messages are guaranteed to be delivered but may be duplicated (producer retries on network error create duplicates). Requires idempotent consumers. At-most-once: messages may be lost but never duplicated (fire and forget, acks=0). Exactly-once: messages are delivered precisely once end-to-end, using idempotent producers (dedup at broker using PID+sequence) and transactional API (atomic consume+produce). Exactly-once is complex and has performance overhead; at-least-once + idempotent consumers is the most practical production approach.

**Q: How do you make a consumer idempotent?**

A: Every event should carry a unique ID (UUID). Before processing, check if this ID has been processed before (using a database unique constraint, a Redis SET, or a dedup table). If already processed, skip. If not, process and record the ID atomically (within the same transaction as the business operation). For naturally idempotent operations (upserts, SET operations), no extra dedup is needed. For non-idempotent operations (increment, insert), dedup is mandatory.

**Q: When would you choose RabbitMQ over Kafka?**

A: Choose RabbitMQ for: (1) complex message routing — exchanges with routing keys, headers, fanout patterns; (2) per-message TTL and priority queues; (3) low-latency task queues where broker push model outperforms consumer polling; (4) request-reply (RPC over queue) patterns; (5) simpler operational model — no need for retention, replay, or high throughput. Kafka is superior for high-throughput event streaming, replay capability, multiple independent consumers, and building data pipelines.

**Q: What is a DLQ and why is it important?**

A: A Dead Letter Queue receives messages that failed processing after all retry attempts. Without a DLQ, a poison message (malformed, triggers a bug, references non-existent data) causes an infinite retry loop that blocks the entire partition — all subsequent messages are never processed. The DLQ routes the poison message out of the main processing path, preserving it for investigation while allowing normal processing to continue. Alert on DLQ depth > 0 in production.

**Q: What does `acks=all` mean in a Kafka producer?**

A: `acks=all` (or `acks=-1`) means the producer waits for acknowledgment from all **in-sync replicas** (ISR) of the partition before considering the write successful. Combined with `min.insync.replicas=2`, this means at least 2 replicas must acknowledge before the producer gets a success response. This is the strongest durability guarantee — a message confirmed with `acks=all` is not lost even if all but one broker fails. The tradeoff is higher latency (must wait for all ISR members to write to disk).

---

## Resources

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Confluent Developer Kafka Tutorials](https://developer.confluent.io/tutorials/)
- [The Log: What every software engineer should know about real-time data — Jay Kreps](https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying)
- [Designing Data-Intensive Applications — Chapter 11: Stream Processing (Kleppmann)](https://dataintensive.net/)
- [KafkaJS Documentation](https://kafka.js.org/)
- [aiokafka Documentation](https://aiokafka.readthedocs.io/)
- [IBM Sarama (Go)](https://github.com/IBM/sarama)
- [Kafka Consumer Group Rebalancing Deep Dive](https://www.confluent.io/blog/kafka-consumer-multi-threaded-messaging/)

---

**Next:** [Part 9.2: Event-Driven Architecture Patterns](./09-event-driven-patterns.md)
