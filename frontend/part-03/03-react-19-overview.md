# Part 3.9: React 19 Overview

## What You'll Learn

- React 19 new features overview
- Actions for form submission
- useActionState hook
- useFormStatus hook
- Server Components introduction
- Enhanced error handling
- New hooks and APIs
- Migration path from React 18
- Interview questions

---

## Table of Contents

1. [React 19 Features Overview](#react-19-features-overview)
2. [Actions and Form Handling](#actions-and-form-handling)
3. [useActionState Hook](#useactionstate-hook)
4. [useFormStatus Hook](#useformstatus-hook)
5. [Server Components Intro](#server-components-intro)
6. [New Hooks in React 19](#new-hooks-in-react-19)
7. [Enhanced Error Boundaries](#enhanced-error-boundaries)
8. [Breaking Changes](#breaking-changes)
9. [Common Patterns](#common-patterns)
10. [Interview Questions](#interview-questions)
11. [Resources](#resources)

---

## React 19 Features Overview

### What's New?

React 19 brings several improvements focused on:

```javascript
// 1. Simpler Form Handling
// Actions: functions that run on server or client

// 2. Better Form UX
// useFormStatus: pending state without manual loading

// 3. Server Components
// Mix server and client components seamlessly

// 4. Enhanced Hooks
// More powerful and fewer edge cases

// 5. Improved Error Handling
// Better error boundaries and fallbacks

// 6. Automatic Batching (improved)
// More batching scenarios handled automatically
```

### Key Themes

```javascript
// Simplification
// - Reduce boilerplate
// - Cleaner APIs
// - Less manual state management

// Performance
// - Server Components for zero JS overhead
// - Automatic code splitting
// - Streaming SSR

// Developer Experience
// - Better error messages
// - Built-in form handling
// - Clearer data flow
```

---

## Actions and Form Handling

### What are Actions?

Actions are functions that handle form submissions and other async operations.

```jsx
// Traditional form handling
function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      
      if (!response.ok) throw new Error('Login failed');
      const data = await response.json();
      // Handle success
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  // Lots of boilerplate!
}

// React 19 with Actions
function LoginForm() {
  async function login(formData) {
    const email = formData.get('email');
    const password = formData.get('password');
    
    const response = await fetch('/api/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    
    if (!response.ok) throw new Error('Login failed');
    const data = await response.json();
    // Handle success
  }
  
  return (
    <form action={login}>
      <input name="email" type="email" required />
      <input name="password" type="password" required />
      <button type="submit">Login</button>
    </form>
  );
}

// Much cleaner!
```

### Action Function Signature

```javascript
// Actions receive FormData object
async function submitForm(formData) {
  // formData.get('fieldName')
  // formData.getAll('fieldName') - for multiple values
  
  // Do async work
  // Throw errors if something fails
  // Return data if needed
}

// Used with form action prop
<form action={submitForm}>
  <input name="username" />
  <button type="submit">Submit</button>
</form>
```

---

## useActionState Hook

### What is useActionState?

useActionState manages the state of an action (pending, error, data).

```jsx
import { useActionState } from 'react';

function EditUserForm({ user }) {
  async function updateUser(prevState, formData) {
    const name = formData.get('name');
    const email = formData.get('email');
    
    try {
      const response = await fetch(`/api/users/${user.id}`, {
        method: 'PUT',
        body: JSON.stringify({ name, email })
      });
      
      if (!response.ok) throw new Error('Update failed');
      const updated = await response.json();
      
      return { success: true, data: updated };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }
  
  const [state, formAction, isPending] = useActionState(updateUser, null);
  
  return (
    <form action={formAction}>
      <input name="name" defaultValue={user.name} />
      <input name="email" defaultValue={user.email} />
      
      {state?.error && <p className="error">{state.error}</p>}
      {state?.success && <p className="success">Saved!</p>}
      
      <button disabled={isPending}>
        {isPending ? 'Saving...' : 'Save'}
      </button>
    </form>
  );
}

// useActionState returns:
// 1. state: previous return value from action
// 2. formAction: function to pass to form
// 3. isPending: boolean, true while action runs
```

### useActionState vs useState

```jsx
// Old way with useState
function Form() {
  const [formData, setFormData] = useState({ name: '', email: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/users', {
        method: 'POST',
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) throw new Error('Failed');
      // Handle success
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input 
        name="name"
        value={formData.name}
        onChange={(e) => setFormData({...formData, name: e.target.value})}
      />
      {error && <p>{error}</p>}
      <button disabled={loading}>{loading ? 'Loading...' : 'Submit'}</button>
    </form>
  );
}

// New way with useActionState
function Form() {
  async function submit(formData) {
    const response = await fetch('/api/users', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) throw new Error('Failed');
    return { success: true };
  }
  
  const [state, formAction, isPending] = useActionState(submit, null);
  
  return (
    <form action={formAction}>
      <input name="name" />
      {state?.error && <p>{state.error}</p>}
      <button disabled={isPending}>{isPending ? 'Loading...' : 'Submit'}</button>
    </form>
  );
}

// Cleaner with less boilerplate!
```

---

## useFormStatus Hook

### What is useFormStatus?

useFormStatus gives you the pending state of the nearest parent form.

```jsx
import { useFormStatus } from 'react-dom';

function SubmitButton() {
  const { pending } = useFormStatus();
  
  return (
    <button type="submit" disabled={pending}>
      {pending ? 'Submitting...' : 'Submit'}
    </button>
  );
}

function Form() {
  async function handleSubmit(formData) {
    // Process form
  }
  
  return (
    <form action={handleSubmit}>
      <input name="email" />
      <SubmitButton />  {/* Can access form's pending state! */}
    </form>
  );
}

// useFormStatus returns:
// { pending: boolean, data: FormData | null, method: 'GET' | 'POST' }
```

### Benefits

```jsx
// No need to pass callbacks through multiple levels!

// Old way (prop drilling):
function Form() {
  const [loading, setLoading] = useState(false);
  
  return (
    <form>
      <input name="email" />
      <SubmitButton loading={loading} />  {/* Pass through props */}
    </form>
  );
}

function SubmitButton({ loading }) {
  return <button disabled={loading}>Submit</button>;
}

// New way (useFormStatus):
function Form() {
  return (
    <form action={handleSubmit}>
      <input name="email" />
      <SubmitButton />  {/* Access form status directly */}
    </form>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();
  return <button disabled={pending}>Submit</button>;
}

// Much cleaner!
```

---

## Server Components Intro

### What are Server Components?

Server Components run only on the server, sending HTML to the client.

```jsx
// Server Component (runs on server)
// async/await, direct database access, secrets

async function UserProfile({ userId }) {
  // This runs on SERVER only
  const user = await db.query(`SELECT * FROM users WHERE id = ?`, [userId]);
  
  // No JavaScript sent to browser!
  // Zero client-side overhead
  
  return (
    <div>
      <h1>{user.name}</h1>
      <p>{user.email}</p>
      {/* Can include Client Components here */}
      <InteractiveButton userId={userId} />
    </div>
  );
}

// Client Component (runs in browser)
'use client';  // Mark as client component

function InteractiveButton({ userId }) {
  const [clicked, setClicked] = useState(false);
  
  return (
    <button onClick={() => setClicked(!clicked)}>
      {clicked ? 'Clicked!' : 'Click me'}
    </button>
  );
}
```

### Server vs Client Components

```javascript
// Server Components
// ✅ Direct database access
// ✅ Keep secrets on server
// ✅ Use large dependencies
// ✅ Zero client JavaScript
// ❌ Can't use hooks (except new ones)
// ❌ No state

// Client Components
// ✅ Interactivity (onClick, onChange, etc.)
// ✅ useState, useEffect, hooks
// ✅ Browser APIs
// ❌ Larger bundle size
// ❌ Slower than Server Components

// Mix both!
// Server Components for data fetching and logic
// Client Components for interactivity
```

---

## New Hooks in React 19

### use() Hook

The `use` hook reads context or promises.

```jsx
// Reading context
const ThemeContext = createContext('light');

function Component() {
  const theme = use(ThemeContext);
  return <div>{theme}</div>;
}

// Reading promises
async function getUser(userId) {
  const response = await fetch(`/api/users/${userId}`);
  return response.json();
}

function UserComponent({ userId }) {
  // Can pass promise directly!
  const user = use(getUser(userId));
  
  return <div>{user.name}</div>;
}

// Benefits
// - Cleaner than await in effect
// - Handles Suspense
// - Works in Server Components
```

### useCallback Improvements

```jsx
// React 19: useCallback with minimal dependencies

function Component() {
  const [count, setCount] = useState(0);
  
  // Can access count without listing in dependencies!
  const increment = useCallback(() => {
    setCount(c => c + 1);
  }, []);  // Empty deps!
  
  // React 19 compiler optimizes this automatically
}
```

---

## Enhanced Error Boundaries

### Better Error Handling

```jsx
// Error boundaries improved in React 19

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div>
          <h1>Something went wrong</h1>
          <p>{this.state.error?.message}</p>
          {/* Can retry */}
          <button onClick={() => this.setState({ hasError: false })}>
            Try again
          </button>
        </div>
      );
    }
    
    return this.props.children;
  }
}

// Usage
function App() {
  return (
    <ErrorBoundary>
      <MainApp />
    </ErrorBoundary>
  );
}
```

---

## Breaking Changes

### Things that Changed from React 18

```javascript
// 1. Stricter effects
// Effects run twice in dev to find bugs

// 2. Ref cleanup
// Ref callbacks can now return cleanup function

// 3. Removed some deprecated APIs
// Some old APIs removed

// 4. Context changes
// Context Provider value behavior improved

// 5. Component naming
// Anonymous components work better with DevTools
```

### Migration from React 18

```jsx
// Old: useState with form
const [formData, setFormData] = useState({});

// New: useActionState with form action
const [state, formAction] = useActionState(submitForm, null);

// Old: manual loading state
const [loading, setLoading] = useState(false);

// New: useFormStatus
const { pending } = useFormStatus();

// Old: pass callbacks through props
<SubmitButton onClick={handleClick} />

// New: useFormStatus in component
const { pending } = useFormStatus();
```

---

## Common Patterns

### Pattern 1: Form with Validation

```jsx
function SignupForm() {
  async function signup(prevState, formData) {
    const name = formData.get('name');
    const email = formData.get('email');
    
    // Validate
    if (!name || !email) {
      return { error: 'All fields required' };
    }
    
    if (!email.includes('@')) {
      return { error: 'Invalid email' };
    }
    
    // Submit
    try {
      const response = await fetch('/api/signup', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const error = await response.json();
        return { error: error.message };
      }
      
      return { success: true, message: 'Signup successful!' };
    } catch (err) {
      return { error: err.message };
    }
  }
  
  const [state, formAction, isPending] = useActionState(signup, null);
  
  return (
    <form action={formAction}>
      <input name="name" placeholder="Full name" required />
      <input name="email" type="email" placeholder="Email" required />
      
      {state?.error && <p className="error">{state.error}</p>}
      {state?.success && <p className="success">{state.message}</p>}
      
      <button disabled={isPending}>
        {isPending ? 'Signing up...' : 'Sign up'}
      </button>
    </form>
  );
}
```

### Pattern 2: Server Component with Interactive Parts

```jsx
// app/page.jsx (Server Component by default)
import { UserProfile } from './components/UserProfile';
import { LikeButton } from './components/LikeButton';

export default async function Page({ params }) {
  const user = await db.query(`SELECT * FROM users WHERE id = ?`, [params.id]);
  
  return (
    <div>
      <UserProfile user={user} />
      <LikeButton userId={user.id} />
    </div>
  );
}

// app/components/UserProfile.jsx (Server Component)
export function UserProfile({ user }) {
  return (
    <div>
      <h1>{user.name}</h1>
      <p>{user.bio}</p>
    </div>
  );
}

// app/components/LikeButton.jsx (Client Component)
'use client';

import { useState } from 'react';

export function LikeButton({ userId }) {
  const [liked, setLiked] = useState(false);
  
  return (
    <button onClick={() => setLiked(!liked)}>
      {liked ? '❤️ Unlike' : '🤍 Like'}
    </button>
  );
}
```

---

## Interview Questions

### Q1: What problem do Actions solve?

```
Answer:
Actions simplify form submission and async operations.

Before: Manual form handling, loading states, error handling
After: Declarative actions, automatic pending state, cleaner code

Example:
<form action={submitAction}>
  <input name="email" />
  <button type="submit">Submit</button>
</form>

useFormStatus gives pending state without prop drilling.
```

### Q2: What are Server Components?

```
Answer:
Components that run on server only, not sent to client.

Benefits:
- No JavaScript sent to browser
- Direct database access
- Secrets stay on server
- Smaller client bundle

Limitations:
- Can't use interactivity hooks
- No useState/useEffect
- Must use "use client" for interactive parts

Mix Server and Client Components.
```

### Q3: When should you use React 19 features vs React 18?

```
Answer:
Use React 19 when:
- Starting new project
- Need simpler form handling
- Want Server Components
- Can use Next.js or similar

Use React 18 when:
- Maintaining existing project
- Can't upgrade dependencies
- Need wide browser support
- Not using full-stack framework

Actions and useFormStatus are purely optional improvements.
```

---

## Resources

- **React 19 Release:** https://react.dev/blog/2024/12/05/react-19
- **Actions:** https://react.dev/reference/react/use-server
- **useActionState:** https://react.dev/reference/react/useActionState
- **useFormStatus:** https://react.dev/reference/react-dom/useFormStatus
- **Server Components:** https://react.dev/reference/rsc/server-components

---

**Next:** [Part 3.10: React Compiler](./03-react-compiler.md) - Automatic optimization of React code
