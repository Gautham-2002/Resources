# Part 13.4: Build & Bundle Size Optimization

## What You'll Learn

- Analyzing bundle size
- Tree shaking and dead code elimination
- Code splitting strategies
- Dependency optimization
- Compression (gzip, brotli)
- Vite build configuration

---

## Table of Contents

1. [Analyzing Bundle Size](#analyzing-bundle-size)
2. [Tree Shaking](#tree-shaking)
3. [Code Splitting](#code-splitting)
4. [Dependency Optimization](#dependency-optimization)
5. [Compression](#compression)
6. [Vite Build Config](#vite-build-config)
7. [Common Patterns & Best Practices](#common-patterns--best-practices)
8. [Common Pitfalls](#common-pitfalls)
9. [Resources](#resources)

---

## Analyzing Bundle Size

### Vite Bundle Analyzer

```bash
pnpm add -D rollup-plugin-visualizer
```

```typescript
// vite.config.ts
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    react(),
    visualizer({
      open: true,
      gzipSize: true,
      filename: 'bundle-analysis.html',
    }),
  ],
});
```

```bash
# Build and see analysis
pnpm build
# Opens interactive treemap in browser
```

### Package Size Checking

```bash
# Check package size before installing
npx bundle-phobia <package-name>

# Or use bundlephobia.com
# https://bundlephobia.com/package/lodash
```

---

## Tree Shaking

```typescript
// Tree shaking removes unused exports from bundles

// ❌ Imports entire library (~70KB)
import _ from 'lodash';
const result = _.pick(obj, ['name']);

// ✅ Import only what you need (~2KB)
import pick from 'lodash/pick';
const result = pick(obj, ['name']);

// ✅ Or use lodash-es (tree-shakeable)
import { pick } from 'lodash-es';

// Icon libraries: same principle
// ❌ Imports ALL icons (~500KB)
import { icons } from 'lucide-react';

// ✅ Import individual icons (~1KB each)
import { Search, User, Settings } from 'lucide-react';
```

---

## Code Splitting

### Route-Based (Most Common)

```typescript
// Each route becomes a separate chunk
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Users = lazy(() => import('./pages/Users'));
const Analytics = lazy(() => import('./pages/Analytics'));

// Vite automatically creates:
// dist/assets/Dashboard-[hash].js
// dist/assets/Users-[hash].js
// dist/assets/Analytics-[hash].js
```

### Component-Based

```typescript
// Heavy components loaded on demand
const RichTextEditor = lazy(() => import('./components/RichTextEditor'));
const ChartLibrary = lazy(() => import('./components/Charts'));

function PostEditor() {
  return (
    <Suspense fallback={<EditorSkeleton />}>
      <RichTextEditor />
    </Suspense>
  );
}
```

### Manual Chunk Configuration

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks (shared across routes)
          'vendor-react': ['react', 'react-dom'],
          'vendor-query': ['@tanstack/react-query'],
          'vendor-router': ['@tanstack/react-router'],
          'vendor-ui': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
  },
});
```

---

## Dependency Optimization

### Audit Dependencies

```bash
# Check for duplicate packages
npx depcheck

# Find lighter alternatives
# date-fns (~7KB) vs moment (~72KB)
# zustand (~1KB) vs redux toolkit (~40KB)
# clsx (~0.5KB) vs classnames (~1KB)
```

### Common Replacements

```
Heavy Library    → Lighter Alternative     │ Size Saved
─────────────────┼─────────────────────────┼──────────
moment.js (72KB) → date-fns (7KB)          │ 65KB
                 → dayjs (2KB)             │ 70KB
lodash (70KB)    → lodash-es (tree-shake)  │ ~60KB
                 → native JS methods       │ 70KB
axios (13KB)     → ky (3KB)                │ 10KB
                 → native fetch            │ 13KB
uuid (4KB)       → crypto.randomUUID()     │ 4KB
classnames (1KB) → clsx (0.5KB)            │ 0.5KB
```

### Dynamic Imports for Heavy Features

```typescript
// Don't bundle PDF generation in main bundle
async function exportToPDF(data: Report) {
  const { jsPDF } = await import('jspdf'); // Loaded on demand
  const doc = new jsPDF();
  doc.text(data.title, 10, 10);
  doc.save('report.pdf');
}

// Don't bundle chart library in main bundle
async function renderChart(container: HTMLElement) {
  const { Chart } = await import('chart.js/auto');
  new Chart(container, { /* ... */ });
}
```

---

## Compression

### Vite Compression Plugin

```bash
pnpm add -D vite-plugin-compression
```

```typescript
// vite.config.ts
import compression from 'vite-plugin-compression';

export default defineConfig({
  plugins: [
    react(),
    compression({
      algorithm: 'gzip',
      ext: '.gz',
    }),
    compression({
      algorithm: 'brotliCompress',
      ext: '.br',
    }),
  ],
});
```

### Server Configuration

```nginx
# Nginx: Serve pre-compressed files
location /assets/ {
  gzip_static on;
  brotli_static on;
  expires 1y;
  add_header Cache-Control "public, immutable";
}
```

---

## Vite Build Config

### Optimized Production Config

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    target: 'es2020',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,  // Remove console.log in production
        drop_debugger: true, // Remove debugger statements
      },
    },
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('react')) return 'vendor-react';
            if (id.includes('@tanstack')) return 'vendor-tanstack';
            return 'vendor';
          }
        },
      },
    },
    chunkSizeWarningLimit: 500,
    sourcemap: true, // Enable for debugging production issues
  },
});
```

---

## Common Patterns & Best Practices

### Pattern 1: Bundle Budget in CI

```yaml
# .github/workflows/bundle-check.yml
- name: Check bundle size
  run: |
    pnpm build
    # Fail if main chunk > 200KB
    MAX_SIZE=200000
    MAIN_SIZE=$(stat -f%z dist/assets/index-*.js)
    if [ $MAIN_SIZE -gt $MAX_SIZE ]; then
      echo "Bundle too large: ${MAIN_SIZE} bytes"
      exit 1
    fi
```

### Pattern 2: Import Cost Awareness

```
Install "Import Cost" VS Code extension
Shows the size of each import inline:
  import { pick } from 'lodash-es';  // 2.3KB
  import moment from 'moment';       // 72KB ← WARNING!
```

---

## Common Pitfalls

### Pitfall 1: Not Tree Shaking Barrel Exports

```typescript
// ❌ Barrel exports can prevent tree shaking
// utils/index.ts
export { formatDate } from './date';
export { formatCurrency } from './currency';
export { heavyFunction } from './heavy'; // Included even if not used!

// ✅ Import directly from the module
import { formatDate } from '@/utils/date';
```

### Pitfall 2: Development Dependencies in Production

```json
// ❌ devDependencies installed in production
{
  "dependencies": {
    "react": "^18.2.0",
    "@tanstack/react-query-devtools": "^5.0.0"  // Should be devDependency!
  }
}

// ✅ Correct placement
{
  "dependencies": { "react": "^18.2.0" },
  "devDependencies": { "@tanstack/react-query-devtools": "^5.0.0" }
}
```

---

## Resources

- **Vite Build Optimization:** https://vitejs.dev/guide/build
- **Bundlephobia:** https://bundlephobia.com/
- **Import Cost Extension:** https://marketplace.visualstudio.com/items?itemName=wix.vscode-import-cost
- **Lighthouse Performance:** https://developer.chrome.com/docs/lighthouse/performance/

---

**Next:** [Part 14.1: Testing Pyramid](../part-14/14-testing-pyramid.md)
