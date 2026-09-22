# ThinkDesk Architecture

## Current state (V1 — AI Knowledge Assistant)

```
User
  |
  v
Next.js frontend (frontend/)
  |  fetch() with credentials: "include"
  v
FastAPI backend (backend/)
  |
  |  app/auth/          -> User, Session
  |  app/organizations/  -> Organization, OrganizationMember (RBAC)
  |  app/documents/      -> Document  (upload, extraction, chunking)
  |  app/ai/             -> EmbeddingProvider, LLMProvider (swappable)
  |  app/retrieval/      -> DocumentChunk search (cosine similarity)
  |  app/chat/           -> Conversation, Message (grounded generation + citations)
  |
  |  SQLAlchemy (async) + asyncpg
  v
PostgreSQL 16 (native local install)
```

- **Frontend**: Next.js 15, App Router, TypeScript, Tailwind CSS. `/signup`
  and `/login` pages; `AuthStatus`/`HealthStatus` widgets show real,
  live-fetched state, never a hardcoded status.
- **Backend layering**: `api/` or feature router → service layer (business
  logic, no FastAPI types) → `database.py` (async SQLAlchemy engine +
  `Base` + `get_db`). Settings via `pydantic-settings`.

### Authorization boundary (the part that matters most)

Every organization-scoped route depends on
`get_organization_membership` (`app/organizations/dependencies.py`), which
runs **before** any document, chunk, or conversation is fetched. A user who
isn't a member of the organization gets a 403 without the retrieval layer
ever running — the LLM is never in a position to leak cross-tenant data
because the data is never fetched for it in the first place. This is
covered by `backend/tests/test_tenant_isolation.py`, not just asserted in
prose.

### Document pipeline (Steps 7–11)

```
Upload (PDF, ≤20MB)
  -> Document row (status=pending), saved to backend/data/uploads/{org_id}/{doc_id}.pdf
  -> BackgroundTask: extract_pages (pypdf) -> chunk_pages (paragraph-aware,
     page-tagged) -> embed (LocalEmbeddingProvider, fastembed, 384-dim,
     no API key) -> DocumentChunk rows
  -> status=ready (or failed, with error_message)
```

BackgroundTasks (FastAPI's built-in, in-process) are used instead of
Celery/Redis — appropriate at V1's scale; if upload volume ever needs a
real job queue, `process_document`'s body moves into a task with the same
signature, and the API contract (upload now, poll `document.status`)
doesn't change.

### Retrieval (Steps 11–12)

`app/retrieval/vector_store.py` fetches an organization's chunks (already
filtered by `organization_id`, not trusted from the caller) and ranks them
by cosine similarity in Python (`numpy`). This is a deliberate, documented
simplification: `pgvector` v0.8.0 has been **compiled from source** against
this machine's PostgreSQL 16 (using the VS Build Tools already installed)
and is vendored at `backend/vendor/pgvector-win64/`, but installing it
needs one elevated (admin) copy step this session can't perform — see that
folder's README. Swapping to a native `vector` column + HNSW index changes
`vector_store.py`'s internals only; `search()`'s signature and every
caller stay the same.

### Chat + citations (Steps 13–15)

`app/chat/service.py` retrieves the top-k chunks for a query, and only
calls the LLM if at least one chunk was found (never generates an
ungrounded answer). The system prompt explicitly tells the model the
context excerpts are untrusted document content, not instructions — see
[security.md](./security.md#prompt-injection). **Citations are built
directly from the retrieval results, not parsed out of the LLM's
response** — so a citation always traces back to a real chunk, even if the
model's phrasing is imprecise.

LLM generation is behind an `LLMProvider` abstraction
(`app/ai/llm.py`) currently implemented for Groq's free, OpenAI-compatible
API. With no `GROQ_API_KEY` set, chat still runs end-to-end (retrieval,
citations, conversation history) but returns a clear "no LLM configured"
message instead of crashing or fabricating an answer.

### Database

PostgreSQL 16, native Windows install (Docker isn't available on this
machine). Schema changes go through Alembic migrations
(`backend/migrations/`) — never hand-edited. `docker-compose.yml` still
targets `pgvector/pgvector:pg16` for anyone running this project with
Docker instead.

## Target architecture (long-term)

```
User
  |
Next.js
  |
API (FastAPI)
  |
Authentication
  |
Authorization
  |
Application Services
  |
AI Orchestration
  |
RAG / Agents / Automation
  |
PostgreSQL + pgvector
  |
Object/File Storage
  |
External Integrations
```

Concerns stay separated as:

```
API Layer -> Service Layer -> Repository/Data Layer
```

Business logic does not live inside route handlers; route handlers call
services, services call repositories/data access. This is already the
shape of `app/{auth,organizations,documents,retrieval,chat}/` — each has
its own `service.py` with no FastAPI imports, tested independently of the
HTTP layer where practical (`test_chunking.py`, `test_auth_security.py`).

## Multi-tenancy

Every table holding customer data (`Document`, `DocumentChunk`,
`Conversation`, `Message`) carries an `organization_id`, and authorization
is enforced before retrieval — not left to the model to decide. See
"Authorization boundary" above; this is implemented, not aspirational, as
of Step 6.
