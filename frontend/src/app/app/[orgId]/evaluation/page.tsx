"use client";

import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { FlaskConical, Plus, Trash2 } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import { ApiError, runEvaluation, type EvalCase, type EvalReport, type OrganizationRole } from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

const CAN_RUN: OrganizationRole[] = ["owner", "admin", "manager"];

function ScoreBadge({ label, value }: { label: string; value: number | null }) {
  if (value === null) return <Badge tone="neutral">{label}: n/a</Badge>;
  const tone = value >= 0.7 ? "success" : value >= 0.4 ? "warning" : "danger";
  return (
    <Badge tone={tone}>
      {label}: {Math.round(value * 100)}%
    </Badge>
  );
}

export default function EvaluationPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [question, setQuestion] = useState("");
  const [keywords, setKeywords] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<EvalReport | null>(null);

  function handleAddCase(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setCases((prev) => [
      ...prev,
      {
        question: question.trim(),
        expected_keywords: keywords
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean),
      },
    ]);
    setQuestion("");
    setKeywords("");
  }

  function handleRemoveCase(index: number) {
    setCases((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleRun() {
    setError(null);
    setRunning(true);
    setReport(null);
    try {
      const result = await runEvaluation(orgId, cases);
      setReport(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not run evaluation");
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

  if (!CAN_RUN.includes(org.role)) {
    return (
      <>
        <OrgNav orgId={orgId} orgName={org.name} />
        <main className="mx-auto flex w-full max-w-2xl flex-1 items-center justify-center px-6 py-10">
          <p className="text-sm text-muted">Only owners, admins, and managers can run RAG evaluations.</p>
        </main>
      </>
    );
  }

  return (
    <>
      <OrgNav orgId={orgId} orgName={org.name} />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-foreground">
            <FlaskConical className="h-5 w-5 text-brand" />
            RAG Evaluation
          </h1>
          <p className="mt-1 text-sm text-muted">
            Build a set of test questions for this workspace&apos;s documents and score how well retrieval and
            generation actually perform — not a guess, a real run through the same pipeline chat uses.
          </p>
        </div>

        <Card className="flex flex-col gap-4 p-4">
          <form onSubmit={handleAddCase} className="flex flex-col gap-2">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Test question, e.g. What is the refund policy?"
            />
            <div className="flex gap-2">
              <Input
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="Optional expected keywords, comma-separated (e.g. refund, 30 days)"
                className="min-w-0 flex-1"
              />
              <Button type="submit" variant="secondary">
                <Plus className="h-4 w-4" />
                Add case
              </Button>
            </div>
          </form>

          {cases.length > 0 && (
            <ul className="flex flex-col gap-2">
              {cases.map((c, i) => (
                <li key={i} className="flex items-center justify-between gap-2 rounded-lg bg-surface px-3 py-2 text-sm">
                  <div className="min-w-0">
                    <p className="truncate text-foreground">{c.question}</p>
                    {c.expected_keywords.length > 0 && (
                      <p className="truncate text-xs text-muted">expects: {c.expected_keywords.join(", ")}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveCase(i)}
                    aria-label="Remove case"
                    className="shrink-0 rounded-lg p-1.5 text-muted transition hover:bg-red-500/10 hover:text-red-500"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          <Button onClick={handleRun} disabled={cases.length === 0 || running} className="self-start">
            {running && <Spinner className="h-4 w-4" />}
            Run evaluation ({cases.length} case{cases.length === 1 ? "" : "s"})
          </Button>
        </Card>

        {error && <Alert>{error}</Alert>}

        {report && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-2">
              <ScoreBadge
                label="Retrieval hit rate"
                value={report.retrieval_hit_rate}
              />
              <ScoreBadge label="Avg. faithfulness" value={report.average_faithfulness} />
              <ScoreBadge label="Avg. relevance" value={report.average_relevance} />
            </div>

            <ul className="flex flex-col gap-3">
              {report.results.map((result, i) => (
                <li key={i}>
                  <Card className="flex flex-col gap-2 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-medium text-foreground">{result.question}</p>
                      {result.retrieval_hit !== null && (
                        <Badge tone={result.retrieval_hit ? "success" : "danger"}>
                          {result.retrieval_hit ? "retrieval hit" : "retrieval miss"}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted">{result.answer}</p>
                    <div className="flex flex-wrap gap-2 pt-1">
                      <Badge tone="neutral">{result.retrieved_chunk_count} chunk(s) retrieved</Badge>
                      <ScoreBadge label="faithfulness" value={result.faithfulness} />
                      <ScoreBadge label="relevance" value={result.relevance} />
                    </div>
                    {result.judge_notes && <p className="text-xs italic text-muted">{result.judge_notes}</p>}
                  </Card>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
    </>
  );
}
