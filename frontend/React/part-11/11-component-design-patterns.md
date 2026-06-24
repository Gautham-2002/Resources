# Part 11.1: Component Design Patterns

## What You'll Learn

- Compound component pattern
- Render props and children as function
- Polymorphic components (as prop)
- Controlled vs uncontrolled components
- Composition over configuration
- Provider pattern for shared state

---

## Table of Contents

1. [Compound Components](#compound-components)
2. [Render Props](#render-props)
3. [Polymorphic Components](#polymorphic-components)
4. [Controlled vs Uncontrolled](#controlled-vs-uncontrolled)
5. [Composition Pattern](#composition-pattern)
6. [Provider Pattern](#provider-pattern)
7. [Slot Pattern](#slot-pattern)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Resources](#resources)

---

## Compound Components

### Concept

Compound components share implicit state via context, allowing flexible composition.

```typescript
// Context for shared state
interface AccordionContextValue {
  openItems: Set<string>;
  toggle: (id: string) => void;
}

const AccordionContext = createContext<AccordionContextValue | null>(null);

function useAccordionContext() {
  const ctx = useContext(AccordionContext);
  if (!ctx) throw new Error('Must be used within Accordion');
  return ctx;
}

// Parent component
function Accordion({ children, defaultOpen = [] }: {
  children: React.ReactNode;
  defaultOpen?: string[];
}) {
  const [openItems, setOpenItems] = useState(new Set(defaultOpen));

  const toggle = useCallback((id: string) => {
    setOpenItems(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  return (
    <AccordionContext.Provider value={{ openItems, toggle }}>
      <div className="divide-y border rounded-lg">{children}</div>
    </AccordionContext.Provider>
  );
}

// Child components
function AccordionItem({ id, children }: { id: string; children: React.ReactNode }) {
  return <div>{children}</div>;
}

function AccordionTrigger({ id, children }: { id: string; children: React.ReactNode }) {
  const { openItems, toggle } = useAccordionContext();
  const isOpen = openItems.has(id);

  return (
    <button
      onClick={() => toggle(id)}
      className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50"
      aria-expanded={isOpen}
    >
      {children}
      <span className={cn('transition-transform', isOpen && 'rotate-180')}>▼</span>
    </button>
  );
}

function AccordionContent({ id, children }: { id: string; children: React.ReactNode }) {
  const { openItems } = useAccordionContext();
  if (!openItems.has(id)) return null;
  return <div className="px-4 py-3">{children}</div>;
}

// Attach sub-components
Accordion.Item = AccordionItem;
Accordion.Trigger = AccordionTrigger;
Accordion.Content = AccordionContent;

// Usage — clean, flexible API
<Accordion defaultOpen={['faq-1']}>
  <Accordion.Item id="faq-1">
    <Accordion.Trigger id="faq-1">What is React?</Accordion.Trigger>
    <Accordion.Content id="faq-1">
      React is a JavaScript library for building UIs.
    </Accordion.Content>
  </Accordion.Item>
  <Accordion.Item id="faq-2">
    <Accordion.Trigger id="faq-2">Why TanStack?</Accordion.Trigger>
    <Accordion.Content id="faq-2">
      Type-safe, headless, and powerful.
    </Accordion.Content>
  </Accordion.Item>
</Accordion>
```

---

## Render Props

```typescript
// Data fetching with render props
interface FetchProps<T> {
  url: string;
  children: (state: { data: T | null; isLoading: boolean; error: Error | null }) => React.ReactNode;
}

function Fetch<T>({ url, children }: FetchProps<T>) {
  const { data, isLoading, error } = useQuery({
    queryKey: [url],
    queryFn: () => fetch(url).then(r => r.json()),
  });

  return <>{children({ data: data ?? null, isLoading, error: error as Error | null })}</>;
}

// Usage
<Fetch<User[]> url="/api/users">
  {({ data, isLoading, error }) => {
    if (isLoading) return <Spinner />;
    if (error) return <Error message={error.message} />;
    return <UserList users={data!} />;
  }}
</Fetch>
```

---

## Polymorphic Components

### The "as" Prop Pattern

```typescript
type PolymorphicRef<C extends React.ElementType> = React.ComponentPropsWithRef<C>['ref'];

type PolymorphicProps<C extends React.ElementType, Props = {}> = Props & {
  as?: C;
} & Omit<React.ComponentPropsWithoutRef<C>, keyof Props | 'as'>;

// Usage: Button that can render as <button>, <a>, or any element
interface ButtonBaseProps {
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
}

function Button<C extends React.ElementType = 'button'>({
  as,
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}: PolymorphicProps<C, ButtonBaseProps>) {
  const Component = as || 'button';

  return (
    <Component
      className={cn(
        'inline-flex items-center justify-center rounded-lg font-medium',
        variant === 'primary' && 'bg-blue-600 text-white hover:bg-blue-700',
        variant === 'secondary' && 'bg-gray-100 text-gray-800 hover:bg-gray-200',
        size === 'sm' && 'px-3 py-1.5 text-sm',
        size === 'md' && 'px-4 py-2 text-sm',
        size === 'lg' && 'px-6 py-3 text-base',
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}

// Renders as <button>
<Button onClick={handleClick}>Click me</Button>

// Renders as <a>
<Button as="a" href="/about">About</Button>

// Renders as Link (router component)
<Button as={Link} to="/dashboard">Dashboard</Button>
```

---

## Controlled vs Uncontrolled

```typescript
// Support both controlled and uncontrolled usage
interface ToggleProps {
  defaultChecked?: boolean;     // Uncontrolled
  checked?: boolean;            // Controlled
  onChange?: (checked: boolean) => void;
}

function Toggle({ defaultChecked = false, checked: controlledChecked, onChange }: ToggleProps) {
  const [internalChecked, setInternalChecked] = useState(defaultChecked);

  // Use controlled value if provided, otherwise internal
  const isChecked = controlledChecked !== undefined ? controlledChecked : internalChecked;

  const handleToggle = () => {
    const newValue = !isChecked;
    setInternalChecked(newValue);
    onChange?.(newValue);
  };

  return (
    <button
      role="switch"
      aria-checked={isChecked}
      onClick={handleToggle}
      className={cn(
        'relative w-11 h-6 rounded-full transition-colors',
        isChecked ? 'bg-blue-600' : 'bg-gray-300'
      )}
    >
      <span className={cn(
        'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform',
        isChecked && 'translate-x-5'
      )} />
    </button>
  );
}

// Uncontrolled
<Toggle defaultChecked={true} onChange={(v) => console.log(v)} />

// Controlled
<Toggle checked={isDark} onChange={setIsDark} />
```

---

## Composition Pattern

```typescript
// Prefer composition over configuration

// ❌ Configuration-heavy (inflexible)
<Modal
  title="Delete User"
  description="Are you sure?"
  confirmText="Delete"
  cancelText="Cancel"
  onConfirm={handleDelete}
  onCancel={handleCancel}
  icon="warning"
  variant="danger"
/>

// ✅ Composition (flexible)
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Delete User</DialogTitle>
      <DialogDescription>
        Are you sure? This action cannot be undone.
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="secondary" onClick={() => setIsOpen(false)}>Cancel</Button>
      <Button variant="danger" onClick={handleDelete}>Delete</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

---

## Provider Pattern

```typescript
// Toast notification system using provider pattern
interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (message: string, type?: Toast['type']) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = crypto.randomUUID();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => removeToast(id), 5000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map(toast => (
          <div key={toast.id} className={cn(
            'px-4 py-3 rounded-lg shadow-lg text-white text-sm animate-slide-up',
            toast.type === 'success' && 'bg-green-600',
            toast.type === 'error' && 'bg-red-600',
            toast.type === 'info' && 'bg-blue-600',
          )}>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// Usage
const { addToast } = useToast();
addToast('User created successfully!', 'success');
```

---

## Slot Pattern

```typescript
// Allow custom rendering in specific "slots"
interface CardProps {
  header?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
}

function Card({ header, footer, children }: CardProps) {
  return (
    <div className="border rounded-xl overflow-hidden">
      {header && <div className="px-6 py-4 border-b bg-gray-50">{header}</div>}
      <div className="px-6 py-4">{children}</div>
      {footer && <div className="px-6 py-4 border-t bg-gray-50">{footer}</div>}
    </div>
  );
}

<Card
  header={<h3 className="font-semibold">User Profile</h3>}
  footer={<Button>Save Changes</Button>}
>
  <p>Card content here</p>
</Card>
```

---

## Common Patterns & Best Practices

- Always accept `className` for style overrides
- Use `forwardRef` for DOM-wrapping components
- Support both controlled and uncontrolled modes
- Prefer composition over configuration props
- Use context for implicitly shared state

---

## Common Pitfalls

### Pitfall 1: Prop Drilling Instead of Composition

```typescript
// ❌ Too many props
<Table data={d} columns={c} onSort={s} onFilter={f} onPaginate={p} renderRow={r} />

// ✅ Compose
<Table data={d} columns={c}>
  <TableToolbar onFilter={f} />
  <TableBody renderRow={r} />
  <TablePagination onPaginate={p} />
</Table>
```

---

## Resources

- **React Patterns:** https://reactpatterns.com/
- **Compound Components:** https://kentcdodds.com/blog/compound-components-with-react-hooks
- **Polymorphic Components:** https://www.benmvp.com/blog/polymorphic-react-components-typescript/

---

**Next:** [Part 11.2: Headless UI Libraries](./11-headless-ui-libraries.md)
