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
| 12 | Semantic retrieval | ✅ Done (`POST /organizations/{id}/search`), upgraded to hybrid (see Phase 2) |
| 13 | LLM generation | ✅ Done — Groq (`openai/gpt-oss-120b`, OpenAI-compatible API) generating real grounded answers with a configured `GROQ_API_KEY`; still degrades to a clear message (not a crash) if the key is ever missing or the provider call fails |
| 14 | Citations | ✅ Done (always built from real retrieval results, never parsed from LLM output) |
| 15 | Chat history | ✅ Done (conversations + messages, scoped to org and owning user; frontend has a sidebar to list past conversations and switch between them) |
| 16 | Testing | ✅ Done (36 pytest tests: chunking, auth security, auth flow, tenant isolation, hybrid search ranking, reranking, document delete, member invites, full upload→search→chat round trip) |

Also since V1: **document deletion** (`DELETE /organizations/{id}/documents/{id}`), **team invites** (`POST /organizations/{id}/members`, owner/admin-only, honestly limited to inviting people who already have an account — no email provider is configured), and **member role editing/removal** (`PATCH`/`DELETE /organizations/{id}/members/{user_id}`, with a standing invariant that an organization can never be left with zero owners) were added as real CRUD/collaboration gaps, plus a light/dark/system **theme toggle** in the UI.

## Phase 2 — Advanced RAG

| Step | Milestone | Status |
|------|-----------|--------|
| 17 | Hybrid search | ✅ Done — BM25 keyword ranking (`rank_bm25`) fused with vector cosine similarity via Reciprocal Rank Fusion (`app/retrieval/vector_store.py::hybrid_search`); used by both `/search` and `/chat` automatically |
| 18 | Reranking | ✅ Done — local cross-encoder (fastembed, `Xenova/ms-marco-MiniLM-L-6-v2`, free/no API key) re-scores a widened hybrid-search candidate pool (`app/ai/reranker.py`, wired into `app/retrieval/service.py`) |
| 19 | Query rewriting | ✅ Done — LLM generates up to 2 alternate phrasings per query (`app/retrieval/query_rewrite.py`), each run through hybrid search, merged by chunk id, then reranked against the original query |
| 20 | RAG evaluation framework | ✅ Done — `POST /organizations/{id}/evaluation/run` scores test questions through the real retrieval+generation pipeline: a deterministic keyword-in-context retrieval check plus an LLM-as-judge faithfulness/relevance score; `/app/[orgId]/evaluation` UI to build a case set and read the report |

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

**Current focus:** Phase 2 (Advanced RAG) is now fully complete — hybrid
search, reranking, query rewriting, and a RAG evaluation framework (Steps
17–20), all tested end-to-end, including real LLM-generated answers (Groq
`openai/gpt-oss-120b`) and real LLM-judged evaluation scores verified live
in a real browser session — not just retrieval/citations. One known,
clearly-flagged gap remains: `pgvector` needs one elevated copy command to
finish installing — see `backend/vendor/pgvector-win64/README.md`; the
Python cosine + BM25 + reranking pipeline is correct in the meantime, just
not indexed/scaled.

Next up: Phase 3 (Document Intelligence — comparison, extraction,
contradiction detection, report generation) is the next credential-free
milestone. Phases 5–7 (agents with real external tools, automation on real
external services, integrations) need credentials/accounts this session
cannot create — those should be scoped with the project owner before
implementation starts, per the master brief's own rule against building
ahead of what can actually be verified.
