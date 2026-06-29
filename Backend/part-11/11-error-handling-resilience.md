# Part 11.1: Error Handling Patterns

## What You'll Learn
- How to model, propagate, and present errors in Go, Node.js, and Python
- The philosophical difference between errors-as-values and exceptions
- Custom error types with HTTP status codes
- Structured error responses clients can depend on
- Logging strategy: what to log vs what to return
- Global error middleware in Chi, Express, and FastAPI
- How interviewers test your error-handling maturity

## Table of Contents
1. [Error Handling Philosophy](#1-error-handling-philosophy)
2. [Go Error Handling — Deep Dive](#2-go-error-handling--deep-dive)
3. [Node.js Error Handling — Deep Dive](#3-nodejs-error-handling--deep-dive)
4. [Python Error Handling — Deep Dive](#4-python-error-handling--deep-dive)
5. [Structured Error Responses](#5-structured-error-responses)
6. [Error Logging Best Practices](#6-error-logging-best-practices)
7. [Implementation Examples](#7-implementation-examples)
8. [Common Patterns & Best Practices](#8-common-patterns--best-practices)
9. [Common Pitfalls](#9-common-pitfalls)
10. [Interview Questions & Answers](#10-interview-questions--answers)
11. [Resources](#11-resources)

---

## 1. Error Handling Philosophy

### Errors Are Information, Not Exceptions

The way a language models errors shapes how you think about failure. Go treats errors as ordinary values that flow through your program like any other data. Python and JavaScript treat errors as exceptional conditions that interrupt the normal flow via exception propagation. Neither is strictly better — but each has trade-offs you must articulate in an interview.

```
Go model (errors as values):
  ┌─────────┐   (value, error)   ┌─────────┐
  │ caller  │ ◄────────────────  │ callee  │
  └─────────┘                    └─────────┘
  The caller MUST decide what to do with the error.
  Ignoring it requires explicit _ assignment.

Python/Node model (exceptions):
  ┌─────────┐                    ┌─────────┐
  │ caller  │                    │ callee  │ raises/throws
  └─────────┘                    └─────────┘
        ↑ exception propagates up the call stack
        │ automatically — until caught or process crashes
```

**Key mental model difference:**
- In Go, if you don't check `err`, the program continues with a zero-value result. This is a common bug.
- In Python/Node, if you don't catch an exception, it propagates automatically. You can have a catch-all at the top.
- Go forces you to handle errors at the point they occur. Python/Node allow you to centralize error handling.

### Operational Errors vs Programming Errors

This distinction is crucial. Senior engineers know the difference instinctively.

**Operational errors** — expected, predictable failures at runtime:
- Database connection refused
- HTTP request timeout
- File not found
- Invalid user input
- Third-party API returns 503

These are **recoverable**. You handle them, log them at appropriate severity, and return a meaningful response to the client.

**Programming errors** — bugs in your code:
- Nil pointer dereference
- Array out of bounds
- Type assertion failure on wrong type
- Using a closed channel

These are **not recoverable** in the traditional sense. In Go, they often cause a panic. In Node.js, they throw a TypeError or ReferenceError. The correct response is to crash (or let the process manager restart) rather than try to recover and continue in a corrupt state.

```
Decision tree for error handling:

Is this error expected at runtime?
├── YES → Operational error
│         ├── Can we retry? → Retry with backoff
│         ├── Can we degrade? → Return partial result
│         └── Must fail? → Return structured error response to client
└── NO → Programming error
          └── Log with full stack trace
              Crash / panic
              Let process manager restart
              Alert on-call
```

### Never Swallow Errors Silently

The worst thing you can do is discard an error:

```go
// BAD — silent discard
result, _ := doSomething()

// BAD — ignore and continue
if err != nil {
    // do nothing
}
```

```javascript
// BAD — swallowed promise rejection
someAsyncOperation().then(result => {
    // use result
})
// no .catch()
```

```python
# BAD — bare except
try:
    do_something()
except:
    pass
```

If you can't handle an error at a given level, **propagate it up** with additional context.

---

## 2. Go Error Handling — Deep Dive

### The `error` Interface

```go
type error interface {
    Error() string
}
```

This is the entire error interface. Anything that implements `Error() string` is an error. This simplicity is powerful — you can attach any context to a custom error type.

### Sentinel Errors

Sentinel errors are package-level error variables that callers compare against:

```go
// From the standard library:
var ErrNoRows = errors.New("sql: no rows in result set")
var io.EOF = errors.New("EOF")

// Your own sentinel errors:
var (
    ErrNotFound      = errors.New("not found")
    ErrUnauthorized  = errors.New("unauthorized")
    ErrInvalidInput  = errors.New("invalid input")
)
```

**When to use:** When the caller needs to take a different code path based on the error type, and the error carries no additional context beyond its identity.

**Checking sentinel errors:**

```go
// Direct comparison (only safe if error is not wrapped)
if err == sql.ErrNoRows {
    return nil, ErrNotFound
}

// errors.Is — safe even through wrapping chains
if errors.Is(err, sql.ErrNoRows) {
    return nil, ErrNotFound
}
```

### Error Wrapping with `fmt.Errorf` and `%w`

Wrapping adds context to an error while preserving the original for later inspection:

```go
func getUserByID(ctx context.Context, id string) (*User, error) {
    user, err := db.QueryUser(ctx, id)
    if err != nil {
        // %w wraps the error — original is preserved and accessible via errors.Is/As
        return nil, fmt.Errorf("getUserByID(id=%s): %w", id, err)
    }
    return user, nil
}
```

The resulting error message reads like a call stack:
```
handler: getUserByID(id=abc123): queryUser: pq: relation "users" does not exist
```

Each layer adds context. You can reconstruct what happened from the error message alone.

**`%w` vs `%v`:**
- `%w` wraps the error — the original is accessible via `errors.Is` and `errors.As`
- `%v` formats the error as a string — the original error is lost, you get a plain string error

```go
// With %w:
wrapped := fmt.Errorf("database error: %w", sql.ErrNoRows)
errors.Is(wrapped, sql.ErrNoRows) // true ✓

// With %v:
strErr := fmt.Errorf("database error: %v", sql.ErrNoRows)
errors.Is(strErr, sql.ErrNoRows) // false ✗
```

### Custom Error Types with Context

When you need to carry structured data alongside an error:

```go
// AppError carries HTTP status code and a user-safe message
type AppError struct {
    Code       int    // HTTP status code
    Message    string // safe to return to client
    Internal   error  // original error, never sent to client
    Field      string // optional: which field caused the error
    RequestID  string // for log correlation
}

func (e *AppError) Error() string {
    if e.Internal != nil {
        return fmt.Sprintf("[%d] %s: %v", e.Code, e.Message, e.Internal)
    }
    return fmt.Sprintf("[%d] %s", e.Code, e.Message)
}

// Unwrap allows errors.Is/As to look through AppError
func (e *AppError) Unwrap() error {
    return e.Internal
}

// Constructor helpers
func NewNotFoundError(msg string, internal error) *AppError {
    return &AppError{Code: 404, Message: msg, Internal: internal}
}

func NewValidationError(field, msg string) *AppError {
    return &AppError{Code: 400, Message: msg, Field: field}
}

func NewInternalError(internal error) *AppError {
    return &AppError{Code: 500, Message: "internal server error", Internal: internal}
}
```

### `errors.As` — Extracting Typed Errors

`errors.As` traverses the error chain looking for a specific type:

```go
func handleError(err error) {
    var appErr *AppError
    if errors.As(err, &appErr) {
        // appErr is now populated with the *AppError from the chain
        log.Printf("HTTP %d: %s", appErr.Code, appErr.Message)
        return
    }

    var pgErr *pq.Error
    if errors.As(err, &pgErr) {
        if pgErr.Code == "23505" { // unique_violation
            // handle duplicate
        }
    }
}
```

### Panic vs Error

**Use panic for programming errors — impossible states:**

```go
// Panic: this should NEVER happen if code is correct
func mustParseUUID(s string) uuid.UUID {
    id, err := uuid.Parse(s)
    if err != nil {
        panic(fmt.Sprintf("mustParseUUID: invalid UUID constant %q: %v", s, err))
    }
    return id
}

// Panic: nil argument violates contract
func (s *UserService) Create(ctx context.Context, user *User) error {
    if user == nil {
        panic("Create called with nil user") // programming error
    }
    // ...
}
```

**Use error for operational failures:**

```go
// Error: user might not exist — this is expected
func (s *UserService) GetByID(ctx context.Context, id string) (*User, error) {
    user, err := s.repo.FindByID(ctx, id)
    if errors.Is(err, ErrNotFound) {
        return nil, fmt.Errorf("user %s not found: %w", id, ErrNotFound)
    }
    if err != nil {
        return nil, fmt.Errorf("GetByID: %w", err)
    }
    return user, nil
}
```

### Defer + Recover

`recover()` catches panics in the same goroutine. Use it in middleware to prevent a handler panic from crashing the whole server:

```go
func recoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if rec := recover(); rec != nil {
                // Get stack trace
                buf := make([]byte, 4096)
                n := runtime.Stack(buf, false)
                stack := string(buf[:n])

                log.Printf("PANIC recovered: %v\n%s", rec, stack)

                // Return 500 to client
                w.Header().Set("Content-Type", "application/json")
                w.WriteHeader(http.StatusInternalServerError)
                json.NewEncoder(w).Encode(map[string]interface{}{
                    "error": map[string]string{
                        "code":    "INTERNAL_ERROR",
                        "message": "an unexpected error occurred",
                    },
                })
            }
        }()
        next.ServeHTTP(w, r)
    })
}
```

### Error Groups for Concurrent Operations

When you fan out to multiple goroutines and need to collect all errors:

```go
import "golang.org/x/sync/errgroup"

func fetchUserData(ctx context.Context, userID string) (*UserData, error) {
    g, ctx := errgroup.WithContext(ctx)

    var profile *Profile
    var orders []*Order
    var preferences *Preferences

    g.Go(func() error {
        var err error
        profile, err = profileService.Get(ctx, userID)
        return fmt.Errorf("profile: %w", err)
    })

    g.Go(func() error {
        var err error
        orders, err = orderService.List(ctx, userID)
        return fmt.Errorf("orders: %w", err)
    })

    g.Go(func() error {
        var err error
        preferences, err = prefService.Get(ctx, userID)
        return fmt.Errorf("preferences: %w", err)
    })

    // Wait for all goroutines — returns first non-nil error
    // The context is cancelled when any goroutine returns an error
    if err := g.Wait(); err != nil {
        return nil, fmt.Errorf("fetchUserData: %w", err)
    }

    return &UserData{Profile: profile, Orders: orders, Preferences: preferences}, nil
}
```

---

## 3. Node.js Error Handling — Deep Dive

### Async/Await and try/catch

Modern Node.js uses `async/await`. Every `async` function returns a Promise. Unhandled rejections crash the process in Node.js 15+.

```javascript
// ALWAYS await async calls inside try/catch
async function getUserByID(id) {
    try {
        const user = await db.query('SELECT * FROM users WHERE id = $1', [id]);
        if (!user.rows.length) {
            throw new NotFoundError(`User ${id} not found`);
        }
        return user.rows[0];
    } catch (err) {
        if (err instanceof NotFoundError) throw err; // re-throw known errors
        // Wrap unknown errors with context
        throw new DatabaseError(`getUserByID failed for id=${id}`, { cause: err });
    }
}
```

### Custom Error Classes

```javascript
// Base class: all app errors extend this
class AppError extends Error {
    constructor(message, options = {}) {
        super(message);
        this.name = this.constructor.name;
        this.statusCode = options.statusCode || 500;
        this.code = options.code || 'INTERNAL_ERROR';
        this.isOperational = options.isOperational !== false; // default true
        this.details = options.details || null;

        // Preserve original error chain (Node 16.9+)
        if (options.cause) {
            this.cause = options.cause;
        }

        // Capture stack trace, excluding constructor
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, this.constructor);
        }
    }
}

class NotFoundError extends AppError {
    constructor(message, options = {}) {
        super(message, { ...options, statusCode: 404, code: 'NOT_FOUND', isOperational: true });
    }
}

class ValidationError extends AppError {
    constructor(message, fields = []) {
        super(message, { statusCode: 400, code: 'VALIDATION_ERROR', isOperational: true });
        this.fields = fields; // [{ field: 'email', message: 'invalid format' }]
    }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Unauthorized') {
        super(message, { statusCode: 401, code: 'UNAUTHORIZED', isOperational: true });
    }
}

class DatabaseError extends AppError {
    constructor(message, options = {}) {
        super(message, { ...options, statusCode: 500, code: 'DATABASE_ERROR', isOperational: false });
    }
}
```

### Express Error Middleware

Express error handlers take **4 arguments** — `(err, req, res, next)`. Express identifies them by arity.

```javascript
// MUST be registered AFTER all routes
function errorHandler(err, req, res, next) {
    const requestId = req.headers['x-request-id'] || req.id;

    // Determine if this is an operational error we can handle gracefully
    if (err instanceof AppError && err.isOperational) {
        // Log at appropriate level
        const logLevel = err.statusCode >= 500 ? 'error' : 'warn';
        logger[logLevel]({
            requestId,
            error: err.message,
            code: err.code,
            statusCode: err.statusCode,
            stack: err.stack,
        });

        const response = {
            error: {
                code: err.code,
                message: err.message,
                requestId,
            },
        };

        // Include field errors for validation errors
        if (err instanceof ValidationError) {
            response.error.fields = err.fields;
        }

        return res.status(err.statusCode).json(response);
    }

    // Unknown / programming error — log everything, return generic 500
    logger.error({
        requestId,
        error: err.message,
        stack: err.stack,
        cause: err.cause?.message,
    });

    return res.status(500).json({
        error: {
            code: 'INTERNAL_ERROR',
            message: 'An unexpected error occurred',
            requestId,
        },
    });
}

// Register in app:
app.use(errorHandler);
```

### Unhandled Promise Rejections

```javascript
// Register these at process startup — they are your last line of defense

// Unhandled promise rejection (async code where .catch() was missed)
process.on('unhandledRejection', (reason, promise) => {
    logger.fatal({ reason, promise }, 'Unhandled promise rejection — shutting down');
    // Give in-flight requests time to complete, then exit
    server.close(() => {
        process.exit(1);
    });
});

// Uncaught exception (synchronous throw with no try/catch)
process.on('uncaughtException', (err) => {
    logger.fatal({ err }, 'Uncaught exception — shutting down');
    server.close(() => {
        process.exit(1);
    });
});
```

**Why crash on unhandledRejection?** Because the program is in an unknown state. Continuing to serve requests from a potentially corrupt state is worse than restarting cleanly.

### Async Wrapper for Express

Express does not automatically catch async errors. Without a wrapper, rejected promises are unhandled:

```javascript
// Without wrapper — uncaught rejection:
app.get('/users/:id', async (req, res) => {
    const user = await getUserByID(req.params.id); // if this throws, Express doesn't catch it
    res.json(user);
});

// Option 1: Manual try/catch (verbose but explicit)
app.get('/users/:id', async (req, res, next) => {
    try {
        const user = await getUserByID(req.params.id);
        res.json(user);
    } catch (err) {
        next(err); // passes to error middleware
    }
});

// Option 2: asyncHandler wrapper (clean)
const asyncHandler = (fn) => (req, res, next) =>
    Promise.resolve(fn(req, res, next)).catch(next);

app.get('/users/:id', asyncHandler(async (req, res) => {
    const user = await getUserByID(req.params.id);
    res.json(user);
}));

// Option 3: Express 5 (handles async natively — still in RC as of 2026)
// No wrapper needed
```

---

## 4. Python Error Handling — Deep Dive

### Exception Hierarchy

```
BaseException
├── SystemExit
├── KeyboardInterrupt
├── GeneratorExit
└── Exception
    ├── StopIteration
    ├── ArithmeticError
    │   └── ZeroDivisionError
    ├── LookupError
    │   ├── KeyError
    │   └── IndexError
    ├── OSError (IOError, EnvironmentError)
    │   ├── FileNotFoundError
    │   └── ConnectionError
    ├── ValueError
    ├── TypeError
    └── RuntimeError
```

**Always catch the most specific exception you can handle.** Catching `Exception` is a last resort. Never catch `BaseException` unless you're writing shutdown code.

### try/except/else/finally

```python
def read_config(path: str) -> dict:
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        # Specific: file doesn't exist
        raise ConfigError(f"Config file not found: {path}")
    except json.JSONDecodeError as e:
        # Specific: file exists but is invalid JSON
        raise ConfigError(f"Invalid JSON in config {path}: {e}") from e
    except OSError as e:
        # General OS errors (permissions, etc.)
        raise ConfigError(f"Cannot read config {path}: {e}") from e
    else:
        # Runs only if no exception was raised in try block
        # Good place for code that should only run on success
        logger.info(f"Config loaded from {path}")
        return data
    finally:
        # Always runs — cleanup regardless of success/failure
        # Note: if try block has a return, finally still runs
        logger.debug(f"Config read attempt completed for {path}")
```

### Exception Chaining — `raise ... from`

```python
# raise X from Y — explicit chaining, sets X.__cause__ = Y
try:
    result = db.execute(query)
except psycopg2.Error as e:
    raise DatabaseError(f"Query failed: {query[:50]}") from e
    # Full traceback shows both the DatabaseError AND the original psycopg2.Error

# raise X from None — suppress the original exception (be careful)
try:
    internal_result = _internal_operation()
except _InternalError as e:
    raise PublicError("operation failed") from None
    # Original exception is hidden from traceback
```

### Custom Exception Classes

```python
from typing import Optional, Any
import http

class AppError(Exception):
    """Base class for all application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str = "INTERNAL_ERROR",
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details

    def to_dict(self) -> dict:
        result = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404, code="NOT_FOUND")


class ValidationError(AppError):
    def __init__(self, message: str, fields: list[dict] = None):
        super().__init__(message, status_code=400, code="VALIDATION_ERROR")
        self.fields = fields or []

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.fields:
            d["fields"] = self.fields
        return d


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401, code="UNAUTHORIZED")


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=409, code="CONFLICT")
```

### FastAPI Exception Handling

FastAPI has two exception handling mechanisms:

**1. `HTTPException` — built-in, for quick error responses:**

```python
from fastapi import HTTPException

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"code": "USER_NOT_FOUND", "message": f"User {user_id} not found"}
        )
    return user
```

**2. `@app.exception_handler` — custom handlers for custom exception types:**

```python
from fastapi import Request
from fastapi.responses import JSONResponse
import uuid

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Log with appropriate level
    if exc.status_code >= 500:
        logger.error(
            "Application error",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "error_code": exc.code,
                "error_message": exc.message,
                "exc_info": True,  # includes traceback in logs
            },
        )
    else:
        logger.warning(
            "Client error",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "error_code": exc.code,
            },
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                **exc.to_dict(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    logger.exception(
        "Unhandled exception",
        extra={"request_id": request_id, "path": request.url.path},
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id,
            }
        },
    )
```

**3. Pydantic `RequestValidationError` — automatic for request validation:**

```python
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = []
    for error in exc.errors():
        fields.append({
            "field": ".".join(str(loc) for loc in error["loc"] if loc != "body"),
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "fields": fields,
            }
        },
    )
```

### Context Managers for Resource Cleanup

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def db_transaction(session):
    """Ensure transaction is committed or rolled back."""
    async with session.begin():
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()

# Usage:
async def create_order(user_id: str, items: list):
    async with db_transaction(session) as tx:
        order = Order(user_id=user_id)
        tx.add(order)
        for item in items:
            tx.add(OrderItem(order_id=order.id, **item))
        # commit happens automatically in else clause
```

---

## 5. Structured Error Responses

### Standard Error Envelope

Every error response should follow the same shape. Clients can rely on it:

```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User abc123 not found",
    "request_id": "req_01HGP5ZK3XYZABC",
    "details": null
  }
}
```

**For validation errors, include field-level details:**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "request_id": "req_01HGP5ZK3XYZABC",
    "fields": [
      { "field": "email", "message": "must be a valid email address" },
      { "field": "age", "message": "must be greater than 0" }
    ]
  }
}
```

### RFC 7807 — Problem Details for HTTP APIs

```json
{
  "type": "https://api.example.com/errors/user-not-found",
  "title": "User Not Found",
  "status": 404,
  "detail": "User with id abc123 does not exist",
  "instance": "/users/abc123",
  "requestId": "req_01HGP5ZK3XYZABC"
}
```

RFC 7807 adds machine-readable URIs for error types. Use it when building public APIs that third parties consume — it allows them to define behavior based on `type` rather than just status codes.

### HTTP Status Code Mapping

```
400 Bad Request          → VALIDATION_ERROR, INVALID_INPUT
401 Unauthorized         → UNAUTHORIZED, TOKEN_EXPIRED, TOKEN_INVALID
403 Forbidden            → FORBIDDEN, INSUFFICIENT_PERMISSIONS
404 Not Found            → NOT_FOUND, RESOURCE_NOT_FOUND
409 Conflict             → CONFLICT, DUPLICATE_RESOURCE
410 Gone                 → RESOURCE_DELETED (permanent)
422 Unprocessable Entity → VALIDATION_ERROR (semantic validation)
429 Too Many Requests    → RATE_LIMITED
500 Internal Server Error → INTERNAL_ERROR
502 Bad Gateway          → UPSTREAM_ERROR
503 Service Unavailable  → SERVICE_UNAVAILABLE
504 Gateway Timeout      → UPSTREAM_TIMEOUT
```

### What Not to Leak to Clients

```
NEVER include in error responses:
- Stack traces
- SQL queries or database error messages
- Internal file paths
- Internal variable values
- Library-specific error codes (e.g., psycopg2 error code directly)
- Connection strings
- Environment variable names
```

---

## 6. Error Logging Best Practices

### What to Include in Every Error Log

```json
{
  "timestamp": "2026-06-29T10:45:12.345Z",
  "level": "error",
  "request_id": "req_01HGP5ZK3XYZABC",
  "user_id": "user_789",
  "session_id": "sess_456",
  "method": "POST",
  "path": "/api/v1/orders",
  "status_code": 500,
  "duration_ms": 245,
  "error": {
    "type": "DatabaseError",
    "message": "connection refused",
    "stack": "DatabaseError: connection refused\n  at ...",
    "cause": "connect ECONNREFUSED 127.0.0.1:5432"
  },
  "service": "order-service",
  "version": "1.4.2",
  "environment": "production"
}
```

### Log Level Guidelines

```
DEBUG  — detailed internal state, loop iterations, variable values
         Never in production. Only in local dev.

INFO   — normal operations: request received, user authenticated,
         order created. No errors.

WARN   — unexpected but handled: retry attempt, fallback triggered,
         slow query, cache miss on hot path

ERROR  — operation failed: DB unavailable, external API error,
         unrecoverable for this request. PagerDuty alert candidate.

FATAL  — process is about to die: unhandled exception, unrecoverable
         system error. Always triggers alert + restart.
```

### Don't Log Expected Errors at ERROR Level

```go
// BAD — 404s are expected, don't flood your error logs
logger.Error("user not found", "id", id) // ERROR level for a 404?

// GOOD — 404 is a normal operational condition
logger.Warn("user not found", "id", id)  // WARN or INFO

// GOOD — 500s and unexpected failures are ERROR
logger.Error("database query failed", "query", query, "error", err)
```

### Request ID Propagation

Every request gets a unique ID. It flows through every log entry for that request and is returned in the error response. This lets you `grep` your logs for a specific request:

```
grep "req_01HGP5ZK3XYZABC" /var/log/app/*.log | sort -k1
```

---

## 7. Implementation Examples

### Go + Chi Router

```go
// errors/errors.go
package errors

import (
    "fmt"
    "net/http"
)

type AppError struct {
    Code       int
    ErrCode    string
    Message    string
    Internal   error
    Fields     []FieldError
    RequestID  string
}

type FieldError struct {
    Field   string `json:"field"`
    Message string `json:"message"`
}

func (e *AppError) Error() string {
    if e.Internal != nil {
        return fmt.Sprintf("[%d/%s] %s: %v", e.Code, e.ErrCode, e.Message, e.Internal)
    }
    return fmt.Sprintf("[%d/%s] %s", e.Code, e.ErrCode, e.Message)
}

func (e *AppError) Unwrap() error { return e.Internal }

func NotFound(msg string, internal error) *AppError {
    return &AppError{Code: http.StatusNotFound, ErrCode: "NOT_FOUND", Message: msg, Internal: internal}
}

func BadRequest(msg string, fields ...FieldError) *AppError {
    return &AppError{Code: http.StatusBadRequest, ErrCode: "VALIDATION_ERROR", Message: msg, Fields: fields}
}

func Internal(internal error) *AppError {
    return &AppError{Code: http.StatusInternalServerError, ErrCode: "INTERNAL_ERROR", Message: "internal server error", Internal: internal}
}

func Unauthorized(msg string) *AppError {
    return &AppError{Code: http.StatusUnauthorized, ErrCode: "UNAUTHORIZED", Message: msg}
}
```

```go
// middleware/error_handler.go
package middleware

import (
    "encoding/json"
    "net/http"
    "runtime/debug"

    appErrors "myapp/errors"

    "github.com/go-chi/chi/v5/middleware"
    "golang.org/x/exp/slog"
    "errors"
)

type errorResponse struct {
    Error errorBody `json:"error"`
}

type errorBody struct {
    Code      string                    `json:"code"`
    Message   string                    `json:"message"`
    RequestID string                    `json:"request_id,omitempty"`
    Fields    []appErrors.FieldError    `json:"fields,omitempty"`
}

// ErrorHandler wraps the next handler and handles AppError returns
// Usage: Use a response writer wrapper to capture errors, OR have handlers call writeError directly
func WriteError(w http.ResponseWriter, r *http.Request, err error) {
    reqID := middleware.GetReqID(r.Context())

    var appErr *appErrors.AppError
    if errors.As(err, &appErr) {
        // Log internal error server-side
        if appErr.Internal != nil {
            slog.Error("application error",
                "request_id", reqID,
                "error_code", appErr.ErrCode,
                "internal", appErr.Internal,
                "path", r.URL.Path,
            )
        } else if appErr.Code >= 500 {
            slog.Error("application error",
                "request_id", reqID,
                "error_code", appErr.ErrCode,
                "message", appErr.Message,
            )
        } else {
            slog.Warn("client error",
                "request_id", reqID,
                "error_code", appErr.ErrCode,
                "path", r.URL.Path,
            )
        }

        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(appErr.Code)
        json.NewEncoder(w).Encode(errorResponse{
            Error: errorBody{
                Code:      appErr.ErrCode,
                Message:   appErr.Message,
                RequestID: reqID,
                Fields:    appErr.Fields,
            },
        })
        return
    }

    // Unknown error
    slog.Error("unhandled error",
        "request_id", reqID,
        "error", err,
        "path", r.URL.Path,
    )

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusInternalServerError)
    json.NewEncoder(w).Encode(errorResponse{
        Error: errorBody{
            Code:      "INTERNAL_ERROR",
            Message:   "an unexpected error occurred",
            RequestID: reqID,
        },
    })
}

// RecoveryMiddleware catches panics
func RecoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if rec := recover(); rec != nil {
                slog.Error("panic recovered",
                    "panic", rec,
                    "stack", string(debug.Stack()),
                    "path", r.URL.Path,
                )
                w.Header().Set("Content-Type", "application/json")
                w.WriteHeader(http.StatusInternalServerError)
                json.NewEncoder(w).Encode(errorResponse{
                    Error: errorBody{
                        Code:    "INTERNAL_ERROR",
                        Message: "an unexpected error occurred",
                    },
                })
            }
        }()
        next.ServeHTTP(w, r)
    })
}
```

```go
// handlers/user_handler.go
package handlers

import (
    "encoding/json"
    "net/http"

    appErrors "myapp/errors"
    "myapp/middleware"
    "myapp/services"

    "github.com/go-chi/chi/v5"
)

type UserHandler struct {
    svc services.UserService
}

func (h *UserHandler) GetUser(w http.ResponseWriter, r *http.Request) {
    userID := chi.URLParam(r, "id")
    if userID == "" {
        middleware.WriteError(w, r, appErrors.BadRequest("user id is required"))
        return
    }

    user, err := h.svc.GetByID(r.Context(), userID)
    if err != nil {
        middleware.WriteError(w, r, err) // errors already typed from service layer
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(user)
}
```

```go
// main.go — router setup
r := chi.NewRouter()
r.Use(chiMiddleware.RequestID)
r.Use(chiMiddleware.Logger)
r.Use(middleware.RecoveryMiddleware)

r.Get("/users/{id}", userHandler.GetUser)
```

---

### Node.js + Express

```javascript
// errors/AppError.js
class AppError extends Error {
    constructor(message, statusCode = 500, code = 'INTERNAL_ERROR', details = null) {
        super(message);
        this.name = this.constructor.name;
        this.statusCode = statusCode;
        this.code = code;
        this.isOperational = true;
        this.details = details;
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, this.constructor);
        }
    }
}

class NotFoundError extends AppError {
    constructor(msg = 'Not found') {
        super(msg, 404, 'NOT_FOUND');
    }
}

class ValidationError extends AppError {
    constructor(msg, fields = []) {
        super(msg, 400, 'VALIDATION_ERROR');
        this.fields = fields;
    }
}

class UnauthorizedError extends AppError {
    constructor(msg = 'Unauthorized') {
        super(msg, 401, 'UNAUTHORIZED');
    }
}

module.exports = { AppError, NotFoundError, ValidationError, UnauthorizedError };
```

```javascript
// middleware/errorHandler.js
const { AppError, ValidationError } = require('../errors/AppError');
const logger = require('../logger');

function errorHandler(err, req, res, next) {
    const requestId = req.headers['x-request-id'] || req.id || 'unknown';

    // Normalize third-party errors
    const normalizedErr = normalizeError(err);

    if (normalizedErr instanceof AppError && normalizedErr.isOperational) {
        const level = normalizedErr.statusCode >= 500 ? 'error' : 'warn';
        logger[level]({
            requestId,
            method: req.method,
            path: req.path,
            statusCode: normalizedErr.statusCode,
            errorCode: normalizedErr.code,
            error: normalizedErr.message,
        });

        const body = {
            error: {
                code: normalizedErr.code,
                message: normalizedErr.message,
                requestId,
            },
        };

        if (normalizedErr instanceof ValidationError && normalizedErr.fields?.length) {
            body.error.fields = normalizedErr.fields;
        }

        return res.status(normalizedErr.statusCode).json(body);
    }

    // Programming error or unknown — log full stack
    logger.error({
        requestId,
        method: req.method,
        path: req.path,
        error: err.message,
        stack: err.stack,
        cause: err.cause?.message,
    });

    return res.status(500).json({
        error: {
            code: 'INTERNAL_ERROR',
            message: 'An unexpected error occurred',
            requestId,
        },
    });
}

function normalizeError(err) {
    // Map common library errors to AppErrors
    if (err.name === 'JsonWebTokenError') {
        return new (require('../errors/AppError').UnauthorizedError)('Invalid token');
    }
    if (err.name === 'TokenExpiredError') {
        return new (require('../errors/AppError').UnauthorizedError)('Token expired');
    }
    if (err.code === 'ECONNREFUSED') {
        const { AppError } = require('../errors/AppError');
        return new AppError('Service temporarily unavailable', 503, 'SERVICE_UNAVAILABLE');
    }
    return err;
}

module.exports = errorHandler;
```

```javascript
// middleware/asyncHandler.js
const asyncHandler = (fn) => (req, res, next) =>
    Promise.resolve(fn(req, res, next)).catch(next);

module.exports = asyncHandler;
```

```javascript
// routes/users.js
const { Router } = require('express');
const asyncHandler = require('../middleware/asyncHandler');
const { NotFoundError, ValidationError } = require('../errors/AppError');
const userService = require('../services/userService');

const router = Router();

router.get('/:id', asyncHandler(async (req, res) => {
    const { id } = req.params;
    if (!id || id.length < 1) {
        throw new ValidationError('Invalid request', [
            { field: 'id', message: 'User ID is required' }
        ]);
    }
    const user = await userService.getByID(id);
    if (!user) throw new NotFoundError(`User ${id} not found`);
    res.json({ data: user });
}));

module.exports = router;
```

---

### Python + FastAPI

```python
# errors/exceptions.py
from typing import Any, Optional

class AppError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str = "INTERNAL_ERROR",
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details

    def to_dict(self) -> dict:
        d = {"code": self.code, "message": self.message}
        if self.details is not None:
            d["details"] = self.details
        return d


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404, code="NOT_FOUND")


class ValidationError(AppError):
    def __init__(self, message: str, fields: list[dict] | None = None):
        super().__init__(message, status_code=400, code="VALIDATION_ERROR")
        self.fields = fields or []

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.fields:
            d["fields"] = self.fields
        return d


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401, code="UNAUTHORIZED")


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=409, code="CONFLICT")
```

```python
# middleware/error_handlers.py
import uuid
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from errors.exceptions import AppError

logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    log_extra = {
        "request_id": request_id,
        "method": request.method,
        "path": str(request.url.path),
        "error_code": exc.code,
    }

    if exc.status_code >= 500:
        logger.error("Application error: %s", exc.message, extra=log_extra, exc_info=True)
    else:
        logger.warning("Client error: %s", exc.message, extra=log_extra)

    body = {"error": {**exc.to_dict(), "request_id": request_id}}
    return JSONResponse(status_code=exc.status_code, content=body)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    logger.exception(
        "Unhandled exception",
        extra={"request_id": request_id, "path": str(request.url.path)},
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id,
            }
        },
    )


async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    fields = [
        {
            "field": ".".join(str(loc) for loc in e["loc"] if loc != "body"),
            "message": e["msg"],
            "type": e["type"],
        }
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "fields": fields,
                "request_id": request_id,
            }
        },
    )
```

```python
# main.py
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from errors.exceptions import AppError
from middleware.error_handlers import (
    app_error_handler,
    unhandled_exception_handler,
    request_validation_handler,
)

app = FastAPI()

# Register exception handlers — order matters: most specific first
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
```

```python
# routers/users.py
from fastapi import APIRouter
from errors.exceptions import NotFoundError
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])
user_service = UserService()

@router.get("/{user_id}")
async def get_user(user_id: str):
    user = await user_service.get_by_id(user_id)
    if not user:
        raise NotFoundError(f"User {user_id} not found")
    return {"data": user}
```

---

## 8. Common Patterns & Best Practices

### Pattern 1: Error Context Chain

Each function in the call stack adds context before propagating:

```
Handler:      "POST /orders: " + service error
Service:      "createOrder(userID=abc): " + repo error
Repository:   "insertOrder: " + db error
DB driver:    "pq: unique_violation on orders_user_id_ref_idx"
```

When you read the final error, you know exactly what happened at every layer.

### Pattern 2: Centralized HTTP Status Mapping

```go
// In your error package, provide a helper that maps AppError to HTTP status
func HTTPStatusFromError(err error) int {
    var appErr *AppError
    if errors.As(err, &appErr) {
        return appErr.Code
    }
    return http.StatusInternalServerError
}
```

### Pattern 3: Idiomatic Error Return in Services

Services should return domain errors, not HTTP errors. The handler translates:

```go
// service layer — domain errors
var ErrUserNotFound = errors.New("user not found")
var ErrEmailTaken   = errors.New("email already taken")

func (s *UserService) Create(ctx context.Context, req CreateUserReq) (*User, error) {
    if exists, _ := s.repo.EmailExists(ctx, req.Email); exists {
        return nil, fmt.Errorf("create user: %w", ErrEmailTaken)
    }
    // ...
}

// handler layer — translates domain errors to HTTP errors
func (h *UserHandler) CreateUser(w http.ResponseWriter, r *http.Request) {
    user, err := h.svc.Create(r.Context(), req)
    if err != nil {
        switch {
        case errors.Is(err, services.ErrEmailTaken):
            middleware.WriteError(w, r, appErrors.Conflict("email address is already registered"))
        default:
            middleware.WriteError(w, r, appErrors.Internal(err))
        }
        return
    }
    // ...
}
```

### Pattern 4: Error Boundary Middleware

For multi-tenant systems, add tenant context to every error log:

```go
func tenantErrorContext(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        next.ServeHTTP(w, r)
        // If response was a 5xx, log with tenant context
    })
}
```

---

## 9. Common Pitfalls

### Pitfall 1: Logging and Returning the Same Error at Multiple Levels

```go
// BAD — error gets logged at every layer, creating duplicate log entries
func (r *UserRepo) FindByID(ctx context.Context, id string) (*User, error) {
    user, err := r.db.Get(ctx, id)
    if err != nil {
        log.Error("db error", err) // logs here
        return nil, err
    }
    return user, nil
}

func (s *UserService) GetByID(ctx context.Context, id string) (*User, error) {
    user, err := s.repo.FindByID(ctx, id)
    if err != nil {
        log.Error("repo error", err) // AND here — duplicate log
        return nil, err
    }
    return user, nil
}

// GOOD — log once, at the boundary (handler or global middleware)
// Lower layers just wrap and propagate
func (r *UserRepo) FindByID(ctx context.Context, id string) (*User, error) {
    user, err := r.db.Get(ctx, id)
    if err != nil {
        return nil, fmt.Errorf("FindByID(id=%s): %w", id, err) // wrap, don't log
    }
    return user, nil
}
```

### Pitfall 2: Losing Error Context with String Formatting

```go
// BAD — wraps with %v, not %w — errors.Is/As won't work
return nil, fmt.Errorf("db error: %v", err) // can't unwrap

// GOOD — wraps with %w
return nil, fmt.Errorf("db error: %w", err) // can unwrap
```

### Pitfall 3: Panic in Request Handler Without Recovery Middleware

If any goroutine panics without recovery, the entire Go process crashes. Always install recovery middleware.

### Pitfall 4: Catching `Exception` in Python and Continuing

```python
# BAD — catches everything including SystemExit, KeyboardInterrupt
try:
    result = do_something()
except Exception:
    pass  # swallowed — you have no idea what broke

# GOOD — be specific or at minimum log and re-raise
try:
    result = do_something()
except SomeSpecificError as e:
    logger.warning("expected failure", exc_info=True)
    result = default_value
except Exception:
    logger.exception("unexpected error")
    raise  # re-raise — let it propagate
```

### Pitfall 5: Not Checking `errors.Is` When Errors Might Be Wrapped

```go
// BAD — breaks when error is wrapped
if err == sql.ErrNoRows { ... }

// GOOD — traverses the entire error chain
if errors.Is(err, sql.ErrNoRows) { ... }
```

### Pitfall 6: Leaking Internal Error Details to Clients

```go
// BAD
json.NewEncoder(w).Encode(map[string]string{
    "error": err.Error(), // might contain SQL query, file path, etc.
})

// GOOD
json.NewEncoder(w).Encode(map[string]interface{}{
    "error": map[string]string{
        "code":    "INTERNAL_ERROR",
        "message": "internal server error", // generic, safe
    },
})
// Log the full err internally
```

### Pitfall 7: Express Error Middleware with Wrong Arity

```javascript
// BAD — Express won't recognize this as an error handler (only 3 args)
app.use((err, req, res) => {
    res.status(500).json({ error: err.message });
});

// GOOD — must have exactly 4 parameters
app.use((err, req, res, next) => {
    res.status(500).json({ error: err.message });
});
```

---

## 10. Interview Questions & Answers

### Q1: What is error wrapping in Go and why is it important?

**Answer:** Error wrapping means attaching an existing error as the "cause" of a new error using `fmt.Errorf("context: %w", originalErr)`. The `%w` verb stores a reference to the original error so it can be retrieved later with `errors.Is` and `errors.As`.

**Why it matters:**
1. **Context preservation** — each layer adds what it knows without discarding the original cause
2. **Root cause analysis** — you can inspect the full error chain at the top level
3. **Type-based handling** — `errors.As` lets you extract typed errors (e.g., `*pq.Error`) from anywhere in the chain, even if it was wrapped multiple times
4. **Better logs** — the final error message reads like a breadcrumb trail: `"handler: service: repo: pq: connection refused"`

Without wrapping, you'd either lose the original error (use `%v`) or re-check errors at every layer (verbose and fragile).

---

### Q2: How do you handle unhandled promise rejections in Node.js?

**Answer:** In Node.js 15+, an unhandled promise rejection terminates the process with exit code 1. The correct approach is:

1. **Always attach `.catch()` or use `try/catch` with `async/await`** for every Promise
2. **Use an `asyncHandler` wrapper** around Express route handlers to route rejected Promises to `next(err)`
3. **Register `process.on('unhandledRejection')`** as a last-resort handler that logs the error and initiates graceful shutdown

```javascript
process.on('unhandledRejection', (reason) => {
    logger.fatal({ reason }, 'Unhandled rejection — shutting down');
    server.close(() => process.exit(1));
});
```

The key insight for interviewers: you should **crash on unhandled rejection** rather than continue, because the process is in an unknown state. Process managers (PM2, Kubernetes) will restart you.

---

### Q3: What is the difference between operational errors and programming errors?

**Answer:**

| | Operational Error | Programming Error |
|---|---|---|
| **Cause** | Expected failure at runtime | Bug in code |
| **Examples** | DB connection refused, user not found, timeout | Null dereference, off-by-one, wrong type |
| **Recovery** | Yes — handle gracefully | No — restart is safest |
| **Response** | Return structured error to client | Log full stack, crash or 500 |
| **Go** | Return `error` | `panic` |
| **Node.js** | Throw `AppError` subclass | Throw `TypeError`, `ReferenceError` |

The practical implication: operational errors should not alert on-call unless they spike. Programming errors should always alert because they indicate a bug that must be fixed.

---

### Q4: How should you structure error responses?

**Answer:** Use a consistent envelope:

```json
{
  "error": {
    "code": "machine-readable string like NOT_FOUND",
    "message": "human-readable, safe to show to users",
    "request_id": "for log correlation",
    "fields": [optional array for validation errors]
  }
}
```

Key principles:
- **Consistent shape** — clients can always parse `error.code` regardless of endpoint
- **Machine-readable code** — clients can branch on `NOT_FOUND` without string-matching
- **Never leak internals** — no stack traces, SQL, file paths
- **Request ID** — lets support staff correlate client report with server logs
- **Field errors** — for 400/422, tell the client exactly which fields failed and why

RFC 7807 extends this with `type` (a URI) and `instance` (the request path), useful for public APIs.

---

### Q5: What should you log vs what should you return to the client?

**Answer:**

**Log (server-side):**
- Full stack trace
- Original error from library (e.g., `pq.Error` with code and query)
- Request ID, user ID, tenant ID, session ID
- Request method, path, duration
- Internal variable values relevant to debugging

**Return to client:**
- Machine-readable error code (`NOT_FOUND`, `VALIDATION_ERROR`)
- Human-readable message (sanitized — no internal details)
- Request ID (for correlation only — client can report it to support)
- Field-level errors for validation failures

**Never return:** Stack traces, SQL queries, connection strings, internal file paths, library error messages, environment details.

---

### Q6: How does FastAPI's exception handling work?

**Answer:** FastAPI has three exception handling layers:

1. **`HTTPException`** — built-in, used anywhere in a route. FastAPI catches it and returns a JSON response with `status_code` and `detail`.

2. **`@app.exception_handler(ExcType)`** — custom handler for a specific exception type. FastAPI calls the handler whenever that exception type (or subclass) is raised in a route. You have full control over the response shape.

3. **`RequestValidationError`** — automatically raised by Pydantic when the request body or path/query params don't match the schema. You can override its default handler to customize the response shape.

4. **Starlette's `ServerErrorMiddleware`** — catches any uncaught exception and returns a 500. You can override the `Exception` handler to customize this.

Registration order matters: FastAPI checks handlers from most specific to least specific. Register `AppError` before `Exception` to ensure subclasses are handled correctly.

---

## 11. Resources

- [Go Blog: Error handling and Go](https://go.dev/blog/error-handling-and-go)
- [Go Blog: Working with Errors in Go 1.13](https://go.dev/blog/go1.13-errors)
- [pkg/errors (archived) — understand the history](https://github.com/pkg/errors)
- [Express Error Handling Guide](https://expressjs.com/en/guide/error-handling.html)
- [FastAPI Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [RFC 7807 — Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc7807)
- [Node.js Best Practices: Error Handling](https://github.com/goldbergyoni/nodebestpractices#2-error-handling-practices)
- [Joyent Error Handling in Node.js (classic)](https://www.joyent.com/node-js/production/design/errors)

---

**Next:** [Part 11.2: Circuit Breakers, Retries, Timeouts & Bulkhead](./11-circuit-breakers-retries.md)
