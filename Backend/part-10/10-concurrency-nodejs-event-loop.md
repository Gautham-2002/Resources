# Part 10.2: Node.js Concurrency — Event Loop & Runtime

## What You'll Learn
- How Node.js achieves concurrency with a single JavaScript thread
- V8 engine, libuv, and the thread pool — what each layer does
- The event loop phases in exact detail — timers, poll, check, close callbacks
- process.nextTick vs setImmediate vs Promises — precise execution ordering
- Why blocking the event loop is catastrophic and how to fix it
- Worker threads for CPU-bound work — SharedArrayBuffer, MessageChannel
- Cluster module — multi-process scaling, IPC, load balancing
- Promise semantics: Promise.all, allSettled, race, any — real differences
- Full code: worker threads, cluster setup, event loop ordering demonstration

## Table of Contents
1. [Node.js Runtime Architecture](#nodejs-runtime-architecture)
2. [The V8 Engine](#the-v8-engine)
3. [libuv and the Thread Pool](#libuv-and-the-thread-pool)
4. [The Event Loop — Detailed Phases](#the-event-loop--detailed-phases)
5. [process.nextTick vs setImmediate](#processnexttick-vs-setimmediate)
6. [Microtask Queue — Promises](#microtask-queue--promises)
7. [Execution Order — The Full Picture](#execution-order--the-full-picture)
8. [Blocking the Event Loop](#blocking-the-event-loop)
9. [Worker Threads](#worker-threads)
10. [The Cluster Module](#the-cluster-module)
11. [Promise Combinators](#promise-combinators)
12. [Async Iterators and Streams](#async-iterators-and-streams)
13. [Implementation Examples](#implementation-examples)
14. [Common Patterns & Best Practices](#common-patterns--best-practices)
15. [Common Pitfalls](#common-pitfalls)
16. [Interview Questions](#interview-questions)
17. [Resources](#resources)

---

## Node.js Runtime Architecture

Node.js is often called "single-threaded" — this is partially true. JavaScript executes on a **single thread**, but many Node.js operations run on separate threads managed by libuv.

```
Node.js Architecture:

┌─────────────────────────────────────────────────────────────┐
│                    Your Application Code                     │
│                   (JavaScript / TypeScript)                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    Node.js Bindings                          │
│              (C++ bridge between JS and native)              │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
┌──────────▼──────────┐      ┌────────────▼────────────────┐
│      V8 Engine       │      │          libuv              │
│  (JavaScript VM)    │      │  (event loop + I/O + pool)  │
│                     │      │                             │
│  - JIT compilation  │      │  - Event loop (main thread) │
│  - Garbage collect  │      │  - Thread pool (4 threads)  │
│  - Heap management  │      │  - Timers                   │
│  - Call stack       │      │  - Network I/O (epoll/kqueue)│
└─────────────────────┘      └─────────────────────────────┘
```

The key insight: **JavaScript code runs on one thread**. But waiting (for disk, network, DNS) happens on libuv's threads or via OS async I/O. When the wait completes, libuv queues a callback for the JavaScript thread to execute.

This means Node.js can handle thousands of concurrent connections with one thread — it's always doing *something* (running JS), never *waiting* (I/O happens in the background).

---

## The V8 Engine

V8 is Google's open-source JavaScript engine (also used in Chrome). It:
- **Compiles JavaScript to native machine code** via JIT (Just-In-Time) compilation — not interpreted
- Manages the **call stack** (where synchronous JS execution happens)
- Manages the **heap** (where objects are allocated)
- Runs the **garbage collector** (mark-and-sweep, generational)

```
V8 Call Stack:

function c() { ... }
function b() { c() }
function a() { b() }
a()

Call stack:
  [a]          ← a is called first
  [a → b]      ← a calls b
  [a → b → c]  ← b calls c
  [a → b]      ← c returns
  [a]          ← b returns
  []           ← a returns, stack empty

The event loop only runs callbacks when the call stack is EMPTY.
Long-running synchronous code blocks the entire event loop.
```

### What V8 Does NOT Handle

V8 is a pure JavaScript engine. It has no concept of:
- File system access
- Network I/O
- Timers (setTimeout)
- DNS resolution

These are provided by Node.js via libuv and native bindings.

---

## libuv and the Thread Pool

**libuv** is the C library that powers Node.js's non-blocking I/O. It provides:

### The Event Loop (single-threaded)

The event loop is the central coordinator. It runs on the **same thread as JavaScript**. It polls for I/O events and dispatches callbacks.

```
libuv event loop (runs on JS thread):
- "What I/O is ready?"
- "What timers have fired?"
- "Run the callbacks for ready events"
- Repeat
```

### The Thread Pool (multi-threaded)

For operations that don't have async OS support, libuv uses a **thread pool** (default: 4 threads). Operations that run in the thread pool:
- **File system**: `fs.readFile`, `fs.writeFile`, `fs.stat`, etc.
- **DNS**: `dns.lookup` (but NOT `dns.resolve` — that uses async OS API)
- **Crypto**: `crypto.pbkdf2`, `crypto.randomBytes`, `crypto.scrypt`
- **Compression**: `zlib` operations
- **User-defined**: native addons using `uv_queue_work`

```
Thread Pool in Action:

JS Thread:            fs.readFile('data.json', callback)
                            │
                            ▼
                    libuv queues task to thread pool
                            │
Thread pool:         Thread 1 → reads file from disk (blocking OS call)
                            │
                    (JS thread continues running other code)
                            │
Thread 1 done:       callback queued in event loop
                            │
JS Thread:           event loop picks up callback → executes it
```

### Why 4 Threads?

The default of 4 thread pool threads is tunable via `UV_THREADPOOL_SIZE` (max 1024). If your app does heavy crypto, file I/O, or DNS lookups concurrently, increase this:

```bash
UV_THREADPOOL_SIZE=16 node app.js
```

**Important**: Network I/O (TCP, HTTP, sockets) does NOT use the thread pool — it uses OS-level async I/O (epoll on Linux, kqueue on macOS, IOCP on Windows). This is why Node.js handles thousands of concurrent connections efficiently: network I/O is truly non-blocking at the OS level, not merely offloaded to threads.

---

## The Event Loop — Detailed Phases

The event loop has 6 phases that execute in a fixed order. Each phase has its own callback queue. The loop runs phases in order, processing each queue until it's empty or the per-phase maximum is reached.

```
   ┌───────────────────────────────────────────────────────┐
┌─>│  1. timers                                            │
│  │     setTimeout(fn, 0), setInterval callbacks          │
│  └───────────────────────┬───────────────────────────────┘
│  ┌───────────────────────▼───────────────────────────────┐
│  │  2. pending callbacks                                 │
│  │     I/O callbacks deferred to next loop               │
│  │     (e.g., TCP errors reported by OS)                 │
│  └───────────────────────┬───────────────────────────────┘
│  ┌───────────────────────▼───────────────────────────────┐
│  │  3. idle, prepare                                     │
│  │     Internal use only (libuv internals)               │
│  └───────────────────────┬───────────────────────────────┘
│  ┌───────────────────────▼───────────────────────────────┐
│  │  4. poll                    ← WHERE MOST WORK HAPPENS │
│  │     Retrieve new I/O events                           │
│  │     Execute I/O callbacks (fs, net, etc.)             │
│  │     Block here waiting for I/O if no timers pending   │
│  └───────────────────────┬───────────────────────────────┘
│  ┌───────────────────────▼───────────────────────────────┐
│  │  5. check                                             │
│  │     setImmediate callbacks                            │
│  └───────────────────────┬───────────────────────────────┘
│  ┌───────────────────────▼───────────────────────────────┐
└──┤  6. close callbacks                                   │
   │     socket.on('close'), stream.on('close')            │
   └───────────────────────────────────────────────────────┘
```

### Phase 1: Timers

Executes callbacks scheduled by `setTimeout()` and `setInterval()` that have reached their threshold. The timer's delay is a **minimum time** — callbacks may run later if the event loop is busy processing I/O.

```javascript
setTimeout(() => console.log('timer 1'), 0);
setTimeout(() => console.log('timer 2'), 0);
// These run in Phase 1 of the next event loop iteration
```

### Phase 2: Pending Callbacks

I/O callbacks that were deferred to the next iteration. Rare — typically TCP error callbacks that the OS reported.

### Phase 3: Idle, Prepare

Internal to libuv. Not accessible from JavaScript.

### Phase 4: Poll — The Heart of Node.js

This is where Node.js spends most of its time:

1. **Process I/O callbacks**: Execute callbacks for completed I/O operations (file reads, network responses)
2. **Wait for I/O**: If no timers are pending, block here waiting for I/O events
3. **Limit**: Won't block if `setImmediate` callbacks are pending or timers are past their delay

```
Poll phase behavior:

If poll queue is non-empty:
  → Execute all callbacks in poll queue synchronously, until empty or system limit

If poll queue is empty:
  If setImmediate() was called:
    → End poll phase, move to check phase
  If no setImmediate() but timers are pending:
    → Wait until earliest timer threshold, then move to timers phase
  If no setImmediate() and no timers:
    → Block indefinitely until I/O event arrives
```

### Phase 5: Check

Executes `setImmediate()` callbacks. Always runs after the poll phase on the current iteration.

### Phase 6: Close Callbacks

Callbacks for abruptly closed resources:
```javascript
socket.destroy();
socket.on('close', () => console.log('socket closed'));  // fires here
```

---

## process.nextTick vs setImmediate

### process.nextTick

`process.nextTick` callbacks are NOT part of the event loop phases. They execute **after the current operation completes but before the event loop continues to the next phase** — at the end of the current "tick".

The nextTick queue is processed to completion before the event loop moves on. This means you can starve the event loop with recursive `process.nextTick` calls.

```javascript
// nextTick fires before the event loop's next phase
setTimeout(() => console.log('timeout'), 0);
setImmediate(() => console.log('immediate'));
process.nextTick(() => console.log('nextTick'));

// Output (always):
// nextTick    ← fires before event loop proceeds to timers phase
// timeout     ← phase 1
// immediate   ← phase 5
```

### setImmediate

`setImmediate` fires in the **check phase** — after the poll phase on the current event loop iteration.

### setTimeout(fn, 0) vs setImmediate

When called from the **main module** (outside I/O callbacks):
```javascript
// Order is NOT deterministic — depends on OS timer precision
setTimeout(() => console.log('timeout'), 0);
setImmediate(() => console.log('immediate'));
// May print: timeout then immediate, OR immediate then timeout
```

When called from **within an I/O callback**:
```javascript
const fs = require('fs');
fs.readFile('/etc/hosts', () => {
    // Inside poll phase callback — setImmediate ALWAYS fires before setTimeout here
    setTimeout(() => console.log('timeout'), 0);
    setImmediate(() => console.log('immediate'));
    // Always: immediate (check phase) then timeout (timers phase, next iteration)
});
```

### When to Use Each

| | `process.nextTick` | `setImmediate` |
|---|---|---|
| **When fires** | Before next event loop phase | After poll phase (check phase) |
| **Use case** | Error handling, ensure async behavior | Compute after I/O, break up long sync work |
| **Risk** | Can starve I/O if used recursively | Cannot starve event loop |
| **Preferred** | For user-facing async APIs | For deferring compute work |

```javascript
// Good use of nextTick: ensure callback is async even if condition is sync
function readData(file, callback) {
    if (cache.has(file)) {
        // Without nextTick: callback called synchronously — confusing API behavior
        process.nextTick(() => callback(null, cache.get(file)));
        return;
    }
    fs.readFile(file, callback);
}
```

---

## Microtask Queue — Promises

Promises and `queueMicrotask` use the **microtask queue**, which is separate from the event loop phases and separate from the nextTick queue.

### Execution Order Within a Phase

After each callback in an event loop phase (and after each nextTick queue drain), the microtask queue is fully drained.

```
Execution order within a single phase:

1. Execute current task (callback in event loop phase)
2. Drain nextTick queue completely
3. Drain microtask queue (Promises) completely
4. Back to step 1 (next task in current phase)
```

```javascript
Promise.resolve().then(() => console.log('microtask 1'));
process.nextTick(() => console.log('nextTick 1'));
Promise.resolve().then(() => console.log('microtask 2'));
process.nextTick(() => console.log('nextTick 2'));

// Output (Node.js v11+):
// nextTick 1    ← nextTick queue drains first
// nextTick 2
// microtask 1   ← then microtask (Promise) queue
// microtask 2
```

**Node.js v11+ change**: In Node.js v11+, microtasks drain between each callback in a phase (same behavior as browsers). In v10 and earlier, microtasks only drained between phases.

### Async/Await and the Event Loop

`async/await` is syntactic sugar over Promises. Every `await` expression:
1. Suspends the current async function
2. Queues the continuation as a microtask
3. Returns control to the event loop (or the calling code)

```javascript
async function example() {
    console.log('1 - before await');
    await Promise.resolve();
    console.log('3 - after await (microtask)');
}

console.log('start');
example();
console.log('2 - sync continues');

// Output:
// start
// 1 - before await
// 2 - sync continues   ← event loop is free here
// 3 - after await      ← microtask, runs when call stack is clear
```

---

## Blocking the Event Loop

The most critical Node.js performance concept: **any synchronous operation that takes a long time blocks ALL requests**.

```
Blocked event loop:

Request 1 arrives → starts JSON.parse(largePayload) [takes 500ms]
Request 2 arrives → WAITS (event loop is occupied with Request 1)
Request 3 arrives → WAITS
...
Request 1000 arrives → WAITS

Response times: 500ms, 1000ms, 1500ms... instead of ~1ms
```

### What Blocks the Event Loop

**1. CPU-intensive JavaScript**
```javascript
// Bad: blocks event loop for duration of sort
app.get('/sort', (req, res) => {
    const sorted = hugeArray.sort(); // O(n log n) on millions of items = seconds
    res.json(sorted);
});

// Bad: regex backtracking (ReDoS attack vector)
app.post('/validate', (req, res) => {
    const match = /^(a+)+$/.test(req.body.input); // catastrophic backtracking
    res.json({ valid: match });
});
```

**2. Synchronous I/O**
```javascript
// Bad: synchronous file read — blocks entire event loop while disk reads
const data = fs.readFileSync('/large/file.json');
const parsed = JSON.parse(data);

// Good: async
const data = await fs.promises.readFile('/large/file.json');
```

**3. Large JSON operations**
```javascript
// Blocking: JSON.parse on a 100MB payload takes ~2 seconds
const obj = JSON.parse(veryLargeString);

// Mitigation: stream parsing (simdjson, JSONStream)
// or offload to worker thread
```

**4. Heavy cryptography (without thread pool)**
```javascript
// Bad: sync crypto blocks
const hash = crypto.createHash('sha256').update(data).digest('hex');

// Good: async (uses thread pool, doesn't block event loop)
const { subtle } = require('crypto').webcrypto;
const hash = await subtle.digest('SHA-256', buffer);
```

### Detecting Event Loop Lag

```javascript
// Measure event loop lag (how long between event loop ticks)
let lastCheck = Date.now();
setInterval(() => {
    const now = Date.now();
    const lag = now - lastCheck - 1000; // expected 1000ms gap
    if (lag > 100) {
        console.warn(`Event loop lag: ${lag}ms`);
    }
    lastCheck = now;
}, 1000);

// Better: use clinic.js or 0x for profiling
// npm install -g clinic
// clinic doctor -- node app.js
```

---

## Worker Threads

`worker_threads` module (Node.js 12+, stable) creates actual OS threads for CPU-bound work. Workers run JavaScript but have separate V8 instances and separate heaps.

```
Worker Threads Architecture:

Main Thread (Event Loop)          Worker Thread 1
┌──────────────────────┐         ┌────────────────────────┐
│  JavaScript Runtime  │         │  JavaScript Runtime     │
│  V8 Instance         │         │  V8 Instance (separate) │
│  Event Loop          │◄──IPC──►│  Event Loop             │
│                      │         │                         │
│  Handle HTTP reqs    │         │  CPU-bound processing   │
│  Manage workers      │         │  (doesn't block main)  │
└──────────────────────┘         └────────────────────────┘

Communication: MessageChannel (structured clone, or SharedArrayBuffer)
```

### Basic Worker Thread

```javascript
// worker.js — the worker code
const { workerData, parentPort } = require('worker_threads');

// Receive data from main thread
const { numbers } = workerData;

// CPU-intensive work (won't block main thread's event loop)
const result = numbers.reduce((sum, n) => sum + (n * n), 0);

// Send result back to main thread
parentPort.postMessage({ result });
```

```javascript
// main.js
const { Worker } = require('worker_threads');
const path = require('path');

function runWorker(workerData) {
    return new Promise((resolve, reject) => {
        const worker = new Worker(path.join(__dirname, 'worker.js'), {
            workerData,
        });
        
        worker.on('message', resolve);        // worker sent result
        worker.on('error', reject);            // worker threw an error
        worker.on('exit', (code) => {
            if (code !== 0) {
                reject(new Error(`Worker exited with code ${code}`));
            }
        });
    });
}

// Usage in Express route
app.post('/compute', async (req, res) => {
    try {
        const { result } = await runWorker({ numbers: req.body.numbers });
        res.json({ result });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});
```

### SharedArrayBuffer — Zero-Copy Shared Memory

For high-performance scenarios, share memory between main thread and workers without copying:

```javascript
// main.js — share array buffer with worker
const { Worker } = require('worker_threads');
const path = require('path');

const sharedBuffer = new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT * 1000000);
const sharedArray = new Int32Array(sharedBuffer);

// Fill with data
for (let i = 0; i < sharedArray.length; i++) sharedArray[i] = i;

const worker = new Worker(path.join(__dirname, 'sharedWorker.js'), {
    workerData: { sharedBuffer }, // buffer is SHARED, not copied
});

worker.on('message', (msg) => {
    if (msg.done) {
        console.log('Sum:', sharedArray[0]); // worker wrote result to index 0
    }
});
```

```javascript
// sharedWorker.js
const { workerData, parentPort } = require('worker_threads');
const sharedArray = new Int32Array(workerData.sharedBuffer);

let sum = 0;
for (let i = 1; i < sharedArray.length; i++) {
    sum += sharedArray[i];
}
Atomics.store(sharedArray, 0, sum); // atomic write to shared memory
parentPort.postMessage({ done: true });
```

### Worker Thread Pool

Creating workers has overhead (~50-100ms). Use a pool of pre-warmed workers:

```javascript
const { Worker, isMainThread, workerData, parentPort } = require('worker_threads');
const os = require('os');

// Simple worker pool
class WorkerPool {
    constructor(workerScript, size = os.cpus().length) {
        this.workerScript = workerScript;
        this.size = size;
        this.workers = [];
        this.queue = [];
        
        for (let i = 0; i < size; i++) {
            this._addWorker();
        }
    }
    
    _addWorker() {
        const worker = new Worker(this.workerScript);
        worker.isIdle = true;
        
        worker.on('message', (result) => {
            worker.isIdle = true;
            if (worker._resolve) {
                worker._resolve(result);
                worker._resolve = null;
            }
            this._processQueue();
        });
        
        worker.on('error', (err) => {
            if (worker._reject) {
                worker._reject(err);
                worker._reject = null;
            }
            // Replace crashed worker
            this.workers = this.workers.filter(w => w !== worker);
            this._addWorker();
        });
        
        this.workers.push(worker);
    }
    
    _processQueue() {
        if (this.queue.length === 0) return;
        
        const idleWorker = this.workers.find(w => w.isIdle);
        if (!idleWorker) return;
        
        const { data, resolve, reject } = this.queue.shift();
        idleWorker.isIdle = false;
        idleWorker._resolve = resolve;
        idleWorker._reject = reject;
        idleWorker.postMessage(data);
    }
    
    run(data) {
        return new Promise((resolve, reject) => {
            this.queue.push({ data, resolve, reject });
            this._processQueue();
        });
    }
}

const pool = new WorkerPool('./computeWorker.js');

app.post('/heavy-compute', async (req, res) => {
    const result = await pool.run(req.body);
    res.json(result);
});
```

---

## The Cluster Module

The `cluster` module allows running multiple Node.js processes (workers), each with its own event loop, that share a TCP port. This scales across CPU cores.

```
Cluster Architecture:

┌────────────────────────────────────────────┐
│            Master Process                   │
│  - Manages worker processes                 │
│  - Forks workers (one per CPU core)         │
│  - Handles worker crashes (restarts them)   │
│  - Routes incoming connections to workers  │
└──────┬──────────────────────────────────────┘
       │  fork()
       ├────────────────────────────────────────
       │              │              │
┌──────▼──────┐ ┌─────▼───────┐ ┌───▼─────────┐
│  Worker 1   │ │  Worker 2   │ │  Worker 3   │
│  (Event loop│ │  (Event loop│ │  (Event loop│
│   + Express)│ │   + Express)│ │   + Express)│
│  Port: 8080 │ │  Port: 8080 │ │  Port: 8080 │
│  (shared)   │ │  (shared)   │ │  (shared)   │
└─────────────┘ └─────────────┘ └─────────────┘
```

### Cluster Setup

```javascript
const cluster = require('cluster');
const http = require('http');
const os = require('os');
const process = require('process');

const numCPUs = os.cpus().length;

if (cluster.isPrimary) {
    console.log(`Primary ${process.pid} is running`);
    console.log(`Forking ${numCPUs} workers...`);
    
    // Fork one worker per CPU
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }
    
    // Restart workers on crash
    cluster.on('exit', (worker, code, signal) => {
        console.log(`Worker ${worker.process.pid} died (${signal || code}). Restarting...`);
        cluster.fork();
    });
    
    // IPC: receive messages from workers
    for (const id in cluster.workers) {
        cluster.workers[id].on('message', (msg) => {
            console.log('Master received:', msg);
            // Broadcast to all workers
            for (const workerId in cluster.workers) {
                cluster.workers[workerId].send({ type: 'broadcast', data: msg });
            }
        });
    }
    
} else {
    // Worker process: each runs its own HTTP server
    const express = require('express');
    const app = express();
    
    app.get('/health', (req, res) => {
        res.json({ pid: process.pid, status: 'ok' });
    });
    
    app.get('/cpu-info', (req, res) => {
        // Each request handled by a different worker (round-robin by default)
        res.json({
            worker: process.pid,
            cpus: os.cpus().length,
        });
    });
    
    // IPC: receive messages from master
    process.on('message', (msg) => {
        if (msg.type === 'broadcast') {
            console.log(`Worker ${process.pid} received broadcast:`, msg.data);
        }
    });
    
    // All workers share port 8080 (SO_REUSEPORT or master proxying)
    app.listen(8080, () => {
        console.log(`Worker ${process.pid} started`);
    });
}
```

### Cluster vs PM2 vs Container Scaling

| | `cluster` module | PM2 | Container (K8s) |
|---|---|---|---|
| **Granularity** | Process per core (1 host) | Process per core + cluster mode | Pod per replica |
| **Config** | Code | Config file | YAML manifest |
| **Restart** | Manual code | Automatic | Automatic (liveness probe) |
| **Logging** | You manage | Built-in log management | Centralized (ELK/Datadog) |
| **Deployment** | Manual | `pm2 reload` (zero-downtime) | Rolling update |
| **Health checks** | Manual | HTTP health check | Liveness/readiness probes |
| **Use case** | Learning, custom control | Single VM production | Cloud-native production |

In modern production deployments: **1 process per container** + K8s horizontal scaling is preferred over cluster. Let the orchestrator handle failure and scaling.

### IPC Between Master and Workers

```javascript
// Worker → Master
process.send({ type: 'metrics', rps: 500, memory: process.memoryUsage() });

// Master → specific worker
cluster.workers[id].send({ type: 'config-update', config: newConfig });

// Master → all workers
Object.values(cluster.workers).forEach(worker => {
    worker.send({ type: 'config-update', config: newConfig });
});
```

---

## Promise Combinators

### Promise.all — All Must Succeed

Resolves when ALL promises resolve. **Rejects immediately** on the first rejection (fast-fail). Best for operations that must all succeed and you need all results.

```javascript
const [user, orders, payments] = await Promise.all([
    fetchUser(userId),
    fetchOrders(userId),
    fetchPayments(userId),
]);
// All 3 run concurrently. If any fails, the whole thing fails.
// Total time ≈ max(t_user, t_orders, t_payments), not sum.
```

### Promise.allSettled — All Complete (Succeed or Fail)

Waits for ALL promises to settle (resolve or reject). Never rejects. Returns array of `{status, value}` or `{status, reason}`.

```javascript
const results = await Promise.allSettled([
    fetchUser(userId),
    fetchRecommendations(userId),  // non-critical: ok if it fails
    fetchAds(userId),              // non-critical
]);

const user = results[0].status === 'fulfilled' ? results[0].value : null;
// Use allSettled when partial failure is acceptable — e.g., fetching optional data
```

### Promise.race — First Settles (Succeed or Fail)

Resolves/rejects with the result of the **first** promise that settles (either way).

```javascript
// Timeout pattern
const result = await Promise.race([
    fetchSlowData(),
    new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000)),
]);
// If fetchSlowData takes > 5s, rejects with Timeout error

// WARNING: losing race doesn't cancel the other promise's execution
// fetchSlowData() still runs to completion, just its result is ignored
```

### Promise.any — First Succeeds

Resolves with the **first** promise that **resolves**. Only rejects if **all** promises reject (`AggregateError`). Use for "try multiple sources, use the first that works."

```javascript
// Try multiple CDN endpoints, use fastest responding
const response = await Promise.any([
    fetch('https://cdn1.example.com/data.json'),
    fetch('https://cdn2.example.com/data.json'),
    fetch('https://cdn3.example.com/data.json'),
]);
// Returns first successful response, ignores failures (unless all fail)
```

### Summary Table

| Combinator | Resolves when | Rejects when | Use case |
|---|---|---|---|
| `Promise.all` | All resolve | First rejects | Required parallel fetches |
| `Promise.allSettled` | All settle | Never | Optional parallel fetches |
| `Promise.race` | First settles | First rejects | Timeout pattern |
| `Promise.any` | First resolves | All reject | Fallback/redundancy |

---

## Async Iterators and Streams

### Async Iterators

For processing streams of data where each item requires async work:

```javascript
// Process a paginated API without loading all pages into memory
async function* fetchAllUsers() {
    let page = 1;
    while (true) {
        const users = await api.getUsers({ page, limit: 100 });
        if (users.length === 0) break;
        yield* users;  // yield each user one at a time
        page++;
    }
}

// Consumer
for await (const user of fetchAllUsers()) {
    await processUser(user);  // process one at a time, backpressure built-in
}
```

### Node.js Streams with Async/Await

```javascript
const { pipeline } = require('stream/promises');
const fs = require('fs');
const zlib = require('zlib');

// Pipeline handles backpressure automatically
await pipeline(
    fs.createReadStream('large-file.txt'),
    zlib.createGzip(),
    fs.createWriteStream('large-file.txt.gz'),
);
// Streams data chunk by chunk — never loads entire file into memory
```

---

## Implementation Examples

### How It Works Internally (ASCII Diagram)

```
Complete Request Lifecycle in Node.js:

Browser ──HTTP──► Node.js (port 8080)
                      │
                  Event Loop (poll phase)
                  picks up incoming connection
                      │
                  Express middleware chain
                  (synchronous JS execution)
                      │
                  await db.query(...)
                  ┌──── await releases call stack ────────────────────────────┐
                  │                                                            │
                  │  libuv sends query to PostgreSQL over TCP (non-blocking)  │
                  │  Event loop free to handle other requests                 │
                  │                                                            │
                  │  PostgreSQL responds → libuv queues callback              │
                  └──── Event loop picks up callback, resumes await ──────────┘
                      │
                  Response sent to browser
```

---

### Event Loop Phase Demonstration

```javascript
// demo-event-loop.js — run this to see exact execution order
console.log('=== Start ===');

// Phase 1: Timers
setTimeout(() => console.log('[setTimeout 0ms]'), 0);
setTimeout(() => console.log('[setTimeout 100ms]'), 100);

// Phase 5: Check
setImmediate(() => console.log('[setImmediate - outer]'));

// nextTick queue (before next phase)
process.nextTick(() => {
    console.log('[nextTick - 1]');
    process.nextTick(() => console.log('[nextTick - nested (runs before Promises)]'));
});

// Microtask queue (Promises)
Promise.resolve().then(() => {
    console.log('[Promise.resolve - 1]');
    return Promise.resolve();
}).then(() => console.log('[Promise.resolve - chained]'));

Promise.resolve().then(() => console.log('[Promise.resolve - 2]'));

// I/O callback (Phase 4: Poll)
const fs = require('fs');
fs.readFile('/etc/hostname', () => {
    console.log('[fs.readFile callback - poll phase]');
    
    // Inside I/O callback: setImmediate fires BEFORE setTimeout
    setImmediate(() => console.log('[setImmediate inside I/O - always before setTimeout]'));
    setTimeout(() => console.log('[setTimeout inside I/O - after setImmediate]'), 0);
    process.nextTick(() => console.log('[nextTick inside I/O]'));
    Promise.resolve().then(() => console.log('[Promise inside I/O]'));
});

console.log('=== End of synchronous code ===');

/* Expected output:
=== Start ===
=== End of synchronous code ===
[nextTick - 1]
[nextTick - nested (runs before Promises)]
[Promise.resolve - 1]
[Promise.resolve - 2]
[Promise.resolve - chained]
[setTimeout 0ms]
[setImmediate - outer]          ← check phase
[fs.readFile callback - poll phase]
[nextTick inside I/O]
[Promise inside I/O]
[setImmediate inside I/O - always before setTimeout]
[setTimeout inside I/O - after setImmediate]
[setTimeout 100ms]
*/
```

---

### Worker Thread for CPU Task

```javascript
// prime-worker.js
const { workerData, parentPort } = require('worker_threads');

function isPrime(n) {
    if (n < 2) return false;
    if (n === 2) return true;
    if (n % 2 === 0) return false;
    for (let i = 3; i <= Math.sqrt(n); i += 2) {
        if (n % i === 0) return false;
    }
    return true;
}

function countPrimes(limit) {
    let count = 0;
    for (let i = 2; i <= limit; i++) {
        if (isPrime(i)) count++;
    }
    return count;
}

const result = countPrimes(workerData.limit);
parentPort.postMessage({ count: result });
```

```javascript
// app.js
const { Worker } = require('worker_threads');
const path = require('path');
const express = require('express');

const app = express();

// BAD: blocks event loop — ALL other requests freeze during computation
app.get('/primes-blocking', (req, res) => {
    const limit = parseInt(req.query.limit) || 1000000;
    // This runs on the main thread — blocks for ~500ms on modern hardware
    let count = 0;
    for (let i = 2; i <= limit; i++) {
        if (isPrime(i)) count++;
    }
    res.json({ count });
});

// GOOD: offloads to worker thread — event loop stays responsive
app.get('/primes-async', async (req, res) => {
    const limit = parseInt(req.query.limit) || 1000000;
    
    try {
        const { count } = await new Promise((resolve, reject) => {
            const worker = new Worker(path.join(__dirname, 'prime-worker.js'), {
                workerData: { limit },
            });
            worker.on('message', resolve);
            worker.on('error', reject);
        });
        res.json({ count });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Health check responds instantly even while prime computation runs
app.get('/health', (req, res) => res.json({ status: 'ok' }));

function isPrime(n) {
    if (n < 2) return false;
    for (let i = 2; i <= Math.sqrt(n); i++) if (n % i === 0) return false;
    return true;
}

app.listen(3000, () => console.log('Server running on :3000'));
```

---

### Async Waterfall Pitfall — Sequential vs Concurrent

```javascript
// SLOW: awaiting sequentially — each call waits for the previous
async function getUserDataSlow(userId) {
    const user = await db.getUser(userId);          // 100ms
    const orders = await db.getOrders(userId);      // 100ms  (waits for user)
    const payments = await db.getPayments(userId);  // 100ms  (waits for orders)
    return { user, orders, payments };
    // Total: ~300ms
}

// FAST: concurrent — all 3 run in parallel
async function getUserDataFast(userId) {
    const [user, orders, payments] = await Promise.all([
        db.getUser(userId),       // starts immediately
        db.getOrders(userId),     // starts immediately
        db.getPayments(userId),   // starts immediately
    ]);
    return { user, orders, payments };
    // Total: ~100ms (max of 3 parallel operations)
}

// GOTCHA: loop with sequential awaits (very common mistake)
// SLOW:
async function processOrdersSlow(orderIds) {
    for (const id of orderIds) {
        await processOrder(id);  // sequential, one at a time
    }
}
// Total: n * processOrder_time

// FAST: concurrent with limit
async function processOrdersFast(orderIds, concurrency = 10) {
    const { default: pLimit } = await import('p-limit');
    const limit = pLimit(concurrency);
    
    await Promise.all(
        orderIds.map(id => limit(() => processOrder(id)))
    );
}
// Total: ≈ (n / concurrency) * processOrder_time
```

---

## Common Patterns & Best Practices

### Pattern 1: Avoid sync I/O in Server Code

Never use sync I/O in request handlers. The one exception: loading config files at startup before the server starts accepting connections.

```javascript
// Startup (before server.listen): acceptable
const config = JSON.parse(fs.readFileSync('config.json'));

// In request handler: NEVER
app.get('/data', (req, res) => {
    const data = fs.readFileSync('data.json');  // blocks all requests
    res.json(data);
});
```

### Pattern 2: Use process.nextTick for Consistent Async Behavior

When a function may complete synchronously in some code paths, use `process.nextTick` to ensure the callback is always asynchronous:

```javascript
function getFromCacheOrDB(key, callback) {
    if (memCache.has(key)) {
        process.nextTick(() => callback(null, memCache.get(key)));
        // Without nextTick: callback would be synchronous — breaks caller expectations
        return;
    }
    db.get(key, callback);
}
```

### Pattern 3: Graceful Shutdown

```javascript
const server = app.listen(3000);

process.on('SIGTERM', () => {
    console.log('SIGTERM received, shutting down gracefully');
    
    // Stop accepting new connections
    server.close(() => {
        console.log('HTTP server closed');
        // Close DB connections, finish processing, then exit
        db.end().then(() => process.exit(0));
    });
    
    // Force exit after 30s if graceful shutdown takes too long
    setTimeout(() => {
        console.error('Forced shutdown after timeout');
        process.exit(1);
    }, 30000);
});
```

### Pattern 4: Unhandled Promise Rejections

```javascript
// Catch unhandled rejections globally
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Promise Rejection:', reason);
    // In production: log to error tracking (Sentry), then crash
    process.exit(1);
});

// Catch uncaught exceptions
process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
    process.exit(1);  // Always exit on uncaughtException — state may be corrupt
});
```

---

## Common Pitfalls

**1. CPU-bound work on the main thread**
Sorting large arrays, heavy regex, large JSON.parse, or cryptographic operations without `util.promisify` or worker threads will block all requests. Measure with event loop latency metrics; fix with worker threads.

**2. Sequential awaits in loops**
`for (const x of items) { await processItem(x) }` processes one item at a time. Use `Promise.all` with concurrency limiting for parallel processing.

**3. Forgetting that process.nextTick starves the event loop**
Recursively scheduling `process.nextTick` prevents I/O callbacks from firing. Use `setImmediate` for recursive deferred work.

**4. Not increasing UV_THREADPOOL_SIZE for crypto/file-heavy apps**
Default 4 threads means concurrent `pbkdf2`, `scrypt`, or heavy file operations queue up. Set `UV_THREADPOOL_SIZE` appropriately.

**5. Promise.race doesn't cancel losers**
The "losing" promises in `Promise.race` still execute to completion — they just have their results ignored. Use `AbortController` if you need to actually cancel the losing operations.

**6. Missing error handling in event emitters**
`EventEmitter` with no `error` listener crashes the process. Always attach `.on('error', handler)` to event emitters.

**7. Memory leaks from unremoved event listeners**
`emitter.on('data', fn)` adds a listener. If you add listeners in a loop or per-request without removing them, you get a listener leak. Use `emitter.once()` or `emitter.removeListener()`.

**8. Cluster workers share no state**
In-memory sessions, caches, rate limiters don't work across cluster workers. Use Redis for shared state.

---

## Interview Questions

**Q: Explain the Node.js event loop phases.**

A: The event loop has 6 phases executed in order: (1) **Timers** — runs `setTimeout`/`setInterval` callbacks that have reached their threshold. (2) **Pending callbacks** — I/O error callbacks deferred from previous iteration. (3) **Idle/Prepare** — internal libuv use. (4) **Poll** — the main phase: retrieves I/O events, executes their callbacks, blocks waiting for I/O if no timers are pending. (5) **Check** — runs `setImmediate` callbacks. (6) **Close callbacks** — close events. Between each phase, nextTick queue and microtask (Promise) queue are fully drained.

**Q: What is the difference between process.nextTick and setImmediate?**

A: `process.nextTick` fires **before** the event loop moves to the next phase — at the end of the current operation. It can starve I/O if used recursively. `setImmediate` fires in the **check phase**, after the poll phase on the current event loop iteration. Inside I/O callbacks, `setImmediate` always fires before `setTimeout(fn, 0)`. `nextTick` is for ensuring async behavior in synchronous paths (e.g., returning cached value asynchronously). `setImmediate` is for deferring compute work without starving I/O.

**Q: Why is Node.js good for I/O-bound but bad for CPU-bound tasks?**

A: For I/O-bound work, Node.js uses libuv's async I/O — while waiting for disk or network, the event loop handles other requests. A single thread can serve thousands of concurrent connections efficiently because waiting time is "free." For CPU-bound work, JavaScript executes synchronously on one thread. A 500ms computation blocks the event loop for 500ms — all other requests queue up. Solution: offload CPU work to worker threads (for JavaScript) or child processes (for native code).

**Q: How do worker threads differ from child processes?**

A: **Worker threads** (`worker_threads` module): share the same process, can share memory via `SharedArrayBuffer`, communicate via `MessageChannel`, have lower creation overhead (~5ms). **Child processes** (`child_process`): separate OS processes, separate V8 instances, communicate via IPC (pipes/sockets or message passing), higher overhead (~100ms to fork). Use worker threads for CPU-bound JavaScript (number crunching, parsing). Use child processes for running external programs, truly isolated execution, or when crash isolation is needed.

**Q: What is the libuv thread pool used for?**

A: libuv's thread pool (default 4 threads, tunable via `UV_THREADPOOL_SIZE`) handles operations that lack async OS support: file system operations (`fs.readFile`, `fs.stat`), DNS lookups (`dns.lookup`), CPU-bound crypto (`crypto.pbkdf2`, `crypto.scrypt`), and zlib compression. Notably, **network I/O does NOT use the thread pool** — it uses OS-level async I/O (epoll/kqueue/IOCP) which is truly non-blocking. Saturating the thread pool (e.g., many concurrent `pbkdf2` calls with only 4 threads) causes I/O callbacks to wait for an available thread.

**Q: How does the cluster module scale Node.js?**

A: `cluster.fork()` creates child processes (workers), each with its own event loop and V8 instance. The master process listens on a port and distributes connections to workers — either via round-robin (default on non-Windows) or by sharing the socket file descriptor (workers accept connections directly). Workers share the port via `SO_REUSEPORT` or master proxying. Each worker is an independent Node.js process, so a crash in one worker doesn't affect others. IPC between master and workers uses `process.send()` / `worker.on('message')`. In cloud deployments, prefer one process per container + horizontal pod autoscaling over cluster.

**Q: What happens when you block the event loop?**

A: All incoming requests queue up. No I/O callbacks can fire. No timers fire. `setImmediate` doesn't run. The server is effectively frozen for all other clients for the duration of the blocking operation. If blocking lasts longer than the client's timeout, connections are dropped. This is the primary scalability failure mode for Node.js. Monitor with event loop lag metrics (time between `setInterval` callbacks vs expected interval). Solutions: use async I/O, offload CPU work to worker threads, use `setImmediate` to yield between chunks of large computations.

---

## Resources

- [Node.js Event Loop Official Documentation](https://nodejs.org/en/docs/guides/event-loop-timers-and-nexttick)
- [libuv Design Overview](http://docs.libuv.org/en/v1.x/design.html)
- [Node.js worker_threads Documentation](https://nodejs.org/api/worker_threads.html)
- [Cluster Module Documentation](https://nodejs.org/api/cluster.html)
- [Don't Block the Event Loop — Node.js Guide](https://nodejs.org/en/docs/guides/dont-block-the-event-loop)
- [Clinic.js — Node.js Performance Profiling](https://clinicjs.org/)
- [p-limit — Concurrency Limiting for Promises](https://github.com/sindresorhus/p-limit)
- [Understanding the Node.js Event Loop — Bert Belder (talk)](https://youtu.be/PNa9OMajl9s)

---

**Next:** [Part 10.3: Python Concurrency — asyncio, GIL & WSGI vs ASGI](./10-concurrency-python-asyncio-gil.md)
