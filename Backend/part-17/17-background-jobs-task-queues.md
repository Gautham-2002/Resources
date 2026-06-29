# Part 17.1: Background Jobs & Task Queues

## What You'll Learn
- Why background jobs are essential in production backend systems
- Core architecture of job queues (producers, queues, workers, DLQs)
- How exactly-once processing works and why it's hard
- Retry strategies: immediate, exponential backoff, jitter
- Cron job coordination in distributed systems
- Production job libraries: asynq (Go), BullMQ (Node.js), Celery/arq (Python)
- How to enqueue, process, schedule, and monitor jobs
- Common failure modes, interview traps, and alerting strategies

## Table of Contents
1. [Why Background Jobs?](#1-why-background-jobs)
2. [Job Queue Architecture](#2-job-queue-architecture)
3. [Core Components Deep Dive](#3-core-components-deep-dive)
4. [Exactly-Once Processing](#4-exactly-once-processing)
5. [Retry Strategies](#5-retry-strategies)
6. [Cron Jobs & Distributed Scheduling](#6-cron-jobs--distributed-scheduling)
7. [Job Libraries by Stack](#7-job-libraries-by-stack)
8. [How It Works Internally](#8-how-it-works-internally)
9. [Implementation Examples](#9-implementation-examples)
   - [Go + asynq](#go--asynq)
   - [Node.js + BullMQ](#nodejs--bullmq)
   - [Python + Celery / arq](#python--celery--arq)
10. [Monitoring & Observability](#10-monitoring--observability)
11. [Common Patterns & Best Practices](#11-common-patterns--best-practices)
12. [Common Pitfalls](#12-common-pitfalls)
13. [Interview Questions](#13-interview-questions)
14. [Resources](#14-resources)

---

## 1. Why Background Jobs?

The core principle: **don't make your users wait for things they don't need to wait for.**

### The Inline Processing Problem

When an API request triggers a slow operation inline, the user bears the full cost:

```
POST /register
├── Validate input          ~1ms
├── Create user in DB       ~5ms
├── Send welcome email  ← ~2000ms (SMTP + template rendering)
├── Generate avatar     ← ~3000ms (image processing)
├── Notify Slack        ← ~800ms  (external API call)
└── Return 201          total: ~5806ms  ← terrible UX
```

With background jobs:

```
POST /register
├── Validate input          ~1ms
├── Create user in DB       ~5ms
├── Enqueue: send_email     ~2ms  (Redis LPUSH)
├── Enqueue: gen_avatar     ~2ms
├── Enqueue: notify_slack   ~2ms
└── Return 201              total: ~12ms  ← great UX
```

The slow work happens asynchronously. The user sees a fast response.

### The Five Canonical Reasons to Use Background Jobs

**1. Don't make users wait for slow operations**
- Sending emails (SMTP, transactional email services)
- Image/video processing (resize, transcode, watermark)
- Report generation (PDF, Excel, large CSV exports)
- AI/ML inference (embeddings, image classification)
- Geocoding, third-party enrichment APIs

**2. Retry failed operations automatically**
- Transient failures (network blip, rate limit, downstream service 503)
- Inline handlers can't retry without blocking the user
- Queue workers can back off and retry transparently

**3. Rate-limit outbound API calls**
- You can burst-write 10,000 jobs into a queue
- The worker pool processes them at a controlled rate (e.g., 100/minute)
- Prevents blowing past Twilio/SendGrid/Stripe API rate limits

**4. Fan-out processing (one event → multiple jobs)**
- User places order → simultaneously enqueue: payment capture, inventory update, email confirmation, analytics event, fraud check
- All happen in parallel, none blocking the API response

**5. Scheduled recurring tasks (cron jobs)**
- Daily reports, weekly digests, hourly cleanup
- Database index maintenance, cache warming
- Subscription billing cycles, invoice generation

---

## 2. Job Queue Architecture

### High-Level Flow

```
                        ┌─────────────────────────────────────────────┐
                        │              API Server (Producer)           │
  HTTP POST /checkout   │  1. Validate request                         │
  ──────────────────►   │  2. Write to DB                              │
                        │  3. Enqueue job (fire-and-forget)            │
  HTTP 200 (fast) ◄───  │  4. Return response                          │
                        └──────────────────┬──────────────────────────┘
                                           │ Enqueue
                                           ▼
                        ┌──────────────────────────────────────────────┐
                        │                   Queue                       │
                        │   Redis List / Redis Streams / RabbitMQ      │
                        │   SQS / Kafka / PostgreSQL (SKIP LOCKED)     │
                        │                                              │
                        │   [job_1][job_2][job_3][job_4] ──► consume  │
                        └──────────────────┬───────────────────────────┘
                                           │ Dequeue
                                           ▼
                        ┌──────────────────────────────────────────────┐
                        │              Worker Pool (Consumers)          │
                        │                                              │
                        │   Worker 1: processing job_1                 │
                        │   Worker 2: processing job_2                 │
                        │   Worker 3: idle                             │
                        │   Worker 4: processing job_3                 │
                        └──────────────────┬───────────────────────────┘
                                           │ Execute
                                           ▼
                        ┌──────────────────────────────────────────────┐
                        │            Job Processor (Business Logic)     │
                        │                                              │
                        │   Success → mark complete                    │
                        │   Failure → retry with backoff               │
                        │   Max retries exceeded → Dead Letter Queue   │
                        └──────────────────────────────────────────────┘
```

### Queue Backend Options

| Queue Backend | Best For | Persistence | Ordering | Throughput |
|---------------|----------|-------------|----------|------------|
| Redis List (`LPUSH`/`BRPOP`) | Simple task queues | Optional (AOF/RDB) | FIFO | Very high |
| Redis Streams | At-least-once with consumer groups | Yes | Yes | Very high |
| RabbitMQ | Complex routing, fanout, topic exchanges | Yes | FIFO per queue | High |
| AWS SQS | Cloud-native, serverless workers | Yes | Best-effort FIFO | High |
| Apache Kafka | Event streaming, replay, audit log | Yes | Per-partition | Extreme |
| PostgreSQL (SKIP LOCKED) | Already using Postgres, simple needs | Yes | FIFO | Moderate |

---

## 3. Core Components Deep Dive

### 3.1 Producer

The API server (or any service) that creates and enqueues jobs. Key characteristics:
- Should be **fast** — enqueuing must not slow down the HTTP response
- Should be **reliable** — if enqueue fails, don't silently drop the job
- Enqueue is typically `O(1)` — a single Redis command or DB insert

**Outbox Pattern (reliable enqueue):**

When you need to guarantee a job is enqueued when a DB write succeeds (avoiding the dual-write problem):

```
BEGIN TRANSACTION
  INSERT INTO orders (...)           ← main write
  INSERT INTO outbox (job_type, payload, status='pending')  ← job record
COMMIT

── Background outbox poller ──►  reads outbox, enqueues to Redis, marks dispatched
```

This prevents: "wrote to DB, then process crashed before enqueuing to Redis."

### 3.2 Queue

The durable, ordered data structure where jobs wait for processing.

**Redis List internals:**
```
LPUSH jobs:email '{"id":"abc","to":"user@example.com"}'
BRPOP jobs:email 0   ← worker blocks until job available, returns within timeout
```

**Job payload structure:**
```json
{
  "id": "01J8X...",
  "type": "send_welcome_email",
  "payload": {
    "user_id": 1234,
    "email": "user@example.com"
  },
  "retry_count": 0,
  "max_retries": 3,
  "enqueued_at": "2026-06-29T10:00:00Z",
  "run_at": "2026-06-29T10:00:00Z"
}
```

### 3.3 Consumer / Worker

The process that dequeues and executes jobs.

**Worker lifecycle:**
```
WORKER STARTUP
│
├── Register job type handlers (type → handler function)
├── Connect to queue backend
└── Start processing loop:
      │
      ├── DEQUEUE job (blocking wait, e.g., BRPOP)
      │     ↓
      ├── CLAIM job (mark as "in-processing" with visibility timeout)
      │     ↓
      ├── EXECUTE handler
      │     ├── SUCCESS → ACK job, mark complete
      │     └── FAILURE → NACK, reschedule with backoff
      │           └── max retries exceeded → send to DLQ
      └── loop
```

**Concurrency model:**
- Goroutine-per-job (Go), thread pool (Python Celery), async tasks (Node.js BullMQ)
- Worker concurrency = number of jobs processed simultaneously
- Too high → overwhelms downstream services
- Too low → queue depth grows, jobs lag

### 3.4 Visibility Timeout (Critical Concept)

This is the mechanism that prevents jobs from being lost when workers die.

```
Timeline:
t=0  Worker A dequeues job_1
         │
         │   Job is "invisible" to other workers
         │   (visibility timeout = 30s)
         │
t=10 Worker A DIES (crash, OOM, network partition)
         │
         │   ... job_1 remains invisible ...
         │
t=30 Visibility timeout EXPIRES
         │
         ▼
     Job_1 is REQUEUED automatically
         │
t=31 Worker B dequeues job_1 and processes it ✓
```

**Why this matters:**
- Ensures at-least-once delivery: if a worker dies mid-job, the job is retried
- The downside: if the job actually completed before the worker crashed and ACK was lost, the job runs twice → need idempotency

**Typical visibility timeouts by operation:**
- Email send: 30s
- Image processing: 5min
- PDF report generation: 15min
- Video transcoding: 1hr+

### 3.5 Dead Letter Queue (DLQ)

Jobs that exhaust all retry attempts land in the DLQ.

```
Queue: jobs:email
         │
         │  retry 1 (immediate)
         │  retry 2 (30s delay)
         │  retry 3 (5min delay)
         │  retry 4 (30min delay)
         │  retry 5 (2hr delay) ← MAX RETRIES
         ▼
DLQ: jobs:email:dead
```

**DLQ is not a trash can — it's an audit trail:**
- Alert on any DLQ growth (health signal)
- Engineers inspect DLQ jobs to diagnose bugs
- Requeue DLQ jobs after fixing the underlying bug
- Some DLQ jobs warrant manual intervention (payment failures, critical notifications)

---

## 4. Exactly-Once Processing

True exactly-once is impossible in distributed systems (see: the two generals problem). What you can achieve: **at-least-once delivery + idempotent handlers = effectively-once behavior.**

### Why Exactly-Once Is Hard

```
Worker A:
  1. Dequeues job_1
  2. Processes payment ($100 charge to Stripe)       ← Stripe charges the card
  3. Crashes before ACKing the job

Queue:
  4. Visibility timeout expires
  5. Job_1 requeued

Worker B:
  6. Dequeues job_1
  7. Processes payment ($100 charge to Stripe)       ← Stripe charges the card AGAIN
```

The user gets charged twice. This is the core problem.

### Solution: Idempotency Keys

An idempotency key is a unique identifier for a specific "operation intent." If you see the same key twice, you know you've already done the work.

**Strategy 1: Database unique constraint**
```sql
CREATE TABLE email_sends (
    idempotency_key VARCHAR(64) PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    sent_at         TIMESTAMP,
    status          VARCHAR(20)
);

-- In the job handler:
INSERT INTO email_sends (idempotency_key, user_id, status)
VALUES ($1, $2, 'sent')
ON CONFLICT (idempotency_key) DO NOTHING
RETURNING id;

-- If nothing returned → already processed, skip
```

**Strategy 2: Redis SET NX (atomic check-and-set)**
```
SETNX job:idempotency:{job_id} "1" EX 86400
  ├── Returns 1 (success) → first time processing, proceed
  └── Returns 0 (fail)    → already processed, skip
```

**Strategy 3: Check-then-act in DB transaction**
```
BEGIN TRANSACTION
  SELECT status FROM jobs WHERE id = $1 FOR UPDATE
    ├── status = 'completed' → ROLLBACK, return early
    └── status = 'processing' → continue
  -- do the work
  UPDATE jobs SET status = 'completed' WHERE id = $1
COMMIT
```

### Designing Idempotent Job Handlers

Good idempotent handler structure:
```
func handleSendEmail(ctx, job):
    // 1. Check if already done
    if alreadySent(job.idempotencyKey):
        return nil  // silently succeed — idempotent

    // 2. Do the work
    err := emailService.Send(job.to, job.subject, job.body)
    if err != nil:
        return err  // will retry

    // 3. Record that it's done (AFTER success, not before)
    markAsSent(job.idempotencyKey)
    return nil
```

**Idempotency key generation:**
- Include job type + unique business identifiers
- `email:{user_id}:{template}:{date}` for daily digest emails
- `charge:{order_id}` for payment capture
- UUID generated at enqueue time, stored in job payload

---

## 5. Retry Strategies

### 5.1 Immediate Retry

```
Job fails → immediately requeue → immediately retry
```

**Problem:** If the failure is caused by a downstream dependency (database overloaded, external API down), an immediate retry will pound the already-failing service, making things worse.

**Use when:** Bug fix already deployed and you're manually reprocessing DLQ.

### 5.2 Exponential Backoff

```
retry 1: delay = 2^1 = 2s
retry 2: delay = 2^2 = 4s
retry 3: delay = 2^3 = 8s
retry 4: delay = 2^4 = 16s
retry 5: delay = 2^5 = 32s  ← typically cap here or DLQ
```

Formula: `delay = min(base * 2^attempt, max_delay)`

This gives the downstream service time to recover between retries.

### 5.3 Jitter (Critical for Production Systems)

**Problem with pure exponential backoff:**

If 10,000 jobs fail simultaneously (Redis blip at t=0), with pure backoff they ALL retry at t=2s, ALL retry again at t=4s, etc. This creates a **thundering herd** that repeatedly hammers the recovering service.

**Solution: Add randomness (jitter)**

```
Full jitter:   delay = random(0, base * 2^attempt)
Equal jitter:  delay = (base * 2^attempt / 2) + random(0, base * 2^attempt / 2)
```

With full jitter, 10,000 jobs spread their retries randomly across the window instead of hitting at the same instant.

AWS wrote the canonical article on this: ["Exponential Backoff and Jitter"](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/).

### 5.4 Retry Decision Logic

Not all errors should be retried:

```
type of error         → retry?
─────────────────────────────────────────────────────
network timeout       → YES  (transient)
service 503           → YES  (transient)
rate limit 429        → YES  (respect Retry-After header)
invalid payload 400   → NO   (permanent failure, send to DLQ immediately)
"user not found"      → NO   (permanent, the user was deleted)
DB unique constraint  → NO   (already processed — idempotent, not an error)
```

Implementation:
```python
class NonRetryableError(Exception):
    """Raised when a job should go directly to DLQ without retry."""
    pass

@celery_app.task(bind=True, max_retries=5)
def send_email(self, user_id: int, template: str):
    try:
        user = db.get_user(user_id)
        if user is None:
            raise NonRetryableError(f"User {user_id} not found")  # no retry
        email_client.send(user.email, template)
    except NonRetryableError:
        raise  # goes to DLQ immediately
    except Exception as exc:
        # exponential backoff with jitter
        delay = min(2 ** self.request.retries + random.uniform(0, 1), 3600)
        raise self.retry(exc=exc, countdown=delay)
```

---

## 6. Cron Jobs & Distributed Scheduling

### 6.1 Cron Expression Syntax

```
┌──── minute (0-59)
│  ┌─── hour (0-23)
│  │  ┌── day of month (1-31)
│  │  │  ┌─ month (1-12)
│  │  │  │  ┌ day of week (0-6, 0=Sunday)
│  │  │  │  │
*  *  *  *  *

Examples:
0 2 * * *         = 2:00 AM every day
0 */6 * * *       = every 6 hours
0 9 * * 1-5       = 9 AM weekdays only
*/15 * * * *      = every 15 minutes
0 0 1 * *         = midnight on the 1st of every month
```

### 6.2 The Distributed Cron Problem

In a single-server world, cron runs once on that server. Simple.

In a distributed system with 10 API server replicas, if all 10 run their own cron schedulers, **every cron job runs 10 times** — 10 billing emails, 10 database cleanups, 10 report generations.

```
Server 1: 0 2 * * * → triggers send_monthly_invoices
Server 2: 0 2 * * * → triggers send_monthly_invoices  ← duplicate!
Server 3: 0 2 * * * → triggers send_monthly_invoices  ← duplicate!
...
Server 10: 0 2 * * * → triggers send_monthly_invoices  ← duplicate!
```

### 6.3 Solutions for Distributed Cron

**Solution 1: Dedicated scheduler service (simplest)**
- Run exactly one instance of your scheduler as a separate deployment
- Kubernetes: `replicas: 1` for the scheduler deployment
- Risk: single point of failure

**Solution 2: Redis Distributed Lock**
```
At cron trigger time (all servers attempt this):

SETNX cron:monthly_invoices:2026-06-01 "server-3" EX 3600
  ├── Returns 1 → this server "won", run the job
  └── Returns 0 → another server already running it, skip
```

The lock TTL (3600s = 1hr) should be longer than the job's max duration.

**Solution 3: Leader Election**
- Use Redis, etcd, or Zookeeper for leader election
- Only the elected leader runs cron jobs
- On leader failure, a new leader is elected

**Solution 4: Database-level locking with advisory locks (PostgreSQL)**
```sql
-- All servers attempt to acquire advisory lock with same ID
SELECT pg_try_advisory_lock(hashtext('monthly_invoices'));
  ├── true  → run the job, release lock when done
  └── false → another server has the lock, skip
```

### 6.4 Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: monthly-invoices
spec:
  schedule: "0 2 1 * *"          # 2 AM on the 1st of each month
  concurrencyPolicy: Forbid       # don't start if previous run still active
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: invoice-generator
              image: myapp:latest
              command: ["python", "manage.py", "generate_invoices"]
```

`concurrencyPolicy: Forbid` prevents the distributed duplicate problem when using Kubernetes.

---

## 7. Job Libraries by Stack

### Go

| Library | Backend | Best For | Status |
|---------|---------|----------|--------|
| **asynq** | Redis | General-purpose, production-ready | Very active |
| **river** | PostgreSQL | Already using PG, want transactional enqueue | Active |
| **machinery** | Redis/AMQP | Multi-broker, complex workflows | Mature |
| **temporal** | Temporal server | Long-running, durable workflows | Enterprise |

**asynq** is the de facto standard for Go Redis-backed job queues. Built by Hibiki Saito, used by many companies in production.

### Node.js

| Library | Backend | Best For | Status |
|---------|---------|----------|--------|
| **BullMQ** | Redis | General-purpose, replacement for Bull | Very active |
| **Bull** | Redis | Older, widely deployed | Maintenance mode |
| **bee-queue** | Redis | Simple, high-throughput | Stable |
| **agenda** | MongoDB | Already using Mongo | Moderate |
| **Temporal SDK** | Temporal server | Durable workflows | Active |

**BullMQ** is the modern standard. Built on Redis Streams, supports retries, priorities, delays, repeatable jobs, and has excellent observability via Bull Board.

### Python

| Library | Backend | Best For | Status |
|---------|---------|----------|--------|
| **Celery** | Redis, RabbitMQ | Most mature, most features | Very active |
| **rq (Redis Queue)** | Redis | Simple, low overhead | Active |
| **arq** | Redis | Async (asyncio), clean API | Active |
| **dramatiq** | Redis, RabbitMQ | Better defaults than Celery | Active |
| **Temporal SDK** | Temporal server | Durable workflows | Active |

**Celery** is the industry standard but has sharp edges (result backend config, task serialization, broker connection management). **arq** is excellent for modern async Python codebases.

---

## 8. How It Works Internally

### Redis-Backed Queue Internals (asynq / BullMQ)

```
Redis Key Structure (asynq):
────────────────────────────────────────────────────────
asynq:{queue_name}:pending         ← sorted set (score = enqueue time)
asynq:{queue_name}:active          ← list of currently-processing jobs
asynq:{queue_name}:scheduled       ← sorted set (score = run_at timestamp)
asynq:{queue_name}:retry           ← sorted set (score = retry_at timestamp)
asynq:{queue_name}:completed       ← sorted set (recent completions)
asynq:{queue_name}:dead            ← sorted set (DLQ)
asynq:task:{task_id}               ← hash (full task payload)

Processing Flow:
────────────────────────────────────────────────────────
1. ENQUEUE:
   ZADD asynq:{q}:pending  <score> <task_id>   ← atomic
   HSET asynq:task:{id}    type payload ...

2. DEQUEUE (worker):
   ZRANGEBYSCORE asynq:{q}:pending -inf +inf LIMIT 1  ← get next task
   LMOVE asynq:{q}:pending asynq:{q}:active            ← atomic move

3. HEARTBEAT:
   Worker periodically updates task's "deadline" in Redis
   If deadline passes → task moves back to pending (visibility timeout expired)

4. ACK (success):
   LREM  asynq:{q}:active  1 <task_id>         ← remove from active
   ZADD  asynq:{q}:completed <score> <task_id> ← add to completed

5. NACK (failure):
   LREM  asynq:{q}:active  1 <task_id>
   ZADD  asynq:{q}:retry   <retry_at> <task_id> ← schedule retry
   (if max retries exceeded)
   ZADD  asynq:{q}:dead    <score> <task_id>     ← move to DLQ
```

### Celery Internals (with Redis broker)

```
Producer (API Server)
│
│  apply_async(args, kwargs, queue='emails', countdown=5)
│       ↓
│  Serialize task (pickle / JSON / msgpack)
│  LPUSH kombu.{queue}.{exchange} <serialized_message>
│
▼
Redis Broker (message queue)
│
│  Worker process reads:
│  BRPOP kombu.{queue}.{exchange} 0
│       ↓
│  Deserialize message
│  Dispatch to registered task handler
│
▼
Celery Worker (consumer)
│
│  Executes task function
│  Stores result in result backend (Redis/DB):
│  SET celery-task-meta-{task_id} {status, result}
│
▼
Result Backend (optional — Redis/PostgreSQL/etc.)
```

### BullMQ Internals (Redis Streams)

```
BullMQ uses Redis Streams for at-least-once delivery:

Producer:
  XADD bull:{queue}:events * jobId {id} ...   ← append to stream

Consumer Group:
  XREADGROUP GROUP workers worker1 COUNT 1 STREAMS bull:{queue} >
      ↓
  Returns pending entries (not yet ACKed by any consumer)
  Mark as "claimed" by worker1

On success:
  XACK bull:{queue} workers {message-id}       ← acknowledge

On crash (worker dies):
  Pending entries remain in PEL (Pending Entries List)
  Other workers can XCLAIM entries older than visibility timeout
```

---

## 9. Implementation Examples

### Go + asynq

**Project structure:**
```
├── main.go
├── workers/
│   ├── worker.go        ← worker setup
│   ├── email.go         ← email job handler
│   └── scheduler.go     ← cron jobs
├── tasks/
│   └── tasks.go         ← job type definitions & enqueueing
```

**Task definitions and enqueueing (`tasks/tasks.go`):**
```go
package tasks

import (
    "context"
    "encoding/json"
    "fmt"

    "github.com/hibiken/asynq"
)

// Job type constants — use constants to avoid typos
const (
    TypeEmailWelcome     = "email:welcome"
    TypeEmailPasswordReset = "email:password_reset"
    TypeImageResize      = "image:resize"
    TypeReportGenerate   = "report:generate"
)

// Payload types — strongly typed job payloads
type WelcomeEmailPayload struct {
    UserID    int64  `json:"user_id"`
    Email     string `json:"email"`
    FirstName string `json:"first_name"`
}

type ImageResizePayload struct {
    ImageID   int64  `json:"image_id"`
    SourceURL string `json:"source_url"`
    Width     int    `json:"width"`
    Height    int    `json:"height"`
}

// NewWelcomeEmailTask creates a task to be enqueued
func NewWelcomeEmailTask(userID int64, email, firstName string) (*asynq.Task, error) {
    payload, err := json.Marshal(WelcomeEmailPayload{
        UserID:    userID,
        Email:     email,
        FirstName: firstName,
    })
    if err != nil {
        return nil, fmt.Errorf("marshal welcome email payload: %w", err)
    }
    return asynq.NewTask(TypeEmailWelcome, payload), nil
}

func NewImageResizeTask(imageID int64, sourceURL string, w, h int) (*asynq.Task, error) {
    payload, err := json.Marshal(ImageResizePayload{
        ImageID:   imageID,
        SourceURL: sourceURL,
        Width:     w,
        Height:    h,
    })
    if err != nil {
        return nil, fmt.Errorf("marshal image resize payload: %w", err)
    }
    // Max retries: 5, Timeout: 10 minutes, Queue: critical
    return asynq.NewTask(TypeImageResize, payload,
        asynq.MaxRetry(5),
        asynq.Timeout(10*time.Minute),
        asynq.Queue("critical"),
    ), nil
}
```

**HTTP handler enqueuing a job (`handlers/user.go`):**
```go
package handlers

import (
    "encoding/json"
    "net/http"

    "github.com/hibiken/asynq"
    "myapp/tasks"
)

type UserHandler struct {
    db     *sql.DB
    client *asynq.Client  // asynq producer client
}

func (h *UserHandler) Register(w http.ResponseWriter, r *http.Request) {
    var req RegisterRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "bad request", http.StatusBadRequest)
        return
    }

    // 1. Write to database
    user, err := h.db.CreateUser(r.Context(), req.Email, req.Password)
    if err != nil {
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }

    // 2. Enqueue welcome email (non-blocking, ~1ms)
    task, err := tasks.NewWelcomeEmailTask(user.ID, user.Email, user.FirstName)
    if err != nil {
        // Log but don't fail the request — user was created successfully
        // In production: use outbox pattern to guarantee delivery
        log.Printf("failed to create email task: %v", err)
    } else {
        info, err := h.client.Enqueue(task,
            asynq.Queue("default"),
            asynq.MaxRetry(3),
            // Delay for 5 seconds — lets the DB write propagate to replicas
            asynq.ProcessIn(5*time.Second),
        )
        if err != nil {
            log.Printf("failed to enqueue email task: %v", err)
        } else {
            log.Printf("enqueued task: id=%s queue=%s", info.ID, info.Queue)
        }
    }

    // 3. Return response immediately — don't wait for email
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(user)
}
```

**Worker setup (`workers/worker.go`):**
```go
package workers

import (
    "context"
    "log"
    "os"
    "os/signal"
    "syscall"

    "github.com/hibiken/asynq"
    "myapp/workers/handlers"
)

func StartWorker() {
    redisOpt := asynq.RedisClientOpt{Addr: "localhost:6379"}

    // Worker configuration
    srv := asynq.NewServer(redisOpt, asynq.Config{
        // Number of concurrent workers
        Concurrency: 10,

        // Queue priorities (weighted)
        // critical: 6 workers, default: 3, low: 1
        Queues: map[string]int{
            "critical": 6,
            "default":  3,
            "low":      1,
        },

        // Error handler — called on job failure
        ErrorHandler: asynq.ErrorHandlerFunc(func(ctx context.Context, task *asynq.Task, err error) {
            log.Printf("job failed: type=%s err=%v", task.Type(), err)
            // Send to alerting (PagerDuty, Sentry, etc.)
        }),

        // Logger
        Logger: log.New(os.Stdout, "asynq: ", log.LstdFlags),

        // Retry delay function (exponential backoff with jitter)
        RetryDelayFunc: func(n int, e error, t *asynq.Task) time.Duration {
            base := time.Duration(math.Pow(2, float64(n))) * time.Second
            jitter := time.Duration(rand.Intn(1000)) * time.Millisecond
            return base + jitter
        },
    })

    // Register job handlers
    mux := asynq.NewServeMux()
    mux.HandleFunc(tasks.TypeEmailWelcome, handlers.HandleWelcomeEmail)
    mux.HandleFunc(tasks.TypeEmailPasswordReset, handlers.HandlePasswordResetEmail)
    mux.HandleFunc(tasks.TypeImageResize, handlers.HandleImageResize)

    // Graceful shutdown
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    go func() {
        <-quit
        log.Println("shutting down worker...")
        srv.Shutdown()
    }()

    if err := srv.Run(mux); err != nil {
        log.Fatalf("worker failed: %v", err)
    }
}
```

**Job handler with retry logic (`workers/handlers/email.go`):**
```go
package handlers

import (
    "context"
    "encoding/json"
    "fmt"

    "github.com/hibiken/asynq"
    "myapp/tasks"
)

func HandleWelcomeEmail(ctx context.Context, t *asynq.Task) error {
    var payload tasks.WelcomeEmailPayload
    if err := json.Unmarshal(t.Payload(), &payload); err != nil {
        // Bad payload — permanent failure, don't retry
        return fmt.Errorf("%w: %v", asynq.SkipRetry, err)
    }

    // Check idempotency — prevent duplicate emails
    alreadySent, err := checkIdempotency(ctx, t.ResultWriter(), payload.UserID)
    if err != nil {
        return fmt.Errorf("check idempotency: %w", err)
    }
    if alreadySent {
        return nil // already sent, silently succeed
    }

    // Send the email
    if err := emailService.SendWelcome(ctx, payload.Email, payload.FirstName); err != nil {
        // Transient error — will be retried
        return fmt.Errorf("send welcome email to %s: %w", payload.Email, err)
    }

    // Mark as sent for idempotency
    markIdempotencyKey(ctx, payload.UserID)
    return nil
}
```

**Cron / Scheduled jobs (`workers/scheduler.go`):**
```go
package workers

import (
    "context"
    "fmt"
    "log"

    "github.com/hibiken/asynq"
)

func StartScheduler() {
    redisOpt := asynq.RedisClientOpt{Addr: "localhost:6379"}
    scheduler := asynq.NewScheduler(redisOpt, &asynq.SchedulerOpts{
        // Timezone for cron expressions
        Location: time.UTC,
    })

    // Daily digest email at 9 AM UTC
    entryID, err := scheduler.Register("0 9 * * *",
        asynq.NewTask("email:daily_digest", nil),
        asynq.Queue("low"),
    )
    if err != nil {
        log.Fatalf("register daily digest: %v", err)
    }
    log.Printf("registered daily digest scheduler: id=%s", entryID)

    // Hourly cleanup job
    scheduler.Register("0 * * * *",
        asynq.NewTask("db:cleanup_expired_sessions", nil),
    )

    // Every 15 minutes: process pending webhooks
    scheduler.Register("*/15 * * * *",
        asynq.NewTask("webhook:flush_pending", nil),
    )

    if err := scheduler.Run(); err != nil {
        log.Fatalf("scheduler failed: %v", err)
    }
}
```

**DLQ handler (inspect and requeue dead jobs):**
```go
func InspectDLQ() {
    redisOpt := asynq.RedisClientOpt{Addr: "localhost:6379"}
    inspector := asynq.NewInspector(redisOpt)

    // List dead jobs
    deadTasks, err := inspector.ListDeadTasks("default")
    if err != nil {
        log.Fatal(err)
    }

    for _, task := range deadTasks {
        log.Printf("dead task: id=%s type=%s last_err=%s last_failed=%v retried=%d",
            task.ID, task.Type, task.LastErr, task.LastFailedAt, task.Retried)

        // Optionally requeue after fixing the bug
        // inspector.RunTask("default", task.ID)

        // Or delete permanently
        // inspector.DeleteTask("default", task.ID)
    }
}
```

---

### Node.js + BullMQ

**Setup (`src/queues/index.js`):**
```javascript
import { Queue, Worker, QueueEvents, FlowProducer } from 'bullmq';
import IORedis from 'ioredis';

// Shared Redis connection
const connection = new IORedis({
  host: process.env.REDIS_HOST || 'localhost',
  port: 6379,
  maxRetriesPerRequest: null,  // required by BullMQ
  enableReadyCheck: false,
});

// Queue definitions
export const emailQueue = new Queue('emails', { connection });
export const imageQueue = new Queue('images', { connection, defaultJobOptions: {
  attempts: 5,
  backoff: {
    type: 'exponential',
    delay: 2000,  // starts at 2s, doubles each retry
  },
  removeOnComplete: { count: 100 },  // keep last 100 completed jobs
  removeOnFail: false,               // keep all failed jobs (for DLQ inspection)
}});

// Monitor queue events
const emailQueueEvents = new QueueEvents('emails', { connection });
emailQueueEvents.on('failed', ({ jobId, failedReason }) => {
  console.error(`Job ${jobId} failed: ${failedReason}`);
  // alert to monitoring system
});
emailQueueEvents.on('completed', ({ jobId }) => {
  console.log(`Job ${jobId} completed`);
});
```

**HTTP handler enqueuing a job (`src/routes/users.js`):**
```javascript
import express from 'express';
import { emailQueue, imageQueue } from '../queues/index.js';

const router = express.Router();

router.post('/register', async (req, res) => {
  const { email, firstName, password } = req.body;

  try {
    // 1. Create user in DB
    const user = await db.users.create({ email, firstName, password });

    // 2. Enqueue jobs (non-blocking)
    await Promise.all([
      emailQueue.add('welcome-email', {
        userId: user.id,
        email: user.email,
        firstName: user.firstName,
      }, {
        // Deduplicate: if same jobId already in queue, skip
        jobId: `welcome:${user.id}`,
        delay: 5000,  // wait 5s to let DB replicas catch up
        attempts: 3,
        backoff: { type: 'exponential', delay: 1000 },
      }),
      imageQueue.add('generate-avatar', {
        userId: user.id,
        email: user.email,
      }),
    ]);

    return res.status(201).json({ id: user.id, email: user.email });
  } catch (err) {
    console.error('Registration failed:', err);
    return res.status(500).json({ error: 'Registration failed' });
  }
});

export default router;
```

**Worker with retry and error handling (`src/workers/emailWorker.js`):**
```javascript
import { Worker } from 'bullmq';
import IORedis from 'ioredis';

const connection = new IORedis({ maxRetriesPerRequest: null });

const emailWorker = new Worker('emails', async (job) => {
  console.log(`Processing job ${job.id}: ${job.name}`);

  switch (job.name) {
    case 'welcome-email':
      return await processWelcomeEmail(job.data);
    case 'password-reset':
      return await processPasswordReset(job.data);
    default:
      throw new Error(`Unknown job type: ${job.name}`);
  }
}, {
  connection,
  concurrency: 5,               // process 5 jobs simultaneously
  limiter: {                    // rate limit: max 100 jobs/minute
    max: 100,
    duration: 60 * 1000,
  },
});

async function processWelcomeEmail({ userId, email, firstName }) {
  // Idempotency check
  const alreadySent = await redis.get(`email:welcome:sent:${userId}`);
  if (alreadySent) {
    console.log(`Welcome email already sent to user ${userId}, skipping`);
    return { skipped: true };
  }

  await emailService.send({
    to: email,
    template: 'welcome',
    data: { firstName },
  });

  // Mark as sent (expire after 7 days)
  await redis.setex(`email:welcome:sent:${userId}`, 7 * 24 * 3600, '1');

  return { sent: true, email };
}

// Handle worker-level errors
emailWorker.on('failed', (job, err) => {
  console.error(`Job ${job.id} failed after ${job.attemptsMade} attempts:`, err.message);
  if (job.attemptsMade >= job.opts.attempts) {
    // Max retries exceeded — this job goes to the "failed" state (BullMQ's DLQ)
    console.error(`Job ${job.id} moved to dead letter (failed) queue`);
    // Alert engineering team
    alerting.notify('job_max_retries_exceeded', { jobId: job.id, type: job.name });
  }
});

emailWorker.on('completed', (job, result) => {
  console.log(`Job ${job.id} completed:`, result);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('Shutting down worker gracefully...');
  await emailWorker.close();
  process.exit(0);
});
```

**Repeatable (cron) jobs (`src/schedulers/cronJobs.js`):**
```javascript
import { Queue } from 'bullmq';

async function setupCronJobs() {
  const mainQueue = new Queue('main', { connection });

  // Remove existing repeatable jobs (prevents duplicates on redeploy)
  const repeatableJobs = await mainQueue.getRepeatableJobs();
  for (const job of repeatableJobs) {
    await mainQueue.removeRepeatableByKey(job.key);
  }

  // Daily digest at 9 AM UTC
  await mainQueue.add('daily-digest', {}, {
    repeat: { cron: '0 9 * * *', tz: 'UTC' },
    jobId: 'daily-digest',  // stable ID for deduplication
  });

  // Hourly cleanup
  await mainQueue.add('cleanup-sessions', {}, {
    repeat: { every: 60 * 60 * 1000 },  // every hour in ms
  });

  // Every 15 minutes: flush pending webhooks
  await mainQueue.add('flush-webhooks', {}, {
    repeat: { cron: '*/15 * * * *' },
  });

  console.log('Cron jobs registered');
}

setupCronJobs();
```

**BullMQ Board for monitoring (`src/app.js`):**
```javascript
import { createBullBoard } from '@bull-board/api';
import { BullMQAdapter } from '@bull-board/api/bullMQAdapter.js';
import { ExpressAdapter } from '@bull-board/express';
import { emailQueue, imageQueue } from './queues/index.js';

const serverAdapter = new ExpressAdapter();
serverAdapter.setBasePath('/admin/queues');

createBullBoard({
  queues: [
    new BullMQAdapter(emailQueue),
    new BullMQAdapter(imageQueue),
  ],
  serverAdapter,
});

app.use('/admin/queues', serverAdapter.getRouter());
// Visit http://localhost:3000/admin/queues for a web UI
```

---

### Python + Celery / arq

**Celery setup with Redis (`celery_app.py`):**
```python
import os
from celery import Celery
from kombu import Queue, Exchange

# Create Celery app
celery_app = Celery(
    "myapp",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=["tasks.email", "tasks.image", "tasks.report"],
)

# Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task routing — send to specific queues
    task_routes={
        "tasks.email.*": {"queue": "emails"},
        "tasks.image.*": {"queue": "images"},
        "tasks.report.*": {"queue": "reports"},
    },

    # Queue definitions with priorities
    task_queues=(
        Queue("critical", Exchange("critical"), routing_key="critical"),
        Queue("emails",   Exchange("emails"),   routing_key="emails"),
        Queue("images",   Exchange("images"),   routing_key="images"),
        Queue("reports",  Exchange("reports"),  routing_key="reports"),
        Queue("default",  Exchange("default"),  routing_key="default"),
    ),

    # Default task options
    task_acks_late=True,           # ACK after processing, not before (safer)
    task_reject_on_worker_lost=True,  # requeue if worker dies
    worker_prefetch_multiplier=1,  # don't prefetch more than 1 task per worker
                                   # (prevents one worker hoarding long tasks)

    # Result expiry
    result_expires=3600,  # results expire after 1 hour
)
```

**Task definitions (`tasks/email.py`):**
```python
import logging
import random
from celery import Task
from celery_app import celery_app
from services.email import send_email
from services.redis_client import redis_client

logger = logging.getLogger(__name__)


class IdempotentTask(Task):
    """Base task class with built-in idempotency checking."""

    abstract = True

    def get_idempotency_key(self, *args, **kwargs) -> str:
        raise NotImplementedError

    def is_already_processed(self, *args, **kwargs) -> bool:
        key = self.get_idempotency_key(*args, **kwargs)
        return redis_client.exists(f"task:idempotent:{key}") > 0

    def mark_processed(self, *args, **kwargs) -> None:
        key = self.get_idempotency_key(*args, **kwargs)
        redis_client.setex(f"task:idempotent:{key}", 86400, "1")


@celery_app.task(
    bind=True,
    base=IdempotentTask,
    name="tasks.email.send_welcome",
    max_retries=5,
    default_retry_delay=60,
    queue="emails",
    # Soft time limit: raises SoftTimeLimitExceeded, giving task time to clean up
    soft_time_limit=30,
    # Hard time limit: kills the task worker process
    time_limit=60,
)
def send_welcome_email(self, user_id: int, email: str, first_name: str):
    """Send a welcome email to a newly registered user."""

    # Idempotency check
    if self.is_already_processed(user_id=user_id):
        logger.info(f"Welcome email already sent to user {user_id}, skipping")
        return {"status": "skipped", "reason": "already_sent"}

    try:
        send_email(
            to=email,
            template="welcome",
            context={"first_name": first_name},
        )

        # Mark as processed AFTER successful send
        self.mark_processed(user_id=user_id)
        logger.info(f"Welcome email sent to {email} (user {user_id})")
        return {"status": "sent", "email": email}

    except Exception as exc:
        logger.warning(
            f"Failed to send welcome email (attempt {self.request.retries + 1}/"
            f"{self.max_retries + 1}): {exc}"
        )
        # Exponential backoff with jitter
        delay = min(
            (2 ** self.request.retries) + random.uniform(0, 1),
            3600,  # max delay: 1 hour
        )
        raise self.retry(exc=exc, countdown=delay)


@celery_app.task(
    bind=True,
    name="tasks.email.send_password_reset",
    max_retries=3,
    queue="emails",
)
def send_password_reset_email(self, user_id: int, email: str, reset_token: str):
    """Send password reset email. Has expiry — fail fast if token expired."""
    try:
        # Check token hasn't expired before sending
        if not token_service.is_valid(reset_token):
            logger.warning(f"Password reset token expired for user {user_id}, skipping")
            return {"status": "skipped", "reason": "token_expired"}

        send_email(
            to=email,
            template="password_reset",
            context={"reset_token": reset_token},
        )
        return {"status": "sent"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
```

**FastAPI handler enqueuing Celery tasks:**
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tasks.email import send_welcome_email
from tasks.image import generate_avatar

app = FastAPI()


class RegisterRequest(BaseModel):
    email: str
    first_name: str
    password: str


@app.post("/register", status_code=201)
async def register(request: RegisterRequest):
    # 1. Create user in database
    try:
        user = await db.users.create(
            email=request.email,
            first_name=request.first_name,
            password=hash_password(request.password),
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")

    # 2. Enqueue jobs asynchronously (non-blocking)
    # .delay() is shorthand for .apply_async()
    send_welcome_email.apply_async(
        args=[user.id, user.email, user.first_name],
        queue="emails",
        countdown=5,       # delay 5 seconds
        max_retries=3,
    )

    generate_avatar.apply_async(
        args=[user.id],
        queue="images",
        # Retry with exponential backoff
        retry_policy={
            "max_retries": 5,
            "interval_start": 2,
            "interval_step": 2,
            "interval_max": 3600,
        },
    )

    # 3. Return immediately — don't wait for emails/images
    return {"id": user.id, "email": user.email}
```

**Celery Beat for cron jobs (`celery_beat_schedule.py`):**
```python
from celery.schedules import crontab
from celery_app import celery_app

celery_app.conf.beat_schedule = {
    # Daily digest at 9 AM UTC
    "daily-digest": {
        "task": "tasks.email.send_daily_digest",
        "schedule": crontab(hour=9, minute=0),
        "options": {"queue": "emails"},
    },

    # Hourly cleanup of expired sessions
    "cleanup-sessions": {
        "task": "tasks.db.cleanup_expired_sessions",
        "schedule": crontab(minute=0),  # top of every hour
    },

    # Every 15 minutes: process pending webhooks
    "process-webhooks": {
        "task": "tasks.webhook.flush_pending",
        "schedule": crontab(minute="*/15"),
    },

    # Weekly report every Monday at 8 AM
    "weekly-report": {
        "task": "tasks.report.generate_weekly_summary",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
        "options": {"queue": "reports"},
    },
}

# Start beat: celery -A celery_app beat --loglevel=info
# Start worker: celery -A celery_app worker --queues=emails,images,reports --concurrency=4
```

**arq (async Python alternative — cleaner for FastAPI):**
```python
import asyncio
from arq import create_pool, cron
from arq.connections import RedisSettings


# Task functions (plain async functions)
async def send_welcome_email(ctx, user_id: int, email: str, first_name: str):
    """ctx contains the shared Redis pool and any startup resources."""
    redis = ctx["redis"]

    # Idempotency
    key = f"email:welcome:sent:{user_id}"
    if await redis.exists(key):
        return {"status": "skipped"}

    await ctx["email_service"].send(email, "welcome", {"first_name": first_name})
    await redis.setex(key, 86400, "1")
    return {"status": "sent"}


async def generate_monthly_report(ctx):
    """Called by cron scheduler."""
    report = await ctx["db"].generate_report()
    await ctx["storage"].upload(report)
    return {"rows": len(report)}


# Worker class definition
class WorkerSettings:
    functions = [send_welcome_email, generate_monthly_report]
    redis_settings = RedisSettings()

    cron_jobs = [
        cron(generate_monthly_report, hour=2, minute=0),  # 2 AM daily
    ]

    # Retry settings
    max_tries = 5
    job_timeout = 300  # 5 minutes

    # Called on worker startup — connect to shared resources
    async def on_startup(ctx):
        ctx["db"] = await create_db_pool()
        ctx["email_service"] = EmailService()

    async def on_shutdown(ctx):
        await ctx["db"].close()


# FastAPI integration
async def lifespan(app: FastAPI):
    app.state.arq_pool = await create_pool(RedisSettings())
    yield
    await app.state.arq_pool.close()


@app.post("/register", status_code=201)
async def register(request: RegisterRequest, req: Request):
    user = await db.users.create(...)

    # Enqueue with arq
    await req.app.state.arq_pool.enqueue_job(
        "send_welcome_email",
        user.id, user.email, user.first_name,
        _defer_by=5,   # delay 5 seconds
    )

    return {"id": user.id}
```

---

## 10. Monitoring & Observability

### Key Metrics to Track

**Queue Depth (most important)**
```
ALERT: queue_depth{queue="emails"} > 1000
ALERT: queue_depth{queue="critical"} > 10  ← stricter for critical queue
```

Growing queue depth = workers not keeping up = jobs lagging = user impact.

**Job Processing Rate**
```
jobs_processed_total{queue="emails", status="success"}
jobs_processed_total{queue="emails", status="failed"}

Rate of failure / rate of success = error rate
Alert if error_rate > 5% over 5 minutes
```

**DLQ Depth**
```
ALERT: dlq_depth{queue="emails"} > 0  ← any DLQ messages warrant investigation
```

DLQ messages mean jobs have permanently failed. This is always an alert.

**Job Execution Duration**
```
histogram_quantile(0.95, job_duration_seconds{queue="emails"})
```

P95 latency tells you if jobs are running slowly (resource contention, slow external calls).

**Worker Concurrency Saturation**
```
workers_active / workers_total > 0.9  ← approaching saturation, scale up
```

### Prometheus Metrics (Go example with asynq)

```go
// asynq has built-in Prometheus integration
import "github.com/hibiken/asynq/x/metrics"

// Register asynq metrics with Prometheus
if err := metrics.Register(prometheus.DefaultRegisterer,
    asynq.NewInspector(redisOpt)); err != nil {
    log.Fatal(err)
}

// Exposes:
// asynq_queue_size{queue="default"}
// asynq_queue_latency_seconds{queue="default"}
// asynq_tasks_active_total{queue="default"}
// asynq_tasks_failed_total{queue="default"}
```

### Alerting Rules (Grafana/Prometheus)

```yaml
groups:
  - name: job_queue_alerts
    rules:
      - alert: QueueDepthHigh
        expr: asynq_queue_size{queue!="low"} > 500
        for: 5m
        annotations:
          summary: "Queue {{ $labels.queue }} has {{ $value }} pending jobs"

      - alert: DLQHasMessages
        expr: asynq_tasks_failed_total > 0
        for: 1m
        annotations:
          summary: "Dead letter queue has failed jobs — investigate"

      - alert: WorkerProcessingSlowly
        expr: histogram_quantile(0.95, asynq_task_processing_duration_seconds) > 30
        for: 10m
        annotations:
          summary: "P95 job processing time exceeds 30s"

      - alert: HighJobFailureRate
        expr: rate(asynq_tasks_failed_total[5m]) / rate(asynq_tasks_processed_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "Job failure rate exceeds 5%"
```

---

## 11. Common Patterns & Best Practices

### Pattern 1: Job Chaining

Process a sequence of dependent steps as separate jobs:
```
UploadImage job
  → on success: enqueue ResizeImage job
    → on success: enqueue UpdateUserAvatar job
      → on success: enqueue NotifyUser job
```

This makes each step independently retryable and observable.

### Pattern 2: Fan-Out

One job spawns multiple parallel jobs:
```python
@celery_app.task
def process_order(order_id: int):
    order = db.get_order(order_id)

    # Spawn parallel jobs
    group(
        capture_payment.s(order.payment_id),
        update_inventory.s(order.items),
        send_confirmation_email.s(order.user_id),
        notify_warehouse.s(order.items),
        record_analytics.s(order_id),
    ).apply_async()
```

Celery `group` runs all tasks in parallel.

### Pattern 3: Batch Processing

Instead of one job per record, batch for efficiency:
```go
// Instead of: enqueue 10,000 individual jobs
// Do: enqueue batches of 100

func EnqueueEmailBatch(userIDs []int64) {
    batchSize := 100
    for i := 0; i < len(userIDs); i += batchSize {
        end := min(i+batchSize, len(userIDs))
        batch := userIDs[i:end]

        task := NewEmailBatchTask(batch)
        client.Enqueue(task)
    }
}
```

### Pattern 4: Outbox Pattern (Transactional Enqueue)

Guarantee exactly-once job creation with DB transactions:
```sql
-- Atomic: create order AND record the job to be dispatched
BEGIN;
  INSERT INTO orders (...) VALUES (...) RETURNING id INTO order_id;
  INSERT INTO job_outbox (type, payload, status)
    VALUES ('process_order', json_build_object('order_id', order_id), 'pending');
COMMIT;

-- Separate background process polls outbox and dispatches to Redis
-- This avoids: write to DB succeeded, crash before enqueue to Redis
```

### Pattern 5: Priority Queues

Don't mix critical and background work in one queue:
```
Queue: critical (concurrency: 8)
  └── password_reset_email, payment_failure_alert

Queue: default (concurrency: 4)
  └── welcome_email, notification

Queue: low (concurrency: 2)
  └── weekly_digest, analytics_event, audit_log
```

---

## 12. Common Pitfalls

### Pitfall 1: Processing Work Inline That Should Be Async
```go
// BAD: making user wait 3 seconds for email
func Register(w http.ResponseWriter, r *http.Request) {
    user := createUser(r)
    sendWelcomeEmail(user)  // 2-3 seconds, user is waiting
    w.WriteHeader(201)
}

// GOOD: enqueue and return immediately
func Register(w http.ResponseWriter, r *http.Request) {
    user := createUser(r)
    enqueueWelcomeEmail(user)  // 1-2ms
    w.WriteHeader(201)
}
```

### Pitfall 2: Not Designing for Idempotency
Retries happen. Network partitions happen. Always ask: "If this job runs twice, is that safe?"

### Pitfall 3: Setting Visibility Timeout Too Short
If your job takes 5 minutes but your visibility timeout is 30 seconds, the job will be picked up by another worker while still being processed. Set timeout to 2x the expected job duration.

### Pitfall 4: Running Cron on Every Server Instance
Without distributed locking, `n` servers = `n` duplicate job executions. Use Redis lock, leader election, or Kubernetes CronJob.

### Pitfall 5: Silently Swallowing Errors
```python
# BAD: job "succeeds" even though email failed
@celery_app.task
def send_email(user_id):
    try:
        email_service.send(...)
    except Exception:
        pass  # ← never retry, never alert, silent failure

# GOOD: propagate errors so Celery handles retry
@celery_app.task
def send_email(user_id):
    email_service.send(...)  # let exception propagate → automatic retry
```

### Pitfall 6: No DLQ Monitoring
DLQ jobs are silent failures. If you don't alert on DLQ depth, you'll never know jobs are permanently failing.

### Pitfall 7: Not Using `task_acks_late` in Celery
Default Celery behavior: ACK the task before processing. If the worker dies mid-processing, the job is lost.

```python
# In celery config:
task_acks_late = True  # ACK after processing
worker_prefetch_multiplier = 1  # don't prefetch > 1 task
```

### Pitfall 8: Unbounded Queue Growth
If your consumers are slower than your producers, the queue depth grows unboundedly. This causes memory exhaustion in Redis and increasing job lag. Monitor queue depth and scale workers when needed.

---

## 13. Interview Questions

**Q: Why would you use a job queue instead of processing inline in the API handler?**

A: Three reasons. First, user experience — slow operations (email, image processing, reports) block the HTTP response; queuing lets you return in milliseconds. Second, reliability — inline failures fail the whole request, while queue workers can retry with backoff without the user retrying. Third, rate control — you can enqueue bursts and process at a steady rate, preventing overload of downstream services.

---

**Q: How do you prevent a job from being processed twice?**

A: You design for at-least-once delivery plus idempotent handlers. True exactly-once processing is impossible in distributed systems. The pattern is: include an idempotency key in the job payload, check if it's already been processed at the start of the handler (using a Redis SETNX or a DB unique constraint), and only mark it processed after successful completion. This way, a retry on a job that already succeeded does nothing.

---

**Q: What happens when a worker dies while processing a job?**

A: The job's visibility timeout expires, and the queue backend makes the job visible again for another worker to pick up. This is why at-least-once delivery is the guarantee, not exactly-once — the job will run again. The original worker's processing is abandoned. To handle this safely, job handlers must be idempotent.

---

**Q: What is a visibility timeout in job queues?**

A: When a worker dequeues a job, the job is "locked" — made invisible to other workers — for a configurable duration called the visibility timeout. The worker must either complete the job (ACK it) or extend the lock before the timeout expires. If the timeout expires without an ACK (e.g., worker crashed), the job becomes visible again and another worker can pick it up. In AWS SQS this is called VisibilityTimeout; in asynq, workers send heartbeats to extend the lock.

---

**Q: How do you ensure only one instance runs a cron job in a distributed system?**

A: Several options: (1) Redis distributed lock — use SETNX with a TTL longer than the job duration; only the server that acquires the lock runs the job. (2) Dedicated scheduler service — run one instance of your scheduler pod with `replicas: 1`. (3) Kubernetes CronJob with `concurrencyPolicy: Forbid`. (4) Database advisory locks (PostgreSQL `pg_try_advisory_lock`). The Redis lock is the most common in practice.

---

**Q: What should trigger an alert on a job queue?**

A: Four critical alerts: (1) Queue depth growing — workers can't keep up, jobs are lagging. (2) DLQ has any messages — jobs have permanently failed after all retries, requires investigation. (3) High job failure rate — more than 5-10% of jobs failing suggests a systemic bug or downstream dependency issue. (4) P95 job processing time exceeding expected duration — workers are running slowly, possibly due to resource contention or slow external calls.

---

**Q: What is the difference between Celery and asynq?**

A: Celery is the Python standard — multi-broker (Redis, RabbitMQ, SQS), very mature, extensive ecosystem, but has a steeper configuration curve and some footguns (ACK semantics, serialization). asynq is Go-specific, backed only by Redis, with a cleaner API and excellent observability tooling. The key architectural difference: asynq uses Redis Sorted Sets for scheduling and a heartbeat mechanism for visibility timeouts; Celery uses the broker's native messaging primitives. For Python async codebases, arq is a cleaner alternative to Celery.

---

**Q: What is the outbox pattern and when do you need it?**

A: The outbox pattern solves the dual-write problem: when you need to write to a database AND enqueue a job, and you can't afford to lose either. Without it, if you write to DB then crash before enqueuing, the job is silently lost. The pattern: wrap both writes in one DB transaction — write the main record AND write a "pending outbox" record. A separate background process polls the outbox table, dispatches jobs to Redis, and marks them as dispatched. This guarantees at-least-once job creation with the DB write.

---

## 14. Resources

- [asynq GitHub](https://github.com/hibiken/asynq) — Go Redis task queue
- [BullMQ Documentation](https://docs.bullmq.io/) — Node.js task queue
- [Celery Documentation](https://docs.celeryq.dev/) — Python task queue
- [arq Documentation](https://arq-docs.helpmanual.io/) — Async Python task queue
- [AWS: Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) — Definitive article on retry strategies
- [Temporal Documentation](https://docs.temporal.io/) — Durable workflow engine
- [Transactional Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html) — Reliable event publishing
- [Sidekiq Best Practices](https://github.com/mperham/sidekiq/wiki/Best-Practices) — Ruby but principles apply universally

---

**Next:** [Part 17.2: WebSockets, Server-Sent Events & File Streaming](./17-websockets-realtime-streaming.md)
