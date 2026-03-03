"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "LayoutDashboard" },
  { href: "/dashboard/trends", label: "Trends", icon: "TrendingUp" },
  { href: "/dashboard/ideas", label: "Ideas", icon: "Lightbulb" },
  { href: "/dashboard/scripts", label: "Scripts", icon: "FileText" },
  { href: "/dashboard/seo", label: "SEO", icon: "Search" },
  { href: "/dashboard/content", label: "Content", icon: "Kanban" },
  { href: "/dashboard/analytics", label: "Analytics", icon: "BarChart3" },
  { href: "/dashboard/media-kit", label: "Media Kit", icon: "Briefcase" },
  { href: "/dashboard/profile", label: "DNA Profile", icon: "Dna" },
  { href: "/dashboard/settings", label: "Settings", icon: "Settings" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 flex-col border-r bg-card">
      <div className="flex h-16 items-center gap-2 border-b px-6">
        <span className="text-xl font-bold text-primary">Creator</span>
        <span className="text-xl font-bold">OS</span>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {navItems.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <span className="text-xs">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4">
        <div className="rounded-lg bg-primary/5 p-3">
          <p className="text-xs font-medium text-primary">Agent Status</p>
          <p className="mt-1 text-xs text-muted-foreground">All agents idle</p>
        </div>
      </div>
    </aside>
  );
}
