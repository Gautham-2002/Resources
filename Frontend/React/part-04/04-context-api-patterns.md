# Part 4.1: Context API Patterns

## What You'll Learn

- Advanced context patterns
- When context is sufficient vs when you need libraries
- Context with performance optimization
- Combining context with useReducer for state management
- Multiple contexts organization
- Testing context providers
- Real-world patterns and examples
- Interview questions

---

## Table of Contents

1. [Context as State Management](#context-as-state-management)
2. [Provider Pattern](#provider-pattern)
3. [Compound Provider Pattern](#compound-provider-pattern)
4. [Custom Hook Pattern](#custom-hook-pattern)
5. [Performance Optimization](#performance-optimization)
6. [Context with Reducer](#context-with-reducer)
7. [Testing Context](#testing-context)
8. [Real-World Examples](#real-world-examples)
9. [Common Pitfalls](#common-pitfalls)
10. [Interview Questions](#interview-questions)
11. [Resources](#resources)

---

## Context as State Management

### When Context is Enough

Context can handle state management if:

```javascript
// ✅ Context is sufficient for:
// 1. App-level settings (theme, language)
// 2. User authentication (user data, logout)
// 3. Modal/notification state
// 4. Global UI state (sidebar open/close)
// 5. Infrequently changing data

// ❌ Context is NOT sufficient for:
// 1. Frequently changing state (form inputs)
// 2. Complex state transitions (state machines)
// 3. Large amounts of data
// 4. Need for time-travel debugging
// 5. Need for middleware
```

### Simple State Management with Context

```jsx
import { createContext, useContext, useState } from 'react';

const NotificationContext = createContext();

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);
  
  const addNotification = (message, type = 'info') => {
    const id = Date.now();
    setNotifications(prev => [
      ...prev,
      { id, message, type }
    ]);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
      removeNotification(id);
    }, 3000);
  };
  
  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };
  
  const value = {
    notifications,
    addNotification,
    removeNotification
  };
  
  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within NotificationProvider');
  }
  return context;
};
```

### Usage

```jsx
function App() {
  return (
    <NotificationProvider>
      <MainApp />
    </NotificationProvider>
  );
}

function MainApp() {
  const { addNotification } = useNotification();
  
  return (
    <div>
      <button onClick={() => addNotification('Success!', 'success')}>
        Show Success
      </button>
    </div>
  );
}

function NotificationList() {
  const { notifications } = useNotification();
  
  return (
    <div>
      {notifications.map(n => (
        <div key={n.id} className={`notification ${n.type}`}>
          {n.message}
        </div>
      ))}
    </div>
  );
}
```

---

## Provider Pattern

### Single Provider Pattern

```jsx
// Create context
const AppContext = createContext();

// Create provider component
export function AppProvider({ children }) {
  const [state, setState] = useState(initialState);
  
  const value = {
    state,
    setState
  };
  
  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

// Create custom hook
export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
};

// Usage
function App() {
  return (
    <AppProvider>
      <MainContent />
    </AppProvider>
  );
}
```

### Multiple Providers Pattern

```jsx
// Combine multiple providers
export function RootProvider({ children }) {
  return (
    <AuthProvider>
      <ThemeProvider>
        <NotificationProvider>
          <LanguageProvider>
            {children}
          </LanguageProvider>
        </NotificationProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}

// Single place to wrap entire app
function App() {
  return (
    <RootProvider>
      <MainApp />
    </RootProvider>
  );
}
```

---

## Compound Provider Pattern

### Creating Compound Providers

```jsx
// Create multiple contexts
const AuthContext = createContext();
const AuthDispatchContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const dispatch = {
    login: async (email, password) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/login', {
          method: 'POST',
          body: JSON.stringify({ email, password })
        });
        const userData = await response.json();
        setUser(userData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    
    logout: () => {
      setUser(null);
      setError(null);
    },
    
    signup: async (email, password) => {
      // Similar to login
    }
  };
  
  return (
    <AuthContext.Provider value={{ user, loading, error }}>
      <AuthDispatchContext.Provider value={dispatch}>
        {children}
      </AuthDispatchContext.Provider>
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const useAuthDispatch = () => {
  const context = useContext(AuthDispatchContext);
  if (!context) {
    throw new Error('useAuthDispatch must be used within AuthProvider');
  }
  return context;
};
```

### Benefits of Compound Pattern

```javascript
// Separates state from actions
// Components only re-render when their context changes

// Without separation:
<AuthContext.Provider value={{ user, loading, error, login, logout }}>
  // Every component re-renders when ANY value changes

// With separation:
<AuthContext.Provider value={{ user, loading, error }}>
  <AuthDispatchContext.Provider value={{ login, logout }}>
    // Components using only dispatch don't re-render on state change
    // Components using only state don't re-render on dispatch function change
```

---

## Custom Hook Pattern

### Wrapping Context in Custom Hook

```jsx
const TodoContext = createContext();

export function TodoProvider({ children }) {
  const [todos, setTodos] = useState([]);
  
  const actions = {
    add: (text) => {
      setTodos(prev => [...prev, {
        id: Date.now(),
        text,
        completed: false
      }]);
    },
    
    toggle: (id) => {
      setTodos(prev => prev.map(t =>
        t.id === id ? { ...t, completed: !t.completed } : t
      ));
    },
    
    remove: (id) => {
      setTodos(prev => prev.filter(t => t.id !== id));
    }
  };
  
  const value = {
    todos,
    ...actions
  };
  
  return (
    <TodoContext.Provider value={value}>
      {children}
    </TodoContext.Provider>
  );
}

export const useTodos = () => {
  const context = useContext(TodoContext);
  if (!context) {
    throw new Error('useTodos must be used within TodoProvider');
  }
  
  // Optionally: wrap with useMemo for optimization
  return useMemo(() => context, [context]);
};
```

### Usage is Clean

```jsx
function TodoList() {
  const { todos, add, toggle, remove } = useTodos();
  
  return (
    <div>
      {todos.map(todo => (
        <div key={todo.id}>
          <input
            type="checkbox"
            checked={todo.completed}
            onChange={() => toggle(todo.id)}
          />
          {todo.text}
          <button onClick={() => remove(todo.id)}>×</button>
        </div>
      ))}
    </div>
  );
}
```

---

## Performance Optimization

### Splitting Contexts by Update Frequency

```jsx
// ❌ WRONG: Single context with everything
const AppContext = createContext();

export function AppProvider({ children }) {
  const [theme, setTheme] = useState('light');           // Changes rarely
  const [notifications, setNotifications] = useState([]); // Changes often
  const [user, setUser] = useState(null);                // Changes rarely
  
  // Every component re-renders when ANY changes
  const value = { theme, setTheme, notifications, setNotifications, user, setUser };
  
  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

// ✅ CORRECT: Split by update frequency
const ThemeContext = createContext();
const NotificationContext = createContext();
const UserContext = createContext();

export function AppProvider({ children }) {
  return (
    <ThemeProvider>
      <NotificationProvider>
        <UserProvider>
          {children}
        </UserProvider>
      </NotificationProvider>
    </ThemeProvider>
  );
}

// Components only subscribe to what they use
function Header() {
  const { theme } = useTheme();  // Only re-renders on theme change
  return <header style={{ background: theme === 'dark' ? '#000' : '#fff' }} />;
}

function NotificationCenter() {
  const { notifications } = useNotification();  // Only re-renders on notification change
  return <div>{notifications.map(n => ...)}</div>;
}
```

### Memoization for Context Values

```jsx
export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  
  // Memoize value object
  const value = useMemo(() => ({
    user,
    role,
    setUser,
    setRole
  }), [user, role]);
  
  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}
```

---

## Context with Reducer

### Combining Context + Reducer for Complex State

```jsx
import { createContext, useContext, useReducer, useMemo } from 'react';

const StoreContext = createContext();

const initialState = {
  cart: [],
  total: 0,
  discountCode: null,
  shipping: 'standard'
};

function storeReducer(state, action) {
  switch (action.type) {
    case 'ADD_TO_CART':
      return {
        ...state,
        cart: [...state.cart, action.payload],
        total: state.total + action.payload.price
      };
    
    case 'REMOVE_FROM_CART':
      const item = state.cart.find(item => item.id === action.payload);
      return {
        ...state,
        cart: state.cart.filter(item => item.id !== action.payload),
        total: state.total - item.price
      };
    
    case 'APPLY_DISCOUNT':
      const discount = action.payload.code === 'SAVE10' ? 0.1 : 0;
      return {
        ...state,
        discountCode: action.payload.code,
        total: state.total * (1 - discount)
      };
    
    case 'SET_SHIPPING':
      const shippingCost = action.payload === 'express' ? 10 : 5;
      return {
        ...state,
        shipping: action.payload,
        total: state.total + shippingCost
      };
    
    default:
      return state;
  }
}

export function StoreProvider({ children }) {
  const [state, dispatch] = useReducer(storeReducer, initialState);
  
  const value = useMemo(() => ({
    state,
    dispatch
  }), [state]);
  
  return (
    <StoreContext.Provider value={value}>
      {children}
    </StoreContext.Provider>
  );
}

export const useStore = () => {
  const context = useContext(StoreContext);
  if (!context) {
    throw new Error('useStore must be used within StoreProvider');
  }
  return context;
};
```

### Usage

```jsx
function ShoppingCart() {
  const { state, dispatch } = useStore();
  
  return (
    <div>
      <h2>Cart ({state.cart.length})</h2>
      {state.cart.map(item => (
        <div key={item.id}>
          <p>{item.name} - ${item.price}</p>
          <button onClick={() => dispatch({
            type: 'REMOVE_FROM_CART',
            payload: item.id
          })}>Remove</button>
        </div>
      ))}
      <p>Total: ${state.total}</p>
    </div>
  );
}

function DiscountInput() {
  const { dispatch } = useStore();
  
  return (
    <input
      placeholder="Discount code"
      onBlur={(e) => dispatch({
        type: 'APPLY_DISCOUNT',
        payload: { code: e.target.value }
      })}
    />
  );
}
```

---

## Testing Context

### Testing Provider with React Testing Library

```jsx
import { render, screen } from '@testing-library/react';
import { ThemeProvider, useTheme } from './ThemeContext';

function TestComponent() {
  const { theme } = useTheme();
  return <div>{theme}</div>;
}

describe('ThemeContext', () => {
  it('provides theme value', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    expect(screen.getByText('light')).toBeInTheDocument();
  });
  
  it('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => {
      render(<TestComponent />);
    }).toThrow('useTheme must be used within ThemeProvider');
    
    spy.mockRestore();
  });
});
```

### Testing with userEvent

```jsx
import userEvent from '@testing-library/user-event';

describe('ThemeContext with actions', () => {
  it('toggles theme on button click', async () => {
    const user = userEvent.setup();
    
    function TestApp() {
      const { theme, toggleTheme } = useTheme();
      return (
        <div>
          <p>{theme}</p>
          <button onClick={toggleTheme}>Toggle</button>
        </div>
      );
    }
    
    render(
      <ThemeProvider>
        <TestApp />
      </ThemeProvider>
    );
    
    expect(screen.getByText('light')).toBeInTheDocument();
    
    await user.click(screen.getByRole('button'));
    
    expect(screen.getByText('dark')).toBeInTheDocument();
  });
});
```

---

## Real-World Examples

### Authentication Context

```jsx
const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Check if user is already logged in on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('/api/me');
        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    checkAuth();
  }, []);
  
  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      
      if (!response.ok) throw new Error('Login failed');
      
      const userData = await response.json();
      setUser(userData);
      localStorage.setItem('token', userData.token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const logout = () => {
    setUser(null);
    localStorage.removeItem('token');
  };
  
  const value = {
    user,
    loading,
    error,
    login,
    logout,
    isAuthenticated: !!user
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

### Theme Context with Persistence

```jsx
const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    // Read from localStorage on init
    return localStorage.getItem('theme') || 'light';
  });
  
  // Persist to localStorage when theme changes
  useEffect(() => {
    localStorage.setItem('theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);
  
  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };
  
  const value = { theme, toggleTheme };
  
  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};
```

---

## Common Pitfalls

### Pitfall 1: Creating Context Inside Component

```jsx
// ❌ WRONG: Context created inside component
function App() {
  const AppContext = createContext();  // New context every render!
  
  return (
    <AppContext.Provider value="test">
      <Child />
    </AppContext.Provider>
  );
}

// ✅ CORRECT: Context created outside
const AppContext = createContext();

function App() {
  return (
    <AppContext.Provider value="test">
      <Child />
    </AppContext.Provider>
  );
}
```

### Pitfall 2: Not Memoizing Context Value

```jsx
// ❌ WRONG: New object every render
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>  // New object!
      {children}
    </ThemeContext.Provider>
  );
}

// ✅ CORRECT: Memoize the value
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  
  const value = useMemo(() => ({
    theme,
    setTheme
  }), [theme]);
  
  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}
```

### Pitfall 3: Putting Frequently Changing State in Context

```jsx
// ❌ WRONG: Form input in context (re-renders every keystroke)
<FormContext.Provider value={{ formData, setFormData }}>
  <FormInput />  // Re-renders on every keystroke!
</FormContext.Provider>

// ✅ CORRECT: Use local state for form inputs
function FormInput() {
  const [formData, setFormData] = useState({});
  
  return <input onChange={(e) => setFormData(...)} />;
}
```

---

## Interview Questions

### Q1: When should you use Context vs Zustand?

```
Answer:
Context:
- Pros: Built-in, no dependencies, simple
- Cons: All consumers re-render on change, not optimized for frequent changes

Zustand:
- Pros: Optimized for frequent updates, small bundle, selectors
- Cons: External dependency

Use Context for: App settings, auth, theme, language
Use Zustand for: Complex state, frequent updates, multiple features
```

### Q2: How do you prevent unnecessary re-renders with Context?

```
Answer:
1. Split contexts by update frequency
2. Memoize context values
3. Use compound context pattern (separate state/dispatch)
4. Use custom hooks with useMemo

Example:
const value = useMemo(() => ({ user, setUser }), [user]);
<Context.Provider value={value}>
```

### Q3: Why is error handling in custom hooks important?

```
Answer:
Custom hooks should throw errors if used outside provider.

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

Helps catch mistakes early.
Provides clear error messages.
```

---

## Resources

- **Context API Advanced:** https://react.dev/reference/react/useContext
- **Avoiding Over-Engineering:** https://kentcdodds.com/blog/how-to-use-react-context-effectively
- **Context Performance:** https://react.dev/learn/passing-data-deeply-with-context#optimizing-re-renders-when-passing-objects-and-functions
- **useReducer with Context:** https://react.dev/learn/scaling-up-with-reducer-and-context
- **Context Best Practices:** https://blog.logrocket.com/react-context-api-deep-dive-examples/

---

**Next:** [Part 4.2: Zustand Fundamentals](./04-zustand-fundamentals.md) - Modern state management without Redux complexity
