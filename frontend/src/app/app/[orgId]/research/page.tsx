"use client";

import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Search } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import { ApiError, runResearch, type ResearchReport } from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

export default function ResearchPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);
  const [topic, setTopic] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ResearchReport | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!topic.trim()) return;
    setRunning(true);
    setError(null);
    setReport(null);
    try {
      const result = await runResearch(orgId, topic.trim());
      setReport(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Research failed");
    } finally {
      setRunning(false);
    }
  }

  if (org === undefined) return <PageSpinner />;
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
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-foreground">
            <Search className="h-5 w-5 text-brand" />
            Research
          </h1>
          <p className="mt-1 text-sm text-muted">
            Ask about a topic and get findings drawn from across this workspace&apos;s entire knowledge base, each
            one cited — and marked as corroborated by multiple documents or resting on just one.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. What is our remote work policy?"
            className="min-w-0 flex-1"
          />
          <Button type="submit" disabled={running || !topic.trim()}>
            {running ? <Spinner className="h-4 w-4" /> : <Search className="h-4 w-4" />}
            Research
          </Button>
        </form>

        {error && <Alert>{error}</Alert>}

        {report && (
          <div className="flex flex-col gap-4">
            <Card className="p-5">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">{report.topic}</p>
              <p className="mt-1 text-sm text-foreground">{report.summary}</p>
              {report.documents_used.length > 0 && (
                <p className="mt-2 text-xs text-muted">Drawing on: {report.documents_used.join(", ")}</p>
              )}
            </Card>

            {report.findings.length === 0 ? (
              <Card className="p-5 text-center text-sm text-muted">No grounded findings for this topic yet.</Card>
            ) : (
              <ul className="flex flex-col gap-3">
                {report.findings.map((finding, i) => (
                  <li key={i}>
                    <Card className="flex flex-col gap-2 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm text-foreground">{finding.claim}</p>
                        <Badge tone={finding.confidence === "verified" ? "success" : "warning"}>
                          {finding.confidence === "verified" ? "verified · 2+ sources" : "single source"}
                        </Badge>
                      </div>
                      <div className="flex flex-col gap-1.5 border-t border-border pt-2">
                        {finding.citations.map((citation, j) => (
                          <p key={j} className="text-xs text-muted">
                            <span className="font-medium text-foreground">
                              {citation.filename}
                              {citation.page_number !== null ? `, p.${citation.page_number}` : ""}:
                            </span>{" "}
                            &ldquo;{citation.snippet}&rdquo;
                          </p>
                        ))}
                      </div>
                    </Card>
                  </li>
                ))}
              </ul>
            )}

            {report.gaps.length > 0 && (
              <Card className="p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Not covered by the knowledge base
                </h3>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-muted">
                  {report.gaps.map((gap, i) => (
                    <li key={i}>{gap}</li>
                  ))}
                </ul>
              </Card>
            )}
          </div>
        )}
      </main>
    </>
  );
}
