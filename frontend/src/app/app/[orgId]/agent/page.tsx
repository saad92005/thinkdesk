"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Bot, CheckCircle2, FileText, Mail, Send } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import {
  ApiError,
  draftDocumentDigest,
  draftEmailSummary,
  listConnectorChannels,
  listConnectors,
  listDocuments,
  postToSlack,
  type Connector,
  type DocumentItem,
  type OrganizationRole,
  type SlackChannel,
} from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

const CAN_EXECUTE: OrganizationRole[] = ["owner", "admin"];
type Source = "gmail" | "document";

export default function AgentPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);
  const [connectors, setConnectors] = useState<Connector[] | null>(null);
  const [channels, setChannels] = useState<SlackChannel[] | null>(null);
  const [selectedChannel, setSelectedChannel] = useState("");
  const [source, setSource] = useState<Source>("gmail");
  const [documents, setDocuments] = useState<DocumentItem[] | null>(null);
  const [selectedDocument, setSelectedDocument] = useState("");

  const [drafting, setDrafting] = useState(false);
  const [draft, setDraft] = useState("");
  const [sourceLabel, setSourceLabel] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);
  const [posted, setPosted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listConnectors(orgId).then(setConnectors).catch(() => {});
    listDocuments(orgId)
      .then((docs) => {
        const ready = docs.filter((d) => d.status === "ready");
        setDocuments(ready);
        if (ready.length > 0) setSelectedDocument(ready[0].id);
      })
      .catch(() => {});
  }, [orgId]);

  const gmail = connectors?.find((c) => c.provider === "google") ?? null;
  const slack = connectors?.find((c) => c.provider === "slack") ?? null;

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

  async function handleDraft() {
    setError(null);
    setPosted(false);
    setDrafting(true);
    try {
      if (source === "gmail") {
        if (!gmail) return;
        const result = await draftEmailSummary(orgId, gmail.id);
        setDraft(result.draft_text);
        setSourceLabel(`${result.source_email_count} recent email(s)`);
      } else {
        if (!selectedDocument) return;
        const result = await draftDocumentDigest(orgId, selectedDocument);
        setDraft(result.draft_text);
        setSourceLabel(`${result.source_document_name}${result.truncated ? " (truncated)" : ""}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not draft summary");
    } finally {
      setDrafting(false);
    }
  }

  async function handleApproveAndPost() {
    if (!slack || !selectedChannel || !draft.trim()) return;
    setError(null);
    setPosting(true);
    try {
      await postToSlack(orgId, slack.id, selectedChannel, draft.trim());
      setPosted(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not post to Slack");
    } finally {
      setPosting(false);
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

  const canExecute = CAN_EXECUTE.includes(org.role);

  return (
    <>
      <OrgNav orgId={orgId} orgName={org.name} />
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-10">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-foreground">
            <Bot className="h-5 w-5 text-brand" />
            Agent: draft &amp; post to Slack
          </h1>
          <p className="mt-1 text-sm text-muted">
            Drafts a summary from Gmail or a document already in this workspace — nothing is sent anywhere until you
            review and explicitly approve it below.
          </p>
        </div>

        {!slack && (
          <Alert tone="info">
            This needs a Slack connector to post to. Connect Slack on the{" "}
            <Link href={`/app/${orgId}/connectors`} className="underline">
              Connectors page
            </Link>{" "}
            first.
          </Alert>
        )}

        {error && <Alert>{error}</Alert>}

        <div className="flex gap-2">
          <Button
            size="sm"
            variant={source === "gmail" ? "primary" : "secondary"}
            onClick={() => {
              setSource("gmail");
              setDraft("");
              setPosted(false);
            }}
          >
            <Mail className="h-4 w-4" /> From Gmail
          </Button>
          <Button
            size="sm"
            variant={source === "document" ? "primary" : "secondary"}
            onClick={() => {
              setSource("document");
              setDraft("");
              setPosted(false);
            }}
          >
            <FileText className="h-4 w-4" /> From a document
          </Button>
        </div>

        {source === "gmail" && !gmail && (
          <Alert tone="info">
            Connect Gmail on the{" "}
            <Link href={`/app/${orgId}/connectors`} className="underline">
              Connectors page
            </Link>{" "}
            to draft from recent email.
          </Alert>
        )}

        {source === "document" && documents !== null && documents.length === 0 && (
          <Alert tone="info">
            No processed documents yet — upload one on the{" "}
            <Link href={`/app/${orgId}/documents`} className="underline">
              Documents page
            </Link>{" "}
            first.
          </Alert>
        )}

        {((source === "gmail" && gmail) || (source === "document" && documents && documents.length > 0)) && (
          <Card className="flex flex-col gap-3 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                {source === "gmail" ? <Mail className="h-4 w-4 text-muted" /> : <FileText className="h-4 w-4 text-muted" />}
                Step 1 — Draft from {source === "gmail" ? gmail!.account_label : "a document"}
              </div>
              <Button size="sm" onClick={handleDraft} disabled={drafting}>
                {drafting ? <Spinner className="h-4 w-4" /> : null}
                {draft ? "Redraft" : "Draft summary"}
              </Button>
            </div>

            {source === "document" && documents && (
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

            {sourceLabel && <p className="text-xs text-muted">Based on: {sourceLabel}.</p>}

            {draft && (
              <textarea
                value={draft}
                onChange={(e) => {
                  setDraft(e.target.value);
                  setPosted(false);
                }}
                rows={6}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
              />
            )}
          </Card>
        )}

        {slack && draft && (
          <Card className="flex flex-col gap-3 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Send className="h-4 w-4 text-muted" />
              Step 2 — Review, then approve &amp; post to Slack
            </div>

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
              <p className="text-xs text-muted">No channels found for this Slack connector.</p>
            )}

            {canExecute ? (
              <Button
                onClick={handleApproveAndPost}
                disabled={posting || !selectedChannel || !draft.trim()}
                className="self-start"
              >
                {posting ? <Spinner className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                Approve &amp; post to Slack
              </Button>
            ) : (
              <p className="text-xs text-muted">Only owners and admins can approve and send.</p>
            )}

            {posted && (
              <Badge tone="success">
                <CheckCircle2 className="h-3 w-3" /> Posted to Slack
              </Badge>
            )}
          </Card>
        )}
      </main>
    </>
  );
}
