# Part 3.3: useEffect Hook

## What You'll Learn

- What useEffect is and why it exists
- Synchronization concept (not lifecycle)
- Dependency arrays and when effects run
- Cleanup functions and memory leaks
- Race conditions and how to prevent them
- AbortController pattern
- Effect dependencies best practices
- Common patterns and anti-patterns
- Debugging effects
- Interview questions

---

## Table of Contents

1. [useEffect Fundamentals](#useeffect-fundamentals)
2. [Thinking in Synchronization](#thinking-in-synchronization)
3. [Effect Dependencies](#effect-dependencies)
4. [Cleanup Functions](#cleanup-functions)
5. [Race Conditions](#race-conditions)
6. [AbortController Pattern](#abortcontroller-pattern)
7. [Missing Dependencies](#missing-dependencies)
8. [useLayoutEffect vs useEffect](#uselayouteffect-vs-useeffect)
9. [Common Patterns](#common-patterns)
10. [Common Pitfalls](#common-pitfalls)
11. [Interview Questions](#interview-questions)
12. [Resources](#resources)

---

## useEffect Fundamentals

### What is useEffect?

useEffect runs **side effects** (code with external consequences) after render.

```jsx
import { useEffect, useState } from 'react';

function Component() {
  const [count, setCount] = useState(0);
  
  // Side effect: runs after render
  useEffect(() => {
    console.log('Effect ran, count is now:', count);
    // This code runs AFTER component renders
  }, [count]);  // Dependency array
  
  return (
    <button onClick={() => setCount(count + 1)}>
      Count: {count}
    </button>
  );
}

// Timeline:
// 1. Component renders
// 2. Browser paints
// 3. Effect runs
// 4. User sees component
```

### Side Effects

Side effects are operations with external impact:

```javascript
// Side effects (use useEffect):
- API calls
- localStorage access
- Subscriptions
- Event listeners
- Timers/intervals
- Modifying DOM directly
- Logging

// NOT side effects (don't need useEffect):
- Calculations
- Object creation
- State updates (in render)
- Passing data to child components
```

### Basic Structure

```jsx
function Component() {
  useEffect(() => {
    // Effect code here
    // Runs after render
    
    return () => {
      // Cleanup code (optional)
      // Runs before next effect or unmount
    };
  }, []);  // Dependency array
}

// useEffect takes 2 arguments:
// 1. Effect function
// 2. Dependency array (optional)
```

---

## Thinking in Synchronization

### Not Lifecycle Thinking

```jsx
// ❌ WRONG: Lifecycle thinking
function Component() {
  useEffect(() => {
    // Think: "on mount"
    fetchData();
  }, []);
  
  useEffect(() => {
    // Think: "on update"
    analytics.track('page view');
  });
  
  useEffect(() => {
    // Think: "on unmount"
    return () => cleanup();
  }, []);
}

// This is wrong! Leads to bugs.
```

### Synchronization Thinking

```jsx
// ✅ CORRECT: Synchronization thinking
function Component({ userId }) {
  useEffect(() => {
    // "Keep this in sync with userId"
    const subscription = subscribeToUser(userId);
    
    return () => subscription.unsubscribe();
  }, [userId]);  // Effect depends on userId
  
  // When userId changes:
  // 1. Cleanup old subscription
  // 2. Create new subscription
  // 3. Keep them in sync
}

// Think: "Synchronize with these values"
// Not: "Run on mount/update/unmount"
```

### Real Example: Document Title

```jsx
// Synchronization: Keep document title in sync with state
function Component({ title }) {
  useEffect(() => {
    // Synchronize: title state → document title
    document.title = title;
  }, [title]);  // Re-synchronize when title changes
}

// If title = "Home"
// Effect runs: document.title = "Home"
// 
// If title = "About"
// Effect runs: document.title = "About"
// 
// They stay in sync!
```

### Another Example: Window Resize

```jsx
function Component() {
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);
  
  useEffect(() => {
    // Synchronize: window → state
    const handleResize = () => setWindowWidth(window.innerWidth);
    
    window.addEventListener('resize', handleResize);
    
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);  // No dependencies - set up once and maintain sync
  
  return <div>Width: {windowWidth}</div>;
}

// Effect sets up: state = window width
// Every time window resizes: state updates to match
// State stays in sync with window!
```

---

## Effect Dependencies

### No Dependency Array

```jsx
function Component() {
  useEffect(() => {
    console.log('Effect ran');
  });  // No dependency array
  
  return <button>Click</button>;
}

// Timeline:
// Mount: render → effect runs (logs "Effect ran")
// Update: render → effect runs (logs "Effect ran")
// Update: render → effect runs (logs "Effect ran")
// Effect runs EVERY render!

// Use when: Effect must stay in sync with every render
// Rarely needed! Usually means missing dependencies
```

### Empty Dependency Array

```jsx
function Component() {
  useEffect(() => {
    console.log('Effect ran');
  }, []);  // Empty array
  
  return <button>Click</button>;
}

// Timeline:
// Mount: render → effect runs once (logs "Effect ran")
// Update: render → effect skipped
// Update: render → effect skipped
// Effect runs ONCE after mount

// Use when: Effect should run once (setup)
// Examples:
// - Fetch initial data
// - Set up subscription once
// - Initialize library
```

### With Dependencies

```jsx
function Component({ userId }) {
  useEffect(() => {
    console.log('Effect ran for userId:', userId);
  }, [userId]);  // Depend on userId
  
  return <button>Click</button>;
}

// Timeline:
// Mount: userId = 1 → render → effect runs (logs "userId: 1")
// Update: userId = 1 → render → effect skipped (same userId)
// Update: userId = 2 → render → effect runs (logs "userId: 2")
// Update: userId = 2 → render → effect skipped (same userId)

// Effect runs when dependency changes
// Keeps effect in sync with dependency
```

### Multiple Dependencies

```jsx
function Component({ userId, postId }) {
  useEffect(() => {
    // Both userId and postId changes trigger effect
    fetchUserPost(userId, postId);
  }, [userId, postId]);
  
  return <div></div>;
}

// Timeline:
// userId = 1, postId = 'A' → fetch(1, 'A')
// userId = 1, postId = 'A' → skip (same)
// userId = 2, postId = 'A' → fetch(2, 'A')
// userId = 2, postId = 'B' → fetch(2, 'B')
// userId = 2, postId = 'B' → skip (same)

// React checks: Has userId or postId changed?
// If yes → run effect
// If no → skip effect
```

---

## Cleanup Functions

### What is Cleanup?

Cleanup runs **before the next effect or unmount**.

```jsx
function Component() {
  useEffect(() => {
    console.log('Effect setup');
    
    return () => {
      console.log('Effect cleanup');
    };
  }, []);
  
  return <div>Component</div>;
}

// Timeline:
// Mount: "Effect setup"
// Unmount: "Effect cleanup"

// With dependency:
function Component({ userId }) {
  useEffect(() => {
    console.log('Set up for userId:', userId);
    
    return () => {
      console.log('Clean up for userId:', userId);
    };
  }, [userId]);
  
  return <div></div>;
}

// userId = 1: "Set up for userId: 1"
// userId = 2: "Clean up for userId: 1" → "Set up for userId: 2"
// Unmount: "Clean up for userId: 2"
```

### Memory Leak Prevention

```jsx
// ❌ WRONG: Memory leak - no cleanup
function Component() {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    const subscription = dataSource.subscribe(data => {
      setData(data);
    });
    // Forgot to unsubscribe!
  }, []);
  
  return <div>{data}</div>;
}

// Every mount: new subscription
// No cleanup: old subscriptions never unsubscribed
// Memory leak! Subscriptions keep piling up!

// ✅ CORRECT: Cleanup unsubscribes
function Component() {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    const subscription = dataSource.subscribe(data => {
      setData(data);
    });
    
    return () => {
      subscription.unsubscribe();  // Cleanup!
    };
  }, []);
  
  return <div>{data}</div>;
}

// Every mount: new subscription
// Every unmount: unsubscribe
// No leak!
```

### Common Cleanups

```jsx
// Event listener cleanup
useEffect(() => {
  const handleResize = () => {
    // Handle resize
  };
  
  window.addEventListener('resize', handleResize);
  
  return () => {
    window.removeEventListener('resize', handleResize);
  };
}, []);

// Timer cleanup
useEffect(() => {
  const timer = setTimeout(() => {
    // Do something
  }, 1000);
  
  return () => {
    clearTimeout(timer);
  };
}, []);

// Interval cleanup
useEffect(() => {
  const interval = setInterval(() => {
    // Do something
  }, 1000);
  
  return () => {
    clearInterval(interval);
  };
}, []);

// Subscription cleanup
useEffect(() => {
  const subscription = observable.subscribe(value => {
    // Handle value
  });
  
  return () => {
    subscription.unsubscribe();
  };
}, []);

// AbortController cleanup (covered next)
useEffect(() => {
  const abortController = new AbortController();
  
  fetch('/api/data', { signal: abortController.signal })
    .then(r => r.json())
    .then(data => {
      // Use data
    });
  
  return () => {
    abortController.abort();
  };
}, []);
```

---

## Race Conditions

### What is a Race Condition?

Race condition happens when **multiple async operations compete, results arrive out of order**.

```jsx
function Component({ userId }) {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    // Fetch user 1
    fetch(`/api/users/1`).then(r => r.json()).then(data => {
      setUser(data);
    });
  }, []);
  
  // Fetch user 2 (somehow)
  useEffect(() => {
    fetch(`/api/users/2`).then(r => r.json()).then(data => {
      setUser(data);
    });
  }, []);
  
  return <div>{user.name}</div>;
}

// What happens?
// 1. Start fetch user 1
// 2. Start fetch user 2
// 3. User 2 response arrives first (faster)
// 4. setUser(user2)
// 5. User 1 response arrives
// 6. setUser(user1)
// Result: Shows user 1, but request was for user 2!
// This is a race condition!
```

### Better Example: Dependency Changes

```jsx
function Component({ userId }) {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then(r => r.json())
      .then(data => {
        setUser(data);
      });
  }, [userId]);  // Re-fetch when userId changes
  
  return <div>{user?.name}</div>;
}

// Timeline:
// userId = 1: fetch user 1
// Before response: userId = 2 → new effect starts
// userId = 2: fetch user 2
// User 1 response arrives (slow) → setUser(user1) ❌ WRONG!
// User 2 response arrives (fast) → setUser(user2) ✓ RIGHT

// Final state: user1, but should be user2!
// Race condition!
```

### Solution: Cleanup with AbortController

Covered in next section...

---

## AbortController Pattern

### What is AbortController?

AbortController **cancels fetch requests** when effect cleans up.

```jsx
function Component({ userId }) {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    const abortController = new AbortController();
    
    fetch(`/api/users/${userId}`, {
      signal: abortController.signal  // Pass abort signal
    })
      .then(r => r.json())
      .then(data => {
        setUser(data);  // Won't run if aborted
      })
      .catch(error => {
        if (error.name === 'AbortError') {
          // Request was cancelled - don't update state
          return;
        }
        // Real error, handle it
      });
    
    // Cleanup: abort request if effect cleans up
    return () => {
      abortController.abort();
    };
  }, [userId]);
  
  return <div>{user?.name}</div>;
}

// Timeline:
// userId = 1: fetch user 1, signal = signal1
// Before response: userId = 2
// Cleanup: abortController.abort() → signal1 aborts
// Fetch user 1 cancelled
// userId = 2: fetch user 2, signal = signal2
// User 2 response arrives → setUser(user2) ✓ CORRECT!
```

### Why AbortController Helps

```javascript
// Without AbortController:
// 1. Start request 1
// 2. Dependency changes
// 3. Start request 2
// 4. Request 1 completes (race condition!)
// 5. setUser(user1) ❌ WRONG STATE

// With AbortController:
// 1. Start request 1 with signal1
// 2. Dependency changes
// 3. signal1.abort() → request 1 cancelled
// 4. Start request 2 with signal2
// 5. Request 1 fails (AbortError)
// 6. Request 2 completes
// 7. setUser(user2) ✓ CORRECT STATE
```

### Modern Fetch with AbortController

```jsx
function useFetch(url) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const abortController = new AbortController();
    
    (async () => {
      try {
        setLoading(true);
        
        const response = await fetch(url, {
          signal: abortController.signal
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const json = await response.json();
        setData(json);
        setError(null);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err);
          setData(null);
        }
      } finally {
        setLoading(false);
      }
    })();
    
    return () => abortController.abort();
  }, [url]);
  
  return { data, error, loading };
}

// Usage:
function Component({ userId }) {
  const { data: user, loading, error } = useFetch(`/api/users/${userId}`);
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  return <div>{user.name}</div>;
}
```

---

## Missing Dependencies

### The Most Common Bug

```jsx
// ❌ WRONG: Missing dependency (ESLint warns)
function Component() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(count + 1);  // Uses count
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);  // Missing count!
}

// What happens:
// Mount: count = 0, effect runs
// Timer created, closes over count = 0
// count state becomes 1, 2, 3...
// But timer still has count = 0!
// Timer runs: setCount(0 + 1) = setCount(1)
// Every timer tick: setCount(1)
// count never goes above 1!

// ✅ CORRECT: Include dependency
function Component() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(count + 1);
    }, 1000);
    
    return () => clearInterval(timer);
  }, [count]);  // Include count!
}

// Mount: count = 0, effect runs
// Timer created, closes over count = 0
// count becomes 1, dependency changed
// Cleanup: clear old timer
// Effect runs again: count = 1, effect runs
// New timer created, closes over count = 1
// count becomes 2, dependency changed
// Cleanup: clear old timer
// Effect runs again: count = 2, effect runs
// Keeps incrementing!

// But we can optimize...
```

### Fixing Without Adding Dependency

```jsx
// ✅ BETTER: Functional update (no dependency needed)
function Component() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(c => c + 1);  // Functional update!
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);  // Empty deps OK!
}

// Functional update gets current count
// No dependency needed!
// Timer runs: setCount(prevCount => prevCount + 1)
// Always uses latest count
```

### ESLint Help

```javascript
// ESLint rule: react-hooks/exhaustive-deps

// ❌ Warns about missing dependency
useEffect(() => {
  console.log(count);
}, []);  // ← Warning: count is missing

// ✅ Correct
useEffect(() => {
  console.log(count);
}, [count]);  // ← OK

// Safe cases (no warning):
useEffect(() => {
  // setState itself is stable
  setCount(c => c + 1);
}, []);  // OK - setState doesn't change

// setData, setUser, etc. are all stable
// Don't need to include them in deps
```

---

## useLayoutEffect vs useEffect

### Timing Difference

```jsx
function Component() {
  useLayoutEffect(() => {
    console.log('1. useLayoutEffect (before paint)');
  }, []);
  
  useEffect(() => {
    console.log('2. useEffect (after paint)');
  }, []);
  
  return <div>Component</div>;
}

// Output:
// "1. useLayoutEffect (before paint)"
// (Browser paints DOM)
// "2. useEffect (after paint)"

// useLayoutEffect runs BEFORE browser paints
// useEffect runs AFTER browser paints
```

### When to Use Each

```jsx
// ✅ USE useLayoutEffect for:
// - Measuring DOM (offsetWidth, offsetHeight)
// - Adjusting layout based on measurements
// - Preventing visual flicker
// - Reading DOM before paint

function Component() {
  useLayoutEffect(() => {
    const height = element.offsetHeight;  // Measure
    element.style.transform = `scale(${height / 100})`;  // Adjust
    // All before browser paints!
  }, []);
}

// ✅ USE useEffect for:
// - API calls
// - Setting state
// - Event listeners
// - setTimeout/setInterval
// - Most side effects!

function Component() {
  useEffect(() => {
    fetch('/api/data').then(data => setData(data));
  }, []);
}

// useEffect is more performant (doesn't block paint)
// Use it unless you specifically need useLayoutEffect
```

### Performance Impact

```jsx
// ❌ WRONG: useLayoutEffect for everything
function Component() {
  useLayoutEffect(() => {
    fetch('/api/data').then(data => setData(data));
  }, []);
  
  // useLayoutEffect blocks browser from painting
  // User sees blank screen while fetch happens
  // BAD!
}

// ✅ CORRECT: useEffect for side effects
function Component() {
  useEffect(() => {
    fetch('/api/data').then(data => setData(data));
  }, []);
  
  // useEffect after paint
  // User sees component while fetch happens
  // GOOD!
}
```

---

## Common Patterns

### Pattern 1: Fetch Data

```jsx
function Component({ userId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const abortController = new AbortController();
    
    const fetch Data = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/users/${userId}`, {
          signal: abortController.signal
        });
        if (!response.ok) throw new Error('Failed to fetch');
        
        const json = await response.json();
        setData(json);
        setError(null);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err);
        }
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
    
    return () => abortController.abort();
  }, [userId]);
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  return <div>{data?.name}</div>;
}
```

### Pattern 2: Event Listener

```jsx
function Component() {
  useEffect(() => {
    const handleResize = () => {
      // Handle resize
      console.log('Resized');
    };
    
    window.addEventListener('resize', handleResize);
    
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);
  
  return <div>Window listener set up</div>;
}
```

### Pattern 3: localStorage Sync

```jsx
function Component() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'light';
  });
  
  // Keep localStorage in sync with state
  useEffect(() => {
    localStorage.setItem('theme', theme);
  }, [theme]);
  
  return (
    <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
      Theme: {theme}
    </button>
  );
}
```

### Pattern 4: Subscription

```jsx
function Component() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    // Subscribe to external source
    const unsubscribe = store.subscribe((value) => {
      setCount(value);
    });
    
    // Cleanup: unsubscribe
    return () => unsubscribe();
  }, []);
  
  return <div>{count}</div>;
}
```

---

## Common Pitfalls

### Pitfall 1: Missing Dependencies

```jsx
// ❌ WRONG: Missing dependency
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    console.log(count);
  }, []);  // Missing count!
  
  // Logs 0 always, even if count changes
}

// ✅ CORRECT: Include dependency
function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    console.log(count);
  }, [count]);  // Include count!
  
  // Logs whenever count changes
}
```

### Pitfall 2: No Cleanup for Subscriptions

```jsx
// ❌ WRONG: No cleanup
function Example() {
  useEffect(() => {
    store.subscribe((value) => {
      // Subscribe forever
    });
  }, []);
  
  // Every mount: new subscription
  // No cleanup: old subscriptions never removed
  // MEMORY LEAK!
}

// ✅ CORRECT: Cleanup subscription
function Example() {
  useEffect(() => {
    const unsubscribe = store.subscribe((value) => {
      // Handle value
    });
    
    return () => unsubscribe();
  }, []);
  
  // Cleanup: unsubscribe
  // No leak!
}
```

### Pitfall 3: Not Handling Race Conditions

```jsx
// ❌ WRONG: Race condition
function Example({ userId }) {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then(r => r.json())
      .then(data => setUser(data));  // Might be stale!
  }, [userId]);
}

// ✅ CORRECT: Use AbortController
function Example({ userId }) {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    const abortController = new AbortController();
    
    fetch(`/api/users/${userId}`, {
      signal: abortController.signal
    })
      .then(r => r.json())
      .then(data => setUser(data));
    
    return () => abortController.abort();
  }, [userId]);
}
```

---

## Interview Questions

### Q1: What's the difference between useEffect and useLayoutEffect?

```
Answer:
- useEffect: Runs AFTER browser paints (async)
- useLayoutEffect: Runs BEFORE browser paints (sync)

useEffect is more performant (doesn't block paint).
useLayoutEffect for measuring DOM or preventing flicker.

useEffect is safer default choice.
```

### Q2: How do you prevent race conditions?

```
Answer: Use AbortController to cancel old requests.

useEffect(() => {
  const abortController = new AbortController();
  
  fetch(url, { signal: abortController.signal })
    .then(handleResponse)
    .catch(handleError);
  
  return () => abortController.abort();
}, [url]);

Cleanup aborts old request when dependency changes.
Prevents stale state updates.
```

### Q3: What's the difference between missing dependencies and infinite loops?

```
Missing dependency:
- Effect uses state but doesn't list it
- State becomes stale
- Effect uses old value
- Bug! But no infinite loop

Infinite loop:
- Effect updates dependency value
- Dependency changes → effect runs
- Effect updates dependency again
- Infinite loop!

Example of infinite:
useEffect(() => {
  setCount(count + 1);  // Updates count
}, [count]);  // Depends on count
// count changes → effect runs → count changes → ...
```

### Q4: Why do we need cleanup functions?

```
Answer: Prevent memory leaks and side effects.

useEffect(() => {
  const subscription = subscribe();
  const listener = addEventListener();
  const timer = setTimeout();
  
  return () => {
    subscription.unsubscribe();  // Cleanup
    removeEventListener();        // Cleanup
    clearTimeout(timer);          // Cleanup
  };
}, []);

Without cleanup:
- Every mount creates new subscription
- Never unsubscribed
- Memory piles up
- LEAK!

With cleanup:
- Cleanup runs before next effect or unmount
- Resources properly released
- No leak!
```

---

## Resources

- **useEffect Documentation:** https://react.dev/reference/react/useEffect
- **useLayoutEffect:** https://react.dev/reference/react/useLayoutEffect
- **A Complete Guide to useEffect:** https://overreacted.io/a-complete-guide-to-useeffect/
- **Race Conditions in React:** https://kentcdodds.com/blog/understanding-react-useeffect
- **AbortController API:** https://developer.mozilla.org/en-US/docs/Web/API/AbortController
- **Lifecycle vs Effects:** https://react.dev/learn/lifecycle-of-reactive-effect

---

**Next:** [Part 3.4: useContext Hook](./03-useContext-hook.md) - Master context for prop drilling solutions
