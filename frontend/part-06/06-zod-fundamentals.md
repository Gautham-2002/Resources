# Part 6.1: Zod Fundamentals

## What You'll Learn

- What schema validation is and why it matters
- Why Zod over Yup, Joi, and other validators
- Basic schema creation and type inference
- Built-in validators and transformations
- Custom error messages
- TypeScript integration and type inference
- Parsing vs safeParsing

---

## Table of Contents

1. [Why Schema Validation](#why-schema-validation)
2. [Why Zod](#why-zod)
3. [Basic Schemas](#basic-schemas)
4. [Type Inference](#type-inference)
5. [Built-in Validators](#built-in-validators)
6. [Object Schemas](#object-schemas)
7. [Array Schemas](#array-schemas)
8. [Union & Discriminated Unions](#union--discriminated-unions)
9. [Parsing & Error Handling](#parsing--error-handling)
10. [Custom Error Messages](#custom-error-messages)
11. [Transformations](#transformations)
12. [Common Patterns & Best Practices](#common-patterns--best-practices)
13. [Common Pitfalls](#common-pitfalls)
14. [Resources](#resources)

---

## Why Schema Validation

### The Problem

```typescript
// API returns data - but is it what you expect?
const response = await fetch('/api/users/1');
const user = await response.json();

// TypeScript says user is `any`
// What if API changed? What if fields are missing?
console.log(user.name.toUpperCase()); // Could crash!
```

### The Solution: Runtime Validation

```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string().email(),
  age: z.number().min(0).max(150),
});

// Now validate at runtime
const result = UserSchema.safeParse(apiData);

if (result.success) {
  // TypeScript KNOWS the shape here
  console.log(result.data.name.toUpperCase()); // Safe!
} else {
  console.error('Invalid data:', result.error);
}
```

---

## Why Zod

### Comparison with Alternatives

```typescript
// Yup (older, less TypeScript-friendly)
const yupSchema = yup.object({
  name: yup.string().required(),
  age: yup.number().positive().integer(),
});
// ❌ Type inference is weak
// ❌ Different API for optional vs required

// Joi (designed for Node.js, heavy)
const joiSchema = Joi.object({
  name: Joi.string().required(),
  age: Joi.number().positive().integer(),
});
// ❌ Not TypeScript-first
// ❌ Large bundle size (~150KB)

// Zod (TypeScript-first, modern)
const zodSchema = z.object({
  name: z.string(),
  age: z.number().positive().int(),
});
type User = z.infer<typeof zodSchema>; // Perfect type!
// ✅ TypeScript-first design
// ✅ Small bundle (~13KB)
// ✅ Excellent type inference
// ✅ Composable schemas
```

### Key Advantages

```
1. TypeScript-first: Designed for TS from day one
2. Type inference: z.infer<typeof schema> gives exact types
3. Zero dependencies: Small, self-contained
4. Composable: Build complex schemas from simple ones
5. Ecosystem: Works with React Hook Form, tRPC, etc.
6. Developer experience: Excellent autocomplete
```

---

## Basic Schemas

### Primitives

```typescript
import { z } from 'zod';

// String
const nameSchema = z.string();
nameSchema.parse("John");      // ✅ Returns "John"
nameSchema.parse(42);          // ❌ Throws ZodError

// Number
const ageSchema = z.number();
ageSchema.parse(25);           // ✅
ageSchema.parse("25");         // ❌

// Boolean
const isActiveSchema = z.boolean();
isActiveSchema.parse(true);    // ✅
isActiveSchema.parse("true");  // ❌

// Date
const createdAtSchema = z.date();
createdAtSchema.parse(new Date()); // ✅

// Null, Undefined, Void
const nullSchema = z.null();
const undefinedSchema = z.undefined();

// Literal
const statusSchema = z.literal('active');
statusSchema.parse('active');  // ✅
statusSchema.parse('inactive'); // ❌

// Enum
const roleSchema = z.enum(['admin', 'user', 'moderator']);
roleSchema.parse('admin');     // ✅
roleSchema.parse('superadmin'); // ❌
```

### Optional & Nullable

```typescript
// Optional (string | undefined)
const optionalName = z.string().optional();
optionalName.parse(undefined); // ✅
optionalName.parse("John");   // ✅
optionalName.parse(null);     // ❌

// Nullable (string | null)
const nullableName = z.string().nullable();
nullableName.parse(null);      // ✅
nullableName.parse("John");    // ✅
nullableName.parse(undefined); // ❌

// Both (string | null | undefined)
const flexibleName = z.string().optional().nullable();

// Default values
const withDefault = z.string().default('Unknown');
withDefault.parse(undefined);  // Returns "Unknown"
withDefault.parse("John");     // Returns "John"
```

---

## Type Inference

### The Power of z.infer

```typescript
// Define schema once
const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string().email(),
  role: z.enum(['admin', 'user']),
  profile: z.object({
    bio: z.string().optional(),
    avatar: z.string().url().optional(),
  }),
  tags: z.array(z.string()),
  createdAt: z.string().datetime(),
});

// Infer the TypeScript type automatically!
type User = z.infer<typeof UserSchema>;

// Equivalent to:
// type User = {
//   id: number;
//   name: string;
//   email: string;
//   role: 'admin' | 'user';
//   profile: {
//     bio?: string | undefined;
//     avatar?: string | undefined;
//   };
//   tags: string[];
//   createdAt: string;
// }

// Use the type
function displayUser(user: User) {
  console.log(user.name);
  console.log(user.profile.bio ?? 'No bio');
}
```

### Input vs Output Types

```typescript
const TransformSchema = z.object({
  age: z.string().transform(Number), // Input: string, Output: number
});

type Input = z.input<typeof TransformSchema>;
// { age: string }

type Output = z.output<typeof TransformSchema>;
// { age: number }

// z.infer is the same as z.output
type Inferred = z.infer<typeof TransformSchema>;
// { age: number }
```

---

## Built-in Validators

### String Validators

```typescript
const stringValidators = z.string()
  .min(1, 'Required')          // Minimum length
  .max(100, 'Too long')        // Maximum length
  .email('Invalid email')       // Email format
  .url('Invalid URL')           // URL format
  .uuid('Invalid UUID')         // UUID format
  .regex(/^[A-Z]/, 'Must start with uppercase')
  .startsWith('https://')
  .endsWith('.com')
  .includes('@')
  .trim()                       // Trim whitespace
  .toLowerCase()                // Transform to lowercase
  .toUpperCase();               // Transform to uppercase

// Datetime
z.string().datetime();          // ISO 8601 format
z.string().ip();                // IP address
```

### Number Validators

```typescript
const numberValidators = z.number()
  .min(0, 'Must be positive')
  .max(100, 'Must be <= 100')
  .int('Must be integer')
  .positive('Must be positive')
  .negative('Must be negative')
  .nonnegative('Must be >= 0')
  .nonpositive('Must be <= 0')
  .multipleOf(5, 'Must be multiple of 5')
  .finite('Must be finite');
```

### Coercion (Convert Types)

```typescript
// Useful for form inputs (which are always strings)
const coercedNumber = z.coerce.number();
coercedNumber.parse("42");     // Returns 42 (number)
coercedNumber.parse("abc");    // ❌ NaN error

const coercedBoolean = z.coerce.boolean();
coercedBoolean.parse("true");  // Returns true
coercedBoolean.parse("");      // Returns false

const coercedDate = z.coerce.date();
coercedDate.parse("2024-01-01"); // Returns Date object
```

---

## Object Schemas

### Basic Objects

```typescript
const PersonSchema = z.object({
  name: z.string(),
  age: z.number(),
  email: z.string().email(),
});

// Strict: reject unknown keys
const StrictPerson = PersonSchema.strict();
StrictPerson.parse({ name: 'John', age: 30, email: 'j@j.com', extra: true });
// ❌ Throws: Unrecognized key "extra"

// Strip: remove unknown keys (default behavior)
const StrippedPerson = PersonSchema.strip();

// Passthrough: keep unknown keys
const PassthroughPerson = PersonSchema.passthrough();
```

### Extending & Merging

```typescript
const BaseSchema = z.object({
  id: z.number(),
  createdAt: z.string().datetime(),
});

// Extend
const UserSchema = BaseSchema.extend({
  name: z.string(),
  email: z.string().email(),
});

// Merge two schemas
const ProfileSchema = z.object({
  bio: z.string(),
  avatar: z.string().url(),
});

const FullUserSchema = UserSchema.merge(ProfileSchema);

// Pick specific fields
const UserNameOnly = UserSchema.pick({ name: true, email: true });

// Omit specific fields
const UserWithoutId = UserSchema.omit({ id: true });

// Partial (all fields optional)
const PartialUser = UserSchema.partial();

// DeepPartial
const DeepPartialUser = UserSchema.deepPartial();

// Required (make all optional fields required)
const RequiredUser = PartialUser.required();
```

---

## Array Schemas

```typescript
// Basic array
const tagsSchema = z.array(z.string());
tagsSchema.parse(['react', 'typescript']); // ✅
tagsSchema.parse([1, 2, 3]);              // ❌

// With constraints
const constrainedArray = z.array(z.string())
  .min(1, 'At least one tag required')
  .max(10, 'Maximum 10 tags')
  .nonempty('Cannot be empty'); // Makes type non-optional

// Tuple (fixed-length, mixed types)
const coordinateSchema = z.tuple([z.number(), z.number()]);
coordinateSchema.parse([51.5, -0.12]); // ✅ [lat, lng]

// Record (string keys, typed values)
const scoresSchema = z.record(z.string(), z.number());
scoresSchema.parse({ math: 95, english: 88 }); // ✅
```

---

## Union & Discriminated Unions

### Basic Union

```typescript
const stringOrNumber = z.union([z.string(), z.number()]);
// Shorthand:
const stringOrNumber2 = z.string().or(z.number());

stringOrNumber.parse("hello"); // ✅
stringOrNumber.parse(42);      // ✅
stringOrNumber.parse(true);    // ❌
```

### Discriminated Unions (Important Pattern)

```typescript
// Use when objects share a common "type" field
const EventSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('click'),
    x: z.number(),
    y: z.number(),
  }),
  z.object({
    type: z.literal('keypress'),
    key: z.string(),
    ctrlKey: z.boolean(),
  }),
  z.object({
    type: z.literal('scroll'),
    scrollY: z.number(),
  }),
]);

type Event = z.infer<typeof EventSchema>;

// TypeScript narrows the type based on 'type' field
function handleEvent(event: Event) {
  switch (event.type) {
    case 'click':
      console.log(event.x, event.y); // TS knows x, y exist
      break;
    case 'keypress':
      console.log(event.key); // TS knows key exists
      break;
  }
}
```

---

## Parsing & Error Handling

### parse vs safeParse

```typescript
const schema = z.string().email();

// parse: Throws on failure
try {
  const email = schema.parse('invalid');
} catch (error) {
  if (error instanceof z.ZodError) {
    console.log(error.issues);
  }
}

// safeParse: Returns result object (recommended)
const result = schema.safeParse('invalid');

if (result.success) {
  console.log(result.data); // Typed correctly
} else {
  console.log(result.error.issues);
  // [{ code: 'invalid_string', validation: 'email', message: 'Invalid email' }]
}
```

### Error Formatting

```typescript
const UserSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
  age: z.number().min(18, 'Must be 18+'),
});

const result = UserSchema.safeParse({
  name: '',
  email: 'bad',
  age: 15,
});

if (!result.success) {
  // Flat format (great for forms)
  const formatted = result.error.flatten();
  console.log(formatted.fieldErrors);
  // {
  //   name: ['Name is required'],
  //   email: ['Invalid email'],
  //   age: ['Must be 18+']
  // }

  // Or format for nested display
  const formattedNested = result.error.format();
  console.log(formattedNested.name?._errors);
  // ['Name is required']
}
```

---

## Custom Error Messages

```typescript
const UserSchema = z.object({
  name: z.string({
    required_error: 'Name is required',
    invalid_type_error: 'Name must be a string',
  }).min(2, { message: 'Name must be at least 2 characters' }),

  email: z.string()
    .min(1, 'Email is required')
    .email('Please enter a valid email'),

  age: z.number({
    required_error: 'Age is required',
    invalid_type_error: 'Age must be a number',
  })
    .min(18, 'You must be at least 18 years old')
    .max(120, 'Please enter a valid age'),

  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain an uppercase letter')
    .regex(/[0-9]/, 'Password must contain a number')
    .regex(/[^A-Za-z0-9]/, 'Password must contain a special character'),
});
```

---

## Transformations

```typescript
// Transform during parsing
const FormSchema = z.object({
  // Trim whitespace and lowercase
  email: z.string().trim().toLowerCase().email(),

  // Convert string to number
  age: z.string().transform(Number).pipe(z.number().min(0)),

  // Parse comma-separated tags
  tags: z.string().transform((val) => val.split(',').map(s => s.trim())),

  // Default values
  role: z.enum(['admin', 'user']).default('user'),

  // Preprocess (run before validation)
  price: z.preprocess(
    (val) => (typeof val === 'string' ? parseFloat(val) : val),
    z.number().positive()
  ),
});
```

---

## Common Patterns & Best Practices

### Pattern 1: Schema File Organization

```typescript
// schemas/user.schema.ts
import { z } from 'zod';

// Base schema
export const UserSchema = z.object({
  id: z.number(),
  name: z.string().min(1),
  email: z.string().email(),
  role: z.enum(['admin', 'user']),
});

// Derived schemas
export const CreateUserSchema = UserSchema.omit({ id: true });
export const UpdateUserSchema = UserSchema.partial().required({ id: true });
export const UserResponseSchema = UserSchema.extend({
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

// Types
export type User = z.infer<typeof UserSchema>;
export type CreateUser = z.infer<typeof CreateUserSchema>;
export type UpdateUser = z.infer<typeof UpdateUserSchema>;
```

### Pattern 2: API Response Validation

```typescript
// services/api.ts
import { z } from 'zod';

const ApiResponseSchema = <T extends z.ZodType>(dataSchema: T) =>
  z.object({
    success: z.boolean(),
    data: dataSchema,
    meta: z.object({
      total: z.number(),
      page: z.number(),
    }).optional(),
  });

// Usage
const UsersResponseSchema = ApiResponseSchema(z.array(UserSchema));

async function fetchUsers(): Promise<z.infer<typeof UsersResponseSchema>> {
  const response = await fetch('/api/users');
  const json = await response.json();
  return UsersResponseSchema.parse(json); // Validated!
}
```

### Pattern 3: Environment Variable Validation

```typescript
// config/env.ts
const EnvSchema = z.object({
  VITE_API_URL: z.string().url(),
  VITE_APP_NAME: z.string().default('My App'),
  VITE_ENABLE_ANALYTICS: z.coerce.boolean().default(false),
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
});

export const env = EnvSchema.parse(import.meta.env);
// Now env.VITE_API_URL is typed and validated!
```

---

## Common Pitfalls

### Pitfall 1: parse vs safeParse in Production

```typescript
// ❌ parse throws — can crash your app
const user = UserSchema.parse(apiData);

// ✅ safeParse returns a result — handle errors gracefully
const result = UserSchema.safeParse(apiData);
if (!result.success) {
  // Handle error
}
```

### Pitfall 2: Forgetting Coercion for Form Data

```typescript
// ❌ Form inputs are always strings
const schema = z.object({ age: z.number() });
schema.parse({ age: "25" }); // Error! "25" is not a number

// ✅ Use coercion for form data
const schema = z.object({ age: z.coerce.number() });
schema.parse({ age: "25" }); // ✅ Returns { age: 25 }
```

### Pitfall 3: Not Reusing Schemas

```typescript
// ❌ Duplicating schema definitions
const createUserSchema = z.object({ name: z.string(), email: z.string().email() });
const updateUserSchema = z.object({ name: z.string(), email: z.string().email(), id: z.number() });

// ✅ Derive from base schema
const baseSchema = z.object({ name: z.string(), email: z.string().email() });
const createUserSchema = baseSchema;
const updateUserSchema = baseSchema.extend({ id: z.number() });
```

---

## Resources

- **Zod Documentation:** https://zod.dev/
- **Zod GitHub:** https://github.com/colinhacks/zod
- **Zod Error Handling:** https://zod.dev/ERROR_HANDLING
- **TypeScript Utility Types with Zod:** https://zod.dev/?id=type-inference
- **Valibot (Alternative):** https://valibot.dev/ (smaller bundle, similar API)

---

**Next:** [Part 6.2: Zod Advanced Patterns](./06-zod-advanced-patterns.md)
