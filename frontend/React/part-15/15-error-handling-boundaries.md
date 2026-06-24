# Part 15.2: Error Handling and Error Boundaries

## What You'll Learn

- Creating robust error boundaries
- Error recovery patterns
- Global error handlers
- Error logging and monitoring
- Graceful degradation strategies
- Error UI patterns
- Handling different error types
- Interview questions

---

## Table of Contents

1. [Error Boundary Fundamentals](#error-boundary-fundamentals)
2. [Advanced Error Boundaries](#advanced-error-boundaries)
3. [Global Error Handlers](#global-error-handlers)
4. [Async Error Handling](#async-error-handling)
5. [Error Recovery Patterns](#error-recovery-patterns)
6. [Graceful Degradation](#graceful-degradation)
7. [Error Logging](#error-logging)
8. [Error UI Patterns](#error-ui-patterns)
9. [Common Patterns](#common-patterns)
10. [Interview Questions](#interview-questions)
11. [Resources](#resources)

---

## Error Boundary Fundamentals

### Basic Error Boundary

```jsx
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null 
    };
  }
  
  static getDerivedStateFromError(error) {
    // Update state so next render shows fallback UI
    return { hasError: true, error };
  }
  
  componentDidCatch(error, errorInfo) {
    // Log error for monitoring
    console.error('Error caught by boundary:', error);
    console.error('Error info:', errorInfo);
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
        </div>
      );
    }
    
    return this.props.children;
  }
}

// Usage
function App() {
  return (
    <ErrorBoundary>
      <MainApp />
    </ErrorBoundary>
  );
}
```

### Error Boundary Scope

```javascript
// What Error Boundaries CATCH:
// ✅ Rendering errors
// ✅ Lifecycle method errors
// ✅ Constructor errors
// ✅ useEffect errors (in class components)

// What Error Boundaries DON'T CATCH:
// ❌ Event handler errors (use try-catch)
// ❌ Async code (use try-catch)
// ❌ Server-side rendering
// ❌ Errors in the Error Boundary itself
// ❌ Promises (not awaited)
```

---

## Advanced Error Boundaries

### Error Boundary with Recovery

```jsx
class ErrorBoundaryWithRecovery extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorCount: 0
    };
  }
  
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  
  componentDidCatch(error, errorInfo) {
    // Log error
    console.error('Error:', error);
    
    // Send to error tracking
    this.logErrorToService(error, errorInfo);
    
    // Increment error count
    this.setState(prev => ({ errorCount: prev.errorCount + 1 }));
  }
  
  logErrorToService = (error, errorInfo) => {
    // Send to Sentry, Rollbar, etc
    fetch('/api/errors', {
      method: 'POST',
      body: JSON.stringify({
        message: error.toString(),
        stack: errorInfo.componentStack,
        timestamp: new Date().toISOString()
      })
    });
  }
  
  handleReset = () => {
    this.setState({ 
      hasError: false, 
      error: null 
    });
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ 
          padding: '20px', 
          border: '2px solid red',
          borderRadius: '8px',
          backgroundColor: '#ffe6e6'
        }}>
          <h2>🔴 An error occurred</h2>
          <p>{this.state.error?.message}</p>
          <p style={{ fontSize: '12px', color: '#666' }}>
            Error #{this.state.errorCount}
          </p>
          
          <button 
            onClick={this.handleReset}
            style={{ 
              padding: '8px 16px',
              marginRight: '8px',
              cursor: 'pointer'
            }}
          >
            Try again
          </button>
          
          <button 
            onClick={() => window.location.href = '/'}
            style={{ 
              padding: '8px 16px',
              cursor: 'pointer'
            }}
          >
            Go home
          </button>
        </div>
      );
    }
    
    return this.props.children;
  }
}
```

### Nested Error Boundaries

```jsx
function App() {
  return (
    <ErrorBoundary name="App">
      <Header />
      
      {/* Header crash won't crash entire app */}
      <ErrorBoundary name="Sidebar">
        <Sidebar />
      </ErrorBoundary>
      
      {/* Content crash won't crash entire app */}
      <ErrorBoundary name="MainContent">
        <MainContent />
      </ErrorBoundary>
      
      {/* Footer crash won't crash entire app */}
      <ErrorBoundary name="Footer">
        <Footer />
      </ErrorBoundary>
    </ErrorBoundary>
  );
}

// Benefits:
// - If Header crashes: Header shows error, others work
// - If Sidebar crashes: Sidebar shows error, others work
// - If MainContent crashes: Only MainContent affected
// - Much better UX than blank screen

// Inner boundary catches error first
// If it doesn't have boundary, outer catches it
```

---

## Global Error Handlers

### Window Error Handler

```javascript
// Catch unhandled errors
window.addEventListener('error', (event) => {
  console.error('Uncaught error:', event.error);
  
  // Send to error tracking service
  reportErrorToService({
    type: 'uncaught-error',
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    stack: event.error?.stack
  });
});

// Catch unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
  
  // Send to error tracking service
  reportErrorToService({
    type: 'unhandled-rejection',
    message: event.reason?.message || String(event.reason),
    stack: event.reason?.stack
  });
});

function reportErrorToService(errorData) {
  // Send to Sentry, Rollbar, etc
  fetch('/api/errors', {
    method: 'POST',
    body: JSON.stringify(errorData)
  }).catch(() => {
    // Even error reporting failed, at least log locally
    console.error('Failed to report error');
  });
}
```

### Setup in main.jsx

```jsx
// main.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

// Setup global error handlers
window.addEventListener('error', (event) => {
  console.error('Uncaught error:', event.error);
  // Report to service
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled rejection:', event.reason);
  // Report to service
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

---

## Async Error Handling

### Event Handler Errors

```jsx
function Form() {
  const [error, setError] = useState(null);
  
  // ❌ ERROR BOUNDARY WON'T CATCH THIS
  const handleBadSubmit = () => {
    throw new Error('Form error');  // Won't be caught!
  };
  
  // ✅ HANDLE WITH TRY-CATCH
  const handleGoodSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    
    try {
      const response = await fetch('/api/form', {
        method: 'POST',
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        throw new Error('Failed to submit');
      }
      
      const data = await response.json();
      console.log('Success:', data);
    } catch (err) {
      setError(err.message);
      console.error('Form submission failed:', err);
    }
  };
  
  return (
    <form onSubmit={handleGoodSubmit}>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <button type="submit">Submit</button>
    </form>
  );
}
```

### Async Function Error Handling

```jsx
function DataFetcher({ id }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    // ❌ DON'T MAKE useEffect ASYNC
    // useEffect(async () => { ... })  // WRONG!
    
    // ✅ CREATE ASYNC FUNCTION INSIDE
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`/api/items/${id}`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        setData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [id]);
  
  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error}</p>;
  return <div>{data?.name}</div>;
}
```

---

## Error Recovery Patterns

### Retry Pattern

```jsx
function RetryableComponent({ url, maxRetries = 3 }) {
  const [data, setData] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const [error, setError] = useState(null);
  
  const fetchData = async () => {
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      setData(data);
      setRetryCount(0);  // Reset on success
    } catch (err) {
      console.error('Fetch failed:', err);
      
      if (retryCount < maxRetries) {
        // Exponential backoff: wait 1s, 2s, 4s...
        const waitTime = Math.pow(2, retryCount) * 1000;
        setTimeout(() => {
          setRetryCount(retryCount + 1);
          fetchData();
        }, waitTime);
      } else {
        setError(err.message);
      }
    }
  };
  
  useEffect(() => {
    fetchData();
  }, [url]);
  
  if (error) {
    return (
      <div>
        <p>Failed after {maxRetries} retries: {error}</p>
        <button onClick={() => {
          setRetryCount(0);
          setError(null);
          fetchData();
        }}>
          Try again manually
        </button>
      </div>
    );
  }
  
  return <div>{data?.name}</div>;
}
```

### Fallback Pattern

```jsx
function SafeImageComponent({ src, alt }) {
  const [error, setError] = useState(false);
  
  if (error) {
    // Show fallback image
    return (
      <div style={{ 
        width: '100px',
        height: '100px',
        backgroundColor: '#ddd',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        No image
      </div>
    );
  }
  
  return (
    <img 
      src={src} 
      alt={alt}
      onError={() => setError(true)}
      style={{ maxWidth: '100%' }}
    />
  );
}

// Or with lazy loading
function SafeComponent({ Component, fallback }) {
  const [error, setError] = useState(false);
  
  if (error) {
    return fallback || <div>Failed to load component</div>;
  }
  
  return (
    <ErrorBoundary onError={() => setError(true)}>
      <Component />
    </ErrorBoundary>
  );
}
```

---

## Graceful Degradation

### Feature Degradation

```jsx
function AdvancedFeature() {
  const [supported, setSupported] = useState(true);
  
  useEffect(() => {
    // Check if feature is supported
    if (!navigator.geolocation) {
      setSupported(false);
    }
  }, []);
  
  if (!supported) {
    return (
      <div>
        <p>Your browser doesn't support location.</p>
        <p>Please enter your location manually.</p>
        <input placeholder="City name" />
      </div>
    );
  }
  
  // Feature is supported, use it
  return <GeolocationComponent />;
}
```

### API Fallback

```jsx
function DataComponent({ primaryApi, fallbackApi }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Try primary API first
        const response = await fetch(primaryApi);
        const data = await response.json();
        setData(data);
      } catch (err) {
        console.warn('Primary API failed, trying fallback');
        
        try {
          // Fallback to secondary API
          const response = await fetch(fallbackApi);
          const data = await response.json();
          setData(data);
        } catch (fallbackErr) {
          setError('Both APIs failed');
        }
      }
    };
    
    fetchData();
  }, [primaryApi, fallbackApi]);
  
  if (error) return <p>{error}</p>;
  return <div>{data?.name}</div>;
}
```

---

## Error Logging

### Structured Logging

```javascript
class ErrorLogger {
  static log(level, message, error, context = {}) {
    const errorData = {
      timestamp: new Date().toISOString(),
      level,
      message,
      error: {
        message: error?.message,
        stack: error?.stack,
        name: error?.name
      },
      context,
      userAgent: navigator.userAgent,
      url: window.location.href
    };
    
    // Log locally
    console.error(level, message, errorData);
    
    // Send to service
    this.reportToService(errorData);
  }
  
  static reportToService(errorData) {
    fetch('/api/errors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(errorData)
    }).catch(err => {
      console.error('Failed to report error:', err);
    });
  }
}

// Usage
try {
  riskyOperation();
} catch (error) {
  ErrorLogger.log('ERROR', 'Operation failed', error, {
    operation: 'riskyOperation',
    userId: '123'
  });
}
```

---

## Error UI Patterns

### Error Overlay

```jsx
function ErrorOverlay({ error, onDismiss }) {
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '20px',
        borderRadius: '8px',
        maxWidth: '500px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
      }}>
        <h2 style={{ color: '#d32f2f' }}>Error</h2>
        <p>{error}</p>
        
        <button 
          onClick={onDismiss}
          style={{
            padding: '8px 16px',
            backgroundColor: '#d32f2f',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
```

### Toast Notifications

```jsx
function useErrorToast() {
  const [errors, setErrors] = useState([]);
  
  const addError = (message, duration = 5000) => {
    const id = Date.now();
    setErrors(prev => [...prev, { id, message }]);
    
    setTimeout(() => {
      setErrors(prev => prev.filter(e => e.id !== id));
    }, duration);
  };
  
  return {
    errors,
    addError,
    ErrorToast: () => (
      <div style={{ position: 'fixed', bottom: '20px', right: '20px' }}>
        {errors.map(error => (
          <div 
            key={error.id}
            style={{
              backgroundColor: '#d32f2f',
              color: 'white',
              padding: '12px 16px',
              borderRadius: '4px',
              marginBottom: '8px',
              boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)'
            }}
          >
            {error.message}
          </div>
        ))}
      </div>
    )
  };
}
```

---

## Common Patterns

### Pattern 1: Safe Component Wrapper

```jsx
function SafeComponent({ Component, fallback }) {
  const [error, setError] = useState(null);
  
  if (error) {
    return fallback || <p>Failed to load</p>;
  }
  
  return (
    <ErrorBoundary onError={() => setError(true)}>
      <Component />
    </ErrorBoundary>
  );
}

// Usage
<SafeComponent 
  Component={ProblematicComponent} 
  fallback={<div>Failed to load component</div>}
/>
```

---

## Interview Questions

### Q1: What can Error Boundaries catch?

```
Answer:
Error Boundaries CATCH:
- Rendering errors in components
- Lifecycle method errors
- Constructor errors
- Errors in useLayoutEffect (in class components)

Error Boundaries DON'T CATCH:
- Event handler errors (use try-catch)
- Async code errors (use try-catch)
- Server-side rendering errors
- Errors in the error boundary itself
- Promises (not awaited)

Example:
❌ onClick={() => throw error}  // Won't catch
✅ onClick={() => { try { throw error } catch(e) {...} }}
```

### Q2: How do you handle async errors?

```
Answer:
1. In event handlers: use try-catch
2. In useEffect: create async function inside
3. In promises: use .catch()

Example:
const handleSubmit = async () => {
  try {
    const data = await fetch('/api');
    // Handle success
  } catch (error) {
    setError(error.message);
  }
};

DON'T make useEffect itself async!
DO create async function inside useEffect
```

---

## Resources

- **Error Boundaries:** https://react.dev/reference/react/Component#catching-rendering-errors
- **Error Handling:** https://react.dev/learn/error-boundaries
- **Sentry:** https://sentry.io/
- **Error Recovery:** https://github.com/jaredpalmer/error-boundaries

---

**Next:** [Part 15.3: Performance Debugging](./15-performance-debugging.md) - Finding and fixing performance issues
