# Part 4.4: State Management Comparison

## What You'll Learn

- Comparing Context API, Zustand, Redux, and TanStack Query
- Decision matrix for choosing state management
- When to use each tool
- Real-world examples
- Migrating between solutions
- Anti-patterns to avoid
- Interview questions

---

## Table of Contents

1. [The Four Solutions](#the-four-solutions)
2. [Context API](#context-api)
3. [Zustand](#zustand)
4. [Redux](#redux)
5. [TanStack Query](#tanstack-query)
6. [Decision Matrix](#decision-matrix)
7. [Real-World Examples](#real-world-examples)
8. [Migration Paths](#migration-paths)
9. [Common Pitfalls](#common-pitfalls)
10. [Interview Questions](#interview-questions)
11. [Resources](#resources)

---

## The Four Solutions

### Overview

```javascript
// You have 4 main options for state management:

// 1. Context API (React built-in)
// 2. Zustand (Simple, performant)
// 3. Redux (Complex, comprehensive)
// 4. TanStack Query (Server state)
```

---

## Context API

### Strengths

```javascript
// ✅ STRENGTHS:
// - Built into React (no dependencies)
// - Simple API (createContext, useContext)
// - Good for app-level state
// - Type-safe with TypeScript
// - Perfect for themes, language, user auth

// Examples where Context shines:
// - Theme (light/dark)
// - Language selection
// - User authentication
// - Global settings
// - Modal open/close state
```

### Weaknesses

```javascript
// ❌ WEAKNESSES:
// - All consumers re-render on any change
// - Hard to optimize (requires context splitting)
// - No built-in devtools
// - No middleware system
// - No persistence helpers
// - No normalization helpers

// Examples where Context struggles:
// - Complex state with many features
// - Frequently changing state
// - Need for time-travel debugging
// - Large applications with many stores
```

### When to Use Context

```javascript
// Use Context when:
// 1. State is app-level (not feature-level)
// 2. Changes infrequently
// 3. Small state objects
// 4. Want zero dependencies
// 5. Simple authentication

// Example: Theme context
const ThemeContext = createContext();

function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
```

---

## Zustand

### Strengths

```javascript
// ✅ STRENGTHS:
// - Tiny bundle size (2KB)
// - Simple, intuitive API
// - Excellent performance (selectors)
// - Built-in devtools support
// - Middleware system
// - Immer integration
// - TypeScript friendly
// - No providers needed (optional)

// Examples where Zustand shines:
// - E-commerce cart
// - Complex form state
// - UI state (modals, sidebars)
// - Feature state (todos, posts)
// - Game state
```

### Weaknesses

```javascript
// ❌ WEAKNESSES:
// - External dependency
// - Smaller ecosystem than Redux
// - Not as mature (but stable)
// - Need to handle async yourself
// - Limited normalization helpers

// These are minor compared to benefits
```

### When to Use Zustand

```javascript
// Use Zustand when:
// 1. Need simple state management
// 2. Want good performance
// 3. Don't want Redux complexity
// 4. Have multiple related features
// 5. Want optional devtools

// Example: Shopping cart
const useCartStore = create((set) => ({
  items: [],
  
  addItem: (item) => set((state) => ({
    items: [...state.items, item]
  })),
  
  removeItem: (id) => set((state) => ({
    items: state.items.filter(item => item.id !== id)
  }))
}));
```

---

## Redux

### Strengths

```javascript
// ✅ STRENGTHS:
// - Mature and battle-tested
// - Large ecosystem (Redux Thunk, Saga, RTK)
// - Excellent devtools (time travel!)
// - Normalized state patterns
// - Good for large teams
// - Middleware system
// - Predictable state updates

// Examples where Redux shines:
// - Large enterprise applications
// - Complex state transitions
// - Need comprehensive devtools
// - Multiple developers/teams
// - Extensive async patterns
```

### Weaknesses

```javascript
// ❌ WEAKNESSES:
// - Lots of boilerplate (actions, reducers, dispatch)
// - Steep learning curve
// - Large bundle size
// - Verbose patterns
// - Requires Redux Thunk for async
// - Over-engineered for simple apps

// Examples where Redux is overkill:
// - Small projects
// - Few state features
// - Simple form state
// - Learning React
```

### When to Use Redux

```javascript
// Use Redux when:
// 1. Large, complex application
// 2. Multiple developers/teams
// 3. Need comprehensive devtools
// 4. Have complex async patterns
// 5. Team already knows Redux

// Example: Redux action
const INCREMENT = 'INCREMENT';

function reducer(state = 0, action) {
  if (action.type === INCREMENT) {
    return state + 1;
  }
  return state;
}

// vs Zustand equivalent (much simpler!)
const useCounter = create((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 }))
}));
```

---

## TanStack Query

### Strengths

```javascript
// ✅ STRENGTHS:
// - Purpose-built for server state
// - Automatic caching and synchronization
// - Background refetching
// - Deduplication
// - Stale-while-revalidate
// - Optimistic updates
// - Pagination and infinite queries
// - Excellent devtools

// Examples where TanStack Query shines:
// - Fetching data from API
// - Caching responses
// - Synchronizing with server
// - Background updates
// - Managing pagination
// - Infinite scrolling
```

### Weaknesses

```javascript
// ❌ WEAKNESSES:
// - Only for server state (not client state)
// - Learning curve for advanced features
// - Requires separate client state management
// - Extra dependency

// These aren't really weaknesses, just different purpose
```

### When to Use TanStack Query

```javascript
// Use TanStack Query when:
// 1. Fetching data from API
// 2. Need caching
// 3. Need background sync
// 4. Managing server state

// Example: Fetching users
function UserList() {
  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await fetch('/api/users');
      return response.json();
    }
  });
  
  if (isLoading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;
  
  return (
    <ul>
      {users?.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}
```

---

## Decision Matrix

### Quick Reference

```
┌─────────────────────┬─────────────┬────────┬──────────┬──────────┐
│ Use Case            │ Context API │ Zustand│ Redux    │ TQuery   │
├─────────────────────┼─────────────┼────────┼──────────┼──────────┤
│ App themes          │ ✅ BEST     │ OK     │ Overkill │ NO       │
│ User auth           │ ✅ BEST     │ OK     │ OK       │ NO       │
│ UI state (modals)   │ OK          │ ✅ BEST│ OK       │ NO       │
│ Shopping cart       │ NO          │ ✅ BEST│ OK       │ NO       │
│ Complex features    │ NO          │ ✅ BEST│ ✅ OK    │ NO       │
│ Large app, team     │ NO          │ OK     │ ✅ BEST  │ N/A      │
│ API data            │ NO          │ NO     │ NO       │ ✅ BEST  │
│ Pagination          │ NO          │ NO     │ NO       │ ✅ BEST  │
│ Caching            │ NO          │ NO     │ NO       │ ✅ BEST  │
│ Bundle size         │ ✅ 0KB      │ ✅ 2KB │ ❌ 30KB  │ ⚠️ 7KB   │
│ Learning curve      │ ✅ Easy     │ ✅ Easy│ ❌ Hard  │ ⚠️ Medium│
│ DevTools            │ ❌ None     │ ✅ Redux│ ✅ Redux │ ✅ React │
│ Devtools            │ None        │ Yes    │ Yes      │ Yes      │
└─────────────────────┴─────────────┴────────┴──────────┴──────────┘
```

---

## Real-World Examples

### Example 1: E-commerce App

```javascript
// Recommended architecture:
// 1. Context for: User auth, theme, language
// 2. Zustand for: Shopping cart, filters, sorting
// 3. TanStack Query for: Product list, search results, reviews

// Context (User)
const useAuth = () => useContext(AuthContext);

// Zustand (Cart)
const useCartStore = create((set) => ({
  items: [],
  addItem: (item) => set((state) => ({
    items: [...state.items, item]
  }))
}));

// TanStack Query (Server)
function ProductList() {
  const { data: products } = useQuery({
    queryKey: ['products'],
    queryFn: fetchProducts
  });
}

// Combining in component
function ProductPage() {
  const { user } = useAuth();                    // Context
  const { addItem } = useCartStore();            // Zustand
  const { data: product } = useQuery({...});    // Query
  
  return (
    <div>
      <p>Welcome, {user.name}</p>
      <button onClick={() => addItem(product)}>
        Add to Cart
      </button>
    </div>
  );
}
```

### Example 2: Project Management Tool

```javascript
// Recommended:
// 1. Context for: User auth, workspace settings
// 2. Zustand for: UI state (sidebar, modal), filters
// 3. TanStack Query for: Projects, tasks, comments
// 4. No Redux needed!

// Context
const useAuth = () => useContext(AuthContext);
const useWorkspace = () => useContext(WorkspaceContext);

// Zustand (UI state)
const useUIStore = create((set) => ({
  sidebarOpen: true,
  selectedProjectId: null,
  filters: { status: 'all' },
  toggleSidebar: () => set((state) => ({
    sidebarOpen: !state.sidebarOpen
  }))
}));

// Query (Server state)
function ProjectList() {
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects
  });
}
```

### Example 3: When Redux Makes Sense

```javascript
// Redux needed when:
// - 100+ person teams
// - Extremely complex state interactions
// - Existing Redux codebase
// - Time-travel debugging critical

// Example: Financial trading platform
// Redux can model:
// - Market state
// - Portfolio state
// - Order management
// - Trade history
// - Account settings
// With time-travel debugging through all changes

// But honestly, Zustand + TanStack Query might be better!
```

---

## Migration Paths

### Context → Zustand

```javascript
// Before: Context
const UserContext = createContext();

function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  
  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
}

// After: Zustand
const useUserStore = create((set) => ({
  user: null,
  setUser: (user) => set({ user })
}));

// Migration steps:
// 1. Create Zustand store with same structure
// 2. Replace useContext calls with useUserStore
// 3. Remove Provider (optional - still works)
// 4. Test everything
```

### Redux → Zustand

```javascript
// Before: Redux
const INCREMENT = 'INCREMENT';

function counterReducer(state = 0, action) {
  if (action.type === INCREMENT) {
    return state + 1;
  }
  return state;
}

const store = createStore(counterReducer);

// After: Zustand (so much simpler!)
const useCounterStore = create((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 }))
}));

// Migration steps:
// 1. Replace each reducer with Zustand action
// 2. Replace useSelector with hook
// 3. Replace dispatch with direct action call
// 4. Remove Provider
```

### No Query Library → TanStack Query

```javascript
// Before: Manual fetching
function UserList() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    setLoading(true);
    fetch('/api/users')
      .then(r => r.json())
      .then(data => {
        setUsers(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, []);
  
  // Lots of manual state!
}

// After: TanStack Query (much cleaner!)
function UserList() {
  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => fetch('/api/users').then(r => r.json())
  });
  
  // Automatic caching, refetching, deduplication!
}
```

---

## Common Pitfalls

### Pitfall 1: Using the Wrong Tool

```javascript
// ❌ WRONG: Using Redux for simple cart
// Too much boilerplate for simple state

const useCart = create((set) => ({
  items: [],
  addItem: (item) => set((state) => ({
    items: [...state.items, item]
  }))
}));

// ✅ Simple with Zustand, perfect!
```

### Pitfall 2: Managing Server State with Client State Tools

```javascript
// ❌ WRONG: Using Zustand for API data
const useUsersStore = create((set) => ({
  users: [],
  
  fetchUsers: async () => {
    const data = await fetch('/api/users').then(r => r.json());
    set({ users: data });
  }
}));

// Problems:
// - No automatic caching
// - Manual refetching logic
// - No deduplication
// - Manual background sync

// ✅ CORRECT: Use TanStack Query
function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => fetch('/api/users').then(r => r.json())
  });
}

// Automatic: caching, refetching, deduplication, background sync
```

### Pitfall 3: Over-Engineering Simple Apps

```javascript
// ❌ WRONG: Using Redux for a 3-page blog
// Way too much boilerplate

// ✅ CORRECT: Use Context + TanStack Query
const AuthContext = createContext();  // Auth
const useQuery(...);                   // Blog posts
```

---

## Interview Questions

### Q1: When should you use Context vs Zustand?

```
Answer:
Context:
- App-level state (theme, auth, language)
- Changes infrequently
- Want zero dependencies
- Simple structure

Zustand:
- Feature-level state (cart, filters, UI)
- More frequent updates
- Complex state interactions
- Need good performance
- Want optional devtools

Example:
- Theme: Context (app-level)
- Cart: Zustand (feature-level)
```

### Q2: Should you use Redux today?

```
Answer:
Redux is still good for:
- Very large teams (100+ people)
- Existing Redux codebases
- Extremely complex state

But for new projects, consider:
- Zustand: Much simpler, better DX
- TanStack Query: Better for server state

Redux added overhead that most projects don't need.
Modern alternatives are better choices.
```

### Q3: What's the relationship between Zustand and TanStack Query?

```
Answer:
Different purposes:

Zustand: Client state
- Form state
- UI state (modals, sidebar)
- User preferences
- Shopping cart

TanStack Query: Server state
- API data
- Caching
- Synchronization
- Pagination

Use both together:
- Zustand for local state
- Query for server state
- They work great together
```

---

## Resources

- **Context API:** https://react.dev/reference/react/useContext
- **Zustand:** https://github.com/pmndrs/zustand
- **Redux:** https://redux.js.org/
- **TanStack Query:** https://tanstack.com/query/latest
- **State Management Guide:** https://kentcdodds.com/blog/how-to-use-react-context-effectively

---

**Next:** [Part 4.5: Testing State Management](./04-testing-state-management.md) - Complete testing strategies
