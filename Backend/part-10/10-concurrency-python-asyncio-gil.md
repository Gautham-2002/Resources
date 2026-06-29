# Part 10.3: Python Concurrency — asyncio, GIL & WSGI vs ASGI

## What You'll Learn

- What the Global Interpreter Lock (GIL) is and exactly how it limits Python threads
- When to use `threading` vs `multiprocessing` vs `asyncio` — and why the answer is never "always asyncio"
- How the asyncio event loop works internally
- The difference between WSGI and ASGI — and why FastAPI is fast
- How to run CPU-bound work inside an async application without blocking the event loop
- Python 3.13 no-GIL experimental mode

---

## Table of Contents

1. [The Global Interpreter Lock (GIL)](#the-global-interpreter-lock-gil)
2. [Threading vs Multiprocessing vs asyncio](#threading-vs-multiprocessing-vs-asyncio)
3. [asyncio Deep Dive](#asyncio-deep-dive)
4. [WSGI vs ASGI](#wsgi-vs-asgi)
5. [FastAPI & Uvicorn](#fastapi--uvicorn)
6. [Implementation Examples](#implementation-examples)
7. [Common Patterns & Best Practices](#common-patterns--best-practices)
8. [Common Pitfalls](#common-pitfalls)
9. [Interview Questions](#interview-questions)
10. [Resources](#resources)

---

## The Global Interpreter Lock (GIL)

### What the GIL Is

The GIL (Global Interpreter Lock) is a mutex in CPython's runtime that allows only **one thread to execute Python bytecode at a time**, even on multi-core hardware.

It exists because CPython uses **reference counting** for memory management. Every Python object has a `ob_refcnt` field. When two threads simultaneously increment or decrement a reference count without synchronisation, the count becomes wrong and the wrong time to free memory is chosen — leading to use-after-free or memory leaks. The GIL eliminates this race condition by serialising all bytecode execution.

```
Thread 1 executing bytecode ──────► GIL held
Thread 2 waiting              ──────► GIL blocked (waiting)
                                       ↑ only one runs at a time
```

### What the GIL Does NOT Prevent

- I/O operations (file, network, socket) release the GIL while waiting — so `threading` IS effective for I/O-bound work
- C extensions can release the GIL (numpy, pandas, Pillow do this for heavy computation)
- `multiprocessing` uses separate processes — each has its own GIL

### Effect on CPU-Bound vs I/O-Bound Work

```
CPU-bound (matrix multiply, compression, encryption):
  Thread 1: [GIL] execute ... release ... [GIL] execute ...
  Thread 2:        waiting ...    [GIL] execute ...
  → Threads take turns on ONE core. No speedup. Often SLOWER than single-thread (lock contention)

I/O-bound (HTTP request, DB query, file read):
  Thread 1: [GIL] send request → release GIL while waiting → [GIL] process response
  Thread 2:                       [GIL] send request → release GIL while waiting ...
  → Threads overlap I/O wait times. REAL speedup.
```

### Python 3.13 No-GIL (PEP 703)

Python 3.13 ships an experimental build with the GIL disabled (`python3.13t`). It requires thread-safe reference counting and Biased Reference Counting (BRC) to reduce contention. As of 2026 it is still opt-in and not all third-party C extensions are compatible. Worth knowing for interviews — "Python is working on removing the GIL" is a valid answer.

---

## Threading vs Multiprocessing vs asyncio

### Decision Table

| Dimension | `threading` | `multiprocessing` | `asyncio` |
|---|---|---|---|
| True parallelism | No (GIL) | Yes (separate processes) | No |
| I/O-bound tasks | Yes | Yes | Yes (best) |
| CPU-bound tasks | No | Yes (best) | No |
| Memory model | Shared | Separate (IPC needed) | Shared |
| Startup overhead | Low | High (fork/spawn) | Very low |
| Complexity | Medium | High (pickling, IPC) | Medium (event loop) |
| Use case | I/O with legacy sync code | CPU-heavy work | I/O, async APIs |

### When to Use Each

**`threading`** — use when:
- You have legacy synchronous code (DB drivers, HTTP clients) that cannot be made async
- You need simple parallelism for I/O-bound work without rewriting to async
- You need to call blocking C extensions that release the GIL

```python
import threading
import requests

def fetch(url):
    r = requests.get(url)  # blocking, releases GIL during network I/O
    print(r.status_code)

threads = [threading.Thread(target=fetch, args=(url,)) for url in urls]
for t in threads: t.start()
for t in threads: t.join()
```

**`multiprocessing`** — use when:
- CPU-bound work: image processing, ML inference, data compression, crypto
- Need true parallelism across all CPU cores
- Can afford process startup time and serialisation cost

```python
from multiprocessing import Pool

def cpu_heavy(n):
    return sum(i * i for i in range(n))

with Pool(processes=4) as pool:
    results = pool.map(cpu_heavy, [10_000_000] * 4)
```

**`asyncio`** — use when:
- Building async APIs (FastAPI, aiohttp)
- Making many concurrent I/O calls (HTTP, DB, Redis, Kafka)
- Prefer single-threaded cooperative multitasking for I/O

---

## asyncio Deep Dive

### How the Event Loop Works

asyncio runs on a **single OS thread**. It maintains a queue of coroutines (tasks) and an I/O selector (epoll/kqueue). When a coroutine hits an `await`, it suspends itself and hands control back to the event loop, which runs another coroutine. When the I/O is ready, the first coroutine is resumed.

```
Event Loop Iteration:
┌─────────────────────────────────────────────────────┐
│ 1. Run all ready callbacks                          │
│ 2. Poll I/O (epoll) with timeout                    │
│ 3. Schedule callbacks for ready I/O events          │
│ 4. Run scheduled callbacks (call_later, call_soon)  │
└─────────────────────────────────────────────────────┘
                    ↺ repeat forever
```

### Coroutines, Tasks, and Futures

```python
import asyncio

# Coroutine — does not run until awaited or scheduled
async def fetch_user(user_id: int):
    await asyncio.sleep(0.1)  # simulates DB query
    return {"id": user_id, "name": "Gautham"}

# Running a single coroutine
result = asyncio.run(fetch_user(1))

# asyncio.create_task — schedule coroutine to run concurrently
async def main():
    # Without create_task — sequential
    user = await fetch_user(1)          # 0.1s
    orders = await fetch_orders(1)      # 0.1s
    # Total: 0.2s

    # With create_task — concurrent
    user_task = asyncio.create_task(fetch_user(1))
    orders_task = asyncio.create_task(fetch_orders(1))
    user = await user_task              # both run concurrently
    orders = await orders_task
    # Total: ~0.1s
```

### asyncio.gather — Fan-out Pattern

```python
import asyncio
import httpx

async def fetch(client: httpx.AsyncClient, url: str) -> dict:
    response = await client.get(url)
    return response.json()

async def fetch_all(urls: list[str]) -> list[dict]:
    async with httpx.AsyncClient() as client:
        tasks = [fetch(client, url) for url in urls]
        # gather runs all tasks concurrently, returns list of results in order
        results = await asyncio.gather(*tasks)
        return results

# Fetch 100 URLs concurrently in ~1 network RTT instead of 100 RTTs
```

### asyncio.gather vs asyncio.wait vs asyncio.TaskGroup

```python
# gather — run all, return results in order (raises on first exception by default)
results = await asyncio.gather(task1, task2, task3)
results = await asyncio.gather(task1, task2, return_exceptions=True)  # don't raise

# wait — more control, returns (done, pending) sets
done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

# TaskGroup (Python 3.11+) — recommended, structured concurrency
async with asyncio.TaskGroup() as tg:
    task1 = tg.create_task(coro1())
    task2 = tg.create_task(coro2())
# Both tasks complete before exiting the context manager
```

### asyncio.wait_for — Timeouts

```python
async def slow_operation():
    await asyncio.sleep(10)
    return "done"

try:
    result = await asyncio.wait_for(slow_operation(), timeout=2.0)
except asyncio.TimeoutError:
    print("Operation timed out")
```

### asyncio Synchronisation Primitives

```python
import asyncio

# Lock — mutual exclusion (not reentrant)
lock = asyncio.Lock()
async def critical_section():
    async with lock:
        # only one coroutine here at a time
        pass

# Semaphore — limit concurrent access
semaphore = asyncio.Semaphore(10)  # max 10 concurrent
async def limited_fetch(url):
    async with semaphore:
        return await client.get(url)

# Event — signal between coroutines
event = asyncio.Event()
async def waiter():
    await event.wait()
    print("Event fired!")

async def setter():
    await asyncio.sleep(1)
    event.set()

# Queue — async producer/consumer
queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)

async def producer():
    for item in data:
        await queue.put(item)  # blocks if full
    await queue.join()         # wait until all items processed

async def consumer():
    while True:
        item = await queue.get()
        await process(item)
        queue.task_done()
```

### Running Blocking Code in async Context

**The cardinal sin**: calling a blocking function from an async handler blocks the entire event loop.

```python
# ❌ WRONG — blocks event loop for all users
@app.get("/users/{id}")
async def get_user(id: int):
    user = db.execute("SELECT ...", id)  # synchronous DB call — blocks event loop!
    return user

# ✅ CORRECT — use async driver
@app.get("/users/{id}")
async def get_user(id: int):
    user = await db.fetchone("SELECT ...", id)  # asyncpg, databases, etc.
    return user

# ✅ CORRECT — offload to thread pool for unavoidable sync calls
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=10)

@app.get("/users/{id}")
async def get_user(id: int):
    loop = asyncio.get_event_loop()
    user = await loop.run_in_executor(executor, sync_db_call, id)
    return user

# ✅ CORRECT — FastAPI handles sync def automatically (uses threadpool)
@app.get("/users/{id}")
def get_user(id: int):          # NOT async — FastAPI runs in threadpool
    user = db.execute("SELECT ...", id)
    return user
```

---

## WSGI vs ASGI

### WSGI (Web Server Gateway Interface)

The old standard (PEP 3333). Synchronous: handles one request per thread/process. Flask and Django (traditional) are WSGI.

```
WSGI interface:
def application(environ: dict, start_response: callable) -> Iterable[bytes]:
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'Hello World']

Gunicorn launches N worker processes, each handles 1 request at a time.
```

**Problem**: Cannot handle WebSockets, SSE, or async operations. 1000 concurrent requests = 1000 threads/processes (expensive).

### ASGI (Asynchronous Server Gateway Interface)

The modern standard (PEP 3333 async evolution). Handles HTTP, WebSockets, and long-polling. FastAPI, Starlette, and Django Channels are ASGI.

```python
# ASGI interface
async def application(scope: dict, receive: callable, send: callable) -> None:
    if scope['type'] == 'http':
        body = await receive()
        await send({'type': 'http.response.start', 'status': 200, ...})
        await send({'type': 'http.response.body', 'body': b'Hello'})
    elif scope['type'] == 'websocket':
        # handle websocket
        pass
```

| | WSGI | ASGI |
|---|---|---|
| Concurrency model | 1 thread per request | Async event loop |
| WebSocket support | No | Yes |
| SSE support | No | Yes |
| HTTP/2 | No | Yes (via uvicorn) |
| Examples | Flask, Django (old) | FastAPI, Starlette, Django 4+ |
| Server | Gunicorn, uWSGI | Uvicorn, Hypercorn, Daphne |

---

## FastAPI & Uvicorn

### Why FastAPI is Fast

1. **Starlette** — lightweight ASGI framework underneath FastAPI
2. **Pydantic v2** — validation written in Rust (pydantic-core), 5–50x faster than v1
3. **asyncio** — all I/O is non-blocking by default
4. **No overhead framework** — minimal middleware stack vs Django

### Uvicorn

Uvicorn is an ASGI server built on `uvloop` (a fast event loop built on libuv, same as Node.js).

```bash
# Development
uvicorn main:app --reload

# Production — multiple workers
uvicorn main:app --workers 4

# Production with Gunicorn managing uvicorn workers (recommended)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

**Why `gunicorn + uvicorn workers`**: Gunicorn handles worker lifecycle (restart crashed workers, graceful reload). Uvicorn provides the async event loop. Best of both worlds.

### FastAPI sync vs async handlers

```python
from fastapi import FastAPI
import asyncio
import time

app = FastAPI()

# async def — runs in event loop, good for async I/O
@app.get("/async")
async def async_handler():
    await asyncio.sleep(1)  # non-blocking — event loop handles other requests
    return {"type": "async"}

# def (sync) — FastAPI automatically runs in a thread pool
# This avoids blocking the event loop for legacy sync code
@app.get("/sync")
def sync_handler():
    time.sleep(1)  # FastAPI uses run_in_executor internally
    return {"type": "sync"}

# ❌ WRONG — async def with blocking call
@app.get("/bad")
async def bad_handler():
    time.sleep(1)  # blocks the ENTIRE event loop!
    return {"bad": True}
```

### Pydantic v2

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from typing import Annotated

class UserCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: str
    age: Annotated[int, Field(ge=0, le=150)]

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()

    @model_validator(mode="after")
    def validate_model(self):
        if self.age < 18 and "admin" in self.name:
            raise ValueError("Admin must be 18+")
        return self

# Settings management
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Implementation Examples

### Python + FastAPI

#### Full async endpoint with concurrent DB + Redis calls

```python
from fastapi import FastAPI, Depends, HTTPException
import asyncpg
import redis.asyncio as aioredis
import asyncio
from contextlib import asynccontextmanager

# Lifespan context manager (FastAPI 0.95+)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db_pool = await asyncpg.create_pool(
        dsn="postgresql://user:pass@localhost/db",
        min_size=5,
        max_size=20
    )
    app.state.redis = aioredis.from_url("redis://localhost")
    yield
    # Shutdown
    await app.state.db_pool.close()
    await app.state.redis.close()

app = FastAPI(lifespan=lifespan)

async def get_db(request):
    return request.app.state.db_pool

async def get_redis(request):
    return request.app.state.redis

@app.get("/users/{user_id}")
async def get_user(user_id: int, db=Depends(get_db), redis=Depends(get_redis)):
    # Check cache first
    cached = await redis.get(f"user:{user_id}")
    if cached:
        return {"user": cached, "source": "cache"}

    # DB and some other I/O concurrently
    user_task = asyncio.create_task(
        db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    )
    stats_task = asyncio.create_task(
        db.fetchval("SELECT COUNT(*) FROM orders WHERE user_id = $1", user_id)
    )

    user, order_count = await asyncio.gather(user_task, stats_task)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = dict(user) | {"order_count": order_count}
    await redis.setex(f"user:{user_id}", 300, str(result))  # TTL 5 min
    return {"user": result, "source": "db"}
```

#### Running CPU-bound work without blocking

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor
from fastapi import FastAPI

app = FastAPI()
process_pool = ProcessPoolExecutor(max_workers=4)

def cpu_intensive_task(data: bytes) -> bytes:
    """This runs in a separate process — doesn't touch event loop"""
    import hashlib
    return hashlib.sha256(data).hexdigest()

@app.post("/hash")
async def hash_data(body: bytes):
    loop = asyncio.get_event_loop()
    # Offload to process pool — event loop is free during computation
    result = await loop.run_in_executor(process_pool, cpu_intensive_task, body)
    return {"hash": result}
```

#### asyncio Queue — Producer/Consumer

```python
import asyncio
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()
job_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

async def worker():
    while True:
        item = await job_queue.get()
        try:
            await process_item(item)
        except Exception as e:
            print(f"Failed: {e}")
        finally:
            job_queue.task_done()

@app.on_event("startup")
async def start_workers():
    for _ in range(5):
        asyncio.create_task(worker())

@app.post("/jobs")
async def submit_job(payload: dict):
    await job_queue.put(payload)
    return {"status": "queued", "queue_size": job_queue.qsize()}
```

### Go + Chi Router

For reference — Go's approach without GIL concerns:

```go
package main

import (
    "context"
    "net/http"
    "sync"

    "github.com/go-chi/chi/v5"
    "github.com/jackc/pgx/v5/pgxpool"
)

// Go has no GIL — goroutines are truly parallel on multiple cores
// Each HTTP request runs in its own goroutine
func getUserHandler(db *pgxpool.Pool) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        userID := chi.URLParam(r, "id")

        // Concurrent DB queries — goroutines run in parallel
        var user User
        var orderCount int
        var wg sync.WaitGroup
        var mu sync.Mutex
        errs := make([]error, 0)

        wg.Add(2)
        go func() {
            defer wg.Done()
            err := db.QueryRow(r.Context(),
                "SELECT id, name FROM users WHERE id = $1", userID,
            ).Scan(&user.ID, &user.Name)
            if err != nil {
                mu.Lock()
                errs = append(errs, err)
                mu.Unlock()
            }
        }()
        go func() {
            defer wg.Done()
            err := db.QueryRow(r.Context(),
                "SELECT COUNT(*) FROM orders WHERE user_id = $1", userID,
            ).Scan(&orderCount)
            if err != nil {
                mu.Lock()
                errs = append(errs, err)
                mu.Unlock()
            }
        }()
        wg.Wait()
        // handle errs, write response...
    }
}
```

### Node.js + Express

```javascript
// Node.js has no GIL but IS single-threaded for JS
// CPU-bound work must be offloaded to worker threads

const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');

// ❌ WRONG — CPU work blocks event loop
app.post('/hash', (req, res) => {
  const hash = crypto.createHash('sha256').update(req.body).digest('hex'); // fast, ok
  // But complex compression, image processing etc would block
  res.json({ hash });
});

// ✅ CORRECT — offload heavy CPU work to worker thread
function runInWorker(data) {
  return new Promise((resolve, reject) => {
    const worker = new Worker('./hash-worker.js', { workerData: data });
    worker.on('message', resolve);
    worker.on('error', reject);
  });
}

app.post('/compress', async (req, res) => {
  const result = await runInWorker(req.body);  // runs in separate thread
  res.json({ compressed: result });
});
```

---

## Common Patterns & Best Practices

### Pattern 1: Always use async DB drivers in FastAPI

```python
# ❌ WRONG — psycopg2 is synchronous, blocks event loop
import psycopg2
conn = psycopg2.connect(...)

# ✅ CORRECT — asyncpg or psycopg3 async
import asyncpg
pool = await asyncpg.create_pool(...)
row = await pool.fetchrow("SELECT ...")

# ✅ CORRECT — SQLAlchemy 2.0 async
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
engine = create_async_engine("postgresql+asyncpg://...")
async with AsyncSession(engine) as session:
    result = await session.execute(select(User).where(User.id == user_id))
```

### Pattern 2: Limit concurrency with Semaphore

```python
# Without semaphore — 10,000 concurrent requests could overwhelm downstream
async def fetch_all(urls):
    tasks = [fetch(url) for url in urls]
    return await asyncio.gather(*tasks)

# With semaphore — max 50 concurrent at any time
async def fetch_all_limited(urls):
    semaphore = asyncio.Semaphore(50)
    async def fetch_with_limit(url):
        async with semaphore:
            return await fetch(url)
    tasks = [fetch_with_limit(url) for url in urls]
    return await asyncio.gather(*tasks)
```

### Pattern 3: Use lifespan for startup/shutdown

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialise connection pools
    app.state.db = await asyncpg.create_pool(DATABASE_URL)
    app.state.redis = aioredis.from_url(REDIS_URL)
    yield
    # Shutdown: close cleanly
    await app.state.db.close()
    await app.state.redis.close()

app = FastAPI(lifespan=lifespan)
```

---

## Common Pitfalls

- ❌ WRONG: `async def handler(): time.sleep(1)` — blocks entire event loop
- ✅ CORRECT: `async def handler(): await asyncio.sleep(1)` or use `def` (FastAPI threadpool)

- ❌ WRONG: Using threading for CPU-bound work expecting parallelism
- ✅ CORRECT: Use `multiprocessing` or `ProcessPoolExecutor` for CPU-bound work

- ❌ WRONG: Sharing state between async tasks without locks
- ✅ CORRECT: Use `asyncio.Lock()` for shared mutable state

- ❌ WRONG: Creating a new event loop manually inside FastAPI handlers
- ✅ CORRECT: Use `asyncio.get_event_loop()` or just write async code naturally

- ❌ WRONG: Using `asyncio.run()` inside an already-running event loop
- ✅ CORRECT: `await coroutine()` directly, or `asyncio.create_task(coroutine())`

- ❌ WRONG: Not awaiting coroutines — `fetch_user(1)` returns a coroutine object, not the result
- ✅ CORRECT: `await fetch_user(1)`

---

## Interview Questions

**Q1. What is the GIL and how does it affect threading in Python?**

**Answer:** The GIL (Global Interpreter Lock) is a mutex in CPython that allows only one thread to execute Python bytecode at a time, even on multi-core hardware. It exists to protect CPython's reference-counting memory management from race conditions. For **I/O-bound** work (network, files, DB), the GIL is released during the wait, so threading provides real concurrency. For **CPU-bound** work, threads are serialised — no speedup, often slower due to lock contention. For CPU-bound parallelism, use `multiprocessing` (separate processes, each with its own GIL).

---

**Q2. When would you use `multiprocessing` vs `threading` vs `asyncio`?**

**Answer:**
- `asyncio` — preferred for I/O-bound async code (FastAPI, aiohttp, async DB drivers). Lowest overhead, most scalable.
- `threading` — use when working with synchronous I/O-bound legacy code that cannot be made async. The GIL releases during I/O so real concurrency is achieved.
- `multiprocessing` — use for CPU-bound work (image processing, ML, data compression). Each process has its own GIL and runs on a separate core.

Rule of thumb: FastAPI app → asyncio for I/O, ProcessPoolExecutor for any CPU-heavy computation.

---

**Q3. What is the difference between WSGI and ASGI?**

**Answer:** WSGI (PEP 3333) is a synchronous interface — one request is handled per thread/process, no support for WebSockets or long-lived connections. Flask and traditional Django use WSGI. ASGI is the async successor — it uses coroutines, supports HTTP, WebSockets, SSE, and HTTP/2 in the same server process. FastAPI and Starlette are ASGI frameworks. ASGI servers (uvicorn, hypercorn) use an asyncio event loop to handle thousands of concurrent connections in a single process.

---

**Q4. What happens if you call a blocking function inside an async function in FastAPI?**

**Answer:** It blocks the entire event loop for the duration of the blocking call. Since the event loop is single-threaded, no other request can be processed until the blocking call returns. This turns your async API into a synchronous one under load. Fix: either use an async equivalent (asyncpg instead of psycopg2), or run the blocking call in a thread pool via `loop.run_in_executor()`. Note: FastAPI automatically runs `def` (non-async) endpoints in a thread pool, so using `def` instead of `async def` is a valid solution for sync code.

---

**Q5. How does `asyncio.gather` work and when would you use it?**

**Answer:** `asyncio.gather(*coroutines)` schedules all coroutines as concurrent tasks and waits for all to complete, returning results in the same order as inputs. It's used for fan-out I/O: fetching multiple APIs simultaneously, running concurrent DB queries, or batching cache lookups. By default it raises immediately on the first exception; pass `return_exceptions=True` to collect all results including exceptions. For Python 3.11+, `asyncio.TaskGroup` is preferred as it provides structured concurrency with better cancellation semantics.

---

**Q6. Why is FastAPI considered fast compared to Flask?**

**Answer:** Three reasons: (1) ASGI vs WSGI — FastAPI uses uvicorn/asyncio which handles I/O concurrently in one event loop; Flask uses WSGI which needs one thread per concurrent request. (2) Pydantic v2 — request validation is written in Rust, making it 5–50x faster than pure Python validation. (3) No ORM overhead — FastAPI doesn't force a heavy framework; async DB drivers like asyncpg communicate directly with PostgreSQL's binary protocol.

---

**Q7. What is `loop.run_in_executor` and when do you use it?**

**Answer:** `run_in_executor(executor, func, *args)` runs a synchronous function in a thread pool (or process pool) without blocking the event loop. Use it when you must call a synchronous library (legacy SDK, sync DB driver, file operations) from an async context. Pass `None` as executor to use the default `ThreadPoolExecutor`. Pass a `ProcessPoolExecutor` for CPU-bound work. FastAPI's `def` endpoints use this internally — declaring a sync `def` route is equivalent to wrapping it in `run_in_executor`.

---

## Resources

- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [FastAPI documentation — async](https://fastapi.tiangolo.com/async/)
- [PEP 703 — Making the GIL Optional](https://peps.python.org/pep-0703/)
- [asyncpg documentation](https://magicstack.github.io/asyncpg/current/)
- [uvicorn documentation](https://www.uvicorn.org/)
- [Real Python — Async IO in Python](https://realpython.com/async-io-python/)
- [Lynn Root — asyncio: We Did It Wrong](https://www.roguelynn.com/words/asyncio-we-did-it-wrong/)

---

**Next:** [Part 11.1: Error Handling & Resilience](../part-11/11-error-handling-resilience.md)
