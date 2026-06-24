# Part 6.4: Form Patterns & Complex Scenarios

## What You'll Learn

- Multi-step form wizard pattern
- Auto-save and draft patterns
- Optimistic form updates
- Loading states and submission feedback
- Field dependencies and conditional fields
- File upload forms
- Accessibility best practices in forms

---

## Table of Contents

1. [Multi-Step Form Wizard](#multi-step-form-wizard)
2. [Auto-Save Pattern](#auto-save-pattern)
3. [Optimistic Updates](#optimistic-updates)
4. [Loading States](#loading-states)
5. [Conditional Fields](#conditional-fields)
6. [File Upload Forms](#file-upload-forms)
7. [Search with Debouncing](#search-with-debouncing)
8. [Accessibility in Forms](#accessibility-in-forms)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Resources](#resources)

---

## Multi-Step Form Wizard

### Schema Per Step

```typescript
import { z } from 'zod';

// Step 1: Personal Info
const personalInfoSchema = z.object({
  firstName: z.string().min(1, 'First name is required'),
  lastName: z.string().min(1, 'Last name is required'),
  email: z.string().email('Invalid email'),
});

// Step 2: Address
const addressSchema = z.object({
  street: z.string().min(1, 'Street is required'),
  city: z.string().min(1, 'City is required'),
  state: z.string().min(1, 'State is required'),
  zip: z.string().regex(/^\d{5}$/, 'Invalid zip code'),
});

// Step 3: Payment
const paymentSchema = z.object({
  cardNumber: z.string().regex(/^\d{16}$/, 'Invalid card number'),
  expiry: z.string().regex(/^\d{2}\/\d{2}$/, 'Format: MM/YY'),
  cvv: z.string().regex(/^\d{3,4}$/, 'Invalid CVV'),
});

// Full schema (for final submission)
const fullSchema = personalInfoSchema.merge(addressSchema).merge(paymentSchema);
type FullFormData = z.infer<typeof fullSchema>;
```

### Wizard Component

```typescript
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

const steps = [
  { schema: personalInfoSchema, title: 'Personal Info' },
  { schema: addressSchema, title: 'Address' },
  { schema: paymentSchema, title: 'Payment' },
];

function FormWizard() {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<Partial<FullFormData>>({});

  const currentSchema = steps[currentStep].schema;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(currentSchema),
    defaultValues: formData,
  });

  const onNext = (data: any) => {
    const updatedData = { ...formData, ...data };
    setFormData(updatedData);

    if (currentStep < steps.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      // Final submission
      submitForm(updatedData as FullFormData);
    }
  };

  const onBack = () => {
    setCurrentStep((prev) => Math.max(0, prev - 1));
  };

  return (
    <div className="max-w-lg mx-auto">
      {/* Progress bar */}
      <div className="flex gap-2 mb-8">
        {steps.map((step, index) => (
          <div key={step.title} className="flex-1">
            <div
              className={cn(
                'h-2 rounded-full transition-colors',
                index <= currentStep ? 'bg-blue-600' : 'bg-gray-200'
              )}
            />
            <p className="text-xs mt-1 text-gray-500">{step.title}</p>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit(onNext)} className="space-y-4">
        {/* Step 1 */}
        {currentStep === 0 && (
          <>
            <input {...register('firstName')} placeholder="First Name" />
            <input {...register('lastName')} placeholder="Last Name" />
            <input {...register('email')} placeholder="Email" />
          </>
        )}

        {/* Step 2 */}
        {currentStep === 1 && (
          <>
            <input {...register('street')} placeholder="Street" />
            <input {...register('city')} placeholder="City" />
            <input {...register('state')} placeholder="State" />
            <input {...register('zip')} placeholder="ZIP Code" />
          </>
        )}

        {/* Step 3 */}
        {currentStep === 2 && (
          <>
            <input {...register('cardNumber')} placeholder="Card Number" />
            <input {...register('expiry')} placeholder="MM/YY" />
            <input {...register('cvv')} placeholder="CVV" />
          </>
        )}

        <div className="flex justify-between pt-4">
          {currentStep > 0 && (
            <button type="button" onClick={onBack} className="px-4 py-2 border rounded">
              Back
            </button>
          )}
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded ml-auto">
            {currentStep === steps.length - 1 ? 'Submit' : 'Next'}
          </button>
        </div>
      </form>
    </div>
  );
}
```

---

## Auto-Save Pattern

```typescript
import { useForm } from 'react-hook-form';
import { useEffect, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useDebounce } from '@/hooks/useDebounce';

function AutoSaveForm({ initialData }) {
  const { register, watch, formState: { isDirty } } = useForm({
    defaultValues: initialData,
  });

  // Watch all form values
  const formValues = watch();
  const debouncedValues = useDebounce(formValues, 1000);

  const saveMutation = useMutation({
    mutationFn: (data) => api.saveDraft(data),
  });

  // Auto-save when values change (debounced)
  useEffect(() => {
    if (isDirty) {
      saveMutation.mutate(debouncedValues);
    }
  }, [debouncedValues]);

  return (
    <form className="space-y-4">
      <div className="flex items-center justify-between">
        <h2>Edit Document</h2>
        <span className="text-sm text-gray-500">
          {saveMutation.isPending && '💾 Saving...'}
          {saveMutation.isSuccess && '✅ Saved'}
          {saveMutation.isError && '❌ Save failed'}
        </span>
      </div>

      <input {...register('title')} placeholder="Title" />
      <textarea {...register('content')} placeholder="Content" rows={10} />
    </form>
  );
}
```

---

## Optimistic Updates

```typescript
function EditProfileForm({ user }) {
  const { register, handleSubmit, reset } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: user,
  });

  const updateMutation = useMutation({
    mutationFn: (data) => api.updateProfile(data),
    onMutate: async (newData) => {
      // Optimistic: show new data immediately
      // (handled by TanStack Query's optimistic updates)
    },
    onError: (error, variables, context) => {
      // Revert form to previous values on error
      reset(user);
      toast.error('Failed to update profile');
    },
    onSuccess: () => {
      toast.success('Profile updated!');
    },
  });

  return (
    <form onSubmit={handleSubmit((data) => updateMutation.mutate(data))}>
      <input {...register('name')} />
      <input {...register('bio')} />
      <button type="submit" disabled={updateMutation.isPending}>
        {updateMutation.isPending ? 'Saving...' : 'Save'}
      </button>
    </form>
  );
}
```

---

## Loading States

### Shimmer/Skeleton for Form Loading

```typescript
function FormSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-4 w-20 bg-gray-200 rounded" />
      <div className="h-10 bg-gray-200 rounded" />
      <div className="h-4 w-24 bg-gray-200 rounded" />
      <div className="h-10 bg-gray-200 rounded" />
      <div className="h-4 w-16 bg-gray-200 rounded" />
      <div className="h-24 bg-gray-200 rounded" />
      <div className="h-10 w-32 bg-gray-200 rounded" />
    </div>
  );
}

function EditForm({ id }) {
  const { data, isLoading } = useQuery({
    queryKey: ['user', id],
    queryFn: () => api.getUser(id),
  });

  if (isLoading) return <FormSkeleton />;

  return <ActualForm defaultValues={data} />;
}
```

### Submit Button States

```typescript
function SubmitButton({ isSubmitting, isDirty, isValid }) {
  return (
    <button
      type="submit"
      disabled={isSubmitting || !isDirty}
      className={cn(
        'px-6 py-2 rounded-lg font-medium transition-all',
        isSubmitting
          ? 'bg-gray-400 cursor-wait'
          : isDirty
          ? 'bg-blue-600 hover:bg-blue-700 text-white'
          : 'bg-gray-300 cursor-not-allowed text-gray-500'
      )}
    >
      {isSubmitting ? (
        <span className="flex items-center gap-2">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Saving...
        </span>
      ) : (
        'Save Changes'
      )}
    </button>
  );
}
```

---

## Conditional Fields

```typescript
const eventSchema = z.discriminatedUnion('eventType', [
  z.object({
    eventType: z.literal('online'),
    platform: z.enum(['zoom', 'meet', 'teams']),
    meetingUrl: z.string().url('Invalid URL'),
  }),
  z.object({
    eventType: z.literal('in-person'),
    venue: z.string().min(1, 'Venue is required'),
    address: z.string().min(1, 'Address is required'),
    capacity: z.coerce.number().positive(),
  }),
  z.object({
    eventType: z.literal('hybrid'),
    platform: z.enum(['zoom', 'meet', 'teams']),
    meetingUrl: z.string().url('Invalid URL'),
    venue: z.string().min(1, 'Venue is required'),
    address: z.string().min(1, 'Address is required'),
    capacity: z.coerce.number().positive(),
  }),
]);

function EventForm() {
  const { register, watch, handleSubmit } = useForm({
    resolver: zodResolver(eventSchema),
  });

  const eventType = watch('eventType');

  return (
    <form onSubmit={handleSubmit(console.log)}>
      <select {...register('eventType')}>
        <option value="online">Online</option>
        <option value="in-person">In-Person</option>
        <option value="hybrid">Hybrid</option>
      </select>

      {(eventType === 'online' || eventType === 'hybrid') && (
        <>
          <select {...register('platform')}>
            <option value="zoom">Zoom</option>
            <option value="meet">Google Meet</option>
            <option value="teams">MS Teams</option>
          </select>
          <input {...register('meetingUrl')} placeholder="Meeting URL" />
        </>
      )}

      {(eventType === 'in-person' || eventType === 'hybrid') && (
        <>
          <input {...register('venue')} placeholder="Venue Name" />
          <input {...register('address')} placeholder="Address" />
          <input type="number" {...register('capacity')} placeholder="Capacity" />
        </>
      )}

      <button type="submit">Create Event</button>
    </form>
  );
}
```

---

## File Upload Forms

```typescript
const fileSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  file: z
    .instanceof(FileList)
    .refine((files) => files.length > 0, 'File is required')
    .refine(
      (files) => files[0]?.size <= 5 * 1024 * 1024,
      'File must be less than 5MB'
    )
    .refine(
      (files) => ['image/jpeg', 'image/png', 'image/webp'].includes(files[0]?.type),
      'Only JPEG, PNG, and WebP are allowed'
    ),
});

function FileUploadForm() {
  const { register, handleSubmit, watch, formState: { errors } } = useForm({
    resolver: zodResolver(fileSchema),
  });

  const file = watch('file');
  const preview = file?.[0] ? URL.createObjectURL(file[0]) : null;

  const onSubmit = async (data) => {
    const formData = new FormData();
    formData.append('title', data.title);
    formData.append('file', data.file[0]);
    await api.upload(formData);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <input {...register('title')} placeholder="Title" />

      <div className="border-2 border-dashed rounded-lg p-8 text-center">
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          {...register('file')}
          className="hidden"
          id="file-upload"
        />
        <label htmlFor="file-upload" className="cursor-pointer">
          {preview ? (
            <img src={preview} alt="Preview" className="mx-auto max-h-40 rounded" />
          ) : (
            <p className="text-gray-500">Click to upload image</p>
          )}
        </label>
      </div>
      {errors.file && <p className="text-red-500 text-sm">{errors.file.message}</p>}

      <button type="submit">Upload</button>
    </form>
  );
}
```

---

## Search with Debouncing

```typescript
import { useState, useDeferredValue } from 'react';

function SearchInput() {
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);

  const { data, isLoading } = useQuery({
    queryKey: ['search', deferredQuery],
    queryFn: () => api.search(deferredQuery),
    enabled: deferredQuery.length >= 2,
  });

  return (
    <div className="relative">
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
        className="w-full px-4 py-2 border rounded-lg"
      />

      {isLoading && (
        <div className="absolute right-3 top-3">
          <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
        </div>
      )}

      {data && data.length > 0 && (
        <ul className="absolute top-full left-0 right-0 bg-white border rounded-lg shadow-lg mt-1 max-h-60 overflow-auto">
          {data.map((item) => (
            <li key={item.id} className="px-4 py-2 hover:bg-gray-50 cursor-pointer">
              {item.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

---

## Accessibility in Forms

```typescript
// Accessible form field component
function AccessibleField({ label, error, required, description, id, children }) {
  const errorId = `${id}-error`;
  const descriptionId = `${id}-description`;

  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500 ml-1" aria-label="required">*</span>}
      </label>

      {description && (
        <p id={descriptionId} className="text-xs text-gray-500">
          {description}
        </p>
      )}

      {/* Clone child and add aria attributes */}
      {React.cloneElement(children, {
        id,
        'aria-invalid': error ? 'true' : undefined,
        'aria-describedby': [
          description ? descriptionId : '',
          error ? errorId : '',
        ].filter(Boolean).join(' ') || undefined,
        'aria-required': required ? 'true' : undefined,
      })}

      {error && (
        <p id={errorId} className="text-sm text-red-500" role="alert">
          {error.message}
        </p>
      )}
    </div>
  );
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Form Schema Co-location

```
src/
  features/
    users/
      schemas/
        createUser.schema.ts    # Schema + types
      components/
        CreateUserForm.tsx      # Form using schema
```

### Pattern 2: Confirm Before Submit

```typescript
function DangerousForm() {
  const [showConfirm, setShowConfirm] = useState(false);
  const { handleSubmit } = useForm();

  const onSubmit = (data) => {
    setShowConfirm(true); // Show confirmation dialog
  };

  const onConfirm = () => {
    // Actually submit
    performDangerousAction();
    setShowConfirm(false);
  };

  return (
    <>
      <form onSubmit={handleSubmit(onSubmit)}>
        <button type="submit" className="bg-red-600 text-white">Delete Account</button>
      </form>

      {showConfirm && (
        <Dialog onConfirm={onConfirm} onCancel={() => setShowConfirm(false)}>
          Are you sure? This cannot be undone.
        </Dialog>
      )}
    </>
  );
}
```

---

## Common Pitfalls

### Pitfall 1: Losing Data Between Steps

```typescript
// ❌ Each step resets form data
// ✅ Store data in parent state and pass as defaultValues
```

### Pitfall 2: Not Preventing Double Submission

```typescript
// ❌ User clicks submit twice, two API calls
<button type="submit">Submit</button>

// ✅ Disable during submission
<button type="submit" disabled={isSubmitting}>
  {isSubmitting ? 'Submitting...' : 'Submit'}
</button>
```

### Pitfall 3: Not Handling Network Errors in Forms

```typescript
// ❌ Errors silently swallowed
const onSubmit = async (data) => {
  await api.submit(data);
};

// ✅ Show error to user
const onSubmit = async (data) => {
  try {
    await api.submit(data);
    toast.success('Saved!');
  } catch (error) {
    setError('root', { message: 'Network error. Please try again.' });
  }
};
```

---

## Resources

- **Multi-Step Form Examples:** https://react-hook-form.com/advanced-usage#WizardFormFunnel
- **Form Accessibility:** https://www.w3.org/WAI/tutorials/forms/
- **ARIA Forms Guide:** https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/forms
- **Debounce Patterns:** https://usehooks.com/useDebounce

---

**Next:** [Part 7.1: Axios Fundamentals](../part-07/07-axios-fundamentals.md)
