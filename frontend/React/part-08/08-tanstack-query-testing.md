# Part 8.4: TanStack Query Testing

## What You'll Learn

- Setting up TanStack Query for testing
- Mocking queries in unit tests
- Testing mutations
- Testing loading, error, and success states
- Integration testing with MSW

---

## Table of Contents

1. [Test Setup](#test-setup)
2. [Testing useQuery](#testing-usequery)
3. [Testing useMutation](#testing-usemutation)
4. [Testing with MSW](#testing-with-msw)
5. [Testing Custom Hooks](#testing-custom-hooks)
6. [Common Patterns & Best Practices](#common-patterns--best-practices)
7. [Resources](#resources)

---

## Test Setup

### Query Client for Tests

```typescript
// test/utils.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions } from '@testing-library/react';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,        // Don't retry in tests
        gcTime: Infinity,    // Don't garbage collect
        staleTime: Infinity, // Don't refetch
      },
    },
  });
}

export function createWrapper() {
  const queryClient = createTestQueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

export function renderWithQuery(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  const queryClient = createTestQueryClient();
  return {
    ...render(ui, {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      ),
      ...options,
    }),
    queryClient,
  };
}
```

---

## Testing useQuery

### Testing a Component with useQuery

```typescript
// UserProfile.tsx
function UserProfile({ userId }: { userId: string }) {
  const { data: user, isLoading, error } = useQuery({
    queryKey: ['users', userId],
    queryFn: () => usersApi.getById(userId),
  });

  if (isLoading) return <div data-testid="loading">Loading...</div>;
  if (error) return <div data-testid="error">Error: {error.message}</div>;

  return (
    <div data-testid="user-profile">
      <h1>{user.name}</h1>
      <p>{user.email}</p>
    </div>
  );
}

// __tests__/UserProfile.test.tsx
import { screen, waitFor } from '@testing-library/react';
import { renderWithQuery } from '@/test/utils';
import { vi } from 'vitest';

// Mock the API module
vi.mock('@/services/api/endpoints/users', () => ({
  usersApi: {
    getById: vi.fn(),
  },
}));

import { usersApi } from '@/services/api/endpoints/users';

describe('UserProfile', () => {
  it('shows loading state initially', () => {
    (usersApi.getById as any).mockReturnValue(new Promise(() => {})); // Never resolves

    renderWithQuery(<UserProfile userId="1" />);
    expect(screen.getByTestId('loading')).toBeInTheDocument();
  });

  it('displays user data on success', async () => {
    (usersApi.getById as any).mockResolvedValue({
      id: '1',
      name: 'John Doe',
      email: 'john@example.com',
    });

    renderWithQuery(<UserProfile userId="1" />);

    await waitFor(() => {
      expect(screen.getByTestId('user-profile')).toBeInTheDocument();
    });

    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
  });

  it('shows error state on failure', async () => {
    (usersApi.getById as any).mockRejectedValue(new Error('Not found'));

    renderWithQuery(<UserProfile userId="999" />);

    await waitFor(() => {
      expect(screen.getByTestId('error')).toBeInTheDocument();
    });

    expect(screen.getByText(/Not found/)).toBeInTheDocument();
  });
});
```

---

## Testing useMutation

```typescript
// __tests__/CreateUserForm.test.tsx
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithQuery } from '@/test/utils';

describe('CreateUserForm', () => {
  it('submits form and invalidates queries', async () => {
    const user = userEvent.setup();

    (usersApi.create as any).mockResolvedValue({
      id: '1',
      name: 'Jane',
      email: 'jane@example.com',
    });

    const { queryClient } = renderWithQuery(<CreateUserForm />);
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    await user.type(screen.getByLabelText('Name'), 'Jane');
    await user.type(screen.getByLabelText('Email'), 'jane@example.com');
    await user.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(usersApi.create).toHaveBeenCalledWith({
        name: 'Jane',
        email: 'jane@example.com',
      });
    });

    // Verify query invalidation
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['users'],
    });
  });
});
```

---

## Testing with MSW

```typescript
// mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/users', () => {
    return HttpResponse.json([
      { id: '1', name: 'Alice', email: 'alice@example.com' },
      { id: '2', name: 'Bob', email: 'bob@example.com' },
    ]);
  }),

  http.get('/api/users/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'Alice',
      email: 'alice@example.com',
    });
  }),

  http.post('/api/users', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ id: '3', ...body }, { status: 201 });
  }),
];

// mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);

// vitest.setup.ts
import { server } from './mocks/server';

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Test using MSW (no mocking needed!)
describe('UsersList with MSW', () => {
  it('fetches and displays users', async () => {
    renderWithQuery(<UsersList />);

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
    });
  });

  it('handles server error', async () => {
    // Override handler for this test
    server.use(
      http.get('/api/users', () => {
        return HttpResponse.json({ message: 'Server error' }, { status: 500 });
      })
    );

    renderWithQuery(<UsersList />);

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
```

---

## Testing Custom Hooks

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { createWrapper } from '@/test/utils';

describe('useUsers hook', () => {
  it('returns users data', async () => {
    (usersApi.list as any).mockResolvedValue([
      { id: '1', name: 'Alice' },
    ]);

    const { result } = renderHook(() => useUsers(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(1);
    expect(result.current.data[0].name).toBe('Alice');
  });
});
```

---

## Common Patterns & Best Practices

### Pattern 1: Always Create Fresh QueryClient per Test

```typescript
// ❌ Shared client leaks state between tests
const queryClient = new QueryClient();

// ✅ Fresh client per test
function createTestQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}
```

### Pattern 2: Disable Retries in Tests

```typescript
// Tests should fail fast, not retry
new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});
```

---

## Resources

- **TanStack Query Testing Guide:** https://tanstack.com/query/latest/docs/framework/react/guides/testing
- **MSW Documentation:** https://mswjs.io/docs/
- **React Testing Library:** https://testing-library.com/docs/react-testing-library/intro/
- **Testing Hooks:** https://react-hooks-testing-library.com/

---

**Next:** [Part 9.1: TanStack Router Fundamentals](../part-09/09-tanstack-router-fundamentals.md)
