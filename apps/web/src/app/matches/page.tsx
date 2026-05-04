"use client";

import { useEffect, useState } from "react";
import Navigation from "@/components/Navigation";

const API = "/api/proxy";

export default function MatchesPage() {
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch(`${API}/analytics/matches`)
      .then(r => r.json())
      .then(data => { setMatches(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = matches.filter(m =>
    !search ||
    m.prospect_name?.toLowerCase().includes(search.toLowerCase()) ||
    m.plumber_name?.toLowerCase().includes(search.toLowerCase())
  );

  const perfect = matches.filter(m => m.match_score >= 90).length;
  const good = matches.filter(m => m.match_score >= 60 && m.match_score < 90).length;
  const uniqueProspects = new Set(matches.map(m => m.prospect_name)).size;

  return (
    <>
      <Navigation />
      <div style={{ minHeight: "100vh", background: "#0f172a", padding: "32px 24px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ marginBottom: 32 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.5px" }}>Matches</h1>
            <p style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>{matches.length} plumber-prospect matches</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 28 }}>
            <StatCard label="Total Matches" value={matches.length} color="#60a5fa" />
            <StatCard label="Score 90+" value={perfect} color="#34d399" />
            <StatCard label="Score 60-89" value={good} color="#fbbf24" />
            <StatCard label="Unique Prospects" value={uniqueProspects} color="#a78bfa" />
          </div>

          <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by prospect or plumber name..."
              style={{ width: "100%", background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 14px", color: "#f1f5f9", fontSize: 13, marginBottom: 20, outline: "none", boxSizing: "border-box" }}
            />
            {loading ? (
              <p style={{ color: "#64748b", fontSize: 13 }}>Loading...</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th style={th}>#</th>
                      <th style={th}>Prospect</th>
                      <th style={th}>Plumber</th>
                      <th style={{ ...th, textAlign: "center" }}>Match Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((m, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid #1e293b", background: i % 2 === 0 ? "transparent" : "#0f172a22" }}>
                        <td style={{ ...td, color: "#475569", width: 40 }}>{i + 1}</td>
                        <td style={td}><span style={{ color: "#f1f5f9", fontWeight: 500 }}>{m.prospect_name}</span></td>
                        <td style={td}><span style={{ color: "#94a3b8" }}>{m.plumber_name}</span></td>
                        <td style={{ ...td, textAlign: "center" }}>
                          <span style={{
                            background: m.match_score >= 90 ? "#064e3b" : m.match_score >= 60 ? "#1e3a5f" : "#1e293b",
                            color: m.match_score >= 90 ? "#34d399" : m.match_score >= 60 ? "#60a5fa" : "#475569",
                            padding: "3px 10px", borderRadius: 20, fontSize: 12, fontWeight: 700
                          }}>
                            {m.match_score}
                          </span>
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

const th: React.CSSProperties = { textAlign: "left", padding: "8px 12px", color: "#475569", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "1px solid #334155" };
const td: React.CSSProperties = { padding: "10px 12px", color: "#94a3b8", fontSize: 13 };
