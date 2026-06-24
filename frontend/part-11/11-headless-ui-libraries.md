# Part 11.2: Headless UI Libraries

## What You'll Learn

- Headless vs styled component libraries
- Radix UI primitives for accessible components
- Headless UI for unstyled components
- Building a Dialog, Dropdown, Tooltip, and Popover
- Accessibility guarantees from headless libraries
- When to use headless vs pre-styled libraries

---

## Table of Contents

1. [Headless vs Styled Libraries](#headless-vs-styled-libraries)
2. [Radix UI](#radix-ui)
3. [Headless UI](#headless-ui)
4. [Building a Dialog](#building-a-dialog)
5. [Building a Dropdown Menu](#building-a-dropdown-menu)
6. [Building a Tooltip](#building-a-tooltip)
7. [Building a Select/Combobox](#building-a-selectcombobox)
8. [Comparison & Recommendation](#comparison--recommendation)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Resources](#resources)

---

## Headless vs Styled Libraries

```
Styled Libraries (MUI, Ant Design, Chakra UI):
  ✅ Fast prototyping
  ✅ Pre-built themes
  ❌ Hard to customize deeply
  ❌ Large bundle size
  ❌ "Every app looks the same"

Headless Libraries (Radix, Headless UI, React Aria):
  ✅ Full visual control
  ✅ Accessible by default (WAI-ARIA)
  ✅ Small bundle size
  ✅ Works with ANY styling solution
  ❌ You style everything yourself
  ❌ More initial setup
```

---

## Radix UI

### Installation

```bash
pnpm add @radix-ui/react-dialog
pnpm add @radix-ui/react-dropdown-menu
pnpm add @radix-ui/react-tooltip
pnpm add @radix-ui/react-select
pnpm add @radix-ui/react-popover
pnpm add @radix-ui/react-tabs
```

### Why Radix?

```
1. WAI-ARIA compliant out of the box
2. Keyboard navigation built-in
3. Focus management handled
4. Screen reader support
5. Composable API (compound components)
6. Animation-friendly (data attributes for state)
7. Used by Shadcn/ui under the hood
```

---

## Building a Dialog

```typescript
import * as Dialog from '@radix-ui/react-dialog';

function ConfirmDialog({
  open, onOpenChange, title, description, onConfirm, confirmText = 'Confirm',
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  onConfirm: () => void;
  confirmText?: string;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        {/* Overlay with fade animation */}
        <Dialog.Overlay className="fixed inset-0 bg-black/50 data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />

        {/* Content */}
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-full max-w-md data-[state=open]:animate-scale-in data-[state=closed]:animate-scale-out focus:outline-none">
          <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-white">
            {title}
          </Dialog.Title>
          <Dialog.Description className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {description}
          </Dialog.Description>

          <div className="mt-6 flex justify-end gap-3">
            <Dialog.Close asChild>
              <button className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">
                Cancel
              </button>
            </Dialog.Close>
            <button
              onClick={() => { onConfirm(); onOpenChange(false); }}
              className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              {confirmText}
            </button>
          </div>

          {/* Close button */}
          <Dialog.Close asChild>
            <button className="absolute top-4 right-4 text-gray-400 hover:text-gray-600" aria-label="Close">
              ✕
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

---

## Building a Dropdown Menu

```typescript
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

function UserMenu({ user }: { user: User }) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100">
          <div className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm">
            {user.name.charAt(0)}
          </div>
          <span className="text-sm font-medium">{user.name}</span>
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="min-w-[200px] bg-white dark:bg-gray-800 rounded-lg shadow-lg border p-1 animate-slide-down"
          sideOffset={5}
          align="end"
        >
          <DropdownMenu.Label className="px-3 py-2 text-xs font-medium text-gray-500 uppercase">
            Account
          </DropdownMenu.Label>

          <DropdownMenu.Item className="px-3 py-2 text-sm rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 outline-none focus:bg-gray-100">
            Profile
          </DropdownMenu.Item>

          <DropdownMenu.Item className="px-3 py-2 text-sm rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 outline-none focus:bg-gray-100">
            Settings
          </DropdownMenu.Item>

          <DropdownMenu.Separator className="h-px my-1 bg-gray-200 dark:bg-gray-700" />

          <DropdownMenu.Item className="px-3 py-2 text-sm rounded cursor-pointer text-red-600 hover:bg-red-50 outline-none focus:bg-red-50">
            Sign Out
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
```

---

## Building a Tooltip

```typescript
import * as Tooltip from '@radix-ui/react-tooltip';

function TooltipWrapper({ children, content, side = 'top' }: {
  children: React.ReactNode;
  content: string;
  side?: 'top' | 'right' | 'bottom' | 'left';
}) {
  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side={side}
            sideOffset={5}
            className="bg-gray-900 text-white text-xs px-3 py-1.5 rounded-md shadow-lg animate-fade-in"
          >
            {content}
            <Tooltip.Arrow className="fill-gray-900" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

// Usage
<TooltipWrapper content="Edit this item">
  <button className="p-2 hover:bg-gray-100 rounded">✏️</button>
</TooltipWrapper>
```

---

## Building a Select/Combobox

```typescript
import * as Select from '@radix-ui/react-select';

function CustomSelect({ options, value, onChange, placeholder = 'Select...' }: {
  options: { value: string; label: string }[];
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <Select.Root value={value} onValueChange={onChange}>
      <Select.Trigger className="inline-flex items-center justify-between w-full px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 focus:ring-2 focus:ring-blue-500">
        <Select.Value placeholder={placeholder} />
        <Select.Icon>▼</Select.Icon>
      </Select.Trigger>

      <Select.Portal>
        <Select.Content className="bg-white border rounded-lg shadow-lg overflow-hidden animate-slide-down">
          <Select.Viewport className="p-1">
            {options.map((option) => (
              <Select.Item
                key={option.value}
                value={option.value}
                className="px-3 py-2 text-sm rounded cursor-pointer outline-none hover:bg-blue-50 focus:bg-blue-50 data-[state=checked]:text-blue-600 data-[state=checked]:font-medium"
              >
                <Select.ItemText>{option.label}</Select.ItemText>
                <Select.ItemIndicator className="ml-auto">✓</Select.ItemIndicator>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}
```

---

## Comparison & Recommendation

| Feature | Radix UI | Headless UI | React Aria |
|---------|----------|-------------|------------|
| Framework | React | React, Vue | React |
| Accessibility | Excellent | Excellent | Excellent |
| Component count | 30+ | 10+ | 40+ |
| Bundle size | Small (per component) | Small | Medium |
| Animation support | data attributes | Transition component | CSS states |
| Used by | Shadcn/ui | Tailwind Labs | Adobe Spectrum |
| Learning curve | Low | Low | Medium |
| **Recommendation** | **Best for React + Tailwind** | Good for simpler needs | Best for complex a11y |

---

## Common Patterns & Best Practices

- Install Radix primitives individually (not a monolith)
- Wrap Radix components in your own design system components
- Use `data-[state=open]` attributes for CSS animations
- Always use `asChild` when wrapping custom trigger components
- Shadcn/ui is pre-wrapped Radix — use it for faster setup

---

## Resources

- **Radix UI:** https://www.radix-ui.com/
- **Headless UI:** https://headlessui.com/
- **React Aria:** https://react-spectrum.adobe.com/react-aria/
- **Shadcn/ui (Radix + Tailwind):** https://ui.shadcn.com/
- **WAI-ARIA Practices:** https://www.w3.org/WAI/ARIA/apg/

---

**Next:** [Part 11.3: CSS Component Libraries](./11-css-component-libraries.md)
