# Part 3.2: useState Hook

## What You'll Learn

- How useState works internally
- State updates are asynchronous
- Batching of multiple setState calls
- Lazy initialization
- Functional updates vs value updates
- Setting the same state
- State updates and re-renders
- Common pitfalls and how to avoid them
- Interview questions

---

## Table of Contents

1. [useState Fundamentals](#usestate-fundamentals)
2. [How useState Works](#how-usestate-works)
3. [Asynchronous State Updates](#asynchronous-state-updates)
4. [State Batching](#state-batching)
5. [Lazy Initialization](#lazy-initialization)
6. [Functional Updates](#functional-updates)
7. [Setting Same State](#setting-same-state)
8. [Objects and Arrays in State](#objects-and-arrays-in-state)
9. [State and Re-renders](#state-and-re-renders)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Interview Questions](#interview-questions)
13. [Resources](#resources)

---

## useState Fundamentals

### Basic Usage

```jsx
import { useState } from 'react';

function Counter() {
  // Destructure: [state, setState]
  const [count, setCount] = useState(0);
  //   ^state   ^setter    ^initial value
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  );
}

// useState returns an array with two elements:
// 1. Current state value
// 2. Function to update state
```

### Multiple State Variables

```jsx
function Form() {
  // Declare multiple state variables
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [age, setAge] = useState(0);
  const [subscribed, setSubscribed] = useState(false);
  
  return (
    <div>
      <input 
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Name"
      />
      <input 
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
      <input 
        type="number"
        value={age}
        onChange={(e) => setAge(Number(e.target.value))}
        placeholder="Age"
      />
      <input 
        type="checkbox"
        checked={subscribed}
        onChange={(e) => setSubscribed(e.target.checked)}
      />
    </div>
  );
}

// Or use useReducer for many related states
// (covered in Part 3.5)
```

### State Can Be Any Type

```jsx
function Example() {
  // String
  const [text, setText] = useState('hello');
  
  // Number
  const [count, setCount] = useState(0);
  
  // Boolean
  const [isOpen, setIsOpen] = useState(false);
  
  // Object
  const [user, setUser] = useState({ name: 'John', age: 30 });
  
  // Array
  const [items, setItems] = useState([1, 2, 3]);
  
  // null
  const [data, setData] = useState(null);
  
  // Any value!
  
  return <div></div>;
}
```

---

## How useState Works

### Internal Mechanism

```javascript
// Simplified version of how React implements useState

const componentHooks = [];
let hookIndex = 0;

function useState(initialValue) {
  const index = hookIndex;
  hookIndex++;
  
  // Initialize if first time
  if (componentHooks[index] === undefined) {
    componentHooks[index] = initialValue;
  }
  
  // Return current state and setter
  const setState = (newValue) => {
    componentHooks[index] = newValue;
    scheduleRender();  // Re-render
  };
  
  return [componentHooks[index], setState];
}

// This is why:
// 1. Hooks must be at top level (consistent index)
// 2. Can't call conditionally (index changes)
// 3. Order matters (index-based lookup)
```

### State Per Component Instance

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      {count}
      <button onClick={() => setCount(count + 1)}>+</button>
    </div>
  );
}

// In App:
function App() {
  return (
    <div>
      <Counter />
      <Counter />
      <Counter />
    </div>
  );
}

// Each Counter instance has its own state!
// First Counter: count = 0
// Second Counter: count = 0  
// Third Counter: count = 0

// Each maintains separate state!
// Updating one doesn't affect others

// This works because React:
// - Tracks component instance (fiber)
// - Stores hooks array in that fiber
// - Each instance has own hooks array
```

---

## Asynchronous State Updates

### State Updates Are Not Immediate

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  
  const handleClick = () => {
    setCount(count + 1);
    console.log(count);  // ❌ Logs old value!
    // Why? setState is asynchronous
  };
  
  return (
    <button onClick={handleClick}>
      Count: {count}
    </button>
  );
}

// Timeline:
// 1. count = 0
// 2. User clicks
// 3. handleClick runs
// 4. setCount(1) called (scheduled, not immediate)
// 5. console.log(count) runs → logs 0 (still old)
// 6. handleClick completes
// 7. React processes setState
// 8. Re-render with count = 1
```

### Why Asynchronous?

```javascript
// Multiple setState calls in a row:
function handleChange(e) {
  const value = e.target.value;
  
  setState1(value);      // Queued
  setState2(value);      // Queued
  setState3(value);      // Queued
  
  // If synchronous: 3 renders
  // If asynchronous: 1 render (batched)
  
  // React batches them together
  // More efficient!
}
```

### Reading New State After Update

```jsx
// ❌ Can't read new state immediately after setState
function Example() {
  const [count, setCount] = useState(0);
  
  const handleClick = () => {
    setCount(1);
    console.log(count);  // 0, not 1!
  };
  
  return <button onClick={handleClick}>Click</button>;
}

// ✅ Use useEffect to read new state
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    console.log(count);  // Logs new value!
  }, [count]);  // Runs when count changes
  
  return (
    <button onClick={() => setCount(count + 1)}>
      Count: {count}
    </button>
  );
}

// ✅ Or reference new value in same render
function Example() {
  const [count, setCount] = useState(0);
  
  const newCount = count + 1;
  
  const handleClick = () => {
    setCount(newCount);
    console.log(newCount);  // New value!
  };
  
  return <button onClick={handleClick}>Click</button>;
}
```

---

## State Batching

### Automatic Batching

```jsx
function Example() {
  const [count, setCount] = useState(0);
  const [text, setText] = useState('');
  
  const handleClick = () => {
    setCount(count + 1);
    setText('updated');
    // React 18: Both batched into one render!
  };
  
  return <button onClick={handleClick}>Update</button>;
}

// Render order:
// 1. User clicks
// 2. setCount queued
// 3. setText queued
// 4. (Both batched)
// 5. Single re-render with both updates
// 6. Browser paints once
```

### Async Batching (React 18)

```jsx
function Example() {
  const [count, setCount] = useState(0);
  const [text, setText] = useState('');
  
  const handleAsync = async () => {
    await fetchData();  // Wait for async
    
    setCount(count + 1);  // React 18: Batched!
    setText('done');      // React 18: Batched!
    
    // React 17 would NOT batch after await
    // React 18 batches automatically
  };
  
  return <button onClick={handleAsync}>Async</button>;
}
```

### Manual Batching If Needed

```jsx
import { flushSync } from 'react-dom';

function Example() {
  const [count, setCount] = useState(0);
  const [text, setText] = useState('');
  
  const handleClick = () => {
    // Force render immediately after count update
    flushSync(() => {
      setCount(count + 1);
    });
    // count is updated and rendered here
    
    // This batches
    setText('done');
  };
  
  return <button onClick={handleClick}>Click</button>;
}

// When to use flushSync?
// - Rare! Usually batching is better
// - Reading DOM values after update
// - Integrating with non-React code
// - Performance testing
```

---

## Lazy Initialization

### Problem: Expensive Initialization

```jsx
function Component() {
  // ❌ This runs EVERY render!
  const initialState = expensiveCalculation();
  const [state, setState] = useState(initialState);
  
  return <div>{state}</div>;
}

// Timeline:
// Render 1: expensiveCalculation() runs, returns value, useState(value)
// Render 2: expensiveCalculation() runs again (wasted!), useState ignores it
// Render 3: expensiveCalculation() runs again (wasted!)
//
// expensiveCalculation() runs even though only used for initial value!
```

### Solution: Lazy Initialization

```jsx
function Component() {
  // ✅ This runs ONCE on mount!
  const [state, setState] = useState(() => {
    return expensiveCalculation();
  });
  
  return <div>{state}</div>;
}

// Timeline:
// Render 1: Callback runs → expensiveCalculation() → value → state initialized
// Render 2: Callback skipped (already initialized)
// Render 3: Callback skipped (already initialized)
//
// expensiveCalculation() runs only once!
```

### Real Example: LocalStorage

```jsx
function TodoList() {
  // ❌ Bad: Reads localStorage every render
  const [todos, setTodos] = useState(
    JSON.parse(localStorage.getItem('todos') || '[]')
  );
  
  return <div>{todos}</div>;
}

// localStorage.getItem runs every render (wasteful)
// JSON.parse runs every render (wasteful)

// ✅ Good: Lazy initialization
function TodoList() {
  const [todos, setTodos] = useState(() => {
    const stored = localStorage.getItem('todos');
    return stored ? JSON.parse(stored) : [];
  });
  
  return <div>{todos}</div>;
}

// Initialization runs once
// Efficient!
```

### When to Use Lazy Init

```jsx
// Use lazy init when:
// 1. Initialization is expensive
// 2. Initialization depends on props
// 3. Initialization depends on data

// ✅ With props
function Component({ initialValue }) {
  const [state, setState] = useState(() => {
    return calculateInitialState(initialValue);
  });
  
  return <div>{state}</div>;
}

// ✅ With API call (not really, use effect instead)
function Component({ userId }) {
  const [user, setUser] = useState(() => {
    // Actually, use useEffect for async!
    // But lazy init for sync initialization
    return getUserFromCache(userId);
  });
  
  return <div>{user}</div>;
}
```

---

## Functional Updates

### Value vs Functional Update

```jsx
// Value update
const [count, setCount] = useState(0);
setCount(1);           // Set to 1
setCount(2);           // Set to 2

// Functional update
const [count, setCount] = useState(0);
setCount(c => c + 1);  // Add 1
setCount(c => c + 1);  // Add 1 again
```

### When Batching Matters

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  
  const handleClick = () => {
    // Value updates (batched into one render)
    setCount(count + 1);
    setCount(count + 1);
    setCount(count + 1);
    // Only counts to 1, all use same count value
  };
  
  return (
    <div>
      {count}
      <button onClick={handleClick}>Click</button>
    </div>
  );
}

// Better: Functional update
function Counter() {
  const [count, setCount] = useState(0);
  
  const handleClick = () => {
    setCount(c => c + 1);
    setCount(c => c + 1);
    setCount(c => c + 1);
    // Counts to 3!
    // Each update sees result of previous
  };
  
  return (
    <div>
      {count}
      <button onClick={handleClick}>Click</button>
    </div>
  );
}
```

### Functional Update Timing

```jsx
function Example() {
  const [count, setCount] = useState(0);
  
  const handleClick = () => {
    // Functional update queued
    setCount(c => {
      console.log(`Current: ${c}`);
      return c + 1;
    });
    
    // Callback still receives old count
    console.log(`Still: ${count}`);
  };
  
  return <button onClick={handleClick}>Click</button>;
}

// Output:
// "Still: 0"     (logged immediately)
// "Current: 0"   (logged during render)
// Re-render: count = 1
```

### Use Cases for Functional Updates

```jsx
// ✅ Use functional update when:
// - You need previous value
// - You're doing calculation on current state
// - You want to avoid dependency on specific state

function Counter() {
  const [count, setCount] = useState(0);
  
  // ✅ Good: Functional update, no deps needed
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(c => c + 1);  // Always gets current count
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);  // Empty deps! count not needed
}

// ✅ Good: Form updates
function Form() {
  const [formData, setFormData] = useState({ name: '', email: '' });
  
  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };
  
  return (
    <div>
      <input 
        onChange={(e) => handleChange('name', e.target.value)}
      />
    </div>
  );
}
```

---

## Setting Same State

### What Happens?

```jsx
function Example() {
  const [count, setCount] = useState(0);
  
  const handleClick = () => {
    setCount(0);  // Setting same value
    // What happens?
  };
  
  return (
    <div>
      {count}
      <button onClick={handleClick}>Click</button>
    </div>
  );
}

// React compares old and new:
// Old: 0
// New: 0
// Same? Yes
// Result: No re-render
// Component doesn't re-render!
```

### Object Identity Matters

```jsx
function Example() {
  const [state, setState] = useState({ count: 0 });
  
  const handleClick = () => {
    // ❌ Creates new object with same data
    setState({ count: 0 });
    // Always re-renders (new object)
  };
  
  return <button onClick={handleClick}>Click</button>;
}

// React compares by Object.is():
// { count: 0 } !== { count: 0 }
// They're different objects!
// Re-renders even though data is same

// ✅ Correct approach
function Example() {
  const [state, setState] = useState({ count: 0 });
  
  const handleClick = () => {
    setState(prev => {
      // Only update if changed
      if (prev.count === 0) {
        return prev;  // Same object, no re-render
      }
      return { count: prev.count + 1 };
    });
  };
  
  return <button onClick={handleClick}>Click</button>;
}
```

---

## Objects and Arrays in State

### Why Immutability Matters

```jsx
// ❌ WRONG: Mutating state directly
function Example() {
  const [user, setUser] = useState({ name: 'John', age: 30 });
  
  const updateName = () => {
    user.name = 'Jane';  // Mutate directly
    setUser(user);       // Set same object
    // Object.is(user, user) = true
    // No re-render!
  };
  
  return <button onClick={updateName}>{user.name}</button>;
  // Still shows "John" even after "update"
}

// ✅ CORRECT: Create new object
function Example() {
  const [user, setUser] = useState({ name: 'John', age: 30 });
  
  const updateName = () => {
    setUser({
      ...user,
      name: 'Jane'  // New object with updated field
    });
    // New object! Different reference
    // Re-renders!
  };
  
  return <button onClick={updateName}>{user.name}</button>;
}
```

### Array Updates

```jsx
function TodoList() {
  const [todos, setTodos] = useState([
    { id: 1, text: 'Learn React' },
    { id: 2, text: 'Learn Hooks' }
  ]);
  
  // ❌ WRONG: Mutating array
  const addTodo = (text) => {
    todos.push({ id: 3, text });  // Mutates array
    setTodos(todos);  // No re-render!
  };
  
  // ✅ CORRECT: Create new array
  const addTodo = (text) => {
    setTodos([...todos, { id: 3, text }]);  // New array
  };
  
  // ✅ CORRECT: Functional update
  const addTodo = (text) => {
    setTodos(prev => [...prev, { id: 3, text }]);
  };
  
  // ✅ CORRECT: Using array methods
  const addTodo = (text) => {
    setTodos(prev => prev.concat({ id: 3, text }));
  };
  
  // Removing
  const removeTodo = (id) => {
    setTodos(prev => prev.filter(t => t.id !== id));
  };
  
  // Updating
  const updateTodo = (id, text) => {
    setTodos(prev => 
      prev.map(t => t.id === id ? { ...t, text } : t)
    );
  };
  
  return <div></div>;
}
```

### Immer Pattern (Easier Mutation)

```jsx
// Using immer library for easier immutable updates
import produce from 'immer';

function TodoList() {
  const [todos, setTodos] = useState([
    { id: 1, text: 'Learn React' },
    { id: 2, text: 'Learn Hooks' }
  ]);
  
  // Write like you're mutating, Immer handles immutability
  const addTodo = (text) => {
    setTodos(produce(draft => {
      draft.push({ id: 3, text });  // Looks like mutation
    }));
    // But creates new array under the hood!
  };
  
  const updateTodo = (id, text) => {
    setTodos(produce(draft => {
      const todo = draft.find(t => t.id === id);
      if (todo) {
        todo.text = text;  // Looks like mutation
      }
    }));
  };
  
  return <div></div>;
}
```

---

## State and Re-renders

### When Components Re-render

```jsx
function Parent() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <p>{count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
      <Child />
    </div>
  );
}

function Child() {
  console.log('Child renders');
  return <div>Child</div>;
}

// Timeline:
// 1. Mount: Parent renders, Child renders
// 2. Click button: setCount(1)
// 3. Parent re-renders with count=1
// 4. Child ALSO re-renders (parent renders → all children re-render)
// 5. Console logs "Child renders"

// Child doesn't get count prop, but still re-renders
// This is normal React behavior
```

### Optimization: React.memo

```jsx
function Parent() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <p>{count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
      <Child />
    </div>
  );
}

// ✅ Memoize Child (only re-renders if props change)
const Child = React.memo(function Child() {
  console.log('Child renders');
  return <div>Child</div>;
});

// Timeline:
// 1. Mount: Parent renders, Child renders
// 2. Click button: setCount(1)
// 3. Parent re-renders with count=1
// 4. React checks if Child's props changed
// 5. Props didn't change (no props passed)
// 6. Child DOESN'T re-render
// 7. Console doesn't log "Child renders"
```

---

## Common Patterns & Best Practices

### Pattern 1: Derived State

```jsx
// ❌ WRONG: Storing derived value in state
function Component({ price }) {
  const [discountedPrice, setDiscountedPrice] = useState(null);
  
  useEffect(() => {
    setDiscountedPrice(price * 0.9);
  }, [price]);
  
  return <div>{discountedPrice}</div>;
}

// ✅ CORRECT: Calculate derived value
function Component({ price }) {
  const discountedPrice = price * 0.9;
  
  return <div>{discountedPrice}</div>;
}

// Rule: If you can calculate it, don't store it
```

### Pattern 2: Controlled Components

```jsx
// ✅ GOOD: Controlled input
function SearchForm() {
  const [query, setQuery] = useState('');
  
  const handleChange = (e) => {
    setQuery(e.target.value);  // Update state
  };
  
  return (
    <div>
      <input 
        value={query}      // Controlled by state
        onChange={handleChange}
      />
      <p>Searching: {query}</p>
    </div>
  );
}

// Value is always in sync with state
// Can easily modify, validate, transform input
```

### Pattern 3: State Setter Callback Workaround

```jsx
// You can't do callback in setState like in class components
// But you can use useEffect:

function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    // Runs after count changes
    console.log('Count changed to', count);
  }, [count]);  // ← Depends on count
  
  return (
    <button onClick={() => setCount(count + 1)}>
      {count}
    </button>
  );
}

// Or use useCallback:
function Example() {
  const [count, setCount] = useState(0);
  
  const handleClick = useCallback(() => {
    const newCount = count + 1;
    setCount(newCount);
    console.log('Count changed to', newCount);  // Can access new value
  }, [count]);
  
  return <button onClick={handleClick}>{count}</button>;
}
```

---

## Common Pitfalls

### Pitfall 1: Stale State Closure

```jsx
// ❌ WRONG: Stale state
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(count + 1);  // Stale count!
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);  // Missing count!
}

// count is always 0 in the closure

// ✅ CORRECT: Functional update
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(c => c + 1);  // Always current
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);  // Empty deps OK with functional update
}
```

### Pitfall 2: Mutating State

```jsx
// ❌ WRONG: Mutating directly
function List() {
  const [items, setItems] = useState([1, 2, 3]);
  
  const addItem = () => {
    items.push(4);      // Mutate array
    setItems(items);    // No re-render!
  };
  
  return <button onClick={addItem}>{items}</button>;
}

// ✅ CORRECT: Create new array
function List() {
  const [items, setItems] = useState([1, 2, 3]);
  
  const addItem = () => {
    setItems([...items, 4]);  // New array
  };
  
  return <button onClick={addItem}>{items}</button>;
}
```

### Pitfall 3: Initializing with Function Parameter

```jsx
// ❌ WRONG: Passing function directly (won't call it)
function Component() {
  const [count, setCount] = useState(calculateInitial());
  // calculateInitial() runs immediately! Not what we want
  
  return <div>{count}</div>;
}

// ❌ WRONG: This ALSO runs it
function Component() {
  const [count, setCount] = useState(calculateInitial());
  // Still runs immediately
  
  return <div>{count}</div>;
}

// ✅ CORRECT: Pass function itself
function Component() {
  const [count, setCount] = useState(calculateInitial);
  // calculateInitial is called lazily, only on mount
  
  return <div>{count}</div>;
}

// Or with arrow function for complex init:
function Component() {
  const [count, setCount] = useState(() => {
    return calculateInitial();
  });
  
  return <div>{count}</div>;
}
```

---

## Interview Questions

### Q1: What's the difference between value and functional updates?

```javascript
// Value update: all use same state value
setCount(count + 1);  // Uses count from closure
setCount(count + 1);  // Uses count from closure
setCount(count + 1);  // Uses count from closure
// All see same count, only counts to 1

// Functional update: chain updates
setCount(c => c + 1);  // Uses prev result
setCount(c => c + 1);  // Uses prev result
setCount(c => c + 1);  // Uses prev result
// Counts to 3, each update based on previous
```

### Q2: Why are state updates asynchronous?

```
Answer: For performance through batching.
Multiple setState calls get batched into single render.
If synchronous: each setState = new render (slow).
If asynchronous: batch updates = one render (fast).

Also allows React to schedule updates by priority.
High priority updates render first.
```

### Q3: How do you handle dependencies in state updates?

```javascript
// Use functional update when you need previous state:
setCount(c => c + 1);

// Use dependency array in useEffect to sync external:
useEffect(() => {
  // Runs when count changes
}, [count]);

// Use lazy initialization for expensive setup:
useState(() => calculateInitial());
```

### Q4: When would you use useReducer instead of useState?

```
Answer: Use useReducer when:
- Multiple state variables are related
- Complex state transitions
- Logic needs to be extracted
- Multiple setState calls that should batch

Use useState for:
- Simple state (string, number, boolean)
- Independent state variables
```

---

## Resources

- **useState Reference:** https://react.dev/reference/react/useState
- **Queueing State:** https://react.dev/learn/queueing-a-series-of-state-updates
- **Updating State:** https://react.dev/learn/state-a-components-memory
- **Batching Explanation:** https://react.dev/blog/2022/03/08/react-18-is-released
- **React DevTools:** https://react-devtools-tutorial.vercel.app/

---

**Next:** [Part 3.3: useEffect Hook](./03-useEffect-hook.md) - Master the most complex and important hook
