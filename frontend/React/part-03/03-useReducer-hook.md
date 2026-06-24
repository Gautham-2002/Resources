# Part 3.5: useReducer Hook

## What You'll Learn

- What reducers are and why they exist
- When to use useReducer vs useState
- Reducer pattern (actions, types, handlers)
- Immer integration for immutable updates
- useReducer with useContext for state management
- Complex state transitions
- Debugging reducers
- Testing reducers
- Interview questions

---

## Table of Contents

1. [useReducer Fundamentals](#usereducer-fundamentals)
2. [The Reducer Pattern](#the-reducer-pattern)
3. [When to Use useReducer](#when-to-use-usereducer)
4. [useReducer vs useState](#usereducer-vs-usestate)
5. [Complex State Logic](#complex-state-logic)
6. [Immer with useReducer](#immer-with-usereducer)
7. [useReducer with useContext](#usereducer-with-usecontext)
8. [Dispatch Function Memoization](#dispatch-function-memoization)
9. [Common Patterns](#common-patterns)
10. [Common Pitfalls](#common-pitfalls)
11. [Interview Questions](#interview-questions)
12. [Resources](#resources)

---

## useReducer Fundamentals

### What is useReducer?

useReducer is a hook for **managing complex state with a reducer function**.

```jsx
import { useReducer } from 'react';

function Counter() {
  // useReducer takes 2 required args and 1 optional
  const [state, dispatch] = useReducer(
    reducer,        // Function: (state, action) => newState
    initialState,   // Initial state value
    init            // Optional: init function for lazy init
  );
  
  return (
    <div>
      <p>Count: {state}</p>
      <button onClick={() => dispatch({ type: 'INCREMENT' })}>
        +
      </button>
    </div>
  );
}

function reducer(state, action) {
  switch (action.type) {
    case 'INCREMENT':
      return state + 1;
    case 'DECREMENT':
      return state - 1;
    case 'RESET':
      return 0;
    default:
      return state;
  }
}
```

### Reducer Function

A reducer is a **pure function that takes state and action, returns new state**.

```javascript
// Simple reducer
function reducer(state, action) {
  // state: current state
  // action: describes what happened
  
  // Return new state based on action
  switch (action.type) {
    case 'ACTION_A':
      return newState;
    case 'ACTION_B':
      return differentNewState;
    default:
      throw new Error(`Unknown action: ${action.type}`);
  }
}

// Must be PURE:
// - Same input always gives same output
// - No side effects
// - No mutations
```

### Dispatch vs setState

```jsx
// useState: Direct value updates
const [count, setCount] = useState(0);
setCount(1);         // Set to 1
setCount(count + 1); // Increment

// useReducer: Action-based updates
const [count, dispatch] = useReducer(reducer, 0);
dispatch({ type: 'SET_COUNT', payload: 1 });           // Set to 1
dispatch({ type: 'INCREMENT_COUNT', payload: 1 });      // Increment
```

---

## The Reducer Pattern

### Action Types

```javascript
// Define constants for action types
const ACTIONS = {
  INCREMENT: 'INCREMENT',
  DECREMENT: 'DECREMENT',
  RESET: 'RESET',
  SET_COUNT: 'SET_COUNT'
};

// Use in reducer
function reducer(state, action) {
  switch (action.type) {
    case ACTIONS.INCREMENT:
      return state + 1;
    case ACTIONS.DECREMENT:
      return state - 1;
    case ACTIONS.RESET:
      return 0;
    case ACTIONS.SET_COUNT:
      return action.payload;
    default:
      throw new Error(`Unknown action type: ${action.type}`);
  }
}

// Benefits:
// - No typos (TypeScript helps too)
// - Easier refactoring
// - Single source of truth
```

### Action Objects

```javascript
// Simple action
dispatch({ type: 'INCREMENT' });

// Action with payload
dispatch({ type: 'SET_COUNT', payload: 5 });

// Complex action
dispatch({
  type: 'UPDATE_USER',
  payload: {
    id: 1,
    name: 'John',
    email: 'john@example.com'
  }
});

// Action with metadata
dispatch({
  type: 'FETCH_SUCCESS',
  payload: data,
  meta: {
    timestamp: Date.now(),
    source: 'api'
  }
});
```

### Reducer Implementation

```javascript
const ACTIONS = {
  INCREMENT: 'INCREMENT',
  DECREMENT: 'DECREMENT',
  RESET: 'RESET'
};

function counterReducer(state, action) {
  switch (action.type) {
    case ACTIONS.INCREMENT:
      return state + 1;
    
    case ACTIONS.DECREMENT:
      return state - 1;
    
    case ACTIONS.RESET:
      return 0;
    
    default:
      throw new Error(`Unknown action: ${action.type}`);
  }
}

// Usage
function Counter() {
  const [count, dispatch] = useReducer(counterReducer, 0);
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => dispatch({ type: ACTIONS.INCREMENT })}>+</button>
      <button onClick={() => dispatch({ type: ACTIONS.DECREMENT })}>-</button>
      <button onClick={() => dispatch({ type: ACTIONS.RESET })}>Reset</button>
    </div>
  );
}
```

---

## When to Use useReducer

### useState is Simpler

```jsx
// Use useState for simple state
const [name, setName] = useState('');
const [email, setEmail] = useState('');
const [age, setAge] = useState(0);

// This is fine! useState is simpler
```

### useReducer is Better For

```jsx
// 1. Multiple related state variables
// Instead of:
const [user, setUser] = useState(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);

// Better:
const [state, dispatch] = useReducer(userReducer, initialState);
// state = { user, loading, error }

// 2. Complex state transitions
function userReducer(state, action) {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: null };
    case 'FETCH_SUCCESS':
      return { user: action.payload, loading: false, error: null };
    case 'FETCH_ERROR':
      return { ...state, loading: false, error: action.payload };
  }
}

// 3. Many state updates
// Easier to track all updates in one place (reducer)

// 4. State depends on previous state
// Reducer makes dependencies clear

// 5. Passing state down to many components
// Combine with useContext for global state
```

---

## useReducer vs useState

### Simple Counter: useState Better

```jsx
// useState: Clear and simple
function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <p>{count}</p>
      <button onClick={() => setCount(count + 1)}>+</button>
      <button onClick={() => setCount(count - 1)}>-</button>
    </div>
  );
}

// useReducer: Overkill for simple state
function Counter() {
  const [count, dispatch] = useReducer(counterReducer, 0);
  
  return (
    <div>
      <p>{count}</p>
      <button onClick={() => dispatch({ type: 'INCREMENT' })}>+</button>
      <button onClick={() => dispatch({ type: 'DECREMENT' })}>-</button>
    </div>
  );
}

// useState is better here - simpler and clearer
```

### Complex Form: useReducer Better

```jsx
// useState: Too many state variables
function Form() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Hard to track all related state changes
}

// useReducer: Clear state management
const initialState = {
  fields: { name: '', email: '', password: '', confirmPassword: '' },
  errors: {},
  touched: {},
  isSubmitting: false
};

function formReducer(state, action) {
  switch (action.type) {
    case 'CHANGE_FIELD':
      return {
        ...state,
        fields: {
          ...state.fields,
          [action.payload.name]: action.payload.value
        }
      };
    case 'TOUCH_FIELD':
      return {
        ...state,
        touched: { ...state.touched, [action.payload]: true }
      };
    case 'SET_ERRORS':
      return { ...state, errors: action.payload };
    case 'SUBMIT_START':
      return { ...state, isSubmitting: true };
    case 'SUBMIT_END':
      return { ...state, isSubmitting: false };
    default:
      return state;
  }
}

function Form() {
  const [state, dispatch] = useReducer(formReducer, initialState);
  
  // Much clearer!
  // All related state changes are in one function
}
```

---

## Complex State Logic

### Async Operations

```jsx
const ACTIONS = {
  FETCH_START: 'FETCH_START',
  FETCH_SUCCESS: 'FETCH_SUCCESS',
  FETCH_ERROR: 'FETCH_ERROR'
};

const initialState = {
  data: null,
  loading: false,
  error: null
};

function dataReducer(state, action) {
  switch (action.type) {
    case ACTIONS.FETCH_START:
      return {
        ...state,
        loading: true,
        error: null
      };
    
    case ACTIONS.FETCH_SUCCESS:
      return {
        data: action.payload,
        loading: false,
        error: null
      };
    
    case ACTIONS.FETCH_ERROR:
      return {
        ...state,
        loading: false,
        error: action.payload
      };
    
    default:
      return state;
  }
}

function DataFetcher() {
  const [state, dispatch] = useReducer(dataReducer, initialState);
  
  useEffect(() => {
    const fetchData = async () => {
      dispatch({ type: ACTIONS.FETCH_START });
      
      try {
        const response = await fetch('/api/data');
        const data = await response.json();
        dispatch({ type: ACTIONS.FETCH_SUCCESS, payload: data });
      } catch (error) {
        dispatch({ type: ACTIONS.FETCH_ERROR, payload: error.message });
      }
    };
    
    fetchData();
  }, []);
  
  if (state.loading) return <div>Loading...</div>;
  if (state.error) return <div>Error: {state.error}</div>;
  return <div>{JSON.stringify(state.data)}</div>;
}
```

### State Machines

```jsx
const STATES = {
  IDLE: 'IDLE',
  LOADING: 'LOADING',
  SUCCESS: 'SUCCESS',
  ERROR: 'ERROR'
};

const ACTIONS = {
  START: 'START',
  SUCCESS: 'SUCCESS',
  ERROR: 'ERROR',
  RESET: 'RESET'
};

function stateMachineReducer(state, action) {
  // Enforce valid state transitions
  switch (state) {
    case STATES.IDLE:
      if (action.type === ACTIONS.START) return STATES.LOADING;
      break;
    
    case STATES.LOADING:
      if (action.type === ACTIONS.SUCCESS) return STATES.SUCCESS;
      if (action.type === ACTIONS.ERROR) return STATES.ERROR;
      break;
    
    case STATES.SUCCESS:
      if (action.type === ACTIONS.RESET) return STATES.IDLE;
      break;
    
    case STATES.ERROR:
      if (action.type === ACTIONS.RESET) return STATES.IDLE;
      break;
  }
  
  return state;  // Invalid transition
}

// Only valid transitions allowed!
// Can't go from LOADING to LOADING
```

---

## Immer with useReducer

### Without Immer (Manual Immutability)

```jsx
const initialState = {
  user: {
    name: 'John',
    address: {
      street: '123 Main St',
      city: 'NYC'
    }
  },
  todos: [
    { id: 1, text: 'Learn React', done: false }
  ]
};

function reducer(state, action) {
  switch (action.type) {
    case 'UPDATE_USER_CITY':
      return {
        ...state,
        user: {
          ...state.user,
          address: {
            ...state.user.address,
            city: action.payload
          }
        }
      };  // Lots of spreading!
    
    case 'TOGGLE_TODO':
      return {
        ...state,
        todos: state.todos.map(todo =>
          todo.id === action.payload
            ? { ...todo, done: !todo.done }
            : todo
        )
      };  // Complex map
    
    default:
      return state;
  }
}
```

### With Immer (Mutate-Like Syntax)

```jsx
import produce from 'immer';

const initialState = {
  user: {
    name: 'John',
    address: {
      street: '123 Main St',
      city: 'NYC'
    }
  },
  todos: [
    { id: 1, text: 'Learn React', done: false }
  ]
};

function reducer(state, action) {
  return produce(state, draft => {
    switch (action.type) {
      case 'UPDATE_USER_CITY':
        draft.user.address.city = action.payload;  // Looks like mutation!
        break;
      
      case 'TOGGLE_TODO':
        const todo = draft.todos.find(t => t.id === action.payload);
        if (todo) {
          todo.done = !todo.done;  // Direct mutation syntax!
        }
        break;
    }
  });
}

// Much cleaner! Immer handles immutability
```

### Benefits of Immer

```javascript
// Without Immer: Deep nesting = complex
state.level1.level2.level3.level4.value = newValue;
// vs
return {
  ...state,
  level1: {
    ...state.level1,
    level2: {
      ...state.level2,
      level3: {
        ...state.level3,
        level4: { ...state.level4, value: newValue }
      }
    }
  }
};

// With Immer: Direct assignment
produce(state, draft => {
  draft.level1.level2.level3.level4.value = newValue;
});

// Much clearer!
```

---

## useReducer with useContext

### Combining for Global State

```jsx
const AppContext = createContext();

const ACTIONS = {
  SET_USER: 'SET_USER',
  SET_THEME: 'SET_THEME',
  ADD_NOTIFICATION: 'ADD_NOTIFICATION'
};

const initialState = {
  user: null,
  theme: 'light',
  notifications: []
};

function appReducer(state, action) {
  switch (action.type) {
    case ACTIONS.SET_USER:
      return { ...state, user: action.payload };
    
    case ACTIONS.SET_THEME:
      return { ...state, theme: action.payload };
    
    case ACTIONS.ADD_NOTIFICATION:
      return {
        ...state,
        notifications: [...state.notifications, action.payload]
      };
    
    default:
      return state;
  }
}

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  
  const value = {
    state,
    dispatch
  };
  
  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
};
```

### Usage

```jsx
function UserProfile() {
  const { state, dispatch } = useApp();
  
  const handleLoginClick = async () => {
    const userData = await fetchUser();
    dispatch({ type: ACTIONS.SET_USER, payload: userData });
  };
  
  if (!state.user) {
    return <button onClick={handleLoginClick}>Login</button>;
  }
  
  return <div>{state.user.name}</div>;
}

function ThemeToggle() {
  const { state, dispatch } = useApp();
  
  const toggleTheme = () => {
    const newTheme = state.theme === 'light' ? 'dark' : 'light';
    dispatch({ type: ACTIONS.SET_THEME, payload: newTheme });
  };
  
  return (
    <button onClick={toggleTheme}>
      Current theme: {state.theme}
    </button>
  );
}
```

---

## Dispatch Function Memoization

### The Problem

```jsx
function TodoProvider({ children }) {
  const [todos, dispatch] = useReducer(todoReducer, initialTodos);
  
  // dispatch is stable (doesn't change)
  // But we should memoize it anyway
  
  const value = {
    todos,
    dispatch
  };
  
  // value object changes every render!
  // Causes child components to re-render
  
  return (
    <TodoContext.Provider value={value}>
      {children}
    </TodoContext.Provider>
  );
}
```

### The Solution

```jsx
function TodoProvider({ children }) {
  const [todos, dispatch] = useReducer(todoReducer, initialTodos);
  
  // Memoize value to prevent unnecessary re-renders
  const value = useMemo(() => ({
    todos,
    dispatch
  }), [todos]);
  
  return (
    <TodoContext.Provider value={value}>
      {children}
    </TodoContext.Provider>
  );
}

// Or use useCallback for functions
const addTodo = useCallback(
  (text) => dispatch({ type: 'ADD_TODO', payload: text }),
  []  // dispatch never changes, safe to leave empty
);
```

---

## Common Patterns

### Pattern 1: Action Creators

```javascript
// Create functions that return actions
const addTodo = (text) => ({
  type: 'ADD_TODO',
  payload: text
});

const toggleTodo = (id) => ({
  type: 'TOGGLE_TODO',
  payload: id
});

const removeTodo = (id) => ({
  type: 'REMOVE_TODO',
  payload: id
});

// Usage
dispatch(addTodo('Learn React'));
dispatch(toggleTodo(1));
dispatch(removeTodo(2));

// Benefits:
// - Type-safe with TypeScript
// - Easier to refactor
// - Single source of truth for action structure
```

### Pattern 2: Async Thunks

```javascript
// Handle async operations in action creators
const fetchUser = (id) => async (dispatch) => {
  dispatch({ type: 'FETCH_START' });
  
  try {
    const response = await fetch(`/api/users/${id}`);
    const data = await response.json();
    dispatch({ type: 'FETCH_SUCCESS', payload: data });
  } catch (error) {
    dispatch({ type: 'FETCH_ERROR', payload: error });
  }
};

// Usage
dispatch(fetchUser(1));

// Better: Use hooks for async
useEffect(() => {
  (async () => {
    dispatch({ type: 'FETCH_START' });
    // ...
  })();
}, []);
```

### Pattern 3: Lazy Initialization

```jsx
// Use init function for complex initialization
const initialState = { todos: [] };

function init(initial) {
  // Can do complex setup here
  const stored = localStorage.getItem('todos');
  return {
    ...initial,
    todos: stored ? JSON.parse(stored) : []
  };
}

function TodoApp() {
  const [state, dispatch] = useReducer(
    todoReducer,
    initialState,
    init  // Init function called once
  );
  
  // state.todos initialized from localStorage!
}
```

---

## Common Pitfalls

### Pitfall 1: Mutating State

```jsx
// ❌ WRONG: Mutating state
function reducer(state, action) {
  switch (action.type) {
    case 'ADD':
      state.items.push(action.payload);  // Mutate!
      return state;  // Return same object
    
    case 'UPDATE':
      state.items[0].name = 'new';  // Mutate!
      return state;
  }
}

// ✅ CORRECT: Immutable updates
function reducer(state, action) {
  switch (action.type) {
    case 'ADD':
      return {
        ...state,
        items: [...state.items, action.payload]
      };
    
    case 'UPDATE':
      return {
        ...state,
        items: state.items.map((item, i) =>
          i === 0 ? { ...item, name: 'new' } : item
        )
      };
  }
}

// Or use Immer for cleaner syntax
```

### Pitfall 2: Forgetting Dispatch Function

```jsx
// ❌ WRONG: Calling reducer directly
function Component() {
  const [state, dispatch] = useReducer(myReducer, initial);
  
  // Don't call reducer directly!
  const newState = myReducer(state, action);
  
  return <div></div>;
}

// ✅ CORRECT: Use dispatch
function Component() {
  const [state, dispatch] = useReducer(myReducer, initial);
  
  // Always use dispatch
  dispatch(action);
  
  return <div></div>;
}
```

### Pitfall 3: Default Case Not Returning State

```jsx
// ❌ WRONG: Default case missing
function reducer(state, action) {
  switch (action.type) {
    case 'ACTION':
      return newState;
    // Missing default!
  }
}

// ✅ CORRECT: Handle all cases
function reducer(state, action) {
  switch (action.type) {
    case 'ACTION':
      return newState;
    default:
      return state;  // Or throw error
  }
}
```

---

## Interview Questions

### Q1: When should you use useReducer instead of useState?

```
Answer: Use useReducer when:
1. Multiple related state variables
2. Complex state transitions
3. State depends on previous state
4. Many related setters (pass single dispatch)
5. Easier to pass through Context

Use useState for:
- Simple independent state
- Single values
- Not many updates
```

### Q2: What's the difference between action and reducer?

```
Answer:
Action: Object describing what happened
- Has type (required)
- May have payload
- Example: { type: 'INCREMENT', payload: 5 }

Reducer: Pure function (state, action) => newState
- Takes current state and action
- Returns new state
- Pure: no side effects, no mutations
- Example: (state, action) => state + action.payload
```

### Q3: How do you handle async operations with useReducer?

```
Answer: Use useEffect for async, dispatch results:

useEffect(() => {
  (async () => {
    dispatch({ type: 'START' });
    try {
      const data = await fetch(...);
      dispatch({ type: 'SUCCESS', payload: data });
    } catch (err) {
      dispatch({ type: 'ERROR', payload: err });
    }
  })();
}, []);

Or use Immer for complex state updates.
Or combine with context for global state.
```

---

## Resources

- **useReducer Documentation:** https://react.dev/reference/react/useReducer
- **Reducer Pattern:** https://redux.js.org/understanding/thinking-in-redux
- **Immer Documentation:** https://immerjs.github.io/immer/
- **State Management Patterns:** https://kentcdodds.com/blog/application-state-management-with-react-hooks
- **useReducer vs useState:** https://react.dev/learn/extracting-state-logic-into-a-reducer

---

**Next:** [Part 3.6: useCallback & useMemo](./03-useCallback-and-useMemo.md) - Master React optimization hooks
