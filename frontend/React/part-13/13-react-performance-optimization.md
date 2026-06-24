# Part 13.2: React Performance Optimization

## What You'll Learn

- React rendering behavior and when to optimize
- React.memo, useMemo, useCallback correctly
- Key extraction and list rendering
- Virtualization for large lists
- State colocation and lifting
- React DevTools Profiler
- The React Compiler (React 19+)

---

## Table of Contents

1. [React Rendering Behavior](#react-rendering-behavior)
2. [When to Optimize](#when-to-optimize)
3. [React.memo](#reactmemo)
4. [useMemo & useCallback](#usememo--usecallback)
5. [Key Optimization for Lists](#key-optimization-for-lists)
6. [State Colocation](#state-colocation)
7. [Virtualization](#virtualization)
8. [React DevTools Profiler](#react-devtools-profiler)
9. [React Compiler](#react-compiler)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Resources](#resources)

---

## React Rendering Behavior

```
Key Rule: When a component re-renders, ALL its children re-render too.

Parent re-renders → Child A re-renders → Grandchild re-renders
                  → Child B re-renders

This is BY DESIGN. React's reconciliation is fast.
Most re-renders are NOT a performance problem.

Only optimize when you MEASURE a real problem!
```

### What Triggers a Re-render?

```typescript
// 1. State change in the component
const [count, setCount] = useState(0);
setCount(1); // → Re-render

// 2. Parent re-renders
function Parent() {
  const [x, setX] = useState(0);
  return <Child />; // Child re-renders when Parent does
}

// 3. Context value changes
const ThemeContext = createContext('light');
// All consumers re-render when context value changes

// 4. Custom hook state changes
function useWindowSize() {
  const [size, setSize] = useState({ width: 0, height: 0 });
  // Component using this hook re-renders on resize
}
```

---

## When to Optimize

```
The Golden Rule of Performance Optimization:
"Don't optimize prematurely. Measure first, optimize second."

When NOT to optimize:
- Re-renders that take < 16ms (60fps)
- Small component trees
- Simple state updates
- "It might be slow someday"

When TO optimize:
- Measured slowness (>16ms renders)
- Large lists (100+ items)
- Heavy computations in render
- Frequent updates (real-time data, animations)
- User-reported jank
```

---

## React.memo

```typescript
// React.memo: Skip re-render if props haven't changed

// ❌ Without memo: re-renders every time parent renders
function ExpensiveList({ items }: { items: Item[] }) {
  return (
    <ul>
      {items.map(item => (
        <li key={item.id}>{expensiveFormat(item)}</li>
      ))}
    </ul>
  );
}

// ✅ With memo: only re-renders when items actually change
const ExpensiveList = memo(function ExpensiveList({ items }: { items: Item[] }) {
  return (
    <ul>
      {items.map(item => (
        <li key={item.id}>{expensiveFormat(item)}</li>
      ))}
    </ul>
  );
});

// Custom comparison (for complex props)
const UserCard = memo(function UserCard({ user }: { user: User }) {
  return <div>{user.name}</div>;
}, (prevProps, nextProps) => {
  return prevProps.user.id === nextProps.user.id &&
         prevProps.user.name === nextProps.user.name;
});
```

---

## useMemo & useCallback

### useMemo: Cache Expensive Computations

```typescript
function DataTable({ data, filter }: { data: Item[]; filter: string }) {
  // ❌ Filters on every render (even if data and filter haven't changed)
  const filtered = data.filter(item => item.name.includes(filter));

  // ✅ Only recomputes when data or filter changes
  const filtered = useMemo(
    () => data.filter(item => item.name.includes(filter)),
    [data, filter]
  );

  return <Table data={filtered} />;
}
```

### useCallback: Cache Function References

```typescript
function ParentComponent() {
  const [count, setCount] = useState(0);

  // ❌ New function every render (breaks memo on child)
  const handleClick = () => console.log('clicked');

  // ✅ Same function reference between renders
  const handleClick = useCallback(() => {
    console.log('clicked');
  }, []);

  return <MemoizedChild onClick={handleClick} />;
}
```

### When to Use (Rules of Thumb)

```
useMemo:
  ✅ Expensive computations (sorting, filtering 1000+ items)
  ✅ Creating objects/arrays passed to memo'd children
  ❌ Simple calculations (a + b, string concatenation)
  ❌ Everything "just in case"

useCallback:
  ✅ Functions passed to React.memo'd children
  ✅ Functions used in useEffect dependency arrays
  ❌ Event handlers that don't go to memo'd children
  ❌ Every function "just in case"
```

---

## Key Optimization for Lists

```typescript
// ❌ Using index as key (causes bugs with reordering/filtering)
{items.map((item, index) => (
  <ListItem key={index} item={item} />
))}

// ✅ Using stable, unique ID
{items.map((item) => (
  <ListItem key={item.id} item={item} />
))}

// Why index is bad:
// If you remove item at index 2:
// - React thinks items shifted (index 2 is now old index 3)
// - Components get wrong props
// - State gets mixed up between items
```

---

## State Colocation

### Push State Down

```typescript
// ❌ State too high: entire page re-renders on search
function Page() {
  const [search, setSearch] = useState('');
  return (
    <div>
      <Header />  {/* Re-renders on search change! */}
      <Sidebar /> {/* Re-renders on search change! */}
      <SearchBar value={search} onChange={setSearch} />
      <Results query={search} />
    </div>
  );
}

// ✅ State colocated: only SearchSection re-renders
function Page() {
  return (
    <div>
      <Header />
      <Sidebar />
      <SearchSection /> {/* Search state lives here */}
    </div>
  );
}

function SearchSection() {
  const [search, setSearch] = useState('');
  return (
    <>
      <SearchBar value={search} onChange={setSearch} />
      <Results query={search} />
    </>
  );
}
```

### Lift Content Up (Children Pattern)

```typescript
// ❌ ScrollTracker forces all children to re-render
function ScrollTracker() {
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handler = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handler);
    return () => window.removeEventListener('scroll', handler);
  }, []);

  return (
    <div>
      <ScrollIndicator position={scrollY} />
      <HeavyContent /> {/* Re-renders on every scroll! */}
    </div>
  );
}

// ✅ Children pattern: HeavyContent doesn't re-render
function ScrollTracker({ children }: { children: React.ReactNode }) {
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handler = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handler);
    return () => window.removeEventListener('scroll', handler);
  }, []);

  return (
    <div>
      <ScrollIndicator position={scrollY} />
      {children} {/* Doesn't re-render! Created by parent */}
    </div>
  );
}

// Usage
<ScrollTracker>
  <HeavyContent />
</ScrollTracker>
```

---

## Virtualization

```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualizedList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
    overscan: 5,
  });

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto">
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            className="absolute top-0 left-0 w-full"
            style={{
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            <ItemRow item={items[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## React DevTools Profiler

```
How to use the React Profiler:
1. Install React DevTools browser extension
2. Open DevTools → Profiler tab
3. Click "Record" → interact with app → "Stop"
4. Analyze:
   - Which components re-rendered
   - How long each render took
   - What caused the render
   - Flame graph of component tree

Key things to look for:
- Components rendering unnecessarily (gray = skipped, colored = rendered)
- Long render times (>16ms = dropped frame)
- Frequent re-renders from unchanged props
```

---

## React Compiler

```
React Compiler (React 19+):
- Automatically memoizes components and values
- No more manual React.memo, useMemo, useCallback
- Compiler analyzes your code at build time
- Generates optimized output

Before compiler:
  const filtered = useMemo(() => items.filter(fn), [items]);
  const handleClick = useCallback(() => { ... }, [dep]);

After compiler:
  const filtered = items.filter(fn);  // Compiler handles memoization!
  const handleClick = () => { ... };  // Compiler handles this too!
```

---

## Common Patterns & Best Practices

### Pattern 1: Profile Before Optimizing

```
1. Open React DevTools Profiler
2. Record a user interaction
3. Find the slowest renders
4. Optimize THOSE specific components
5. Re-measure to confirm improvement
```

### Pattern 2: Avoid Inline Objects in JSX

```typescript
// ❌ New object every render (breaks memo)
<MyComponent style={{ color: 'red' }} options={{ sort: 'name' }} />

// ✅ Stable references
const style = useMemo(() => ({ color: 'red' }), []);
const options = useMemo(() => ({ sort: 'name' }), []);
<MyComponent style={style} options={options} />
```

---

## Common Pitfalls

### Pitfall 1: Premature Optimization

```typescript
// ❌ Wrapping everything in memo "just in case"
const Title = memo(({ text }) => <h1>{text}</h1>);
// This is slower than not using memo (comparison overhead)!

// ✅ Only memo when there's a measured problem
```

### Pitfall 2: Breaking Memoization

```typescript
// ❌ memo is useless because onClick is new every render
const MemoChild = memo(Child);
function Parent() {
  return <MemoChild onClick={() => doSomething()} />;
}

// ✅ Stable callback reference
function Parent() {
  const onClick = useCallback(() => doSomething(), []);
  return <MemoChild onClick={onClick} />;
}
```

---

## Resources

- **React Performance:** https://react.dev/reference/react/memo
- **Profiler:** https://react.dev/reference/react/Profiler
- **React Compiler:** https://react.dev/learn/react-compiler
- **TanStack Virtual:** https://tanstack.com/virtual/latest
- **Kent C. Dodds - Fix Slow Renders:** https://kentcdodds.com/blog/fix-the-slow-render-before-you-fix-the-re-render

---

**Next:** [Part 13.3: Image Optimization](./13-image-optimization.md)
