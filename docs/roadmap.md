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

| Feature | Status |
|---------|--------|
| Document comparison + contradiction detection | ✅ Done — `POST /organizations/{id}/documents/compare` runs two documents' full text through the LLM and returns a grounded summary, similarities, differences, and contradictions (never invented -- an empty contradictions list is a valid, honest result); `/app/[orgId]/documents` UI to select two ready documents and see the report |
| Structured data extraction | ✅ Done — `POST /organizations/{id}/documents/{document_id}/extract` pulls key facts (dates, amounts, parties, obligations) as label/value pairs, grounded strictly in the document's own text; a sparkle button per document on the documents page |
| Report generation | ✅ Done — `POST /organizations/{id}/documents/report` synthesizes up to 5 documents (with an optional focus area) into a structured report: title, overview, key findings, risks/gaps, recommendations, all grounded in the source text |

## Phase 4 — Research Mode — ✅ Complete

`POST /organizations/{id}/research` takes a free-text topic (not a
user-picked document set) and researches it across the *entire* knowledge
base: retrieval (`app/retrieval/service.py::search`, the same hybrid +
rerank + query-rewrite pipeline chat uses) pulls a wide candidate pool,
then the LLM produces findings, each required to cite the specific
retrieved excerpts that support it. Source verification is computed
deterministically, not self-reported by the LLM: a finding backed by
excerpts from 2+ distinct documents is marked `verified`, one backed by
only one document is `single_source` — an honest signal about how
corroborated each claim actually is. A `gaps` list surfaces what the
topic asks that the knowledge base doesn't actually cover. `/app/[orgId]/research`
is the UI. 4 new backend tests (64 total).

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

**Current focus:** Phases 1-4 are all fully complete — AI Knowledge
Assistant, Advanced RAG (hybrid search, reranking, query rewriting, RAG
evaluation), Document Intelligence (comparison, contradiction detection,
extraction, report generation), and Research Mode (topic-driven research
across the whole knowledge base with deterministic multi-source
verification). All of it tested end-to-end and verified live in a real
browser session, not just unit tests -- including a real Playwright run
where the LLM correctly marked a claim `verified` after finding it
corroborated across two separate uploaded documents. One known,
clearly-flagged gap remains: `pgvector` needs one elevated copy command to
finish installing — see `backend/vendor/pgvector-win64/README.md`; the
Python cosine + BM25 + reranking pipeline is correct in the meantime, just
not indexed/scaled.

Next up: Phases 5–7 (AI agents with real external tools, automation on
real external services, third-party integrations like Gmail/Slack) and
Phase 8 (billing) all need credentials/accounts only the project owner can
create -- OAuth app registrations, API keys, a payment provider account.
None of that can be built without those in hand first; see the project
owner's own notes on what's needed for each.
