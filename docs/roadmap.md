# ThinkDesk Roadmap

Development proceeds milestone by milestone. Do not skip ahead — each step
should work and be verified before the next begins.

## Phase 1 — AI Knowledge Assistant (V1) — ✅ Complete

| Step | Milestone | Status |
|------|-----------|--------|
| 1 | Project initialization | ✅ Done |
| 2 | Next.js frontend | ✅ Done |
| 3 | FastAPI backend | ✅ Done |
| 4 | PostgreSQL | ✅ Running locally (native install); `pgvector` compiled and vendored but not yet installed into the running instance (needs one elevated copy step) — Python cosine-similarity fallback used until then |
| 5 | Authentication | ✅ Done (email/password, argon2id, server-side sessions) |
| 6 | Organizations / workspaces | ✅ Done (RBAC roles, auto-created workspace on signup, authorization enforced before any data lookup) |
| 7 | PDF upload | ✅ Done (local disk storage, 20MB limit, PDF-only) |
| 8 | Document processing | ✅ Done (pypdf text extraction, runs as a background task) |
| 9 | Chunking | ✅ Done (paragraph-aware, page-tagged, configurable size/overlap) |
| 10 | Embeddings | ✅ Done (local, free — `fastembed`/BAAI/bge-small-en-v1.5, no API key) |
| 11 | pgvector indexing | ⚠️ Fallback in place (Python cosine similarity); native pgvector compiled and vendored, pending one elevated install step |
| 12 | Semantic retrieval | ✅ Done (`POST /organizations/{id}/search`) |
| 13 | LLM generation | ⚠️ Wired up (Groq, OpenAI-compatible), but **no API key configured** — degrades to a clear message instead of crashing or fabricating an answer |
| 14 | Citations | ✅ Done (always built from real retrieval results, never parsed from LLM output) |
| 15 | Chat history | ✅ Done (conversations + messages, scoped to org and owning user) |
| 16 | Testing | ✅ Done (22 pytest tests: chunking, auth security, auth flow, tenant isolation, full upload→search→chat round trip) |

## Phase 2 — Advanced RAG

Hybrid search (BM25 + semantic), reranking, query rewriting, evaluation
framework (Steps 17–20). Not started.

## Phase 3 — Document Intelligence

Comparison, extraction, contradiction detection, report generation. Not
started.

## Phase 4 — Research Mode

Multi-document research with source verification and structured reports.
Not started.

## Phase 5 — AI Agents

Tool use, planning, permission-checked execution, human approval. Not
started.

## Phase 6 — Automation

Triggers, conditions, AI processing, actions. Not started.

## Phase 7 — Integrations

Gmail, Outlook, Drive, OneDrive, Slack, Teams, calendars, CRMs — one
reusable connector architecture, built incrementally. **Blocked on real
developer app registrations/OAuth credentials that only the project owner
can create** — not something that can be built without those accounts.

## Phase 8 — SaaS

RBAC (partially in place via organization roles), usage tracking, plans/
billing, analytics, public API. Billing specifically needs a real payment
provider (e.g. Stripe) account before it can be wired up for real.

---

**Current focus:** V1 (Phase 1) is functionally complete and tested
end-to-end, with two known, clearly-flagged gaps: (1) `pgvector` needs one
elevated copy command to finish installing — see
`backend/vendor/pgvector-win64/README.md`; (2) LLM answer generation needs
a free Groq API key in `backend/.env` (`GROQ_API_KEY=...`) — get one at
https://console.groq.com. Everything else in the pipeline (upload,
processing, chunking, embeddings, retrieval, citations, chat history) is
real and verified, not stubbed.

Next up: Phase 2 (hybrid search, reranking, query rewriting, evaluation)
is the natural next step once an LLM key is available to meaningfully
evaluate answer quality. Phases 5–7 (agents with real external tools,
automation on real external services, integrations) need credentials/
accounts this session cannot create — those should be scoped with the
project owner before implementation starts, per the master brief's own
rule against building ahead of what can actually be verified.
