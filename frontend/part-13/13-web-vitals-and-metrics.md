# Part 13.1: Web Vitals & Performance Metrics

## What You'll Learn

- Core Web Vitals (LCP, FID/INP, CLS)
- Additional performance metrics (TTFB, FCP, TTI)
- How to measure performance
- Lighthouse and Performance APIs
- Performance budgets
- Real user monitoring (RUM)

---

## Table of Contents

1. [Core Web Vitals](#core-web-vitals)
2. [LCP - Largest Contentful Paint](#lcp---largest-contentful-paint)
3. [INP - Interaction to Next Paint](#inp---interaction-to-next-paint)
4. [CLS - Cumulative Layout Shift](#cls---cumulative-layout-shift)
5. [Additional Metrics](#additional-metrics)
6. [Measuring Performance](#measuring-performance)
7. [Performance Budgets](#performance-budgets)
8. [Real User Monitoring](#real-user-monitoring)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Resources](#resources)

---

## Core Web Vitals

```
Google's Core Web Vitals (2024+):

┌────────────────────────────────────────────┐
│  Metric    │  Good    │  Needs Work │ Poor │
├────────────┼──────────┼─────────────┼──────┤
│  LCP       │  ≤2.5s   │  2.5-4s     │ >4s  │
│  INP       │  ≤200ms  │  200-500ms  │ >500ms│
│  CLS       │  ≤0.1    │  0.1-0.25   │ >0.25│
└────────────────────────────────────────────┘

LCP: Loading performance — how fast does main content appear?
INP: Interactivity — how fast does the page respond to user input?
CLS: Visual stability — does the page shift around during load?
```

---

## LCP - Largest Contentful Paint

```
What it measures: Time until the largest visible content element renders.
Largest element is usually: hero image, heading text, or video poster.

Optimize LCP:
1. Optimize server response time (TTFB)
2. Preload critical resources
3. Optimize images (format, size, lazy loading)
4. Remove render-blocking CSS/JS
5. Use CDN for static assets
```

```html
<!-- Preload hero image -->
<link rel="preload" as="image" href="/hero.webp" />

<!-- Preload critical font -->
<link rel="preload" as="font" href="/fonts/Inter.woff2" crossorigin />
```

```typescript
// Preload critical images in React
function HeroImage() {
  return (
    <img
      src="/hero.webp"
      alt="Hero"
      loading="eager"           // Don't lazy load LCP image
      fetchPriority="high"      // Prioritize this fetch
      decoding="async"
      width={1200}
      height={600}
    />
  );
}
```

---

## INP - Interaction to Next Paint

```
What it measures: Time from user interaction to visual update.
Replaced FID (First Input Delay) in 2024.

Unlike FID (measures only first interaction), INP measures ALL interactions
and reports the worst-case responsiveness.

Optimize INP:
1. Avoid long tasks (>50ms) on main thread
2. Use web workers for heavy computation
3. Debounce rapid interactions
4. Use React.startTransition for non-urgent updates
5. Optimize event handlers
```

```typescript
// React 18: Mark non-urgent updates as transitions
import { useTransition } from 'react';

function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isPending, startTransition] = useTransition();

  const handleSearch = (value: string) => {
    setQuery(value); // Urgent: update input immediately

    startTransition(() => {
      // Non-urgent: can be deferred
      const filtered = filterLargeDataset(value);
      setResults(filtered);
    });
  };

  return (
    <div>
      <input value={query} onChange={(e) => handleSearch(e.target.value)} />
      <div className={isPending ? 'opacity-50' : ''}>
        <ResultsList results={results} />
      </div>
    </div>
  );
}
```

---

## CLS - Cumulative Layout Shift

```
What it measures: How much the page layout shifts unexpectedly.
Caused by: images without dimensions, dynamically injected content,
           late-loading fonts, ads.

Optimize CLS:
1. Always set width/height on images and videos
2. Reserve space for dynamic content
3. Use font-display: swap with size-adjusted fallback
4. Avoid inserting content above existing content
5. Use CSS aspect-ratio for responsive media
```

```typescript
// Always specify dimensions
<img src="/photo.jpg" width={600} height={400} alt="Photo" />

// Or use aspect-ratio
<div className="aspect-video bg-gray-200">
  <img src="/video-thumb.jpg" className="w-full h-full object-cover" />
</div>

// Skeleton placeholder (prevents CLS)
function AdBanner() {
  const { data, isLoading } = useQuery({ queryKey: ['ad'], queryFn: fetchAd });

  return (
    <div className="h-[250px] w-[300px]"> {/* Fixed dimensions */}
      {isLoading ? (
        <div className="h-full bg-gray-100 animate-pulse rounded" />
      ) : (
        <img src={data.imageUrl} className="w-full h-full" alt="Ad" />
      )}
    </div>
  );
}
```

---

## Additional Metrics

```
TTFB (Time to First Byte): Server response time
  Good: <800ms

FCP (First Contentful Paint): First text/image rendered
  Good: <1.8s

TTI (Time to Interactive): Page fully interactive
  Good: <3.8s

TBT (Total Blocking Time): Main thread blocked time
  Good: <200ms

Speed Index: How quickly content is visually populated
  Good: <3.4s
```

---

## Measuring Performance

### web-vitals Library

```bash
pnpm add web-vitals
```

```typescript
// utils/reportWebVitals.ts
import { onCLS, onINP, onLCP, onFCP, onTTFB } from 'web-vitals';

function sendToAnalytics(metric: any) {
  const { name, value, id, rating } = metric;
  console.log(`${name}: ${value.toFixed(2)} (${rating})`);

  // Send to analytics service
  navigator.sendBeacon('/api/analytics', JSON.stringify({
    name, value, id, rating,
    url: window.location.href,
    timestamp: Date.now(),
  }));
}

export function reportWebVitals() {
  onCLS(sendToAnalytics);
  onINP(sendToAnalytics);
  onLCP(sendToAnalytics);
  onFCP(sendToAnalytics);
  onTTFB(sendToAnalytics);
}

// main.tsx
reportWebVitals();
```

### Performance API

```typescript
// Measure custom operations
performance.mark('fetch-start');
const data = await fetchUsers();
performance.mark('fetch-end');

performance.measure('user-fetch', 'fetch-start', 'fetch-end');
const measure = performance.getEntriesByName('user-fetch')[0];
console.log(`Fetch took: ${measure.duration.toFixed(2)}ms`);
```

---

## Performance Budgets

```
Set limits for your application:

Bundle Size:
  - Initial JS: <200KB (compressed)
  - Per-route chunk: <50KB
  - Total CSS: <50KB

Metrics:
  - LCP: <2.5s
  - INP: <200ms
  - CLS: <0.1
  - TTFB: <800ms

Images:
  - Hero image: <200KB
  - Thumbnails: <30KB
  - Use WebP/AVIF format
```

```javascript
// vite.config.ts — warn on large chunks
export default defineConfig({
  build: {
    chunkSizeWarningLimit: 500, // Warn if chunk > 500KB
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          query: ['@tanstack/react-query'],
          router: ['@tanstack/react-router'],
        },
      },
    },
  },
});
```

---

## Real User Monitoring

```typescript
// Track performance for real users (not just lab tests)
function PerformanceMonitor() {
  useEffect(() => {
    // Long task observer
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > 50) {
            console.warn(`Long task detected: ${entry.duration.toFixed(2)}ms`);
          }
        }
      });
      observer.observe({ type: 'longtask', buffered: true });
      return () => observer.disconnect();
    }
  }, []);

  return null;
}
```

---

## Common Patterns & Best Practices

- Measure first, optimize second (don't guess)
- Use Lighthouse CI in your pipeline
- Set performance budgets and enforce them
- Monitor real user metrics, not just lab tests
- Prioritize LCP — it has the most user impact
- Use `loading="lazy"` for below-fold images
- Use `fetchPriority="high"` for hero images

---

## Resources

- **Web Vitals:** https://web.dev/vitals/
- **web-vitals library:** https://github.com/GoogleChrome/web-vitals
- **Lighthouse:** https://developer.chrome.com/docs/lighthouse/
- **PageSpeed Insights:** https://pagespeed.web.dev/

---

**Next:** [Part 13.2: React Performance Optimization](./13-react-performance-optimization.md)
