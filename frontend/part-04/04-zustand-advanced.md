# Part 4.3: Zustand Advanced Patterns

## What You'll Learn

- Combining multiple stores
- Store composition patterns
- Advanced middleware creation
- Optimistic updates
- Store subscription patterns
- Handling async state properly
- Store normalization
- Testing complex stores
- Interview questions

---

## Table of Contents

1. [Combining Multiple Stores](#combining-multiple-stores)
2. [Store Composition](#store-composition)
3. [Advanced Middleware](#advanced-middleware)
4. [Optimistic Updates](#optimistic-updates)
5. [Subscription Patterns](#subscription-patterns)
6. [Async State Management](#async-state-management)
7. [Store Normalization](#store-normalization)
8. [Testing Advanced Patterns](#testing-advanced-patterns)
9. [Common Patterns](#common-patterns)
10. [Common Pitfalls](#common-pitfalls)
11. [Interview Questions](#interview-questions)
12. [Resources](#resources)

---

## Combining Multiple Stores

### The Problem: Store Interdependencies

```javascript
// Multiple stores that need to interact
const useUserStore = create((set) => ({
  user: null,
  setUser: (user) => set({ user })
}));

const useCartStore = create((set) => ({
  items: [],
  addItem: (item) => set((state) => ({
    items: [...state.items, item]
  }))
}));

// What if adding item to cart needs to check user permissions?
// Or user logout needs to clear cart?
// Hard to coordinate!
```

### Solution 1: Shared Hook

```javascript
// Create a hook that combines stores
function useAppState() {
  const user = useUserStore();
  const cart = useCartStore();
  
  // Add computed values
  const canCheckout = user.user && cart.items.length > 0;
  
  return {
    user,
    cart,
    canCheckout
  };
}

// Usage
function App() {
  const { user, cart, canCheckout } = useAppState();
  
  return (
    <div>
      {user.user && <p>Welcome, {user.user.name}</p>}
      <p>Cart items: {cart.items.length}</p>
      <button disabled={!canCheckout}>Checkout</button>
    </div>
  );
}

// Benefits:
// - Keeps components clean
// - Coordinates multiple stores
// - Single point for computed values
```

### Solution 2: Cross-Store Communication

```javascript
// Subscribe to one store and update another
const useUserStore = create((set) => ({
  user: null,
  setUser: (user) => set({ user })
}));

const useCartStore = create((set) => ({
  items: [],
  addItem: (item) => set((state) => ({
    items: [...state.items, item]
  })),
  clear: () => set({ items: [] })
}));

// When user logs out, clear cart
useUserStore.subscribe(
  (state) => state.user,
  (user) => {
    if (!user) {
      // User logged out, clear cart
      useCartStore.getState().clear();
    }
  }
);

// Or better: use useEffect in component
function App() {
  const user = useUserStore((state) => state.user);
  const clearCart = useCartStore((state) => state.clear);
  
  useEffect(() => {
    if (!user) {
      clearCart();
    }
  }, [user, clearCart]);
}
```

### Solution 3: Combined Store

```javascript
// Create a master store that combines others
const useAppStore = create((set, get) => {
  // Get individual stores
  const userStore = useUserStore.getState();
  const cartStore = useCartStore.getState();
  
  return {
    // Expose both stores
    user: userStore,
    cart: cartStore,
    
    // Add coordinated actions
    checkout: async () => {
      const state = get();
      
      if (!state.user.user) {
        throw new Error('Must be logged in');
      }
      
      if (state.cart.items.length === 0) {
        throw new Error('Cart is empty');
      }
      
      // Process checkout
      const response = await fetch('/api/checkout', {
        method: 'POST',
        body: JSON.stringify({
          userId: state.user.user.id,
          items: state.cart.items
        })
      });
      
      // Clear cart after success
      state.cart.clear();
    }
  };
});

// Usage
function CheckoutButton() {
  const checkout = useAppStore((state) => state.checkout);
  const canCheckout = useAppStore((state) => {
    const hasUser = state.user.user;
    const hasItems = state.cart.items.length > 0;
    return hasUser && hasItems;
  });
  
  return (
    <button onClick={checkout} disabled={!canCheckout}>
      Checkout
    </button>
  );
}
```

---

## Store Composition

### Building Complex Stores

```javascript
const createUserSlice = (set, get) => ({
  user: null,
  
  setUser: (user) => set({ user }),
  
  logout: () => {
    set({ user: null });
    // Trigger side effects
    get().clearUserData();
  },
  
  clearUserData: () => {
    // Clear user-related data
  }
});

const createCartSlice = (set, get) => ({
  items: [],
  
  addItem: (item) => set((state) => ({
    items: [...state.items, item]
  })),
  
  clear: () => set({ items: [] })
});

// Combine slices
const useStore = create((set, get) => ({
  ...createUserSlice(set, get),
  ...createCartSlice(set, get)
}));

// Or with TypeScript for better typing
type UserSlice = ReturnType<typeof createUserSlice>;
type CartSlice = ReturnType<typeof createCartSlice>;

const useStore = create<UserSlice & CartSlice>((set, get) => ({
  ...createUserSlice(set, get),
  ...createCartSlice(set, get)
}));
```

### Slice Pattern with Utilities

```javascript
// Helper to create slices
const createSlice = (name, initialState, actions) => {
  return (set, get) => {
    return Object.fromEntries(
      Object.entries(actions).map(([key, action]) => [
        key,
        (...args) => action(set, get, initialState)(...args)
      ])
    );
  };
};

// Define user slice
const userSlice = createSlice('user', { user: null }, {
  setUser: (set, get) => (user) => {
    set({ user });
    console.log('User changed');
  },
  logout: (set, get) => () => set({ user: null })
});

// Define cart slice
const cartSlice = createSlice('cart', { items: [] }, {
  addItem: (set, get) => (item) => set((state) => ({
    items: [...state.items, item]
  }))
});

// Combine
const useStore = create((set, get) => ({
  ...userSlice(set, get),
  ...cartSlice(set, get)
}));
```

---

## Advanced Middleware

### Creating Custom Middleware

```javascript
// Middleware that logs actions
const logger = (name) => (f) => (set, get, api) =>
  f(
    (args) => {
      console.log(`[${name}] Setting:`, args);
      set(args);
      console.log(`[${name}] New state:`, get());
    },
    get,
    api
  );

const useStore = create(
  logger('MyStore')((set) => ({
    count: 0,
    increment: () => set((state) => ({ count: state.count + 1 }))
  }))
);

// Output:
// [MyStore] Setting: { count: 1 }
// [MyStore] New state: { count: 1 }
```

### Combining Multiple Middlewares

```javascript
import { devtools, persist, immer } from 'zustand/middleware';

const useStore = create(
  devtools(
    persist(
      immer((set) => ({
        todos: [],
        
        addTodo: (text) => set((state) => {
          state.todos.push({ id: Date.now(), text, done: false });
        })
      })),
      { name: 'todo-store' }
    ),
    { name: 'TodoStore' }
  )
);

// Order matters!
// devtools outer → can debug everything
// persist middle → saves state
// immer inner → allows mutations
```

### Custom Middleware for Rate Limiting

```javascript
const rateLimit = (maxCalls, timeWindow) => (f) => (set, get, api) => {
  let callCount = 0;
  
  const resetCounter = () => {
    callCount = 0;
    setTimeout(resetCounter, timeWindow);
  };
  
  resetCounter();
  
  return f(
    (args) => {
      if (callCount >= maxCalls) {
        console.warn('Rate limit exceeded');
        return;
      }
      
      callCount++;
      set(args);
    },
    get,
    api
  );
};

// Only allow 5 updates per second
const useStore = create(
  rateLimit(5, 1000)((set) => ({
    count: 0,
    increment: () => set((state) => ({ count: state.count + 1 }))
  }))
);
```

---

## Optimistic Updates

### Pattern for Optimistic Updates

```javascript
const usePostStore = create((set, get) => ({
  posts: [],
  error: null,
  
  // Optimistic update: update UI immediately, sync with server
  likePost: async (postId) => {
    // Save previous state in case we need to rollback
    const previousPosts = get().posts;
    
    // Update UI immediately (optimistic)
    set((state) => ({
      posts: state.posts.map(post =>
        post.id === postId
          ? { ...post, likes: post.likes + 1, liked: true }
          : post
      ),
      error: null
    }));
    
    try {
      // Send to server
      const response = await fetch(`/api/posts/${postId}/like`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Failed to like post');
      
      // Server confirmed, we're good!
    } catch (error) {
      // Rollback on error
      set({
        posts: previousPosts,
        error: error.message
      });
    }
  }
}));

// Usage
function PostCard({ post }) {
  const likePost = usePostStore((state) => state.likePost);
  const liked = post.liked;
  
  return (
    <div>
      <p>{post.text}</p>
      <button 
        onClick={() => likePost(post.id)}
        style={{ color: liked ? 'red' : 'gray' }}
      >
        Like ({post.likes})
      </button>
    </div>
  );
}
```

### Optimistic Updates with Undo

```javascript
const useFormStore = create((set, get) => ({
  form: { title: '', description: '' },
  history: [],
  
  updateField: (field, value) => {
    const previousForm = get().form;
    
    // Save to history
    set((state) => ({
      history: [...state.history, previousForm],
      form: { ...state.form, [field]: value }
    }));
  },
  
  undo: () => {
    const history = get().history;
    
    if (history.length === 0) return;
    
    const previousForm = history[history.length - 1];
    
    set({
      form: previousForm,
      history: history.slice(0, -1)
    });
  }
}));

// Usage
function Form() {
  const form = useFormStore((state) => state.form);
  const updateField = useFormStore((state) => state.updateField);
  const undo = useFormStore((state) => state.undo);
  
  return (
    <div>
      <input
        value={form.title}
        onChange={(e) => updateField('title', e.target.value)}
        placeholder="Title"
      />
      <button onClick={undo}>Undo</button>
    </div>
  );
}
```

---

## Subscription Patterns

### Store Subscriptions

```javascript
// Subscribe to entire store
const unsubscribe = useStore.subscribe(
  (state) => state,
  (newState) => {
    console.log('Store changed:', newState);
  }
);

// Subscribe to specific value
const unsubscribe = useStore.subscribe(
  (state) => state.count,
  (count) => {
    console.log('Count changed:', count);
  }
);

// Subscribe with selector and equality check
const unsubscribe = useStore.subscribe(
  (state) => state.user.name,
  (name) => {
    console.log('User name changed:', name);
  }
);

// Don't forget to unsubscribe!
useEffect(() => {
  const unsubscribe = useStore.subscribe(
    (state) => state.count,
    (count) => {
      console.log('Count:', count);
    }
  );
  
  return unsubscribe;  // Cleanup
}, []);
```

### Advanced Subscription with Effects

```javascript
const useEffectStore = create((set, get) => ({
  data: null,
  loading: false,
  error: null,
  
  // Setup subscriptions on initialization
  _initialize: () => {
    // When error occurs, log it
    useEffectStore.subscribe(
      (state) => state.error,
      (error) => {
        if (error) {
          console.error('Error occurred:', error);
          // Could send to error tracking service
        }
      }
    );
  }
}));

// Initialize on import
useEffectStore.getState()._initialize();
```

---

## Async State Management

### Proper Async Patterns

```javascript
const useDataStore = create((set) => ({
  data: null,
  loading: false,
  error: null,
  
  // Async action with proper state management
  fetchData: async (url) => {
    set({ loading: true, error: null, data: null });
    
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      set({ data, loading: false, error: null });
      return data;
    } catch (error) {
      set({
        error: error.message,
        loading: false,
        data: null
      });
      
      throw error;  // Re-throw for caller
    }
  }
}));

// Usage with proper error handling
function DataComponent({ url }) {
  const { data, loading, error } = useDataStore((state) => ({
    data: state.data,
    loading: state.loading,
    error: state.error
  }));
  
  const fetch = useDataStore((state) => state.fetchData);
  
  useEffect(() => {
    fetch(url).catch((error) => {
      console.error('Failed to fetch:', error);
    });
  }, [url, fetch]);
  
  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error}</p>;
  return <p>{JSON.stringify(data)}</p>;
}
```

### Handling Race Conditions in Async

```javascript
const useAsyncStore = create((set, get) => ({
  data: null,
  loading: false,
  currentRequestId: null,
  
  fetchData: async (url) => {
    const requestId = Date.now();  // Unique ID for this request
    
    set({
      loading: true,
      currentRequestId: requestId
    });
    
    try {
      const response = await fetch(url);
      const data = await response.json();
      
      // Only update if this is still the latest request
      if (get().currentRequestId === requestId) {
        set({ data, loading: false });
      }
    } catch (error) {
      if (get().currentRequestId === requestId) {
        set({ loading: false, error: error.message });
      }
    }
  }
}));

// If user navigates away or makes new request
// Old responses are ignored
```

---

## Store Normalization

### Normalized State Structure

```javascript
// Denormalized (hard to update)
const useBadStore = create((set) => ({
  posts: [
    {
      id: 1,
      title: 'Post 1',
      author: { id: 1, name: 'John' }
    },
    {
      id: 2,
      title: 'Post 2',
      author: { id: 1, name: 'John' }  // Duplicate data!
    }
  ]
}));

// Normalized (easy to update)
const useNormalizedStore = create((set) => ({
  entities: {
    posts: {
      1: { id: 1, title: 'Post 1', authorId: 1 },
      2: { id: 2, title: 'Post 2', authorId: 1 }
    },
    authors: {
      1: { id: 1, name: 'John' }
    }
  },
  
  // Selectors to get normalized data
  getPost: (id) => {
    const state = useNormalizedStore.getState();
    const post = state.entities.posts[id];
    const author = state.entities.authors[post.authorId];
    
    return { ...post, author };
  },
  
  // Easy to update author
  updateAuthor: (id, updates) => set((state) => ({
    entities: {
      ...state.entities,
      authors: {
        ...state.entities.authors,
        [id]: { ...state.entities.authors[id], ...updates }
      }
    }
  }))
}));

// Benefits:
// - No duplicate data
// - Easy to update (single source of truth)
// - Efficient for large datasets
```

---

## Testing Advanced Patterns

### Testing Stores with Vitest

```javascript
import { describe, it, expect, beforeEach } from 'vitest';
import { useCounterStore } from './store';

describe('Counter Store', () => {
  beforeEach(() => {
    // Reset store before each test
    useCounterStore.setState({ count: 0 });
  });
  
  it('should increment count', () => {
    const { increment } = useCounterStore.getState();
    
    increment();
    
    expect(useCounterStore.getState().count).toBe(1);
  });
  
  it('should handle multiple increments', () => {
    const { increment } = useCounterStore.getState();
    
    increment();
    increment();
    increment();
    
    expect(useCounterStore.getState().count).toBe(3);
  });
  
  it('should notify subscribers', () => {
    const listener = vitest.fn();
    const unsubscribe = useCounterStore.subscribe(
      (state) => state.count,
      listener
    );
    
    useCounterStore.getState().increment();
    
    expect(listener).toHaveBeenCalledWith(1, 0);
    
    unsubscribe();
  });
});
```

### Testing Async Stores

```javascript
describe('Async Store', () => {
  it('should handle successful fetch', async () => {
    // Mock fetch
    global.fetch = vitest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ id: 1, name: 'John' })
      })
    );
    
    const { fetchData } = useAsyncStore.getState();
    await fetchData('/api/user/1');
    
    const state = useAsyncStore.getState();
    expect(state.data).toEqual({ id: 1, name: 'John' });
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });
  
  it('should handle fetch errors', async () => {
    global.fetch = vitest.fn(() =>
      Promise.reject(new Error('Network error'))
    );
    
    const { fetchData } = useAsyncStore.getState();
    
    await expect(fetchData('/api/user/1')).rejects.toThrow();
    
    const state = useAsyncStore.getState();
    expect(state.error).toBe('Network error');
    expect(state.loading).toBe(false);
  });
});
```

---

## Common Patterns

### Pattern 1: Undo/Redo

```javascript
const useUndoStore = create((set, get) => ({
  past: [],
  present: { count: 0 },
  future: [],
  
  setState: (state) => {
    const current = get().present;
    
    set({
      past: [...get().past, current],
      present: state,
      future: []
    });
  },
  
  undo: () => {
    const { past, present, future } = get();
    
    if (past.length === 0) return;
    
    const newPresent = past[past.length - 1];
    
    set({
      past: past.slice(0, -1),
      present: newPresent,
      future: [present, ...future]
    });
  },
  
  redo: () => {
    const { past, present, future } = get();
    
    if (future.length === 0) return;
    
    const newPresent = future[0];
    
    set({
      past: [...past, present],
      present: newPresent,
      future: future.slice(1)
    });
  }
}));
```

### Pattern 2: Namespaced Stores

```javascript
// Create factory for creating stores with same structure
const createStore = (namespace) =>
  create((set) => ({
    namespace,
    data: null,
    loading: false,
    
    fetch: async (url) => {
      set({ loading: true });
      const data = await fetch(url).then(r => r.json());
      set({ data, loading: false });
    }
  }));

// Create multiple stores
const useUserStore = createStore('user');
const usePostStore = createStore('post');
const useCommentStore = createStore('comment');

// Each has same interface but separate state
```

---

## Common Pitfalls

### Pitfall 1: Mutations in Selectors

```javascript
// ❌ WRONG: Creating new object in selector (causes re-renders)
function Component() {
  const combined = useStore((state) => ({
    name: state.user.name,
    email: state.user.email
  }));
  
  return <p>{combined.name}</p>;
}

// ✅ CORRECT: Select primitive value
function Component() {
  const name = useStore((state) => state.user.name);
  
  return <p>{name}</p>;
}

// Or use shallow if you need object
import { shallow } from 'zustand/react/shallow';

function Component() {
  const { name, email } = useStore(
    (state) => ({ name: state.user.name, email: state.user.email }),
    shallow
  );
  
  return <p>{name}</p>;
}
```

### Pitfall 2: Forgetting to Unsubscribe

```javascript
// ❌ WRONG: Memory leak
useEffect(() => {
  useStore.subscribe(
    (state) => state.data,
    (data) => console.log(data)
  );
  // No cleanup!
}, []);

// ✅ CORRECT: Proper cleanup
useEffect(() => {
  const unsubscribe = useStore.subscribe(
    (state) => state.data,
    (data) => console.log(data)
  );
  
  return unsubscribe;
}, []);
```

---

## Interview Questions

### Q1: How do you combine multiple Zustand stores?

```
Answer:
Option 1: Create a combined hook
function useAppState() {
  const user = useUserStore();
  const cart = useCartStore();
  return { user, cart };
}

Option 2: Cross-store subscription
useUserStore.subscribe(
  (state) => state.user,
  (user) => {
    if (!user) useCartStore.getState().clear();
  }
);

Option 3: Create master store
const useAppStore = create((set, get) => ({
  user: useUserStore.getState(),
  cart: useCartStore.getState(),
  checkout: async () => { /* coordinated action */ }
}));

Choose based on complexity and dependencies.
```

### Q2: What's the best way to handle async operations?

```
Answer:
Use proper state management:

const store = create((set) => ({
  data: null,
  loading: false,
  error: null,
  
  fetch: async (url) => {
    set({ loading: true, error: null });
    try {
      const data = await fetch(url).then(r => r.json());
      set({ data, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  }
}));

Key:
- Set loading before fetch
- Clear error on start
- Handle errors properly
- Always set loading to false
```

---

## Resources

- **Zustand Advanced:** https://github.com/pmndrs/zustand
- **Immer Middleware:** https://immerjs.github.io/immer/
- **Store Composition:** https://github.com/pmndrs/zustand#strongly-typed-selectors
- **Testing Stores:** https://vitest.dev/
- **Performance Tips:** https://github.com/pmndrs/zustand#using-zustand-without-react

---

**Next:** [Part 4.4: State Management Comparison](./04-state-management-comparison.md) - When to use Context vs Zustand vs TanStack Query
