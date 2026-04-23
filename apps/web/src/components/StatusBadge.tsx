interface Props {
  status: "success" | "error" | "running" | "idle" | string;
  message?: string;
}

const STYLES: Record<string, string> = {
  success: "bg-green-100 text-green-800 border border-green-200",
  error:   "bg-red-100  text-red-800   border border-red-200",
  running: "bg-blue-100 text-blue-800  border border-blue-200",
  idle:    "bg-slate-100 text-slate-600 border border-slate-200",
};

export default function StatusBadge({ status, message }: Props) {
  if (!message && status === "idle") return null;

  const style = STYLES[status] ?? STYLES.idle;

  return (
    <div className={`rounded-md px-4 py-3 text-sm ${style}`}>
      <span className="font-semibold capitalize">{status}</span>
      {message && <span className="ml-2">{message}</span>}
    </div>
  );
}
