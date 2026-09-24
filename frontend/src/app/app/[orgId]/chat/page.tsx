"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { MessageSquarePlus, Send, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageSpinner } from "@/components/ui/spinner";
import {
  ApiError,
  getConversationMessages,
  listConversations,
  sendChatMessage,
  type ChatMessage,
  type ConversationSummary,
} from "@/lib/api";
import { cn } from "@/lib/cn";
import { useOrganization } from "@/lib/useOrganization";

let tempIdCounter = 0;

export default function ChatPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshConversations = useCallback(() => {
    // Sidebar list is a convenience, not critical -- leave it stale on
    // transient failure rather than blocking the chat itself.
    listConversations(orgId).then(setConversations).catch(() => {});
  }, [orgId]);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  async function openConversation(id: string) {
    setError(null);
    setConversationId(id);
    try {
      setMessages(await getConversationMessages(orgId, id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load conversation");
    }
  }

  function startNewConversation() {
    setConversationId(null);
    setMessages([]);
    setError(null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (!question) return;

    setError(null);
    setInput("");
    setMessages((prev) => [
      ...prev,
      {
        id: `temp-${tempIdCounter++}`,
        role: "user",
        content: question,
        citations: null,
        created_at: new Date().toISOString(),
      },
    ]);
    setSending(true);

    try {
      const response = await sendChatMessage(orgId, question, conversationId);
      const isNewConversation = conversationId === null;
      setConversationId(response.conversation_id);
      setMessages((prev) => [...prev, response.message]);
      if (isNewConversation) refreshConversations();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  }

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
      <main className="mx-auto flex w-full max-w-4xl flex-1 gap-6 px-6 py-6">
        <aside className="flex w-56 shrink-0 flex-col gap-2 border-r border-border pr-4">
          <Button onClick={startNewConversation} variant="secondary" size="sm" className="justify-start">
            <MessageSquarePlus className="h-4 w-4" />
            New chat
          </Button>
          <div className="flex flex-col gap-1 overflow-y-auto">
            {conversations.length === 0 && <p className="px-1 text-xs text-muted">No conversations yet.</p>}
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                onClick={() => openConversation(conversation.id)}
                className={cn(
                  "truncate rounded-md px-3 py-1.5 text-left text-sm transition-colors",
                  conversation.id === conversationId
                    ? "bg-brand-soft font-medium text-brand"
                    : "text-muted hover:bg-black/[.04] dark:hover:bg-white/[.06]"
                )}
                title={conversation.title}
              >
                {conversation.title || "New conversation"}
              </button>
            ))}
          </div>
        </aside>

        <div className="flex flex-1 flex-col">
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto pb-4">
            {messages.length === 0 && (
              <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center">
                <Sparkles className="h-6 w-6 text-brand" strokeWidth={1.5} />
                <p className="max-w-xs text-sm text-muted">
                  Ask a question about the documents in this workspace. Answers are grounded in what you&apos;ve
                  uploaded and always show their sources.
                </p>
              </div>
            )}
            {messages.map((message) => (
              <div key={message.id} className={message.role === "user" ? "self-end" : "self-start"}>
                <div
                  className={cn(
                    "max-w-lg rounded-lg px-4 py-2 text-sm",
                    message.role === "user"
                      ? "bg-brand text-brand-foreground"
                      : "border border-border text-foreground [&_ol]:list-decimal [&_ol]:pl-5 [&_p+p]:mt-2 [&_ul]:list-disc [&_ul]:pl-5"
                  )}
                >
                  {message.role === "assistant" ? (
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  ) : (
                    message.content
                  )}
                </div>
                {message.citations && message.citations.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1">
                    {message.citations.map((citation) => (
                      <div
                        key={citation.chunk_id}
                        className="max-w-lg rounded border border-border bg-surface px-3 py-1.5 text-xs text-muted"
                      >
                        <span className="font-medium text-foreground">
                          {citation.filename}
                          {citation.page_number !== null ? ` — page ${citation.page_number}` : ""}
                        </span>
                        <p className="mt-0.5 line-clamp-2">{citation.snippet}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {sending && <p className="text-sm text-muted">Thinking…</p>}
          </div>

          {error && <Alert>{error}</Alert>}

          <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border pt-4">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents…"
            />
            <Button type="submit" disabled={sending}>
              <Send className="h-4 w-4" />
              Send
            </Button>
          </form>
        </div>
      </main>
    </>
  );
}
