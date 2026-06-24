# Part 12.3: Server-Side Rendering Deep Dive

## What You'll Learn

- SSR with Next.js App Router
- Server Components vs Client Components
- Data fetching patterns in SSR
- Streaming and Suspense on the server
- Hydration and its costs
- When SSR adds value vs complexity

---

## Table of Contents

1. [SSR Fundamentals](#ssr-fundamentals)
2. [Next.js App Router](#nextjs-app-router)
3. [Server vs Client Components](#server-vs-client-components)
4. [Data Fetching in SSR](#data-fetching-in-ssr)
5. [Streaming SSR](#streaming-ssr)
6. [Hydration](#hydration)
7. [SEO with SSR](#seo-with-ssr)
8. [SSR vs CSR Trade-offs](#ssr-vs-csr-trade-offs)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Resources](#resources)

---

## SSR Fundamentals

### How SSR Works

```
Traditional CSR:
  Browser → Empty HTML → Download JS → Execute JS → Render UI → Fetch Data → Display

SSR:
  Browser → Server renders full HTML → Send HTML → Display content immediately
                                       ↓
                                Download JS → Hydrate → Interactive

Key insight: User sees content BEFORE JavaScript loads.
```

---

## Next.js App Router

### Basic SSR Page

```typescript
// app/users/page.tsx (Server Component by default)
async function UsersPage() {
  // This runs on the SERVER
  const users = await fetch('https://api.example.com/users').then(r => r.json());

  return (
    <div>
      <h1>Users</h1>
      <ul>
        {users.map(user => (
          <li key={user.id}>{user.name}</li>
        ))}
      </ul>
    </div>
  );
}

export default UsersPage;
```

### Static vs Dynamic Rendering

```typescript
// Static (default): Rendered at build time
async function AboutPage() {
  return <div>About us</div>;
}

// Dynamic: Rendered on each request
export const dynamic = 'force-dynamic';

async function DashboardPage() {
  const data = await fetchDashboardData();
  return <Dashboard data={data} />;
}

// Revalidate: ISR - Static but refreshes every N seconds
export const revalidate = 60; // Regenerate every 60 seconds

async function ProductPage({ params }) {
  const product = await fetchProduct(params.id);
  return <ProductDisplay product={product} />;
}
```

---

## Server vs Client Components

### The Mental Model

```typescript
// SERVER COMPONENT (default in App Router)
// ✅ Can: access DB, file system, env vars, async/await
// ❌ Cannot: useState, useEffect, event handlers, browser APIs

// app/users/page.tsx
async function UsersPage() {
  const users = await db.users.findMany(); // Direct DB access!
  return <UserList users={users} />;
}

// CLIENT COMPONENT (opt-in with 'use client')
// ✅ Can: useState, useEffect, event handlers, browser APIs
// ❌ Cannot: direct DB access, file system

// components/SearchInput.tsx
'use client';
import { useState } from 'react';

function SearchInput({ onSearch }) {
  const [query, setQuery] = useState('');
  return (
    <input
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      onKeyDown={(e) => e.key === 'Enter' && onSearch(query)}
    />
  );
}
```

### Composition Pattern

```typescript
// Server Component wraps Client Component
// app/dashboard/page.tsx (Server)
async function DashboardPage() {
  const stats = await fetchStats(); // Server-side data fetch

  return (
    <div>
      <h1>Dashboard</h1>
      <StatsDisplay stats={stats} />        {/* Server component */}
      <InteractiveChart data={stats.chart} /> {/* Client component */}
      <RealtimeNotifications />               {/* Client component */}
    </div>
  );
}
```

---

## Data Fetching in SSR

### Server Component Data Fetching

```typescript
// Direct fetch in Server Components (Next.js extends fetch)
async function ProductPage({ params }: { params: { id: string } }) {
  const product = await fetch(`https://api.example.com/products/${params.id}`, {
    next: { revalidate: 3600 }, // Cache for 1 hour
  }).then(r => r.json());

  return <ProductDisplay product={product} />;
}
```

### Parallel Data Fetching

```typescript
async function DashboardPage() {
  // ❌ Sequential (slow): Each waits for the previous
  const users = await fetchUsers();
  const orders = await fetchOrders();
  const revenue = await fetchRevenue();

  // ✅ Parallel (fast): All fetch simultaneously
  const [users, orders, revenue] = await Promise.all([
    fetchUsers(),
    fetchOrders(),
    fetchRevenue(),
  ]);

  return <Dashboard users={users} orders={orders} revenue={revenue} />;
}
```

---

## Streaming SSR

```typescript
// With React Suspense, parts of the page stream progressively
import { Suspense } from 'react';

async function DashboardPage() {
  return (
    <div>
      {/* Header renders immediately */}
      <h1>Dashboard</h1>

      {/* Stats stream when ready */}
      <Suspense fallback={<StatsSkeleton />}>
        <StatsSection />
      </Suspense>

      {/* Chart streams independently */}
      <Suspense fallback={<ChartSkeleton />}>
        <SlowChart />
      </Suspense>

      {/* Table streams independently */}
      <Suspense fallback={<TableSkeleton />}>
        <RecentOrders />
      </Suspense>
    </div>
  );
}

// Each Suspense boundary is a streaming chunk
// The page progressively fills in as data arrives
```

---

## Hydration

### What Is Hydration?

```
Hydration is the process of making server-rendered HTML interactive.

1. Server sends fully rendered HTML (user sees content)
2. Browser downloads React JavaScript
3. React "hydrates": attaches event handlers to existing DOM
4. Page becomes interactive

The cost:
- User sees content immediately ✅
- But can't interact until hydration completes ❌
- Called "uncanny valley" — looks ready but isn't
```

### Selective Hydration

```typescript
// React 18+ can hydrate Suspense boundaries independently
<Suspense fallback={<Skeleton />}>
  <HeavyInteractiveComponent />
</Suspense>

// If user clicks on a Suspense boundary before it hydrates,
// React prioritizes hydrating THAT boundary first!
```

---

## SEO with SSR

```typescript
// app/products/[id]/page.tsx
import { type Metadata } from 'next';

// Dynamic metadata for SEO
export async function generateMetadata({ params }): Promise<Metadata> {
  const product = await fetchProduct(params.id);

  return {
    title: `${product.name} | My Store`,
    description: product.description,
    openGraph: {
      title: product.name,
      description: product.description,
      images: [product.image],
    },
    twitter: {
      card: 'summary_large_image',
      title: product.name,
      images: [product.image],
    },
  };
}
```

---

## SSR vs CSR Trade-offs

| Aspect | CSR (Vite + React) | SSR (Next.js) |
|--------|-------------------|---------------|
| Initial load | Slower (JS first) | Faster (HTML first) |
| SEO | Poor (without workarounds) | Excellent |
| Complexity | Simple | More complex |
| Hosting | Static (cheap) | Node.js server |
| Interactivity | Immediate after load | Delayed (hydration) |
| Data fetching | Client-side (TanStack Query) | Server + client |
| Best for | Authenticated apps, SPAs | Public-facing, SEO-critical |

---

## Common Patterns & Best Practices

### Pattern 1: Push Interactivity to Leaves

```typescript
// Server Component (most of the page)
async function ProductPage({ params }) {
  const product = await fetchProduct(params.id);

  return (
    <div>
      <h1>{product.name}</h1>           {/* Server: no JS */}
      <p>{product.description}</p>       {/* Server: no JS */}
      <img src={product.image} />        {/* Server: no JS */}
      <AddToCartButton product={product} /> {/* Client: needs JS */}
    </div>
  );
}
// Most of the page = zero JavaScript!
```

### Pattern 2: When to Choose SSR

```
Choose CSR (Vite) when:
- Building authenticated dashboards
- No SEO requirements
- Want simpler deployment
- Team is smaller

Choose SSR (Next.js) when:
- SEO is critical (e-commerce, blogs, marketing)
- Need social media previews
- Want fastest initial load
- Building public-facing pages
```

---

## Common Pitfalls

### Pitfall 1: Using SSR When CSR Suffices

```
❌ Building an admin dashboard with Next.js SSR
   → Nobody googles your admin panel
   → CSR with Vite is simpler and cheaper

✅ Using Next.js SSR for product pages
   → SEO drives traffic
   → Social sharing previews matter
```

### Pitfall 2: Hydration Mismatch

```typescript
// ❌ Server renders different HTML than client
function Timer() {
  return <p>Time: {new Date().toLocaleString()}</p>;
  // Server time ≠ client time → hydration mismatch!
}

// ✅ Use useEffect for client-only values
function Timer() {
  const [time, setTime] = useState<string | null>(null);

  useEffect(() => {
    setTime(new Date().toLocaleString());
  }, []);

  return <p>Time: {time ?? 'Loading...'}</p>;
}
```

---

## Resources

- **Next.js App Router:** https://nextjs.org/docs/app
- **React Server Components:** https://react.dev/reference/rsc/server-components
- **Streaming SSR:** https://react.dev/reference/react-dom/server/renderToPipeableStream
- **Hydration:** https://react.dev/reference/react-dom/client/hydrateRoot

---

**Next:** [Part 12.4: Hydration & Islands Architecture](./12-hydration-and-islands.md)
