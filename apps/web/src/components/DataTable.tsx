"use client";

import { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  className?: string;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  keyField?: keyof T;
  emptyMessage?: string;
}

export default function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
  keyField = "id" as keyof T,
  emptyMessage = "No records found.",
}: Props<T>) {
  if (rows.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500 text-sm">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className="px-4 py-3 text-left font-semibold text-slate-600 whitespace-nowrap"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-slate-100">
          {rows.map((row, i) => (
            <tr
              key={String(row[keyField] ?? i)}
              className="hover:bg-slate-50 transition-colors"
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`px-4 py-2 text-slate-700 ${col.className ?? ""}`}
                >
                  {col.render
                    ? col.render(row)
                    : (row[col.key] as ReactNode) ?? (
                        <span className="text-slate-300">—</span>
                      )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
