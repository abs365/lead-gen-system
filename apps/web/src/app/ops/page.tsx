cat > /home/claude/ops_new.tsx << 'EOF'
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
    log("Full pipeline complete ✓");
  }

  return (
    <>
      <Navigation />
      <div style={{ minHeight: "100vh", background: "#0f172a", padding: "32px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>

          {/* HEADER */}
          <div style={{ marginBottom: 32 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.5px" }}>
              Operations Console
            </h1>
            <p style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>
              Manually trigger pipeline steps and monitor system status.
            </p>
          </div>

          {/* PIPELINE STATUS */}
          <Panel title="Pipeline Status" icon="📊">
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 20 }}>
              {pipeline ? (
                <>
                  <Stat label="New" value={pipeline.new ?? 0} color="#60a5fa" />
                  <Stat label="Contacted" value={pipeline.contacted ?? 0} color="#fbbf24" />
                  <Stat label="Interested" value={pipeline.interested ?? 0} color="#34d399" />
                  <Stat label="Closed" value={pipeline.closed ?? 0} color="#a78bfa" />
                </>
              ) : (
                <p style={{ color: "#475569", fontSize: 13 }}>Click Refresh to load pipeline data.</p>
              )}
            </div>
            <Btn label="Refresh Pipeline" loading={loading} onClick={loadPipeline} color="#3b82f6" />
          </Panel>

          {/* FULL PIPELINE */}
          <Panel title="Full Pipeline" icon="⚡">
            <p style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>
              Runs automatically every day at 6am. Click to trigger manually.
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Btn label="Run Full Pipeline" loading={loading} onClick={runFullPipeline} color="#10b981" />
              <span style={{ fontSize: 12, color: "#475569" }}>
                Collect → Score → Match → Send
              </span>
            </div>
          </Panel>

          {/* INDIVIDUAL STEPS */}
          <Panel title="Individual Steps" icon="🔧">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 10 }}>
              <StepBtn label="Score Demand" loading={loading} onClick={() => call("Score Demand", "/collect/score-demand")} color="#6366f1" desc="Score all prospects" />
              <StepBtn label="Run Matching Engine" loading={loading} onClick={() => call("Run Matching", "/collect/run-matching-engine")} color="#6366f1" desc="Match prospects to plumbers" />
              <StepBtn label="Send Match Outreach" loading={loading} onClick={() => call("Send Match Outreach", "/automation/send-match-outreach", "POST")} color="#f59e0b" desc="Email top matches" />
              <StepBtn label="Send Standard Outreach" loading={loading} onClick={() => call("Send Outreach", "/automation/send-outreach")} color="#f59e0b" desc="Standard email sequence" />
              <StepBtn label="Detect Replies" loading={loading} onClick={() => call("Detect Replies", "/automation/detect-replies", "POST")} color="#64748b" desc="Scan inbox for replies" />
              <StepBtn label="Follow Up Hot Leads" loading={loading} onClick={() => call("Follow Up", "/automation/follow-up-hot-leads")} color="#64748b" desc="Follow up interested leads" />
              <StepBtn label="Clean Bad Leads" loading={loading} onClick={() => call("Clean Bad Leads", "/analytics/clean-bad-leads", "POST")} color="#ef4444" desc="Remove invalid emails" />
            </div>
          </Panel>

          {/* SYSTEM HEALTH */}
          <Panel title="System Health" icon="💚">
            <Btn label="Check Health" loading={loading} onClick={() => call("Health Check", "/health")} color="#3b82f6" />
          </Panel>

          {/* ACTIVITY LOG */}
          <Panel title="Activity Log" icon="📋">
            {logs.length === 0 ? (
              <p style={{ color: "#475569", fontSize: 13 }}>No activity yet. Run a command above.</p>
            ) : (
              <div style={{
                fontFamily: "monospace",
                fontSize: 12,
                background: "#020617",
                color: "#e2e8f0",
                borderRadius: 8,
                padding: 16,
                maxHeight: 320,
                overflowY: "auto",
                border: "1px solid #1e293b",
              }}>
                {logs.map((l, i) => (
                  <div key={i} style={{ marginBottom: 6, display: "flex", gap: 10 }}>
                    <span style={{ color: "#334155", minWidth: 70 }}>[{l.time}]</span>
                    <span style={{ color: l.ok ? "#86efac" : "#fca5a5" }}>{l.message}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

        </div>
      </div>
    </>
  );
}

function Panel({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: "#1e293b",
      borderRadius: 12,
      padding: 24,
      marginBottom: 20,
      border: "1px solid #334155",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
        <span style={{ fontSize: 16 }}>{icon}</span>
        <h2 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          {title}
        </h2>
      </div>
      {children}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{
      background: "#0f172a",
      borderRadius: 10,
      padding: "14px 20px",
      minWidth: 120,
      border: `1px solid ${color}33`,
    }}>
      <div style={{ fontSize: 26, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color: "#64748b", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
    </div>
  );
}

function Btn({ label, onClick, loading, color }: { label: string; onClick: () => void; loading: string | null; color: string }) {
  const isLoading = loading === label;
  return (
    <button onClick={onClick} disabled={!!loading} style={{
      background: isLoading ? "#334155" : color,
      color: "#fff",
      border: "none",
      borderRadius: 8,
      padding: "10px 20px",
      fontSize: 13,
      fontWeight: 600,
      cursor: loading ? "not-allowed" : "pointer",
      opacity: loading && !isLoading ? 0.5 : 1,
    }}>
      {isLoading ? "Running..." : label}
    </button>
  );
}

function StepBtn({ label, onClick, loading, color, desc }: { label: string; onClick: () => void; loading: string | null; color: string; desc: string }) {
  const isLoading = loading === label;
  return (
    <button onClick={onClick} disabled={!!loading} style={{
      background: isLoading ? "#334155" : `${color}22`,
      color: isLoading ? "#64748b" : color,
      border: `1px solid ${color}44`,
      borderRadius: 10,
      padding: "14px 16px",
      fontSize: 13,
      fontWeight: 600,
      cursor: loading ? "not-allowed" : "pointer",
      textAlign: "left",
      opacity: loading && !isLoading ? 0.5 : 1,
      transition: "all 0.15s",
    }}>
      <div>{isLoading ? "Running..." : label}</div>
      <div style={{ fontSize: 11, color: "#475569", marginTop: 4, fontWeight: 400 }}>{desc}</div>
    </button>
  );
}
