"use client";

import { useEffect, useState, useCallback } from "react";
import Navigation from "@/components/Navigation";

const API = "/api/proxy";

export default function MatchesPage() {
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [perPage] = useState(50);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [score90, setScore90] = useState(0);
  const [score60, setScore60] = useState(0);
  const [uniqueProspects, setUniqueProspects] = useState(0);
  const [minScore, setMinScore] = useState(0);

  const fetchMatches = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    });
    if (minScore > 0) params.append("min_score", String(minScore));
    if (search) params.append("search", search);

    fetch(`${API}/analytics/matches?${params}`)
      .then(r => r.json())
      .then(data => {
        if (data.matches) {
          setMatches(data.matches);
          setTotal(data.total || 0);
          setTotalPages(data.total_pages || 1);
          if (data.score_90_plus !== undefined) setScore90(data.score_90_plus);
          if (data.score_60_89 !== undefined) setScore60(data.score_60_89);
          if (data.unique_prospects !== undefined) setUniqueProspects(data.unique_prospects);
        } else {
          // Fallback for old API format (array response)
          const arr = Array.isArray(data) ? data : [];
          setMatches(arr);
          setTotal(arr.length);
          setTotalPages(1);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [page, perPage, minScore, search]);

  useEffect(() => { fetchMatches(); }, [fetchMatches]);

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  const handleScoreFilter = (score: number) => {
    setMinScore(prev => prev === score ? 0 : score);
    setPage(1);
  };

  const startRow = (page - 1) * perPage + 1;
  const endRow = Math.min(page * perPage, total);

  return (
    <>
      <Navigation />
      <div style={{ minHeight: "100vh", background: "#0f172a", padding: "32px 24px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ marginBottom: 32 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.5px" }}>Matches</h1>
            <p style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>
              {total.toLocaleString()} plumber-prospect matches
            </p>
          </div>

          {/* Stats cards — clickable for filtering */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 28 }}>
            <StatCard
              label="Total Matches"
              value={total}
              color="#60a5fa"
              active={minScore === 0}
              onClick={() => handleScoreFilter(0)}
            />
            <StatCard
              label="Score 90+"
              value={score90}
              color="#34d399"
              active={minScore === 90}
              onClick={() => handleScoreFilter(90)}
            />
            <StatCard
              label="Score 60-89"
              value={score60}
              color="#fbbf24"
              active={minScore === 60}
              onClick={() => handleScoreFilter(60)}
            />
            <StatCard
              label="Unique Prospects"
              value={uniqueProspects}
              color="#a78bfa"
            />
          </div>

          <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
            {/* Search bar */}
            <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
              <input
                value={searchInput}
                onChange={e => setSearchInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search by prospect or plumber name..."
                style={{
                  flex: 1, background: "#0f172a", border: "1px solid #334155",
                  borderRadius: 8, padding: "10px 14px", color: "#f1f5f9",
                  fontSize: 13, outline: "none", boxSizing: "border-box",
                }}
              />
              <button
                onClick={handleSearch}
                style={{
                  background: "#3b82f6", color: "#fff", border: "none",
                  borderRadius: 8, padding: "10px 20px", fontSize: 13,
                  fontWeight: 600, cursor: "pointer",
                }}
              >
                Search
              </button>
              {search && (
                <button
                  onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
                  style={{
                    background: "#334155", color: "#94a3b8", border: "none",
                    borderRadius: 8, padding: "10px 16px", fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  Clear
                </button>
              )}
            </div>

            {loading ? (
              <p style={{ color: "#64748b", fontSize: 13 }}>Loading...</p>
            ) : (
              <>
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
                      {matches.map((m, i) => (
                        <tr
                          key={i}
                          style={{
                            borderBottom: "1px solid #1e293b",
                            background: i % 2 === 0 ? "transparent" : "#0f172a22",
                          }}
                        >
                          <td style={{ ...td, color: "#475569", width: 40 }}>{startRow + i}</td>
                          <td style={td}>
                            <span style={{ color: "#f1f5f9", fontWeight: 500 }}>{m.prospect_name}</span>
                          </td>
                          <td style={td}>
                            <span style={{ color: "#94a3b8" }}>{m.plumber_name}</span>
                          </td>
                          <td style={{ ...td, textAlign: "center" }}>
                            <span
                              style={{
                                background: m.match_score >= 90 ? "#064e3b" : m.match_score >= 60 ? "#1e3a5f" : "#1e293b",
                                color: m.match_score >= 90 ? "#34d399" : m.match_score >= 60 ? "#60a5fa" : "#475569",
                                padding: "3px 10px",
                                borderRadius: 20,
                                fontSize: 12,
                                fontWeight: 700,
                              }}
                            >
                              {m.match_score}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginTop: 20,
                    paddingTop: 16,
                    borderTop: "1px solid #334155",
                  }}
                >
                  <span style={{ color: "#64748b", fontSize: 12 }}>
                    Showing {startRow.toLocaleString()}-{endRow.toLocaleString()} of{" "}
                    {total.toLocaleString()}
                  </span>

                  <div style={{ display: "flex", gap: 6 }}>
                    <PaginationBtn
                      label="First"
                      onClick={() => setPage(1)}
                      disabled={page === 1}
                    />
                    <PaginationBtn
                      label="Prev"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                    />

                    <span
                      style={{
                        color: "#f1f5f9",
                        fontSize: 13,
                        padding: "6px 12px",
                        background: "#334155",
                        borderRadius: 6,
                        fontWeight: 600,
                      }}
                    >
                      {page} / {totalPages.toLocaleString()}
                    </span>

                    <PaginationBtn
                      label="Next"
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    />
                    <PaginationBtn
                      label="Last"
                      onClick={() => setPage(totalPages)}
                      disabled={page === totalPages}
                    />
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function StatCard({
  label,
  value,
  color,
  active,
  onClick,
}: {
  label: string;
  value: number;
  color: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "#1e293b",
        borderRadius: 12,
        padding: "20px 24px",
        border: active ? `2px solid ${color}` : "1px solid #334155",
        cursor: onClick ? "pointer" : "default",
        transition: "border-color 0.2s",
      }}
    >
      <div style={{ fontSize: 32, fontWeight: 700, color, lineHeight: 1 }}>
        {value.toLocaleString()}
      </div>
      <div
        style={{
          fontSize: 12,
          color: "#64748b",
          marginTop: 6,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {label}
      </div>
    </div>
  );
}

function PaginationBtn({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: disabled ? "#1e293b" : "#334155",
        color: disabled ? "#475569" : "#f1f5f9",
        border: "1px solid #334155",
        borderRadius: 6,
        padding: "6px 14px",
        fontSize: 12,
        fontWeight: 500,
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      {label}
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
  color: "#94a3b8",
  fontSize: 13,
};
