"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/dashboard", label: "Revenue Command Center", icon: "◧" },
  { href: "/claims", label: "Provider Workflow", icon: "▲" },
  { href: "/appeals", label: "Appeals Hub", icon: "✉" },
  { href: "/policies", label: "Policy Intelligence", icon: "▤" },
  { href: "/ask", label: "Ask My Data", icon: "◎" },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-hairline bg-surface">
      <div className="px-5 py-6">
        <div className="text-lg font-semibold tracking-tight text-ink">CuraSense AI</div>
        <div className="text-xs text-ink-muted">Revenue &amp; Insurance Platform</div>
      </div>
      <nav className="flex flex-1 flex-col gap-1 px-3">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                active ? "bg-brand/10 text-brand" : "text-ink-secondary hover:bg-surface-muted"
              }`}
            >
              <span aria-hidden className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-hairline px-5 py-4 text-xs text-ink-muted">
        Signed in as <span className="font-medium text-ink-secondary">Billing Staff</span> (demo)
        <br />
        Synthetic data only - no real PHI
      </div>
    </aside>
  );
}
