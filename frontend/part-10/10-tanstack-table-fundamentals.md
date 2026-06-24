# Part 10.1: TanStack Table Fundamentals

## What You'll Learn

- Headless UI philosophy and why it matters
- useReactTable hook and setup
- Column definitions and types
- Row rendering and data binding
- Sorting, filtering, and pagination
- Basic table styling with Tailwind

---

## Table of Contents

1. [Why Headless Tables](#why-headless-tables)
2. [Setup & Installation](#setup--installation)
3. [Basic Table](#basic-table)
4. [Column Definitions](#column-definitions)
5. [Sorting](#sorting)
6. [Filtering](#filtering)
7. [Pagination](#pagination)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Resources](#resources)

---

## Why Headless Tables

```
Traditional table libraries: Give you pre-styled components
  ❌ Hard to customize
  ❌ Fight against default styles
  ❌ Bundle unused features

Headless tables: Give you logic, YOU provide the UI
  ✅ Full control over rendering
  ✅ Use YOUR design system
  ✅ Only include what you need
  ✅ Accessible by design
```

---

## Setup & Installation

```bash
pnpm add @tanstack/react-table
```

---

## Basic Table

```typescript
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from '@tanstack/react-table';

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'inactive';
}

const columns: ColumnDef<User>[] = [
  { accessorKey: 'name', header: 'Name' },
  { accessorKey: 'email', header: 'Email' },
  { accessorKey: 'role', header: 'Role' },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ getValue }) => {
      const status = getValue<string>();
      return (
        <span className={cn(
          'px-2 py-1 rounded-full text-xs font-medium',
          status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
        )}>
          {status}
        </span>
      );
    },
  },
];

function UsersTable({ data }: { data: User[] }) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 dark:bg-gray-800">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id} className="px-4 py-3 text-left text-sm font-semibold text-gray-600">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y">
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3 text-sm">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Column Definitions

```typescript
const columns: ColumnDef<User>[] = [
  // Simple accessor
  { accessorKey: 'name', header: 'Name' },

  // Custom header
  {
    accessorKey: 'email',
    header: () => <span className="flex items-center gap-1">📧 Email</span>,
  },

  // Computed/formatted cell
  {
    accessorKey: 'createdAt',
    header: 'Joined',
    cell: ({ getValue }) => new Date(getValue<string>()).toLocaleDateString(),
  },

  // Accessor function (for nested/computed data)
  {
    accessorFn: (row) => `${row.firstName} ${row.lastName}`,
    id: 'fullName',
    header: 'Full Name',
  },

  // Actions column
  {
    id: 'actions',
    header: '',
    cell: ({ row }) => (
      <div className="flex gap-2">
        <button onClick={() => handleEdit(row.original)} className="text-blue-600 hover:underline">
          Edit
        </button>
        <button onClick={() => handleDelete(row.original.id)} className="text-red-600 hover:underline">
          Delete
        </button>
      </div>
    ),
  },
];
```

---

## Sorting

```typescript
import { getSortedRowModel, type SortingState } from '@tanstack/react-table';

function SortableTable({ data }: { data: User[] }) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <table>
      <thead>
        {table.getHeaderGroups().map((headerGroup) => (
          <tr key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <th
                key={header.id}
                onClick={header.column.getToggleSortingHandler()}
                className={cn('px-4 py-3 text-left cursor-pointer select-none hover:bg-gray-100',
                  header.column.getCanSort() && 'cursor-pointer'
                )}
              >
                <div className="flex items-center gap-1">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {header.column.getIsSorted() === 'asc' && ' ↑'}
                  {header.column.getIsSorted() === 'desc' && ' ↓'}
                </div>
              </th>
            ))}
          </tr>
        ))}
      </thead>
      {/* ... body */}
    </table>
  );
}
```

---

## Filtering

```typescript
import { getFilteredRowModel, type ColumnFiltersState } from '@tanstack/react-table';

function FilterableTable({ data }: { data: User[] }) {
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const table = useReactTable({
    data,
    columns,
    state: { columnFilters, globalFilter },
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div>
      {/* Global search */}
      <input
        value={globalFilter}
        onChange={(e) => setGlobalFilter(e.target.value)}
        placeholder="Search all columns..."
        className="mb-4 px-4 py-2 border rounded-lg w-full max-w-sm"
      />

      {/* Per-column filter */}
      <input
        value={(table.getColumn('name')?.getFilterValue() as string) ?? ''}
        onChange={(e) => table.getColumn('name')?.setFilterValue(e.target.value)}
        placeholder="Filter by name..."
        className="mb-4 px-4 py-2 border rounded-lg"
      />

      {/* Table */}
      <table>{/* ... */}</table>
    </div>
  );
}
```

---

## Pagination

```typescript
import { getPaginationRowModel } from '@tanstack/react-table';

function PaginatedTable({ data }: { data: User[] }) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } },
  });

  return (
    <div>
      <table>{/* ... render rows from table.getRowModel() */}</table>

      {/* Pagination controls */}
      <div className="flex items-center justify-between px-4 py-3 border-t">
        <div className="text-sm text-gray-500">
          Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
          {' · '}
          {table.getFilteredRowModel().rows.length} total rows
        </div>

        <div className="flex gap-2">
          <button onClick={() => table.firstPage()} disabled={!table.getCanPreviousPage()}>
            ««
          </button>
          <button onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>
            ‹
          </button>
          <button onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
            ›
          </button>
          <button onClick={() => table.lastPage()} disabled={!table.getCanNextPage()}>
            »»
          </button>
        </div>

        <select
          value={table.getState().pagination.pageSize}
          onChange={(e) => table.setPageSize(Number(e.target.value))}
          className="border rounded px-2 py-1 text-sm"
        >
          {[10, 20, 50, 100].map((size) => (
            <option key={size} value={size}>Show {size}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Reusable DataTable Component

```typescript
interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T, any>[];
  isLoading?: boolean;
  pagination?: boolean;
  sorting?: boolean;
  filtering?: boolean;
}

function DataTable<T>({ data, columns, isLoading, pagination = true }: DataTableProps<T>) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    ...(pagination && { getPaginationRowModel: getPaginationRowModel() }),
  });

  if (isLoading) return <TableSkeleton columns={columns.length} />;

  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full">{/* ... */}</table>
      {pagination && <PaginationControls table={table} />}
    </div>
  );
}
```

### Pattern 2: Empty State

```typescript
{table.getRowModel().rows.length === 0 ? (
  <tr>
    <td colSpan={columns.length} className="text-center py-12">
      <p className="text-gray-500">No data found</p>
    </td>
  </tr>
) : (
  table.getRowModel().rows.map((row) => (/* ... */))
)}
```

---

## Common Pitfalls

### Pitfall 1: Unstable Column Definitions

```typescript
// ❌ New array every render → infinite re-renders
function Table() {
  const columns = [/* ... */]; // Created every render!
  const table = useReactTable({ columns });
}

// ✅ Memoize or define outside component
const columns: ColumnDef<User>[] = [/* ... */]; // Module-level

// Or with useMemo
const columns = useMemo(() => [/* ... */], []);
```

### Pitfall 2: Mutating Data Directly

```typescript
// ❌ Mutating data breaks React
data[0].name = 'New Name';

// ✅ Create new reference
setData(prev => prev.map(item =>
  item.id === id ? { ...item, name: 'New Name' } : item
));
```

---

## Resources

- **TanStack Table Documentation:** https://tanstack.com/table/latest
- **Column Definitions:** https://tanstack.com/table/latest/docs/guide/column-defs
- **Sorting Guide:** https://tanstack.com/table/latest/docs/guide/sorting
- **Examples:** https://tanstack.com/table/latest/docs/framework/react/examples

---

**Next:** [Part 10.2: TanStack Table Advanced Features](./10-tanstack-table-advanced.md)
