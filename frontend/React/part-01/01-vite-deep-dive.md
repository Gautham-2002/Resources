# Part 1.2: Vite Deep Dive

## What You'll Learn

- Why Vite exists and what problem it solves
- ESM-first approach
- Development vs production strategies
- Pre-bundling and optimization
- Hot Module Replacement (HMR)
- Vite plugin system
- Configuration and customization
- Performance characteristics
- Comparison with other bundlers

---

## Table of Contents

1. [Why Vite?](#why-vite)
2. [The Core Philosophy](#the-core-philosophy)
3. [Development Server](#development-server)
4. [Production Build](#production-build)
5. [Pre-bundling](#pre-bundling)
6. [Hot Module Replacement (HMR)](#hot-module-replacement-hmr)
7. [Plugin System](#plugin-system)
8. [Configuration Deep Dive](#configuration-deep-dive)
9. [Vite vs Other Bundlers](#vite-vs-other-bundlers)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Resources](#resources)

---

## Why Vite?

### The Webpack Problem (Pre-2020)

By 2020, webpack was the standard, but it had issues:

```
Webpack development build for a medium-sized app:
├── Initial start: 3-5 seconds
├── File change → rebuild: 1-2 seconds
└── Result: Slow feedback loop while developing
```

**Why so slow?**

Webpack processed everything:
1. Parse all files
2. Resolve all dependencies
3. Transform everything (TypeScript → JS, JSX → JS)
4. Bundle everything
5. Serve the bundle

Even if you changed one file, it rebundled everything.

### The Browser Breakthrough (2015+)

Modern browsers support ES Modules natively:

```html
<!-- Modern browsers understand this -->
<script type="module" src="./app.js"></script>
```

```javascript
// app.js
import { Button } from './components/Button.js';
import axios from 'axios'; // Browser fetches from CDN

export function App() { ... }
```

**Key insight:** Browsers can handle module resolution! We don't need to bundle everything anymore.

### Vite's Solution (2020)

**Observation:** During development, we don't need bundling. We need:
1. Fast file serving
2. Module resolution
3. Quick feedback (HMR)

Vite's strategy:
- **Dev:** Serve ES modules directly to browser (unbundled)
- **Prod:** Bundle for optimized shipping (traditional bundling)

```
Dev mode:
browser request → Vite → esbuild transform → send module → HMR on change

Prod mode:
all files → Rollup bundle → optimized output → ship to users
```

---

## The Core Philosophy

Vite's philosophy: **ESM-first, zero-config, lightning-fast**

### Principle 1: Native ESM During Development

Instead of bundling everything:

```javascript
// app.js imports Button
import { Button } from './components/Button.tsx';

// OLD WAY (Webpack):
// 1. Parse app.js
// 2. Find dependency: Button.tsx
// 3. Transform Button.tsx: TypeScript → JavaScript
// 4. Parse Button.tsx, find dependencies
// 5. Keep going recursively
// 6. Bundle everything
// 7. Serve bundle (3-5 seconds)

// VITE WAY:
// 1. Parse app.js
// 2. Find dependency: Button.tsx
// 3. Transform Button.tsx on-demand: TypeScript → JavaScript
// 4. Serve module (50ms)
```

### Principle 2: Smart Pre-bundling

Pre-bundle dependencies only once:

```javascript
// app.js
import React from 'react'; // Large dependency
import axios from 'axios'; // Another dependency

// VITE:
// 1. First time: Pre-bundle react and axios (happens once)
// 2. Serve pre-bundled version
// 3. Your code still unbundled
// 4. Fast dev server!
```

### Principle 3: HMR for Instant Feedback

```javascript
// button.tsx
export function Button() {
  return <button>Click me</button>;
}

// YOU: Edit to <button>Clicked!</button>
// VITE: 
// 1. Detects change
// 2. Sends only updated module via WebSocket
// 3. Browser updates instantly (< 100ms)
// 4. State preserved!
```

---

## Development Server

### How Vite Dev Server Works

```
1. Browser requests http://localhost:5173/
2. Vite serves index.html
3. index.html includes <script type="module" src="/src/main.tsx"></script>
4. Browser requests /src/main.tsx
5. Vite transforms (if needed) and serves
6. Browser processes ES modules, making more requests
7. Each request → Vite transforms on-demand and serves
8. WebSocket connection for HMR updates
```

### Why This is Fast

**Webpack approach:**
```
File change → Rebundle everything → Serve → Wait 1-2 seconds
```

**Vite approach:**
```
File change → Transform only that file → Serve → Instant
```

### Example: Development Server Behavior

```typescript
// src/main.tsx
import React from 'react';
import { Button } from './components/Button';
import axios from 'axios';

// Browser makes requests:
// 1. GET /src/main.tsx → Vite transforms and serves
// 2. GET /src/components/Button.tsx → Transform and serve
// 3. GET /node_modules/.vite/react.js → Pre-bundled, serve
// 4. GET /node_modules/.vite/axios.js → Pre-bundled, serve

// Each request is fast because:
// - Either already pre-bundled (node_modules)
// - Or transformed on-demand (your code)
```

---

## Production Build

### Development vs Production Strategy

**Development:** Keep bundling to minimum, maximize speed

**Production:** Bundle everything, optimize for shipping

Vite uses **Rollup** for production bundling:

```javascript
// vite.config.ts
export default {
  build: {
    // Rollup config
    rollupOptions: {
      output: {
        // Multiple formats supported
        format: 'es', // ES Modules
      }
    }
  }
}
```

### Build Process

```
1. Read all source files
2. Transform (TypeScript → JS, JSX → JS)
3. Bundle using Rollup
4. Minify
5. Generate source maps
6. Emit to dist/ folder
```

### Example Build Output

```
npm run build

✓ 520 modules transformed.
2 packages in 12 ms

dist/index.html                  0.43 kB │ gzip:   0.27 kB
dist/assets/index-hash.js        234.5 kB │ gzip:  58.27 kB
dist/assets/chunk-hash.js        45.3 kB │ gzip:  12.11 kB
dist/assets/index-hash.css       2.5 kB │ gzip:   1.5 kB
```

---

## Pre-bundling

### What is Pre-bundling?

Pre-bundling is a behind-the-scenes optimization:

```javascript
// app.js
import React from 'react';

// VITE DOES:
// 1. Detects react is a dependency
// 2. Finds react in node_modules
// 3. Bundles react into single file
// 4. Places in node_modules/.vite/react.js
// 5. Updates imports to point there
// 6. Next request uses pre-bundled version
```

### Why Pre-bundle?

**Problem 1: Many modules**

```javascript
// react package has 50+ internal files
import React from 'react';

// Without pre-bundling:
// Browser makes 50 requests to load React

// With pre-bundling:
// Browser makes 1 request for bundled React
```

**Problem 2: CommonJS Packages**

```javascript
import axios from 'axios'; // CommonJS package

// Without pre-bundling:
// Browser can't understand CommonJS

// With pre-bundling:
// Vite converts to ESM, browser understands it
```

### Pre-bundling Configuration

```typescript
// vite.config.ts
export default {
  optimizeDeps: {
    // Explicitly include packages to pre-bundle
    include: ['axios', 'react-query'],
    
    // Exclude from pre-bundling
    exclude: ['my-local-package'],
    
    // Force rebuild
    force: true // Delete cache and rebuild
  }
}
```

### When Pre-bundling Happens

1. **On first dev server start** - Builds `.vite/` cache
2. **When dependencies change** - Auto-rebuilds
3. **On explicit command** - `vite optimize --force`

### Cache Location

```
node_modules/.vite/
├── react.js          # Pre-bundled React
├── react-dom.js      # Pre-bundled React DOM
├── axios.js          # Pre-bundled Axios
└── metadata.json     # Metadata about bundles
```

---

## Hot Module Replacement (HMR)

### What is HMR?

HMR allows updating modules without full page reload while preserving state.

### Without HMR (Traditional)

```javascript
// counter.tsx
export function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}

// YOU: Change text to "Count: {count}"
// RESULT: Page refreshes, count resets to 0 ❌
```

### With HMR (Vite)

```javascript
// counter.tsx
export function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}

// YOU: Change text to "Count: {count}"
// RESULT: Module updates, component re-renders, count stays! ✅
```

### How HMR Works

```
1. YOU: Save file
2. VITE: Detects change
3. VITE: Sends update via WebSocket to browser
4. BROWSER: Receives update
5. FRAMEWORK: (React) re-executes the module
6. STATE: If handled correctly, state persists
7. UI: Updates instantly
```

### HMR API (Advanced)

Sometimes you need to handle HMR manually:

```typescript
// api-client.ts
let apiClient = createClient();

// Handle HMR updates
if (import.meta.hot) {
  import.meta.hot.accept(() => {
    apiClient = createClient(); // Recreate on update
  });
}

export function getClient() {
  return apiClient;
}
```

### React Fast Refresh

React Fast Refresh is HMR for React:

```typescript
// Vite auto-handles this with @vitejs/plugin-react
// No manual configuration needed!

// You get:
// 1. Component updates without full reload
// 2. State preservation
// 3. Error boundaries on syntax errors
// 4. Instant feedback
```

---

## Plugin System

### What is a Vite Plugin?

Plugins hook into Vite's build process:

```typescript
// Simple plugin
export default function myPlugin() {
  return {
    name: 'my-plugin', // Required, must be unique
    
    resolveId(id) {
      // Hook into module resolution
      if (id === 'virtual-module') {
        return id;
      }
    },
    
    load(id) {
      // Hook into module loading
      if (id === 'virtual-module') {
        return 'export default "virtual content"';
      }
    }
  };
}
```

### Hooks Available

**Resolution Hooks:**
```typescript
{
  resolveId(id) { }, // Resolve module ID
  resolveDynamicImport(id) { }, // Resolve dynamic imports
}
```

**Transformation Hooks:**
```typescript
{
  transform(code, id) { }, // Transform module code
  transformIndexHtml(html) { }, // Transform index.html
}
```

**Execution Hooks:**
```typescript
{
  configResolved(config) { }, // Called when config is ready
  configureServer(server) { }, // Configure dev server
  handleHotUpdate(ctx) { }, // Custom HMR handling
}
```

### Common Plugins

```typescript
// vite.config.ts
import react from '@vitejs/plugin-react';
import vue from '@vitejs/plugin-vue';
import svgr from 'vite-plugin-svgr';

export default {
  plugins: [
    react(), // React JSX support
    svgr(), // Import SVG as React component
  ]
}
```

### Creating a Custom Plugin

```typescript
// vite-plugin-custom-loader.ts
export default function customLoader() {
  return {
    name: 'custom-loader',
    
    resolveId(id) {
      if (id.endsWith('.custom')) {
        return id;
      }
    },
    
    load(id) {
      if (id.endsWith('.custom')) {
        // Custom file format
        const content = fs.readFileSync(id, 'utf-8');
        const transformed = parseCustomFormat(content);
        return `export default ${JSON.stringify(transformed)}`;
      }
    }
  };
}
```

---

## Configuration Deep Dive

### Minimal Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()]
});
```

That's it! Everything else has good defaults.

### Common Configuration Options

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // Server configuration
  server: {
    port: 3000,
    open: true, // Auto-open browser
    cors: true,
    headers: {
      'Cross-Origin-Embedder-Policy': 'require-corp',
    }
  },

  // Build configuration
  build: {
    target: 'ES2020', // JavaScript target
    outDir: 'dist',
    sourcemap: 'hidden', // Production source maps
    minify: 'terser', // Minification strategy
    
    rollupOptions: {
      output: {
        // Chunk optimization
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
        }
      }
    }
  },

  // Resolve configuration
  resolve: {
    alias: {
      '@': '/src', // Path alias
    },
    extensions: ['.ts', '.tsx', '.js'] // Import extensions
  },

  // CSS configuration
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@import "src/styles/variables.scss";`
      }
    }
  },

  // Environment variables
  define: {
    __APP_VERSION__: JSON.stringify('1.0.0'),
  },

  // Optimize dependencies
  optimizeDeps: {
    include: ['react', 'react-dom'],
    exclude: ['local-package']
  },

  // Plugins
  plugins: [react()]
});
```

### Environment-Specific Configuration

```typescript
// vite.config.ts
export default defineConfig(({ command, mode }) => {
  if (command === 'serve') {
    // Development config
    return {
      define: {
        __DEV__: true
      }
    };
  } else {
    // Production config
    return {
      build: {
        minify: 'terser',
        sourcemap: false
      }
    };
  }
});
```

### Using Environment Variables

```typescript
// .env
VITE_API_URL=https://api.example.com
VITE_APP_NAME=MyApp

// src/config.ts
export const API_URL = import.meta.env.VITE_API_URL;
export const APP_NAME = import.meta.env.VITE_APP_NAME;
```

Important: Only variables prefixed with `VITE_` are exposed to client-side code for security.

---

## Vite vs Other Bundlers

### Vite vs Webpack

| Aspect | Vite | Webpack |
|--------|------|---------|
| Dev Speed | 🚀 Extremely fast | 🐢 Slower |
| Config | 📄 Simple defaults | 🔧 Complex setup |
| Maturity | 🌱 Newer | 🏢 Enterprise-ready |
| Flexibility | ⚡ Good | 🎯 Maximum |
| Learning Curve | 📚 Easy | 📖 Steep |
| Plugins | 🔌 Growing | 🔌 Massive |
| Production | ✅ Good | ✅ Excellent |

**Choose Vite if:**
- You want fast development
- You're building a modern SPA/React app
- You want minimal configuration

**Choose Webpack if:**
- You need maximum flexibility
- You have complex requirements
- You have legacy code

### Vite vs Next.js

| Aspect | Vite | Next.js |
|--------|------|---------|
| Type | ⚙️ Bundler | 🏗️ Framework |
| SSR | ❌ Manual | ✅ Built-in |
| Pages | ❌ Manual routing | ✅ File-based routing |
| API Routes | ❌ Needs separate | ✅ Built-in |
| Setup | 🚀 Quick | 📦 Opinionated |

**Choose Vite if:**
- You want a SPA (Single Page App)
- You need flexibility in architecture
- You like using libraries + building yourself

**Choose Next.js if:**
- You need SSR/SSG
- You want full-stack (API + frontend)
- You prefer conventions over configuration

### Vite vs Turbopack

| Aspect | Vite | Turbopack |
|--------|------|-----------|
| Dev Speed | ⚡ Fast (esbuild) | 🚀 Faster (Rust) |
| Stability | ✅ Stable | 🚧 Alpha |
| Ecosystem | ✅ Mature | 🌱 Early |
| Config | 📄 Simple | 📄 Simple |

**Turbopack is faster but newer. Vite is stable and recommended for production.**

---

## Common Patterns & Best Practices

### Pattern 1: Environment-Based Configuration

```typescript
// vite.config.ts
export default defineConfig({
  define: {
    __DEV__: JSON.stringify(true),
  },
  
  server: {
    // Only in development
    headers: {
      'X-Custom-Header': 'dev'
    }
  }
});

// src/main.ts
if (__DEV__) {
  console.log('Development mode');
}
```

### Pattern 2: Path Aliases for Clean Imports

```typescript
// vite.config.ts
export default defineConfig({
  resolve: {
    alias: {
      '@': '/src',
      '@components': '/src/components',
      '@hooks': '/src/hooks',
      '@utils': '/src/utils',
      '@stores': '/src/stores',
    }
  }
});

// src/App.tsx
import Button from '@components/Button'; // Clean!
import { useLocalStorage } from '@hooks/useLocalStorage';
import { cn } from '@utils/cn';
```

### Pattern 3: Smart Chunking

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate vendor chunks for better caching
          'react-vendor': ['react', 'react-dom'],
          'router': ['@tanstack/react-router'],
          'query': ['@tanstack/react-query'],
        }
      }
    }
  }
});
```

### Pattern 4: Source Map Strategy

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    // Development: Full source maps
    sourcemap: 'inline',
    
    // Production: Hidden source maps (uploaded separately)
    // sourcemap: 'hidden',
  }
});
```

### Pattern 5: HMR Configuration for Remote Development

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    hmr: {
      host: 'your-remote-server.com',
      port: 443,
      protocol: 'wss',
    }
  }
});
```

---

## Common Pitfalls

### Pitfall 1: Large Dependencies in Dev

```typescript
// ❌ Bad - Dependencies pre-bundled, still slow
import * as lodash from 'lodash'; // 70KB!

// ✅ Good - Use smaller alternatives
import { debounce } from 'lodash-es'; // Tree-shakeable
// OR
import { debounce } from 'rambda'; // Smaller
```

### Pitfall 2: Circular Dependencies with HMR

```typescript
// ❌ Can cause HMR issues
// moduleA.ts imports moduleB
// moduleB.ts imports moduleA

// ✅ Refactor to avoid circular imports
// utils.ts (shared)
// moduleA.ts imports utils
// moduleB.ts imports utils
```

### Pitfall 3: Not Handling HMR for Setup Code

```typescript
// ❌ Bad - Setup not rerun on HMR
const client = setupClient();

if (import.meta.hot) {
  import.meta.hot.accept();
}

// ✅ Good - Handle HMR updates
let client = setupClient();

if (import.meta.hot) {
  import.meta.hot.accept(() => {
    client = setupClient();
  });
}
```

### Pitfall 4: Relying on CJS-only Features

```typescript
// ❌ Won't work in Vite (ESM)
require.context('./icons', true, /\.svg$/);

// ✅ Use dynamic imports instead
const icons = import.meta.glob('./icons/*.svg', { eager: true });
```

### Pitfall 5: Misconfigured Build Output

```typescript
// ❌ Bad - All in root
output: { dir: './' }

// ✅ Good - Organized output
output: { dir: 'dist' }
```

---

## Resources

- **Vite Official Documentation:** https://vitejs.dev/
- **Vite Config Reference:** https://vitejs.dev/config/
- **Vite Plugin API:** https://vitejs.dev/guide/api-plugin.html
- **Why Vite (Evan You talk):** https://www.youtube.com/watch?v=UJSr90S6CC0
- **ESM in Browsers:** https://caniuse.com/es6-module
- **Vite Ecosystem Plugins:** https://github.com/vitejs/awesome-vite

---

**Next:** [Part 1.3: Developer Tools & Ecosystem](./01-dev-tools-ecosystem.md) - Master ESLint, Prettier, and development tooling
