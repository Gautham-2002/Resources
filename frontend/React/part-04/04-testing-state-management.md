# Part 4.5: Testing State Management

## What You'll Learn

- Testing Context API providers
- Testing Zustand stores
- Testing Redux patterns
- Testing hooks that use stores
- Integration testing with state management
- Common testing pitfalls
- Best practices for state management tests
- Interview questions

---

## Table of Contents

1. [Testing Fundamentals](#testing-fundamentals)
2. [Testing Context API](#testing-context-api)
3. [Testing Zustand](#testing-zustand)
4. [Testing Hooks with Stores](#testing-hooks-with-stores)
5. [Integration Testing](#integration-testing)
6. [Testing Async State](#testing-async-state)
7. [Common Patterns](#common-patterns)
8. [Common Pitfalls](#common-pitfalls)
9. [Interview Questions](#interview-questions)
10. [Resources](#resources)

---

## Testing Fundamentals

### Testing Tools

```javascript
// Tools we'll use:
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderHook, act } from '@testing-library/react';

// Vitest: Test runner (fast, Vite-native)
// React Testing Library: Render components, query elements
// renderHook: Test hooks in isolation
```

### Testing Strategy

```javascript
// Three levels of testing:

// 1. Unit: Test store/context in isolation
// - Test actions change state correctly
// - Test selectors return correct values

// 2. Integration: Test components with state
// - Test components can read state
// - Test components can dispatch actions
// - Test state changes trigger re-renders

// 3. E2E: Test full user flows
// - User interactions cause state changes
// - Components respond to state changes
```

---

## Testing Context API

### Testing Context Hooks

```javascript
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTheme, ThemeProvider } from './theme-context';

describe('ThemeContext', () => {
  // Must provide wrapper for context
  const wrapper = ({ children }) => (
    <ThemeProvider>{children}</ThemeProvider>
  );
  
  it('should provide theme value', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    
    expect(result.current.theme).toBe('light');
  });
  
  it('should toggle theme', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    
    act(() => {
      result.current.toggleTheme();
    });
    
    expect(result.current.theme).toBe('dark');
  });
  
  it('should throw error when used outside provider', () => {
    // Suppress error output for this test
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => {
      renderHook(() => useTheme());
    }).toThrow('useTheme must be used within ThemeProvider');
    
    spy.mockRestore();
  });
});
```

### Testing Context Components

```javascript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from './theme-context';
import { ThemeToggle } from './theme-toggle';

describe('ThemeToggle Component', () => {
  it('should display current theme', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );
    
    expect(screen.getByText(/light/i)).toBeInTheDocument();
  });
  
  it('should toggle theme on button click', async () => {
    const user = userEvent.setup();
    
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );
    
    const button = screen.getByRole('button', { name: /toggle/i });
    
    await user.click(button);
    
    expect(screen.getByText(/dark/i)).toBeInTheDocument();
  });
});
```

---

## Testing Zustand

### Testing Store Functions

```javascript
import { describe, it, expect, beforeEach } from 'vitest';
import { useCounterStore } from './counter-store';

describe('Counter Store', () => {
  beforeEach(() => {
    // Reset store before each test
    useCounterStore.setState({ count: 0 });
  });
  
  it('should have initial state', () => {
    const state = useCounterStore.getState();
    expect(state.count).toBe(0);
  });
  
  it('should increment count', () => {
    const { increment } = useCounterStore.getState();
    
    increment();
    
    expect(useCounterStore.getState().count).toBe(1);
  });
  
  it('should decrement count', () => {
    useCounterStore.setState({ count: 5 });
    
    const { decrement } = useCounterStore.getState();
    decrement();
    
    expect(useCounterStore.getState().count).toBe(4);
  });
  
  it('should reset count', () => {
    useCounterStore.setState({ count: 42 });
    
    const { reset } = useCounterStore.getState();
    reset();
    
    expect(useCounterStore.getState().count).toBe(0);
  });
});
```

### Testing Store with renderHook

```javascript
import { renderHook, act } from '@testing-library/react';
import { useCounterStore } from './counter-store';

describe('Counter Store with renderHook', () => {
  it('should increment when action called', () => {
    const { result } = renderHook(() => useCounterStore());
    
    expect(result.current.count).toBe(0);
    
    act(() => {
      result.current.increment();
    });
    
    expect(result.current.count).toBe(1);
  });
  
  it('should subscribe to changes', () => {
    const listener = vi.fn();
    
    const { result } = renderHook(() => useCounterStore());
    
    // Subscribe to count changes
    const unsubscribe = useCounterStore.subscribe(
      (state) => state.count,
      listener
    );
    
    act(() => {
      result.current.increment();
    });
    
    expect(listener).toHaveBeenCalledWith(1, 0);
    
    unsubscribe();
  });
});
```

### Testing Store Selectors

```javascript
import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useCartStore } from './cart-store';

describe('Cart Store Selectors', () => {
  it('should select only items', () => {
    const { result: result1 } = renderHook(() =>
      useCartStore((state) => state.items)
    );
    
    const { result: result2 } = renderHook(() =>
      useCartStore((state) => state.items)
    );
    
    // Both should have items
    expect(result1.current).toEqual(result2.current);
  });
  
  it('should not re-render when unselected state changes', () => {
    const renderSpy = vi.fn();
    
    const { rerender } = renderHook(() => {
      renderSpy();
      return useCartStore((state) => state.items);
    });
    
    // Change cart total (not items)
    useCartStore.setState({ total: 100 });
    
    // Component shouldn't re-render
    expect(renderSpy).toHaveBeenCalledOnce();
  });
});
```

---

## Testing Hooks with Stores

### Testing Custom Hooks

```javascript
import { renderHook, act } from '@testing-library/react';
import { useFilteredTodos } from './use-filtered-todos';
import { useTodoStore } from './todo-store';

describe('useFilteredTodos', () => {
  beforeEach(() => {
    useTodoStore.setState({
      todos: [
        { id: 1, text: 'Learn React', done: true },
        { id: 2, text: 'Learn Zustand', done: false },
        { id: 3, text: 'Learn Testing', done: false }
      ],
      filter: 'all'
    });
  });
  
  it('should return all todos when filter is "all"', () => {
    const { result } = renderHook(() => useFilteredTodos());
    
    expect(result.current).toHaveLength(3);
  });
  
  it('should return only completed todos when filter is "done"', () => {
    useTodoStore.setState({ filter: 'done' });
    
    const { result } = renderHook(() => useFilteredTodos());
    
    expect(result.current).toHaveLength(1);
    expect(result.current[0].text).toBe('Learn React');
  });
  
  it('should return only pending todos when filter is "pending"', () => {
    useTodoStore.setState({ filter: 'pending' });
    
    const { result } = renderHook(() => useFilteredTodos());
    
    expect(result.current).toHaveLength(2);
  });
});
```

### Testing Hooks with Async

```javascript
import { renderHook, act, waitFor } from '@testing-library/react';
import { useFetchUser } from './use-fetch-user';
import { vi } from 'vitest';

describe('useFetchUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  
  it('should fetch user data', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ id: 1, name: 'John' })
      })
    );
    
    const { result } = renderHook(() => useFetchUser(1));
    
    expect(result.current.loading).toBe(true);
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.user).toEqual({ id: 1, name: 'John' });
  });
  
  it('should handle errors', async () => {
    global.fetch = vi.fn(() =>
      Promise.reject(new Error('Network error'))
    );
    
    const { result } = renderHook(() => useFetchUser(1));
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.error).toBe('Network error');
  });
});
```

---

## Integration Testing

### Testing Components with State

```javascript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TodoList } from './todo-list';
import { useTodoStore } from './todo-store';

describe('TodoList Component', () => {
  beforeEach(() => {
    useTodoStore.setState({
      todos: [
        { id: 1, text: 'Learn React', done: false }
      ]
    });
  });
  
  it('should display todos from store', () => {
    render(<TodoList />);
    
    expect(screen.getByText('Learn React')).toBeInTheDocument();
  });
  
  it('should add todo when form submitted', async () => {
    const user = userEvent.setup();
    
    render(<TodoList />);
    
    const input = screen.getByPlaceholderText('Add todo');
    const button = screen.getByRole('button', { name: /add/i });
    
    await user.type(input, 'Learn Testing');
    await user.click(button);
    
    expect(screen.getByText('Learn Testing')).toBeInTheDocument();
  });
  
  it('should toggle todo completion', async () => {
    const user = userEvent.setup();
    
    render(<TodoList />);
    
    const checkbox = screen.getByRole('checkbox');
    
    await user.click(checkbox);
    
    expect(checkbox).toBeChecked();
  });
});
```

---

## Testing Async State

### Testing Async Actions

```javascript
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAsyncStore } from './async-store';
import { vi } from 'vitest';

describe('Async Store', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAsyncStore.setState({
      data: null,
      loading: false,
      error: null
    });
  });
  
  it('should handle successful fetch', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([{ id: 1, name: 'Item' }])
      })
    );
    
    const { result } = renderHook(() => useAsyncStore());
    
    act(() => {
      result.current.fetch('/api/items');
    });
    
    expect(result.current.loading).toBe(true);
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.data).toEqual([{ id: 1, name: 'Item' }]);
    expect(result.current.error).toBeNull();
  });
  
  it('should handle fetch errors', async () => {
    global.fetch = vi.fn(() =>
      Promise.reject(new Error('Failed to fetch'))
    );
    
    const { result } = renderHook(() => useAsyncStore());
    
    act(() => {
      result.current.fetch('/api/items');
    });
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.error).toBe('Failed to fetch');
    expect(result.current.data).toBeNull();
  });
});
```

---

## Common Patterns

### Pattern 1: Testing Store Interactions

```javascript
describe('Store Interactions', () => {
  it('should handle complex state changes', () => {
    const { increment, multiply, reset } = useCounterStore.getState();
    
    increment();  // 1
    increment();  // 2
    multiply(5);  // 10
    
    expect(useCounterStore.getState().count).toBe(10);
    
    reset();
    
    expect(useCounterStore.getState().count).toBe(0);
  });
});
```

### Pattern 2: Mocking API Calls

```javascript
describe('Store with API', () => {
  it('should fetch and cache data', async () => {
    const fetchSpy = vi.fn();
    
    global.fetch = fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: 1, name: 'John' })
    });
    
    const { fetch } = useStore.getState();
    
    await fetch('/api/user/1');
    
    expect(fetchSpy).toHaveBeenCalledWith('/api/user/1');
    expect(useStore.getState().data).toEqual({ id: 1, name: 'John' });
  });
});
```

---

## Common Pitfalls

### Pitfall 1: Not Resetting Store Between Tests

```javascript
// ❌ WRONG: Store state leaks between tests
describe('Store', () => {
  it('test 1', () => {
    useStore.setState({ count: 5 });
    expect(useStore.getState().count).toBe(5);
  });
  
  it('test 2', () => {
    // count is still 5 from previous test!
    expect(useStore.getState().count).toBe(0);  // FAILS!
  });
});

// ✅ CORRECT: Reset before each test
describe('Store', () => {
  beforeEach(() => {
    useStore.setState({ count: 0 });
  });
  
  it('test 1', () => {
    useStore.setState({ count: 5 });
    expect(useStore.getState().count).toBe(5);
  });
  
  it('test 2', () => {
    expect(useStore.getState().count).toBe(0);  // PASSES!
  });
});
```

### Pitfall 2: Forgetting to Use act()

```javascript
// ❌ WRONG: State updates outside act()
const { result } = renderHook(() => useStore());

result.current.increment();  // Warning!

// ✅ CORRECT: Wrap updates in act()
const { result } = renderHook(() => useStore());

act(() => {
  result.current.increment();
});
```

### Pitfall 3: Testing Implementation Details

```javascript
// ❌ WRONG: Testing internal function names
expect(result.current._computeTotal).toBeCalled();

// ✅ CORRECT: Test behavior, not implementation
expect(result.current.total).toBe(expectedTotal);
```

---

## Interview Questions

### Q1: How do you test a Zustand store?

```
Answer:
1. Use vi.fn() to mock functions
2. Use getState() to access current state
3. Use setState() to set initial state
4. Use renderHook() with act() for hook tests
5. Reset state in beforeEach()

Example:
beforeEach(() => {
  useStore.setState({ count: 0 });
});

it('should increment', () => {
  const { increment } = useStore.getState();
  increment();
  expect(useStore.getState().count).toBe(1);
});
```

### Q2: How do you test Context providers?

```
Answer:
1. Create wrapper component with provider
2. Pass wrapper to renderHook
3. Use act() for state changes
4. Test error handling (outside provider)

Example:
const wrapper = ({ children }) => (
  <Provider>{children}</Provider>
);

const { result } = renderHook(() => useContext(), { wrapper });
```

### Q3: What's the difference between unit and integration tests?

```
Answer:
Unit tests:
- Test store/context in isolation
- Test individual actions
- Test selectors
- Mock everything external

Integration tests:
- Test components with state
- Test user interactions
- Test state changes trigger UI updates
- Test actual store/context behavior

Use both: unit tests for logic, integration tests for user flow
```

---

## Resources

- **Vitest:** https://vitest.dev/
- **React Testing Library:** https://testing-library.com/react
- **Testing Zustand:** https://github.com/pmndrs/zustand#testing
- **Testing Context:** https://kentcdodds.com/blog/how-to-test-react-context
- **Testing Best Practices:** https://kentcdodds.com/blog/common-mistakes-with-react-testing-library

---

**Part 4 Complete!** You've mastered state management (Context, Zustand, comparison, testing). Next: Part 5 - Styling & Forms
