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

## Phase 5 — AI Agents — 🚧 Started (Gmail-to-Slack summary agent)

`app/agents/` is the first genuine agent action: tool use (Gmail + Slack
connectors), planning (an LLM call that turns raw emails into a draft),
and permission-checked, human-approved execution -- the three things this
phase's definition calls for, actually built, not stubbed.

The flow is a strict two-step propose/approve/execute loop, split across
two separate endpoints so the "execute" step can never be reached
accidentally:

1. `POST /organizations/{id}/agent/draft-email-summary` -- **read-only**.
   Fetches recent Gmail messages through the existing connector and asks
   the LLM to summarize them. Returns the draft text. Nothing is sent or
   posted anywhere; this step alone cannot have any external effect.
2. `POST /organizations/{id}/agent/post-to-slack` -- **the only write**.
   Takes an exact message string and posts it to a chosen Slack channel.
   It has no concept of "the draft" -- it posts whatever text it's given,
   which only reaches it because the UI puts that text in an editable box
   and requires an explicit "Approve & post" click first. Gated to
   owner/admin, unlike the read-only draft step.

`slack_oauth.py::post_message()` is the only place in the codebase that
ever writes to Slack, and its docstring says so -- a deliberate,
findable choke point rather than a capability sprinkled around. Slack's
bot scope grew to `channels:read,chat:write` to support this. New
`/app/[orgId]/agent` UI walks through both steps. 5 new backend tests (81
total), including one asserting the exact human-edited text is what
actually gets sent -- not a re-fetched or re-generated version.

**Deliberately not built**: anything that runs without a human clicking
"Approve" first -- that would violate the master brief's own rule, not
just be an early version of a future feature. See Phase 6 for what
"automation" can honestly mean without breaking that rule.

## Phase 6 — Automation

Triggers, conditions, AI processing, actions. Not started.

Worth flagging now, before it's built: "automation" (running unattended,
e.g. on a schedule) is in real tension with Phase 5's per-action
human-approval rule -- an unattended pipeline has no human standing by to
click "Approve." The honest way to reconcile them, when this gets built,
is approving a *rule* once (e.g. "always OK to draft a daily summary")
rather than skipping approval for the resulting *actions* -- draft
generation can run unattended, but anything Phase 5 currently gates
(actually posting/sending) either still waits for a per-instance approval,
or is scoped to something genuinely safe enough to pre-approve as a
standing policy. Not deciding this by default-approving everything.

## Phase 7 — Integrations — 🚧 Started (Gmail + Slack connectors)

Reusable connector architecture (`app/connectors/`), proven out with two
real integrations sharing the same machinery:

- **OAuth flow**: `GET /organizations/{id}/connectors/{google|slack}/authorize`
  builds a real consent URL for the given provider; `GET /connectors/{provider}/callback`
  exchanges the returned code for tokens and stores the connection. Both
  callbacks share one CSRF-validation helper (`_consume_state_or_403`) --
  the state/nonce logic (`app/connectors/oauth_state.py`) was written once,
  not copy-pasted. Documented as single-process-only; a multi-worker
  deployment would need the nonce store in Redis instead.
- **Encrypted token storage**: access/refresh tokens are Fernet-encrypted
  (`app/connectors/crypto.py`) before being written to the
  `connector_accounts` table, decrypted only in memory when a call to the
  provider's API needs them. Missing encryption key -> clear error, not a
  crash or a plaintext fallback. The account identifier column is named
  `account_label` (not `account_email`) since Slack's identifier is a
  workspace name, not an email.
- **Read-only actions**: `GET /organizations/{id}/connectors/{id}/emails`
  lists recent Gmail messages, auto-refreshing the access token first if
  expired; `GET /organizations/{id}/connectors/{id}/channels` lists public
  Slack channels (Slack bot tokens don't need refreshing).
- `/app/[orgId]/connectors` UI: connect either provider, view emails or
  channels, disconnect.
- 16 connector-related backend tests (76 total), mocking Google's/Slack's
  HTTP endpoints (no real accounts exercised in CI) -- the actual OAuth
  consent click-throughs were verified live in a real browser: Google's
  genuine "Sign in to continue to Thinkdesk" screen, and Slack's genuine
  "Sign in to your workspace" screen, both reached via the correct
  `client_id` for each provider's real registered app.

**Deliberately not built yet**: any action that sends, deletes, posts, or
modifies anything (scopes are `gmail.readonly` / `channels:read` only) --
that's Phase 5's job, and per the master brief's own rule, any such action
needs a human-approval step before it executes, not just before it's
"available." Notion, Outlook, and other connectors follow the same pattern
once their own OAuth credentials are supplied -- each is additional, not a
redesign.

## Phase 8 — SaaS — 🚧 Started (Lemon Squeezy billing)

RBAC is partially in place via organization roles; usage tracking,
analytics, and a public API remain not started. Billing is real, not a
placeholder: **Stripe doesn't support Pakistan-based accounts**, so this
project uses **Lemon Squeezy** instead (a Merchant of Record platform: no
home-country restriction, handles global sales tax compliance, payouts via
bank transfer/Payoneer/Wise).

- `app/billing/lemonsqueezy.py::create_checkout_url()` creates a real
  hosted Lemon Squeezy checkout session via their API, embedding the
  organization's id as `custom_data` so the webhook can later tell which
  workspace subscribed.
- `verify_webhook_signature()` checks Lemon Squeezy's `X-Signature` header
  (HMAC-SHA256 of the *raw* request body) before anything in the payload
  is trusted -- an unsigned or tampered webhook is rejected with 401, not
  processed.
- `app/billing/service.py::apply_webhook_event()` is the **only** place a
  workspace's plan ever changes -- ThinkDesk never infers or guesses a
  plan change, it only reflects what a signature-verified Lemon Squeezy
  webhook actually says happened. One `Subscription` row per organization
  (`app/models/subscription.py`), upserted by organization id so a
  resubscribe after cancellation updates the same row rather than
  creating a second one.
- `POST /organizations/{id}/billing/checkout` (owner/admin only), `GET
  .../billing/subscription`, `POST /billing/lemonsqueezy/webhook`
  (unauthenticated by session -- authenticated by signature instead, since
  Lemon Squeezy's servers call it directly). `/app/[orgId]/billing` UI.
  8 new backend tests (89 total): signature accept/reject/tamper, role
  gating, and a create-then-cancel webhook sequence proving the upsert
  logic updates the right row.
- Verified live: hitting "Subscribe" with no plan configured yet correctly
  surfaces "Lemon Squeezy isn't fully configured... create a Product +
  Variant in the dashboard first" in the UI, rather than a raw 500 --
  exactly the fail-clearly pattern used everywhere else in this codebase.

**One step left to make checkout actually work**: a Product + Variant
(an actual priced plan) needs to exist in the Lemon Squeezy dashboard, and
its variant ID goes in `LEMONSQUEEZY_VARIANT_ID`. The webhook receiver and
signature verification are fully functional independent of that -- only
the "start a checkout" half needs it.

---

**Current focus:** Phases 1-4 are all fully complete — AI Knowledge
Assistant, Advanced RAG (hybrid search, reranking, query rewriting, RAG
evaluation), Document Intelligence (comparison, contradiction detection,
extraction, report generation), and Research Mode (topic-driven research
across the whole knowledge base with deterministic multi-source
verification). Phase 7 (Integrations) has working Gmail and Slack
connectors sharing one reusable OAuth architecture, Phase 5 (AI Agents)
has its first real action (draft a Gmail summary, review it, explicitly
approve before it's posted to Slack), and Phase 8 (SaaS) has real Lemon
Squeezy billing wired up (checkout creation + signature-verified webhook
handling). All of it tested end-to-end (89 backend tests) and verified
live in a real browser session, not just unit tests -- including a real
Playwright run where the LLM correctly marked a claim `verified` after
finding it corroborated across two separate uploaded documents, real
redirects to both Google's and Slack's actual consent screens, and a
real ngrok tunnel confirmed reachable for Lemon Squeezy's webhook
delivery. One known, clearly-flagged gap remains: `pgvector` needs one
elevated copy command to finish installing — see
`backend/vendor/pgvector-win64/README.md`; the Python cosine + BM25 +
reranking pipeline is correct in the meantime, just
not indexed/scaled.

Next up: create a Product + Variant in the Lemon Squeezy dashboard and set
`LEMONSQUEEZY_VARIANT_ID` to actually complete a real subscription
end-to-end (checkout -> webhook -> Subscription row). A second agent
action, or a third connector (Notion's token is already stored, unused),
follow the same now-proven patterns whenever prioritized.
