"use client";

import { useEffect, useState } from "react";
import Navigation from "@/components/Navigation";
import { useAuth } from "@/components/AuthProvider";

const API = "/api/proxy";

export default function AdminPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("user");
  const [message, setMessage] = useState("");

  async function loadUsers() {
    const res = await fetch(`${API}/auth/users`);
    const data = await res.json();
    setUsers(Array.isArray(data) ? data : []);
    setLoading(false);
  }

  useEffect(() => { loadUsers(); }, []);

  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch(`${API}/auth/users`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: newEmail, password: newPassword, name: newName, role: newRole }),
    });
    const data = await res.json();
    if (res.ok) {
      setMessage(`User ${newEmail} created successfully`);
      setNewEmail(""); setNewName(""); setNewPassword(""); setNewRole("user");
      loadUsers();
    } else {
      setMessage(`Error: ${data.detail}`);
    }
  }

  async function toggleUser(id: number) {
   await fetch(`${API}/auth/users/${id}/toggle`, { method: "POST" });
    loadUsers();
  }

  async function deleteUser(id: number) {
    if (!confirm("Delete this user?")) return;
    await fetch(`${API}/auth/users/${id}`, { method: "DELETE" });
    loadUsers();
  }

  if (user?.role !== "admin") {
    return (
      <>
        <Navigation />
        <div style={{ minHeight: "100vh", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p style={{ color: "#ef4444", fontSize: 16 }}>Access denied. Admins only.</p>
        </div>
      </>
    );
  }

  return (
    <>
      <Navigation />
      <div style={{ minHeight: "100vh", background: "#0f172a", padding: "32px 24px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <div style={{ marginBottom: 32 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9" }}>User Management</h1>
            <p style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>Manage who has access to the dashboard</p>
          </div>

          {/* ADD USER */}
          <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155", marginBottom: 24 }}>
            <h2 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 20 }}>
              Add New User
            </h2>
            <form onSubmit={createUser}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
                <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Full name" required style={inputStyle} />
                <input type="email" value={newEmail} onChange={e => setNewEmail(e.target.value)} placeholder="Email address" required style={inputStyle} />
                <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="Password" required style={inputStyle} />
                <select value={newRole} onChange={e => setNewRole(e.target.value)} style={inputStyle}>
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <button type="submit" style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
                Create User
              </button>
              {message && <span style={{ marginLeft: 16, color: message.startsWith("Error") ? "#ef4444" : "#34d399", fontSize: 13 }}>{message}</span>}
            </form>
          </div>

          {/* USER LIST */}
          <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
            <h2 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 20 }}>
              Users ({users.length})
            </h2>
            {loading ? <p style={{ color: "#64748b", fontSize: 13 }}>Loading...</p> : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={th}>Name</th>
                    <th style={th}>Email</th>
                    <th style={th}>Role</th>
                    <th style={th}>Last Login</th>
                    <th style={{ ...th, textAlign: "center" }}>Status</th>
                    <th style={{ ...th, textAlign: "center" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u, i) => (
                    <tr key={u.id} style={{ borderBottom: "1px solid #1e293b" }}>
                      <td style={td}><span style={{ color: "#f1f5f9", fontWeight: 500 }}>{u.name}</span></td>
                      <td style={td}>{u.email}</td>
                      <td style={td}>
                        <span style={{ background: u.role === "admin" ? "#1e3a5f" : "#1e293b", color: u.role === "admin" ? "#60a5fa" : "#94a3b8", padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 600 }}>
                          {u.role}
                        </span>
                      </td>
                      <td style={td}>{u.last_login ? new Date(u.last_login).toLocaleDateString() : "Never"}</td>
                      <td style={{ ...td, textAlign: "center" }}>
                        <span style={{ background: u.is_active ? "#064e3b" : "#431407", color: u.is_active ? "#34d399" : "#fca5a5", padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 600 }}>
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td style={{ ...td, textAlign: "center" }}>
                        <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
                          <button onClick={() => toggleUser(u.id)} style={{ background: "#334155", color: "#94a3b8", border: "none", borderRadius: 6, padding: "4px 10px", fontSize: 11, cursor: "pointer" }}>
                            {u.is_active ? "Disable" : "Enable"}
                          </button>
                          <button onClick={() => deleteUser(u.id)} style={{ background: "#431407", color: "#fca5a5", border: "none", borderRadius: 6, padding: "4px 10px", fontSize: 11, cursor: "pointer" }}>
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

const inputStyle: React.CSSProperties = { background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 14px", color: "#f1f5f9", fontSize: 13, outline: "none", width: "100%", boxSizing: "border-box" };
const th: React.CSSProperties = { textAlign: "left", padding: "8px 12px", color: "#475569", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "1px solid #334155" };
const td: React.CSSProperties = { padding: "10px 12px", color: "#94a3b8", fontSize: 13 };
