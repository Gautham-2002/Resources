# Part 1.2: REST vs GraphQL vs gRPC

## What You'll Learn
- The six REST constraints and what makes an API truly RESTful (vs just HTTP-based)
- The Richardson Maturity Model and why "Level 3 REST" matters in interviews
- GraphQL's schema system, queries, mutations, subscriptions, and why N+1 is the hardest production problem
- How DataLoader works internally to batch and cache database queries
- gRPC's protocol buffer binary encoding, HTTP/2 streaming types, and when it demolishes REST in performance
- Concrete decision criteria: which protocol to choose for which use case
- tRPC, webhooks, and emerging patterns for modern API design

## Table of Contents
1. [REST — Principles and Constraints](#rest--principles-and-constraints)
2. [Richardson Maturity Model](#richardson-maturity-model)
3. [REST URL Design and Versioning](#rest-url-design-and-versioning)
4. [GraphQL — Schema, Operations, and Internals](#graphql--schema-operations-and-internals)
5. [The N+1 Problem and DataLoader](#the-n1-problem-and-dataloader)
6. [gRPC — Protocol Buffers and HTTP/2 Streaming](#grpc--protocol-buffers-and-http2-streaming)
7. [Comparison Table](#comparison-table)
8. [When to Use Each](#when-to-use-each)
9. [Webhooks](#webhooks)
10. [tRPC — TypeScript-First RPC](#trpc--typescript-first-rpc)
11. [Implementation Examples](#implementation-examples)
12. [Common Patterns & Best Practices](#common-patterns--best-practices)
13. [Common Pitfalls](#common-pitfalls)
14. [Interview Questions](#interview-questions)
15. [Resources](#resources)

---

## REST — Principles and Constraints

REST (Representational State Transfer) was defined by Roy Fielding in his 2000 dissertation. It is an **architectural style**, not a protocol or standard. REST is often conflated with "HTTP APIs that return JSON," but the actual constraints are more specific.

### The Six REST Constraints

**1. Client-Server**
The client and server are separated by a clean interface. The client doesn't know about server storage; the server doesn't know about the client's UI. This separation enables independent evolution — you can scale the backend without changing the frontend contract, and vice versa.

**2. Statelessness**
Each request from client to server must contain **all information** needed to process that request. The server stores no client session state between requests. Authentication tokens, pagination cursors, and filters are all sent with each request.

Consequences:
- Servers can be horizontally scaled — any server can handle any request
- Load balancers don't need sticky sessions
- Requests are independently retryable
- Tradeoff: Clients send more data per request (auth headers, etc.)

**3. Cacheability**
Responses must label themselves as cacheable or non-cacheable. Cacheable responses reduce client-server interactions. HTTP's `Cache-Control`, `ETag`, `Last-Modified` headers implement this.

If caching is violated (e.g., a POST returns stale cached data), clients may operate on outdated state, creating bugs.

**4. Uniform Interface**
This is REST's defining constraint, composed of four sub-constraints:

- **Resource identification in requests**: Resources are identified by URIs. The URI is stable; the representation returned may vary (JSON, XML, etc.).
- **Resource manipulation through representations**: When a client holds a representation (e.g., a JSON user object) with metadata, it has enough information to modify or delete the resource.
- **Self-descriptive messages**: Each message includes enough information to describe how to process it (Content-Type tells the client how to parse the body).
- **HATEOAS** (Hypermedia As The Engine Of Application State): Responses include links to related actions/resources. The client discovers what it can do next from the response, not from out-of-band documentation.

**5. Layered System**
The client cannot tell whether it's connected directly to the server or to an intermediary (load balancer, CDN, API gateway, cache). Layers can provide SSL termination, caching, rate limiting, authentication — all transparent to clients.

**6. Code on Demand (Optional)**
Servers can send executable code to clients (JavaScript). The only optional constraint. This is what a browser does (receives and executes JS), but REST APIs typically don't use it.

### Why "Statelessness" Is Often Violated in Practice

Most "REST" APIs store session state server-side (in Redis, DB) and use session IDs in cookies. This violates REST's statelessness constraint. JWT tokens (which carry state in the token itself) are more REST-compatible since the server doesn't need to look up session state — it decodes the token.

---

## Richardson Maturity Model

The Richardson Maturity Model (RMM), defined by Leonard Richardson, grades API "RESTfulness" on four levels. Interviewers love asking about this.

```
Level 3 ── Hypermedia Controls (HATEOAS)
   ↑
Level 2 ── HTTP Verbs
   ↑
Level 1 ── Resources
   ↑
Level 0 ── The Swamp of POX (Plain Old XML/JSON)
```

### Level 0 — Single URI, Single Method

All operations go to one endpoint, distinguished by request body. Common in SOAP and early RPC systems.

```
POST /api
{"action": "getUser", "userId": 42}

POST /api
{"action": "createOrder", "userId": 42, "product": "..."}

POST /api
{"action": "deleteUser", "userId": 42}
```

Problems: No HTTP caching (everything is POST), no meaningful status codes, URL is not a resource locator.

### Level 1 — Resources

Multiple URIs, but still only one HTTP method. Resources are named but operations are still encoded in the URL or body.

```
POST /users/getUser
POST /users/createUser
POST /users/deleteUser
POST /orders/getOrdersForUser
```

Some improvement: URLs are resource-oriented, but HTTP semantics are ignored.

### Level 2 — HTTP Verbs (Most "REST" APIs in the Wild)

Uses appropriate HTTP methods with multiple resource URIs. This is what most people mean when they say "RESTful API."

```
GET    /users        → list users
POST   /users        → create user
GET    /users/42     → get specific user
PUT    /users/42     → replace user
PATCH  /users/42     → partial update
DELETE /users/42     → delete user
```

Status codes used correctly: 200, 201, 204, 400, 401, 403, 404, 422, 429, 500.

**This is the industry minimum for "RESTful."** Most APIs stop here.

### Level 3 — Hypermedia Controls (HATEOAS)

Responses include links to valid next operations. Clients discover API capabilities from responses, not documentation.

```json
GET /users/42

{
  "id": 42,
  "name": "Alice",
  "email": "alice@example.com",
  "status": "active",
  "_links": {
    "self":    {"href": "/users/42",         "method": "GET"},
    "update":  {"href": "/users/42",         "method": "PATCH"},
    "delete":  {"href": "/users/42",         "method": "DELETE"},
    "orders":  {"href": "/users/42/orders",  "method": "GET"},
    "suspend": {"href": "/users/42/suspend", "method": "POST"}
  }
}
```

The client doesn't need hardcoded knowledge of URLs — it follows links. If the user is already suspended, the response omits the `suspend` link (business logic surfaced through hypermedia).

**Formats for HATEOAS:**
- HAL (Hypertext Application Language): `_links`, `_embedded`
- JSON:API: standardized document structure with `relationships` and `links`
- Siren: actions, not just links

**Reality check**: HATEOAS is rarely fully implemented in production. It increases response payload and couples clients to link-following logic. Most teams stop at Level 2 and document their APIs with OpenAPI/Swagger instead. But understanding Level 3 in an interview context shows deep REST knowledge.

---

## REST URL Design and Versioning

### URL Design Principles

```
# Resources are nouns, not verbs
✅ GET /users/42/orders
❌ GET /getUserOrders?userId=42

# Plural collection names
✅ /users, /orders, /products
❌ /user, /order, /product

# Nested resources for ownership (max 2 levels deep)
✅ /users/42/orders            → orders for user 42
✅ /orders/99/line-items       → line items for order 99
❌ /users/42/orders/99/items/5/reviews  → too deep, use flat: /reviews/xyz

# Actions that don't map to CRUD
✅ POST /users/42/activate         → action as sub-resource
✅ POST /orders/99/cancel
✅ POST /payments/99/refund
❌ GET /activateUser?id=42         → verb in URL

# Query parameters for filtering, sorting, pagination
GET /users?status=active&sort=created_at&order=desc&page=2&limit=50

# Search
GET /users/search?q=alice
POST /users/search  (for complex search bodies)
```

### API Versioning Strategies

**URI versioning** (most common, most visible):
```
/api/v1/users
/api/v2/users
```
Pros: Simple, bookmarkable, logged clearly in access logs. Cons: URLs should represent resources, not API versions — purists argue version doesn't belong in URL.

**Header versioning**:
```
Accept: application/vnd.myapi.v2+json
API-Version: 2
```
Pros: Clean URLs. Cons: Harder to test in browser, less visible.

**Query parameter versioning**:
```
GET /api/users?version=2
```
Pros: Easy to test. Cons: Pollutes query strings, can be accidentally cached.

**Recommendation for interviews**: URI versioning (`/v1/`, `/v2/`) because it's explicit, easy to route at the gateway level, and easy to deprecate by removing the prefix.

**Versioning strategy**:
1. Never break existing versions (additive changes are non-breaking)
2. Non-breaking: add new fields, add new optional parameters, add new endpoints
3. Breaking: remove fields, change field types, change URL structure → requires new version
4. Deprecate with `Sunset` header: `Sunset: Sat, 01 Jan 2027 00:00:00 GMT`

---

## GraphQL — Schema, Operations, and Internals

GraphQL, created by Facebook in 2012 and open-sourced in 2015, is a **query language for APIs** and a runtime for executing those queries.

The core problem GraphQL solves: REST requires the server to define response shapes. With many clients (web, mobile, TV apps) needing different data, you get:
- **Over-fetching**: REST endpoint returns 20 fields but mobile app only needs 3
- **Under-fetching**: Getting a user's profile requires `GET /users/42` then `GET /users/42/posts` then `GET /posts/1/comments` — 3 round trips

### The GraphQL Schema

The schema is a **contract** between client and server written in Schema Definition Language (SDL):

```graphql
# Scalar types: Int, Float, String, Boolean, ID
# ! = non-nullable

type User {
  id: ID!
  name: String!
  email: String!
  role: UserRole!
  createdAt: String!
  posts: [Post!]!         # nested types resolved separately
  followerCount: Int!
}

enum UserRole {
  ADMIN
  USER
  MODERATOR
}

type Post {
  id: ID!
  title: String!
  body: String!
  author: User!
  comments: [Comment!]!
  tags: [String!]!
  publishedAt: String
}

type Comment {
  id: ID!
  text: String!
  author: User!
  post: Post!
}

# Query type: read operations
type Query {
  user(id: ID!): User
  users(limit: Int = 20, offset: Int = 0, role: UserRole): [User!]!
  post(id: ID!): Post
  searchPosts(query: String!, limit: Int = 10): [Post!]!
}

# Mutation type: write operations
type Mutation {
  createUser(input: CreateUserInput!): User!
  updateUser(id: ID!, input: UpdateUserInput!): User!
  deleteUser(id: ID!): Boolean!
  createPost(input: CreatePostInput!): Post!
}

# Subscription type: real-time events
type Subscription {
  postPublished: Post!
  commentAdded(postId: ID!): Comment!
  userOnlineStatus(userId: ID!): Boolean!
}

input CreateUserInput {
  name: String!
  email: String!
  role: UserRole = USER
}

input UpdateUserInput {
  name: String
  email: String
}
```

### Queries

Clients request exactly the fields they need:

```graphql
# Mobile app: minimal fields
query GetUserProfile($id: ID!) {
  user(id: $id) {
    id
    name
    followerCount
  }
}

# Web app: full profile with recent posts
query GetUserFull($id: ID!) {
  user(id: $id) {
    id
    name
    email
    role
    createdAt
    posts {
      id
      title
      publishedAt
      tags
    }
  }
}
```

Both queries hit the same `/graphql` endpoint. The server returns exactly the shape requested — no more, no less. This is GraphQL's core value proposition.

### Mutations

```graphql
mutation CreateUser($input: CreateUserInput!) {
  createUser(input: $input) {
    id
    name
    email
  }
}

# Variables (sent separately in the request body):
{
  "input": {
    "name": "Alice",
    "email": "alice@example.com",
    "role": "ADMIN"
  }
}
```

Mutations are distinguished from queries semantically:
- Queries are read-only, can run in parallel
- Mutations modify state, run **sequentially** when multiple are in one request
- Mutations should return the modified resource (not just a boolean) — enables cache updates

### Subscriptions

Subscriptions use WebSocket or SSE (Server-Sent Events) for real-time updates:

```graphql
subscription OnCommentAdded($postId: ID!) {
  commentAdded(postId: $postId) {
    id
    text
    author {
      name
    }
  }
}
```

The client subscribes once. The server pushes events as they occur. Apollo Server uses WebSocket protocol `graphql-ws`.

### Resolver Architecture

GraphQL execution is field-by-field. Each field has a **resolver** function:

```
Query.user(id: "42") 
  → User.name          (trivially: return user.name)
  → User.email         (trivially: return user.email)
  → User.posts         ← calls DB: SELECT * FROM posts WHERE author_id = 42
    → Post.title       (trivially: return post.title)
    → Post.comments    ← calls DB: SELECT * FROM comments WHERE post_id = ?
      → Comment.author ← calls DB: SELECT * FROM users WHERE id = ?
```

Each arrow that hits the DB is a potential N+1 problem.

---

## The N+1 Problem and DataLoader

### What Is N+1?

Consider this query on 10 users, each with posts:

```graphql
query {
  users(limit: 10) {
    id
    name
    posts {
      title
    }
  }
}
```

Naive resolver execution:
```
1 query:  SELECT * FROM users LIMIT 10;          → returns 10 users
N queries: SELECT * FROM posts WHERE author_id = 1;
           SELECT * FROM posts WHERE author_id = 2;
           SELECT * FROM posts WHERE author_id = 3;
           ... (10 more queries)
           
Total: 1 + 10 = 11 queries for a simple request
With nested comments: 1 + 10 + N_posts * 10 = potentially hundreds
```

This is the **N+1 problem**: one query to fetch N items, then N more queries to fetch related data for each.

In REST, you'd write a single SQL JOIN. In GraphQL, resolvers execute independently, so the naive approach fires one DB query per item.

### DataLoader: Batching and Caching

DataLoader (Facebook's solution, now at `graphql/dataloader`) defers resolver execution to collect all IDs, then fires a single batched query.

```
How DataLoader works:

Resolver 1 requests user_id=1  ─┐
Resolver 2 requests user_id=2  ─┤ DataLoader batches these
Resolver 3 requests user_id=3  ─┘ into one call per tick
                                  ↓
                          batchLoadFn([1, 2, 3])
                          → SELECT * FROM users WHERE id IN (1, 2, 3)
                          → returns [user1, user2, user3]
                                  ↓
           DataLoader distributes results back to each resolver
```

**Batching**: DataLoader collects all load() calls within a single event loop tick (using `process.nextTick` in Node.js). At the end of the tick, it calls `batchLoadFn` with all accumulated keys.

**Caching**: Within a single request, DataLoader caches results by key. If `user_id=42` is needed 5 times in a query (e.g., same author on 5 comments), it's only fetched once.

```javascript
// DataLoader implementation in Node.js
import DataLoader from 'dataloader';
import { pool } from './db.js';

// One DataLoader per request (created in context factory)
const createLoaders = () => ({
  userLoader: new DataLoader(async (userIds) => {
    // userIds = [1, 2, 3, ...] — all IDs accumulated in one tick
    const result = await pool.query(
      'SELECT * FROM users WHERE id = ANY($1)',
      [userIds]
    );
    
    // DataLoader requires results in the SAME ORDER as input keys
    // and one result per key (null for not found)
    const userMap = new Map(result.rows.map(u => [u.id, u]));
    return userIds.map(id => userMap.get(id) || null);
  }),

  postsByAuthorLoader: new DataLoader(async (authorIds) => {
    const result = await pool.query(
      'SELECT * FROM posts WHERE author_id = ANY($1)',
      [authorIds]
    );
    
    // Group by author_id since one author → many posts
    const postMap = new Map();
    for (const post of result.rows) {
      if (!postMap.has(post.author_id)) postMap.set(post.author_id, []);
      postMap.get(post.author_id).push(post);
    }
    return authorIds.map(id => postMap.get(id) || []);
  }),
});

// Resolver using DataLoader
const resolvers = {
  User: {
    posts: async (user, _args, context) => {
      // Each call to this resolver adds user.id to the batch
      // DataLoader batches ALL these calls into one query
      return context.loaders.userLoader.load(user.id);
    },
  },
  Post: {
    author: async (post, _args, context) => {
      return context.loaders.userLoader.load(post.author_id);
    },
  },
};
```

**Result**: 10-user query goes from 11 queries to 2:
```
1 query: SELECT * FROM users LIMIT 10;
1 query: SELECT * FROM posts WHERE author_id IN (1,2,3,...,10);
```

**Important**: Create new DataLoader instances per request, not per application. DataLoader's per-request cache would return stale data if shared across requests.

### GraphQL Caching Challenges

GraphQL is hard to cache at the HTTP layer because:
1. All queries hit `POST /graphql` — HTTP caches key on URL, so every request looks the same
2. Query bodies are arbitrary — no URL-based cache key
3. Partial responses: caching the entire response is wrong if only part of it changes

Solutions:
- **Persisted queries**: Client hashes query, sends only the hash. Server maps hash → query. `GET /graphql?operationName=GetUser&variables={id:42}&extensions={persistedQuery:{id:"abc123"}}` — now GET-cacheable by URL
- **Apollo CDN caching**: `@cacheControl` directive on schema fields
- **Client-side caching**: Apollo Client's normalized cache (normalizes by `__typename + id`, not by query)
- **Redis-based result caching**: Cache resolved field values with TTLs

---

## gRPC — Protocol Buffers and HTTP/2 Streaming

gRPC (Google Remote Procedure Call) is a high-performance RPC framework that uses **Protocol Buffers** for serialization and **HTTP/2** for transport.

### Protocol Buffers (Protobuf)

Protobuf is a language-neutral, binary serialization format. You define your data structure in a `.proto` file, and `protoc` generates type-safe client and server code for your language.

```protobuf
// user.proto
syntax = "proto3";

package user.v1;

option go_package = "github.com/example/user/v1;userv1";
option java_package = "com.example.user.v1";

// Service definition
service UserService {
  // Unary RPC: one request → one response
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
  rpc CreateUser(CreateUserRequest) returns (CreateUserResponse);
  
  // Server-side streaming: one request → stream of responses
  rpc ListUsers(ListUsersRequest) returns (stream UserResponse);
  
  // Client-side streaming: stream of requests → one response
  rpc BulkCreateUsers(stream CreateUserRequest) returns (BulkCreateResponse);
  
  // Bidirectional streaming: stream of requests → stream of responses
  rpc SyncUsers(stream UserSyncRequest) returns (stream UserSyncResponse);
}

message GetUserRequest {
  string user_id = 1;    // field number 1
}

message GetUserResponse {
  User user = 1;
  string request_id = 2;
}

message User {
  string id = 1;
  string name = 2;
  string email = 3;
  UserRole role = 4;
  int64 created_at_unix = 5;  // unix timestamp
  repeated string tags = 6;  // array
  map<string, string> metadata = 7;  // map type
}

enum UserRole {
  USER_ROLE_UNSPECIFIED = 0;  // proto3 requires 0 value for enums
  USER_ROLE_USER = 1;
  USER_ROLE_ADMIN = 2;
  USER_ROLE_MODERATOR = 3;
}

message ListUsersRequest {
  int32 page_size = 1;
  string page_token = 2;    // cursor-based pagination
  UserRole filter_role = 3;
}

message BulkCreateResponse {
  int32 created_count = 1;
  repeated string failed_ids = 2;
}
```

### How Protobuf Encoding Works

Protobuf uses a compact binary encoding. Each field is encoded as `(field_number << 3) | wire_type`:

```
Field "name = 2" with value "Alice":
  Tag: (2 << 3) | 2 = 18 (field 2, wire type 2 = length-delimited)
  Length: 5 (bytes)
  Data: 41 6c 69 63 65 ("Alice" in UTF-8)

Full wire: 12 05 41 6c 69 63 65
                                 ↑ 7 bytes total

Compare with JSON:
  "name": "Alice"  ← 15 bytes, plus surrounding {}, commas, etc.
```

Key properties:
- **Compact**: No field names on wire, binary not text
- **Schemaless reading impossible**: Without the `.proto`, you can't decode the message (unlike JSON)
- **Field numbers are stable**: Changing field names is non-breaking. Changing field numbers is breaking.
- **Unknown fields preserved**: Adding new fields to the proto doesn't break old clients (they ignore unknown field numbers)

### Streaming Types

```
1. Unary (Request-Response):
   Client ──[single request]──▶ Server
   Client ◀──[single response]── Server
   
   Use: Most CRUD operations, lookups

2. Server-Side Streaming:
   Client ──[single request]──▶ Server
   Client ◀──[response 1]─────── Server
   Client ◀──[response 2]─────── Server
   Client ◀──[response N]─────── Server
   Client ◀──[END]──────────── Server
   
   Use: Large dataset pagination, log tailing, real-time feeds

3. Client-Side Streaming:
   Client ──[request 1]──────▶ Server
   Client ──[request 2]──────▶ Server
   Client ──[request N]──────▶ Server
   Client ──[END]────────────▶ Server
   Client ◀──[single response]── Server
   
   Use: Bulk uploads, file upload in chunks, telemetry ingestion

4. Bidirectional Streaming:
   Client ──[request 1]──────▶ Server
   Client ◀──[response 1]────── Server
   Client ──[request 2]──────▶ Server
   Client ◀──[response 2]────── Server
   (interleaved, full-duplex)
   
   Use: Chat, collaborative editing, live game state sync
```

### gRPC vs REST on the Wire

```
REST JSON Request:
POST /api/v1/users HTTP/1.1
Content-Type: application/json
Content-Length: 87

{"name":"Alice Chen","email":"alice@example.com","role":"ADMIN","metadata":{}}
                                                              ↑ 87 bytes body

Equivalent gRPC Protobuf:
Binary frame: 0a 0a 41 6c 69 63 65 20 43 68 65 6e 12 11 61 6c 69 63 65 40 65 78 61 6d 70 6c 65 2e 63 6f 6d 18 02
                                                              ↑ ~35 bytes
```

Performance advantage compounds for:
- High-frequency calls (telemetry, logging)
- Large payloads (many fields)
- Network-constrained environments

### gRPC Error Handling

gRPC uses its own status codes (different from HTTP):

```
Code                 Meaning                         HTTP Equivalent
OK                   Success                         200
CANCELLED            Client cancelled request        499
INVALID_ARGUMENT     Bad input                       400
NOT_FOUND            Resource not found              404
ALREADY_EXISTS       Duplicate                       409
PERMISSION_DENIED    Auth failed                     403
UNAUTHENTICATED      No credentials                  401
RESOURCE_EXHAUSTED   Rate limited / quota exceeded   429
FAILED_PRECONDITION  System not in required state    412
ABORTED              Concurrency conflict             409
OUT_OF_RANGE         Out of valid range              400
UNIMPLEMENTED        Method not implemented          501
INTERNAL             Server error                    500
UNAVAILABLE          Service unavailable             503
DEADLINE_EXCEEDED    Timeout                         504
```

### gRPC in Practice (gRPC-Web and gRPC-Gateway)

**Problem**: Browsers cannot make native gRPC calls (requires direct control of HTTP/2 framing that browsers don't expose).

**Solutions**:
1. **gRPC-Web**: A JavaScript client that communicates via a proxy (Envoy) which translates gRPC-Web → gRPC. Supports unary and server streaming, not full bidirectional streaming.

2. **gRPC-Gateway**: Generates a reverse proxy from your `.proto` file that translates REST/JSON calls to gRPC calls. Serve both REST and gRPC from one implementation.

```protobuf
// gRPC-Gateway annotation in .proto
import "google/api/annotations.proto";

service UserService {
  rpc GetUser(GetUserRequest) returns (GetUserResponse) {
    option (google.api.http) = {
      get: "/v1/users/{user_id}"
    };
  }
  rpc CreateUser(CreateUserRequest) returns (CreateUserResponse) {
    option (google.api.http) = {
      post: "/v1/users"
      body: "*"
    };
  }
}
```

---

## Comparison Table

| Feature | REST | GraphQL | gRPC |
|---------|------|---------|------|
| **Protocol** | HTTP/1.1 or HTTP/2 | HTTP/1.1 or HTTP/2 | HTTP/2 (required) |
| **Data format** | JSON/XML/any | JSON | Protocol Buffers (binary) |
| **Schema** | Optional (OpenAPI) | Required (SDL) | Required (.proto) |
| **Type safety** | Weak (runtime) | Strong (schema validation) | Strong (generated code) |
| **Browser support** | ✅ Native | ✅ Native | ⚠️ Needs gRPC-Web proxy |
| **HTTP caching** | ✅ Excellent (GET) | ⚠️ Poor (POST-only) | ❌ Not applicable |
| **Streaming** | ❌ Limited (SSE, chunked) | ⚠️ Subscriptions (WebSocket) | ✅ Native (4 modes) |
| **Over-fetching** | ❌ Common | ✅ Solved | ✅ Binary, schema-defined |
| **Under-fetching** | ❌ Common (N+1 round trips) | ✅ Single request | ✅ Designed per service |
| **Code generation** | Optional | Optional | ✅ Required (protoc) |
| **API versioning** | URL/header/query | Schema evolution | Proto field numbers |
| **Tooling / Ecosystem** | ✅ Mature (Postman, curl) | ✅ Mature (GraphiQL, Apollo) | ⚠️ Growing (grpcurl, Evans) |
| **Learning curve** | Low | Medium | Medium-High |
| **Performance (latency)** | Good | Good | ✅ Best (binary, HTTP/2) |
| **Performance (throughput)** | Good | Good | ✅ Best |
| **Error handling** | HTTP status codes | Application-level errors | gRPC status codes |
| **Interoperability** | ✅ Universal | ✅ Any HTTP client | ⚠️ Requires gRPC support |
| **Self-documenting** | ⚠️ Needs OpenAPI | ✅ Introspection built-in | ⚠️ .proto files |

---

## When to Use Each

### Use REST When:
- **Public APIs**: Developers need to curl it, test in browsers, use with Postman. REST's universality wins.
- **Simple CRUD**: Standard create/read/update/delete operations without complex querying needs
- **HTTP caching is important**: Public APIs where CDN caching of GET responses is a performance strategy
- **Small teams**: Simplest to implement, debug, and evolve. No toolchain to set up.
- **Microservices with clear single-resource operations**: `GET /payments/42` not `getUserWithOrdersAndPaymentsAndReviews`
- **Webhooks**: REST is the de facto webhook format

**Real-world examples**: Stripe API, GitHub API, Twilio API, Shopify Admin API

### Use GraphQL When:
- **Multiple client types with different data needs**: Mobile app needs 3 fields, web dashboard needs 20, TV app needs 5 — different per query without separate endpoints
- **Complex, nested data requirements**: Social graphs, product catalogs with complex relationships, dashboards
- **Rapid frontend iteration**: Frontend teams can evolve queries without backend changes; just add new fields to schema
- **API aggregation/BFF (Backend for Frontend)**: GraphQL layer aggregates multiple microservices into one schema
- **Introspection and tooling**: Auto-generated documentation, GraphiQL playground, type-safe query generation (GraphQL Code Generator)

**Real-world examples**: GitHub GraphQL API (v4), Shopify Storefront API, Facebook, Twitter (partially), Airbnb

**Watch out for**:
- N+1 problem (requires DataLoader discipline)
- Security: clients can request deeply nested data causing expensive queries — use query complexity limits
- Rate limiting: REST is per-endpoint, GraphQL needs per-field or query complexity rate limiting

### Use gRPC When:
- **Internal microservice communication**: Service mesh where all services are in your control. High performance, strict contracts, generated clients in any language.
- **High throughput, low latency requirements**: Real-time systems, trading platforms, telemetry ingestion, game servers. Protobuf is 5-10x smaller than JSON, binary parsing is faster.
- **Streaming requirements**: Log tailing, live sensor data, collaborative tools, real-time analytics — server/client/bidirectional streaming built in.
- **Polyglot services**: `.proto` generates type-safe clients in Go, Java, Python, Node.js, Rust, C++ from the same definition. Contract-first development.
- **Strong typing at the boundary**: Compile-time errors on API contract violations, not runtime surprises.

**Real-world examples**: Google internal APIs, Kubernetes API (uses gRPC internally), Cockroach DB, Etcd, NATS, Istio

**Watch out for**:
- Browser clients need gRPC-Web or gRPC-Gateway proxy
- Harder to debug (binary, not human-readable); use grpcurl, Evans, or enable reflection
- Ecosystem is less mature than REST (fewer tutorials, support)
- Firewall/proxy issues: some infrastructure doesn't support HTTP/2 well

### Summary Decision Tree

```
Is this a public API developers will consume?
  ├── Yes → REST (universality > performance)
  └── No → Is it internal service-to-service?
              ├── Yes, high performance/streaming → gRPC
              ├── Yes, moderate complexity → REST or gRPC
              └── No, client-facing with complex queries?
                    ├── Multiple clients, different data shapes → GraphQL
                    └── Simple CRUD, single client → REST
```

---

## Webhooks

Webhooks are **reverse APIs**: instead of the client polling your server for changes, your server calls the client's URL when an event occurs.

```
Traditional polling:                  Webhooks (push):
Client ──GET /events──▶ Server        Server ──POST──▶ Client
Client ◀──(no new)──── Server         (when event occurs)
(wait)
Client ──GET /events──▶ Server
Client ◀──(no new)──── Server         Real-time, no wasted requests
(repeat every N seconds...)
```

### Webhook Design Best Practices

**Event payload format:**
```json
{
  "id": "evt_1234567890",
  "type": "order.completed",
  "created": 1719654000,
  "api_version": "2024-01-01",
  "data": {
    "object": {
      "id": "ord_abc123",
      "status": "completed",
      "amount": 9999,
      "currency": "inr"
    },
    "previous_attributes": {
      "status": "processing"
    }
  }
}
```

**Signature verification** (prevents fake webhooks):
```
1. Server signs payload with HMAC-SHA256 using a shared secret
2. Signature sent in header: Stripe-Signature: t=timestamp,v1=signature
3. Client verifies: HMAC(secret, timestamp + "." + body) == signature
4. Client also checks timestamp is within 5 minutes (prevents replay attacks)
```

**Retry logic**: Webhooks fail (client down, timeout, 5xx). Retry with exponential backoff:
```
Attempt 1: immediately
Attempt 2: 1 minute later
Attempt 3: 10 minutes later
Attempt 4: 1 hour later
Attempt 5: 24 hours later
After 5 failures: mark as failed, alert
```

**Idempotency**: Webhooks can be delivered more than once. Clients must be idempotent (process `event.id` once, store processed IDs in DB to skip duplicates).

**Delivery guarantees**: Webhook systems typically guarantee **at-least-once** delivery, not exactly-once. Design consumers to handle duplicates.

---

## tRPC — TypeScript-First RPC

tRPC is an end-to-end type-safe RPC library for TypeScript. It allows you to call backend functions from the frontend with full type inference — no code generation, no schemas.

```typescript
// server/router.ts
import { initTRPC } from '@trpc/server';
import { z } from 'zod';

const t = initTRPC.create();

export const appRouter = t.router({
  user: t.router({
    getById: t.procedure
      .input(z.object({ id: z.string() }))
      .query(async ({ input }) => {
        return db.user.findUnique({ where: { id: input.id } });
      }),
    
    create: t.procedure
      .input(z.object({ name: z.string(), email: z.string().email() }))
      .mutation(async ({ input }) => {
        return db.user.create({ data: input });
      }),
  }),
});

// client/pages/profile.tsx
import { trpc } from '../utils/trpc';

function Profile({ userId }: { userId: string }) {
  const { data: user } = trpc.user.getById.useQuery({ id: userId });
  // `user` is fully typed — no type assertion needed
  // If server changes the return type, this line errors at compile time
}
```

**Why tRPC?**: Eliminates the REST/GraphQL layer entirely for TypeScript monorepos (Next.js apps, T3 stack). Instant feedback on API contract changes — if backend renames a field, frontend shows a type error immediately.

**Limitation**: TypeScript only. Not suitable for multi-language services or public APIs. Use REST or GraphQL for those.

---

## Implementation Examples

### Go + Chi Router

```go
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

// Domain models
type User struct {
	ID        int       `json:"id"`
	Name      string    `json:"name"`
	Email     string    `json:"email"`
	CreatedAt time.Time `json:"createdAt"`
}

type Post struct {
	ID       int    `json:"id"`
	Title    string `json:"title"`
	AuthorID int    `json:"authorId"`
}

// RESTful resource handler — Level 2 RMM
type UserHandler struct {
	// In production: inject repository interface here
}

func (h *UserHandler) Routes() chi.Router {
	r := chi.NewRouter()
	r.Get("/", h.List)
	r.Post("/", h.Create)
	r.Route("/{id}", func(r chi.Router) {
		r.Get("/", h.Get)
		r.Put("/", h.Replace)
		r.Patch("/", h.Update)
		r.Delete("/", h.Delete)
		// Nested resource
		r.Get("/posts", h.ListPosts)
		// Actions as sub-resources
		r.Post("/activate", h.Activate)
		r.Post("/deactivate", h.Deactivate)
	})
	return r
}

func (h *UserHandler) List(w http.ResponseWriter, r *http.Request) {
	// Parse pagination/filter query params
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	if limit == 0 || limit > 100 {
		limit = 20
	}
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	status := r.URL.Query().Get("status")

	log.Printf("list users: limit=%d offset=%d status=%s", limit, offset, status)

	users := []User{
		{ID: 1, Name: "Alice", Email: "alice@example.com", CreatedAt: time.Now()},
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-Total-Count", "1") // useful for pagination UI
	json.NewEncoder(w).Encode(map[string]any{
		"data":   users,
		"limit":  limit,
		"offset": offset,
		"total":  1,
	})
}

func (h *UserHandler) Create(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Name  string `json:"name"`
		Email string `json:"email"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		http.Error(w, `{"error":"invalid JSON"}`, http.StatusBadRequest)
		return
	}

	user := User{ID: 42, Name: input.Name, Email: input.Email, CreatedAt: time.Now()}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Location", "/api/v1/users/42")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(user)
}

func (h *UserHandler) Get(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	// Fetch from DB by id...
	user := User{ID: 1, Name: "Alice", Email: "alice@example.com"}
	_ = id

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(user)
}

func (h *UserHandler) Replace(w http.ResponseWriter, r *http.Request) {
	// Full resource replacement
	w.WriteHeader(http.StatusNoContent)
}

func (h *UserHandler) Update(w http.ResponseWriter, r *http.Request) {
	// Partial update
	w.WriteHeader(http.StatusNoContent)
}

func (h *UserHandler) Delete(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusNoContent)
}

func (h *UserHandler) ListPosts(w http.ResponseWriter, r *http.Request) {
	userID := chi.URLParam(r, "id")
	log.Printf("listing posts for user %s", userID)
	posts := []Post{{ID: 1, Title: "Hello World", AuthorID: 1}}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(posts)
}

func (h *UserHandler) Activate(w http.ResponseWriter, r *http.Request) {
	// Action endpoint — uses POST, not a new HTTP method
	w.WriteHeader(http.StatusNoContent)
}

func (h *UserHandler) Deactivate(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusNoContent)
}

func main() {
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	userHandler := &UserHandler{}
	r.Mount("/api/v1/users", userHandler.Routes())

	// gRPC note for Go: use google.golang.org/grpc package
	// protoc --go_out=. --go-grpc_out=. user.proto
	// Then implement the generated UserServiceServer interface

	log.Fatal(http.ListenAndServe(":8080", r))
}
```

### Node.js + Express

```javascript
import express from 'express';

const app = express();
app.use(express.json());

// ─── REST Endpoints ────────────────────────────────────────────────────────

const router = express.Router();

// GET /users — list with pagination and filtering
router.get('/', async (req, res) => {
  const {
    limit = 20,
    offset = 0,
    status,
    sort = 'created_at',
    order = 'desc',
  } = req.query;

  // In production: query DB with these params
  const users = [{ id: 1, name: 'Alice', email: 'alice@example.com' }];
  const total = 1;

  res
    .set('X-Total-Count', String(total))
    .json({ data: users, limit: Number(limit), offset: Number(offset), total });
});

// GET /users/:id
router.get('/:id', async (req, res) => {
  const { id } = req.params;
  // const user = await db.users.findById(id)
  // if (!user) return res.status(404).json({ error: 'Not found' })
  res.json({ id, name: 'Alice', email: 'alice@example.com' });
});

// POST /users
router.post('/', async (req, res) => {
  const { name, email } = req.body;
  if (!name || !email) {
    return res.status(422).json({
      type: 'https://api.example.com/errors/validation-error',
      title: 'Validation Error',
      status: 422,
      errors: [
        !name && { field: 'name', message: 'Required' },
        !email && { field: 'email', message: 'Required' },
      ].filter(Boolean),
    });
  }

  const user = { id: 42, name, email };
  res.status(201).location(`/api/v1/users/${user.id}`).json(user);
});

// PUT /users/:id — full replacement
router.put('/:id', async (req, res) => {
  const { id } = req.params;
  const { name, email, role } = req.body; // all fields required for PUT
  if (!name || !email || !role) {
    return res.status(400).json({ error: 'PUT requires all fields' });
  }
  res.json({ id, name, email, role });
});

// PATCH /users/:id — partial update
router.patch('/:id', async (req, res) => {
  const updates = req.body; // only provided fields
  res.status(204).end();
});

// DELETE /users/:id
router.delete('/:id', async (req, res) => {
  res.status(204).end();
});

// Nested resource: GET /users/:id/posts
router.get('/:id/posts', async (req, res) => {
  const { id } = req.params;
  const posts = [{ id: 1, title: 'Hello World', authorId: Number(id) }];
  res.json({ data: posts });
});

// Action sub-resource: POST /users/:id/activate
router.post('/:id/activate', async (req, res) => {
  res.status(204).end();
});

app.use('/api/v1/users', router);

// ─── GraphQL setup (Apollo Server) ────────────────────────────────────────
// npm install @apollo/server graphql dataloader

/*
import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';

const server = new ApolloServer({ typeDefs, resolvers });
await server.start();
app.use('/graphql', expressMiddleware(server, {
  context: async ({ req }) => ({
    loaders: createLoaders(), // DataLoader instances per request
    userId: req.headers['x-user-id'],
  }),
}));
*/

// ─── gRPC setup ────────────────────────────────────────────────────────────
// npm install @grpc/grpc-js @grpc/proto-loader

/*
import grpc from '@grpc/grpc-js';
import protoLoader from '@grpc/proto-loader';

const packageDef = protoLoader.loadSync('user.proto', {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});
const userProto = grpc.loadPackageDefinition(packageDef).user.v1;

const grpcServer = new grpc.Server();
grpcServer.addService(userProto.UserService.service, {
  getUser: (call, callback) => {
    const { user_id } = call.request;
    callback(null, { user: { id: user_id, name: 'Alice' } });
  },
  listUsers: (call) => {
    // Server-side streaming
    users.forEach(user => call.write({ user }));
    call.end();
  },
});
grpcServer.bindAsync('0.0.0.0:50051', grpc.ServerCredentials.createInsecure(), () => {
  grpcServer.start();
});
*/

app.listen(8080, () => console.log('Server on :8080'));
```

### Python + FastAPI

```python
from fastapi import FastAPI, Query, Path, HTTPException, Response
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from enum import Enum

app = FastAPI(title="Users API", version="1.0.0")


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None


class UserReplace(BaseModel):
    """PUT requires all fields — use different model from PATCH"""
    name: str
    email: EmailStr
    role: UserRole


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole


class PaginatedUsers(BaseModel):
    data: List[UserResponse]
    limit: int
    offset: int
    total: int


# ─── REST Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/v1/users", response_model=PaginatedUsers)
async def list_users(
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = None,
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
):
    users = [UserResponse(id=1, name="Alice", email="alice@example.com", role=UserRole.USER)]
    total = 1
    response.headers["X-Total-Count"] = str(total)
    return PaginatedUsers(data=users, limit=limit, offset=offset, total=total)


@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int = Path(ge=1)):
    # user = await db.users.find_by_id(user_id)
    # if not user: raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return UserResponse(id=user_id, name="Alice", email="alice@example.com", role=UserRole.USER)


@app.post("/api/v1/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, response: Response):
    created = UserResponse(id=42, name=user.name, email=user.email, role=user.role)
    response.headers["Location"] = f"/api/v1/users/{created.id}"
    return created


@app.put("/api/v1/users/{user_id}", response_model=UserResponse)
async def replace_user(user_id: int, user: UserReplace):
    """Full replacement — all fields required"""
    return UserResponse(id=user_id, name=user.name, email=user.email, role=user.role)


@app.patch("/api/v1/users/{user_id}", status_code=204)
async def update_user(user_id: int, updates: UserUpdate):
    """Partial update — only provided fields changed"""
    # Fetch existing, apply only non-None fields from updates
    return Response(status_code=204)


@app.delete("/api/v1/users/{user_id}", status_code=204)
async def delete_user(user_id: int):
    return Response(status_code=204)


# Nested resource
@app.get("/api/v1/users/{user_id}/posts")
async def list_user_posts(user_id: int):
    return {"data": [{"id": 1, "title": "Hello World", "authorId": user_id}]}


# Action endpoint
@app.post("/api/v1/users/{user_id}/activate", status_code=204)
async def activate_user(user_id: int):
    return Response(status_code=204)


# ─── GraphQL with Strawberry ────────────────────────────────────────────────
# pip install strawberry-graphql[fastapi]
"""
import strawberry
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class UserType:
    id: int
    name: str
    email: str

@strawberry.type
class Query:
    @strawberry.field
    async def user(self, id: int) -> UserType:
        return UserType(id=id, name="Alice", email="alice@example.com")

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(self, name: str, email: str) -> UserType:
        return UserType(id=42, name=name, email=email)

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema)
app.include_router(graphql_router, prefix="/graphql")
"""

# ─── gRPC with grpcio ────────────────────────────────────────────────────────
# pip install grpcio grpcio-tools
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. user.proto
"""
import grpc
from concurrent import futures
import user_pb2
import user_pb2_grpc

class UserServiceServicer(user_pb2_grpc.UserServiceServicer):
    def GetUser(self, request, context):
        return user_pb2.GetUserResponse(
            user=user_pb2.User(
                id=request.user_id,
                name="Alice",
                email="alice@example.com",
            )
        )

    def ListUsers(self, request, context):
        # Server-side streaming
        users = [user_pb2.User(id=1, name="Alice", email="alice@example.com")]
        for user in users:
            yield user_pb2.UserResponse(user=user)

def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()
"""
```

---

## Common Patterns & Best Practices

1. **Cursor-based pagination over offset pagination for large datasets**: Offset pagination (`LIMIT 20 OFFSET 10000`) requires the DB to scan 10020 rows. Cursor-based (`WHERE created_at < $cursor ORDER BY created_at DESC LIMIT 20`) uses an index. Expose as `nextCursor` in response.

2. **Use DataLoader for every relation in GraphQL**: Any field that resolves a related resource must use a DataLoader. Make it a team rule — N+1 in production is the #1 GraphQL performance killer.

3. **Set query complexity limits in GraphQL**: Users can send deeply nested queries that cause O(N^3) DB queries. Use `graphql-query-complexity` or `graphql-depth-limit` to reject expensive queries before execution.
   ```javascript
   maxDepth: 7,
   maxComplexity: 200, // each field costs 1 + nesting multiplier
   ```

4. **Version your proto files with Go module paths**: `option go_package = "github.com/org/proto/user/v1;userv1"`. Include `v1/`, `v2/` in directory structure. Breaking proto changes get a new package path.

5. **Always return the created/updated resource from mutations**: Even if the client already has the data, returning the server-side truth avoids an extra fetch. GraphQL mutations should return the mutated object.

6. **Use a BFF (Backend for Frontend) pattern**: Rather than having mobile and web call the same generic REST/GraphQL API, add a thin BFF layer per client type that aggregates and shapes data for that client's specific needs. The BFF can call gRPC internally.

7. **Design REST endpoints around resources, not actions** — except when the action doesn't map to a resource state change. `POST /payments/42/capture` is fine. Don't use `GET /capturePayment?id=42`.

8. **Schema-first development for gRPC**: Write the `.proto` file first, agree on the contract with consumers, then implement. This enables parallel development — teams can generate mocks from the proto while implementation is in progress.

9. **Use structured error bodies consistently**: Pick RFC 7807 (Problem Details) for REST. Return field-level errors for validation failures. Never return "error: true" with a 200 status.

10. **Exponential backoff with jitter for webhook retries**: Pure exponential backoff (all clients retry at the same time after server recovers from outage) causes thundering herd. Add `jitter = random(0, delay * 0.1)`.

---

## Common Pitfalls

- ❌ **WRONG**: Creating endpoints like `GET /getAllActiveUsersWithOrders` — embedding query logic in URL
  - ✅ **CORRECT**: `GET /users?status=active&include=orders` — use query params for filtering, standard resource URL structure

- ❌ **WRONG**: Using GraphQL for simple CRUD with a single client and no complex relationships
  - ✅ **CORRECT**: REST is simpler, better cached, easier to debug for simple CRUD. GraphQL adds complexity that only pays off at scale.

- ❌ **WRONG**: Loading relations in GraphQL resolvers without DataLoader
  - ✅ **CORRECT**: Every resolver that loads a related entity must use DataLoader. No exceptions.

- ❌ **WRONG**: Creating a new DataLoader once at server startup and sharing across requests
  - ✅ **CORRECT**: DataLoader must be created per-request (in the context factory). Shared DataLoaders return cached data from other users' requests.

- ❌ **WRONG**: Using gRPC for a public API that developers will curl/test in browsers
  - ✅ **CORRECT**: Use REST or GraphQL for public APIs. gRPC is for internal service communication.

- ❌ **WRONG**: Returning a `200 OK` with `{"success": false, "error": "Not found"}` from GraphQL errors
  - ✅ **CORRECT**: GraphQL has a structured `errors` field. Use it. Business logic errors go in `errors[]`; only return `200` when execution succeeded (even if data is null).

- ❌ **WRONG**: Changing a protobuf field number (e.g., renaming field 3 from `email` to `email_address`)
  - ✅ **CORRECT**: Field numbers are the stable wire identity in protobuf. Add a new field with a new number; mark the old field as `reserved 3; reserved "email";`. Never reuse numbers.

- ❌ **WRONG**: Using `offset` pagination for GraphQL lists that will have millions of rows
  - ✅ **CORRECT**: Use cursor-based pagination with `after`/`before` arguments following the Relay Connection Spec.

- ❌ **WRONG**: Not validating webhook signatures — accepting any POST to your webhook endpoint
  - ✅ **CORRECT**: Always verify HMAC signature and check timestamp freshness (within 5 minutes) to prevent replay attacks.

- ❌ **WRONG**: Exposing gRPC server error internals to clients (stack traces, DB errors)
  - ✅ **CORRECT**: Map internal errors to gRPC status codes with safe messages. Log full errors server-side.

---

## Interview Questions

**Q1. What are the trade-offs between REST and GraphQL?**

**Answer:**

REST advantages:
- Simpler to implement, debug, and monitor (every endpoint is a distinct URL, HTTP status codes)
- Excellent HTTP caching — GET endpoints cached at CDN, browser, or proxy layer
- Universal tooling (curl, Postman, any HTTP client)
- Clear contracts per endpoint; easier rate limiting per operation
- Stateless by design — no schema to maintain

GraphQL advantages:
- Clients specify exactly what data they need — eliminates over-fetching and under-fetching
- Single endpoint — reduces round trips for complex, nested data needs (blog post + author + comments in one request)
- Strongly typed schema with built-in introspection and documentation
- Enables rapid frontend evolution without backend changes
- Excellent for multiple clients with different data needs (mobile vs web)

REST disadvantages:
- Over-fetching (endpoint returns 20 fields, client needs 3)
- Under-fetching (multiple round trips for related data)
- API versioning requires coordination
- No standard way to discover all operations (OpenAPI helps but isn't native)

GraphQL disadvantages:
- N+1 problem requires DataLoader discipline
- HTTP caching doesn't work natively (everything is POST /graphql)
- Query complexity attacks — malicious clients can send deeply nested queries
- Harder to rate limit (per-query instead of per-endpoint)
- Learning curve for teams unfamiliar with schema design

**When to choose**: REST for public APIs, simple CRUD, caching-heavy scenarios. GraphQL for complex data requirements, multiple clients, mobile-first products.

---

**Q2. When would you choose gRPC over REST?**

**Answer:** Choose gRPC when:

1. **Performance is critical**: Binary Protobuf encoding is ~5-10x smaller than JSON. HTTP/2 multiplexing and header compression reduce overhead. For high-throughput internal services (10K+ RPS), this matters.

2. **Streaming is required**: gRPC has native server-side, client-side, and bidirectional streaming. REST lacks native full-duplex streaming (SSE is server-only, WebSockets aren't REST).

3. **Polyglot microservices**: A single `.proto` file generates type-safe clients in Go, Java, Python, Node.js, etc. No need to hand-write and maintain client SDKs.

4. **Strict contracts**: Proto field numbers and types enforce the API contract at compile time. Breaking changes fail the build, not production.

5. **Service mesh environments**: Envoy, Istio, and Linkerd speak gRPC natively — observability, load balancing, and retries work out of the box.

Choose REST over gRPC when:
- It's a public API (gRPC needs grpcurl or Evans, not curl)
- Browser clients need to call it directly (gRPC-Web adds proxy complexity)
- Team is unfamiliar with protobuf toolchain
- Response caching is important (REST GET responses are HTTP-cacheable)

**Real scenario**: Your internal notification service receives 50K events/second from 20 microservices, processes them, and streams results back. Use gRPC bidirectional streaming. Your public REST API that external developers consume? Keep it REST.

---

**Q3. What is the N+1 problem in GraphQL and how do you solve it?**

**Answer:** The N+1 problem occurs when fetching a list of N items and then making one database query per item to fetch related data:

```graphql
query { users(limit: 10) { posts { title } } }
```
Naive resolvers fire:
- 1 query: `SELECT * FROM users LIMIT 10`
- 10 queries: `SELECT * FROM posts WHERE author_id = ?` for each user
= 11 queries total (1 + N)

**Solution: DataLoader**

DataLoader batches all `.load(id)` calls from within a single event loop tick into a single batched query:

```javascript
const userLoader = new DataLoader(async (ids) => {
  const posts = await db.query('SELECT * FROM posts WHERE author_id = ANY($1)', [ids]);
  // Group by author_id, return in same order as ids
  const map = groupBy(posts, 'author_id');
  return ids.map(id => map[id] || []);
});

// Each User.posts resolver just calls:
return context.loaders.postsByAuthor.load(user.id);
// DataLoader accumulates all these and fires one batched query
```

Result: 2 queries instead of 11.

**Important details**:
1. DataLoader must be instantiated per-request, not per-application (per-request cache, not global)
2. Return order must match input order (DataLoader contract)
3. Return one result per input key (null for not found)
4. DataLoader also caches within a request — if `user_id=42` is needed 5 times, fetched once

For deeply nested graphs (users → posts → comments → authors), each level needs its own DataLoader. Without it, a simple query can trigger thousands of DB calls.

---

**Q4. What makes an API truly RESTful (Richardson Maturity Model)?**

**Answer:** The Richardson Maturity Model defines four levels:

**Level 0 — Swamp of POX**: Single URI, everything via POST. RPC-over-HTTP. Not REST.
```
POST /api {"action": "createUser", "name": "Alice"}
```

**Level 1 — Resources**: Multiple URIs identifying resources, but still only one HTTP method.
```
POST /users/create
POST /users/delete
```

**Level 2 — HTTP Verbs**: Uses appropriate methods (GET, POST, PUT, PATCH, DELETE) and status codes correctly. This is what most people call "RESTful" in practice.
```
GET /users → 200, POST /users → 201, DELETE /users/42 → 204
```

**Level 3 — Hypermedia (HATEOAS)**: Responses include links to valid next operations. Clients navigate the API by following links from responses, not by reading documentation.
```json
{
  "id": 42, "name": "Alice",
  "_links": {
    "self": "/users/42",
    "orders": "/users/42/orders",
    "deactivate": "/users/42/deactivate"
  }
}
```

**True REST per Fielding**: All six constraints (stateless, uniform interface, cacheable, client-server, layered, optional code-on-demand) plus HATEOAS.

**In practice**: Most production APIs are Level 2. Full HATEOAS is complex and rarely worth the engineering investment unless building a hypermedia API for external developers. Knowing Level 3 in an interview signals depth.

---

**Q5. What is the difference between a mutation and a query in GraphQL?**

**Answer:**

**Queries** are read operations — they fetch data without side effects. Queries are executed in **parallel** by the GraphQL runtime when multiple fields are requested.

**Mutations** modify server state — create, update, delete, or trigger actions. When a client sends multiple mutations in one request, they execute **sequentially** (each completes before the next begins). This prevents race conditions from concurrent mutations.

```graphql
# Mutations run in order: createUser → createPost → sendWelcomeEmail
mutation {
  createUser(input: {name: "Alice"}) { id }
  createPost(input: {title: "Hello"}) { id }
  sendWelcomeEmail(userId: 42) { success }
}
```

Best practices for mutations:
1. Return the mutated object (not just boolean), enabling client cache updates
2. Include all fields the client might want to update its cache with
3. Use specific input types (`CreateUserInput`) rather than inline scalar arguments
4. Return errors in the `errors` array for business logic failures, not HTTP 4xx (GraphQL always returns 200 if the query was understood)

**Conceptually**: The distinction is equivalent to HTTP GET (safe, idempotent, parallel) vs POST/PUT/DELETE (state-changing, sequential in a batch). GraphQL makes this distinction explicit and enforces execution order for mutations.

---

**Q6. Why can't GraphQL responses be cached as easily as REST?**

**Answer:** HTTP caching is based on the request URL and HTTP method. REST GET requests are uniquely identified by URL, making them trivially cacheable:
```
GET /users/42 → Cache-Control: max-age=60, ETag: "abc123"
CDN caches this. Subsequent requests serve from CDN.
```

GraphQL problems:
1. **All requests hit `POST /graphql`**: HTTP caches key on URL. Every GraphQL query looks identical to the cache — different queries return different data but have the same URL.
2. **Query bodies vary**: The cache can't distinguish `{user{name}}` from `{user{email orders{id}}}` without parsing the body, which HTTP caches don't do.
3. **Partial data**: A cached response for `{user{name email}}` is not usable for `{user{name}}` (though Apollo's normalized client cache handles this).

**Solutions**:
1. **Persisted queries**: Client sends a hash instead of the full query. The hash is stable and URL-safe → `GET /graphql?operationId=abc123&variables={"id":42}` can be CDN-cached.
2. **Apollo client-side normalized cache**: Normalizes by `__typename + id`. `{user(id:42){name}}` and `{user(id:42){email}}` both update the same cached `User:42` object.
3. **`@cacheControl` directives**: Server annotates schema fields with cache hints. Apollo CDN respects these for GET-based persisted queries.
4. **Redis result caching**: Cache entire query results keyed by `hash(query + variables + user)` with appropriate TTLs.

This is a meaningful architectural constraint when choosing between REST and GraphQL for public, CDN-heavy APIs.

---

## Resources

- [Roy Fielding's Dissertation — Architectural Styles and the Design of Network-based Software Architectures](https://www.ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm)
- [Richardson Maturity Model — Martin Fowler](https://martinfowler.com/articles/richardsonMaturityModel.html)
- [GraphQL Official Documentation](https://graphql.org/learn/)
- [GraphQL Best Practices — graphql.org](https://graphql.org/learn/best-practices/)
- [DataLoader — GitHub](https://github.com/graphql/dataloader)
- [gRPC Official Documentation](https://grpc.io/docs/)
- [Protocol Buffers Language Guide](https://protobuf.dev/programming-guides/proto3/)
- [gRPC-Gateway — REST + gRPC from one .proto](https://grpc-ecosystem.github.io/grpc-gateway/)
- [Google API Design Guide](https://cloud.google.com/apis/design)
- [Stripe API Design — one of the best REST API examples](https://stripe.com/docs/api)
- [GitHub GraphQL Explorer](https://docs.github.com/en/graphql/overview/explorer)
- [Production-Ready GraphQL — Marc-André Giroux (book)](https://productionreadygraphql.com/)
- [tRPC Documentation](https://trpc.io/)
- [Webhook.site — Test webhook endpoints](https://webhook.site/)

---

**Next:** [Part 2.1: API Design Principles](../part-02/02-api-design-principles.md)
