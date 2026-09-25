"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { LogOut, Trash2, UserPlus } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import {
  addMember,
  ApiError,
  fetchCurrentUser,
  listMembers,
  removeMember,
  updateMemberRole,
  type Member,
  type OrganizationRole,
} from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

const ASSIGNABLE_ROLES: OrganizationRole[] = ["admin", "manager", "member", "viewer"];
const CAN_MANAGE: OrganizationRole[] = ["owner", "admin"];

export default function MembersPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const router = useRouter();
  const org = useOrganization(orgId);
  const [members, setMembers] = useState<Member[] | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<OrganizationRole>("member");
  const [error, setError] = useState<string | null>(null);
  const [inviting, setInviting] = useState(false);
  const [busyUserId, setBusyUserId] = useState<string | null>(null);

  const refresh = useCallback(() => {
    listMembers(orgId).then(setMembers).catch(() => {});
  }, [orgId]);

  useEffect(() => {
    refresh();
    fetchCurrentUser().then((user) => setCurrentUserId(user?.id ?? null));
  }, [refresh]);

  async function handleInvite(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setInviting(true);
    try {
      const member = await addMember(orgId, email, role);
      setMembers((prev) => [...(prev ?? []), member]);
      setEmail("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add member");
    } finally {
      setInviting(false);
    }
  }

  async function handleRoleChange(userId: string, newRole: OrganizationRole) {
    setError(null);
    setBusyUserId(userId);
    try {
      const updated = await updateMemberRole(orgId, userId, newRole);
      setMembers((prev) => (prev ?? []).map((m) => (m.user_id === userId ? updated : m)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update role");
    } finally {
      setBusyUserId(null);
    }
  }

  async function handleRemove(userId: string, isSelf: boolean) {
    if (!window.confirm(isSelf ? "Leave this workspace?" : "Remove this member from the workspace?")) return;
    setError(null);
    setBusyUserId(userId);
    try {
      await removeMember(orgId, userId);
      setMembers((prev) => (prev ?? []).filter((m) => m.user_id !== userId));
      if (isSelf) router.push("/app");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not remove member");
      setBusyUserId(null);
    }
  }

  if (org === undefined || members === null) {
    return <PageSpinner />;
  }
  if (org === null) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-red-500">You don&apos;t have access to this workspace.</p>
      </main>
    );
  }

  const canManage = CAN_MANAGE.includes(org.role);
  const ownerCount = members.filter((m) => m.role === "owner").length;

  return (
    <>
      <OrgNav orgId={orgId} orgName={org.name} />
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-10">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Members</h1>
          <p className="mt-1 text-sm text-muted">Everyone in this workspace can see all documents and chats.</p>
        </div>

        {canManage && (
          <Card className="p-4">
            <form onSubmit={handleInvite} className="flex flex-wrap gap-2">
              <Input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="teammate@company.com"
                className="min-w-0 flex-1"
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as OrganizationRole)}
                className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
              >
                {ASSIGNABLE_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
              <Button type="submit" disabled={inviting}>
                <UserPlus className="h-4 w-4" />
                Add
              </Button>
            </form>
            <p className="mt-2 text-xs text-muted">
              They need an existing ThinkDesk account with this email — invite emails aren&apos;t sent yet.
            </p>
          </Card>
        )}

        {error && <Alert>{error}</Alert>}

        <ul className="flex flex-col gap-2">
          {members.map((member) => {
            const isSelf = member.user_id === currentUserId;
            const isSoleOwner = member.role === "owner" && ownerCount <= 1;
            const isBusy = busyUserId === member.user_id;
            const canEditThisRow = canManage && !isSoleOwner;
            const canRemoveThisRow = (canManage || isSelf) && !isSoleOwner;

            return (
              <li key={member.user_id}>
                <Card className="flex items-center justify-between gap-3 p-4">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="truncate text-sm font-medium text-foreground">{member.email}</span>
                    {isSelf && <span className="text-xs text-muted">(you)</span>}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {canEditThisRow ? (
                      <select
                        value={member.role}
                        disabled={isBusy}
                        onChange={(e) => handleRoleChange(member.user_id, e.target.value as OrganizationRole)}
                        className="rounded-lg border border-border bg-surface px-2 py-1 text-xs text-foreground focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
                      >
                        {[...ASSIGNABLE_ROLES, "owner"].map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Badge tone={member.role === "owner" ? "info" : "neutral"}>{member.role}</Badge>
                    )}
                    {canRemoveThisRow && (
                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => handleRemove(member.user_id, isSelf)}
                        aria-label={isSelf ? "Leave workspace" : "Remove member"}
                        className="rounded-lg p-1.5 text-muted transition hover:bg-red-500/10 hover:text-red-500 disabled:opacity-50"
                      >
                        {isSelf ? <LogOut className="h-4 w-4" /> : <Trash2 className="h-4 w-4" />}
                      </button>
                    )}
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>
      </main>
    </>
  );
}
