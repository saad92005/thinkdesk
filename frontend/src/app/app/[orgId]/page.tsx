"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { OrgNav } from "@/components/org-nav";
import { useOrganization } from "@/lib/useOrganization";

export default function OrgHomePage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);

  if (org === undefined) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-neutral-400">Loading…</p>
      </main>
    );
  }

  if (org === null) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-red-500">You don&apos;t have access to this workspace.</p>
      </main>
    );
  }

  return (
    <>
      <OrgNav orgId={orgId} orgName={org.name} />
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center gap-4 px-6">
        <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{org.name}</h1>
        <div className="flex gap-4">
          <Link
            href={`/app/${orgId}/documents`}
            className="rounded-md border border-neutral-200 px-6 py-4 text-center hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
          >
            Documents
          </Link>
          <Link
            href={`/app/${orgId}/chat`}
            className="rounded-md border border-neutral-200 px-6 py-4 text-center hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
          >
            Chat
          </Link>
        </div>
      </main>
    </>
  );
}
