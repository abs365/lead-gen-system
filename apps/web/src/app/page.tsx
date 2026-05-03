cat > /home/claude/dashboard_new.tsx << 'EOF'
"use client";

import { useEffect, useState } from "react";
import Navigation from "@/components/Navigation";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const API_KEY = "12B295n305T286s113a151e24";

export default function Dashboard() {
  const [pipeline, setPipeline] = useState<any>(null);
  const [matches, setMatches] = useState<any[]>([]);
  const [sending, setSending] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  async function loadPipeline() {
    try {
      const res = await fetch(`${API}/analytics/pipeline`);
      const data = await res.json();
      setPipeline(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e) { console.error(e); }
  }

  async function loadMatches() {
    try {
      const res = await fetch(`${API}/analytics/matches`);
      const data = await res.json();
      setMatches(Array.isArray(data) ? data : []);
    } catch (e) { console.error(e); }
  }

  async function sendOutreach() {
    setSending(true);
    try {
      await fetch(`${API}/automation/send-outreach`, { method: "GET", headers: { "X-API-KEY": API_KEY } });
      await loadPipeline();
    } finally { setSending(false); }
  }

  async function sendMatchOutreach() {
    setSending(true);
    try {
      await fetch(`${API}/automation/send-match-outreach`, { method: "POST", headers: { "X-API-KEY": API_KEY } });
      await loadMatches();
    } finally { setSending(false); }
  }

  useEffect(() => {
    loadPipeline();
    loadMatches();
    const interval = setInterval(() => { loadPipeline(); loadMatches(); }, 10000);
    return () => clearInterval(interval);
  }, []);

  const total = pipeline
    ? (pipeline.new ?? 0) + (pipeline.contacted ?? 0) + (pipeline.interested ?? 0) + (pipeline.closed ?? 0)
    : 0;

  const chartData = pipeline ? [
    { name: "New", value: pipeline.new ?? 0, color: "#60a5fa" },
    { name: "Contacted", value: pipeline.contacted ?? 0, color: "#fbbf24" },
    { name: "Interested", value: pipeline.interested ?? 0, color: "#34d399" },
    { name: "Closed", value: pipeline.closed ?? 0, color: "#a78bfa" },
  ] : [];

  return (
    <>
      <Navigation />
      <div style={{ minHeight: "100vh", background: "#0f172a", padding: "32px 24px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>

          {/* HEADER */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32 }}>
            <div>
              <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.5px" }}>
                Performance Dashboard
              </h1>
              <p style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>
                {lastUpdated ? `Last updated ${lastUpdated}` : "Loading..."}
              </p>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <ActionBtn label="Send Outreach" onClick={sendOutreach} loading={sending} color="#3b82f6" />
              <ActionBtn label="Send Matches" onClick={sendMatchOutreach} loading={sending} color="#10b981" />
            </div>
          </div>

          {/* KPI CARDS */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 32 }}>
            <KPICard label="Total Leads" value={total} icon="⚡" color="#60a5fa" />
            <KPICard label="New" value={pipeline?.new ?? 0} icon="🆕" color="#60a5fa" />
            <KPICard label="Contacted" value={pipeline?.contacted ?? 0} icon="📧" color="#fbbf24" />
            <KPICard label="Interested" value={pipeline?.interested ?? 0} icon="🔥" color="#34d399" />
            <KPICard label="Closed" value={pipeline?.closed ?? 0} icon="✅" color="#a78bfa" />
          </div>

          {/* CHART + TABLE ROW */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: 20, marginBottom: 32 }}>

            {/* CHART */}
            <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
              <h2 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 20 }}>
                Pipeline Funnel
              </h2>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} barSize={40}>
                  <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, color: "#f1f5f9" }}
                    cursor={{ fill: "rgba(255,255,255,0.05)" }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* MATCHES TABLE */}
            <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
              <h2 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 20 }}>
                Top Matches
              </h2>
              <div style={{ overflowY: "auto", maxHeight: 260 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th style={th}>Prospect</th>
                      <th style={th}>Plumber</th>
                      <th style={{ ...th, textAlign: "center" }}>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matches.map((m, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                        <td style={td}>{m.prospect_name}</td>
                        <td style={td}>{m.plumber_name}</td>
                        <td style={{ ...td, textAlign: "center" }}>
                          <span style={{
                            background: m.match_score >= 90 ? "#064e3b" : "#1e3a5f",
                            color: m.match_score >= 90 ? "#34d399" : "#60a5fa",
                            padding: "2px 8px", borderRadius: 20, fontSize: 12, fontWeight: 600
                          }}>
                            {m.match_score}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

        </div>
      </div>
    </>
  );
}

function KPICard({ label, value, icon, color }: { label: string; value: number; icon: string; color: string }) {
  return (
    <div style={{
      background: "#1e293b",
      borderRadius: 12,
      padding: "20px 24px",
      border: "1px solid #334155",
      position: "relative",
      overflow: "hidden",
    }}>
      <div style={{ fontSize: 24, marginBottom: 8 }}>{icon}</div>
      <div style={{ fontSize: 32, fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 12, color: "#64748b", marginTop: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
    </div>
  );
}

function ActionBtn({ label, onClick, loading, color }: { label: string; onClick: () => void; loading: boolean; color: string }) {
  return (
    <button onClick={onClick} disabled={loading} style={{
      background: loading ? "#334155" : color,
      color: "#fff",
      border: "none",
      borderRadius: 8,
      padding: "10px 18px",
      fontSize: 13,
      fontWeight: 600,
      cursor: loading ? "not-allowed" : "pointer",
    }}>
      {loading ? "..." : label}
    </button>
  );
}

const th: React.CSSProperties = {
  textAlign: "left",
  padding: "8px 12px",
  color: "#475569",
  fontSize: 11,
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  borderBottom: "1px solid #334155",
};

const td: React.CSSProperties = {
  padding: "10px 12px",
  color: "#cbd5e1",
  fontSize: 13,
};
