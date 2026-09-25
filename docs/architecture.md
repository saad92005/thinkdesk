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

### Retrieval (Steps 11–12, hybrid search Step 17, reranking Step 18, query rewriting Step 19)

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

Retrieval is **hybrid**, not vector-only: `hybrid_search()` runs the
cosine-similarity ranking above alongside a BM25 keyword ranking
(`rank_bm25`) over the same org-scoped chunks, then combines the two
rankings with Reciprocal Rank Fusion (by rank position, not raw score,
since BM25 and cosine scores aren't on comparable scales). This catches
exact terms — names, codes, numbers — that a semantic embedding can blur
together, without giving up semantic matching for paraphrased questions.
Both `/search` and `/chat` go through `search()` in
`app/retrieval/service.py`, so both benefit automatically.

Before any of that, `search()` **rewrites the query**
(`app/retrieval/query_rewrite.py`): it asks the LLM for up to 2 alternate
phrasings of the question (synonyms, expanded abbreviations, a more
keyword-heavy version), runs hybrid search once per variant (original
included), and merges the results by chunk id, keeping each chunk's best
fusion score. This catches the common case where a user's wording shares
little vocabulary with the source document (e.g. "refund policy" vs. a
document that only says "reimbursement terms") -- something neither BM25
nor a single embedding lookup can fix on their own. If no LLM is
configured, or the rewrite call fails, `rewrite_query()` returns just the
original query -- rewriting is a recall enhancement, never a hard
dependency, so search degrades to exactly its pre-Step-19 behavior rather
than breaking.

`search()` then **reranks**: it takes the merged candidate pool (capped at
25 -- free, since hybrid search already scores every org chunk internally
before truncating) and re-scores it with a local cross-encoder
(`app/ai/reranker.py`, fastembed `Xenova/ms-marco-MiniLM-L-6-v2`, ~80MB, no
API key), scored against the *original* query -- rewrites widen what gets
retrieved, but relevance is still judged against what the user actually
asked. A cross-encoder scores the query and a candidate jointly, which is
more precise than comparing two independently-computed embeddings, but too
slow to run over an entire corpus -- which is exactly why it only touches
the shortlist, not every chunk.

One trade-off worth knowing: because `/search` and `/chat` share
`search()`, a configured LLM key means every call to either endpoint now
makes an extra LLM round trip for rewriting, on top of `/chat`'s own
generation call. On Groq's free tier this is usually fine at V1's traffic
levels, but it's a real added cost/latency/rate-limit consumer, not a free
lunch.

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
API (`openai/gpt-oss-120b` by default — Groq's hosted lineup changes over
time, override with `GROQ_MODEL` if this one is ever retired). With no
`GROQ_API_KEY` set, or if the provider call itself fails (bad model name,
rate limit, network issue), chat still runs end-to-end (retrieval,
citations, conversation history) but returns a clear error message
(`LLMNotConfiguredError` / `LLMGenerationError`) instead of crashing or
fabricating an answer.

### RAG evaluation (Step 20)

`app/evaluation/` runs a set of test questions through the *exact same*
retrieval + generation path a real chat message takes
(`app.retrieval.service.search` and the shared prompts in
`app.chat.prompts`) and scores the result two ways:

- **Retrieval hit**: a deterministic check that at least one expected
  keyword appears somewhere in the retrieved context. No LLM judgment
  involved -- this can't be talked into a false pass.
- **Faithfulness / relevance**: an LLM-as-judge call
  (`app/evaluation/service.py::_judge_answer`) scores the generated answer
  0.0-1.0 against the retrieved context, using a separate, narrowly-scoped
  judge prompt. If the judge's response can't be parsed as the expected
  JSON, or no LLM is configured, the score is reported as missing (`null`)
  -- never defaulted to a fake pass or a made-up number.

`POST /organizations/{id}/evaluation/run` (owner/admin/manager only, since
each run costs LLM quota) takes an ad hoc list of test cases and returns a
report with per-case results plus aggregate averages; `/app/[orgId]/evaluation`
is the UI for building a case set and reading the results. There's
deliberately no persisted "eval case library" yet -- each run is
self-contained, which is enough to answer "did my last retrieval/prompt
change help or hurt," the main thing an evaluation framework needs to do
at this stage.

### Document intelligence (Phase 3: comparison + extraction)

`app/intelligence/` holds Phase 3 features: document comparison and
structured extraction, both sharing `_load_document_text()` (org-scoped,
rejects a document that hasn't finished processing) and the same
"extract the first `{...}` block, or report unavailable rather than
guess" response-parsing pattern.

`extract_key_information()` sends a single document's full text to the
LLM with a prompt scoped narrowly to concrete, stated facts (dates,
amounts, named parties, obligations) as label/value pairs, explicitly
instructed not to infer or invent a fact that isn't in the text -- an
empty `fields` list is a valid result for a document with nothing
extractable, not a bug.

`generate_report()` extends the same pattern to up to 5 documents at once:
each is loaded and truncated to a smaller per-document budget
(`REPORT_MAX_CHARS_PER_DOCUMENT`, since several documents share one
prompt), combined into one prompt with an optional user-supplied focus
area, and synthesized into a structured report -- title, overview, key
findings, risks/gaps, recommendations -- grounded strictly in what the
combined excerpts say.

`compare_documents()` loads each document's full chunk text
(ordered by `chunk_index`, org-scoped the same way retrieval is), truncates
either side that exceeds `MAX_CHARS_PER_DOCUMENT` (flagging `truncated:
true` in the response rather than silently comparing a partial document as
if it were complete), and sends both to the LLM with a prompt that asks
for exactly three judgments: similarities, differences, and contradictions
-- grounded strictly in the text given, with an explicit instruction not
to force a contradiction entry when there isn't one. Response parsing
mirrors the evaluation judge's approach: extract the first `{...}` block,
and surface a clear "unavailable" error rather than a guess if it doesn't
parse. A document that hasn't finished processing yet (no chunks) is
rejected with a 409, not silently compared against nothing.

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
