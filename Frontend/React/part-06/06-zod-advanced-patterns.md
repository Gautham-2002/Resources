# Part 6.2: Zod Advanced Patterns

## What You'll Learn

- Schema composition and reuse
- Conditional validation with refine and superRefine
- Cross-field validation
- Async validation
- Custom error maps
- Discriminated unions for complex forms
- Recursive schemas
- Testing validation logic

---

## Table of Contents

1. [Schema Composition](#schema-composition)
2. [Refine & SuperRefine](#refine--superrefine)
3. [Cross-Field Validation](#cross-field-validation)
4. [Async Validation](#async-validation)
5. [Custom Error Maps](#custom-error-maps)
6. [Recursive Schemas](#recursive-schemas)
7. [Branded Types](#branded-types)
8. [Schema Pipelines](#schema-pipelines)
9. [Testing Validation](#testing-validation)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Resources](#resources)

---

## Schema Composition

### Building Complex Schemas from Simple Ones

```typescript
import { z } from 'zod';

// Base building blocks
const AddressSchema = z.object({
  street: z.string().min(1, 'Street is required'),
  city: z.string().min(1, 'City is required'),
  state: z.string().length(2, 'State must be 2-letter code'),
  zip: z.string().regex(/^\d{5}(-\d{4})?$/, 'Invalid zip code'),
  country: z.string().default('US'),
});

const PhoneSchema = z.string()
  .regex(/^\+?[\d\s\-()]{10,}$/, 'Invalid phone number');

const TimestampSchema = z.object({
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

// Compose into complex schema
const CustomerSchema = z.object({
  name: z.string().min(1),
  email: z.string().email(),
  phone: PhoneSchema.optional(),
  billingAddress: AddressSchema,
  shippingAddress: AddressSchema.optional(),
}).merge(TimestampSchema);

type Customer = z.infer<typeof CustomerSchema>;
```

### Intersection (AND)

```typescript
const HasId = z.object({ id: z.number() });
const HasName = z.object({ name: z.string() });

// Intersection: must satisfy BOTH schemas
const Named = z.intersection(HasId, HasName);
// Equivalent:
const Named2 = HasId.and(HasName);
// type: { id: number; name: string }
```

---

## Refine & SuperRefine

### refine: Custom Validation Logic

```typescript
// Simple custom validation
const PasswordSchema = z.string()
  .min(8, 'Password must be at least 8 characters')
  .refine(
    (val) => /[A-Z]/.test(val),
    { message: 'Must contain uppercase letter' }
  )
  .refine(
    (val) => /[0-9]/.test(val),
    { message: 'Must contain a number' }
  )
  .refine(
    (val) => /[!@#$%^&*]/.test(val),
    { message: 'Must contain a special character' }
  );

// Refine on objects
const DateRangeSchema = z.object({
  startDate: z.string().datetime(),
  endDate: z.string().datetime(),
}).refine(
  (data) => new Date(data.endDate) > new Date(data.startDate),
  {
    message: 'End date must be after start date',
    path: ['endDate'], // Attach error to specific field
  }
);
```

### superRefine: Multiple Custom Errors

```typescript
const RegistrationSchema = z.object({
  username: z.string(),
  password: z.string(),
  confirmPassword: z.string(),
}).superRefine((data, ctx) => {
  // Check password match
  if (data.password !== data.confirmPassword) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Passwords do not match',
      path: ['confirmPassword'],
    });
  }

  // Check password strength
  if (data.password.length < 8) {
    ctx.addIssue({
      code: z.ZodIssueCode.too_small,
      minimum: 8,
      type: 'string',
      inclusive: true,
      message: 'Password must be at least 8 characters',
      path: ['password'],
    });
  }

  // Check username is not same as password
  if (data.username === data.password) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Password cannot be same as username',
      path: ['password'],
    });
  }
});
```

---

## Cross-Field Validation

### Common Patterns

```typescript
// Payment form with conditional validation
const PaymentSchema = z.discriminatedUnion('method', [
  z.object({
    method: z.literal('credit_card'),
    cardNumber: z.string().regex(/^\d{16}$/, 'Must be 16 digits'),
    expiry: z.string().regex(/^\d{2}\/\d{2}$/, 'Format: MM/YY'),
    cvv: z.string().regex(/^\d{3,4}$/, 'Must be 3-4 digits'),
  }),
  z.object({
    method: z.literal('bank_transfer'),
    accountNumber: z.string().min(8, 'Invalid account number'),
    routingNumber: z.string().length(9, 'Must be 9 digits'),
  }),
  z.object({
    method: z.literal('paypal'),
    paypalEmail: z.string().email('Invalid PayPal email'),
  }),
]);

// Shipping form: same address checkbox
const OrderSchema = z.object({
  billingAddress: AddressSchema,
  sameAsShipping: z.boolean(),
  shippingAddress: AddressSchema.optional(),
}).refine(
  (data) => data.sameAsShipping || data.shippingAddress !== undefined,
  {
    message: 'Shipping address is required when different from billing',
    path: ['shippingAddress'],
  }
);
```

---

## Async Validation

```typescript
// Check if username is available (API call)
const UsernameSchema = z.string()
  .min(3, 'Username must be at least 3 characters')
  .max(20, 'Username must be at most 20 characters')
  .regex(/^[a-zA-Z0-9_]+$/, 'Only letters, numbers, and underscores');

const RegistrationSchema = z.object({
  username: UsernameSchema,
  email: z.string().email(),
  password: z.string().min(8),
}).superRefine(async (data, ctx) => {
  // Check username availability
  const isAvailable = await checkUsernameAvailability(data.username);
  if (!isAvailable) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Username is already taken',
      path: ['username'],
    });
  }

  // Check email availability
  const emailExists = await checkEmailExists(data.email);
  if (emailExists) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Email is already registered',
      path: ['email'],
    });
  }
});

// Must use parseAsync for async schemas
const result = await RegistrationSchema.safeParseAsync(formData);
```

---

## Custom Error Maps

```typescript
// Global error map (customize all default messages)
const customErrorMap: z.ZodErrorMap = (issue, ctx) => {
  // Customize by error code
  switch (issue.code) {
    case z.ZodIssueCode.invalid_type:
      if (issue.expected === 'string') {
        return { message: 'This field is required' };
      }
      return { message: `Expected ${issue.expected}, got ${issue.received}` };

    case z.ZodIssueCode.too_small:
      if (issue.type === 'string') {
        return { message: `Must be at least ${issue.minimum} characters` };
      }
      return { message: `Must be at least ${issue.minimum}` };

    case z.ZodIssueCode.too_big:
      return { message: `Must be at most ${issue.maximum}` };

    default:
      return { message: ctx.defaultError };
  }
};

// Set globally
z.setErrorMap(customErrorMap);
```

---

## Recursive Schemas

```typescript
// Tree/nested structure (e.g., comments with replies)
interface Comment {
  id: number;
  text: string;
  author: string;
  replies: Comment[];
}

const CommentSchema: z.ZodType<Comment> = z.lazy(() =>
  z.object({
    id: z.number(),
    text: z.string(),
    author: z.string(),
    replies: z.array(CommentSchema),
  })
);

// File system tree
interface FileNode {
  name: string;
  type: 'file' | 'directory';
  children?: FileNode[];
}

const FileNodeSchema: z.ZodType<FileNode> = z.lazy(() =>
  z.object({
    name: z.string(),
    type: z.enum(['file', 'directory']),
    children: z.array(FileNodeSchema).optional(),
  })
);
```

---

## Branded Types

```typescript
// Branded types prevent mixing up similar types
const UserId = z.string().uuid().brand<'UserId'>();
const OrderId = z.string().uuid().brand<'OrderId'>();

type UserId = z.infer<typeof UserId>;
type OrderId = z.infer<typeof OrderId>;

// Now TypeScript prevents accidental misuse
function getUser(id: UserId) { /* ... */ }
function getOrder(id: OrderId) { /* ... */ }

const userId = UserId.parse('550e8400-e29b-41d4-a716-446655440000');
const orderId = OrderId.parse('550e8400-e29b-41d4-a716-446655440001');

getUser(userId);   // ✅
getUser(orderId);  // ❌ Type error! OrderId is not UserId
```

---

## Schema Pipelines

```typescript
// Pipeline: validate → transform → validate again
const AgeFromString = z.string()
  .transform((val) => parseInt(val, 10))
  .pipe(z.number().min(0).max(150));

AgeFromString.parse("25");   // Returns 25 (number)
AgeFromString.parse("abc");  // Error (NaN fails number check)
AgeFromString.parse("-5");   // Error (fails min(0))

// Complex pipeline: CSV string → array → validated items
const TagsPipeline = z.string()
  .transform((val) => val.split(',').map(s => s.trim()).filter(Boolean))
  .pipe(z.array(z.string().min(1)).min(1, 'At least one tag required'));

TagsPipeline.parse("react, typescript, zod");
// Returns ["react", "typescript", "zod"]
```

---

## Testing Validation

```typescript
// __tests__/schemas/user.schema.test.ts
import { describe, it, expect } from 'vitest';
import { UserSchema, CreateUserSchema } from '@/schemas/user.schema';

describe('UserSchema', () => {
  it('should validate a correct user', () => {
    const validUser = {
      id: 1,
      name: 'John Doe',
      email: 'john@example.com',
      role: 'admin',
    };

    const result = UserSchema.safeParse(validUser);
    expect(result.success).toBe(true);
  });

  it('should reject invalid email', () => {
    const result = UserSchema.safeParse({
      id: 1,
      name: 'John',
      email: 'not-an-email',
      role: 'user',
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.flatten().fieldErrors.email).toBeDefined();
    }
  });

  it('should reject invalid role', () => {
    const result = UserSchema.safeParse({
      id: 1,
      name: 'John',
      email: 'john@example.com',
      role: 'superadmin', // Not in enum
    });

    expect(result.success).toBe(false);
  });

  it('should apply default values', () => {
    const schema = CreateUserSchema.extend({
      role: z.enum(['admin', 'user']).default('user'),
    });

    const result = schema.parse({ name: 'John', email: 'j@j.com' });
    expect(result.role).toBe('user');
  });
});
```

---

## Common Patterns & Best Practices

### Pattern 1: Form Schema with Confirm Password

```typescript
export const SignUpSchema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'At least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});
```

### Pattern 2: Pagination Schema

```typescript
export const PaginationSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  sortBy: z.string().optional(),
  sortOrder: z.enum(['asc', 'desc']).default('asc'),
});
```

### Pattern 3: API Error Schema

```typescript
export const ApiErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  details: z.record(z.string(), z.array(z.string())).optional(),
  timestamp: z.string().datetime(),
});
```

---

## Common Pitfalls

### Pitfall 1: refine Doesn't Run if Base Validation Fails

```typescript
// ❌ refine won't execute if email or password fail first
const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
}).refine(/* ... */);

// This is by design — Zod short-circuits on first error
```

### Pitfall 2: Object Keys Are Stripped by Default

```typescript
const schema = z.object({ name: z.string() });
const result = schema.parse({ name: 'John', extra: 'data' });
// result = { name: 'John' } — extra is stripped!

// Use .passthrough() to keep unknown keys
// Use .strict() to throw on unknown keys
```

---

## Resources

- **Zod Documentation:** https://zod.dev/
- **Zod Recipes:** https://github.com/colinhacks/zod/discussions
- **Form Validation Patterns:** https://zod.dev/?id=refine
- **Branded Types:** https://zod.dev/?id=brand

---

**Next:** [Part 6.3: React Hook Form + Zod Integration](./06-react-hook-form-zod.md)
