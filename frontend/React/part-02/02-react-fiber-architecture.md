# Part 2.4: React Fiber Architecture

## What You'll Learn

- What Fiber architecture is and why it exists
- The problem React 15 had (can't interrupt rendering)
- How Fibers solve the problem
- Work units and scheduling
- Priority levels and task scheduling
- Time slicing (breaking work into chunks)
- Incremental rendering concept
- How hooks integrate with Fiber
- Practical implications for developers

---

## Table of Contents

1. [The React 15 Problem](#the-react-15-problem)
2. [Fiber Concept](#fiber-concept)
3. [Work Units and Scheduling](#work-units-and-scheduling)
4. [Priority Levels](#priority-levels)
5. [Time Slicing](#time-slicing)
6. [Incremental Rendering](#incremental-rendering)
7. [Hooks and Fiber](#hooks-and-fiber)
8. [Concurrent Features](#concurrent-features)
9. [Practical Implications](#practical-implications)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Resources](#resources)

---

## The React 15 Problem

### React 15 Rendering

React 15 rendered synchronously:

```
Component.render() → Reconciliation → Real DOM update → Next component

All at once, can't interrupt!
```

### The Problem Visualized

```
Timeline:
0ms ────────────────────────────────────── 20ms
     React rendering (can't interrupt)
     ├─ Component A
     ├─ Component B
     ├─ Component C
     └─ Update DOM

User interaction (click) happens at 5ms:
0ms ──[Click!]──────────────────────────── 20ms
     React rendering (still going!)
     ├─ Component A
     ├─ Component B
     ├─ Component C
     └─ Update DOM
     
Result: User sees delayed response! (20ms not 5ms)
This feels LAGGY
```

### Real Impact

```javascript
// Large render takes 20ms
// User clicks at 5ms
// User must wait another 15ms for response

// At 60 FPS, each frame = 16.67ms
// If render takes 20ms, browser can't update UI (drops frame)
// User sees janky, laggy interaction
```

### Why Not Interrupt?

```javascript
// Stack-based rendering (React 15)
// When you call a function, it goes on the stack
// Can't pause a function mid-way in traditional JavaScript

function renderApp(component) {
  const vdom = component.render();  // Can't pause here
  reconcile(vdom);                  // Can't pause here
  updateDOM(vdom);                  // Can't pause here
  // Stack unwinds only when all done
}

// JavaScript runs until function completes
// No way to say "hey, pause rendering, browser needs to paint"
```

---

## Fiber Concept

### What is a Fiber?

A Fiber is a **unit of work that React can start, pause, and resume**.

```javascript
// Traditional function call
function render() {
  // All or nothing
  reconcile(vdom);
  updateDOM(vdom);
}
// Can't pause!

// Fiber approach
const fiber = {
  type: 'Component',
  key: null,
  parent: null,
  child: null,
  sibling: null,
  
  // Work to do
  work: () => { /* reconcile */ },
  
  // Can be paused and resumed!
}

// React can:
// 1. Do some work on fiber
// 2. Pause
// 3. Let browser paint
// 4. Resume work on same fiber
```

### Fiber Architecture

```
Before Fiber (Tree structure - stack):
App
├─ Header
├─ Content
│  ├─ Item 1
│  ├─ Item 2
│  └─ Item 3
└─ Footer

Rendering: App → Header → Content → Item1 → Item2 → Item3 → Footer
All synchronous, can't interrupt!

After Fiber (Linked list structure - pausable):
App ── Header ── Content ── Item1 ── Item2 ── Item3 ── Footer
│       ↓
└─ Can traverse this list, do work on one node
└─ Pause and resume at any point!
```

### Key Differences

```javascript
// React 15 (Stack):
// - Recursive component tree traversal
// - Can't pause
// - All or nothing

// React 16+ (Fiber):
// - Linked list of work units
// - Can pause and resume
// - Incremental work

// Same end result, different execution strategy
```

---

## Work Units and Scheduling

### What is Work?

In React, "work" is:

```javascript
// Work = Reconciliation
// - Call component function
// - Create Virtual DOM
// - Compare with old VDOM
// - Identify changes

// NOT work = Real DOM updates
// - Applying changes to real DOM is done in batch
// - In "commit" phase, all at once

// Fiber manages reconciliation work (pausable)
// Commit phase (applying to DOM) is not pausable (must be atomic)
```

### Work Scheduling

```
React's Work Scheduling:

1. Schedule Phase
   ├─ User interaction / state change
   └─ Creates work to do

2. Render Phase (can be interrupted)
   ├─ Calls component functions
   ├─ Reconciles Virtual DOM
   ├─ Identifies changes
   └─ Can pause here if browser needs frame

3. Commit Phase (cannot be interrupted)
   ├─ Apply changes to real DOM
   ├─ Run useLayoutEffect
   ├─ Run useEffect cleanup
   ├─ Run new useEffect
   └─ Must complete atomically

4. Passive Phase
   ├─ Run remaining cleanup
   └─ Other non-critical work
```

### Example: Fiber Work

```javascript
// Component that needs rendering
function TodoApp() {
  const [todos, setTodos] = useState([]);
  
  return (
    <div>
      {todos.map(todo => <TodoItem key={todo.id} {...todo} />)}
    </div>
  );
}

// React creates fibers for each unit:
const fibers = [
  {
    type: TodoApp,
    // Work: Call TodoApp function
    // Identify child fibers needed
  },
  {
    type: 'div',
    // Work: Reconcile div element
  },
  {
    type: TodoItem,
    key: 1,
    // Work: Call TodoItem function
  },
  {
    type: TodoItem,
    key: 2,
    // Work: Call TodoItem function
  },
  // ... more fibers
];

// React schedules work on these fibers
// Can pause between any two fibers
// Allows browser to paint in between
```

---

## Priority Levels

### Why Multiple Priorities?

```
Not all work is equally urgent!

High priority (urgent):
- User input (typing, clicking)
- Animations
- Hover states

Normal priority (routine):
- Data fetching
- Component updates
- Effects

Low priority (not urgent):
- Background updates
- Pre-fetching
- Logging

React 18 lets you specify!
```

### Priority Levels in React

```javascript
// Automatic priorities
function Component() {
  // High priority (user interaction)
  const handleClick = () => {
    setCount(count + 1);  // High priority
  };
  
  // Normal priority (effect)
  useEffect(() => {
    fetchData();  // Normal priority
  }, []);
  
  // Low priority (transition)
  const handleSearch = () => {
    startTransition(() => {
      setSearchResults(results);  // Low priority
    });
  };
}

// Manual priority control
import { flushSync } from 'react-dom';

function Component() {
  const handleClick = () => {
    // Highest priority - execute synchronously
    flushSync(() => {
      setCritical(value);
    });
    
    // Rest of handler runs after update completes
    // Rarely needed!
  };
}
```

### Priority Example: Search

```javascript
function SearchComponent() {
  const [input, setInput] = useState('');
  const [results, setResults] = useState([]);
  const [isPending, setIsPending] = useState(false);
  
  const handleSearch = (e) => {
    const value = e.target.value;
    
    // High priority: Update input immediately (user sees typing)
    setInput(value);
    
    // Low priority: Update results (can be interrupted)
    startTransition(() => {
      // This low-priority update can be interrupted
      // If user types again, React drops old search and starts new one
      setResults(filterResults(value));
      setIsPending(false);
    });
    
    setIsPending(true);
  };
  
  return (
    <div>
      <input value={input} onChange={handleSearch} />
      {isPending && <Spinner />}
      <Results items={results} />
    </div>
  );
}

// User types: "a"
// - High priority: Input shows "a" instantly
// - Low priority: Start searching for "a"

// User types: "ab" (before "a" search completes)
// - High priority: Input shows "ab" instantly
// - Low priority: React abandons "a" search, starts "ab" search
// - Result: No wasted work on "a"!
```

---

## Time Slicing

### What is Time Slicing?

Time slicing means **breaking rendering work into small chunks** that fit within a frame budget.

```
Without time slicing (40ms work):
0ms ────────────────────────── 40ms ──────────────────────── 80ms
     React work (blocking)         React work (blocking)
     User can't interact!          User can't interact!

With time slicing (5ms chunks):
0ms ── 5ms ── 10ms ── 15ms ── 20ms ── 25ms ── 30ms ── 35ms ── 40ms
    Work  Paint Work  Paint Work  Paint Work  Paint Work  Paint
    ✓     ✓     ✓     ✓     ✓     ✓     ✓     ✓     ✓     ✓
    User can interact between paints!
```

### Frame Budget

At 60 FPS:

```
Each frame = 16.67ms

Ideal breakdown:
├─ React render work: 5ms (leave time for other stuff)
├─ Browser reflow/repaint: 8ms
├─ Browser compositing: 2ms
└─ Buffer: 1.67ms

If React takes more than ~5ms, frame gets dropped!
User sees jank!
```

### Time Slicing Example

```javascript
function BusyComponent({ items }) {
  // This component needs to render 1000 items
  // Takes ~50ms total
  
  // Without time slicing:
  // Returns: All 1000 items at once
  // Takes 50ms → drops frames → jank
  
  // With time slicing:
  // React breaks work:
  // - 0-5ms: Render items 1-100
  // - Paint frame
  // - 16-21ms: Render items 101-200
  // - Paint frame
  // - 32-37ms: Render items 201-300
  // - etc.
  
  // User sees progressive rendering
  // While first items show, React works on next batch
  // Feels responsive!
  
  return (
    <ul>
      {items.map(item => (
        <li key={item.id}>{item.name}</li>
      ))}
    </ul>
  );
}
```

---

## Incremental Rendering

### What is Incremental Rendering?

Incremental rendering means **rendering happens in stages, not all at once**.

```
Old approach (React 15):
State change → Full render → Full commit → Done
             (all or nothing)

New approach (React 16+):
State change → Render phase (pausable)
           → Commit phase (atomic)
           → Done

Benefits:
- Can show partial UI faster
- Can prioritize important updates
- Can cancel lower-priority updates
```

### Suspense and Incremental Rendering

```jsx
// Concurrent rendering with Suspense
import { lazy, Suspense } from 'react';

const HeavyComponent = lazy(() => import('./Heavy'));

function App() {
  return (
    <div>
      <Header />
      <Suspense fallback={<Spinner />}>
        <HeavyComponent />
      </Suspense>
      <Footer />
    </div>
  );
}

// Rendering increments:
// 1. Render Header + Footer immediately
// 2. Show Spinner while HeavyComponent loads
// 3. When HeavyComponent ready, render and show it

// User sees partial UI faster!
// Not waiting for everything to be ready
```

### useTransition for Incremental Updates

```jsx
function SearchResults({ query }) {
  const [results, setResults] = useState([]);
  const [isPending, setIsPending] = useState(false);
  
  useEffect(() => {
    setIsPending(true);
    
    // Heavy filtering/sorting
    const filtered = expensiveFilter(query);
    
    setResults(filtered);
    setIsPending(false);
  }, [query]);
  
  return (
    <div>
      {isPending && <Spinner />}
      {results.map(r => <Result key={r.id} {...r} />)}
    </div>
  );
}

// Incremental update with startTransition:
function SearchComponent() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isPending, startTransition] = useTransition();
  
  const handleChange = (e) => {
    const value = e.target.value;
    
    // High priority: Show user typed
    setQuery(value);
    
    // Low priority: Update results incrementally
    startTransition(() => {
      const filtered = expensiveFilter(value);
      setResults(filtered);
    });
  };
  
  return (
    <div>
      <input value={query} onChange={handleChange} />
      {isPending && <Spinner />}
      {results.map(r => <Result key={r.id} {...r} />)}
    </div>
  );
}

// Rendering happens incrementally:
// 1. Input updates immediately (high priority)
// 2. Results update starts (low priority)
// 3. React can pause filtering, let user type more
// 4. When user stops typing, complete the update
```

---

## Hooks and Fiber

### Why Hooks Needed Fiber

```javascript
// Hooks depend on call order
function Component() {
  const [count, setCount] = useState(0);      // Hook 1
  const [text, setText] = useState('');        // Hook 2
  const [items, setItems] = useState([]);      // Hook 3
  
  // React tracks: Hook 1, Hook 2, Hook 3 in this component
  // Must be called in same order every render!
}

// With Fiber, React can:
// 1. Keep track of which component (fiber) is rendering
// 2. Keep a list of hooks for that fiber
// 3. Call hooks in order
// 4. Store state in that fiber

// Without Fiber, hooks would be impossible!
// Need to know which component is currently rendering
```

### Hook Storage in Fiber

```javascript
// Each fiber has a hooks queue:
const fiber = {
  type: Component,
  
  // Hooks state storage
  hooks: [
    {
      state: 0,
      queue: [/* pending updates */]
    },
    {
      state: '',
      queue: [/* pending updates */]
    },
    {
      state: [],
      queue: [/* pending updates */]
    }
  ],
  
  // Component instance
  component: Component,
  
  // Relationships
  parent: parentFiber,
  child: childFiber,
  sibling: siblingFiber
};
```

### Hook Execution Flow

```javascript
function Counter() {
  const [count, setCount] = useState(0);      // Hook index 0
  const effect = useEffect(() => { ... }, []); // Hook index 1
  const text = useRef('');                     // Hook index 2
}

// Render 1:
// 1. React identifies fiber for Counter
// 2. Calls Counter function
// 3. Counter calls useState
//    - React: "Hook 0 for this fiber"
//    - Returns state and setState
// 4. Counter calls useEffect
//    - React: "Hook 1 for this fiber"
//    - Registers effect
// 5. Counter calls useRef
//    - React: "Hook 2 for this fiber"
//    - Returns ref object
// 6. Counter returns JSX

// Render 2 (state changed):
// 1. React identifies same fiber for Counter
// 2. Calls Counter function again
// 3. Counter calls useState
//    - React: "Hook 0 for this fiber"
//    - Returns updated state and setState
// 4. Counter calls useEffect
//    - React: "Hook 1 for this fiber"
//    - Sees no dependency change
//    - Doesn't run effect
// 5. Counter calls useRef
//    - React: "Hook 2 for this fiber"
//    - Returns same ref object
// 6. Counter returns JSX
```

---

## Concurrent Features

### What are Concurrent Features?

Concurrent features let React **render multiple versions of the UI** without blocking.

```javascript
// Concurrent rendering in action:
function App() {
  // Render version 1: Initial state
  // Render version 2: User input
  // Render version 3: Data fetched
  
  // React can work on multiple versions
  // Commit the best one when ready
}

// Benefits:
// - Can prioritize important updates
// - Can retry failed updates
// - Can show fallback UI while loading
```

### useTransition for Concurrent Updates

```jsx
function TabSelector() {
  const [tab, setTab] = useState('home');
  const [isPending, startTransition] = useTransition();
  
  const selectTab = (nextTab) => {
    // Concurrent rendering!
    // React starts rendering new tab
    // But doesn't commit yet
    // User can interrupt by clicking again
    
    startTransition(() => {
      setTab(nextTab);
    });
  };
  
  return (
    <div>
      <button 
        onClick={() => selectTab('home')}
        style={{ opacity: tab === 'home' && !isPending ? 1 : 0.5 }}
      >
        Home
      </button>
      <button 
        onClick={() => selectTab('about')}
        style={{ opacity: tab === 'about' && !isPending ? 1 : 0.5 }}
      >
        About
      </button>
      <TabContent tab={tab} isPending={isPending} />
    </div>
  );
}

// User experience:
// 1. Click "About" → starts rendering About tab
// 2. Before About finishes → click "Home"
// 3. React abandons About, starts rendering Home
// 4. No wasted work on About!
```

### useDeferredValue for Concurrent Values

```jsx
function SearchApp({ initialQuery }) {
  const [query, setQuery] = useState(initialQuery);
  const deferredQuery = useDeferredValue(query);
  
  // query updates immediately (user sees typing)
  // deferredQuery updates at lower priority (results update)
  
  return (
    <div>
      <input 
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {/* Re-render only when deferredQuery changes */}
      <SearchResults query={deferredQuery} />
    </div>
  );
}

// Without useDeferredValue:
// - Input and results both update immediately
// - Heavy filtering blocks input
// - Input feels laggy

// With useDeferredValue:
// - Input updates immediately
// - Results update deferred (low priority)
// - Input feels responsive!
```

---

## Practical Implications

### For Your Code

```jsx
// 1. Hooks must be in same order
function ✅ Good() {
  const [count, setCount] = useState(0);
  useEffect(() => { /* ... */ }, []);
  return <div>{count}</div>;
}

function ❌ Bad() {
  if (someCondition) {
    const [count, setCount] = useState(0);  // Conditional hook!
  }
  return <div></div>;
}

// 2. Concurrent features help with responsiveness
function SearchComponent() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isPending, startTransition] = useTransition();
  
  return (
    <div>
      <input 
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);  // High priority
          startTransition(() => {      // Low priority
            setResults(search(e.target.value));
          });
        }}
      />
      {isPending && <Spinner />}
      <ul>
        {results.map(r => <li key={r.id}>{r.name}</li>)}
      </ul>
    </div>
  );
}

// 3. Component quality depends on render efficiency
// If component's render is expensive,
// it blocks fiber scheduling!

function ❌ ExpensiveRender() {
  // Heavy calculation during render
  const bigArray = generateArrayOfSize(1000000);
  bigArray.sort();  // Blocking!
  
  return <div>{bigArray.length}</div>;
}

function ✅ OptimizedRender() {
  const [bigArray, setBigArray] = useState(null);
  
  // Heavy work in effect, not render
  useEffect(() => {
    const array = generateArrayOfSize(1000000);
    array.sort();
    setBigArray(array);
  }, []);
  
  return <div>{bigArray?.length}</div>;
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Using useTransition

```jsx
// For non-blocking updates
function TabComponent() {
  const [tab, setTab] = useState('home');
  const [isPending, startTransition] = useTransition();
  
  const handleTabChange = (nextTab) => {
    startTransition(() => {
      setTab(nextTab);
    });
  };
  
  return (
    <div>
      <button 
        onClick={() => handleTabChange('home')}
        disabled={isPending && tab === 'about'}
      >
        Home
      </button>
      <button 
        onClick={() => handleTabChange('about')}
        disabled={isPending && tab === 'home'}
      >
        About
      </button>
      {isPending ? <Spinner /> : <TabContent tab={tab} />}
    </div>
  );
}
```

### Pattern 2: Using useDeferredValue

```jsx
// For debouncing without setTimeout
function AutocompleteComponent() {
  const [input, setInput] = useState('');
  const deferredInput = useDeferredValue(input);
  
  return (
    <div>
      <input 
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type to search..."
      />
      {/* This only re-renders when deferredInput changes */}
      <Results query={deferredInput} />
    </div>
  );
}
```

### Pattern 3: Efficient Component Design

```jsx
// ✅ Keep renders fast and pure
function Item({ id, name, isSelected }) {
  return (
    <li style={{ fontWeight: isSelected ? 'bold' : 'normal' }}>
      {name}
    </li>
  );
}

// ❌ Heavy work during render
function Item({ id, name, isSelected }) {
  const processed = expensiveTransformation(name);  // Blocks!
  return <li>{processed}</li>;
}
```

---

## Common Pitfalls

### Pitfall 1: Conditional Hooks

```jsx
// ❌ Hook call order changes
function Component({ showEmail }) {
  if (showEmail) {
    const [email, setEmail] = useState('');  // Conditional!
  }
  const [name, setName] = useState('');
}

// First render: email hook, then name hook
// Second render (showEmail changes): only name hook
// Hook indices don't match! → Bug

// ✅ Fixed
function Component({ showEmail }) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  
  if (!showEmail) {
    // Don't use email state
  }
}
```

### Pitfall 2: Misunderstanding useTransition

```jsx
// ❌ Wrong: useTransition doesn't defer state
function Component() {
  const [state, setState] = useState(0);
  const [isPending, startTransition] = useTransition();
  
  const handler = () => {
    startTransition(() => {
      setState(state + 1);
    });
    console.log(state);  // Still logs old state!
  };
}

// ✅ Correct: Use it for non-blocking updates
function Component() {
  const [results, setResults] = useState([]);
  const [isPending, startTransition] = useTransition();
  
  const handleSearch = (query) => {
    startTransition(() => {
      // This expensive update won't block
      setResults(heavyFilter(query));
    });
  };
}
```

### Pitfall 3: Forgetting useCallback with Fibers

```jsx
// With fibers, unnecessary re-renders still matter
function List({ items }) {
  // ❌ Creates new handler every render
  return (
    <div>
      {items.map(item => (
        <Item 
          key={item.id}
          onDelete={() => deleteItem(item.id)}  // New function
        />
      ))}
    </div>
  );
}

// Even though fibers help with scheduling,
// still causes child re-renders

// ✅ Memoize the handler
function List({ items }) {
  const handleDelete = useCallback((id) => {
    deleteItem(id);
  }, []);
  
  return (
    <div>
      {items.map(item => (
        <Item 
          key={item.id}
          onDelete={handleDelete}
        />
      ))}
    </div>
  );
}
```

---

## Resources

- **React Fibers Official:** https://github.com/acdlite/react-fiber-architecture
- **Concurrent Rendering:** https://react.dev/reference/react/useTransition
- **Lin Clark's Explanation:** https://www.youtube.com/watch?v=ZCuYPiUIONs
- **Dan Abramov on Fibers:** https://overreacted.io/
- **Fiber Implementation Details:** https://indepth.dev/posts/1008/inside-fiber-in-depth-overview-of-new-reconciliation-engine-in-react

---

**Next:** [Part 2.5: React Rendering Phases](./02-react-rendering-phases.md) - Understand render phase vs commit phase and batching in React 18+
