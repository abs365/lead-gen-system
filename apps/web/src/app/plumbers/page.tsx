"use client";

import { useEffect, useState } from "react";
import Navigation from "@/components/Navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const API_KEY = "12B295n305T286s113a151e24";

export default function PlumbersPage() {
  const [plumbers, setPlumbers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch(`${API}/analytics/plumbers`)
      .then(r => r.json())
      .then(data => { setPlumbers(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = plumbers.filter(p =>
    !search || p.name?.toLowerCase().includes(search.toLowerCase()) ||
    p.email?.toLowerCase().includes(search.toLowerCase())
  );

  const commercial = plumbers.filter(p => p.is_commercial).length;
  const withEmail = plumbers.filter(p => p.email).length;

  return (
    <>
      <Navigation />
      <div style={{ minHeight: "100vh", background: "#0f172a", padding: "32px 24px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ marginBottom: 32 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.5px" }}>Plumbers</h1>
            <p style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>{plumbers.length} plumbers in database</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 28 }}>
            <StatCard label="Total" value={plumbers.length} color="#60a5fa" />
            <StatCard label="Commercial" value={commercial} color="#34d399" />
            <StatCard label="With Email" value={withEmail} color="#fbbf24" />
          </div>

          <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search plumbers..."
              style={{ width: "100%", background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 14px", color: "#f1f5f9", fontSize: 13, marginBottom: 20, outline: "none", boxSizing: "border-box" }}
            />
            {loading ? (
              <p style={{ color: "#64748b", fontSize: 13 }}>Loading...</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th style={th}>Name</th>
                      <th style={th}>Email</th>
                      <th style={th}>Phone</th>
                      <th style={th}>Address</th>
                      <th style={{ ...th, textAlign: "center" }}>Commercial</th>
                      <th style={th}>Website</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((p, i) => (
                      <tr key={p.id} style={{ borderBottom: "1px solid #1e293b", background: i % 2 === 0 ? "transparent" : "#0f172a22" }}>
                        <td style={td}><span style={{ color: "#f1f5f9", fontWeight: 500 }}>{p.name}</span></td>
                        <td style={td}>{p.email ? <a href={`mailto:${p.email}`} style={{ color: "#60a5fa", textDecoration: "none" }}>{p.email}</a> : <span style={{ color: "#475569" }}>—</span>}</td>
                        <td style={td}>{p.phone || <span style={{ color: "#475569" }}>—</span>}</td>
                        <td style={{ ...td, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.address || <span style={{ color: "#475569" }}>—</span>}</td>
                        <td style={{ ...td, textAlign: "center" }}>
                          <span style={{ background: p.is_commercial ? "#064e3b" : "#1e293b", color: p.is_commercial ? "#34d399" : "#475569", padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 600 }}>
                            {p.is_commercial ? "Yes" : "No"}
                          </span>
                        </td>
                        <td style={td}>{p.website ? <a href={p.website} target="_blank" rel="noopener noreferrer" style={{ color: "#60a5fa", textDecoration: "none" }}>Visit</a> : <span style={{ color: "#475569" }}>—</span>}</td>
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

const th: React.CSSProperties = { textAlign: "left", padding: "8px 12px", color: "#475569", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "1px solid #334155" };
const td: React.CSSProperties = { padding: "10px 12px", color: "#94a3b8", fontSize: 13 };