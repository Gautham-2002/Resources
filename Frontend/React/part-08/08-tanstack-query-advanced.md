# Part 8.2: TanStack Query Advanced Patterns

## What You'll Learn

- Infinite queries for pagination and infinite scroll
- Optimistic updates with rollback
- Query invalidation strategies
- Dependent and parallel queries
- Prefetching for instant navigation
- Offline support patterns
- Retry and error recovery

---

## Table of Contents

1. [Pagination](#pagination)
2. [Infinite Scroll](#infinite-scroll)
3. [Optimistic Updates](#optimistic-updates)
4. [Prefetching](#prefetching)
5. [Parallel Queries](#parallel-queries)
6. [Dependent Queries](#dependent-queries)
7. [Query Invalidation Strategies](#query-invalidation-strategies)
8. [Offline Support](#offline-support)
9. [Select & Data Transformation](#select--data-transformation)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Resources](#resources)

---

## Pagination

### Traditional Pagination

```typescript
import { useQuery, keepPreviousData } from '@tanstack/react-query';

function PaginatedUsers() {
  const [page, setPage] = useState(1);
  const limit = 20;

  const { data, isLoading, isPlaceholderData } = useQuery({
    queryKey: ['users', 'list', { page, limit }],
    queryFn: () => usersApi.list({ page, limit }),
    placeholderData: keepPreviousData, // Keep showing old data while loading new page
  });

  return (
    <div>
      {/* Loading overlay for page transitions */}
      <div className={cn('transition-opacity', isPlaceholderData && 'opacity-50')}>
        {data?.data.map(user => (
          <UserRow key={user.id} user={user} />
        ))}
      </div>

      {/* Pagination controls */}
      <div className="flex items-center justify-between mt-4">
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
          className="px-4 py-2 border rounded disabled:opacity-50"
        >
          Previous
        </button>

        <span className="text-sm text-gray-500">
          Page {page} of {data?.meta?.totalPages ?? '...'}
        </span>

        <button
          onClick={() => setPage(p => p + 1)}
          disabled={!data?.meta || page >= data.meta.totalPages}
          className="px-4 py-2 border rounded disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
```

---

## Infinite Scroll

### useInfiniteQuery

```typescript
import { useInfiniteQuery } from '@tanstack/react-query';
import { useInView } from 'react-intersection-observer';

function InfiniteUsersList() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = useInfiniteQuery({
    queryKey: ['users', 'infinite'],
    queryFn: ({ pageParam }) =>
      usersApi.list({ page: pageParam, limit: 20 }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      if (lastPage.meta.page < lastPage.meta.totalPages) {
        return lastPage.meta.page + 1;
      }
      return undefined; // No more pages
    },
  });

  // Intersection observer for auto-loading
  const { ref: loadMoreRef, inView } = useInView();

  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (isLoading) return <UserListSkeleton />;

  return (
    <div>
      {data?.pages.map((page) =>
        page.data.map((user) => (
          <UserCard key={user.id} user={user} />
        ))
      )}

      {/* Load more trigger */}
      <div ref={loadMoreRef} className="py-4 text-center">
        {isFetchingNextPage && <Spinner />}
        {!hasNextPage && <p className="text-gray-400">No more users</p>}
      </div>
    </div>
  );
}
```

---

## Optimistic Updates

### Full Pattern with Rollback

```typescript
function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateUserDTO }) =>
      usersApi.update(id, data),

    onMutate: async ({ id, data }) => {
      // 1. Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['users', id] });
      await queryClient.cancelQueries({ queryKey: ['users', 'list'] });

      // 2. Snapshot current state
      const previousUser = queryClient.getQueryData<User>(['users', id]);
      const previousList = queryClient.getQueryData<User[]>(['users', 'list']);

      // 3. Optimistically update detail view
      queryClient.setQueryData<User>(['users', id], (old) =>
        old ? { ...old, ...data } : old
      );

      // 4. Optimistically update list view
      queryClient.setQueryData<User[]>(['users', 'list'], (old) =>
        old?.map(u => u.id === id ? { ...u, ...data } : u)
      );

      return { previousUser, previousList };
    },

    onError: (err, variables, context) => {
      // Rollback to snapshots
      if (context?.previousUser) {
        queryClient.setQueryData(['users', variables.id], context.previousUser);
      }
      if (context?.previousList) {
        queryClient.setQueryData(['users', 'list'], context.previousList);
      }
      toast.error('Failed to update user');
    },

    onSettled: (data, error, { id }) => {
      // Refetch to ensure server consistency
      queryClient.invalidateQueries({ queryKey: ['users', id] });
      queryClient.invalidateQueries({ queryKey: ['users', 'list'] });
    },
  });
}
```

---

## Prefetching

### Prefetch on Hover

```typescript
function UserListItem({ user }: { user: User }) {
  const queryClient = useQueryClient();

  const prefetchUser = () => {
    queryClient.prefetchQuery({
      queryKey: ['users', user.id],
      queryFn: () => usersApi.getById(user.id),
      staleTime: 1000 * 60 * 5, // Don't refetch if less than 5 min old
    });
  };

  return (
    <Link
      to={`/users/${user.id}`}
      onMouseEnter={prefetchUser}  // Prefetch on hover!
      onFocus={prefetchUser}       // Prefetch on focus (keyboard nav)
      className="block p-4 hover:bg-gray-50"
    >
      <span>{user.name}</span>
    </Link>
  );
}
```

### Prefetch in Route Loader

```typescript
// With TanStack Router
const userRoute = createRoute({
  path: '/users/$userId',
  loader: ({ params, context }) => {
    context.queryClient.ensureQueryData({
      queryKey: ['users', params.userId],
      queryFn: () => usersApi.getById(params.userId),
    });
  },
  component: UserPage,
});
```

---

## Parallel Queries

```typescript
// Multiple independent queries
function Dashboard() {
  const usersQuery = useQuery({ queryKey: ['users'], queryFn: fetchUsers });
  const productsQuery = useQuery({ queryKey: ['products'], queryFn: fetchProducts });
  const statsQuery = useQuery({ queryKey: ['stats'], queryFn: fetchStats });

  // They all fire in parallel!

  if (usersQuery.isLoading || productsQuery.isLoading || statsQuery.isLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="grid grid-cols-3 gap-6">
      <UsersWidget data={usersQuery.data} />
      <ProductsWidget data={productsQuery.data} />
      <StatsWidget data={statsQuery.data} />
    </div>
  );
}

// useQueries for dynamic parallel queries
function UserProfiles({ userIds }: { userIds: string[] }) {
  const userQueries = useQueries({
    queries: userIds.map(id => ({
      queryKey: ['users', id],
      queryFn: () => usersApi.getById(id),
    })),
  });

  const isLoading = userQueries.some(q => q.isLoading);
  const users = userQueries.map(q => q.data).filter(Boolean);

  return <UserGrid users={users} />;
}
```

---

## Dependent Queries

```typescript
// Second query depends on first query's result
function UserOrdersPage({ userId }: { userId: string }) {
  // First: fetch user
  const { data: user } = useQuery({
    queryKey: ['users', userId],
    queryFn: () => usersApi.getById(userId),
  });

  // Second: fetch user's organization (needs user.orgId)
  const { data: org } = useQuery({
    queryKey: ['orgs', user?.orgId],
    queryFn: () => orgsApi.getById(user!.orgId),
    enabled: !!user?.orgId, // Only fetch when orgId is available
  });

  // Third: fetch org's orders
  const { data: orders } = useQuery({
    queryKey: ['orgs', user?.orgId, 'orders'],
    queryFn: () => ordersApi.getByOrg(user!.orgId),
    enabled: !!org, // Only fetch when org is loaded
  });
}
```

---

## Query Invalidation Strategies

```typescript
const queryClient = useQueryClient();

// Strategy 1: Invalidate specific query
queryClient.invalidateQueries({ queryKey: ['users', '123'] });

// Strategy 2: Invalidate all matching queries
queryClient.invalidateQueries({ queryKey: ['users'] });
// Invalidates: ['users'], ['users', 'list'], ['users', '123']

// Strategy 3: Invalidate with predicate
queryClient.invalidateQueries({
  predicate: (query) => {
    return query.queryKey[0] === 'users' &&
           query.state.dataUpdatedAt < Date.now() - 60000;
  },
});

// Strategy 4: Invalidate + refetch active only
queryClient.invalidateQueries({
  queryKey: ['users'],
  refetchType: 'active', // Only refetch queries that are currently mounted
});

// Strategy 5: Reset query (clear cache + refetch)
queryClient.resetQueries({ queryKey: ['users'] });
```

---

## Offline Support

```typescript
import { onlineManager } from '@tanstack/react-query';

// Check online status
function OfflineBanner() {
  const isOnline = useSyncExternalStore(
    onlineManager.subscribe,
    () => onlineManager.isOnline(),
  );

  if (isOnline) return null;

  return (
    <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2 text-sm text-yellow-800">
      ⚠️ You are offline. Changes will sync when you reconnect.
    </div>
  );
}

// Mutations queue when offline
// When back online, they execute automatically
const mutation = useMutation({
  mutationFn: updateUser,
  // TanStack Query automatically pauses mutations when offline
  // and resumes when back online
});
```

---

## Select & Data Transformation

```typescript
// Transform data in the select option (doesn't affect cache)
function useUserNames() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.list(),
    select: (data) => data.map(user => ({
      id: user.id,
      label: `${user.firstName} ${user.lastName}`,
    })),
  });
}

// Memoized select (stable reference)
function useUserCount() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.list(),
    select: useCallback((data: User[]) => data.length, []),
  });
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Query Hook per Feature

```typescript
// hooks/queries/useUsers.ts
export function useUsers(filters?: UserFilters) {
  return useQuery({
    queryKey: userKeys.list(filters ?? {}),
    queryFn: () => usersApi.list(filters),
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: userKeys.all }),
  });
}
```

### Pattern 2: Suspense Mode

```typescript
// Enable Suspense for cleaner loading states
function UserProfile({ userId }) {
  const { data } = useSuspenseQuery({
    queryKey: ['users', userId],
    queryFn: () => usersApi.getById(userId),
  });

  // No need for isLoading check!
  return <div>{data.name}</div>;
}

// Wrap with Suspense boundary
<Suspense fallback={<ProfileSkeleton />}>
  <UserProfile userId="123" />
</Suspense>
```

---

## Common Pitfalls

### Pitfall 1: Not Including All Variables in Query Key

```typescript
// ❌ Filter changes but query key doesn't
useQuery({
  queryKey: ['users'],
  queryFn: () => usersApi.list({ status: filter }),
});

// ✅ Include filter in key
useQuery({
  queryKey: ['users', { status: filter }],
  queryFn: () => usersApi.list({ status: filter }),
});
```

### Pitfall 2: Creating Objects in queryKey

```typescript
// ❌ New object every render = infinite refetching
useQuery({
  queryKey: ['users', { filters: { ...filters } }],
  queryFn: fetchUsers,
});

// ✅ Stable reference
const stableFilters = useMemo(() => filters, [filters.search, filters.role]);
useQuery({
  queryKey: ['users', stableFilters],
  queryFn: fetchUsers,
});
```

---

## Resources

- **Practical React Query by TkDodo:** https://tkdodo.eu/blog/practical-react-query
- **TanStack Query Infinite Queries:** https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries
- **Optimistic Updates:** https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates
- **Offline Support:** https://tanstack.com/query/latest/docs/framework/react/guides/network-mode

---

**Next:** [Part 8.3: TanStack Query Performance](./08-tanstack-query-performance.md)
