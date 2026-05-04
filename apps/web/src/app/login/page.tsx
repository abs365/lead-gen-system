"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Login failed");
        return;
      }

      localStorage.setItem("auth_token", data.token);
      localStorage.setItem("auth_user", JSON.stringify(data.user));
      router.push("/");
    } catch {
      setError("Connection error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0f172a",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: 24,
    }}>
      <div style={{
        background: "#1e293b",
        borderRadius: 16,
        padding: "48px 40px",
        width: "100%",
        maxWidth: 420,
        border: "1px solid #334155",
      }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 32, fontWeight: 800, color: "#3b82f6", letterSpacing: "-1px", marginBottom: 8 }}>
            LeadGen
          </div>
          <p style={{ color: "#64748b", fontSize: 14 }}>Sign in to your account</p>
        </div>

        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", color: "#94a3b8", fontSize: 13, fontWeight: 500, marginBottom: 8 }}>
              Email address
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              placeholder="you@meritbold.com"
              style={{
                width: "100%",
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: 8,
                padding: "12px 14px",
                color: "#f1f5f9",
                fontSize: 14,
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ marginBottom: 28 }}>
            <label style={{ display: "block", color: "#94a3b8", fontSize: 13, fontWeight: 500, marginBottom: 8 }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              style={{
                width: "100%",
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: 8,
                padding: "12px 14px",
                color: "#f1f5f9",
                fontSize: 14,
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          {error && (
            <div style={{
              background: "#431407",
              border: "1px solid #dc2626",
              borderRadius: 8,
              padding: "10px 14px",
              color: "#fca5a5",
              fontSize: 13,
              marginBottom: 20,
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              background: loading ? "#334155" : "#3b82f6",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "13px",
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}