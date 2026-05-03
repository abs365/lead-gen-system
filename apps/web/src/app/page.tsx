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

export default function Dashboard() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);

  // -----------------------------
  // LOAD ANALYTICS
  // -----------------------------
  async function loadAnalytics() {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analytics/pipeline`);
    const data = await res.json();
    setAnalytics(data);
  }

  // -----------------------------
  // LOAD ACTIVITY
  // -----------------------------
  async function loadActivity() {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analytics/matches`);
    const data = await res.json();
    setActivity(data);
  }

  // -----------------------------
  // SEND EMAILS
  // -----------------------------
  async function sendOutreach() {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/automation/send-outreach`, {
      method: "POST",
    });
    loadAnalytics();
    loadActivity();
  }

  // -----------------------------
  // AUTO REFRESH
  // -----------------------------
  useEffect(() => {
    loadAnalytics();
    loadActivity();

    const interval = setInterval(() => {
      loadAnalytics();
      loadActivity();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  if (!analytics) return <div>Loading...</div>;

  // -----------------------------
  // CALCULATIONS
  // -----------------------------
  const openRate =
    analytics.total_sent > 0
      ? ((analytics.opened / analytics.total_sent) * 100).toFixed(1)
      : 0;

  const clickRate =
    analytics.total_sent > 0
      ? ((analytics.clicked / analytics.total_sent) * 100).toFixed(1)
      : 0;

  const chartData = [
    {
      name: "Sent",
      value: analytics.total_sent,
      label: "100%",
    },
    {
      name: "Opened",
      value: analytics.opened,
      label: `${openRate}%`,
    },
    {
      name: "Clicked",
      value: analytics.clicked,
      label: `${clickRate}%`,
    },
  ];

  return (
    <div style={{ padding: 30, maxWidth: 1200, margin: "0 auto" }}>
      <h1>LeadGen Performance Dashboard</h1>

      <button onClick={sendOutreach} style={{ marginBottom: 20 }}>
        Send Outreach
      </button>

      {/* METRICS */}
      <div style={{ display: "flex", gap: 20, marginBottom: 30 }}>
        <Card title="Total Sent" value={analytics.total_sent} />
        <Card title="Open Rate %" value={analytics.open_rate_percent} />
        <Card title="Click Rate %" value={analytics.click_rate_percent} />
      </div>

      {/* CHART */}
      <h2>Outreach Funnel</h2>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="value" fill="#3b82f6">
            <LabelList dataKey="label" position="top" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* TABLE */}
      <h2 style={{ marginTop: 40 }}>Recent Activity</h2>

      <div style={{ marginTop: 20 }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 14,
          }}
        >
          <thead>
            <tr style={{ background: "#f5f5f5" }}>
              <th style={cell}>Email</th>
              <th style={cell}>Subject</th>
              <th style={cell}>Opened</th>
              <th style={cell}>Clicked</th>
              <th style={cell}>Time</th>
            </tr>
          </thead>
          <tbody>
            {Array.isArray(activity) && activity.map((a, i) => (
              <tr key={i}>
                <td style={cell}>{a.email}</td>
                <td style={cell}>{a.subject}</td>
                <td style={cell}>{a.opened ? "✔" : "—"}</td>
                <td style={cell}>{a.clicked ? "✔" : "—"}</td>
                <td style={cell}>
                  {new Date(a.sent_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// -----------------------------
// CARD COMPONENT
// -----------------------------
function Card({ title, value }: { title: string; value: any }) {
  return (
    <div
      style={{
        border: "1px solid #ddd",
        borderRadius: 8,
        padding: 20,
        minWidth: 200,
        background: "#fff",
        boxShadow: "0 2px 6px rgba(0,0,0,0.05)",
      }}
    >
      <h4 style={{ marginBottom: 10 }}>{title}</h4>
      <p style={{ fontSize: 28, fontWeight: "bold" }}>{value}</p>
    </div>
  );
}

// -----------------------------
// TABLE CELL STYLE
// -----------------------------
const cell = {
  border: "1px solid #ddd",
  padding: "8px",
  textAlign: "left" as const,
};