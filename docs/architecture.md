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

### Research mode (Phase 4)

`app/research/` answers a free-text topic by researching *across the
whole knowledge base*, unlike Phase 3's comparison/report features where
the user picks specific documents. `research_topic()` runs the topic
through the same retrieval pipeline chat uses (`app.retrieval.service.search`,
hybrid + rerank + query-rewrite) with a wider candidate pool
(`RESEARCH_TOP_K = 15`), then asks the LLM to produce findings, each one
required to name which numbered excerpt(s) support it.

The one place this deliberately extends ThinkDesk's usual "citations are
built from real retrieval results, never parsed from the LLM's claims"
rule: the LLM does choose *which* of the given excerpts back a specific
finding. That's a narrower trust boundary than it sounds -- every citable
excerpt is still a real, retrieved chunk (the LLM cannot invent a
citation's content), an out-of-range or missing excerpt number is silently
dropped, and a finding left with zero valid citations after that
validation is discarded entirely rather than shown ungrounded.

**Source verification is computed by ThinkDesk, not self-reported by the
LLM**: after validating a finding's citations, the code counts how many
*distinct documents* they span. Two or more -> `verified`. Exactly one ->
`single_source`. The LLM is never asked for a confidence score, because an
LLM's self-rated confidence is not a fact -- corroboration across
independently-uploaded documents is.

### Connectors (Phase 7): Gmail, Slack, and Notion

`app/connectors/` is a reusable pattern for third-party integrations,
proven out across **two different auth models**, not just repeated OAuth:

- `crypto.py` -- Fernet encryption for tokens at rest, keyed by
  `CONNECTOR_ENCRYPTION_KEY`. `ConnectorEncryptionNotConfiguredError` if
  unset, matching `LLMNotConfiguredError`'s "fail clearly" pattern rather
  than a plaintext fallback or a crash.
- `oauth_state.py` -- a single-use, short-lived (10 min) in-memory nonce
  store tying an OAuth "state" round trip to the organization and user
  that started it (Google and Slack only -- Notion has no OAuth step).
  This is CSRF protection scoped honestly to what it actually is: enough
  for a single-process dev/demo deployment, explicitly not enough for
  multiple workers (which don't share process memory) -- that would need
  the same nonce in Redis or the database instead.
- `google_oauth.py` / `slack_oauth.py` -- the OAuth provider halves
  (authorize URL, token exchange, list-data call). `router.py`'s
  `_consume_state_or_403()` helper is what both providers' callback routes
  share -- the state/CSRF validation logic is written once, not
  copy-pasted per provider.
- `notion_client.py` -- **no OAuth at all**. Notion's internal-integration
  tokens are pasted directly by the user (from their own Notion integration
  settings); `verify_token()` calls Notion's real API to confirm the token
  works and to derive a human-readable label, since these tokens don't
  carry one the way an OAuth response does. Reuses the exact same
  `ConnectorAccount` model, `crypto.py`, and `service.upsert_connection()`
  as the OAuth providers -- adding a token-based provider needed zero
  changes to the shared machinery, which is the actual proof the
  architecture is reusable, not just repeated.
- `ConnectorAccount` (`app/models/connector.py`) -- one row per connected
  account, scoped to `organization_id` like every other tenant-owned
  table. Its human-readable identifier column is named `account_label`,
  not `account_email` -- Slack and Notion have workspace names, not email
  addresses, and the schema shouldn't quietly assume every future provider
  looks like Google.

All three connectors are deliberately **read-only**: Gmail with
`gmail.readonly` (lists recent messages), Slack with `channels:read`
(lists public channels), Notion with its read-only search endpoint (lists
pages/databases actually shared with the integration -- an empty list is
the honest, expected state until the user shares something, not a bug).
Sending, deleting, posting, or modifying anything is Phase 5 (AI Agents)
territory, and per the master brief's own rule, any such action needs an
explicit human-approval step before it executes -- that's a genuinely
different, not-yet-built feature, not an oversight in any connector.
Slack and Notion tokens also don't expire the way Google's do, so
`get_valid_access_token()` only attempts a refresh for Google accounts --
those `ConnectorAccount` rows never have `token_expires_at` set, so they
always take the "return the stored token" path.

**A real bug this caught**: the migrations adding Slack's and Notion's
enum values used lowercase labels ('slack', 'notion'), but SQLAlchemy's
`Enum` column type serializes a Python str-Enum by its member *name*
by default ('SLACK', 'NOTION') -- matching the original 'GOOGLE' label.
Invisible in the test suite (its database is rebuilt fresh from the
current models every run, so it was always self-consistent), this only
surfaced as a clear Postgres error on the first real connection attempt
against the incrementally-migrated dev database. Fixed with a follow-up
`ALTER TYPE ... RENAME VALUE` migration rather than editing the
already-applied ones.

### Agents (Phase 5): a real propose/approve/execute loop

`app/agents/` builds directly on the connectors above. It's deliberately
separate "propose" and "execute" endpoints, not one "do the thing" call,
because the split *is* the safety mechanism. Two independent propose
functions currently feed the same execute function:

- `draft_email_summary()` (read-only) fetches Gmail messages and asks the
  LLM to summarize them. It cannot post, send, or modify anything -- there
  is no code path from this function to any external write.
- `draft_document_digest()` (read-only) reuses `intelligence`'s document-
  loading code to summarize a document already stored in this workspace's
  own knowledge base -- same read-only guarantee, different source, proving
  the pattern isn't specific to Gmail.
- `post_to_slack()` (the only write, shared by both draft functions above)
  takes an exact message string and a
  channel and posts it. It has no awareness that a "draft" ever existed --
  it posts whatever text it's handed. The only reason approved text ever
  reaches it is that the frontend puts the draft in an editable textarea
  and requires an explicit "Approve & post" click, which calls a
  completely separate endpoint gated to owner/admin.

This means "skip the approval step" isn't a flag to flip or a code path
to bypass -- doing so would require calling `post_to_slack()` directly
with attacker-chosen text, which is exactly the same shape as any other
Slack-posting bug, not a special "agent bypassed its safety check" case.
The safety property comes from there being no function that both drafts
and posts.

`slack_oauth.py::post_message()` is the only call site in the codebase
that writes to Slack, by design -- if a second write action is ever added
(e.g. creating a Slack reminder, sending a Gmail reply), it should be
similarly isolated: one narrow function, one clear "this is where external
state changes" comment, reachable only after an equivalent human-approval
gate.

### Automation (Phase 6): rules that only ever queue

`app/automation/` is the answer this doc gave, before it was built, to the
tension between "automation" and Phase 5's per-action approval rule: an
`AutomationRule` can be run unattended, but *running* it only ever inserts
a `QueuedDraft` row -- it calls the exact same `draft_email_summary()` /
`draft_document_digest()` functions Phase 5 already built, so there is
zero new code path to an external system. Approving a queued draft is the
only write (`approve_queued_draft()`, which itself just calls Phase 5's
`post_to_slack()`), gated to owner/admin like every other write in this
codebase.

Rules are triggered by a "Run now" button today, not a real clock. That's
a deliberate scope cut, not a shortcut around the safety property: a
background scheduler is infrastructure (which process owns it, retries,
missed-run handling) that's orthogonal to *whether unattended automation
can bypass human approval* -- and it can't, regardless of what triggers
`run_rule()`. Swapping "Run now" for a real interval-based scheduler later
means adding a caller, not changing `run_rule()` or the approval gate.

### Billing (Phase 8): Lemon Squeezy

`app/billing/` follows the same "verify, don't trust" discipline as the
rest of the codebase, applied to money:

- `lemonsqueezy.py::create_checkout_url()` calls Lemon Squeezy's API to
  create a real hosted checkout, embedding `organization_id` as
  `custom_data` -- this is how the webhook later knows which ThinkDesk
  workspace a subscription belongs to, since Lemon Squeezy echoes
  `custom_data` back on every subsequent event for that checkout's
  subscription.
- `verify_webhook_signature()` recomputes the HMAC-SHA256 of the **raw**
  request body with the webhook secret and compares it (constant-time,
  via `hmac.compare_digest`) against Lemon Squeezy's `X-Signature` header.
  The router reads `request.body()` before any JSON parsing touches it,
  since re-serializing parsed JSON could produce different bytes than what
  was actually signed. An unsigned or mismatched request gets a 401 before
  `service.apply_webhook_event()` ever runs -- the payload's contents are
  never trusted until the signature proves they came from Lemon Squeezy.
- `service.apply_webhook_event()` is the **only** code path that changes a
  `Subscription` row (`app/models/subscription.py`, one per organization).
  ThinkDesk does not infer plan changes from anything else -- a workspace's
  billing status is exactly what the last verified webhook said it is.
  Non-`subscription_*` events (orders, license keys) are accepted and
  ignored, not rejected, since a webhook can be subscribed to event types
  this code doesn't act on yet.
- The upsert is keyed by `organization_id`, not by Lemon Squeezy's
  subscription id -- a cancel-then-resubscribe produces a new subscription
  id on Lemon Squeezy's side, but must still update the same workspace's
  one row rather than create a second.

Local webhook testing needs a public URL (Lemon Squeezy's servers can't
reach `localhost`); this project uses ngrok's free tier for that, whose
URL changes on every restart -- not suitable for anything beyond
development.

**Live-verified, not just unit-tested**: a real product/variant was
created in the Lemon Squeezy dashboard, a real checkout was completed with
a test-mode card, the resulting webhook was delivered through the ngrok
tunnel and processed, and the resulting `Subscription` row was confirmed
directly in the database -- matching what Lemon Squeezy's own dashboard
reported (1 order, $9.99, 1 new subscription). Both sides of the
integration agreeing independently is stronger evidence than either alone.

### Usage limits (`app/billing/limits.py`)

Ties the subscription status to actual enforcement, not just a nicer
number on a dashboard:

- `is_on_paid_plan()` checks whether the org's `Subscription` (if any) has
  status `active` or `on_trial`.
- `enforce_document_limit()` / `enforce_message_limit()` are called from
  `documents/router.py`'s upload route and `chat/router.py`'s send route
  respectively, *before* the underlying service function runs -- a
  free-plan workspace at its cap gets a `402 Payment Required` naming the
  limit and pointing at the upgrade path, and the document is never
  created / the message is never sent. A paid-plan workspace skips the
  count query entirely.
- `get_usage()` powers the billing page's usage card using the exact same
  counting helpers the enforcement functions call -- the displayed
  "3 / 3 documents" can never disagree with what's actually enforced,
  because it's computed by the same code, not a parallel implementation
  that could drift.

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
