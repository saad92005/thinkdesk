"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { UserPlus } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import { addMember, ApiError, listMembers, type Member, type OrganizationRole } from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

const ASSIGNABLE_ROLES: OrganizationRole[] = ["admin", "manager", "member", "viewer"];
const CAN_MANAGE: OrganizationRole[] = ["owner", "admin"];

export default function MembersPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);
  const [members, setMembers] = useState<Member[] | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<OrganizationRole>("member");
  const [error, setError] = useState<string | null>(null);
  const [inviting, setInviting] = useState(false);

  const refresh = useCallback(() => {
    listMembers(orgId).then(setMembers).catch(() => {});
  }, [orgId]);

  useEffect(() => {
    refresh();
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
          {members.map((member) => (
            <li key={member.user_id}>
              <Card className="flex items-center justify-between p-4">
                <span className="text-sm font-medium text-foreground">{member.email}</span>
                <Badge tone={member.role === "owner" ? "info" : "neutral"}>{member.role}</Badge>
              </Card>
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
