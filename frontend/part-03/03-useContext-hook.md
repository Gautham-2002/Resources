# Part 3.4: useContext Hook

## What You'll Learn

- The prop drilling problem
- Context API fundamentals
- Creating and using context
- Provider and Consumer patterns
- Context with multiple values
- Optimizing context (preventing unnecessary re-renders)
- Context vs state management libraries
- Common patterns and best practices
- Performance considerations
- Interview questions

---

## Table of Contents

1. [The Prop Drilling Problem](#the-prop-drilling-problem)
2. [Context Fundamentals](#context-fundamentals)
3. [Creating Context](#creating-context)
4. [Consuming Context](#consuming-context)
5. [Multiple Context Values](#multiple-context-values)
6. [Context with useState](#context-with-usestate)
7. [Context with useReducer](#context-with-usereducer)
8. [Optimizing Context Performance](#optimizing-context-performance)
9. [Context vs State Management](#context-vs-state-management)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Interview Questions](#interview-questions)
13. [Resources](#resources)

---

## The Prop Drilling Problem

### What is Prop Drilling?

Prop drilling is passing data through many levels of components that don't use it.

```jsx
// Problem: Passing theme through many levels
function App() {
  const [theme, setTheme] = useState('light');
  
  // Must pass theme through every component
  return <Header theme={theme} setTheme={setTheme} />;
}

function Header({ theme, setTheme }) {
  // Don't use theme, but must pass it along
  return <Navigation theme={theme} setTheme={setTheme} />;
}

function Navigation({ theme, setTheme }) {
  // Don't use theme, but must pass it along
  return <SideMenu theme={theme} setTheme={setTheme} />;
}

function SideMenu({ theme, setTheme }) {
  // Don't use theme, but must pass it along
  return <ThemeButton theme={theme} setTheme={setTheme} />;
}

function ThemeButton({ theme, setTheme }) {
  // Finally use theme here
  return (
    <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
      Current theme: {theme}
    </button>
  );
}

// Problem:
// - Many components pass theme without using it
// - Hard to add new props (must pass through all)
// - Refactoring is painful
// - Props are "noise" in component signatures
```

### Why It's Bad

```jsx
// Every component must accept and pass props
// Even if it doesn't use them
// This is "prop drilling" or "threading"

function GrandparentComponent({ userId, userName, userEmail, userRole, theme, language, timezone }) {
  return (
    <ParentComponent 
      userId={userId}
      userName={userName}
      userEmail={userEmail}
      userRole={userRole}
      theme={theme}
      language={language}
      timezone={timezone}
    />
  );
}

// This is hard to read and maintain
// Props are mixed with actual component logic
```

---

## Context Fundamentals

### What is Context?

Context provides a way to **pass data through the component tree without passing props at every level**.

```jsx
// Without context (prop drilling)
<GrandparentComponent user={user} />
  <ParentComponent user={user} />
    <ChildComponent user={user} />
      <GrandchildComponent user={user} />  // user finally used here
        Display: {user.name}

// With context (skip the middlemen)
<UserProvider user={user}>
  <GrandparentComponent />
    <ParentComponent />
      <ChildComponent />
        <GrandchildComponent />
          Display: {user.name}  // Access user from context
```

### Context API Overview

```jsx
// 3 pieces:
// 1. Create context
const UserContext = React.createContext();

// 2. Provide context
function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  
  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
}

// 3. Consume context
function UserDisplay() {
  const { user } = useContext(UserContext);
  return <div>{user?.name}</div>;
}
```

---

## Creating Context

### Step 1: Create Context

```jsx
import { createContext } from 'react';

// Create context with default value
const ThemeContext = createContext(null);

// Or with default value
const ThemeContext = createContext({
  theme: 'light',
  setTheme: () => {}
});

// Best practice: Create custom hook
export const useTheme = () => {
  const context = useContext(ThemeContext);
  
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  
  return context;
};
```

### Step 2: Create Provider Component

```jsx
import { useState, createContext, useContext } from 'react';

const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  
  const value = {
    theme,
    setTheme,
    toggleTheme: () => setTheme(t => t === 'light' ? 'dark' : 'light')
  };
  
  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

// Custom hook for consuming
export const useTheme = () => {
  const context = useContext(ThemeContext);
  
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  
  return context;
};
```

### Step 3: Use in App

```jsx
function App() {
  return (
    <ThemeProvider>
      <Header />
      <MainContent />
      <Footer />
    </ThemeProvider>
  );
}
```

---

## Consuming Context

### Using useContext Hook

```jsx
import { useContext } from 'react';

function ThemedButton() {
  // Get context value
  const { theme, toggleTheme } = useContext(ThemeContext);
  
  return (
    <button 
      style={{ 
        backgroundColor: theme === 'light' ? '#fff' : '#000',
        color: theme === 'light' ? '#000' : '#fff'
      }}
      onClick={toggleTheme}
    >
      Current theme: {theme}
    </button>
  );
}
```

### With Custom Hook (Recommended)

```jsx
function ThemedButton() {
  const { theme, toggleTheme } = useTheme();  // Custom hook
  
  return (
    <button onClick={toggleTheme}>
      Current theme: {theme}
    </button>
  );
}

// Benefits:
// - Cleaner code
// - Type-safe (with TypeScript)
// - Error handling (throws if not in provider)
```

### Error Handling

```jsx
// Good practice: Throw error if context not available
export const useTheme = () => {
  const context = useContext(ThemeContext);
  
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  
  return context;
};

// If someone forgets to wrap with provider:
function Component() {
  const theme = useTheme();  // ❌ Error: useTheme must be used within ThemeProvider
  return <div>{theme}</div>;
}

// App.js (missing provider)
// function App() {
//   return <Component />;  // ❌ Error thrown
// }

// Correct:
function App() {
  return (
    <ThemeProvider>
      <Component />  // ✅ Works
    </ThemeProvider>
  );
}
```

---

## Multiple Context Values

### Multiple Context Pattern

```jsx
import { createContext, useContext, useState } from 'react';

// Create multiple contexts
const UserContext = createContext();
const ThemeContext = createContext();
const LanguageContext = createContext();

// Custom hooks
export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) throw new Error('useUser must be used within UserProvider');
  return context;
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within LanguageProvider');
  return context;
};

// Providers
export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState('en');
  return (
    <LanguageContext.Provider value={{ language, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}

// Combined provider
export function AppProviders({ children }) {
  return (
    <UserProvider>
      <ThemeProvider>
        <LanguageProvider>
          {children}
        </LanguageProvider>
      </ThemeProvider>
    </UserProvider>
  );
}
```

### Usage

```jsx
function App() {
  return (
    <AppProviders>
      <Header />
      <MainContent />
      <Footer />
    </AppProviders>
  );
}

function Header() {
  const { user } = useUser();
  const { theme } = useTheme();
  const { language } = useLanguage();
  
  return (
    <header style={{ background: theme === 'light' ? '#fff' : '#000' }}>
      <h1>{language === 'en' ? 'Welcome' : 'Bienvenue'}, {user?.name}</h1>
    </header>
  );
}
```

---

## Context with useState

### Simple State Management

```jsx
import { createContext, useContext, useState } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const login = async (email, password) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      
      if (!response.ok) throw new Error('Login failed');
      
      const userData = await response.json();
      setUser(userData);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };
  
  const logout = () => {
    setUser(null);
  };
  
  const value = {
    user,
    isLoading,
    error,
    login,
    logout
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
```

### Usage

```jsx
function LoginForm() {
  const { login, isLoading, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    await login(email, password);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input 
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
      <input 
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
      />
      <button disabled={isLoading}>
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
      {error && <p>{error}</p>}
    </form>
  );
}

function Dashboard() {
  const { user, logout } = useAuth();
  
  if (!user) return <div>Not logged in</div>;
  
  return (
    <div>
      <h1>Welcome, {user.name}</h1>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

---

## Context with useReducer

### Complex State Management

```jsx
import { createContext, useContext, useReducer } from 'react';

const StoreContext = createContext();

// Reducer function
function storeReducer(state, action) {
  switch (action.type) {
    case 'ADD_TO_CART':
      return {
        ...state,
        cart: [...state.cart, action.payload]
      };
    
    case 'REMOVE_FROM_CART':
      return {
        ...state,
        cart: state.cart.filter(item => item.id !== action.payload)
      };
    
    case 'UPDATE_QUANTITY':
      return {
        ...state,
        cart: state.cart.map(item =>
          item.id === action.payload.id
            ? { ...item, quantity: action.payload.quantity }
            : item
        )
      };
    
    case 'CLEAR_CART':
      return {
        ...state,
        cart: []
      };
    
    default:
      return state;
  }
}

const initialState = {
  cart: [],
  total: 0
};

export function StoreProvider({ children }) {
  const [state, dispatch] = useReducer(storeReducer, initialState);
  
  const value = {
    state,
    dispatch
  };
  
  return (
    <StoreContext.Provider value={value}>
      {children}
    </StoreContext.Provider>
  );
}

export const useStore = () => {
  const context = useContext(StoreContext);
  if (!context) throw new Error('useStore must be used within StoreProvider');
  return context;
};
```

### Usage

```jsx
function ProductCard({ product }) {
  const { dispatch } = useStore();
  
  return (
    <div>
      <h3>{product.name}</h3>
      <p>${product.price}</p>
      <button onClick={() => dispatch({
        type: 'ADD_TO_CART',
        payload: product
      })}>
        Add to Cart
      </button>
    </div>
  );
}

function Cart() {
  const { state, dispatch } = useStore();
  
  return (
    <div>
      <h2>Cart ({state.cart.length})</h2>
      {state.cart.map(item => (
        <div key={item.id}>
          <p>{item.name}</p>
          <input 
            type="number"
            value={item.quantity}
            onChange={(e) => dispatch({
              type: 'UPDATE_QUANTITY',
              payload: { id: item.id, quantity: Number(e.target.value) }
            })}
          />
          <button onClick={() => dispatch({
            type: 'REMOVE_FROM_CART',
            payload: item.id
          })}>
            Remove
          </button>
        </div>
      ))}
      <button onClick={() => dispatch({ type: 'CLEAR_CART' })}>
        Clear Cart
      </button>
    </div>
  );
}
```

---

## Optimizing Context Performance

### The Problem: All Consumers Re-render

```jsx
function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  const [fontSize, setFontSize] = useState(16);
  
  // Every consumer re-renders when ANYTHING changes
  const value = {
    theme,
    setTheme,
    fontSize,
    setFontSize
  };
  
  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

// Problem:
function ThemeButton() {
  const { theme, setTheme } = useContext(ThemeContext);
  // Re-renders when fontSize changes (doesn't use it!)
  return <button onClick={() => setTheme('dark')}>{theme}</button>;
}

function FontSizeSelector() {
  const { fontSize, setFontSize } = useContext(ThemeContext);
  // Re-renders when theme changes (doesn't use it!)
  return <input onChange={(e) => setFontSize(Number(e.target.value))} />;
}
```

### Solution 1: Split Context

```jsx
// Separate contexts for different values
const ThemeContext = createContext();
const FontSizeContext = createContext();

function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

function FontSizeProvider({ children }) {
  const [fontSize, setFontSize] = useState(16);
  
  return (
    <FontSizeContext.Provider value={{ fontSize, setFontSize }}>
      {children}
    </FontSizeContext.Provider>
  );
}

// Now each component only re-renders when its context changes!
function ThemeButton() {
  const { theme, setTheme } = useContext(ThemeContext);
  // Only re-renders when theme changes ✓
  return <button onClick={() => setTheme('dark')}>{theme}</button>;
}

function FontSizeSelector() {
  const { fontSize, setFontSize } = useContext(FontSizeContext);
  // Only re-renders when fontSize changes ✓
  return <input onChange={(e) => setFontSize(Number(e.target.value))} />;
}
```

### Solution 2: useMemo for Value

```jsx
// Memoize context value to prevent unnecessary updates
function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  
  // Memoize value object
  const value = useMemo(() => ({
    theme,
    setTheme
  }), [theme]);  // Only creates new object when theme changes
  
  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

// But best practice is still to split contexts
```

### Solution 3: Selector Pattern (Advanced)

```jsx
// Allow consumers to select specific parts
function useTheme(selector) {
  const context = useContext(ThemeContext);
  
  // Let consumer select what they care about
  if (selector) {
    return selector(context);
  }
  
  return context;
}

// Usage:
function ThemeButton() {
  // Only subscribes to theme changes
  const theme = useTheme(ctx => ctx.theme);
  return <button>{theme}</button>;
}

// This is complex, better to split context instead
```

---

## Context vs State Management

### When to Use Context

```jsx
// ✅ USE CONTEXT FOR:
// 1. Theme/appearance
// 2. Language/localization
// 3. User authentication
// 4. Global UI state (modal open/close)
// 5. Application settings

// Example: Theme
const ThemeProvider = () => {
  const [theme, setTheme] = useState('light');
  
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
```

### When NOT to Use Context

```jsx
// ❌ DON'T USE CONTEXT FOR:
// 1. Frequently changing state (lots of re-renders)
// 2. Complex state updates
// 3. Need for time-travel debugging
// 4. Need for middleware
// 5. Large amounts of data

// Example: Form state
// BAD: Don't use context
<FormContext.Provider value={{ formState, setFormState }}>
  <TextInput />
  <TextInput />
  {/* Every keystroke re-renders all inputs */}
</FormContext.Provider>

// GOOD: Use local state
function Form() {
  const [formState, setFormState] = useState({...});
  
  return (
    <>
      <TextInput value={formState.name} onChange={...} />
      <TextInput value={formState.email} onChange={...} />
    </>
  );
}
```

### Context + TanStack Query/Zustand

```jsx
// Best practice: Context for app-level state, Zustand for complex state

// Context: Theme, Auth, Language
<AuthProvider>
  <ThemeProvider>
    <LanguageProvider>
      {/* App */}
    </LanguageProvider>
  </ThemeProvider>
</AuthProvider>

// Zustand: Shopping cart, notifications, complex state
const useStore = create((set) => ({
  cart: [],
  addToCart: (item) => set(state => ({
    cart: [...state.cart, item]
  }))
}));

// TanStack Query: Server state
const { data: users } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers
});
```

---

## Common Patterns & Best Practices

### Pattern 1: Custom Provider Hook

```jsx
// Always export both provider and hook together
export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  
  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within UserProvider');
  }
  return context;
}

// Usage:
// 1. Wrap app with provider
// 2. Use custom hook anywhere inside
```

### Pattern 2: Context with Callbacks

```jsx
export function DataProvider({ children }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const fetchData = useCallback(async (url) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(url);
      const json = await response.json();
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);
  
  const value = useMemo(() => ({
    data,
    loading,
    error,
    fetchData
  }), [data, loading, error, fetchData]);
  
  return (
    <DataContext.Provider value={value}>
      {children}
    </DataContext.Provider>
  );
}
```

### Pattern 3: Combining Multiple Providers

```jsx
// Export combined providers
export function AppProviders({ children }) {
  return (
    <AuthProvider>
      <ThemeProvider>
        <LanguageProvider>
          <NotificationProvider>
            {children}
          </NotificationProvider>
        </LanguageProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}

// Usage: Wrap whole app once
function App() {
  return (
    <AppProviders>
      <MainApp />
    </AppProviders>
  );
}
```

---

## Common Pitfalls

### Pitfall 1: Creating Context Inside Component

```jsx
// ❌ WRONG: Creates new context every render
function App() {
  const ThemeContext = createContext();  // New context!
  
  return (
    <ThemeContext.Provider value="light">
      <Component />
    </ThemeContext.Provider>
  );
}

// ✅ CORRECT: Create outside component
const ThemeContext = createContext();

function App() {
  return (
    <ThemeContext.Provider value="light">
      <Component />
    </ThemeContext.Provider>
  );
}
```

### Pitfall 2: Forgetting Provider

```jsx
// ❌ WRONG: No provider
function App() {
  return <Component />;
}

function Component() {
  const { theme } = useTheme();  // ❌ Error!
  return <div>{theme}</div>;
}

// ✅ CORRECT: Wrap with provider
function App() {
  return (
    <ThemeProvider>
      <Component />
    </ThemeProvider>
  );
}
```

### Pitfall 3: Unnecessary Re-renders

```jsx
// ❌ WRONG: All consumers re-render
const value = {
  theme,
  setTheme,
  fontSize,
  setFontSize
};

// ✅ CORRECT: Split contexts or memoize
const value = useMemo(() => ({
  theme,
  setTheme
}), [theme]);
```

---

## Interview Questions

### Q1: What's the difference between Context and Props?

```
Answer:
Props pass data directly parent → child (explicit).
Context passes data through tree without intermediate props (implicit).

Props:
- Explicit data flow
- Components must pass through
- Easy to track
- Better for component reusability

Context:
- Implicit data flow
- Skip intermediate components
- Harder to track
- Better for global state

Use props for component-specific data.
Use context for app-level data (theme, auth, language).
```

### Q2: When should you NOT use Context?

```
Answer: Don't use context for:
- Frequently changing state (many re-renders)
- Form input state (use local state)
- Data that components own
- Complex state logic (use useReducer + library)
- When you need debugging (use Zustand with devtools)

Use Zustand or Redux for complex state management.
Use TanStack Query for server state.
Use context for app-level settings only.
```

### Q3: How do you prevent unnecessary Context re-renders?

```
Answer: Multiple approaches:
1. Split contexts (separate contexts for different values)
2. Memoize context value (useMemo)
3. Use selector pattern (select specific values)
4. Lift provider higher (wrap only what needs it)

Best: Split contexts based on update frequency.
Keep frequently changing state in separate context.
```

---

## Resources

- **Context API Documentation:** https://react.dev/reference/react/createContext
- **useContext Hook:** https://react.dev/reference/react/useContext
- **Prop Drilling Solutions:** https://react.dev/learn/passing-data-deeply-with-context
- **Context Performance:** https://kentcdodds.com/blog/how-to-optimize-your-context-value
- **Context vs Redux:** https://redux.js.org/tutorials/fundamentals/part-8-modern-redux

---

**Next:** [Part 3.5: useReducer Hook](./03-useReducer-hook.md) - Master complex state management with reducers
