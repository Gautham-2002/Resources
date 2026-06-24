# Part 4.2: Zustand Fundamentals

## What You'll Learn

- What Zustand is and why use it
- Creating stores with Zustand
- Subscribing to stores
- Actions and state mutations
- Devtools integration
- Middleware and advanced features
- Performance optimization
- Comparing with Redux and Context
- Interview questions

---

## Table of Contents

1. [Zustand Overview](#zustand-overview)
2. [Why Zustand](#why-zustand)
3. [Creating Stores](#creating-stores)
4. [Accessing State](#accessing-state)
5. [Actions and Mutations](#actions-and-mutations)
6. [Immer Middleware](#immer-middleware)
7. [Devtools Integration](#devtools-integration)
8. [Selectors and Performance](#selectors-and-performance)
9. [Middleware](#middleware)
10. [Common Patterns](#common-patterns)
11. [Interview Questions](#interview-questions)
12. [Resources](#resources)

---

## Zustand Overview

### What is Zustand?

Zustand is a **small, fast, modern state management library** for React.

```javascript
// Key characteristics:
// - Tiny (2KB minified)
// - Simple API (not boilerplate-heavy like Redux)
// - No providers needed (optional)
// - Handles updates efficiently
// - TypeScript support
// - Devtools support
```

### Why Not Context?

```javascript
// Context issues:
// - All consumers re-render when context changes
// - Hard to optimize (even with splits)
// - No built-in devtools
// - No middleware system

// Zustand solves all of this!
// - Selective subscriptions (only re-render if selected state changes)
// - Built-in optimizations
// - Devtools support
// - Middleware system
// - Optional provider pattern
```

### Why Not Redux?

```javascript
// Redux issues:
// - Lots of boilerplate (actions, reducers, dispatch)
// - Verbose setup
// - Steep learning curve
// - Large bundle size

// Zustand advantages:
// - Minimal boilerplate
// - Simple API
// - Smaller bundle
// - Still powerful for complex state
```

---

## Why Zustand

### Comparison

```javascript
// Same feature, different libraries:

// Redux (verbose)
const INCREMENT = 'INCREMENT';

function counterReducer(state = 0, action) {
  if (action.type === INCREMENT) {
    return state + 1;
  }
  return state;
}

const store = createStore(counterReducer);
<Provider store={store}>
  <App />
</Provider>

function Counter() {
  const count = useSelector(state => state);
  const dispatch = useDispatch();
  return <button onClick={() => dispatch({ type: INCREMENT })}>{count}</button>;
}

// Context (manual optimization)
const CountContext = createContext();

function CountProvider({ children }) {
  const [count, setCount] = useState(0);
  const value = useMemo(() => ({ count, setCount }), [count]);
  return <CountContext.Provider value={value}>{children}</CountContext.Provider>;
}

function Counter() {
  const { count, setCount } = useContext(CountContext);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}

// Zustand (simplest!)
const useCounter = create((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 }))
}));

function Counter() {
  const { count, increment } = useCounter();
  return <button onClick={increment}>{count}</button>;
}
```

### When to Use Zustand

```javascript
// ✅ Use Zustand for:
// - Complex state (multiple features)
// - Shared state across many components
// - Frequent updates
// - Need for devtools debugging
// - Want simplicity without Redux complexity

// ✅ Use Context for:
// - Simple app-level state (theme, auth)
// - Don't need optimization
// - Want built-in React solution

// ✅ Use TanStack Query for:
// - Server state (API data)
// - Caching and synchronization
// - Server data management
```

---

## Creating Stores

### Basic Store

```javascript
import { create } from 'zustand';

// Create a store
const useCounterStore = create((set) => ({
  // State
  count: 0,
  
  // Actions (functions that update state)
  increment: () => set((state) => ({ count: state.count + 1 })),
  decrement: () => set((state) => ({ count: state.count - 1 })),
  reset: () => set({ count: 0 })
}));

// Using the store
function Counter() {
  const count = useCounterStore((state) => state.count);
  const increment = useCounterStore((state) => state.increment);
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={increment}>+</button>
    </div>
  );
}
```

### Store Structure

```javascript
// Every store follows this pattern:
const useStore = create((set, get) => ({
  // 1. State properties
  count: 0,
  name: 'John',
  items: [],
  
  // 2. Actions (mutation functions)
  increment: () => set((state) => ({ count: state.count + 1 })),
  setName: (name) => set({ name }),
  addItem: (item) => set((state) => ({
    items: [...state.items, item]
  })),
  
  // 3. Computed values (optional)
  get doubledCount() {
    return this.count * 2;
  },
  
  // 4. Complex actions (optional)
  reset: () => set({ count: 0, name: 'John', items: [] })
}));

// `set`: updates state
// `get`: accesses current state in actions
```

### Multiple Stores

```javascript
// Create separate stores for different concerns
const useUserStore = create((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  logout: () => set({ user: null })
}));

const useThemeStore = create((set) => ({
  theme: 'light',
  toggleTheme: () => set((state) => ({
    theme: state.theme === 'light' ? 'dark' : 'light'
  }))
}));

const useNotificationStore = create((set) => ({
  notifications: [],
  addNotification: (message) => set((state) => ({
    notifications: [...state.notifications, { id: Date.now(), message }]
  })),
  removeNotification: (id) => set((state) => ({
    notifications: state.notifications.filter(n => n.id !== id)
  }))
}));

// Use in components
function App() {
  const user = useUserStore((state) => state.user);
  const theme = useThemeStore((state) => state.theme);
  const notifications = useNotificationStore((state) => state.notifications);
  
  return (
    <div style={{ background: theme === 'light' ? '#fff' : '#000' }}>
      {user && <p>Welcome, {user.name}</p>}
      {notifications.map(n => <p key={n.id}>{n.message}</p>)}
    </div>
  );
}
```

---

## Accessing State

### Using the Hook

```javascript
// Full store (all state and actions)
function Component() {
  const store = useCounterStore();
  
  return (
    <div>
      <p>{store.count}</p>
      <button onClick={store.increment}>+</button>
    </div>
  );
}

// Destructure what you need
function Component() {
  const { count, increment } = useCounterStore();
  
  return (
    <div>
      <p>{count}</p>
      <button onClick={increment}>+</button>
    </div>
  );
}

// Subscribe to specific state (recommended for performance)
function Component() {
  const count = useCounterStore((state) => state.count);
  const increment = useCounterStore((state) => state.increment);
  
  return (
    <div>
      <p>{count}</p>
      <button onClick={increment}>+</button>
    </div>
  );
}
```

### Direct Access (Outside Components)

```javascript
// Access store outside React components
function logger() {
  // Get current state
  const state = useCounterStore.getState();
  console.log('Current count:', state.count);
  
  // Call actions
  useCounterStore.getState().increment();
}

// Subscribe to changes
useCounterStore.subscribe(
  (state) => state.count,
  (count) => console.log('Count changed:', count)
);

// Useful for:
// - Server-side rendering
// - Testing
// - Logging
// - Integration with non-React code
```

---

## Actions and Mutations

### Simple Actions

```javascript
const useStore = create((set) => ({
  count: 0,
  text: '',
  
  // Simple value update
  setText: (text) => set({ text }),
  
  // Update based on current state
  increment: () => set((state) => ({ count: state.count + 1 })),
  
  // Multiple updates in one action
  reset: () => set({ count: 0, text: '' })
}));
```

### Complex Actions with `get`

```javascript
const useStore = create((set, get) => ({
  count: 0,
  multiplier: 2,
  
  // Use `get` to access current state
  incrementByMultiplier: () => {
    const state = get();
    set({ count: state.count + state.multiplier });
  },
  
  // Chaining operations
  complexOperation: () => {
    const state = get();
    
    if (state.count > 10) {
      set({ count: 0 });
    } else {
      set({ count: state.count + 1 });
    }
  }
}));
```

### Async Actions

```javascript
const useUserStore = create((set) => ({
  user: null,
  loading: false,
  error: null,
  
  // Async action
  fetchUser: async (userId) => {
    set({ loading: true, error: null });
    
    try {
      const response = await fetch(`/api/users/${userId}`);
      const user = await response.json();
      set({ user, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  }
}));

// Usage
function UserProfile({ userId }) {
  const user = useUserStore((state) => state.user);
  const loading = useUserStore((state) => state.loading);
  const error = useUserStore((state) => state.error);
  const fetchUser = useUserStore((state) => state.fetchUser);
  
  useEffect(() => {
    fetchUser(userId);
  }, [userId, fetchUser]);
  
  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error}</p>;
  return <p>{user?.name}</p>;
}
```

---

## Immer Middleware

### Why Immer?

Zustand requires immutable updates by default:

```javascript
// Without Immer: Must spread/copy
const useStore = create((set) => ({
  user: { name: 'John', age: 30 },
  
  updateName: (name) => set((state) => ({
    user: { ...state.user, name }
  }))
}));

// With Immer: Can mutate directly!
import { immer } from 'zustand/middleware/immer';

const useStore = create(
  immer((set) => ({
    user: { name: 'John', age: 30 },
    
    updateName: (name) => set((state) => {
      state.user.name = name;  // Direct mutation!
    })
  }))
);
```

### Using Immer

```javascript
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

const useTodoStore = create(
  immer((set) => ({
    todos: [],
    
    // Add todo
    addTodo: (text) => set((state) => {
      state.todos.push({ id: Date.now(), text, done: false });
    }),
    
    // Toggle todo
    toggleTodo: (id) => set((state) => {
      const todo = state.todos.find(t => t.id === id);
      if (todo) {
        todo.done = !todo.done;
      }
    }),
    
    // Remove todo
    removeTodo: (id) => set((state) => {
      state.todos = state.todos.filter(t => t.id !== id);
    })
  }))
);

// Much cleaner! No spreading required
```

---

## Devtools Integration

### Setup Devtools Middleware

```javascript
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

const useCounterStore = create(
  devtools((set) => ({
    count: 0,
    increment: () => set((state) => ({ count: state.count + 1 }))
  }), { name: 'Counter Store' })
);

// Install browser extension: Redux DevTools
// Then inspect store in Redux DevTools tab
```

### Combining Middlewares

```javascript
import { create } from 'zustand';
import { devtools, immer } from 'zustand/middleware';

const useStore = create(
  devtools(
    immer((set) => ({
      todos: [],
      
      addTodo: (text) => set((state) => {
        state.todos.push({ id: Date.now(), text });
      })
    })),
    { name: 'Todo Store' }
  )
);

// Order matters!
// devtools on outside, immer on inside
```

### What You Get in Devtools

```
- All state changes logged
- Time travel debugging (jump to any state)
- Action history
- Dispatch actions manually
- Export/import state
- Performance metrics

Super helpful for debugging!
```

---

## Selectors and Performance

### Selector Performance

```javascript
// Every component re-render means you call the hook
// Zustand is smart about not re-rendering unnecessarily

function Component() {
  // Only re-renders when count changes
  const count = useCounterStore((state) => state.count);
  
  // Component doesn't re-render when increment changes
  const increment = useCounterStore((state) => state.increment);
  
  return (
    <div>
      <p>{count}</p>
      <button onClick={increment}>+</button>
    </div>
  );
}
```

### Comparing Selectors

```javascript
// ❌ WRONG: Selector returns new object each time
const Component = () => {
  const user = useUserStore((state) => ({
    name: state.name,
    email: state.email
  }));  // New object every time!
  
  return <p>{user.name}</p>;
};

// ✅ CORRECT: Selector returns single value
const Component = () => {
  const name = useUserStore((state) => state.name);
  const email = useUserStore((state) => state.email);
  
  return <p>{name}</p>;
};

// Or use shallow for object comparison:
import { shallow } from 'zustand/react/shallow';

const Component = () => {
  const { name, email } = useUserStore(
    (state) => ({ name: state.name, email: state.email }),
    shallow  // Compares keys, not reference
  );
  
  return <p>{name}</p>;
};
```

---

## Middleware

### Custom Middleware

```javascript
import { create } from 'zustand';

const logger = (f) => (set, get, api) =>
  f(
    (args) => {
      console.log('Setting', args);
      set(args);
      console.log('New state', get());
    },
    get,
    api
  );

const useStore = create(
  logger((set) => ({
    count: 0,
    increment: () => set((state) => ({ count: state.count + 1 }))
  }))
);

// Logs every state change
```

### Persist Middleware

```javascript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      login: (user) => set({ user }),
      logout: () => set({ user: null })
    }),
    {
      name: 'auth-storage',  // Key in localStorage
      storage: localStorage  // Can use sessionStorage, etc.
    }
  )
);

// State persisted to localStorage automatically
// Rehydrated on app load
```

---

## Common Patterns

### Pattern 1: Feature Store

```javascript
const useCartStore = create((set, get) => ({
  // State
  items: [],
  total: 0,
  
  // Actions
  addItem: (item) => set((state) => ({
    items: [...state.items, item],
    total: state.total + item.price
  })),
  
  removeItem: (id) => {
    const item = get().items.find(i => i.id === id);
    set((state) => ({
      items: state.items.filter(i => i.id !== id),
      total: state.total - (item?.price || 0)
    }));
  },
  
  clear: () => set({ items: [], total: 0 })
}));
```

### Pattern 2: Combined Stores

```javascript
// Combine multiple stores in hook
function useAppState() {
  const user = useUserStore();
  const cart = useCartStore();
  const theme = useThemeStore();
  
  return { user, cart, theme };
}

// Use combined hook
function App() {
  const { user, cart, theme } = useAppState();
  
  return (
    <div style={{ background: theme.isDark ? '#000' : '#fff' }}>
      {user.isLoggedIn && (
        <p>Welcome, {user.name}</p>
      )}
      <p>Cart items: {cart.items.length}</p>
    </div>
  );
}
```

---

## Interview Questions

### Q1: Why choose Zustand over Redux?

```
Answer:
Zustand advantages:
- Much simpler API (no actions, reducers, dispatch)
- Smaller bundle size
- Less boilerplate
- Easier to learn
- Still powerful for complex state

Redux advantages:
- Larger ecosystem
- More tools and integrations
- Better for teams familiar with Redux
- More formal patterns

For new projects: Zustand
For existing Redux projects: Stay with Redux
```

### Q2: How does Zustand prevent unnecessary re-renders?

```
Answer:
Zustand uses selectors.

When you do:
const count = useCounterStore((state) => state.count);

Zustand:
1. Extracts just the `count` value
2. Subscribes only to changes to `count`
3. Component only re-renders when `count` changes
4. Other state changes don't affect this component

Compare to Context:
- Context wraps entire store
- All consumers re-render on any change
- Must manually split context to optimize
```

### Q3: What's the difference between `set` and `get`?

```
Answer:
`set`: Updates state
- Use to modify state
- Triggers re-renders
- Synchronous

`get`: Reads current state
- Use to access current state in actions
- Doesn't trigger re-renders
- Useful for dependent updates

Example:
const store = create((set, get) => ({
  count: 0,
  text: '',
  
  updateBoth: () => {
    const currentCount = get().count;  // Read current
    set({ count: currentCount + 1, text: 'updated' });  // Update
  }
}));
```

---

## Resources

- **Zustand Documentation:** https://github.com/pmndrs/zustand
- **Zustand API:** https://github.com/pmndrs/zustand#basic-example
- **Middleware:** https://github.com/pmndrs/zustand#middleware
- **Redux DevTools Integration:** https://github.com/pmndrs/zustand#middleware
- **Comparison with Redux:** https://github.com/pmndrs/zustand#motivation

---

**Next:** [Part 4.3: Zustand Advanced Patterns](./04-zustand-advanced.md) - Advanced patterns and optimizations
