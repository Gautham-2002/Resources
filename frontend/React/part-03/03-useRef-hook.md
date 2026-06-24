# Part 3.7: useRef Hook

## What You'll Learn

- What refs are and when to use them
- useRef for DOM access
- useRef for persistent values (not state)
- forwardRef for function components
- useImperativeHandle for custom ref behavior
- Refs vs state trade-offs
- Common patterns and anti-patterns
- Interview questions

---

## Table of Contents

1. [useRef Fundamentals](#useref-fundamentals)
2. [Refs vs State](#refs-vs-state)
3. [DOM Access with Refs](#dom-access-with-refs)
4. [Persistent Values with Refs](#persistent-values-with-refs)
5. [forwardRef Component Wrapper](#forwardref-component-wrapper)
6. [useImperativeHandle](#useimperativehandle)
7. [Common Use Cases](#common-use-cases)
8. [Refs Best Practices](#refs-best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Interview Questions](#interview-questions)
11. [Resources](#resources)

---

## useRef Fundamentals

### What is a Ref?

A ref is a **mutable object that persists across renders** and holds a value that doesn't cause re-renders.

```jsx
function Component() {
  // Create ref
  const inputRef = useRef(null);
  
  // useRef returns an object with a 'current' property
  // {
  //   current: null
  // }
  
  return <input ref={inputRef} />;
}

// Accessing ref value
console.log(inputRef.current);  // The input DOM element
```

### Key Characteristics

```javascript
// 1. Persistent: Same object across renders
function Component() {
  const ref = useRef(0);
  
  const handleClick = () => {
    ref.current++;
    console.log(ref.current);
  };
  
  // Click 5 times: logs 1, 2, 3, 4, 5
  // ref persists across renders
}

// 2. Mutable: Can change without side effects
const ref = useRef(0);
ref.current = 5;  // Directly assign
ref.current = { data: 'anything' };  // Can hold any value

// 3. Doesn't cause re-renders: Changing ref doesn't re-render
function Component() {
  const ref = useRef(0);
  
  const increment = () => {
    ref.current++;
    // No re-render happens!
  };
  
  return <button onClick={increment}>{ref.current}</button>;
  // Button always shows 0 (not updated after click)
}
```

---

## Refs vs State

### The Comparison

```jsx
// useState: Triggers re-render when value changes
function CounterWithState() {
  const [count, setCount] = useState(0);
  
  const increment = () => {
    setCount(count + 1);  // Triggers re-render
  };
  
  return <div>Count: {count}</div>;
  // Shows updated count
}

// useRef: No re-render when value changes
function CounterWithRef() {
  const count = useRef(0);
  
  const increment = () => {
    count.current++;  // No re-render!
  };
  
  return <div>Count: {count.current}</div>;
  // Always shows 0
}
```

### When to Use Each

```jsx
// Use state when:
// - Value affects render output
// - Need re-render on change
// - Data visible to user

function Timer() {
  const [seconds, setSeconds] = useState(0);  // User sees this
  
  useEffect(() => {
    const interval = setInterval(() => {
      setSeconds(s => s + 1);
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);
  
  return <div>Elapsed: {seconds}s</div>;
}

// Use ref when:
// - Value doesn't affect render
// - Need persistent value across renders
// - Direct DOM access needed

function StopWatch() {
  const startTime = useRef(null);
  const [elapsed, setElapsed] = useState(0);
  
  const start = () => {
    startTime.current = Date.now();  // Persistent value
  };
  
  const getElapsed = () => {
    if (!startTime.current) return 0;
    return Math.floor((Date.now() - startTime.current) / 1000);
  };
  
  return (
    <div>
      <button onClick={start}>Start</button>
      <button onClick={() => setElapsed(getElapsed())}>
        Get Time: {elapsed}s
      </button>
    </div>
  );
}
```

---

## DOM Access with Refs

### Accessing DOM Elements

```jsx
function TextInput() {
  const inputRef = useRef(null);
  
  const focusInput = () => {
    inputRef.current.focus();
  };
  
  return (
    <div>
      <input ref={inputRef} type="text" />
      <button onClick={focusInput}>Focus Input</button>
    </div>
  );
}

// Use cases for DOM access:
// - Focus management
// - Text selection
// - Playing/pausing media
// - Triggering animations
// - Integrating with 3rd party DOM libraries
```

### Measuring DOM Elements

```jsx
function MeasureElement() {
  const elementRef = useRef(null);
  const [width, setWidth] = useState(0);
  
  const measureWidth = () => {
    if (elementRef.current) {
      setWidth(elementRef.current.offsetWidth);
    }
  };
  
  return (
    <div>
      <div ref={elementRef}>This is the element</div>
      <button onClick={measureWidth}>Measure</button>
      <p>Width: {width}px</p>
    </div>
  );
}
```

### Focus Management

```jsx
function SearchField() {
  const inputRef = useRef(null);
  const [query, setQuery] = useState('');
  
  // Focus on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);
  
  // Focus on query clear
  const handleClear = () => {
    setQuery('');
    inputRef.current?.focus();
  };
  
  return (
    <div>
      <input
        ref={inputRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
      />
      <button onClick={handleClear}>Clear</button>
    </div>
  );
}
```

### Media Control

```jsx
function VideoPlayer() {
  const videoRef = useRef(null);
  
  const play = () => {
    videoRef.current?.play();
  };
  
  const pause = () => {
    videoRef.current?.pause();
  };
  
  return (
    <div>
      <video ref={videoRef} src="movie.mp4" />
      <button onClick={play}>Play</button>
      <button onClick={pause}>Pause</button>
    </div>
  );
}
```

---

## Persistent Values with Refs

### Storing Previous Values

```jsx
function Component({ value }) {
  const prevValueRef = useRef();
  
  useEffect(() => {
    prevValueRef.current = value;  // Store current value
  }, [value]);
  
  return <div>Current: {value}, Previous: {prevValueRef.current}</div>;
  // Shows current and previous value
}

// Timeline:
// Render 1: value=1, prevValue=undefined
// After effect: prevValue=1
// Render 2: value=2, prevValue=1
// After effect: prevValue=2
// Render 3: value=3, prevValue=2
```

### Tracking Renders

```jsx
function Component() {
  const renderCount = useRef(0);
  
  useEffect(() => {
    renderCount.current++;
  });
  
  return <div>Rendered {renderCount.current} times</div>;
}

// Every render, effect increments ref
// Component re-renders, ref updates, effect runs again
// Shows render count
```

### Storing Timers/Intervals

```jsx
function StopWatch() {
  const timerRef = useRef(null);
  const [isRunning, setIsRunning] = useState(false);
  const [seconds, setSeconds] = useState(0);
  
  const start = () => {
    setIsRunning(true);
    timerRef.current = setInterval(() => {
      setSeconds(s => s + 1);
    }, 1000);
  };
  
  const stop = () => {
    clearInterval(timerRef.current);
    setIsRunning(false);
  };
  
  return (
    <div>
      <p>Time: {seconds}s</p>
      <button onClick={start} disabled={isRunning}>Start</button>
      <button onClick={stop} disabled={!isRunning}>Stop</button>
    </div>
  );
}

// Ref stores interval ID for later cleanup
```

---

## forwardRef Component Wrapper

### The Problem

```jsx
// Function components don't have refs by default
function TextInput({ placeholder }) {
  return <input placeholder={placeholder} />;
}

// This doesn't work!
function Parent() {
  const inputRef = useRef(null);
  
  const focusInput = () => {
    inputRef.current?.focus();  // undefined - ref not forwarded
  };
  
  return (
    <>
      <TextInput ref={inputRef} placeholder="Enter text" />
      <button onClick={focusInput}>Focus</button>
    </>
  );
}
```

### The Solution: forwardRef

```jsx
import { forwardRef } from 'react';

// Wrap function component with forwardRef
const TextInput = forwardRef(function TextInput({ placeholder }, ref) {
  // ref is passed as second argument
  return <input ref={ref} placeholder={placeholder} />;
});

function Parent() {
  const inputRef = useRef(null);
  
  const focusInput = () => {
    inputRef.current?.focus();  // Works now!
  };
  
  return (
    <>
      <TextInput ref={inputRef} placeholder="Enter text" />
      <button onClick={focusInput}>Focus</button>
    </>
  );
}
```

### forwardRef with Other Props

```jsx
const Button = forwardRef(function Button({ color, ...props }, ref) {
  return (
    <button
      ref={ref}
      style={{ backgroundColor: color }}
      {...props}
    />
  );
});

function App() {
  const buttonRef = useRef(null);
  
  const handleClick = () => {
    buttonRef.current?.scrollIntoView();
  };
  
  return <Button ref={buttonRef} color="blue">Click me</Button>;
}
```

---

## useImperativeHandle

### What is useImperativeHandle?

useImperativeHandle **customizes what a ref exposes** from a component.

```jsx
import { forwardRef, useImperativeHandle } from 'react';

const TextInput = forwardRef(function TextInput(props, ref) {
  const inputRef = useRef(null);
  
  // Define what ref.current can do
  useImperativeHandle(ref, () => ({
    // Custom methods
    focus: () => {
      inputRef.current?.focus();
    },
    
    getValue: () => {
      return inputRef.current?.value;
    },
    
    setValue: (value) => {
      inputRef.current.value = value;
    },
    
    clear: () => {
      inputRef.current.value = '';
    }
  }), []);
  
  return <input ref={inputRef} {...props} />;
});

// Usage
function Form() {
  const inputRef = useRef(null);
  
  const handleClear = () => {
    inputRef.current?.clear();  // Custom method
  };
  
  const getValue = () => {
    alert(inputRef.current?.getValue());
  };
  
  return (
    <div>
      <TextInput ref={inputRef} />
      <button onClick={getValue}>Get Value</button>
      <button onClick={handleClear}>Clear</button>
    </div>
  );
}
```

### Advanced Example: Form Control

```jsx
const FormInput = forwardRef(function FormInput({ label, ...props }, ref) {
  const inputRef = useRef(null);
  
  useImperativeHandle(ref, () => ({
    focus: () => inputRef.current?.focus(),
    getValue: () => inputRef.current?.value || '',
    setValue: (value) => {
      inputRef.current.value = value;
    },
    clear: () => {
      inputRef.current.value = '';
    },
    validate: () => {
      const value = inputRef.current?.value;
      return value && value.length > 0;
    }
  }), []);
  
  return (
    <div>
      <label>{label}</label>
      <input ref={inputRef} {...props} />
    </div>
  );
});

function Form() {
  const nameRef = useRef(null);
  const emailRef = useRef(null);
  
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validate using ref methods
    if (!nameRef.current?.validate()) {
      alert('Name is required');
      nameRef.current?.focus();
      return;
    }
    
    if (!emailRef.current?.validate()) {
      alert('Email is required');
      emailRef.current?.focus();
      return;
    }
    
    console.log({
      name: nameRef.current?.getValue(),
      email: emailRef.current?.getValue()
    });
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <FormInput ref={nameRef} label="Name" />
      <FormInput ref={emailRef} label="Email" type="email" />
      <button type="submit">Submit</button>
    </form>
  );
}
```

---

## Common Use Cases

### Case 1: Text Selection

```jsx
function SearchInput() {
  const inputRef = useRef(null);
  
  const selectAll = () => {
    inputRef.current?.select();
  };
  
  return (
    <div>
      <input ref={inputRef} type="text" />
      <button onClick={selectAll}>Select All</button>
    </div>
  );
}
```

### Case 2: Scroll Into View

```jsx
function ScrollToBottom() {
  const endRef = useRef(null);
  const [messages, setMessages] = useState([]);
  
  useEffect(() => {
    // Scroll to bottom when messages change
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  return (
    <div>
      {messages.map(msg => <p key={msg.id}>{msg.text}</p>)}
      <div ref={endRef} />
    </div>
  );
}
```

### Case 3: Third-Party Library Integration

```jsx
import { Chart } from 'some-chart-library';

function LineChart() {
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);
  
  useEffect(() => {
    // Initialize third-party library
    chartInstanceRef.current = new Chart(chartRef.current, {
      type: 'line',
      data: { /* ... */ }
    });
    
    return () => {
      chartInstanceRef.current?.destroy();
    };
  }, []);
  
  return <canvas ref={chartRef}></canvas>;
}
```

---

## Refs Best Practices

### Do

```jsx
// ✅ Use for DOM access when needed
const inputRef = useRef(null);

// ✅ Use for persistent values
const timerRef = useRef(null);

// ✅ Use with forwardRef for custom components
const CustomInput = forwardRef((props, ref) => (
  <input ref={ref} {...props} />
));

// ✅ Initialize ref in useEffect cleanup
useEffect(() => {
  return () => {
    clearInterval(timerRef.current);
  };
}, []);
```

### Don't

```jsx
// ❌ Use instead of state
const [count, setCount] = useState(0);
// Don't do this:
// const count = useRef(0);

// ❌ Set ref values during render
function Component() {
  const ref = useRef(null);
  ref.current = 'value';  // Wrong! Do in useEffect
  return <div/>;
}

// ❌ Overuse forwardRef
// Only use when you need to expose imperative APIs

// ❌ Store complex logic in refs
// Keep logic in functions and components
```

---

## Common Pitfalls

### Pitfall 1: Ref Not Updated During Render

```jsx
// ❌ WRONG: Setting ref during render
function Component() {
  const ref = useRef(null);
  
  ref.current = 'value';  // Runs every render
  
  return <div>{ref.current}</div>;  // Unreliable
}

// ✅ CORRECT: Set in useEffect
function Component() {
  const ref = useRef(null);
  
  useEffect(() => {
    ref.current = 'value';  // Set once on mount
  }, []);
  
  return <div>{ref.current}</div>;
}
```

### Pitfall 2: Depending on Ref in Effect

```jsx
// ❌ WRONG: Ref in dependency array
function Component() {
  const ref = useRef(null);
  
  useEffect(() => {
    // Do something with ref
  }, [ref]);  // ref never changes, pointless
}

// ✅ CORRECT: Refs don't go in dependencies
function Component() {
  const ref = useRef(null);
  
  useEffect(() => {
    // Do something with ref
  }, []);  // Empty deps, ref is always there
}
```

### Pitfall 3: Using Ref Instead of State

```jsx
// ❌ WRONG: Ref when state is needed
function Counter() {
  const count = useRef(0);
  
  const increment = () => {
    count.current++;
  };
  
  return (
    <div>
      {count.current}  {/* Always shows 0 */}
      <button onClick={increment}>+</button>
    </div>
  );
}

// ✅ CORRECT: Use state
function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      {count}  {/* Updates correctly */}
      <button onClick={() => setCount(count + 1)}>+</button>
    </div>
  );
}
```

---

## Interview Questions

### Q1: What's the difference between useRef and useState?

```
Answer:
useRef:
- Mutable object
- Doesn't cause re-renders
- Same object across renders
- Suitable for persistent values

useState:
- Immutable updates
- Causes re-renders on change
- New state on each update
- Suitable for render data

Use ref for:
- DOM access
- Persistent values not affecting render
- Storing timers/intervals

Use state for:
- Values that affect render
- User input
- Component display data
```

### Q2: When should you use forwardRef?

```
Answer: Use forwardRef when:
1. You need to expose DOM element to parent
2. Custom component needs imperative control
3. Parent needs direct DOM access

Example: Custom TextInput
function TextInput(props, ref) {
  return <input ref={ref} {...props} />;
}

export default forwardRef(TextInput);

Don't use forwardRef:
- For props forwarding (use ...props)
- For simple custom components
- When declarative approach works
```

### Q3: What does useImperativeHandle do?

```
Answer: useImperativeHandle customizes what a ref exposes.

Instead of exposing raw DOM element:
const ref = useRef(null);
// ref.current = input DOM element

Expose only what's needed:
useImperativeHandle(ref, () => ({
  focus: () => { /* focus logic */ },
  getValue: () => { /* get value */ },
  clear: () => { /* clear value */ }
}));

Benefits:
- Hide implementation details
- Provide custom methods
- Control what parent can access
- Better abstraction
```

---

## Resources

- **useRef Documentation:** https://react.dev/reference/react/useRef
- **forwardRef Documentation:** https://react.dev/reference/react/forwardRef
- **useImperativeHandle:** https://react.dev/reference/react/useImperativeHandle
- **When to Use Refs:** https://react.dev/learn/manipulating-the-dom-with-refs
- **Refs and DOM:** https://react.dev/learn/avoiding-direct-dom-manipulation

---

**Next:** [Part 3.8: Custom Hooks](./03-custom-hooks.md) - Master extracting and reusing hook logic
