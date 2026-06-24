# Part 8.1: TanStack Query Fundamentals

## What You'll Learn

- Why server state is different from client state
- QueryClient setup and configuration
- useQuery for data fetching
- useMutation for data mutations
- Cache management and stale time
- Background refetching behavior
- Loading, error, and success states

---

## Table of Contents

1. [Server State vs Client State](#server-state-vs-client-state)
2. [Setup & Configuration](#setup--configuration)
3. [useQuery Hook](#usequery-hook)
4. [Query Keys](#query-keys)
5. [useMutation Hook](#usemutation-hook)
6. [Query Invalidation](#query-invalidation)
7. [Stale Time & GC Time](#stale-time--gc-time)
8. [Loading & Error States](#loading--error-states)
9. [Enabled & Dependent Queries](#enabled--dependent-queries)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Resources](#resources)

---

## Server State vs Client State

### The Problem

```typescript
// Client state (UI state): theme, sidebar open, form values
// → Controlled by the user, synchronous, deterministic

// Server state (remote data): user list, product catalog
// → Controlled by the server, asynchronous, shared between users

// Managing server state manually is painful:
function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRefetching, setIsRefetching] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetch('/api/users')
      .then(res => res.json())
      .then(data => {
        if (!cancelled) setUsers(data);
      })
      .catch(err => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  // Problems:
  // - No caching (refetches every mount)
  // - No deduplication (multiple components = multiple requests)
  // - No background refetching
  // - No optimistic updates
  // - Race conditions
  // - Memory leaks
  // - Manual loading/error state
}
```

### TanStack Query Solution

```typescript
import { useQuery } from '@tanstack/react-query';

function UsersPage() {
  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => fetch('/api/users').then(res => res.json()),
  });

  // ✅ Automatic caching
  // ✅ Deduplication (one request, multiple subscribers)
  // ✅ Background refetching
  // ✅ Automatic retry on failure
  // ✅ Window focus refetching
  // ✅ Garbage collection
  // ✅ DevTools
}
```

---

## Setup & Configuration

### Installation

```bash
pnpm add @tanstack/react-query
pnpm add -D @tanstack/react-query-devtools
```

### Provider Setup

```typescript
// main.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,       // 1 minute (data considered fresh)
      gcTime: 1000 * 60 * 5,      // 5 minutes (cache garbage collection)
      retry: 3,                    // Retry failed requests 3 times
      refetchOnWindowFocus: true,  // Refetch when tab regains focus
      refetchOnReconnect: true,    // Refetch when internet reconnects
    },
    mutations: {
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router />
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}
```

---

## useQuery Hook

### Basic Usage

```typescript
import { useQuery } from '@tanstack/react-query';
import { usersApi } from '@/services/api';

function UsersList() {
  const {
    data,          // The fetched data
    isLoading,     // True on first load (no cached data)
    isFetching,    // True whenever a request is in-flight
    isError,       // True if query errored
    error,         // The error object
    isSuccess,     // True if query succeeded
    refetch,       // Manual refetch function
    isRefetching,  // True when refetching (has cached data + fetching)
    isPending,     // True when no cached data and loading
    isStale,       // True when data is stale
  } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.list(),
  });

  if (isLoading) return <Skeleton />;
  if (isError) return <ErrorDisplay error={error} />;

  return (
    <ul>
      {data?.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}
```

### With Parameters

```typescript
function UserProfile({ userId }: { userId: string }) {
  const { data: user, isLoading } = useQuery({
    queryKey: ['users', userId],          // Unique per userId
    queryFn: () => usersApi.getById(userId),
    enabled: !!userId,                    // Don't fetch if no userId
  });

  if (isLoading) return <ProfileSkeleton />;
  return <div>{user?.name}</div>;
}
```

---

## Query Keys

### Why Keys Matter

```typescript
// Query keys uniquely identify cached data
// Same key = same cache entry

// ✅ Good: Hierarchical keys
['users']                          // All users
['users', { page: 1, limit: 10 }] // Paginated users
['users', '123']                   // Single user
['users', '123', 'posts']          // User's posts

// The key is serialized — objects are compared by content
['users', { page: 1 }] === ['users', { page: 1 }] // Same cache!
['users', { page: 1 }] !== ['users', { page: 2 }] // Different cache

// Query key factory pattern (recommended)
export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (filters: UserFilters) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};

// Usage
useQuery({ queryKey: userKeys.detail(userId), queryFn: ... });
```

---

## useMutation Hook

### Basic Mutation

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';

function CreateUserForm() {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (newUser: CreateUserDTO) => usersApi.create(newUser),

    onSuccess: (createdUser) => {
      // Invalidate and refetch users list
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success(`User ${createdUser.name} created!`);
    },

    onError: (error) => {
      toast.error('Failed to create user');
    },
  });

  const handleSubmit = (data: CreateUserDTO) => {
    createMutation.mutate(data);
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* form fields */}
      <button disabled={createMutation.isPending}>
        {createMutation.isPending ? 'Creating...' : 'Create User'}
      </button>
    </form>
  );
}
```

### Delete with Optimistic Update

```typescript
function UserItem({ user }: { user: User }) {
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: (id: string) => usersApi.delete(id),

    onMutate: async (deletedId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['users'] });

      // Snapshot previous value
      const previousUsers = queryClient.getQueryData<User[]>(['users']);

      // Optimistically remove from cache
      queryClient.setQueryData<User[]>(['users'], (old) =>
        old?.filter(u => u.id !== deletedId)
      );

      return { previousUsers };
    },

    onError: (err, deletedId, context) => {
      // Rollback on error
      queryClient.setQueryData(['users'], context?.previousUsers);
      toast.error('Failed to delete user');
    },

    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  return (
    <div className="flex items-center justify-between">
      <span>{user.name}</span>
      <button
        onClick={() => deleteMutation.mutate(user.id)}
        disabled={deleteMutation.isPending}
        className="text-red-500 hover:text-red-700"
      >
        {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
      </button>
    </div>
  );
}
```

---

## Query Invalidation

```typescript
const queryClient = useQueryClient();

// Invalidate exact query
queryClient.invalidateQueries({ queryKey: ['users', '123'] });

// Invalidate all queries starting with 'users'
queryClient.invalidateQueries({ queryKey: ['users'] });

// Invalidate everything
queryClient.invalidateQueries();

// Remove from cache entirely
queryClient.removeQueries({ queryKey: ['users', '123'] });

// Set cache data directly
queryClient.setQueryData(['users', '123'], updatedUser);
```

---

## Stale Time & GC Time

```typescript
// staleTime: How long data is considered "fresh"
// - Fresh data is NEVER refetched automatically
// - After staleTime, data becomes "stale"
// - Stale data is refetched in background on:
//   - New component mount
//   - Window focus
//   - Network reconnect
//   - Manual invalidation

// gcTime (garbage collection time):
// - How long INACTIVE data stays in cache
// - Inactive = no components are subscribed
// - After gcTime, data is garbage collected

useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers,
  staleTime: 1000 * 60 * 5,     // 5 minutes: data is fresh for 5 min
  gcTime: 1000 * 60 * 30,       // 30 minutes: keep in cache for 30 min
});

// Common configurations:
// Real-time data:    staleTime: 0 (always refetch)
// Semi-static data:  staleTime: 5 * 60 * 1000 (5 min)
// Static data:       staleTime: Infinity (never stale)
```

---

## Loading & Error States

### Comprehensive State Handling

```typescript
function DataDisplay() {
  const { data, isLoading, isFetching, isError, error } = useQuery({
    queryKey: ['data'],
    queryFn: fetchData,
  });

  // First load — no cached data
  if (isLoading) {
    return <Skeleton />;
  }

  // Error with no cached data
  if (isError) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500">Error: {error.message}</p>
        <button onClick={() => refetch()}>Retry</button>
      </div>
    );
  }

  return (
    <div>
      {/* Background refetch indicator */}
      {isFetching && (
        <div className="fixed top-0 left-0 right-0 h-1 bg-blue-500 animate-pulse" />
      )}
      {/* Render data */}
      <DataList items={data} />
    </div>
  );
}
```

---

## Enabled & Dependent Queries

```typescript
// Dependent: fetch user's posts only after user is loaded
function UserPosts({ userId }: { userId: string }) {
  const userQuery = useQuery({
    queryKey: ['users', userId],
    queryFn: () => usersApi.getById(userId),
  });

  const postsQuery = useQuery({
    queryKey: ['users', userId, 'posts'],
    queryFn: () => postsApi.getByUser(userId),
    enabled: !!userQuery.data, // Only fetch when user is loaded
  });

  return (
    <div>
      <h2>{userQuery.data?.name}'s Posts</h2>
      {postsQuery.isLoading && <Skeleton />}
      {postsQuery.data?.map(post => (
        <PostCard key={post.id} post={post} />
      ))}
    </div>
  );
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Custom Query Hook

```typescript
// hooks/useUsers.ts
export function useUsers(filters?: UserFilters) {
  return useQuery({
    queryKey: userKeys.list(filters ?? {}),
    queryFn: () => usersApi.list(filters),
    staleTime: 1000 * 60 * 2,
  });
}

export function useUser(id: string) {
  return useQuery({
    queryKey: userKeys.detail(id),
    queryFn: () => usersApi.getById(id),
    enabled: !!id,
  });
}

// Usage — clean and reusable
function UsersList() {
  const { data: users, isLoading } = useUsers({ role: 'admin' });
}
```

### Pattern 2: Placeholder Data

```typescript
useQuery({
  queryKey: ['users', userId],
  queryFn: () => usersApi.getById(userId),
  placeholderData: (previousData) => previousData, // Keep previous while loading
  // OR
  placeholderData: { id: userId, name: 'Loading...', email: '' }, // Static placeholder
});
```

---

## Common Pitfalls

### Pitfall 1: Unstable Query Functions

```typescript
// ❌ Creates new function every render (triggers refetch!)
useQuery({
  queryKey: ['users'],
  queryFn: () => fetch(`/api/users?role=${role}`).then(r => r.json()),
});

// ✅ Include variables in queryKey, not just queryFn
useQuery({
  queryKey: ['users', { role }],
  queryFn: () => usersApi.list({ role }),
});
```

### Pitfall 2: Forgetting staleTime

```typescript
// ❌ Default staleTime is 0 — refetches on every mount!
useQuery({ queryKey: ['config'], queryFn: fetchConfig });

// ✅ Set appropriate staleTime
useQuery({ queryKey: ['config'], queryFn: fetchConfig, staleTime: Infinity });
```

### Pitfall 3: Not Invalidating After Mutations

```typescript
// ❌ Cache shows stale data after mutation
mutation.mutate(data);

// ✅ Always invalidate related queries
mutation.mutate(data, {
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
});
```

---

## Resources

- **TanStack Query Documentation:** https://tanstack.com/query/latest
- **TanStack Query DevTools:** https://tanstack.com/query/latest/docs/framework/react/devtools
- **Practical React Query (Blog):** https://tkdodo.eu/blog/practical-react-query
- **Query Keys Best Practices:** https://tkdodo.eu/blog/effective-react-query-keys

---

**Next:** [Part 8.2: TanStack Query Advanced Patterns](./08-tanstack-query-advanced.md)
