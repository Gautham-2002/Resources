# Part 5.2: Tailwind CSS Best Practices

## What You'll Learn

- Component composition patterns with Tailwind
- Managing class name complexity
- Performance optimization and PurgeCSS
- Responsive design patterns
- Accessibility with Tailwind
- Design tokens and consistency
- Common mistakes and how to avoid them

---

## Table of Contents

1. [Component Composition](#component-composition)
2. [Managing Class Complexity](#managing-class-complexity)
3. [The cn() Utility Pattern](#the-cn-utility-pattern)
4. [CVA - Class Variance Authority](#cva---class-variance-authority)
5. [Responsive Design Patterns](#responsive-design-patterns)
6. [Performance Optimization](#performance-optimization)
7. [Accessibility](#accessibility)
8. [Design System Tokens](#design-system-tokens)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Resources](#resources)

---

## Component Composition

### Building a Design System with React Components

```typescript
// components/ui/Button.tsx
import { cn } from '@/utils/cn';
import { type ButtonHTMLAttributes, forwardRef } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          // Base styles
          'inline-flex items-center justify-center rounded-lg font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',

          // Variants
          variant === 'primary' && 'bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-500',
          variant === 'secondary' && 'bg-gray-100 text-gray-900 hover:bg-gray-200 focus-visible:ring-gray-500',
          variant === 'danger' && 'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500',
          variant === 'ghost' && 'hover:bg-gray-100 text-gray-700 focus-visible:ring-gray-500',

          // Sizes
          size === 'sm' && 'h-8 px-3 text-sm',
          size === 'md' && 'h-10 px-4 text-sm',
          size === 'lg' && 'h-12 px-6 text-base',

          className
        )}
        {...props}
      >
        {isLoading && (
          <svg className="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
export { Button };
```

### Input Component

```typescript
// components/ui/Input.tsx
import { cn } from '@/utils/cn';
import { forwardRef, type InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  label?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, label, id, ...props }, ref) => {
    return (
      <div className="space-y-1">
        {label && (
          <label htmlFor={id} className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={cn(
            'flex h-10 w-full rounded-lg border bg-white px-3 py-2 text-sm',
            'placeholder:text-gray-400',
            'focus:outline-none focus:ring-2 focus:ring-offset-2',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'dark:bg-gray-800 dark:text-white dark:border-gray-600',
            error
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:ring-blue-500',
            className
          )}
          {...props}
        />
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
export { Input };
```

---

## Managing Class Complexity

### The Problem

```typescript
// This gets unwieldy fast
<div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-4 md:p-8 lg:p-12">
```

### Solution 1: Extract to Variables

```typescript
function PageLayout({ children }) {
  const containerStyles = cn(
    'flex flex-col items-center justify-center min-h-screen p-4 md:p-8 lg:p-12',
    'bg-gradient-to-br from-blue-50 via-white to-purple-50',
    'dark:from-gray-900 dark:via-gray-800 dark:to-gray-900'
  );

  return <div className={containerStyles}>{children}</div>;
}
```

### Solution 2: Composition Over Concatenation

```typescript
// Break complex UIs into smaller components
function Card({ children, className }) {
  return (
    <div className={cn(
      'rounded-xl border border-gray-200 bg-white shadow-sm',
      'dark:border-gray-700 dark:bg-gray-800',
      className
    )}>
      {children}
    </div>
  );
}

function CardHeader({ children }) {
  return <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-4">{children}</div>;
}

function CardBody({ children }) {
  return <div className="px-6 py-4">{children}</div>;
}

function CardFooter({ children }) {
  return <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4">{children}</div>;
}

// Usage - clean and readable
<Card>
  <CardHeader>
    <h3 className="text-lg font-semibold">Title</h3>
  </CardHeader>
  <CardBody>
    <p>Content here</p>
  </CardBody>
  <CardFooter>
    <Button>Save</Button>
  </CardFooter>
</Card>
```

---

## The cn() Utility Pattern

### Setup

```typescript
// utils/cn.ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

```bash
pnpm add clsx tailwind-merge
```

### Why Both clsx AND tailwind-merge?

```typescript
// clsx: Handles conditional classes
clsx('base', isActive && 'active', { 'hidden': !visible });
// Result: "base active" or "base hidden"

// tailwind-merge: Resolves Tailwind conflicts
twMerge('bg-red-500 bg-blue-500');
// Result: "bg-blue-500" (last one wins)

// Combined cn(): Best of both
cn('px-4 py-2', isLarge && 'px-8 py-4');
// Result: "px-8 py-4" when isLarge (conflicts resolved)
```

---

## CVA - Class Variance Authority

### Why CVA?

CVA provides type-safe variant management for Tailwind components.

```bash
pnpm add class-variance-authority
```

### Basic Usage

```typescript
// components/ui/Badge.tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/utils/cn';

const badgeVariants = cva(
  // Base styles
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
        success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
        danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        outline: 'border border-current bg-transparent',
      },
      size: {
        sm: 'text-xs px-2 py-0.5',
        md: 'text-sm px-2.5 py-0.5',
        lg: 'text-sm px-3 py-1',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
);

interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, size }), className)} {...props} />
  );
}

// Usage
<Badge variant="success">Active</Badge>
<Badge variant="danger" size="lg">Error</Badge>
```

---

## Responsive Design Patterns

### Mobile-First Navigation

```typescript
function Navigation() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex-shrink-0">
            <span className="text-xl font-bold text-blue-600">Logo</span>
          </div>

          {/* Desktop nav */}
          <div className="hidden md:flex md:items-center md:space-x-8">
            <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">Home</a>
            <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">About</a>
            <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">Contact</a>
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-gray-100"
          >
            <span className="sr-only">Open menu</span>
            {isOpen ? '✕' : '☰'}
          </button>
        </div>
      </div>

      {/* Mobile nav */}
      {isOpen && (
        <div className="md:hidden border-t border-gray-200">
          <div className="px-4 py-3 space-y-2">
            <a href="#" className="block px-3 py-2 rounded-lg hover:bg-gray-100">Home</a>
            <a href="#" className="block px-3 py-2 rounded-lg hover:bg-gray-100">About</a>
            <a href="#" className="block px-3 py-2 rounded-lg hover:bg-gray-100">Contact</a>
          </div>
        </div>
      )}
    </nav>
  );
}
```

### Responsive Card Grid

```typescript
function ProductGrid({ products }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {products.map((product) => (
        <div key={product.id} className="group rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow">
          <div className="aspect-square overflow-hidden">
            <img
              src={product.image}
              alt={product.name}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          </div>
          <div className="p-4">
            <h3 className="font-semibold text-gray-900 truncate">{product.name}</h3>
            <p className="text-sm text-gray-500 mt-1 line-clamp-2">{product.description}</p>
            <p className="text-lg font-bold text-blue-600 mt-2">${product.price}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## Performance Optimization

### PurgeCSS (Automatic in Tailwind)

```
Tailwind automatically removes unused CSS in production builds.

Development: Full Tailwind (~3MB)
Production:  Only used classes (~10-30KB gzipped)

This works because Tailwind scans your content files
for class names and only includes what's used.
```

### Critical Rules for PurgeCSS

```typescript
// ❌ NEVER construct class names dynamically
const size = 'lg';
className={`text-${size}`}  // PurgeCSS can't find this!

// ✅ ALWAYS use complete class names
const sizeMap = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
};
className={sizeMap[size]}  // PurgeCSS finds all three!
```

### Safelist (When You Must Use Dynamic Classes)

```javascript
// tailwind.config.js (v3)
module.exports = {
  safelist: [
    'bg-red-500',
    'bg-green-500',
    'bg-blue-500',
    // Pattern matching
    { pattern: /bg-(red|green|blue)-(100|500|900)/ },
  ],
};
```

---

## Accessibility

### Focus Indicators

```html
<!-- Always provide visible focus indicators -->
<button class="
  focus:outline-none
  focus-visible:ring-2
  focus-visible:ring-blue-500
  focus-visible:ring-offset-2
">
  Accessible button
</button>

<!-- focus-visible: Only shows for keyboard navigation -->
<!-- focus: Shows for both mouse and keyboard -->
```

### Screen Reader Utilities

```html
<!-- Visually hidden but accessible to screen readers -->
<span class="sr-only">Close menu</span>

<!-- Skip to content link -->
<a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-white focus:px-4 focus:py-2 focus:rounded">
  Skip to main content
</a>
```

### Reduced Motion

```html
<!-- Respect user's motion preferences -->
<div class="transition-transform duration-300 motion-reduce:transition-none motion-reduce:transform-none">
  Animated element
</div>
```

---

## Design System Tokens

### Establishing a Token System

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      // Semantic color tokens
      colors: {
        surface: {
          primary: 'var(--surface-primary)',
          secondary: 'var(--surface-secondary)',
          elevated: 'var(--surface-elevated)',
        },
        content: {
          primary: 'var(--content-primary)',
          secondary: 'var(--content-secondary)',
          muted: 'var(--content-muted)',
        },
        interactive: {
          DEFAULT: 'var(--interactive)',
          hover: 'var(--interactive-hover)',
          active: 'var(--interactive-active)',
        },
      },
    },
  },
};
```

```css
/* index.css - Define tokens as CSS custom properties */
:root {
  --surface-primary: #ffffff;
  --surface-secondary: #f9fafb;
  --surface-elevated: #ffffff;
  --content-primary: #111827;
  --content-secondary: #4b5563;
  --content-muted: #9ca3af;
  --interactive: #3b82f6;
  --interactive-hover: #2563eb;
  --interactive-active: #1d4ed8;
}

.dark {
  --surface-primary: #111827;
  --surface-secondary: #1f2937;
  --surface-elevated: #374151;
  --content-primary: #f9fafb;
  --content-secondary: #d1d5db;
  --content-muted: #6b7280;
  --interactive: #60a5fa;
  --interactive-hover: #93c5fd;
  --interactive-active: #3b82f6;
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Consistent Component API

```typescript
// Every UI component should accept className for overrides
interface ComponentProps {
  className?: string;
  children: React.ReactNode;
}

function Component({ className, children }: ComponentProps) {
  return (
    <div className={cn('base-styles', className)}>
      {children}
    </div>
  );
}
```

### Pattern 2: Group Hover/Focus

```html
<!-- Parent hover affects child -->
<div class="group cursor-pointer p-4 rounded-lg hover:bg-gray-50">
  <h3 class="font-semibold group-hover:text-blue-600 transition-colors">Title</h3>
  <p class="text-gray-500">Description</p>
  <span class="opacity-0 group-hover:opacity-100 transition-opacity">→</span>
</div>
```

### Pattern 3: Animation Classes

```html
<!-- Smooth transitions -->
<div class="transition-all duration-200 ease-in-out hover:scale-105 hover:shadow-lg">
  Hover card effect
</div>

<!-- Pulse animation for loading -->
<div class="animate-pulse bg-gray-200 rounded h-4 w-3/4"></div>

<!-- Custom animations -->
<div class="animate-fade-in">Fading in content</div>
```

---

## Common Pitfalls

### Pitfall 1: Overriding Without tailwind-merge

```typescript
// ❌ Parent provides padding, child can't override
<Button className="px-8">  {/* May not work */}

// ✅ Use cn() with tailwind-merge in the component
<button className={cn('px-4', className)}>  {/* px-8 wins */}
```

### Pitfall 2: Using @apply Everywhere

```css
/* ❌ You just recreated traditional CSS with extra steps */
.card { @apply rounded-lg shadow-md p-4 bg-white; }
.card-title { @apply text-xl font-bold text-gray-900; }

/* ✅ @apply is fine for global base styles only */
@layer base {
  body { @apply antialiased; }
}
```

### Pitfall 3: Ignoring the Spacing Scale

```html
<!-- ❌ Inconsistent: mixing arbitrary values -->
<div class="mt-[13px] mb-[7px] p-[22px]">

<!-- ✅ Use the spacing scale for consistency -->
<div class="mt-3 mb-2 p-6">
```

---

## Resources

- **Tailwind CSS Best Practices:** https://tailwindcss.com/docs/reusing-styles
- **Tailwind Merge:** https://github.com/dcastil/tailwind-merge
- **CVA Documentation:** https://cva.style/docs
- **Tailwind CSS IntelliSense (VS Code):** https://marketplace.visualstudio.com/items?itemName=bradlc.vscode-tailwindcss
- **Prettier Plugin Tailwind:** https://github.com/tailwindlabs/prettier-plugin-tailwindcss

---

**Next:** [Part 5.3: CSS & Styling Patterns in React](./05-css-in-react-patterns.md)
