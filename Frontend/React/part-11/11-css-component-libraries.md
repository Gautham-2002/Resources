# Part 11.3: CSS Component Libraries

## What You'll Learn

- Overview of popular CSS/styled component libraries
- When to use pre-styled vs headless
- Shadcn/ui deep dive (Radix + Tailwind)
- MUI, Ant Design, Chakra UI comparison
- Library selection criteria
- Migration strategies

---

## Table of Contents

1. [Library Landscape](#library-landscape)
2. [Shadcn/ui](#shadcnui)
3. [Material UI (MUI)](#material-ui-mui)
4. [Ant Design](#ant-design)
5. [Chakra UI](#chakra-ui)
6. [DaisyUI](#daisyui)
7. [Decision Matrix](#decision-matrix)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Resources](#resources)

---

## Library Landscape

```
┌─────────────────────────────────────────────────┐
│            Component Library Spectrum            │
├─────────────────────────────────────────────────┤
│                                                 │
│  Full Control ←──────────────────→ Full Styled  │
│                                                 │
│  Vanilla CSS    Tailwind    Shadcn   Chakra  MUI│
│  CSS Modules    + Radix     /ui      UI         │
│  Headless UI                        Ant Design  │
│                                                 │
│  You style      You own     Pre-styled          │
│  everything     components  components          │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Shadcn/ui

### The Modern Standard (2024-2026)

Shadcn/ui is the most recommended approach for new React projects. It's not a library — it's a **component collection** you copy into your project.

```bash
# Setup
pnpm dlx shadcn@latest init

# Add components as needed
pnpm dlx shadcn@latest add button input card dialog table
```

### Why Shadcn/ui?

```
1. NOT a dependency (no npm install)
2. Copy into YOUR project → full ownership
3. Built on Radix UI (accessible)
4. Styled with Tailwind CSS
5. Variants with CVA
6. Fully customizable
7. TypeScript first
8. Growing ecosystem of extensions
```

### Theme Customization

```css
/* globals.css — Customize via CSS variables */
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --radius: 0.5rem;
  }
  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 47.4% 11.2%;
  }
}
```

---

## Material UI (MUI)

```bash
pnpm add @mui/material @emotion/react @emotion/styled
```

### Pros & Cons

```
✅ Largest React UI library
✅ Material Design system
✅ Extensive component set (100+)
✅ Strong TypeScript support
✅ Large community

❌ Large bundle size (~200KB+)
❌ Opinionated Material Design style
❌ Complex theming overrides
❌ Emotion runtime cost
❌ "Every MUI app looks the same"
```

### Quick Example

```typescript
import { Button, TextField, Card, CardContent } from '@mui/material';

function MUIExample() {
  return (
    <Card sx={{ maxWidth: 400, mx: 'auto', mt: 4 }}>
      <CardContent>
        <TextField label="Email" fullWidth margin="normal" />
        <TextField label="Password" type="password" fullWidth margin="normal" />
        <Button variant="contained" fullWidth sx={{ mt: 2 }}>
          Sign In
        </Button>
      </CardContent>
    </Card>
  );
}
```

---

## Ant Design

```bash
pnpm add antd
```

### Pros & Cons

```
✅ Enterprise-grade components
✅ Excellent table, form, and data display
✅ Built-in i18n
✅ Strong TypeScript support

❌ Very opinionated design
❌ Large bundle (even with tree-shaking)
❌ Chinese-centric community (docs sometimes lag)
❌ Hard to override styles
```

---

## Chakra UI

```bash
pnpm add @chakra-ui/react @emotion/react @emotion/styled framer-motion
```

### Pros & Cons

```
✅ Composable component API
✅ Built-in dark mode
✅ Style props (like Tailwind but in JSX)
✅ Good accessibility

❌ Runtime CSS (Emotion)
❌ Requires framer-motion (~25KB)
❌ Smaller component set than MUI
❌ v3 migration disrupted ecosystem
```

---

## DaisyUI

```bash
pnpm add -D daisyui
```

### What Is It?

DaisyUI is a Tailwind CSS plugin that provides pre-styled component classes.

```html
<!-- DaisyUI: Semantic class names backed by Tailwind -->
<button class="btn btn-primary">Click me</button>
<div class="card bg-base-100 shadow-xl">
  <div class="card-body">
    <h2 class="card-title">Title</h2>
    <p>Content</p>
  </div>
</div>
```

### Pros & Cons

```
✅ Zero JavaScript (CSS only)
✅ 30+ themes built-in
✅ Tiny bundle (just CSS classes)
✅ Works with any framework
✅ Easy to customize

❌ No JS behavior (no dropdown logic, etc.)
❌ Less control than pure Tailwind
❌ Need to combine with Radix/Headless for interactive components
```

---

## Decision Matrix

| Criteria | Shadcn/ui | MUI | Ant Design | Chakra UI | DaisyUI |
|----------|-----------|-----|------------|-----------|---------|
| Bundle size | Minimal | Large | Large | Medium | Tiny |
| Runtime CSS | No | Yes | Partial | Yes | No |
| Customization | Full | Hard | Hard | Good | Good |
| Accessibility | Excellent (Radix) | Good | Good | Good | Manual |
| Components | 40+ | 100+ | 80+ | 60+ | 50+ |
| TypeScript | Excellent | Excellent | Excellent | Good | N/A |
| Design flexibility | Full | Low | Low | Medium | Medium |
| Learning curve | Low | Medium | Medium | Low | Very Low |
| **Best for** | **Custom designs** | Enterprise | Enterprise | Rapid MVP | Simple sites |

### Recommendation

```
For most new React projects in 2024-2026:
→ Shadcn/ui + Radix UI + Tailwind CSS

Why?
1. Zero runtime CSS overhead
2. Full design control
3. Accessible by default
4. You own the code (no dependency lock-in)
5. Industry momentum and community growth
```

---

## Common Patterns & Best Practices

### Pattern 1: Start with Shadcn/ui, Customize Later

```bash
# Start fast with pre-built components
pnpm dlx shadcn@latest add button input card dialog table select

# Then customize the generated files to match your design
# components/ui/button.tsx — modify styles, add variants
```

### Pattern 2: Don't Mix Libraries

```typescript
// ❌ MUI Button + Chakra Input + Shadcn Card
// Inconsistent styles, multiple runtime costs, larger bundle

// ✅ Pick ONE library and commit to it
```

### Pattern 3: Extract Shared Components Early

```
src/
  components/
    ui/          # Base UI components (from Shadcn/ui or custom)
      button.tsx
      input.tsx
      card.tsx
    shared/      # Domain-agnostic composed components
      DataTable.tsx
      SearchInput.tsx
      ConfirmDialog.tsx
    features/    # Feature-specific components
      users/
      products/
```

---

## Resources

- **Shadcn/ui:** https://ui.shadcn.com/
- **Material UI:** https://mui.com/
- **Ant Design:** https://ant.design/
- **Chakra UI:** https://chakra-ui.com/
- **DaisyUI:** https://daisyui.com/
- **Radix UI:** https://www.radix-ui.com/

---

**Next:** [Part 12.1: Rendering Strategies Overview](../part-12/12-rendering-strategies-overview.md)
