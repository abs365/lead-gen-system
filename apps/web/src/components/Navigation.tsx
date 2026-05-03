"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/",        label: "Dashboard" },
  { href: "/plumbers", label: "Plumbers" },
  { href: "/demand",   label: "Demand Prospects" },
  { href: "/matches",  label: "Matches" },
  { href: "/ops",      label: "Ops" },
];

export default function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="bg-slate-900 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-8">
        <span className="font-bold text-lg tracking-tight text-blue-400">
          LeadGen
        </span>
        <div className="flex gap-1">
          {LINKS.map(({ href, label }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                  active
                    ? "bg-blue-600 text-white"
                    : "text-slate-300 hover:bg-slate-700 hover:text-white"
                }`}
              >
                {label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
