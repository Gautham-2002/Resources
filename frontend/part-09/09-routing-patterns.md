# Part 9.3: Routing Patterns & Authentication

## What You'll Learn

- Complete authentication flow implementation
- Route protection patterns
- Redirect after login/logout
- Role-based access control
- Route transitions and loading states
- Deep linking and URL state synchronization
- 404 and error boundary patterns

---

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [Protected Routes](#protected-routes)
3. [Role-Based Access Control](#role-based-access-control)
4. [URL State Synchronization](#url-state-synchronization)
5. [Route Transitions](#route-transitions)
6. [Deep Linking](#deep-linking)
7. [Complete Auth Implementation](#complete-auth-implementation)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Resources](#resources)

---

## Authentication Flow

### Auth Store (Zustand)

```typescript
// stores/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginDTO) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,

      login: async (credentials) => {
        const { accessToken, user } = await authApi.login(credentials);
        set({ user, accessToken, isAuthenticated: true });
      },

      logout: () => {
        authApi.logout().catch(() => {});
        set({ user: null, accessToken: null, isAuthenticated: false });
      },

      checkAuth: async () => {
        try {
          const user = await authApi.getMe();
          set({ user, isAuthenticated: true });
        } catch {
          set({ user: null, accessToken: null, isAuthenticated: false });
        }
      },
    }),
    { name: 'auth-storage', partialize: (state) => ({ accessToken: state.accessToken }) }
  )
);
```

---

## Protected Routes

### Guard Layout

```typescript
// routes/_authenticated.tsx
import { createRoute, redirect, Outlet } from '@tanstack/react-router';

const authenticatedRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'authenticated',
  beforeLoad: ({ context, location }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({
        to: '/login',
        search: { redirect: location.href },
      });
    }
  },
  component: () => (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <TopNav />
        <main className="flex-1 p-6 bg-gray-50 dark:bg-gray-900">
          <Outlet />
        </main>
      </div>
    </div>
  ),
});
```

### Login Page with Redirect

```typescript
// routes/login.tsx
const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  validateSearch: z.object({
    redirect: z.string().optional(),
  }),
  beforeLoad: ({ context, search }) => {
    // If already logged in, redirect away
    if (context.auth.isAuthenticated) {
      throw redirect({ to: search.redirect || '/dashboard' });
    }
  },
  component: LoginPage,
});

function LoginPage() {
  const { redirect: redirectTo } = loginRoute.useSearch();
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const onSubmit = async (data: LoginForm) => {
    await login(data);
    navigate({ to: redirectTo || '/dashboard' });
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg p-8">
        <h1 className="text-2xl font-bold text-center mb-6">Sign In</h1>
        <LoginForm onSubmit={onSubmit} />
      </div>
    </div>
  );
}
```

---

## Role-Based Access Control

```typescript
// Route-level role checking
const adminRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/admin',
  beforeLoad: ({ context }) => {
    if (context.auth.user?.role !== 'admin') {
      throw redirect({ to: '/dashboard' });
    }
  },
  component: AdminDashboard,
});

// Component-level role checking
function RoleGate({ children, roles }: { children: React.ReactNode; roles: string[] }) {
  const user = useAuthStore((s) => s.user);

  if (!user || !roles.includes(user.role)) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-600">
          You don't have permission to view this content
        </h2>
      </div>
    );
  }

  return <>{children}</>;
}

// Usage
<RoleGate roles={['admin', 'manager']}>
  <SensitiveComponent />
</RoleGate>
```

---

## URL State Synchronization

### Filters in URL

```typescript
const productsSearchSchema = z.object({
  category: z.string().optional(),
  minPrice: z.coerce.number().optional(),
  maxPrice: z.coerce.number().optional(),
  sort: z.enum(['price-asc', 'price-desc', 'name', 'newest']).default('newest'),
  page: z.coerce.number().positive().default(1),
});

type ProductsSearch = z.infer<typeof productsSearchSchema>;

const productsRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/products',
  validateSearch: productsSearchSchema,
  component: ProductsPage,
});

function ProductsPage() {
  const search = productsRoute.useSearch();
  const navigate = useNavigate();

  // Update search params helper
  const updateSearch = (updates: Partial<ProductsSearch>) => {
    navigate({
      search: (prev) => ({ ...prev, ...updates, page: 1 }), // Reset page on filter change
    });
  };

  const { data } = useQuery({
    queryKey: ['products', search],
    queryFn: () => productsApi.list(search),
  });

  return (
    <div className="flex gap-6">
      {/* Filters sidebar */}
      <aside className="w-64 space-y-4">
        <CategoryFilter
          value={search.category}
          onChange={(category) => updateSearch({ category })}
        />
        <PriceRange
          min={search.minPrice}
          max={search.maxPrice}
          onChange={(min, max) => updateSearch({ minPrice: min, maxPrice: max })}
        />
        <SortSelect
          value={search.sort}
          onChange={(sort) => updateSearch({ sort })}
        />
      </aside>

      {/* Product grid */}
      <div className="flex-1">
        <ProductGrid products={data?.data ?? []} />
        <Pagination
          page={search.page}
          totalPages={data?.meta.totalPages ?? 1}
          onChange={(page) => navigate({ search: (prev) => ({ ...prev, page }) })}
        />
      </div>
    </div>
  );
}
```

---

## Route Transitions

### Smooth Page Transitions

```typescript
// Root layout with transition
import { useRouterState } from '@tanstack/react-router';

function RootLayout() {
  const isNavigating = useRouterState({ select: (s) => s.isLoading });

  return (
    <div>
      {/* Top loading bar */}
      {isNavigating && (
        <div className="fixed top-0 left-0 right-0 z-50">
          <div className="h-1 bg-blue-600 animate-[loading_1s_ease-in-out_infinite]" />
        </div>
      )}

      <Outlet />
    </div>
  );
}
```

---

## Deep Linking

```typescript
// Deep link with tabs
const userRoute = createRoute({
  path: '/users/$userId',
  validateSearch: z.object({
    tab: z.enum(['profile', 'posts', 'settings']).default('profile'),
  }),
  component: UserPage,
});

function UserPage() {
  const { userId } = userRoute.useParams();
  const { tab } = userRoute.useSearch();
  const navigate = useNavigate();

  return (
    <div>
      {/* Tab navigation */}
      <div className="flex border-b">
        {['profile', 'posts', 'settings'].map((t) => (
          <button
            key={t}
            onClick={() => navigate({ search: { tab: t } })}
            className={cn(
              'px-4 py-2 border-b-2 font-medium capitalize',
              tab === t
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'profile' && <ProfileTab userId={userId} />}
      {tab === 'posts' && <PostsTab userId={userId} />}
      {tab === 'settings' && <SettingsTab userId={userId} />}
    </div>
  );
}

// Users can share: /users/123?tab=settings
// Bookmarkable, shareable, browser back/forward works
```

---

## Complete Auth Implementation

### Full Router Setup

```typescript
// router.tsx
import { createRouter, createRootRouteWithContext } from '@tanstack/react-router';

interface RouterContext {
  queryClient: QueryClient;
  auth: AuthState;
}

const rootRoute = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
  notFoundComponent: NotFoundPage,
});

// Public routes
const loginRoute = createRoute({ /* ... */ });
const registerRoute = createRoute({ /* ... */ });

// Protected layout
const protectedLayout = createRoute({
  getParentRoute: () => rootRoute,
  id: 'protected',
  beforeLoad: ({ context, location }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({ to: '/login', search: { redirect: location.href } });
    }
  },
  component: ProtectedLayout,
});

// Protected routes
const dashboardRoute = createRoute({ getParentRoute: () => protectedLayout, path: '/dashboard' });
const usersRoute = createRoute({ getParentRoute: () => protectedLayout, path: '/users' });
const settingsRoute = createRoute({ getParentRoute: () => protectedLayout, path: '/settings' });

const routeTree = rootRoute.addChildren([
  loginRoute,
  registerRoute,
  protectedLayout.addChildren([dashboardRoute, usersRoute, settingsRoute]),
]);

export const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
  context: {
    queryClient: undefined!,
    auth: undefined!,
  },
});
```

---

## Common Patterns & Best Practices

### Pattern 1: Scroll Restoration

```typescript
const router = createRouter({
  routeTree,
  defaultPreloadStaleTime: 0,
  scrollRestoration: true, // Automatic scroll restoration
});
```

### Pattern 2: URL as Single Source of Truth

```
For filter/search pages, the URL should be the source of truth:
- Read state FROM the URL (useSearch)
- Write state TO the URL (navigate with search)
- Components derive their state from search params
- This gives you: shareable URLs, browser back/forward, bookmarkable state
```

---

## Common Pitfalls

### Pitfall 1: Auth Race Condition

```typescript
// ❌ Auth check happens after render
function App() {
  const { checkAuth } = useAuthStore();
  useEffect(() => { checkAuth(); }, []);
  return <RouterProvider router={router} />;
}

// ✅ Ensure auth is checked before router
function App() {
  const [isReady, setIsReady] = useState(false);
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth().finally(() => setIsReady(true));
  }, []);

  if (!isReady) return <FullPageSpinner />;
  return <RouterProvider router={router} />;
}
```

---

## Resources

- **TanStack Router Auth Guide:** https://tanstack.com/router/latest/docs/framework/react/guide/authenticated-routes
- **Search Params:** https://tanstack.com/router/latest/docs/framework/react/guide/search-params
- **Route Loaders:** https://tanstack.com/router/latest/docs/framework/react/guide/data-loading

---

**Next:** [Part 10.1: TanStack Table Fundamentals](../part-10/10-tanstack-table-fundamentals.md)
