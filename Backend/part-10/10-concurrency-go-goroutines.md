# Part 10.1: Go Concurrency — Goroutines, Channels & Context

## What You'll Learn
- How the Go runtime schedules goroutines — the M:N threading model
- Work-stealing scheduler internals: G, M, P and how goroutines run efficiently
- Goroutine stacks — why 2KB start size matters
- Channels: unbuffered vs buffered, send/receive semantics, select, close
- Fan-out, fan-in, pipeline patterns with channels
- `context.Context` — the foundation of cancellation and timeouts in Go
- sync primitives: Mutex, RWMutex, Once, Map, atomic operations
- Worker pool, semaphore, and graceful shutdown patterns
- Goroutine leaks — how they happen and how to detect them
- Full working code: worker pool, pipeline, context propagation, HTTP handler

## Table of Contents
1. [Go Runtime Model](#go-runtime-model)
2. [Goroutines](#goroutines)
3. [Goroutine Leaks](#goroutine-leaks)
4. [Channels](#channels)
5. [Select Statement](#select-statement)
6. [Channel Patterns](#channel-patterns)
7. [context.Context](#contextcontext)
8. [Synchronization Primitives](#synchronization-primitives)
9. [Atomic Operations](#atomic-operations)
10. [The Race Detector](#the-race-detector)
11. [Common Concurrency Patterns](#common-concurrency-patterns)
12. [Implementation Examples](#implementation-examples)
13. [Common Pitfalls](#common-pitfalls)
14. [Interview Questions](#interview-questions)
15. [Resources](#resources)

---

## Go Runtime Model

### M:N Threading

Go uses an **M:N threading model**: M goroutines are multiplexed over N OS threads by the Go scheduler. This is different from 1:1 threading (one OS thread per goroutine) used by most other runtimes.

```
M:N Threading Model:

  Goroutines (G):    G1  G2  G3  G4  G5  G6  G7  G8  ...  (thousands/millions)
                      \  |  /    \  |  /
  Processors (P):    [P0]        [P1]        (GOMAXPROCS = 2)
                      |            |
  OS Threads (M):   [M0]         [M1]        (OS-level threads)
                      |            |
  CPU Cores:        Core 0       Core 1
```

### The GMP Model

The Go scheduler uses three entities:

**G (Goroutine)**: The unit of execution. Holds the function to run and its stack. Goroutines are Go's equivalent of lightweight threads — but they're managed by the Go runtime, not the OS.

**M (Machine)**: An OS thread. Executes Go code. There are typically a small number of M's (on the order of GOMAXPROCS). M's are created by the runtime and handed back to the OS pool when idle.

**P (Processor)**: A logical processor. P holds a local run queue of goroutines ready to execute. GOMAXPROCS controls how many P's exist — this determines the degree of parallelism. Each M must hold a P to execute Go code.

```
Detailed GMP State:

P0 (local run queue: [G3, G5, G8]):
  M0 is executing G1
  
P1 (local run queue: [G4, G6]):
  M1 is executing G2

Global run queue: [G7, G9, G10, ...]

Scheduler behavior:
  - Each P drains its local run queue
  - If local queue empty: steal from another P's queue (work stealing)
  - If all P queues empty: pull from global run queue
  - If still empty: M parks (goes idle)
```

### Work-Stealing Scheduler

Work stealing ensures CPU cores stay busy even when goroutines are unevenly distributed:
1. P runs out of goroutines in its local queue
2. P tries to steal half the goroutines from another random P's queue
3. If all queues empty, P spins briefly then parks its M

This means goroutines are automatically load-balanced across CPUs without programmer intervention.

### Goroutine Stack

A goroutine starts with a **2KB stack** (not 1MB+ like OS threads). When a goroutine's stack grows (via deeply nested function calls), the Go runtime **copies the stack** to a new, larger location. This is called a **segmented/copying stack** — stacks grow and shrink dynamically.

```
OS Thread stack:   Fixed 1-8MB → large footprint even for idle threads
Goroutine stack:   Starts at 2KB → grows only as needed → 1M goroutines = ~2GB baseline
                   Shrinks back when functions return (collected by GC)
```

This is why you can run millions of goroutines: each idle goroutine costs only 2KB.

### GOMAXPROCS

`GOMAXPROCS` sets the number of P's (logical processors) — and therefore the maximum number of OS threads executing Go code simultaneously.

```go
import "runtime"

// Default: number of CPU cores on the machine
runtime.GOMAXPROCS(0)  // 0 = query current value
runtime.GOMAXPROCS(4)  // set to 4 logical processors

// In containers: GOMAXPROCS defaults to host CPU count, not container CPU limit
// Use: github.com/uber-go/automaxprocs to auto-detect container limits
import _ "go.uber.org/automaxprocs"
```

When to change GOMAXPROCS:
- **CPU-bound workloads**: Default (= CPU count) is usually correct
- **Containers with CPU limits**: Use automaxprocs to read cgroup limits
- **I/O-bound workloads**: Higher GOMAXPROCS rarely helps (I/O waits, not CPU)
- **Garbage-sensitive apps**: Lower GOMAXPROCS reduces GC pause time

### Context Switching Cost

| | Goroutine | OS Thread |
|---|---|---|
| **Stack size** | 2KB (grows) | 1-8MB (fixed) |
| **Create time** | ~1 microsecond | ~1 millisecond |
| **Switch time** | ~100 nanoseconds | ~1 microsecond |
| **Scheduling** | Go runtime (user space) | OS kernel |
| **Max practical** | Millions | Thousands |

---

## Goroutines

### Spawning a Goroutine

```go
// Fire and forget — no way to wait, no way to collect errors
go func() {
    fmt.Println("running in goroutine")
}()

// Goroutine with a parameter (capture by value, not by reference)
for i := 0; i < 5; i++ {
    i := i // shadow i — create new binding per iteration!
    go func() {
        fmt.Println(i)
    }()
}

// Without shadowing (WRONG — all goroutines capture the same 'i'):
for i := 0; i < 5; i++ {
    go func() {
        fmt.Println(i) // i may be 5 for all goroutines — data race!
    }()
}
```

### sync.WaitGroup

WaitGroup lets you wait for a collection of goroutines to complete.

```go
package main

import (
    "fmt"
    "sync"
)

func processItems(items []string) {
    var wg sync.WaitGroup

    for _, item := range items {
        wg.Add(1)             // increment counter BEFORE spawning goroutine
        item := item          // capture by value
        go func() {
            defer wg.Done()   // decrement counter when goroutine exits
            process(item)
        }()
    }

    wg.Wait()  // block until counter reaches 0
    fmt.Println("All items processed")
}

func process(item string) {
    fmt.Println("processing:", item)
}
```

### errgroup — WaitGroup with Error Propagation

`golang.org/x/sync/errgroup` extends WaitGroup to collect errors:

```go
import "golang.org/x/sync/errgroup"

func processItemsWithErrors(ctx context.Context, items []string) error {
    g, ctx := errgroup.WithContext(ctx)

    for _, item := range items {
        item := item
        g.Go(func() error {
            return processWithError(ctx, item)
        })
    }

    // Wait returns the FIRST non-nil error (and cancels ctx for others)
    return g.Wait()
}

func processWithError(ctx context.Context, item string) error {
    select {
    case <-ctx.Done():
        return ctx.Err()
    default:
        if item == "bad" {
            return fmt.Errorf("failed to process item: %s", item)
        }
        return nil
    }
}
```

---

## Goroutine Leaks

A **goroutine leak** occurs when a goroutine is spawned but never terminates — it stays in memory consuming resources indefinitely.

### Common Leak Patterns

**1. Blocked send on unbuffered channel with no receiver**
```go
// LEAK: goroutine blocks forever trying to send
func leak1() {
    ch := make(chan int)
    go func() {
        ch <- 1  // blocks forever — nobody reads from ch
    }()
    // function returns, ch goes out of scope, but goroutine is stuck
}

// FIX: use buffered channel or ensure receiver
func noLeak1() {
    ch := make(chan int, 1)  // buffered — send doesn't block
    go func() {
        ch <- 1
    }()
    <-ch  // ensure we read
}
```

**2. Blocked receive with no sender and no cancel**
```go
// LEAK: goroutine waits forever for data that never comes
func leak2() {
    ch := make(chan int)
    go func() {
        val := <-ch  // blocks forever if nobody sends
        fmt.Println(val)
    }()
}

// FIX: use context for cancellation
func noLeak2(ctx context.Context) {
    ch := make(chan int)
    go func() {
        select {
        case val := <-ch:
            fmt.Println(val)
        case <-ctx.Done():
            return  // goroutine exits when context cancelled
        }
    }()
}
```

**3. HTTP request handler leaks goroutine**
```go
// LEAK: if the HTTP request times out, the downstream call goroutine keeps running
func handleRequest(w http.ResponseWriter, r *http.Request) {
    resultCh := make(chan string)
    go func() {
        result := callSlowService()  // takes 30 seconds
        resultCh <- result           // nobody reads — HTTP already returned timeout
    }()
    
    select {
    case result := <-resultCh:
        w.Write([]byte(result))
    case <-time.After(5 * time.Second):
        http.Error(w, "timeout", http.StatusGatewayTimeout)
        // goroutine is now leaked — still running callSlowService()
    }
}

// FIX: pass request context to downstream call
func handleRequestFixed(w http.ResponseWriter, r *http.Request) {
    resultCh := make(chan string, 1)  // buffered so goroutine can exit
    go func() {
        result, err := callSlowServiceWithContext(r.Context())
        if err != nil {
            return  // context cancelled — goroutine exits cleanly
        }
        resultCh <- result
    }()
    
    select {
    case result := <-resultCh:
        w.Write([]byte(result))
    case <-r.Context().Done():
        http.Error(w, "timeout", http.StatusGatewayTimeout)
    }
}
```

### Detecting Goroutine Leaks

```go
// In tests: use goleak package
import "go.uber.org/goleak"

func TestMyHandler(t *testing.T) {
    defer goleak.VerifyNone(t)  // fails test if goroutines leak
    
    // ... test code ...
}

// In production: expose goroutine count via metrics
import "runtime"

func goroutineCount() int {
    return runtime.NumGoroutine()
}
// Alert when goroutine count grows unboundedly over time
```

---

## Channels

### Unbuffered Channels

An unbuffered channel has capacity 0. A **send blocks until a receiver is ready**, and a **receive blocks until a sender is ready**. Both sides must be present simultaneously — it's a synchronous handoff.

```go
ch := make(chan int)  // unbuffered

// Send blocks: goroutine is parked until someone receives
go func() { ch <- 42 }()

// Receive unblocks the sender
val := <-ch  // val == 42
```

Use unbuffered channels when you want guaranteed synchronization: "I know my goroutine received the value before I move on."

### Buffered Channels

A buffered channel has capacity N. **Sends don't block until the buffer is full**. **Receives don't block until the buffer is empty**.

```go
ch := make(chan int, 3)  // buffered, capacity 3

ch <- 1  // doesn't block (buffer: [1])
ch <- 2  // doesn't block (buffer: [1, 2])
ch <- 3  // doesn't block (buffer: [1, 2, 3])
ch <- 4  // BLOCKS — buffer is full

val := <-ch  // val == 1 (FIFO)
ch <- 4  // now succeeds (buffer: [2, 3, 4])
```

Use buffered channels to:
- Decouple producer and consumer speeds
- Implement semaphores (capacity = max concurrency)
- Prevent goroutine leaks when receiver may be gone

### Channel Directions

In function signatures, you can restrict channel direction to communicate intent and prevent misuse:

```go
func producer(ch chan<- int) {  // send-only
    ch <- 42
    // <-ch  // compile error: cannot receive from send-only channel
}

func consumer(ch <-chan int) {  // receive-only
    val := <-ch
    // ch <- 1  // compile error: cannot send to receive-only channel
}

func main() {
    ch := make(chan int, 1)
    producer(ch)  // bidirectional converts to send-only at call site
    consumer(ch)  // bidirectional converts to receive-only at call site
}
```

### Close Semantics

Closing a channel signals that no more values will be sent.

```go
ch := make(chan int, 3)
ch <- 1
ch <- 2
ch <- 3
close(ch)

// Reading from closed channel:
val, ok := <-ch    // ok=true, val=1 (buffered values drain first)
val, ok = <-ch     // ok=true, val=2
val, ok = <-ch     // ok=true, val=3
val, ok = <-ch     // ok=false, val=0 (zero value) — channel exhausted

// Range loop: exits when channel closed AND drained
for val := range ch {
    fmt.Println(val)
}
// Equivalent to: read until ok=false

// PANICS: sending to a closed channel, or closing an already-closed channel
close(ch)  // panic: close of closed channel
ch <- 4    // panic: send on closed channel
```

**The ownership rule**: Only the sender should close a channel. Never close from the receiver side. If multiple goroutines send to the same channel, use a WaitGroup to close after all senders are done.

```go
var wg sync.WaitGroup
ch := make(chan int)

for i := 0; i < 3; i++ {
    wg.Add(1)
    go func(i int) {
        defer wg.Done()
        ch <- i
    }(i)
}

// Closer goroutine: waits for all senders, then closes
go func() {
    wg.Wait()
    close(ch)
}()

for val := range ch {
    fmt.Println(val)
}
```

---

## Select Statement

`select` lets a goroutine wait on multiple channel operations. It executes the first case that's ready; if multiple cases are ready, it picks one at random.

```go
// Basic select
select {
case msg := <-ch1:
    fmt.Println("received from ch1:", msg)
case msg := <-ch2:
    fmt.Println("received from ch2:", msg)
case ch3 <- "hello":
    fmt.Println("sent to ch3")
}

// Non-blocking operation using default
select {
case msg := <-ch:
    fmt.Println("got:", msg)
default:
    fmt.Println("no message ready")  // executes immediately if ch is empty
}

// Timeout pattern
select {
case result := <-resultCh:
    return result, nil
case <-time.After(5 * time.Second):
    return nil, errors.New("operation timed out")
}

// Context cancellation
select {
case result := <-resultCh:
    return result, nil
case <-ctx.Done():
    return nil, ctx.Err()
}
```

---

## Channel Patterns

### Fan-Out

One goroutine sends work to multiple workers via channels.

```go
func fanOut(input <-chan int, numWorkers int) []<-chan int {
    outputs := make([]<-chan int, numWorkers)
    for i := 0; i < numWorkers; i++ {
        outputs[i] = worker(input)  // each worker reads from same input channel
    }
    return outputs
}

func worker(input <-chan int) <-chan int {
    output := make(chan int)
    go func() {
        defer close(output)
        for n := range input {
            output <- n * n  // process and forward
        }
    }()
    return output
}
```

### Fan-In (Multiplexing)

Merge multiple channels into one.

```go
func fanIn(channels ...<-chan int) <-chan int {
    merged := make(chan int)
    var wg sync.WaitGroup

    output := func(ch <-chan int) {
        defer wg.Done()
        for val := range ch {
            merged <- val
        }
    }

    wg.Add(len(channels))
    for _, ch := range channels {
        go output(ch)
    }

    // Close merged when all inputs are exhausted
    go func() {
        wg.Wait()
        close(merged)
    }()

    return merged
}
```

### Pipeline Pattern

Chain stages of processing. Each stage reads from its input channel and writes to its output channel.

```go
// Stage 1: generate
func generate(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for _, n := range nums {
            out <- n
        }
    }()
    return out
}

// Stage 2: square
func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for n := range in {
            out <- n * n
        }
    }()
    return out
}

// Stage 3: filter (only evens)
func filterEven(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for n := range in {
            if n%2 == 0 {
                out <- n
            }
        }
    }()
    return out
}

// Usage: compose a pipeline
func main() {
    nums := generate(1, 2, 3, 4, 5)
    squares := square(nums)
    evens := filterEven(squares)
    
    for v := range evens {
        fmt.Println(v)  // 4, 16 (2²=4, 4²=16)
    }
}
```

### Done Channel for Cancellation

Before `context.Context` became standard, "done channels" were the cancellation primitive:

```go
func processWithDone(done <-chan struct{}, input <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for {
            select {
            case <-done:
                return
            case n, ok := <-input:
                if !ok {
                    return
                }
                out <- n * 2
            }
        }
    }()
    return out
}
```

Today, prefer `context.Context` over done channels — it's the idiomatic Go approach.

---

## context.Context

### What context.Context Provides

1. **Cancellation**: cancel a tree of goroutines when a parent operation is done
2. **Deadline**: cancel after a specific time.Time
3. **Timeout**: cancel after a duration
4. **Request-scoped values**: pass trace IDs, auth tokens across function calls without changing signatures

### The Context Tree

```
context.Background()
    │
    ├─ WithCancel → cancel() signals this node and all children
    │       │
    │       ├─ WithTimeout → auto-cancels after duration
    │       │       │
    │       │       └─ WithValue → carries request-scoped data
    │
    └─ WithDeadline → auto-cancels at absolute time.Time

When any parent is cancelled, ALL its children are cancelled too.
```

### Creating Contexts

```go
// Root contexts (always valid)
ctx := context.Background()  // non-nil, never cancelled — use as root
ctx := context.TODO()        // same as Background, but signals "placeholder, will be replaced"

// Cancellable context — you call cancel() to stop everything
ctx, cancel := context.WithCancel(parent)
defer cancel()  // ALWAYS defer cancel to avoid goroutine leaks

// Timeout context — auto-cancels after duration
ctx, cancel := context.WithTimeout(parent, 5*time.Second)
defer cancel()

// Deadline context — auto-cancels at specific time
deadline := time.Now().Add(5 * time.Second)
ctx, cancel := context.WithDeadline(parent, deadline)
defer cancel()

// Value context — attach request-scoped data
type contextKey string
const requestIDKey contextKey = "request_id"

ctx = context.WithValue(parent, requestIDKey, "req-123")
requestID := ctx.Value(requestIDKey).(string)  // retrieve
```

### Context Propagation

```go
// CORRECT: pass ctx as first argument
func handler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()  // request context — cancelled when client disconnects
    
    result, err := fetchData(ctx, "user-123")
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    json.NewEncoder(w).Encode(result)
}

func fetchData(ctx context.Context, userID string) (*User, error) {
    // Pass ctx to DB query — query aborts if context is cancelled
    row := db.QueryRowContext(ctx, "SELECT * FROM users WHERE id=$1", userID)
    // ...
}

// WRONG: storing context in struct (anti-pattern)
type Service struct {
    ctx context.Context  // DON'T DO THIS
}
```

### Checking Context in Long Loops

```go
func processLargeDataset(ctx context.Context, items []Item) error {
    for i, item := range items {
        // Check for cancellation every iteration (or every N iterations for performance)
        select {
        case <-ctx.Done():
            log.Printf("Processing cancelled after %d items: %v", i, ctx.Err())
            return ctx.Err()
        default:
            // continue
        }
        
        if err := processItem(ctx, item); err != nil {
            return err
        }
    }
    return nil
}
```

### Context Values — Type-Safe Pattern

Use unexported custom types as keys to avoid collision between packages:

```go
package middleware

// Unexported type prevents external packages from constructing the same key
type contextKey int

const (
    requestIDKey contextKey = iota
    userIDKey
    traceSpanKey
)

func WithRequestID(ctx context.Context, id string) context.Context {
    return context.WithValue(ctx, requestIDKey, id)
}

func RequestID(ctx context.Context) (string, bool) {
    id, ok := ctx.Value(requestIDKey).(string)
    return id, ok
}
```

---

## Synchronization Primitives

### sync.Mutex

A mutual exclusion lock. Only one goroutine can hold it at a time.

```go
type SafeCounter struct {
    mu    sync.Mutex
    count int
}

func (c *SafeCounter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}

func (c *SafeCounter) Value() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.count
}
```

### sync.RWMutex

Allows multiple concurrent readers OR one writer. Use when reads significantly outnumber writes.

```go
type SafeCache struct {
    mu    sync.RWMutex
    cache map[string]string
}

func (c *SafeCache) Get(key string) (string, bool) {
    c.mu.RLock()         // multiple goroutines can RLock simultaneously
    defer c.mu.RUnlock()
    val, ok := c.cache[key]
    return val, ok
}

func (c *SafeCache) Set(key, value string) {
    c.mu.Lock()          // exclusive lock — no readers allowed while writing
    defer c.mu.Unlock()
    c.cache[key] = value
}

// RWMutex is beneficial when:
// - Reads are >> writes (cache, config, registry)
// - Read operations are fast (short critical section)
// NOT beneficial when:
// - Writes are frequent — read lock acquisition has overhead
// - Read operations are slow — holds read lock too long, blocks writers
```

### sync.Once

Ensures a function is called exactly once, safe for concurrent use. Perfect for lazy initialization.

```go
var (
    instance *DatabaseConnection
    once     sync.Once
)

func GetDB() *DatabaseConnection {
    once.Do(func() {
        // Called exactly once, even if GetDB() called concurrently by many goroutines
        instance = &DatabaseConnection{
            pool: newConnectionPool(),
        }
    })
    return instance
}

// Once blocks all callers until the initialization function returns.
// If the function panics, Once considers it "done" — subsequent calls won't retry.
```

### sync.Map

A concurrent-safe map optimized for two scenarios:
1. Write once, read many times (stable keys)
2. Many goroutines each writing/reading different keys (no key overlap)

NOT beneficial when goroutines read and update the same keys (use map + RWMutex instead).

```go
var m sync.Map

// Store
m.Store("key", "value")

// Load
val, ok := m.Load("key")
if ok {
    fmt.Println(val.(string))
}

// LoadOrStore — atomic: load if exists, store if not
actual, loaded := m.LoadOrStore("key", "default")
// loaded=true: key existed, actual=existing value
// loaded=false: key didn't exist, actual="default" (now stored)

// Delete
m.Delete("key")

// Range — iterate all key-value pairs
m.Range(func(key, value interface{}) bool {
    fmt.Printf("%v: %v\n", key, value)
    return true  // return false to stop iteration
})

// When to prefer map+RWMutex:
// - You need to iterate and modify concurrently
// - You need to check length (sync.Map has no Len())
// - Keys are known/stable and read rate >> write rate
```

---

## Atomic Operations

`sync/atomic` provides lock-free atomic operations on integers and pointers. Much faster than mutexes for simple counter/flag operations.

```go
import "sync/atomic"

// Atomic counter
var counter int64

atomic.AddInt64(&counter, 1)          // increment
atomic.AddInt64(&counter, -1)         // decrement
val := atomic.LoadInt64(&counter)     // read
atomic.StoreInt64(&counter, 0)        // write

// Compare and swap (CAS) — the foundation of lock-free data structures
// Sets val to newVal only if val==expected
swapped := atomic.CompareAndSwapInt64(&counter, 5, 10)
// If counter was 5, it's now 10, swapped=true
// If counter wasn't 5, unchanged, swapped=false

// Atomic bool flag for shutdown/done signals
var done int32  // 0=running, 1=stopped

// Set done flag
atomic.StoreInt32(&done, 1)

// Check done flag (in tight loops, cheaper than select on channel)
if atomic.LoadInt32(&done) == 1 {
    return
}

// Go 1.19+: typed atomic values
var atomicBool atomic.Bool
atomicBool.Store(true)
atomicBool.Load()

var atomicInt atomic.Int64
atomicInt.Add(1)
```

---

## The Race Detector

The Go race detector instruments memory accesses at compile time and reports data races at runtime. Always run tests with `-race`.

```bash
# Run tests with race detector
go test -race ./...

# Build with race detector (for canary testing in staging)
go build -race -o myapp

# Run with race detector
go run -race main.go
```

```go
// Data race example (race detector catches this):
var count int

go func() { count++ }()  // write
go func() { count++ }()  // write (concurrent with first write)
// Race detected: multiple goroutines accessing 'count' without synchronization

// Fix: use atomic or mutex
var count int64
go func() { atomic.AddInt64(&count, 1) }()
go func() { atomic.AddInt64(&count, 1) }()
```

The race detector has ~2-20x overhead. Use in:
- All unit and integration tests (`go test -race ./...` in CI)
- Canary builds in staging
- Never in production (performance impact)

---

## Common Concurrency Patterns

### Worker Pool

Limit concurrent goroutines processing work from a channel.

```go
package main

import (
    "context"
    "fmt"
    "sync"
)

type Job struct {
    ID    int
    Input string
}

type Result struct {
    JobID  int
    Output string
    Err    error
}

// WorkerPool processes jobs concurrently with a fixed number of workers
func WorkerPool(ctx context.Context, numWorkers int, jobs <-chan Job) <-chan Result {
    results := make(chan Result, numWorkers)

    var wg sync.WaitGroup
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        workerID := i
        go func() {
            defer wg.Done()
            for {
                select {
                case job, ok := <-jobs:
                    if !ok {
                        return  // jobs channel closed, worker exits
                    }
                    result := processJob(ctx, workerID, job)
                    select {
                    case results <- result:
                    case <-ctx.Done():
                        return
                    }
                case <-ctx.Done():
                    return
                }
            }
        }()
    }

    // Close results when all workers are done
    go func() {
        wg.Wait()
        close(results)
    }()

    return results
}

func processJob(ctx context.Context, workerID int, job Job) Result {
    // Check for cancellation before heavy work
    select {
    case <-ctx.Done():
        return Result{JobID: job.ID, Err: ctx.Err()}
    default:
    }

    output := fmt.Sprintf("worker-%d processed: %s", workerID, job.Input)
    return Result{JobID: job.ID, Output: output}
}

func main() {
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    // Create jobs channel and fill it
    jobs := make(chan Job, 100)
    for i := 0; i < 50; i++ {
        jobs <- Job{ID: i, Input: fmt.Sprintf("item-%d", i)}
    }
    close(jobs)

    // Start worker pool with 5 workers
    results := WorkerPool(ctx, 5, jobs)

    // Collect results
    for result := range results {
        if result.Err != nil {
            fmt.Printf("Job %d failed: %v\n", result.JobID, result.Err)
        } else {
            fmt.Printf("Job %d: %s\n", result.JobID, result.Output)
        }
    }
}
```

### Semaphore — Limit Concurrent Operations

```go
// Semaphore using buffered channel
type Semaphore chan struct{}

func NewSemaphore(n int) Semaphore {
    return make(Semaphore, n)
}

func (s Semaphore) Acquire() {
    s <- struct{}{}  // blocks when capacity reached
}

func (s Semaphore) Release() {
    <-s
}

// Usage: limit to 10 concurrent HTTP requests
sem := NewSemaphore(10)

for _, url := range urls {
    url := url
    go func() {
        sem.Acquire()
        defer sem.Release()
        fetchURL(url)
    }()
}

// Or use golang.org/x/sync/semaphore for context-aware version:
import "golang.org/x/sync/semaphore"

sem := semaphore.NewWeighted(10)
sem.Acquire(ctx, 1)
defer sem.Release(1)
```

### Graceful Shutdown with Context

```go
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"
)

func main() {
    // Create server
    mux := http.NewServeMux()
    mux.HandleFunc("/", handler)
    
    srv := &http.Server{
        Addr:    ":8080",
        Handler: mux,
    }

    // Start server in goroutine
    go func() {
        log.Println("Starting server on :8080")
        if err := srv.ListenAndServe(); err != http.ErrServerClosed {
            log.Fatalf("Server error: %v", err)
        }
    }()

    // Wait for shutdown signal
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    log.Println("Received shutdown signal, draining connections...")

    // Graceful shutdown: wait up to 30s for in-flight requests to complete
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    if err := srv.Shutdown(ctx); err != nil {
        log.Printf("Server forced shutdown: %v", err)
    }

    log.Println("Server exited cleanly")
}

func handler(w http.ResponseWriter, r *http.Request) {
    w.Write([]byte("OK"))
}
```

---

## Implementation Examples

### Full Go Code: Context Cancellation in HTTP Handler

```go
package main

import (
    "context"
    "database/sql"
    "encoding/json"
    "errors"
    "log"
    "net/http"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"
)

type OrderService struct {
    db *sql.DB
}

type Order struct {
    ID     string  `json:"id"`
    UserID string  `json:"user_id"`
    Amount float64 `json:"amount"`
    Status string  `json:"status"`
}

func (s *OrderService) GetOrder(w http.ResponseWriter, r *http.Request) {
    orderID := chi.URLParam(r, "orderID")
    ctx := r.Context()  // inherits deadline from chi's timeout middleware

    // Fetch order with 3-second DB timeout
    dbCtx, cancel := context.WithTimeout(ctx, 3*time.Second)
    defer cancel()

    order, err := s.fetchOrderFromDB(dbCtx, orderID)
    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) {
            http.Error(w, "database timeout", http.StatusGatewayTimeout)
            return
        }
        if errors.Is(err, sql.ErrNoRows) {
            http.Error(w, "order not found", http.StatusNotFound)
            return
        }
        log.Printf("ERROR fetching order %s: %v", orderID, err)
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(order)
}

func (s *OrderService) fetchOrderFromDB(ctx context.Context, id string) (*Order, error) {
    row := s.db.QueryRowContext(ctx, "SELECT id, user_id, amount, status FROM orders WHERE id=$1", id)
    
    var o Order
    if err := row.Scan(&o.ID, &o.UserID, &o.Amount, &o.Status); err != nil {
        return nil, err
    }
    return &o, nil
}

func main() {
    db, _ := sql.Open("postgres", "postgres://localhost/orders")
    svc := &OrderService{db: db}

    r := chi.NewRouter()
    r.Use(middleware.RequestID)
    r.Use(middleware.Logger)
    r.Use(middleware.Timeout(10 * time.Second))  // sets deadline on request context
    
    r.Get("/orders/{orderID}", svc.GetOrder)
    
    http.ListenAndServe(":8080", r)
}
```

### Mutex vs RWMutex — When Each Wins

```go
package main

import (
    "sync"
    "testing"
)

// Scenario: cache with 90% reads, 10% writes

// Using sync.Mutex (suboptimal for read-heavy workloads)
type MutexCache struct {
    mu    sync.Mutex
    data  map[string]string
}

func (c *MutexCache) Get(key string) (string, bool) {
    c.mu.Lock()
    defer c.mu.Unlock()
    val, ok := c.data[key]
    return val, ok
    // All concurrent readers serialize here, even though they don't write
}

// Using sync.RWMutex (better for read-heavy workloads)
type RWCache struct {
    mu   sync.RWMutex
    data map[string]string
}

func (c *RWCache) Get(key string) (string, bool) {
    c.mu.RLock()          // Multiple goroutines can hold RLock simultaneously
    defer c.mu.RUnlock()
    val, ok := c.data[key]
    return val, ok
}

func (c *RWCache) Set(key, val string) {
    c.mu.Lock()           // Exclusive: no readers or writers while setting
    defer c.mu.Unlock()
    c.data[key] = val
}

// Benchmark results (read-heavy, 8 goroutines):
// BenchmarkMutexCache-8    5000000    234 ns/op
// BenchmarkRWCache-8      20000000     67 ns/op  ← ~3.5x faster
```

---

## Common Pitfalls

**1. Closing a channel from multiple goroutines**
Only one goroutine should close a channel (the owner/sender). Multiple closers → panic.

**2. Forgetting to cancel context**
`context.WithCancel` / `WithTimeout` leak memory if cancel is never called. Always `defer cancel()` immediately after creating a cancellable context.

**3. Passing context in struct fields**
Context should be passed as the first function argument, not stored in structs. Structs have lifetimes independent of requests; contexts don't.

**4. Capturing loop variable in goroutine**
```go
for i := 0; i < 5; i++ {
    go func() { fmt.Println(i) }()  // i is captured by reference, all print 5
    // Fix: go func(i int) { fmt.Println(i) }(i)
    //  or: i := i (shadow)
}
```

**5. WaitGroup misuse**
Call `wg.Add(n)` before spawning goroutines, not inside them. If `wg.Wait()` is called before `wg.Add()` in a fast path, the program exits early.

**6. Nil channel blocks forever**
Sending to or receiving from a nil channel blocks forever — useful for disabling a select case, but an easy bug if unintentional.

**7. Large struct values in channels**
Channels copy values on send/receive. Sending large structs is expensive. Send pointers instead.

**8. sync.Mutex is not reentrant**
If a goroutine holding a lock tries to lock it again, it deadlocks. Go's mutex is not recursive/reentrant.

---

## Interview Questions

**Q: What is the difference between a goroutine and an OS thread?**

A: An OS thread is managed by the kernel, starts with 1-8MB stack, costs ~1ms to create, and context switches in ~1µs. A goroutine is managed by the Go runtime in user space, starts with a 2KB stack that grows dynamically, costs ~1µs to create, and context switches in ~100ns. The M:N scheduler multiplexes many goroutines over few OS threads. You can run millions of goroutines but only thousands of OS threads. Goroutines are cheaper to create, switch, and destroy, enabling concurrency patterns that would be impractical with OS threads.

**Q: What is GOMAXPROCS and when would you change it?**

A: GOMAXPROCS controls the number of P (processor) entities, which determines how many goroutines can execute Go code simultaneously. Defaults to the number of CPU cores. Change it: (1) In containers — default reads host CPU count, not container's CPU limit; use `automaxprocs` to read cgroup limits. (2) For CPU-bound workloads where you want to limit parallelism to reduce resource contention. (3) Rarely: I/O-bound services don't benefit from higher GOMAXPROCS since goroutines block on I/O, not CPU.

**Q: What is a goroutine leak and how do you detect it?**

A: A goroutine leak is a goroutine that never terminates — typically blocked on a channel receive with no sender, a channel send with no receiver, or waiting for a mutex that's never unlocked. Leaks accumulate over time, consuming memory. Detect with: (1) `runtime.NumGoroutine()` exposed as a metric — alert on unbounded growth. (2) `go.uber.org/goleak` in tests — fails the test if goroutines are leaked. (3) `go tool pprof` goroutine profile — shows all running goroutines and where they're blocked. Prevention: always pass context to goroutines; use `select` with `ctx.Done()` to unblock.

**Q: Explain the difference between buffered and unbuffered channels.**

A: An unbuffered channel (capacity 0) requires both sender and receiver to be ready simultaneously — it's a synchronous rendezvous. Send blocks until a receiver arrives; receive blocks until a sender sends. Use for synchronization guarantees. A buffered channel (capacity N) allows sends without a receiver up to capacity N. When full, sends block; when empty, receives block. Use for decoupling producer/consumer speeds and preventing goroutine leaks when the receiver may be gone.

**Q: What does closing a channel signal?**

A: Closing a channel signals "no more values will be sent." Receivers can still drain buffered values after close. The two-value receive `val, ok := <-ch` returns `ok=false` when the channel is closed and empty. `range` over a channel exits when the channel is closed and empty. Sending to a closed channel panics. Closing an already-closed channel panics. Only the sender should close (ownership principle). Use close to signal completion to consumers (e.g., "all work has been submitted").

**Q: How does context.Context help with cancellation?**

A: `context.Context` provides a tree of cancellation signals. `context.WithCancel` returns a context and a cancel function. Calling cancel() closes the `ctx.Done()` channel, which propagates through all child contexts. Functions that respect context check `ctx.Done()` in loops and before blocking operations. HTTP servers cancel the request context when the client disconnects. `database/sql`, `net/http`, and most Go standard library packages accept context and abort when it's cancelled. Without context, goroutines may continue work after the caller has moved on, wasting resources and potentially causing side effects.

**Q: What is the Go memory model and why does it matter for channels?**

A: The Go memory model defines when one goroutine is guaranteed to observe the writes of another. The key rule: a **send on a channel happens before the corresponding receive completes** (for unbuffered) or **closes happen before receives that return zero values**. This means after `ch <- x`, a goroutine reading `<-ch` is guaranteed to see the write to `x`. Without this guarantee, you'd need explicit memory barriers. For synchronization, you need to use channels, sync primitives, or atomic operations — plain variable access from multiple goroutines without synchronization is a data race.

**Q: When would you use sync.Map over a map with a mutex?**

A: `sync.Map` is beneficial when: (1) entries are written once and read many times (caches, service registries); (2) many goroutines access disjoint key sets (no key contention). It's NOT beneficial when: goroutines frequently read and update the same keys (higher overhead than map+RWMutex), you need to know the map's length (no Len() method), you need complex atomic operations. For most use cases, `map + sync.RWMutex` is simpler and often faster. `sync.Map`'s internal use of `interface{}` adds indirection and allocation overhead not present in typed maps.

---

## Resources

- [The Go Memory Model](https://go.dev/ref/mem)
- [Go Concurrency Patterns — Rob Pike (talk)](https://talks.golang.org/2012/concurrency.slide)
- [Advanced Go Concurrency Patterns — Sameer Ajmani (talk)](https://talks.golang.org/2013/advconc.slide)
- [Concurrency in Go — Katherine Cox-Buday (O'Reilly)](https://www.oreilly.com/library/view/concurrency-in-go/9781491941294/)
- [go.uber.org/goleak — goroutine leak detector](https://github.com/uber-go/goleak)
- [golang.org/x/sync — errgroup, semaphore](https://pkg.go.dev/golang.org/x/sync)
- [Go Blog: Pipelines and Cancellation](https://go.dev/blog/pipelines)

---

**Next:** [Part 10.2: Node.js Concurrency — Event Loop & Runtime](./10-concurrency-nodejs-event-loop.md)
