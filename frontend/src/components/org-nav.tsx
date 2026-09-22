"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function OrgNav({ orgId, orgName }: { orgId: string; orgName: string }) {
  const pathname = usePathname();

  const links = [
    { href: `/app/${orgId}/documents`, label: "Documents" },
    { href: `/app/${orgId}/chat`, label: "Chat" },
  ];

  return (
    <header className="flex items-center justify-between border-b border-neutral-200 px-6 py-3 dark:border-neutral-800">
      <div className="flex items-center gap-4">
        <Link href="/app" className="text-sm text-neutral-400 hover:underline">
          Workspaces
        </Link>
        <span className="text-neutral-300">/</span>
        <span className="font-medium text-neutral-900 dark:text-neutral-100">{orgName}</span>
      </div>
      <nav className="flex gap-4 text-sm">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={
              pathname?.startsWith(link.href)
                ? "font-medium text-neutral-900 underline dark:text-neutral-100"
                : "text-neutral-500 hover:underline dark:text-neutral-400"
            }
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
