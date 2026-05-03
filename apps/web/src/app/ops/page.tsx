bash

cat > /home/claude/ops_page.tsx << 'ENDOFFILE'
"use client";

import { useState } from "react";
import Navigation from "@/components/Navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const API_KEY = "12B295n305T286s113a151e24";

type LogEntry = { time: string; message: string; ok: boolean };

export default function OpsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const [pipeline, setPipeline] = useState<any>(null);

  function log(message: string, ok = true) {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [{ time, message, ok }, ...prev].slice(0, 50));
  }

  async function call(label: string, path: string, method = "GET") {
    setLoading(label);
    try {
      const res = await fetch(`${API}${path}`, {
        method,
        headers: { "X-API-KEY": API_KEY },
      });
      const data = await res.json();
      log(`${label}: ${JSON.stringify(data)}`, res.ok);
      return data;
    } catch (e: any) {
      log(`${label}: ERROR — ${e.message}`, false);
    } finally {
      setLoading(null);
    }
  }

  async function loadPipeline() {
    const data = await call("Load Pipeline", "/analytics/pipeline");
    if (data) setPipeline(data);
  }

  async function runFullPipeline() {
    log("Starting full pipeline...");
    await call("Score Demand", "/collect/score-demand");
    await call("Run Matching", "/collect/run-matching-engine");
    await call("Send Match Outreach", "/automation/send-match-outreach", "POST");
    await loadPipeline();
    log("Full pipeline complete");
  }

  return (
    <>
      <Navigation />
      <div style={{ padding: 30, maxWidth: 1100, margin: "0 auto" }}>
        <h1 style={{ fontSize: 24, fontWeight: "bold", marginBottom: 6 }}>
          Operations Console
        </h1>
        <p style={{ color: "#666", marginBottom: 30, fontSize: 14 }}>
          Use these controls to manually trigger pipeline steps and monitor system status.
        </p>

        {/* PIPELINE STATUS */}
        <Section title="Pipeline Status">
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
            {pipeline ? (
              <>
                <KPI label="New" value={pipeline.new ?? 0} color="#3b82f6" />
                <KPI label="Contacted" value={pipeline.contacted ?? 0} color="#f59e0b" />
                <KPI label="Interested" value={pipeline.interested ?? 0} color="#10b981" />
                <KPI label="Closed" value={pipeline.closed ?? 0} color="#6366f1" />
              </>
            ) : (
              <p style={{ color: "#999", fontSize: 14 }}>Click "Refresh Pipeline" to load.</p>
            )}
          </div>
          <Btn label="Refresh Pipeline" loading={loading} onClick={loadPipeline} color="#3b82f6" />
        </Section>

        {/* FULL PIPELINE */}
        <Section title="Full Pipeline (Collect → Score → Match → Send)">
          <p style={{ fontSize: 13, color: "#666", marginBottom: 12 }}>
            Runs automatically every day at 6am. Use this button to trigger manually.
          </p>
          <Btn label="Run Full Pipeline" loading={loading} onClick={runFullPipeline} color="#10b981" />
        </Section>

        {/* INDIVIDUAL STEPS */}
        <Section title="Individual Steps">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <Btn
              label="Score Demand"
              loading={loading}
              onClick={() => call("Score Demand", "/collect/score-demand")}
              color="#6366f1"
            />
            <Btn
              label="Run Matching Engine"
              loading={loading}
              onClick={() => call("Run Matching", "/collect/run-matching-engine")}
              color="#6366f1"
            />
            <Btn
              label="Send Match Outreach"
              loading={loading}
              onClick={() => call("Send Match Outreach", "/automation/send-match-outreach", "POST")}
              color="#f59e0b"
            />
            <Btn
              label="Send Standard Outreach"
              loading={loading}
              onClick={() => call("Send Outreach", "/automation/send-outreach")}
              color="#f59e0b"
            />
            <Btn
              label="Detect Replies"
              loading={loading}
              onClick={() => call("Detect Replies", "/automation/detect-replies", "POST")}
              color="#64748b"
            />
            <Btn
              label="Follow Up Hot Leads"
              loading={loading}
              onClick={() => call("Follow Up", "/automation/follow-up-hot-leads")}
              color="#64748b"
            />
            <Btn
              label="Clean Bad Leads"
              loading={loading}
              onClick={() => call("Clean Bad Leads", "/analytics/clean-bad-leads", "POST")}
              color="#ef4444"
            />
          </div>
        </Section>

        {/* SYSTEM HEALTH */}
        <Section title="System Health">
          <Btn
            label="Check Health"
            loading={loading}
            onClick={() => call("Health Check", "/health")}
            color="#3b82f6"
          />
        </Section>

        {/* ACTIVITY LOG */}
        <Section title="Activity Log">
          {logs.length === 0 ? (
            <p style={{ color: "#999", fontSize: 13 }}>No activity yet. Run a command above.</p>
          ) : (
            <div
              style={{
                fontFamily: "monospace",
                fontSize: 12,
                background: "#0f172a",
                color: "#e2e8f0",
                borderRadius: 8,
                padding: 16,
                maxHeight: 300,
                overflowY: "auto",
              }}
            >
              {logs.map((l, i) => (
                <div key={i} style={{ marginBottom: 4, color: l.ok ? "#86efac" : "#fca5a5" }}>
                  <span style={{ color: "#94a3b8" }}>[{l.time}]</span> {l.message}
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        border: "1px solid #e2e8f0",
        borderRadius: 10,
        padding: 24,
        marginBottom: 24,
        background: "#fff",
      }}
    >
      <h2 style={{ fontSize: 16, fontWeight: "600", marginBottom: 16, color: "#1e293b" }}>
        {title}
      </h2>
      {children}
    </div>
  );
}

function KPI({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div
      style={{
        border: `2px solid ${color}`,
        borderRadius: 8,
        padding: "12px 20px",
        minWidth: 120,
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 28, fontWeight: "bold", color }}>{value}</div>
      <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>{label}</div>
    </div>
  );
}

function Btn({
  label,
  onClick,
  loading,
  color,
}: {
  label: string;
  onClick: () => void;
  loading: string | null;
  color: string;
}) {
  const isLoading = loading === label;
  return (
    <button
      onClick={onClick}
      disabled={!!loading}
      style={{
        background: isLoading ? "#94a3b8" : color,
        color: "#fff",
        border: "none",
        borderRadius: 6,
        padding: "10px 18px",
        fontSize: 13,
        fontWeight: 500,
        cursor: loading ? "not-allowed" : "pointer",
        transition: "opacity 0.2s",
        opacity: loading && !isLoading ? 0.6 : 1,
      }}
    >
      {isLoading ? "Running..." : label}
    </button>
  );
}
ENDOFFILE
echo "Done"
Output

Done
