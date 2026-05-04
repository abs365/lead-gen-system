"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/",         label: "Dashboard" },
  { href: "/plumbers", label: "Plumbers" },
  { href: "/demand",   label: "Demand" },
  { href: "/matches",  label: "Matches" },
  { href: "/ops",      label: "Ops" },
];

export default function Navigation() {
  const pathname = usePathname();
  return (
    <nav style={{
      background: "#020617",
      borderBottom: "1px solid #1e293b",
      padding: "0 24px",
    }}>
      <div style={{
        maxWidth: 1200,
        margin: "0 auto",
        display: "flex",
        alignItems: "center",
        gap: 8,
        height: 56,
      }}>
        <span style={{
          fontWeight: 800,
          fontSize: 16,
          color: "#3b82f6",
          letterSpacing: "-0.5px",
          marginRight: 16,
        }}>
          LeadGen
        </span>
        {LINKS.map(({ href, label }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              style={{
                padding: "6px 14px",
                borderRadius: 6,
                fontSize: 13,
                fontWeight: 500,
                textDecoration: "none",
                background: active ? "#1e3a5f" : "transparent",
                color: active ? "#60a5fa" : "#64748b",
                transition: "all 0.15s",
              }}
            >
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
