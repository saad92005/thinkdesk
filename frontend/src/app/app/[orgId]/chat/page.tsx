"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { OrgNav } from "@/components/org-nav";
import {
  ApiError,
  getConversationMessages,
  listConversations,
  sendChatMessage,
  type ChatMessage,
  type ConversationSummary,
} from "@/lib/api";
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
      <main className="mx-auto flex w-full max-w-4xl flex-1 gap-6 px-6 py-6">
        <aside className="flex w-56 shrink-0 flex-col gap-2 border-r border-neutral-200 pr-4 dark:border-neutral-800">
          <button
            onClick={startNewConversation}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-left text-sm font-medium text-neutral-900 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-100 dark:hover:bg-neutral-900"
          >
            + New chat
          </button>
          <div className="flex flex-col gap-1 overflow-y-auto">
            {conversations.length === 0 && (
              <p className="px-1 text-xs text-neutral-400">No conversations yet.</p>
            )}
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                onClick={() => openConversation(conversation.id)}
                className={
                  conversation.id === conversationId
                    ? "truncate rounded-md bg-neutral-900 px-3 py-1.5 text-left text-sm text-white dark:bg-neutral-100 dark:text-neutral-900"
                    : "truncate rounded-md px-3 py-1.5 text-left text-sm text-neutral-600 hover:bg-neutral-50 dark:text-neutral-300 dark:hover:bg-neutral-900"
                }
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
              <p className="text-sm text-neutral-400">
                Ask a question about the documents in this workspace. Answers are grounded in your uploaded
                documents and always show their sources.
              </p>
            )}
            {messages.map((message) => (
              <div key={message.id} className={message.role === "user" ? "self-end" : "self-start"}>
                <div
                  className={
                    message.role === "user"
                      ? "rounded-lg bg-neutral-900 px-4 py-2 text-sm text-white dark:bg-neutral-100 dark:text-neutral-900"
                      : "rounded-lg border border-neutral-200 px-4 py-2 text-sm text-neutral-900 dark:border-neutral-800 dark:text-neutral-100"
                  }
                >
                  {message.content}
                </div>
                {message.citations && message.citations.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1">
                    {message.citations.map((citation) => (
                      <div
                        key={citation.chunk_id}
                        className="rounded border border-neutral-100 bg-neutral-50 px-3 py-1.5 text-xs text-neutral-500 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-400"
                      >
                        <span className="font-medium">
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
            {sending && <p className="text-sm text-neutral-400">Thinking…</p>}
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <form
            onSubmit={handleSubmit}
            className="flex gap-2 border-t border-neutral-200 pt-4 dark:border-neutral-800"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents…"
              className="flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            />
            <button
              type="submit"
              disabled={sending}
              className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900"
            >
              Send
            </button>
          </form>
        </div>
      </main>
    </>
  );
}
