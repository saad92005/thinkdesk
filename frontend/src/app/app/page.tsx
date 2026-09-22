"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ApiError, createOrganization, fetchCurrentUser, listOrganizations, type Organization } from "@/lib/api";

export default function WorkspacesPage() {
  const router = useRouter();
  const [orgs, setOrgs] = useState<Organization[] | null>(null);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchCurrentUser().then((user) => {
      if (cancelled) return;
      if (!user) {
        router.push("/login");
        return;
      }
      listOrganizations().then((data) => !cancelled && setOrgs(data));
    });
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setCreating(true);
    try {
      const org = await createOrganization(newName);
      setOrgs((prev) => [...(prev ?? []), org]);
      setNewName("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create workspace");
    } finally {
      setCreating(false);
    }
  }

  if (orgs === null) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-neutral-400">Loading workspaces…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-16">
      <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">Your workspaces</h1>

      <ul className="flex flex-col gap-2">
        {orgs.map((org) => (
          <li key={org.id}>
            <Link
              href={`/app/${org.id}`}
              className="flex items-center justify-between rounded-md border border-neutral-200 px-4 py-3 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
            >
              <span className="font-medium text-neutral-900 dark:text-neutral-100">{org.name}</span>
              <span className="text-xs uppercase text-neutral-400">{org.role}</span>
            </Link>
          </li>
        ))}
      </ul>

      <form onSubmit={handleCreate} className="flex gap-2 border-t border-neutral-200 pt-6 dark:border-neutral-800">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New workspace name"
          required
          className="flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
        <button
          type="submit"
          disabled={creating}
          className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900"
        >
          Create
        </button>
      </form>
      {error && <p className="text-sm text-red-500">{error}</p>}
    </main>
  );
}
