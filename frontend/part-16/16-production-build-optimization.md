# Part 16.1: Production Build and Optimization

## What You'll Learn

- Build process with Vite
- Bundle analysis and optimization
- Code splitting strategies
- Lazy loading implementation
- Image optimization
- Tree-shaking techniques
- Asset hashing for caching
- Performance budget management
- Interview questions

---

## Table of Contents

1. [Build Process](#build-process)
2. [Bundle Analysis](#bundle-analysis)
3. [Code Splitting](#code-splitting)
4. [Lazy Loading](#lazy-loading)
5. [Image Optimization](#image-optimization)
6. [Tree-Shaking](#tree-shaking)
7. [Asset Hashing](#asset-hashing)
8. [Performance Budget](#performance-budget)
9. [Common Patterns](#common-patterns)
10. [Interview Questions](#interview-questions)
11. [Resources](#resources)

---

## Build Process

### Vite Build Configuration

```javascript
// vite.config.js
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    minify: 'terser',
    terserOptions: {
      compress: { drop_console: true }
    },
    sourcemap: false,  // true in staging only
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@radix-ui/react-dialog'],
          query: ['@tanstack/react-query']
        }
      }
    },
    chunkSizeWarningLimit: 500
  }
})
```

### Build Output Structure

```bash
# Run build
npm run build

# Output:
# dist/
# ├── index.html
# ├── assets/
# │   ├── index-abc123.js (main app code)
# │   ├── vendor-def456.js (React + ReactDOM)
# │   ├── ui-ghi789.js (UI library)
# │   ├── index-mno345.css
# │   └── logo-pqr678.webp

# Files have hash for cache busting
# If content changes, hash changes
# Browser downloads new version
```

### Build Steps

```javascript
// 1. Analysis - scan source files
// 2. Compilation - TS/JSX to JS
// 3. Module resolution - link dependencies
// 4. Tree-shaking - remove unused code
// 5. Code splitting - separate chunks
// 6. Minification - reduce file size
// 7. Optimization - compress assets
// 8. Hashing - add cache-bust hashes
```

---

## Bundle Analysis

### Using Visualizer

```javascript
// vite.config.js
import { visualizer } from "rollup-plugin-visualizer";

export default {
  plugins: [
    visualizer({
      open: true,
      filename: "dist/stats.html"
    })
  ]
}

// npm install -D rollup-plugin-visualizer
// npm run build
// View dist/stats.html automatically
```

### Analyzing Results

```javascript
// Example output:
// Total: 485KB (raw) | 145KB (gzipped)

// By package:
// react-dom: 125KB | 35KB gzipped
// react: 65KB | 18KB gzipped
// @radix-ui: 85KB | 22KB gzipped
// lodash: 72KB | 19KB gzipped  ← Can optimize!
// Your app code: 70KB | 36KB gzipped

// Opportunities:
// - Replace lodash (save 72KB)
// - Reduce @radix-ui (save 40KB)
// - Total possible: 180KB saved
```

---

## Code Splitting

### Manual Code Splitting

```javascript
export default {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
          ui: ['@radix-ui/react-dialog'],
          query: ['@tanstack/react-query'],
          zustand: ['zustand'],
          form: ['react-hook-form', 'zod']
        }
      }
    }
  }
}

// Benefits:
// - Separate chunks don't change together
// - React rarely changes (cached longer)
// - UI updates need redownload
// - Faster for incremental updates
```

### Dynamic Import Splitting

```jsx
// Automatic code splitting for routes
import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';

// Each route becomes separate chunk
const Home = lazy(() => import('./pages/Home'));
const About = lazy(() => import('./pages/About'));
const Products = lazy(() => import('./pages/Products'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/products" element={<Products />} />
      </Routes>
    </Suspense>
  );
}

// Results:
// - Initial bundle: 45KB (Home + common)
// - About chunk: 12KB (loaded on demand)
// - Products chunk: 18KB (loaded on demand)
// - Much faster initial load!
```

---

## Lazy Loading

### Route-Based Lazy Loading

```jsx
import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));
const Admin = lazy(() => import('./pages/Admin'));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

// Only Dashboard loads initially
// Settings loads when user navigates to /settings
// Admin loads when user navigates to /admin
```

### Component-Based Lazy Loading

```jsx
// Lazy load large components
import { lazy, Suspense } from 'react';

const HeavyChart = lazy(() => import('./components/HeavyChart'));
const RichTextEditor = lazy(() => import('./components/RichTextEditor'));

function App() {
  const [showChart, setShowChart] = useState(false);
  
  return (
    <div>
      <button onClick={() => setShowChart(true)}>
        Show Chart
      </button>
      
      {showChart && (
        <Suspense fallback={<div>Loading chart...</div>}>
          <HeavyChart />
        </Suspense>
      )}
    </div>
  );
}

// HeavyChart only loads when user clicks button
// Saves 50KB from initial bundle
```

### Intersection Observer Lazy Loading

```jsx
function LazyComponent() {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef(null);
  
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsVisible(true);
        observer.unobserve(entry.target);
      }
    });
    
    if (ref.current) {
      observer.observe(ref.current);
    }
    
    return () => observer.disconnect();
  }, []);
  
  return (
    <div ref={ref}>
      {isVisible ? (
        <HeavyComponent />
      ) : (
        <div style={{ height: '400px' }}>Placeholder</div>
      )}
    </div>
  );
}

// Component only renders when scrolled into view
// Great for long pages with many heavy components
```

---

## Image Optimization

### Image Format Optimization

```jsx
// Use modern formats with fallbacks
function OptimizedImage({ src, alt }) {
  return (
    <picture>
      {/* Modern: WebP */}
      <source srcSet={src.replace(/\.\w+$/, '.webp')} type="image/webp" />
      
      {/* Fallback: JPEG */}
      <img src={src} alt={alt} loading="lazy" />
    </picture>
  );
}

// Example sizes:
// Original JPEG: 200KB
// Optimized WebP: 45KB (4.4x smaller!)
```

### Responsive Images

```jsx
function ResponsiveImage({ src, alt }) {
  return (
    <picture>
      {/* Mobile: 400px wide */}
      <source 
        media="(max-width: 640px)" 
        srcSet={src.replace(/\.\w+$/, '-sm.webp')} 
      />
      
      {/* Tablet: 800px wide */}
      <source 
        media="(max-width: 1024px)" 
        srcSet={src.replace(/\.\w+$/, '-md.webp')} 
      />
      
      {/* Desktop: 1200px wide */}
      <source 
        srcSet={src.replace(/\.\w+$/, '-lg.webp')} 
      />
      
      {/* Fallback */}
      <img src={src} alt={alt} loading="lazy" />
    </picture>
  );
}

// Results:
// Mobile: 45KB (optimized for small screen)
// Tablet: 80KB (medium resolution)
// Desktop: 150KB (full resolution)
// Users only download what they need!
```

### Image Optimization Tools

```bash
# Optimize images before deploying
npm install -g imagemin-cli

# Optimize all images
imagemin img/**/* --out-dir=img-optimized

# WebP conversion
npm install -D imagemin-webp

# Batch optimize
imagemin img/**/* --plugin=webp --out-dir=img-webp

# Results:
# Original PNG: 500KB
# Optimized PNG: 150KB (70% smaller)
# WebP: 40KB (92% smaller!)
```

---

## Tree-Shaking

### Understanding Tree-Shaking

```javascript
// tree-shaking removes unused code

// utils.js
export function usedFunction() { }
export function unusedFunction() { }
export function anotherUnused() { }

// app.js
import { usedFunction } from './utils';
usedFunction();

// After tree-shaking:
// unusedFunction is removed
// anotherUnused is removed
// Only usedFunction in final bundle

// Size reduction:
// Before: 50KB
// After: 15KB (70% reduction!)
```

### Enabling Tree-Shaking

```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      // Enable tree-shaking
      treeshake: {
        moduleSideEffects: false,  // Remove modules with no side effects
        propertyReadSideEffects: false
      }
    }
  }
}

// Write code that enables tree-shaking:

// ✅ GOOD: Named exports (tree-shakeable)
export function add(a, b) { return a + b; }
export function subtract(a, b) { return a - b; }
export function multiply(a, b) { return a * b; }

// Only used function imported
import { add } from './math';  // subtract and multiply removed!

// ❌ BAD: Default exports (not tree-shakeable)
export default {
  add: (a, b) => a + b,
  subtract: (a, b) => a - b,
  multiply: (a, b) => a * b
}
// All functions stay in bundle
```

---

## Asset Hashing

### Cache Busting with Hashes

```javascript
// dist/assets/index-abc123.js
// dist/assets/index-def456.css

// Hash is based on content:
// - File changes → hash changes
// - Hash changes → browser downloads new version
// - No hash → browser caches forever

// Setup caching headers:
Cache-Control: max-age=31536000, immutable  // 1 year (never changes)

// For index.html:
Cache-Control: no-cache, no-store, must-revalidate  // Always check
```

### Filename Hashing Configuration

```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      output: {
        // Customize hash filename
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]'
      }
    }
  }
}

// Result:
// index-abc123.js (hashed - cache 1 year)
// vendor-def456.js (hashed - cache 1 year)
// index.html (no hash - cache 1 hour)
```

---

## Performance Budget

### Setting Budgets

```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      output: {
        // Warn if chunks exceed size
        manualChunks: {
          vendor: ['react', 'react-dom']  // Should be ~150KB gzipped
        }
      }
    },
    chunkSizeWarningLimit: 500  // KB - warn if chunk > 500KB
  }
}

// Recommended budgets (gzipped):
// JS bundle: < 200KB
// CSS bundle: < 50KB
// Images: < 1MB total
// Fonts: < 200KB total
```

### Monitoring Budgets

```bash
# Check bundle size after build
npm run build

# Output shows:
# dist/assets/index-abc123.js   145.25 kB │ gzip:  42.51 kB
# dist/assets/vendor-def456.js  285.43 kB │ gzip:  95.23 kB
# dist/assets/index-mno345.css   25.12 kB │ gzip:   6.78 kB

# If over budget, warnings appear:
# ⚠️ (!) some of the bundled packages are quite large...
```

---

## Common Patterns

### Pattern 1: Optimized Build Setup

```javascript
// vite.config.js - production-ready
export default {
  build: {
    outDir: 'dist',
    minify: 'terser',
    sourcemap: process.env.VITE_SOURCEMAP === 'true',
    
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['@radix-ui/react-dialog'],
          query: ['@tanstack/react-query'],
          form: ['react-hook-form', 'zod'],
          utils: ['date-fns']
        }
      }
    },
    
    chunkSizeWarningLimit: 500
  }
}
```

### Pattern 2: Environment-Based Configuration

```javascript
// vite.config.js
export default {
  build: {
    sourcemap: process.env.NODE_ENV === 'staging',
    minify: process.env.NODE_ENV === 'production' ? 'terser' : false,
    
    rollupOptions: {
      output: {
        manualChunks: process.env.NODE_ENV === 'production' 
          ? {...}  // Full splitting in production
          : {}     // No splitting in staging
      }
    }
  }
}
```

---

## Interview Questions

### Q1: How do you optimize a React app for production?

```
Answer:
1. Code splitting
   - Separate vendor from app code
   - Lazy load routes
   - Split heavy components

2. Tree-shaking
   - Remove unused code
   - Use named exports
   - Check bundle analysis

3. Asset optimization
   - Image compression (WebP)
   - Lazy load images
   - Responsive images

4. Caching
   - Hash filenames
   - Cache busting
   - Long-term caching headers

5. Monitoring
   - Bundle size analysis
   - Performance budget
   - Web Vitals tracking
```

### Q2: What's code splitting and why do you need it?

```
Answer:
Code splitting: Breaking bundle into smaller chunks

Why:
- Initial bundle smaller (faster load)
- Code loads on demand
- Better caching (vendor doesn't change)
- Parallel downloads

How:
- Route-based: lazy(() => import('./page'))
- Component-based: lazy(() => import('./component'))
- Library-based: manualChunks in config

Result:
- 450KB → 150KB initial (67% reduction)
- Remaining chunks load when needed
```

---

## Resources

- **Vite Build:** https://vitejs.dev/guide/build.html
- **Bundle Analysis:** https://github.com/btd/rollup-plugin-visualizer
- **Image Optimization:** https://imageoptim.com/
- **Tree-shaking:** https://webpack.js.org/guides/tree-shaking/
- **Performance Budget:** https://web.dev/performance-budgets-101/

---

**Next:** [Part 16.2: Deployment Platforms & CI/CD](./16-deployment-platforms-cicd.md) - Deploying to production
