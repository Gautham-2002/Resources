# Part 3.2: Request Validation

## What You'll Learn
- Why input validation at the boundary is the first line of defense (not the last)
- The three layers of validation: structural, type, and business-rule
- JSON binding, struct tags, and annotation-driven validation in Go, Node.js, and Python
- Writing custom validators for domain-specific rules (email format, UUID, custom business logic)
- Producing actionable, field-level error responses — not "validation failed"
- The difference between input sanitization and validation
- Validating file uploads: MIME type sniffing, size limits, content inspection
- Query parameter and path parameter validation
- The unique challenge of PATCH (partial update) validation

---

## Table of Contents

1. [Why Validate at the Boundary](#1-why-validate-at-the-boundary)
2. [The Three Layers of Validation](#2-the-three-layers-of-validation)
3. [Validation Error Response Design](#3-validation-error-response-design)
4. [JSON Binding and Struct Tags](#4-json-binding-and-struct-tags)
5. [Custom Validators](#5-custom-validators)
6. [Query Parameter Validation](#6-query-parameter-validation)
7. [Path Parameter Validation](#7-path-parameter-validation)
8. [PATCH — Partial Update Validation](#8-patch--partial-update-validation)
9. [Input Sanitization vs Validation](#9-input-sanitization-vs-validation)
10. [File Upload Validation](#10-file-upload-validation)
11. [Implementation Examples](#11-implementation-examples)
12. [Common Patterns & Best Practices](#common-patterns--best-practices)
13. [Common Pitfalls](#common-pitfalls)
14. [Interview Questions](#interview-questions)
15. [Resources](#resources)

---

## 1. Why Validate at the Boundary

**"Trust nothing that comes from outside your process boundary."**

This principle is the foundation of secure, reliable backends. Every piece of data entering your system — HTTP request body, query parameters, path parameters, HTTP headers — is attacker-controlled input. Validation at the boundary means:

1. Reject malformed or invalid data immediately, before any business logic executes
2. Fail fast with a clear error message, rather than propagating garbage deep into your system
3. Prevent SQL injection, buffer overflows, and logic errors that stem from unexpected data shapes

```
Client                      Backend
  │                            │
  │── POST /users ────────────►│
  │   { "age": -5, "email": "not-an-email" }
  │                            │
  │                            ├─ Validation Layer  ◄── BOUNDARY
  │                            │   ✗ email: invalid format
  │                            │   ✗ age: must be positive
  │                            │
  │◄── 422 Unprocessable ──────┤
  │   { "errors": [...] }      │
  │                            │
  │                       Business logic      ← NEVER reached with invalid input
  │                       Database            ← NEVER reached with invalid input
```

### Defense in Depth

Validation is not a single layer — it exists at multiple levels:

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Client-side validation (UX only, NEVER trust this)    │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: API Gateway / Load Balancer (rate limiting, basic auth)│
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Handler / Controller (structural + type validation)  ◄─── This file
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Service Layer (business rules)                        │
├─────────────────────────────────────────────────────────────────┤
│  Layer 5: Database constraints (NOT NULL, UNIQUE, FK)           │
└─────────────────────────────────────────────────────────────────┘
```

Your API handler is responsible for Layers 3 and partially 4. Database constraints are a last-resort safety net, not a substitute for application-level validation.

---

## 2. The Three Layers of Validation

### Layer 1: Structural Validation — Can it be parsed?

```
Input: "not json at all"
Error: 400 Bad Request — "body must be valid JSON"

Input: {"name": "Alice", "age": }
Error: 400 Bad Request — "body must be valid JSON (syntax error at position 24)"
```

This layer answers: "Does the input conform to the expected wire format (JSON, form data, multipart)?"

### Layer 2: Type Validation — Are the types correct?

```
Input: {"age": "twenty-five"}
Error: 422 — age must be an integer

Input: {"active": "yes"}
Error: 422 — active must be a boolean
```

This layer answers: "Once parsed, do the values have the expected types and are required fields present?"

### Layer 3: Business Rule Validation — Does it make sense?

```
Input: {"age": -5}
Error: 422 — age must be greater than 0

Input: {"start_date": "2025-12-01", "end_date": "2025-11-01"}
Error: 422 — end_date must be after start_date

Input: {"username": "admin"}
Error: 422 — username 'admin' is reserved
```

This layer answers: "Is the value semantically valid within our domain?"

### The Status Code Question (Interview-Ready)

| Scenario | HTTP Status |
|---|---|
| Can't parse JSON body | `400 Bad Request` |
| JSON parses but field types wrong | `422 Unprocessable Entity` |
| Business rule violation | `422 Unprocessable Entity` |
| Valid input but not authorized | `403 Forbidden` |
| Valid input but resource not found | `404 Not Found` |

`422` is the correct status for "the request was well-formed but semantically invalid." Some APIs use `400` for everything — that's less precise but acceptable if consistent.

---

## 3. Validation Error Response Design

**One of the most underrated interview topics.** A vague `"validation failed"` error is useless to the client. A good validation error response:

1. Uses a consistent error schema
2. Identifies **which field** failed
3. Explains **why** it failed (without leaking internal details)
4. Returns **all** errors at once (don't make the client fix one error, resubmit, find next error)

### The Error Schema

```json
{
  "error": "validation_failed",
  "message": "Request body contains invalid fields",
  "details": [
    {
      "field": "email",
      "message": "must be a valid email address",
      "value": "not-an-email"
    },
    {
      "field": "age",
      "message": "must be greater than 0",
      "value": -5
    },
    {
      "field": "username",
      "message": "is required"
    }
  ]
}
```

### Design Decisions

**Should you echo the invalid value back?**
- For string/number values: often helpful for debugging
- Never echo passwords, tokens, or sensitive data
- Consider whether your logs redact it too

**Nested field paths:**
```json
{
  "field": "address.zip_code",
  "message": "must be a 5-digit US zip code"
}
```

**Array field paths:**
```json
{
  "field": "items[2].quantity",
  "message": "must be greater than 0"
}
```

---

## 4. JSON Binding and Struct Tags

### Go: Struct Tags for Validation

Go uses struct tags to describe how fields are parsed and validated. The most widely used validation library is `github.com/go-playground/validator/v10`.

```go
type CreateUserRequest struct {
    // json:"name"      — JSON field name
    // validate:"required,min=2,max=100"  — validation rules
    Name     string `json:"name"     validate:"required,min=2,max=100"`
    Email    string `json:"email"    validate:"required,email"`
    Age      int    `json:"age"      validate:"required,min=1,max=150"`
    Phone    string `json:"phone"    validate:"omitempty,e164"`   // optional but if present, must be E.164
    Role     string `json:"role"     validate:"required,oneof=user admin moderator"`
    Password string `json:"password" validate:"required,min=8"`
}
```

**Common `validator` tags:**

| Tag | Meaning |
|---|---|
| `required` | Field must be present and non-zero |
| `omitempty` | Skip validation if field is zero value |
| `min=N` | Minimum length (string) or value (number) |
| `max=N` | Maximum length (string) or value (number) |
| `email` | Valid email format |
| `url` | Valid URL |
| `uuid` / `uuid4` | Valid UUID |
| `oneof=a b c` | Must be one of the listed values |
| `e164` | E.164 phone number format (+12125551234) |
| `len=N` | Exact length |
| `gt=N` / `gte=N` | Greater than / greater than or equal |
| `lt=N` / `lte=N` | Less than / less than or equal |
| `alphanum` | Alphanumeric only |
| `eqfield=Field` | Must equal another field (e.g., password confirmation) |

### FastAPI/Pydantic: Type Annotations + Field constraints

Pydantic v2 derives validation rules from Python type annotations and `Field()` constraints:

```python
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import Optional, Literal
import re

class CreateUserRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr  # validated email type
    age: int = Field(gt=0, lt=150)
    phone: Optional[str] = Field(default=None, pattern=r'^\+[1-9]\d{1,14}$')
    role: Literal["user", "admin", "moderator"] = "user"
    password: str = Field(min_length=8)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self) -> "CreateUserRequest":
        if self.password != self.confirm_password:
            raise ValueError("passwords do not match")
        return self
```

### Zod (Node.js): Schema-first validation

```javascript
import { z } from 'zod';

const createUserSchema = z.object({
  name: z.string().min(2).max(100),
  email: z.string().email(),
  age: z.number().int().min(1).max(150),
  phone: z.string().regex(/^\+[1-9]\d{1,14}$/).optional(),
  role: z.enum(['user', 'admin', 'moderator']),
  password: z.string().min(8),
  confirmPassword: z.string(),
}).refine(
  (data) => data.password === data.confirmPassword,
  {
    message: 'passwords do not match',
    path: ['confirmPassword'],
  }
);

// Infer TypeScript type from schema
type CreateUserRequest = z.infer<typeof createUserSchema>;
```

---

## 5. Custom Validators

### Go: Custom Validation Functions

```go
package validation

import (
    "regexp"
    "github.com/go-playground/validator/v10"
)

var validate *validator.Validate

func init() {
    validate = validator.New()

    // Register custom tag names from JSON tags (so errors show "email" not "Email")
    validate.RegisterTagNameFunc(func(fld reflect.StructField) string {
        name := strings.SplitN(fld.Tag.Get("json"), ",", 2)[0]
        if name == "-" {
            return ""
        }
        return name
    })

    // Custom validator: no spaces allowed
    validate.RegisterValidation("nospaces", func(fl validator.FieldLevel) bool {
        return !strings.Contains(fl.Field().String(), " ")
    })

    // Custom validator: valid slug (lowercase alphanumeric + hyphens)
    slugRegex := regexp.MustCompile(`^[a-z0-9]+(?:-[a-z0-9]+)*$`)
    validate.RegisterValidation("slug", func(fl validator.FieldLevel) bool {
        return slugRegex.MatchString(fl.Field().String())
    })

    // Cross-field validator: start must be before end
    validate.RegisterStructValidation(func(sl validator.StructLevel) {
        type DateRange struct {
            StartDate time.Time
            EndDate   time.Time
        }
        req, ok := sl.Current().Interface().(DateRange)
        if !ok {
            return
        }
        if !req.EndDate.After(req.StartDate) {
            sl.ReportError(req.EndDate, "end_date", "EndDate", "gtfield", "start_date")
        }
    }, DateRange{})
}

type DateRange struct {
    StartDate time.Time `json:"start_date" validate:"required"`
    EndDate   time.Time `json:"end_date"   validate:"required"`
}

type CreatePostRequest struct {
    Title   string `json:"title"   validate:"required,min=3,max=200"`
    Slug    string `json:"slug"    validate:"required,slug"`
    Content string `json:"content" validate:"required,min=10"`
}
```

### Custom Validator with Database Check (Uniqueness)

```go
// Unique email validator — requires DB access
// Pass the DB as a parameter via closure
func UniqueEmailValidator(db *sql.DB) validator.Func {
    return func(fl validator.FieldLevel) bool {
        email := fl.Field().String()
        var count int
        err := db.QueryRow(
            "SELECT COUNT(*) FROM users WHERE email = $1", email,
        ).Scan(&count)
        if err != nil {
            // If DB check fails, fail open (reject) to be safe
            return false
        }
        return count == 0
    }
}

// Register:
validate.RegisterValidation("unique_email", UniqueEmailValidator(db))
```

**Interview note:** Be careful with validators that call the database — they add latency to every request. Consider whether the uniqueness check belongs in the service layer (where you can return a domain error) rather than the validation layer.

---

## 6. Query Parameter Validation

Query parameters need the same rigor as request bodies.

### Common patterns:

```
GET /users?page=0&limit=1000&sort=invalidfield
```

Issues to catch:
- `page=0` → should be ≥ 1
- `limit=1000` → exceeds max allowed (e.g., 100)
- `sort=invalidfield` → not a sortable field

```go
// Go: query param parsing and validation
type ListUsersQuery struct {
    Page   int    `schema:"page"   validate:"min=1"`
    Limit  int    `schema:"limit"  validate:"min=1,max=100"`
    Sort   string `schema:"sort"   validate:"omitempty,oneof=created_at name email"`
    Order  string `schema:"order"  validate:"omitempty,oneof=asc desc"`
    Search string `schema:"search" validate:"omitempty,max=100"`
}

func parseQuery(r *http.Request, dst interface{}) error {
    decoder := schema.NewDecoder()
    decoder.IgnoreUnknownKeys(true)
    if err := decoder.Decode(dst, r.URL.Query()); err != nil {
        return fmt.Errorf("invalid query parameters: %w", err)
    }
    return validate.Struct(dst)
}

// Usage in handler:
func listUsersHandler(w http.ResponseWriter, r *http.Request) {
    var q ListUsersQuery
    q.Page = 1    // defaults
    q.Limit = 20
    q.Order = "desc"
    q.Sort = "created_at"
    
    if err := parseQuery(r, &q); err != nil {
        renderValidationError(w, err)
        return
    }
    // use q.Page, q.Limit, q.Sort etc.
}
```

### Fastapi: Query parameters are first-class citizens

```python
from fastapi import Query
from typing import Literal, Optional

@app.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1, description="Page number, 1-indexed"),
    limit: int = Query(default=20, ge=1, le=100, description="Results per page"),
    sort: Literal["created_at", "name", "email"] = Query(default="created_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    search: Optional[str] = Query(default=None, max_length=100),
):
    # FastAPI automatically validates and returns 422 if constraints violated
    return {"page": page, "limit": limit, "sort": sort}
```

### Express: Manual query validation with Zod

```javascript
import { z } from 'zod';

const listUsersQuerySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),   // coerce: "2" → 2
  limit: z.coerce.number().int().min(1).max(100).default(20),
  sort: z.enum(['created_at', 'name', 'email']).default('created_at'),
  order: z.enum(['asc', 'desc']).default('desc'),
  search: z.string().max(100).optional(),
});

function validateQuery(schema) {
  return (req, res, next) => {
    const result = schema.safeParse(req.query);
    if (!result.success) {
      return res.status(422).json(formatZodErrors(result.error));
    }
    req.validatedQuery = result.data;
    next();
  };
}

app.get('/users', validateQuery(listUsersQuerySchema), (req, res) => {
  const { page, limit, sort, order, search } = req.validatedQuery;
  res.json({ page, limit, sort });
});
```

---

## 7. Path Parameter Validation

Path parameters are always strings at the transport layer — you must parse and validate them.

### Common path parameter types:

- **Integer ID:** `/users/42` — must be a positive integer
- **UUID:** `/posts/550e8400-e29b-41d4-a716-446655440000` — must be valid UUID v4
- **Slug:** `/articles/my-first-post` — lowercase alphanumeric + hyphens

```go
// Go + chi: path parameter validation
func getUserHandler(w http.ResponseWriter, r *http.Request) {
    idStr := chi.URLParam(r, "id")

    // Parse as UUID
    userID, err := uuid.Parse(idStr)
    if err != nil {
        http.Error(w, `{"error":"invalid user ID format, expected UUID"}`, http.StatusBadRequest)
        return
    }
    
    // Now userID is a typed uuid.UUID, not a raw string
    user, err := userService.GetByID(r.Context(), userID)
    if errors.Is(err, ErrNotFound) {
        http.Error(w, `{"error":"user not found"}`, http.StatusNotFound)
        return
    }
    // ...
}

// For integer IDs:
func getPostHandler(w http.ResponseWriter, r *http.Request) {
    idStr := chi.URLParam(r, "id")
    id, err := strconv.ParseInt(idStr, 10, 64)
    if err != nil || id <= 0 {
        http.Error(w, `{"error":"invalid post ID"}`, http.StatusBadRequest)
        return
    }
    // ...
}
```

### FastAPI: Automatic path parameter parsing

```python
from uuid import UUID

@app.get("/users/{user_id}")
async def get_user(user_id: UUID) -> dict:
    # FastAPI automatically validates UUID format
    # Returns 422 if user_id is not a valid UUID
    return {"id": str(user_id)}

@app.get("/posts/{post_id}")
async def get_post(post_id: int = Path(gt=0)) -> dict:
    # FastAPI parses string → int, validates gt=0
    return {"id": post_id}
```

---

## 8. PATCH — Partial Update Validation

`PATCH` is the hardest HTTP method to validate correctly because:

1. Not all fields are required — only the fields sent should be validated
2. You can't distinguish "field not sent" from "field sent as null" with standard JSON
3. Business rules may require cross-field validation on only the updated fields

### The Problem with Naive Approaches

```go
// NAIVE (broken) approach:
type UpdateUserRequest struct {
    Name  string `json:"name"  validate:"required,min=2"` // WRONG
    Email string `json:"email" validate:"required,email"` // WRONG for PATCH
}
// If client sends only {"name": "Alice"}, email fails "required" validation
// but we don't want to require email on a PATCH!
```

### Solution 1: Pointer Fields (Go)

Use `*string` for optional fields. `nil` means "not provided", non-nil means "provided (even if empty string)".

```go
type UpdateUserRequest struct {
    Name  *string `json:"name"  validate:"omitempty,min=2,max=100"`
    Email *string `json:"email" validate:"omitempty,email"`
    Age   *int    `json:"age"   validate:"omitempty,min=1,max=150"`
}

func updateUserHandler(w http.ResponseWriter, r *http.Request) {
    userID := chi.URLParam(r, "id")
    
    var req UpdateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, `{"error":"invalid JSON"}`, http.StatusBadRequest)
        return
    }
    
    if err := validate.Struct(req); err != nil {
        renderValidationError(w, err)
        return
    }

    // Build update set — only update fields that were provided
    update := UserUpdate{ID: userID}
    if req.Name != nil {
        update.Name = req.Name
    }
    if req.Email != nil {
        update.Email = req.Email
    }
    if req.Age != nil {
        update.Age = req.Age
    }
    
    if update.IsEmpty() {
        http.Error(w, `{"error":"no fields to update"}`, http.StatusBadRequest)
        return
    }
    
    // apply update...
}
```

### Solution 2: JSON Merge Patch (RFC 7396)

JSON Merge Patch is the standard for partial updates. Fields present in the patch are applied; fields absent are left unchanged; fields set to `null` are deleted.

```go
import "encoding/json"

func applyMergePatch(original, patch json.RawMessage) (json.RawMessage, error) {
    // Unmarshal both to maps
    var orig, p map[string]interface{}
    json.Unmarshal(original, &orig)
    json.Unmarshal(patch, &p)
    
    for k, v := range p {
        if v == nil {
            delete(orig, k)  // null means delete
        } else {
            orig[k] = v      // present means update
        }
    }
    return json.Marshal(orig)
}
```

### Solution 3: Pydantic Partial Models (Python/FastAPI)

```python
from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    name: str
    email: str
    age: int

# For PATCH: all fields optional
class UpdateUserRequest(UserBase):
    model_config = {"extra": "forbid"}  # reject unknown fields
    
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None

# Alternative: use Pydantic's partial mechanism
from pydantic import create_model

def make_partial(model: type[BaseModel]) -> type[BaseModel]:
    fields = {
        name: (Optional[field.annotation], None)
        for name, field in model.model_fields.items()
    }
    return create_model(f"Partial{model.__name__}", **fields)

PartialUser = make_partial(UserBase)
```

### Solution 4: Zod's `partial()` method (Node.js)

```javascript
const userSchema = z.object({
  name: z.string().min(2).max(100),
  email: z.string().email(),
  age: z.number().int().min(1).max(150),
});

// All fields become optional for PATCH
const updateUserSchema = userSchema.partial().refine(
  (data) => Object.keys(data).length > 0,
  { message: 'at least one field must be provided' }
);
```

---

## 9. Input Sanitization vs Validation

These are different operations with different purposes. Confusing them is a common mistake.

| | Validation | Sanitization |
|---|---|---|
| **Purpose** | Reject invalid input | Transform input to safe form |
| **Result** | Accept or reject | Modified value |
| **When** | Before processing | Before storing/rendering |
| **Example** | "Is this a valid email?" | Strip HTML tags, trim whitespace |

**Validation example:** `"admin@example.com"` → valid, proceed. `"not-an-email"` → invalid, reject.

**Sanitization example:** `"  hello world  "` → `"hello world"` (trim whitespace). `"<script>alert(1)</script>"` → `""` or `"&lt;script&gt;..."` (strip or escape HTML).

### Key principle: Validate first, then sanitize

```go
// WRONG order:
sanitize(input)   // Sanitization can change the value!
validate(input)   // Now validating the sanitized version, which may differ

// CORRECT order:
validate(rawInput)          // Validate the raw input — reject if invalid
sanitized := sanitize(rawInput)  // Then sanitize for storage/display
store(sanitized)
```

### What to sanitize:

1. **HTML/JavaScript injection:** Any user-provided string that will be rendered in a browser — use a library like `bluemonday` (Go) or `DOMPurify` (JS) to strip/escape HTML tags
2. **Whitespace:** Trim leading/trailing whitespace from names, emails
3. **Null bytes:** Strip `\0` from strings before passing to C-backed libraries or filesystems
4. **Unicode normalization:** Normalize to NFC to prevent homoglyph attacks (`é` can be one or two codepoints)
5. **Filename sanitization:** Strip `../`, null bytes, and dangerous characters from user-provided filenames

```go
// Go: sanitize HTML with bluemonday
import "github.com/microcosm-cc/bluemonday"

policy := bluemonday.UGCPolicy()  // Allow safe HTML subset
clean := policy.Sanitize(userInput)

// Strip all HTML:
strict := bluemonday.StrictPolicy()
plainText := strict.Sanitize(userInput)
```

---

## 10. File Upload Validation

File uploads are a particularly dangerous input vector. Attackers can:
- Upload executable files (PHP, shell scripts) and trigger remote code execution
- Upload extremely large files to exhaust disk space
- Upload a file with a legitimate extension but malicious content (image polyglots)
- Bypass extension checks by sending `Content-Type: image/jpeg` with a PHP payload

### Multi-layer file validation:

```
1. File size limit       — reject before reading full content
2. Extension check       — cheap first filter (easily bypassed alone)
3. MIME type from header — can be spoofed by client
4. Magic bytes (content sniffing) — read first N bytes, compare known signatures
5. Deep inspection       — for images: try to decode with image library
```

### Magic Bytes (File Signatures)

File type is determined by the first few bytes of the content, not the extension or `Content-Type` header.

```
JPEG:   FF D8 FF
PNG:    89 50 4E 47 0D 0A 1A 0A
GIF:    47 49 46 38 (GIF8)
PDF:    25 50 44 46 (%PDF)
ZIP:    50 4B 03 04
```

```go
package main

import (
    "bytes"
    "fmt"
    "io"
    "mime"
    "mime/multipart"
    "net/http"
    "path/filepath"
    "strings"
)

const (
    maxFileSize    = 10 << 20 // 10 MB
    maxMemoryParse = 5 << 20  // 5 MB in memory, rest on disk
)

var allowedMIMETypes = map[string]bool{
    "image/jpeg": true,
    "image/png":  true,
    "image/gif":  true,
    "image/webp": true,
}

var allowedExtensions = map[string]bool{
    ".jpg": true, ".jpeg": true,
    ".png": true,
    ".gif": true,
    ".webp": true,
}

// detectMIME reads the first 512 bytes to detect MIME type using magic bytes
func detectMIME(r io.ReadSeeker) (string, error) {
    buf := make([]byte, 512)
    n, err := r.Read(buf)
    if err != nil && err != io.EOF {
        return "", err
    }
    // Reset so the caller can read from the beginning
    if _, err := r.Seek(0, io.SeekStart); err != nil {
        return "", err
    }
    return http.DetectContentType(buf[:n]), nil
}

func uploadHandler(w http.ResponseWriter, r *http.Request) {
    // 1. Limit total request size
    r.Body = http.MaxBytesReader(w, r.Body, maxFileSize+1024) // +1024 for form fields

    if err := r.ParseMultipartForm(maxMemoryParse); err != nil {
        if strings.Contains(err.Error(), "request body too large") {
            http.Error(w, `{"error":"file too large, max 10MB"}`, http.StatusRequestEntityTooLarge)
            return
        }
        http.Error(w, `{"error":"invalid multipart form"}`, http.StatusBadRequest)
        return
    }

    file, header, err := r.FormFile("file")
    if err != nil {
        http.Error(w, `{"error":"missing file field"}`, http.StatusBadRequest)
        return
    }
    defer file.Close()

    // 2. Check file size (already limited by MaxBytesReader, but explicit is clearer)
    if header.Size > maxFileSize {
        http.Error(w, `{"error":"file too large, max 10MB"}`, http.StatusRequestEntityTooLarge)
        return
    }

    // 3. Check extension
    ext := strings.ToLower(filepath.Ext(header.Filename))
    if !allowedExtensions[ext] {
        http.Error(w, fmt.Sprintf(`{"error":"file type %s not allowed"}`, ext), http.StatusUnsupportedMediaType)
        return
    }

    // 4. Check Content-Type header (weak — client-provided, but adds a layer)
    clientMIME := header.Header.Get("Content-Type")
    if clientMIME != "" {
        mediaType, _, _ := mime.ParseMediaType(clientMIME)
        if !allowedMIMETypes[mediaType] {
            http.Error(w, `{"error":"content type not allowed"}`, http.StatusUnsupportedMediaType)
            return
        }
    }

    // 5. Magic byte detection — read first 512 bytes
    // file implements io.ReadSeeker since it's a multipart.File
    detectedMIME, err := detectMIME(file)
    if err != nil {
        http.Error(w, `{"error":"could not read file"}`, http.StatusInternalServerError)
        return
    }

    if !allowedMIMETypes[detectedMIME] {
        http.Error(w, fmt.Sprintf(`{"error":"file content detected as %s, not allowed"}`, detectedMIME), http.StatusUnsupportedMediaType)
        return
    }

    // 6. For images: attempt to decode to verify it's a valid image
    // This catches malformed images and polyglot attacks
    _, format, err := image.DecodeConfig(file)
    if err != nil {
        http.Error(w, `{"error":"invalid or corrupt image file"}`, http.StatusUnprocessableEntity)
        return
    }
    file.Seek(0, io.SeekStart) // reset after decode attempt
    _ = format

    // 7. Generate a server-side filename — NEVER use the client-provided filename directly
    safeFilename := fmt.Sprintf("%s%s", uuid.New().String(), ext)
    
    // Store to disk / S3 with safeFilename
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(map[string]string{"filename": safeFilename})
}
```

### Node.js: File upload with multer

```javascript
import multer from 'multer';
import { fromBuffer } from 'file-type';
import crypto from 'crypto';

const ALLOWED_MIME_TYPES = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp']);
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const storage = multer.memoryStorage(); // Buffer in memory for inspection

const upload = multer({
  storage,
  limits: { fileSize: MAX_FILE_SIZE },
  fileFilter: (req, file, cb) => {
    // Check MIME type from multer (from Content-Type, easily spoofed — we verify below)
    if (!ALLOWED_MIME_TYPES.has(file.mimetype)) {
      return cb(new Error(`file type ${file.mimetype} not allowed`));
    }
    cb(null, true);
  },
});

app.post('/upload', upload.single('file'), async (req, res, next) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'no file provided' });
    }

    // Magic byte detection — file-type library reads first bytes
    const fileTypeResult = await fromBuffer(req.file.buffer);
    if (!fileTypeResult || !ALLOWED_MIME_TYPES.has(fileTypeResult.mime)) {
      return res.status(415).json({
        error: `file content detected as ${fileTypeResult?.mime ?? 'unknown'}, not allowed`,
      });
    }

    // Generate safe server-side filename
    const ext = fileTypeResult.ext;
    const safeFilename = `${crypto.randomUUID()}.${ext}`;

    // Upload to S3 / store to disk using safeFilename
    res.status(201).json({ filename: safeFilename });
  } catch (err) {
    next(err);
  }
});
```

---

## 11. Implementation Examples

### Go + Chi: Full Validation Setup

```go
package main

import (
    "encoding/json"
    "errors"
    "net/http"
    "reflect"
    "strings"

    "github.com/go-chi/chi/v5"
    "github.com/go-playground/validator/v10"
)

// --------------------------------------------------------------------------
// Validation infrastructure
// --------------------------------------------------------------------------

var validate *validator.Validate

func init() {
    validate = validator.New(validator.WithRequiredStructEnabled())

    // Use JSON tag names in error messages, not Go field names
    validate.RegisterTagNameFunc(func(fld reflect.StructField) string {
        name := strings.SplitN(fld.Tag.Get("json"), ",", 2)[0]
        if name == "-" {
            return ""
        }
        return name
    })
}

// ValidationError represents a single field error
type ValidationError struct {
    Field   string `json:"field"`
    Message string `json:"message"`
    Value   any    `json:"value,omitempty"`
}

// ValidationErrorResponse is the response body for 422 errors
type ValidationErrorResponse struct {
    Error   string            `json:"error"`
    Message string            `json:"message"`
    Details []ValidationError `json:"details"`
}

// parseAndValidate decodes JSON from the request body and validates the struct.
// Returns nil if valid, writes error response and returns error if not.
func parseAndValidate(w http.ResponseWriter, r *http.Request, dst any) error {
    w.Header().Set("Content-Type", "application/json")

    dec := json.NewDecoder(r.Body)
    dec.DisallowUnknownFields() // reject unknown JSON keys — forces explicit field mapping
    
    if err := dec.Decode(dst); err != nil {
        var syntaxErr *json.SyntaxError
        var unmarshalTypeErr *json.UnmarshalTypeError

        var status int
        var message string

        switch {
        case errors.As(err, &syntaxErr):
            status = http.StatusBadRequest
            message = fmt.Sprintf("request body contains malformed JSON at position %d", syntaxErr.Offset)
        case errors.As(err, &unmarshalTypeErr):
            status = http.StatusUnprocessableEntity
            message = fmt.Sprintf("field %q must be of type %v", unmarshalTypeErr.Field, unmarshalTypeErr.Type)
        case strings.HasPrefix(err.Error(), "json: unknown field"):
            status = http.StatusBadRequest
            message = err.Error()
        default:
            status = http.StatusBadRequest
            message = "request body must be valid JSON"
        }

        w.WriteHeader(status)
        json.NewEncoder(w).Encode(map[string]string{"error": message})
        return err
    }

    if err := validate.Struct(dst); err != nil {
        var validationErrors validator.ValidationErrors
        if !errors.As(err, &validationErrors) {
            w.WriteHeader(http.StatusInternalServerError)
            json.NewEncoder(w).Encode(map[string]string{"error": "internal error"})
            return err
        }

        details := make([]ValidationError, 0, len(validationErrors))
        for _, fe := range validationErrors {
            details = append(details, ValidationError{
                Field:   fe.Field(),
                Message: humanizeValidationTag(fe),
            })
        }

        w.WriteHeader(http.StatusUnprocessableEntity)
        json.NewEncoder(w).Encode(ValidationErrorResponse{
            Error:   "validation_failed",
            Message: "request body contains invalid fields",
            Details: details,
        })
        return errors.New("validation failed")
    }

    return nil
}

// humanizeValidationTag converts validator tag names to readable messages
func humanizeValidationTag(fe validator.FieldError) string {
    switch fe.Tag() {
    case "required":
        return "is required"
    case "email":
        return "must be a valid email address"
    case "min":
        if fe.Type().Kind() == reflect.String {
            return fmt.Sprintf("must be at least %s characters", fe.Param())
        }
        return fmt.Sprintf("must be at least %s", fe.Param())
    case "max":
        if fe.Type().Kind() == reflect.String {
            return fmt.Sprintf("must be at most %s characters", fe.Param())
        }
        return fmt.Sprintf("must be at most %s", fe.Param())
    case "oneof":
        return fmt.Sprintf("must be one of: %s", strings.ReplaceAll(fe.Param(), " ", ", "))
    case "uuid4":
        return "must be a valid UUID v4"
    case "url":
        return "must be a valid URL"
    case "e164":
        return "must be a valid phone number in E.164 format (e.g., +12125551234)"
    default:
        return fmt.Sprintf("failed validation: %s", fe.Tag())
    }
}

// --------------------------------------------------------------------------
// Request/Response types
// --------------------------------------------------------------------------

type CreateUserRequest struct {
    Name            string `json:"name"             validate:"required,min=2,max=100"`
    Email           string `json:"email"            validate:"required,email"`
    Age             int    `json:"age"              validate:"required,min=1,max=150"`
    Role            string `json:"role"             validate:"required,oneof=user admin moderator"`
    Password        string `json:"password"         validate:"required,min=8"`
    ConfirmPassword string `json:"confirm_password" validate:"required,eqfield=Password"`
}

type UpdateUserRequest struct {
    Name  *string `json:"name"  validate:"omitempty,min=2,max=100"`
    Email *string `json:"email" validate:"omitempty,email"`
    Age   *int    `json:"age"   validate:"omitempty,min=1,max=150"`
}

// --------------------------------------------------------------------------
// Handlers
// --------------------------------------------------------------------------

func createUserHandler(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    if err := parseAndValidate(w, r, &req); err != nil {
        return // response already written
    }

    // Business logic
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(map[string]string{
        "id":    "new-user-id",
        "email": req.Email,
        "name":  req.Name,
    })
}

func updateUserHandler(w http.ResponseWriter, r *http.Request) {
    userID := chi.URLParam(r, "id")
    
    var req UpdateUserRequest
    if err := parseAndValidate(w, r, &req); err != nil {
        return
    }
    
    // Check at least one field provided
    if req.Name == nil && req.Email == nil && req.Age == nil {
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusBadRequest)
        json.NewEncoder(w).Encode(map[string]string{
            "error": "at least one field must be provided for update",
        })
        return
    }
    
    _ = userID
    w.WriteHeader(http.StatusOK)
}
```

---

### Node.js + Express: Full Validation with Zod

```javascript
import express from 'express';
import { z, ZodError } from 'zod';

const app = express();
app.use(express.json());

// ── Zod schemas ─────────────────────────────────────────────────────────────

const createUserSchema = z.object({
  name: z.string().min(2, 'must be at least 2 characters').max(100),
  email: z.string().email('must be a valid email address'),
  age: z.number({ required_error: 'is required' })
        .int()
        .min(1, 'must be at least 1')
        .max(150, 'must be at most 150'),
  role: z.enum(['user', 'admin', 'moderator'], {
    errorMap: () => ({ message: 'must be one of: user, admin, moderator' }),
  }),
  password: z.string().min(8, 'must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine(
  (data) => data.password === data.confirmPassword,
  {
    message: 'passwords do not match',
    path: ['confirm_password'],
  }
);

const updateUserSchema = z.object({
  name: z.string().min(2).max(100).optional(),
  email: z.string().email().optional(),
  age: z.number().int().min(1).max(150).optional(),
}).refine(
  (data) => Object.values(data).some((v) => v !== undefined),
  { message: 'at least one field must be provided' }
);

// ── Zod error formatter ──────────────────────────────────────────────────────

function formatZodError(error) {
  const details = error.errors.map((issue) => ({
    field: issue.path.join('.') || 'body',
    message: issue.message,
  }));
  return {
    error: 'validation_failed',
    message: 'Request contains invalid fields',
    details,
  };
}

// ── Validation middleware factory ────────────────────────────────────────────

function validateBody(schema) {
  return (req, res, next) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(422).json(formatZodError(result.error));
    }
    req.body = result.data; // replace with parsed + coerced data
    next();
  };
}

function validateQuery(schema) {
  return (req, res, next) => {
    const result = schema.safeParse(req.query);
    if (!result.success) {
      return res.status(422).json(formatZodError(result.error));
    }
    req.validatedQuery = result.data;
    next();
  };
}

// ── Routes ──────────────────────────────────────────────────────────────────

const listUsersQuerySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
});

app.post('/users', validateBody(createUserSchema), (req, res) => {
  // req.body is now typed and validated
  const { name, email, role } = req.body;
  res.status(201).json({ id: 'new-id', name, email, role });
});

app.patch('/users/:id', validateBody(updateUserSchema), (req, res) => {
  res.json({ updated: true, fields: Object.keys(req.body) });
});

app.get('/users', validateQuery(listUsersQuerySchema), (req, res) => {
  const { page, limit } = req.validatedQuery;
  res.json({ page, limit, users: [] });
});

// Error handling for malformed JSON
app.use((err, req, res, next) => {
  if (err.type === 'entity.parse.failed') {
    return res.status(400).json({ error: 'request body must be valid JSON' });
  }
  next(err);
});
```

---

### Python + FastAPI: Full Validation with Pydantic v2

```python
from __future__ import annotations

from typing import Annotated, Optional, Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Path, Query, status
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)
from pydantic_core import PydanticCustomError

app = FastAPI()

# ── Request schemas ──────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # reject unknown fields
    
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    age: int = Field(gt=0, lt=150)
    role: Literal["user", "admin", "moderator"] = "user"
    password: str = Field(min_length=8)
    confirm_password: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()  # also sanitize: trim whitespace

    @model_validator(mode="after")
    def passwords_must_match(self) -> "CreateUserRequest":
        if self.password != self.confirm_password:
            raise PydanticCustomError(
                "passwords_mismatch",
                "passwords do not match",
            )
        return self


class UpdateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(default=None, gt=0, lt=150)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UpdateUserRequest":
        if all(v is None for v in (self.name, self.email, self.age)):
            raise ValueError("at least one field must be provided")
        return self


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(body: CreateUserRequest) -> UserResponse:
    # FastAPI automatically validates body, returns 422 on failure
    # ValidationError is automatically formatted by FastAPI as:
    # {
    #   "detail": [
    #     { "type": "...", "loc": ["body", "email"], "msg": "...", "input": "..." }
    #   ]
    # }
    from uuid import uuid4
    return UserResponse(
        id=uuid4(),
        name=body.name,
        email=body.email,
        role=body.role,
    )


@app.patch("/users/{user_id}")
async def update_user(
    user_id: UUID = Path(description="UUID of the user to update"),
    body: UpdateUserRequest = ...,
) -> dict:
    return {"id": str(user_id), "updated_fields": body.model_dump(exclude_none=True)}


@app.get("/users")
async def list_users(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    sort: Literal["created_at", "name", "email"] = Query(default="created_at"),
    search: Annotated[Optional[str], Query(max_length=100)] = None,
) -> dict:
    return {"page": page, "limit": limit, "sort": sort, "search": search}


# Custom 422 error response format (optional: make it match your error schema)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        details.append({
            "field": field_path or "body",
            "message": error["msg"].replace("Value error, ", ""),
            "type": error["type"],
        })
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_failed",
            "message": "Request contains invalid fields",
            "details": details,
        },
    )
```

---

## Common Patterns & Best Practices

### 1. Validate at the Entry Point, Never Deep in the Stack
Business logic and data layers should receive **already-validated** data. If your repository layer needs to check whether an email is valid, you've let garbage past your boundary.

### 2. Return All Validation Errors at Once
Never return one error, force the client to fix it, then return the next. Collect all errors from all fields and return them in one `422` response. Users and API consumers hate fix-one-at-a-time error loops.

### 3. Use Consistent Error Schemas
Pick one error response shape and use it everywhere. SDKs and clients that consume your API will write error parsing code once. Inconsistency means every endpoint needs special-cased error handling.

### 4. Reject Unknown Fields
Unknown fields in request bodies can indicate:
- Typos in field names (silent data loss — the intended field is ignored)
- Attempts to inject extra fields (mass assignment vulnerabilities)

Go: `dec.DisallowUnknownFields()`  
Pydantic: `model_config = ConfigDict(extra="forbid")`  
Zod: `.strict()` instead of `.object()`

### 5. Set Maximum Body Size
Always limit request body size to prevent memory exhaustion:
```go
r.Body = http.MaxBytesReader(w, r.Body, 1<<20) // 1 MB
```

### 6. Validate Enums Explicitly
Don't just check `len > 0` for a string that should be an enum value. If `role` can only be `user`, `admin`, or `moderator`, validate exactly that. Unknown values in database ENUM columns cause application errors at write time.

### 7. Don't Validate in the Database
Database constraints (`NOT NULL`, `CHECK`, `UNIQUE`) are a safety net, not the primary validation strategy. Application-level validation gives better error messages, can enforce complex cross-field rules, and doesn't require a round-trip to the DB to learn about an error.

---

## Common Pitfalls

- ❌ **WRONG:** Using `string` type for all path params without parsing
  ```go
  id := chi.URLParam(r, "id")
  userService.GetByID(ctx, id) // passing raw string, DB will fail with ugly error
  ```
  **✅ CORRECT:** Parse and validate path params immediately:
  ```go
  userID, err := uuid.Parse(chi.URLParam(r, "id"))
  if err != nil {
      http.Error(w, `{"error":"invalid ID"}`, 400)
      return
  }
  ```

- ❌ **WRONG:** For PATCH, marking all fields as `required` in the struct
  **✅ CORRECT:** Use pointer fields (`*string`, `*int`) with `omitempty` tag to distinguish "not provided" from "provided as zero value".

- ❌ **WRONG:** Trusting `Content-Type` header for file upload type detection
  **✅ CORRECT:** Read the first 512 bytes and use magic byte detection (`http.DetectContentType` in Go, `file-type` in Node). The `Content-Type` header is client-controlled.

- ❌ **WRONG:** Using the client-provided filename directly when storing uploaded files
  ```go
  os.WriteFile(header.Filename, data, 0644)  // Path traversal attack: "../../../etc/cron.d/malicious"
  ```
  **✅ CORRECT:** Generate a server-side UUID filename, store the original name separately in the database.

- ❌ **WRONG:** Returning first validation error only
  ```javascript
  if (!isValidEmail(body.email)) return res.status(422).json({ error: 'invalid email' });
  if (!body.name) return res.status(422).json({ error: 'name required' });
  ```
  **✅ CORRECT:** Collect all errors, return once:
  ```javascript
  const result = schema.safeParse(req.body);
  if (!result.success) return res.status(422).json(formatZodError(result.error));
  ```

- ❌ **WRONG:** Sanitizing before validating:
  ```
  sanitize(input) → validate(sanitized_input)
  ```
  **✅ CORRECT:** Validate raw input first, then sanitize before storage/rendering.

- ❌ **WRONG:** Not setting `DisallowUnknownFields` in Go JSON decoder
  **✅ CORRECT:** Unknown fields in a request body are silent bugs. Reject them to force clients to send exactly what you expect.

---

## Interview Questions

**Q1. What is the difference between validation and sanitization?**

**Answer:** Validation is a binary decision: accept or reject input based on whether it meets expected constraints. Sanitization is a transformation: modify the input to make it safe for a specific context (storage, rendering). Validation should happen first — you validate the raw input, then sanitize what passes validation for storage or display. Never sanitize as a substitute for validation; you might sanitize away something that makes the input invalid.

---

**Q2. Why should validation happen at the API boundary, not in the service or repository layer?**

**Answer:** "Fail fast" — the earlier you reject invalid data, the less work is wasted. If invalid data reaches the repository layer, you've already done route matching, middleware, auth verification, context setup, and business logic before discovering the error. Additionally, different entry points (REST API, gRPC, background jobs) might call the same service layer, but each has different input shapes. The boundary layer is where the translation from external format (JSON) to internal types happens, and that's where format and type validation belongs. Business rule validation (cross-field, domain semantics) can live in the service layer since it's often reused across entry points.

---

**Q3. How do you handle PATCH validation — when only some fields need to be validated?**

**Answer:** Three approaches, each with trade-offs:
1. **Pointer fields:** Make all PATCH fields optional using pointer types (`*string`). A `nil` pointer means "not provided," a non-nil pointer means "provided." Use `omitempty` tag to skip validation for nil fields. Check in the service layer which fields to update.
2. **JSON Merge Patch (RFC 7396):** A standard patch format where present fields are updated, absent fields are unchanged, and null means delete. Deserialize to a `map[string]any`, validate only present keys, then apply to the existing resource.
3. **Schema `.partial()` methods:** Libraries like Zod offer `.partial()` which makes all fields optional, and Pydantic supports optional fields natively. Combine with a `.refine()` check that at least one field is present.

---

**Q4. What HTTP status code should you return for a validation failure, and why?**

**Answer:** `422 Unprocessable Entity`. The distinction: `400 Bad Request` means the request is malformed (can't be parsed — syntax error, invalid JSON). `422` means the request was syntactically well-formed but semantically invalid (JSON parsed successfully, but field values violate business rules). In practice, many APIs use `400` for both, and that's acceptable if consistent. The important thing is: don't use `500` for user input errors — that signals a server-side bug, not a client error, and will confuse monitoring and alerting.

---

**Q5. How would you validate a file upload to prevent malicious uploads?**

**Answer:** Multiple layers are required because any single check can be bypassed:
1. **Size limit:** Reject before reading the full body (`MaxBytesReader` / `limits` in multer).
2. **Extension check:** Quick first filter, but easily bypassed (rename `evil.php` to `photo.jpg`).
3. **Content-Type header check:** Still client-controlled, but adds a layer.
4. **Magic byte detection:** Read first 512 bytes and compare against known file signatures. This is the most reliable check for file type. `http.DetectContentType` in Go, `file-type` npm package in Node.
5. **Deep validation:** For images, attempt to decode with an image library. A valid JPEG decoder will fail on a PHP script with a JPEG magic header prepended.
6. **Never use client-provided filenames** for storage. Generate server-side UUIDs. Store the original name in the database only, never on the filesystem path.

---

**Q6. What is a mass assignment vulnerability, and how does validation prevent it?**

**Answer:** Mass assignment is when a client sends extra fields in the request body that get directly bound to a model, setting fields the client shouldn't control. Example: a `POST /users` endpoint that accepts `{"name": "Alice", "role": "admin"}` — if the handler blindly sets all received fields on the user model, the client has just given themselves admin privileges.

Prevention:
- **Allowlist fields explicitly:** Only map the fields you expect. Go: `DisallowUnknownFields()` doesn't prevent it alone — you must also use explicit field mapping. Pydantic: `extra="forbid"`. Zod: `.strict()`.
- **Separate request types from domain types:** A `CreateUserRequest` struct should only have `name`, `email`, `password`. The `role` field belongs on the internal `User` model with a default value set by business logic, never from external input.

---

## Resources

- [go-playground/validator Documentation](https://github.com/go-playground/validator)
- [Zod Documentation](https://zod.dev)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [FastAPI Request Validation](https://fastapi.tiangolo.com/tutorial/body/)
- [RFC 7396 — JSON Merge Patch](https://datatracker.ietf.org/doc/html/rfc7396)
- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [HTTP Status Code 422 (RFC 9110)](https://httpwg.org/specs/rfc9110.html#status.422)

---

**Next:** [Part 4.1: Authentication — JWT & Sessions](../part-04/04-authentication-jwt-sessions.md)
