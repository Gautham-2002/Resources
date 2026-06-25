**Senior Engineer**

**Interview Preparation Guide**

65 Questions & Senior-Level Answers

API Design • Database & Schema • Distributed Systems • Performance

Software Design • Debugging • Principles & Patterns • Messaging

Gokulakonda Gautham • 2026

# **Table of Contents**

**1\. API Design** (13 questions)

Q1. How do you design a REST API from scratch?

Q2. How do you handle backward compatibility when evolving an API?

Q3. How do you design pagination for a large dataset API?

Q4. How do you design an API for rate limiting?

Q5. What is the difference between REST, GraphQL, and gRPC - and when do you choose each?

Q6. How do you design for idempotency in APIs?

Q7. How do you design API authentication and authorization?

Q8. How do you design an API that needs to support long-running operations?

Q9. What is the difference between PUT and PATCH?

Q10. How do you design API security beyond authentication?

Q11. How do you design an API for file uploads?

Q12. How do you design an idempotent job/background worker system?

Q13. What is the difference between an idempotency token, correlation ID, and trace ID?

**2\. Database & Schema** (9 questions)

Q1. Walk me through database normalization - 1NF through 3NF with examples.

Q2. How do you design a database schema for a multi-tenant SaaS application?

Q3. How do you handle database migrations in production without downtime?

Q4. Explain database indexing - when do you add an index and when is it harmful?

Q5. What is the N+1 query problem and how do you solve it?

Q6. What is a database transaction and what are isolation levels?

Q7. What is a database deadlock and how do you prevent it?

Q8. What is sharding and what are the common sharding strategies?

Q9. How do database views, materialized views, and CTEs differ?

**3\. Distributed Systems** (10 questions)

Q1. Explain CAP theorem and how it affects your design decisions.

Q2. What is the Saga pattern and how does it compare to 2-Phase Commit?

Q3. How do you design a system to handle exactly-once message delivery?

Q4. How do you implement distributed rate limiting across multiple instances?

Q5. What is a circuit breaker and when do you use it?

Q6. How do you design a distributed cache and what cache invalidation strategies do you know?

Q7. What is service discovery and how does it work in Kubernetes?

Q8. How do you implement graceful shutdown in a service?

Q9. What is the outbox pattern and how does it solve dual writes?

Q10. What is a health check? How should you design readiness vs liveness probes?

**4\. Performance & Latency** (6 questions)

Q1. How do you debug the latency of a slow API endpoint?

Q2. How do you optimize a system that is hitting its throughput limit?

Q3. How do you profile a Go application in production?

Q4. What is connection pooling and why does it matter?

Q5. What is tail latency and why is p99 more important than average latency?

Q6. What is horizontal vs vertical scaling? When do you choose each?

**5\. Software Design** (6 questions)

Q1. How do you approach system design for a new feature from scratch?

Q2. What is event-driven architecture and when would you use it?

Q3. What is the difference between microservices and a monolith? When do you prefer each?

Q4. How do you design a feature flag system?

Q5. What is synchronous vs asynchronous communication in microservices?

Q6. How do you handle secrets and configuration management in production?

**6\. Debugging** (5 questions)

Q1. How do you approach debugging a production issue you've never seen before?

Q2. How do you debug a memory leak in a production Go service?

Q3. How do you add observability to a microservices system?

Q4. How do you approach a race condition in concurrent code?

Q5. How do you debug an intermittent failure you cannot reproduce locally?

**7\. Principles & Patterns** (10 questions)

Q1. Walk me through SOLID principles with concrete examples.

Q2. What are design patterns - explain 5+ patterns you've used in production.

Q3. What is DRY vs WET vs AHA? When is code duplication acceptable?

Q4. Explain CQRS and Event Sourcing.

Q5. What are the 12-Factor App principles and how do they affect your architecture?

Q6. What is dependency injection and why does it matter?

Q7. What is eventual consistency and how do you handle it in the UI and backend?

Q8. What is clean architecture / hexagonal (ports and adapters) pattern?

Q9. What is immutability and why is it important in distributed systems?

Q10. What is technical debt and when do you pay it down vs live with it?

**8\. Messaging & Events** (6 questions)

Q1. How does Kafka work and when do you choose it over RabbitMQ?

Q2. How do you design a dead letter queue and why does it matter?

Q3. Explain backpressure in streaming systems.

Q4. How do you ensure message ordering in a distributed messaging system?

Q5. What is database query plan caching and why can it cause problems?

Q6. What is the difference between microservices synchronous and asynchronous communication and when do you use each?

## **1\. API Design**

| **Q1** | **How do you design a REST API from scratch?** | **API Design** |
| ------ | ---------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Start with resources, not actions</strong></p><p>Every noun in your domain becomes a URL segment. Operations map to HTTP verbs. Identify domain entities (User, Order, Product), use plural nouns like /users and /orders/:id/items, and avoid verbs in paths - /getUser is wrong; GET /users/:id is right.</p><p><strong>Versioning strategy</strong></p><ul><li>URL versioning (/v1/users) - most explicit, easiest to route at the gateway</li><li>Header versioning (Accept: application/vnd.api+json;version=2) - cleaner URLs but harder to test in browser</li><li>Prefer URL versioning for public APIs: cache-friendly and debuggable</li></ul><p><strong>Standard response shape</strong></p><table><tbody><tr><th><p>{ "data": { ... }, // always present on success</p><p>"error": null, // null on success, object on failure</p><p>"meta": { // pagination, rate limit info</p><p>"page": 1,</p><p>"total": 240,</p><p>"rate_limit_remaining": 95</p><p>}</p><p>}</p></th></tr></tbody></table><p><strong>Status codes - the non-obvious ones</strong></p><ul><li>201 Created + Location header on POST</li><li>202 Accepted for async jobs (return a job ID)</li><li>422 Unprocessable Entity for business logic failures (valid JSON, invalid logic)</li><li>409 Conflict for duplicate resource creation</li><li>Never let 500s leak internal details - map exceptions to problem types</li></ul><p><strong>Idempotency</strong></p><p>PUT and DELETE must be idempotent by definition. For POST (e.g., payments), accept an Idempotency-Key header and cache the result for ~24h so retries are safe.</p></th></tr></tbody></table></div>

| **Q2** | **How do you handle backward compatibility when evolving an API?** | **API Design** |
| ------ | ------------------------------------------------------------------ | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>Never break a contract that a client depends on. The key insight: evolution and breaking changes are different things.</p><p><strong>Safe changes (non-breaking)</strong></p><ul><li>Adding new optional fields to responses</li><li>Adding new endpoints</li><li>Adding new optional query parameters</li><li>Relaxing validation rules</li></ul><p><strong>Breaking changes (require version bump)</strong></p><ul><li>Renaming or removing a field</li><li>Changing a field's type</li><li>Making an optional field required</li><li>Changing HTTP status codes for existing scenarios</li></ul><p><strong>Migration strategy</strong></p><ul><li>Run v1 and v2 simultaneously (the expand-contract pattern)</li><li>Deprecate v1 with a Deprecation and Sunset response header</li><li>Use API gateways to route traffic gradually (feature flags at the gateway layer)</li></ul><p>If you cannot version: introduce the new field alongside the old one, serve both, document the old one as deprecated, and remove after a sunset window.</p></th></tr></tbody></table></div>

| **Q3** | **How do you design pagination for a large dataset API?** | **API Design** |
| ------ | --------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Offset pagination</strong></p><table><tbody><tr><th><p>GET /users?page=5&amp;limit=20</p><p>-- SQL: SELECT * FROM users ORDER BY id OFFSET 80 LIMIT 20</p></th></tr></tbody></table><p>Problem: if a row is inserted between pages, you get duplicates or skips. Also, OFFSET scans are O(offset) - slow at large offsets.</p><p><strong>Cursor-based pagination (preferred for real-time data)</strong></p><table><tbody><tr><th><p>GET /users?after=cursor_opaque_value&amp;limit=20</p><p>-- Server decodes cursor to: WHERE id &gt; 12345 ORDER BY id LIMIT 20</p></th></tr></tbody></table><ul><li>Stable under inserts and deletes</li><li>O(log n) with an index</li><li>Tradeoff: cannot jump to page 50 arbitrarily</li></ul><p><strong>When to use which</strong></p><ul><li>Offset: admin panels where you need arbitrary page jumps and data is not real-time</li><li>Cursor/Keyset: feeds, timelines, any data with inserts during pagination</li></ul></th></tr></tbody></table></div>

| **Q4** | **How do you design an API for rate limiting?** | **API Design** |
| ------ | ----------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Common algorithms</strong></p><ul><li>Token bucket: bucket of N tokens, refilled at rate R. Bursts allowed up to bucket size. Best for general use.</li><li>Sliding window log: store timestamp of each request; count in last 60s. Accurate but memory-heavy.</li><li>Fixed window counter: simple but has a spike problem at window boundary (2x traffic possible).</li><li>Sliding window counter: hybrid - weight previous window by overlap fraction. Best accuracy-to-cost tradeoff.</li></ul><p><strong>What to limit on</strong></p><ul><li>IP - but be careful with NAT (entire offices behind one IP)</li><li>User/API key - better for authenticated endpoints</li><li>User + endpoint combination - different limits for cheap vs expensive endpoints</li></ul><p><strong>Response contract</strong></p><table><tbody><tr><th><p>HTTP 429 Too Many Requests</p><p>X-RateLimit-Limit: 100</p><p>X-RateLimit-Remaining: 0</p><p>X-RateLimit-Reset: 1720000000 // Unix timestamp</p><p>Retry-After: 60</p></th></tr></tbody></table><p>Redis is the standard store. Use INCR + EXPIRE for fixed window; sorted sets for sliding window log. Use a Lua script to make INCR + check atomic.</p></th></tr></tbody></table></div>

| **Q5** | **What is the difference between REST, GraphQL, and gRPC - and when do you choose each?** | **API Design** |
| ------ | ----------------------------------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>REST</strong></p><p>Resource-oriented, human-readable, stateless. Works great when your domain maps cleanly to nouns and you have diverse clients (web, mobile, third-party).</p><p><strong>GraphQL</strong></p><p>Query language - clients specify exactly what fields they need. Solves over-fetching and under-fetching. Best for: product APIs with many client types, rapid frontend iteration, or graph-shaped data models. Tradeoffs: harder to cache (POSTs), N+1 query problems require dataloaders, complex authorization logic.</p><p><strong>gRPC</strong></p><p>Binary protocol over HTTP/2 with Protobuf schemas. Best for: internal service-to-service communication, streaming, or strongly typed contracts across teams. Tradeoffs: not browser-native (needs grpc-web proxy), Protobuf schema management overhead.</p><p><strong>Heuristic</strong></p><ul><li>Public / third-party API → REST</li><li>Complex product with many clients → GraphQL</li><li>Internal microservices → gRPC</li></ul></th></tr></tbody></table></div>

| **Q6** | **How do you design for idempotency in APIs?** | **API Design** |
| ------ | ---------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>Idempotency means calling an operation multiple times produces the same result as calling it once. Critical for payment, order creation, and any mutation.</p><p><strong>HTTP verbs</strong></p><p>GET, HEAD, PUT, DELETE are idempotent by spec. POST and PATCH are not by default.</p><p><strong>Making POST idempotent</strong></p><table><tbody><tr><th><p>POST /payments</p><p>Idempotency-Key: uuid-from-client</p><p>key = hash("idempotency:" + client_id + ":" + idempotency_key)</p><p>cached = redis.get(key)</p><p>if cached: return cached</p><p>result = process_payment(body)</p><p>redis.setex(key, 86400, serialize(result))</p><p>return result</p></th></tr></tbody></table><ul><li>Key must be scoped to the client</li><li>Cache the entire response, not just a flag</li><li>Use a distributed lock during processing to avoid double execution</li><li>Return 200 (not 201) on a replayed request so clients know it was a replay</li></ul></th></tr></tbody></table></div>

| **Q7** | **How do you design API authentication and authorization?** | **API Design** |
| ------ | ----------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>Authentication = who are you. Authorization = what can you do.</p><p><strong>Authentication options</strong></p><ul><li>API keys: simple for machine-to-machine. Hash them in DB (SHA-256), never store raw.</li><li>JWT: stateless, self-contained. Access token (15min TTL) + refresh token (7-30d). Validate signature + expiry on every request. Never put sensitive data in payload.</li><li>OAuth 2.0: for delegated access. Use authorization code flow with PKCE for web/mobile.</li></ul><p><strong>JWT access/refresh rotation</strong></p><table><tbody><tr><th><p>1. Login → issue access_token (15min) + refresh_token (7d, HttpOnly cookie)</p><p>2. Expired access_token → client sends refresh_token</p><p>3. Server validates, issues new access_token + rotates refresh_token</p><p>4. Old refresh_token is invalidated (token family detection)</p><p>5. Stolen refresh_token reused → invalidate entire token family</p></th></tr></tbody></table><p><strong>Authorization patterns</strong></p><ul><li>RBAC (Role-Based): user has roles (admin, editor). Simple but coarse.</li><li>ABAC (Attribute-Based): policy checks attributes. Fine-grained but complex.</li><li>ReBAC (Relation-Based, like Google Zanzibar): user can edit doc because user is member of group with edit permission. Best for complex ownership graphs.</li></ul></th></tr></tbody></table></div>

| **Q8** | **How do you design an API that needs to support long-running operations?** | **API Design** |
| ------ | --------------------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>Never make the client wait synchronously for something that takes more than 1-2 seconds.</p><p><strong>Async job pattern</strong></p><table><tbody><tr><th><p>// 1. Submit</p><p>POST /exports → 202 Accepted</p><p>{ "job_id": "job_abc123", "status_url": "/jobs/job_abc123" }</p><p>// 2. Poll</p><p>GET /jobs/job_abc123 → { "status": "running", "progress": 45 }</p><p>// 3. Done</p><p>GET /jobs/job_abc123 → { "status": "done", "result_url": "/exports/result.csv" }</p></th></tr></tbody></table><p><strong>Push-based alternatives</strong></p><ul><li>Webhooks: server POSTs to a client URL when done. Best for async B2B integrations.</li><li>SSE (Server-Sent Events): client opens a long-lived GET, server streams updates. Great for progress bars. Works through proxies unlike WebSockets.</li><li>WebSockets: bidirectional, real-time. Overkill for one-way progress updates.</li></ul><p><strong>Job queue design</strong></p><p>Store jobs in DB for durability. Track status transitions: pending → running → done/failed. Support retries with exponential backoff and a dead-letter queue.</p></th></tr></tbody></table></div>

| **Q9** | **What is the difference between PUT and PATCH?** | **API Design** |
| ------ | ------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>PUT - full replacement</strong></p><table><tbody><tr><th><p>PUT /users/123</p><p>{ "name": "Gautham", "email": "g@example.com" }</p><p>// Result: user has exactly these fields - other fields are removed</p></th></tr></tbody></table><p><strong>PATCH - partial update</strong></p><table><tbody><tr><th><p>PATCH /users/123</p><p>{ "email": "new@example.com" }</p><p>// Result: only email is changed, name is preserved</p></th></tr></tbody></table><p><strong>Idempotency</strong></p><p>PUT is idempotent by spec. PATCH is NOT necessarily idempotent - increment patches like { "count": "+1" } are not idempotent.</p><p><strong>When to use which</strong></p><ul><li>PUT: when the client knows and sends the complete representation</li><li>PATCH: when clients update specific fields (inline editing, toggling a flag)</li><li>Most modern APIs use PATCH for updates because clients rarely want to send the full resource</li></ul></th></tr></tbody></table></div>

| **Q10** | **How do you design API security beyond authentication?** | **API Design** |
| ------- | --------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Input validation</strong></p><ul><li>Validate every input at the API boundary: type, range, length, format</li><li>Never trust client-supplied IDs to access resources without verifying ownership (prevents IDOR - Insecure Direct Object Reference)</li><li>Parameterized queries always - never interpolate user input into SQL strings</li></ul><p><strong>Output filtering</strong></p><ul><li>Do not return more fields than the caller needs</li><li>Apply object-level and field-level authorization (not just route-level)</li></ul><p><strong>OWASP API Top 10 (key items)</strong></p><ul><li>BOLA/IDOR: access control at the object level</li><li>Mass assignment: do not bind request body fields to model fields blindly</li><li>Excessive data exposure: return only what is needed</li><li>Security misconfiguration: no default credentials, no verbose errors in prod, no open CORS</li></ul><p><strong>CORS</strong></p><p>Do not set Access-Control-Allow-Origin: * for authenticated APIs. Whitelist specific origins. Use SameSite=Strict cookies to prevent CSRF.</p></th></tr></tbody></table></div>

| **Q11** | **How do you design an API for file uploads?** | **API Design** |
| ------- | ---------------------------------------------- | -------------- |

**Small files (< 5 MB): direct upload**

POST /uploads

Content-Type: multipart/form-data

// Body: file bytes + metadata fields

Simple but: gateway/load balancer body size limits, file goes through your API server consuming memory and CPU.

**Large files: presigned URL pattern (preferred)**

// Step 1: Client requests an upload URL

POST /uploads/initiate

{ "filename": "report.pdf", "size": 52428800 }

→ { "upload_url": "<https://storage.googleapis.com/>...", "file_id": "file_abc123" }

// Step 2: Client uploads DIRECTLY to GCS/S3

PUT upload_url ← binary file data

// Step 3: Client confirms upload

POST /uploads/file_abc123/confirm

Post-upload processing: do not process files synchronously. Publish an event; background workers handle virus scanning, format conversion, thumbnail generation.

| **Q12** | **How do you design an idempotent job/background worker system?** | **API Design** |
| ------- | ----------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>Background workers must be designed to handle reruns, duplicate job dispatches, and partial failures without corrupting state.</p><p><strong>Core principle: jobs must be idempotent</strong></p><p>Running the same job twice should produce the same result as running it once.</p><p><strong>Design patterns</strong></p><ul><li>Deduplicate at dispatch: check if a job with the same idempotency key already exists in pending/running state</li><li>Check-before-act in the worker: verify the prerequisite state is still true before doing work</li><li>Write result idempotently: use UPSERT / INSERT ON CONFLICT; use conditional updates (UPDATE ... WHERE status = 'pending')</li></ul><p><strong>Job state machine</strong></p><table><tbody><tr><th><p>pending → running → done</p><p>pending → running → failed → pending (retry) → ... → dead</p></th></tr></tbody></table><p>Track attempt_count, last_error, next_run_at. Use exponential backoff for retry timing.</p></th></tr></tbody></table></div>

| **Q13** | **What is the difference between an idempotency token, correlation ID, and trace ID?** | **API Design** |
| ------- | -------------------------------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Idempotency token / key</strong></p><p>Client-generated token passed with a mutation request. Enables the server to deduplicate retries. Scope: one logical operation (one payment, one order). Consumed by the server for deduplication logic.</p><p><strong>Correlation ID</strong></p><p>A request-scoped identifier that follows a request through all services it touches. Generated at the entry point. Passed via HTTP header (X-Correlation-ID). Every service logs it and passes it downstream. Purpose: trace all log lines across services that belong to one logical request.</p><p><strong>Trace ID (OpenTelemetry)</strong></p><p>Similar to correlation ID but with more structure: trace ID identifies the entire request tree; span IDs identify individual operations within the trace; parent-child span relationships form the trace tree. Propagated via W3C traceparent header.</p><p><strong>In practice</strong></p><ul><li>Idempotency keys: payments, order creation, any POST that creates something expensive</li><li>Correlation IDs: log aggregation across services (grep in Loki/Elasticsearch)</li><li>Trace IDs: latency debugging - which service is slow?</li></ul></th></tr></tbody></table></div>

## **2\. Database & Schema**

| **Q14** | **Walk me through database normalization - 1NF through 3NF with examples.** | **Database** |
| ------- | --------------------------------------------------------------------------- | ------------ |

Normalization eliminates data anomalies by organizing data into smaller, well-defined tables.

**1NF - First Normal Form**

Rule: each column holds atomic (indivisible) values; no repeating groups.

\-- BAD: items = "Pen, Notebook, Stapler" - multi-valued, non-atomic

orders(id, customer, items)

\-- GOOD:

orders(id, customer_id)

order_items(order_id, item_id, quantity)

**2NF - Second Normal Form**

Rule: 1NF AND every non-key column must depend on the ENTIRE primary key (no partial dependencies). Only applies when PK is composite.

\-- BAD: product_name depends only on product_id, not (order_id, product_id)

order_items(order_id, product_id, quantity, product_name)

\-- GOOD: move product_name to products table

order_items(order_id, product_id, quantity)

products(product_id, product_name, price)

**3NF - Third Normal Form**

Rule: 2NF AND no transitive dependencies (non-key column depending on another non-key column).

\-- BAD: dept_name depends on dept_id, not on emp_id

employees(emp_id, dept_id, dept_name)

\-- GOOD:

employees(emp_id, dept_id)

departments(dept_id, dept_name)

**When to denormalize**

Normalization is for write correctness. Denormalize for read performance: pre-aggregated stats tables, materialized views, duplicating a rarely-changing column to avoid joins in hot read paths.

| **Q15** | **How do you design a database schema for a multi-tenant SaaS application?** | **Database** |
| ------- | ---------------------------------------------------------------------------- | ------------ |

**Pattern 1: Shared schema (row-level tenancy)**

Add a tenant_id column to every table. Use PostgreSQL Row Level Security (RLS) to enforce isolation at the DB level.

ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON orders

USING (tenant_id = current_setting('app.tenant_id')::UUID);

Pros: cheapest, single schema to migrate. Cons: one misconfigured query leaks all tenants' data.

**Pattern 2: Schema-per-tenant**

Each tenant gets their own PostgreSQL schema. Connection pool routes via SET search_path TO tenant_abc. Strong isolation, easy per-tenant migrations. More management overhead.

**Pattern 3: Database-per-tenant**

Complete isolation. Required for compliance (SOC2, HIPAA). High cost. Use for enterprise tiers.

**Recommendation**

Shared schema + RLS for startup/growth stage. Schema-per-tenant when you hit compliance requirements. Database-per-tenant only for regulated/enterprise.

| **Q16** | **How do you handle database migrations in production without downtime?** | **Database** |
| ------- | ------------------------------------------------------------------------- | ------------ |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>The key is the expand-contract pattern (also called blue-green migrations).</p><p><strong>The 3 phases</strong></p><table><tbody><tr><th><p>Phase 1 - EXPAND (backward compatible):</p><p>- Add the new column/table as nullable</p><p>- Deploy code that writes to BOTH old and new column</p><p>- Backfill existing rows in batches (never in one transaction)</p><p>Phase 2 - MIGRATE:</p><p>- Verify backfill is complete</p><p>- Switch reads to the new column</p><p>Phase 3 - CONTRACT:</p><p>- Drop old column/table after you are confident</p></th></tr></tbody></table><p><strong>Concrete example: renaming a column</strong></p><table><tbody><tr><th><p>-- Step 1: add nullable column (no lock contention)</p><p>ALTER TABLE users ADD COLUMN full_name TEXT;</p><p>-- Step 2: backfill in batches</p><p>UPDATE users SET full_name = first_name || ' ' || last_name</p><p>WHERE id BETWEEN 0 AND 10000 AND full_name IS NULL;</p><p>-- Step 3: add NOT NULL AFTER backfill</p><p>ALTER TABLE users ALTER COLUMN full_name SET NOT NULL;</p><p>-- Step 4: drop old columns after new code is stable</p></th></tr></tbody></table><p><strong>Never do in production</strong></p><ul><li>DROP COLUMN or RENAME COLUMN with running traffic</li><li>Adding a NOT NULL column with no default (table rewrite = full lock)</li><li>Migrations inside application startup code</li></ul></th></tr></tbody></table></div>

| **Q17** | **Explain database indexing - when do you add an index and when is it harmful?** | **Database** |
| ------- | -------------------------------------------------------------------------------- | ------------ |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>An index is a separate data structure (usually B-tree) that lets the DB find rows without a full table scan.</p><p><strong>When to add an index</strong></p><ul><li>Columns in WHERE clauses that filter significantly (high cardinality)</li><li>Columns used in JOINs (foreign keys)</li><li>Columns in ORDER BY + LIMIT (the index already has sorted order)</li><li>Composite index for multi-column filters - put equality column first, range column last</li></ul><p><strong>Composite index column order</strong></p><table><tbody><tr><th><p>-- Query: WHERE tenant_id = ? AND created_at &gt; ?</p><p>-- Correct: INDEX ON (tenant_id, created_at)</p><p>-- Wrong: INDEX ON (created_at, tenant_id) - DB cannot use it efficiently</p></th></tr></tbody></table><p><strong>When an index is harmful</strong></p><ul><li>Tables with very high write throughput - every INSERT/UPDATE/DELETE must update all indexes</li><li>Low-cardinality columns (e.g., status with 3 values) - a full table scan may be faster</li><li>Small tables - optimizer will choose seq scan anyway</li></ul><p><strong>PostgreSQL-specific</strong></p><ul><li>Partial indexes: WHERE deleted_at IS NULL - only index active rows</li><li>Covering indexes: INCLUDE (email) - avoid a heap fetch entirely</li><li>EXPLAIN ANALYZE is your friend - look at actual vs estimated row counts</li></ul></th></tr></tbody></table></div>

| **Q18** | **What is the N+1 query problem and how do you solve it?** | **Database** |
| ------- | ---------------------------------------------------------- | ------------ |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>N+1 happens when you fetch N records and then execute 1 additional query per record to fetch related data.</p><table><tbody><tr><th><p>users = db.query("SELECT * FROM users LIMIT 100") // 1 query</p><p>for user in users:</p><p>orders = db.query("SELECT * FROM orders WHERE user_id = ?", user.id) // N queries</p><p>// Total: 101 queries for 100 users</p></th></tr></tbody></table><p><strong>Solutions</strong></p><ul><li>JOIN: fetch users and orders in a single query. Works well for 1:1 or small 1:many.</li><li>Batch loading: collect all user IDs, do one WHERE user_id IN (...) query, then map in-app. This is what DataLoader (GraphQL) does.</li></ul><table><tbody><tr><th><p>user_ids = [u.id for u in users]</p><p>orders = db.query("SELECT * FROM orders WHERE user_id = ANY(?)", user_ids)</p><p>orders_by_user = group_by(orders, lambda o: o.user_id)</p></th></tr></tbody></table><ul><li>Eager loading: ORMs like GORM/Sequelize have preload/include that do the batching automatically.</li></ul><p><strong>Detection</strong></p><p>Log slow query count per request. If you see 100+ queries for a single endpoint, it is almost certainly N+1. Tools like pganalyze or query-count middleware help catch this in CI.</p></th></tr></tbody></table></div>

| **Q19** | **What is a database transaction and what are isolation levels?** | **Database** |
| ------- | ----------------------------------------------------------------- | ------------ |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>A transaction is a unit of work that is Atomic, Consistent, Isolated, and Durable (ACID).</p><p><strong>The 4 isolation levels</strong></p><ul><li>Read Uncommitted: can read uncommitted changes. Dirty reads possible. Never use.</li><li>Read Committed: only reads committed data. Default in PostgreSQL. Prevents dirty reads but allows non-repeatable reads.</li><li>Repeatable Read: a row read twice in the same transaction returns the same value. PostgreSQL's RR also prevents phantoms via MVCC.</li><li>Serializable: transactions execute as if they ran one after another. Highest isolation, highest contention. Use for financial operations.</li></ul><p><strong>Read phenomena</strong></p><table><tbody><tr><th><p>Dirty Read: T1 reads T2's uncommitted write</p><p>Non-repeatable: T1 reads row, T2 updates, T1 reads again - different result</p><p>Phantom Read: T1 reads set of rows, T2 inserts matching row - new row appears</p></th></tr></tbody></table><p><strong>Practical choice</strong></p><ul><li>Read Committed: most CRUD operations</li><li>Repeatable Read: generating consistent reports or snapshots</li><li>Serializable: bank transfers, inventory deduction, any "check then act" pattern</li></ul></th></tr></tbody></table></div>

| **Q20** | **What is a database deadlock and how do you prevent it?** | **Database** |
| ------- | ---------------------------------------------------------- | ------------ |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>A deadlock occurs when two or more transactions are each waiting for a lock held by the other, and neither can proceed.</p><table><tbody><tr><th><p>Transaction A: Transaction B:</p><p>1. LOCK orders WHERE id = 1 ← 1. LOCK payments WHERE order_id = 1</p><p>2. Waiting for payments lock 2. Waiting for orders lock</p><p>DEADLOCK</p></th></tr></tbody></table><p><strong>Prevention strategies</strong></p><ul><li>Consistent lock order: always acquire locks in the same order across all transactions</li><li>Keep transactions short: the shorter a transaction holds locks, the less chance of conflict</li><li>Use SELECT FOR UPDATE to acquire locks early, rather than upgrading a read lock mid-transaction</li></ul><p><strong>Optimistic locking</strong></p><table><tbody><tr><th><p>SELECT id, version FROM accounts WHERE id = 123;</p><p>-- do work ...</p><p>UPDATE accounts SET balance = new_balance, version = version + 1</p><p>WHERE id = 123 AND version = original_version;</p><p>-- 0 rows updated → someone else changed it → retry</p></th></tr></tbody></table></th></tr></tbody></table></div>

| **Q21** | **What is sharding and what are the common sharding strategies?** | **Database** |
| ------- | ----------------------------------------------------------------- | ------------ |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>Sharding splits data across multiple databases (shards) to scale writes and storage beyond what a single node can handle. Only after exhausting: vertical scaling, read replicas, caching, query optimization.</p><p><strong>Sharding strategies</strong></p><ul><li>Range sharding: shard by value range (users 1-1M on shard 1). Simple, good for range queries. Problem: hotspots on recent data.</li><li>Hash sharding: shard_id = hash(user_id) % num_shards. Even distribution. Problem: range queries are expensive.</li><li>Directory sharding: lookup table maps key → shard. Maximum flexibility. Problem: directory is a bottleneck.</li><li>Consistent hashing: shards on a ring; keys map to nearest shard. Adding/removing a shard moves only ~1/N keys. Used by Cassandra, Redis Cluster.</li></ul><p><strong>Shard key choice</strong></p><p>Must be: high cardinality (not gender), uniformly distributed, present in most queries, immutable (or moving data between shards is expensive).</p><p><strong>Cross-shard queries</strong></p><p>The biggest pain point. Aggregate queries require scatter-gather (query all shards, merge results), or maintain a separate denormalized analytics DB.</p></th></tr></tbody></table></div>

| **Q22** | **How do database views, materialized views, and CTEs differ?** | **Database** |
| ------- | --------------------------------------------------------------- | ------------ |

**View**

A stored SQL query that you query like a table. No data is stored - every query against the view reruns the underlying SQL.

CREATE VIEW active_users AS

SELECT id, email FROM users WHERE deleted_at IS NULL;

**Materialized View**

Like a view, but the result is physically stored and periodically refreshed. Very fast reads. Tradeoff: data may be stale.

CREATE MATERIALIZED VIEW monthly_revenue AS

SELECT date_trunc('month', created_at) as month, sum(amount)

FROM orders GROUP BY 1;

REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue;

**CTE (Common Table Expression)**

A named subquery defined in the same statement using WITH. Scoped to the single query - not stored anywhere. Makes complex queries readable.

WITH ranked_users AS (

SELECT \*, ROW_NUMBER() OVER (PARTITION BY country ORDER BY revenue DESC) as rank

FROM users

)

SELECT \* FROM ranked_users WHERE rank <= 10;

## **3\. Distributed Systems**

| **Q23** | **Explain CAP theorem and how it affects your design decisions.** | **Distributed** |
| ------- | ----------------------------------------------------------------- | --------------- |

CAP states that a distributed system can guarantee at most 2 of: Consistency, Availability, Partition Tolerance. Since network partitions will happen, the real choice is: during a partition, do you prefer Consistency (CP) or Availability (AP)?

**CP systems**

When a partition occurs, refuse to serve stale data. Return an error instead. Examples: ZooKeeper, etcd, traditional RDBMS with synchronous replication. Use when: financial systems, inventory deduction, leader election.

**AP systems**

When a partition occurs, continue serving - possibly returning stale data. Examples: Cassandra, DynamoDB, Redis cluster. Use when: user feeds, product catalogs, caches.

**PACELC (the better model)**

Even without partitions, there is a tradeoff between latency and consistency. PA/EL (Cassandra) vs PC/EC (Spanner-like systems).

| **Q24** | **What is the Saga pattern and how does it compare to 2-Phase Commit?** | **Distributed** |
| ------- | ----------------------------------------------------------------------- | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>2-Phase Commit (2PC)</strong></p><table><tbody><tr><th><p>Phase 1 - Prepare: coordinator asks all participants "can you commit?"</p><p>Phase 2 - Commit: if all say yes → commit; else → rollback</p></th></tr></tbody></table><p>Problems: blocking protocol (coordinator failure leaves participants stuck), single point of failure, high latency.</p><p><strong>Saga pattern</strong></p><p>A saga is a sequence of local transactions, each publishing an event that triggers the next. If a step fails, compensating transactions undo previous steps.</p><table><tbody><tr><th><p>Order Saga (choreography):</p><p>1. OrderService: create order → publish OrderCreated</p><p>2. PaymentService: charge card → publish PaymentSucceeded</p><p>(on failure: publish PaymentFailed → OrderService cancels)</p><p>3. InventoryService: reserve stock → publish StockReserved</p><p>(on failure: PaymentService refunds, OrderService cancels)</p></th></tr></tbody></table><p><strong>Two Saga styles</strong></p><ul><li>Choreography: each service listens to events and reacts. Simple but hard to visualize.</li><li>Orchestration: a central saga orchestrator directs each service and tracks state. Explicit, easier to debug. Preferred for complex flows.</li></ul><p>Key insight: Sagas are eventually consistent - design your UI around this (show "payment pending" state, not a hard lock).</p></th></tr></tbody></table></div>

| **Q25** | **How do you design a system to handle exactly-once message delivery?** | **Distributed** |
| ------- | ----------------------------------------------------------------------- | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>True exactly-once delivery at the infrastructure level is extremely hard. The practical solution is idempotent consumers.</p><p><strong>Kafka's semantics</strong></p><ul><li>At-most-once: auto-commit offsets before processing. Messages can be lost on crash.</li><li>At-least-once: commit only after processing. Messages can be replayed → duplicates possible.</li><li>Exactly-once: Kafka transactions + idempotent producer. Works end-to-end only within Kafka.</li></ul><p><strong>Idempotent consumer pattern (practical solution)</strong></p><table><tbody><tr><th><p>func processMessage(msg Message) error {</p><p>exists, _ := redis.Get("processed:" + msg.ID)</p><p>if exists { return nil } // already done</p><p>err := doBusinessLogic(msg)</p><p>if err != nil { return err } // will be retried</p><p>redis.SetEX("processed:" + msg.ID, 86400, "1")</p><p>return nil</p><p>}</p></th></tr></tbody></table><p><strong>Transactional outbox pattern</strong></p><p>Write the event to an outbox table in the same DB transaction as the business data. A separate poller reads from the outbox and publishes to Kafka. Guarantees the event is published exactly once even if the app crashes mid-write.</p></th></tr></tbody></table></div>

| **Q26** | **How do you implement distributed rate limiting across multiple instances?** | **Distributed** |
| ------- | ----------------------------------------------------------------------------- | --------------- |

Local in-memory rate limiting is useless when you have 10 instances - each instance only sees 1/10 of the traffic.

**Centralized counter with Redis (Lua for atomicity)**

local key = KEYS\[1\]

local now = tonumber(ARGV\[1\])

local window = tonumber(ARGV\[2\])

local limit = tonumber(ARGV\[3\])

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

local count = redis.call('ZCARD', key)

if count >= limit then return 0 end -- rate limited

redis.call('ZADD', key, now, now .. math.random())

redis.call('EXPIRE', key, window)

return 1 -- allowed

**Sliding window with two counters**

Keep a counter for the current window and previous window. Estimate current count as: prev_count × (1 - elapsed/window) + curr_count. Gives an approximation without storing per-request timestamps.

| **Q27** | **What is a circuit breaker and when do you use it?** | **Distributed** |
| ------- | ----------------------------------------------------- | --------------- |

A circuit breaker prevents cascading failures by detecting that a downstream service is unhealthy and stopping calls to it temporarily.

**The three states**

CLOSED (normal):

Requests flow through. Track failure rate.

If failures > threshold (e.g., 50% in 60s): → OPEN

OPEN (tripped):

All requests fail immediately (no network call).

Wait for reset_timeout (e.g., 30s): → HALF-OPEN

HALF-OPEN (probing):

Allow limited test requests.

If success: → CLOSED If failure: → OPEN

**Go implementation**

cb := gobreaker.NewCircuitBreaker(gobreaker.Settings{

Name: "payment-service",

MaxRequests: 3,

Interval: 60 \* time.Second,

Timeout: 30 \* time.Second,

ReadyToTrip: func(counts gobreaker.Counts) bool {

return counts.ConsecutiveFailures > 5

},

})

Combine with: retry (exponential backoff for transient errors) + circuit breaker (persistent failures) + timeout (prevent indefinite blocking). These three form a resilience layer.

| **Q28** | **How do you design a distributed cache and what cache invalidation strategies do you know?** | **Distributed** |
| ------- | --------------------------------------------------------------------------------------------- | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Cache-aside (Lazy loading)</strong></p><table><tbody><tr><th><p>value = cache.get(key)</p><p>if not value:</p><p>value = db.query(...)</p><p>cache.set(key, value, ttl=300)</p><p>return value</p></th></tr></tbody></table><p><strong>Write-through</strong></p><p>Every write to DB also writes to cache. Cache is always warm. Problem: write latency increases; cache filled with data that may never be read.</p><p><strong>Write-behind (Write-back)</strong></p><p>Write to cache only; async write to DB later. Best performance but risk of data loss if cache crashes.</p><p><strong>Invalidation strategies</strong></p><ul><li>TTL-based: simplest. Accept eventual consistency within the TTL window.</li><li>Event-driven: on DB write, publish an invalidation event; cache subscriber deletes the key.</li><li>Cache tags: associate keys with tags. Invalidate all keys with a tag atomically.</li></ul><p><strong>Cache stampede</strong></p><p>When a hot key expires, thousands of requests hit the DB simultaneously. Solutions: probabilistic early expiration; mutex/lock on cache miss so only one request populates the cache.</p></th></tr></tbody></table></div>

| **Q29** | **What is service discovery and how does it work in Kubernetes?** | **Distributed** |
| ------- | ----------------------------------------------------------------- | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Client-side vs server-side</strong></p><ul><li>Client-side: client queries a registry (Consul, etcd), gets a list of instances, picks one. Client does the work.</li><li>Server-side: client sends to a single endpoint (load balancer); the LB discovers and routes. Client is dumb.</li></ul><p><strong>Kubernetes service discovery</strong></p><table><tbody><tr><th><p>Service: payment-service (ClusterIP: 10.96.0.10)</p><p>→ Routes to pods matching selector: app=payment-service</p><p>// DNS-based (automatic):</p><p>payment-service.default.svc.cluster.local:8080</p><p>// Any pod in the cluster can resolve this</p></th></tr></tbody></table><p>CoreDNS resolves service names to ClusterIP. kube-proxy maintains iptables rules routing ClusterIP → pod IPs. Endpoints object tracks healthy pod IPs; updated when pods start/stop. Readiness probes ensure traffic only goes to ready pods.</p><p>In practice: just use Kubernetes Service names as hostnames. Your Go service connects to http://payment-service:8080 - Kubernetes handles the rest.</p></th></tr></tbody></table></div>

| **Q30** | **How do you implement graceful shutdown in a service?** | **Distributed** |
| ------- | -------------------------------------------------------- | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>Graceful shutdown means: stop accepting new work, finish in-flight work, then exit cleanly. Kubernetes sends SIGTERM before killing a pod.</p><p><strong>Go implementation</strong></p><table><tbody><tr><th><p>func main() {</p><p>server := &amp;http.Server{Addr: ":8080", Handler: mux}</p><p>go func() {</p><p>if err := server.ListenAndServe(); err != http.ErrServerClosed {</p><p>log.Fatal(err)</p><p>}</p><p>}()</p><p>quit := make(chan os.Signal, 1)</p><p>signal.Notify(quit, syscall.SIGTERM, syscall.SIGINT)</p><p>&lt;-quit</p><p>ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)</p><p>defer cancel()</p><p>server.Shutdown(ctx)</p><p>db.Close()</p><p>kafkaProducer.Flush(5000)</p><p>kafkaProducer.Close()</p><p>}</p></th></tr></tbody></table><p><strong>Kubernetes considerations</strong></p><ul><li>Set terminationGracePeriodSeconds in pod spec to match your shutdown timeout</li><li>A short sleep after receiving SIGTERM helps because there is a propagation delay before pod is removed from endpoints</li><li>For Kafka consumers: commit offsets of in-flight messages before shutdown; they will be reprocessed on restart (idempotent consumer handles this)</li></ul></th></tr></tbody></table></div>

| **Q31** | **What is the outbox pattern and how does it solve dual writes?** | **Distributed** |
| ------- | ----------------------------------------------------------------- | --------------- |

The dual write problem: you need to write to your DB AND publish an event to Kafka atomically. If your process crashes between the two writes, you have inconsistency.

**The wrong approach**

// BAD: non-atomic dual write

db.Exec("UPDATE orders SET status = 'confirmed'")

kafka.Publish("order.confirmed", orderEvent) // crashes here? event never sent

**Outbox pattern**

// GOOD: write event to outbox table in SAME transaction

BEGIN;

UPDATE orders SET status = 'confirmed' WHERE id = ?;

INSERT INTO outbox (id, topic, payload, created_at)

VALUES (uuid(), 'order.confirmed', json(orderEvent), now());

COMMIT;

// Separate process: polls outbox, publishes to Kafka, then deletes row

**Alternative: CDC (Change Data Capture)**

Debezium reads the PostgreSQL WAL and publishes every DB change as a Kafka event. No outbox table needed - the transaction log IS the outbox. Powerful but more infrastructure.

| **Q32** | **What is a health check? How should you design readiness vs liveness probes?** | **Distributed** |
| ------- | ------------------------------------------------------------------------------- | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Liveness probe</strong></p><p>"Is this process alive? Should Kubernetes restart it?" If it fails: container is killed and restarted.</p><table><tbody><tr><th><p>GET /health/live → 200 OK { "status": "ok" }</p><p>// Only check: can the HTTP server handle a request?</p><p>// Do NOT check DB connectivity - a DB outage should not restart all pods</p></th></tr></tbody></table><p><strong>Readiness probe</strong></p><p>"Is this instance ready to receive traffic?" If it fails: pod is removed from service endpoints, no new requests sent. Container is NOT restarted.</p><table><tbody><tr><th><p>GET /health/ready</p><p>// Check: DB connection works, Redis connected, cache warmed up</p><p>→ 503 if not ready</p><p>→ 200 OK when ready</p></th></tr></tbody></table><p><strong>Design guidelines</strong></p><ul><li>Liveness: return 200 if the process is alive. Do not check dependencies.</li><li>Readiness: check critical dependencies with short timeouts. Return 503 with detail if critical dependency is down.</li><li>Never make readiness dependent on non-critical external services</li></ul></th></tr></tbody></table></div>

## **4\. Performance & Latency**

| **Q33** | **How do you debug the latency of a slow API endpoint?** | **Performance** |
| ------- | -------------------------------------------------------- | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Step 1: Reproduce and isolate</strong></p><ul><li>Is it slow for all users or specific users/tenants?</li><li>Did latency spike after a deploy (code change) or gradually (data growth)?</li><li>Is it consistently slow or intermittently slow?</li></ul><p><strong>Step 2: Distributed tracing</strong></p><table><tbody><tr><th><p>Request (total: 2100ms)</p><p>├── Middleware auth check (8ms)</p><p>├── DB query 1: fetch user (12ms)</p><p>├── DB query 2: fetch orders (1800ms) ← HOT SPOT</p><p>├── External API call (200ms)</p><p>└── Response serialization (80ms)</p></th></tr></tbody></table><p><strong>Step 3: Database query analysis</strong></p><ul><li>EXPLAIN ANALYZE the slow query</li><li>Look for: Seq Scan on large table, sort without index, high actual vs estimated rows</li><li>Check pg_stat_statements for query patterns and total time</li><li>Check for lock waits: pg_locks, pg_blocking_pids()</li></ul><p><strong>Step 4: Infrastructure layer</strong></p><ul><li>Network latency between services (especially cross-AZ calls)</li><li>Connection pool exhaustion (requests queuing for a connection)</li><li>CPU throttling in Kubernetes (CPU limits cause invisible throttling)</li></ul><p><strong>Step 5: Application code</strong></p><ul><li>N+1 queries (log query count per request)</li><li>Synchronous calls that could be parallelized</li><li>Large JSON serialization (benchmark with pprof)</li></ul></th></tr></tbody></table></div>

| **Q34** | **How do you optimize a system that is hitting its throughput limit?** | **Performance** |
| ------- | ---------------------------------------------------------------------- | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>First, find the bottleneck (Little's Law: throughput = concurrency / latency). Do not optimize before profiling.</p><p><strong>Identify the bottleneck</strong></p><ul><li>CPU-bound: CPU at 100%, latency scales linearly with load</li><li>I/O-bound: high wait time, CPU low; look at DB, network, disk</li><li>Concurrency-bound: connection pool exhausted, thread pool full</li></ul><p><strong>CPU-bound solutions</strong></p><ul><li>Horizontal scaling (more instances)</li><li>Profile hot functions (pprof in Go) and optimize algorithms</li><li>Reduce serialization overhead (use protobuf instead of JSON for internal calls)</li></ul><p><strong>I/O-bound solutions</strong></p><ul><li>Cache frequently read data (Redis)</li><li>Use read replicas for read-heavy workloads</li><li>Batch writes (buffer and flush vs one-by-one inserts)</li></ul><p><strong>Architecture-level</strong></p><ul><li>Move expensive work to async (publish to Kafka, process in background)</li><li>Shard by tenant/user ID to distribute load</li><li>Use a CDN for static assets and cacheable API responses</li></ul></th></tr></tbody></table></div>

| **Q35** | **How do you profile a Go application in production?** | **Performance** |
| ------- | ------------------------------------------------------ | --------------- |

Go has excellent built-in profiling via pprof.

**Expose pprof endpoint**

import \_ "net/http/pprof"

go func() {

log.Fatal(http.ListenAndServe(":6060", nil))

}()

**Common profiles**

go tool pprof <http://localhost:6060/debug/pprof/profile?seconds=30> // CPU

go tool pprof <http://localhost:6060/debug/pprof/heap> // Memory

go tool pprof <http://localhost:6060/debug/pprof/goroutine> // Goroutine leaks

go tool pprof <http://localhost:6060/debug/pprof/block> // Blocking

go tool pprof <http://localhost:6060/debug/pprof/mutex> // Mutex contention

**In pprof interactive mode**

(pprof) web // opens SVG flame graph in browser

(pprof) top10 // top 10 functions by CPU/mem

(pprof) list FuncName // annotated source

CPU profiling has ~5% overhead. Short (5-10s) profiles are safe in prod. For continuous profiling, use Pyroscope or Datadog's continuous profiler.

| **Q36** | **What is connection pooling and why does it matter?** | **Performance** |
| ------- | ------------------------------------------------------ | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>Creating a new DB connection is expensive: TCP handshake, authentication, SSL negotiation - can take 20-50ms. A connection pool reuses existing connections.</p><p><strong>How it works</strong></p><table><tbody><tr><th><p>Pool initialization:</p><p>min connections: pre-created, always ready</p><p>max connections: cap on total concurrent connections</p><p>Request flow:</p><p>1. App requests a connection from pool</p><p>2. Idle connection available: return immediately</p><p>3. Pool not full: create new connection</p><p>4. Pool full: queue request (with timeout)</p><p>5. After use: return to pool (do not close)</p></th></tr></tbody></table><p><strong>PgBouncer modes</strong></p><ul><li>Session mode: connection assigned for entire client session. No benefit for short queries.</li><li>Transaction mode: connection assigned per transaction only. Best multiplexing. Note: prepared statements and advisory locks do not work across transactions.</li></ul><p><strong>Scale impact</strong></p><p>PostgreSQL has a process per connection. With PgBouncer: 5000 app connections → 100 real DB connections. In Go: set db.SetMaxOpenConns, SetMaxIdleConns, SetConnMaxLifetime.</p></th></tr></tbody></table></div>

| **Q37** | **What is tail latency and why is p99 more important than average latency?** | **Performance** |
| ------- | ---------------------------------------------------------------------------- | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>The problem with averages</strong></p><p>If 99% of requests take 10ms and 1% take 10 seconds, your average is ~110ms - looks fine. But 1% of requests means millions of users at scale.</p><p><strong>Percentile latencies</strong></p><ul><li>p50: median - half of requests are faster than this</li><li>p95: 95% of requests are faster than this</li><li>p99: 99% of requests are faster than this</li><li>p999: 99.9% - critical for financial/safety systems</li></ul><p><strong>Why tail latency matters more at scale</strong></p><p>In a system where a user request fans out to 100 microservices, the user waits for the SLOWEST response. If each service has 1% chance of being slow, the probability that at least one is slow = 1 - (0.99)^100 ≈ 63%.</p><p><strong>Common causes of high tail latency</strong></p><ul><li>GC pauses</li><li>Lock contention - some requests wait while others hold a lock</li><li>Hot partitions - some DB rows or cache keys get much more traffic</li><li>Connection pool exhaustion - unlucky requests queue for a connection</li><li>CPU throttling in Kubernetes (CPU limits cause invisible throttling)</li></ul><p><strong>Hedged requests</strong></p><p>If a request to a backend has not returned within p95 time, send a duplicate request to a second instance. Accept whichever returns first. Cancel the other. Reduces p99 at the cost of slightly higher backend load.</p></th></tr></tbody></table></div>

| **Q38** | **What is horizontal vs vertical scaling? When do you choose each?** | **Performance** |
| ------- | -------------------------------------------------------------------- | --------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Vertical scaling (scale up)</strong></p><p>Give the existing server more resources. Simpler - no application changes needed. Pros: no distributed systems complexity. Cons: hardware limits, single point of failure, requires downtime to resize.</p><p><strong>Horizontal scaling (scale out)</strong></p><p>Add more instances of the service. Requires the application to be stateless. Pros: theoretically unlimited scale, redundancy. Cons: distributed systems complexity, stateful components (DB, cache) become bottlenecks.</p><p><strong>Database horizontal scaling</strong></p><ul><li>Read replicas: scale reads horizontally</li><li>Sharding: partition data across multiple primaries - high complexity, only when vertical + replicas are not enough</li><li>CQRS with a separate read store (Elasticsearch, Redis) for specific query patterns</li></ul></th></tr></tbody></table></div>

## **5\. Software Design**

| **Q39** | **How do you approach system design for a new feature from scratch?** | **Sys Design** |
| ------- | --------------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>1. Clarify requirements (the most important step)</strong></p><ul><li>What is the user/system goal? What problem does this solve?</li><li>Who are the users and what scale do we expect? (DAU, QPS, data volume)</li><li>What are the latency/consistency/availability requirements?</li><li>What is explicitly in scope and out of scope?</li></ul><p><strong>2. Define the data model first</strong></p><p>The data model is the foundation. If you get it wrong, everything built on it is wrong. Identify entities, relationships, and access patterns (read-heavy vs write-heavy, hot keys, fan-out).</p><p><strong>3. Design the API contract</strong></p><p>Before the internals. This is the interface your teammates depend on.</p><p><strong>4. High-level architecture</strong></p><p>Draw the boxes: clients, API gateway, services, queues, databases, caches. Identify data flows.</p><p><strong>5. Deep dive on the hardest part</strong></p><p>Every system has one tricky piece - scaling writes, real-time updates, consistency across services. Spend most design time here.</p><p><strong>6. Failure modes</strong></p><ul><li>What happens if service X goes down?</li><li>What happens if we lose a message?</li><li>What happens if we get a duplicate request?</li></ul></th></tr></tbody></table></div>

| **Q40** | **What is event-driven architecture and when would you use it?** | **Sys Design** |
| ------- | ---------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Core concepts</strong></p><ul><li>Event: an immutable record of something that happened (OrderPlaced, PaymentFailed)</li><li>Producer: publishes events without knowing who consumes them</li><li>Consumer: subscribes to event types and reacts</li><li>Broker: Kafka, RabbitMQ, Google Pub/Sub - the durable channel between them</li></ul><p><strong>When to use it</strong></p><ul><li>Decoupling services that do not need immediate responses</li><li>Fan-out: one event triggers many consumers (order placed → notify, invoice, fulfillment)</li><li>Audit logs and event sourcing</li><li>Handling traffic spikes - buffer in the queue, consumers process at their own pace</li></ul><p><strong>When NOT to use it</strong></p><ul><li>When you need an immediate response (login, checkout confirmation)</li><li>Simple CRUD apps - event-driven adds complexity without benefit</li></ul><p><strong>Tradeoffs to call out</strong></p><p>Eventual consistency. Harder to trace a request across services (need correlation IDs). Schema evolution must be backward-compatible. Testing is harder - you need to verify events were published with the right content.</p></th></tr></tbody></table></div>

| **Q41** | **What is the difference between microservices and a monolith? When do you prefer each?** | **Sys Design** |
| ------- | ----------------------------------------------------------------------------------------- | -------------- |

**Monolith**

Single deployable unit. All modules share a process and database. Pros: simple to develop, test, deploy, debug; low latency; ACID transactions across the entire domain. Cons: scales as a unit, deployment risk for unrelated changes, team coupling.

**Microservices**

Each service owns its domain, database, and deployment. Pros: independent scaling, deployment, team autonomy, technology flexibility. Cons: distributed systems complexity, network latency, no cross-service ACID transactions, operational overhead.

**Honest recommendation**

Start with a modular monolith. Extract services when you have: (a) a team ownership boundary, (b) a scaling bottleneck, (c) a compliance boundary. Do not microservice-ify prematurely.

**Modular monolith**

Strict module boundaries within one codebase and one deployment. Each module owns its schema (separate tables, no cross-module joins). Extract as a service later when justified - the module boundary already gives you the interface.

| **Q42** | **How do you design a feature flag system?** | **Sys Design** |
| ------- | -------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Core data model</strong></p><table><tbody><tr><th><p>flags: id, name, description, enabled (global kill switch)</p><p>flag_rules: flag_id, rule_type, value, percentage</p><p>// rule_type: user_id, tenant_id, percentage_rollout</p></th></tr></tbody></table><p><strong>Evaluation logic</strong></p><table><tbody><tr><th><p>func IsEnabled(flagName string, ctx EvalContext) bool {</p><p>flag := getFlag(flagName)</p><p>if !flag.Enabled { return false }</p><p>for _, rule := range flag.Rules {</p><p>switch rule.Type {</p><p>case "user_id":</p><p>if ctx.UserID == rule.Value { return true }</p><p>case "percentage":</p><p>// Stable: same user always gets same result</p><p>bucket := stableHash(ctx.UserID, flagName) % 100</p><p>if bucket &lt; rule.Percentage { return true }</p><p>}</p><p>}</p><p>return false</p><p>}</p></th></tr></tbody></table><p><strong>Key design decisions</strong></p><ul><li>Stable bucketing: same user always gets the same flag value - use a hash, not random</li><li>Cache flags: flags are read on every request. Cache in memory with a short TTL (30s).</li><li>Gradual rollout: start at 1%, watch error rates, then 10%, 50%, 100%</li><li>Kill switch pattern: flag is on by default; flip it off in incidents</li></ul></th></tr></tbody></table></div>

| **Q43** | **What is synchronous vs asynchronous communication in microservices?** | **Sys Design** |
| ------- | ----------------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Synchronous (request-response)</strong></p><p>Service A calls Service B and waits for a response. HTTP/REST, gRPC. Pros: simple, immediate consistency, easy error handling. Cons: temporal coupling (B must be up for A to work), cascading failures.</p><p><strong>Asynchronous (message-based)</strong></p><p>Service A publishes an event; Service B processes it later. Kafka, RabbitMQ. Pros: temporal decoupling, better resilience, absorbs traffic spikes. Cons: eventual consistency, harder to debug, complex error handling.</p><p><strong>When to use which</strong></p><ul><li>Sync: login, checkout confirmation, user-facing queries that need immediate answers</li><li>Async: sending emails, updating analytics, syncing to external systems</li></ul><p><strong>Hybrid: async request-response</strong></p><p>POST /export returns 202 + job_id. Client polls or subscribes to SSE for completion. Best of both worlds.</p></th></tr></tbody></table></div>

| **Q44** | **How do you handle secrets and configuration management in production?** | **Sys Design** |
| ------- | ------------------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Never do</strong></p><ul><li>Hardcode secrets in source code (they end up in git history permanently)</li><li>Commit .env files with real values</li><li>Pass secrets as Docker CMD arguments (visible in docker ps and logs)</li></ul><p><strong>Secret management options</strong></p><ul><li>Kubernetes Secrets: base64-encoded (not encrypted by default). Enable encryption at rest via KMS.</li><li>GCP Secret Manager / AWS Secrets Manager / HashiCorp Vault: secrets stored encrypted, accessed via API with IAM authentication. Support secret rotation, audit logs, versioning.</li><li>External Secrets Operator: syncs secrets from Vault/GCP Secret Manager into Kubernetes Secrets automatically.</li></ul><p><strong>Principle of least privilege</strong></p><p>Each service should only have access to the secrets it needs. Do not give the frontend service access to the DB password.</p><p><strong>Secret rotation</strong></p><ul><li>Design services to reload secrets without restart (poll Secret Manager periodically)</li><li>Use short-lived credentials where possible (GCP Workload Identity, AWS IAM Roles for Service Accounts)</li><li>Configuration vs secrets: non-sensitive config (feature flags, URLs, timeouts) goes in ConfigMaps. Secrets go in a secret store. Never conflate them.</li></ul></th></tr></tbody></table></div>

## **6\. Debugging**

| **Q45** | **How do you approach debugging a production issue you've never seen before?** | **Debugging** |
| ------- | ------------------------------------------------------------------------------ | ------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>1. Contain first, fix second</strong></p><p>If users are impacted: can I roll back? Can I feature-flag this off? Mitigation first, root cause second.</p><p><strong>2. Gather evidence</strong></p><ul><li>When did it start? (correlate with deploys, config changes, traffic spikes)</li><li>How many users/requests are affected? What is the blast radius?</li><li>What changed? (deployment, config, traffic pattern, upstream dependency)</li><li>What do the logs say? Look for the FIRST error, not the cascade that follows.</li></ul><p><strong>3. Form a hypothesis</strong></p><p>Based on evidence, form ONE specific hypothesis. Do not fix five things at once - you will not know what worked.</p><p><strong>4. Test the hypothesis</strong></p><p>Find evidence that confirms or refutes it WITHOUT making changes first. Only then make one targeted fix.</p><p><strong>5. Fix, verify, document</strong></p><p>Make one targeted change. Monitor for 10 minutes. Write a postmortem: what happened, why, what we changed, what prevents it in future. The postmortem is as valuable as the fix.</p></th></tr></tbody></table></div>

| **Q46** | **How do you debug a memory leak in a production Go service?** | **Debugging** |
| ------- | -------------------------------------------------------------- | ------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Signs of a memory leak</strong></p><ul><li>Memory grows monotonically over hours/days and never releases</li><li>Eventually OOMKilled by Kubernetes</li></ul><p><strong>Step 1: Confirm it is a leak</strong></p><p>Plot memory usage over time. If it grows unboundedly, it is a leak. If it is high but stable, it is a sizing issue.</p><p><strong>Step 2: Heap profile</strong></p><table><tbody><tr><th><p>go tool pprof http://localhost:6060/debug/pprof/heap</p><p>(pprof) top // what is holding most memory?</p><p>(pprof) list PackageName.FunctionName</p></th></tr></tbody></table><p><strong>Common causes in Go</strong></p><ul><li>Goroutine leak: goroutines that never exit (blocked on channel with no writer/reader). Check /debug/pprof/goroutine - if count grows, you have a goroutine leak. Fix: always pass context with cancellation.</li><li>Unbounded cache: in-memory map that grows forever. Fix: add eviction (LRU cache, TTL).</li><li>HTTP response body not closed: resp.Body.Close() must always be called.</li><li>Timer not stopped: time.After in a loop creates a new timer every iteration. Use time.NewTimer and Reset/Stop.</li><li>Reference held in slice: s = s[1:] does not release the backing array.</li></ul></th></tr></tbody></table></div>

| **Q47** | **How do you add observability to a microservices system?** | **Debugging** |
| ------- | ----------------------------------------------------------- | ------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Logs - the "what happened"</strong></p><ul><li>Structured logging (JSON) always - grep on free text does not scale</li><li>Every log entry: timestamp, level, service, trace_id, span_id, message + structured fields</li><li>Log levels: ERROR (page-worthy), WARN (investigate soon), INFO (normal events), DEBUG (dev only)</li></ul><table><tbody><tr><th><p>logger.Info("payment processed",</p><p>"payment_id", p.ID,</p><p>"amount", p.Amount,</p><p>"tenant_id", p.TenantID,</p><p>"duration_ms", elapsed.Milliseconds())</p></th></tr></tbody></table><p><strong>Metrics - the "how much/how often"</strong></p><ul><li>RED method: Rate (requests/sec), Errors (error rate), Duration (latency percentiles)</li><li>Track p50, p95, p99 latency - not just averages (averages hide tail latency)</li><li>Expose Prometheus metrics at /metrics; scrape with Prometheus, visualize in Grafana</li></ul><p><strong>Traces - the "where did time go"</strong></p><ul><li>OpenTelemetry SDK: instrument at service entry/exit and before/after external calls</li><li>Propagate trace context via HTTP headers (W3C traceparent)</li><li>Export to Jaeger, Tempo, or DataDog</li></ul><p><strong>Alerts</strong></p><p>Alert on symptoms (user impact), not causes. Error rate &gt; 1% is a symptom. High CPU is a cause - usually not worth waking someone up for.</p></th></tr></tbody></table></div>

| **Q48** | **How do you approach a race condition in concurrent code?** | **Debugging** |
| ------- | ------------------------------------------------------------ | ------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Detection</strong></p><table><tbody><tr><th><p>go test -race ./...</p><p>go run -race main.go</p></th></tr></tbody></table><p><strong>Common patterns and fixes in Go</strong></p><table><tbody><tr><th><p>// RACE: multiple goroutines write to map</p><p>var cache = make(map[string]int)</p><p>go func() { cache["key"] = 1 }()</p><p>go func() { cache["key"] = 2 }()</p><p>// FIX: use sync.RWMutex or sync.Map</p><p>var mu sync.RWMutex</p><p>mu.Lock()</p><p>cache["key"] = value</p><p>mu.Unlock()</p></th></tr></tbody></table><ul><li>Check-then-act: read a value, decide to act, but value changes between read and act. Fix: hold the lock across the check AND the act.</li><li>Closing a channel twice. Fix: only the sender closes channels; use sync.Once if multiple closers are possible.</li></ul><p><strong>Goroutine variable capture</strong></p><table><tbody><tr><th><p>// RACE: loop variable captured by goroutine</p><p>for _, v := range items {</p><p>go func() { process(v) }() // v is shared</p><p>}</p><p>// FIX: shadow with local copy</p><p>for _, v := range items {</p><p>v := v</p><p>go func() { process(v) }()</p><p>}</p></th></tr></tbody></table></th></tr></tbody></table></div>

| **Q49** | **How do you debug an intermittent failure you cannot reproduce locally?** | **Debugging** |
| ------- | -------------------------------------------------------------------------- | ------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Step 1: Make it observable in production</strong></p><ul><li>Add detailed logging around the failure path: log inputs, intermediate state, and outputs</li><li>Add a metric counter for every branch of the code path</li><li>Add distributed trace spans so you can see exactly where time is spent when it fails</li></ul><p><strong>Step 2: Characterize the failure</strong></p><ul><li>What % of requests fail? Is it time-based (only at night, only at peak)?</li><li>Is it correlated with a specific user, tenant, data shape, or request pattern?</li><li>Does it fail in one instance but not others? (State in one pod)</li><li>Is it correlated with another event (another service timing out, a batch job running)?</li></ul><p><strong>Step 3: Reproduce in controlled environment</strong></p><ul><li>Replay the exact input from logs against a staging environment</li><li>Add fault injection: artificially slow down or fail dependencies to reproduce race conditions</li><li>Write a load test that approximates production traffic patterns</li></ul><p><strong>Step 4: Hypothesis and verification</strong></p><p>Form one hypothesis. Add an assertion or log that would definitively confirm or deny it. Deploy and wait for the next occurrence. This is often the only way to debug true intermittent failures.</p></th></tr></tbody></table></div>

## **7\. Principles & Patterns**

| **Q50** | **Walk me through SOLID principles with concrete examples.** | **Principles** |
| ------- | ------------------------------------------------------------ | -------------- |

**S - Single Responsibility**

A class/module should have one reason to change. Split UserService into AuthService, EmailService, and UserRepository - each has one job.

**O - Open/Closed**

Open for extension, closed for modification. Define a PaymentProcessor interface; each payment provider implements it. Adding a new payment type = add a new struct, no modification to existing code.

**L - Liskov Substitution**

Subtypes must be substitutable for their base types without breaking behavior. Classic violation: Square "is-a" Rectangle but overriding SetWidth breaks the invariant that width and height are independent.

**I - Interface Segregation**

Clients should not depend on methods they do not use. Split a fat Worker interface (Work, Eat, Sleep) into Worker (Work) and Human (Work, Rest). A Robot should not be forced to implement Eat.

**D - Dependency Inversion**

// BAD: service directly instantiates DB

type OrderService struct { db \*PostgresDB }

// GOOD: depend on interface

type OrderRepository interface {

FindByID(id string) (\*Order, error)

}

type OrderService struct { repo OrderRepository }

| **Q51** | **What are design patterns - explain 5+ patterns you've used in production.** | **Principles** |
| ------- | ----------------------------------------------------------------------------- | -------------- |

**Repository pattern**

Abstracts data access. Your service talks to an interface; the concrete implementation hits PostgreSQL or a mock in tests.

**Factory pattern**

func NewProcessor(cfg Config) PaymentProcessor {

switch cfg.Provider {

case "stripe": return NewStripeProcessor(cfg.APIKey)

case "razorpay": return NewRazorpayProcessor(cfg.Secret)

}

return nil

}

**Observer / Pub-Sub pattern**

Publishers emit events; subscribers react. Decouples producers from consumers. Kafka is pub-sub at infrastructure scale. In-process: Go channels implement this naturally.

**Strategy pattern**

Define a family of algorithms, encapsulate each, make them interchangeable. Used in test automation tools - different script generation strategies per browser type, swappable without changing the caller.

**Circuit Breaker pattern**

State machine around a remote call that trips open when failure rate exceeds threshold. Prevents cascading failures.

**Outbox pattern**

Reliably publish events by writing to an outbox table in the same DB transaction as business data. A poller reads and publishes. Guarantees at-least-once delivery.

**BFF (Backend for Frontend) pattern**

Each client type (mobile, web, third-party) has its own API layer that aggregates and tailors responses. Avoids exposing internal microservice complexity to clients.

| **Q52** | **What is DRY vs WET vs AHA? When is code duplication acceptable?** | **Principles** |
| ------- | ------------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>DRY - Don't Repeat Yourself</strong></p><p>Every piece of knowledge should have a single authoritative representation. Not just code - also configuration, documentation, schema definitions.</p><p><strong>WET - Write Everything Twice</strong></p><p>The observation that premature abstraction is worse than duplication. Wait until you have written it a third time before abstracting.</p><p><strong>AHA - Avoid Hasty Abstractions</strong></p><p>Prefer duplication over the wrong abstraction. A wrong abstraction forces every future use case into a shape it does not fit, making code harder to change, not easier.</p><p><strong>When duplication is acceptable</strong></p><ul><li>The two pieces of code look similar but change for different reasons - coincidentally similar, not the same thing</li><li>You do not yet know what the abstraction should look like (wait for the third occurrence)</li><li>The abstraction would require so many parameters that it becomes harder to understand than the duplication</li><li>Tests - some duplication in tests is acceptable for readability and isolation</li></ul><p>Duplication is better than coupling. If sharing requires importing one service into another that should not know about it, keep the duplication.</p></th></tr></tbody></table></div>

| **Q53** | **Explain CQRS and Event Sourcing.** | **Principles** |
| ------- | ------------------------------------ | -------------- |

**CQRS - Command Query Responsibility Segregation**

Separate the write model (commands) from the read model (queries).

Write side: optimized for consistency

PlaceOrderCommand → OrderAggregate → orders table (normalized)

Read side: optimized for read performance

OrdersQuery → orders_view (denormalized, pre-joined)

→ or Elasticsearch index

Benefits: read and write sides can scale independently, read models shaped exactly to UI needs. Drawbacks: eventual consistency between models, more complexity to maintain.

**Event Sourcing**

Instead of storing current state, store every event that led to it.

// Traditional: store current balance

accounts: { id: 1, balance: 500 }

// Event sourcing: store events

events: \[

{ type: "AccountOpened", amount: 1000 },

{ type: "Withdrawn", amount: 300 },

{ type: "Deposited", amount: -200 },

\]

// Current state = replay all events

Benefits: complete audit trail, time-travel debugging, natural fit with CQRS. Drawbacks: replaying many events is slow (need snapshots), schema evolution for past events is hard.

| **Q54** | **What are the 12-Factor App principles and how do they affect your architecture?** | **Principles** |
| ------- | ----------------------------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Most impactful factors</strong></p><ul><li>Factor III - Config in environment: no hardcoded config. Everything that differs between environments is in environment variables. This is what makes Docker + Kubernetes deployments clean.</li><li>Factor IV - Backing services as attached resources: treat DB, Redis, Kafka as attached resources accessed via URL. Swap Postgres for RDS by changing an env var, not code.</li><li>Factor VI - Stateless processes: processes share nothing. No in-memory session state. Session data goes in Redis. This is what makes horizontal scaling trivial.</li><li>Factor IX - Disposability: fast startup, graceful shutdown. Handle SIGTERM, finish in-flight requests, release connections cleanly. Critical for Kubernetes rolling deployments.</li><li>Factor X - Dev/prod parity: dev environment should mirror prod. Use Docker Compose to run Postgres, Kafka, Redis locally instead of sqlite or in-memory fakes.</li></ul></th></tr></tbody></table></div>

| **Q55** | **What is dependency injection and why does it matter?** | **Principles** |
| ------- | -------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>Dependency injection means a component receives its dependencies from outside rather than creating them internally.</p><table><tbody><tr><th><p>// WITHOUT DI: creates its own dependency</p><p>type OrderService struct{}</p><p>func (s *OrderService) PlaceOrder(order Order) error {</p><p>db, _ := sql.Open("postgres", "hardcoded_conn_string")</p><p>...</p><p>}</p><p>// WITH DI: receives dependency</p><p>type OrderService struct {</p><p>repo OrderRepository</p><p>mailer Mailer</p><p>}</p><p>func NewOrderService(repo OrderRepository, mailer Mailer) *OrderService {</p><p>return &amp;OrderService{repo: repo, mailer: mailer}</p><p>}</p></th></tr></tbody></table><p><strong>Why it matters</strong></p><ul><li>Testability: inject mocks in tests, never need a real DB connection</li><li>Flexibility: swap Redis for Memcached by providing a different implementation of the same interface</li><li>Explicit dependencies: all dependencies visible in the constructor, no hidden globals</li></ul><p>In Go, DI is done manually (wire up in main.go) or with tools like google/wire. Manual DI is preferred for smaller services - it is explicit and the compiler catches everything.</p></th></tr></tbody></table></div>

| **Q56** | **What is eventual consistency and how do you handle it in the UI and backend?** | **Principles** |
| ------- | -------------------------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Where it comes from</strong></p><ul><li>Kafka consumer processing lag</li><li>Read replica replication lag</li><li>Distributed caches with TTL</li><li>Saga pattern - partial state between compensating transactions</li></ul><p><strong>Backend strategies</strong></p><ul><li>Read-your-writes consistency: after a write, route subsequent reads from the same user to the primary for a short window (e.g., 5s), then fall back to replica.</li><li>Monotonic reads: a user always reads from the same replica within a session. They will not see data go back in time.</li><li>Conditional reads: return a version/etag with data. Client sends it back; if server is behind, it can fetch from primary.</li></ul><p><strong>UI strategies</strong></p><ul><li>Optimistic updates: update the UI immediately on user action; roll back if the server returns an error.</li><li>Show pending state: display "Submitting..." or a "pending" badge on items being processed asynchronously.</li><li>Polling/SSE: poll the status endpoint or stream server-sent events until the operation is confirmed.</li></ul></th></tr></tbody></table></div>

| **Q57** | **What is clean architecture / hexagonal (ports and adapters) pattern?** | **Principles** |
| ------- | ------------------------------------------------------------------------ | -------------- |

Both address the same problem: business logic should not depend on infrastructure (DB, HTTP, message queue). Infrastructure should depend on business logic.

**Clean architecture**

Outer → Inner (dependency direction: always inward)

\[Frameworks & Drivers\] → \[Interface Adapters\] → \[Use Cases\] → \[Entities\]

\- Entities: pure business objects, no framework dependencies

\- Use Cases: application-specific business rules

\- Interface Adapters: controllers, repositories (implement ports)

\- Frameworks: HTTP, DB, message brokers

**Hexagonal / Ports and Adapters**

// Port (defined by core):

type PaymentGateway interface {

Charge(userID string, amount int) error

}

// Adapter (implements port):

type StripeAdapter struct { client \*stripe.Client }

func (s \*StripeAdapter) Charge(userID string, amount int) error { ... }

// Core does not import stripe - only knows about the port

You can swap Stripe for Razorpay by writing a new adapter. The business logic is framework-free and easily unit-testable.

| **Q58** | **What is immutability and why is it important in distributed systems?** | **Principles** |
| ------- | ------------------------------------------------------------------------ | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Why it matters in distributed systems</strong></p><ul><li>No cache invalidation needed: if a value never changes, cached copies are always valid</li><li>Safe to share across goroutines/threads without locks: no mutation = no race conditions</li><li>Reproducibility: given the same immutable inputs, a function always produces the same output</li><li>Event logs are naturally immutable: a Kafka log is an append-only sequence of immutable events</li></ul><p><strong>In code</strong></p><table><tbody><tr><th><p>// Instead of mutating:</p><p>user.status = "active"</p><p>// Return a new value:</p><p>activeUser := User{...user, Status: "active"}</p></th></tr></tbody></table><p><strong>Content-addressable storage</strong></p><p>Store data by hash of its content. If the content does not change, the hash does not change. Used by Docker image layers, Git (every commit is an immutable snapshot addressed by its hash).</p><p>Practical note: full immutability is not always practical for databases. The pattern is: make the mutation log immutable (event sourcing), even if the current state projection is mutable.</p></th></tr></tbody></table></div>

| **Q59** | **What is technical debt and when do you pay it down vs live with it?** | **Principles** |
| ------- | ----------------------------------------------------------------------- | -------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>Not all debt is equal</strong></p><ul><li>Deliberate prudent debt: "We know this is not the right approach, but we will refactor later." Legitimate - document it.</li><li>Deliberate reckless debt: "We do not have time for tests." Compounds fast.</li><li>Inadvertent debt: "We did not know better at the time." Fix it when you touch the code (Boy Scout rule).</li></ul><p><strong>When to pay it down</strong></p><ul><li>When it directly slows a current feature</li><li>When it causes incidents (reliability debt is the most expensive kind)</li><li>When onboarding new engineers takes more than 1 day to understand a subsystem</li><li>When the area is touched frequently (high-traffic code paths get more ROI from cleanup)</li></ul><p><strong>When to live with it</strong></p><ul><li>When the area is stable and rarely changed</li><li>When fixing it would be a large refactor with high risk and low business impact</li><li>When you are pre-product-market-fit (speed &gt; cleanliness)</li></ul><p>Track debt explicitly: a "tech debt" label in your issue tracker, a section in sprint planning for debt reduction (the 20% rule). Do not let it live only in engineers' heads.</p></th></tr></tbody></table></div>

## **8\. Messaging & Events**

| **Q60** | **How does Kafka work and when do you choose it over RabbitMQ?** | **Messaging** |
| ------- | ---------------------------------------------------------------- | ------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p><strong>How Kafka works</strong></p><ul><li>Topics are split into partitions; each partition is an ordered, immutable log</li><li>Producers append to the end; consumers read at their own offset</li><li>Offsets are committed by consumers - if a consumer crashes, it restarts from its last committed offset</li><li>Consumer groups: each partition is consumed by exactly one consumer in the group, giving parallelism</li><li>Messages are retained for a configurable period (e.g., 7 days) regardless of consumption - multiple consumer groups can independently read the same topic</li></ul><p><strong>Kafka vs RabbitMQ</strong></p><ul><li>RabbitMQ: messages are deleted after consumption (queue semantics). Best for task queues where each message needs to be processed once.</li><li>Kafka: messages are retained; multiple consumers can replay. Best for: event streaming, audit logs, event sourcing, data pipelines, fan-out to many consumers.</li></ul><p><strong>Partitioning strategy</strong></p><ul><li>Use tenant_id or user_id as key if you need ordered processing per tenant/user</li><li>Using a constant key = all messages go to one partition = no parallelism</li></ul><p><strong>Consumer group lag</strong></p><p>The most important Kafka operational metric. Lag = latest offset - consumer offset. If lag is growing, your consumers are not keeping up. Scale out consumers (up to the number of partitions).</p></th></tr></tbody></table></div>

| **Q61** | **How do you design a dead letter queue and why does it matter?** | **Messaging** |
| ------- | ----------------------------------------------------------------- | ------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>A dead letter queue (DLQ) captures messages that fail processing after all retries, so they do not block the main queue or get silently lost.</p><p><strong>DLQ design</strong></p><table><tbody><tr><th><p>Main Topic → Consumer → ProcessMessage()</p><p>↓ on failure</p><p>Retry (up to N times, exponential backoff)</p><p>↓ still failing</p><p>Dead Letter Topic (DLQ)</p><p>↓</p><p>Alert + Dashboard for manual inspection</p></th></tr></tbody></table><p><strong>Retry strategy</strong></p><ul><li>Distinguish between transient errors (DB connection timeout - retry) and permanent errors (invalid data format - DLQ immediately)</li><li>Exponential backoff: 1s, 2s, 4s, 8s, ... up to max (30s)</li><li>Jitter: add randomness to backoff to avoid thundering herd on recovery</li></ul><p><strong>DLQ operations</strong></p><ul><li>Store original message + error metadata (exception, stack trace, attempt count, timestamps)</li><li>Build a replay tool: after fixing the bug, replay DLQ messages back to the main topic</li><li>Alert on DLQ size crossing a threshold</li></ul></th></tr></tbody></table></div>

| **Q62** | **Explain backpressure in streaming systems.** | **Messaging** |
| ------- | ---------------------------------------------- | ------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>Backpressure is a mechanism for a consumer to signal to a producer that it cannot keep up with the current rate, causing the producer to slow down.</p><p><strong>The problem without backpressure</strong></p><p>Producer (fast) → Consumer (slow). Without backpressure: messages queue up unboundedly, memory fills up, consumer crashes, or messages are dropped.</p><p><strong>Backpressure mechanisms</strong></p><ul><li>Kafka (pull-based): consumers pull at their own rate. Natural backpressure - consumer controls its consumption rate.</li><li>Go channels with bounded buffer: channel of size N blocks the producer when full. Producer automatically slows down.</li></ul><table><tbody><tr><th><p>jobs := make(chan Job, 100) // buffer of 100</p><p>go func() {</p><p>for _, j := range allJobs {</p><p>jobs &lt;- j // blocks when buffer full - backpressure applied</p><p>}</p><p>close(jobs)</p><p>}()</p><p>for i := 0; i &lt; numWorkers; i++ {</p><p>go func() {</p><p>for job := range jobs { process(job) }</p><p>}()</p><p>}</p></th></tr></tbody></table><p><strong>When you cannot apply backpressure</strong></p><p>Load shedding: intentionally drop low-priority requests under overload. Better to return 503 to 5% of requests than to crash under full load and return 503 to 100%.</p></th></tr></tbody></table></div>

| **Q63** | **How do you ensure message ordering in a distributed messaging system?** | **Messaging** |
| ------- | ------------------------------------------------------------------------- | ------------- |

Global ordering is expensive; partial ordering is often sufficient.

**Within a Kafka partition**

Messages within a single partition are strictly ordered. Use this by choosing the right partition key - all events for an order use orderId as key, ensuring they land in the same partition.

**Across partitions**

No global ordering guarantee. Design to not need it, or use a single partition (sacrifices parallelism).

**Sequence numbers / version fields**

Include a monotonic sequence number in each message. Consumers can detect gaps or out-of-order delivery and buffer until the missing sequence arrives.

**Idempotent consumers**

// Only apply event if it is newer than what we have

if event.Version > currentVersion {

applyEvent(event)

}

**Inbox pattern**

Consumer writes events to an inbox table (ordered by sequence), processes them in order from the table. Decouples the consume step from the process step - allows reprocessing in order even if Kafka delivers out of order across partitions.

| **Q64** | **What is database query plan caching and why can it cause problems?** | **Messaging** |
| ------- | ---------------------------------------------------------------------- | ------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>PostgreSQL prepares and caches query execution plans for parameterized queries to avoid replanning on every execution.</p><p><strong>How it works</strong></p><table><tbody><tr><th><p>-- First call: planner analyzes statistics, generates a plan</p><p>SELECT * FROM orders WHERE tenant_id = $1 AND status = $2</p><p>-- After 5+ calls: PostgreSQL caches a generic plan</p><p>-- (not specific to any particular $1/$2 values)</p></th></tr></tbody></table><p><strong>The problem: stale plans</strong></p><p>If the data distribution changes significantly (a new tenant with 10x more data), the cached plan may become suboptimal. A query that was fast suddenly becomes slow after data growth.</p><p><strong>Symptoms</strong></p><p>EXPLAIN ANALYZE shows a bad plan (sequential scan when an index scan would be better) despite the data being present in the index.</p><p><strong>Solutions</strong></p><ul><li>ANALYZE tablename: update statistics so the planner has accurate information</li><li>SET plan_cache_mode = force_custom_plan: disables generic plan caching for that session</li><li>Increase autovacuum frequency for hot tables so statistics are always fresh</li><li>PgBouncer in transaction mode: prepared statements are not cached across transactions (avoids stale plans but loses planning performance benefit)</li></ul></th></tr></tbody></table></div>

| **Q65** | **What is the difference between microservices synchronous and asynchronous communication and when do you use each?** | **Messaging** |
| ------- | --------------------------------------------------------------------------------------------------------------------- | ------------- |

<div class="joplin-table-wrapper"><table><tbody><tr><th><p>(See the Software Design section for synchronous vs asynchronous communication. This entry adds nuance around event-driven messaging specifically.)</p><p><strong>Choreography vs Orchestration in async systems</strong></p><ul><li>Choreography: each service listens to events and decides its own reaction. Low coupling. Hard to see the overall flow as complexity grows.</li><li>Orchestration: a central orchestrator service directs each service and tracks the overall workflow. More explicit, easier to debug, but the orchestrator becomes a dependency.</li></ul><p><strong>Exactly-once vs at-least-once in practice</strong></p><p>Design for at-least-once delivery + idempotent consumers rather than chasing exactly-once at the infrastructure layer. Idempotent consumers give you the same outcome with far less complexity.</p><p><strong>Schema evolution in event-driven systems</strong></p><ul><li>Use a schema registry (Confluent Schema Registry with Avro) to enforce compatibility</li><li>Backward compatible changes only: add optional fields, never remove or rename</li><li>Versioned event types: OrderPlacedV1, OrderPlacedV2 when breaking changes are unavoidable</li></ul></th></tr></tbody></table></div>

# **Quick Reference: Key Concepts at a Glance**

| **Concept**               | **One-Line Summary**                                                                |
| ------------------------- | ----------------------------------------------------------------------------------- |
| REST idempotency key      | Client-generated UUID; server caches response; enables safe retries                 |
| Cursor pagination         | WHERE id > last_seen ORDER BY id LIMIT N - stable, O(log n), no skips               |
| Circuit breaker states    | CLOSED → OPEN (on failures) → HALF-OPEN (probe) → CLOSED (on success)               |
| Expand-contract migration | Add new column → write to both → backfill → switch reads → drop old                 |
| 1NF / 2NF / 3NF           | Atomic values / No partial PK deps / No transitive deps                             |
| CAP theorem               | CP (consistent but unavailable during partition) vs AP (available but stale)        |
| Saga vs 2PC               | Saga = local txns + compensations (eventual); 2PC = blocking distributed lock       |
| Outbox pattern            | Write event to DB in same txn as business data; poller publishes to Kafka           |
| SOLID - D principle       | Depend on abstractions (interfaces), not concretions (concrete types)               |
| p99 vs average latency    | Fan-out of 100 services: if each has 1% slow chance, 63% of requests hit a slow one |
| Cache stampede fix        | Mutex on cache miss + probabilistic early expiration                                |
| DLQ purpose               | Capture messages that fail all retries; enable replay after bug fix                 |
| Backpressure in Go        | Bounded channel (make(chan Job, N)) blocks producer when consumer is slow           |
| Hedged requests           | If no reply by p95, send duplicate to second instance; accept first reply           |
| CQRS                      | Separate write model (normalized, consistent) from read model (denormalized, fast)  |
| Liveness vs readiness     | Liveness: is process alive? Readiness: is it ready for traffic?                     |
| Token bucket rate limit   | Bucket of N tokens refilled at rate R; bursts up to bucket size allowed             |
| Graceful shutdown         | SIGTERM → stop accepting → finish in-flight → close resources → exit                |
| Modular monolith          | Strict module boundaries in one codebase; extract services when justified           |