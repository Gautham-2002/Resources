# Part 5.1: Authorization — RBAC & ABAC

## What You'll Learn

- The precise difference between authentication and authorization (and why conflating them is a design mistake)
- Role-Based Access Control (RBAC): flat, hierarchical, JWT-stored vs DB-lookup
- Attribute-Based Access Control (ABAC): policies, subjects, objects, PDP/PEP
- Resource-level authorization — ensuring a user can only touch their own data
- Route-level vs resource-level checks, and the `can(user, action, resource)` pattern
- Open Policy Agent (OPA) — architecture and use cases
- Casbin — a library that implements multiple access-control models
- Authorization in microservices: centralized vs decentralized approaches
- Full middleware implementations in Go+Chi, Node.js+Express, Python+FastAPI

---

## Table of Contents

1. [Authentication vs Authorization](#1-authentication-vs-authorization)
2. [Role-Based Access Control (RBAC)](#2-role-based-access-control-rbac)
   - 2.1 Core Concepts: Roles, Permissions, Users
   - 2.2 Flat RBAC vs Hierarchical RBAC
   - 2.3 Storing Roles: JWT Claims vs Database Lookup
   - 2.4 Role Explosion Problem
3. [Attribute-Based Access Control (ABAC)](#3-attribute-based-access-control-abac)
   - 3.1 Subjects, Objects, Actions, Environment
   - 3.2 PDP vs PEP
   - 3.3 When ABAC Beats RBAC
   - 3.4 Open Policy Agent (OPA)
4. [Resource-Level Authorization](#4-resource-level-authorization)
5. [Route-Level vs Resource-Level Authorization](#5-route-level-vs-resource-level-authorization)
6. [The `can(user, action, resource)` Pattern](#6-the-canuser-action-resource-pattern)
7. [Casbin — Policy Enforcement Library](#7-casbin--policy-enforcement-library)
8. [JWT Claims for Roles](#8-jwt-claims-for-roles)
9. [Wildcard vs Explicit Permissions](#9-wildcard-vs-explicit-permissions)
10. [Authorization in Microservices](#10-authorization-in-microservices)
11. [Implementation Examples](#11-implementation-examples)
12. [Common Patterns & Best Practices](#common-patterns--best-practices)
13. [Common Pitfalls](#common-pitfalls)
14. [Interview Questions & Answers](#interview-questions--answers)
15. [Resources](#resources)

---

## 1. Authentication vs Authorization

These two words are used interchangeably in casual conversation, and that imprecision causes real design bugs.

```
Authentication (AuthN)              Authorization (AuthZ)
─────────────────────────────────   ─────────────────────────────────
"Who are you?"                      "What are you allowed to do?"
Establishes identity                Enforces permissions
Happens once per session/token      Happens on every protected request
JWT signature, OAuth2, sessions     RBAC, ABAC, ACLs, OPA policies
Output: verified principal          Output: allow / deny decision
```

**Concrete flow:**

```
Browser ──── POST /login ────► AuthService
                                    │
                              Validates credentials
                                    │
                              Issues JWT (AuthN complete)
                                    │
              JWT ◄─────────────────┘

Browser ──── GET /orders/42 ──► API Gateway
             [JWT in header]        │
                               Verify JWT signature (AuthN)
                               Check: does this user have READ on /orders?
                               Check: does order 42 belong to this user? (AuthZ)
                                    │
                               ─ allow ─► Handler
                               ─ deny  ─► 403 Forbidden
```

> **Key insight for interviews:** Authentication failure → `401 Unauthorized`. Authorization failure → `403 Forbidden`. Using 401 for an authorization failure is a common mistake — 401 means "you need to authenticate (or re-authenticate)," not "you don't have permission."

---

## 2. Role-Based Access Control (RBAC)

### 2.1 Core Concepts: Roles, Permissions, Users

RBAC groups permissions into named roles. Instead of assigning hundreds of permissions to each user directly, you assign roles. Roles carry permissions.

```
┌─────────┐        ┌─────────────┐        ┌──────────────────────────────┐
│  User   │──has──►│    Role     │──has──►│        Permission            │
└─────────┘        └─────────────┘        └──────────────────────────────┘
  alice              admin                  orders:read, orders:write,
  bob                editor                 users:delete, settings:*
  carol              viewer                 orders:read
                                            orders:read
```

**Core entities:**

| Entity | Description | Example |
|--------|-------------|---------|
| **User** | The principal (person, service account) | `user_id: "u_abc123"` |
| **Role** | A named collection of permissions | `"admin"`, `"editor"`, `"viewer"` |
| **Permission** | An action on a resource type | `"orders:write"`, `"users:delete"` |
| **Role Assignment** | Binding a user to a role | `alice → [admin, editor]` |

**Database schema:**

```sql
CREATE TABLE roles (
    id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,        -- 'admin', 'editor', 'viewer'
    description TEXT
);

CREATE TABLE permissions (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource TEXT NOT NULL,           -- 'orders', 'users', 'reports'
    action   TEXT NOT NULL,           -- 'read', 'write', 'delete'
    UNIQUE(resource, action)
);

CREATE TABLE role_permissions (
    role_id       UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);
```

### 2.2 Flat RBAC vs Hierarchical RBAC

**Flat RBAC** — roles are independent sets with no inheritance. Simple, but leads to duplication.

```
viewer:  [orders:read, products:read]
editor:  [orders:read, orders:write, products:read, products:write]  ← duplicates viewer perms
admin:   [orders:read, orders:write, orders:delete, users:*]        ← duplicates editor perms
```

**Hierarchical RBAC** — roles can inherit from parent roles.

```
               admin
              /     \
         editor    user-manager
            |
          viewer
            |
         readonly
```

With hierarchy, `editor` automatically has all `viewer` permissions. This removes duplication but adds complexity (resolving the full permission set requires traversal).

```sql
-- Adjacency list for role hierarchy
ALTER TABLE roles ADD COLUMN parent_id UUID REFERENCES roles(id);

-- Recursive CTE to get all permissions for a role (including inherited)
WITH RECURSIVE role_tree AS (
    SELECT id, parent_id FROM roles WHERE id = $1
    UNION ALL
    SELECT r.id, r.parent_id
    FROM roles r
    JOIN role_tree rt ON r.id = rt.parent_id
)
SELECT DISTINCT p.resource, p.action
FROM role_tree rt
JOIN role_permissions rp ON rp.role_id = rt.id
JOIN permissions p ON p.id = rp.permission_id;
```

### 2.3 Storing Roles: JWT Claims vs Database Lookup

This is a classic interview trade-off question.

**Option A: Roles in JWT**

```json
{
  "sub": "u_abc123",
  "email": "alice@example.com",
  "roles": ["admin", "editor"],
  "iat": 1719656400,
  "exp": 1719742800
}
```

Pros:
- **Zero DB calls on every request** — the middleware just inspects the token
- Scales horizontally without a shared cache
- Simple to implement

Cons:
- **Stale roles** — if you revoke a role, the JWT still carries the old role until it expires
- JWT size grows with many roles (causes issues if used as cookies; large headers)
- You cannot revoke individual permissions without revoking the whole token

**Option B: DB Lookup on Every Request**

```
Request → Middleware → DB: "SELECT roles for user u_abc123" → Check permissions → Handler
```

Pros:
- **Always fresh** — revoke a role, it takes effect immediately
- No payload bloat

Cons:
- **Extra DB round-trip on every request** — latency + load
- Requires caching (Redis) to be practical at scale

**Option C: Hybrid (JWT + Redis Cache)**

```
Request → Middleware
    → read roles from JWT
    → check Redis for revocation flag keyed by user_id
    → if revoked: re-fetch from DB, issue new JWT
    → otherwise: trust JWT roles
```

This is the production-grade approach. JWT carries roles (fast path), Redis holds revocation signals (correctness guard). TTL on JWT is short (15–60 min); Redis key is set on role change.

```
┌─────────────────────────────────────────────┐
│  JWT roles check (in-memory, 0ms)           │
│  ↓                                          │
│  Redis revocation check (~1ms)              │
│  ↓ not revoked                              │
│  Allow (total ~1ms overhead)                │
└─────────────────────────────────────────────┘
```

### 2.4 Role Explosion Problem

In large organizations, roles are often created per team, per resource type, per region:

```
org:us-east:orders:reader
org:us-east:orders:writer
org:eu-west:orders:reader
org:eu-west:orders:writer
...
```

This creates hundreds or thousands of roles that are impossible to manage. The fix:

1. **Switch to ABAC** for fine-grained, multi-dimensional access — roles can't express it cleanly
2. **Add role context/scope** — a single `orders:reader` role with a `scope` attribute
3. **Use permission wildcards** — `orders:*`, `reports:read:*`
4. **Parameterized roles** — `reader[department=engineering]`

> **Interview answer:** If you find yourself creating more than 20-30 roles that differ only by one dimension (region, department, tier), you have role explosion. The solution is to either add scope/context to roles or migrate to ABAC for that dimension.

---

## 3. Attribute-Based Access Control (ABAC)

### 3.1 Subjects, Objects, Actions, Environment

ABAC makes access decisions based on attributes rather than pre-assigned roles.

```
Subject attributes:  { user_id, department, clearance_level, employment_status }
Object attributes:   { resource_type, owner_id, classification, region }
Action:              read | write | delete | approve
Environment:         { time_of_day, ip_address, request_origin, mfa_verified }
```

**Policy example (XACML-like, simplified):**

```
ALLOW IF:
    subject.department == object.department
    AND subject.clearance >= object.classification
    AND environment.time_of_day BETWEEN "09:00" AND "18:00"
    AND action == "read"
```

This policy is impossible to express in RBAC without creating a role for every combination of department, clearance level, time window, and classification.

### 3.2 PDP vs PEP

These two components appear in every serious authorization system:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Request flow                                                            │
│                                                                          │
│  Client ──► API Gateway ──► PEP (Policy Enforcement Point)              │
│                                  │                                       │
│                                  │  "Can alice READ order/42?"           │
│                                  ▼                                       │
│                             PDP (Policy Decision Point)                  │
│                                  │                                       │
│                          ┌───────┴────────┐                             │
│                          │ Policy Store   │  Subject attrs               │
│                          │ (OPA, Casbin,  │  Object attrs                │
│                          │  DB policies)  │  Environment                 │
│                          └───────┬────────┘                             │
│                                  │  ALLOW / DENY                        │
│                                  ▼                                       │
│                              PEP enforces                                │
│                              → Allow: forward to handler                 │
│                              → Deny: return 403                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**PEP** is part of your application (middleware, API gateway plugin, service mesh sidecar). It intercepts requests and asks the PDP.

**PDP** is the policy engine. It evaluates policies and returns decisions. It can be:
- In-process (a library call — fast, no network hop)
- Sidecar (OPA running alongside your service — small network hop, language-agnostic)
- Centralized service (one PDP for all services — network latency, single point of failure risk)

### 3.3 When ABAC Beats RBAC

Use ABAC when:

| Scenario | Why RBAC Fails | ABAC Solution |
|----------|----------------|---------------|
| Multi-tenant SaaS: user can only read their org's data | Need a role per org (explosion) | `subject.org_id == object.org_id` |
| Time-based access (contractors 9–5 only) | Can't encode time in a role | `environment.hour BETWEEN 9 AND 17` |
| Data classification (SECRET vs CONFIDENTIAL) | Need roles × classification levels | `subject.clearance >= object.classification` |
| Geo-restriction (EU users can only access EU data) | Need roles × regions | `subject.region == object.region` |
| Resource ownership (users edit only their posts) | RBAC is blind to ownership | `subject.user_id == object.owner_id` |

### 3.4 Open Policy Agent (OPA)

OPA is a general-purpose, open-source policy engine. It decouples policy from application code.

**Architecture:**

```
Your Service              OPA Sidecar
┌────────────┐            ┌──────────────────────┐
│  Request   │──JSON──►   │  Rego policy engine  │
│  context   │            │                      │
│            │◄──JSON──   │  Returns:            │
│ allow/deny │  decision  │  { "allow": true }   │
└────────────┘            └──────────────────────┘
                                    │
                           Policies loaded from:
                           - Git repo (GitOps)
                           - OPA Bundle server
                           - Kubernetes ConfigMap
```

**Rego policy example:**

```rego
package authz

import future.keywords.if
import future.keywords.in

default allow := false

# Allow admin users to do anything
allow if {
    "admin" in input.user.roles
}

# Allow users to read their own orders
allow if {
    input.action == "read"
    input.resource.type == "order"
    input.resource.owner_id == input.user.id
}

# Allow editors to write to orders
allow if {
    input.action in {"read", "write"}
    input.resource.type == "order"
    "editor" in input.user.roles
}
```

**OPA query from Go:**

```go
// input sent to OPA
input := map[string]interface{}{
    "user": map[string]interface{}{
        "id":    userID,
        "roles": roles,
    },
    "action":   "write",
    "resource": map[string]interface{}{
        "type":     "order",
        "owner_id": orderOwnerID,
    },
}
// POST http://localhost:8181/v1/data/authz/allow
// Body: {"input": input}
// Response: {"result": true}
```

**When to use OPA:**

- Large teams where policy authors aren't necessarily developers
- Policies need to be version-controlled, audited, and deployed independently of code
- Multi-language environment (one policy engine for Go, Node, Python services)
- Compliance requirements that demand auditable policy decisions
- Kubernetes admission control (OPA Gatekeeper)

**When NOT to use OPA:**

- Small, single-service apps with simple RBAC — the operational overhead isn't worth it
- Latency-sensitive paths — even the sidecar adds ~1–5ms per request
- Teams without Rego expertise

---

## 4. Resource-Level Authorization

Route-level authorization checks: "does this user have the `orders:read` permission?" That's necessary but not sufficient. You also need to check: "does this specific order belong to this user?"

**The bug without resource-level checks:**

```
GET /api/orders/99   (user alice, order 99 belongs to bob)

Route-level: alice has orders:read ✓
             → Handler fetches order 99 → returns bob's order ✗
```

This is **Broken Object Level Authorization (BOLA)** — OWASP API Security Top 10 #1.

**Fix — ownership check in handler:**

```go
func GetOrder(w http.ResponseWriter, r *http.Request) {
    orderID := chi.URLParam(r, "id")
    userID  := r.Context().Value(UserIDKey).(string)

    order, err := db.GetOrder(ctx, orderID)
    if err != nil { ... }

    // CRITICAL: check ownership
    if order.UserID != userID && !userIsAdmin(r) {
        http.Error(w, "forbidden", http.StatusForbidden)
        return
    }

    json.NewEncoder(w).Encode(order)
}
```

**Patterns for ownership checks:**

1. **Handler-level**: check inside each handler (repetitive, easy to forget)
2. **Repository-level**: always filter by `AND user_id = $userID` in queries (safest)
3. **Middleware with resource loader**: load the resource in middleware, attach to context, check ownership there

The repository-level approach is the most secure because even if a developer forgets to add a check, the SQL query won't return unauthorized rows:

```sql
-- Handler calls this function with userID always included
SELECT * FROM orders
WHERE id = $1
AND user_id = $2    -- ownership enforced at data layer
```

---

## 5. Route-Level vs Resource-Level Authorization

```
┌──────────────────────────────────────────────────────────────┐
│ Route-Level (Middleware)         Resource-Level (Handler/DB) │
│──────────────────────────────────────────────────────────────│
│ "Can this role access this       "Does this user own this    │
│  route at all?"                   specific resource?"        │
│                                                              │
│ Examples:                         Examples:                  │
│  - admin only: DELETE /users      - order.user_id == userID  │
│  - logged-in: GET /dashboard      - post.author_id == userID │
│  - public: GET /products          - doc.org_id == user.org   │
│                                                              │
│ Implemented as:                   Implemented as:            │
│  - HTTP middleware                - Repository filters       │
│  - API gateway policy             - Handler assertions       │
│  - OPA sidecar                    - ABAC policy check        │
└──────────────────────────────────────────────────────────────┘
```

Both layers are required. Route-level is a coarse filter. Resource-level is the fine-grained guard.

---

## 6. The `can(user, action, resource)` Pattern

A clean authorization abstraction that unifies RBAC and ABAC behind a single interface:

```go
type Authorizer interface {
    Can(user User, action string, resource interface{}) (bool, error)
}
```

Usage at call sites:

```go
if allowed, _ := authz.Can(user, "delete", order); !allowed {
    return ErrForbidden
}
```

The implementation can be swapped without changing callers:

```go
// RBAC implementation
func (r *RBACAuthorizer) Can(user User, action string, resource interface{}) (bool, error) {
    permission := resourceTypeOf(resource) + ":" + action
    return r.userHasPermission(user.ID, permission)
}

// ABAC implementation (delegates to OPA)
func (o *OPAAuthorizer) Can(user User, action string, resource interface{}) (bool, error) {
    input := buildOPAInput(user, action, resource)
    return o.queryOPA(input)
}
```

This pattern also makes authorization unit-testable in isolation:

```go
func TestOrderDelete_AdminAllowed(t *testing.T) {
    authz := NewRBACAuthorizer(mockDB)
    admin := User{ID: "u1", Roles: []string{"admin"}}
    order := Order{ID: "o1", UserID: "u2"}

    allowed, _ := authz.Can(admin, "delete", order)
    assert.True(t, allowed)
}
```

---

## 7. Casbin — Policy Enforcement Library

Casbin is a library that implements multiple access-control models (RBAC, ABAC, ACL, RBAC with domains) by separating the model definition from the policy data.

**Model file (conf):**

```ini
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

**Policy file (CSV):**

```
p, admin, /orders, read
p, admin, /orders, write
p, admin, /orders, delete
p, editor, /orders, read
p, editor, /orders, write
p, viewer, /orders, read

g, alice, admin
g, bob, editor
```

**Go usage:**

```go
e, _ := casbin.NewEnforcer("model.conf", "policy.csv")

// Check permission
allowed, _ := e.Enforce("alice", "/orders", "delete")  // true (alice is admin)
allowed, _ = e.Enforce("bob", "/orders", "delete")     // false (bob is editor)
```

Casbin supports:
- Loading policies from PostgreSQL, Redis, MongoDB (adapters)
- Role inheritance
- Domain/tenant isolation
- ABAC with custom attribute functions

---

## 8. JWT Claims for Roles

The JWT payload carrying roles for RBAC:

```json
{
  "sub": "u_abc123",
  "email": "alice@example.com",
  "roles": ["admin", "editor"],
  "permissions": ["orders:read", "orders:write"],
  "iat": 1719656400,
  "exp": 1719742800
}
```

**Trade-offs of embedding permissions vs roles:**

| Embed | Pros | Cons |
|-------|------|------|
| **Roles** (`["admin"]`) | Small token, roles rarely change | Need role→permission lookup in middleware |
| **Permissions** (`["orders:write"]`) | Middleware is simple (direct check) | Large token, permissions change often |
| **Both** | Maximum flexibility | Largest token, can get stale |

**Recommended:** embed roles only. Keep permissions in DB/cache. Load them once per session, not per request.

**Claim structure for multi-tenant apps:**

```json
{
  "sub": "u_abc123",
  "org_id": "org_xyz",
  "roles": {
    "org_xyz": ["admin"],
    "org_abc": ["viewer"]
  }
}
```

This encodes per-organization roles without requiring multiple tokens.

---

## 9. Wildcard vs Explicit Permissions

**Explicit permissions:**

```
orders:read
orders:write
orders:delete
users:read
users:write
```

**Wildcard permissions:**

```
orders:*          → all actions on orders
*:read            → read action on all resources
*:*               → superuser
reports:*:export  → hierarchical wildcard
```

**Trade-offs:**

| | Explicit | Wildcard |
|-|----------|----------|
| Auditability | Easy to audit exactly | Harder to understand scope |
| Flexibility | Rigid but safe | Flexible but over-permissive risk |
| Performance | More DB rows | Single row matches many |
| Least privilege | Natural fit | Requires careful policy |

**Implementation — matching wildcard permissions:**

```go
func hasPermission(userPerms []string, required string) bool {
    for _, p := range userPerms {
        if p == required {
            return true
        }
        if matchWildcard(p, required) {
            return true
        }
    }
    return false
}

func matchWildcard(pattern, target string) bool {
    // "orders:*" matches "orders:read", "orders:write"
    // "*:read"   matches "orders:read", "users:read"
    patParts := strings.Split(pattern, ":")
    tgtParts := strings.Split(target, ":")
    if len(patParts) != len(tgtParts) {
        return false
    }
    for i, p := range patParts {
        if p != "*" && p != tgtParts[i] {
            return false
        }
    }
    return true
}
```

---

## 10. Authorization in Microservices

In a microservices system, you have two main models:

### Centralized Authorization Service

```
Service A ──► AuthZ Service ──► Decision
Service B ──► AuthZ Service ──► Decision
Service C ──► AuthZ Service ──► Decision
```

Pros: Single policy store, consistent decisions, easier audit
Cons: Network dependency on every auth check, single point of failure, latency

### Decentralized (Each Service Enforces Its Own Policy)

```
Service A: checks its own RBAC (loaded from shared DB/cache)
Service B: runs its own OPA sidecar
Service C: validates JWT claims locally
```

Pros: No additional network hop, resilient (service A can work even if AuthZ service is down)
Cons: Policy drift (services implement differently), harder to audit uniformly

### Hybrid (JWT for Basic AuthN/AuthZ + Sidecar for Fine-Grained)

```
API Gateway: validates JWT, extracts user identity, passes headers downstream
Each Service: runs OPA sidecar with service-specific policies
Shared policy bundle: served from central OPA bundle server (Git-backed)
```

This is the industry standard in large microservices architectures (Netflix, Airbnb, etc.).

**Token forwarding between services:**

```
Client → Service A → Service B
                   Bearer: <JWT>  (forward original token)
         OR
                   X-Internal-User: <user_id>  (service mesh with mTLS)
```

---

## 11. Implementation Examples

### Go + Chi Router

#### RBAC Middleware with Permission Check

```go
package middleware

import (
    "context"
    "encoding/json"
    "net/http"
    "strings"

    "github.com/golang-jwt/jwt/v5"
)

type contextKey string

const (
    UserIDKey    contextKey = "userID"
    UserRolesKey contextKey = "userRoles"
)

// Permission constants — define all permissions centrally
const (
    PermOrdersRead   = "orders:read"
    PermOrdersWrite  = "orders:write"
    PermOrdersDelete = "orders:delete"
    PermUsersRead    = "users:read"
    PermUsersWrite   = "users:write"
    PermUsersDelete  = "users:delete"
)

// rolePermissions maps roles to their permissions.
// In production, load this from DB on startup and cache.
var rolePermissions = map[string][]string{
    "admin":  {"orders:*", "users:*", "reports:*"},
    "editor": {"orders:read", "orders:write", "users:read"},
    "viewer": {"orders:read", "users:read"},
}

type Claims struct {
    UserID string   `json:"sub"`
    Email  string   `json:"email"`
    Roles  []string `json:"roles"`
    jwt.RegisteredClaims
}

// JWTMiddleware extracts and validates the JWT, then stores user info in context.
func JWTMiddleware(jwtSecret string) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            authHeader := r.Header.Get("Authorization")
            if authHeader == "" || !strings.HasPrefix(authHeader, "Bearer ") {
                http.Error(w, `{"error":"missing token"}`, http.StatusUnauthorized)
                return
            }

            tokenStr := strings.TrimPrefix(authHeader, "Bearer ")
            claims := &Claims{}

            token, err := jwt.ParseWithClaims(tokenStr, claims, func(t *jwt.Token) (interface{}, error) {
                if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
                    return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
                }
                return []byte(jwtSecret), nil
            })

            if err != nil || !token.Valid {
                http.Error(w, `{"error":"invalid token"}`, http.StatusUnauthorized)
                return
            }

            ctx := context.WithValue(r.Context(), UserIDKey, claims.UserID)
            ctx = context.WithValue(ctx, UserRolesKey, claims.Roles)
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}

// RequirePermission returns middleware that enforces a specific permission.
func RequirePermission(permission string) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            roles, ok := r.Context().Value(UserRolesKey).([]string)
            if !ok {
                http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
                return
            }

            if !userHasPermission(roles, permission) {
                http.Error(w, `{"error":"forbidden"}`, http.StatusForbidden)
                return
            }

            next.ServeHTTP(w, r)
        })
    }
}

// userHasPermission checks if any of the user's roles grants the required permission.
func userHasPermission(roles []string, required string) bool {
    for _, role := range roles {
        perms, exists := rolePermissions[role]
        if !exists {
            continue
        }
        for _, perm := range perms {
            if perm == required || matchWildcard(perm, required) {
                return true
            }
        }
    }
    return false
}

// matchWildcard checks if a wildcard permission pattern matches a required permission.
// "orders:*" matches "orders:read", "orders:write", etc.
func matchWildcard(pattern, target string) bool {
    if pattern == "*" {
        return true
    }
    patParts := strings.Split(pattern, ":")
    tgtParts := strings.Split(target, ":")
    if len(patParts) != len(tgtParts) {
        return false
    }
    for i, part := range patParts {
        if part != "*" && part != tgtParts[i] {
            return false
        }
    }
    return true
}
```

#### Router Setup with RBAC

```go
package main

import (
    "github.com/go-chi/chi/v5"
    chimiddleware "github.com/go-chi/chi/v5/middleware"
    "yourapp/middleware"
)

func main() {
    r := chi.NewRouter()
    r.Use(chimiddleware.Logger)
    r.Use(chimiddleware.Recoverer)

    // Public routes (no auth)
    r.Get("/health", healthHandler)
    r.Post("/auth/login", loginHandler)

    // Protected routes (require valid JWT)
    r.Group(func(r chi.Router) {
        r.Use(middleware.JWTMiddleware(cfg.JWTSecret))

        // Any authenticated user
        r.Get("/profile", getProfileHandler)

        // Require orders:read permission
        r.With(middleware.RequirePermission("orders:read")).Get("/orders", listOrdersHandler)
        r.With(middleware.RequirePermission("orders:read")).Get("/orders/{id}", getOrderHandler)

        // Require orders:write permission
        r.With(middleware.RequirePermission("orders:write")).Post("/orders", createOrderHandler)

        // Require orders:delete permission
        r.With(middleware.RequirePermission("orders:delete")).Delete("/orders/{id}", deleteOrderHandler)

        // Admin-only routes
        r.Route("/admin", func(r chi.Router) {
            r.Use(middleware.RequirePermission("users:*"))
            r.Get("/users", listUsersHandler)
            r.Delete("/users/{id}", deleteUserHandler)
        })
    })

    http.ListenAndServe(":8080", r)
}
```

#### Resource Ownership Check

```go
package handlers

import (
    "net/http"
    "github.com/go-chi/chi/v5"
    "yourapp/middleware"
    "yourapp/store"
)

func GetOrder(db *store.DB) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        orderID := chi.URLParam(r, "id")
        userID  := r.Context().Value(middleware.UserIDKey).(string)
        roles   := r.Context().Value(middleware.UserRolesKey).([]string)

        order, err := db.GetOrderByID(r.Context(), orderID)
        if err != nil {
            if errors.Is(err, store.ErrNotFound) {
                http.Error(w, `{"error":"not found"}`, http.StatusNotFound)
            } else {
                http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
            }
            return
        }

        // Resource-level authorization: admin can see any order, others only their own
        isAdmin := containsRole(roles, "admin")
        if !isAdmin && order.UserID != userID {
            // Return 404 instead of 403 to avoid leaking resource existence
            http.Error(w, `{"error":"not found"}`, http.StatusNotFound)
            return
        }

        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(order)
    }
}

func containsRole(roles []string, target string) bool {
    for _, r := range roles {
        if r == target {
            return true
        }
    }
    return false
}
```

---

### Node.js + Express

#### RBAC Middleware

```javascript
// middleware/auth.js
const jwt = require('jsonwebtoken');

// Role-to-permission mapping — in production, load from DB/cache
const rolePermissions = {
  admin:  ['orders:*', 'users:*', 'reports:*'],
  editor: ['orders:read', 'orders:write', 'users:read'],
  viewer: ['orders:read', 'users:read'],
};

/**
 * Checks if a wildcard permission pattern matches a required permission.
 * "orders:*" matches "orders:read", "orders:write"
 */
function matchPermission(pattern, required) {
  if (pattern === '*') return true;
  const patParts = pattern.split(':');
  const reqParts = required.split(':');
  if (patParts.length !== reqParts.length) return false;
  return patParts.every((part, i) => part === '*' || part === reqParts[i]);
}

/**
 * Checks if a user's roles grant a specific permission.
 */
function userHasPermission(roles, required) {
  return roles.some((role) => {
    const perms = rolePermissions[role] || [];
    return perms.some((perm) => matchPermission(perm, required));
  });
}

/**
 * JWT authentication middleware.
 * Attaches decoded user to req.user.
 */
function authenticate(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid token' });
  }

  const token = authHeader.slice(7);
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded; // { sub, email, roles, ... }
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid token' });
  }
}

/**
 * Authorization middleware factory.
 * Usage: router.get('/orders', authenticate, requirePermission('orders:read'), handler)
 */
function requirePermission(permission) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Not authenticated' });
    }

    const roles = req.user.roles || [];
    if (!userHasPermission(roles, permission)) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }

    next();
  };
}

/**
 * Middleware that loads a resource and checks ownership.
 * Usage: router.get('/orders/:id', authenticate, requireOwnership(loadOrder), handler)
 */
function requireOwnership(resourceLoader) {
  return async (req, res, next) => {
    try {
      const resource = await resourceLoader(req.params.id);
      if (!resource) {
        return res.status(404).json({ error: 'Not found' });
      }

      const isAdmin = (req.user.roles || []).includes('admin');
      const isOwner = resource.userId === req.user.sub;

      if (!isAdmin && !isOwner) {
        // Return 404 to avoid leaking resource existence to unauthorized users
        return res.status(404).json({ error: 'Not found' });
      }

      req.resource = resource; // attach to request for handler use
      next();
    } catch (err) {
      next(err);
    }
  };
}

module.exports = { authenticate, requirePermission, requireOwnership };
```

#### Router Setup

```javascript
// routes/orders.js
const express = require('express');
const router = express.Router();
const { authenticate, requirePermission, requireOwnership } = require('../middleware/auth');
const orderService = require('../services/orderService');

// Resource loader function for orders
const loadOrder = (id) => orderService.findById(id);

// List orders — requires orders:read
router.get(
  '/',
  authenticate,
  requirePermission('orders:read'),
  async (req, res, next) => {
    try {
      const roles = req.user.roles || [];
      const isAdmin = roles.includes('admin');

      // Non-admins only see their own orders (resource-level filter)
      const orders = isAdmin
        ? await orderService.findAll()
        : await orderService.findByUserId(req.user.sub);

      res.json({ data: orders });
    } catch (err) {
      next(err);
    }
  }
);

// Get single order — requires orders:read + ownership
router.get(
  '/:id',
  authenticate,
  requirePermission('orders:read'),
  requireOwnership(loadOrder),
  (req, res) => {
    res.json({ data: req.resource });
  }
);

// Create order — requires orders:write
router.post(
  '/',
  authenticate,
  requirePermission('orders:write'),
  async (req, res, next) => {
    try {
      const order = await orderService.create({
        ...req.body,
        userId: req.user.sub, // always set from token, never from body
      });
      res.status(201).json({ data: order });
    } catch (err) {
      next(err);
    }
  }
);

// Delete order — requires orders:delete + ownership (or admin)
router.delete(
  '/:id',
  authenticate,
  requirePermission('orders:delete'),
  requireOwnership(loadOrder),
  async (req, res, next) => {
    try {
      await orderService.delete(req.resource.id);
      res.status(204).end();
    } catch (err) {
      next(err);
    }
  }
);

module.exports = router;
```

#### JWT Role Claims Issuance

```javascript
// services/authService.js
const jwt = require('jsonwebtoken');
const { getUserRoles } = require('../db/userRepository');

async function login(email, password) {
  const user = await validateCredentials(email, password);
  if (!user) throw new Error('Invalid credentials');

  // Fetch roles from DB at login time
  const roles = await getUserRoles(user.id);

  const token = jwt.sign(
    {
      sub: user.id,
      email: user.email,
      roles,                    // embed roles in JWT
    },
    process.env.JWT_SECRET,
    {
      expiresIn: '1h',          // short-lived; roles baked in for 1 hour
      issuer: 'api.example.com',
      audience: 'app.example.com',
    }
  );

  return { token, expiresIn: 3600 };
}

module.exports = { login };
```

---

### Python + FastAPI

#### RBAC Middleware & Dependencies

```python
# auth/dependencies.py
from __future__ import annotations

import fnmatch
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

from config import settings

# Role-to-permission mapping — load from DB/cache in production
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin":  ["orders:*", "users:*", "reports:*"],
    "editor": ["orders:read", "orders:write", "users:read"],
    "viewer": ["orders:read", "users:read"],
}


class TokenData(BaseModel):
    user_id: str
    email: str
    roles: list[str] = []


def match_permission(pattern: str, required: str) -> bool:
    """
    Check if a wildcard permission pattern matches the required permission.
    Uses fnmatch: "orders:*" matches "orders:read", "orders:write".
    """
    return fnmatch.fnmatch(required, pattern)


def user_has_permission(roles: list[str], required: str) -> bool:
    """Return True if any of the user's roles grant the required permission."""
    for role in roles:
        perms = ROLE_PERMISSIONS.get(role, [])
        if any(match_permission(perm, required) for perm in perms):
            return True
    return False


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None
) -> TokenData:
    """
    FastAPI dependency that extracts and validates the JWT.
    Raises 401 if the token is missing or invalid.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_error

    token = authorization.removeprefix("Bearer ")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email", "")
        roles: list[str] = payload.get("roles", [])

        if user_id is None:
            raise credentials_error

        return TokenData(user_id=user_id, email=email, roles=roles)

    except JWTError:
        raise credentials_error


def require_permission(permission: str):
    """
    Dependency factory for permission-based authorization.

    Usage:
        @router.get("/orders", dependencies=[Depends(require_permission("orders:read"))])
    """
    async def check_permission(
        current_user: Annotated[TokenData, Depends(get_current_user)]
    ) -> TokenData:
        if not user_has_permission(current_user.roles, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return check_permission
```

#### Router with RBAC

```python
# routers/orders.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from auth.dependencies import TokenData, get_current_user, require_permission
from db.repositories import OrderRepository
from models import Order, OrderCreate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get(
    "/",
    dependencies=[Depends(require_permission("orders:read"))],
)
async def list_orders(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    repo: Annotated[OrderRepository, Depends()],
) -> list[Order]:
    is_admin = "admin" in current_user.roles
    if is_admin:
        return await repo.find_all()
    # Resource-level: non-admins see only their own orders
    return await repo.find_by_user_id(current_user.user_id)


@router.get("/{order_id}")
async def get_order(
    order_id: UUID,
    current_user: Annotated[TokenData, Depends(require_permission("orders:read"))],
    repo: Annotated[OrderRepository, Depends()],
) -> Order:
    order = await repo.find_by_id(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Resource-level ownership check
    is_admin = "admin" in current_user.roles
    if not is_admin and order.user_id != current_user.user_id:
        # Return 404 to avoid leaking resource existence
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return order


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    current_user: Annotated[TokenData, Depends(require_permission("orders:write"))],
    repo: Annotated[OrderRepository, Depends()],
) -> Order:
    return await repo.create(
        user_id=current_user.user_id,  # always from token, never from request body
        **body.model_dump(),
    )


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: UUID,
    current_user: Annotated[TokenData, Depends(require_permission("orders:delete"))],
    repo: Annotated[OrderRepository, Depends()],
) -> None:
    order = await repo.find_by_id(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    is_admin = "admin" in current_user.roles
    if not is_admin and order.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    await repo.delete(order_id)
```

---

## Common Patterns & Best Practices

### 1. Principle of Least Privilege
Grant the minimum permissions necessary. Start with zero and add only what's needed. Review and prune permissions regularly.

### 2. Fail Closed (Deny by Default)
When in doubt, deny. Your authorization logic should return `false` by default, and only return `true` when a policy explicitly allows the action.

```go
// Bad: fail open
func hasPermission(user User, action string) bool {
    for _, p := range user.Permissions {
        if p == action {
            return true
        }
    }
    return true // BUG: allows everything if no permissions
}

// Good: fail closed
func hasPermission(user User, action string) bool {
    for _, p := range user.Permissions {
        if p == action {
            return true
        }
    }
    return false // default: deny
}
```

### 3. Return 404 Instead of 403 for Owned Resources
When a user tries to access another user's resource, return `404 Not Found` rather than `403 Forbidden`. This prevents leaking the existence of the resource (prevents enumeration attacks).

### 4. Never Trust User-Supplied Role Claims
When creating resources, always set `user_id` from the validated JWT, never from the request body. A user can claim any `user_id` in a request body.

### 5. Audit Log All Authorization Decisions
Especially for sensitive operations (admin actions, financial data, PII access). Log who, what, when, and whether it was allowed or denied.

### 6. Keep Authorization Logic Centralized
Don't scatter permission checks across handlers. Use a single `can(user, action, resource)` abstraction. This makes it easy to test, audit, and update.

### 7. Short JWT Expiry + Refresh Tokens
Shorter-lived JWTs (15–60 minutes) with refresh tokens limit the window for stale role claims. Use a revocation cache (Redis) for immediate effect.

---

## Common Pitfalls

### Pitfall 1: Checking Route Permission but Not Resource Ownership
```
GET /orders/{id}  → user has orders:read ✓ → returns order for ANY id ✗
```
Always implement both layers.

### Pitfall 2: Hardcoding Admin User IDs
```python
if user_id == "admin_user_id_hardcoded": # NEVER do this
    return True
```
Always use role-based checks, never user ID-based hardcoding.

### Pitfall 3: Trusting User-Provided Role Claims Without Signature Verification
The JWT signature must be verified before trusting any claims. Never decode without verifying.

### Pitfall 4: Not Handling Missing Claims Gracefully
```javascript
// Bug: if roles is undefined, includes throws
if (req.user.roles.includes('admin')) { ... }

// Safe: use optional chaining
if ((req.user.roles ?? []).includes('admin')) { ... }
```

### Pitfall 5: Verbose Error Messages That Leak Information
```json
// Bad: tells the attacker the resource exists
{"error": "You don't have permission to access order 99"}

// Good: ambiguous
{"error": "Not found"}
```

### Pitfall 6: Over-Caching Role Assignments
If you cache role assignments in Redis for 24 hours, a revoked employee has access for up to 24 hours. Keep cache TTL aligned with your security policy (typically 5–15 minutes for sensitive systems).

### Pitfall 7: Not Testing Authorization Logic
Authorization bugs are security vulnerabilities. Test every role/permission combination, including negative cases (user without permission should get 403, user without ownership should get 404).

---

## Interview Questions & Answers

### Q1: What is the difference between RBAC and ABAC?

**Answer:**
RBAC assigns permissions to named roles, and users are assigned to roles. It's simple, fast, and works well when access patterns are predictable and don't depend on contextual factors. The trade-off is role explosion — when access needs to vary by many dimensions (department, region, data classification), you end up with hundreds of roles.

ABAC makes access decisions based on attributes of the subject (user), object (resource), action, and environment. It's more expressive — you can write policies like "allow if subject.clearance >= object.classification AND environment.time is business hours." The trade-off is complexity: policies are harder to reason about and audit, and the performance overhead is higher.

In practice, most systems use RBAC for coarse-grained access (route-level) and add ABAC-style attribute checks for fine-grained access (resource ownership, data classification). OPA unifies both under a single policy language (Rego).

---

### Q2: Should you store roles in JWT or look them up from DB on every request?

**Answer:**
There's a genuine trade-off. JWT-embedded roles have zero latency overhead but go stale — if you revoke a role, the user keeps it until the JWT expires. DB lookup is always fresh but adds a round-trip on every request, which is expensive at scale.

The production answer is a hybrid: embed roles in JWT for the fast path, and use a Redis revocation cache for immediate invalidation. On role change, write a short-lived key to Redis (`revoke:{user_id}`). Middleware checks Redis first (~1ms); on a cache hit, re-fetches from DB and issues a new token. This gives you the performance of JWT-embedded roles with the correctness of DB lookup.

Short JWT expiry (15–60 minutes) is also important — it bounds the maximum staleness window even without a revocation cache.

---

### Q3: How do you prevent a user from accessing another user's resource?

**Answer:**
This is the Broken Object Level Authorization (BOLA) problem — OWASP API Security Top 10 #1. There are three defense layers:

1. **SQL filter by owner**: Always add `WHERE user_id = $userID` to queries that return owned resources. Even if a developer forgets a handler-level check, the data layer won't return unauthorized rows.

2. **Handler-level ownership check**: After fetching the resource, compare `resource.user_id` against the authenticated `user.id` from the JWT (not from user-provided input). Return `404` (not `403`) to avoid leaking resource existence.

3. **Resource-scoped middleware**: For RESTful routes that operate on owned resources, extract the ownership check into reusable middleware that loads the resource, verifies ownership, and attaches it to the request context.

The most important principle: never trust user-supplied IDs in the request body for ownership purposes. Always use the identity from the verified JWT.

---

### Q4: What is OPA and when would you use it?

**Answer:**
OPA (Open Policy Agent) is a general-purpose policy engine that decouples policy from application code. You write policies in Rego (a declarative language), and OPA evaluates them given a JSON input. It can run as a sidecar (HTTP API), as a Go library (embedded), or as a Kubernetes admission controller.

Use OPA when:
- You have multiple services in different languages that need consistent policy enforcement
- Policies need to be authored, versioned, and deployed independently from application code (GitOps for policy)
- You need auditable policy decisions (OPA has a decision log)
- Your team has compliance requirements that demand a clear separation between code and policy
- You need complex ABAC-style policies that are difficult to express in application code

Avoid OPA when you have a single service with simple RBAC — the operational overhead (running OPA sidecar, writing Rego, managing bundle server) isn't justified for simple role checks.

---

### Q5: What is the difference between route-level and resource-level authorization?

**Answer:**
Route-level authorization answers: "is this user's role allowed to invoke this endpoint at all?" It's implemented in middleware and runs before the handler. For example, only `admin` role can call `DELETE /users/{id}`.

Resource-level authorization answers: "among the resources this endpoint can return, is the user allowed to access this specific one?" It runs inside the handler (or at the data layer). For example, a user with `orders:read` can call `GET /orders/{id}`, but should only be able to retrieve orders that belong to them.

Both are necessary. Route-level alone is insufficient — without resource-level checks, any user with `orders:read` can read any order by guessing IDs (BOLA vulnerability). Resource-level alone without route-level is also wrong — it would allow any authenticated user to attempt access to any route.

The correct architecture: route-level middleware filters by role/permission, resource-level checks filter by ownership, and the data layer enforces both.

---

## Resources

- [OWASP API Security Top 10 — BOLA](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
- [Open Policy Agent Documentation](https://www.openpolicyagent.org/docs/latest/)
- [Casbin Documentation](https://casbin.org/docs/overview)
- [NIST RBAC Model](https://csrc.nist.gov/projects/role-based-access-control)
- [JWT Best Practices (RFC 8725)](https://www.rfc-editor.org/rfc/rfc8725)
- [Google Zanzibar — Authorization System at Google Scale](https://research.google/pubs/pub48190/)
- [Auth0 — RBAC vs ABAC](https://auth0.com/docs/manage-users/access-control/rbac)

---

**Next:** [Part 6.1: Database Fundamentals](../part-06/06-database-fundamentals.md)
