# Part 16.1: Docker, Containerization & CI/CD

## What You'll Learn

- How containers work at the Linux kernel level (namespaces and cgroups)
- Dockerfile best practices: multi-stage builds, layer caching, security hardening
- Docker Compose for local development
- Kubernetes fundamentals: Pods, Deployments, Services, probes
- CI/CD pipelines with GitHub Actions: lint, test, build, push, deploy
- Deployment strategies: rolling, blue-green, canary
- Production-ready Dockerfiles for Go, Node.js, and Python

---

## Table of Contents

1. [How Containers Work Internally](#1-how-containers-work-internally)
2. [Container vs Virtual Machine](#2-container-vs-virtual-machine)
3. [Dockerfile Deep Dive](#3-dockerfile-deep-dive)
4. [Multi-Stage Builds](#4-multi-stage-builds)
5. [Layer Caching Optimization](#5-layer-caching-optimization)
6. [Security: Non-Root, Image Scanning](#6-security)
7. [Docker Compose for Local Development](#7-docker-compose)
8. [Kubernetes Fundamentals](#8-kubernetes-fundamentals)
9. [CI/CD with GitHub Actions](#9-cicd-with-github-actions)
10. [Deployment Strategies](#10-deployment-strategies)
11. [How It Works Internally (ASCII Diagrams)](#11-how-it-works-internally)
12. [Implementation Examples](#12-implementation-examples)
13. [Common Patterns & Best Practices](#13-common-patterns--best-practices)
14. [Common Pitfalls](#14-common-pitfalls)
15. [Interview Questions & Answers](#15-interview-questions--answers)
16. [Resources](#16-resources)

---

## 1. How Containers Work Internally

Containers are not VMs. They're **Linux processes** with isolated namespaces and resource limits imposed via cgroups. The container runtime (Docker, containerd) sets up this isolation transparently.

### Linux Namespaces

Namespaces provide isolation for specific system resources. Each container gets its own set of namespaces:

| Namespace | Isolates                                       | Effect for container                    |
|-----------|------------------------------------------------|-----------------------------------------|
| `pid`     | Process IDs                                    | Container has its own PID 1 (init)      |
| `net`     | Network interfaces, IP addresses, routing      | Container has its own eth0, IP          |
| `mnt`     | Filesystem mount points                        | Container sees its own filesystem tree  |
| `uts`     | Hostname and domain name                       | Container has its own hostname          |
| `ipc`     | IPC objects (shared memory, semaphores)        | Isolated inter-process communication    |
| `user`    | User and group IDs                             | UID 0 in container ≠ UID 0 on host     |

```
Host OS (Linux Kernel)
├── Namespace: pid (host processes)
├── Namespace: net (host network)
│
└── Container Process (nginx)
    ├── Namespace: pid (container's PID 1 = nginx)
    ├── Namespace: net (container's eth0: 172.17.0.2)
    ├── Namespace: mnt (container's / = nginx image layers)
    └── Namespace: uts (hostname = container ID)
```

### Control Groups (cgroups)

While namespaces provide isolation (what a process can see), cgroups provide **resource limits** (what a process can use).

```
Without cgroups:
Container process can use:
  - 100% of CPU (starves other containers)
  - All available RAM (causes OOM on host)

With cgroups:
Container constraints:
  memory.limit_in_bytes = 512MB   (max RAM)
  cpu.cfs_quota_us = 50000        (50% of one CPU core)
  blkio.throttle.read_bps_device  (disk I/O limits)
```

In Kubernetes, these correspond to container resource limits:
```yaml
resources:
  limits:
    memory: "512Mi"
    cpu: "500m"    # 500 millicores = 50% of 1 CPU core
  requests:
    memory: "256Mi"
    cpu: "250m"
```

### Union Filesystem (OverlayFS)

Docker images are built as layers stacked on top of each other using OverlayFS. Each `RUN`, `COPY`, `ADD` instruction in a Dockerfile creates a new layer.

```
┌───────────────────────────────────────────────────┐
│  Container layer (read-write) ← writable by app   │
├───────────────────────────────────────────────────┤
│  Layer: COPY ./app /app                           │
├───────────────────────────────────────────────────┤
│  Layer: RUN npm install                           │
├───────────────────────────────────────────────────┤
│  Layer: COPY package*.json ./                     │
├───────────────────────────────────────────────────┤
│  Base: node:20-alpine (read-only)                 │
└───────────────────────────────────────────────────┘

Multiple containers from the same image share the read-only layers.
Only the top writable layer is unique per container.
This is why containers start fast — no copying base layers.
```

---

## 2. Container vs Virtual Machine

```
VIRTUAL MACHINES:                    CONTAINERS:
┌─────────────────────────────┐      ┌──────────────────────────────────┐
│ App A      │ App B           │      │ App A    │ App B    │ App C       │
├────────────┼─────────────────┤      ├──────────┼──────────┼────────────┤
│ Guest OS A │ Guest OS B      │      │ Libs A   │ Libs B   │ Libs C     │
│ (full OS,  │ (full OS,       │      ├──────────┴──────────┴────────────┤
│ 1-4 GB)    │ 1-4 GB)         │      │   Container Runtime (Docker)     │
├────────────┴─────────────────┤      ├──────────────────────────────────┤
│ Hypervisor (VMware/KVM)      │      │         HOST OS KERNEL           │
├──────────────────────────────┤      ├──────────────────────────────────┤
│         HOST OS              │      │           HARDWARE               │
├──────────────────────────────┤      └──────────────────────────────────┘
│         HARDWARE             │
└──────────────────────────────┘

VMs:                                  Containers:
- Each has full OS kernel copy        - Share host OS kernel
- Startup: 30s - 3min                 - Startup: milliseconds
- Size: 1-20 GB per VM                - Size: 5 MB - 500 MB per image
- Strong isolation (separate kernel)  - Process-level isolation
- Good for untrusted workloads        - Good for trusted, same-team services
- Hardware-level virtualization       - OS-level virtualization
```

**When to use VMs over containers:**
- Running untrusted third-party code (container escapes are possible)
- Need different OS kernels (Windows containers need Windows kernel)
- Compliance requirements mandate hardware-level isolation
- Running database servers (VMs provide stronger I/O guarantees)

---

## 3. Dockerfile Deep Dive

### Core Instructions

```dockerfile
# FROM — base image
FROM golang:1.22-alpine AS builder

# WORKDIR — set working directory (creates it if not exists)
WORKDIR /app

# COPY — copy files from build context into image
COPY go.mod go.sum ./    # copy dependency files first (cache optimization)
COPY . .                 # copy the rest of the code

# RUN — execute a command and create a new layer
RUN go build -o server ./cmd/server

# ENV — set environment variable (baked into image)
ENV GIN_MODE=release

# ARG — build-time variable (not in final image, unlike ENV)
ARG APP_VERSION=dev
RUN echo $APP_VERSION > /app/version.txt

# EXPOSE — document the port (does NOT publish the port; informational)
EXPOSE 8080

# CMD — default command; can be overridden at docker run
CMD ["/app/server"]

# ENTRYPOINT — command that always runs; CMD becomes its arguments
ENTRYPOINT ["/app/server"]
CMD ["--config", "/etc/app/config.yaml"]
```

### CMD vs ENTRYPOINT

This is a classic interview question.

```dockerfile
# CMD only — can be fully overridden
CMD ["node", "server.js"]
# docker run myapp echo hello → runs "echo hello" (CMD replaced)

# ENTRYPOINT only — command always runs
ENTRYPOINT ["node", "server.js"]
# docker run myapp --port 3000 → runs "node server.js --port 3000"
# docker run myapp echo hello → runs "node server.js echo hello" (weird!)

# ENTRYPOINT + CMD — best pattern
ENTRYPOINT ["node"]
CMD ["server.js"]
# docker run myapp → runs "node server.js"
# docker run myapp worker.js → runs "node worker.js" (CMD overridden)
# docker run --entrypoint /bin/sh myapp → can override ENTRYPOINT too

# Exec form (preferred) vs Shell form
ENTRYPOINT ["node", "server.js"]   # Exec form: PID 1 = node; signals received correctly
ENTRYPOINT node server.js          # Shell form: PID 1 = /bin/sh; signals go to shell, NOT node
```

**Critical:** Always use exec form (`["executable", "arg"]`) for `CMD` and `ENTRYPOINT`. Shell form starts a shell as PID 1, which won't forward `SIGTERM` to your application. This breaks graceful shutdown.

### .dockerignore

```
# .dockerignore — exclude files from build context
node_modules/
.git/
.env
.env.*
*.log
dist/
coverage/
.DS_Store
**/*.test.ts
**/__tests__/
Dockerfile*
docker-compose*.yml
README.md
.github/
```

A large build context is slow to send to the Docker daemon (especially over remote Docker). Always have a `.dockerignore`.

---

## 4. Multi-Stage Builds

Multi-stage builds let you use a large build environment and copy only the compiled artifact to a minimal runtime image.

### Go Multi-Stage Build

```dockerfile
# ─── Stage 1: Build ───────────────────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git ca-certificates

WORKDIR /app

# Copy dependency files FIRST (cache optimization — see Section 5)
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build: static binary, no CGO, stripped debug symbols
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s -X main.version=${VERSION}" \
    -o /app/server \
    ./cmd/server

# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
# scratch = empty image, absolute minimum (no shell, no nothing)
# Use gcr.io/distroless/static or alpine if you need a shell for debugging
FROM gcr.io/distroless/static-debian12

# Copy only the compiled binary and CA certificates
COPY --from=builder /app/server /server
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Non-root user (UID 65534 = nobody)
USER 65534:65534

EXPOSE 8080

ENTRYPOINT ["/server"]

# Result: image size ~5-10 MB vs ~800 MB with golang:1.22
```

### Node.js Multi-Stage Build

```dockerfile
# ─── Stage 1: Dependencies ────────────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install only production dependencies
RUN npm ci --only=production

# ─── Stage 2: Build (TypeScript compilation) ──────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Copy package files and install ALL deps (including devDeps for TypeScript)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and compile
COPY tsconfig.json ./
COPY src/ ./src/
RUN npm run build  # tsc → dist/

# ─── Stage 3: Runtime ─────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

# Security: non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Copy compiled code
COPY --from=builder /app/dist ./dist

# Copy production node_modules (not devDeps)
COPY --from=deps /app/node_modules ./node_modules

# Copy package.json for metadata
COPY package.json ./

# Switch to non-root
USER appuser

EXPOSE 3000

# Use exec form for signal handling
ENTRYPOINT ["node"]
CMD ["dist/server.js"]

# Result: ~150 MB vs ~1 GB with full node:20 + devDeps
```

### Python Multi-Stage Build

```dockerfile
# ─── Stage 1: Build dependencies ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies (gcc for some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt ./

# Install to a specific directory for easy copying
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8000

# Use exec form — uvicorn receives SIGTERM directly
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

---

## 5. Layer Caching Optimization

Docker caches each layer. If a layer hasn't changed (same instruction + same files), it reuses the cached layer instead of rerunning.

### The Golden Rule: Most-Stable to Least-Stable

```dockerfile
# ❌ WRONG — bad cache behavior
FROM node:20-alpine
WORKDIR /app
COPY . .                   # copies ALL files — any code change invalidates this
RUN npm ci                 # re-runs npm install on every code change (slow!)
CMD ["node", "server.js"]

# ✅ CORRECT — optimized cache behavior
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./   # only changes when deps change
RUN npm ci                               # cached unless deps change!
COPY . .                                 # code changes don't affect npm ci layer
CMD ["node", "server.js"]
```

### Cache Invalidation Chain

```
Layer 1: FROM node:20-alpine         ← rarely changes
Layer 2: WORKDIR /app                ← never changes
Layer 3: COPY package*.json ./       ← changes only when you add/remove packages
Layer 4: RUN npm ci                  ← cached until layer 3 changes
Layer 5: COPY . .                    ← changes every commit
Layer 6: RUN npm run build           ← re-runs every commit (fast, just compilation)

On code change only:
- Layers 1-4: CACHED (no re-download of node_modules!)
- Layers 5-6: re-execute (fast)

On dependency change (package.json modified):
- Layers 1-2: CACHED
- Layers 3-6: re-execute (npm ci is slow, but necessary)
```

### Docker BuildKit Cache Mount

For even faster builds, use BuildKit's cache mounts:

```dockerfile
# Cache the Go module download cache across builds
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# Cache the Go build cache across builds
RUN --mount=type=cache,target=/root/.cache/go-build \
    go build -o /app/server ./cmd/server

# Cache pip cache across builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

---

## 6. Security

### Non-Root User

By default, containers run as root (UID 0). Root in a container is root on the host (with some caveats). If an attacker exploits your app, they get root access to the container and potentially the host.

```dockerfile
# ❌ Running as root (default)
FROM node:20-alpine
WORKDIR /app
COPY . .
CMD ["node", "server.js"]
# If node.js has a vulnerability, attacker runs as root

# ✅ Running as non-root
FROM node:20-alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --chown=appuser:appgroup . .
USER appuser  # switch to non-root
CMD ["node", "server.js"]
```

### Read-Only Filesystem

```dockerfile
# Run with read-only root filesystem
# (must mount writable volumes for tmp, logs)
FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/server /server
USER 65534:65534
ENTRYPOINT ["/server"]
```

```bash
docker run --read-only \
    --tmpfs /tmp:rw,size=100m \
    myapp
```

In Kubernetes:
```yaml
securityContext:
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 65534
```

### Image Scanning

Scan images for known CVEs (Common Vulnerabilities and Exposures) before deploying.

```bash
# Trivy — fast, comprehensive scanner
trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:latest

# In CI (fail the build if HIGH or CRITICAL CVEs found)
trivy image --exit-code 1 --severity HIGH,CRITICAL \
    --ignore-unfixed \
    myapp:${{ github.sha }}
```

### Image Size Reduction Checklist

```
1. Use minimal base images:
   - Go: scratch or gcr.io/distroless/static
   - Node.js: node:20-alpine (not node:20)
   - Python: python:3.12-slim (not python:3.12)

2. Multi-stage builds (don't ship build tools)

3. Remove package manager caches:
   RUN apt-get update && apt-get install -y pkg \
       && rm -rf /var/lib/apt/lists/*

4. Combine RUN commands to minimize layers:
   RUN apk add --no-cache git curl \
       && command1 \
       && command2

5. Don't COPY unnecessary files (.git, test files, docs)
```

---

## 7. Docker Compose

Docker Compose is the standard tool for running multi-service local development environments.

```yaml
# docker-compose.yml
version: '3.9'

services:
  # Application services
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: builder   # use build stage for hot-reload in dev
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/appdb
      - REDIS_URL=redis://redis:6379
      - KAFKA_BROKERS=kafka:9092
    volumes:
      - .:/app    # mount source for hot-reload
      - /app/node_modules  # anonymous volume: don't overwrite with host's node_modules
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: on-failure

  # Infrastructure services
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: appdb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d  # auto-run SQL on first start
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d appdb"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  kafka:
    image: confluentinc/cp-kafka:7.6.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      CLUSTER_ID: "MkU3OEVBNTcwNTJENDM2Qk"
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 10s
      timeout: 10s
      retries: 5

volumes:
  postgres_data:
```

**Useful Compose Commands:**

```bash
# Start all services
docker compose up -d

# View logs (follow)
docker compose logs -f api

# Restart one service
docker compose restart api

# Run one-off command (e.g., migrations)
docker compose run --rm api ./migrate up

# Rebuild and restart
docker compose up --build api

# Tear down (remove containers and networks, keep volumes)
docker compose down

# Tear down (remove everything including volumes)
docker compose down -v
```

---

## 8. Kubernetes Fundamentals

### Core Objects

**Pod** — the smallest deployable unit; one or more containers that share network and storage.
**Deployment** — manages a ReplicaSet to ensure N replicas of a Pod are always running; handles rolling updates.
**Service** — stable network endpoint (DNS + IP) for a set of Pods; load balances across them.
**ConfigMap** — non-secret configuration as key-value pairs.
**Secret** — sensitive data (passwords, API keys) base64-encoded; integrate with vault for production.
**Ingress** — HTTP routing rules; routes external traffic to Services by hostname or path.
**HorizontalPodAutoscaler (HPA)** — automatically scales Deployment based on CPU/memory metrics.

### Deployment with Probes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  labels:
    app: order-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-service
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1    # at most 1 pod can be unavailable during update
      maxSurge: 1          # at most 1 extra pod above desired count
  template:
    metadata:
      labels:
        app: order-service
    spec:
      containers:
        - name: order-service
          image: myregistry/order-service:v1.2.3
          ports:
            - containerPort: 8080
          
          # Resource management (required for HPA to work)
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "500m"
          
          # Liveness probe: "is the process hung/deadlocked?"
          # If this fails, Kubernetes KILLS and RESTARTS the container
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 10   # wait 10s before first check (startup time)
            periodSeconds: 15         # check every 15s
            failureThreshold: 3       # kill after 3 consecutive failures
          
          # Readiness probe: "is this pod ready to receive traffic?"
          # If this fails, Kubernetes REMOVES pod from Service endpoints (no traffic)
          # Does NOT kill/restart the pod
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          
          # Startup probe: "has the app finished starting?"
          # For slow-starting apps; disables liveness until startup probe succeeds
          startupProbe:
            httpGet:
              path: /health/live
              port: 8080
            failureThreshold: 30     # allow up to 30 * 10s = 5 minutes to start
            periodSeconds: 10
          
          # Environment from ConfigMap and Secrets
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: order-service-secrets
                  key: database-url
            - name: LOG_LEVEL
              valueFrom:
                configMapKeyRef:
                  name: order-service-config
                  key: log-level
          
          # Graceful shutdown
          lifecycle:
            preStop:
              exec:
                # Sleep before shutdown to allow iptables rules to propagate
                # (Kubernetes updates kube-proxy rules slightly after pod is marked terminating)
                command: ["/bin/sh", "-c", "sleep 5"]
      
      # How long to wait before forcefully killing (SIGKILL)
      terminationGracePeriodSeconds: 60
```

### Service and Ingress

```yaml
apiVersion: v1
kind: Service
metadata:
  name: order-service
spec:
  selector:
    app: order-service    # routes to pods with this label
  ports:
    - port: 80            # service port (what clients call)
      targetPort: 8080    # container port (what pods listen on)
  type: ClusterIP         # internal only (use LoadBalancer for external)

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  ingressClassName: nginx
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /orders(/|$)(.*)
            pathType: Prefix
            backend:
              service:
                name: order-service
                port:
                  number: 80
          - path: /users(/|$)(.*)
            pathType: Prefix
            backend:
              service:
                name: user-service
                port:
                  number: 80
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: order-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-service
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70    # scale up when avg CPU > 70%
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

---

## 9. CI/CD with GitHub Actions

### Complete Pipeline: Lint → Test → Build → Push → Deploy

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ─── Lint ────────────────────────────────────────────────────────────────────
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true
      
      - name: Run golangci-lint
        uses: golangci/golangci-lint-action@v4
        with:
          version: latest
          args: --timeout=5m

  # ─── Test ─────────────────────────────────────────────────────────────────────
  test:
    name: Test
    runs-on: ubuntu-latest
    needs: lint
    
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true
      
      - name: Run tests
        env:
          DATABASE_URL: postgres://test:test@localhost:5432/testdb?sslmode=disable
        run: go test -v -race -coverprofile=coverage.out ./...
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.out

  # ─── Build & Push ─────────────────────────────────────────────────────────────
  build:
    name: Build & Push Docker Image
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    permissions:
      contents: read
      packages: write
    
    outputs:
      image: ${{ steps.image.outputs.image }}
      digest: ${{ steps.build.outputs.digest }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}   # automatic, no manual secret needed
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=sha-
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          # Cache from/to GitHub Actions cache (layer caching in CI)
          cache-from: type=gha
          cache-to: type=gha,mode=max
          # Build args
          build-args: |
            VERSION=${{ github.sha }}
      
      - name: Output image reference
        id: image
        run: |
          echo "image=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }}" >> $GITHUB_OUTPUT
      
      # Scan for CVEs after build
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          exit-code: '1'
          severity: 'HIGH,CRITICAL'
          ignore-unfixed: true

  # ─── Deploy ───────────────────────────────────────────────────────────────────
  deploy:
    name: Deploy to Kubernetes
    runs-on: ubuntu-latest
    needs: build
    environment: production   # requires manual approval in GitHub
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
      
      - name: Configure kubeconfig
        run: |
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > kubeconfig
          echo "KUBECONFIG=kubeconfig" >> $GITHUB_ENV
      
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/order-service \
            order-service=${{ needs.build.outputs.image }} \
            --record
          
          # Wait for rollout to complete
          kubectl rollout status deployment/order-service --timeout=5m
      
      - name: Verify deployment
        run: |
          kubectl get pods -l app=order-service
          kubectl rollout history deployment/order-service
```

### Matrix Testing (Multiple Versions)

```yaml
jobs:
  test:
    strategy:
      matrix:
        go-version: ['1.21', '1.22']
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/setup-go@v5
        with:
          go-version: ${{ matrix.go-version }}
      - run: go test ./...
```

---

## 10. Deployment Strategies

### Rolling Update (Default in Kubernetes)

New pods replace old pods gradually. At any point, both old and new versions are running.

```
Before update (3 replicas, v1):
  [v1] [v1] [v1]

Step 1 (maxSurge=1, maxUnavailable=1):
  [v1] [v1] [v2]    ← start 1 new pod

Step 2:
  [v1] [v2] [v2]    ← terminate 1 old pod

Step 3:
  [v2] [v2] [v2]    ← done

Traffic during update: both v1 and v2 receive requests
```

**Pros:** Zero downtime; automatic rollback if new pods fail health checks
**Cons:** Both versions run simultaneously; requires backward-compatible changes (DB schema, API)

### Blue-Green Deployment

Two identical environments: Blue (current production) and Green (new version). Traffic switches all at once.

```
          Load Balancer
               │
               ▼
        ┌─────────────┐
        │  Blue (v1)  │ ◄── 100% of traffic
        │  [v1][v1]   │
        └─────────────┘

New version deployed to Green (idle):
        ┌─────────────┐
        │  Green (v2) │ ◄── 0% of traffic (being tested)
        │  [v2][v2]   │
        └─────────────┘

After verification, switch traffic:
        ┌─────────────┐
        │  Blue (v1)  │ ◄── 0% (kept for instant rollback)
        └─────────────┘
        ┌─────────────┐
        │  Green (v2) │ ◄── 100% of traffic
        └─────────────┘

Rollback: switch traffic back to Blue (instant!)
```

**Pros:** Instant rollback; no mixed versions during switchover; easy to test in production before going live
**Cons:** Double the infrastructure cost; database migrations must be backward-compatible (both versions share DB)

### Canary Deployment

Send a small percentage of traffic to the new version, monitor, then gradually increase.

```
Stage 1: Canary at 5%
  ┌─────────────────────────────────────────┐
  │  v1 (95%)     [v1][v1][v1][v1][v1][v1] │
  │  v2 (5%)      [v2]                      │
  └─────────────────────────────────────────┘
  Monitor: error rate, latency, business metrics

Stage 2: Canary at 25% (if stage 1 looks good)
  ┌─────────────────────────────────────────┐
  │  v1 (75%)     [v1][v1][v1]              │
  │  v2 (25%)     [v2]                      │
  └─────────────────────────────────────────┘

Stage 3: Full rollout 100%
  [v2][v2][v2][v2]
```

**Pros:** Real production traffic tests the new version; limited blast radius if v2 has a bug; data-driven rollout decision
**Cons:** Complex traffic splitting infrastructure (Istio, Argo Rollouts, NGINX weight annotations); both versions must be compatible for extended periods

### Kubernetes Canary with Nginx Ingress

```yaml
# Stable deployment (95% traffic)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: order-service-stable
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /orders
            backend:
              service:
                name: order-service-stable
                port:
                  number: 80

---
# Canary deployment (5% traffic)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: order-service-canary
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "5"   # 5% traffic
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /orders
            backend:
              service:
                name: order-service-canary
                port:
                  number: 80
```

---

## 11. How It Works Internally

### Docker Build Process

```
docker build -t myapp .

1. Docker CLI sends build context to Docker daemon
   (all files not in .dockerignore are sent)

2. Daemon processes each Dockerfile instruction:
   ┌──────────────────────────────────────────────┐
   │ FROM node:20-alpine                          │
   │  → Pull base image (or use cached)           │
   │                                              │
   │ COPY package*.json ./                        │
   │  → Check cache key (hash of instruction +    │
   │    files being copied)                       │
   │  → If cache hit: use cached layer            │
   │  → If cache miss: create new layer           │
   │                                              │
   │ RUN npm ci                                   │
   │  → Run command in a temporary container      │
   │  → Commit result as new layer                │
   └──────────────────────────────────────────────┘

3. Final image = stack of all layers
4. Tag and store in local registry
5. (Optional) docker push sends to remote registry
```

### CI/CD Pipeline Flow

```
Developer pushes code to GitHub
             │
             ▼
    ┌──────────────────┐
    │  GitHub Actions  │
    │  (trigger: push) │
    └────────┬─────────┘
             │
     ┌───────┴────────┐
     │   Job: lint    │
     │  golangci-lint │
     └───────┬────────┘
             │ pass
     ┌───────▼────────┐
     │   Job: test    │
     │  go test -race │
     │  (with Postgres│
     │   service)     │
     └───────┬────────┘
             │ pass
     ┌───────▼──────────────┐
     │   Job: build         │
     │  docker buildx build │
     │  push to GHCR        │
     │  trivy scan          │
     └───────┬──────────────┘
             │ pass + manual approval
     ┌───────▼──────────────┐
     │   Job: deploy        │
     │  kubectl set image   │
     │  kubectl rollout     │
     │  status (wait)       │
     └───────┬──────────────┘
             │ success
             ▼
        Deployment complete
        (or rollback if health checks fail)
```

---

## 12. Implementation Examples

### Go + Chi: Production Dockerfile

```dockerfile
# Dockerfile.go
FROM golang:1.22-alpine AS builder

ARG VERSION=dev
ARG COMMIT=unknown

RUN apk add --no-cache git ca-certificates tzdata

WORKDIR /app

# Download dependencies (cached separately)
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# Build
COPY . .
RUN --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build \
    -ldflags="-w -s -X main.version=${VERSION} -X main.commit=${COMMIT}" \
    -trimpath \
    -o /server \
    ./cmd/server

# ── Runtime ──────────────────────────────────────
FROM gcr.io/distroless/static-debian12

# Include timezone data (for time.LoadLocation to work)
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy binary
COPY --from=builder /server /server

# Non-root (nobody)
USER 65534:65534

EXPOSE 8080

ENTRYPOINT ["/server"]
```

### Node.js + Express: GitHub Actions Workflow

```yaml
# .github/workflows/node-ci.yml
name: Node.js CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ci:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        node-version: [20.x, 22.x]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'   # caches ~/.npm
      
      - name: Install dependencies
        run: npm ci   # use ci not install (reproducible)
      
      - name: Lint
        run: npm run lint
      
      - name: Type check
        run: npm run type-check
      
      - name: Test
        run: npm test -- --coverage
        env:
          NODE_ENV: test
      
      - name: Build
        run: npm run build

  docker:
    needs: ci
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Python + FastAPI: Complete Dockerfile and Compose

```dockerfile
# Dockerfile.python
# ─── Build stage ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps needed to compile some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, install wheel
RUN pip install --upgrade pip wheel

# Install Python dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# ─── Runtime stage ──────────────────────────────────────────
FROM python:3.12-slim AS runtime

# System dependencies for runtime (not build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --system --create-home --shell /bin/false appuser

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy app
COPY --chown=appuser:appuser app/ ./app/

USER appuser

EXPOSE 8000

# Use exec form; --no-access-log in prod (use structured logging middleware instead)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--no-access-log"]
```

```yaml
# docker-compose.dev.yml (development override)
version: '3.9'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.python
      target: builder   # use builder stage (has dev tools)
    command: ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    volumes:
      - ./app:/app/app   # hot-reload: code changes reflect immediately
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/appdb
      - ENVIRONMENT=development
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: appdb
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 5s
      retries: 5
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

---

## 13. Common Patterns & Best Practices

### Immutable Tags

Never use `:latest` for production deployments. Always use content-addressable tags (git SHA, semantic version).

```bash
# ❌ Mutable, unpredictable
docker pull myapp:latest

# ✅ Immutable, auditable
docker pull myapp:sha-a3f2b1c
docker pull myapp:v1.2.3

# ✅ Even better: use digest (image hash)
docker pull myapp@sha256:abc123...
```

### One Process Per Container

Each container should run a single process. Don't run nginx AND your app in the same container. This violates the single-responsibility principle and makes health checks, scaling, and logging harder.

```
# ❌ Multiple processes in one container
CMD: supervisord → [nginx, app, cron]

# ✅ Separate containers
Container 1: nginx (reverse proxy / static files)
Container 2: app
Container 3: cron job (Kubernetes CronJob)
```

### Init Containers (Kubernetes)

Use init containers for pre-startup tasks (database migrations, config file generation):

```yaml
spec:
  initContainers:
    - name: run-migrations
      image: myapp:sha-abc123
      command: ["./migrate", "up"]
      env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
  containers:
    - name: app
      image: myapp:sha-abc123
      # app only starts after migrations succeed
```

---

## 14. Common Pitfalls

### 1. Using :latest Tag in Production

`:latest` is mutable. You can't tell which code is running, and `kubectl rollout undo` might not work correctly. Always use immutable tags.

### 2. Copying Source Before Dependencies

```dockerfile
# ❌ — code copy invalidates npm ci cache on every change
COPY . .
RUN npm ci

# ✅ — npm ci is cached unless package.json changes
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
```

### 3. Running as Root

The default in most base images. Always add a non-root user.

### 4. Large Docker Build Context

Not having `.dockerignore`. Sending `node_modules/` (500MB) to the Docker daemon on every build.

### 5. Not Setting Resource Requests/Limits

Without `requests`, the scheduler places pods on nodes without knowing their needs. Without `limits`, a buggy pod can consume all node resources and starve neighbors.

### 6. Not Waiting for Dependencies

App crashes immediately because PostgreSQL isn't ready yet. Always use readiness probes and `depends_on: condition: service_healthy` in Compose. Use init containers or retry logic in Kubernetes.

### 7. Secrets in ENV Instructions

```dockerfile
# ❌ Secrets baked into image layers FOREVER (even if overwritten in later layer)
ENV API_KEY=supersecret

# ✅ Pass secrets at runtime via environment variables
docker run -e API_KEY=$API_KEY myapp
```

---

## 15. Interview Questions & Answers

**Q: What is the difference between a container and a VM?**

A VM virtualizes hardware and runs a complete guest OS kernel. Containers share the host OS kernel and use Linux namespaces (pid, net, mnt, uts) for isolation and cgroups for resource limits. Containers start in milliseconds (just a process), are typically 5–500 MB, and share the host kernel (more efficient but weaker isolation). VMs take 30s–3min to start, are 1–20 GB, but provide stronger isolation with a separate kernel. Containers are preferred for services; VMs for untrusted code or compliance-mandated isolation.

---

**Q: What is a multi-stage Docker build and why do you use it?**

A multi-stage build uses multiple `FROM` instructions in a Dockerfile. Each stage is a separate build environment. The key benefit: you use a large "builder" image (with build tools, compilers, dev dependencies) to compile your artifact, then `COPY --from=builder` only the compiled artifact into a minimal "runtime" image. The final image doesn't contain build tools, source code, or dev dependencies — only what's needed to run. A Go service goes from ~800 MB (golang:1.22) to ~10 MB (scratch + binary).

---

**Q: What is layer caching in Docker and how do you optimize it?**

Each Dockerfile instruction creates an immutable layer. Docker caches layers: if an instruction and its inputs haven't changed, it reuses the cached layer instead of re-executing. Optimization: order instructions from least-likely-to-change to most-likely-to-change. Always copy dependency files (package.json, go.mod, requirements.txt) and install dependencies BEFORE copying source code. This way, a code change doesn't invalidate the expensive dependency installation layer — it's only invalidated when dependencies actually change.

---

**Q: What is the difference between CMD and ENTRYPOINT in a Dockerfile?**

`ENTRYPOINT` defines the command that always runs. `CMD` provides default arguments that can be overridden. With `ENTRYPOINT ["node"]` and `CMD ["server.js"]`, running `docker run myapp` executes `node server.js`. Running `docker run myapp worker.js` executes `node worker.js` (CMD overridden). Use exec form (`["executable"]`) for both — shell form (`command`) starts a shell as PID 1, which won't forward signals to your app, breaking graceful shutdown.

---

**Q: Explain rolling vs blue-green vs canary deployment.**

**Rolling:** New pods replace old pods gradually (e.g., 1 at a time). Zero downtime, but both versions receive traffic simultaneously — requires backward-compatible changes. Default in Kubernetes.

**Blue-green:** Maintain two identical environments. Deploy new version to idle environment, test it, then switch all traffic at once. Instant rollback possible. Costs double the infrastructure. Good when you need testing in production before go-live.

**Canary:** Send a small percentage of traffic (5%) to new version. Monitor error rate, latency, business metrics. Gradually increase traffic. Limits blast radius if the new version has bugs. Requires traffic splitting infrastructure (Nginx weights, Istio, Argo Rollouts). Best for high-traffic systems where catching issues early is critical.

---

**Q: Why should you not run containers as root?**

Container root (UID 0) maps to root on the host if the container breaks out of its namespace (container escape vulnerabilities exist). A compromised container running as root can potentially write to host filesystems, access secrets, or affect other containers. Running as a non-root user limits the blast radius of a container compromise. Additionally, some security policies and Kubernetes admission controllers block root containers entirely.

---

## 16. Resources

- [Docker Documentation — Dockerfile reference](https://docs.docker.com/reference/dockerfile/)
- [Docker Documentation — Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Kubernetes — Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes — Configure Liveness, Readiness, Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [GitHub Actions — Quickstart](https://docs.github.com/en/actions/quickstart)
- [Trivy — Container Scanner](https://github.com/aquasecurity/trivy)
- [Google — Distroless containers](https://github.com/GoogleContainerTools/distroless)
- [Argo Rollouts — Canary deployments](https://argo-rollouts.readthedocs.io/)

---

**Next:** [Part 16.2: Graceful Shutdown & Production Patterns](./16-graceful-shutdown-production.md)
