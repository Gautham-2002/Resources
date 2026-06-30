# Go (Golang) Interview Question Bank

### Compiled for Mid-Level Engineers (2–4 yrs experience) — FAANG / Indian Unicorn Bar

### Sources synthesized: InterviewBit, MentorCruise, CodeForGeek, Hirist, Turing, Second Talent, Gank Interview, Medium/DEV.to "Tricky Go Interview" series, Reddit r/golang, Quora, LinkedIn discussion threads, and real onsite/phone-screen reports from Uber, Flipkart, Razorpay, Swiggy, Zepto, PhonePe style interviews.

---

## How to use this document

Each question is tagged:

- **[F]** Frequently asked — shows up across almost every site/company surveyed
- **[T]** Tricky / gotcha — the kind that trips up experienced devs, often live-coded
- **[C]** Coding exercise — write actual code
- **Difficulty:** Easy / Medium / Hard relative to a 2–4 yr bar

Sections are ordered roughly the way a real interview loop progresses: language fundamentals → data structures → concurrency (the heart of Go interviews) → error handling & idioms → standard library/tooling → coding exercises → system-design-adjacent Go questions.

---

## 1. Language Fundamentals & Syntax

1. **[F]** Easy — What is Go, and what design goals motivated Robert Griesemer, Rob Pike, and Ken Thompson to create it at Google?
2. **[F]** Easy — What are the main advantages of Go over languages like Java, Python, or C++?
3. Easy — Is Go an object-oriented language? How does it support OOP-like patterns without classes or inheritance?
4. **[F]** Easy — Explain Go's type system. Is Go statically or dynamically typed, and why does that matter?
5. Easy — What is the zero value in Go? Give the zero value for int, string, bool, pointer, slice, map, and struct.
6. **[F]** Easy/Medium — What is the difference between `var`, `:=`, and `const` for declaring variables?
7. Medium — What is variable shadowing in Go? Give an example where it causes a subtle bug.
8. **[F]** Medium — Explain Go's `init()` function — when does it run, can a package have multiple, and what's the execution order?
9. Easy — What are Go's looping constructs? Why is there only one (`for`) and how does it replace `while` and `do-while`?
10. Medium — What's the difference between `new()` and `make()`? When would you use one over the other?
11. **[F]** Medium — What are pointers in Go, and why are they important for performance and mutation semantics?
12. Easy — Does Go support pointer arithmetic like C? Why or why not?
13. Medium — Explain Go's package system. What does an unexported (lowercase) identifier mean for visibility?
14. **[T]** Medium — What is the difference between passing a struct by value vs. by pointer to a function? When does each make sense?
15. Easy — What are named return values in Go, and what's a pitfall of using them with `defer`?
16. **[T]** Medium — Explain how `defer` works, including evaluation of arguments at defer-time vs. execution-time.
17. **[F][T]** Medium — What's the classic "defer in a loop" gotcha (e.g., deferring `file.Close()` inside a loop)? How do you fix it?
18. Medium — What is the blank identifier `_` used for? Give 3 distinct use cases.
19. Easy — What are Go build tags / build constraints, and when would you use them?
20. Medium — Explain iota and how it's used to create enums in Go.
21. Medium — What is type embedding (struct embedding)? How does it differ from inheritance?
22. **[F]** Medium — How does Go implement interfaces? Why are they implicit (structural typing) rather than explicit like Java's `implements`?
23. **[T]** Hard — What is the "nil interface vs nil pointer" gotcha? Why can `err != nil` be true even when the underlying pointer is nil?
24. Medium — What is the empty interface `interface{}` (or `any` in modern Go)? What are its tradeoffs?
25. **[F]** Medium — What are type assertions and type switches? How do they differ?
26. Medium — What is method receiver — value receiver vs pointer receiver — and how does Go decide which method set a type satisfies?
27. **[T]** Medium — If a type has a pointer receiver method, can you call it on a value that's not addressable? Why does this sometimes fail to compile?
28. Easy — What are variadic functions? How do you pass a slice into a variadic parameter?
29. Medium — How does Go handle function values and closures? What's a classic closure-over-loop-variable bug (pre Go 1.22)?
30. **[F][T]** Medium — Explain the "loop variable capture" bug in goroutines launched inside a `for range` loop, and how Go 1.22 changed this.
31. Easy — What is `go vet`, `gofmt`, and `golint`/`staticcheck`, and why does the Go tooling enforce a single formatting style?
32. Medium — What are labeled `break` and `continue` used for in Go?
33. Easy — Explain string immutability in Go and how `[]byte` and `[]rune` conversions relate to UTF-8 handling.
34. **[T]** Medium — Why does `len("héllo")` not equal the number of visible characters? Explain runes vs bytes.
35. Medium — What is the difference between an array and a slice in Go?

---

## 2. Slices, Arrays, Maps — Internals & Gotchas (heavily tested)

36. **[F]** Medium — Explain the internal structure of a slice (pointer, length, capacity). Draw or describe the "slice header."
37. **[F][T]** Hard — Given two slices sharing the same underlying array, explain what happens when you `append()` to one and it doesn't exceed capacity vs. when it does. Walk through len/cap changes.
38. **[T][C]** Hard — Code trace: predict the output.

```go
func main() {
    x := []int{1, 2, 3, 4}
    y := x
    x = append(x, 5)
    y = append(y, 6)
    x[0] = 0
    fmt.Println(x)
    fmt.Println(y)
}
```

(Tests understanding of capacity reallocation and shared backing arrays.) 39. **[T][C]** Hard — Code trace: a slice is passed to a function, appended to inside the function, and the caller checks `s[:1]` afterward — explain why data "leaks" into the caller's view even though the slice "header" was passed by value. 40. **[F]** Medium — How does Go grow slice capacity when it exceeds the current capacity? (2x growth below 1024 elements, ~1.25x growth above — know the general rule, exact constants change across Go versions.) 41. **[T]** Medium — What's the danger of slicing a large slice/array (e.g., `data[1000:1001]`) and holding onto it long-term? (Memory retention / leak via shared backing array.) 42. **[F]** Easy/Medium — How do you safely copy a slice so mutations don't affect the original? (`copy()`, full slice expressions `s[:len:cap]`.) 43. Medium — What's the difference between `nil` slice and an empty (`[]int{}`) slice? Are they `==` comparable? Do they behave the same with `append`, `len`, `range`? 44. **[F]** Medium — Are maps in Go safe for concurrent read/write? What error do you get if you violate this, and how do you fix it (`sync.Mutex`, `sync.Map`, sharding)? 45. Medium — How does Go's map implementation guarantee/not guarantee iteration order? Why is range over a map randomized? 46. **[T]** Medium — Can you take the address of a map value (`&m[key]`)? Why or why not? 47. Easy — How do you check if a key exists in a map vs. just getting its zero value? (`v, ok := m[key]`) 48. Medium — How do you delete a key from a map while iterating over it — is it safe in Go? 49. **[F]** Medium — What are arrays' value semantics vs. slices' reference-like semantics? What happens when you pass an array (not a slice) to a function? 50. Hard — How would you implement a generic "Set" type using Go 1.18+ generics and a map? 51. Medium — When would you choose `[N]T` (array) over `[]T` (slice) in real code?

---

## 3. Concurrency — Goroutines, Channels, sync (THE core of Go interviews)

### 3.1 Goroutines fundamentals

52. **[F]** Easy — What is a goroutine? How is it different from an OS thread?
53. **[F]** Medium — Explain the GMP model (Goroutine, Machine/OS thread, Processor). What role does `GOMAXPROCS` play?
54. **[F]** Medium — How does the Go scheduler multiplex goroutines onto OS threads? What is "work stealing"?
55. Medium — What is a goroutine leak? Give 2–3 real scenarios that cause one (e.g., sending to an unbuffered channel nobody reads, blocking on a channel that's never closed).
56. **[F][T]** Medium — Why does `fmt.Println("Started")` followed by `go someFunc()` followed immediately by `fmt.Println("Finished")` not guarantee `someFunc`'s output appears? What's the role of `main()` exiting early?
57. Medium — How do you limit the number of concurrently running goroutines (worker pool pattern, semaphore via buffered channel)?
58. Hard — How would you detect a goroutine leak in production? (pprof goroutine profile, runtime.NumGoroutine() monitoring.)
59. Medium — What is `runtime.Gosched()` and when (rarely) would you use it?

### 3.2 Channels

60. **[F]** Easy — What is a channel? How do you create buffered vs. unbuffered channels?
61. **[F]** Medium — What's the difference in blocking behavior between buffered and unbuffered channels?
62. **[F][T]** Medium — What happens when you send on a closed channel? What happens when you receive from a closed channel? What happens if you close an already-closed channel?
63. **[F][T]** Hard — Code trace / deadlock spotting:

```go
func main() {
    ch := make(chan int, 4)
    ch <- 1
    ch <- 2
    ch <- 3
    ch <- 4
    ch <- 5 // what happens here?
    close(ch)
    for num := range ch {
        fmt.Println(num)
    }
}
```

Explain why this deadlocks, and how adding a producer goroutine fixes it. 64. **[F]** Medium — How do you safely close a channel when multiple goroutines might be writing to it? ("Don't close a channel from the receiver side, and don't close a channel with multiple writers" — discuss patterns to avoid panics.) 65. **[F]** Medium — What's the idiomatic way to signal "done" to one or more goroutines? (close a channel as a broadcast signal vs. `context.Context`.) 66. **[F]** Medium — Explain the `select` statement. What happens if multiple cases are ready simultaneously? What does a `default` case do? 67. **[T]** Medium — How do you implement a non-blocking channel send/receive using `select` + `default`? 68. **[T]** Hard — How do you implement a timeout on a channel receive using `select` and `time.After`? What's a memory-leak gotcha with `time.After` inside a loop? 69. Medium — What is the difference between directional channels (`chan<- T`, `<-chan T`) and bidirectional channels? Why restrict direction in function signatures? 70. **[F]** Hard — "Don't communicate by sharing memory; share memory by communicating" — explain this Go proverb and when you'd still reach for a mutex instead of a channel. 71. **[T]** Medium — Code trace: explain why iterating with `for v := range ch` deadlocks if the channel is never closed but a `sync.WaitGroup.Wait()` is also involved.

### 3.3 sync package & memory model

72. **[F]** Easy/Medium — What is `sync.WaitGroup` used for? Walk through `Add`, `Done`, `Wait` semantics and the common mistake of calling `Add` inside the goroutine instead of before launching it.
73. **[F]** Medium — What is `sync.Mutex` vs `sync.RWMutex`? When would you choose RWMutex?
74. **[T]** Medium — What's the difference between `Lock()`/`Unlock()` deadlocking due to recursive locking, and how do you avoid it (Go mutexes are not reentrant)?
75. **[F]** Medium — What is `sync.Once` used for? Give a real use case (singleton init, lazy config loading).
76. Medium — What is `sync.Pool`? When would you use it for performance, and what are its caveats (objects can be GC'd at any time)?
77. **[F]** Medium — What is `sync.Map`, and when is it preferable to a regular map + mutex? What are its tradeoffs?
78. **[F]** Medium — What does the `sync/atomic` package provide, and when would you use atomic operations instead of a mutex?
79. **[T]** Hard — What is a race condition? Demonstrate with code where two goroutines increment a shared counter without synchronization. How does `go run -race` help?
80. Hard — Explain Go's memory model guarantees — specifically what "happens-before" means for channel operations and mutexes.

### 3.4 context package

81. **[F]** Medium — What is `context.Context` used for? What are the four ways to derive a context (`WithCancel`, `WithTimeout`, `WithDeadline`, `WithValue`)?
82. **[F]** Medium — Why is `context.WithValue` discouraged for passing optional parameters, and when is it actually appropriate?
83. **[T]** Medium — What's the convention for context as a function parameter (always first, named `ctx`)? Why shouldn't you store a context in a struct field?
84. **[F]** Medium — How does context cancellation propagate through a call chain involving multiple goroutines / downstream HTTP calls?
85. Medium — What happens if you forget to call the `cancel()` function returned by `context.WithCancel`? (Context leak.)

### 3.5 Concurrency patterns (the "design a thing" questions)

86. **[F][C]** Medium — **Print odd and even numbers alternately using two goroutines and channels** (classic ping-pong synchronization problem).
87. **[F][C]** Hard — **Write a fan-in function: given a variadic number of `<-chan T`, merge them into a single output channel.** Handle proper closing using `sync.WaitGroup`.
88. **[C]** Medium — Implement a fan-out pattern: distribute work items from one channel across N worker goroutines.
89. **[C]** Hard — Implement a worker pool with a fixed number of workers processing jobs from a queue, collecting results, and shutting down cleanly on completion or cancellation.
90. **[C]** Medium — Implement a pipeline: stage 1 generates numbers, stage 2 squares them, stage 3 filters evens — each stage as a goroutine connected by channels.
91. **[C]** Hard — Implement a rate limiter using channels or `time.Ticker`.
92. **[C]** Hard — Implement the producer-consumer pattern with multiple producers and multiple consumers sharing a buffered channel, with graceful shutdown.
93. **[C]** Medium — Use `sync.WaitGroup` to wait for N goroutines to finish processing a slice of items concurrently, then aggregate results safely.
94. **[C]** Hard — Implement debouncing or throttling of function calls using goroutines and timers.
95. **[C]** Hard — Implement a concurrent-safe LRU cache (combine map + doubly linked list + mutex).
96. **[C]** Medium — Implement "first response wins": fire the same request to N replicas/goroutines concurrently and return whichever responds first, cancelling the rest via context.
97. **[C]** Hard — Implement a semaphore using a buffered channel to cap concurrent goroutines to a max of N.
98. **[C]** Medium — Given a list of URLs, fetch them all concurrently with a max concurrency limit and collect results/errors without one failure blocking others.
99. **[C]** Hard — Implement your own simplified `sync.Once` using a mutex and a boolean flag (to test true understanding rather than rote API knowledge).
100.  **[C]** Medium — Print numbers 1 to N using exactly 3 goroutines, each printing in round-robin order (tests channel-based coordination beyond simple 2-goroutine ping-pong).

---

## 4. Error Handling & Idiomatic Go

101. **[F]** Easy — How does Go handle errors? Why did the language designers choose explicit `error` returns over exceptions?
102. **[F]** Medium — What's the difference between `errors.New()` and `fmt.Errorf()`?
103. **[F]** Medium — Explain error wrapping with `%w`, and how `errors.Is()` and `errors.As()` work with wrapped error chains.
104. Medium — What are sentinel errors (e.g., `io.EOF`, `sql.ErrNoRows`)? What's the downside of relying heavily on them vs. custom error types?
105. Medium — How do you define a custom error type that implements the `error` interface? When would you add extra fields to it (e.g., error codes)?
106. **[T]** Medium — What's the danger of comparing errors with `==` instead of `errors.Is()` once wrapping is involved?
107. **[F]** Medium — `panic` vs `error` — when is it idiomatic to panic in Go, and when should you always return an error instead?
108. **[F]** Medium — What is `recover()`? How does it interact with `defer` and `panic`? Write a function that recovers from a panic and converts it to an error.
109. **[T]** Hard — Can `recover()` work if called directly (not inside a deferred function)? Explain why or why not.
110. Medium — Should you use panic/recover for normal control flow in Go? Why is that considered an anti-pattern?
111. Medium — How do you handle errors from multiple goroutines running concurrently and aggregate them (e.g., using `errgroup.Group` from `golang.org/x/sync/errgroup`)?

---

## 5. Structs, Interfaces & Generics

112. **[F]** Medium — How do you implement polymorphism in Go without classes, using interfaces?
113. **[F]** Medium — What is the difference between composition (embedding) and inheritance? Why does Go favor composition?
114. **[T]** Medium — If struct `B` embeds struct `A`, and both define a method `Foo()`, which one wins when called on a `B` instance? What about ambiguity with multiple embedded types?
115. Medium — What are struct tags (e.g., `json:"name"`) and how does reflection use them (e.g., in `encoding/json`)?
116. **[F]** Medium — Explain the "accept interfaces, return structs" Go idiom and why it improves API design and testability.
117. Medium — How do you design small, focused interfaces in Go (the `io.Reader`/`io.Writer` philosophy) instead of large interfaces?
118. **[F]** Medium/Hard — Explain Go generics (introduced in 1.18). Write a generic function `Map[T, U any](s []T, f func(T) U) []U`.
119. Medium — What are type constraints in generics, and what's the difference between `any` and a custom constraint interface (e.g., `constraints.Ordered`)?
120. **[T]** Medium — Why can't you use `==` to compare two values of an interface type if the underlying types aren't comparable? What runtime panic can this cause?
121. Hard — How would you implement the Strategy or Decorator design pattern idiomatically in Go using interfaces and function types?

---

## 6. Memory Management, Performance & Internals

122. **[F]** Medium — How does Go's garbage collector work at a high level (concurrent, tri-color mark-and-sweep)?
123. **[F]** Medium — What is escape analysis? How does Go decide whether a variable is allocated on the stack vs. the heap?
124. Medium — How can you check what's escaping to the heap in your code? (`go build -gcflags="-m"`)
125. Medium — What is `GOGC` and how does tuning it affect GC frequency and memory usage tradeoffs?
126. **[F]** Medium — How do you profile a Go application for CPU and memory usage? (`pprof`, `go tool pprof`, `runtime/pprof`, `net/http/pprof`)
127. Medium — What are some common causes of memory leaks in a long-running Go service (goroutine leaks, unbounded caches, slice-retains-backing-array, timer/ticker not stopped)?
128. **[F]** Medium — How would you reduce GC pressure in a hot path (object reuse via `sync.Pool`, preallocating slices with known capacity, avoiding unnecessary allocations)?
129. Medium — What's the cost difference between value receivers and pointer receivers for large structs, in terms of copying?
130. Hard — Explain how Go's stack growth works for goroutines (starts small, ~2-8KB, grows via copying/segmented stacks historically, now contiguous stacks).

---

## 7. Standard Library, Tooling & Ecosystem

131. **[F]** Easy/Medium — What's the difference between `go build`, `go run`, `go install`, and `go vet`?
132. **[F]** Medium — How do Go Modules (`go.mod`, `go.sum`) work? What problem did they solve compared to `GOPATH`?
133. Medium — How do you pin a specific version of a dependency, and what does `go mod tidy` do?
134. **[F]** Medium — How do you write table-driven tests in Go? Why is this the idiomatic testing style?
135. **[F]** Medium — What is `testing.T` vs `testing.B`? How do you write and run a benchmark in Go?
136. Medium — How do you mock dependencies in Go for unit testing (interfaces + hand-written mocks vs. tools like `gomock`/`mockery`)?
137. Medium — What is `httptest.NewServer` / `httptest.NewRecorder` used for when testing HTTP handlers?
138. **[F]** Medium — How does Go's `net/http` package structure handlers (`http.Handler` interface, `HandlerFunc`)? How would you write middleware (e.g., for logging or auth)?
139. Medium — What is the difference between `encoding/json`'s `Marshal`/`Unmarshal` and using `json.Decoder`/`json.Encoder` for streaming?
140. Medium — How do you handle graceful shutdown of an HTTP server in Go (catching OS signals, `server.Shutdown(ctx)`)?
141. Medium — What logging libraries are commonly used in production Go services (structured logging with `log/slog`, Zap, Zerolog) and why prefer them over the standard `log` package?
142. Easy — What is `go fmt` and why does Go enforce a single canonical formatting style across the ecosystem?
143. Medium — How would you structure a medium-sized Go microservice's project layout (cmd/, internal/, pkg/ conventions)?

---

## 8. Coding Exercises — Strings, Arrays & Classic DSA in Go (live-coding favorites beyond concurrency)

### 8.1 Strings & basic manipulation (extremely common warm-up questions)

144. **[F][C]** Easy — Reverse a string in Go without using built-in reverse functions (mind UTF-8/rune handling — a plain `[]byte` reversal breaks on multi-byte characters).
145. **[F][C]** Easy — Check if a string is a palindrome (and a variant: ignoring case/punctuation/spaces).
146. **[F][C]** Medium — Check if two strings are anagrams of each other (frequency-count via map approach is the expected idiomatic Go solution).
147. **[F][C]** Medium — Find the first non-repeating character in a string.
148. **[C]** Easy — Count the frequency of each character/word in a string using a `map[string]int` (or `map[rune]int`).
149. **[F][C]** Medium — Given a large text/file, count word frequency **concurrently** — split the text into chunks, process each chunk in a goroutine, and merge partial maps safely (combines string processing + concurrency in one question, a favorite at backend-heavy companies).
150. **[C]** Medium — Implement `strings.Contains`/`strstr` (substring search) from scratch.
151. **[C]** Medium — Reverse the words in a sentence in place (e.g., `"the sky is blue"` → `"blue is sky the"`).
152. **[C]** Easy — Swap the values of two variables without using a temporary variable (multiple-assignment idiom: `a, b = b, a`).
153. **[C]** Medium — Check if one string is a rotation of another.
154. **[C]** Medium — Find the longest substring without repeating characters (sliding window — commonly asked even in Go-specific rounds).
155. **[C]** Medium — Implement run-length encoding/decoding of a string.
156. **[C]** Medium — Group anagrams from a list of strings using a map of sorted-string-key → slice of strings.

### 8.2 Arrays, slices & two-pointer/sliding-window problems

157. **[C]** Medium — Given a slice of integers, find all pairs that sum to a target value (two-sum, both O(n²) and O(n) hashmap approaches).
158. **[C]** Easy — Find the second largest element in a slice without sorting.
159. **[C]** Medium — Find the missing number in a slice containing n distinct numbers from 0 to n.
160. **[C]** Medium — Rotate a slice (array) to the right by k steps, in place.
161. **[C]** Medium — Find the maximum sum of any contiguous subarray (Kadane's algorithm) — common "explain your time complexity" follow-up.
162. **[C]** Medium — Merge two sorted slices into one sorted slice without using `sort.Sort`.
163. **[C]** Medium — Find the intersection of two slices (common elements) efficiently using a map.
164. **[C]** Easy — Remove duplicates from a sorted slice in place.
165. **[C]** Medium — Implement a generic `Filter[T any](s []T, pred func(T) bool) []T` and `Reduce[T, U any](s []T, init U, f func(U, T) U) U` using Go generics — tests both DSA thinking and 1.18+ generics knowledge simultaneously.
166. **[C]** Medium — Find all triplets in a slice that sum to zero (3Sum).
167. **[C]** Medium — Given a slice, find the maximum product of two integers in it.
168. **[C]** Easy — Implement `binary search` on a sorted slice, iteratively and recursively.
169. **[C]** Medium — Find the kth largest element in an unsorted slice (quickselect or heap-based approach).

### 8.3 Linked lists, trees, stacks & queues

170. **[F][C]** Medium — Detect a cycle in a singly linked list (Floyd's cycle detection / tortoise-and-hare) implemented with Go structs/pointers.
171. **[C]** Medium — Reverse a singly linked list, iteratively and recursively, using Go struct pointers.
172. **[C]** Medium — Merge two sorted linked lists.
173. **[C]** Medium — Find the middle node of a linked list in one pass.
174. **[F][C]** Medium — Implement a basic stack and queue using a slice, including the gotchas of slice-based pop operations (and why removing from the front of a slice-backed queue is O(n)).
175. **[C]** Medium — Implement a "min stack" that supports push, pop, and retrieving the minimum element in O(1).
176. **[C]** Medium — Check for balanced parentheses/brackets in a string using a stack.
177. **[F][C]** Medium — Implement a binary search tree (BST) in Go with Insert, Search, and InOrder traversal methods.
178. **[C]** Medium — Validate whether a binary tree is a valid BST.
179. **[C]** Medium — Find the maximum depth / height of a binary tree (recursive and iterative/BFS approaches).
180. **[C]** Medium — Check if a binary tree is height-balanced.
181. **[C]** Medium — Implement level-order traversal (BFS) of a binary tree using a slice-backed queue.
182. **[C]** Medium — Find the lowest common ancestor (LCA) of two nodes in a BST.
183. **[C]** Hard — Serialize and deserialize a binary tree to/from a string.

### 8.4 Sorting, recursion & combinatorics

184. **[F][C]** Medium — Implement quicksort or mergesort from scratch on a `[]int`.
185. **[C]** Medium — Print all permutations of a slice of characters or a string (recursive backtracking).
186. **[C]** Medium — Print all subsets/the power set of a slice.
187. **[C]** Easy — Implement a recursive Fibonacci, then optimize it with memoization (`map[int]int`) — tests recursion + map usage together.
188. **[C]** Medium — Implement min and max behavior for a slice without using a third-party library.
189. **[C]** Easy — What is the easiest way to check if a slice is nil or empty, and reverse the order of a slice in place?
190. **[C]** Medium — Climbing stairs / coin change style basic dynamic programming problem, implemented iteratively in Go.
191. **[C]** Medium — Implement a basic trie (prefix tree) in Go for autocomplete-style prefix search.

### 8.5 Concurrency + DSA combined (the "show me you can do both" questions — increasingly common)

192. **[F][C]** Hard — Implement a concurrent merge sort: spawn goroutines for the left/right recursive halves, synchronize with a `chan bool` or `sync.WaitGroup` before merging.
193. **[F][C]** Medium — Implement `SumOfSquares(c int)`: a function using a `for-select` loop with goroutines and channels that streams `1², 2², 3², ...` up to `c` through a channel, and supports early cancellation via a `quit` channel.
194. **[C]** Hard — Given a slice of integers, compute the sum using N goroutines each summing a partition, then combine partial sums safely (classic map-reduce-in-Go warm-up).
195. **[C]** Hard — Implement a concurrent binary tree traversal where each subtree is processed in its own goroutine, with results merged through a channel.
196. **[C]** Hard — Implement a thread-safe counter exposed via an HTTP endpoint, hit concurrently by multiple requests — show correct locking with `sync.Mutex` or `sync/atomic`.
197. **[C]** Medium — Write a generic function to deduplicate elements in a slice while preserving order, then parallelize deduplication across chunks of a very large slice.
198. **[C]** Hard — Implement a simple in-memory key-value store with TTL expiration for entries (background goroutine sweeping expired keys, guarded by a mutex).
199. **[C]** Medium — Implement a concurrent-safe LRU cache (combine map + doubly linked list + mutex) — frequently asked as a 30–45 min standalone design+code exercise.
200. **[C]** Hard — Implement your own simplified version of `sync.WaitGroup` using channels (tests deep understanding, not API memorization).
201. **[C]** Hard — Given a list of URLs/IDs, fetch/process them concurrently with a max concurrency limit (semaphore pattern), collecting both successful results and errors without one failure blocking others.
202. **[C]** Medium — Write a function to flatten a nested slice of interfaces (`[]interface{}`) recursively.

---

## 9. System-Design-Adjacent Go Questions (common at senior-leaning mid-level loops)

203. **[F]** Medium — How would you design a Go service to handle 10,000 concurrent client connections efficiently? What role does Go's goroutine model play here vs. thread-per-connection models in other languages?
204. Medium — How would you implement connection pooling for a database in Go (`database/sql`'s built-in pool, `SetMaxOpenConns`, `SetMaxIdleConns`)?
205. Medium — How do you handle retries with exponential backoff for an external API call in Go, while respecting context cancellation?
206. **[F]** Medium — How would you implement a circuit breaker pattern in Go for calls to a flaky downstream service?
207. Medium — How do you structure a Go application to support graceful degradation if a dependency (e.g., Redis) is unavailable?
208. Medium — How would you batch and debounce writes to a database from a high-throughput Go service (e.g., using a buffered channel + worker that flushes on size/time threshold)?
209. Hard — Design a Go-based rate limiter for an API gateway, supporting per-client limits (token bucket or leaky bucket implemented with goroutines/tickers or `golang.org/x/time/rate`).
210. Medium — How would you handle distributed tracing/context propagation across services in Go (e.g., via `context.Context` and OpenTelemetry)?

---

## 10. "Tricky / Gotcha" Quick-Fire Round (frequently cited as the questions that catch experienced devs off guard)

211. **[T]** What does this print, and why?

```go
func main() {
    defer fmt.Println("1")
    defer fmt.Println("2")
    defer fmt.Println("3")
}
```

(Tests LIFO order of defers.) 212. **[T]** Why does a `for i := 0; i < 5; i++ { go func() { fmt.Println(i) }() }` sometimes print `5 5 5 5 5` on Go versions before 1.22, and why did this change in 1.22? 213. **[T]** What's wrong with returning a pointer to a local variable in Go — is this safe (unlike C), and why? 214. **[T]** Why does comparing two structs with `==` work, but comparing two slices with `==` fail to compile? 215. **[T]** What happens if you call a method with a pointer receiver on a `nil` pointer of that type? Is it always a panic? 216. **[T]** Why might `interface{}` holding a `nil` `*MyStruct` not itself be considered `nil` when compared with `== nil`? 217. **[T]** What's the output difference between using `range` to iterate a slice of structs and mutating the loop variable, vs. mutating via index — and how did Go 1.22's per-iteration loop variable change affect this class of bug? 218. **[T]** Why can appending to a slice silently corrupt another, unrelated slice if you're not careful with capacity and sub-slicing? 219. **[T]** Why does an unbuffered channel send block until _both_ sender and receiver are ready, and how does that differ from a buffered channel with available capacity?

---

## Suggested Prep Strategy

Given a 2–4 year experience bar, interviewers typically allocate roughly: 30% core language/syntax sanity checks, 40% concurrency (goroutines/channels/sync/context — this is where Go interviews differentiate candidates), 15% error handling and idiomatic patterns, 15% live coding (often a concurrency pattern from Section 3.5, or a DSA problem from Section 8 solved in Go). Prioritize Sections 2, 3, and 10 — slice internals and concurrency gotchas are asked far more often than generic OOP-style questions, since they're what distinguish someone who has _used_ Go from someone who has only _read about_ it.
