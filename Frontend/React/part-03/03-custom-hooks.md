# Part 3.8: Custom Hooks

## What You'll Learn

- What custom hooks are and why they exist
- Naming conventions for custom hooks
- Extracting hook logic from components
- Building common custom hooks
- Sharing hooks across projects
- Complex custom hook patterns
- Testing custom hooks
- Interview questions

---

## Table of Contents

1. [Custom Hook Fundamentals](#custom-hook-fundamentals)
2. [Naming and Rules](#naming-and-rules)
3. [Building Custom Hooks](#building-custom-hooks)
4. [Common Custom Hooks](#common-custom-hooks)
5. [Advanced Patterns](#advanced-patterns)
6. [Hook Composition](#hook-composition)
7. [Testing Custom Hooks](#testing-custom-hooks)
8. [Common Patterns](#common-patterns)
9. [Common Pitfalls](#common-pitfalls)
10. [Interview Questions](#interview-questions)
11. [Resources](#resources)

---

## Custom Hook Fundamentals

### What is a Custom Hook?

A custom hook is a **JavaScript function that uses React hooks to extract component logic into reusable functions**.

```jsx
// Regular component with logic
function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    setLoading(true);
    fetch(`/api/users/${userId}`)
      .then(r => r.json())
      .then(data => {
        setUser(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, [userId]);
  
  return (
    <div>
      {loading && <p>Loading...</p>}
      {error && <p>Error: {error}</p>}
      {user && <p>{user.name}</p>}
    </div>
  );
}

// Extract the logic into a custom hook
function useUser(userId) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    setLoading(true);
    fetch(`/api/users/${userId}`)
      .then(r => r.json())
      .then(data => {
        setUser(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, [userId]);
  
  return { user, loading, error };
}

// Now the component is cleaner
function UserProfile({ userId }) {
  const { user, loading, error } = useUser(userId);
  
  return (
    <div>
      {loading && <p>Loading...</p>}
      {error && <p>Error: {error}</p>}
      {user && <p>{user.name}</p>}
    </div>
  );
}
```

### Benefits of Custom Hooks

```javascript
// 1. Code Reuse
// Instead of duplicating logic in multiple components

// 2. Separation of Concerns
// Logic separated from UI components

// 3. Composition
// Combine hooks to build complex behavior

// 4. Testing
// Easier to test logic in isolation

// 5. Sharing
// Share hooks across projects via npm
```

---

## Naming and Rules

### Naming Convention

```javascript
// Custom hooks must start with "use"
function useLocalStorage(key, initialValue) { }
function useFetch(url) { }
function useWindowSize() { }
function useAsync(asyncFunction, immediate = true) { }
function useFormInput(initialValue) { }

// NOT custom hooks (don't start with use)
function getRandomNumber() { }  // Regular function
function formatDate() { }       // Regular function
```

### Rules for Custom Hooks

Custom hooks follow the same rules as regular hooks:

```javascript
// Rule 1: Only call hooks at top level
function useCustom() {
  // ✅ Top level
  const [state, setState] = useState(0);
  
  // ❌ Not top level
  if (condition) {
    const [invalid, setInvalid] = useState(0);  // ERROR!
  }
}

// Rule 2: Only call from React components or other hooks
function useCustom() {
  // ✅ Called from another hook
  const state = useState(0);
  return state;
}

function regularFunction() {
  // ❌ Can't call hook from regular function
  const [state, setState] = useState(0);  // ERROR!
}
```

---

## Building Custom Hooks

### Step 1: Extract Logic

```jsx
// Before: Logic in component
function TodoApp() {
  const [todos, setTodos] = useState([]);
  const [input, setInput] = useState('');
  
  const addTodo = () => {
    setTodos([...todos, { id: Date.now(), text: input }]);
    setInput('');
  };
  
  const removeTodo = (id) => {
    setTodos(todos.filter(t => t.id !== id));
  };
  
  const toggleTodo = (id) => {
    setTodos(todos.map(t =>
      t.id === id ? { ...t, completed: !t.completed } : t
    ));
  };
  
  return (
    <div>
      <input value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={addTodo}>Add</button>
      <ul>
        {todos.map(todo => (
          <li key={todo.id}>
            <input
              type="checkbox"
              checked={todo.completed}
              onChange={() => toggleTodo(todo.id)}
            />
            {todo.text}
            <button onClick={() => removeTodo(todo.id)}>Remove</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Step 2: Extract into Custom Hook

```jsx
// Extract into useTodos hook
function useTodos() {
  const [todos, setTodos] = useState([]);
  
  const addTodo = (text) => {
    setTodos([...todos, { id: Date.now(), text, completed: false }]);
  };
  
  const removeTodo = (id) => {
    setTodos(todos.filter(t => t.id !== id));
  };
  
  const toggleTodo = (id) => {
    setTodos(todos.map(t =>
      t.id === id ? { ...t, completed: !t.completed } : t
    ));
  };
  
  return {
    todos,
    addTodo,
    removeTodo,
    toggleTodo
  };
}

// Step 3: Simplify component
function TodoApp() {
  const [input, setInput] = useState('');
  const { todos, addTodo, removeTodo, toggleTodo } = useTodos();
  
  const handleAddTodo = () => {
    addTodo(input);
    setInput('');
  };
  
  return (
    <div>
      <input value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={handleAddTodo}>Add</button>
      <ul>
        {todos.map(todo => (
          <li key={todo.id}>
            <input
              type="checkbox"
              checked={todo.completed}
              onChange={() => toggleTodo(todo.id)}
            />
            {todo.text}
            <button onClick={() => removeTodo(todo.id)}>Remove</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

## Common Custom Hooks

### useLocalStorage

```jsx
function useLocalStorage(key, initialValue) {
  // Get from local storage then parse stored json or return initialValue
  const readValue = () => {
    if (typeof window === 'undefined') {
      return initialValue;
    }
    
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(error);
      return initialValue;
    }
  };
  
  const [storedValue, setStoredValue] = useState(readValue);
  
  // Return a wrapped version of useState's setter function that
  // persists the new value to localStorage
  const setValue = (value) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      console.warn(error);
    }
  };
  
  return [storedValue, setValue];
}

// Usage
function App() {
  const [name, setName] = useLocalStorage('name', 'John');
  
  return (
    <div>
      <input value={name} onChange={(e) => setName(e.target.value)} />
      <p>Saved: {name}</p>
    </div>
  );
}
```

### useFetch

```jsx
function useFetch(url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    if (!url) return;
    
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(url);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const json = await response.json();
        setData(json);
        setError(null);
      } catch (err) {
        setError(err);
        setData(null);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [url]);
  
  return { data, loading, error };
}

// Usage
function UserList() {
  const { data: users, loading, error } = useFetch('/api/users');
  
  if (loading) return <p>Loading...</p>;
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

### useDebounce

```jsx
function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    // Set up the timeout
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    // Clean up the timeout if value changes (or component unmounts)
    return () => clearTimeout(handler);
  }, [value, delay]);
  
  return debouncedValue;
}

// Usage
function SearchComponent() {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 500);
  
  useEffect(() => {
    if (debouncedSearchTerm) {
      performSearch(debouncedSearchTerm);
    }
  }, [debouncedSearchTerm]);
  
  return (
    <input
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
      placeholder="Search..."
    />
  );
}
```

### useAsync

```jsx
function useAsync(asyncFunction, immediate = true) {
  const [status, setStatus] = useState('idle');
  const [value, setValue] = useState(null);
  const [error, setError] = useState(null);
  
  const execute = useCallback(async () => {
    setStatus('pending');
    setValue(null);
    setError(null);
    
    try {
      const response = await asyncFunction();
      setValue(response);
      setStatus('success');
      return response;
    } catch (error) {
      setError(error);
      setStatus('error');
    }
  }, [asyncFunction]);
  
  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [execute, immediate]);
  
  return { execute, status, value, error };
}

// Usage
function Component() {
  const { status, value, error, execute } = useAsync(
    async () => {
      const response = await fetch('/api/data');
      return response.json();
    }
  );
  
  return (
    <div>
      {status === 'pending' && <p>Loading...</p>}
      {status === 'success' && <p>{value}</p>}
      {status === 'error' && <p>Error: {error.message}</p>}
      <button onClick={execute}>Retry</button>
    </div>
  );
}
```

---

## Advanced Patterns

### Hook Composition

```jsx
// Compose hooks to build complex behavior
function useUser(userId) {
  const { data: user, loading, error } = useFetch(`/api/users/${userId}`);
  const userInStorage = useLocalStorage(`user-${userId}`, null);
  
  // Combine fetched user with storage
  return {
    user: user || userInStorage,
    loading,
    error,
    saveLocally: (userData) => userInStorage[1](userData)
  };
}

// Usage
function UserProfile({ userId }) {
  const { user, loading, error, saveLocally } = useUser(userId);
  
  return (
    <div>
      {loading && <p>Loading...</p>}
      {error && <p>Error</p>}
      {user && (
        <div>
          <p>{user.name}</p>
          <button onClick={() => saveLocally(user)}>Save Locally</button>
        </div>
      )}
    </div>
  );
}
```

### Configurable Hooks

```jsx
function useFetch(url, options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const {
    headers = {},
    method = 'GET',
    body = null,
    skip = false,
    onSuccess = null,
    onError = null
  } = options;
  
  useEffect(() => {
    if (skip) return;
    
    const fetchData = async () => {
      try {
        const response = await fetch(url, {
          method,
          headers,
          body: body ? JSON.stringify(body) : null
        });
        
        const json = await response.json();
        setData(json);
        onSuccess?.(json);
      } catch (err) {
        setError(err);
        onError?.(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [url, method, headers, body, skip, onSuccess, onError]);
  
  return { data, loading, error };
}

// Usage with options
function Component() {
  const { data, loading, error } = useFetch('/api/users', {
    headers: { 'Authorization': 'Bearer token' },
    onSuccess: (data) => console.log('Fetched:', data),
    onError: (error) => console.log('Error:', error)
  });
  
  return <div>{/* ... */}</div>;
}
```

---

## Hook Composition

### Multiple Hooks Together

```jsx
function useFormField(initialValue) {
  const [value, setValue] = useState(initialValue);
  
  return {
    value,
    setValue,
    bind: {
      value,
      onChange: (e) => setValue(e.target.value)
    },
    reset: () => setValue(initialValue)
  };
}

function useForm(initialValues) {
  const fields = {};
  
  Object.entries(initialValues).forEach(([name, value]) => {
    fields[name] = useFormField(value);
  });
  
  const getValues = () => {
    const values = {};
    Object.entries(fields).forEach(([name, field]) => {
      values[name] = field.value;
    });
    return values;
  };
  
  const reset = () => {
    Object.values(fields).forEach(field => field.reset());
  };
  
  return {
    fields,
    getValues,
    reset
  };
}

// Usage
function LoginForm() {
  const { fields, getValues, reset } = useForm({
    email: '',
    password: ''
  });
  
  const handleSubmit = (e) => {
    e.preventDefault();
    console.log(getValues());
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input {...fields.email.bind} placeholder="Email" />
      <input {...fields.password.bind} type="password" placeholder="Password" />
      <button type="submit">Login</button>
      <button type="button" onClick={reset}>Reset</button>
    </form>
  );
}
```

---

## Testing Custom Hooks

### Using React Testing Library

```jsx
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

describe('useCounter', () => {
  it('should increment counter', () => {
    const { result } = renderHook(() => useCounter(0));
    
    expect(result.current.count).toBe(0);
    
    act(() => {
      result.current.increment();
    });
    
    expect(result.current.count).toBe(1);
  });
  
  it('should decrement counter', () => {
    const { result } = renderHook(() => useCounter(0));
    
    act(() => {
      result.current.decrement();
    });
    
    expect(result.current.count).toBe(-1);
  });
});
```

### Testing useFetch

```jsx
import { renderHook, waitFor } from '@testing-library/react';
import { useFetch } from './useFetch';

describe('useFetch', () => {
  it('should fetch data', async () => {
    const { result } = renderHook(() => useFetch('/api/users'));
    
    expect(result.current.loading).toBe(true);
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.data).toBeDefined();
  });
});
```

---

## Common Patterns

### Pattern 1: Hook with Callbacks

```jsx
function useList(initial = []) {
  const [items, setItems] = useState(initial);
  
  const add = useCallback((item) => {
    setItems(prev => [...prev, item]);
  }, []);
  
  const remove = useCallback((index) => {
    setItems(prev => prev.filter((_, i) => i !== index));
  }, []);
  
  const clear = useCallback(() => {
    setItems([]);
  }, []);
  
  return { items, add, remove, clear };
}
```

### Pattern 2: Hook with Refs

```jsx
function useClickOutside(callback) {
  const ref = useRef(null);
  
  useEffect(() => {
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        callback();
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [callback]);
  
  return ref;
}
```

---

## Common Pitfalls

### Pitfall 1: Not Following Hook Rules

```jsx
// ❌ WRONG: Conditional hook
function useBadHook(shouldUse) {
  if (shouldUse) {
    const [state, setState] = useState(0);  // ❌ Conditional!
  }
}

// ✅ CORRECT: Always call hooks
function useGoodHook(shouldUse) {
  const [state, setState] = useState(0);  // Always called
  
  // Use state conditionally instead
  if (!shouldUse) return null;
  
  return state;
}
```

### Pitfall 2: Not Including Dependencies

```jsx
// ❌ WRONG: Missing dependency
function useFetch(url) {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    fetch(url).then(r => r.json()).then(setData);
  }, []);  // ❌ Missing url!
}

// ✅ CORRECT: Include dependency
function useFetch(url) {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    fetch(url).then(r => r.json()).then(setData);
  }, [url]);  // ✅ Include url
}
```

### Pitfall 3: Returning New Objects Every Render

```jsx
// ❌ WRONG: New object every render
function useConfig() {
  return {
    timeout: 5000,
    retries: 3
  };  // New object every render!
}

// ✅ CORRECT: Memoize return value
function useConfig() {
  return useMemo(() => ({
    timeout: 5000,
    retries: 3
  }), []);  // Same object
}
```

---

## Interview Questions

### Q1: What's a custom hook and why use them?

```
Answer:
A custom hook is a JavaScript function that uses React hooks.
Allows reusing stateful logic between components.

Benefits:
- Code reuse
- Separation of concerns
- Easier testing
- Composable logic
- Shareable across projects

Must start with "use" prefix.
Follow same rules as regular hooks.
```

### Q2: How do you extract logic into a custom hook?

```
Answer:
1. Identify the logic you want to reuse
2. Move it into a function starting with "use"
3. Return the state and handlers
4. Replace original logic with the hook

Example: useLocalStorage extracted from multiple components.
Each component calls hook, gets their own state instance.
```

### Q3: What would you use useCallback for in a custom hook?

```
Answer:
useCallback ensures functions stay the same between renders.

Useful when:
- Returning functions from hook
- Functions used in dependency arrays
- Functions passed to child components

Example:
const add = useCallback((item) => {
  setItems([...items, item]);
}, [items]);

Prevents unnecessary re-renders in components using the hook.
```

---

## Resources

- **Custom Hooks Documentation:** https://react.dev/learn/reusing-logic-with-custom-hooks
- **Building Custom Hooks:** https://react.dev/reference/react/useState#storing-information-from-previous-renders
- **useHooks Collection:** https://usehooks.com/
- **React Hooks Library:** https://react-use.github.io/react-use/
- **Testing Hooks:** https://react-hooks-testing-library.com/

---

**Part 3 Complete!** You've mastered all essential React Hooks. Next: Part 4 - State Management with Zustand
