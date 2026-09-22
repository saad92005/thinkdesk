# ThinkDesk Roadmap

Development proceeds milestone by milestone. Do not skip ahead — each step
should work and be verified before the next begins.

## Phase 1 — AI Knowledge Assistant (V1)

| Step | Milestone | Status |
|------|-----------|--------|
| 1 | Project initialization | ✅ Done |
| 2 | Next.js frontend | ✅ Done |
| 3 | FastAPI backend | ✅ Done |
| 4 | PostgreSQL | ✅ Running locally (native install); `pgvector` deferred to Step 10–11 |
| 5 | Authentication | ⬜ Not started |
| 6 | Organizations / workspaces | ⬜ Not started |
| 7 | PDF upload | ⬜ Not started |
| 8 | Document processing | ⬜ Not started |
| 9 | Chunking | ⬜ Not started |
| 10 | Embeddings | ⬜ Not started |
| 11 | pgvector indexing | ⬜ Not started |
| 12 | Semantic retrieval | ⬜ Not started |
| 13 | LLM generation | ⬜ Not started |
| 14 | Citations | ⬜ Not started |
| 15 | Chat history | ⬜ Not started |
| 16 | Testing | ⬜ Not started |

## Phase 2 — Advanced RAG

Hybrid search (BM25 + semantic), reranking, query rewriting, evaluation
framework (Steps 17–20).

## Phase 3 — Document Intelligence

Comparison, extraction, contradiction detection, report generation.

## Phase 4 — Research Mode

Multi-document research with source verification and structured reports.

## Phase 5 — AI Agents

Tool use, planning, permission-checked execution, human approval.

## Phase 6 — Automation

Triggers, conditions, AI processing, actions.

## Phase 7 — Integrations

Gmail, Outlook, Drive, OneDrive, Slack, Teams, calendars, CRMs — one
reusable connector architecture, built incrementally.

## Phase 8 — SaaS

RBAC, usage tracking, plans/billing, analytics, public API.

---

**Current focus:** V0 is verified end-to-end (frontend, backend, and a
native local PostgreSQL all confirmed working via `/health`). Next up:
Step 5 (Authentication).
