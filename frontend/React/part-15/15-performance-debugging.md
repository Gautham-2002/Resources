# Part 15.3: Performance Debugging

## What You'll Learn

- Identifying performance bottlenecks
- Using React Profiler effectively
- Measuring performance metrics
- Memory leaks detection
- CPU profiling techniques
- Web Vitals measurement
- Performance optimization techniques
- Interview questions

---

## Table of Contents

1. [Performance Metrics](#performance-metrics)
2. [React Profiler Mastery](#react-profiler-mastery)
3. [Identifying Bottlenecks](#identifying-bottlenecks)
4. [Memory Leak Detection](#memory-leak-detection)
5. [CPU Profiling](#cpu-profiling)
6. [Web Vitals](#web-vitals)
7. [Performance Tools](#performance-tools)
8. [Optimization Techniques](#optimization-techniques)
9. [Common Patterns](#common-patterns)
10. [Interview Questions](#interview-questions)
11. [Resources](#resources)

---

## Performance Metrics

### Key Metrics

```javascript
// Core Web Vitals (Google's metrics for good UX):

// 1. Largest Contentful Paint (LCP)
// - When largest content element becomes visible
// - Goal: < 2.5 seconds
// - Measures: perceived load speed

// 2. First Input Delay (FID)
// - Time from user input to browser response
// - Goal: < 100 milliseconds
// - Measures: interactivity

// 3. Cumulative Layout Shift (CLS)
// - Unexpected layout shifts
// - Goal: < 0.1
// - Measures: visual stability

// Better metrics in React 19+:
// - Interaction to Next Paint (INP)
// - Helps measure responsiveness
```

### Measuring Performance

```jsx
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

// Track Core Web Vitals
function reportWebVitals(metric) {
  console.log(`${metric.name}:`, metric.value);
  
  // Send to analytics
  fetch('/api/analytics', {
    method: 'POST',
    body: JSON.stringify(metric)
  });
}

getCLS(reportWebVitals);   // Cumulative Layout Shift
getFID(reportWebVitals);   // First Input Delay
getFCP(reportWebVitals);   // First Contentful Paint
getLCP(reportWebVitals);   // Largest Contentful Paint
getTTFB(reportWebVitals);  // Time to First Byte

// Example output:
// LCP: 1.5 (good)
// FID: 50 (good)
// CLS: 0.05 (good)
```

---

## React Profiler Mastery

### Step-by-Step Profiling

```jsx
function SlowComponent({ items }) {
  // Intentionally slow
  const processed = items.map(item => {
    let result = item;
    for (let i = 0; i < 1000000; i++) {
      result = result * Math.random();
    }
    return result;
  });
  
  return <div>{processed.length} items</div>;
}

function App() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <button onClick={() => setCount(count + 1)}>
        Increment ({count})
      </button>
      <SlowComponent items={[1, 2, 3, 4, 5]} />
    </div>
  );
}

// To profile:
// 1. Open DevTools Profiler tab
// 2. Click record button (red circle)
// 3. Click button several times quickly
// 4. Stop recording
// 5. View timeline

// You see:
// ┌─ App: 50ms
// │  ├─ button element
// │  └─ SlowComponent: 49ms (bottleneck!)
```

### Reading Flamegraph

```javascript
// Flamegraph shows render time:
//
// ┌────────────────────────────────┐
// │ App: 50ms                      │  Height = render time
// ├──────────┬─────────────────────┤
// │ Button   │ SlowComponent: 49ms │
// │  0.5ms   │                     │
// └──────────┴─────────────────────┘
//
// What it tells you:
// - App took 50ms to render
// - Button only took 0.5ms
// - SlowComponent took 49ms
// - SlowComponent is the bottleneck!

// How to use:
// 1. Look for longest bars
// 2. Click on them
// 3. See component details
// 4. Check what caused render
// 5. Optimize that part
```

### Comparing Renders

```javascript
// Profile before and after optimization

// Before:
// ┌─ App: 50ms
// └─ SlowComponent: 49ms

// Optimization: Add useMemo
const processed = useMemo(() => {
  return items.map(item => {
    let result = item;
    for (let i = 0; i < 1000000; i++) {
      result = result * Math.random();
    }
    return result;
  });
}, [items]);

// After:
// ┌─ App: 1ms
// └─ SlowComponent: 0.5ms (memoized, skipped)

// Result: 50x faster!
```

---

## Identifying Bottlenecks

### Finding Unnecessary Re-renders

```jsx
function Parent() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <button onClick={() => setCount(count + 1)}>
        Count: {count}
      </button>
      {/* This shouldn't re-render when count changes */}
      <ExpensiveList />
    </div>
  );
}

function ExpensiveList() {
  // Expensive to render
  const items = Array(1000).fill(0).map(i => <div>Item {i}</div>);
  return <div>{items}</div>;
}

// Problem: Clicking button re-renders ExpensiveList
// even though its props didn't change

// Solution: Memoize ExpensiveList
const ExpensiveList = React.memo(function ExpensiveList() {
  const items = useMemo(() => (
    Array(1000).fill(0).map(i => <div>Item {i}</div>)
  ), []);
  
  return <div>{items}</div>;
});

// Now:
// - Clicking button only re-renders Parent
// - ExpensiveList is skipped
// - Much faster!
```

### Finding Expensive Calculations

```jsx
function DataProcessor({ data }) {
  // ❌ This runs on EVERY render
  const sorted = data
    .sort((a, b) => a.name.localeCompare(b.name))
    .filter(item => item.active)
    .map(item => ({ ...item, processed: true }));
  
  return <div>{sorted.length} items</div>;
}

// Profiler shows: 100ms render
// Clicking button that changes unrelated state: still 100ms
// The problem: sorting/filtering every render!

// ✅ Fix: Memoize computation
const sorted = useMemo(() => {
  return data
    .sort((a, b) => a.name.localeCompare(b.name))
    .filter(item => item.active)
    .map(item => ({ ...item, processed: true }));
}, [data]);

// Now: 0.5ms render (when data unchanged)
// Massive improvement!
```

### Render Waterfall

```javascript
// Profiler shows render order:
//
// Timeline:
// |-- App render (5ms)
//     |-- Header render (1ms)
//     |-- Sidebar render (2ms)
//     |-- Content render (2ms)
//         |-- List render (1.5ms)
//         |-- Item render (0.5ms x 20 items = 10ms)
//
// This is waterfall - sequential
// Item renders wait for List to finish

// Some can't be optimized (parent must render first)
// But if items render slowly individually, optimize items
```

---

## Memory Leak Detection

### Finding Memory Leaks

```jsx
function ComponentWithLeak() {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    // Forgot to clean up!
    const interval = setInterval(() => {
      console.log('Still running...');
    }, 1000);
    
    return () => {
      // This is what's MISSING!
      // clearInterval(interval);
    };
  }, []);
  
  // If this component mounts/unmounts 10 times:
  // 10 intervals running simultaneously
  // Memory grows continuously
  // Browser gets slower and slower
}

// ✅ FIX: Clean up resources
useEffect(() => {
  const interval = setInterval(() => {
    console.log('Running...');
  }, 1000);
  
  return () => {
    clearInterval(interval);  // Clean up!
  };
}, []);
```

### Memory Profiler

```javascript
// Using Chrome DevTools Memory tab:

// 1. Open DevTools Memory tab
// 2. Take heap snapshot (baseline)
// 3. Interact with app (mount/unmount components)
// 4. Take another snapshot
// 5. Compare snapshots

// Look for:
// - Growing object count
// - Increasing memory size
// - Same objects that should be garbage collected

// Common leaks:
// - Event listeners not removed
// - Timers not cleared
// - Subscriptions not unsubscribed
// - References in closures
```

### Common Leak Pattern

```jsx
// ❌ LEAK: Event listener never removed
useEffect(() => {
  const handleResize = () => {
    console.log('Window resized');
  };
  
  window.addEventListener('resize', handleResize);
  // Missing: removeEventListener
}, []);

// ✅ FIX: Remove listener on cleanup
useEffect(() => {
  const handleResize = () => {
    console.log('Window resized');
  };
  
  window.addEventListener('resize', handleResize);
  
  return () => {
    window.removeEventListener('resize', handleResize);
  };
}, []);

// ❌ LEAK: Subscription never unsubscribed
useEffect(() => {
  const subscription = observable.subscribe(value => {
    setState(value);
  });
  // Missing: unsubscribe
}, []);

// ✅ FIX: Unsubscribe on cleanup
useEffect(() => {
  const subscription = observable.subscribe(value => {
    setState(value);
  });
  
  return () => {
    subscription.unsubscribe();
  };
}, []);
```

---

## CPU Profiling

### Chrome DevTools Performance Tab

```javascript
// Steps:
// 1. Open DevTools Performance tab
// 2. Click record button
// 3. Interact with app (click, type, etc.)
// 4. Stop recording
// 5. View timeline

// Flame chart shows:
// - JavaScript execution time
// - Rendering time
// - Style/Layout recalculation
// - Paint operations
// - Network requests

// Look for:
// - Long JavaScript blocks (> 50ms)
// - Excessive layout recalculations
// - Paint operations
// - Garbage collection pauses
```

### Identifying Slow JavaScript

```javascript
// Performance tab shows JavaScript blocks:
//
// |---JavaScript (100ms)---|
// |---Rendering (20ms)-|
// |---Paint (5ms)|
//
// The 100ms JavaScript block is slow
// Click on it to see which function
// Look at source code and optimize

// Common slow operations:
// - JSON.parse on large data
// - Array sorting
// - Regular expressions
// - Large DOM queries
// - Heavy calculations
```

---

## Web Vitals

### Measuring Core Web Vitals

```jsx
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

function initializeMetrics() {
  // Measure all Web Vitals
  const vitals = {};
  
  getCLS(metric => {
    vitals.cls = metric.value;
    console.log('CLS:', metric.value, 'rating:', metric.rating);
  });
  
  getFID(metric => {
    vitals.fid = metric.value;
    console.log('FID:', metric.value, 'rating:', metric.rating);
  });
  
  getLCP(metric => {
    vitals.lcp = metric.value;
    console.log('LCP:', metric.value, 'rating:', metric.rating);
  });
  
  // Send to analytics after page interactive
  window.addEventListener('load', () => {
    setTimeout(() => {
      fetch('/api/analytics', {
        method: 'POST',
        body: JSON.stringify(vitals)
      });
    }, 0);
  });
}

initializeMetrics();
```

### Interpreting Results

```javascript
// Good vs Poor scores:

// LCP (Largest Contentful Paint)
// Good: < 2.5s
// Needs improvement: 2.5s - 4s
// Poor: > 4s

// FID (First Input Delay)
// Good: < 100ms
// Needs improvement: 100-300ms
// Poor: > 300ms

// CLS (Cumulative Layout Shift)
// Good: < 0.1
// Needs improvement: 0.1 - 0.25
// Poor: > 0.25

// Example:
// LCP: 1.2s (good)
// FID: 45ms (good)
// CLS: 0.08 (good)
// Overall: GOOD
```

---

## Performance Tools

### Lighthouse

```javascript
// Chrome built-in performance audit:

// 1. Open DevTools Lighthouse tab
// 2. Click "Analyze page load"
// 3. Wait for audit to complete
// 4. Get score (0-100)

// Reports on:
// - Performance (0-100)
// - Accessibility (0-100)
// - Best Practices (0-100)
// - SEO (0-100)

// Gives recommendations:
// - Reduce JavaScript
// - Optimize images
// - Remove unused CSS
// - Implement caching
// - Enable compression

// Usually 90+ is excellent
// 80-90 is good
// < 80 needs work
```

### Bundle Analysis

```bash
# Analyze bundle size
npm install --save-dev rollup-plugin-visualizer

# In vite.config.js
import { visualizer } from "rollup-plugin-visualizer";

export default {
  plugins: [
    visualizer({
      open: true,
      filename: "dist/stats.html"
    })
  ]
}

# Build and view
npm run build

# Opens visualization showing:
# - Package sizes
# - What's largest
# - What can be optimized
# - Code splitting opportunities
```

---

## Optimization Techniques

### Code Splitting

```jsx
import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';

// Lazy load routes
const Home = lazy(() => import('./pages/Home'));
const About = lazy(() => import('./pages/About'));
const Contact = lazy(() => import('./pages/Contact'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/contact" element={<Contact />} />
      </Routes>
    </Suspense>
  );
}

// Benefits:
// - Initial bundle smaller
// - Faster page load
// - Code loads on demand
```

### Memoization

```jsx
// Prevent unnecessary re-renders
const MemoizedComponent = React.memo(function Component({ prop }) {
  return <div>{prop}</div>;
});

// With useMemo
const memoized = useMemo(() => {
  return expensiveCalculation();
}, [dependency]);

// With useCallback
const callback = useCallback(() => {
  doSomething();
}, [dependency]);
```

---

## Common Patterns

### Pattern 1: Measuring Custom Code

```javascript
// Manual timing
function MyFunction() {
  console.time('myFunction');
  
  // Do work
  let result = 0;
  for (let i = 0; i < 1000000; i++) {
    result += i;
  }
  
  console.timeEnd('myFunction');
  // Output: myFunction: 5.23ms
}
```

---

## Interview Questions

### Q1: How do you find performance bottlenecks?

```
Answer:
1. React Profiler
   - Record interactions
   - Look for longest bars
   - Identify slow components

2. Chrome DevTools
   - Performance tab for JavaScript
   - Memory tab for leaks
   - Lighthouse for overall score

3. Web Vitals
   - LCP: < 2.5s
   - FID: < 100ms
   - CLS: < 0.1

4. Bundle analysis
   - What's largest?
   - What can be split?
```

### Q2: What causes memory leaks in React?

```
Answer:
- Event listeners not removed
- Timers (setInterval) not cleared
- Subscriptions not unsubscribed
- References in closures

Always clean up in useEffect return:
useEffect(() => {
  // Register
  addEventListener(...);
  
  return () => {
    // Clean up
    removeEventListener(...);
  };
}, []);
```

---

## Resources

- **Web Vitals:** https://web.dev/vitals/
- **React Profiler:** https://react.dev/learn/render-and-commit
- **Chrome DevTools:** https://developer.chrome.com/docs/devtools/performance/
- **Lighthouse:** https://developers.google.com/web/tools/lighthouse
- **Performance API:** https://developer.mozilla.org/en-US/docs/Web/API/Performance

---

**Part 15 Complete!** You've mastered debugging and performance optimization. Next: Part 16 - Deployment & Production
