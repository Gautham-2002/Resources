# Part 3.1: Hook Rules & Principles

## What You'll Learn

- The Rules of Hooks and why they exist
- Call order and how React tracks hooks
- Closures and scope in hooks
- Why hooks must be at top level
- Hook dependency arrays
- Stale closures and how to fix them
- ESLint rules for hooks
- Common misconceptions
- Hook design principles

---

## Table of Contents

1. [What Are Hooks?](#what-are-hooks)
2. [The Rules of Hooks](#the-rules-of-hooks)
3. [Why These Rules Exist](#why-these-rules-exist)
4. [Call Order and Hook Tracking](#call-order-and-hook-tracking)
5. [Closures in Hooks](#closures-in-hooks)
6. [Dependency Arrays](#dependency-arrays)
7. [Stale Closures](#stale-closures)
8. [ESLint Rules](#eslint-rules)
9. [Hook Design Principles](#hook-design-principles)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Resources](#resources)

---

## What Are Hooks?

### Definition

Hooks are **functions that "hook into" React state and lifecycle features**.

```javascript
// Traditional class component
class Counter extends React.Component {
  constructor(props) {
    super(props);
    this.state = { count: 0 };
  }
  
  render() {
    return (
      <button onClick={() => this.setState({ count: this.state.count + 1 })}>
        Count: {this.state.count}
      </button>
    );
  }
}

// Hooks version (much simpler!)
function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <button onClick={() => setCount(count + 1)}>
      Count: {count}
    </button>
  );
}
```

### Why Hooks?

Before hooks, you had to:
1. Use class components for state
2. Copy lifecycle logic in multiple places
3. Deal with `this` binding
4. Couldn't reuse stateful logic between components

Hooks solve all these problems!

### Built-in Hooks

React provides several built-in hooks:

```javascript
// State
useState()        // Manage state
useReducer()      // Complex state logic

// Effects
useEffect()       // Side effects
useLayoutEffect() // Synchronous effects

// Context
useContext()      // Access context values

// Optimization
useMemo()         // Memoize expensive calculations
useCallback()     // Memoize functions
useTransition()   // Mark updates as non-blocking
useDeferredValue() // Defer value updates

// References
useRef()          // Persistent object reference

// Debugging
useDebugValue()   // DevTools display

// Advanced
useReducer()      // Complex state
useId()           // Unique IDs
useImperativeHandle() // Customize ref behavior
```

---

## The Rules of Hooks

### Rule 1: Only Call at Top Level

**Don't call hooks inside conditions, loops, or nested functions.**

```jsx
// ❌ WRONG: Conditional hook
function Component() {
  if (someCondition) {
    const [state, setState] = useState(0);  // ERROR!
  }
  
  return <div></div>;
}

// ✅ CORRECT: Top level
function Component() {
  const [state, setState] = useState(0);  // ✓
  
  if (someCondition) {
    // Use state here, don't declare here
  }
  
  return <div></div>;
}

// ❌ WRONG: Loop hook
function Component() {
  const items = [];
  
  for (let i = 0; i < 5; i++) {
    const [count, setCount] = useState(0);  // ERROR!
  }
  
  return <div></div>;
}

// ✅ CORRECT: Use separate component for loop
function ItemList() {
  const items = [1, 2, 3, 4, 5];
  
  return (
    <div>
      {items.map(item => (
        <Item key={item} />  // Hooks in Item component
      ))}
    </div>
  );
}

function Item() {
  const [count, setCount] = useState(0);  // ✓
  return <div>{count}</div>;
}
```

### Rule 2: Only Call from React Functions

**Call hooks from React function components or custom hooks.**

```jsx
// ❌ WRONG: Regular function (not a component)
function regularFunction() {
  const [state, setState] = useState(0);  // ERROR!
  return state;
}

// ❌ WRONG: Class component
class MyComponent extends React.Component {
  render() {
    const [state, setState] = useState(0);  // ERROR!
    return <div></div>;
  }
}

// ❌ WRONG: Event handler
function Component() {
  const handleClick = () => {
    const [state, setState] = useState(0);  // ERROR!
  };
  
  return <button onClick={handleClick}>Click</button>;
}

// ✅ CORRECT: React function component
function Component() {
  const [state, setState] = useState(0);  // ✓
  return <div>{state}</div>;
}

// ✅ CORRECT: Custom hook
function useCustomState(initial) {
  const [state, setState] = useState(initial);  // ✓
  return [state, setState];
}
```

---

## Why These Rules Exist

### Rule 1: Call Order

React identifies hooks by **call order**, not by name.

```javascript
// Render 1: Call order
function Component() {
  const [count, setCount] = useState(0);        // Hook index 0
  const [text, setText] = useState('');          // Hook index 1
  useEffect(() => { ... }, []);                  // Hook index 2
  
  return <div>{count} {text}</div>;
}

// React remembers:
// Index 0: count state
// Index 1: text state  
// Index 2: effect

// Render 2: Same call order
function Component() {
  const [count, setCount] = useState(0);        // Hook index 0 ✓
  const [text, setText] = useState('');          // Hook index 1 ✓
  useEffect(() => { ... }, []);                  // Hook index 2 ✓
  
  // Everything matches up!
}

// Render 3: BROKEN call order (conditional)
function Component() {
  if (someCondition) {
    const [count, setCount] = useState(0);      // Hook index 0 (sometimes)
  }
  const [text, setText] = useState('');          // Hook index 0 or 1?
  
  // Indices don't match! count state might go to text!
  // BROKEN!
}
```

### Call Order Problem Explained

```jsx
function Component({ showEmail }) {
  if (showEmail) {
    const [email, setEmail] = useState('');  // Hook 0 (conditional!)
  }
  const [name, setName] = useState('');       // Hook 0 or 1?
}

// Scenario 1: showEmail = true
// Render: Hook 0 (email), Hook 1 (name)
// React stores:
// - Index 0: email state
// - Index 1: name state

// Scenario 2: showEmail = false
// Render: Hook 0 (name only!)
// React thinks:
// - Index 0: name (but it's expecting email!)
// Wrong state assigned!

// Result: name gets email's state, bugs everywhere!
```

### Why Top-Level?

Because React needs consistent hook indices across renders:

```javascript
// React internally:
function Component() {
  const hooks = [];  // Array of hooks
  let hookIndex = 0;
  
  // When useState called
  const state = hooks[hookIndex];
  hookIndex++;
  
  // When useEffect called
  const effect = hooks[hookIndex];
  hookIndex++;
  
  // If you use conditional hooks, hookIndex gets messed up!
}
```

---

## Call Order and Hook Tracking

### How React Tracks Hooks

```javascript
// Component function with hooks
function Counter() {
  const [count, setCount] = useState(0);        // Slot 0
  const [text, setText] = useState('hello');    // Slot 1
  
  useEffect(() => {                             // Slot 2
    console.log('Effect');
  }, [count]);
  
  return <div>{count} {text}</div>;
}

// React creates fiber with hooks array:
const fiber = {
  component: Counter,
  hooks: [
    { state: 0, queue: [] },           // Slot 0: count
    { state: 'hello', queue: [] },     // Slot 1: text
    { callback: ..., deps: [0] }       // Slot 2: effect
  ]
};

// Every render, React:
// 1. Calls Counter()
// 2. Tracks hook calls by index
// 3. Returns state from slots
// 4. Executes effects

// Key: Slots must be consistent!
// Can't skip a slot, can't add conditionally
```

### Stable Hook Indices

```jsx
// ✅ GOOD: Same hooks, same order
function Component() {
  const [count, setCount] = useState(0);      // Index 0
  const [text, setText] = useState('');        // Index 1
  
  useEffect(() => {                            // Index 2
    // Effects here
  }, [count]);
  
  return <div>{count} {text}</div>;
}

// Every render: Index 0, 1, 2 in same order
// React knows which state is which

// ❌ BAD: Conditional hooks
function Component({ toggle }) {
  if (toggle) {
    const [extra, setExtra] = useState(null);  // Index 0 (sometimes!)
  }
  
  const [count, setCount] = useState(0);       // Index 0 or 1?
  const [text, setText] = useState('');        // Index 1 or 2?
  
  // Indices change! State gets mixed up!
}
```

---

## Closures in Hooks

### Understanding Closures

A closure is **a function that remembers variables from its outer scope**.

```javascript
function outer() {
  const message = 'Hello';  // Outer scope
  
  function inner() {
    console.log(message);   // Accesses message from outer scope
  }
  
  return inner;
}

const func = outer();
func();  // Logs 'Hello'
// Closure remembers 'message'
```

### Closures in Hooks

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  
  const handleClick = () => {
    // handleClick closes over count
    console.log(count);  // Has access to count
    setCount(count + 1);
  };
  
  return <button onClick={handleClick}>Count: {count}</button>;
}

// Render 1: count = 0
// handleClick closes over count = 0
// Click → console.log(0), setCount(1)

// Render 2: count = 1
// New handleClick created (closes over count = 1)
// Click → console.log(1), setCount(2)

// Each render, new closure with new count value!
```

### Why Closures Matter

```jsx
function Example() {
  const [count, setCount] = useState(0);
  
  // This effect closes over count
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log(`Count is ${count}`);  // Closes over count
    }, 3000);
    
    return () => clearTimeout(timer);
  }, []);  // ← NO dependency! Missing count!
}

// Render 1: count = 0
// useEffect runs once
// Timer created, closes over count = 0

// User clicks button: count = 1
// useEffect doesn't run (empty deps)
// Timer still has count = 0

// 3 seconds later:
// "Count is 0"  ← Wrong! Should be 1!
// This is a stale closure!
```

### Fixing Stale Closures

```jsx
// Solution 1: Add dependency
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log(`Count is ${count}`);
    }, 3000);
    
    return () => clearTimeout(timer);
  }, [count]);  // ← Include count!
}

// Now when count changes:
// Effect re-runs
// Timer cleared
// New timer with new count
// Correct!

// Solution 2: Use function update
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setCount(c => {
        console.log(`Count is ${c}`);  // Always fresh!
        return c;
      });
    }, 3000);
    
    return () => clearTimeout(timer);
  }, []);  // ← Can omit dependency!
}

// setCount provides current count
// No stale closure!
```

---

## Dependency Arrays

### What is a Dependency Array?

A dependency array tells React **when to re-run the effect**.

```javascript
// No dependency array: Run every render
useEffect(() => {
  console.log('Runs every render');
});

// Empty dependency array: Run once (mount only)
useEffect(() => {
  console.log('Runs once on mount');
}, []);

// With dependencies: Run when dependencies change
useEffect(() => {
  console.log('Runs when count changes');
}, [count]);

// Multiple dependencies: Run when any changes
useEffect(() => {
  console.log('Runs when count or name changes');
}, [count, name]);
```

### Dependency Comparison

```javascript
// React compares dependencies using Object.is()

// Render 1: [count, name] = [0, 'Alice']
// Effect runs

// Render 2: [count, name] = [0, 'Alice']
// Object.is(0, 0) = true ✓
// Object.is('Alice', 'Alice') = true ✓
// Both deps same → Effect doesn't run

// Render 3: [count, name] = [1, 'Alice']
// Object.is(1, 0) = false
// At least one dep changed → Effect runs

// Render 4: [count, name] = [1, 'Bob']
// Object.is('Bob', 'Alice') = false
// Dependency changed → Effect runs
```

### Missing Dependencies

```jsx
// ❌ WRONG: Missing dependency
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    // Uses count but doesn't list it!
    console.log(count);
  }, []);  // ← Missing count!
}

// Effect runs once
// Closes over count = 0
// If count changes to 1, effect doesn't re-run
// Still logs 0

// ✅ CORRECT: Include dependency
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    console.log(count);
  }, [count]);  // ← Include count!
}

// Effect runs when count changes
// Logs current count each time
```

### ESLint Help

```javascript
// Install: npm install --save-dev eslint-plugin-react-hooks

// .eslintrc.js
{
  "plugins": ["react-hooks"],
  "rules": {
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn"  // ← Warns about missing deps
  }
}

// ESLint helps catch:
// ❌ function ExampleComponent() {
//   const [count, setCount] = useState(0);
//   
//   useEffect(() => {
//     console.log(count);
//   }, []);  // ← ESLint warns: "count is missing"
// }
```

---

## Stale Closures

### What is Stale Closure?

Stale closure is when **a function captures old state value and uses it later**.

```jsx
function Example() {
  const [count, setCount] = useState(0);
  
  const handleClick = () => {
    // handleClick closes over count = 0
    setTimeout(() => {
      alert(count);  // Still 0 after 3 seconds!
    }, 3000);
  };
  
  return (
    <div>
      <p>{count}</p>
      <button onClick={handleClick}>Click me</button>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}

// Timeline:
// 1. Render 1: count = 0
// 2. User clicks "Click me" button
//    - handleClick created (closes over count = 0)
//    - setTimeout queues alert
// 3. User clicks "Increment" button 5 times
//    - count = 5
//    - New handleClick created (closes over count = 5)
// 4. 3 seconds later:
//    - alert(0)  ← STALE! Should be 5!
//    - This is the first handleClick's closure
```

### Fixing Stale Closures

```jsx
// Solution 1: useEffect with proper dependencies
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const handleClick = () => {
      setTimeout(() => {
        console.log(count);  // Current count
      }, 3000);
    };
    
    element.addEventListener('click', handleClick);
    return () => element.removeEventListener('click', handleClick);
  }, [count]);  // Re-run when count changes
}

// Solution 2: Function update pattern
function Example() {
  const [count, setCount] = useState(0);
  
  const handleClick = () => {
    setCount(currentCount => {
      // currentCount is always fresh!
      setTimeout(() => {
        console.log(currentCount);
      }, 3000);
      return currentCount;
    });
  };
  
  return <button onClick={handleClick}>Click</button>;
}

// Solution 3: useRef for latest value
function Example() {
  const [count, setCount] = useState(0);
  const countRef = useRef(count);
  
  useEffect(() => {
    countRef.current = count;  // Always updated
  }, [count]);
  
  const handleClick = () => {
    setTimeout(() => {
      console.log(countRef.current);  // Always fresh!
    }, 3000);
  };
  
  return <button onClick={handleClick}>Click</button>;
}
```

---

## ESLint Rules

### react-hooks/rules-of-hooks

```javascript
// Checks for Rule 1 and Rule 2

// ❌ Error: Hook inside condition
function Component() {
  if (condition) {
    const [state, setState] = useState(0);
    // Error: React Hook "useState" is called conditionally
  }
}

// ❌ Error: Hook inside event handler
function Component() {
  const handleClick = () => {
    const [state, setState] = useState(0);
    // Error: React Hook "useState" is called in a function that is neither a React function component nor a custom React Hook
  };
}

// ✅ Correct: Hook at top level
function Component() {
  const [state, setState] = useState(0);  // ✓
  
  const handleClick = () => {
    setState(state + 1);  // Using hook's result is fine
  };
}
```

### react-hooks/exhaustive-deps

```javascript
// Checks for missing dependencies in useEffect

// ❌ Warning: Missing dependency
function Component() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    console.log(count);  // Uses count
  }, []);  // Warning: missing count in deps array
}

// ✅ Correct: All dependencies listed
function Component() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    console.log(count);
  }, [count]);  // ✓ count included
}

// Cases where you might suppress warning:
function Component() {
  const [count, setCount] = useState(0);
  
  // setCount doesn't need to be in deps
  // It's guaranteed stable
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(c => c + 1);  // Safe without dependency
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);  // OK: setCount is stable function
}
```

---

## Hook Design Principles

### Principle 1: Hooks Are Composable

```jsx
// Hooks can call other hooks
function useFormInput(initialValue) {
  const [value, setValue] = useState(initialValue);      // ✓ useState
  
  useEffect(() => {                                       // ✓ useEffect
    console.log('Value changed:', value);
  }, [value]);
  
  return { value, setValue };  // Return state and setter
}

function useForm(initialState) {
  const fields = {};
  
  for (const [key, value] of Object.entries(initialState)) {
    fields[key] = useFormInput(value);  // ✓ Custom hook
  }
  
  return fields;
}

// Hooks calling hooks = composable!
```

### Principle 2: Hooks Extract Logic

```jsx
// Before: Logic scattered in component
function Component() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(c => c + 1);
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);
  
  return <div>{count}</div>;
}

// After: Logic extracted to hook
function useCounter() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(c => c + 1);
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);
  
  return count;
}

function Component() {
  const count = useCounter();
  return <div>{count}</div>;
}

// Much cleaner!
```

### Principle 3: Hooks Are Functions

```javascript
// Hooks follow normal JavaScript function rules

// ✓ Hooks can return anything
function useValue() {
  const [value, setValue] = useState(0);
  return value;  // Return single value
}

function useState() {
  const [state, setState] = useState(0);
  return [state, setState];  // Return array
}

function useObject() {
  const [data, setData] = useState(null);
  return { data, setData };  // Return object
}

// ✓ Hooks can take parameters
function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(() => {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : initialValue;
  });
  
  return [value, setValue];
}

// ✓ Hooks can use other hooks
function useFetch(url) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    fetch(url)
      .then(r => r.json())
      .then(setData)
      .catch(setError);
  }, [url]);
  
  return [data, error];
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Proper Dependency Management

```jsx
// ✅ GOOD: Complete dependencies
function Example() {
  const [count, setCount] = useState(0);
  const [text, setText] = useState('');
  
  useEffect(() => {
    // Uses both count and text
    const message = `${text}: ${count}`;
    console.log(message);
  }, [count, text]);  // Both included
}

// ✅ GOOD: Function update for setState
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(c => c + 1);  // No dependency needed!
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);
}
```

### Pattern 2: Hooks at Top Level

```jsx
// ✅ GOOD: All hooks at top
function Component({ showEmail }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  
  // Use state conditionally, not declare conditionally
  if (!showEmail) {
    // Can use email here, just don't initialize here
  }
  
  return <div>{name}</div>;
}

// ❌ WRONG: Hook inside condition
function Component({ showEmail }) {
  if (showEmail) {
    const [email, setEmail] = useState('');  // ERROR!
  }
  
  return <div></div>;
}
```

### Pattern 3: useCallback for Callbacks

```jsx
// ✅ GOOD: Memoized callback
function Example({ onUpdate }) {
  const [count, setCount] = useState(0);
  
  const handleUpdate = useCallback(() => {
    onUpdate(count);
  }, [count, onUpdate]);
  
  return <button onClick={handleUpdate}>Update</button>;
}
```

---

## Common Pitfalls

### Pitfall 1: Forgetting Dependencies

```jsx
// ❌ WRONG: Missing dependency
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      console.log(count);  // Stale count!
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);  // Missing count
}

// ✅ CORRECT: Include dependency
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      console.log(count);
    }, 1000);
    
    return () => clearInterval(timer);
  }, [count]);  // Include count
}
```

### Pitfall 2: Conditional Hooks

```jsx
// ❌ WRONG: Conditional call order
function Example({ showCounter }) {
  if (showCounter) {
    const [count, setCount] = useState(0);
  }
  const [text, setText] = useState('');
  
  // When showCounter changes, hook indices get messed up!
}

// ✅ CORRECT: Always call
function Example({ showCounter }) {
  const [count, setCount] = useState(0);
  const [text, setText] = useState('');
  
  if (!showCounter) {
    return <div>{text}</div>;  // Don't use count
  }
  
  return <div>{count} {text}</div>;
}
```

### Pitfall 3: Hooks in Loops

```jsx
// ❌ WRONG: Hook inside loop
function Example({ items }) {
  return (
    <div>
      {items.map(item => {
        const [count, setCount] = useState(0);  // ERROR!
        return <div>{count}</div>;
      })}
    </div>
  );
}

// ✅ CORRECT: Component for each item
function Example({ items }) {
  return (
    <div>
      {items.map(item => (
        <Item key={item.id} item={item} />  // Hook in Item
      ))}
    </div>
  );
}

function Item({ item }) {
  const [count, setCount] = useState(0);  // ✓ Top level
  return <div>{count}</div>;
}
```

---

## Resources

- **Rules of Hooks:** https://react.dev/warnings/invalid-hook-call-warning
- **ESLint Plugin:** https://github.com/facebook/react/tree/main/packages/eslint-plugin-react-hooks
- **React Hooks Intro:** https://react.dev/reference/react#hooks
- **Stale Closures:** https://dmitripavlutin.com/react-hooks-stale-closures/
- **Dependency Arrays:** https://react.dev/reference/react/useEffect#specifying-reactive-dependencies

---

**Next:** [Part 3.2: useState Hook](./03-useState-hook.md) - Master React's most fundamental hook
