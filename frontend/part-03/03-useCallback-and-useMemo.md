# Part 3.6: useCallback & useMemo

## What You'll Learn

- When to use useMemo vs useCallback
- Memoization concepts and benefits
- Dependency arrays in optimization hooks
- Premature optimization pitfalls
- Profiling and finding real bottlenecks
- Common patterns and anti-patterns
- Performance impact and trade-offs
- Interview questions

---

## Table of Contents

1. [Memoization Concepts](#memoization-concepts)
2. [useMemo Fundamentals](#usememo-fundamentals)
3. [useCallback Fundamentals](#usecallback-fundamentals)
4. [When to Use Each](#when-to-use-each)
5. [Performance Profiling](#performance-profiling)
6. [Premature Optimization](#premature-optimization)
7. [React.memo for Components](#reactmemo-for-components)
8. [Common Patterns](#common-patterns)
9. [Common Pitfalls](#common-pitfalls)
10. [Interview Questions](#interview-questions)
11. [Resources](#resources)

---

## Memoization Concepts

### What is Memoization?

Memoization means **caching a computation result and returning it if inputs haven't changed**.

```javascript
// Without memoization
function expensiveCalculation(n) {
  // Heavy computation
  let result = 0;
  for (let i = 0; i < n * 1000000; i++) {
    result += i;
  }
  return result;
}

// Call 1: expensiveCalculation(100) → takes 100ms
// Call 2: expensiveCalculation(100) → takes 100ms again (recompute)
// Total: 200ms

// With memoization
const cache = {};

function memoizedExpensiveCalculation(n) {
  if (cache[n] !== undefined) {
    console.log('From cache');
    return cache[n];
  }
  
  console.log('Computing...');
  let result = 0;
  for (let i = 0; i < n * 1000000; i++) {
    result += i;
  }
  
  cache[n] = result;
  return result;
}

// Call 1: memoizedExpensiveCalculation(100) → takes 100ms
// Call 2: memoizedExpensiveCalculation(100) → instant (from cache)
// Total: 100ms
```

### Why Memoization Matters in React

```jsx
// Without memoization
function Parent() {
  const [count, setCount] = useState(0);
  
  // New object created every render
  const expensiveValue = {
    data: calculateExpensiveData()  // Heavy computation
  };
  
  return (
    <div>
      <button onClick={() => setCount(count + 1)}>Increment</button>
      <Child value={expensiveValue} />
    </div>
  );
}

// With memoization
function Parent() {
  const [count, setCount] = useState(0);
  
  // Only recompute when dependencies change
  const expensiveValue = useMemo(() => ({
    data: calculateExpensiveData()
  }), []);  // Never recompute (no dependencies)
  
  return (
    <div>
      <button onClick={() => setCount(count + 1)}>Increment</button>
      <Child value={expensiveValue} />
    </div>
  );
}
```

---

## useMemo Fundamentals

### What is useMemo?

useMemo **memoizes a computed value** and returns it only if dependencies haven't changed.

```jsx
function Component() {
  const [count, setCount] = useState(0);
  const [name, setName] = useState('John');
  
  // Memoize expensive calculation
  const expensiveValue = useMemo(() => {
    // This runs only when 'count' changes
    // Not when 'name' changes
    return calculateExpensiveValue(count);
  }, [count]);  // Dependency array
  
  return (
    <div>
      <p>Count: {count}</p>
      <p>Name: {name}</p>
      <p>Expensive: {expensiveValue}</p>
      <button onClick={() => setCount(count + 1)}>Increment Count</button>
      <button onClick={() => setName('Jane')}>Change Name</button>
    </div>
  );
}

// Timeline:
// 1. Render 1: count=0, name='John' → calculate expensiveValue
// 2. Click "Change Name" → name='Jane', count=0
//    expensiveValue not recalculated (count didn't change)
// 3. Click "Increment Count" → count=1, name='Jane'
//    expensiveValue recalculated (count changed)
```

### Basic Usage Pattern

```jsx
const memoizedValue = useMemo(() => {
  // Expensive computation
  return computeExpensiveValue(a, b);
}, [a, b]);  // Recalculate when a or b changes

// Return value
return <div>{memoizedValue}</div>;
```

### Memoizing Objects and Arrays

```jsx
function Component({ userId }) {
  const [theme, setTheme] = useState('light');
  
  // ❌ Without useMemo: New object every render
  const user = {
    id: userId,
    name: 'John',
    preferences: { theme }
  };
  
  // ✅ With useMemo: Object only recreated when userId or theme change
  const user = useMemo(() => ({
    id: userId,
    name: 'John',
    preferences: { theme }
  }), [userId, theme]);
  
  return <UserProfile user={user} />;
}

// Without useMemo:
// Parent renders → new user object → Child re-renders (new prop reference)

// With useMemo:
// Parent renders, userId same → same user object → Child doesn't re-render
```

---

## useCallback Fundamentals

### What is useCallback?

useCallback **memoizes a function** and returns the same function reference if dependencies haven't changed.

```jsx
function Component() {
  const [count, setCount] = useState(0);
  
  // ❌ Without useCallback: New function every render
  const handleIncrement = () => {
    setCount(count + 1);
  };
  
  // ✅ With useCallback: Same function unless 'count' changes
  const handleIncrement = useCallback(() => {
    setCount(count + 1);
  }, [count]);  // Recalculate function when count changes
  
  return (
    <div>
      <p>{count}</p>
      <button onClick={handleIncrement}>Increment</button>
    </div>
  );
}
```

### Function Identity Matters

```jsx
function Parent() {
  const [count, setCount] = useState(0);
  
  // ❌ Without useCallback
  const handleClick = () => {
    setCount(count + 1);
  };
  
  // New function object every render
  // Even if logic is identical
  // handleClick === handleClick from last render? NO
  
  return <Child onClick={handleClick} />;
}

// ✅ With useCallback
function Parent() {
  const [count, setCount] = useState(0);
  
  const handleClick = useCallback(() => {
    setCount(count + 1);
  }, [count]);
  
  // Same function object unless dependencies change
  // handleClick === handleClick from last render? YES (if count same)
  
  return <Child onClick={handleClick} />;
}

// Child component (memoized)
const Child = React.memo(function Child({ onClick }) {
  console.log('Child rendered');
  return <button onClick={onClick}>Click</button>;
});

// Without useCallback: Child logs "Child rendered" every time Parent renders
// With useCallback: Child logs "Child rendered" only when count changes
```

### Basic Usage Pattern

```jsx
const memoizedCallback = useCallback(() => {
  doSomething(a, b);
}, [a, b]);  // Recalculate when a or b changes

return <Child onClick={memoizedCallback} />;
```

---

## When to Use Each

### useMemo Use Cases

```jsx
// 1. Expensive calculations
function Component({ items }) {
  const sortedItems = useMemo(() => {
    // Heavy sorting operation
    return items.sort((a, b) => b.value - a.value);
  }, [items]);
  
  return <List items={sortedItems} />;
}

// 2. Complex object creation
function Component({ userId, name, email }) {
  const user = useMemo(() => ({
    id: userId,
    name,
    email,
    created: new Date()
  }), [userId, name, email]);
  
  return <UserCard user={user} />;
}

// 3. Filtering/searching
function Component({ items, query }) {
  const filtered = useMemo(() => {
    return items.filter(item => 
      item.name.toLowerCase().includes(query.toLowerCase())
    );
  }, [items, query]);
  
  return <List items={filtered} />;
}

// 4. Context value (prevent unnecessary re-renders)
function Provider({ children }) {
  const [user, setUser] = useState(null);
  
  const value = useMemo(() => ({
    user,
    setUser
  }), [user]);
  
  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
}
```

### useCallback Use Cases

```jsx
// 1. Passing callback to memoized child
function Parent() {
  const [count, setCount] = useState(0);
  
  const handleClick = useCallback(() => {
    setCount(c => c + 1);
  }, []);  // Empty deps: function never changes
  
  return <MemoizedButton onClick={handleClick} />;
}

// 2. Event handler for effect
function Component() {
  const handleResize = useCallback(() => {
    console.log('Resized');
  }, []);
  
  useEffect(() => {
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [handleResize]);  // Safe to include in deps
}

// 3. Function passed to custom hook
function Component() {
  const validator = useCallback((value) => {
    return value.length > 0;
  }, []);
  
  useCustomValidator(validator);
}
```

### When NOT to Use

```jsx
// ❌ Don't memoize simple values
function Component() {
  // Simple number: doesn't benefit from memoization
  const doubled = useMemo(() => count * 2, [count]);
  
  // Just compute directly
  const doubled = count * 2;
}

// ❌ Don't memoize if no memoized children
function Component() {
  const handleClick = useCallback(() => {
    setCount(count + 1);
  }, [count]);
  
  // If Child is not memoized, useCallback doesn't help
  return <Child onClick={handleClick} />;
}

// ❌ Don't memoize everything
// Memoization has costs too!
// Only memoize when there's a real performance problem
```

---

## Performance Profiling

### Using React DevTools Profiler

```javascript
// 1. Open React DevTools in Chrome/Firefox
// 2. Click "Profiler" tab
// 3. Click "Record" button
// 4. Interact with your app
// 5. Stop recording
// 6. Analyze which components re-render

// Look for:
// - Unnecessary re-renders (same props)
// - Long render times
// - Patterns of wasted renders
```

### Measuring Performance Programmatically

```jsx
function Component() {
  const start = performance.now();
  
  // Expensive calculation
  const result = expensiveCalculation();
  
  const end = performance.now();
  console.log(`Took ${end - start}ms`);
  
  return <div>{result}</div>;
}

// Better: Use React's built-in profiler
import { Profiler } from 'react';

function App() {
  const onRenderCallback = (
    id,
    phase,
    actualDuration,
    baseDuration,
    startTime,
    commitTime
  ) => {
    console.log(`${id} (${phase}) took ${actualDuration}ms`);
  };
  
  return (
    <Profiler id="App" onRender={onRenderCallback}>
      <Component />
    </Profiler>
  );
}
```

### Finding Real Bottlenecks

```jsx
// Step 1: Measure WITHOUT optimization
function expensiveSort(items) {
  console.time('sort');
  const sorted = [...items].sort((a, b) => b.value - a.value);
  console.timeEnd('sort');
  return sorted;
}

// Step 2: See if it's actually slow
// Step 3: Only then optimize

// Example:
// Without memoization: sort takes 5ms
// With memoization: saves 5ms per render
// But memoization costs 1ms in memory overhead
// Net gain: 4ms

// But if sort only happens once per mount:
// Without: 5ms one time
// With: 5ms one time + 1ms overhead
// Net loss: -1ms (worse!)

// ONLY optimize real bottlenecks!
```

---

## Premature Optimization

### The Problem

```jsx
// ❌ Optimizing everything makes code harder to read
function Component() {
  const [count, setCount] = useState(0);
  const [name, setName] = useState('');
  const [items, setItems] = useState([]);
  
  // Over-optimized
  const memoizedCount = useMemo(() => count, [count]);
  const memoizedName = useMemo(() => name, [name]);
  const memoizedItems = useMemo(() => items, [items]);
  
  const handleIncrement = useCallback(() => {
    setCount(count + 1);
  }, [count]);
  
  const handleNameChange = useCallback((e) => {
    setName(e.target.value);
  }, []);
  
  const handleAddItem = useCallback(() => {
    setItems([...items, {}]);
  }, [items]);
  
  // Too much memoization!
  // Makes code verbose and harder to read
  // Probably no performance benefit
}
```

### The Reality

```javascript
// Most React apps don't need optimization
// React is fast enough for most use cases

// Performance problems usually come from:
// 1. Rendering 1000+ items without virtualization
// 2. Expensive calculations (not React)
// 3. Network requests (not React)
// 4. Large bundle size (not React)
// 5. Images not optimized (not React)

// React itself is rarely the bottleneck!
```

### When Optimization Matters

```jsx
// ✅ DO optimize when:
// 1. You've measured and found a real problem
// 2. Profiler shows excessive re-renders
// 3. The component tree is complex
// 4. User action is noticeably slow

function SearchResults({ query }) {
  // Query changes frequently (every keystroke)
  // Results are expensive to calculate
  // Child components are memoized
  
  const filteredResults = useMemo(() => {
    // Heavy filtering
    return filterAndSort(allResults, query);
  }, [query]);
  
  return (
    <div>
      {filteredResults.map(result => (
        <MemoizedResult key={result.id} result={result} />
      ))}
    </div>
  );
}

// This makes sense because:
// - Filtering is expensive
// - Runs frequently
// - Prevents child re-renders
```

---

## React.memo for Components

### Memoizing Components

```jsx
// Without React.memo
function UserCard({ user }) {
  console.log('UserCard rendered');
  return <div>{user.name}</div>;
}

function App() {
  const [theme, setTheme] = useState('light');
  const user = { name: 'John' };
  
  return (
    <div>
      <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
        Toggle Theme
      </button>
      <UserCard user={user} />
    </div>
  );
}

// When theme changes:
// App re-renders
// UserCard re-renders (even though user object is same!)
// Logs: "UserCard rendered"

// ✅ With React.memo
const UserCard = React.memo(function UserCard({ user }) {
  console.log('UserCard rendered');
  return <div>{user.name}</div>;
});

// When theme changes:
// App re-renders
// UserCard checks props
// user prop is same object reference
// UserCard doesn't re-render!
// Doesn't log
```

### React.memo with Custom Comparison

```jsx
const UserCard = React.memo(
  function UserCard({ user }) {
    return <div>{user.name}</div>;
  },
  (prevProps, nextProps) => {
    // Return true if props are "equal" (don't re-render)
    // Return false if props are different (do re-render)
    
    // Custom comparison
    return prevProps.user.id === nextProps.user.id;
  }
);

// This is rarely needed
// Usually just check object reference
```

### Combining React.memo with useCallback

```jsx
const Button = React.memo(({ onClick, label }) => {
  console.log('Button rendered');
  return <button onClick={onClick}>{label}</button>;
});

function Parent() {
  const [count, setCount] = useState(0);
  
  // ❌ Without useCallback: Button re-renders every time Parent renders
  const handleClick = () => {
    setCount(count + 1);
  };
  
  // Parent renders → new handleClick → Button props change → Button re-renders
  
  // ✅ With useCallback: Button only re-renders when count changes
  const handleClick = useCallback(() => {
    setCount(count + 1);
  }, [count]);
  
  // Parent renders → same handleClick (if count same) → Button doesn't re-render
  
  return <Button onClick={handleClick} label="Increment" />;
}
```

---

## Common Patterns

### Pattern 1: Context Value Memoization

```jsx
function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [theme, setTheme] = useState('light');
  
  // Without useMemo: All consumers re-render when any value changes
  // With useMemo: Only consumers using changed value re-render
  
  const authValue = useMemo(() => ({
    user,
    setUser
  }), [user]);
  
  const themeValue = useMemo(() => ({
    theme,
    setTheme
  }), [theme]);
  
  return (
    <AuthContext.Provider value={authValue}>
      <ThemeContext.Provider value={themeValue}>
        {children}
      </ThemeContext.Provider>
    </AuthContext.Provider>
  );
}
```

### Pattern 2: Memoized Selectors

```jsx
function Component() {
  const state = useAppState();
  
  // Without useMemo: New object every render
  const user = {
    id: state.user.id,
    name: state.user.name
  };
  
  // With useMemo: Only recalculate when state.user changes
  const user = useMemo(() => ({
    id: state.user.id,
    name: state.user.name
  }), [state.user]);
  
  return <UserDisplay user={user} />;
}
```

### Pattern 3: Stable Event Handlers

```jsx
function Form() {
  const [formData, setFormData] = useState({});
  const [errors, setErrors] = useState({});
  
  // Stable handlers for form fields
  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  }, []);
  
  const handleSubmit = useCallback(async () => {
    const newErrors = validate(formData);
    setErrors(newErrors);
    if (Object.keys(newErrors).length === 0) {
      await submitForm(formData);
    }
  }, [formData]);
  
  return (
    <form onSubmit={handleSubmit}>
      <input name="email" onChange={handleChange} />
      <input name="password" onChange={handleChange} />
      <button type="submit">Submit</button>
    </form>
  );
}
```

---

## Common Pitfalls

### Pitfall 1: Wrong Dependencies

```jsx
// ❌ WRONG: Missing dependency
function Component({ items }) {
  const sorted = useMemo(() => {
    return items.sort((a, b) => b.value - a.value);
  }, []);  // Missing items!
}

// items change but sorted doesn't recalculate
// Returns stale data

// ✅ CORRECT: Include all dependencies
function Component({ items }) {
  const sorted = useMemo(() => {
    return items.sort((a, b) => b.value - a.value);
  }, [items]);  // Include items
}
```

### Pitfall 2: Memoizing Too Much

```jsx
// ❌ Over-optimization
function Component() {
  const value = useMemo(() => 42, []);
  const handler = useCallback(() => {}, []);
  const obj = useMemo(() => ({}), []);
  
  // These don't need memoization
  // Adds complexity with no benefit
}

// ✅ Only optimize what matters
function Component() {
  const expensiveData = useMemo(() => {
    return complexCalculation();
  }, []);
  
  // Only memoize expensive operations
}
```

### Pitfall 3: Dependencies Array Issues

```jsx
// ❌ WRONG: Including non-dependencies
function Component() {
  const data = useCallback(() => {
    return calculateData();
  }, [Math.random()]);  // WRONG!
  // New random number every render
  // Function recalculates every render
}

// ✅ CORRECT: Only actual dependencies
function Component() {
  const data = useCallback(() => {
    return calculateData();
  }, []);  // No dependencies
}

// ❌ WRONG: Objects as dependencies
function Component({ config }) {
  const memoized = useMemo(() => {
    return process(config);
  }, [config]);  // config is a new object every render!
}

// ✅ CORRECT: Memoize the config object too
function Component({ config }) {
  const memoizedConfig = useMemo(() => config, [config.id]);
  
  const memoized = useMemo(() => {
    return process(memoizedConfig);
  }, [memoizedConfig]);
}
```

---

## Interview Questions

### Q1: What's the difference between useMemo and useCallback?

```
Answer:
useMemo: Memoizes a VALUE
const value = useMemo(() => expensiveComputation(), [deps]);

useCallback: Memoizes a FUNCTION
const callback = useCallback(() => doSomething(), [deps]);

Both:
- Cache based on dependencies
- Return same reference if deps unchanged
- Have memory overhead
- Should only be used for real performance issues

Difference:
- useMemo returns the value
- useCallback returns the function itself

Analogy:
- useMemo: "Remember this calculation"
- useCallback: "Remember this function"
```

### Q2: When should you NOT use useMemo or useCallback?

```
Answer: Don't use when:
1. The value/function is simple (number, string, simple function)
2. The component doesn't have memoized children receiving it
3. You haven't measured a real performance problem
4. Memoization cost exceeds computation cost

Example of waste:
useMemo(() => count * 2, [count]);
// Memoization costs 1ms
// Computation costs 0.1ms
// Net loss: 0.9ms per render

Reality:
- 99% of apps don't need this
- Profile first, optimize second
- Premature optimization is evil
```

### Q3: How do you decide between useMemo and useCallback?

```
Answer:
Use useMemo when:
- Computing an expensive value
- Object/array creation that props depend on
- Context value that many consumers use

Use useCallback when:
- Function passed to memoized child
- Function used in dependency array
- Event handler stabilization

Rule of thumb:
- Start with no memoization
- Measure performance
- Add memoization only where needed
- Verify it actually helps
```

---

## Resources

- **useMemo Documentation:** https://react.dev/reference/react/useMemo
- **useCallback Documentation:** https://react.dev/reference/react/useCallback
- **When to useMemo:** https://kentcdodds.com/blog/usememo-and-usecallback
- **React DevTools Profiler:** https://react.dev/learn/react-developer-tools
- **Premature Optimization:** https://en.wikipedia.org/wiki/Program_optimization#When_to_optimize
- **React Performance:** https://react.dev/learn/render-and-commit

---

**Next:** [Part 3.7: useRef Hook](./03-useRef-hook.md) - Master imperative access to DOM and values
