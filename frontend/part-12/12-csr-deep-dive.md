# Part 12.2: Client-Side Rendering Deep Dive

## What You'll Learn

- CSR architecture and lifecycle
- Code splitting and lazy loading
- Suspense boundaries for loading states
- Error boundaries for resilient UIs
- Performance optimization for CSR apps
- SPA routing considerations

---

## Table of Contents

1. [CSR Architecture](#csr-architecture)
2. [Code Splitting](#code-splitting)
3. [React.lazy & Suspense](#reactlazy--suspense)
4. [Error Boundaries](#error-boundaries)
5. [Loading State Patterns](#loading-state-patterns)
6. [SEO Considerations](#seo-considerations)
7. [Common Patterns & Best Practices](#common-patterns--best-practices)
8. [Common Pitfalls](#common-pitfalls)
9. [Resources](#resources)

---

## CSR Architecture

### How Vite + React CSR Works

```
1. index.html loaded (minimal HTML shell)
2. <script type="module" src="/src/main.tsx"> loaded
3. Vite serves ES modules (dev) or bundled chunks (prod)
4. React mounts to #root
5. Router determines which page to render
6. Components fetch data via TanStack Query
7. UI rendered in the browser

Development (Vite dev server):
  - ES modules served individually
  - HMR for instant updates
  - No bundling needed

Production (Vite build):
  - Code split into chunks
  - Tree-shaken and minified
  - Served as static files from CDN
```

---

## Code Splitting

### Route-Based Code Splitting

```typescript
import { lazy, Suspense } from 'react';

// Each route is a separate chunk
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Users = lazy(() => import('./pages/Users'));
const Settings = lazy(() => import('./pages/Settings'));
const Analytics = lazy(() => import('./pages/Analytics'));

// Vite creates separate chunks:
// dist/assets/Dashboard-abc123.js
// dist/assets/Users-def456.js
// dist/assets/Settings-ghi789.js
```

### Named Exports with lazy

```typescript
// If the page is a named export:
const Dashboard = lazy(() =>
  import('./pages/Dashboard').then(module => ({
    default: module.DashboardPage,
  }))
);
```

### Preloading on Hover

```typescript
// Preload the chunk when user hovers over the link
function NavLink({ to, children, loadComponent }: {
  to: string;
  children: React.ReactNode;
  loadComponent: () => Promise<any>;
}) {
  return (
    <Link
      to={to}
      onMouseEnter={() => loadComponent()}
      onFocus={() => loadComponent()}
    >
      {children}
    </Link>
  );
}

// Usage
<NavLink to="/analytics" loadComponent={() => import('./pages/Analytics')}>
  Analytics
</NavLink>
```

---

## React.lazy & Suspense

### Basic Suspense Boundary

```typescript
function App() {
  return (
    <Layout>
      <Suspense fallback={<PageSkeleton />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/users" element={<Users />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
```

### Nested Suspense Boundaries

```typescript
function DashboardPage() {
  return (
    <div className="grid grid-cols-3 gap-6">
      {/* Each widget loads independently */}
      <Suspense fallback={<WidgetSkeleton />}>
        <RevenueWidget />
      </Suspense>

      <Suspense fallback={<WidgetSkeleton />}>
        <UsersWidget />
      </Suspense>

      <Suspense fallback={<WidgetSkeleton />}>
        <OrdersWidget />
      </Suspense>
    </div>
  );
}
```

### Suspense with TanStack Query

```typescript
import { useSuspenseQuery } from '@tanstack/react-query';

// Component that suspends while loading
function RevenueWidget() {
  const { data } = useSuspenseQuery({
    queryKey: ['revenue', 'summary'],
    queryFn: () => analyticsApi.getRevenue(),
  });

  // No loading check needed — Suspense handles it!
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm">
      <h3 className="text-sm font-medium text-gray-500">Revenue</h3>
      <p className="text-3xl font-bold mt-2">${data.total.toLocaleString()}</p>
    </div>
  );
}
```

---

## Error Boundaries

### Class-Based Error Boundary

```typescript
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error boundary caught:', error, errorInfo);
    // Send to error tracking service
    // errorTracker.captureException(error, { extra: errorInfo });
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (typeof this.props.fallback === 'function') {
        return this.props.fallback(this.state.error!, this.reset);
      }
      return this.props.fallback ?? <DefaultErrorUI error={this.state.error!} onReset={this.reset} />;
    }

    return this.props.children;
  }
}

function DefaultErrorUI({ error, onReset }: { error: Error; onReset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
      <div className="text-6xl mb-4">💥</div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">Something went wrong</h2>
      <p className="text-gray-500 mb-6 text-center max-w-md">{error.message}</p>
      <button onClick={onReset} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
        Try Again
      </button>
    </div>
  );
}
```

### Using Error Boundaries

```typescript
function App() {
  return (
    <ErrorBoundary>
      <Layout>
        <ErrorBoundary fallback={<PageErrorUI />}>
          <Suspense fallback={<PageSkeleton />}>
            <Router />
          </Suspense>
        </ErrorBoundary>
      </Layout>
    </ErrorBoundary>
  );
}
```

---

## Loading State Patterns

### Skeleton Screens

```typescript
function UserCardSkeleton() {
  return (
    <div className="animate-pulse border rounded-xl p-4">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 bg-gray-200 rounded-full" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-gray-200 rounded w-3/4" />
          <div className="h-3 bg-gray-200 rounded w-1/2" />
        </div>
      </div>
    </div>
  );
}

// Reusable skeleton list
function SkeletonList({ count = 5, component: Skeleton }: { count?: number; component: React.ComponentType }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} />
      ))}
    </div>
  );
}
```

---

## SEO Considerations

```typescript
// For CSR apps that need basic SEO:

// 1. React Helmet for meta tags
import { Helmet } from 'react-helmet-async';

function ProductPage({ product }) {
  return (
    <>
      <Helmet>
        <title>{product.name} | My Store</title>
        <meta name="description" content={product.description} />
        <meta property="og:title" content={product.name} />
        <meta property="og:image" content={product.image} />
      </Helmet>
      <ProductContent product={product} />
    </>
  );
}

// 2. Pre-rendering service (for crawlers)
// Services like Prerender.io serve pre-rendered HTML to bots

// 3. If SEO is critical → Use Next.js or Astro instead of CSR
```

---

## Common Patterns & Best Practices

### Pattern 1: Suspense + Error Boundary Wrapper

```typescript
function AsyncBoundary({ children, fallback, errorFallback }: {
  children: React.ReactNode;
  fallback: React.ReactNode;
  errorFallback?: React.ReactNode;
}) {
  return (
    <ErrorBoundary fallback={errorFallback}>
      <Suspense fallback={fallback}>
        {children}
      </Suspense>
    </ErrorBoundary>
  );
}

// Usage
<AsyncBoundary fallback={<Skeleton />} errorFallback={<ErrorCard />}>
  <DataComponent />
</AsyncBoundary>
```

### Pattern 2: Progressive Loading

```typescript
// Load critical content first, defer secondary content
function Dashboard() {
  return (
    <>
      {/* Critical: loads with page */}
      <DashboardHeader />
      <KPICards />

      {/* Deferred: loads after */}
      <Suspense fallback={<ChartSkeleton />}>
        <RevenueChart />
      </Suspense>

      <Suspense fallback={<TableSkeleton />}>
        <RecentOrdersTable />
      </Suspense>
    </>
  );
}
```

---

## Common Pitfalls

### Pitfall 1: Single Suspense Boundary

```typescript
// ❌ Everything waits for the slowest component
<Suspense fallback={<FullPageSpinner />}>
  <FastComponent />
  <SlowComponent />  {/* Blocks everything */}
</Suspense>

// ✅ Independent boundaries
<FastComponent />
<Suspense fallback={<Skeleton />}>
  <SlowComponent />
</Suspense>
```

### Pitfall 2: Not Code Splitting

```typescript
// ❌ One massive bundle (1MB+ JS)
import Dashboard from './pages/Dashboard';
import Analytics from './pages/Analytics';
import Reports from './pages/Reports';

// ✅ Split per route
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Reports = lazy(() => import('./pages/Reports'));
```

---

## Resources

- **React.lazy:** https://react.dev/reference/react/lazy
- **Suspense:** https://react.dev/reference/react/Suspense
- **Error Boundaries:** https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary
- **Code Splitting:** https://vitejs.dev/guide/build#chunking-strategy

---

**Next:** [Part 12.3: SSR Deep Dive](./12-ssr-deep-dive.md)
