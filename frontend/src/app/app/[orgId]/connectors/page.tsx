"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Hash, Mail, Plug, Trash2 } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import {
  ApiError,
  deleteConnector,
  getGoogleAuthorizeUrl,
  getSlackAuthorizeUrl,
  listConnectorChannels,
  listConnectorEmails,
  listConnectors,
  type Connector,
  type EmailMessage,
  type OrganizationRole,
  type SlackChannel,
} from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

const CAN_MANAGE: OrganizationRole[] = ["owner", "admin"];

type ExpandedData = { kind: "emails"; items: EmailMessage[] } | { kind: "channels"; items: SlackChannel[] };

const PROVIDER_META = {
  google: { icon: Mail, label: "Gmail (read-only)" },
  slack: { icon: Hash, label: "Slack (read-only)" },
} as const;

export default function ConnectorsPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const searchParams = useSearchParams();
  const org = useOrganization(orgId);
  const [connectors, setConnectors] = useState<Connector[] | null>(null);
  const [connectingProvider, setConnectingProvider] = useState<"google" | "slack" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedByConnector, setExpandedByConnector] = useState<Record<string, ExpandedData>>({});
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const refresh = useCallback(() => {
    listConnectors(orgId).then(setConnectors).catch(() => {});
  }, [orgId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const justConnected = searchParams.get("connected");

  async function handleConnect(provider: "google" | "slack") {
    setError(null);
    setConnectingProvider(provider);
    try {
      const url = provider === "google" ? await getGoogleAuthorizeUrl(orgId) : await getSlackAuthorizeUrl(orgId);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Could not start ${provider} connection`);
      setConnectingProvider(null);
    }
  }

  async function handleToggleExpanded(connector: Connector) {
    if (expandedByConnector[connector.id]) {
      setExpandedByConnector((prev) => {
        const next = { ...prev };
        delete next[connector.id];
        return next;
      });
      return;
    }
    setError(null);
    setLoadingId(connector.id);
    try {
      if (connector.provider === "google") {
        const items = await listConnectorEmails(orgId, connector.id);
        setExpandedByConnector((prev) => ({ ...prev, [connector.id]: { kind: "emails", items } }));
      } else {
        const items = await listConnectorChannels(orgId, connector.id);
        setExpandedByConnector((prev) => ({ ...prev, [connector.id]: { kind: "channels", items } }));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load connector data");
    } finally {
      setLoadingId(null);
    }
  }

  async function handleDelete(connector: Connector) {
    if (!window.confirm(`Disconnect ${connector.account_label}?`)) return;
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

        {justConnected && <Alert tone="info">{justConnected === "google" ? "Gmail" : "Slack"} connected.</Alert>}
        {error && <Alert>{error}</Alert>}

        {canManage && (
          <Card className="flex flex-col gap-3 p-4">
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => handleConnect("google")} disabled={connectingProvider !== null}>
                {connectingProvider === "google" ? <Spinner className="h-4 w-4" /> : <Mail className="h-4 w-4" />}
                Connect Gmail
              </Button>
              <Button
                variant="secondary"
                onClick={() => handleConnect("slack")}
                disabled={connectingProvider !== null}
              >
                {connectingProvider === "slack" ? <Spinner className="h-4 w-4" /> : <Hash className="h-4 w-4" />}
                Connect Slack
              </Button>
            </div>
            <p className="text-xs text-muted">
              Google may show an &quot;unverified app&quot; warning until this app passes Google&apos;s review —
              that&apos;s expected during development. Click through it to continue.
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
            {connectors.map((connector) => {
              const meta = PROVIDER_META[connector.provider];
              const Icon = meta.icon;
              const expanded = expandedByConnector[connector.id];

              return (
                <li key={connector.id}>
                  <Card className="flex flex-col gap-3 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <Icon className="h-5 w-5 text-muted" strokeWidth={1.5} />
                        <div>
                          <p className="text-sm font-medium text-foreground">{connector.account_label}</p>
                          <p className="text-xs text-muted">{meta.label}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleToggleExpanded(connector)}
                          disabled={loadingId === connector.id}
                        >
                          {loadingId === connector.id ? (
                            <Spinner className="h-4 w-4" />
                          ) : expanded ? (
                            "Hide"
                          ) : connector.provider === "google" ? (
                            "View recent emails"
                          ) : (
                            "View channels"
                          )}
                        </Button>
                        {canManage && (
                          <button
                            onClick={() => handleDelete(connector)}
                            disabled={deletingId === connector.id}
                            aria-label={`Disconnect ${connector.account_label}`}
                            className="text-muted transition-colors hover:text-red-500 disabled:opacity-50"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {expanded && expanded.kind === "emails" && (
                      <div className="flex flex-col gap-2 border-t border-border pt-3">
                        {expanded.items.length === 0 ? (
                          <p className="text-sm italic text-muted">No recent messages.</p>
                        ) : (
                          expanded.items.map((email) => (
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

                    {expanded && expanded.kind === "channels" && (
                      <div className="flex flex-col gap-2 border-t border-border pt-3">
                        {expanded.items.length === 0 ? (
                          <p className="text-sm italic text-muted">No public channels found.</p>
                        ) : (
                          expanded.items.map((channel) => (
                            <div key={channel.id} className="flex items-center justify-between rounded-lg bg-surface p-3">
                              <p className="text-sm font-medium text-foreground">#{channel.name}</p>
                              <p className="text-xs text-muted">
                                {channel.num_members !== null ? `${channel.num_members} members` : ""}
                                {channel.is_member ? " · joined" : ""}
                              </p>
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </Card>
                </li>
              );
            })}
          </ul>
        )}
      </main>
    </>
  );
}
