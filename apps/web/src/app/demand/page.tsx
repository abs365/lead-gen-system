"use client";

import { useEffect, useState } from "react";
import Navigation from "@/components/Navigation";

const API = "/api/proxy";

export default function DemandPage() {
  const [prospects, setProspects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetch(`${API}/analytics/demand-prospects`)
      .then(r => r.json())
      .then(data => { setProspects(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = prospects.filter(p => {
    const matchSearch = !search || p.name?.toLowerCase().includes(search.toLowerCase());
    const matchFilter =
      filter === "all" ||
      (filter === "priority" && p.is_high_priority) ||
      (filter === "enriched" && p.status === "enriched") ||
      filter === p.source;
    return matchSearch && matchFilter;
  });

  const highPriority = prospects.filter(p => p.is_high_priority).length;
  const enriched = prospects.filter(p => p.status === "enriched").length;
  const withEmail = prospects.filter(p => p.email).length;

  return (
    <>
      <Navigation />
      <div style={{ minHeight: "100vh", background: "#0f172a", padding: "32px 24px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ marginBottom: 32 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.5px" }}>
              Demand Prospects
            </h1>
            <p style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>
              {prospects.length} businesses that may need plumbing
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 28 }}>
            <StatCard label="Total" value={prospects.length} color="#60a5fa" />
            <StatCard label="High Priority" value={highPriority} color="#f59e0b" />
            <StatCard label="Enriched" value={enriched} color="#34d399" />
            <StatCard label="With Email" value={withEmail} color="#a78bfa" />
          </div>

          <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
            <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search prospects..."
                style={{ flex: 1, minWidth: 200, background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 14px", color: "#f1f5f9", fontSize: 13, outline: "none" }}
              />
              <select
                value={filter}
                onChange={e => setFilter(e.target.value)}
                style={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 14px", color: "#f1f5f9", fontSize: 13, outline: "none" }}
              >
                <option value="all">All</option>
                <option value="priority">High Priority</option>
                <option value="enriched">Enriched</option>
                <option value="fsa">FSA</option>
                <option value="companies_house">Companies House</option>
              </select>
            </div>

            {loading ? (
              <p style={{ color: "#64748b", fontSize: 13 }}>Loading...</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th style={th}>Name</th>
                      <th style={th}>Category</th>
                      <th style={th}>Address</th>
                      <th style={th}>Email</th>
                      <th style={th}>Phone</th>
                      <th style={{ ...th, textAlign: "center" }}>Score</th>
                      <th style={{ ...th, textAlign: "center" }}>Status</th>
                      <th style={{ ...th, textAlign: "center" }}>Priority</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((p, i) => (
                      <tr key={p.id} style={{ borderBottom: "1px solid #1e293b", background: i % 2 === 0 ? "transparent" : "#0f172a22" }}>
                        <td style={td}>
                          <span style={{ color: "#f1f5f9", fontWeight: 500 }}>{p.name}</span>
                        </td>
                        <td style={td}>
                          <span style={{ color: "#94a3b8", fontSize: 11 }}>{p.category || "—"}</span>
                        </td>
                        <td style={{ ...td, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {p.address || <span style={{ color: "#475569" }}>—</span>}
                        </td>
                        <td style={td}>
                          {p.email
                            ? <a href={`mailto:${p.email}`} style={{ color: "#60a5fa", textDecoration: "none" }}>{p.email}</a>
                            : <span style={{ color: "#475569" }}>—</span>}
                        </td>
                        <td style={td}>{p.phone || <span style={{ color: "#475569" }}>—</span>}</td>
                        <td style={{ ...td, textAlign: "center" }}>
                          <span style={{ background: "#1e3a5f", color: "#60a5fa", padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 600 }}>
                            {p.demand_score}
                          </span>
                        </td>
                        <td style={{ ...td, textAlign: "center" }}>
                          <span style={{
                            background: p.status === "enriched" ? "#064e3b" : p.status === "needs_contact" ? "#431407" : "#1e293b",
                            color: p.status === "enriched" ? "#34d399" : p.status === "needs_contact" ? "#fb923c" : "#475569",
                            padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 600
                          }}>
                            {p.status}
                          </span>
                        </td>
                        <td style={{ ...td, textAlign: "center" }}>
                          {p.is_high_priority
                            ? <span style={{ color: "#f59e0b" }}>★</span>
                            : <span style={{ color: "#334155" }}>—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ background: "#1e293b", borderRadius: 12, padding: "20px 24px", border: "1px solid #334155" }}>
      <div style={{ fontSize: 32, fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 12, color: "#64748b", marginTop: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
    </div>
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
  color: "#94a3b8",
  fontSize: 13,
};