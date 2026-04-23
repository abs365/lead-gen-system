"use client";

import { useState } from "react";
import StatusBadge from "./StatusBadge";

interface Action {
  label: string;
  description?: string;
  onRun: () => Promise<{ status: string; message: string }>;
}

interface Props {
  title: string;
  actions: Action[];
}

export default function CollectPanel({ title, actions }: Props) {
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<{
    status: string;
    message: string;
  } | null>(null);

  async function handleRun(action: Action) {
    setRunning(action.label);
    setResult({ status: "running", message: `Running: ${action.label}…` });
    try {
      const res = await action.onRun();
      setResult({ status: res.status, message: res.message });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setResult({ status: "error", message: msg });
    } finally {
      setRunning(null);
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
      <h2 className="font-semibold text-slate-800 text-base">{title}</h2>

      <div className="flex flex-wrap gap-3">
        {actions.map((action) => (
          <div key={action.label}>
            <button
              onClick={() => handleRun(action)}
              disabled={running !== null}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg
                         hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                         transition-colors"
            >
              {running === action.label ? "Running…" : action.label}
            </button>
            {action.description && (
              <p className="text-xs text-slate-400 mt-1">{action.description}</p>
            )}
          </div>
        ))}
      </div>

      {result && (
        <StatusBadge status={result.status} message={result.message} />
      )}
    </div>
  );
}
