# Part 9.2: TanStack Router Advanced Patterns

## What You'll Learn

- Nested routing and complex layouts
- Route guards and authentication middleware
- Lazy loading routes for code splitting
- Programmatic navigation patterns
- Route context and data sharing
- Server-side rendering considerations

---

## Table of Contents

1. [Nested Routing](#nested-routing)
2. [Route Guards & Authentication](#route-guards--authentication)
3. [Lazy Loading Routes](#lazy-loading-routes)
4. [Route Context](#route-context)
5. [Error Boundaries Per Route](#error-boundaries-per-route)
6. [Not Found Routes](#not-found-routes)
7. [Redirect Patterns](#redirect-patterns)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Resources](#resources)

---

## Nested Routing

### Multi-Level Nesting

```typescript
// Route hierarchy:
// /                     → Home
// /dashboard            → Dashboard (with sidebar layout)
// /dashboard/analytics  → Analytics
// /dashboard/reports    → Reports
// /settings             → Settings (with sidebar layout)
// /settings/profile     → Profile settings
// /settings/security    → Security settings

// Authenticated layout with sidebar
const authLayout = createRoute({
  getParentRoute: () => rootRoute,
  id: 'auth-layout',
  component: () => {
    return (
      <div className="flex min-h-screen">
        <aside className="w-64 border-r bg-gray-50 dark:bg-gray-900 p-4">
          <Sidebar />
        </aside>
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    );
  },
});

// Dashboard section
const dashboardRoute = createRoute({
  getParentRoute: () => authLayout,
  path: '/dashboard',
  component: () => (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <nav className="flex gap-4 mb-6 border-b pb-4">
        <Link to="/dashboard/analytics" activeProps={{ className: 'text-blue-600 font-semibold' }}>
          Analytics
        </Link>
        <Link to="/dashboard/reports" activeProps={{ className: 'text-blue-600 font-semibold' }}>
          Reports
        </Link>
      </nav>
      <Outlet />
    </div>
  ),
});

const analyticsRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: '/analytics',
  component: AnalyticsPage,
});

const reportsRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: '/reports',
  component: ReportsPage,
});
```

---

## Route Guards & Authentication

### beforeLoad Guard

```typescript
// Protected route — redirect if not authenticated
const authLayout = createRoute({
  getParentRoute: () => rootRoute,
  id: 'authenticated',
  beforeLoad: async ({ context, location }) => {
    const { authStore } = context;

    if (!authStore.isAuthenticated) {
      throw redirect({
        to: '/login',
        search: {
          redirect: location.href, // Remember where they wanted to go
        },
      });
    }
  },
  component: AuthenticatedLayout,
});

// Role-based access
const adminRoute = createRoute({
  getParentRoute: () => authLayout,
  path: '/admin',
  beforeLoad: async ({ context }) => {
    if (context.authStore.user?.role !== 'admin') {
      throw redirect({ to: '/dashboard' });
    }
  },
  component: AdminPage,
});
```

### Router Context with Auth

```typescript
// Create router with auth context
const router = createRouter({
  routeTree,
  context: {
    queryClient,
    authStore: useAuthStore.getState(),
  },
});

// Update context when auth changes
function App() {
  const auth = useAuthStore();

  return (
    <RouterProvider
      router={router}
      context={{ queryClient, authStore: auth }}
    />
  );
}
```

---

## Lazy Loading Routes

### Code Splitting Per Route

```typescript
// Lazy load heavy pages
const dashboardRoute = createRoute({
  getParentRoute: () => authLayout,
  path: '/dashboard',
  component: lazy(() => import('./pages/Dashboard')),
  pendingComponent: () => <PageSkeleton />,
});

// Or with createLazyRoute
const dashboardRoute = createRoute({
  getParentRoute: () => authLayout,
  path: '/dashboard',
}).lazy(() =>
  import('./pages/Dashboard.lazy').then((m) => m.Route)
);

// pages/Dashboard.lazy.tsx
import { createLazyRoute } from '@tanstack/react-router';

export const Route = createLazyRoute('/dashboard')({
  component: DashboardPage,
  pendingComponent: DashboardSkeleton,
  errorComponent: DashboardError,
});
```

---

## Route Context

### Sharing Data Across Routes

```typescript
// Root route provides global context
const rootRoute = createRootRouteWithContext<{
  queryClient: QueryClient;
  auth: AuthState;
}>()({
  component: RootLayout,
});

// Child routes access context
const userRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/users/$userId',
  loader: async ({ params, context }) => {
    // Access queryClient from context
    return context.queryClient.ensureQueryData({
      queryKey: ['users', params.userId],
      queryFn: () => usersApi.getById(params.userId),
    });
  },
  component: UserPage,
});
```

---

## Error Boundaries Per Route

```typescript
const userRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/users/$userId',
  component: UserPage,

  // Route-specific error handling
  errorComponent: ({ error, reset }) => (
    <div className="text-center py-12">
      <h2 className="text-2xl font-bold text-red-600 mb-4">
        Failed to load user
      </h2>
      <p className="text-gray-600 mb-6">{error.message}</p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Try Again
      </button>
    </div>
  ),
});
```

---

## Not Found Routes

```typescript
const rootRoute = createRootRoute({
  component: RootLayout,
  notFoundComponent: () => (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
        <p className="text-xl text-gray-600 mb-8">Page not found</p>
        <Link
          to="/"
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Go Home
        </Link>
      </div>
    </div>
  ),
});
```

---

## Redirect Patterns

```typescript
// Post-login redirect
const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  validateSearch: z.object({
    redirect: z.string().optional(),
  }),
  component: LoginPage,
});

function LoginPage() {
  const { redirect: redirectUrl } = loginRoute.useSearch();
  const navigate = useNavigate();

  const handleLogin = async (data: LoginData) => {
    await loginUser(data);
    navigate({ to: redirectUrl || '/dashboard' });
  };
}

// Index redirect
const indexRoute = createRoute({
  getParentRoute: () => authLayout,
  path: '/',
  beforeLoad: () => {
    throw redirect({ to: '/dashboard' });
  },
});
```

---

## Common Patterns & Best Practices

### Pattern 1: Route Organization

```
src/routes/
  __root.tsx                 # Root layout
  index.tsx                  # Home page
  login.tsx                  # Login page
  _authenticated.tsx         # Auth guard layout
  _authenticated/
    dashboard.tsx            # /dashboard
    dashboard.analytics.tsx  # /dashboard/analytics
    users/
      index.tsx             # /users
      $userId.tsx           # /users/:id
```

### Pattern 2: DevTools in Development

```typescript
import { TanStackRouterDevtools } from '@tanstack/router-devtools';

const rootRoute = createRootRoute({
  component: () => (
    <>
      <Outlet />
      {import.meta.env.DEV && <TanStackRouterDevtools />}
    </>
  ),
});
```

---

## Common Pitfalls

### Pitfall 1: Not Using Loaders for Critical Data

```typescript
// ❌ Component fetches data (shows loading spinner)
function UserPage() {
  const { data, isLoading } = useQuery({ queryKey: ['user'], queryFn: fetchUser });
  if (isLoading) return <Spinner />;
  return <div>{data.name}</div>;
}

// ✅ Loader ensures data before render (instant page)
const userRoute = createRoute({
  path: '/users/$userId',
  loader: ({ params, context }) =>
    context.queryClient.ensureQueryData({
      queryKey: ['users', params.userId],
      queryFn: () => usersApi.getById(params.userId),
    }),
  pendingComponent: UserSkeleton,
  component: UserPage,
});
```

### Pitfall 2: Forgetting to Handle Pending State

```typescript
// ❌ No pending UI — page appears stuck during navigation
component: UserPage,

// ✅ Show skeleton while route loads
pendingComponent: () => <UserPageSkeleton />,
component: UserPage,
```

---

## Resources

- **TanStack Router Guides:** https://tanstack.com/router/latest/docs/framework/react/guide
- **Authentication Patterns:** https://tanstack.com/router/latest/docs/framework/react/guide/authenticated-routes
- **Code Splitting:** https://tanstack.com/router/latest/docs/framework/react/guide/code-splitting
- **Route Context:** https://tanstack.com/router/latest/docs/framework/react/guide/router-context

---

**Next:** [Part 9.3: Routing Patterns & Authentication](./09-routing-patterns.md)
