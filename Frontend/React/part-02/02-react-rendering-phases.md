# Part 2.5: React Rendering Phases

## What You'll Learn

- Render phase vs Commit phase
- What happens in each phase
- Side effects and when they run
- Batching and automatic batching (React 18+)
- Manual batching if needed
- Practical implications for developers
- Debugging rendering phases
- Performance implications

---

## Table of Contents

1. [The Two Phases](#the-two-phases)
2. [Render Phase Deep Dive](#render-phase-deep-dive)
3. [Commit Phase Deep Dive](#commit-phase-deep-dive)
4. [Batching in React 18+](#batching-in-react-18)
5. [Side Effects and Timing](#side-effects-and-timing)
6. [Debugging Rendering](#debugging-rendering)
7. [Performance Implications](#performance-implications)
8. [Practical Implications](#practical-implications)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Resources](#resources)

---

## The Two Phases

### Overview

Every React update goes through **two distinct phases**:

```
User interaction / State change
         ↓
    ┌─────────────┐
    │ Render Phase│ (can be interrupted)
    └─────────────┘
         ↓
    ┌─────────────┐
    │ Commit Phase│ (atomic, cannot interrupt)
    └─────────────┘
         ↓
Browser renders updated DOM
```

### Key Difference

```
Render Phase:
- Can be interrupted
- Can be paused/resumed
- Can be abandoned
- Called multiple times if needed
- Must be PURE (no side effects)

Commit Phase:
- CANNOT be interrupted
- Must complete atomically
- Called exactly once
- Can have side effects
- Updates real DOM
```

---

## Render Phase Deep Dive

### What Happens in Render Phase

```
1. Call component functions (return JSX)
2. Create/update Virtual DOM
3. Compare with previous VDOM (diffing)
4. Identify what needs to change
5. Prepare updates (don't apply yet)
```

### Example: Render Phase

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  
  console.log('Render phase: Calling component function');
  
  // This happens during render phase
  const doubled = count * 2;
  
  return (
    <div>
      <p>{count}</p>
      <p>{doubled}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  );
}

// Timeline:
// 1. User clicks button
// 2. setCount(count + 1) called
// 3. React schedules render
// 4. RENDER PHASE:
//    - Counter function called
//    - console.log runs: "Render phase: Calling component function"
//    - doubled = 0 * 2 = 0
//    - JSX returned
//    - VDOM created
//    - Compared with previous VDOM
//    - Changes identified
// 5. COMMIT PHASE:
//    - Real DOM updated
//    - New render visible
```

### Render Phase Can Be Interrupted

```jsx
function List({ items }) {
  console.log('Rendering list');
  
  return (
    <ul>
      {items.map(item => (
        <li key={item.id}>{item.name}</li>
      ))}
    </ul>
  );
}

// Timeline with 1000 items:
// 0-5ms: Render phase starting
//   - List component called
//   - console.log runs (might be called multiple times!)
// 5-10ms: Browser needs to paint
//   - Render phase PAUSED
//   - Browser paints
// 10-15ms: Render phase RESUMED
//   - Continue where we left off
// (etc.)

// Note: console.log might run multiple times!
// This is why render phase must be pure (side-effect free)
```

### Must Be Pure

```jsx
// ❌ Bad: Render phase has side effects
function BadComponent() {
  let globalCounter = 0;  // Outside state
  
  // This runs during render phase
  globalCounter++;  // Side effect! Can run multiple times!
  
  // This might run:
  // - Render 1: globalCounter = 1
  // - Render paused and resumed: globalCounter = 2
  // - Render retried: globalCounter = 3
  // Result: Wrong count!
  
  return <div>{globalCounter}</div>;
}

// ✅ Good: Render phase is pure
function GoodComponent() {
  const [count, setCount] = useState(0);
  
  // Pure calculation, no side effects
  const doubled = count * 2;
  
  return <div>{doubled}</div>;
}

// Even better: Move side effects to effect
function BetterComponent() {
  const [count, setCount] = useState(0);
  const [logged, setLogged] = useState(false);
  
  useEffect(() => {
    // This runs in commit phase, safe for side effects
    console.log('Count changed:', count);
    setLogged(true);
  }, [count]);
  
  return <div>{count}</div>;
}
```

---

## Commit Phase Deep Dive

### What Happens in Commit Phase

```
1. Apply changes to real DOM
2. Run useLayoutEffect cleanup
3. Update DOM (now user can see changes)
4. Run useLayoutEffect hooks
5. Schedule useEffect cleanups
6. Schedule useEffect hooks
```

### Detailed Commit Timeline

```
Commit Phase (atomic):
├─ Update DOM nodes
├─ Call useLayoutEffect cleanups
├─ Call useLayoutEffect hooks
│  (browser hasn't painted yet)
├─ Call useEffect cleanups (scheduled)
├─ Call useEffect hooks (scheduled)
│  (after browser paints)
└─ Browser paints DOM

Key point:
- useLayoutEffect runs BEFORE browser paints
- useEffect runs AFTER browser paints
```

### Example: Commit Phase

```jsx
function Component() {
  useLayoutEffect(() => {
    console.log('1. useLayoutEffect (before paint)');
    return () => {
      console.log('1b. useLayoutEffect cleanup (before paint)');
    };
  }, []);
  
  useEffect(() => {
    console.log('2. useEffect (after paint)');
    return () => {
      console.log('2b. useEffect cleanup (after paint)');
    };
  }, []);
  
  console.log('0. Render phase');
  
  return <div>Component</div>;
}

// Mount timeline:
// 0. Render phase
// 1. useLayoutEffect (before paint)
// [Browser paints DOM]
// 2. useEffect (after paint)

// Update timeline:
// 0. Render phase
// 1b. useLayoutEffect cleanup (before paint)
// 1. useLayoutEffect (before paint)
// [Browser paints DOM]
// 2b. useEffect cleanup (after paint)
// 2. useEffect (after paint)

// Unmount timeline:
// 1b. useLayoutEffect cleanup
// 2b. useEffect cleanup
```

### Cannot Interrupt Commit

```javascript
// Commit phase is atomic
// React MUST complete it fully before allowing interruption

// Why?
// - Real DOM must be in consistent state
// - useLayoutEffect reads/writes DOM
// - Can't leave DOM in half-updated state
// - User can't see incomplete updates

// If React interrupted commit:
// - DOM partially updated
// - useLayoutEffect reads wrong values
// - Visual glitches
// - Data corruption possible
```

---

## Batching in React 18+

### What is Batching?

Batching means **multiple state updates are combined into one render**.

```javascript
// Without batching:
setState1() → render → setState2() → render → setState3() → render
(3 renders)

// With batching:
setState1()
setState2()
setState3()
→ single render
(1 render, 3x faster)
```

### Automatic Batching (React 18)

React 18 automatically batches **all updates**:

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  const [text, setText] = useState('');
  
  // Synchronous event handler
  const handleClick = () => {
    setCount(count + 1);  // Batched
    setText('clicked');    // Batched
    // Single render with both updates
  };
  
  // Async event handler (NOW also batched!)
  const handleAsync = async () => {
    await delay(100);
    
    setCount(count + 1);  // Batched (React 17 would NOT batch)
    setText('async');     // Batched
    // Single render
  };
  
  // setTimeout (NOW also batched!)
  const handleTimeout = () => {
    setTimeout(() => {
      setCount(count + 1);  // Batched (React 17 would NOT batch)
      setText('timeout');   // Batched
      // Single render
    }, 100);
  };
  
  return (
    <div>
      <p>{count} {text}</p>
      <button onClick={handleClick}>Sync</button>
      <button onClick={handleAsync}>Async</button>
      <button onClick={handleTimeout}>Timeout</button>
    </div>
  );
}
```

### React 17 vs React 18 Batching

```javascript
// React 17: Partial automatic batching
function Component() {
  const handleClick = async () => {
    setState1();
    setState2();
    // Batched into one render
    
    await fetchData();
    
    setState3();
    // NOT batched! Separate render
    // (This is the problem React 18 fixed)
  };
}

// React 18: Full automatic batching
function Component() {
  const handleClick = async () => {
    setState1();
    setState2();
    // Batched
    
    await fetchData();
    
    setState3();
    // ALSO batched! Single render total
  };
}
```

### Manual Batching if Needed

```jsx
import { flushSync } from 'react-dom';

function Component() {
  const [count, setCount] = useState(0);
  const [text, setText] = useState('');
  
  const handleClick = () => {
    // Force immediate render after count update
    flushSync(() => {
      setCount(count + 1);
    });
    // Render happens here, synchronously
    
    // Second render for text
    setText('clicked');
  };
  
  return (
    <div>
      <p>{count} {text}</p>
      <button onClick={handleClick}>Click</button>
    </div>
  );
}

// Why use flushSync?
// - Rare need for synchronous updates
// - Reading DOM values after update
// - Integrating with non-React code
```

### Batching Limits

```javascript
// Not batched: Updates in different event handlers
btn1.addEventListener('click', () => setState1());
btn2.addEventListener('click', () => setState2());
// Two separate updates (not through React)

// Batched: Updates in same event handler
const handleClick = () => {
  setState1();
  setState2();
};

// Batched: Updates triggered by setState (callback)
const handleChange = () => {
  setState1();
  // Queued update
};

// Not batched: Updates in Promise.then (but React 18 fixed this)
promise.then(() => {
  setState1();
  setState2();
});
// React 18: Actually batched now!
```

---

## Side Effects and Timing

### Where to Put Side Effects

```javascript
// ❌ Wrong: During render (side effect = dangerous)
function Component() {
  fetch('/api/data');  // Fetches every render!
  return <div></div>;
}

// ✅ Correct: In useEffect
function Component() {
  useEffect(() => {
    fetch('/api/data');  // Fetches once on mount
  }, []);
  
  return <div></div>;
}
```

### useEffect Timing

```jsx
function Component() {
  useEffect(() => {
    console.log('useEffect runs after paint');
    
    return () => {
      console.log('Cleanup before next effect or unmount');
    };
  }, []);
  
  return <div></div>;
}

// Timeline:
// 1. Render phase: Component function called
// 2. Commit phase: DOM updated
// 3. Browser paints
// 4. useEffect runs
// 5. Later... state changes
// 6. Render phase: Component function called again
// 7. Commit phase: DOM updated
// 8. Browser paints
// 9. Cleanup runs
// 10. New useEffect runs
```

### useLayoutEffect Timing

```jsx
function Component() {
  useLayoutEffect(() => {
    console.log('useLayoutEffect runs BEFORE paint');
    // Can read/write DOM synchronously
    // Browser hasn't painted yet
    
    return () => {
      console.log('Cleanup before paint');
    };
  }, []);
  
  return <div></div>;
}

// Use when:
// - Measuring DOM (offsetWidth, offsetHeight)
// - Adjusting layout based on measurements
// - Preventing visual flicker

// Don't use when:
// - Fetching data
// - Setting timeouts
// - Analytics
// (Use useEffect instead, it's more efficient)
```

### Event Handler Timing

```jsx
function Component() {
  const handleClick = () => {
    console.log('1. Event handler runs during commit phase');
    
    setState(value);
    // setState queued, doesn't update immediately
    
    console.log('2. Can read old state here');
    console.log(state);  // Old value
  };
  
  return <button onClick={handleClick}>Click</button>;
}

// Handler timeline:
// 1. User clicks
// 2. Event handler called (during commit phase)
// 3. setState queued
// 4. Handler completes
// 5. New render scheduled
// 6. Render phase
// 7. Commit phase
// 8. DOM updated
```

---

## Debugging Rendering

### React DevTools Profiler

```javascript
// React DevTools Profiler shows:
// - Render phase duration
// - Commit phase duration
// - Which components rendered
// - Why they rendered (props changed, state changed, etc.)

// Usage:
// 1. Install React DevTools extension
// 2. Open DevTools → Profiler tab
// 3. Record interactions
// 4. Analyze flame graph
// 5. Find bottlenecks
```

### Console Logging for Debugging

```jsx
function Component() {
  console.log('Render phase');
  
  useLayoutEffect(() => {
    console.log('useLayoutEffect (before paint)');
  }, []);
  
  useEffect(() => {
    console.log('useEffect (after paint)');
  }, []);
  
  return <div></div>;
}

// Output shows order of execution
// Helps understand timing
```

### Debugging Batch Issues

```javascript
// Check if updates are batched:
function Component() {
  const [count, setCount] = useState(0);
  const [text, setText] = useState('');
  
  const handleClick = () => {
    setCount(count + 1);
    console.log('After setCount');
    
    setText('clicked');
    console.log('After setText');
    
    // Both logs run BEFORE render
    // Proof of batching!
  };
  
  return (
    <div>
      {count} {text}
      <button onClick={handleClick}>Click</button>
    </div>
  );
}

// Output:
// "After setCount"
// "After setText"
// (Render happens here)
// (useEffect happens here)
```

---

## Performance Implications

### Render Phase Performance

```javascript
// Render phase is:
// - CPU-bound (JavaScript execution)
// - Should be fast (<5ms per frame)
// - Can be optimized with memoization

function ExpensiveComponent({ items }) {
  // ❌ Expensive calculation on every render
  const processed = items.map(item => {
    // Heavy processing
    return process(item);
  });
  
  return <div>{processed}</div>;
}

// ✅ Memoize for optimization
const ExpensiveComponent = memo(function({ items }) {
  const processed = useMemo(() => {
    return items.map(item => process(item));
  }, [items]);
  
  return <div>{processed}</div>;
});

// Component only recalculates when items change
```

### Commit Phase Performance

```javascript
// Commit phase is:
// - DOM update (fast usually)
// - Browser reflow/repaint (can be slow)
// - useLayoutEffect runs (should be fast)

// Avoid heavy work in useLayoutEffect:
function Component() {
  useLayoutEffect(() => {
    // ❌ Bad: Heavy work blocks painting
    const result = heavyCalculation();
    
    // ✅ Good: Light work, defer heavy work
    const width = element.offsetWidth;  // Light
    element.style.width = (width + 10) + 'px';
    
    // Defer heavy work to useEffect
    startTransition(() => {
      // Heavy calculation
    });
  }, []);
}
```

---

## Practical Implications

### For Your Code

```jsx
// 1. Keep render phase pure
function ✅ Pure() {
  const doubled = count * 2;
  return <div>{doubled}</div>;
}

function ❌ Impure() {
  fetch('/api');  // Side effect!
  return <div></div>;
}

// 2. Use batching to your advantage
function ✅ Batched() {
  const handleChange = (e) => {
    setSearch(e.target.value);      // Batched
    setCurrentPage(1);               // Batched
    setFilters({});                  // Batched
    // Single render with all changes
  };
}

// 3. Side effects go in useEffect
function ✅ CorrectSideEffects() {
  useEffect(() => {
    fetchData();  // Safe in effect
  }, []);
  
  return <div></div>;
}

// 4. Understand render phase can run multiple times
function ✅ MultipleRenderAware() {
  // This might run 2-3 times
  const calculated = expensiveCalc(props);
  
  // That's fine! It's pure
  // React will use most recent result
  
  return <div>{calculated}</div>;
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Proper Effect Dependencies

```jsx
function Component({ id, onSuccess }) {
  useEffect(() => {
    fetchData(id).then(onSuccess);
  }, [id, onSuccess]);  // Proper dependencies
}

// Effect runs when id or onSuccess changes
// Batching optimizes this automatically
```

### Pattern 2: Deferring Updates

```jsx
function SearchComponent() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isPending, startTransition] = useTransition();
  
  const handleChange = (e) => {
    const value = e.target.value;
    
    // High priority: update input immediately
    setQuery(value);  // Batched
    
    // Low priority: update results deferred
    startTransition(() => {
      setResults(heavySearch(value));  // Separate, low-priority render
    });
  };
}

// Batching + transitions = responsive UI
```

### Pattern 3: Handling Async Updates

```jsx
function Component() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    setLoading(true);  // Batched
    
    fetchData()
      .then(result => {
        setData(result);      // Batched (React 18)
        setLoading(false);    // Batched
        // Single render with all three updates!
      })
      .catch(err => {
        setError(err);        // Batched (React 18)
        setLoading(false);    // Batched
        // Single render
      });
  }, []);
}
```

---

## Common Pitfalls

### Pitfall 1: Side Effects During Render

```jsx
// ❌ Bad: Side effect during render
function Component() {
  localStorage.setItem('key', value);  // Runs multiple times!
  return <div></div>;
}

// ✅ Good: Side effect in useEffect
function Component() {
  useEffect(() => {
    localStorage.setItem('key', value);  // Runs once
  }, [value]);
  
  return <div></div>;
}
```

### Pitfall 2: Forgetting Dependencies

```jsx
// ❌ Bad: Missing dependency
function Component() {
  useEffect(() => {
    const interval = setInterval(() => {
      setCount(count + 1);  // Stale count!
    }, 1000);
  }, []);  // Missing count!
  
  return <div>{count}</div>;
}

// ✅ Good: Proper dependencies
function Component() {
  useEffect(() => {
    const interval = setInterval(() => {
      setCount(c => c + 1);  // Or include count in deps
    }, 1000);
  }, []);
  
  return <div>{count}</div>;
}
```

### Pitfall 3: Unnecessary flushSync

```jsx
// ❌ Over-using flushSync (defeats purpose of batching)
function Component() {
  const handleClick = () => {
    flushSync(() => setCount(c => c + 1));  // Forces render
    flushSync(() => setText('clicked'));    // Forces another render
    // Now we have 2 renders instead of 1!
  };
}

// ✅ Let batching do its job
function Component() {
  const handleClick = () => {
    setCount(c => c + 1);   // Batched
    setText('clicked');     // Batched
    // One render total
  };
}
```

---

## Resources

- **Render vs Commit:** https://react.dev/learn/render-and-commit
- **useEffect:** https://react.dev/reference/react/useEffect
- **useLayoutEffect:** https://react.dev/reference/react/useLayoutEffect
- **Automatic Batching:** https://react.dev/blog/2022/03/08/react-18-is-released
- **React 18 Suspense:** https://react.dev/reference/react/Suspense

---

**Next:** [Part 3.1: Hook Rules & Principles](./03-hooks-rules-and-principles.md) - Master the fundamentals of React Hooks
