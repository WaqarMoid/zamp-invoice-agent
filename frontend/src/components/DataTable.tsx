import React from "react";

export interface Column<T> {
  key: string;
  header: string;
  render: (item: T) => React.ReactNode;
  align?: "left" | "right" | "center";
  className?: string;
  width?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string | number;
  onRowClick?: (item: T) => void;
  emptyState?: React.ReactNode;
  className?: string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  emptyState,
  className = "",
}: DataTableProps<T>) {
  if (data.length === 0 && emptyState) {
    return <div className={`bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 ${className}`}>{emptyState}</div>;
  }

  return (
    <div
      className={`bg-[var(--surface)] border border-[var(--line)] rounded-[10px] shadow-[var(--shadow-1)] overflow-hidden ${className}`}
    >
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-[14px]">
          <thead className="sticky top-0 bg-[var(--surface-sunken)] border-b border-[var(--line)] z-10">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  style={col.width ? { width: col.width } : undefined}
                  className={`py-3 px-4 font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] select-none ${
                    col.align === "right"
                      ? "text-right"
                      : col.align === "center"
                      ? "text-center"
                      : "text-left"
                  } ${col.className || ""}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--line)]">
            {data.map((item) => {
              const key = keyExtractor(item);
              const isClickable = Boolean(onRowClick);

              return (
                <tr
                  key={key}
                  tabIndex={isClickable ? 0 : undefined}
                  onClick={() => onRowClick && onRowClick(item)}
                  onKeyDown={(e) => {
                    if (isClickable && (e.key === "Enter" || e.key === " ")) {
                      e.preventDefault();
                      onRowClick && onRowClick(item);
                    }
                  }}
                  className={`transition-colors duration-100 ${
                    isClickable
                      ? "cursor-pointer hover:bg-[var(--surface-sunken)] focus-visible:bg-[var(--surface-sunken)] focus-visible:outline-none"
                      : ""
                  }`}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`py-3 px-4 text-[var(--ink)] ${
                        col.align === "right"
                          ? "text-right tabular"
                          : col.align === "center"
                          ? "text-center"
                          : "text-left"
                      } ${col.className || ""}`}
                    >
                      {col.render(item)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
