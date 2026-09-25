"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, GitCompare, Sparkles, Trash2, Upload } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Spinner, PageSpinner } from "@/components/ui/spinner";
import {
  ApiError,
  compareDocuments,
  deleteDocument,
  extractDocument,
  listDocuments,
  uploadDocument,
  type ComparisonResult,
  type DocumentItem,
  type ExtractionResult,
} from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

const STATUS_TONE: Record<DocumentItem["status"], "neutral" | "warning" | "success" | "danger"> = {
  pending: "neutral",
  processing: "warning",
  ready: "success",
  failed: "danger",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ComparisonList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-1 text-sm italic text-muted">{empty}</p>
      ) : (
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-foreground">
          {items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function DocumentsPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);
  const [documents, setDocuments] = useState<DocumentItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [comparing, setComparing] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [extractingId, setExtractingId] = useState<string | null>(null);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [extractions, setExtractions] = useState<Record<string, ExtractionResult>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(() => {
    listDocuments(orgId).then(setDocuments).catch(() => {});
  }, [orgId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while anything is still pending/processing, so status updates
  // show up without a manual refresh.
  useEffect(() => {
    const hasInFlight = documents?.some((d) => d.status === "pending" || d.status === "processing");
    if (!hasInFlight) return;
    const interval = setInterval(refresh, 2000);
    return () => clearInterval(interval);
  }, [documents, refresh]);

  async function handleUpload(file: File) {
    if (file.type !== "application/pdf") {
      setError("Only PDF files are supported right now.");
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const doc = await uploadDocument(orgId, file);
      setDocuments((prev) => [doc, ...(prev ?? [])]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDelete(doc: DocumentItem) {
    if (!window.confirm(`Delete "${doc.filename}"? This can't be undone.`)) return;
    setError(null);
    setDeletingId(doc.id);
    try {
      await deleteDocument(orgId, doc.id);
      setDocuments((prev) => (prev ?? []).filter((d) => d.id !== doc.id));
      setSelected((prev) => prev.filter((id) => id !== doc.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  function toggleSelected(docId: string) {
    setComparison(null);
    setComparisonError(null);
    setSelected((prev) => {
      if (prev.includes(docId)) return prev.filter((id) => id !== docId);
      if (prev.length >= 2) return [prev[1], docId];
      return [...prev, docId];
    });
  }

  async function handleExtract(doc: DocumentItem) {
    setExtractError(null);
    if (extractions[doc.id]) {
      setExtractions((prev) => {
        const next = { ...prev };
        delete next[doc.id];
        return next;
      });
      return;
    }
    setExtractingId(doc.id);
    try {
      const result = await extractDocument(orgId, doc.id);
      setExtractions((prev) => ({ ...prev, [doc.id]: result }));
    } catch (err) {
      setExtractError(err instanceof ApiError ? err.message : "Extraction failed");
    } finally {
      setExtractingId(null);
    }
  }

  async function handleCompare() {
    if (selected.length !== 2) return;
    setComparing(true);
    setComparisonError(null);
    setComparison(null);
    try {
      const result = await compareDocuments(orgId, selected[0], selected[1]);
      setComparison(result);
    } catch (err) {
      setComparisonError(err instanceof ApiError ? err.message : "Comparison failed");
    } finally {
      setComparing(false);
    }
  }

  if (org === undefined || documents === null) {
    return <PageSpinner />;
  }
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
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-10">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Documents</h1>
          <p className="mt-1 text-sm text-muted">
            Upload PDFs to make them searchable in Chat. Select two ready documents to compare them.
          </p>
        </div>

        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files?.[0];
            if (file) handleUpload(file);
          }}
          className={`flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
            dragOver ? "border-brand bg-brand-soft" : "border-border hover:border-brand/40"
          }`}
        >
          <Upload className={`h-6 w-6 ${uploading ? "animate-pulse" : ""} text-muted`} strokeWidth={1.5} />
          <p className="text-sm font-medium text-foreground">
            {uploading ? "Uploading…" : "Drop a PDF here or click to browse"}
          </p>
          <p className="text-xs text-muted">PDF only, up to 20 MB</p>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            disabled={uploading}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUpload(file);
            }}
          />
        </label>

        {error && <Alert>{error}</Alert>}

        {documents.length === 0 ? (
          <Card className="flex flex-col items-center gap-2 px-6 py-12 text-center">
            <FileText className="h-7 w-7 text-muted" strokeWidth={1.5} />
            <p className="text-sm text-muted">No documents yet. Upload a PDF to start asking questions about it.</p>
          </Card>
        ) : (
          <>
            <ul className="flex flex-col gap-2">
              {documents.map((doc) => (
                <li key={doc.id}>
                  <Card className="flex flex-col gap-3 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <input
                          type="checkbox"
                          checked={selected.includes(doc.id)}
                          onChange={() => toggleSelected(doc.id)}
                          disabled={doc.status !== "ready"}
                          aria-label={`Select ${doc.filename} for comparison`}
                          className="h-4 w-4 shrink-0 accent-brand disabled:opacity-30"
                        />
                        <FileText className="h-5 w-5 shrink-0 text-muted" strokeWidth={1.5} />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">{doc.filename}</p>
                          <p className="text-xs text-muted">
                            {formatSize(doc.size_bytes)}
                            {doc.page_count !== null ? ` · ${doc.page_count} page(s)` : ""}
                          </p>
                          {doc.error_message && <p className="mt-0.5 text-xs text-red-500">{doc.error_message}</p>}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-3">
                        <Badge tone={STATUS_TONE[doc.status]}>{doc.status}</Badge>
                        {doc.status === "ready" && (
                          <button
                            onClick={() => handleExtract(doc)}
                            disabled={extractingId === doc.id}
                            aria-label={`Extract key information from ${doc.filename}`}
                            className="text-muted transition-colors hover:text-brand disabled:opacity-50"
                          >
                            {extractingId === doc.id ? <Spinner className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(doc)}
                          disabled={deletingId === doc.id}
                          aria-label={`Delete ${doc.filename}`}
                          className="text-muted transition-colors hover:text-red-500 disabled:opacity-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    {extractions[doc.id] && (
                      <div className="rounded-lg bg-surface p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                          Extracted information
                          {extractions[doc.id].truncated && " (from an excerpt — document is long)"}
                        </p>
                        {extractions[doc.id].fields.length === 0 ? (
                          <p className="mt-1 text-sm italic text-muted">No extractable facts found.</p>
                        ) : (
                          <dl className="mt-2 flex flex-col gap-1">
                            {extractions[doc.id].fields.map((field, i) => (
                              <div key={i} className="flex gap-2 text-sm">
                                <dt className="shrink-0 font-medium text-foreground">{field.label}:</dt>
                                <dd className="text-muted">{field.value}</dd>
                              </div>
                            ))}
                          </dl>
                        )}
                      </div>
                    )}
                  </Card>
                </li>
              ))}
            </ul>

            {extractError && <Alert>{extractError}</Alert>}

            {selected.length === 2 && (
              <Button onClick={handleCompare} disabled={comparing} className="self-start">
                {comparing ? <Spinner className="h-4 w-4" /> : <GitCompare className="h-4 w-4" />}
                Compare selected documents
              </Button>
            )}

            {comparisonError && <Alert>{comparisonError}</Alert>}

            {comparison && (
              <Card className="flex flex-col gap-4 p-5">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-muted">
                    {comparison.document_a} vs. {comparison.document_b}
                    {comparison.truncated && " (long documents — compared on an excerpt)"}
                  </p>
                  <p className="mt-1 text-sm text-foreground">{comparison.summary}</p>
                </div>
                <ComparisonList title="Similarities" items={comparison.similarities} empty="None noted." />
                <ComparisonList title="Differences" items={comparison.differences} empty="None noted." />
                <ComparisonList
                  title="Possible contradictions"
                  items={comparison.contradictions}
                  empty="None found."
                />
              </Card>
            )}
          </>
        )}
      </main>
    </>
  );
}
