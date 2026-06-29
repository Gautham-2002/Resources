# Part 16.2: Graceful Shutdown & Production Patterns

## What You'll Learn

- Why graceful shutdown matters in Kubernetes and containerised environments
- The complete shutdown sequence: SIGTERM → drain → close dependencies → exit
- How to implement graceful shutdown in Go, Node.js, and Python/FastAPI
- The 12-Factor App principles and why they make services production-ready
- Zero-downtime database migrations with the expand-contract pattern
- Environment configuration validation at startup
- The production readiness checklist

---

## Table of Contents

1. [Why Graceful Shutdown Matters](#why-graceful-shutdown-matters)
2. [Kubernetes Termination Lifecycle](#kubernetes-termination-lifecycle)
3. [Shutdown Sequence](#shutdown-sequence)
4. [Implementation Examples](#implementation-examples)
5. [12-Factor App Principles](#12-factor-app-principles)
6. [Zero-Downtime Database Migrations](#zero-downtime-database-migrations)
7. [Environment Configuration](#environment-configuration)
8. [Production Readiness Checklist](#production-readiness-checklist)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Interview Questions](#interview-questions)
12. [Resources](#resources)

---

## Why Graceful Shutdown Matters

Without graceful shutdown:

```
User sends request → Pod starts processing → Kubernetes kills pod → Request fails with 500
User's payment is half-processed
DB transaction is left open, locks held
Message from Kafka is "processing" — not committed, not failed — stuck
Connection pool leaked
Logs not flushed — last 5 seconds of errors lost
```

With graceful shutdown:

```
Kubernetes sends SIGTERM → Pod stops accepting new requests → 
Finishes all in-flight requests → Commits/acks pending messages → 
Closes DB connections cleanly → Flushes logs → Exits 0
```

In production at scale, pods are terminated constantly — rollouts, node pressure, spot instance termination. Graceful shutdown is not optional, it's fundamental.

---

## Kubernetes Termination Lifecycle

```
kubectl delete pod / rolling update / node eviction
         │
         ▼
Kubernetes sets pod status: Terminating
         │
         ├──► Removes pod from Service endpoints (stops routing traffic)
         │    (this takes a few seconds due to iptables propagation!)
         │
         ├──► Runs preStop hook (if configured) — sleep 5 is common
         │
         ├──► Sends SIGTERM to container PID 1
         │         │
         │         ▼
         │    Application: graceful shutdown begins
         │         │
         │         ▼
         └──► After terminationGracePeriodSeconds (default 30s):
              Sends SIGKILL — immediate, no cleanup possible
```

**Critical insight**: There's a race condition. Kubernetes removes the pod from endpoints AND sends SIGTERM roughly simultaneously. But iptables rules propagate with a delay of 1–5 seconds. During this window, the load balancer may still route requests to the shutting-down pod. The `preStop` sleep (usually `sleep 5`) gives iptables rules time to propagate before the app stops accepting requests.

### Kubernetes Pod Spec

```yaml
spec:
  terminationGracePeriodSeconds: 60  # must be > preStop sleep + drain time
  containers:
  - name: app
    lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "sleep 5"]  # wait for iptables propagation
    readinessProbe:
      httpGet:
        path: /healthz/ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
    livenessProbe:
      httpGet:
        path: /healthz/live
        port: 8080
      initialDelaySeconds: 10
      periodSeconds: 10
```

---

## Shutdown Sequence

```
1. Receive SIGTERM
2. Set readiness probe to fail → load balancer stops routing new requests
3. Wait for preStop sleep to complete (iptables propagation)
4. Stop accepting new connections / close listener
5. Wait for in-flight requests to complete (drain window — typically 20-30s)
6. Close message queue consumers (stop polling, ack pending messages)
7. Close DB connection pool
8. Flush structured logs and metrics
9. Exit with code 0

Total budget: terminationGracePeriodSeconds - preStop sleep
             = 60s - 5s = 55s for actual draining
```

---

## Implementation Examples

### Go + Chi Router

```go
package main

import (
    "context"
    "errors"
    "log/slog"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"
    "github.com/jackc/pgx/v5/pgxpool"
)

var (
    ready = true // readiness probe state
)

func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
    slog.SetDefault(logger)

    // Connect to DB
    dbPool, err := pgxpool.New(context.Background(), os.Getenv("DATABASE_URL"))
    if err != nil {
        slog.Error("Failed to connect to DB", "error", err)
        os.Exit(1)
    }

    r := chi.NewRouter()
    r.Use(middleware.RequestID)
    r.Use(middleware.RealIP)
    r.Use(middleware.Logger)
    r.Use(middleware.Recoverer)

    // Health check endpoints
    r.Get("/healthz/live", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte(`{"status":"ok"}`))
    })
    r.Get("/healthz/ready", func(w http.ResponseWriter, r *http.Request) {
        if !ready {
            w.WriteHeader(http.StatusServiceUnavailable)
            w.Write([]byte(`{"status":"not_ready"}`))
            return
        }
        // Check DB
        if err := dbPool.Ping(r.Context()); err != nil {
            w.WriteHeader(http.StatusServiceUnavailable)
            w.Write([]byte(`{"status":"db_down"}`))
            return
        }
        w.WriteHeader(http.StatusOK)
        w.Write([]byte(`{"status":"ready"}`))
    })

    // Application routes
    r.Get("/users/{id}", getUserHandler(dbPool))

    server := &http.Server{
        Addr:         ":8080",
        Handler:      r,
        ReadTimeout:  15 * time.Second,
        WriteTimeout: 30 * time.Second,
        IdleTimeout:  60 * time.Second,
    }

    // Start server in background
    serverErr := make(chan error, 1)
    go func() {
        slog.Info("Server starting", "addr", server.Addr)
        if err := server.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
            serverErr <- err
        }
    }()

    // Wait for shutdown signal
    // signal.NotifyContext creates a context that cancels on SIGTERM/SIGINT
    ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
    defer stop()

    select {
    case err := <-serverErr:
        slog.Error("Server error", "error", err)
        os.Exit(1)
    case <-ctx.Done():
        slog.Info("Shutdown signal received")
    }

    // Step 1: Mark unready — readiness probe will fail, LB stops sending traffic
    ready = false
    slog.Info("Marked unready, waiting for traffic drain")

    // Step 2: Graceful shutdown with timeout
    shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    if err := server.Shutdown(shutdownCtx); err != nil {
        slog.Error("Server shutdown error", "error", err)
    }

    // Step 3: Close DB pool
    slog.Info("Closing DB pool")
    dbPool.Close()

    slog.Info("Graceful shutdown complete")
    // os.Exit(0) is implicit — main returns
}

func getUserHandler(db *pgxpool.Pool) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        // handler implementation
    }
}
```

### Node.js + Express

```javascript
const express = require('express');
const { Pool } = require('pg');
const process = require('process');
const http = require('http');

const app = express();
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
let isReady = true;

// Health check endpoints
app.get('/healthz/live', (req, res) => {
  res.json({ status: 'ok' });
});

app.get('/healthz/ready', async (req, res) => {
  if (!isReady) {
    return res.status(503).json({ status: 'shutting_down' });
  }
  try {
    await pool.query('SELECT 1');
    res.json({ status: 'ready' });
  } catch (err) {
    res.status(503).json({ status: 'db_down', error: err.message });
  }
});

app.get('/users/:id', async (req, res) => {
  const { rows } = await pool.query('SELECT * FROM users WHERE id = $1', [req.params.id]);
  if (!rows[0]) return res.status(404).json({ error: 'Not found' });
  res.json(rows[0]);
});

const server = http.createServer(app);

server.listen(8080, () => {
  console.log(JSON.stringify({ level: 'info', msg: 'Server started', port: 8080 }));
});

// Track active connections for draining
const activeConnections = new Set();
server.on('connection', (socket) => {
  activeConnections.add(socket);
  socket.on('close', () => activeConnections.delete(socket));
});

// Graceful shutdown handler
async function gracefulShutdown(signal) {
  console.log(JSON.stringify({ level: 'info', msg: 'Shutdown signal received', signal }));

  // Step 1: Mark unready
  isReady = false;

  // Step 2: Stop accepting new connections
  server.close(async () => {
    console.log(JSON.stringify({ level: 'info', msg: 'HTTP server closed' }));

    // Step 3: Close DB pool
    await pool.end();
    console.log(JSON.stringify({ level: 'info', msg: 'DB pool closed' }));

    console.log(JSON.stringify({ level: 'info', msg: 'Graceful shutdown complete' }));
    process.exit(0);
  });

  // Destroy idle connections immediately (keep active ones)
  for (const socket of activeConnections) {
    if (!socket.destroyed) {
      socket.end(); // half-close — sends FIN, allows in-flight requests to finish
    }
  }

  // Force shutdown if drain takes too long
  setTimeout(() => {
    console.error(JSON.stringify({ level: 'error', msg: 'Forced shutdown after timeout' }));
    process.exit(1);
  }, 30_000);
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Handle uncaught errors — log and exit so Kubernetes can restart
process.on('uncaughtException', (err) => {
  console.error(JSON.stringify({ level: 'fatal', msg: 'Uncaught exception', error: err.message }));
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  console.error(JSON.stringify({ level: 'fatal', msg: 'Unhandled rejection', reason: String(reason) }));
  process.exit(1);
});
```

### Python + FastAPI

```python
import asyncio
import logging
import signal
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncpg
import uvicorn

logger = logging.getLogger(__name__)

# Use lifespan for clean startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── STARTUP ───
    logger.info("Starting up...")

    # Validate required config at startup — fail fast
    required = ["DATABASE_URL", "REDIS_URL", "JWT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

    app.state.db_pool = await asyncpg.create_pool(
        dsn=os.environ["DATABASE_URL"],
        min_size=5,
        max_size=20,
        command_timeout=30,
    )
    app.state.is_ready = True
    logger.info("Startup complete")

    yield  # Application runs here

    # ─── SHUTDOWN ───
    logger.info("Shutdown signal received, beginning graceful shutdown")

    # Mark unready — readiness probe will fail
    app.state.is_ready = False

    # Give in-flight requests time to complete
    # uvicorn handles this automatically when receiving SIGTERM
    # but we can add extra cleanup here

    # Close DB pool
    await app.state.db_pool.close()
    logger.info("DB pool closed")

    logger.info("Graceful shutdown complete")


app = FastAPI(lifespan=lifespan)


@app.get("/healthz/live")
async def liveness():
    return {"status": "ok"}


@app.get("/healthz/ready")
async def readiness(request: Request):
    if not getattr(request.app.state, "is_ready", False):
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    try:
        await request.app.state.db_pool.fetchval("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "db_down"})


@app.get("/users/{user_id}")
async def get_user(user_id: int, request: Request):
    row = await request.app.state.db_pool.fetchrow(
        "SELECT * FROM users WHERE id = $1", user_id
    )
    if not row:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return dict(row)


# Uvicorn startup (production: gunicorn with uvicorn workers)
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        workers=4,
        loop="uvloop",
        timeout_graceful_shutdown=30,
        log_config=None,  # use our own structured logger
    )
```

**Production start command:**
```bash
# gunicorn manages worker lifecycle + uvicorn provides async event loop
gunicorn main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --timeout 60 \
  --graceful-timeout 30 \
  --bind 0.0.0.0:8080 \
  --access-logfile -
```

---

## 12-Factor App Principles

The [12-Factor App](https://12factor.net/) methodology defines how to build portable, production-ready services.

| Factor | Rule | Why |
|---|---|---|
| I. Codebase | One codebase, multiple deploys | No environment-specific branches |
| II. Dependencies | Declare all dependencies explicitly | `go.mod`, `package.json`, `requirements.txt` |
| III. Config | Store config in environment variables | Never hardcode URLs, ports, secrets |
| IV. Backing Services | Treat as attached resources via URL | DB, Redis, Kafka — just URLs in env vars |
| V. Build/Release/Run | Strictly separate stages | Build once, deploy everywhere |
| VI. Processes | Stateless — no local state between requests | Enables horizontal scaling |
| VII. Port Binding | Export services via port binding | Don't rely on injected web server |
| VIII. Concurrency | Scale out via process model | Multiple instances, each stateless |
| IX. Disposability | Fast startup, graceful shutdown | Kubernetes can terminate any pod |
| X. Dev/Prod Parity | Keep environments as similar as possible | Docker makes this achievable |
| XI. Logs | Treat logs as event streams (stdout) | No log files in containers |
| XII. Admin Processes | Run management tasks as one-off processes | DB migrations, seed scripts |

**Most important for backend APIs:**
- **Config (III)**: All configuration from environment variables. Validate at startup.
- **Processes (VI)**: Stateless. Any in-process cache (LRU map) is fine. Never write to local filesystem as persistent storage.
- **Disposability (IX)**: Fast startup (< 10s) and graceful shutdown (drain within `terminationGracePeriodSeconds`).
- **Logs (XI)**: Write to stdout/stderr as JSON. Container runtime captures and forwards to log aggregator (ELK, CloudWatch, Loki).

---

## Zero-Downtime Database Migrations

The hardest part of production deployments is database migrations. The rule: **a deployment must be compatible with both the old AND new code simultaneously** during the rollout window.

### The Expand-Contract Pattern

Never perform a breaking database change in a single deployment. Split into multiple deployments:

**Example: Rename column `user_name` → `full_name`**

```
❌ WRONG — single deployment:
  Deploy 1: ALTER TABLE users RENAME COLUMN user_name TO full_name
  → Old pods still running select user_name → crashes

✅ CORRECT — expand-contract (3 deployments):

  Deployment 1 — EXPAND:
    ALTER TABLE users ADD COLUMN full_name TEXT;
    -- Both columns exist. Old code uses user_name. New code reads full_name, falls back to user_name.
    
  Deployment 2 — MIGRATE DATA:
    UPDATE users SET full_name = user_name WHERE full_name IS NULL;
    -- Backfill. Trigger for ongoing writes: on insert/update, populate both.
    
  Deployment 3 — CONTRACT:
    -- New code only uses full_name, old code is gone.
    ALTER TABLE users DROP COLUMN user_name;
```

### Safe Migration Operations

| Operation | Safe? | Notes |
|---|---|---|
| Add a nullable column | ✅ Safe | Old code ignores it |
| Add a column with default | ✅ Safe (Postgres 11+) | Metadata change, no rewrite |
| Add an index CONCURRENTLY | ✅ Safe | Doesn't lock table |
| Drop a column | ❌ Unsafe | Old code still selects it |
| Rename a column | ❌ Unsafe | Old code uses old name |
| Add NOT NULL without default | ❌ Unsafe | Old code doesn't send value |
| Change column type | ❌ Unsafe | Old code sends wrong type |
| Add a unique constraint | ⚠ Careful | Validates existing data |

```sql
-- ✅ SAFE — add index without blocking writes
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- ❌ UNSAFE — add index the normal way (locks table)
CREATE INDEX idx_users_email ON users(email);

-- ✅ SAFE — add nullable column
ALTER TABLE users ADD COLUMN phone TEXT;

-- ❌ UNSAFE — add NOT NULL without default (old inserts don't have this field)
ALTER TABLE users ADD COLUMN phone TEXT NOT NULL;
```

### Migration Tools

```bash
# Go: goose or golang-migrate
goose postgres "$DATABASE_URL" up
golang-migrate -path ./migrations -database "$DATABASE_URL" up

# Node.js: knex, prisma migrate
npx prisma migrate deploy     # production (no interactive prompts)
npx prisma migrate dev        # development (interactive, generates migration files)

# Python: alembic
alembic upgrade head
```

**Always run migrations before deploying new code** — or use a separate migration job in CI/CD.

---

## Environment Configuration

### Config Validation at Startup

Fail fast if required configuration is missing. Don't let the app start with broken config.

**Go:**
```go
package config

import (
    "fmt"
    "os"
)

type Config struct {
    DatabaseURL  string
    RedisURL     string
    JWTSecret    string
    Port         string
    Environment  string
}

func Load() (*Config, error) {
    c := &Config{
        DatabaseURL: os.Getenv("DATABASE_URL"),
        RedisURL:    os.Getenv("REDIS_URL"),
        JWTSecret:   os.Getenv("JWT_SECRET"),
        Port:        getEnvOrDefault("PORT", "8080"),
        Environment: getEnvOrDefault("ENVIRONMENT", "production"),
    }

    var missing []string
    if c.DatabaseURL == "" { missing = append(missing, "DATABASE_URL") }
    if c.RedisURL == ""    { missing = append(missing, "REDIS_URL") }
    if c.JWTSecret == ""   { missing = append(missing, "JWT_SECRET") }

    if len(missing) > 0 {
        return nil, fmt.Errorf("missing required environment variables: %v", missing)
    }

    return c, nil
}

func getEnvOrDefault(key, defaultVal string) string {
    if v := os.Getenv(key); v != "" {
        return v
    }
    return defaultVal
}
```

**Python (pydantic-settings):**
```python
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str
    port: int = 8080
    environment: str = "production"
    debug: bool = False

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_must_be_long(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    model_config = {"env_file": ".env"}

# Raises ValidationError at startup if any required field missing
settings = Settings()
```

**Node.js (envalid):**
```javascript
const { cleanEnv, str, port, url } = require('envalid');

const env = cleanEnv(process.env, {
  DATABASE_URL: url(),
  REDIS_URL: url(),
  JWT_SECRET: str({ docs: 'https://wiki.internal/secrets' }),
  PORT: port({ default: 8080 }),
  NODE_ENV: str({ choices: ['development', 'production', 'test'], default: 'production' }),
});
// Throws and exits process if validation fails
```

---

## Production Readiness Checklist

Before deploying a new service to production:

**Availability:**
- [ ] `/healthz/live` (liveness probe) returns 200 — process is alive
- [ ] `/healthz/ready` (readiness probe) checks DB, Redis, critical dependencies
- [ ] `terminationGracePeriodSeconds` set appropriately (>= preStop sleep + drain time)
- [ ] `preStop` sleep configured (usually 5s) for iptables propagation
- [ ] Graceful shutdown handler implemented (SIGTERM → drain → close dependencies)
- [ ] Resource requests and limits set in Kubernetes manifests

**Observability:**
- [ ] Structured JSON logging to stdout
- [ ] Request ID injected and propagated in logs
- [ ] `/metrics` Prometheus endpoint exposed
- [ ] p99 latency histogram metric
- [ ] Error rate counter by status code
- [ ] Distributed tracing configured (OpenTelemetry SDK)

**Reliability:**
- [ ] Timeouts on all outbound calls (DB, Redis, external APIs)
- [ ] Circuit breaker for external dependencies
- [ ] Retry with exponential backoff + jitter for transient failures
- [ ] Database connection pool with appropriate min/max sizes
- [ ] Rate limiting enabled (per user, per endpoint)

**Security:**
- [ ] Secrets loaded from environment, not hardcoded
- [ ] Security headers middleware (HSTS, X-Content-Type-Options, etc.)
- [ ] Authentication/authorization middleware on all protected routes
- [ ] Input validation at API boundary (Pydantic, go-validator, Zod)
- [ ] CORS configured explicitly (not `*`)

**Deployment:**
- [ ] Multi-stage Dockerfile with non-root user
- [ ] `.dockerignore` configured
- [ ] Database migrations backwards-compatible (expand-contract pattern)
- [ ] Migration job runs before new code deploys (init container or CI step)
- [ ] Feature flags for risky changes (dark launch)

---

## Common Patterns & Best Practices

### Pattern 1: Use a Done Channel to Coordinate Shutdown

```go
// Signal all goroutines to stop via context cancellation
ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGTERM)
defer cancel()

// Background worker respects context
go func() {
    for {
        select {
        case <-ctx.Done():
            return  // clean exit
        case job := <-jobQueue:
            process(job)
        }
    }
}()

<-ctx.Done()
// ctx is cancelled, all goroutines will stop
```

### Pattern 2: Validate Config Once, Inject Everywhere

Create a `Config` struct at startup, validate it, and inject it as a dependency — never call `os.Getenv` in handler code.

### Pattern 3: Separate Liveness from Readiness

- Liveness: `GET /healthz/live` → always returns 200 if the process is running. No dependency checks. Used by Kubernetes to decide whether to restart the pod.
- Readiness: `GET /healthz/ready` → returns 200 only when the service can handle traffic (DB reachable, cache warm, etc.). Kubernetes stops routing traffic if this fails. Return 503 during graceful shutdown.

---

## Common Pitfalls

- ❌ WRONG: Checking DB in liveness probe — a slow DB will cause Kubernetes to restart all pods in a thundering herd
- ✅ CORRECT: Liveness checks only "is this process alive". Readiness checks dependencies.

- ❌ WRONG: `terminationGracePeriodSeconds: 30` with a drain timeout of 30s — no time for preStop + iptables
- ✅ CORRECT: `terminationGracePeriodSeconds` > preStop sleep + drain window + buffer

- ❌ WRONG: Running DB migrations in the same deploy as the code change (race condition during rolling update)
- ✅ CORRECT: Run migrations as a separate step (init container, CI job) before new pods start

- ❌ WRONG: Dropping a column in the same deploy that stops using it
- ✅ CORRECT: Deploy 1 — stop using the column. Deploy 2 (next sprint) — drop the column.

- ❌ WRONG: Writing to local filesystem for persistent data (container is ephemeral)
- ✅ CORRECT: Use object storage (S3, GCS) or mounted volumes for persistence

- ❌ WRONG: Catching SIGTERM with `process.exit(0)` immediately in Node.js
- ✅ CORRECT: `server.close()` first, wait for connections to drain, THEN exit

---

## Interview Questions

**Q1. What is graceful shutdown and why is it important in Kubernetes?**

**Answer:** Graceful shutdown is the process by which a service finishes all in-flight work before stopping. It's critical in Kubernetes because pods are terminated frequently — during rollouts, node pressure, or spot instance termination. Without graceful shutdown, in-flight requests fail with 500, open DB transactions are left uncommitted (holding locks), and Kafka offsets aren't committed (messages reprocessed on restart). The sequence: receive SIGTERM → mark unready (stop new traffic) → drain in-flight requests → close DB/Redis/Kafka connections → flush logs → exit 0.

---

**Q2. What is the difference between SIGTERM and SIGKILL?**

**Answer:** SIGTERM (signal 15) is a polite request to stop — the process can catch it and perform cleanup. Kubernetes always sends SIGTERM first. SIGKILL (signal 9) is an immediate, unconditional kill from the OS kernel — the process cannot catch or ignore it. After `terminationGracePeriodSeconds` (default 30s), Kubernetes sends SIGKILL if the process hasn't exited. This is why your graceful shutdown must complete within that window.

---

**Q3. What is the expand-contract database migration pattern?**

**Answer:** A technique for zero-downtime column renames or type changes. Instead of renaming a column in one deployment (which would break old pods still running), you expand first: add the new column alongside the old one. Then migrate data to the new column. Then, once no code references the old column, contract: drop the old column. This spans 2–3 deployments over multiple days/sprints but guarantees that at any point in time, both old and new code versions can read the database correctly. It's especially important during rolling deployments where old and new pods run simultaneously.

---

**Q4. What are the 12-Factor App principles and which are most important for backend APIs?**

**Answer:** The 12-Factor methodology defines how to build portable, scalable cloud-native services. The most critical for backend APIs: (1) **Config** — all configuration from environment variables, never hardcoded. (2) **Processes** — stateless processes that can be started/stopped without data loss; no local file state between requests. (3) **Disposability** — fast startup (< 10s) and graceful shutdown, enabling Kubernetes to scale pods freely. (4) **Logs** — treat logs as event streams to stdout; no log files in containers. (5) **Dev/Prod Parity** — use Docker to keep environments identical, avoiding "works on my machine" bugs.

---

**Q5. How do you ensure zero-downtime database migrations?**

**Answer:** Three rules: First, never drop or rename a column in the same deployment that stops using it — split into two deployments. Second, always run migrations before deploying new code (init container, CI migration job before rolling update). Third, use `CREATE INDEX CONCURRENTLY` to add indexes without table locks. The expand-contract pattern handles breaking changes: add the new structure → backfill data → deploy new code → in a later deployment, remove old structure. Also: always test migrations on a staging database with production-sized data before applying to production.

---

**Q6. What would you check before deploying a new service to production?**

**Answer:** I'd verify the production readiness checklist: health check endpoints (`/healthz/live` and `/healthz/ready`) are implemented and tested; graceful shutdown handles SIGTERM, drains in-flight requests, and closes DB/queue connections cleanly; structured JSON logging with request IDs is in place; Prometheus metrics endpoint is exposed; all secrets are loaded from environment (never hardcoded); timeouts are set on all outbound calls; input validation is at the API boundary; database migrations are backward-compatible and tested on staging; Docker image runs as non-root; and resource requests/limits are set in the Kubernetes manifests.

---

## Resources

- [12-Factor App](https://12factor.net/)
- [Kubernetes — Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Kubernetes — Termination of Pods](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination)
- [Alex Edwards — Graceful shutdown in Go](https://www.alexedwards.net/blog/graceful-shutdown-of-a-golang-web-server)
- [golang-migrate](https://github.com/golang-migrate/migrate)
- [Alembic — SQLAlchemy migrations](https://alembic.sqlalchemy.org/)
- [Prisma Migrate](https://www.prisma.io/docs/orm/prisma-migrate)
- [Martin Fowler — Expand-Contract](https://martinfowler.com/bliki/ParallelChange.html)
- [Luca Palmieri — Zero Downtime Deployments](https://www.lpalmieri.com/posts/2020-09-27-zero-downtime-deployments/)

---

**Next:** [Part 17.1: Background Jobs & Task Queues](../part-17/17-background-jobs-task-queues.md)
