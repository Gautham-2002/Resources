# Part 12.1: Testing Backend Services

## What You'll Learn
- The testing pyramid and why each layer exists
- Unit testing philosophy: what to test, what to mock, what not to bother with
- Table-driven tests in Go, Jest in Node.js, pytest in Python
- Mocking databases with the repository pattern
- HTTP handler testing without starting a real server
- Test isolation: why tests must be independent
- Production-quality test code with real patterns interviewers look for

## Table of Contents
1. [Testing Pyramid](#1-testing-pyramid)
2. [Unit Testing Philosophy](#2-unit-testing-philosophy)
3. [Go Testing — Deep Dive](#3-go-testing--deep-dive)
4. [Node.js Testing — Deep Dive](#4-nodejs-testing--deep-dive)
5. [Python Testing — Deep Dive](#5-python-testing--deep-dive)
6. [Mocking Databases](#6-mocking-databases)
7. [Test Isolation](#7-test-isolation)
8. [Implementation Examples](#8-implementation-examples)
9. [Common Patterns & Best Practices](#9-common-patterns--best-practices)
10. [Common Pitfalls](#10-common-pitfalls)
11. [Interview Questions & Answers](#11-interview-questions--answers)
12. [Resources](#12-resources)

---

## 1. Testing Pyramid

```
            /\
           /  \
          / E2E\          ~10%  — slowest, most expensive, fewest
         /------\
        /  Integ  \       ~20%  — test multiple components together
       /------------\
      /  Unit Tests  \    ~70%  — fast, isolated, most numerous
     /________________\
```

### Why a Pyramid (Not a Square)?

**Unit tests are cheap:**
- Run in milliseconds
- No external dependencies
- Pinpoint exactly which function broke
- Safe to run on every commit, every save

**Integration tests are expensive:**
- Require databases, caches, external services (or mocks thereof)
- Slower — DB startup, network latency
- More setup/teardown code
- Still valuable: unit tests can't catch "the query returns wrong results"

**E2E tests are the most expensive:**
- Start the entire stack
- Can be flaky (network issues, timing)
- Catch real integration bugs that unit and integration tests miss
- Run in CI, not on every keystroke

**The anti-pattern (ice cream cone):**
```
   /\
  /E2E\         Most tests — slow, expensive, fragile
 /------\
/ Manual \      Manual testing — doesn't scale
/----------\
/ Unit Tests \  Few — can't catch integration bugs
/______________\
```

### What Each Layer Tests

| Layer | Tests | Example |
|---|---|---|
| Unit | Pure functions, business logic, transformations | `CalculateDiscount(price, coupon)` → correct result |
| Integration | Service + DB, service + cache | `UserService.Create()` actually writes to PostgreSQL |
| E2E/API | Full HTTP request → response | `POST /orders` creates order, charges payment, sends email |
| Contract | Interface between two services | Consumer expects `{ id, name }`, provider delivers `{ id, name }` |

---

## 2. Unit Testing Philosophy

### What to Unit Test

```
✓ Pure functions (given same input, always same output, no side effects)
✓ Business logic — discount calculation, order validation, pricing
✓ Data transformation — mapping DB model to API response
✓ Error conditions — what happens when input is invalid
✓ Edge cases — empty array, zero value, max value, nil/null
✓ Conditional branches — every if/else path should have a test
```

### What NOT to Unit Test

```
✗ Framework glue code — Express route registration, FastAPI decorator
✗ Database queries in isolation — test in integration test with real DB
✗ Trivial getters/setters — no logic, nothing to test
✗ Third-party library internals — test your code's use of them
✗ Configuration loading — too environment-dependent
```

### Mock Interfaces, Not Concrete Types

The key principle: unit tests should test **your logic**, not external systems. Mock the boundary (the interface/protocol) between your code and external systems:

```
Your code → [Interface] → Real DB     (integration test)
Your code → [Interface] → Mock DB     (unit test)
```

If you mock a concrete type (e.g., a specific PostgreSQL driver), your test is tightly coupled to implementation details. If you mock an interface (e.g., `UserRepository`), your test is coupled only to the contract.

### Test Naming Convention

```
Function:  TestFunctionName_Condition_ExpectedBehavior

Examples:
  TestCalculateDiscount_WithValidCoupon_ReturnsDiscountedPrice
  TestCalculateDiscount_WithExpiredCoupon_ReturnsFullPrice
  TestCalculateDiscount_WithNilOrder_ReturnsError
  TestGetUser_WhenUserNotFound_Returns404
  TestGetUser_WhenDBError_Returns500
```

This naming convention makes test output self-documenting. When a test fails, you immediately know what condition broke and what was expected.

---

## 3. Go Testing — Deep Dive

### The `testing` Package

```go
// T — test context, used for unit/integration tests
func TestSomething(t *testing.T) { ... }

// B — benchmark context, measures performance
func BenchmarkSomething(b *testing.B) { ... }

// F — fuzz testing context (Go 1.18+), generates random inputs
func FuzzSomething(f *testing.F) { ... }
```

### Table-Driven Tests

The idiomatic Go way to test multiple cases for the same function:

```go
func TestCalculateDiscount(t *testing.T) {
    tests := []struct {
        name        string
        price       float64
        couponCode  string
        wantPrice   float64
        wantErr     bool
        errContains string
    }{
        {
            name:      "valid percentage coupon",
            price:     100.0,
            couponCode: "SAVE10",
            wantPrice: 90.0,
        },
        {
            name:      "valid flat coupon",
            price:     100.0,
            couponCode: "FLAT20",
            wantPrice: 80.0,
        },
        {
            name:       "expired coupon returns error",
            price:      100.0,
            couponCode: "EXPIRED",
            wantErr:    true,
            errContains: "expired",
        },
        {
            name:       "unknown coupon returns error",
            price:      100.0,
            couponCode: "INVALID123",
            wantErr:    true,
            errContains: "not found",
        },
        {
            name:      "zero price with coupon",
            price:     0.0,
            couponCode: "SAVE10",
            wantPrice: 0.0, // no discount on zero
        },
        {
            name:      "coupon cannot make price negative",
            price:     5.0,
            couponCode: "FLAT20", // $20 off on $5 item
            wantPrice: 0.0,       // floor at 0
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := CalculateDiscount(tt.price, tt.couponCode)

            if tt.wantErr {
                require.Error(t, err)
                if tt.errContains != "" {
                    assert.Contains(t, err.Error(), tt.errContains)
                }
                return
            }

            require.NoError(t, err)
            assert.InDelta(t, tt.wantPrice, got, 0.001, "price mismatch")
        })
    }
}
```

**Why table-driven tests?**
- All cases in one place — easy to see coverage
- Adding a new case is one struct literal
- t.Run() creates sub-tests — `go test -run TestCalculateDiscount/expired_coupon` runs just one case
- Each sub-test has its own pass/fail — one failure doesn't stop others

### Testify — Assertions and Mocks

```go
import (
    "github.com/stretchr/testify/assert"  // non-fatal assertions
    "github.com/stretchr/testify/require" // fatal assertions (test stops on failure)
    "github.com/stretchr/testify/mock"    // mocking
)

// assert — test continues even on failure (good for multiple independent assertions)
assert.Equal(t, expected, actual)
assert.NoError(t, err)
assert.Error(t, err)
assert.Nil(t, val)
assert.NotNil(t, val)
assert.Contains(t, "some string", "substring")
assert.Len(t, slice, 3)
assert.InDelta(t, 1.0, 1.001, 0.01) // float comparison with tolerance

// require — test stops on failure (good for preconditions)
require.NoError(t, err)     // if err != nil, stop here — remaining assertions would panic anyway
require.NotNil(t, result)   // if result == nil, stop here — can't dereference it
```

### Mocking with Testify/Mock

```go
// Define the interface you want to mock
type UserRepository interface {
    FindByID(ctx context.Context, id string) (*User, error)
    Create(ctx context.Context, user *User) error
    Update(ctx context.Context, user *User) error
    Delete(ctx context.Context, id string) error
}

// Generated or hand-written mock
type MockUserRepository struct {
    mock.Mock
}

func (m *MockUserRepository) FindByID(ctx context.Context, id string) (*User, error) {
    args := m.Called(ctx, id)
    if args.Get(0) == nil {
        return nil, args.Error(1)
    }
    return args.Get(0).(*User), args.Error(1)
}

func (m *MockUserRepository) Create(ctx context.Context, user *User) error {
    args := m.Called(ctx, user)
    return args.Error(0)
}

// In a test:
func TestUserService_GetByID_WhenFound_ReturnsUser(t *testing.T) {
    mockRepo := &MockUserRepository{}
    svc := NewUserService(mockRepo)

    expectedUser := &User{ID: "123", Name: "Alice"}

    // Set up expectation: when FindByID is called with "123", return expectedUser
    mockRepo.On("FindByID", mock.Anything, "123").Return(expectedUser, nil)

    got, err := svc.GetByID(context.Background(), "123")

    require.NoError(t, err)
    assert.Equal(t, expectedUser, got)

    // Verify the mock was called as expected
    mockRepo.AssertExpectations(t)
}

func TestUserService_GetByID_WhenNotFound_ReturnsError(t *testing.T) {
    mockRepo := &MockUserRepository{}
    svc := NewUserService(mockRepo)

    mockRepo.On("FindByID", mock.Anything, "nonexistent").Return(nil, ErrNotFound)

    got, err := svc.GetByID(context.Background(), "nonexistent")

    require.Error(t, err)
    assert.True(t, errors.Is(err, ErrNotFound))
    assert.Nil(t, got)
    mockRepo.AssertExpectations(t)
}
```

### HTTP Handler Testing in Go

```go
func TestUserHandler_GetUser_Returns200(t *testing.T) {
    mockSvc := &MockUserService{}
    handler := NewUserHandler(mockSvc)

    expectedUser := &User{ID: "123", Name: "Alice", Email: "alice@example.com"}
    mockSvc.On("GetByID", mock.Anything, "123").Return(expectedUser, nil)

    // Create a test HTTP request
    req := httptest.NewRequest(http.MethodGet, "/users/123", nil)
    req = req.WithContext(context.Background())

    // For Chi, set URL params in context
    rctx := chi.NewRouteContext()
    rctx.URLParams.Add("id", "123")
    req = req.WithContext(context.WithValue(req.Context(), chi.RouteCtxKey, rctx))

    // Record the response
    w := httptest.NewRecorder()

    handler.GetUser(w, req)

    resp := w.Result()
    assert.Equal(t, http.StatusOK, resp.StatusCode)
    assert.Equal(t, "application/json", resp.Header.Get("Content-Type"))

    var body map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&body)
    assert.Equal(t, "123", body["id"])
    assert.Equal(t, "Alice", body["name"])

    mockSvc.AssertExpectations(t)
}

func TestUserHandler_GetUser_WhenNotFound_Returns404(t *testing.T) {
    mockSvc := &MockUserService{}
    handler := NewUserHandler(mockSvc)

    mockSvc.On("GetByID", mock.Anything, "999").Return(nil, ErrNotFound)

    req := httptest.NewRequest(http.MethodGet, "/users/999", nil)
    rctx := chi.NewRouteContext()
    rctx.URLParams.Add("id", "999")
    req = req.WithContext(context.WithValue(req.Context(), chi.RouteCtxKey, rctx))

    w := httptest.NewRecorder()
    handler.GetUser(w, req)

    assert.Equal(t, http.StatusNotFound, w.Code)
    mockSvc.AssertExpectations(t)
}
```

### Benchmark Tests

```go
func BenchmarkCalculateDiscount(b *testing.B) {
    b.ReportAllocs() // report memory allocations per operation

    for i := 0; i < b.N; i++ { // b.N is set by the benchmarking framework
        _, _ = CalculateDiscount(100.0, "SAVE10")
    }
}

// Run with: go test -bench=BenchmarkCalculateDiscount -benchmem
// Output:
// BenchmarkCalculateDiscount-8   5000000   245 ns/op   48 B/op   2 allocs/op
```

### Fuzz Testing (Go 1.18+)

```go
func FuzzCalculateDiscount(f *testing.F) {
    // Seed corpus — known interesting inputs
    f.Add(100.0, "SAVE10")
    f.Add(0.0, "SAVE10")
    f.Add(-1.0, "SAVE10")

    f.Fuzz(func(t *testing.T, price float64, couponCode string) {
        // The function must not panic regardless of input
        result, err := CalculateDiscount(price, couponCode)
        if err == nil {
            // If no error, result must be non-negative
            if result < 0 {
                t.Errorf("negative price: CalculateDiscount(%v, %q) = %v", price, couponCode, result)
            }
        }
    })
}

// Run with: go test -fuzz=FuzzCalculateDiscount
```

---

## 4. Node.js Testing — Deep Dive

### Jest vs Vitest

| Feature | Jest | Vitest |
|---|---|---|
| Speed | Slower (uses Babel transform) | Faster (Vite-powered, native ESM) |
| ESM support | Requires config | Native |
| API | Mature, wide ecosystem | Jest-compatible API |
| TypeScript | Needs ts-jest | Native |
| Best for | Existing Jest projects | New projects, monorepos with Vite |

### Jest Test Structure

```javascript
// __tests__/userService.test.js
const { UserService } = require('../services/userService');
const { NotFoundError } = require('../errors/AppError');

// Mock the entire repository module
jest.mock('../repositories/userRepository');
const { UserRepository } = require('../repositories/userRepository');

describe('UserService', () => {
    let service;
    let mockRepo;

    beforeEach(() => {
        // Clear all mock state before each test
        jest.clearAllMocks();
        mockRepo = new UserRepository();
        service = new UserService(mockRepo);
    });

    describe('getByID', () => {
        it('returns user when found', async () => {
            const expectedUser = { id: '123', name: 'Alice', email: 'alice@example.com' };
            mockRepo.findByID.mockResolvedValue(expectedUser);

            const result = await service.getByID('123');

            expect(result).toEqual(expectedUser);
            expect(mockRepo.findByID).toHaveBeenCalledTimes(1);
            expect(mockRepo.findByID).toHaveBeenCalledWith('123');
        });

        it('throws NotFoundError when user does not exist', async () => {
            mockRepo.findByID.mockResolvedValue(null);

            await expect(service.getByID('999')).rejects.toThrow(NotFoundError);
            await expect(service.getByID('999')).rejects.toThrow('User 999 not found');
        });

        it('propagates database error', async () => {
            const dbError = new Error('Connection refused');
            mockRepo.findByID.mockRejectedValue(dbError);

            await expect(service.getByID('123')).rejects.toThrow('Connection refused');
        });
    });

    describe('create', () => {
        it('creates user with hashed password', async () => {
            const input = { name: 'Bob', email: 'bob@example.com', password: 'secret123' };
            const savedUser = { id: '456', name: 'Bob', email: 'bob@example.com' };
            mockRepo.create.mockResolvedValue(savedUser);

            const result = await service.create(input);

            expect(result).toEqual(savedUser);
            // Verify password was hashed (not stored as plaintext)
            const createCall = mockRepo.create.mock.calls[0][0];
            expect(createCall.password).not.toBe('secret123');
            expect(createCall.password).toMatch(/^\$2[aby]\$/); // bcrypt prefix
        });
    });
});
```

### HTTP Handler Testing with Supertest

```javascript
// __tests__/userRoutes.test.js
const request = require('supertest');
const express = require('express');
const userRoutes = require('../routes/users');
const errorHandler = require('../middleware/errorHandler');

// Mock the service layer
jest.mock('../services/userService');
const userService = require('../services/userService');

function buildApp() {
    const app = express();
    app.use(express.json());
    app.use('/users', userRoutes);
    app.use(errorHandler);
    return app;
}

describe('GET /users/:id', () => {
    let app;

    beforeEach(() => {
        jest.clearAllMocks();
        app = buildApp();
    });

    it('returns 200 with user when found', async () => {
        const user = { id: '123', name: 'Alice', email: 'alice@example.com' };
        userService.getByID.mockResolvedValue(user);

        const response = await request(app)
            .get('/users/123')
            .set('Accept', 'application/json');

        expect(response.status).toBe(200);
        expect(response.body.data).toEqual(user);
        expect(userService.getByID).toHaveBeenCalledWith('123');
    });

    it('returns 404 when user not found', async () => {
        const { NotFoundError } = require('../errors/AppError');
        userService.getByID.mockRejectedValue(new NotFoundError('User 999 not found'));

        const response = await request(app).get('/users/999');

        expect(response.status).toBe(404);
        expect(response.body.error.code).toBe('NOT_FOUND');
        expect(response.body.error.message).toBe('User 999 not found');
    });

    it('returns 500 on unexpected error', async () => {
        userService.getByID.mockRejectedValue(new Error('Database connection failed'));

        const response = await request(app).get('/users/123');

        expect(response.status).toBe(500);
        expect(response.body.error.code).toBe('INTERNAL_ERROR');
        // Must NOT leak internal error details
        expect(response.body.error.message).not.toContain('Database');
    });
});

describe('POST /users', () => {
    let app;

    beforeEach(() => {
        jest.clearAllMocks();
        app = buildApp();
    });

    it('returns 201 with created user', async () => {
        const input = { name: 'Bob', email: 'bob@example.com', password: 'password123' };
        const created = { id: '456', name: 'Bob', email: 'bob@example.com' };
        userService.create.mockResolvedValue(created);

        const response = await request(app)
            .post('/users')
            .send(input)
            .set('Content-Type', 'application/json');

        expect(response.status).toBe(201);
        expect(response.body.data.id).toBe('456');
    });

    it('returns 400 when email is invalid', async () => {
        const { ValidationError } = require('../errors/AppError');
        userService.create.mockRejectedValue(
            new ValidationError('Invalid input', [
                { field: 'email', message: 'must be a valid email' }
            ])
        );

        const response = await request(app)
            .post('/users')
            .send({ name: 'Bob', email: 'notanemail', password: 'pass' });

        expect(response.status).toBe(400);
        expect(response.body.error.code).toBe('VALIDATION_ERROR');
        expect(response.body.error.fields).toContainEqual({
            field: 'email',
            message: 'must be a valid email'
        });
    });
});
```

### Jest.mock — Three Patterns

```javascript
// Pattern 1: Auto-mock the entire module
jest.mock('../repositories/userRepository');
// All functions become jest.fn() — returns undefined by default

// Pattern 2: Manual factory mock
jest.mock('../repositories/userRepository', () => ({
    UserRepository: jest.fn().mockImplementation(() => ({
        findByID: jest.fn(),
        create: jest.fn(),
    }))
}));

// Pattern 3: Mock a specific function with spyOn
const userRepo = require('../repositories/userRepository');
jest.spyOn(userRepo, 'findByID').mockResolvedValue({ id: '123' });
// Restores original after test if you call .mockRestore()
```

---

## 5. Python Testing — Deep Dive

### pytest Fixtures

Fixtures are reusable setup/teardown functions:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Function scope (default) — new instance for each test
@pytest.fixture
def mock_user_repo():
    return MagicMock()

# Module scope — shared across all tests in the module
@pytest.fixture(scope="module")
def test_config():
    return {"db_url": "postgresql://localhost/test", "redis_url": "redis://localhost:6379"}

# Session scope — shared across all tests in the session
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Autouse — automatically used by every test in scope
@pytest.fixture(autouse=True)
def reset_state():
    # Setup
    yield
    # Teardown — runs after every test
    cache.clear()
```

### Parametrize — Python's Table-Driven Tests

```python
import pytest
from decimal import Decimal
from services.discount import calculate_discount
from errors.exceptions import ValidationError

@pytest.mark.parametrize("price,coupon_code,expected", [
    (Decimal("100.00"), "SAVE10", Decimal("90.00")),
    (Decimal("100.00"), "FLAT20", Decimal("80.00")),
    (Decimal("0.00"),   "SAVE10", Decimal("0.00")),
    (Decimal("5.00"),   "FLAT20", Decimal("0.00")),   # floor at 0
    (Decimal("100.00"), "HALFOFF", Decimal("50.00")),
])
def test_calculate_discount_valid_coupons(price, coupon_code, expected):
    result = calculate_discount(price, coupon_code)
    assert result == expected


@pytest.mark.parametrize("price,coupon_code,error_message", [
    (Decimal("100.00"), "EXPIRED", "coupon has expired"),
    (Decimal("100.00"), "INVALID", "coupon not found"),
    (Decimal("-1.00"),  "SAVE10",  "price must be non-negative"),
])
def test_calculate_discount_invalid_inputs(price, coupon_code, error_message):
    with pytest.raises(ValidationError) as exc_info:
        calculate_discount(price, coupon_code)
    assert error_message in str(exc_info.value).lower()
```

### AsyncMock for Async Functions

```python
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from services.user_service import UserService
from errors.exceptions import NotFoundError

@pytest.mark.asyncio
async def test_get_user_returns_user_when_found():
    mock_repo = MagicMock()
    mock_repo.find_by_id = AsyncMock(return_value={"id": "123", "name": "Alice"})

    service = UserService(repo=mock_repo)
    result = await service.get_by_id("123")

    assert result["id"] == "123"
    assert result["name"] == "Alice"
    mock_repo.find_by_id.assert_called_once_with("123")


@pytest.mark.asyncio
async def test_get_user_raises_not_found_when_missing():
    mock_repo = MagicMock()
    mock_repo.find_by_id = AsyncMock(return_value=None)

    service = UserService(repo=mock_repo)

    with pytest.raises(NotFoundError) as exc_info:
        await service.get_by_id("999")

    assert "999" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_user_hashes_password():
    mock_repo = MagicMock()
    created_user = {"id": "456", "name": "Bob", "email": "bob@example.com"}
    mock_repo.create = AsyncMock(return_value=created_user)

    service = UserService(repo=mock_repo)
    result = await service.create({
        "name": "Bob",
        "email": "bob@example.com",
        "password": "plaintext123"
    })

    # Verify the password stored was not plaintext
    saved_data = mock_repo.create.call_args[0][0]
    assert saved_data["password"] != "plaintext123"
    assert saved_data["password"].startswith("$2b$")  # bcrypt hash
```

### FastAPI TestClient — Handler Testing

```python
# tests/test_user_routes.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app
from errors.exceptions import NotFoundError, ValidationError

@pytest.fixture
def client():
    return TestClient(app)


def test_get_user_returns_200(client):
    user_data = {"id": "123", "name": "Alice", "email": "alice@example.com"}

    with patch("routers.users.user_service") as mock_svc:
        mock_svc.get_by_id = AsyncMock(return_value=user_data)

        response = client.get("/users/123")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == "123"


def test_get_user_returns_404_when_not_found(client):
    with patch("routers.users.user_service") as mock_svc:
        mock_svc.get_by_id = AsyncMock(side_effect=NotFoundError("User 999 not found"))

        response = client.get("/users/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert "999" in response.json()["error"]["message"]


def test_get_user_returns_500_on_unexpected_error(client):
    with patch("routers.users.user_service") as mock_svc:
        mock_svc.get_by_id = AsyncMock(side_effect=Exception("Unexpected DB error"))

        response = client.get("/users/123")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    # Must not leak internal details
    assert "DB error" not in response.json()["error"]["message"]


def test_create_user_returns_422_on_invalid_body(client):
    # Missing required fields — Pydantic validation
    response = client.post("/users", json={"name": "Bob"})  # missing email, password

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert any(f["field"] == "email" for f in error["fields"])
```

### pytest-asyncio for Async Tests

```python
# conftest.py
import asyncio
import pytest

@pytest.fixture(scope="session")
def event_loop():
    """Override default event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

```python
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"  # auto-mark all async tests — no need for @pytest.mark.asyncio
```

### Property-Based Testing with Hypothesis

```python
from hypothesis import given, strategies as st
from hypothesis import settings
from services.discount import calculate_discount
from decimal import Decimal

@given(
    price=st.decimals(min_value=0, max_value=10000, places=2),
    coupon_code=st.sampled_from(["SAVE10", "SAVE20", "FLAT5", "FLAT10"])
)
@settings(max_examples=200)
def test_discount_never_makes_price_negative(price, coupon_code):
    """Property: discounted price must always be >= 0."""
    result = calculate_discount(price, coupon_code)
    assert result >= Decimal("0.00"), f"negative price {result} for input price={price}"


@given(
    price=st.decimals(min_value=0, max_value=10000, places=2),
    coupon_code=st.sampled_from(["SAVE10", "SAVE20"])
)
def test_discount_never_exceeds_original_price(price, coupon_code):
    """Property: discounted price must always be <= original."""
    result = calculate_discount(price, coupon_code)
    assert result <= price
```

---

## 6. Mocking Databases

### Why Mock the Database in Unit Tests

Database tests require:
- A running database (setup cost)
- Migration/schema management
- Data seeding and cleanup between tests
- Slower execution

For unit tests, you want to test **your business logic**, not whether PostgreSQL correctly executes a query. Mock the database boundary.

### Repository Pattern — The Key Enabler

The repository pattern abstracts database access behind an interface. Your service depends on the interface, not the concrete database layer:

```go
// Define the contract
type UserRepository interface {
    FindByID(ctx context.Context, id string) (*User, error)
    FindByEmail(ctx context.Context, email string) (*User, error)
    Create(ctx context.Context, user *CreateUserInput) (*User, error)
    Update(ctx context.Context, id string, updates *UpdateUserInput) (*User, error)
    Delete(ctx context.Context, id string) error
    List(ctx context.Context, filter UserFilter) ([]*User, int, error)
}

// Real implementation
type PostgresUserRepository struct {
    db *pgxpool.Pool
}

func (r *PostgresUserRepository) FindByID(ctx context.Context, id string) (*User, error) {
    // Real SQL query
}

// Mock implementation for unit tests
type MockUserRepository struct {
    mock.Mock
}

func (m *MockUserRepository) FindByID(ctx context.Context, id string) (*User, error) {
    args := m.Called(ctx, id)
    // ...
}

// Service depends on the interface, not the concrete type
type UserService struct {
    repo UserRepository // interface — can be real or mock
}
```

### Transaction Rollback Pattern

For integration tests that use a real database, wrap each test in a transaction and roll it back at the end:

```go
func TestUserRepository_Create_Integration(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test")
    }

    db := testhelpers.GetTestDB(t) // shared test DB connection

    // Start a transaction
    tx, err := db.Begin(context.Background())
    require.NoError(t, err)

    // Always roll back — test data is never committed
    defer tx.Rollback(context.Background())

    repo := NewPostgresUserRepository(tx)

    input := &CreateUserInput{
        Name:  "Test User",
        Email: "test@example.com",
    }
    user, err := repo.Create(context.Background(), input)

    require.NoError(t, err)
    require.NotNil(t, user)
    assert.NotEmpty(t, user.ID)
    assert.Equal(t, "Test User", user.Name)

    // The rollback in defer means this data never hits the DB permanently
}
```

### In-Memory SQLite for Simple Cases

```python
# conftest.py — SQLite in-memory DB for Python integration tests
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base

@pytest.fixture(scope="function")
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
```

**Caution with SQLite:** SQLite does not support all PostgreSQL features (window functions, certain data types, full-text search). For complex queries, use a real PostgreSQL instance via testcontainers instead.

---

## 7. Test Isolation

### The Golden Rule: Tests Must Be Independent

A test that passes when run alone but fails when run with other tests is a broken test. It has hidden dependencies on shared state.

**Common sources of shared state:**
- Global variables
- Singleton instances
- Database rows not cleaned up between tests
- Cache entries from previous tests
- File system state
- Environment variables

```go
// BAD — shared counter
var requestCount int

func TestHandlerA(t *testing.T) {
    requestCount = 0
    handle(req)
    assert.Equal(t, 1, requestCount) // passes alone
}

func TestHandlerB(t *testing.T) {
    handle(req)
    assert.Equal(t, 1, requestCount) // passes alone, but fails if TestHandlerA ran first
}

// GOOD — each test owns its state
func TestHandlerA(t *testing.T) {
    counter := &Counter{}
    handle(req, counter)
    assert.Equal(t, 1, counter.Value())
}
```

### Setup and Teardown Patterns

**Go:**
```go
func TestMain(m *testing.M) {
    // Suite-level setup (runs once for all tests in the package)
    testDB = setupTestDatabase()

    code := m.Run() // run all tests

    // Suite-level teardown
    testDB.Close()
    os.Exit(code)
}
```

**Node.js:**
```javascript
describe('UserService', () => {
    let db;

    beforeAll(async () => {
        db = await setupTestDatabase();
    });

    afterAll(async () => {
        await db.close();
    });

    beforeEach(async () => {
        await db.truncate('users'); // clean slate for each test
    });

    // tests...
});
```

**Python:**
```python
@pytest.fixture(autouse=True)
async def clean_db(db_session):
    yield
    # Runs after each test — truncate all tables
    for table in reversed(Base.metadata.sorted_tables):
        await db_session.execute(table.delete())
    await db_session.commit()
```

---

## 8. Implementation Examples

### Go: Full Unit Test Suite for UserService

```go
// services/user_service_test.go
package services_test

import (
    "context"
    "errors"
    "testing"

    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/mock"
    "github.com/stretchr/testify/require"

    "myapp/models"
    "myapp/repositories"
    "myapp/services"
)

type MockUserRepository struct {
    mock.Mock
}

func (m *MockUserRepository) FindByID(ctx context.Context, id string) (*models.User, error) {
    args := m.Called(ctx, id)
    if args.Get(0) == nil {
        return nil, args.Error(1)
    }
    return args.Get(0).(*models.User), args.Error(1)
}

func (m *MockUserRepository) FindByEmail(ctx context.Context, email string) (*models.User, error) {
    args := m.Called(ctx, email)
    if args.Get(0) == nil {
        return nil, args.Error(1)
    }
    return args.Get(0).(*models.User), args.Error(1)
}

func (m *MockUserRepository) Create(ctx context.Context, input *repositories.CreateUserInput) (*models.User, error) {
    args := m.Called(ctx, input)
    if args.Get(0) == nil {
        return nil, args.Error(1)
    }
    return args.Get(0).(*models.User), args.Error(1)
}

var _ repositories.UserRepository = (*MockUserRepository)(nil) // compile-time interface check

func TestUserService_GetByID(t *testing.T) {
    ctx := context.Background()

    tests := []struct {
        name      string
        id        string
        mockSetup func(*MockUserRepository)
        wantUser  *models.User
        wantErr   error
    }{
        {
            name: "found",
            id:   "123",
            mockSetup: func(m *MockUserRepository) {
                m.On("FindByID", mock.Anything, "123").
                    Return(&models.User{ID: "123", Name: "Alice"}, nil)
            },
            wantUser: &models.User{ID: "123", Name: "Alice"},
        },
        {
            name: "not found",
            id:   "999",
            mockSetup: func(m *MockUserRepository) {
                m.On("FindByID", mock.Anything, "999").
                    Return(nil, repositories.ErrNotFound)
            },
            wantErr: services.ErrUserNotFound,
        },
        {
            name: "db error",
            id:   "123",
            mockSetup: func(m *MockUserRepository) {
                m.On("FindByID", mock.Anything, "123").
                    Return(nil, errors.New("connection refused"))
            },
            wantErr: errors.New("connection refused"), // any non-nil error
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            mockRepo := &MockUserRepository{}
            tt.mockSetup(mockRepo)

            svc := services.NewUserService(mockRepo)
            got, err := svc.GetByID(ctx, tt.id)

            if tt.wantErr != nil {
                require.Error(t, err)
                if errors.Is(tt.wantErr, services.ErrUserNotFound) {
                    assert.True(t, errors.Is(err, services.ErrUserNotFound))
                }
            } else {
                require.NoError(t, err)
                assert.Equal(t, tt.wantUser, got)
            }

            mockRepo.AssertExpectations(t)
        })
    }
}
```

### Node.js: Service Test with Jest

```javascript
// __tests__/services/orderService.test.js
const { OrderService } = require('../../services/orderService');
const { NotFoundError, ValidationError } = require('../../errors/AppError');

const mockOrderRepo = {
    create: jest.fn(),
    findByID: jest.fn(),
    updateStatus: jest.fn(),
};

const mockPaymentClient = {
    charge: jest.fn(),
};

const mockEventBus = {
    publish: jest.fn(),
};

describe('OrderService.createOrder', () => {
    let service;

    beforeEach(() => {
        jest.clearAllMocks();
        service = new OrderService({
            orderRepo: mockOrderRepo,
            paymentClient: mockPaymentClient,
            eventBus: mockEventBus,
        });
    });

    it('creates order and publishes event on success', async () => {
        const input = {
            userId: 'user-1',
            items: [{ productId: 'prod-1', quantity: 2, price: 50.00 }],
            paymentToken: 'tok_test_123',
        };

        const savedOrder = { id: 'order-1', ...input, status: 'pending' };
        const chargeResult = { id: 'charge-1', amount: 100.00 };

        mockOrderRepo.create.mockResolvedValue(savedOrder);
        mockPaymentClient.charge.mockResolvedValue(chargeResult);
        mockOrderRepo.updateStatus.mockResolvedValue({ ...savedOrder, status: 'paid' });
        mockEventBus.publish.mockResolvedValue(undefined);

        const result = await service.createOrder(input);

        expect(result.status).toBe('paid');
        expect(mockPaymentClient.charge).toHaveBeenCalledWith({
            token: 'tok_test_123',
            amount: 100.00,
            orderId: 'order-1',
        });
        expect(mockEventBus.publish).toHaveBeenCalledWith('order.paid', {
            orderId: 'order-1',
            userId: 'user-1',
        });
    });

    it('marks order as payment_failed when charge fails', async () => {
        const input = {
            userId: 'user-1',
            items: [{ productId: 'prod-1', quantity: 1, price: 50.00 }],
            paymentToken: 'tok_declined',
        };

        mockOrderRepo.create.mockResolvedValue({ id: 'order-2', status: 'pending' });
        mockPaymentClient.charge.mockRejectedValue(new Error('Card declined'));
        mockOrderRepo.updateStatus.mockResolvedValue({ id: 'order-2', status: 'payment_failed' });

        await expect(service.createOrder(input)).rejects.toThrow('Card declined');

        expect(mockOrderRepo.updateStatus).toHaveBeenCalledWith('order-2', 'payment_failed');
    });

    it('rejects order with empty items', async () => {
        await expect(
            service.createOrder({ userId: 'user-1', items: [], paymentToken: 'tok_1' })
        ).rejects.toThrow(ValidationError);
    });
});
```

### Python: Async Service Test with pytest

```python
# tests/services/test_order_service.py
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call

from services.order_service import OrderService
from errors.exceptions import ValidationError


@pytest.fixture
def mock_order_repo():
    return MagicMock()


@pytest.fixture
def mock_payment_client():
    return MagicMock()


@pytest.fixture
def mock_event_bus():
    return MagicMock()


@pytest.fixture
def order_service(mock_order_repo, mock_payment_client, mock_event_bus):
    return OrderService(
        order_repo=mock_order_repo,
        payment_client=mock_payment_client,
        event_bus=mock_event_bus,
    )


@pytest.mark.asyncio
async def test_create_order_success(order_service, mock_order_repo, mock_payment_client, mock_event_bus):
    input_data = {
        "user_id": "user-1",
        "items": [{"product_id": "prod-1", "quantity": 2, "price": Decimal("50.00")}],
        "payment_token": "tok_test_123",
    }

    saved_order = {"id": "order-1", **input_data, "status": "pending"}
    charge_result = {"id": "charge-1", "amount": Decimal("100.00")}
    paid_order = {**saved_order, "status": "paid"}

    mock_order_repo.create = AsyncMock(return_value=saved_order)
    mock_payment_client.charge = AsyncMock(return_value=charge_result)
    mock_order_repo.update_status = AsyncMock(return_value=paid_order)
    mock_event_bus.publish = AsyncMock()

    result = await order_service.create_order(input_data)

    assert result["status"] == "paid"
    mock_payment_client.charge.assert_called_once_with(
        token="tok_test_123",
        amount=Decimal("100.00"),
        order_id="order-1",
    )
    mock_event_bus.publish.assert_called_once_with(
        "order.paid",
        {"order_id": "order-1", "user_id": "user-1"},
    )


@pytest.mark.asyncio
async def test_create_order_marks_failed_on_payment_error(
    order_service, mock_order_repo, mock_payment_client
):
    input_data = {
        "user_id": "user-1",
        "items": [{"product_id": "prod-1", "quantity": 1, "price": Decimal("50.00")}],
        "payment_token": "tok_declined",
    }

    mock_order_repo.create = AsyncMock(return_value={"id": "order-2", "status": "pending"})
    mock_payment_client.charge = AsyncMock(side_effect=Exception("Card declined"))
    mock_order_repo.update_status = AsyncMock()

    with pytest.raises(Exception, match="Card declined"):
        await order_service.create_order(input_data)

    mock_order_repo.update_status.assert_called_once_with("order-2", "payment_failed")


@pytest.mark.asyncio
async def test_create_order_raises_validation_error_for_empty_items(order_service):
    with pytest.raises(ValidationError):
        await order_service.create_order({
            "user_id": "user-1",
            "items": [],
            "payment_token": "tok_1",
        })
```

---

## 9. Common Patterns & Best Practices

### Pattern 1: Test at the Right Level

Don't use integration tests to cover 30 error cases — unit test the business logic, and use integration tests for the "happy path + 1-2 critical error cases".

### Pattern 2: Compile-Time Interface Check (Go)

```go
var _ UserRepository = (*PostgresUserRepository)(nil)
var _ UserRepository = (*MockUserRepository)(nil)
```

If either concrete type is missing a method, the code won't compile. This is better than discovering a broken mock at test runtime.

### Pattern 3: Build Helpers for Test Objects (Factory Pattern)

```go
// testhelpers/factories.go
func NewTestUser(overrides ...func(*models.User)) *models.User {
    u := &models.User{
        ID:    "test-user-123",
        Name:  "Test User",
        Email: "test@example.com",
    }
    for _, override := range overrides {
        override(u)
    }
    return u
}

// Usage:
user := testhelpers.NewTestUser()
adminUser := testhelpers.NewTestUser(func(u *models.User) {
    u.Role = "admin"
})
```

### Pattern 4: Avoid `time.Now()` in Business Logic — Inject Clock

```go
type Clock interface {
    Now() time.Time
}

type RealClock struct{}
func (c *RealClock) Now() time.Time { return time.Now() }

type MockClock struct {
    Fixed time.Time
}
func (c *MockClock) Now() time.Time { return c.Fixed }

// Service uses the clock interface
type CouponService struct {
    clock Clock
}

func (s *CouponService) IsExpired(coupon *Coupon) bool {
    return s.clock.Now().After(coupon.ExpiresAt)
}

// In tests:
clock := &MockClock{Fixed: time.Date(2026, 1, 15, 0, 0, 0, 0, time.UTC)}
svc := &CouponService{clock: clock}
// Now you can test time-dependent logic deterministically
```

---

## 10. Common Pitfalls

### Pitfall 1: Testing Implementation, Not Behavior

```go
// BAD — tests that the mock was called with specific internal arguments
// If you refactor the implementation, this test breaks even if behavior is correct
mockRepo.On("FindByID", mock.Anything, "123").Return(user, nil)
// ...
mockRepo.AssertNumberOfCalls(t, "FindByID", 2) // why 2? implementation detail

// GOOD — tests observable behavior
got, err := svc.GetByID(ctx, "123")
assert.Equal(t, expected, got)
assert.NoError(t, err)
```

### Pitfall 2: Mocking What You Don't Own

Don't mock third-party libraries directly. Wrap them in your own interface, then mock the interface:

```go
// BAD — mocking the AWS SDK directly
mockS3 := &mockS3Client{}
mockS3.On("PutObject", ...).Return(...)
// Your test is now testing AWS SDK internals

// GOOD — wrap the SDK in your interface
type FileStorage interface {
    Upload(ctx context.Context, key string, data io.Reader) error
    Download(ctx context.Context, key string) (io.ReadCloser, error)
}

// Your S3 implementation:
type S3FileStorage struct { client *s3.Client }
// Your mock:
type MockFileStorage struct { mock.Mock }
```

### Pitfall 3: `t.Parallel()` with Shared State

```go
func TestSomething(t *testing.T) {
    t.Parallel() // runs concurrently with other parallel tests

    // BAD: accessing global state without synchronization
    globalCache[t.Name()] = "value" // race condition

    // GOOD: each test creates its own state
    cache := NewLocalCache()
    cache.Set(t.Name(), "value")
}
```

### Pitfall 4: Ignoring Test Cleanup

```python
# BAD — test file not cleaned up
def test_export():
    path = export_to_file(data)
    assert os.path.exists(path)
    # File left on disk — might affect other tests

# GOOD — cleanup registered
def test_export(tmp_path):
    path = tmp_path / "export.csv"  # pytest tmp_path handles cleanup automatically
    export_to_file(data, path)
    assert path.exists()
```

### Pitfall 5: Tests That Always Pass

```go
// BAD — assert on wrong variable
expected := 42
got := calculate()
assert.Equal(t, expected, expected) // always true — typo: should be (expected, got)
```

Use linters (`go vet`, `staticcheck`) and write tests that you've seen fail at least once.

---

## 11. Interview Questions & Answers

### Q1: What is the testing pyramid and why is it shaped like a pyramid?

**Answer:** The testing pyramid describes the recommended distribution of test types:
- **70% unit tests** — fast, cheap, isolated; test one function at a time
- **20% integration tests** — slower, test multiple components together (service + DB)
- **10% E2E/API tests** — slowest, test the full stack

It's a pyramid because:
- Unit tests are cheapest to write, run, and maintain → have the most
- Each layer is slower and more expensive than the layer below
- A broad base of unit tests gives fast, specific feedback on where something broke
- A narrow top of E2E tests gives confidence that the system works end-to-end

The anti-pattern (ice cream cone) has many E2E tests and few unit tests — this leads to slow CI, flaky tests, and poor failure isolation.

---

### Q2: How do you unit test a handler that depends on a database?

**Answer:** The key is the **repository pattern**:

1. Define a `UserRepository` **interface** with methods like `FindByID`, `Create`
2. The handler depends on the interface, not the concrete PostgreSQL implementation
3. In tests, inject a **mock implementation** of the interface
4. Use `testify/mock` (Go), `jest.fn()` (Node.js), or `AsyncMock` (Python) to set up return values

The handler test becomes:
```go
mockRepo := &MockUserRepository{}
mockRepo.On("FindByID", mock.Anything, "123").Return(expectedUser, nil)
handler := NewUserHandler(NewUserService(mockRepo))
// call handler with httptest.NewRecorder, assert response
```

The test is fast (no DB), deterministic (controlled return values), and focused on handler logic.

---

### Q3: What is the repository pattern and why does it make testing easier?

**Answer:** The repository pattern abstracts data access behind an interface. Instead of calling `db.Query("SELECT * FROM users WHERE id = $1", id)` directly in your service, you call `repo.FindByID(ctx, id)`.

**Why it makes testing easier:**
1. **Swappable implementations** — swap `PostgresUserRepo` for `MockUserRepo` in tests
2. **No test database needed** — mock returns whatever the test specifies
3. **Test business logic in isolation** — the service test doesn't care whether FindByID queries PostgreSQL or a file
4. **Clean separation** — SQL logic is in one place (repository), business logic is in another (service)

Without the repository pattern, services contain SQL directly, making them hard to unit test — you'd need a real database for every service test.

---

### Q4: What is the difference between a mock and a stub?

**Answer:**
- **Stub** — returns a pre-configured response, no assertions on how it was called. "Whenever you ask for user 123, here's what to return." A stub is used to control indirect input to the system under test.

- **Mock** — has expectations. You assert that it was called with specific arguments, a specific number of times. If the mock was called differently than expected, the test fails. A mock is used to verify indirect output from the system under test.

**Practical example:**
```go
// Stub — just controls what gets returned, no assertions
stubRepo := &UserRepository{}
stubRepo.FindByIDFunc = func(ctx context.Context, id string) (*User, error) {
    return &User{ID: "123"}, nil // always returns this, regardless of call pattern
}

// Mock — verifies calls
mockRepo := &MockUserRepository{}
mockRepo.On("FindByID", mock.Anything, "123").Return(&User{ID: "123"}, nil)
// ...
mockRepo.AssertExpectations(t) // fails if FindByID was never called, or called with different args
```

In practice, testify/mock is technically a mock (it has expectations), but many people use "mock" colloquially to mean both.

---

### Q5: What is table-driven testing in Go?

**Answer:** Table-driven testing is the Go idiom for testing multiple inputs/outputs for the same function in one test function. You define a slice of test cases (the "table"), each with inputs, expected outputs, and a name. Then you loop over them with `t.Run()`.

**Benefits:**
- All test cases for a function in one place — easy to see coverage
- Adding a case = adding one struct literal
- `t.Run()` creates sub-tests — each has its own pass/fail, output, and can be run individually with `-run TestName/subtest_name`
- Consistent structure across the codebase

It maps directly to parametrize in pytest and `it.each()` in Jest — different syntax, same concept.

---

### Q6: How do you use testcontainers for integration tests?

**Answer:** Testcontainers is a library that programmatically starts Docker containers for use in tests. Instead of maintaining a separate test DB or using mocks for integration tests, you start a real PostgreSQL container in `TestMain`:

```go
func TestMain(m *testing.M) {
    ctx := context.Background()
    pg, err := postgres.RunContainer(ctx,
        testcontainers.WithImage("postgres:16"),
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
        testcontainers.WithWaitStrategy(wait.ForLog("database system is ready")),
    )
    if err != nil {
        log.Fatal(err)
    }
    defer pg.Terminate(ctx)

    connStr, _ := pg.ConnectionString(ctx, "sslmode=disable")
    testDB = connectDB(connStr)
    runMigrations(testDB)

    os.Exit(m.Run())
}
```

**Benefits:** Tests run against a real database — no SQLite incompatibilities, no "works in test, fails in prod" surprises. **Trade-off:** Requires Docker, slower startup (seconds rather than milliseconds), but you get real-world fidelity for integration tests.

---

## 12. Resources

- [Go Testing Package Documentation](https://pkg.go.dev/testing)
- [Testify — assertions and mocks for Go](https://github.com/stretchr/testify)
- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Supertest — HTTP assertions for Node.js](https://github.com/ladjs/supertest)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Hypothesis — property-based testing for Python](https://hypothesis.readthedocs.io/)
- [The Practical Test Pyramid — Ham Vocke](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Test Doubles — Martin Fowler](https://martinfowler.com/bliki/TestDouble.html)

---

**Next:** [Part 12.2: Integration Testing & API Testing](./12-integration-api-testing.md)
