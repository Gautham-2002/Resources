# Part 12.1: Rendering Strategies Overview

## What You'll Learn

- Client-Side Rendering (CSR)
- Server-Side Rendering (SSR)
- Static Site Generation (SSG)
- Incremental Static Regeneration (ISR)
- Streaming SSR
- React Server Components (RSC)
- When to use which strategy

---

## Table of Contents

1. [Rendering Taxonomy](#rendering-taxonomy)
2. [CSR - Client-Side Rendering](#csr---client-side-rendering)
3. [SSR - Server-Side Rendering](#ssr---server-side-rendering)
4. [SSG - Static Site Generation](#ssg---static-site-generation)
5. [ISR - Incremental Static Regeneration](#isr---incremental-static-regeneration)
6. [Streaming SSR](#streaming-ssr)
7. [React Server Components](#react-server-components)
8. [Decision Matrix](#decision-matrix)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Resources](#resources)

---

## Rendering Taxonomy

```
┌──────────────────────────────────────────────────┐
│              Rendering Strategies                 │
├──────────────────────────────────────────────────┤
│                                                  │
│  Build Time ←─────────────────→ Request Time     │
│                                                  │
│  SSG        ISR        SSR       CSR             │
│  (Static)   (Hybrid)   (Server)  (Client)        │
│                                                  │
│  Fastest    Fast+Fresh  Fresh     Interactive     │
│  TTFB       TTFB        TTFB     (slow TTFB)     │
│                                                  │
│  Best for:  Best for:   Best for: Best for:      │
│  Blog,docs  E-commerce  Dynamic   SPAs,          │
│  Marketing  News feeds  Dashboard Dashboards     │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## CSR - Client-Side Rendering

```
How it works:
1. Server sends empty HTML + JS bundle
2. Browser downloads and parses JavaScript
3. React renders the UI in the browser
4. Data fetched via API calls

Timeline:
[Request] → [Empty HTML] → [Download JS] → [Parse JS] → [Render] → [Fetch Data] → [Display]
                                                          ↑ First paint (blank page until here)

Pros:
✅ Simple deployment (static hosting)
✅ Rich interactivity
✅ No server needed
✅ Good for authenticated/private content

Cons:
❌ Slow initial load (large JS bundle)
❌ Poor SEO (search engines see empty page)
❌ Flash of blank content
❌ Waterfall: load JS → fetch data → render
```

### CSR with Vite (Our Stack)

```typescript
// This is what we use! Vite + React = CSR by default
// main.tsx
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// All rendering happens in the browser
// API data fetched with TanStack Query
```

---

## SSR - Server-Side Rendering

```
How it works:
1. Server runs React, generates full HTML
2. HTML sent to browser (user sees content immediately)
3. JavaScript loads and "hydrates" (makes interactive)

Timeline:
[Request] → [Server Renders] → [Full HTML] → [Download JS] → [Hydrate] → [Interactive]
                                 ↑ First paint (content visible!)

Pros:
✅ Fast first contentful paint (FCP)
✅ SEO friendly (full HTML for crawlers)
✅ Social media previews work
✅ No blank page flash

Cons:
❌ Server required (Node.js)
❌ Higher TTFB (server must render)
❌ Hydration cost (page interactive later)
❌ More complex deployment
❌ Server load scales with traffic
```

---

## SSG - Static Site Generation

```
How it works:
1. At BUILD time, React renders all pages to HTML
2. HTML files served from CDN
3. No server needed at runtime

Timeline:
[Build] → [Generate HTML files] → [Deploy to CDN]
[Request] → [CDN serves HTML] → [Download JS] → [Hydrate]
              ↑ Fastest possible TTFB

Pros:
✅ Fastest TTFB (CDN-served)
✅ SEO perfect
✅ Cheapest hosting (static files)
✅ Most resilient (no server to crash)

Cons:
❌ Build time grows with pages
❌ Stale data (until rebuild)
❌ Not suitable for dynamic/personalized content
❌ Need rebuild for content changes
```

---

## ISR - Incremental Static Regeneration

```
How it works:
1. Pages pre-rendered at build (like SSG)
2. After a "revalidation" period, page is regenerated on next request
3. Users always get static HTML, but it stays fresh

Timeline:
[Build] → [Static HTML]
[Request within revalidate period] → [Serve cached HTML]
[Request after revalidate period] → [Serve stale HTML] + [Regenerate in background]
[Next request] → [Serve fresh HTML]

Pros:
✅ Fast TTFB (cached)
✅ Content stays fresh
✅ No full rebuild needed
✅ Scales to millions of pages

Cons:
❌ Next.js specific (mostly)
❌ Stale data for first request after expiry
❌ Complex cache invalidation
```

---

## Streaming SSR

```
How it works:
1. Server starts sending HTML immediately
2. As parts become ready, they stream to the browser
3. Browser renders progressively
4. React Suspense boundaries define streaming chunks

Timeline:
[Request] → [Stream shell HTML] → [Stream content chunks] → [Hydrate progressively]
              ↑ First paint               ↑ Content appears incrementally

Pros:
✅ Fast TTFB (streaming starts immediately)
✅ Progressive rendering (no waiting for slowest query)
✅ Better UX than traditional SSR
✅ Works with React Suspense

Cons:
❌ More complex infrastructure
❌ Requires streaming-capable server
```

---

## React Server Components

```
RSC is a NEW paradigm (React 18+):
- Components run ONLY on the server
- Zero JavaScript shipped for server components
- Can directly access databases, file system
- Client components marked with 'use client'

Server Component (default):
- Runs on server
- No useState, useEffect, event handlers
- Can be async
- Zero bundle size impact

Client Component ('use client'):
- Runs in browser
- Has interactivity (state, effects, handlers)
- Same as traditional React components
```

```typescript
// Server Component (no 'use client' directive)
async function UserList() {
  const users = await db.users.findMany(); // Direct DB access!
  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}

// Client Component
'use client';
function SearchInput() {
  const [query, setQuery] = useState('');
  return <input value={query} onChange={e => setQuery(e.target.value)} />;
}
```

---

## Decision Matrix

| Strategy | SEO | TTFB | Interactivity | Dynamic Data | Best For |
|----------|-----|------|---------------|-------------|----------|
| CSR | ❌ Poor | ❌ Slow | ✅ Full | ✅ Real-time | Dashboards, SPAs |
| SSR | ✅ Great | ⚠️ Depends | ✅ Full | ✅ Fresh | E-commerce, social |
| SSG | ✅ Great | ✅ Fastest | ✅ Full | ❌ Stale | Blogs, docs, marketing |
| ISR | ✅ Great | ✅ Fast | ✅ Full | ⚠️ Eventually fresh | News, product pages |
| Streaming | ✅ Great | ✅ Fast | ✅ Full | ✅ Fresh | Complex pages |
| RSC | ✅ Great | ✅ Fast | Partial | ✅ Fresh | Full-stack apps |

### Our Stack Decision

```
For our template project (Vite + React SPA):
→ CSR (Client-Side Rendering)

Why?
1. Dashboard/admin panel = authenticated (no SEO needed)
2. Vite is CSR by default
3. Simplest deployment (static hosting)
4. TanStack Query handles data fetching excellently
5. No server infrastructure needed

When would we switch?
→ Need SEO? Consider Next.js (SSR/SSG)
→ Need both? Next.js with RSC
→ Marketing pages? SSG with Astro
```

---

## Common Patterns & Best Practices

### Pattern 1: Hybrid Approach

```
Many production apps use multiple strategies:
- Marketing pages → SSG
- Product pages → ISR
- Dashboard → CSR
- Search results → SSR

Frameworks like Next.js support per-page rendering strategies.
```

### Pattern 2: SEO for SPAs

```typescript
// If you MUST have SEO with CSR:
// 1. Use react-helmet for meta tags
// 2. Pre-render critical pages at build time
// 3. Use a service like Prerender.io
// 4. Generate a sitemap.xml
```

---

## Resources

- **React Docs - Server Components:** https://react.dev/reference/rsc/server-components
- **Patterns.dev - Rendering Patterns:** https://www.patterns.dev/react/rendering-patterns
- **Next.js Rendering:** https://nextjs.org/docs/app/building-your-application/rendering
- **Web.dev Core Web Vitals:** https://web.dev/vitals/

---

**Next:** [Part 12.2: CSR Deep Dive](./12-csr-deep-dive.md)
