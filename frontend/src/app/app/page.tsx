"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Plus, Users } from "lucide-react";
import { ApiError, createOrganization, fetchCurrentUser, listOrganizations, type Organization } from "@/lib/api";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Logo } from "@/components/ui/logo";
import { PageSpinner } from "@/components/ui/spinner";
import { UserMenu } from "@/components/user-menu";

export default function WorkspacesPage() {
  const router = useRouter();
  const [orgs, setOrgs] = useState<Organization[] | null>(null);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

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
      setShowCreateForm(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create workspace");
    } finally {
      setCreating(false);
    }
  }

  if (orgs === null) {
    return <PageSpinner label="Loading workspaces…" />;
  }

  return (
    <>
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-border bg-background px-6 py-3">
        <Link href="/app">
          <Logo />
        </Link>
        <UserMenu />
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-12">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Your workspaces</h1>
            <p className="mt-1 text-sm text-muted">Pick a workspace to manage its documents and chats.</p>
          </div>
          <Button onClick={() => setShowCreateForm((v) => !v)} size="sm">
            <Plus className="h-4 w-4" />
            New workspace
          </Button>
        </div>

        {showCreateForm && (
          <Card className="p-4">
            <form onSubmit={handleCreate} className="flex gap-2">
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Workspace name"
                autoFocus
                required
              />
              <Button type="submit" disabled={creating}>
                {creating ? "Creating…" : "Create"}
              </Button>
            </form>
          </Card>
        )}

        {error && <Alert>{error}</Alert>}

        {orgs.length === 0 ? (
          <Card className="flex flex-col items-center gap-2 px-6 py-16 text-center">
            <Users className="h-8 w-8 text-muted" strokeWidth={1.5} />
            <p className="font-medium text-foreground">No workspaces yet</p>
            <p className="text-sm text-muted">Create one to start uploading documents and asking questions.</p>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {orgs.map((org) => (
              <Link key={org.id} href={`/app/${org.id}`}>
                <Card className="flex items-center justify-between p-4 transition-colors hover:border-brand/40">
                  <span className="font-medium text-foreground">{org.name}</span>
                  <span className="text-xs font-medium uppercase tracking-wide text-muted">{org.role}</span>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
