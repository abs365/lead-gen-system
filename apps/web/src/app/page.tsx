"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default function Dashboard() {
  const [pipeline, setPipeline] = useState<any>(null);
  const [matches, setMatches] = useState<any[]>([]);
  const [sending, setSending] = useState(false);

  async function loadPipeline() {
    try {
      const res = await fetch(`${API}/analytics/pipeline`);
      const data = await res.json();
      setPipeline(data);
    } catch (e) {
      console.error("Pipeline load failed", e);
    }
  }

  async function loadMatches() {
    try {
      const res = await fetch(`${API}/analytics/matches`);
      const data = await res.json();
      setMatches(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error("Matches load failed", e);
    }
  }

  async function sendOutreach() {
    setSending(true);
    try {
      await fetch(`${API}/automation/send-outreach`, { method: "GET" });
      await loadPipeline();
      await loadMatches();
    } finally {
      setSending(false);
    }
  }

  async function sendMatchOutreach() {
    setSending(true);
    try {
      await fetch(`${API}/automation/send-match-outreach`, { method: "POST" });
      await loadMatches();
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    loadPipeline();
    loadMatches();
    const interval = setInterval(() => {
      loadPipeline();
      loadMatches();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const chartData = pipeline
    ? [
        { name: "New", value: pipeline.new ?? 0 },
        { name: "Contacted", value: pipeline.contacted ?? 0 },
        { name: "Interested", value: pipeline.interested ?? 0 },
        { name: "Closed", value: pipeline.closed ?? 0 },
      ]
    : [];

  const total = pipeline
    ? (pipeline.new ?? 0) +
      (pipeline.contacted ?? 0) +
      (pipeline.interested ?? 0) +
      (pipeline.closed ?? 0)
    : 0;

  return (
    <div style={{ padding: 30, maxWidth: 1200, margin: "0 auto" }}>
      <h1>LeadGen Performance Dashboard</h1>

      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        <button onClick={sendOutreach} disabled={sending}>
          {sending ? "Sending..." : "Send Outreach"}
        </button>
        <button onClick={sendMatchOutreach} disabled={sending}>
          {sending ? "Sending..." : "Send Match Outreach"}
        </button>
      </div>

      {/* KPI CARDS */}
      <div style={{ display: "flex", gap: 20, marginBottom: 30 }}>
        <Card title="Total Leads" value={total} />
        <Card title="Contacted" value={pipeline?.contacted ?? "—"} />
        <Card title="Interested" value={pipeline?.interested ?? "—"} />
        <Card title="Closed" value={pipeline?.closed ?? "—"} />
      </div>

      {/* PIPELINE CHART */}
      <h2>Lead Pipeline</h2>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="value" fill="#3b82f6">
            <LabelList dataKey="value" position="top" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* MATCHES TABLE */}
      <h2 style={{ marginTop: 40 }}>Top Matches</h2>
      <div style={{ marginTop: 20 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ background: "#f5f5f5" }}>
              <th style={cell}>Prospect</th>
              <th style={cell}>Plumber</th>
              <th style={cell}>Match Score</th>
            </tr>
          </thead>
          <tbody>
            {matches.map((m, i) => (
              <tr key={i}>
                <td style={cell}>{m.prospect_name}</td>
                <td style={cell}>{m.plumber_name}</td>
                <td style={cell}>{m.match_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Card({ title, value }: { title: string; value: any }) {
  return (
    <div
      style={{
        border: "1px solid #ddd",
        borderRadius: 8,
        padding: 20,
        minWidth: 180,
        background: "#fff",
        boxShadow: "0 2px 6px rgba(0,0,0,0.05)",
      }}
    >
      <h4 style={{ marginBottom: 10 }}>{title}</h4>
      <p style={{ fontSize: 28, fontWeight: "bold" }}>{value}</p>
    </div>
  );
}

const cell = {
  border: "1px solid #ddd",
  padding: "8px",
  textAlign: "left" as const,
};
