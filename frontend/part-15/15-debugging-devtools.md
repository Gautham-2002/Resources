# Part 15.1: Debugging and DevTools

## What You'll Learn

- React DevTools browser extension setup and usage
- Component inspector for inspecting tree
- Debugging state, props, and hooks
- Performance profiler for identifying bottlenecks
- Hook debugger and effect tracking
- Network debugging and API calls
- Error boundaries for error handling
- Console debugging best practices
- Production debugging strategies
- Interview questions

---

## Table of Contents

1. [React DevTools Setup](#react-devtools-setup)
2. [Component Inspector](#component-inspector)
3. [State & Props Debugging](#state--props-debugging)
4. [Performance Profiler](#performance-profiler)
5. [Hook Debugger](#hook-debugger)
6. [Network Debugging](#network-debugging)
7. [Error Boundaries](#error-boundaries)
8. [Console Debugging](#console-debugging)
9. [Production Debugging](#production-debugging)
10. [Common Patterns](#common-patterns)
11. [Interview Questions](#interview-questions)
12. [Resources](#resources)

---

## React DevTools Setup

### Installation

```javascript
// React DevTools is a browser extension
// Available for Chrome, Firefox, Edge, Safari

// 1. Install from browser store
// Chrome: React Developer Tools extension
// Firefox: React Developer Tools add-on
// Search: "React Developer Tools"

// 2. Verify installation
// Open DevTools (F12 or Cmd+Option+I)
// Look for "Components" and "Profiler" tabs
// Only appears on sites using React 16.8+

// 3. Check functionality
function App() {
  return <div>If DevTools is installed, Components tab appears</div>;
}

// When app loads, you should see:
// - Components tab (shows component tree)
// - Profiler tab (shows performance data)
```

### DevTools Interface Overview

```javascript
// React DevTools adds two main tabs to browser DevTools:

// 1. Components Tab
// - Shows React component tree
// - Inspect props and state
// - Edit props in real-time (for testing)
// - View hooks and their values
// - Track component renders
// - See component source location

// 2. Profiler Tab
// - Record component renders
// - See how long each render takes
// - Identify performance bottlenecks
// - Track what changed state/props
// - View render count per interaction
// - Analyze render waterfall

// Settings (gear icon):
// - Highlight updates when components render
// - Show which props changed
// - Customize highlight colors
```

### DevTools Settings

```javascript
// Important settings to enable:

// 1. Highlight updates
// Components flash when they re-render
// Shows you unnecessary re-renders

// 2. Show what caused a render
// Highlights which state/prop changed
// Very helpful for debugging

// 3. Log owner and props on click
// Logs component info to console
// Good for nested component debugging

// Enable these in DevTools settings menu
```

---

## Component Inspector

### Inspecting Component Tree

```jsx
function App() {
  const [count, setCount] = useState(0);
  
  return (
    <div className="app">
      <Header title="My App" version="1.0" />
      <Counter count={count} onIncrement={() => setCount(count + 1)} />
      <Footer year={2024} />
    </div>
  );
}

function Header({ title, version }) {
  return <h1>{title} v{version}</h1>;
}

// In Components tab, you see tree:
// <App>
//   <Header title="My App" version="1.0" />
//   <Counter count={0} onIncrement={fn} />
//   <Footer year={2024} />

// Click on any component to inspect:
// - All props
// - State values
// - Connected hooks
// - Source file location
// - Render count
```

### Viewing Props and State

```jsx
function UserCard({ userId, userName, isActive }) {
  const [expanded, setExpanded] = useState(false);
  const [likes, setLikes] = useState(0);
  const [userData, setUserData] = useState(null);
  
  const handleExpand = useCallback(() => {
    setExpanded(!expanded);
  }, [expanded]);
  
  return (
    <div>
      <h2>{userName}</h2>
      <button onClick={handleExpand}>
        {expanded ? 'Collapse' : 'Expand'}
      </button>
      {expanded && <p>Details: {userData}</p>}
    </div>
  );
}

// In DevTools, click UserCard component:
//
// Props:
// - userId: 123
// - userName: "John"
// - isActive: true
//
// State (Hooks):
// - State (expanded): false
// - State (likes): 0
// - State (userData): null
// - Callback (handleExpand): ƒ (dependencies: [expanded])
//
// Each value is clickable:
// - See current value
// - How it's being used
// - Where defined
// - Dependencies (for hooks)
```

### Editing Props in Real-Time

```jsx
function Button({ onClick, disabled, variant, label }) {
  const variants = {
    primary: 'bg-blue-500',
    secondary: 'bg-gray-500',
    danger: 'bg-red-500'
  };
  
  return (
    <button 
      onClick={onClick} 
      disabled={disabled}
      className={variants[variant]}
    >
      {label}
    </button>
  );
}

// In DevTools, click on Button component:
//
// Props panel:
// - onClick: ƒ (click to inspect)
// - disabled: false (EDITABLE!)
// - variant: "primary" (EDITABLE!)
// - label: "Click me" (EDITABLE!)
//
// To edit:
// 1. Click on any prop value
// 2. Edit it (e.g., disabled: true)
// 3. Component updates in real-time
// 4. See how it responds
//
// Great for testing states without reloading!
```

---

## State & Props Debugging

### Tracking State Changes

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  const [history, setHistory] = useState([]);
  
  const increment = () => {
    const newCount = count + 1;
    setCount(newCount);
    setHistory([...history, newCount]);
  };
  
  const decrement = () => {
    const newCount = count - 1;
    setCount(newCount);
    setHistory([...history, newCount]);
  };
  
  return (
    <div>
      <p>Count: {count}</p>
      <p>History: {history.join(', ')}</p>
      <button onClick={increment}>+1</button>
      <button onClick={decrement}>-1</button>
    </div>
  );
}

// To debug state changes:
// 1. Open DevTools Components tab
// 2. Click on Counter component
// 3. Watch the State section
// 4. Click +1 button multiple times
// 5. See:
//    - State (count): 1 → 2 → 3
//    - State (history): [] → [1] → [1,2] → [1,2,3]
// 6. Each change shows immediately
// 7. Can click to see what changed
```

### Debugging Props Flow

```jsx
function Parent() {
  const [name, setName] = useState('');
  const [items, setItems] = useState([]);
  
  return (
    <div>
      <input 
        value={name} 
        onChange={(e) => setName(e.target.value)}
        placeholder="Enter name"
      />
      
      <Child name={name} itemCount={items.length} />
      <List items={items} />
    </div>
  );
}

function Child({ name, itemCount }) {
  return <div>Hello {name}, you have {itemCount} items</div>;
}

function List({ items }) {
  return (
    <ul>
      {items.map((item, i) => <li key={i}>{item}</li>)}
    </ul>
  );
}

// To trace props:
// 1. Type in input field
// 2. DevTools shows Parent re-renders
// 3. Shows name prop changed
// 4. Child re-renders with new name prop
// 5. List re-renders with items prop
// 6. Track entire prop flow
```

---

## Performance Profiler

### Using the Profiler

```jsx
function SlowComponent({ items }) {
  // Simulate slow render
  const processed = items.map(item => {
    let result = item;
    for (let i = 0; i < 1000000; i++) {
      result = result + i;
    }
    return result;
  });
  
  return <div>{processed.length} items processed</div>;
}

function FastComponent() {
  return <div>Fast render</div>;
}

function App() {
  return (
    <div>
      <FastComponent />
      <SlowComponent items={[1, 2, 3]} />
    </div>
  );
}

// To profile:
// 1. Open DevTools Profiler tab
// 2. Click record button (red circle)
// 3. Interact with app (type, click, etc.)
// 4. Click stop button
// 5. View timeline
//
// You see:
// - Each component render as a bar
// - Length = render duration
// - Longer bar = slower render
// - Color: green (fast) → yellow (medium) → red (slow)
```

### Reading Profiler Results

```javascript
// When you record in Profiler, you see flamegraph:

// Timeline shows:
// App: 5ms
//   ├─ FastComponent: 0.1ms (fast!)
//   └─ SlowComponent: 4.9ms (slow!)

// For each render, you can see:
// - Component name
// - Render duration (ms)
// - What changed (state/props/hooks)
// - Whether it was necessary or wasted

// Example real output:
// App: 12ms
//   ├─ Header: 1ms
//   ├─ ProductList: 10ms (BOTTLENECK!)
//   ├─ Sidebar: 0.5ms
//   └─ Footer: 0.5ms

// ProductList is slow
// Click on it to see why
```

### Finding and Fixing Bottlenecks

```jsx
// ❌ SLOW: Entire list re-renders and resorts
function ProductList({ products, sortBy }) {
  // This runs on EVERY render
  const sorted = products
    .sort((a, b) => {
      if (sortBy === 'price') {
        return a.price - b.price;
      }
      return a.name.localeCompare(b.name);
    });
  
  return (
    <ul>
      {sorted.map(p => <li key={p.id}>{p.name}</li>)}
    </ul>
  );
}

// Profiler shows: 50ms render (slow!)

// ✅ FIX: Memoize the sorted result
function ProductList({ products, sortBy }) {
  const sorted = useMemo(() => {
    console.log('Sorting...');  // Only logs when needed
    
    return products.sort((a, b) => {
      if (sortBy === 'price') {
        return a.price - b.price;
      }
      return a.name.localeCompare(b.name);
    });
  }, [products, sortBy]);
  
  return (
    <ul>
      {sorted.map(p => <li key={p.id}>{p.name}</li>)}
    </ul>
  );
}

// Profiler shows: 1ms render (much faster!)
// Sort only happens when products or sortBy changes
```

---

## Hook Debugger

### Debugging useState

```jsx
function FormComponent() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [errors, setErrors] = useState({});
  
  const handleNameChange = (e) => {
    setName(e.target.value);
    // Clear error when typing
    if (errors.name) {
      setErrors({ ...errors, name: null });
    }
  };
  
  // In DevTools Components tab:
  // State
  // - State (name): "" (shows current value)
  // - State (email): ""
  // - State (errors): {}
  //
  // Click on any state to:
  // - See current value
  // - See how it's used
  // - Jump to line where it's updated
  
  return (
    <div>
      <input 
        value={name}
        onChange={handleNameChange}
        placeholder="Name"
      />
      <input 
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
    </div>
  );
}
```

### Debugging useEffect

```jsx
function DataFetcher({ userId, shouldFetch }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    if (!shouldFetch) return;
    
    setLoading(true);
    setError(null);
    
    fetch(`/api/users/${userId}`)
      .then(r => r.json())
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [userId, shouldFetch]);
  
  // In DevTools Components tab:
  // Hooks section shows:
  // - State (data): null
  // - State (loading): false
  // - State (error): null
  // - Effect: dependencies [userId, shouldFetch]
  //
  // Shows when effect ran and what triggered it
  // Helps find:
  // - Missing dependencies (effect runs too often)
  // - Extra dependencies (effect doesn't run when needed)
  // - Stale closures (effect uses old values)
  
  return (
    <div>
      {loading && <p>Loading...</p>}
      {error && <p>Error: {error}</p>}
      {data && <pre>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}
```

### Debugging useContext

```jsx
const UserContext = createContext();
const ThemeContext = createContext();

function App() {
  const [user, setUser] = useState({ name: 'John' });
  const [theme, setTheme] = useState('light');
  
  return (
    <UserContext.Provider value={{ user, setUser }}>
      <ThemeContext.Provider value={{ theme, setTheme }}>
        <MainContent />
      </ThemeContext.Provider>
    </UserContext.Provider>
  );
}

function MainContent() {
  const { user } = useContext(UserContext);
  const { theme } = useContext(ThemeContext);
  
  // In DevTools Components tab:
  // Hooks section shows:
  // - Context (UserContext): { user: {...}, setUser: ƒ }
  // - Context (ThemeContext): { theme: "light", setTheme: ƒ }
  //
  // Can see:
  // - What each context provides
  // - Current values
  // - Which contexts component uses
  // - Track context changes
}
```

---

## Network Debugging

### Debugging API Calls

```jsx
function UserList() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    setLoading(true);
    setError(null);
    
    fetch('/api/users')
      .then(r => r.json())
      .then(data => {
        setUsers(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);
  
  // To debug network call:
  // 1. Open DevTools Network tab
  // 2. Filter by "fetch"
  // 3. Reload page
  // 4. See request to /api/users
  // 5. Click to see details:
  //    - URL: /api/users
  //    - Method: GET
  //    - Status: 200 OK
  //    - Response headers
  //    - Response body
  //    - Timing breakdown
  
  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error}</p>;
  
  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}
```

### Network Throttling for Testing

```javascript
// DevTools can simulate slow networks:

// Steps:
// 1. Open DevTools Network tab
// 2. Look for throttling dropdown (default: "No throttling")
// 3. Select preset:
//    - Slow 3G
//    - Fast 3G
//    - WiFi
//    - Custom

// Usage examples:
// - Test loading states on slow network
// - Test error handling with timeouts
// - Test fallback UI
// - Verify spinners appear
// - Check mobile experience

// Example test:
// 1. Set to "Slow 3G"
// 2. Interact with app
// 3. Watch loading states
// 4. Verify UX works well
// 5. Reset to "No throttling"
```

---

## Error Boundaries

### Creating Error Boundary

```jsx
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null 
    };
  }
  
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  
  componentDidCatch(error, errorInfo) {
    // Log error details
    console.error('Error caught:', error, errorInfo);
    this.setState({ errorInfo });
    
    // Send to error tracking service
    // Sentry.captureException(error);
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', border: '1px solid red' }}>
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          
          {process.env.NODE_ENV === 'development' && (
            <details style={{ whiteSpace: 'pre-wrap' }}>
              {this.state.errorInfo?.componentStack}
            </details>
          )}
          
          <button onClick={() => window.location.reload()}>
            Reload page
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
      <MainContent />
    </ErrorBoundary>
  );
}
```

### Error Boundary Patterns

```jsx
// Wrap sections to prevent full crash
function App() {
  return (
    <div>
      <ErrorBoundary name="Header">
        <Header />
      </ErrorBoundary>
      
      <ErrorBoundary name="Sidebar">
        <Sidebar />
      </ErrorBoundary>
      
      <ErrorBoundary name="MainContent">
        <MainContent />
      </ErrorBoundary>
      
      <ErrorBoundary name="Footer">
        <Footer />
      </ErrorBoundary>
    </div>
  );
}

// If Header crashes:
// - Header shows error UI
// - Sidebar, MainContent, Footer work fine
// - User can still navigate
// - Much better UX than blank screen
```

---

## Console Debugging

### Effective Console Logging

```jsx
function Component() {
  const [count, setCount] = useState(0);
  const [items, setItems] = useState([]);
  
  useEffect(() => {
    console.log('Component mounted');
    
    return () => {
      console.log('Component unmounted');
    };
  }, []);
  
  useEffect(() => {
    console.log('Count changed:', count);
  }, [count]);
  
  useEffect(() => {
    console.log('Items updated:', items);
  }, [items]);
  
  return (
    <div>
      <p>{count}</p>
      <button onClick={() => setCount(count + 1)}>+</button>
    </div>
  );
}

// Console output:
// Component mounted
// Count changed: 0
// Count changed: 1
// Count changed: 2
// Component unmounted (when unmounted)
```

### Console Best Practices

```javascript
// ✅ GOOD: Meaningful logs
console.log('User data fetched:', userData);
console.error('Failed to load users:', error.message);
console.warn('Component deprecated, use NewComponent instead');
console.info('Authentication successful');

// ❌ BAD: Unhelpful logs
console.log('x');
console.log('ok');
console.log('done');

// ✅ GOOD: Structured logs
console.table(users);  // Show as table
console.group('User Info');
console.log('Name:', user.name);
console.log('Email:', user.email);
console.groupEnd();

// ✅ GOOD: Conditional logs (dev only)
if (process.env.NODE_ENV === 'development') {
  console.log('Debug info:', data);
}

// ✅ GOOD: Timing logs
console.time('fetchData');
await fetchData();
console.timeEnd('fetchData');  // Shows: fetchData: 523ms
```

---

## Production Debugging

### Source Maps

```javascript
// Problem: Production code is minified
// const user = { name: 'John' };
// Becomes: const u={n:'J'};

// Solution: Use source maps
// vite.config.js
export default {
  build: {
    sourcemap: true  // Generate source maps
  }
}

// With source maps:
// - Errors show original code (not minified)
// - Stack traces are readable
// - Line numbers point to source
// - Debugging is normal (not crazy)

// Keep source maps private!
// Don't expose them in public folder
```

### Error Tracking Services

```javascript
// Use Sentry for production errors

npm install @sentry/react

// Initialize Sentry
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "https://...@sentry.io/...",
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0
});

// Now all errors automatically sent to Sentry:
function Component() {
  const handleClick = () => {
    try {
      riskyOperation();
    } catch (error) {
      // Sentry captures:
      // - Error message
      // - Stack trace
      // - Browser info
      // - User info (if set)
      // - Performance data
      // - User session replay (video-like)
      
      Sentry.captureException(error);
    }
  };
}

// Dashboard shows:
// - All errors with trends
// - Which users affected
// - Release information
// - Session replay videos
// - Performance impact
```

---

## Common Patterns

### Pattern 1: Debug Flag

```jsx
const DEBUG = process.env.NODE_ENV === 'development';

function Component() {
  useEffect(() => {
    DEBUG && console.log('Component mounted');
    
    return () => {
      DEBUG && console.log('Component unmounted');
    };
  }, []);
  
  const handleClick = () => {
    DEBUG && console.log('Clicked!');
  };
}

// Logs only in development
// Production has no console spam
```

### Pattern 2: Custom Hook for Debugging

```jsx
function useDebug(name, value) {
  useEffect(() => {
    console.log(`${name}:`, value);
  }, [value, name]);
}

function Component({ userId, userName }) {
  useDebug('userId', userId);
  useDebug('userName', userName);
  
  // Logs whenever either changes
  // Great for tracking prop changes
}
```

---

## Interview Questions

### Q1: How do you debug React components?

```
Answer:
1. React DevTools
   - Components tab: inspect tree, props, state, hooks
   - Profiler tab: identify performance bottlenecks
   - Edit props in real-time for testing
   - Track render causes

2. Browser DevTools
   - Network tab: debug API calls, see responses
   - Console: log and debug
   - Sources: set breakpoints, step through code

3. Error Boundaries
   - Catch rendering errors
   - Prevent full app crash
   - Show meaningful error UI
   - Log to error tracking

4. Console logs
   - Log state changes
   - Track effect execution
   - Find stale closures
   - Debug async operations
```

### Q2: How do you find performance issues?

```
Answer:
1. React Profiler
   - Record user interactions
   - See render duration
   - Identify slow components
   - Track what caused re-renders

2. DevTools highlighting
   - Show which components re-render
   - Color indicates reason (state/props)
   - Find unnecessary renders

3. Check flamegraph
   - Longer bars = slower renders
   - Find bottlenecks
   - Compare before/after optimization

4. Console.time()
   - Manual timing of functions
   - Measure sorting, filtering
   - Verify optimization worked
```

### Q3: How do you debug useEffect issues?

```
Answer:
React tracks useEffect execution:

1. Check dependency array
   - Missing dependency? Effect runs too often
   - Too many? Effect doesn't run when needed

2. See when effect runs
   - Log at start and end
   - Check DevTools hooks panel
   - Verify dependencies match

3. Track cleanup
   - Log in return function
   - Verify cleanup happens on unmount
   - Check for memory leaks

4. Common issues
   - Missing dependencies (stale closures)
   - Infinite loops
   - Memory leaks from not cleaning up
   - Race conditions in async effects
```

---

## Resources

- **React DevTools:** https://react.dev/learn/react-developer-tools
- **Browser DevTools:** https://developer.chrome.com/docs/devtools/
- **Profiling Performance:** https://react.dev/learn/render-and-commit
- **Error Boundaries:** https://react.dev/reference/react/Component#catching-rendering-errors
- **Sentry Documentation:** https://docs.sentry.io/platforms/javascript/guides/react/
- **Chrome DevTools Guide:** https://developer.chrome.com/docs/devtools/

---

**Next:** [Part 15.2: Error Handling & Error Boundaries](./15-error-handling-boundaries.md) - Creating robust error handling
