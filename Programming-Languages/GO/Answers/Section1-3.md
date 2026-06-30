# Go (Golang) Interview Question Bank — Answers (Sections 1–3)

_Covers Section 1 (Language Fundamentals & Syntax), Section 2 (Slices, Arrays, Maps), and Section 3 (Concurrency). Numbering matches the original question bank._

---

## 1. Language Fundamentals & Syntax

**1. What is Go, and what design goals motivated its creators?**
Go is a statically typed, compiled language created at Google (2007, released 2009) by Robert Griesemer, Rob Pike, and Ken Thompson. It was designed to address pain points the creators saw with large-scale software engineering at Google: slow C++ build times, complex language features that made code hard to read across large teams, and the difficulty of writing safe concurrent code. Goals included fast compilation, simplicity (a small, readable spec), built-in support for concurrency (goroutines/channels), garbage collection, and strong tooling (gofmt, go vet) to keep large codebases consistent.

**2. Main advantages of Go over Java, Python, or C++**

- Compiles to a single static binary with no runtime/VM dependency, unlike Java (JVM) or Python (interpreter).
- Much faster compilation than C++.
- Built-in, lightweight concurrency primitives (goroutines, channels) versus heavier OS threads in Java/C++ or the GIL-limited threading in Python.
- Simpler language: no generics-heavy inheritance hierarchies (pre-1.18), no operator overloading, minimal syntax — easier onboarding for large teams.
- Garbage collected (safer than C++) but with lower memory overhead and more predictable performance than Java in many service workloads.
- Strong standard library, especially for networking/HTTP, and a built-in toolchain (fmt, vet, test, mod) reducing dependency on third-party tooling.

**3. Is Go object-oriented? How does it support OOP-like patterns?**
Go has no classes or inheritance, so it isn't OOP in the classical sense, but it supports OOP patterns: structs hold state, methods can be attached to types (including non-struct types), and interfaces give polymorphism. Code reuse is achieved through composition (struct embedding) instead of inheritance — "favor composition over inheritance" is idiomatic Go.

**4. Go's type system: static or dynamic, and why it matters**
Go is statically typed — types are checked at compile time, and variables have a fixed type for their lifetime. This matters because it catches type errors before runtime, enables better compiler optimizations and tooling (autocomplete, refactoring), and removes a class of runtime bugs common in dynamically typed languages like Python or JavaScript. Go's type inference (via `:=`) gives some of Python's terseness while keeping static guarantees.

**5. Zero values**
Every type has a default "zero value" assigned when a variable is declared without an explicit initializer:

- `int` → `0`
- `string` → `""`
- `bool` → `false`
- pointer → `nil`
- slice → `nil` (a nil slice, len/cap 0, usable with append)
- map → `nil` (read-only; writing to a nil map panics)
- struct → each field set to its own zero value

**6. `var` vs `:=` vs `const`**

- `var x int = 5` (or `var x = 5`) declares a variable explicitly, can be used at package or function scope, and works without an initializer (giving the zero value).
- `x := 5` is short variable declaration with type inference; only valid inside functions, requires an initializer.
- `const x = 5` declares a compile-time constant; the value must be known at compile time, cannot be reassigned, and constants don't have an address (can't take `&x`).

**7. Variable shadowing**
Shadowing occurs when a variable declared in an inner scope has the same name as one in an outer scope, hiding the outer one within that block. A classic bug:

```go
err := doSomething()
if err != nil {
    val, err := doSomethingElse() // err here is a NEW variable, shadowing outer err
    _ = val
}
// outer err is unchanged, even if doSomethingElse failed and the inner err was checked
```

This commonly bites with `:=` inside `if`/`for` blocks where a new `err` is unintentionally created instead of reusing the outer one.

**8. `init()` function**
`init()` runs automatically after all package-level variables are initialized, before `main()`. A single package can have multiple `init()` functions (even across multiple files), and they execute in the order the files are presented to the compiler (alphabetical by filename within a package, in practice), with the order of multiple `init()`s in one file matching declaration order. Init order across packages follows dependency order: imported packages are fully initialized (including their `init()`s) before the importing package's `init()` runs.

**9. Go's looping construct**
Go has only `for`, no separate `while` or `do-while`. `for` works in multiple forms:

```go
for i := 0; i < 10; i++ {}   // classic for
for cond {}                   // while-style
for {}                        // infinite loop (do-while emulated with break)
for i, v := range coll {}     // range loop
```

Having one keyword keeps the language smaller and removes the need to learn multiple looping syntaxes.

**10. `new()` vs `make()`**

- `new(T)` allocates zeroed memory for a value of type `T` and returns a `*T` pointer to it. Works for any type.
- `make(T, args)` is only for slices, maps, and channels; it initializes the internal data structure (e.g., allocates the underlying array for a slice) and returns an initialized (non-zero, usable) value of type `T`, not a pointer.
  Use `make` when you need a working slice/map/channel; use `new` (or more commonly `&T{}`) when you want a pointer to a zeroed value of any other type.

**11. Pointers in Go**
A pointer holds the memory address of a value. They matter for performance (avoid copying large structs) and mutation semantics (a function can modify the caller's data via a pointer receiver/parameter, whereas passing by value only modifies a copy). Go pointers are safer than C pointers — no pointer arithmetic, and the garbage collector tracks pointer liveness.

**12. Pointer arithmetic**
Go does not support pointer arithmetic (`ptr++`, `ptr + 1`) outside the unsafe package. This is a deliberate safety decision: it prevents a whole class of memory-corruption bugs and keeps the garbage collector able to reason precisely about which memory is reachable.

**13. Package system & visibility**
Go organizes code into packages; a directory of `.go` files sharing a `package` declaration. Identifiers (functions, types, variables, struct fields) starting with an uppercase letter are exported (visible outside the package); lowercase ones are unexported and only accessible within the same package. There's no separate `public`/`private` keyword — visibility is determined purely by capitalization.

**14. Struct: pass by value vs by pointer**
Passing by value copies the entire struct; the function works on an independent copy and cannot mutate the caller's original. Passing by pointer (`*T`) shares the same underlying memory; mutations are visible to the caller, and it avoids the cost of copying large structs. Use pointer receivers/parameters when the struct is large, when mutation is needed, or for consistency with other pointer-receiver methods on the same type; use value receivers for small, immutable-style structs (especially in concurrent contexts where you want each goroutine to have its own copy).

**15. Named return values**

```go
func divide(a, b int) (result int, err error) {
    if b == 0 {
        err = errors.New("divide by zero")
        return // naked return, returns result=0, err
    }
    result = a / b
    return
}
```

A pitfall: combined with `defer`, a deferred function can modify named return values after the body executes but before the function actually returns, which can be surprising if not intentional (it's actually a common pattern for converting panics to errors, but can introduce bugs if the deferred closure shadows or accidentally overwrites the named return).

**16. How `defer` works**
`defer` schedules a function call to run when the surrounding function returns (in LIFO order if multiple defers are stacked). Crucially, the _arguments_ to the deferred call are evaluated immediately at the point of the `defer` statement, not when it actually executes:

```go
i := 0
defer fmt.Println(i) // captures i=0 now
i = 5
// prints 0, not 5
```

If you want the deferred call to see updated state, wrap it in a closure: `defer func() { fmt.Println(i) }()`.

**17. "defer in a loop" gotcha**

```go
for _, f := range files {
    file, _ := os.Open(f)
    defer file.Close() // BUG: all Close() calls pile up until the function returns, not the loop iteration
}
```

If the loop processes many files, all the file handles stay open until the enclosing function returns, potentially exhausting file descriptors. Fix: wrap the body in its own function so defer fires per iteration:

```go
for _, f := range files {
    func() {
        file, _ := os.Open(f)
        defer file.Close()
        // use file
    }()
}
```

**18. Blank identifier `_`**
Three common uses:

1. Ignoring a return value: `_, err := doSomething()`
2. Ignoring loop variables: `for _, v := range slice {}`
3. Import for side effects only: `import _ "net/http/pprof"` (runs the package's `init()` without using its identifiers directly).

**19. Build tags / build constraints**
Build tags are comments (or `//go:build` directives) at the top of a file that control whether the file is included in compilation, based on conditions like OS, architecture, or custom tags:

```go
//go:build linux && amd64
```

Used for platform-specific code (e.g., separate implementations for Linux vs Windows), or to separate integration tests that should only run with a specific tag (`go test -tags=integration`).

**20. `iota` and enums**
`iota` is a predeclared identifier that resets to 0 in each `const` block and increments by one per line, used to build C-style enums:

```go
type Weekday int
const (
    Sunday Weekday = iota // 0
    Monday                 // 1
    Tuesday                // 2
)
```

It can also be combined with bit shifts for flag-style enums (`1 << iota`).

**21. Type embedding (struct embedding)**
Embedding places one type inside another without naming a field, promoting the embedded type's fields and methods to the outer type:

```go
type Animal struct { Name string }
func (a Animal) Speak() string { return a.Name + " makes a sound" }

type Dog struct { Animal }
```

`Dog` gets `Speak()` "for free." Unlike inheritance, there's no `is-a` polymorphism through a base class pointer — embedding is composition; the outer type isn't substitutable for the inner type, and method resolution is based on explicit promotion, not dynamic dispatch.

**22. How Go implements interfaces (implicit/structural typing)**
A type satisfies an interface automatically if it implements all the interface's methods — there's no `implements` keyword. This is structural typing: the compiler checks method sets, not declared relationships. Benefits: decoupling (a package can define an interface without consumers needing to import or declare conformance), and the ability to retroactively satisfy interfaces defined elsewhere, enabling flexible mocking/testing.

**23. Nil interface vs nil pointer gotcha**
An interface value is internally a (type, value) pair. If you assign a nil pointer of a concrete type to an interface, the interface's type field is non-nil (it knows the concrete type), even though the value is nil. So:

```go
var p *MyError = nil
var err error = p
fmt.Println(err == nil) // false!
```

`err` is not the nil interface — it's an interface holding a `(*MyError, nil)` pair. This trips people up when a function returns a typed nil pointer as an `error` interface; the caller's `err != nil` check passes even though "logically" there's no error.

**24. Empty interface `interface{}` / `any`**
`interface{}` (aliased to `any` since Go 1.18) has zero methods, so every type satisfies it — it can hold a value of any type, similar to `Object` in Java or `void*` in C. Tradeoffs: it discards static type information, requiring type assertions/switches to recover the concrete type at runtime, losing compile-time safety and incurring some performance overhead (boxing). Generics (1.18+) replace many former uses of `interface{}` while preserving type safety.

**25. Type assertions vs type switches**
A type assertion extracts the concrete type from an interface value: `v, ok := i.(string)` (the two-value form avoids a panic if the assertion fails). A type switch checks against multiple possible types in one construct:

```go
switch v := i.(type) {
case int:
    // v is int
case string:
    // v is string
default:
    // unknown type
}
```

Type assertions check a single type; type switches branch over several possibilities cleanly.

**26. Method receivers — value vs pointer, and method sets**
A method can be declared with a value receiver (`func (t T) M()`) or pointer receiver (`func (t *T) M()`). The method set of type `T` includes only value-receiver methods; the method set of `*T` includes both value- and pointer-receiver methods. This matters for interface satisfaction: if an interface requires a pointer-receiver method, only `*T` (not `T`) satisfies that interface.

**27. Pointer receiver method on a non-addressable value**
If a value is not addressable (e.g., a map value, or a value returned directly from a function call), you cannot call a pointer-receiver method on it directly, because Go can't automatically take its address:

```go
m := map[string]MyStruct{"a": {}}
m["a"].PointerMethod() // compile error: cannot call pointer method on m["a"]
```

Go auto-addresses local variables (`v.PointerMethod()` becomes `(&v).PointerMethod()`), but it can't do this for values that don't have a stable memory address, like map values.

**28. Variadic functions**

```go
func sum(nums ...int) int { ... }
sum(1, 2, 3)
nums := []int{1,2,3}
sum(nums...) // spread a slice into variadic params with ...
```

Variadic parameters are received internally as a slice; you can pass an existing slice using the `...` spread syntax.

**29. Function values, closures, and the classic loop-variable bug (pre-1.22)**
Functions are first-class values; closures capture variables from their enclosing scope by reference. Before Go 1.22, the loop variable in a `for` statement was a single variable reused each iteration, so:

```go
for i := 0; i < 3; i++ {
    go func() { fmt.Println(i) }() // captures the SAME i
}
// could print 3 3 3 instead of 0 1 2
```

Common fix pre-1.22: pass `i` as a parameter, `go func(i int) { fmt.Println(i) }(i)`, or redeclare `i := i` inside the loop body.

**30. Loop variable capture in goroutines, and the Go 1.22 fix**
Same issue as #29, specifically in `for range` loops over collections — the loop variable was shared across iterations pre-1.22, so goroutines launched inside the loop could all observe the final value. Go 1.22 changed loop semantics so that each iteration of a `for` (including `for range`) gets its own fresh copy of the loop variable(s), eliminating this entire bug class without code changes.

**31. `go vet`, `gofmt`, `golint`/`staticcheck`**

- `gofmt` automatically reformats code into the canonical Go style (whitespace, indentation, alignment).
- `go vet` analyzes code for likely bugs (e.g., wrong `Printf` verb, unreachable code, struct tags) that compile fine but are probably mistakes.
- `golint`/`staticcheck` enforce style and best-practice conventions (naming, comments, idiomatic patterns) beyond pure formatting.
  Go enforces one canonical format via tooling so that all Go code looks similar across the ecosystem, removing bikeshedding about style and making code review/diffs cleaner.

**32. Labeled `break` and `continue`**
Labels let you break or continue an outer loop from within a nested loop:

```go
Outer:
for i := 0; i < 3; i++ {
    for j := 0; j < 3; j++ {
        if j == 1 {
            continue Outer
        }
    }
}
```

Without a label, `break`/`continue` only affects the innermost loop or switch/select.

**33. String immutability, `[]byte`/`[]rune`, and UTF-8**
Go strings are immutable, read-only byte slices conceptually, encoded as UTF-8 by convention (not enforced). To mutate string content you convert to `[]byte` (mutable byte slice) or `[]rune` (mutable slice of Unicode code points) and convert back to `string` when done. `[]byte` gives raw byte access (useful for ASCII/binary data); `[]rune` gives one element per Unicode code point, correctly handling multi-byte UTF-8 characters.

**34. `len("héllo")` and runes vs bytes**
`len()` on a string returns the number of _bytes_, not visible characters. `"héllo"` has `é` encoded as 2 bytes in UTF-8, so `len("héllo")` is 6, not 5. To count actual characters (runes), convert: `len([]rune("héllo"))` gives 5. This distinction is critical whenever indexing/slicing strings that may contain non-ASCII characters, since byte-index slicing can cut a multi-byte rune in half.

**35. Array vs slice**
An array (`[N]T`) has a fixed size that's part of its type; arrays are value types — copying an array copies all its elements. A slice (`[]T`) is a reference-like, dynamically-sized view over an underlying array, described by a pointer, length, and capacity; copying a slice copies the header (pointer/len/cap), not the underlying data, so multiple slices can share and mutate the same backing array.

---

## 2. Slices, Arrays, Maps — Internals & Gotchas

**36. Internal structure of a slice (slice header)**
A slice is a small struct with three fields: a pointer to the first element of an underlying array, a length (`len`, number of elements currently accessible), and a capacity (`cap`, number of elements available in the underlying array from the pointer onward). Conceptually:

```go
type sliceHeader struct {
    ptr *T
    len int
    cap int
}
```

This header is what's copied when a slice is passed by value — the underlying array is shared.

**37. Append behavior within vs exceeding capacity**
If two slices share the same backing array and you `append()` to one without exceeding its capacity, the new element is written into the shared array, so the other slice can observe the change if its length/window covers that index. If the append exceeds capacity, Go allocates a brand-new, larger backing array, copies the existing elements over, and the appended slice now points to a different array — it's no longer connected to the original, so further mutations don't affect the other slice.

**38. Code trace**

```go
func main() {
    x := []int{1, 2, 3, 4}
    y := x
    x = append(x, 5) // len=4,cap=4 -> exceeds cap, reallocates; x now points to NEW array
    y = append(y, 6) // y still points to ORIGINAL array (len4,cap4) -> also exceeds cap, reallocates separately
    x[0] = 0          // only affects x's array
    fmt.Println(x)    // [0 2 3 4 5]
    fmt.Println(y)    // [1 2 3 4 6]
}
```

Both appends exceed the original capacity of 4, so each gets its own newly allocated array — `x` and `y` become fully independent after this point, and mutating `x[0]` has no effect on `y`.

**39. Slice "leaking" into the caller after function append**

```go
func modify(s []int) {
    s = append(s, 99) // if len < cap, writes into the shared backing array
}
func main() {
    s := make([]int, 3, 5)
    modify(s)
    fmt.Println(s[:4]) // can see the appended 99 even though s itself wasn't reassigned
}
```

The slice header is passed by value, so `s = append(...)` inside the function doesn't change the caller's `s` variable. But if capacity allowed the append to write in-place (no reallocation), the underlying array — which is shared — now contains that extra element at index 3. The caller's original `s` still has `len=3`, so it won't see it via normal indexing, but if the caller re-slices (`s[:4]`), it will surface the "leaked" data.

**40. Slice capacity growth**
When `append()` exceeds current capacity, Go allocates a new array, typically doubling capacity for smaller slices (under roughly 1024 elements pre Go 1.18-ish heuristics) and growing by a smaller factor (~1.25x) for larger slices, to balance memory waste against amortized append cost. The exact growth factors are implementation details that have changed across Go versions, so the precise rule (and a "memory-aware" smoother growth curve introduced more recently) shouldn't be memorized verbatim — the important concept is amortized O(1) append cost via geometric growth.

**41. Danger of slicing a large array and holding the sub-slice**

```go
data := make([]byte, 1<<20) // 1MB
small := data[1000:1001]    // tiny slice, but shares the SAME backing array
```

Even though `small` only "needs" one element, it keeps the entire 1MB backing array alive because the garbage collector can't free any part of an array while any slice still references it. This causes memory bloat/leaks when long-lived small slices are derived from large temporary buffers. Fix: copy the needed data into a freshly allocated, right-sized slice: `small := append([]byte(nil), data[1000:1001]...)`.

**42. Safely copying a slice**

- `copy(dst, src)` copies elements into a pre-allocated destination slice (`dst := make([]int, len(src)); copy(dst, src)`).
- Full slice expressions `s[low:high:max]` let you control the resulting capacity, which can prevent later appends from accidentally writing into a shared array (forcing a reallocation on the next append since cap is constrained).
  Both techniques decouple the new slice from the original's backing array so mutations don't cross-contaminate.

**43. nil slice vs empty slice**
A `nil` slice (`var s []int`) and an empty slice (`s := []int{}`) both have `len(s) == 0`, both work fine with `append` and `range`, and both print as `[]`. However, they are not `==` comparable to each other meaningfully in general code (slices can only be compared to `nil`, not to each other, except via reflect/explicit loops) — `s == nil` is `true` for the nil slice and `false` for the empty slice. This distinction matters for APIs/JSON marshaling: a nil slice marshals to JSON `null`, while an empty slice marshals to `[]`.

**44. Concurrent map access**
Maps are not safe for concurrent read/write in Go. Concurrent unsynchronized writes (or a write concurrent with a read) trigger a runtime "fatal error: concurrent map read and map write" — this is a fatal crash, not a recoverable panic. Fixes: guard the map with a `sync.Mutex`/`sync.RWMutex`, use `sync.Map` (optimized for specific access patterns like mostly-read or disjoint key sets), or shard the map across multiple locks to reduce contention.

**45. Map iteration order**
Go intentionally randomizes the iteration order of `range` over a map on every run, specifically so developers don't accidentally depend on a particular (and implementation-defined) order. This was a deliberate language design decision to prevent fragile code; if you need ordered iteration, extract and sort the keys separately.

**46. Taking the address of a map value**
You cannot do `&m[key]` — map values are not addressable. This is because the map's internal implementation can move values around in memory during growth/rehashing, so a stable pointer into the map's internals can't be guaranteed. Workaround: store pointers in the map (`map[string]*T`) if you need addressable, mutable values, or extract the value, modify a local copy, then write it back: `v := m[key]; v.Field = x; m[key] = v`.

**47. Checking if a key exists**

```go
v, ok := m[key]
if ok {
    // key exists, v is its value
} else {
    // key absent, v is the zero value of the map's value type
}
```

This "comma-ok" idiom distinguishes "key absent" from "key present with the zero value."

**48. Deleting a key while iterating**
It is safe in Go to call `delete(m, key)` during a `range m` loop — the language spec explicitly guarantees this won't cause a crash, though the deleted key simply won't be produced again if not already visited (and there's no guarantee about whether keys added during iteration appear).

**49. Array value semantics vs slices**
Arrays are value types: passing `[N]T` to a function copies the entire array, and the function operates on an independent copy — mutations inside don't affect the caller. Slices behave reference-like: the header is copied, but it points to the same underlying array, so mutations to elements (not to len/cap reassignment) are visible to the caller. This is why slices, not arrays, are the idiomatic choice for most Go code.

**50. Generic Set implementation**

```go
type Set[T comparable] struct {
    m map[T]struct{}
}

func NewSet[T comparable]() *Set[T] {
    return &Set[T]{m: make(map[T]struct{})}
}

func (s *Set[T]) Add(v T)      { s.m[v] = struct{}{} }
func (s *Set[T]) Remove(v T)   { delete(s.m, v) }
func (s *Set[T]) Contains(v T) bool { _, ok := s.m[v]; return ok }
func (s *Set[T]) Len() int     { return len(s.m) }
```

Using `struct{}` as the value type avoids wasting memory since the empty struct occupies zero bytes; the `comparable` constraint ensures `T` can be used as a map key.

**51. When to choose array over slice**
Use a fixed-size array (`[N]T`) when the size is genuinely fixed and known at compile time and you want value semantics (e.g., a 3-element coordinate type, a fixed-size hash output like `[32]byte` for SHA-256), want to avoid heap allocation/indirection for small, stack-friendly data, or want compile-time guarantees about size. In nearly all other cases — dynamic collections, function parameters, anything growable — slices are the idiomatic, more flexible choice.

---

## 3. Concurrency — Goroutines, Channels, sync

### 3.1 Goroutines fundamentals

**52. What is a goroutine?**
A goroutine is a lightweight, independently executing function managed by the Go runtime, not the OS. Goroutines start with a small stack (~2KB) that grows/shrinks dynamically, versus OS threads which typically have fixed, much larger stacks (often 1-8MB) and are scheduled by the OS kernel. The Go runtime multiplexes many goroutines onto a smaller number of OS threads, making it feasible to run hundreds of thousands of goroutines, whereas OS threads are far more expensive to create and context-switch.

**53. GMP model and GOMAXPROCS**
The GMP model describes Go's scheduler: **G**oroutines (units of work), **M**achine (an OS thread), and **P** (Processor, a scheduling context that holds a run queue of goroutines and is required for an M to execute Go code). `GOMAXPROCS` sets the number of Ps, effectively capping how many goroutines can run Go code truly in parallel at once (defaults to the number of CPU cores). An M must hold a P to run goroutines; if an M blocks on a syscall, its P can be handed off to another M so other goroutines keep running.

**54. Scheduler multiplexing and work stealing**
The scheduler maps many Gs onto few Ms via Ps, each P having a local run queue. When a P's local queue is empty, it "steals" goroutines from another P's queue (work stealing) to keep all processors busy and balance load without a single global lock being a bottleneck. There's also a global run queue checked periodically to avoid starvation.

**55. Goroutine leaks**
A goroutine leak happens when a goroutine blocks forever and is never cleaned up, consuming memory/resources indefinitely. Examples:

1. Sending on an unbuffered channel that nobody ever reads from.
2. Waiting to receive from a channel that's never closed or written to.
3. A worker goroutine listening on a `done`/`quit` channel that the caller forgets to close/signal, so the goroutine blocks on `select` forever.

**56. Why `go someFunc()` then `fmt.Println("Finished")` doesn't guarantee output**
`go someFunc()` starts `someFunc` running concurrently and returns immediately — the calling goroutine doesn't wait for it. If `main()` reaches the end and exits before the scheduler gets around to running/finishing `someFunc`, the whole program terminates and `someFunc`'s side effects (like a `Println`) may never happen, because Go does not wait for outstanding goroutines when `main` returns. You need explicit synchronization (`sync.WaitGroup`, channels) to guarantee the goroutine completes before the program exits.

**57. Limiting concurrent goroutines**
Worker pool / semaphore pattern using a buffered channel as a counting semaphore:

```go
sem := make(chan struct{}, maxConcurrency)
for _, item := range items {
    sem <- struct{}{} // acquire
    go func(item Item) {
        defer func() { <-sem }() // release
        process(item)
    }(item)
}
```

Alternatively, spin up a fixed number of long-lived worker goroutines reading from a shared jobs channel (classic worker pool, see #89/#194).

**58. Detecting goroutine leaks in production**
Use `net/http/pprof`'s goroutine profile endpoint (`/debug/pprof/goroutine`) to inspect a live stack dump of all running goroutines and spot ones stuck in the same blocking call over time. Also monitor `runtime.NumGoroutine()` as a metric over time — a steadily climbing count (that never stabilizes) is a strong signal of leaking goroutines.

**59. `runtime.Gosched()`**
`runtime.Gosched()` voluntarily yields the current goroutine's processor time, letting other goroutines run, without blocking the calling goroutine (it goes back onto the run queue rather than sleeping). It's rarely needed in practice because Go's scheduler is largely cooperative-but-preemptive now; it's occasionally used in tight CPU-bound loops with no natural blocking point, to avoid starving other goroutines on the same P.

### 3.2 Channels

**60. What is a channel?**
A channel is a typed conduit for sending and receiving values between goroutines, providing built-in synchronization. `make(chan int)` creates an unbuffered channel; `make(chan int, 5)` creates a buffered channel with capacity 5.

**61. Buffered vs unbuffered blocking behavior**
An unbuffered channel send blocks until a receiver is ready to receive (synchronous handoff — sender and receiver "rendezvous"). A buffered channel send only blocks if the buffer is full; it succeeds immediately (without a waiting receiver) as long as there's free buffer capacity. Receives block on an empty channel (buffered or not) until a value is available.

**62. Send/receive/close on a closed channel**

- Sending on a closed channel panics.
- Receiving from a closed channel never blocks — it immediately returns the channel's zero value, and the second "comma-ok" form (`v, ok := <-ch`) returns `ok == false` to signal the channel is closed and drained.
- Closing an already-closed channel panics.

**63. Code trace / deadlock**

```go
func main() {
    ch := make(chan int, 4)
    ch <- 1; ch <- 2; ch <- 3; ch <- 4
    ch <- 5 // buffer is full (cap=4) and nobody is reading -> blocks forever -> deadlock
    close(ch)
    for num := range ch {
        fmt.Println(num)
    }
}
```

The fifth send blocks because the buffered channel's capacity (4) is already full and there's no concurrent receiver draining it; since this is the only goroutine, the runtime detects "all goroutines are asleep" and panics with a deadlock error. Fix: launch the sends in a separate goroutine (a producer) so the main goroutine can simultaneously drain via `range`:

```go
go func() {
    for i := 1; i <= 5; i++ { ch <- i }
    close(ch)
}()
for num := range ch {
    fmt.Println(num)
}
```

**64. Safely closing a channel with multiple writers**
The convention is: only the sender(s) should close a channel, never the receiver, and ideally only a single, designated owner goroutine should close it — closing from multiple writers risks a double-close panic, and closing while another writer is still sending risks a send-on-closed-channel panic. Patterns to avoid this: have a single coordinator goroutine that closes the channel once all writers have signaled completion (e.g., using a `sync.WaitGroup` to know when all writers are done, then close), or avoid closing entirely and instead use a separate `done` channel/`context.Context` for cancellation signaling.

**65. Idiomatic "done" signaling**
Closing a channel is the idiomatic way to _broadcast_ a signal to any number of waiting goroutines simultaneously (a closed channel is always immediately receivable by all readers, unlike sending a single value which only one receiver would get). `context.Context` (via `WithCancel`/`WithTimeout`) builds on this same idea (it has a `Done()` channel internally) but adds richer semantics: cancellation propagation through call chains, deadlines, and carrying request-scoped values — it's the standard, idiomatic choice for cancellation in real services.

**66. `select` statement**
`select` lets a goroutine wait on multiple channel operations simultaneously, proceeding with whichever case becomes ready first. If multiple cases are ready at the same time, Go picks one uniformly at random (not the first one written) to avoid starvation bias. A `default` case, if present, makes the whole `select` non-blocking — it runs immediately if no other case is currently ready, instead of waiting.

**67. Non-blocking channel send/receive**

```go
select {
case v := <-ch:
    // received a value
default:
    // channel had nothing ready; don't block
}

select {
case ch <- val:
    // sent successfully
default:
    // channel full/no receiver; don't block
}
```

**68. Timeout on a channel receive, and the `time.After` loop leak**

```go
select {
case v := <-ch:
    // got a value
case <-time.After(2 * time.Second):
    // timed out
}
```

Gotcha: `time.After` creates a new `time.Timer` every call, and that timer isn't garbage collected until it fires — if this is inside a tight loop (e.g., a `select` repeated many times per second), each iteration leaks a live timer until its full duration elapses, building up memory/timer pressure. Fix: create a single reusable `time.NewTimer`/`time.NewTicker` outside the loop and reset it, or use `context.WithTimeout` which cleans up properly.

**69. Directional channels**
`chan<- T` is a send-only channel type; `<-chan T` is receive-only; plain `chan T` is bidirectional. Restricting direction in function signatures (e.g., a producer function takes `chan<- T`, a consumer takes `<-chan T`) is a compile-time safety mechanism — it documents intent and prevents a function from accidentally receiving on a channel it should only send to (or vice versa).

**70. "Don't communicate by sharing memory; share memory by communicating"**
This Go proverb advocates passing ownership of data between goroutines via channels rather than having multiple goroutines mutate shared state protected by locks — channels make data flow explicit and reduce the risk of races. That said, a mutex is still appropriate (and often simpler/faster) for protecting small, frequently accessed shared state like a counter or cache, where modeling the access as message-passing would add unnecessary complexity and overhead; idiomatic Go uses both tools depending on the situation.

**71. `for v := range ch` deadlock with WaitGroup**

```go
var wg sync.WaitGroup
ch := make(chan int)
for i := 0; i < 3; i++ {
    wg.Add(1)
    go func() { defer wg.Done(); ch <- i }()
}
wg.Wait()       // BUG: blocks because nothing is draining ch concurrently
close(ch)
for v := range ch { fmt.Println(v) }
```

Here `wg.Wait()` blocks the main goroutine until all producer goroutines finish, but those producers are themselves blocked trying to send on the unbuffered channel `ch` because nothing is receiving yet (the `range` loop that would drain it comes _after_ `Wait()`). This is a classic deadlock: the consumer is waiting for producers to finish, but producers are waiting for a consumer. Fix: start draining the channel in a separate goroutine before/concurrently with the `Wait()`, then close the channel only after `Wait()` returns:

```go
go func() { wg.Wait(); close(ch) }()
for v := range ch { fmt.Println(v) }
```

### 3.3 sync package & memory model

**72. `sync.WaitGroup`**
`WaitGroup` lets one goroutine wait for a collection of others to finish. `Add(n)` increments an internal counter, `Done()` decrements it (typically `defer wg.Done()`), and `Wait()` blocks until the counter hits zero. Common mistake:

```go
for i := 0; i < 3; i++ {
    go func() {
        wg.Add(1) // BUG: race -- Wait() might run before Add() executes
        defer wg.Done()
        work()
    }()
}
wg.Wait()
```

`Add` must be called _before_ launching the goroutine (in the parent goroutine), not inside it, otherwise `Wait()` can return prematurely if it runs before some goroutines have even called `Add`.

**73. `sync.Mutex` vs `sync.RWMutex`**
`Mutex` allows only one goroutine (reader or writer) to hold the lock at a time. `RWMutex` distinguishes read locks (`RLock`/`RUnlock`, multiple readers can hold simultaneously) from write locks (`Lock`/`Unlock`, exclusive). Choose `RWMutex` when reads vastly outnumber writes and you want to allow concurrent readers for better throughput; for write-heavy or roughly balanced workloads, a plain `Mutex` is usually simpler and just as fast (RWMutex has more overhead per operation).

**74. Recursive locking and reentrancy**
Go's `sync.Mutex` is not reentrant — if a goroutine that already holds the lock calls `Lock()` again (e.g., via a recursive function or calling another method that also locks), it deadlocks waiting for itself to release the lock. Avoid this by not calling locking methods from within other locking methods on the same mutex; instead, factor out an internal, unexported "already locked" version of the logic that the public locking method calls.

**75. `sync.Once`**
`sync.Once` ensures a function runs exactly once, no matter how many goroutines call `Do()` concurrently — useful for thread-safe lazy singleton initialization or one-time config loading:

```go
var once sync.Once
var config *Config
func GetConfig() *Config {
    once.Do(func() { config = loadConfig() })
    return config
}
```

**76. `sync.Pool`**
`sync.Pool` is a pool of reusable, temporary objects to reduce garbage collector pressure for frequently allocated/discarded objects (e.g., byte buffers in a hot request path). Caveat: objects in the pool can be garbage collected at any time (even between `Put` and the next `Get`), especially during GC cycles, so `sync.Pool` is for _optional_ reuse/optimization, never for objects you rely on persisting; it's also not appropriate for managing connections or anything with explicit lifecycle requirements.

**77. `sync.Map`**
`sync.Map` is a built-in concurrent-safe map optimized for two specific access patterns: keys written once and read many times (stable key sets), or many goroutines accessing disjoint sets of keys. It's preferable to `map + Mutex` in those specific high-read-contention scenarios. Tradeoffs: it has a less convenient API (no native `len()`, generic type safety lost pre-1.18 since it stores `any`), and for general-purpose or write-heavy workloads, a regular map with a `Mutex`/`RWMutex` is usually simpler and can be faster.

**78. `sync/atomic`**
`sync/atomic` provides low-level atomic operations (`Add`, `Load`, `Store`, `CompareAndSwap`) on integers and pointers, implemented via CPU-level atomic instructions rather than OS-level locking. Use atomics instead of a mutex for very simple operations like incrementing a counter or toggling a flag, where the overhead of lock acquisition/release would dominate — atomics are faster for these narrow cases, but unlike a mutex they can't protect a multi-field critical section atomically.

**79. Race conditions**
A race condition occurs when two or more goroutines access shared memory concurrently, at least one of them writing, without synchronization, leading to nondeterministic, often incorrect results.

```go
var counter int
var wg sync.WaitGroup
for i := 0; i < 1000; i++ {
    wg.Add(1)
    go func() {
        defer wg.Done()
        counter++ // NOT atomic: read-modify-write race
    }()
}
wg.Wait()
fmt.Println(counter) // often less than 1000
```

`go run -race` (or `go test -race`) instruments the binary with Google's ThreadSanitizer-based race detector, which monitors memory accesses at runtime and reports exactly which goroutines/lines raced on the same memory location — invaluable for catching races that don't reliably reproduce a wrong answer every run.

**80. Go's memory model and "happens-before"**
Go's memory model defines exactly when a write by one goroutine is guaranteed to be visible to a read in another goroutine — this is the "happens-before" relationship. Without a happens-before guarantee, the compiler/CPU may reorder or cache operations, so reads aren't guaranteed to see writes from other goroutines even if they appear "later" in wall-clock time. Channel operations and mutex lock/unlock are the primary synchronization primitives that establish happens-before edges: a send on a channel happens-before the corresponding receive completes, and a goroutine's actions before unlocking a mutex happen-before another goroutine's actions after it acquires that same lock. Code relying on shared variables without going through these primitives (or atomics) has undefined behavior even if it "usually works" in testing.

### 3.4 context package

**81. `context.Context`**
`context.Context` carries deadlines, cancellation signals, and request-scoped values across API boundaries and between goroutines in a call chain. Four ways to derive a context from a parent:

- `context.WithCancel(parent)` — returns a context plus a `cancel()` function to manually cancel it.
- `context.WithTimeout(parent, duration)` — auto-cancels after a relative duration.
- `context.WithDeadline(parent, time)` — auto-cancels at an absolute time.
- `context.WithValue(parent, key, value)` — attaches a request-scoped key/value pair.

**82. Why `WithValue` is discouraged for optional parameters**
`context.WithValue` loses type safety (values are stored as `any` and require type assertions to retrieve) and makes a function's true dependencies invisible from its signature, hurting readability and making it easy to silently break callers when keys change. It's discouraged for passing things a function actually needs to do its job (those should be explicit parameters); it's considered appropriate only for cross-cutting, request-scoped metadata that truly spans an entire call chain regardless of which functions are involved, like a request ID, trace ID, or auth token used for logging/tracing.

**83. Context parameter convention**
The idiomatic convention is that `ctx context.Context` is always the first parameter of a function, named `ctx`. Contexts shouldn't be stored in struct fields because a context represents the scope/lifetime of one specific call (with its own deadline/cancellation), and storing it would let a stale, possibly-already-cancelled context leak into unrelated calls later, decoupling it from the actual request it should be scoped to.

**84. Cancellation propagation**
When a parent context is canceled (manually, via timeout, or deadline), every context derived from it (children created via `WithCancel`/`WithTimeout`/etc.) is also canceled, and their `Done()` channels close. Functions and downstream HTTP calls that respect `ctx.Done()` (e.g., checking it in a `select`, or libraries like `net/http`'s `Request.WithContext` and `database/sql` that natively honor context) abort their work as soon as that signal fires, propagating the cancellation through however many layers of goroutines or network calls are involved.

**85. Forgetting to call `cancel()`**
`context.WithCancel`/`WithTimeout`/`WithDeadline` return a `cancel` function that must be called (typically via `defer cancel()`) once the context is no longer needed, even if it already expired naturally. Forgetting to call it leaks resources: the context (and anything it's holding, like timers for `WithTimeout`) stays alive in memory until the parent context itself is canceled, which in long-lived parent contexts can accumulate indefinitely — a "context leak."

### 3.5 Concurrency patterns (the "design a thing" questions)

**86. Print odd and even numbers alternately using two goroutines and channels**

```go
func main() {
    oddCh := make(chan struct{})
    evenCh := make(chan struct{})
    done := make(chan struct{})
    const max = 10

    go func() { // odd numbers
        for i := 1; i <= max; i += 2 {
            <-oddCh
            fmt.Println("odd:", i)
            evenCh <- struct{}{}
        }
    }()

    go func() { // even numbers
        for i := 2; i <= max; i += 2 {
            <-evenCh
            fmt.Println("even:", i)
            if i+1 > max {
                close(done)
                return
            }
            oddCh <- struct{}{}
        }
    }()

    oddCh <- struct{}{} // kick off
    <-done
}
```

Two unbuffered "turn" channels ping-pong control between the goroutines so only one prints at a time, alternating odd/even.

**87. Fan-in: merge variadic `<-chan T` into one output channel**

```go
func FanIn[T any](channels ...<-chan T) <-chan T {
    out := make(chan T)
    var wg sync.WaitGroup
    wg.Add(len(channels))

    for _, c := range channels {
        go func(c <-chan T) {
            defer wg.Done()
            for v := range c {
                out <- v
            }
        }(c)
    }

    go func() {
        wg.Wait()
        close(out)
    }()

    return out
}
```

Each input channel is drained by its own goroutine forwarding values into `out`; a coordinator goroutine waits for all forwarders to finish (meaning all inputs closed and drained) before closing `out`, so the merged channel correctly signals completion only once.

**88. Fan-out: distribute work across N worker goroutines**

```go
func FanOut(jobs <-chan int, n int, process func(int)) {
    var wg sync.WaitGroup
    wg.Add(n)
    for i := 0; i < n; i++ {
        go func() {
            defer wg.Done()
            for job := range jobs {
                process(job)
            }
        }(  )
    }
    wg.Wait()
}
```

N worker goroutines all read from the same `jobs` channel; Go's channel semantics ensure each value is delivered to exactly one worker, naturally load-balancing work.

**89. Worker pool with fixed workers, results, and clean shutdown**

```go
func WorkerPool(ctx context.Context, jobs <-chan int, numWorkers int) <-chan int {
    results := make(chan int)
    var wg sync.WaitGroup
    wg.Add(numWorkers)

    for i := 0; i < numWorkers; i++ {
        go func() {
            defer wg.Done()
            for {
                select {
                case job, ok := <-jobs:
                    if !ok {
                        return // jobs channel closed: no more work
                    }
                    select {
                    case results <- job * job:
                    case <-ctx.Done():
                        return
                    }
                case <-ctx.Done():
                    return // cancellation requested
                }
            }
        }()
    }

    go func() {
        wg.Wait()
        close(results)
    }()

    return results
}
```

Workers exit either when the `jobs` channel is closed and drained, or when `ctx` is canceled; a coordinator closes `results` once all workers have returned, so a downstream `range results` terminates cleanly either way.

**90. Pipeline: generate → square → filter evens**

```go
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

func main() {
    for v := range filterEven(square(generate(1, 2, 3, 4, 5))) {
        fmt.Println(v)
    }
}
```

Each stage is its own goroutine connected by a channel; each stage closes its output channel once its input is exhausted, so the chain naturally drains and terminates.

**91. Rate limiter using `time.Ticker`**

```go
func RateLimiter(requests <-chan func(), ratePerSecond int) {
    ticker := time.NewTicker(time.Second / time.Duration(ratePerSecond))
    defer ticker.Stop()
    for req := range requests {
        <-ticker.C // wait for the next tick before allowing this request through
        req()
    }
}
```

The ticker fires at a fixed rate; each incoming request must wait for a tick before executing, throttling throughput to `ratePerSecond` calls/second. (For bursty traffic, a token-bucket approach via `golang.org/x/time/rate` is preferred — see #209.)

**92. Producer-consumer, multiple producers/consumers, graceful shutdown**

```go
func ProducerConsumer(ctx context.Context, numProducers, numConsumers int) {
    buf := make(chan int, 100)
    var producersWG, consumersWG sync.WaitGroup

    producersWG.Add(numProducers)
    for p := 0; p < numProducers; p++ {
        go func(id int) {
            defer producersWG.Done()
            for i := 0; ; i++ {
                select {
                case buf <- id*1000 + i:
                case <-ctx.Done():
                    return
                }
            }
        }(p)
    }

    consumersWG.Add(numConsumers)
    for c := 0; c < numConsumers; c++ {
        go func() {
            defer consumersWG.Done()
            for {
                select {
                case v, ok := <-buf:
                    if !ok {
                        return
                    }
                    process(v)
                case <-ctx.Done():
                    return
                }
            }
        }()
    }

    go func() {
        producersWG.Wait()
        close(buf) // close once all producers are done, so consumers drain remaining items then exit
    }()

    consumersWG.Wait()
}
```

Producers stop on cancellation or naturally; once all producers finish, the shared buffer is closed so consumers can drain whatever remains and exit cleanly rather than blocking forever.

**93. `sync.WaitGroup` to process a slice concurrently and aggregate results safely**

```go
func ProcessAll(items []int) []int {
    results := make([]int, len(items))
    var wg sync.WaitGroup
    wg.Add(len(items))
    for i, item := range items {
        go func(i, item int) {
            defer wg.Done()
            results[i] = item * item // each goroutine writes a distinct index: no race
        }(i, item)
    }
    wg.Wait()
    return results
}
```

Pre-allocating the results slice and having each goroutine write to its own unique index avoids any need for a mutex — there's no shared mutable state being contended.

**94. Debouncing/throttling with goroutines and timers**

```go
type Debouncer struct {
    mu    sync.Mutex
    timer *time.Timer
    delay time.Duration
}

func NewDebouncer(delay time.Duration) *Debouncer {
    return &Debouncer{delay: delay}
}

func (d *Debouncer) Call(f func()) {
    d.mu.Lock()
    defer d.mu.Unlock()
    if d.timer != nil {
        d.timer.Stop()
    }
    d.timer = time.AfterFunc(d.delay, f)
}
```

Each `Call` resets the pending timer, so `f` only fires once the calls stop coming in for `delay` — the classic debounce behavior (good for batching rapid-fire events like keystroke-triggered searches).

**95. Concurrent-safe LRU cache**

```go
type entry struct {
    key, value int
}

type LRUCache struct {
    mu       sync.Mutex
    capacity int
    items    map[int]*list.Element
    order    *list.List // front = most recently used
}

func NewLRUCache(capacity int) *LRUCache {
    return &LRUCache{
        capacity: capacity,
        items:    make(map[int]*list.Element),
        order:    list.New(),
    }
}

func (c *LRUCache) Get(key int) (int, bool) {
    c.mu.Lock()
    defer c.mu.Unlock()
    el, ok := c.items[key]
    if !ok {
        return 0, false
    }
    c.order.MoveToFront(el)
    return el.Value.(*entry).value, true
}

func (c *LRUCache) Put(key, value int) {
    c.mu.Lock()
    defer c.mu.Unlock()
    if el, ok := c.items[key]; ok {
        el.Value.(*entry).value = value
        c.order.MoveToFront(el)
        return
    }
    if c.order.Len() >= c.capacity {
        oldest := c.order.Back()
        if oldest != nil {
            c.order.Remove(oldest)
            delete(c.items, oldest.Value.(*entry).key)
        }
    }
    el := c.order.PushFront(&entry{key, value})
    c.items[key] = el
}
```

A `map` gives O(1) key lookup; a doubly linked list (`container/list`) tracks recency order so the least-recently-used item (the list's back) can be evicted in O(1); a single mutex guards both structures together since they must stay consistent.

**96. "First response wins" across N replicas**

```go
func FirstResponse(ctx context.Context, replicas []func(context.Context) (string, error)) (string, error) {
    ctx, cancel := context.WithCancel(ctx)
    defer cancel() // ensure all other goroutines are told to stop once we return

    type result struct {
        val string
        err error
    }
    resCh := make(chan result, len(replicas))

    for _, call := range replicas {
        go func(call func(context.Context) (string, error)) {
            val, err := call(ctx)
            select {
            case resCh <- result{val, err}:
            case <-ctx.Done():
            }
        }(call)
    }

    for i := 0; i < len(replicas); i++ {
        r := <-resCh
        if r.err == nil {
            return r.val, nil // got a success: cancel() (deferred) tells the rest to stop
        }
    }
    return "", errors.New("all replicas failed")
}
```

All replica calls are fired concurrently with a shared cancellable context; as soon as one succeeds, the function returns and the deferred `cancel()` signals every other in-flight call (that respects `ctx`) to abandon its work, avoiding wasted resources.

**97. Semaphore via buffered channel**

```go
func WithSemaphore(n int, tasks []func()) {
    sem := make(chan struct{}, n)
    var wg sync.WaitGroup
    for _, task := range tasks {
        wg.Add(1)
        sem <- struct{}{} // acquire a slot (blocks if n are already in use)
        go func(task func()) {
            defer wg.Done()
            defer func() { <-sem }() // release the slot
            task()
        }(task)
    }
    wg.Wait()
}
```

A buffered channel of capacity `n` acts as a counting semaphore: sending fills a slot (blocking once full), receiving frees one — capping the number of goroutines actually running concurrently to `n`.

**98. Fetch URLs concurrently with max concurrency, collect results/errors without one failure blocking others**

```go
type fetchResult struct {
    url   string
    body  string
    err   error
}

func FetchAll(urls []string, maxConcurrency int) []fetchResult {
    sem := make(chan struct{}, maxConcurrency)
    resultsCh := make(chan fetchResult, len(urls))
    var wg sync.WaitGroup

    for _, u := range urls {
        wg.Add(1)
        sem <- struct{}{}
        go func(u string) {
            defer wg.Done()
            defer func() { <-sem }()
            body, err := fetchURL(u) // hypothetical HTTP fetch
            resultsCh <- fetchResult{url: u, body: body, err: err}
        }(u)
    }

    go func() {
        wg.Wait()
        close(resultsCh)
    }()

    var results []fetchResult
    for r := range resultsCh {
        results = append(results, r) // errors are captured per-URL, not propagated/stopped early
    }
    return results
}
```

Each fetch's error is captured in its own `fetchResult` rather than aborting the whole batch, so one failing URL doesn't block or cancel the others; `errgroup.Group` (with `SetLimit` for concurrency capping) is a common real-world alternative that handles this pattern more concisely.

**99. Simplified `sync.Once` using a mutex and boolean**

```go
type MyOnce struct {
    mu   sync.Mutex
    done bool
}

func (o *MyOnce) Do(f func()) {
    o.mu.Lock()
    defer o.mu.Unlock()
    if !o.done {
        f()
        o.done = true
    }
}
```

Note: the real `sync.Once` uses an atomic fast-path check before acquiring the lock (to avoid lock contention on the common case where `Do` has already run), but this mutex-only version is logically correct and demonstrates the core idea: a lock ensures only one caller executes `f`, and the `done` flag, checked under the same lock, prevents subsequent calls from re-running it.

**100. Print 1 to N using exactly 3 goroutines in round-robin order**

```go
func RoundRobinPrint(n int) {
    chs := make([]chan struct{}, 3)
    for i := range chs {
        chs[i] = make(chan struct{})
    }
    done := make(chan struct{})
    var wg sync.WaitGroup
    wg.Add(3)

    for g := 0; g < 3; g++ {
        go func(id int) {
            defer wg.Done()
            for i := id + 1; i <= n; i += 3 {
                <-chs[id]
                fmt.Println(i)
                next := (id + 1) % 3
                if i+1 <= n {
                    chs[next] <- struct{}{}
                } else {
                    close(done)
                }
            }
        }(g)
    }

    chs[0] <- struct{}{} // kick off goroutine 0
    <-done
    wg.Wait()
}
```

Three "turn" channels are passed around in a ring: each goroutine waits on its own turn channel, prints its number, then signals the next goroutine's turn channel — generalizing the two-goroutine ping-pong pattern from #86 to three participants in round-robin order.
