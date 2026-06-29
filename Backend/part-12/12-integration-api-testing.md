# Part 12.2: Integration Testing & API Testing

## What You'll Learn
- The difference between unit, integration, and E2E tests — and when to use each
- Testcontainers: spin up real Docker containers (PostgreSQL, Redis, Kafka) for tests
- Full HTTP handler tests against a real database
- Testing authenticated endpoints with JWT
- Contract testing with Pact — catch breaking changes before deployment
- Load testing with k6 — stress, soak, and spike tests
- Test data management: factories, seeds, and realistic fake data

## Table of Contents
1. [Integration Testing — What and Why](#1-integration-testing--what-and-why)
2. [Testcontainers](#2-testcontainers)
3. [API/HTTP Testing Patterns](#3-apihttp-testing-patterns)
4. [Testing Authentication](#4-testing-authentication)
5. [Contract Testing](#5-contract-testing)
6. [Load Testing with k6](#6-load-testing-with-k6)
7. [Test Data Management](#7-test-data-management)
8. [Implementation Examples](#8-implementation-examples)
9. [Common Patterns & Best Practices](#9-common-patterns--best-practices)
10. [Common Pitfalls](#10-common-pitfalls)
11. [Interview Questions & Answers](#11-interview-questions--answers)
12. [Resources](#12-resources)

---

## 1. Integration Testing — What and Why

### The Gap Unit Tests Cannot Fill

Unit tests mock every dependency. They prove that your code logic is correct given controlled inputs. But they cannot prove:

- The SQL query actually returns the right rows in the right order
- The foreign key constraint prevents orphaned records
- The Redis TTL was set correctly
- Two services can actually talk to each other over HTTP

Integration tests fill this gap by testing your code against real (or realistic) external systems.

```
Unit test:
  BusinessLogic ←→ MockRepository
  ✓ Fast, isolated, deterministic
  ✗ Doesn't test actual SQL

Integration test:
  BusinessLogic ←→ RealRepository ←→ Real PostgreSQL (in Docker)
  ✓ Tests actual SQL, schema, constraints
  ✗ Slower, requires Docker
```

### The Integration Testing Spectrum

```
Level 1 — Component integration:
  Service + Real DB (no HTTP)
  Example: UserRepository integration test

Level 2 — Service integration:
  HTTP server + Real DB + Real Redis
  Example: POST /users creates row in DB AND warms cache

Level 3 — Contract integration:
  ServiceA ←→ ServiceB (via HTTP or message queue)
  Example: Order Service sends Kafka event, Payment Service consumes it
```

### When to Run Integration Tests

```
Developer workflow:
  ├── Every save:      Unit tests (milliseconds)
  ├── Pre-commit:      Unit + integration for changed packages
  └── CI (PR):         Full unit + integration test suite

Integration tests should complete in:
  ├── < 2 minutes:     Excellent
  ├── < 5 minutes:     Acceptable
  └── > 10 minutes:    Too slow — optimize or split
```

---

## 2. Testcontainers

Testcontainers is a library available in Go, Node.js, Python, Java, and more. It uses the Docker daemon to start containers programmatically during test setup and tear them down after.

### Why Not a Shared Test Database?

```
Problems with a shared test DB:
  ❌ State leaks between test runs (test A pollutes test B)
  ❌ Can't run tests in parallel (race conditions on shared tables)
  ❌ CI environments need a pre-configured DB service
  ❌ Different schema versions between developer machines
  ❌ "Works on my machine" — DB version mismatch

Problems testcontainers solves:
  ✓ Each test suite (or test) gets a fresh DB
  ✓ No pre-existing infrastructure required — just Docker
  ✓ Exact same DB version in dev and CI
  ✓ Parallel test suites each get their own isolated container
  ✓ Container is destroyed after tests — no cleanup
```

### Testcontainers Architecture

```
TestMain / Test Setup
       │
       ▼
testcontainers.RunContainer("postgres:16")
       │
       ▼
Docker daemon starts postgres:16 container
       │
       ▼
Container exposes mapped port (e.g., localhost:54321)
       │
       ▼
Test code connects: "postgresql://localhost:54321/testdb"
       │
       ▼
Run migrations (create schema)
       │
       ▼
Run tests against real PostgreSQL
       │
       ▼
container.Terminate() → Docker removes container
```

### Available Modules

- `testcontainers-go`: PostgreSQL, MySQL, Redis, Kafka, MongoDB, LocalStack, Elasticsearch
- `testcontainers-node`: Same set
- `testcontainers-python` (testcontainers): Same set

---

## 3. API/HTTP Testing Patterns

### What API Integration Tests Should Cover

```
✓ Happy path — correct request returns correct response
✓ Error cases — invalid request body, missing fields
✓ Authentication — unauthenticated request returns 401
✓ Authorization — unauthorized user gets 403
✓ Pagination — page 1, page 2, last page, empty page
✓ Idempotency — duplicate POST with same idempotency key
✓ Concurrent writes — race conditions (optimistic locking)
✓ Large inputs — what happens with 10,000 item array
✓ Database constraints — duplicate email returns 409, not 500
```

### Request/Response Assertion Depth

Don't just assert the status code. Assert:

```
Status code: 201
Content-Type: application/json
Body:
  ✓ data.id is a valid UUID
  ✓ data.email matches input email
  ✓ data.createdAt is a recent timestamp
  ✓ data.password is NOT in the response
  ✓ Location header points to /users/{id}
Database state (for write operations):
  ✓ Row exists in DB with correct values
  ✓ Password is hashed (bcrypt), not plaintext
  ✓ created_at is populated
```

### HTTP Mocking for External Services

When your service calls external APIs (Stripe, Twilio, SendGrid), you don't want to make real API calls in tests. Mock the external HTTP layer:

- **Go:** `httptest.NewServer()` — start a local HTTP server that responds to specific requests
- **Node.js:** `msw` (Mock Service Worker) or `nock` — intercept HTTP requests at the library level
- **Python:** `respx` (for httpx) or `responses` (for requests) — mock HTTP responses

```go
// Go: mock external HTTP server in tests
func TestPaymentService_Charge(t *testing.T) {
    // Start a local server that pretends to be Stripe
    stripeServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.URL.Path == "/v1/charges" && r.Method == "POST" {
            w.Header().Set("Content-Type", "application/json")
            w.WriteHeader(http.StatusOK)
            json.NewEncoder(w).Encode(map[string]interface{}{
                "id":     "ch_test_123",
                "status": "succeeded",
                "amount": 5000,
            })
            return
        }
        w.WriteHeader(http.StatusNotFound)
    }))
    defer stripeServer.Close()

    // Point your payment client at the mock server
    paymentClient := NewStripeClient(stripeServer.URL, "sk_test_fake")

    charge, err := paymentClient.Charge(context.Background(), &ChargeRequest{
        Amount: 5000,
        Token:  "tok_visa",
    })

    require.NoError(t, err)
    assert.Equal(t, "ch_test_123", charge.ID)
    assert.Equal(t, "succeeded", charge.Status)
}
```

### OpenAPI Spec Validation

Validate that every response conforms to your OpenAPI specification:

```javascript
// Node.js: validate responses against OpenAPI spec
const { OpenApiValidator } = require('express-openapi-validator');

// In integration tests:
const app = express();
app.use(OpenApiValidator.middleware({
    apiSpec: './openapi.yaml',
    validateRequests: true,
    validateResponses: true, // validates ALL responses against spec
}));
// If your handler returns a response that doesn't match the spec, the test fails
```

---

## 4. Testing Authentication

### JWT-Authenticated Test Requests

Tests that hit protected endpoints need to include a valid JWT. Don't use production secrets — generate test tokens with a known secret:

```go
// testhelpers/auth.go
package testhelpers

import (
    "time"
    "github.com/golang-jwt/jwt/v5"
)

const TestJWTSecret = "test-secret-do-not-use-in-production"

type TestClaims struct {
    UserID string `json:"user_id"`
    Role   string `json:"role"`
    jwt.RegisteredClaims
}

func GenerateTestToken(userID, role string) string {
    claims := TestClaims{
        UserID: userID,
        Role:   role,
        RegisteredClaims: jwt.RegisteredClaims{
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(1 * time.Hour)),
            IssuedAt:  jwt.NewNumericDate(time.Now()),
            Subject:   userID,
        },
    }
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    signed, _ := token.SignedString([]byte(TestJWTSecret))
    return signed
}

func GenerateAdminToken() string {
    return GenerateTestToken("admin-user-id", "admin")
}

func GenerateUserToken(userID string) string {
    return GenerateTestToken(userID, "user")
}
```

```go
// Usage in tests:
func TestOrderHandler_CreateOrder_Authenticated(t *testing.T) {
    token := testhelpers.GenerateUserToken("user-123")

    req := httptest.NewRequest("POST", "/orders", bytes.NewBufferString(`{
        "items": [{"product_id": "prod-1", "quantity": 1}]
    }`))
    req.Header.Set("Authorization", "Bearer "+token)
    req.Header.Set("Content-Type", "application/json")

    w := httptest.NewRecorder()
    router.ServeHTTP(w, req)

    assert.Equal(t, http.StatusCreated, w.Code)
}

func TestOrderHandler_CreateOrder_Unauthenticated(t *testing.T) {
    req := httptest.NewRequest("POST", "/orders", bytes.NewBufferString(`{}`))
    // No Authorization header
    w := httptest.NewRecorder()
    router.ServeHTTP(w, req)
    assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestOrderHandler_CreateOrder_WrongRole(t *testing.T) {
    // Regular user trying to access admin-only endpoint
    token := testhelpers.GenerateUserToken("user-123")
    req := httptest.NewRequest("DELETE", "/admin/orders/1", nil)
    req.Header.Set("Authorization", "Bearer "+token)
    w := httptest.NewRecorder()
    router.ServeHTTP(w, req)
    assert.Equal(t, http.StatusForbidden, w.Code)
}
```

### Testing Authorization Rules

```python
# Python: pytest parametrize across different auth scenarios
import pytest

@pytest.mark.parametrize("token_factory,expected_status", [
    (lambda: None,                  401),  # no token
    (lambda: "invalid.token.here", 401),  # invalid token
    (lambda: generate_expired_token(), 401),  # expired token
    (lambda: generate_user_token("user-1"), 403),  # wrong role (non-admin)
    (lambda: generate_admin_token(), 200),  # correct role
])
async def test_admin_endpoint_authorization(client, token_factory, expected_status):
    token = token_factory()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    response = await client.get("/admin/stats", headers=headers)
    assert response.status_code == expected_status
```

---

## 5. Contract Testing

### The Problem Contract Testing Solves

In a microservices architecture, Service A (Consumer) calls Service B (Provider) via HTTP. If Service B changes its response shape, Service A breaks. Without contract testing, you discover this in production.

```
Without contract testing:

  Order Service         Payment Service
  (Consumer)            (Provider)
       │                     │
       │  GET /charges/{id}  │
       │────────────────────►│
       │                     │
       │ { id, amount, status}│
       │◄────────────────────│
                             │
                  Dev adds field: status → payment_status
                             │
  Order Service breaks in production ← nobody noticed
```

```
With consumer-driven contract testing:

  Order Service         Pact Broker          Payment Service
  (Consumer)                                 (Provider)
       │                    │                     │
  1. Write consumer test    │                     │
       │                    │                     │
  2. Generates contract ────►                     │
     (pact file)            │                     │
                            │  3. Provider verifies
                            │◄────────────────────│
                            │    (CI gate)         │
  4. Contract violations ───►                     │
     block deployment       │                     │
```

### Pact — Consumer-Driven Contract Testing

**Consumer side** — defines what it expects from the provider:

```javascript
// consumer/tests/paymentService.pact.test.js
const { Pact } = require('@pact-foundation/pact');
const path = require('path');
const { PaymentClient } = require('../src/clients/paymentClient');

const provider = new Pact({
    consumer: 'OrderService',
    provider: 'PaymentService',
    port: 1234,
    log: path.resolve(process.cwd(), 'logs', 'pact.log'),
    dir: path.resolve(process.cwd(), 'pacts'),
    logLevel: 'warn',
});

describe('PaymentService Pact', () => {
    beforeAll(() => provider.setup());
    afterAll(() => provider.finalize());
    afterEach(() => provider.verify());

    describe('GET /charges/:id', () => {
        it('returns charge details', async () => {
            // Define what the consumer expects
            await provider.addInteraction({
                state: 'charge ch_123 exists',
                uponReceiving: 'a request for charge ch_123',
                withRequest: {
                    method: 'GET',
                    path: '/charges/ch_123',
                    headers: { Accept: 'application/json' },
                },
                willRespondWith: {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' },
                    body: {
                        id: 'ch_123',
                        amount: 5000,
                        status: 'succeeded',
                        // NOTE: using matchers instead of exact values
                        // This makes the contract flexible
                        createdAt: Pact.Matchers.iso8601DateTime(),
                    },
                },
            });

            const client = new PaymentClient('http://localhost:1234');
            const charge = await client.getCharge('ch_123');

            expect(charge.id).toBe('ch_123');
            expect(charge.status).toBe('succeeded');
        });
    });
});
// After running, generates pacts/OrderService-PaymentService.json
// Publish to Pact Broker for provider verification
```

**Provider side** — verifies it can fulfill the contract:

```javascript
// provider/tests/pactVerification.test.js
const { Verifier } = require('@pact-foundation/pact');
const app = require('../src/app');

describe('PaymentService Pact Verification', () => {
    it('validates all consumer contracts', async () => {
        const server = app.listen(3001);

        await new Verifier({
            providerBaseUrl: 'http://localhost:3001',
            pactBrokerUrl: process.env.PACT_BROKER_URL,
            publishVerificationResult: true,
            providerVersion: process.env.GIT_SHA,

            // State handlers — set up DB state for each "state" the consumer defined
            stateHandlers: {
                'charge ch_123 exists': async () => {
                    await db.charges.upsert({
                        id: 'ch_123',
                        amount: 5000,
                        status: 'succeeded',
                    });
                },
                'charge ch_999 does not exist': async () => {
                    await db.charges.delete({ id: 'ch_999' });
                },
            },
        }).verifyProvider();

        server.close();
    });
});
```

### Contract Testing Without Pact — Schema Validation

A lighter-weight approach: validate responses against a JSON Schema or TypeScript type:

```javascript
// Validate every response matches the expected schema
const Ajv = require('ajv');
const ajv = new Ajv();

const chargeSchema = {
    type: 'object',
    required: ['id', 'amount', 'status'],
    properties: {
        id: { type: 'string', pattern: '^ch_' },
        amount: { type: 'integer', minimum: 0 },
        status: { type: 'string', enum: ['succeeded', 'pending', 'failed'] },
    },
    additionalProperties: false, // catch unexpected fields
};

const validate = ajv.compile(chargeSchema);

test('GET /charges/:id matches schema', async () => {
    const response = await request(app).get('/charges/ch_123');
    expect(response.status).toBe(200);
    const valid = validate(response.body);
    if (!valid) {
        throw new Error(`Schema validation failed: ${JSON.stringify(validate.errors)}`);
    }
});
```

---

## 6. Load Testing with k6

### k6 Overview

k6 is a developer-friendly load testing tool. Scripts are written in JavaScript. Tests run from the CLI and output performance metrics.

```bash
# Install
brew install k6

# Run a test
k6 run load-test.js

# Run with options
k6 run --vus 100 --duration 30s load-test.js
```

### Basic k6 Test Structure

```javascript
// load-tests/create-order.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('error_rate');
const orderCreationDuration = new Trend('order_creation_duration', true);
const ordersCreated = new Counter('orders_created');

// Test configuration
export const options = {
    stages: [
        { duration: '30s', target: 10 },   // ramp up to 10 VUs over 30s
        { duration: '2m',  target: 10 },   // hold at 10 VUs for 2 minutes
        { duration: '30s', target: 100 },  // ramp up to 100 VUs
        { duration: '2m',  target: 100 },  // hold at 100 VUs
        { duration: '30s', target: 0 },    // ramp down
    ],
    thresholds: {
        // Test fails if these are not met
        http_req_duration: ['p(95)<500'],   // 95th percentile < 500ms
        http_req_failed:   ['rate<0.01'],   // error rate < 1%
        error_rate:        ['rate<0.01'],
    },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export function setup() {
    // Runs once before the test — create test data, get auth tokens
    const loginRes = http.post(`${BASE_URL}/auth/login`, JSON.stringify({
        email: 'loadtest@example.com',
        password: 'loadtest_password',
    }), { headers: { 'Content-Type': 'application/json' } });

    return { token: loginRes.json('token') };
}

export default function (data) {
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${data.token}`,
    };

    // Scenario: create an order
    const payload = JSON.stringify({
        items: [{ productId: 'prod-1', quantity: 1, price: 29.99 }],
        paymentToken: 'tok_visa',
    });

    const start = Date.now();
    const res = http.post(`${BASE_URL}/orders`, payload, { headers });
    const duration = Date.now() - start;

    // Assert and record metrics
    const success = check(res, {
        'status is 201': (r) => r.status === 201,
        'has order id': (r) => r.json('data.id') !== undefined,
        'response time < 500ms': () => duration < 500,
    });

    errorRate.add(!success);
    orderCreationDuration.add(duration);
    if (success) ordersCreated.add(1);

    sleep(1); // think time between requests
}

export function teardown(data) {
    // Cleanup: delete test data created during setup
    http.del(`${BASE_URL}/test/cleanup`, null, {
        headers: { 'Authorization': `Bearer ${data.token}` }
    });
}
```

### Types of Load Tests

**Smoke test — sanity check at minimal load:**
```javascript
export const options = {
    vus: 1,
    duration: '1m',
    thresholds: { http_req_failed: ['rate<0.01'] },
};
// Run before every deployment to verify basic functionality
```

**Load test — expected production traffic:**
```javascript
export const options = {
    stages: [
        { duration: '1m', target: 50 },   // ramp up
        { duration: '3m', target: 50 },   // sustain
        { duration: '1m', target: 0 },    // ramp down
    ],
};
```

**Stress test — find the breaking point:**
```javascript
export const options = {
    stages: [
        { duration: '2m', target: 100 },
        { duration: '5m', target: 100 },
        { duration: '2m', target: 200 },
        { duration: '5m', target: 200 },
        { duration: '2m', target: 300 },
        { duration: '5m', target: 300 },
        // Continue until errors spike
    ],
};
```

**Spike test — sudden traffic surge:**
```javascript
export const options = {
    stages: [
        { duration: '10s', target: 1 },    // baseline
        { duration: '1m',  target: 500 },  // sudden spike
        { duration: '3m',  target: 500 },  // sustain spike
        { duration: '1m',  target: 1 },    // recover
        { duration: '3m',  target: 1 },    // verify recovery
    ],
};
```

**Soak test — extended duration to catch memory leaks:**
```javascript
export const options = {
    stages: [
        { duration: '5m',  target: 50 },
        { duration: '4h',  target: 50 },  // 4 hours at 50 VUs
        { duration: '5m',  target: 0 },
    ],
};
// Watch for: memory growth, connection pool exhaustion, request duration drift
```

### Analyzing k6 Results

```
          /\      Execution: local
         /  \     Script:    load-test.js
        / k6 \    Output:    -
       /______\
                   scenarios: (100.00%) 1 scenario, 100 max VUs

     ✓ status is 201
     ✓ has order id
     ✗ response time < 500ms
       ↳  92% — ✓ 1840 / ✗ 160

     checks.........................: 97.33% ✓ 5840 ✗ 160
     data_received..................: 4.2 MB 14 kB/s
     data_sent......................: 1.8 MB 6.0 kB/s
     http_req_blocked...............: avg=1.52ms  min=1µs    med=3µs    max=1.28s  p(90)=5µs   p(95)=9µs
     http_req_connecting............: avg=1.52ms  min=0s     med=0s     max=1.28s  p(90)=0s    p(95)=0s
   ✗ http_req_duration..............: avg=389ms   min=124ms  med=340ms  max=2.1s   p(90)=701ms p(95)=843ms
       { expected_response:true }...: avg=374ms   min=124ms  med=330ms  max=1.9s   p(90)=685ms p(95)=823ms
     http_req_failed................: 0.50%  ✓ 10    ✗ 1990
     http_req_receiving.............: avg=57.3µs  min=11µs   med=40µs   max=4.2ms  p(90)=116µs p(95)=163µs
     http_req_sending...............: avg=25.1µs  min=8µs    med=19µs   max=1.94ms p(90)=45µs  p(95)=60µs
     http_req_tls_handshaking.......: avg=0s      min=0s     med=0s     max=0s     p(90)=0s    p(95)=0s
     http_req_waiting...............: avg=389ms   min=123ms  med=340ms  max=2.1s   p(90)=700ms p(95)=842ms
     http_reqs......................: 2000   66.6/s
     iterations.....................: 2000   66.6/s
     vus............................: 100    min=100   max=100
     vus_max........................: 100    min=100   max=100

Key metrics to analyze:
  p(50) / median   — typical user experience
  p(90)            — most users (9 out of 10) experience this or better
  p(95)            — SLA metric — 95th percentile latency
  p(99)            — tail latency — worst 1% of users
  error_rate       — % of requests that failed
  throughput (RPS) — requests per second the system handled
```

**What to look for:**
- `p(95)` > SLA target → performance regression
- `http_req_failed` rate > 0.1% → reliability issue
- Latency that increases linearly with VUs → queuing (not enough concurrency)
- Latency that spikes suddenly → hitting a hard limit (connection pool, memory)

---

## 7. Test Data Management

### Test Fixtures — Seed Data for Integration Tests

```go
// testhelpers/fixtures.go
package testhelpers

import (
    "context"
    "myapp/models"
    "myapp/repositories"
)

type Fixtures struct {
    db *pgxpool.Pool
}

func NewFixtures(db *pgxpool.Pool) *Fixtures {
    return &Fixtures{db: db}
}

// CreateUser inserts a user and returns it — use in test setup
func (f *Fixtures) CreateUser(ctx context.Context, overrides ...func(*models.CreateUserInput)) *models.User {
    input := &models.CreateUserInput{
        Name:     "Test User",
        Email:    fmt.Sprintf("test-%s@example.com", uuid.NewString()[:8]),
        Password: "hashed_password",
        Role:     "user",
    }
    for _, override := range overrides {
        override(input)
    }

    repo := repositories.NewUserRepo(f.db)
    user, err := repo.Create(ctx, input)
    if err != nil {
        panic(fmt.Sprintf("fixture CreateUser failed: %v", err))
    }
    return user
}

func (f *Fixtures) CreateAdminUser(ctx context.Context) *models.User {
    return f.CreateUser(ctx, func(u *models.CreateUserInput) {
        u.Role = "admin"
        u.Email = "admin@example.com"
    })
}

func (f *Fixtures) CreateProduct(ctx context.Context, overrides ...func(*models.Product)) *models.Product {
    // ...
}
```

### Factory Pattern for Test Objects

```javascript
// testHelpers/factories.js
const { faker } = require('@faker-js/faker');

const UserFactory = {
    build(overrides = {}) {
        return {
            id: faker.string.uuid(),
            name: faker.person.fullName(),
            email: faker.internet.email(),
            role: 'user',
            createdAt: faker.date.recent(),
            ...overrides,
        };
    },

    buildList(count, overrides = {}) {
        return Array.from({ length: count }, () => this.build(overrides));
    },
};

const OrderFactory = {
    build(overrides = {}) {
        const quantity = faker.number.int({ min: 1, max: 5 });
        const price = parseFloat(faker.commerce.price({ min: 10, max: 500 }));
        return {
            id: faker.string.uuid(),
            userId: faker.string.uuid(),
            items: [
                {
                    productId: faker.string.uuid(),
                    name: faker.commerce.productName(),
                    quantity,
                    price,
                    subtotal: quantity * price,
                },
            ],
            status: 'pending',
            total: quantity * price,
            createdAt: faker.date.recent(),
            ...overrides,
        };
    },
};

module.exports = { UserFactory, OrderFactory };
```

### Faker — Realistic Test Data

```python
# testhelpers/factories.py
from faker import Faker
from decimal import Decimal
import random

fake = Faker()


def make_user(**overrides) -> dict:
    return {
        "id": fake.uuid4(),
        "name": fake.name(),
        "email": fake.email(),
        "role": "user",
        "created_at": fake.date_time_this_year().isoformat(),
        **overrides,
    }


def make_order(**overrides) -> dict:
    quantity = random.randint(1, 5)
    price = Decimal(str(round(random.uniform(10, 500), 2)))
    return {
        "id": fake.uuid4(),
        "user_id": fake.uuid4(),
        "items": [
            {
                "product_id": fake.uuid4(),
                "name": fake.catch_phrase(),
                "quantity": quantity,
                "price": str(price),
                "subtotal": str(price * quantity),
            }
        ],
        "status": "pending",
        "total": str(price * quantity),
        **overrides,
    }


def make_list(factory, count: int, **overrides) -> list:
    return [factory(**overrides) for _ in range(count)]
```

### Test Database Isolation Strategies

```
Strategy 1: Truncate tables between tests
  ✓ Clean state per test
  ✓ Simple implementation
  ✗ Slow for many tables

Strategy 2: Transaction rollback
  ✓ Very fast (no actual writes)
  ✓ Clean state per test
  ✗ Doesn't test COMMIT behavior
  ✗ Doesn't work with code that uses multiple connections

Strategy 3: Separate schema per test
  ✓ True isolation
  ✗ Complex setup

Strategy 4: Fresh container per test suite
  ✓ Total isolation
  ✗ Slowest (container startup time)
  → Use testcontainers with module-scope setup
```

---

## 8. Implementation Examples

### Go + Chi: Integration Test with Testcontainers

```go
// tests/integration/user_api_test.go
package integration_test

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "net/http/httptest"
    "os"
    "testing"

    "github.com/jackc/pgx/v5/pgxpool"
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
    "github.com/testcontainers/testcontainers-go"
    "github.com/testcontainers/testcontainers-go/modules/postgres"
    "github.com/testcontainers/testcontainers-go/wait"

    "myapp/handlers"
    "myapp/repositories"
    "myapp/router"
    "myapp/services"
    "myapp/testhelpers"
)

var (
    testDB  *pgxpool.Pool
    testApp http.Handler
)

func TestMain(m *testing.M) {
    ctx := context.Background()

    // Start PostgreSQL container
    pg, err := postgres.RunContainer(ctx,
        testcontainers.WithImage("postgres:16-alpine"),
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("testuser"),
        postgres.WithPassword("testpass"),
        testcontainers.WithWaitStrategy(
            wait.ForLog("database system is ready to accept connections").
                WithOccurrence(2).
                WithStartupTimeout(60 * time.Second),
        ),
    )
    if err != nil {
        fmt.Printf("failed to start postgres: %v\n", err)
        os.Exit(1)
    }
    defer pg.Terminate(ctx)

    connStr, err := pg.ConnectionString(ctx, "sslmode=disable")
    if err != nil {
        fmt.Printf("failed to get connection string: %v\n", err)
        os.Exit(1)
    }

    testDB, err = pgxpool.New(ctx, connStr)
    if err != nil {
        fmt.Printf("failed to connect: %v\n", err)
        os.Exit(1)
    }
    defer testDB.Close()

    // Run migrations
    if err := runMigrations(connStr); err != nil {
        fmt.Printf("migrations failed: %v\n", err)
        os.Exit(1)
    }

    // Build the full app with real dependencies
    userRepo := repositories.NewPostgresUserRepo(testDB)
    userSvc  := services.NewUserService(userRepo)
    userHdlr := handlers.NewUserHandler(userSvc)
    testApp  = router.Build(userHdlr)

    os.Exit(m.Run())
}

func truncateAllTables(t *testing.T) {
    t.Helper()
    _, err := testDB.Exec(context.Background(),
        "TRUNCATE TABLE users, orders, order_items RESTART IDENTITY CASCADE")
    require.NoError(t, err)
}

func TestCreateUser_Integration(t *testing.T) {
    truncateAllTables(t)

    body := `{"name": "Alice Smith", "email": "alice@example.com", "password": "secure123"}`

    req := httptest.NewRequest("POST", "/users", bytes.NewBufferString(body))
    req.Header.Set("Content-Type", "application/json")
    w := httptest.NewRecorder()

    testApp.ServeHTTP(w, req)

    // Assert HTTP response
    require.Equal(t, http.StatusCreated, w.Code)
    assert.Equal(t, "application/json", w.Header().Get("Content-Type"))

    var resp map[string]interface{}
    json.NewDecoder(w.Body).Decode(&resp)

    data := resp["data"].(map[string]interface{})
    assert.NotEmpty(t, data["id"])
    assert.Equal(t, "alice@example.com", data["email"])
    assert.Nil(t, data["password"]) // password must NOT be in response

    // Assert database state
    var count int
    err := testDB.QueryRow(context.Background(),
        "SELECT COUNT(*) FROM users WHERE email = $1", "alice@example.com").Scan(&count)
    require.NoError(t, err)
    assert.Equal(t, 1, count)

    // Assert password was hashed
    var storedPassword string
    err = testDB.QueryRow(context.Background(),
        "SELECT password FROM users WHERE email = $1", "alice@example.com").Scan(&storedPassword)
    require.NoError(t, err)
    assert.NotEqual(t, "secure123", storedPassword)
    assert.True(t, strings.HasPrefix(storedPassword, "$2"), "expected bcrypt hash")
}

func TestCreateUser_DuplicateEmail_Returns409(t *testing.T) {
    truncateAllTables(t)

    // Create the first user
    body := `{"name": "Alice", "email": "alice@example.com", "password": "pass123"}`
    req := httptest.NewRequest("POST", "/users", bytes.NewBufferString(body))
    req.Header.Set("Content-Type", "application/json")
    w := httptest.NewRecorder()
    testApp.ServeHTTP(w, req)
    require.Equal(t, http.StatusCreated, w.Code)

    // Try to create a duplicate
    req2 := httptest.NewRequest("POST", "/users", bytes.NewBufferString(body))
    req2.Header.Set("Content-Type", "application/json")
    w2 := httptest.NewRecorder()
    testApp.ServeHTTP(w2, req2)

    assert.Equal(t, http.StatusConflict, w2.Code)
    var resp map[string]interface{}
    json.NewDecoder(w2.Body).Decode(&resp)
    assert.Equal(t, "CONFLICT", resp["error"].(map[string]interface{})["code"])
}

func TestGetUser_Authenticated(t *testing.T) {
    truncateAllTables(t)

    // Create a user in the DB directly
    fixtures := testhelpers.NewFixtures(testDB)
    user := fixtures.CreateUser(context.Background())

    // Generate test token for that user
    token := testhelpers.GenerateTestToken(user.ID, "user")

    req := httptest.NewRequest("GET", "/users/"+user.ID, nil)
    req.Header.Set("Authorization", "Bearer "+token)
    w := httptest.NewRecorder()
    testApp.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)

    var resp map[string]interface{}
    json.NewDecoder(w.Body).Decode(&resp)
    data := resp["data"].(map[string]interface{})
    assert.Equal(t, user.ID, data["id"])
}

func TestGetUser_Unauthenticated_Returns401(t *testing.T) {
    req := httptest.NewRequest("GET", "/users/some-id", nil)
    w := httptest.NewRecorder()
    testApp.ServeHTTP(w, req)
    assert.Equal(t, http.StatusUnauthorized, w.Code)
}
```

---

### Node.js + Express: Integration Test with Testcontainers

```javascript
// tests/integration/userApi.integration.test.js
const { GenericContainer, Wait } = require('testcontainers');
const request = require('supertest');
const { Pool } = require('pg');
const { buildApp } = require('../../src/app');
const { runMigrations } = require('../../src/db/migrations');
const jwt = require('jsonwebtoken');

const TEST_JWT_SECRET = 'test-secret';

let pgContainer;
let pool;
let app;

beforeAll(async () => {
    // Start PostgreSQL container
    pgContainer = await new GenericContainer('postgres:16-alpine')
        .withEnvironment({
            POSTGRES_DB: 'testdb',
            POSTGRES_USER: 'testuser',
            POSTGRES_PASSWORD: 'testpass',
        })
        .withExposedPorts(5432)
        .withWaitStrategy(Wait.forLogMessage('database system is ready to accept connections', 2))
        .start();

    const host = pgContainer.getHost();
    const port = pgContainer.getMappedPort(5432);
    const connStr = `postgresql://testuser:testpass@${host}:${port}/testdb`;

    pool = new Pool({ connectionString: connStr });
    await runMigrations(connStr);

    app = buildApp({ db: pool, jwtSecret: TEST_JWT_SECRET });
}, 60000); // 60s timeout for container startup

afterAll(async () => {
    await pool.end();
    await pgContainer.stop();
});

beforeEach(async () => {
    await pool.query('TRUNCATE users, orders RESTART IDENTITY CASCADE');
});

function generateToken(userId, role = 'user') {
    return jwt.sign(
        { userId, role, sub: userId },
        TEST_JWT_SECRET,
        { expiresIn: '1h' }
    );
}

describe('POST /users', () => {
    test('creates user and returns 201', async () => {
        const response = await request(app)
            .post('/users')
            .send({ name: 'Alice', email: 'alice@example.com', password: 'secure123' })
            .expect(201)
            .expect('Content-Type', /json/);

        expect(response.body.data.id).toBeDefined();
        expect(response.body.data.email).toBe('alice@example.com');
        expect(response.body.data.password).toBeUndefined(); // never leak password

        // Verify DB state
        const { rows } = await pool.query(
            'SELECT * FROM users WHERE email = $1',
            ['alice@example.com']
        );
        expect(rows).toHaveLength(1);
        expect(rows[0].password).toMatch(/^\$2b\$/); // bcrypt hash
    });

    test('returns 409 on duplicate email', async () => {
        await request(app)
            .post('/users')
            .send({ name: 'Alice', email: 'alice@example.com', password: 'pass1' })
            .expect(201);

        const response = await request(app)
            .post('/users')
            .send({ name: 'Alice2', email: 'alice@example.com', password: 'pass2' })
            .expect(409);

        expect(response.body.error.code).toBe('CONFLICT');
    });

    test('returns 422 on invalid email', async () => {
        const response = await request(app)
            .post('/users')
            .send({ name: 'Bob', email: 'notanemail', password: 'pass' })
            .expect(422);

        expect(response.body.error.code).toBe('VALIDATION_ERROR');
        expect(response.body.error.fields).toContainEqual(
            expect.objectContaining({ field: 'email' })
        );
    });
});

describe('GET /users/:id (authenticated)', () => {
    test('returns 200 with user data when authenticated', async () => {
        // Create user directly in DB
        const { rows } = await pool.query(
            'INSERT INTO users (name, email, password, role) VALUES ($1, $2, $3, $4) RETURNING *',
            ['Alice', 'alice@example.com', '$2b$10$hashedpw', 'user']
        );
        const user = rows[0];

        const token = generateToken(user.id);

        const response = await request(app)
            .get(`/users/${user.id}`)
            .set('Authorization', `Bearer ${token}`)
            .expect(200);

        expect(response.body.data.id).toBe(user.id);
        expect(response.body.data.email).toBe('alice@example.com');
        expect(response.body.data.password).toBeUndefined();
    });

    test('returns 401 without token', async () => {
        await request(app).get('/users/some-id').expect(401);
    });

    test('returns 403 when accessing other user as non-admin', async () => {
        const token = generateToken('user-1', 'user');

        await request(app)
            .get('/users/user-2') // different user
            .set('Authorization', `Bearer ${token}`)
            .expect(403);
    });
});
```

---

### Python + FastAPI: Integration Test with Testcontainers

```python
# tests/integration/test_user_api.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from main import app
from db.base import Base
from db.session import get_db
from testhelpers.auth import generate_test_token
from testhelpers.factories import make_user


@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="module")
def db_url(postgres_container):
    return postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )


@pytest.fixture(scope="module")
async def engine(db_url):
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()  # rollback after each test


@pytest.fixture(scope="function")
async def client(db_session):
    """Override DB dependency to use test session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_user_returns_201(client, db_session):
    payload = {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "password": "secure123!",
    }

    response = await client.post("/users", json=payload)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id"] is not None
    assert data["email"] == "alice@example.com"
    assert "password" not in data  # never leak password

    # Verify DB state
    from sqlalchemy import text
    result = await db_session.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": "alice@example.com"}
    )
    row = result.fetchone()
    assert row is not None
    assert row.password != "secure123!"  # must be hashed


@pytest.mark.asyncio
async def test_create_user_duplicate_email_returns_409(client):
    payload = {"name": "Alice", "email": "alice@example.com", "password": "pass123"}
    await client.post("/users", json=payload)

    response = await client.post("/users", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_get_user_authenticated(client, db_session):
    # Create user via the API
    create_resp = await client.post("/users", json={
        "name": "Bob", "email": "bob@example.com", "password": "pass123"
    })
    user_id = create_resp.json()["data"]["id"]

    # Generate a token for that user
    token = generate_test_token(user_id, role="user")

    response = await client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == user_id


@pytest.mark.asyncio
async def test_get_user_unauthenticated_returns_401(client):
    response = await client.get("/users/some-id")
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,expected_field", [
    ({"name": "Bob", "password": "pass"},             "email"),
    ({"name": "Bob", "email": "notanemail", "password": "pass"}, "email"),
    ({"email": "bob@example.com", "password": "pass"}, "name"),
])
async def test_create_user_validation_errors(client, payload, expected_field):
    response = await client.post("/users", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    field_names = [f["field"] for f in error.get("fields", [])]
    assert expected_field in field_names
```

---

## 9. Common Patterns & Best Practices

### Pattern 1: Test at the HTTP Boundary for Integration Tests

For integration tests, test through the full HTTP stack — not the handler directly, not the service directly. This tests routing, middleware, authentication, serialization, and business logic all together.

### Pattern 2: Don't Use `sleep()` in Tests — Use Polling or Events

```go
// BAD — fragile, timing-dependent
go processOrder(order)
time.Sleep(500 * time.Millisecond) // hope that's enough time
assert.Equal(t, "processed", getOrderStatus(order.ID))

// GOOD — poll with timeout
require.Eventually(t, func() bool {
    return getOrderStatus(order.ID) == "processed"
}, 5*time.Second, 50*time.Millisecond)
```

### Pattern 3: Run Integration Tests with Build Tags

```go
//go:build integration

package integration_test

// Only compiled and run with: go test -tags=integration ./...
// Regular unit tests run without the tag: go test ./...
```

### Pattern 4: Separate Test Databases for Each CI Job

In CI (GitHub Actions, CircleCI), each parallel job should get its own container. Use testcontainers — each job starts its own isolated PostgreSQL container. No shared state, no port conflicts.

### Pattern 5: Test the Edge Cases of Pagination

```javascript
test('returns empty array for page beyond last page', async () => {
    // Create 5 users
    for (let i = 0; i < 5; i++) {
        await createUser(pool, UserFactory.build());
    }

    // Request page 10 (way beyond last page)
    const response = await request(app)
        .get('/users?page=10&limit=10')
        .set('Authorization', `Bearer ${adminToken}`);

    expect(response.status).toBe(200);
    expect(response.body.data).toEqual([]);
    expect(response.body.pagination.total).toBe(5);
    expect(response.body.pagination.hasNextPage).toBe(false);
});
```

---

## 10. Common Pitfalls

### Pitfall 1: Testcontainers Not Waiting for Readiness

```go
// BAD — container started but DB not ready
pg, _ := postgres.RunContainer(ctx, testcontainers.WithImage("postgres:16"))
// Connect immediately — gets "connection refused" or "DB not ready"

// GOOD — wait for DB to be ready
pg, _ := postgres.RunContainer(ctx,
    testcontainers.WithImage("postgres:16"),
    testcontainers.WithWaitStrategy(
        wait.ForLog("database system is ready to accept connections").WithOccurrence(2),
    ),
)
```

### Pitfall 2: Shared Container State Between Tests

When tests run in parallel and share a container, tests must be truly independent. Truncating all tables between tests works. Using `TRUNCATE ... RESTART IDENTITY CASCADE` resets auto-increment sequences too.

### Pitfall 3: Integration Tests That Mirror Unit Tests

Integration tests should cover what unit tests can't:
- Real DB constraints (unique, FK, check constraints)
- Real SQL semantics (ordering, pagination)
- Middleware interaction (auth, request ID)

Don't write an integration test for a 400 "email invalid" case — that's for unit tests. Write an integration test for "duplicate email causes 409 from DB unique constraint".

### Pitfall 4: Hard-coded Sleep in Load Tests

```javascript
// BAD — fixed think time that may not reflect real traffic
sleep(1); // always wait 1 second

// BETTER — variable think time modeled on real user behavior
sleep(Math.random() * 2 + 0.5); // 0.5 to 2.5 seconds
```

### Pitfall 5: Load Test Without Warmup

```javascript
// BAD — jump immediately to full load
export const options = { vus: 500, duration: '5m' };

// GOOD — ramp up to let connection pools stabilize
export const options = {
    stages: [
        { duration: '1m', target: 50 },   // warmup
        { duration: '3m', target: 500 },  // ramp to full load
        { duration: '5m', target: 500 },  // sustained load
        { duration: '1m', target: 0 },
    ],
};
```

### Pitfall 6: Not Testing Response Shape — Only Status Code

```javascript
// BAD — only checks status
expect(response.status).toBe(201);

// GOOD — checks shape and specific fields
expect(response.status).toBe(201);
expect(response.body.data.id).toMatch(/^[0-9a-f-]{36}$/); // UUID
expect(response.body.data.email).toBe(input.email);
expect(response.body.data.password).toBeUndefined(); // security check
expect(response.headers['location']).toBe(`/users/${response.body.data.id}`);
```

---

## 11. Interview Questions & Answers

### Q1: What is the difference between unit testing and integration testing?

**Answer:**

**Unit tests** test a single function or class in complete isolation. All external dependencies (databases, HTTP clients, caches) are replaced with mocks or stubs. Unit tests are fast (milliseconds), deterministic, and pinpoint the exact function that broke.

**Integration tests** test multiple components working together against real (or realistic) external systems. They verify that SQL queries return correct results, that DB constraints are enforced, that middleware works correctly, that serialization is correct end-to-end.

**Key distinctions:**
| | Unit | Integration |
|---|---|---|
| Speed | Milliseconds | Seconds |
| External deps | Mocked | Real (or testcontainers) |
| What they catch | Logic bugs | SQL bugs, schema bugs, config bugs |
| Failure isolation | Pinpoints exact line | May require investigation |
| When to run | Every save | Per commit / pre-merge |

Neither replaces the other — you need both.

---

### Q2: What is testcontainers and when would you use it?

**Answer:** Testcontainers is a library that programmatically starts Docker containers in test setup code and stops them after tests complete.

**When to use:**
- Integration tests that need a real PostgreSQL, MySQL, Redis, Kafka, or Elasticsearch
- When you need to test actual DB behavior (constraints, indexes, query results) rather than mocked behavior
- When SQLite is insufficient (missing PostgreSQL features like JSON operators, window functions)
- In CI pipelines — no pre-configured DB service needed, just Docker

**How it works:**
1. `TestMain` (or equivalent setup) calls `postgres.RunContainer(ctx, ...)`
2. Testcontainers calls `docker run postgres:16 ...` under the hood
3. Waits for readiness signal (log line or TCP port)
4. Returns connection details (host, mapped port)
5. Tests connect to this instance
6. After tests, `container.Terminate()` calls `docker stop && docker rm`

**Trade-off:** Requires Docker at test time. Adds 5-20 seconds of startup overhead per test suite, but this is acceptable for integration tests.

---

### Q3: What is contract testing and how does it help in a microservices system?

**Answer:** Contract testing verifies that a service consumer and a service provider agree on the API contract — the request/response shape, status codes, and behavior.

**Consumer-driven contract testing (Pact):**
1. The **Consumer** (e.g., Order Service) writes tests that define what it expects from the Provider (e.g., Payment Service)
2. Running these tests generates a **Pact file** (the contract)
3. The contract is shared with the Provider via a **Pact Broker**
4. The **Provider** runs verification tests against the contract — it sets up the required state and verifies its responses match what the consumer expects
5. If the Provider breaks the contract, the build fails **before deployment**

**How it helps:**
- Catch breaking changes before they reach production
- Remove the need for integrated E2E tests to verify service compatibility
- Give teams confidence to deploy independently
- Document service interfaces as executable tests

**Example:** Order Service expects `{ id, amount, status }`. Payment team renames `status` to `payment_status`. Without contract testing, Order Service breaks in production. With contract testing, the Provider verification step fails in CI, blocking the deployment.

---

### Q4: How do you test authenticated endpoints?

**Answer:** Three steps:

1. **Use a known test JWT secret** — configure your test environment to use a fixed JWT secret (different from production). Never hardcode production secrets in tests.

2. **Create a test token generator** — a helper function that generates signed JWTs with specific user IDs and roles:
```go
func generateTestToken(userID, role string) string {
    claims := Claims{UserID: userID, Role: role, /* ... */}
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    signed, _ := token.SignedString([]byte(testJWTSecret))
    return signed
}
```

3. **Test multiple authorization scenarios** — don't just test the happy path. Test:
   - No token → 401
   - Expired token → 401
   - Invalid signature → 401
   - Valid token, wrong role → 403
   - Valid token, correct role → 200/201

This ensures your auth middleware correctly rejects bad tokens AND correctly authorizes good ones.

---

### Q5: What metrics do you look at in a load test?

**Answer:** The key metrics from a k6 (or similar) load test:

**Latency percentiles:**
- `p(50)` / median — typical user experience. If this is high, most users are affected.
- `p(95)` — your SLA metric. "95% of requests complete within Xms." Compare against your SLA.
- `p(99)` — tail latency. The worst 1% of users. High p(99) with low p(50) suggests occasional spikes.

**Error metrics:**
- `http_req_failed` — percentage of requests that returned an error. Anything above 0.1% in production is alarming.
- Error rate by status code — distinguish 4xx (client errors, usually expected) from 5xx (server errors, never expected).

**Throughput:**
- Requests per second (RPS) — how much load the system handled. Compare to your expected traffic.

**Resource metrics (from your monitoring system, not k6):**
- CPU, memory, connection pool utilization at peak load
- Database connection count
- Goroutine count / thread count — are they climbing continuously? (leak)

**What to look for:**
- Latency that increases with VU count → queuing — not enough capacity
- Error rate spike at certain VU count → found the breaking point
- Memory that grows continuously during soak test → memory leak
- p(99) much higher than p(95) → occasional slow requests (GC pause, lock contention)

---

## 12. Resources

- [testcontainers-go](https://golang.testcontainers.org/)
- [testcontainers-node](https://node.testcontainers.org/)
- [testcontainers-python](https://testcontainers-python.readthedocs.io/)
- [k6 Documentation](https://k6.io/docs/)
- [Pact Foundation — contract testing](https://docs.pact.io/)
- [msw — Mock Service Worker for Node.js/browser](https://mswjs.io/)
- [Faker.js — realistic test data](https://fakerjs.dev/)
- [Faker (Python)](https://faker.readthedocs.io/)
- [httptest — Go standard library](https://pkg.go.dev/net/http/httptest)
- [supertest — HTTP testing for Node.js](https://github.com/ladjs/supertest)
- [httpx — async HTTP client for Python (used in FastAPI testing)](https://www.python-httpx.org/)

---

**Next:** [Part 13.1: Observability — Logging, Metrics & Tracing](../part-13/13-observability-logging-metrics.md)
