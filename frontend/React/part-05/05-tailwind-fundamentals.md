# Part 5.1: Tailwind CSS Fundamentals

## What You'll Learn

- Utility-first CSS philosophy and why it works
- How Tailwind differs from traditional CSS/SCSS
- Installation and setup with Vite
- Configuration and theme customization
- Responsive design with breakpoints
- Dark mode implementation
- Core utility classes and layout system
- Extending Tailwind with custom utilities

---

## Table of Contents

1. [Utility-First Philosophy](#utility-first-philosophy)
2. [Why Tailwind Over Traditional CSS](#why-tailwind-over-traditional-css)
3. [Installation & Setup with Vite](#installation--setup-with-vite)
4. [Configuration Deep Dive](#configuration-deep-dive)
5. [Core Utility Classes](#core-utility-classes)
6. [Layout & Flexbox/Grid](#layout--flexboxgrid)
7. [Responsive Design](#responsive-design)
8. [Dark Mode](#dark-mode)
9. [Theme Customization](#theme-customization)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Resources](#resources)

---

## Utility-First Philosophy

### What Does "Utility-First" Mean?

Instead of writing custom CSS classes with semantic names, you compose styles using small, single-purpose utility classes directly in your markup.

```html
<!-- Traditional CSS approach -->
<div class="card">
  <h2 class="card-title">Hello</h2>
  <p class="card-description">World</p>
</div>

<style>
.card {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.card-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a1a1a;
}
.card-description {
  font-size: 0.875rem;
  color: #666;
  margin-top: 8px;
}
</style>

<!-- Tailwind utility-first approach -->
<div class="bg-white rounded-lg p-6 shadow-md">
  <h2 class="text-xl font-bold text-gray-900">Hello</h2>
  <p class="text-sm text-gray-500 mt-2">World</p>
</div>
```

### Why This Works

```
Traditional CSS Problems:
1. Naming is HARD ("card-wrapper-inner-content"?)
2. CSS grows unbounded over time
3. Dead CSS accumulates
4. Global scope causes conflicts
5. Context switching between HTML and CSS files

Utility-First Benefits:
1. No naming - just describe what it looks like
2. CSS file size is bounded (only utilities you use)
3. Dead CSS automatically removed (PurgeCSS)
4. No global conflicts (styles are local to element)
5. Everything in one file (component file)
```

### The Initial Resistance

Most developers' first reaction: "This looks ugly and verbose!"

```html
<!-- Looks messy? -->
<button class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition-colors duration-200">
  Click me
</button>
```

But consider:
1. You never leave the template to style it
2. You can see exactly what it looks like by reading classes
3. Refactoring is safe (delete component, styles go with it)
4. Design consistency is enforced by the design system

---

## Why Tailwind Over Traditional CSS

### Problem 1: CSS Grows Forever

```css
/* Traditional: Your CSS file after 2 years */
.btn { ... }
.btn-primary { ... }
.btn-secondary { ... }
.btn-large { ... }
.btn-small { ... }
.btn-outline { ... }
.btn-ghost { ... }
.card { ... }
.card-header { ... }
.card-body { ... }
.card-footer { ... }
/* ... 5000+ lines nobody dares to touch */

/* Tailwind: Your CSS is always the same size */
/* Only utilities you actually use are included */
/* Delete a component? Its styles disappear too */
```

### Problem 2: Naming Conventions Break Down

```css
/* BEM naming - starts clean, gets messy */
.header__nav-item--active { ... }
.header__nav-item__link--disabled { ... }
.main-content__sidebar__widget__title--highlighted { ... }

/* With Tailwind: No naming needed */
```

### Problem 3: Global Scope Conflicts

```css
/* File A */
.title { color: red; }

/* File B (different developer) */
.title { color: blue; } /* Conflict! */

/* Tailwind: No custom class names = no conflicts */
```

### When NOT to Use Tailwind

```
❌ Very simple static pages (vanilla CSS is fine)
❌ Teams that strongly prefer CSS-in-JS
❌ Projects with strict BEM/SMACSS requirements
❌ When you need highly dynamic styles computed at runtime

✅ Component-based frameworks (React, Vue, Svelte)
✅ Design-system driven projects
✅ Teams wanting consistent styling
✅ Projects needing rapid prototyping
```

---

## Installation & Setup with Vite

### Step 1: Install Dependencies

```bash
# In your Vite + React project
pnpm add -D tailwindcss @tailwindcss/vite
```

### Step 2: Configure Vite Plugin (Tailwind v4+)

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
});
```

### Step 3: Import in CSS

```css
/* src/index.css */
@import "tailwindcss";
```

### Step 4: Import CSS in Entry Point

```typescript
// src/main.tsx
import './index.css';
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### Tailwind v3 Setup (Legacy)

```bash
pnpm add -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

```javascript
// tailwind.config.js (v3)
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

```css
/* src/index.css (v3) */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

---

## Configuration Deep Dive

### Tailwind v4: CSS-First Configuration

```css
/* src/index.css - Tailwind v4 uses CSS for configuration */
@import "tailwindcss";

/* Custom theme values */
@theme {
  --color-brand: #3b82f6;
  --color-brand-dark: #1d4ed8;
  --font-family-display: "Inter", sans-serif;
  --breakpoint-3xl: 1920px;
}
```

### Tailwind v3: JS Configuration

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    // Override defaults
    colors: {
      // Completely replace color palette
      primary: '#3b82f6',
      secondary: '#10b981',
    },
    extend: {
      // Extend defaults (preferred - keeps existing + adds new)
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a8a',
        },
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      fontFamily: {
        display: ['Inter', 'sans-serif'],
        body: ['Roboto', 'sans-serif'],
      },
      borderRadius: {
        '4xl': '2rem',
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'fade-in': 'fadeIn 0.5s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
```

---

## Core Utility Classes

### Typography

```html
<!-- Font size -->
<p class="text-xs">Extra small (12px)</p>
<p class="text-sm">Small (14px)</p>
<p class="text-base">Base (16px)</p>
<p class="text-lg">Large (18px)</p>
<p class="text-xl">Extra large (20px)</p>
<p class="text-2xl">2XL (24px)</p>
<p class="text-4xl">4XL (36px)</p>

<!-- Font weight -->
<p class="font-light">Light (300)</p>
<p class="font-normal">Normal (400)</p>
<p class="font-medium">Medium (500)</p>
<p class="font-semibold">Semibold (600)</p>
<p class="font-bold">Bold (700)</p>

<!-- Text color -->
<p class="text-gray-500">Gray text</p>
<p class="text-blue-600">Blue text</p>
<p class="text-red-500">Red text</p>

<!-- Text alignment -->
<p class="text-left">Left aligned</p>
<p class="text-center">Center aligned</p>
<p class="text-right">Right aligned</p>

<!-- Line height -->
<p class="leading-tight">Tight line height</p>
<p class="leading-normal">Normal line height</p>
<p class="leading-relaxed">Relaxed line height</p>

<!-- Letter spacing -->
<p class="tracking-tight">Tight tracking</p>
<p class="tracking-wide">Wide tracking</p>
```

### Spacing (Padding & Margin)

```html
<!-- Padding -->
<div class="p-4">All sides: 1rem (16px)</div>
<div class="px-4">Horizontal: 1rem</div>
<div class="py-2">Vertical: 0.5rem</div>
<div class="pt-8">Top: 2rem</div>
<div class="pb-4">Bottom: 1rem</div>
<div class="pl-6">Left: 1.5rem</div>
<div class="pr-2">Right: 0.5rem</div>

<!-- Margin -->
<div class="m-4">All sides: 1rem</div>
<div class="mx-auto">Center horizontally</div>
<div class="mt-8">Top margin: 2rem</div>
<div class="mb-4">Bottom margin: 1rem</div>
<div class="-mt-2">Negative top margin: -0.5rem</div>

<!-- Spacing scale:
  0 = 0px
  1 = 0.25rem (4px)
  2 = 0.5rem (8px)
  3 = 0.75rem (12px)
  4 = 1rem (16px)
  5 = 1.25rem (20px)
  6 = 1.5rem (24px)
  8 = 2rem (32px)
  10 = 2.5rem (40px)
  12 = 3rem (48px)
  16 = 4rem (64px)
  20 = 5rem (80px)
-->
```

### Colors

```html
<!-- Background colors -->
<div class="bg-white">White background</div>
<div class="bg-gray-100">Light gray</div>
<div class="bg-blue-500">Blue-500</div>
<div class="bg-blue-500/50">Blue-500 at 50% opacity</div>

<!-- Border colors -->
<div class="border border-gray-300">Gray border</div>
<div class="border-2 border-blue-500">Blue border</div>

<!-- Ring (focus outline) -->
<input class="ring-2 ring-blue-500" />
```

### Sizing

```html
<!-- Width -->
<div class="w-full">100% width</div>
<div class="w-1/2">50% width</div>
<div class="w-64">16rem (256px)</div>
<div class="w-screen">100vw</div>
<div class="max-w-md">Max width: 28rem</div>
<div class="max-w-4xl">Max width: 56rem</div>
<div class="min-w-0">Min width: 0</div>

<!-- Height -->
<div class="h-screen">100vh</div>
<div class="h-full">100% height</div>
<div class="h-64">16rem (256px)</div>
<div class="min-h-screen">Min height: 100vh</div>
```

### Borders & Rounded Corners

```html
<!-- Border -->
<div class="border">1px border</div>
<div class="border-2">2px border</div>
<div class="border-t">Top border only</div>
<div class="border-b-2 border-gray-200">Bottom border 2px gray</div>

<!-- Border radius -->
<div class="rounded">Small radius (4px)</div>
<div class="rounded-md">Medium (6px)</div>
<div class="rounded-lg">Large (8px)</div>
<div class="rounded-xl">Extra large (12px)</div>
<div class="rounded-full">Full circle/pill</div>
```

### Shadows & Effects

```html
<!-- Box shadow -->
<div class="shadow-sm">Small shadow</div>
<div class="shadow">Default shadow</div>
<div class="shadow-md">Medium shadow</div>
<div class="shadow-lg">Large shadow</div>
<div class="shadow-xl">Extra large shadow</div>

<!-- Opacity -->
<div class="opacity-50">50% opacity</div>
<div class="opacity-75">75% opacity</div>

<!-- Transitions -->
<button class="transition-colors duration-200 ease-in-out">
  Smooth color transition
</button>
<div class="transition-all duration-300">
  All properties transition
</div>
```

---

## Layout & Flexbox/Grid

### Flexbox

```html
<!-- Basic flex container -->
<div class="flex">
  <div>Item 1</div>
  <div>Item 2</div>
</div>

<!-- Direction -->
<div class="flex flex-col">Vertical stack</div>
<div class="flex flex-row">Horizontal (default)</div>

<!-- Alignment -->
<div class="flex items-center">Vertically centered</div>
<div class="flex items-start">Top aligned</div>
<div class="flex items-end">Bottom aligned</div>

<!-- Justify -->
<div class="flex justify-between">Space between</div>
<div class="flex justify-center">Center</div>
<div class="flex justify-end">End</div>

<!-- Centering (most common pattern) -->
<div class="flex items-center justify-center h-screen">
  <p>Perfectly centered</p>
</div>

<!-- Gap -->
<div class="flex gap-4">1rem gap between items</div>
<div class="flex gap-x-4 gap-y-2">Different x/y gaps</div>

<!-- Flex children -->
<div class="flex">
  <div class="flex-1">Takes remaining space</div>
  <div class="flex-none">Fixed size</div>
  <div class="flex-shrink-0">Won't shrink</div>
</div>

<!-- Wrapping -->
<div class="flex flex-wrap gap-4">
  <!-- Items wrap to next line -->
</div>
```

### CSS Grid

```html
<!-- Basic grid -->
<div class="grid grid-cols-3 gap-4">
  <div>Col 1</div>
  <div>Col 2</div>
  <div>Col 3</div>
</div>

<!-- Responsive grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <div>Responsive column</div>
  <div>Responsive column</div>
  <div>Responsive column</div>
</div>

<!-- Column spanning -->
<div class="grid grid-cols-4 gap-4">
  <div class="col-span-2">Takes 2 columns</div>
  <div>1 column</div>
  <div>1 column</div>
</div>

<!-- Auto-fit grid -->
<div class="grid grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-4">
  <!-- Cards auto-fit based on space -->
</div>
```

---

## Responsive Design

### Breakpoint System

```
Tailwind uses mobile-first breakpoints:

sm:  640px   (small tablets)
md:  768px   (tablets)
lg:  1024px  (laptops)
xl:  1280px  (desktops)
2xl: 1536px  (large screens)

Mobile-first means: base styles are for mobile,
then you ADD styles for larger screens.
```

### Usage Pattern

```html
<!-- Mobile: 1 column, Tablet: 2 columns, Desktop: 3 columns -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <div class="p-4">Item</div>
</div>

<!-- Mobile: stack, Desktop: side by side -->
<div class="flex flex-col md:flex-row gap-4">
  <aside class="w-full md:w-64">Sidebar</aside>
  <main class="flex-1">Content</main>
</div>

<!-- Hide/show based on screen -->
<nav class="hidden md:block">Desktop nav</nav>
<button class="md:hidden">Mobile menu button</button>

<!-- Different text sizes per breakpoint -->
<h1 class="text-2xl md:text-4xl lg:text-6xl">
  Responsive heading
</h1>

<!-- Different padding -->
<section class="px-4 md:px-8 lg:px-16">
  Content with responsive padding
</section>
```

---

## Dark Mode

### Class-Based Dark Mode (Recommended for React)

```css
/* Tailwind v4 */
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));
```

```javascript
// Tailwind v3 config
module.exports = {
  darkMode: 'class', // or 'media' for system preference
  // ...
};
```

### Using Dark Mode Classes

```html
<div class="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
  <h1 class="text-black dark:text-white">Title</h1>
  <p class="text-gray-600 dark:text-gray-400">Description</p>
  <button class="bg-blue-500 dark:bg-blue-700 text-white">
    Action
  </button>
</div>
```

### Toggle Implementation with React + Zustand

```typescript
// stores/themeStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ThemeStore {
  isDark: boolean;
  toggle: () => void;
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      isDark: false,
      toggle: () => set((state) => {
        const newDark = !state.isDark;
        document.documentElement.classList.toggle('dark', newDark);
        return { isDark: newDark };
      }),
    }),
    { name: 'theme-storage' }
  )
);

// components/ThemeToggle.tsx
import { useThemeStore } from '../stores/themeStore';

export function ThemeToggle() {
  const { isDark, toggle } = useThemeStore();

  return (
    <button
      onClick={toggle}
      class="p-2 rounded-lg bg-gray-200 dark:bg-gray-700"
    >
      {isDark ? '☀️' : '🌙'}
    </button>
  );
}
```

---

## Theme Customization

### Custom Color Palette

```javascript
// tailwind.config.js (v3)
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
          950: '#082f49',
        },
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
      },
    },
  },
};
```

### Custom Fonts

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Cal Sans', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
};
```

```html
<!-- index.html -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

---

## Common Patterns & Best Practices

### Pattern 1: Component Extraction (React)

```typescript
// Instead of repeating long class strings, extract components

// ❌ Repeated everywhere
<button className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition-colors">
  Click
</button>

// ✅ Extract into a component
function Button({ children, variant = 'primary', ...props }) {
  const styles = {
    primary: 'bg-blue-500 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-800',
    danger: 'bg-red-500 hover:bg-red-700 text-white',
  };

  return (
    <button
      className={`${styles[variant]} font-bold py-2 px-4 rounded transition-colors`}
      {...props}
    >
      {children}
    </button>
  );
}
```

### Pattern 2: Conditional Classes with clsx/cn

```typescript
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Utility function (industry standard)
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Usage
function Alert({ type, children }) {
  return (
    <div className={cn(
      'p-4 rounded-lg border',
      type === 'error' && 'bg-red-50 border-red-200 text-red-800',
      type === 'success' && 'bg-green-50 border-green-200 text-green-800',
      type === 'warning' && 'bg-yellow-50 border-yellow-200 text-yellow-800',
    )}>
      {children}
    </div>
  );
}
```

### Pattern 3: Consistent Spacing

```html
<!-- Use consistent spacing throughout -->
<!-- gap-4, p-4, m-4 = 1rem spacing system -->

<div class="space-y-4">  <!-- Vertical spacing between children -->
  <div>Section 1</div>
  <div>Section 2</div>
  <div>Section 3</div>
</div>
```

---

## Common Pitfalls

### Pitfall 1: String Concatenation for Dynamic Classes

```typescript
// ❌ WRONG: Tailwind can't detect dynamically constructed classes
const color = 'blue';
<div className={`bg-${color}-500`}>  {/* Won't work in production! */}

// ✅ CORRECT: Use complete class names
const colorClasses = {
  blue: 'bg-blue-500',
  red: 'bg-red-500',
  green: 'bg-green-500',
};
<div className={colorClasses[color]}>  {/* Works! */}
```

### Pitfall 2: Not Using tailwind-merge

```typescript
// ❌ Problem: Conflicting classes
<div className="bg-red-500 bg-blue-500"> {/* Which wins? Depends on CSS order */}

// ✅ Use tailwind-merge to resolve conflicts
import { twMerge } from 'tailwind-merge';
<div className={twMerge('bg-red-500', isActive && 'bg-blue-500')}>
```

### Pitfall 3: Overusing @apply

```css
/* ❌ Defeats the purpose of utility-first */
.btn {
  @apply bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded;
}

/* ✅ Only use @apply for truly repeated base styles */
/* Better: Create a React component instead */
```

### Pitfall 4: Not Understanding Content Configuration (v3)

```javascript
// ❌ Missing content paths = no styles in production
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  // Forgot index.html!
};

// ✅ Include ALL files that use Tailwind classes
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
};
```

---

## Resources

- **Tailwind CSS Documentation:** https://tailwindcss.com/docs
- **Tailwind CSS v4 Upgrade Guide:** https://tailwindcss.com/docs/upgrade-guide
- **Tailwind Play (Online Playground):** https://play.tailwindcss.com/
- **Tailwind UI (Official Components):** https://tailwindui.com/
- **Headless UI:** https://headlessui.com/
- **tailwind-merge:** https://github.com/dcastil/tailwind-merge
- **clsx:** https://github.com/lukeed/clsx
- **CVA (Class Variance Authority):** https://cva.style/docs

---

**Next:** [Part 5.2: Tailwind CSS Best Practices](./05-tailwind-best-practices.md)
