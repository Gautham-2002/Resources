# Part 10.2: TanStack Table Advanced Features

## What You'll Learn

- Row selection (single and multi-select)
- Expandable rows with sub-rows
- Column pinning and visibility toggles
- Grouping and aggregation
- Virtual scrolling for large datasets
- Server-side table operations

---

## Table of Contents

1. [Row Selection](#row-selection)
2. [Expandable Rows](#expandable-rows)
3. [Column Pinning](#column-pinning)
4. [Column Visibility](#column-visibility)
5. [Grouping & Aggregation](#grouping--aggregation)
6. [Virtual Scrolling](#virtual-scrolling)
7. [Server-Side Operations](#server-side-operations)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Resources](#resources)

---

## Row Selection

### Multi-Select with Checkboxes

```typescript
import { type RowSelectionState } from '@tanstack/react-table';

function SelectableTable({ data }: { data: User[] }) {
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  const columns: ColumnDef<User>[] = [
    {
      id: 'select',
      header: ({ table }) => (
        <input
          type="checkbox"
          checked={table.getIsAllRowsSelected()}
          onChange={table.getToggleAllRowsSelectedHandler()}
          className="rounded"
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={row.getIsSelected()}
          onChange={row.getToggleSelectedHandler()}
          className="rounded"
        />
      ),
      size: 40,
    },
    { accessorKey: 'name', header: 'Name' },
    { accessorKey: 'email', header: 'Email' },
  ];

  const table = useReactTable({
    data,
    columns,
    state: { rowSelection },
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    enableRowSelection: true,
  });

  const selectedRows = table.getFilteredSelectedRowModel().rows;

  return (
    <div>
      {/* Bulk actions */}
      {selectedRows.length > 0 && (
        <div className="bg-blue-50 border-b px-4 py-2 flex items-center justify-between">
          <span className="text-sm text-blue-700">
            {selectedRows.length} row(s) selected
          </span>
          <div className="flex gap-2">
            <button onClick={() => handleBulkDelete(selectedRows.map(r => r.original.id))}
              className="text-sm text-red-600 hover:text-red-800">
              Delete Selected
            </button>
            <button onClick={() => handleBulkExport(selectedRows.map(r => r.original))}
              className="text-sm text-blue-600 hover:text-blue-800">
              Export Selected
            </button>
          </div>
        </div>
      )}

      <table>{/* ... render table */}</table>
    </div>
  );
}
```

---

## Expandable Rows

```typescript
import { getExpandedRowModel, type ExpandedState } from '@tanstack/react-table';

interface Order {
  id: string;
  customerName: string;
  total: number;
  items: OrderItem[];
}

function ExpandableTable({ data }: { data: Order[] }) {
  const [expanded, setExpanded] = useState<ExpandedState>({});

  const columns: ColumnDef<Order>[] = [
    {
      id: 'expand',
      header: '',
      cell: ({ row }) => (
        <button
          onClick={row.getToggleExpandedHandler()}
          className="p-1 hover:bg-gray-100 rounded"
        >
          {row.getIsExpanded() ? '▼' : '▶'}
        </button>
      ),
      size: 40,
    },
    { accessorKey: 'customerName', header: 'Customer' },
    {
      accessorKey: 'total',
      header: 'Total',
      cell: ({ getValue }) => `$${getValue<number>().toFixed(2)}`,
    },
  ];

  const table = useReactTable({
    data,
    columns,
    state: { expanded },
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowCanExpand: () => true,
  });

  return (
    <table className="w-full">
      <thead>{/* ... */}</thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <Fragment key={row.id}>
            <tr className="border-b hover:bg-gray-50">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>

            {/* Expanded content */}
            {row.getIsExpanded() && (
              <tr>
                <td colSpan={columns.length} className="bg-gray-50 px-8 py-4">
                  <h4 className="font-medium mb-2">Order Items:</h4>
                  <ul className="space-y-1">
                    {row.original.items.map((item) => (
                      <li key={item.id} className="text-sm text-gray-600">
                        {item.name} × {item.quantity} — ${item.price.toFixed(2)}
                      </li>
                    ))}
                  </ul>
                </td>
              </tr>
            )}
          </Fragment>
        ))}
      </tbody>
    </table>
  );
}
```

---

## Column Pinning

```typescript
import { type ColumnPinningState } from '@tanstack/react-table';

function PinnedColumnsTable({ data }) {
  const [columnPinning, setColumnPinning] = useState<ColumnPinningState>({
    left: ['name'],      // Pin name column to left
    right: ['actions'],  // Pin actions to right
  });

  const table = useReactTable({
    data,
    columns,
    state: { columnPinning },
    onColumnPinningChange: setColumnPinning,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className={cn(
                    'px-4 py-3 text-left bg-gray-50',
                    header.column.getIsPinned() && 'sticky z-10 bg-white shadow-sm',
                    header.column.getIsPinned() === 'left' && 'left-0',
                    header.column.getIsPinned() === 'right' && 'right-0',
                  )}
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        {/* ... body with same pinning styles */}
      </table>
    </div>
  );
}
```

---

## Column Visibility

```typescript
import { type VisibilityState } from '@tanstack/react-table';

function ColumnToggleTable({ data }) {
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  const table = useReactTable({
    data,
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div>
      {/* Column visibility dropdown */}
      <div className="mb-4 flex gap-2 flex-wrap">
        {table.getAllLeafColumns().map((column) => (
          <label key={column.id} className="flex items-center gap-1 text-sm">
            <input
              type="checkbox"
              checked={column.getIsVisible()}
              onChange={column.getToggleVisibilityHandler()}
              className="rounded"
            />
            {column.id}
          </label>
        ))}
      </div>

      <table>{/* ... render only visible columns */}</table>
    </div>
  );
}
```

---

## Virtual Scrolling

```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualTable({ data }: { data: User[] }) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const { rows } = table.getRowModel();
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48, // Estimated row height
    overscan: 10,
  });

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto border rounded-lg">
      <table className="w-full">
        <thead className="sticky top-0 bg-white z-10 shadow-sm">
          {/* ... headers */}
        </thead>
        <tbody>
          <tr style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
            <td colSpan={columns.length} style={{ padding: 0 }}>
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const row = rows[virtualRow.index];
                return (
                  <div
                    key={row.id}
                    className="absolute w-full flex border-b hover:bg-gray-50"
                    style={{
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <div key={cell.id} className="px-4 py-3 flex-1">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </div>
                    ))}
                  </div>
                );
              })}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
```

---

## Server-Side Operations

```typescript
function ServerSideTable() {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 20 });
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

  // Fetch from server with current table state
  const { data, isLoading } = useQuery({
    queryKey: ['users', 'table', { sorting, pagination, columnFilters }],
    queryFn: () => usersApi.list({
      page: pagination.pageIndex + 1,
      limit: pagination.pageSize,
      sortBy: sorting[0]?.id,
      sortOrder: sorting[0]?.desc ? 'desc' : 'asc',
      filters: Object.fromEntries(
        columnFilters.map(f => [f.id, f.value])
      ),
    }),
    placeholderData: keepPreviousData,
  });

  const table = useReactTable({
    data: data?.data ?? [],
    columns,
    rowCount: data?.meta?.total ?? 0,
    state: { sorting, pagination, columnFilters },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,      // Server handles sorting
    manualPagination: true,   // Server handles pagination
    manualFiltering: true,    // Server handles filtering
  });

  if (isLoading) return <TableSkeleton />;

  return (
    <div>
      <table>{/* ... */}</table>
      <PaginationControls table={table} />
    </div>
  );
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Table Skeleton

```typescript
function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="border rounded-lg overflow-hidden animate-pulse">
      <div className="bg-gray-50 px-4 py-3 flex gap-4">
        {Array.from({ length: columns }).map((_, i) => (
          <div key={i} className="h-4 bg-gray-200 rounded flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-4 py-3 flex gap-4 border-t">
          {Array.from({ length: columns }).map((_, j) => (
            <div key={j} className="h-4 bg-gray-100 rounded flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
```

### Pattern 2: Responsive Table

```typescript
// On mobile, show cards instead of table
function ResponsiveTable({ data, columns }) {
  const isMobile = useMediaQuery('(max-width: 768px)');

  if (isMobile) {
    return (
      <div className="space-y-4">
        {data.map((item) => (
          <div key={item.id} className="border rounded-lg p-4">
            <h3 className="font-semibold">{item.name}</h3>
            <p className="text-sm text-gray-500">{item.email}</p>
            <p className="text-sm">{item.role}</p>
          </div>
        ))}
      </div>
    );
  }

  return <DataTable data={data} columns={columns} />;
}
```

---

## Common Pitfalls

### Pitfall 1: Not Using manualPagination for Server Data

```typescript
// ❌ Client pagination on server data = only paginate current page
useReactTable({ data: serverData, getPaginationRowModel: getPaginationRowModel() });

// ✅ Manual pagination for server data
useReactTable({
  data: serverData,
  rowCount: totalFromServer,
  manualPagination: true,
  getCoreRowModel: getCoreRowModel(),
});
```

### Pitfall 2: Not Handling Empty States

```typescript
// ❌ Empty table looks broken
// ✅ Always show a meaningful empty state
{rows.length === 0 && (
  <div className="text-center py-12 text-gray-500">
    No results found. Try adjusting your filters.
  </div>
)}
```

---

## Resources

- **Row Selection:** https://tanstack.com/table/latest/docs/guide/row-selection
- **Expanding:** https://tanstack.com/table/latest/docs/guide/expanding
- **Column Pinning:** https://tanstack.com/table/latest/docs/guide/column-pinning
- **Virtual Scrolling:** https://tanstack.com/virtual/latest

---

**Next:** [Part 10.3: TanStack Table Integration](./10-tanstack-table-integration.md)
