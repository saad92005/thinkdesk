"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CheckCircle2, FileText, Mail, Play, Plus, Trash2, X, Zap } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import {
  ApiError,
  approveQueuedDraft,
  createAutomationRule,
  deleteAutomationRule,
  dismissQueuedDraft,
  listAutomationQueue,
  listAutomationRules,
  listConnectorChannels,
  listConnectors,
  listDocuments,
  runAutomationRule,
  type AutomationRule,
  type Connector,
  type DocumentItem,
  type OrganizationRole,
  type QueuedDraft,
  type SlackChannel,
} from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

const CAN_EXECUTE: OrganizationRole[] = ["owner", "admin"];

export default function AutomationPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);

  const [connectors, setConnectors] = useState<Connector[] | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[] | null>(null);
  const [rules, setRules] = useState<AutomationRule[] | null>(null);
  const [queue, setQueue] = useState<QueuedDraft[] | null>(null);
  const [channels, setChannels] = useState<SlackChannel[] | null>(null);

  const [name, setName] = useState("");
  const [source, setSource] = useState<"gmail" | "document">("document");
  const [selectedDocument, setSelectedDocument] = useState("");
  const [selectedChannel, setSelectedChannel] = useState("");
  const [creating, setCreating] = useState(false);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [editingDraft, setEditingDraft] = useState<Record<string, string>>({});
  const [busyDraftId, setBusyDraftId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const gmail = connectors?.find((c) => c.provider === "google") ?? null;
  const slack = connectors?.find((c) => c.provider === "slack") ?? null;

  async function refresh() {
    const [rulesData, queueData] = await Promise.all([listAutomationRules(orgId), listAutomationQueue(orgId)]);
    setRules(rulesData);
    setQueue(queueData);
  }

  useEffect(() => {
    listConnectors(orgId).then(setConnectors).catch(() => {});
    listDocuments(orgId)
      .then((docs) => {
        const ready = docs.filter((d) => d.status === "ready");
        setDocuments(ready);
        if (ready.length > 0) setSelectedDocument(ready[0].id);
      })
      .catch(() => {});
    refresh().catch(() => {});
  }, [orgId]);

  useEffect(() => {
    if (!slack) return;
    listConnectorChannels(orgId, slack.id)
      .then((list) => {
        setChannels(list);
        const joined = list.find((c) => c.is_member);
        if (joined) setSelectedChannel(joined.id);
      })
      .catch(() => {});
  }, [orgId, slack]);

  async function handleCreateRule() {
    if (!slack || !selectedChannel || !name.trim()) return;
    if (source === "document" && !selectedDocument) return;
    if (source === "gmail" && !gmail) return;
    setError(null);
    setCreating(true);
    try {
      await createAutomationRule(orgId, {
        name: name.trim(),
        source,
        document_id: source === "document" ? selectedDocument : undefined,
        gmail_connector_id: source === "gmail" ? gmail!.id : undefined,
        slack_connector_id: slack.id,
        channel_id: selectedChannel,
      });
      setName("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create rule");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteRule(ruleId: string) {
    setError(null);
    try {
      await deleteAutomationRule(orgId, ruleId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete rule");
    }
  }

  async function handleRunRule(ruleId: string) {
    setError(null);
    setRunningId(ruleId);
    try {
      await runAutomationRule(orgId, ruleId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not run rule");
    } finally {
      setRunningId(null);
    }
  }

  async function handleApprove(draft: QueuedDraft) {
    const message = (editingDraft[draft.id] ?? draft.draft_text).trim();
    if (!message) return;
    setError(null);
    setBusyDraftId(draft.id);
    try {
      await approveQueuedDraft(orgId, draft.id, message);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not post to Slack");
    } finally {
      setBusyDraftId(null);
    }
  }

  async function handleDismiss(draftId: string) {
    setError(null);
    setBusyDraftId(draftId);
    try {
      await dismissQueuedDraft(orgId, draftId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not dismiss draft");
    } finally {
      setBusyDraftId(null);
    }
  }

  if (org === undefined || connectors === null || rules === null || queue === null) return <PageSpinner />;
  if (org === null) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-red-500">You don&apos;t have access to this workspace.</p>
      </main>
    );
  }

  const canExecute = CAN_EXECUTE.includes(org.role);

  return (
    <>
      <OrgNav orgId={orgId} orgName={org.name} />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-10">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-foreground">
            <Zap className="h-5 w-5 text-brand" />
            Automation
          </h1>
          <p className="mt-1 text-sm text-muted">
            Save a recipe once, run it whenever you like — running a rule only ever queues a draft below. Nothing
            reaches Slack until you personally approve a specific draft, same rule as the Agent page.
          </p>
        </div>

        {!slack && (
          <Alert tone="info">
            This needs a Slack connector. Connect Slack on the{" "}
            <Link href={`/app/${orgId}/connectors`} className="underline">
              Connectors page
            </Link>{" "}
            first.
          </Alert>
        )}

        {error && <Alert>{error}</Alert>}

        {slack && (
          <Card className="flex flex-col gap-3 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Plus className="h-4 w-4 text-muted" />
              New automation rule
            </div>

            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Rule name, e.g. Weekly handbook digest"
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
            />

            <div className="flex gap-2">
              <Button size="sm" variant={source === "document" ? "primary" : "secondary"} onClick={() => setSource("document")}>
                <FileText className="h-4 w-4" /> Document
              </Button>
              <Button size="sm" variant={source === "gmail" ? "primary" : "secondary"} onClick={() => setSource("gmail")} disabled={!gmail}>
                <Mail className="h-4 w-4" /> Gmail
              </Button>
            </div>

            {source === "document" && documents && documents.length > 0 && (
              <select
                value={selectedDocument}
                onChange={(e) => setSelectedDocument(e.target.value)}
                className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
              >
                {documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.filename}
                  </option>
                ))}
              </select>
            )}
            {source === "document" && documents && documents.length === 0 && (
              <p className="text-xs text-muted">
                No processed documents yet — upload one on the{" "}
                <Link href={`/app/${orgId}/documents`} className="underline">
                  Documents page
                </Link>
                .
              </p>
            )}
            {source === "gmail" && !gmail && (
              <p className="text-xs text-muted">
                Connect Gmail on the{" "}
                <Link href={`/app/${orgId}/connectors`} className="underline">
                  Connectors page
                </Link>{" "}
                first.
              </p>
            )}

            {channels && channels.length > 0 ? (
              <select
                value={selectedChannel}
                onChange={(e) => setSelectedChannel(e.target.value)}
                className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
              >
                {channels.map((c) => (
                  <option key={c.id} value={c.id} disabled={!c.is_member}>
                    #{c.name} {!c.is_member ? "(bot not in channel)" : ""}
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-xs text-muted">No Slack channels found.</p>
            )}

            <Button size="sm" onClick={handleCreateRule} disabled={creating} className="self-start">
              {creating ? <Spinner className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              Create rule
            </Button>
          </Card>
        )}

        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-foreground">Rules ({rules.length})</h2>
          {rules.length === 0 && <p className="text-sm text-muted">No automation rules yet.</p>}
          {rules.map((rule) => (
            <Card key={rule.id} className="flex items-center justify-between gap-3 p-4">
              <div>
                <p className="text-sm font-medium text-foreground">{rule.name}</p>
                <p className="text-xs text-muted">
                  Source: {rule.source} · Channel: #{rule.channel_id} ·{" "}
                  {rule.last_run_at ? `last run ${new Date(rule.last_run_at).toLocaleString()}` : "never run"}
                </p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" onClick={() => handleRunRule(rule.id)} disabled={runningId === rule.id}>
                  {runningId === rule.id ? <Spinner className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  Run now
                </Button>
                <Button size="sm" variant="ghost" onClick={() => handleDeleteRule(rule.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>

        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-foreground">Pending approval ({queue.length})</h2>
          {queue.length === 0 && <p className="text-sm text-muted">Nothing waiting for approval.</p>}
          {queue.map((draft) => (
            <Card key={draft.id} className="flex flex-col gap-3 p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-foreground">{draft.rule_name}</p>
                <Badge tone="warning">Awaiting your approval</Badge>
              </div>
              <p className="text-xs text-muted">Based on: {draft.source_label} · destined for #{draft.channel_id}</p>
              <textarea
                value={editingDraft[draft.id] ?? draft.draft_text}
                onChange={(e) => setEditingDraft((prev) => ({ ...prev, [draft.id]: e.target.value }))}
                rows={5}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
              />
              <div className="flex gap-2">
                {canExecute ? (
                  <Button size="sm" onClick={() => handleApprove(draft)} disabled={busyDraftId === draft.id}>
                    {busyDraftId === draft.id ? <Spinner className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                    Approve &amp; post to Slack
                  </Button>
                ) : (
                  <p className="text-xs text-muted">Only owners and admins can approve and send.</p>
                )}
                <Button size="sm" variant="secondary" onClick={() => handleDismiss(draft.id)} disabled={busyDraftId === draft.id}>
                  <X className="h-4 w-4" /> Dismiss
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </main>
    </>
  );
}
