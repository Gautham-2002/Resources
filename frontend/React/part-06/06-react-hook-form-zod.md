# Part 6.3: React Hook Form + Zod Integration

## What You'll Learn

- Why React Hook Form (RHF) is the standard
- Uncontrolled vs controlled form philosophy
- useForm hook and configuration
- Zod resolver integration
- useFieldArray for dynamic fields
- Error handling and display
- Performance optimization
- Validation triggers and modes

---

## Table of Contents

1. [Why React Hook Form](#why-react-hook-form)
2. [Setup & Basic Usage](#setup--basic-usage)
3. [Zod Integration with Resolver](#zod-integration-with-resolver)
4. [Form Fields & Registration](#form-fields--registration)
5. [Error Handling & Display](#error-handling--display)
6. [useFieldArray - Dynamic Fields](#usefieldarray---dynamic-fields)
7. [Validation Modes](#validation-modes)
8. [Watch & Dependent Fields](#watch--dependent-fields)
9. [Form State & Submission](#form-state--submission)
10. [Performance Optimization](#performance-optimization)
11. [Common Patterns & Best Practices](#common-patterns--best-practices)
12. [Common Pitfalls](#common-pitfalls)
13. [Resources](#resources)

---

## Why React Hook Form

### The Problem with Controlled Forms

```typescript
// ❌ Controlled: Every keystroke triggers re-render
function ControlledForm() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  // ... more state for every field

  // Every keystroke → setState → re-render entire form
  // 10 fields × fast typing = hundreds of re-renders
}

// ✅ React Hook Form: Uncontrolled (minimal re-renders)
function UncontrolledForm() {
  const { register, handleSubmit } = useForm();
  // Refs track values — no re-renders on input!
  // Only re-renders on validation or submission
}
```

### RHF Key Benefits

```
1. Performance: Uses refs, not state (minimal re-renders)
2. Bundle size: ~9KB (vs Formik ~13KB)
3. TypeScript: Full type safety with generics
4. Zod integration: First-class resolver support
5. Developer experience: Simple API, powerful features
6. Validation: Flexible modes (onChange, onBlur, onSubmit)
```

---

## Setup & Basic Usage

### Installation

```bash
pnpm add react-hook-form @hookform/resolvers zod
```

### Basic Form Without Zod

```typescript
import { useForm } from 'react-hook-form';

interface FormData {
  name: string;
  email: string;
}

function BasicForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>();

  const onSubmit = async (data: FormData) => {
    console.log(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input
        {...register('name', { required: 'Name is required' })}
        placeholder="Name"
      />
      {errors.name && <span>{errors.name.message}</span>}

      <input
        {...register('email', {
          required: 'Email is required',
          pattern: {
            value: /^\S+@\S+$/,
            message: 'Invalid email',
          },
        })}
        placeholder="Email"
      />
      {errors.email && <span>{errors.email.message}</span>}

      <button type="submit" disabled={isSubmitting}>
        Submit
      </button>
    </form>
  );
}
```

---

## Zod Integration with Resolver

### The Recommended Approach

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// Define schema with Zod
const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Invalid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  rememberMe: z.boolean().default(false),
});

// Infer the type
type LoginForm = z.infer<typeof loginSchema>;

function LoginForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  });

  const onSubmit = async (data: LoginForm) => {
    // data is fully typed and validated!
    await loginUser(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          type="email"
          {...register('email')}
          className={cn(
            'mt-1 block w-full rounded-md border px-3 py-2',
            errors.email ? 'border-red-500' : 'border-gray-300'
          )}
        />
        {errors.email && (
          <p className="mt-1 text-sm text-red-500">{errors.email.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          type="password"
          {...register('password')}
          className={cn(
            'mt-1 block w-full rounded-md border px-3 py-2',
            errors.password ? 'border-red-500' : 'border-gray-300'
          )}
        />
        {errors.password && (
          <p className="mt-1 text-sm text-red-500">{errors.password.message}</p>
        )}
      </div>

      <div className="flex items-center gap-2">
        <input id="rememberMe" type="checkbox" {...register('rememberMe')} />
        <label htmlFor="rememberMe" className="text-sm">Remember me</label>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  );
}
```

---

## Error Handling & Display

### Reusable Error Component

```typescript
// components/ui/FormField.tsx
import { type FieldError } from 'react-hook-form';

interface FormFieldProps {
  label: string;
  error?: FieldError;
  children: React.ReactNode;
  required?: boolean;
}

function FormField({ label, error, children, required }: FormFieldProps) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {error && (
        <p className="text-sm text-red-500 flex items-center gap-1" role="alert">
          <span>⚠</span> {error.message}
        </p>
      )}
    </div>
  );
}

// Usage
<FormField label="Email" error={errors.email} required>
  <input {...register('email')} className="input-styles" />
</FormField>
```

---

## useFieldArray - Dynamic Fields

```typescript
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const orderSchema = z.object({
  customerName: z.string().min(1, 'Name is required'),
  items: z.array(z.object({
    product: z.string().min(1, 'Product is required'),
    quantity: z.coerce.number().min(1, 'Min quantity is 1'),
    price: z.coerce.number().positive('Price must be positive'),
  })).min(1, 'At least one item required'),
});

type OrderForm = z.infer<typeof orderSchema>;

function OrderForm() {
  const { register, control, handleSubmit, formState: { errors } } = useForm<OrderForm>({
    resolver: zodResolver(orderSchema),
    defaultValues: {
      customerName: '',
      items: [{ product: '', quantity: 1, price: 0 }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'items',
  });

  return (
    <form onSubmit={handleSubmit(console.log)} className="space-y-6">
      <input {...register('customerName')} placeholder="Customer Name" />

      {fields.map((field, index) => (
        <div key={field.id} className="flex gap-4 items-start">
          <input
            {...register(`items.${index}.product`)}
            placeholder="Product"
          />
          <input
            type="number"
            {...register(`items.${index}.quantity`)}
            placeholder="Qty"
          />
          <input
            type="number"
            step="0.01"
            {...register(`items.${index}.price`)}
            placeholder="Price"
          />
          {fields.length > 1 && (
            <button type="button" onClick={() => remove(index)}>✕</button>
          )}
        </div>
      ))}

      <button type="button" onClick={() => append({ product: '', quantity: 1, price: 0 })}>
        + Add Item
      </button>

      <button type="submit">Submit Order</button>
    </form>
  );
}
```

---

## Validation Modes

```typescript
const form = useForm({
  resolver: zodResolver(schema),

  // Mode options:
  mode: 'onSubmit',     // Default: validate only on submit
  mode: 'onBlur',       // Validate when field loses focus
  mode: 'onChange',      // Validate on every change (expensive)
  mode: 'onTouched',    // Validate on blur first, then on change
  mode: 'all',          // Validate on blur AND change

  // Recommended for most forms:
  mode: 'onBlur',        // Shows errors after user leaves field
  reValidateMode: 'onChange', // Clears errors as user fixes them
});
```

---

## Watch & Dependent Fields

```typescript
const { register, watch, setValue } = useForm<FormData>();

// Watch a single field
const selectedCountry = watch('country');

// Conditional rendering based on field value
return (
  <form>
    <select {...register('country')}>
      <option value="US">United States</option>
      <option value="CA">Canada</option>
      <option value="UK">United Kingdom</option>
    </select>

    {selectedCountry === 'US' && (
      <select {...register('state')}>
        <option value="CA">California</option>
        <option value="NY">New York</option>
      </select>
    )}

    {selectedCountry === 'CA' && (
      <select {...register('province')}>
        <option value="ON">Ontario</option>
        <option value="BC">British Columbia</option>
      </select>
    )}
  </form>
);
```

---

## Form State & Submission

```typescript
function CompleteForm() {
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: {
      errors,          // Field errors
      isSubmitting,    // True during async submit
      isSubmitSuccessful, // True after successful submit
      isDirty,         // True if any field changed
      isValid,         // True if no errors
      dirtyFields,     // Which fields changed
      touchedFields,   // Which fields were focused
      submitCount,     // Number of submit attempts
    },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    try {
      await api.createUser(data);
    } catch (error) {
      // Set server-side errors on form
      if (error.field === 'email') {
        setError('email', {
          type: 'server',
          message: 'Email already exists',
        });
      } else {
        setError('root', {
          type: 'server',
          message: 'Something went wrong',
        });
      }
    }
  };

  // Reset after successful submission
  useEffect(() => {
    if (isSubmitSuccessful) {
      reset();
    }
  }, [isSubmitSuccessful, reset]);

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* Root error (not tied to any field) */}
      {errors.root && (
        <div className="bg-red-50 text-red-800 p-3 rounded mb-4">
          {errors.root.message}
        </div>
      )}

      {/* Fields... */}

      <button type="submit" disabled={isSubmitting || !isDirty}>
        {isSubmitting ? 'Saving...' : 'Save'}
      </button>
    </form>
  );
}
```

---

## Performance Optimization

### Isolate Re-renders with Controller

```typescript
import { Controller } from 'react-hook-form';

// For complex/third-party components that need controlled behavior
<Controller
  control={control}
  name="category"
  render={({ field, fieldState: { error } }) => (
    <Select
      value={field.value}
      onChange={field.onChange}
      onBlur={field.onBlur}
      options={categories}
      error={error?.message}
    />
  )}
/>
```

### Debounced Validation

```typescript
const form = useForm({
  resolver: zodResolver(schema),
  mode: 'onChange',
  delayError: 500, // Delay showing errors by 500ms
});
```

---

## Common Patterns & Best Practices

### Pattern 1: Reusable Form Wrapper

```typescript
// components/forms/Form.tsx
interface FormProps<T extends z.ZodType> {
  schema: T;
  onSubmit: (data: z.infer<T>) => Promise<void>;
  defaultValues?: Partial<z.infer<T>>;
  children: (methods: UseFormReturn<z.infer<T>>) => React.ReactNode;
}

function Form<T extends z.ZodType>({
  schema,
  onSubmit,
  defaultValues,
  children,
}: FormProps<T>) {
  const methods = useForm({
    resolver: zodResolver(schema),
    defaultValues,
    mode: 'onBlur',
  });

  return (
    <form onSubmit={methods.handleSubmit(onSubmit)}>
      {children(methods)}
    </form>
  );
}

// Usage
<Form schema={loginSchema} onSubmit={handleLogin}>
  {({ register, formState: { errors } }) => (
    <>
      <input {...register('email')} />
      <button type="submit">Login</button>
    </>
  )}
</Form>
```

### Pattern 2: Schema-Driven Forms

```typescript
// Define schema
const contactSchema = z.object({
  name: z.string().min(1, 'Required'),
  email: z.string().email('Invalid email'),
  message: z.string().min(10, 'Min 10 characters'),
});

type ContactForm = z.infer<typeof contactSchema>;

// The form component is completely type-safe
// Changing the schema automatically updates form types
```

---

## Common Pitfalls

### Pitfall 1: Not Using defaultValues

```typescript
// ❌ Controlled/uncontrolled warning
useForm<FormData>({
  resolver: zodResolver(schema),
});

// ✅ Always provide defaultValues
useForm<FormData>({
  resolver: zodResolver(schema),
  defaultValues: {
    name: '',
    email: '',
  },
});
```

### Pitfall 2: Register vs Controller

```typescript
// Use register for native HTML inputs
<input {...register('name')} />

// Use Controller for:
// - Custom components (Select, DatePicker)
// - Components that need value/onChange props
// - Third-party UI libraries
<Controller name="date" control={control} render={({ field }) => (
  <DatePicker value={field.value} onChange={field.onChange} />
)} />
```

### Pitfall 3: Forgetting to Handle Server Errors

```typescript
// ❌ Server errors are lost
const onSubmit = async (data) => {
  await api.submit(data); // If this throws, user sees nothing
};

// ✅ Catch and display server errors
const onSubmit = async (data) => {
  try {
    await api.submit(data);
  } catch (error) {
    setError('root', { message: error.message });
  }
};
```

---

## Resources

- **React Hook Form Documentation:** https://react-hook-form.com/
- **React Hook Form + Zod:** https://react-hook-form.com/get-started#SchemaValidation
- **@hookform/resolvers:** https://github.com/react-hook-form/resolvers
- **React Hook Form DevTools:** https://react-hook-form.com/dev-tools

---

**Next:** [Part 6.4: Form Patterns & Complex Scenarios](./06-form-patterns.md)
