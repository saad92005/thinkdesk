"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, FlaskConical, MessageSquare, Search, Users } from "lucide-react";
import { LogoMark } from "@/components/ui/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { UserMenu } from "@/components/user-menu";
import { cn } from "@/lib/cn";

export function OrgNav({ orgId, orgName }: { orgId: string; orgName: string }) {
  const pathname = usePathname();

  const links = [
    { href: `/app/${orgId}/documents`, label: "Documents", icon: FileText },
    { href: `/app/${orgId}/chat`, label: "Chat", icon: MessageSquare },
    { href: `/app/${orgId}/research`, label: "Research", icon: Search },
    { href: `/app/${orgId}/members`, label: "Members", icon: Users },
    { href: `/app/${orgId}/evaluation`, label: "Evaluation", icon: FlaskConical },
  ];

  return (
    <header className="flex items-center justify-between border-b border-border px-6 py-3">
      <div className="flex items-center gap-3 text-sm">
        <Link href="/app" className="flex items-center gap-2 text-muted transition-colors hover:text-foreground">
          <LogoMark className="h-6 w-6" />
          <span className="hidden sm:inline">Workspaces</span>
        </Link>
        <span className="text-border">/</span>
        <span className="font-medium text-foreground">{orgName}</span>
      </div>
      <div className="flex items-center gap-6">
        <nav className="flex gap-1 text-sm">
          {links.map((link) => {
            const active = pathname?.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors",
                  active ? "bg-brand-soft text-brand" : "text-muted hover:bg-black/[.04] dark:hover:bg-white/[.06]"
                )}
              >
                <link.icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </nav>
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
