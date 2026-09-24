"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { FileText, MessageSquare } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Card } from "@/components/ui/card";
import { PageSpinner } from "@/components/ui/spinner";
import { listConversations, listDocuments } from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

export default function OrgHomePage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);
  const [documentCount, setDocumentCount] = useState<number | null>(null);
  const [conversationCount, setConversationCount] = useState<number | null>(null);

  useEffect(() => {
    listDocuments(orgId).then((docs) => setDocumentCount(docs.length)).catch(() => {});
    listConversations(orgId).then((c) => setConversationCount(c.length)).catch(() => {});
  }, [orgId]);

  if (org === undefined) {
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
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-6 px-6 py-16">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">{org.name}</h1>
          <p className="mt-1 text-sm text-muted">What would you like to do?</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Link href={`/app/${orgId}/documents`}>
            <Card className="flex h-full flex-col gap-3 p-6 transition-colors hover:border-brand/40">
              <FileText className="h-7 w-7 text-brand" strokeWidth={1.5} />
              <div>
                <h2 className="font-semibold text-foreground">Documents</h2>
                <p className="mt-1 text-sm text-muted">
                  {documentCount === null ? "—" : `${documentCount} document${documentCount === 1 ? "" : "s"}`}{" "}
                  uploaded
                </p>
              </div>
            </Card>
          </Link>
          <Link href={`/app/${orgId}/chat`}>
            <Card className="flex h-full flex-col gap-3 p-6 transition-colors hover:border-brand/40">
              <MessageSquare className="h-7 w-7 text-brand" strokeWidth={1.5} />
              <div>
                <h2 className="font-semibold text-foreground">Chat</h2>
                <p className="mt-1 text-sm text-muted">
                  {conversationCount === null
                    ? "—"
                    : `${conversationCount} conversation${conversationCount === 1 ? "" : "s"}`}{" "}
                  so far
                </p>
              </div>
            </Card>
          </Link>
        </div>
      </main>
    </>
  );
}
