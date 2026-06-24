# Part 8.3: TanStack Query Performance

## What You'll Learn

- Query key design for optimal caching
- Request deduplication
- Prefetching strategies
- Structural sharing and reference stability
- Memory management and garbage collection
- DevTools for debugging performance
- Bundle size optimization

---

## Table of Contents

1. [Query Key Design](#query-key-design)
2. [Deduplication](#deduplication)
3. [Caching Strategies](#caching-strategies)
4. [Structural Sharing](#structural-sharing)
5. [Memory Management](#memory-management)
6. [Prefetching Patterns](#prefetching-patterns)
7. [DevTools Debugging](#devtools-debugging)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Resources](#resources)

---

## Query Key Design

### The Key Factory Pattern

```typescript
// keys/userKeys.ts
export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
  detailPosts: (id: string) => [...userKeys.detail(id), 'posts'] as const,
};

// Invalidation becomes surgical:
// Invalidate ALL user data:
queryClient.invalidateQueries({ queryKey: userKeys.all });

// Invalidate only lists (not details):
queryClient.invalidateQueries({ queryKey: userKeys.lists() });

// Invalidate one user's detail:
queryClient.invalidateQueries({ queryKey: userKeys.detail('123') });
```

### Key Hierarchy Rules

```
['users']                              → All user-related data
['users', 'list']                      → All list views
['users', 'list', { page: 1 }]        → Specific list page
['users', 'detail']                    → All detail views
['users', 'detail', '123']            → Specific user
['users', 'detail', '123', 'posts']   → Specific user's posts

Invalidating ['users'] invalidates ALL of the above.
Invalidating ['users', 'list'] only invalidates list views.
```

---

## Deduplication

```
TanStack Query automatically deduplicates identical requests.

If 5 components mount simultaneously and all use:
  useQuery({ queryKey: ['users'], queryFn: fetchUsers })

Only ONE network request is made.
All 5 components share the same data.

This is automatic — you don't need to do anything!
```

### When Deduplication Happens

```typescript
// Same queryKey = same request = deduplication
// Component A
useQuery({ queryKey: ['users'], queryFn: fetchUsers });

// Component B (mounted at same time)
useQuery({ queryKey: ['users'], queryFn: fetchUsers });

// Result: ONE fetch, TWO subscribers

// Different queryKey = separate requests
useQuery({ queryKey: ['users', { role: 'admin' }], queryFn: fetchAdmins });
useQuery({ queryKey: ['users', { role: 'user' }], queryFn: fetchUsers });
// Result: TWO separate fetches
```

---

## Caching Strategies

### Per-Query Configuration

```typescript
// Static reference data (rarely changes)
useQuery({
  queryKey: ['countries'],
  queryFn: fetchCountries,
  staleTime: Infinity,           // Never consider stale
  gcTime: 1000 * 60 * 60 * 24, // Keep in cache for 24 hours
});

// User profile (changes occasionally)
useQuery({
  queryKey: ['users', 'me'],
  queryFn: fetchMyProfile,
  staleTime: 1000 * 60 * 5,    // Fresh for 5 minutes
  gcTime: 1000 * 60 * 30,      // Cache for 30 minutes
});

// Real-time data (needs to be fresh)
useQuery({
  queryKey: ['notifications'],
  queryFn: fetchNotifications,
  staleTime: 0,                 // Always stale
  refetchInterval: 30000,       // Poll every 30 seconds
});

// Search results (short-lived)
useQuery({
  queryKey: ['search', query],
  queryFn: () => search(query),
  staleTime: 1000 * 30,        // Fresh for 30 seconds
  gcTime: 1000 * 60 * 5,       // Cache for 5 minutes
});
```

### Global Defaults

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,   // 2 minutes default
      gcTime: 1000 * 60 * 10,     // 10 minutes default
      retry: 2,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  },
});
```

---

## Structural Sharing

```
TanStack Query uses "structural sharing" to keep stable references.

When data is refetched, it compares old and new data:
- If a nested object hasn't changed → keeps OLD reference
- If a nested object changed → creates NEW reference

Why this matters:
- Components using selectors only re-render when selected data changes
- React.memo and useMemo work correctly
- Prevents unnecessary re-renders
```

```typescript
// Example: user list refetched, only user #3 changed
const oldData = [
  { id: 1, name: 'Alice' },   // unchanged
  { id: 2, name: 'Bob' },     // unchanged
  { id: 3, name: 'Charlie' }, // changed to 'Charles'
];

// After refetch:
const newData = [
  oldData[0],                   // SAME reference (no re-render)
  oldData[1],                   // SAME reference (no re-render)
  { id: 3, name: 'Charles' },  // NEW reference (re-render)
];
```

---

## Memory Management

### Garbage Collection

```typescript
// gcTime controls when inactive query data is removed
// "Inactive" = no component is subscribed to this query

// Timeline:
// 1. Component mounts → useQuery subscribes → data fetched
// 2. Component unmounts → query becomes inactive
// 3. Timer starts (gcTime countdown)
// 4. If no component re-subscribes within gcTime → data removed

// For large datasets, use shorter gcTime
useQuery({
  queryKey: ['large-dataset'],
  queryFn: fetchLargeDataset,
  gcTime: 1000 * 60, // Remove after 1 minute inactive
});

// For frequently revisited data, use longer gcTime
useQuery({
  queryKey: ['user-preferences'],
  queryFn: fetchPreferences,
  gcTime: 1000 * 60 * 60, // Keep for 1 hour
});
```

### Clearing Cache Manually

```typescript
// Remove specific queries
queryClient.removeQueries({ queryKey: ['large-dataset'] });

// Clear entire cache (e.g., on logout)
queryClient.clear();

// Reset specific queries (clear + refetch if active)
queryClient.resetQueries({ queryKey: ['users'] });
```

---

## Prefetching Patterns

### Route-Based Prefetching

```typescript
// Prefetch data before user navigates
function UserListItem({ user }) {
  const queryClient = useQueryClient();

  return (
    <Link
      to={`/users/${user.id}`}
      onMouseEnter={() => {
        queryClient.prefetchQuery({
          queryKey: userKeys.detail(user.id),
          queryFn: () => usersApi.getById(user.id),
          staleTime: 1000 * 60 * 5, // Don't prefetch if fresh
        });
      }}
    >
      {user.name}
    </Link>
  );
}
```

### Pagination Prefetching

```typescript
function PaginatedList() {
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ['items', page],
    queryFn: () => fetchItems(page),
  });

  // Prefetch next page
  useEffect(() => {
    if (data?.meta.totalPages > page) {
      queryClient.prefetchQuery({
        queryKey: ['items', page + 1],
        queryFn: () => fetchItems(page + 1),
      });
    }
  }, [data, page, queryClient]);
}
```

---

## DevTools Debugging

```typescript
// Always include DevTools in development
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router />
      {import.meta.env.DEV && (
        <ReactQueryDevtools
          initialIsOpen={false}
          buttonPosition="bottom-right"
        />
      )}
    </QueryClientProvider>
  );
}

// DevTools shows:
// - All queries and their status (fresh, stale, fetching, inactive)
// - Cache data for each query
// - Query timing (when fetched, stale time remaining)
// - Number of observers (subscribers)
// - Actions: refetch, invalidate, reset, remove
```

---

## Common Patterns & Best Practices

### Pattern 1: Select for Derived Data

```typescript
// Don't create separate queries for derived data
// Use select to transform from existing cache

// ✅ Good: derive from existing query
function useActiveUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: fetchUsers,
    select: (users) => users.filter(u => u.isActive),
  });
}

function useUserCount() {
  return useQuery({
    queryKey: ['users'],
    queryFn: fetchUsers,
    select: (users) => users.length,
  });
}
// Both share the SAME cache entry!
```

### Pattern 2: Polling for Real-Time Data

```typescript
useQuery({
  queryKey: ['notifications'],
  queryFn: fetchNotifications,
  refetchInterval: 30000,           // Poll every 30s
  refetchIntervalInBackground: false, // Don't poll when tab is hidden
});
```

---

## Common Pitfalls

### Pitfall 1: Over-fetching

```typescript
// ❌ staleTime: 0 (default) means every mount triggers refetch
useQuery({ queryKey: ['config'], queryFn: fetchConfig });

// ✅ Set appropriate staleTime
useQuery({ queryKey: ['config'], queryFn: fetchConfig, staleTime: Infinity });
```

### Pitfall 2: Memory Leaks from Infinite Queries

```typescript
// ❌ Infinite scroll accumulates pages in memory
useInfiniteQuery({
  queryKey: ['feed'],
  queryFn: fetchFeedPage,
  // Could accumulate 100+ pages in memory!
});

// ✅ Limit max pages in memory
useInfiniteQuery({
  queryKey: ['feed'],
  queryFn: fetchFeedPage,
  maxPages: 10, // Only keep last 10 pages in cache
});
```

---

## Resources

- **Query Key Best Practices:** https://tkdodo.eu/blog/effective-react-query-keys
- **Performance Optimization:** https://tkdodo.eu/blog/react-query-render-optimizations
- **Caching Strategies:** https://tanstack.com/query/latest/docs/framework/react/guides/caching
- **Structural Sharing:** https://tanstack.com/query/latest/docs/framework/react/guides/render-optimizations

---

**Next:** [Part 8.4: TanStack Query Testing](./08-tanstack-query-testing.md)
