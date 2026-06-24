# Part 10.3: TanStack Table Integration

## What You'll Learn

- Integrating TanStack Table with TanStack Query
- Styling tables with Tailwind CSS
- Accessibility features for data tables
- Search integration with debouncing
- Export functionality (CSV/Excel)
- Custom cell renderers for rich content

---

## Table of Contents

1. [TanStack Query Integration](#tanstack-query-integration)
2. [Tailwind Styled Table Component](#tailwind-styled-table-component)
3. [Accessibility](#accessibility)
4. [Search with Debouncing](#search-with-debouncing)
5. [Export Functionality](#export-functionality)
6. [Custom Cell Renderers](#custom-cell-renderers)
7. [Complete Reusable DataTable](#complete-reusable-datatable)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Resources](#resources)

---

## TanStack Query Integration

### Server-Side Table with React Query

```typescript
function UsersTablePage() {
  const [tableState, setTableState] = useState({
    sorting: [] as SortingState,
    pagination: { pageIndex: 0, pageSize: 20 },
    globalFilter: '',
  });

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['users', 'table', tableState],
    queryFn: () => usersApi.list({
      page: tableState.pagination.pageIndex + 1,
      limit: tableState.pagination.pageSize,
      search: tableState.globalFilter,
      sortBy: tableState.sorting[0]?.id,
      sortOrder: tableState.sorting[0]?.desc ? 'desc' : 'asc',
    }),
    placeholderData: keepPreviousData,
  });

  const table = useReactTable({
    data: data?.data ?? [],
    columns,
    rowCount: data?.meta?.total ?? 0,
    state: tableState,
    onSortingChange: (updater) => setTableState(prev => ({
      ...prev,
      sorting: typeof updater === 'function' ? updater(prev.sorting) : updater,
    })),
    onPaginationChange: (updater) => setTableState(prev => ({
      ...prev,
      pagination: typeof updater === 'function' ? updater(prev.pagination) : updater,
    })),
    onGlobalFilterChange: (value) => setTableState(prev => ({
      ...prev,
      globalFilter: value,
      pagination: { ...prev.pagination, pageIndex: 0 },
    })),
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
    manualPagination: true,
    manualFiltering: true,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <DebouncedInput
          value={tableState.globalFilter}
          onChange={(value) => table.setGlobalFilter(value)}
          placeholder="Search users..."
          className="max-w-sm"
        />
        {isFetching && <Spinner size="sm" />}
      </div>

      {isLoading ? <TableSkeleton /> : <StyledTable table={table} />}

      <PaginationControls table={table} />
    </div>
  );
}
```

---

## Tailwind Styled Table Component

```typescript
function StyledTable<T>({ table }: { table: Table<T> }) {
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden shadow-sm">
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className="bg-gray-50 dark:bg-gray-800/50">
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                  className={cn(
                    'px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider',
                    'text-gray-500 dark:text-gray-400',
                    header.column.getCanSort() && 'cursor-pointer select-none hover:text-gray-700'
                  )}
                  style={{ width: header.getSize() !== 150 ? header.getSize() : undefined }}
                >
                  <div className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getIsSorted() === 'asc' && <span>↑</span>}
                    {header.column.getIsSorted() === 'desc' && <span>↓</span>}
                  </div>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {table.getRowModel().rows.length === 0 ? (
            <tr>
              <td
                colSpan={table.getVisibleLeafColumns().length}
                className="text-center py-12 text-gray-500"
              >
                No results found
              </td>
            </tr>
          ) : (
            table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3 text-gray-700 dark:text-gray-300">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Accessibility

```typescript
// Accessible table with proper ARIA attributes
function AccessibleTable<T>({ table, caption }: { table: Table<T>; caption: string }) {
  return (
    <table role="grid" aria-label={caption} className="w-full">
      <caption className="sr-only">{caption}</caption>
      <thead>
        {table.getHeaderGroups().map((headerGroup) => (
          <tr key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <th
                key={header.id}
                scope="col"
                aria-sort={
                  header.column.getIsSorted() === 'asc' ? 'ascending' :
                  header.column.getIsSorted() === 'desc' ? 'descending' : 'none'
                }
                tabIndex={header.column.getCanSort() ? 0 : undefined}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    header.column.getToggleSortingHandler()?.(e);
                  }
                }}
                onClick={header.column.getToggleSortingHandler()}
                className="px-4 py-3 text-left"
              >
                {flexRender(header.column.columnDef.header, header.getContext())}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>{/* ... */}</tbody>
    </table>
  );
}
```

---

## Search with Debouncing

```typescript
function DebouncedInput({
  value: initialValue,
  onChange,
  debounce = 300,
  ...props
}: {
  value: string;
  onChange: (value: string) => void;
  debounce?: number;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'>) {
  const [value, setValue] = useState(initialValue);

  useEffect(() => {
    setValue(initialValue);
  }, [initialValue]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      onChange(value);
    }, debounce);

    return () => clearTimeout(timeout);
  }, [value, debounce, onChange]);

  return (
    <input
      {...props}
      value={value}
      onChange={(e) => setValue(e.target.value)}
      className={cn(
        'px-4 py-2 border border-gray-300 rounded-lg',
        'focus:outline-none focus:ring-2 focus:ring-blue-500',
        'dark:bg-gray-800 dark:border-gray-600 dark:text-white',
        props.className
      )}
    />
  );
}
```

---

## Export Functionality

```typescript
function exportToCSV<T extends Record<string, any>>(
  data: T[],
  columns: { key: string; header: string }[],
  filename: string
) {
  const headers = columns.map(c => c.header).join(',');
  const rows = data.map(row =>
    columns.map(c => {
      const val = row[c.key];
      // Escape commas and quotes
      const str = String(val ?? '');
      return str.includes(',') || str.includes('"') ? `"${str.replace(/"/g, '""')}"` : str;
    }).join(',')
  );

  const csv = [headers, ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

// Usage with table
function ExportButton<T>({ table }: { table: Table<T> }) {
  const handleExport = () => {
    const visibleColumns = table.getVisibleLeafColumns()
      .filter(col => col.id !== 'select' && col.id !== 'actions')
      .map(col => ({ key: col.id, header: String(col.columnDef.header) }));

    const data = table.getFilteredRowModel().rows.map(row => row.original);
    exportToCSV(data, visibleColumns, 'export');
  };

  return (
    <button onClick={handleExport} className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">
      📥 Export CSV
    </button>
  );
}
```

---

## Custom Cell Renderers

```typescript
const columns: ColumnDef<User>[] = [
  // Avatar + name
  {
    accessorKey: 'name',
    header: 'User',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-sm font-semibold">
          {row.original.name.charAt(0)}
        </div>
        <div>
          <p className="font-medium">{row.original.name}</p>
          <p className="text-xs text-gray-500">{row.original.email}</p>
        </div>
      </div>
    ),
  },

  // Status badge
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ getValue }) => {
      const status = getValue<string>();
      const styles = {
        active: 'bg-green-100 text-green-800',
        inactive: 'bg-gray-100 text-gray-600',
        suspended: 'bg-red-100 text-red-800',
      };
      return (
        <span className={cn('px-2 py-1 rounded-full text-xs font-medium', styles[status])}>
          {status}
        </span>
      );
    },
  },

  // Progress bar
  {
    accessorKey: 'progress',
    header: 'Progress',
    cell: ({ getValue }) => {
      const progress = getValue<number>();
      return (
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${progress}%` }} />
          </div>
          <span className="text-xs text-gray-500 w-8">{progress}%</span>
        </div>
      );
    },
  },

  // Date with relative time
  {
    accessorKey: 'createdAt',
    header: 'Created',
    cell: ({ getValue }) => {
      const date = new Date(getValue<string>());
      const relative = getRelativeTime(date);
      return (
        <span title={date.toLocaleString()} className="text-sm text-gray-500">
          {relative}
        </span>
      );
    },
  },
];
```

---

## Complete Reusable DataTable

```typescript
// components/ui/DataTable.tsx
interface DataTableProps<T> {
  columns: ColumnDef<T, any>[];
  data: T[];
  isLoading?: boolean;
  searchPlaceholder?: string;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  enableSearch?: boolean;
  enablePagination?: boolean;
  enableSorting?: boolean;
  enableExport?: boolean;
}

function DataTable<T>({
  columns, data, isLoading, searchPlaceholder = 'Search...',
  emptyMessage = 'No results found', onRowClick,
  enableSearch = true, enablePagination = true,
  enableSorting = true, enableExport = false,
}: DataTableProps<T>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    ...(enableSorting && { getSortedRowModel: getSortedRowModel() }),
    ...(enableSearch && { getFilteredRowModel: getFilteredRowModel() }),
    ...(enablePagination && { getPaginationRowModel: getPaginationRowModel() }),
  });

  if (isLoading) return <TableSkeleton columns={columns.length} />;

  return (
    <div className="space-y-4">
      {(enableSearch || enableExport) && (
        <div className="flex items-center justify-between">
          {enableSearch && (
            <DebouncedInput value={globalFilter} onChange={setGlobalFilter} placeholder={searchPlaceholder} />
          )}
          {enableExport && <ExportButton table={table} />}
        </div>
      )}

      <StyledTable table={table} onRowClick={onRowClick} emptyMessage={emptyMessage} />

      {enablePagination && table.getPageCount() > 1 && <PaginationControls table={table} />}
    </div>
  );
}
```

---

## Common Patterns & Best Practices

### Pattern 1: URL-Synced Table State

```typescript
// Sync table state with URL search params for shareable/bookmarkable tables
const { sort, page, search } = route.useSearch();

const tableState = useMemo(() => ({
  sorting: sort ? [{ id: sort, desc: order === 'desc' }] : [],
  pagination: { pageIndex: (page ?? 1) - 1, pageSize: 20 },
  globalFilter: search ?? '',
}), [sort, page, search, order]);
```

---

## Resources

- **TanStack Table Examples:** https://tanstack.com/table/latest/docs/framework/react/examples
- **TanStack Virtual:** https://tanstack.com/virtual/latest
- **WAI-ARIA Table Patterns:** https://www.w3.org/WAI/ARIA/apg/patterns/table/

---

**Next:** [Part 11.1: Component Design Patterns](../part-11/11-component-design-patterns.md)
