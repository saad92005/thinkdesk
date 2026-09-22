"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { OrgNav } from "@/components/org-nav";
import { ApiError, listDocuments, uploadDocument, type DocumentItem } from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

const STATUS_COLOR: Record<DocumentItem["status"], string> = {
  pending: "text-neutral-400",
  processing: "text-amber-500",
  ready: "text-emerald-500",
  failed: "text-red-500",
};

export default function DocumentsPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);
  const [documents, setDocuments] = useState<DocumentItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
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

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
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
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-neutral-400">Loading…</p>
      </main>
    );
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
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">Documents</h1>
          <label className="cursor-pointer rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white dark:bg-neutral-100 dark:text-neutral-900">
            {uploading ? "Uploading…" : "Upload PDF"}
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              disabled={uploading}
              onChange={handleFileChange}
            />
          </label>
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        {documents.length === 0 ? (
          <p className="text-sm text-neutral-400">
            No documents yet. Upload a PDF to start asking questions about it.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between rounded-md border border-neutral-200 px-4 py-3 dark:border-neutral-800"
              >
                <div>
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{doc.filename}</p>
                  {doc.error_message && <p className="text-xs text-red-500">{doc.error_message}</p>}
                  {doc.page_count !== null && (
                    <p className="text-xs text-neutral-400">{doc.page_count} page(s)</p>
                  )}
                </div>
                <span className={`text-xs font-medium uppercase ${STATUS_COLOR[doc.status]}`}>{doc.status}</span>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
