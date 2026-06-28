# System Design — Master Plan & Perspective Reset
> **For:** Gautham Gokulakonda | Senior SWE, 3 YOE | Targeting FAANG + Indian Unicorns
> **Goal:** Long-term self-study reference — breadth first, depth later
> **Format:** This is your "before you open any book" document. Read this first, every time.

---

## PART 1 — WHAT IS SYSTEM DESIGN (AND WHAT IT IS NOT)

### The Single Most Important Insight
System Design is **not about memorizing architectures**. It is about developing **judgment** — the ability to look at a set of requirements, constraints, and scale numbers, and reason about trade-offs to arrive at a *defensible* design. There is never one correct answer. There are only better and worse answers *given the constraints*.

> "Don't memorize systems. Build a mindset. Practice structure. Develop judgment."
> — systemdesignhandbook.com

### What interviewers are actually testing
At FAANG level, interviewers want to see:
1. **Can you break ambiguity?** — Ask smart clarifying questions before drawing a single box.
2. **Can you reason about scale?** — Your choices must reflect 10M users, not 10.
3. **Can you articulate trade-offs?** — Why this, and not that?
4. **Can you communicate under pressure?** — Explain complex ideas simply.
5. **Can you adapt?** — Interviewers *will* change constraints mid-interview ("now add multi-region failover").

At Indian unicorn level (Flipkart, Razorpay, Swiggy, Zepto, PhonePe), the focus is more practical:
- Data modelling and API design matter as much as architecture
- LLD (Low Level Design) is often a separate round — class diagrams, SOLID principles
- Real-world India-specific scale: UPI spikes, flash sales, OTP delivery SLAs

### The Fundamental Difference From Coding Interviews
| Coding Interview | System Design Interview |
|---|---|
| One correct answer | Many valid answers |
| Closed-ended | Open-ended |
| Tests knowledge | Tests judgment |
| 20–45 minutes, solo | 45–60 minutes, collaborative |
| You write code | You draw and discuss |

---

## PART 2 — THE RIGHT MENTAL MODELS

### Mental Model 1: Think in Layers
Every system has the same layers. Train yourself to think top-down:

```
[Client / Browser / Mobile App]
        ↓
[DNS → Load Balancer → CDN]
        ↓
[API Gateway / BFF]
        ↓
[Microservices / Application Layer]
        ↓
[Cache Layer (Redis)]      [Message Queue (Kafka)]
        ↓
[Primary Database]  →  [Read Replicas]
        ↓
[Object Storage (S3)]   [Search (Elasticsearch)]
```

Every component you add must answer: **Why not the layer above or below it?**

### Mental Model 2: The Three Axes of Every Design Decision
Before picking any technology or pattern, ask yourself where it sits on these three axes:

1. **Consistency ↔ Availability** (CAP Theorem)
2. **Latency ↔ Throughput** (you can optimise for one, often at cost of the other)
3. **Read-heavy ↔ Write-heavy** (determines caching strategy, DB choice, replication)

### Mental Model 3: Scale Has Phases
Don't over-engineer from the start. Know these phases:

| Phase | Scale | What breaks |
|---|---|---|
| Phase 1 | 1 server, 1 DB | Nothing yet |
| Phase 2 | 10K users | DB becomes the bottleneck |
| Phase 3 | 100K users | Need caching, read replicas |
| Phase 4 | 1M users | Need sharding, queues, CDN |
| Phase 5 | 10M+ users | Need microservices, global replication |

**The interviewer wants to know you understand what breaks at each phase and why.**

### Mental Model 4: Ask "What If This Component Dies?"
For every box you draw, ask: "What happens when this fails?"
- Single point of failure? → Add redundancy
- Can we tolerate stale data? → Cache is okay
- Can we tolerate message loss? → Ack-based queuing
- Can we tolerate eventual consistency? → NoSQL is fine

### Mental Model 5: The 4-Phase Interview Framework
Every system design answer should follow this structure:

```
Phase 1: Clarify (5 min)
  → Functional requirements
  → Non-functional requirements
  → Scale estimates
  → Constraints

Phase 2: Estimate (3–5 min)
  → DAU, QPS, storage, bandwidth

Phase 3: High-Level Design (15 min)
  → Draw the boxes
  → Explain data flow
  → Pick DB and storage types

Phase 4: Deep Dive (15 min)
  → Interviewer picks 1–2 areas to dig into
  → Trade-offs, bottlenecks, alternatives
```

---

## PART 3 — THE QUESTIONS YOU MUST ALWAYS ASK YOURSELF

### During Requirement Clarification
- How many users? DAU? MAU?
- What is the read:write ratio?
- What is the acceptable latency? (real-time vs eventual)
- Is this global or single-region?
- Do we need strong consistency or eventual consistency is okay?
- What are the peak traffic patterns? (flash sales, match day, etc.)
- What is the data retention requirement?
- Mobile-only, web-only, or both?
- Do we need offline support?

### During High-Level Design
- Where does data live and in what format?
- What is the hot path (high frequency, latency-sensitive)?
- What is the cold path (batch, async)?
- What component is the bottleneck first?
- What is the fan-out factor? (1 action → how many writes/reads?)
- How do we handle duplicate requests? (idempotency)
- What is the failure mode of each component?

### During Deep Dive
- What indexes are needed on this table?
- How do we shard this data? What is the shard key?
- What does the cache invalidation strategy look like?
- How do we handle backpressure on the queue?
- How do we monitor this system? (metrics, alerts, SLOs)
- How do we handle schema migrations without downtime?

---

## PART 4 — NUMBERS EVERY SYSTEM DESIGNER MUST KNOW

### Power of 10 — Data Size Reference
| Unit | Value |
|---|---|
| 1 KB | 10³ bytes |
| 1 MB | 10⁶ bytes |
| 1 GB | 10⁹ bytes |
| 1 TB | 10¹² bytes |
| 1 PB | 10¹⁵ bytes |

**Quick size intuitions:**
- A tweet/short text: ~300 bytes
- A user profile row: ~1 KB
- A high-res photo: ~1–3 MB
- A 1-min video (compressed): ~50 MB
- A 2-hour movie (HD): ~4–8 GB

### Latency Numbers (memorise the order of magnitude)
| Operation | Latency |
|---|---|
| L1 cache access | ~1 ns |
| L2 cache access | ~10 ns |
| RAM access | ~100 ns |
| SSD random read | ~100 µs (0.1 ms) |
| HDD random read | ~10 ms |
| Same datacenter network round-trip | ~0.5–1 ms |
| Cross-AZ (same region) | ~1–2 ms |
| Cross-region (e.g. Mumbai → Singapore) | ~50–100 ms |
| Cross-continent (Mumbai → US) | ~150–200 ms |

**The rule:** RAM is 1000x faster than SSD. SSD is 100x faster than disk. Network in same DC is 0.5ms. Cache everything that doesn't need to be fresh.

### Throughput Benchmarks (approximate)
| Component | QPS / Throughput |
|---|---|
| A single modern server (API) | ~10,000–50,000 QPS |
| PostgreSQL (read, indexed) | ~10,000 QPS |
| PostgreSQL (write) | ~1,000–5,000 QPS |
| Redis | ~100,000–500,000 QPS |
| Kafka | ~1,000,000 messages/sec (per partition cluster) |
| A single Nginx server | ~10,000–50,000 req/sec |
| CDN edge node | ~100,000+ req/sec |

### Availability Numbers
| Uptime % | Downtime per year | Called |
|---|---|---|
| 99% | ~3.65 days | Two nines |
| 99.9% | ~8.7 hours | Three nines |
| 99.99% | ~52 minutes | Four nines |
| 99.999% | ~5 minutes | Five nines |

FAANG targets: 99.99% to 99.999%. Indian unicorns: typically 99.9%+.

### Back-of-Envelope Formula Cheat Sheet
```
QPS = (DAU × actions_per_user_per_day) / 86,400

Peak QPS = Average QPS × 2–10 (depending on traffic pattern)

Storage per year = daily_writes × record_size × 365

Bandwidth = QPS × average_response_size

Number of servers = Peak QPS / QPS_per_server

Cache size = daily_requests × 0.2 × avg_object_size  (80/20 rule)
```

**Example — Twitter-like system:**
- 50M DAU, 10 timeline reads/day, 1 tweet/day
- Read QPS = (50M × 10) / 86,400 ≈ 5,800 QPS → round to **6,000**
- Write QPS = (50M × 1) / 86,400 ≈ 580 QPS → round to **600**
- Peak read QPS = 6,000 × 5 = **30,000 QPS**
- Storage: 50M tweets/day × 300 bytes = 15GB/day → **5.5 TB/year**

### Time Constants to Remember
```
1 day    = 86,400 seconds   ≈ 10⁵
1 month  = 2.6M seconds     ≈ 10⁶ (rough)
1 year   = 31.5M seconds    ≈ 3 × 10⁷
```

---

## PART 5 — THE RULES OF THUMB

1. **Cache everything that doesn't change per request.** Static assets → CDN. Computed results → Redis.
2. **Async over sync for non-critical paths.** Sending an email after signup? Use a queue, don't block the response.
3. **Separate read and write paths.** Command Query Responsibility Segregation (CQRS). Write to primary, read from replica/cache.
4. **Add a queue before any slow downstream.** Protects you from spikes and decouples services.
5. **Stateless services wherever possible.** Session state → Redis or JWTs. Stateless services scale horizontally with zero friction.
6. **Shard by the most common query pattern.** If you always query by user_id, shard by user_id. Wrong shard key = hot spots.
7. **NoSQL is not "better than SQL" — it's a trade-off.** NoSQL gives you horizontal scale and flexibility at the cost of ACID transactions and complex joins.
8. **CDN for anything that travels far.** Static content, video, even some API responses.
9. **Idempotency for all write APIs.** Retries happen. Design your writes to be safe to repeat.
10. **Design for failure, not for happy paths.** Circuit breakers, retries with backoff, dead letter queues, health checks.
11. **The 80/20 rule governs caching.** 20% of data serves 80% of requests. Cache that 20%.
12. **Prefer horizontal scaling over vertical.** Adding more machines is cheaper and safer than adding more RAM to one machine.
13. **Observability is part of the design.** Every system needs metrics, logs, and traces (the three pillars of observability).
14. **Pick boring technology.** Proven tools (PostgreSQL, Redis, Kafka) over experimental ones in interviews.

---

## PART 6 — THE 5 PARALLEL LEARNING TRACKS (THE PLAN)

Your full system design curriculum is split into 5 independent tracks. Each track is a standalone self-study module. Study them in parallel (one topic per day across tracks) or sequentially (finish one track before the next).

### Track 1 — Foundations & Communication
**Topics:** Networking fundamentals, HTTP/HTTPS/HTTP2/HTTP3, DNS, CDN, Load Balancers, API Design (REST/GraphQL/gRPC), WebSockets, SSE, Rate Limiting, API Gateway, Proxies (Forward/Reverse)

**Why first?** Every system design question starts with "how does a request get to your server and what does your server return?" You cannot discuss anything else without this foundation.

---

### Track 2 — Storage & Data
**Topics:** SQL vs NoSQL, ACID, CAP Theorem, Indexing, Sharding, Replication, Consistent Hashing, SQL Databases (PostgreSQL), NoSQL Databases (MongoDB, DynamoDB, Cassandra), Object Storage (S3), Search (Elasticsearch), Data Modelling

**Why second?** Every system stores data. Your DB choice and its scaling strategy is usually the #1 bottleneck in any design. This is the most frequently deep-dived topic in interviews.

---

### Track 3 — Scalability & Performance
**Topics:** Caching (L1/L2/Redis/Memcached), Cache patterns (write-through, write-back, write-around), Cache invalidation, Horizontal vs Vertical Scaling, Database Connection Pooling, Message Queues (Kafka, RabbitMQ, SQS), Event-Driven Architecture, Pub/Sub, Backpressure, CQRS, Event Sourcing

**Why third?** Once you have your storage right, scalability is about adding the right acceleration and decoupling layers. Cache + Queue is the answer to 80% of scaling problems.

---

### Track 4 — Distributed Systems & Reliability
**Topics:** Consistency models (strong, eventual, causal), Consensus algorithms (Raft, Paxos), Distributed transactions (2PC, Saga pattern), Leader election, Fault tolerance, Circuit breakers, Retry patterns, Idempotency, Bloom Filters, Distributed Locking, Gossip Protocol, Service Discovery, Health checks, SLOs/SLAs/SLIs, Observability (Metrics, Logging, Tracing)

**Why fourth?** This is what separates mid-level from senior-level answers. Interviewers probe this area to see if you understand what happens when things go wrong at scale.

---

### Track 5 — System Design in Practice (Case Studies)
**Topics:** 15 classic system design problems solved end-to-end — URL Shortener, Rate Limiter, Pastebin, Instagram/Photo Sharing, Twitter Feed (Newsfeed), WhatsApp/Chat System, YouTube/Video Streaming, Uber/Ride Sharing, Google Drive/Dropbox, Notification System, Search Autocomplete, Web Crawler, Distributed Cache, Payment System (Razorpay-style), Ticket Booking System

**Why last?** Case studies are where you apply all four tracks. Each case study will explicitly reference components from Tracks 1–4, connecting all your knowledge.

---

## PART 7 — BEST RESOURCES

### Books (in order of recommendation)
1. **System Design Interview – An Insider's Guide (Vol 1 & 2)** by Alex Xu
   - Best single book. Vol 1 for fundamentals, Vol 2 for advanced.
   - Link: https://www.amazon.in/System-Design-Interview-insiders-Second/dp/B08CMF2CQF

2. **Designing Data-Intensive Applications (DDIA)** by Martin Kleppmann
   - The bible for deep understanding of databases and distributed systems.
   - Link: https://dataintensive.net/

3. **System Design Interview – An Insider's Guide Vol 2** by Alex Xu
   - Advanced topics: proximity service, hotel reservation, stock exchange, etc.

### Online Platforms
1. **ByteByteGo** (Alex Xu) — Best visual learning, diagrams are unmatched
   - https://bytebytego.com

2. **System Design Primer** (Donne Martin, GitHub) — Free, 334K+ GitHub stars, comprehensive
   - https://github.com/donnemartin/system-design-primer

3. **Grokking the System Design Interview** (DesignGurus) — Interview-focused, case-based
   - https://www.designgurus.io/course/grokking-the-system-design-interview

4. **Hello Interview** — Numbers, frameworks, estimation deep-dives
   - https://www.hellointerview.com/learn/system-design

5. **High Scalability Blog** — Real engineering case studies from companies
   - http://highscalability.com

### YouTube Channels
1. **ByteByteGo** (Alex Xu) — Animated, visual explanations
   - https://www.youtube.com/@ByteByteGo

2. **Gaurav Sen** — Very popular in India, clear explanations
   - https://www.youtube.com/@gkcs

3. **System Design Fight Club** — Whiteboard-style deep dives
   - https://www.youtube.com/@SDFC

4. **NeetCode** — System design + DSA, concise
   - https://www.youtube.com/@NeetCode

### Engineering Blogs (read real-world decisions)
- Netflix Tech Blog: https://netflixtechblog.com
- Uber Engineering: https://www.uber.com/en-IN/blog/engineering/
- Discord Engineering: https://discord.com/blog/engineering
- Shopify Engineering: https://shopify.engineering
- Razorpay Blog: https://engineering.razorpay.com
- Swiggy Tech: https://bytes.swiggy.com
- Zepto Engineering: https://engineering.zepto.co.in

### For Indian Market Context
- GeeksforGeeks Interview Experiences: https://www.geeksforgeeks.org/category/interview-experiences/
- LeetCode Discuss (Indian companies): https://leetcode.com/discuss/interview-experience

---

## PART 8 — HOW TO USE THE 5 PARALLEL AGENT PROMPTS

Each of the 5 files (Track 1 through Track 5) is a complete, self-contained prompt. When you are ready to generate the actual study content:

1. Open 5 separate Claude conversations
2. Paste each track's prompt file into one conversation
3. Run them in parallel — they are fully independent
4. Each will generate a comprehensive markdown study guide for that track

**Estimated output per track:** 3,000–5,000 words of study material, covering:
- Concept explanation (why, what, where, trade-offs)
- Interview Q&A (how questions are asked + ideal answers)
- Key numbers and rules of thumb for that track
- Resource links specific to that track

---

*This document is your anchor. Come back to it before every study session and before every interview.*
