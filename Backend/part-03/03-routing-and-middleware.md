# Part 3.1: Routing & Middleware

## What You'll Learn
- How HTTP routers match URLs — path parameters, wildcards, regex constraints, and specificity rules
- Route groups and sub-routers for modular, maintainable code organization
- How middleware works conceptually and mechanically (the onion/chain model)
- Middleware execution order and why it critically matters
- Writing production-grade custom middleware: auth, request ID, structured logging, CORS
- Context propagation — passing data from middleware to handlers safely in Go, Node, and Python
- Scoped vs global middleware and when to use each
- Deep comparison of Go routers: chi vs net/http ServeMux (Go 1.22+) vs Gin vs Echo

---

## Table of Contents

1. [HTTP Routing Fundamentals](#1-http-routing-fundamentals)
2. [Path Parameters, Wildcards & Regex Constraints](#2-path-parameters-wildcards--regex-constraints)
3. [Route Groups and Sub-Routers](#3-route-groups-and-sub-routers)
4. [Method-Based Routing](#4-method-based-routing)
5. [Route Ordering and Specificity](#5-route-ordering-and-specificity)
6. [Router Comparison: chi vs ServeMux vs Gin vs Echo](#6-router-comparison-chi-vs-servemux-vs-gin-vs-echo)
7. [Middleware — The Concept](#7-middleware--the-concept)
8. [The Onion Model (Middleware Execution Order)](#8-the-onion-model-middleware-execution-order)
9. [Built-in Middleware You Should Always Use](#9-built-in-middleware-you-should-always-use)
10. [Writing Custom Middleware](#10-writing-custom-middleware)
11. [Scoped Middleware](#11-scoped-middleware)
12. [Short-Circuit Pattern](#12-short-circuit-pattern)
13. [Context Propagation](#13-context-propagation)
14. [Full Implementation Examples](#14-full-implementation-examples)
15. [Common Patterns & Best Practices](#common-patterns--best-practices)
16. [Common Pitfalls](#common-pitfalls)
17. [Interview Questions](#interview-questions)
18. [Resources](#resources)

---

## 1. HTTP Routing Fundamentals

An HTTP router's job is deceptively simple: take an incoming request (`method + path`) and dispatch it to the right handler function. But how it does that — and how well it does it — varies enormously between frameworks.

Every HTTP server boils down to a function: `(Request) → Response`. A router is just a dispatch table that maps `(method, path pattern)` → `handler`.

```
Incoming Request: GET /users/42/posts?page=2
                        ↓
              Router Pattern Matching
                        ↓
        Match: GET /users/{id}/posts → handler
                        ↓
        Extract: id = "42", query: page = "2"
                        ↓
              Execute handler(w, r)
```

### What Makes a Good Router?

| Concern | Question to ask |
|---|---|
| **Performance** | Does it use a trie/radix tree, or linear scan? |
| **Feature set** | Wildcards, named params, regex, catch-all? |
| **Middleware support** | Per-route? Per-group? Global? |
| **Conflict detection** | Does it panic on ambiguous routes? |
| **Stdlib compatibility** | Does it use `http.Handler` / `http.HandlerFunc`? |

---

## 2. Path Parameters, Wildcards & Regex Constraints

### Named Path Parameters

Named parameters capture a segment of the URL path into a named variable.

```
Pattern:  /users/{id}
URL:      /users/42         → id = "42"
URL:      /users/abc        → id = "abc"
URL:      /users/           → NO MATCH (empty segment)
URL:      /users/42/profile → NO MATCH (extra segment)
```

### Wildcards and Catch-All Routes

A catch-all wildcard captures everything after a prefix, including slashes.

```
Pattern:  /files/*          (chi syntax)
URL:      /files/a/b/c.txt  → wildcard = "a/b/c.txt"

Pattern:  /static/*filepath (ServeMux Go 1.22+)
URL:      /static/js/app.js → filepath = "js/app.js"
```

### Regex Constraints

Some routers let you constrain path parameters with regex patterns:

```
Chi:         /users/{id:[0-9]+}     → only numeric IDs
Gin:         /users/:id             → no built-in regex (workaround needed)
Echo:        /users/:id<[0-9]+>     → regex constraint
```

**Why constraints matter in interviews:** Without them, `/users/abc` hits your `/users/{id}` route and you silently try to parse `"abc"` as an integer. Fail early at the routing layer, not in your handler.

### Chi Pattern Syntax Reference

```
{id}              Named parameter — one segment, no slashes
{id:[0-9]+}       Named parameter with regex constraint
*                 Wildcard — zero or more segments, including slashes
/prefix/*         Catch-all under prefix
```

---

## 3. Route Groups and Sub-Routers

Route groups let you organize routes with a shared prefix and shared middleware. This is critical for large codebases.

### Why Route Groups?

Without groups, you end up repeating yourself:
```
router.Get("/api/v1/users", listUsers)
router.Post("/api/v1/users", createUser)
router.Get("/api/v1/users/{id}", getUser)
router.Get("/api/v1/posts", listPosts)
```

With groups:
```go
r.Route("/api/v1", func(r chi.Router) {
    r.Route("/users", func(r chi.Router) {
        r.Get("/", listUsers)
        r.Post("/", createUser)
        r.Get("/{id}", getUser)
    })
    r.Route("/posts", func(r chi.Router) {
        r.Get("/", listPosts)
    })
})
```

### Sub-Routers vs Route Groups

| | Route Group | Sub-Router |
|---|---|---|
| **Definition** | Inline, within parent router scope | Separate router mounted at a path |
| **Middleware** | Inherits parent + can add scoped | Fully independent middleware chain |
| **Mounting** | `r.Route("/prefix", fn)` | `r.Mount("/prefix", subRouter)` |
| **Use case** | Feature grouping | Reusable module (e.g., admin panel) |

```go
// Sub-router: useful for mounting a self-contained module
adminRouter := chi.NewRouter()
adminRouter.Use(requireAdminMiddleware)
adminRouter.Get("/dashboard", adminDashboard)
adminRouter.Get("/users", adminListUsers)

// Mount it at /admin
r.Mount("/admin", adminRouter)
```

---

## 4. Method-Based Routing

HTTP methods (verbs) carry semantic meaning per REST conventions. Your router should enforce method constraints.

| Method | Semantics | Safe? | Idempotent? |
|---|---|---|---|
| GET | Read resource | ✓ | ✓ |
| POST | Create resource | ✗ | ✗ |
| PUT | Replace resource | ✗ | ✓ |
| PATCH | Partial update | ✗ | ✗* |
| DELETE | Remove resource | ✗ | ✓ |
| HEAD | Like GET, no body | ✓ | ✓ |
| OPTIONS | Describe capabilities | ✓ | ✓ |

*PATCH can be made idempotent with proper design, but isn't by default.

**Idempotent** means calling it N times has the same effect as calling it once. This matters for retries and distributed systems.

### What happens when method doesn't match?

A well-behaved router returns `405 Method Not Allowed` with an `Allow` header listing valid methods for that path. chi does this automatically. A naive router might return `404 Not Found` instead, which confuses clients.

```
GET  /users/42   → handler
POST /users/42   → 405 Method Not Allowed, Allow: GET, PUT, DELETE
```

---

## 5. Route Ordering and Specificity

This is where bugs hide. When two patterns could match the same URL, which wins?

### chi: First Registered Wins (mostly)
chi uses a radix tree (compressed prefix trie). More specific routes take precedence over parameterized routes automatically at the same depth:

```go
r.Get("/users/me", getCurrentUser)   // Specific: matches /users/me exactly
r.Get("/users/{id}", getUserByID)    // Parameterized: matches /users/anything

// GET /users/me → getCurrentUser  (specific wins)
// GET /users/42 → getUserByID     (parameterized fallback)
```

### The Radix Tree Advantage

A **radix tree** (also called Patricia trie) is a compressed trie where each node stores a common prefix. This enables O(k) lookup where k = length of path, regardless of number of routes.

```
Routes registered:
  /users/
  /users/{id}
  /users/me
  /posts/
  /posts/{id}

Radix tree structure:
    root
    ├── /users/
    │   ├── me          → getCurrentUser
    │   └── {id}        → getUserByID  (fallback)
    └── /posts/
        └── {id}        → getPostByID
```

### Conflict Example (Important for Interviews)

```
/users/{id}           matches /users/42
/users/{username}     CONFLICT — both match /users/anything

chi panics at startup on this. Good. You want to know early.
```

---

## 6. Router Comparison: chi vs ServeMux vs Gin vs Echo

This is a classic interview topic at companies using Go. Know why your team chose chi.

### net/http ServeMux (Go 1.22+)

Go 1.22 dramatically improved the standard library's `ServeMux`:

```go
// Go 1.22+ ServeMux
mux := http.NewServeMux()
mux.HandleFunc("GET /users/{id}", getUserHandler)
mux.HandleFunc("POST /users", createUserHandler)
mux.HandleFunc("GET /files/{path...}", fileHandler) // wildcard
```

**New in Go 1.22:**
- Method matching in the pattern (`GET /path`)
- Named path parameters `{name}`
- Wildcard `{name...}` for catch-all
- Exact match with trailing slash distinction

**Still missing in ServeMux:**
- Middleware groups/scoping
- Route-level middleware composition
- Regex constraints on parameters
- Named route URL generation

### chi

chi wraps stdlib's `net/http` interfaces. Every chi handler is an `http.Handler`. This is chi's superpower.

```go
// chi middleware is just http.Handler composition
type Middleware func(http.Handler) http.Handler
```

**chi advantages over ServeMux:**
- `r.Route()` groups with scoped middleware
- `r.Mount()` for sub-routers
- Rich built-in middleware package (`chi/middleware`)
- Inline URL parameter extraction: `chi.URLParam(r, "id")`
- Pattern conflict detection at startup
- `r.MethodNotAllowed()` custom handler

**Why chi "stays close to stdlib":**
- chi handlers are `http.HandlerFunc` — no framework lock-in
- You can mount any `http.Handler` in chi (including stdlib mux, other frameworks)
- Third-party middleware written for `http.Handler` works with chi
- `net/http` knowledge transfers directly

### Gin

```go
// Gin: faster, but breaks stdlib interface
r := gin.Default()
r.GET("/users/:id", func(c *gin.Context) {
    id := c.Param("id")
    c.JSON(200, gin.H{"id": id})
})
```

**Gin vs chi:**
| | chi | Gin |
|---|---|---|
| **Handler type** | `http.HandlerFunc` | `gin.HandlerFunc` |
| **Performance** | Fast (radix tree) | Very fast (httprouter) |
| **Stdlib compat** | ✓ Full | ✗ Partial |
| **Middleware** | `func(http.Handler) http.Handler` | `gin.HandlerFunc` |
| **Context** | `r.Context()` (stdlib) | `*gin.Context` (custom) |
| **Lock-in** | Low | High |

### Echo

```go
// Echo: similar to Gin
e := echo.New()
e.GET("/users/:id", func(c echo.Context) error {
    id := c.Param("id")
    return c.JSON(200, map[string]string{"id": id})
})
```

### Summary Recommendation

- **chi**: Best for teams that value stdlib compatibility and long-term maintainability. No vendor lock-in. Best for FAANG-style codebases.
- **Gin**: Best for raw performance when you're doing benchmarks or very high RPS (100k+/s) on a single node.
- **Echo**: Similar to Gin but with slightly cleaner API.
- **ServeMux (1.22+)**: Now viable for simple services without complex middleware needs.

---

## 7. Middleware — The Concept

Middleware is a function that wraps an HTTP handler to add cross-cutting behavior — logging, auth, rate limiting — without polluting your business logic.

In Go's `net/http` model, a middleware has this exact signature:

```go
type Middleware func(http.Handler) http.Handler
```

That's it. A middleware is a function that takes a handler and returns a new handler. The new handler can:
1. Do something **before** the inner handler (inspect request, add headers, reject early)
2. **Call the inner handler** (or not, for short-circuit)
3. Do something **after** the inner handler (inspect response, log, finalize)

```go
func LoggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        // BEFORE: record start time
        
        next.ServeHTTP(w, r)  // call inner handler
        
        // AFTER: log duration
        log.Printf("%s %s %v", r.Method, r.URL.Path, time.Since(start))
    })
}
```

This is the **decorator pattern** applied to HTTP handlers.

---

## 8. The Onion Model (Middleware Execution Order)

This is the most-asked middleware concept in interviews. Understand it deeply.

```
                    ┌─────────────────────────────────────────────────────┐
                    │                                                       │
  HTTP Request ──►  │  Logger ──► RequestID ──► CORS ──► Auth ──► Handler │
                    │                                                       │
  HTTP Response ◄── │  Logger ◄── RequestID ◄── CORS ◄── Auth ◄── Handler │
                    │                                                       │
                    └─────────────────────────────────────────────────────┘

Middleware wraps the next handler, like layers of an onion:

  ┌─ Logger ─────────────────────────────────────────────────────┐
  │  ┌─ RequestID ──────────────────────────────────────────┐    │
  │  │  ┌─ CORS ───────────────────────────────────────┐    │    │
  │  │  │  ┌─ Auth ────────────────────────────────┐   │    │    │
  │  │  │  │  ┌─ RateLimit ───────────────────┐    │   │    │    │
  │  │  │  │  │                               │    │   │    │    │
  │  │  │  │  │         Handler               │    │   │    │    │
  │  │  │  │  │                               │    │   │    │    │
  │  │  │  │  └───────────────────────────────┘    │   │    │    │
  │  │  │  └───────────────────────────────────────┘   │    │    │
  │  │  └─────────────────────────────────────────────┘    │    │
  │  └────────────────────────────────────────────────────┘    │
  └──────────────────────────────────────────────────────────────┘

Execution order for a request:
  1. Logger.before
  2. RequestID.before
  3. CORS.before
  4. Auth.before
  5. RateLimit.before
  6. Handler executes
  7. RateLimit.after
  8. Auth.after
  9. CORS.after
  10. RequestID.after
  11. Logger.after   ← can now log status code + duration

The LAST middleware registered wraps the handler most tightly.
The FIRST middleware registered is the outermost layer.
```

### Why Does Order Matter?

**Example 1: Logger must be outermost**
If Logger is not the first middleware, it misses the duration of middlewares that run before it.

**Example 2: CORS must come before Auth**
A browser CORS preflight (`OPTIONS`) request has no auth credentials. If Auth runs before CORS, the preflight gets rejected with 401, and your browser never sees the CORS headers. The fix: handle OPTIONS / add CORS headers before Auth checks credentials.

```
WRONG order:  Auth → CORS → Handler
  OPTIONS /api/users → Auth rejects (no token) → browser gets 401, no CORS headers
  Browser: "CORS error" (misleading!)

CORRECT order: CORS → Auth → Handler
  OPTIONS /api/users → CORS handles it, returns 204 with CORS headers
  Browser: "OK, I can proceed with POST /api/users with token"
```

**Example 3: Timeout must wrap everything**
Timeout middleware needs to wrap the handler AND all inner middlewares so the total time budget includes all processing.

**Example 4: Recovery (panic handler) should be early**
If recovery is inner, a panic in an outer middleware is uncaught.

### The Golden Middleware Order

```
1. RequestID     — inject before anything so all logs have correlation ID
2. Logger        — outermost so it captures total latency including all middleware
3. Recoverer     — catches panics in anything below
4. RealIP        — set real client IP from X-Forwarded-For before any logging
5. Timeout       — set deadline for the entire request pipeline
6. CORS          — must be before Auth so OPTIONS preflights are handled
7. Auth          — must know real IP for auditing; CORS headers already set
8. RateLimit     — after Auth so you can rate limit per user, not per IP
9. Handler       
```

---

## 9. Built-in Middleware You Should Always Use

chi provides these in `github.com/go-chi/chi/v5/middleware`:

### RequestID
Assigns a unique ID to every request. Critical for distributed tracing and log correlation.
```
X-Request-Id: 01HXYZ1234567890ABCDEFGH
```

### Logger
Structured request logging. Don't write your own from scratch.

### Recoverer
Catches panics in handlers, logs a stack trace, and returns `500 Internal Server Error` instead of crashing the process. **Always include this.**

### Timeout
Sets a deadline on the request context. After the deadline, `r.Context().Done()` is closed. Handlers that respect context cancellation will abort. Handlers that don't will still complete, but the response is already sent.

```go
r.Use(middleware.Timeout(30 * time.Second))
```

### RealIP
Extracts the real client IP from `X-Real-IP` or `X-Forwarded-For` headers (set by your load balancer/proxy) and sets `r.RemoteAddr`.

### CORS
Cross-Origin Resource Sharing — controls which origins can make requests. Use `github.com/go-chi/cors`.

---

## 10. Writing Custom Middleware

### The Pattern (Go)

```go
func MyMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // PRE-processing

        next.ServeHTTP(w, r) // pass to next

        // POST-processing
    })
}
```

### Middleware with Configuration (Closure Pattern)

When your middleware needs configuration options, return a Middleware from a factory function:

```go
func RateLimiter(requestsPerSecond int) func(http.Handler) http.Handler {
    limiter := rate.NewLimiter(rate.Limit(requestsPerSecond), requestsPerSecond)
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            if !limiter.Allow() {
                http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
                return
            }
            next.ServeHTTP(w, r)
        })
    }
}

// Usage:
r.Use(RateLimiter(100))
```

---

## 11. Scoped Middleware

Scoped middleware applies only to a specific route group, not globally. This is essential for clean architecture.

**Example: Apply auth only to protected routes**

```
/health     → no auth needed (k8s probes, monitoring)
/metrics    → no auth needed (or separate auth)
/api/v1/*   → auth required
/auth/login → no auth (this IS the auth endpoint)
```

```go
r := chi.NewRouter()
r.Use(middleware.Logger)     // global
r.Use(middleware.Recoverer)  // global

r.Get("/health", healthHandler)  // no auth

r.Route("/api/v1", func(r chi.Router) {
    r.Use(AuthMiddleware)         // scoped to /api/v1/*
    r.Use(RateLimitMiddleware)    // scoped to /api/v1/*

    r.Get("/users", listUsers)
    r.Post("/users", createUser)
})
```

---

## 12. Short-Circuit Pattern

A middleware that returns early without calling `next.ServeHTTP()` has **short-circuited** the chain. Nothing below it executes.

```go
func AuthMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        token := r.Header.Get("Authorization")
        if token == "" {
            // SHORT CIRCUIT: don't call next
            http.Error(w, "unauthorized", http.StatusUnauthorized)
            return  // ← critical: must return after writing response
        }
        
        // Validated; pass to next handler
        next.ServeHTTP(w, r)
    })
}
```

**Common bug:** Forgetting the `return` after writing the error response. Without it, execution continues and `next.ServeHTTP()` is called anyway, leading to "superfluous response.WriteHeader call" panics or double responses.

---

## 13. Context Propagation

When middleware extracts data (user identity, request ID, tenant), it needs to pass it to handlers. In Go, this is done through `context.Context` attached to the request.

### Type-Safe Context Keys (Important Interview Topic)

**WRONG — using a plain string key:**
```go
// Any package can accidentally use the same key!
ctx = context.WithValue(ctx, "userID", user.ID)
// Collision risk: another middleware uses ctx.Value("userID")
```

**CORRECT — using an unexported type:**
```go
// In your auth package:
type contextKey string  // unexported type

const (
    contextKeyUser      contextKey = "user"
    contextKeyRequestID contextKey = "requestID"
)

// Set:
ctx = context.WithValue(ctx, contextKeyUser, user)

// Get (type assertion):
user, ok := r.Context().Value(contextKeyUser).(*User)
```

**Why unexported type?**
Because `contextKey("user") != string("user")`. The Go context package compares keys by type AND value. An unexported type from package `auth` cannot be accessed by package `billing` even if they both use the string `"user"` — the types are different.

This prevents accidental collisions between middleware packages from different teams.

### Helper Functions Pattern

Wrap context access in typed helper functions to avoid scattering type assertions everywhere:

```go
// auth/context.go
package auth

type contextKey string
const contextKeyUser contextKey = "user"

// SetUser stores user in context — called by middleware
func SetUser(r *http.Request, user *User) *http.Request {
    ctx := context.WithValue(r.Context(), contextKeyUser, user)
    return r.WithContext(ctx)
}

// GetUser retrieves user from context — called by handlers
func GetUser(r *http.Request) (*User, bool) {
    user, ok := r.Context().Value(contextKeyUser).(*User)
    return user, ok
}
```

---

## 14. Full Implementation Examples

### Go + Chi Router

```go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "log/slog"
    "net/http"
    "os"
    "strings"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"
    "github.com/go-chi/cors"
    "github.com/golang-jwt/jwt/v5"
)

// --------------------------------------------------------------------------
// Domain types
// --------------------------------------------------------------------------

type User struct {
    ID    string `json:"id"`
    Email string `json:"email"`
    Role  string `json:"role"`
}

// --------------------------------------------------------------------------
// Context keys — unexported type prevents collisions
// --------------------------------------------------------------------------

type contextKey string

const (
    contextKeyUser      contextKey = "user"
    contextKeyRequestID contextKey = "requestID"
)

func SetUser(r *http.Request, u *User) *http.Request {
    return r.WithContext(context.WithValue(r.Context(), contextKeyUser, u))
}

func GetUser(r *http.Request) (*User, bool) {
    u, ok := r.Context().Value(contextKeyUser).(*User)
    return u, ok
}

// --------------------------------------------------------------------------
// Custom structured logger middleware
// --------------------------------------------------------------------------

type statusRecorder struct {
    http.ResponseWriter
    status int
    size   int
}

func (sr *statusRecorder) WriteHeader(status int) {
    sr.status = status
    sr.ResponseWriter.WriteHeader(status)
}

func (sr *statusRecorder) Write(b []byte) (int, error) {
    n, err := sr.ResponseWriter.Write(b)
    sr.size += n
    return n, err
}

func StructuredLogger(logger *slog.Logger) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            start := time.Now()
            sr := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

            next.ServeHTTP(sr, r)

            logger.InfoContext(r.Context(), "request",
                slog.String("method", r.Method),
                slog.String("path", r.URL.Path),
                slog.Int("status", sr.status),
                slog.Int("bytes", sr.size),
                slog.Duration("latency", time.Since(start)),
                slog.String("request_id", middleware.GetReqID(r.Context())),
                slog.String("remote_addr", r.RemoteAddr),
            )
        })
    }
}

// --------------------------------------------------------------------------
// JWT Auth middleware
// --------------------------------------------------------------------------

var jwtSecret = []byte(os.Getenv("JWT_SECRET"))

type jwtClaims struct {
    UserID string `json:"sub"`
    Email  string `json:"email"`
    Role   string `json:"role"`
    jwt.RegisteredClaims
}

func AuthMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        authHeader := r.Header.Get("Authorization")
        if authHeader == "" {
            http.Error(w, `{"error":"missing authorization header"}`, http.StatusUnauthorized)
            return
        }

        parts := strings.SplitN(authHeader, " ", 2)
        if len(parts) != 2 || !strings.EqualFold(parts[0], "bearer") {
            http.Error(w, `{"error":"invalid authorization header format"}`, http.StatusUnauthorized)
            return
        }

        tokenStr := parts[1]
        claims := &jwtClaims{}

        token, err := jwt.ParseWithClaims(tokenStr, claims, func(t *jwt.Token) (interface{}, error) {
            // Verify signing algorithm — prevent alg:none attack
            if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
                return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
            }
            return jwtSecret, nil
        })

        if err != nil || !token.Valid {
            http.Error(w, `{"error":"invalid or expired token"}`, http.StatusUnauthorized)
            return
        }

        // Inject user into context
        user := &User{
            ID:    claims.UserID,
            Email: claims.Email,
            Role:  claims.Role,
        }
        r = SetUser(r, user)

        next.ServeHTTP(w, r)
    })
}

// --------------------------------------------------------------------------
// RequireRole middleware — authorization, must run AFTER AuthMiddleware
// --------------------------------------------------------------------------

func RequireRole(role string) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            user, ok := GetUser(r)
            if !ok {
                // This shouldn't happen if AuthMiddleware runs first,
                // but defensive check is good practice.
                http.Error(w, `{"error":"unauthenticated"}`, http.StatusUnauthorized)
                return
            }
            if user.Role != role {
                http.Error(w, `{"error":"insufficient permissions"}`, http.StatusForbidden)
                return
            }
            next.ServeHTTP(w, r)
        })
    }
}

// --------------------------------------------------------------------------
// Handlers
// --------------------------------------------------------------------------

func listUsersHandler(w http.ResponseWriter, r *http.Request) {
    user, _ := GetUser(r)
    reqID := middleware.GetReqID(r.Context())

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "request_id": reqID,
        "caller":     user.Email,
        "users":      []string{"alice", "bob"},
    })
}

func getUserHandler(w http.ResponseWriter, r *http.Request) {
    userID := chi.URLParam(r, "id")
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"id": userID})
}

func adminDashboardHandler(w http.ResponseWriter, r *http.Request) {
    w.Write([]byte(`{"message":"admin only"}`))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

// --------------------------------------------------------------------------
// Router setup
// --------------------------------------------------------------------------

func NewRouter() http.Handler {
    r := chi.NewRouter()

    // ── Global middleware (outermost first) ──────────────────────────────
    r.Use(middleware.RealIP)   // extract real client IP from proxy headers
    r.Use(middleware.RequestID) // inject X-Request-Id
    r.Use(StructuredLogger(slog.Default())) // log with request ID available
    r.Use(middleware.Recoverer) // catch panics
    r.Use(middleware.Timeout(30 * time.Second))

    // CORS — must be before Auth
    r.Use(cors.Handler(cors.Options{
        AllowedOrigins:   []string{"https://app.example.com"},
        AllowedMethods:   []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
        AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-Request-Id"},
        ExposedHeaders:   []string{"X-Request-Id"},
        AllowCredentials: true,
        MaxAge:           300, // preflight cache: 5 minutes
    }))

    // ── Public routes (no auth) ──────────────────────────────────────────
    r.Get("/health", healthHandler)

    // ── Protected API routes ─────────────────────────────────────────────
    r.Route("/api/v1", func(r chi.Router) {
        r.Use(AuthMiddleware) // applies only to /api/v1/*

        // User routes
        r.Route("/users", func(r chi.Router) {
            r.Get("/", listUsersHandler)
            r.Get("/{id:[0-9a-f-]+}", getUserHandler) // UUID constraint
        })

        // Admin routes — additional role check
        r.Route("/admin", func(r chi.Router) {
            r.Use(RequireRole("admin")) // scoped to /api/v1/admin/*
            r.Get("/dashboard", adminDashboardHandler)
        })
    })

    // ── Sub-router example ───────────────────────────────────────────────
    webhookRouter := chi.NewRouter()
    webhookRouter.Use(middleware.AllowContentType("application/json"))
    webhookRouter.Post("/stripe", stripeWebhookHandler)
    r.Mount("/webhooks", webhookRouter)

    return r
}

func stripeWebhookHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
}

func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
    slog.SetDefault(logger)

    srv := &http.Server{
        Addr:         ":8080",
        Handler:      NewRouter(),
        ReadTimeout:  10 * time.Second,
        WriteTimeout: 35 * time.Second, // slightly more than Timeout middleware
        IdleTimeout:  120 * time.Second,
    }

    slog.Info("server starting", "addr", srv.Addr)
    if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
        slog.Error("server failed", "error", err)
        os.Exit(1)
    }
}
```

---

### Node.js + Express

```javascript
// server.js
import express from 'express';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import jwt from 'jsonwebtoken';

const app = express();
const JWT_SECRET = process.env.JWT_SECRET || 'change-this-in-production';

// ── Middleware utilities ────────────────────────────────────────────────

/**
 * Request ID middleware — injects X-Request-Id header and attaches to req
 */
function requestIdMiddleware(req, res, next) {
  const requestId = req.headers['x-request-id'] || uuidv4();
  req.requestId = requestId;
  res.setHeader('X-Request-Id', requestId);
  next();
}

/**
 * Structured logger middleware — must wrap everything to capture latency
 */
function loggerMiddleware(req, res, next) {
  const start = Date.now();

  // Intercept res.end() to capture status code after the response is sent
  const originalEnd = res.end.bind(res);
  res.end = function (...args) {
    const latencyMs = Date.now() - start;
    console.log(JSON.stringify({
      level: 'info',
      method: req.method,
      path: req.path,
      status: res.statusCode,
      latency_ms: latencyMs,
      request_id: req.requestId,
      remote_addr: req.ip,
    }));
    return originalEnd(...args);
  };

  next();
}

/**
 * Auth middleware — validates JWT, injects user into req.user
 * Returns 401 on failure (short-circuit)
 */
function authMiddleware(req, res, next) {
  const authHeader = req.headers['authorization'];
  if (!authHeader) {
    return res.status(401).json({ error: 'missing authorization header' });
  }

  const parts = authHeader.split(' ');
  if (parts.length !== 2 || parts[0].toLowerCase() !== 'bearer') {
    return res.status(401).json({ error: 'invalid authorization header format' });
  }

  const token = parts[1];
  try {
    // jwt.verify throws if invalid or expired
    const payload = jwt.verify(token, JWT_SECRET, {
      algorithms: ['HS256'], // Explicitly allow only HS256 — prevent alg:none
    });
    req.user = {
      id: payload.sub,
      email: payload.email,
      role: payload.role,
    };
    next();
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'token expired' });
    }
    return res.status(401).json({ error: 'invalid token' });
  }
}

/**
 * Role-based authorization middleware factory
 */
function requireRole(role) {
  return function (req, res, next) {
    if (!req.user) {
      return res.status(401).json({ error: 'unauthenticated' });
    }
    if (req.user.role !== role) {
      return res.status(403).json({ error: 'insufficient permissions' });
    }
    next();
  };
}

// ── Global middleware (order matters!) ─────────────────────────────────
app.set('trust proxy', 1);      // trust first proxy (for req.ip)
app.use(requestIdMiddleware);   // inject before logger so logger has req.requestId
app.use(loggerMiddleware);      // outermost: captures full latency
app.use(cors({                  // CORS before auth — OPTIONS must succeed without token
  origin: 'https://app.example.com',
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-Id'],
  exposedHeaders: ['X-Request-Id'],
  credentials: true,
  maxAge: 300,
}));
app.use(express.json({ limit: '1mb' }));  // parse JSON bodies

// ── Public routes (no auth) ─────────────────────────────────────────────
app.get('/health', (req, res) => {
  res.json({ status: 'ok', request_id: req.requestId });
});

// ── API Router — protected with auth ────────────────────────────────────
const apiRouter = express.Router();
apiRouter.use(authMiddleware);  // all /api/v1/* routes require auth

// Users sub-router
const usersRouter = express.Router();
usersRouter.get('/', (req, res) => {
  res.json({
    request_id: req.requestId,
    caller: req.user.email,
    users: ['alice', 'bob'],
  });
});
usersRouter.get('/:id', (req, res) => {
  res.json({ id: req.params.id });
});

// Chained method routing on a single path
usersRouter.route('/:id/posts')
  .get((req, res) => res.json({ posts: [] }))
  .post((req, res) => res.status(201).json({ created: true }));

apiRouter.use('/users', usersRouter);

// Admin sub-router — additional role check scoped to /admin
const adminRouter = express.Router();
adminRouter.use(requireRole('admin')); // scoped middleware
adminRouter.get('/dashboard', (req, res) => {
  res.json({ message: 'admin only', user: req.user });
});
apiRouter.use('/admin', adminRouter);

app.use('/api/v1', apiRouter);

// ── Error handling middleware (must be last, takes 4 args) ──────────────
app.use((err, req, res, next) => {
  console.error(JSON.stringify({
    level: 'error',
    error: err.message,
    stack: err.stack,
    request_id: req.requestId,
  }));
  res.status(err.status || 500).json({
    error: err.message || 'internal server error',
    request_id: req.requestId,
  });
});

app.listen(8080, () => {
  console.log(JSON.stringify({ level: 'info', message: 'server started', port: 8080 }));
});
```

---

### Python + FastAPI

```python
# main.py
from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated, Any

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# ── Configuration ──────────────────────────────────────────────────────────
import os
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production")
JWT_ALGORITHM = "HS256"

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)

# ── Domain types ────────────────────────────────────────────────────────────
from pydantic import BaseModel

class User(BaseModel):
    id: str
    email: str
    role: str

# ── Custom Middleware ────────────────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects X-Request-Id into every request and response."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        # Attach to request state — FastAPI's way of propagating values
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


class StructuredLoggerMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status, latency for every request."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000
        
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round(latency_ms, 2),
                "request_id": request_id,
                "remote_addr": request.client.host if request.client else "unknown",
            }
        )
        return response


# ── Auth dependency (FastAPI uses Dependency Injection, not middleware for auth) ──

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> User:
    """
    FastAPI dependency — can be used per-route or in a router-level dependency.
    Raises HTTPException on failure, which FastAPI converts to 401 response.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],  # Explicit algorithm prevents alg:none
            options={"require": ["exp", "sub", "iat"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return User(
        id=payload["sub"],
        email=payload.get("email", ""),
        role=payload.get("role", "user"),
    )

# Type alias for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(role: str):
    """Returns a dependency that enforces a specific role."""
    async def _require_role(current_user: CurrentUser) -> User:
        if current_user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient permissions",
            )
        return current_user
    return _require_role

AdminUser = Annotated[User, Depends(require_role("admin"))]


# ── Routers ──────────────────────────────────────────────────────────────────

users_router = APIRouter(prefix="/users", tags=["users"])

@users_router.get("/")
async def list_users(current_user: CurrentUser, request: Request) -> dict[str, Any]:
    return {
        "request_id": request.state.request_id,
        "caller": current_user.email,
        "users": ["alice", "bob"],
    }

@users_router.get("/{user_id}")
async def get_user(user_id: str, current_user: CurrentUser) -> dict[str, str]:
    return {"id": user_id}


admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role("admin"))],  # Applied to ALL routes in this router
)

@admin_router.get("/dashboard")
async def admin_dashboard(current_user: CurrentUser) -> dict[str, Any]:
    return {"message": "admin only", "user": current_user.model_dump()}


# ── Main app ──────────────────────────────────────────────────────────────────

app = FastAPI(title="Backend API", version="1.0.0")

# Middleware is applied in REVERSE order of registration in FastAPI/Starlette
# Last added = outermost = first to process the request
# So register in reverse of desired execution order:
#   Desired: RequestID → Logger → CORS
#   Register: CORS, Logger, RequestID  (RequestID added last = outermost)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
    max_age=300,
)
app.add_middleware(StructuredLoggerMiddleware)
app.add_middleware(RequestIDMiddleware)  # Added last = runs first on request


# ── Public routes ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ── Mount protected API routers ────────────────────────────────────────────────

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(users_router)
api_v1.include_router(admin_router)

app.include_router(api_v1)


# ── Global exception handler ────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal server error", "request_id": request_id},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
```

**Important FastAPI note:** FastAPI adds Starlette middleware in reverse registration order. The last `add_middleware` call becomes the outermost layer. This is the opposite of Express and chi, and a frequent source of bugs when porting knowledge between frameworks.

---

## Common Patterns & Best Practices

### 1. Always Wrap Timeouts Around the Entire Pipeline
```go
r.Use(middleware.Timeout(30 * time.Second))
// This sets r.Context().Deadline(), but it's YOUR responsibility to check it:
select {
case <-r.Context().Done():
    return
default:
    // proceed
}
```

### 2. Use `net/http` Compatible Handlers in Go
Write your handlers as `http.HandlerFunc`. Never take a framework-specific context as a parameter unless you absolutely need to. This keeps your handlers testable outside of any framework.

### 3. Propagate Context, Don't Use Global State
Never store request-scoped data in a global map or thread-local equivalent. Always use `context.WithValue` and pass the request down. This is critical for goroutine-safe concurrency.

### 4. Content-Type Enforcement
```go
r.Use(middleware.AllowContentType("application/json"))
// Returns 415 Unsupported Media Type for non-JSON POST/PUT requests
```

### 5. Compress Responses for Bandwidth Savings
```go
r.Use(middleware.Compress(5)) // gzip compression level 5
// Adds Content-Encoding: gzip header
```

### 6. Use Chi's `middleware.StripSlashes` or `middleware.RedirectSlashes`
Prevent duplicate routes for `/users/` and `/users`:
```go
r.Use(middleware.StripSlashes) // /users/ → treated as /users
```

### 7. Panic Recovery Placement
Recovery must be early in the chain, but after logger so that panics are logged. Placement: `Logger → Recoverer → everything else`.

---

## Common Pitfalls

- ❌ **WRONG:** Using `string` as context key type: `ctx.WithValue("user", u)`
  **✅ CORRECT:** Use an unexported custom type: `ctx.WithValue(contextKeyUser, u)` where `contextKeyUser` is of type `contextKey` (an unexported named type).

- ❌ **WRONG:** Putting Auth before CORS in middleware chain
  **✅ CORRECT:** CORS must be before Auth so that OPTIONS preflight requests succeed without authentication headers.

- ❌ **WRONG:** Forgetting `return` after writing error response in Go middleware:
  ```go
  http.Error(w, "unauthorized", 401)
  next.ServeHTTP(w, r) // BUG: executes even after 401 sent
  ```
  **✅ CORRECT:** Always `return` immediately after writing an error response.

- ❌ **WRONG:** Modifying `req.URL` or `req.Header` directly in Express middleware (mutating request object for values that should be scoped)
  **✅ CORRECT:** Attach scoped data to `req.user`, `req.state`, or similar properties.

- ❌ **WRONG:** Applying heavy middleware (DB calls, external service calls) globally
  **✅ CORRECT:** Use scoped middleware. Only run auth DB lookups on routes that need it.

- ❌ **WRONG:** In FastAPI, expecting `add_middleware` registration order to match execution order
  **✅ CORRECT:** FastAPI/Starlette applies middleware in reverse registration order. Last added = outermost.

- ❌ **WRONG:** Not setting `WriteTimeout` on the server larger than the middleware Timeout:
  ```go
  srv.WriteTimeout = 25 * time.Second  // BUG: shorter than 30s middleware timeout
  ```
  **✅ CORRECT:** `WriteTimeout` should be slightly larger than your middleware timeout so the framework can send its timeout response before the server kills the connection.

- ❌ **WRONG:** Using broad wildcard CORS: `AllowedOrigins: ["*"]` with `AllowCredentials: true`
  **✅ CORRECT:** Browsers block `*` + credentials. Use explicit origin list.

---

## Interview Questions

**Q1. What is the middleware pattern and how does it work?**

**Answer:** Middleware is the decorator pattern applied to HTTP handlers. In Go, a middleware has the signature `func(http.Handler) http.Handler` — it takes a handler and returns a new handler that wraps the original. The wrapper can execute code before calling the inner handler (pre-processing: inspect headers, validate auth, inject request ID), call the inner handler (or short-circuit by not calling it), and execute code after (post-processing: log response, compress body, add response headers). This enables cross-cutting concerns like logging, authentication, and rate limiting to be composed cleanly without coupling to business logic.

---

**Q2. Why does middleware order matter? Give a concrete example where wrong order causes a bug.**

**Answer:** Middleware wraps handlers like layers of an onion. The outermost layer runs first on request and last on response. Order matters because later middleware can depend on work done by earlier middleware.

Concrete example: CORS must run before Auth. A browser CORS preflight is an `OPTIONS` request with no `Authorization` header. If Auth runs before CORS, the preflight is rejected with `401 Unauthorized` before CORS headers are ever added to the response. The browser receives `401` with no CORS headers and reports a confusing "CORS error," hiding the real problem. The fix is to run CORS first so it handles `OPTIONS` requests and sends `204` with the proper `Access-Control-Allow-*` headers, allowing the browser to proceed with the actual authenticated request.

---

**Q3. How do you pass data from middleware to a handler (context propagation) in Go?**

**Answer:** Using `context.WithValue`. When middleware needs to share data downstream (e.g., the authenticated user), it creates a new context with the value attached and returns a new request with that context:
```go
ctx := context.WithValue(r.Context(), contextKeyUser, user)
r = r.WithContext(ctx)
next.ServeHTTP(w, r)
```
The handler then retrieves the value:
```go
user, ok := r.Context().Value(contextKeyUser).(*User)
```
Keys must be of an unexported custom type (not a plain `string`) to prevent accidental collisions between packages, since context key lookup compares by type AND value.

---

**Q4. What is the difference between global middleware and route-scoped middleware?**

**Answer:** Global middleware applies to every request the server handles, regardless of path. Scoped middleware applies only to a specific route group or sub-router.

You almost never want auth middleware to be global, because public endpoints like `/health`, `/metrics`, and `/auth/login` don't need authentication and would break. In chi, you scope middleware with `r.Route()` or `r.Group()`:
```go
r.Get("/health", healthHandler)          // no auth

r.Route("/api/v1", func(r chi.Router) {
    r.Use(AuthMiddleware)                 // only applies inside /api/v1/*
    r.Get("/users", listUsers)
})
```

---

**Q5. How does chi's middleware model compare to Express middleware?**

**Answer:** Both use a chain/pipeline model, but with key differences:

- **Type system:** chi uses `func(http.Handler) http.Handler` — a pure function composition. Express uses `func(req, res, next)` — a callback-based chain where you call `next()` to pass control forward.
- **Stdlib compatibility:** chi middleware is just an `http.Handler` wrapper. Any Go middleware library that follows this interface works with chi. Express middleware is Express-specific.
- **Short-circuit:** In chi/Go, you short-circuit by NOT calling `next.ServeHTTP()`. In Express, you call `res.send()` without calling `next()`.
- **Error handling:** Express has a special 4-argument form `(err, req, res, next)` for error handling middleware, which must be registered last. In Go, errors are just values — middleware returns errors via `http.Error()` or by propagating them.
- **Context:** In Go, context is passed through `r.Context()` (stdlib). In Express, context is attached directly to `req` (e.g., `req.user`).

---

**Q6. Why should you use unexported context key types in Go?**

**Answer:** Go's `context.Value` method compares keys using `==`. If two packages both use the string `"user"` as a context key, they will collide — one package's middleware will accidentally read another's value.

By using an unexported named type:
```go
// package auth
type contextKey string
const contextKeyUser contextKey = "user"
```

The key `auth.contextKeyUser` has type `auth.contextKey`, which is distinct from the type `billing.contextKey` even if both have value `"user"`. Since the type `contextKey` is unexported, no external package can construct a key of that type, making key access fully controlled by the owning package.

---

**Q7. Explain how you would implement a circuit breaker as middleware.**

**Answer:** A circuit breaker tracks failures to a downstream service and "opens" (stops forwarding requests) when failures exceed a threshold, preventing a cascade of timeouts. As middleware:

```go
func CircuitBreaker(threshold int, resetTimeout time.Duration) func(http.Handler) http.Handler {
    var (
        failures   int
        lastFailure time.Time
        state      = "closed" // closed = normal, open = blocking
        mu         sync.Mutex
    )
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            mu.Lock()
            if state == "open" && time.Since(lastFailure) < resetTimeout {
                mu.Unlock()
                http.Error(w, "service unavailable", http.StatusServiceUnavailable)
                return
            }
            if state == "open" {
                state = "half-open"
            }
            mu.Unlock()
            
            sr := &statusRecorder{ResponseWriter: w, status: 200}
            next.ServeHTTP(sr, r)
            
            mu.Lock()
            defer mu.Unlock()
            if sr.status >= 500 {
                failures++
                lastFailure = time.Now()
                if failures >= threshold {
                    state = "open"
                }
            } else {
                failures = 0
                state = "closed"
            }
        })
    }
}
```

---

## Resources

- [chi Documentation](https://github.com/go-chi/chi)
- [net/http ServeMux Go 1.22 Release Notes](https://tip.golang.org/doc/go1.22)
- [Go Blog: context package](https://go.dev/blog/context)
- [Express Routing Guide](https://expressjs.com/en/guide/routing.html)
- [FastAPI Middleware Docs](https://fastapi.tiangolo.com/tutorial/middleware/)
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Starlette Middleware](https://www.starlette.io/middleware/)
- [CORS Specification (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)

---

**Next:** [Part 3.2: Request Validation](./03-request-validation.md)
