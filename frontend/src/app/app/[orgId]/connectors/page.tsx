"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Mail, Plug, Trash2 } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import {
  ApiError,
  deleteConnector,
  getGoogleAuthorizeUrl,
  listConnectorEmails,
  listConnectors,
  type Connector,
  type EmailMessage,
  type OrganizationRole,
} from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

const CAN_MANAGE: OrganizationRole[] = ["owner", "admin"];

export default function ConnectorsPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const searchParams = useSearchParams();
  const org = useOrganization(orgId);
  const [connectors, setConnectors] = useState<Connector[] | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailsByConnector, setEmailsByConnector] = useState<Record<string, EmailMessage[]>>({});
  const [loadingEmailsId, setLoadingEmailsId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const refresh = useCallback(() => {
    listConnectors(orgId).then(setConnectors).catch(() => {});
  }, [orgId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const justConnected = searchParams.get("connected") === "google";

  async function handleConnectGoogle() {
    setError(null);
    setConnecting(true);
    try {
      const url = await getGoogleAuthorizeUrl(orgId);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start Google connection");
      setConnecting(false);
    }
  }

  async function handleToggleEmails(connector: Connector) {
    if (emailsByConnector[connector.id]) {
      setEmailsByConnector((prev) => {
        const next = { ...prev };
        delete next[connector.id];
        return next;
      });
      return;
    }
    setError(null);
    setLoadingEmailsId(connector.id);
    try {
      const emails = await listConnectorEmails(orgId, connector.id);
      setEmailsByConnector((prev) => ({ ...prev, [connector.id]: emails }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load emails");
    } finally {
      setLoadingEmailsId(null);
    }
  }

  async function handleDelete(connector: Connector) {
    if (!window.confirm(`Disconnect ${connector.account_email}?`)) return;
    setDeletingId(connector.id);
    try {
      await deleteConnector(orgId, connector.id);
      setConnectors((prev) => (prev ?? []).filter((c) => c.id !== connector.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not disconnect");
    } finally {
      setDeletingId(null);
    }
  }

  if (org === undefined || connectors === null) return <PageSpinner />;
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
          <h1 className="flex items-center gap-2 text-xl font-semibold text-foreground">
            <Plug className="h-5 w-5 text-brand" />
            Connectors
          </h1>
          <p className="mt-1 text-sm text-muted">
            Connect external accounts so ThinkDesk can read from them. Read-only for now — nothing is ever sent or
            deleted on your behalf without an explicit approval step.
          </p>
        </div>

        {justConnected && <Alert tone="info">Google account connected.</Alert>}
        {error && <Alert>{error}</Alert>}

        {canManage && (
          <Card className="p-4">
            <Button onClick={handleConnectGoogle} disabled={connecting}>
              {connecting ? <Spinner className="h-4 w-4" /> : <Mail className="h-4 w-4" />}
              Connect Gmail
            </Button>
            <p className="mt-2 text-xs text-muted">
              You&apos;ll see Google&apos;s consent screen, and possibly an &quot;unverified app&quot; warning until
              this app passes Google&apos;s review — that&apos;s expected during development.
            </p>
          </Card>
        )}

        {connectors.length === 0 ? (
          <Card className="flex flex-col items-center gap-2 px-6 py-12 text-center">
            <Plug className="h-7 w-7 text-muted" strokeWidth={1.5} />
            <p className="text-sm text-muted">No connectors yet.</p>
          </Card>
        ) : (
          <ul className="flex flex-col gap-2">
            {connectors.map((connector) => (
              <li key={connector.id}>
                <Card className="flex flex-col gap-3 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <Mail className="h-5 w-5 text-muted" strokeWidth={1.5} />
                      <div>
                        <p className="text-sm font-medium text-foreground">{connector.account_email}</p>
                        <p className="text-xs text-muted">Gmail (read-only)</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleToggleEmails(connector)}
                        disabled={loadingEmailsId === connector.id}
                      >
                        {loadingEmailsId === connector.id ? (
                          <Spinner className="h-4 w-4" />
                        ) : emailsByConnector[connector.id] ? (
                          "Hide emails"
                        ) : (
                          "View recent emails"
                        )}
                      </Button>
                      {canManage && (
                        <button
                          onClick={() => handleDelete(connector)}
                          disabled={deletingId === connector.id}
                          aria-label={`Disconnect ${connector.account_email}`}
                          className="text-muted transition-colors hover:text-red-500 disabled:opacity-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {emailsByConnector[connector.id] && (
                    <div className="flex flex-col gap-2 border-t border-border pt-3">
                      {emailsByConnector[connector.id].length === 0 ? (
                        <p className="text-sm italic text-muted">No recent messages.</p>
                      ) : (
                        emailsByConnector[connector.id].map((email) => (
                          <div key={email.id} className="rounded-lg bg-surface p-3">
                            <div className="flex items-baseline justify-between gap-2">
                              <p className="text-sm font-medium text-foreground">{email.subject}</p>
                              <p className="shrink-0 text-xs text-muted">{email.date}</p>
                            </div>
                            <p className="text-xs text-muted">{email.sender}</p>
                            <p className="mt-1 text-sm text-muted">{email.snippet}</p>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </Card>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
