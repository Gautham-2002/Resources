# Part 9.1: TanStack Router Fundamentals

## What You'll Learn

- Why TanStack Router over React Router
- Type-safe routing concepts
- Route definition and file structure
- Navigation and links
- Route parameters and search params
- Layout routes and outlets
- Loading states and pending UI

---

## Table of Contents

1. [Why TanStack Router](#why-tanstack-router)
2. [Setup & Installation](#setup--installation)
3. [Route Definitions](#route-definitions)
4. [Navigation](#navigation)
5. [Route Parameters](#route-parameters)
6. [Search Parameters](#search-parameters)
7. [Layout Routes](#layout-routes)
8. [Loading States](#loading-states)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Resources](#resources)

---

## Why TanStack Router

### Comparison with React Router

```typescript
// React Router: Runtime type checking
<Route path="/users/:id" element={<UserPage />} />
// ❌ No type safety for params
// ❌ Search params are untyped strings
// ❌ Links to invalid routes compile fine

// TanStack Router: Compile-time type checking
const userRoute = createRoute({
  path: '/users/$userId',
  component: UserPage,
  validateSearch: (search) => ({ tab: search.tab || 'profile' }),
});
// ✅ Params are fully typed
// ✅ Search params are validated with schemas
// ✅ Invalid links cause TypeScript errors
// ✅ Route loaders for data prefetching
```

### Key Advantages

```
1. Full type safety (params, search, loaders, context)
2. Built-in search param management
3. Route-level data loading
4. Nested layouts with outlets
5. Pending/stale UI states
6. File-based routing (optional)
7. Built-in devtools
8. Integrates with TanStack Query
```

---

## Setup & Installation

```bash
pnpm add @tanstack/react-router
pnpm add -D @tanstack/router-devtools @tanstack/router-plugin
```

### Vite Plugin Setup

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { TanStackRouterVite } from '@tanstack/router-plugin/vite';

export default defineConfig({
  plugins: [
    TanStackRouterVite(), // Auto-generates route tree
    react(),
  ],
});
```

---

## Route Definitions

### Code-Based Routes

```typescript
// routes/__root.tsx
import { createRootRoute, Outlet } from '@tanstack/react-router';

export const rootRoute = createRootRoute({
  component: () => (
    <div className="min-h-screen">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  ),
});

// routes/index.tsx
import { createRoute } from '@tanstack/react-router';
import { rootRoute } from './__root';

export const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: HomePage,
});

// routes/users.tsx
export const usersRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/users',
  component: UsersPage,
});

// routes/users.$userId.tsx
export const userDetailRoute = createRoute({
  getParentRoute: () => usersRoute,
  path: '/$userId',
  component: UserDetailPage,
});

// Create route tree
const routeTree = rootRoute.addChildren([
  indexRoute,
  usersRoute.addChildren([userDetailRoute]),
]);

// Create router
export const router = createRouter({ routeTree });

// Type registration
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

// main.tsx
import { RouterProvider } from '@tanstack/react-router';
import { router } from './routes';

function App() {
  return <RouterProvider router={router} />;
}
```

### File-Based Routes (Recommended)

```
src/
  routes/
    __root.tsx           → Root layout
    index.tsx            → / (home page)
    about.tsx            → /about
    users/
      index.tsx          → /users
      $userId.tsx        → /users/:userId
      $userId.edit.tsx   → /users/:userId/edit
    _layout.tsx          → Layout wrapper (not a route)
    _layout/
      dashboard.tsx      → /dashboard (uses _layout)
      settings.tsx       → /settings (uses _layout)
```

---

## Navigation

### Link Component

```typescript
import { Link } from '@tanstack/react-router';

function Navigation() {
  return (
    <nav className="flex gap-4">
      {/* Basic link */}
      <Link to="/" className="hover:text-blue-600">
        Home
      </Link>

      {/* Link with params */}
      <Link
        to="/users/$userId"
        params={{ userId: '123' }}
        className="hover:text-blue-600"
      >
        User Profile
      </Link>

      {/* Link with search params */}
      <Link
        to="/users"
        search={{ page: 1, filter: 'active' }}
        className="hover:text-blue-600"
      >
        Active Users
      </Link>

      {/* Active link styling */}
      <Link
        to="/about"
        activeProps={{ className: 'text-blue-600 font-bold' }}
        inactiveProps={{ className: 'text-gray-600' }}
      >
        About
      </Link>
    </nav>
  );
}
```

### Programmatic Navigation

```typescript
import { useNavigate, useRouter } from '@tanstack/react-router';

function LoginForm() {
  const navigate = useNavigate();

  const handleLogin = async (data: LoginData) => {
    await loginUser(data);

    // Navigate after login
    navigate({ to: '/dashboard' });

    // With params
    navigate({ to: '/users/$userId', params: { userId: '123' } });

    // With search params
    navigate({ to: '/users', search: { page: 1, filter: 'active' } });

    // Replace history (can't go back)
    navigate({ to: '/dashboard', replace: true });
  };
}
```

---

## Route Parameters

### Typed Params

```typescript
// Route definition
export const userRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/users/$userId',
  component: UserPage,
});

// Component with typed params
function UserPage() {
  const { userId } = userRoute.useParams();
  // userId is typed as string!

  const { data: user } = useQuery({
    queryKey: ['users', userId],
    queryFn: () => usersApi.getById(userId),
  });

  return <div>{user?.name}</div>;
}
```

---

## Search Parameters

### Validated Search Params

```typescript
import { z } from 'zod';

const usersSearchSchema = z.object({
  page: z.number().positive().default(1),
  limit: z.number().min(1).max(100).default(20),
  search: z.string().optional(),
  sort: z.enum(['name', 'email', 'createdAt']).default('name'),
  order: z.enum(['asc', 'desc']).default('asc'),
});

export const usersRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/users',
  validateSearch: usersSearchSchema,
  component: UsersPage,
});

function UsersPage() {
  const search = usersRoute.useSearch();
  // search is fully typed:
  // { page: number; limit: number; search?: string; sort: 'name'|'email'|'createdAt'; order: 'asc'|'desc' }

  const navigate = useNavigate();

  return (
    <div>
      <input
        value={search.search ?? ''}
        onChange={(e) => navigate({
          search: (prev) => ({ ...prev, search: e.target.value, page: 1 }),
        })}
        placeholder="Search users..."
      />

      <select
        value={search.sort}
        onChange={(e) => navigate({
          search: (prev) => ({ ...prev, sort: e.target.value }),
        })}
      >
        <option value="name">Name</option>
        <option value="email">Email</option>
        <option value="createdAt">Created At</option>
      </select>

      {/* Pagination */}
      <button onClick={() => navigate({
        search: (prev) => ({ ...prev, page: prev.page + 1 }),
      })}>
        Next Page
      </button>
    </div>
  );
}
```

---

## Layout Routes

```typescript
// Shared layout for authenticated pages
const authenticatedLayout = createRoute({
  getParentRoute: () => rootRoute,
  id: 'authenticated',
  component: () => (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  ),
});

// Dashboard uses the authenticated layout
const dashboardRoute = createRoute({
  getParentRoute: () => authenticatedLayout,
  path: '/dashboard',
  component: DashboardPage,
});

// Settings also uses it
const settingsRoute = createRoute({
  getParentRoute: () => authenticatedLayout,
  path: '/settings',
  component: SettingsPage,
});

// Route tree
const routeTree = rootRoute.addChildren([
  indexRoute,
  authenticatedLayout.addChildren([
    dashboardRoute,
    settingsRoute,
  ]),
]);
```

---

## Loading States

### Route Loaders

```typescript
export const userRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/users/$userId',
  loader: async ({ params, context }) => {
    // Fetch data before rendering
    return context.queryClient.ensureQueryData({
      queryKey: ['users', params.userId],
      queryFn: () => usersApi.getById(params.userId),
    });
  },
  pendingComponent: () => <UserPageSkeleton />,
  errorComponent: ({ error }) => <ErrorDisplay error={error} />,
  component: UserPage,
});

function UserPage() {
  const user = userRoute.useLoaderData();
  // Data is guaranteed to be available!
  return <div>{user.name}</div>;
}
```

### Pending UI

```typescript
// Show a global loading bar during navigation
function RootLayout() {
  const router = useRouter();
  const isLoading = router.state.isLoading;

  return (
    <div>
      {isLoading && (
        <div className="fixed top-0 left-0 right-0 h-1 bg-blue-500 animate-pulse z-50" />
      )}
      <Outlet />
    </div>
  );
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Route-Level Code Splitting

```typescript
const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dashboard',
  component: lazy(() => import('./pages/Dashboard')),
});
```

### Pattern 2: Breadcrumbs from Route Context

```typescript
// Add metadata to routes
const usersRoute = createRoute({
  path: '/users',
  context: () => ({ breadcrumb: 'Users' }),
});

const userDetailRoute = createRoute({
  path: '/$userId',
  getParentRoute: () => usersRoute,
  context: ({ params }) => ({ breadcrumb: `User ${params.userId}` }),
});
```

---

## Common Pitfalls

### Pitfall 1: Not Registering Router Types

```typescript
// ❌ Links are untyped
<Link to="/users">Users</Link>

// ✅ Register router for full type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
// Now Link's `to` prop only accepts valid routes!
```

### Pitfall 2: Search Params as State

```typescript
// ❌ Storing transient UI state in URL
navigate({ search: { isDropdownOpen: true } });

// ✅ Only store shareable/bookmarkable state in URL
navigate({ search: { page: 2, filter: 'active' } });
```

---

## Resources

- **TanStack Router Documentation:** https://tanstack.com/router/latest
- **File-Based Routing:** https://tanstack.com/router/latest/docs/framework/react/guide/file-based-routing
- **Type-Safe Search Params:** https://tanstack.com/router/latest/docs/framework/react/guide/search-params
- **Route Loaders:** https://tanstack.com/router/latest/docs/framework/react/guide/data-loading

---

**Next:** [Part 9.2: TanStack Router Advanced Patterns](./09-tanstack-router-advanced.md)
