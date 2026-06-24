# Part 5.3: CSS & Styling Patterns in React

## What You'll Learn

- Different CSS approaches in React and their tradeoffs
- CSS Modules for scoped styles
- Styled Components and Emotion (CSS-in-JS)
- Tailwind with component libraries (Shadcn/ui)
- CVA patterns for variant management
- Type-safe styling strategies
- When to use which approach

---

## Table of Contents

1. [CSS Approaches Overview](#css-approaches-overview)
2. [CSS Modules](#css-modules)
3. [CSS-in-JS: Styled Components](#css-in-js-styled-components)
4. [CSS-in-JS: Emotion](#css-in-js-emotion)
5. [Utility CSS: Tailwind](#utility-css-tailwind)
6. [CVA Pattern Deep Dive](#cva-pattern-deep-dive)
7. [Shadcn/ui Component Pattern](#shadcnui-component-pattern)
8. [Comparison & Decision Matrix](#comparison--decision-matrix)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Resources](#resources)

---

## CSS Approaches Overview

```
┌──────────────────────────────────────────────────┐
│              CSS in React Landscape               │
├──────────────────────────────────────────────────┤
│                                                  │
│  Traditional CSS/SCSS                            │
│  └─ Global styles, BEM naming                    │
│                                                  │
│  CSS Modules                                     │
│  └─ Scoped CSS, class name hashing               │
│                                                  │
│  CSS-in-JS (Runtime)                             │
│  ├─ Styled Components                            │
│  └─ Emotion                                      │
│                                                  │
│  CSS-in-JS (Zero Runtime)                        │
│  ├─ Vanilla Extract                              │
│  └─ Linaria                                      │
│                                                  │
│  Utility-First CSS                               │
│  ├─ Tailwind CSS                                 │
│  └─ UnoCSS                                       │
│                                                  │
│  Hybrid (Most popular in 2024-2026)              │
│  └─ Tailwind + CVA + cn()                        │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## CSS Modules

### How It Works

CSS Modules scope your CSS by automatically generating unique class names at build time.

```css
/* Button.module.css */
.button {
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.primary {
  background-color: #3b82f6;
  color: white;
}

.primary:hover {
  background-color: #2563eb;
}

.secondary {
  background-color: #e5e7eb;
  color: #374151;
}
```

```typescript
// Button.tsx
import styles from './Button.module.css';

interface ButtonProps {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
}

function Button({ variant = 'primary', children }: ButtonProps) {
  return (
    <button className={`${styles.button} ${styles[variant]}`}>
      {children}
    </button>
  );
}

// Rendered HTML: <button class="Button_button_x3k2j Button_primary_a8f3d">
```

### Pros & Cons

```
✅ Pros:
- Zero runtime cost (compile-time only)
- True CSS (full feature support)
- Scoped by default (no conflicts)
- Works with any CSS preprocessor (SCSS, Less)
- Native Vite support
- Great for teams familiar with CSS

❌ Cons:
- Context switching between .tsx and .module.css files
- No dynamic styles based on props (without workarounds)
- Class name composition can be verbose
- No theming system built-in
```

---

## CSS-in-JS: Styled Components

### Basic Usage

```typescript
import styled from 'styled-components';

const Button = styled.button<{ $variant?: 'primary' | 'secondary' }>`
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
  border: none;

  ${({ $variant }) =>
    $variant === 'primary'
      ? `
    background-color: #3b82f6;
    color: white;
    &:hover { background-color: #2563eb; }
  `
      : `
    background-color: #e5e7eb;
    color: #374151;
    &:hover { background-color: #d1d5db; }
  `}
`;

// Usage
<Button $variant="primary">Click me</Button>
```

### Pros & Cons

```
✅ Pros:
- Dynamic styles based on props
- Co-located with component (no file switching)
- Automatic vendor prefixing
- Theming support built-in
- Component-level scoping

❌ Cons:
- Runtime cost (CSS generated at runtime)
- Bundle size increase (~12KB)
- SSR complexity (requires extra setup)
- Performance concerns with many dynamic styles
- Moving away from industry trend (2024-2026)
```

---

## CSS-in-JS: Emotion

### Usage

```typescript
/** @jsxImportSource @emotion/react */
import { css } from '@emotion/react';
import styled from '@emotion/styled';

// Option 1: css prop
function Button({ variant = 'primary', children }) {
  return (
    <button
      css={css`
        padding: 8px 16px;
        border-radius: 4px;
        background: ${variant === 'primary' ? '#3b82f6' : '#e5e7eb'};
        color: ${variant === 'primary' ? 'white' : '#374151'};
      `}
    >
      {children}
    </button>
  );
}

// Option 2: styled (same as styled-components API)
const StyledButton = styled.button`
  padding: 8px 16px;
`;
```

---

## Utility CSS: Tailwind

### The Modern Standard (2024-2026)

```typescript
// The industry has largely settled on Tailwind + cn() + CVA

import { cn } from '@/utils/cn';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
}

function Button({ variant = 'primary', className, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        'px-4 py-2 rounded font-semibold transition-colors',
        variant === 'primary' && 'bg-blue-600 text-white hover:bg-blue-700',
        variant === 'secondary' && 'bg-gray-200 text-gray-800 hover:bg-gray-300',
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
```

---

## CVA Pattern Deep Dive

### Complete Component with CVA

```typescript
// components/ui/Alert.tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/utils/cn';

const alertVariants = cva(
  // Base styles
  'relative w-full rounded-lg border p-4 flex items-start gap-3',
  {
    variants: {
      variant: {
        info: 'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-950 dark:border-blue-800 dark:text-blue-200',
        success: 'bg-green-50 border-green-200 text-green-800 dark:bg-green-950 dark:border-green-800 dark:text-green-200',
        warning: 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-950 dark:border-yellow-800 dark:text-yellow-200',
        error: 'bg-red-50 border-red-200 text-red-800 dark:bg-red-950 dark:border-red-800 dark:text-red-200',
      },
      size: {
        sm: 'text-sm p-3',
        md: 'text-sm p-4',
        lg: 'text-base p-5',
      },
      dismissible: {
        true: 'pr-10',
        false: '',
      },
    },
    compoundVariants: [
      // When both variant and size match, apply these
      {
        variant: 'error',
        size: 'lg',
        className: 'border-2', // Extra thick border for large errors
      },
    ],
    defaultVariants: {
      variant: 'info',
      size: 'md',
      dismissible: false,
    },
  }
);

interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  title?: string;
  onDismiss?: () => void;
}

function Alert({ className, variant, size, dismissible, title, children, onDismiss, ...props }: AlertProps) {
  return (
    <div
      role="alert"
      className={cn(alertVariants({ variant, size, dismissible }), className)}
      {...props}
    >
      <div className="flex-1">
        {title && <p className="font-semibold mb-1">{title}</p>}
        <div>{children}</div>
      </div>
      {dismissible && onDismiss && (
        <button
          onClick={onDismiss}
          className="absolute top-4 right-4 opacity-70 hover:opacity-100"
          aria-label="Dismiss"
        >
          ✕
        </button>
      )}
    </div>
  );
}

// Usage
<Alert variant="error" title="Error" dismissible onDismiss={() => {}}>
  Something went wrong. Please try again.
</Alert>
```

---

## Shadcn/ui Component Pattern

### Philosophy

Shadcn/ui is NOT a component library — it's a collection of re-usable components that you copy into your project and own.

```
Traditional library: npm install → import → use
  ❌ Can't customize internals
  ❌ Version lock-in
  ❌ Bundle size overhead

Shadcn/ui: Copy → paste → customize → own
  ✅ Full control over every line
  ✅ No dependency
  ✅ Customize everything
  ✅ Uses Tailwind + CVA + Radix
```

### How It Works

```bash
# Initialize shadcn/ui
pnpm dlx shadcn@latest init

# Add components you need
pnpm dlx shadcn@latest add button
pnpm dlx shadcn@latest add input
pnpm dlx shadcn@latest add dialog
```

This creates files in your project:

```typescript
// components/ui/button.tsx (auto-generated, you OWN this)
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

// You can modify ANY of this!
```

---

## Comparison & Decision Matrix

| Feature | CSS Modules | Styled Components | Tailwind + CVA |
|---------|-------------|-------------------|----------------|
| Runtime cost | None | Yes (~12KB) | None |
| Learning curve | Low | Medium | Medium |
| Dynamic styles | Limited | Excellent | Good (via cn()) |
| TypeScript support | Weak | Good | Excellent (CVA) |
| SSR support | Native | Extra setup | Native |
| Bundle size | Minimal | +12KB | ~10-30KB CSS |
| Industry trend (2026) | Stable | Declining | Growing |
| Theming | Manual | Built-in | CSS variables |
| DX (Developer Experience) | Good | Good | Excellent |

### Recommendation

```
For new React projects in 2024-2026:
→ Tailwind CSS + cn() + CVA + Shadcn/ui pattern

Why?
1. Zero runtime CSS (best performance)
2. Type-safe variants with CVA
3. Industry standard tooling
4. Excellent DX with IntelliSense
5. Design system consistency
6. Easy dark mode / theming
7. Massive community and ecosystem
```

---

## Common Patterns & Best Practices

### Pattern 1: Component Style API

```typescript
// Every styled component should accept:
// 1. className - for overrides
// 2. variant - for preset styles
// 3. size - for sizing
// 4. Standard HTML attributes via ...props

interface ComponentProps extends React.HTMLAttributes<HTMLElement> {
  variant?: 'default' | 'primary';
  size?: 'sm' | 'md' | 'lg';
}
```

### Pattern 2: Semantic Color Tokens

```css
/* Don't use raw colors in components */

/* ❌ Bad */
.button { background: #3b82f6; }

/* ✅ Good - semantic tokens */
.button { background: var(--color-interactive); }
```

### Pattern 3: Responsive Variants with CVA

```typescript
// Use Tailwind responsive prefixes inside CVA
const containerVariants = cva('mx-auto px-4', {
  variants: {
    maxWidth: {
      sm: 'max-w-screen-sm',
      md: 'max-w-screen-md',
      lg: 'max-w-screen-lg',
      xl: 'max-w-screen-xl',
      full: 'max-w-full',
    },
  },
  defaultVariants: {
    maxWidth: 'lg',
  },
});
```

---

## Common Pitfalls

### Pitfall 1: Mixing CSS Approaches

```typescript
// ❌ Don't mix CSS-in-JS and Tailwind in the same project
<StyledButton className="mt-4 px-8" />  // Confusing!

// ✅ Pick one approach and stick with it
```

### Pitfall 2: Not Using CSS Variables for Theming

```typescript
// ❌ Hardcoded colors everywhere
<div className="bg-[#1a1a2e] text-[#e8e8e8]">

// ✅ Use CSS variables or Tailwind theme colors
<div className="bg-surface-primary text-content-primary">
```

### Pitfall 3: Over-engineering Simple Styles

```typescript
// ❌ Creating a CVA variant for one-off styles
const spacerVariants = cva('', { variants: { size: { sm: 'h-2', md: 'h-4' } } });

// ✅ Just use the utility class directly
<div className="h-4" />
```

---

## Resources

- **CSS Modules in Vite:** https://vitejs.dev/guide/features.html#css-modules
- **Styled Components:** https://styled-components.com/
- **Emotion:** https://emotion.sh/
- **Tailwind CSS:** https://tailwindcss.com/
- **CVA (Class Variance Authority):** https://cva.style/docs
- **Shadcn/ui:** https://ui.shadcn.com/
- **Vanilla Extract:** https://vanilla-extract.style/
- **Josh Comeau's CSS Guide:** https://www.joshwcomeau.com/css/

---

**Next:** [Part 6.1: Zod Fundamentals](../part-06/06-zod-fundamentals.md) - Schema validation for TypeScript
