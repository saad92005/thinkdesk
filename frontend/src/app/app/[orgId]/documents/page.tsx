"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Upload } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { PageSpinner } from "@/components/ui/spinner";
import { ApiError, listDocuments, uploadDocument, type DocumentItem } from "@/lib/api";
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

export default function DocumentsPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);
  const [documents, setDocuments] = useState<DocumentItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
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
          <p className="mt-1 text-sm text-muted">Upload PDFs to make them searchable in Chat.</p>
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
          <ul className="flex flex-col gap-2">
            {documents.map((doc) => (
              <li key={doc.id}>
                <Card className="flex items-center justify-between gap-3 p-4">
                  <div className="flex min-w-0 items-center gap-3">
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
                  <Badge tone={STATUS_TONE[doc.status]}>{doc.status}</Badge>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
