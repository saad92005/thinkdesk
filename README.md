# THINKDESK

**Find it. Understand it. Get it done.**

ThinkDesk is an AI-powered knowledge workspace: upload documents, ask
questions, get evidence-backed answers with citations, and — later —
compare documents, research topics across your knowledge base, and let AI
agents take approved actions on your behalf.

This is not "chat with your PDF." It's a knowledge + AI + automation
platform, built in stages. See [docs/roadmap.md](docs/roadmap.md) for the
full plan and [docs/architecture.md](docs/architecture.md) for how the
pieces fit together.

## Current status

**Phases 1 through 4 are all fully complete**: AI Knowledge Assistant,
Advanced RAG, Document Intelligence, and Research Mode. **Phase 7
(Integrations) has working Gmail, Slack, and Notion connectors**, **Phase 5
(AI Agents) has two real actions** built on top of them, **Phase 6
(Automation) has saved rules that queue those same actions for approval**,
and **Phase 8 (SaaS) has real billing wired up** — real OAuth flows and a direct-token
flow (Notion) sharing one connector architecture, a genuine
propose-review-approve-execute agent loop (not a demo that skips the
approval step), automation rules that never skip that same step, and
signature-verified Lemon Squeezy checkout + webhooks
(not a fake "Upgrade" button). Signup →
login →
create workspace → upload a PDF → it gets extracted, chunked, and embedded
locally (no API key needed) → ask a question → the LLM rewrites it into
alternate phrasings to widen recall, retrieval fuses vector + BM25 keyword
search across all phrasings (Reciprocal Rank Fusion), then reranks with a
local cross-encoder → Groq generates a real grounded answer with citations
→ chat history is saved and browsable across past conversations. Invite
teammates (if they already have an account), edit roles, or remove
members per workspace. Run a RAG evaluation against your own documents and
get real retrieval-hit and LLM-judged faithfulness/relevance scores. Select
two documents and get a real, grounded comparison — similarities,
differences, and contradictions — extract key facts from a single
document, or generate a synthesized report across up to 5 documents.
Research any topic across your *entire* knowledge base and get findings
that are marked `verified` only when independently corroborated by two or
more separate documents — not the LLM's own opinion of its confidence, an
actually-computed signal. Connect Gmail and read recent messages, connect Slack and list its
channels, or connect Notion (just paste an integration token, no OAuth
needed) and see the pages you've shared with it — all read-only by
default. On top of that, ask the agent to draft a summary of your recent
emails, or a digest of a document already in your workspace, review and
edit it yourself, and only when you click "Approve &
post" does it actually reach Slack — the AI never sends anything without
that explicit human step. Save that same drafting logic as a reusable
automation rule, run it whenever you like (or plug in a real scheduler
later — the code path is identical), and it still only ever queues a draft
for you to approve, never posts on its own. Subscribe to a real plan via Lemon Squeezy
checkout, and a workspace's billing status updates only from a
signature-verified webhook — never guessed or set client-side. The free
plan is capped for real (3 documents, 50 chat messages), enforced
server-side, not just displayed — an active subscription lifts both
automatically. Full pytest suite (105 tests) covers all of the above and —
the part that matters most for a multi-tenant app — that one
organization's data is genuinely unreachable by another.

Billing note: **Stripe doesn't support Pakistan-based accounts**, so this
project uses **Lemon Squeezy** instead (a Merchant of Record platform with
no home-country restriction) — and it's been proven with a real purchase:
a genuine test-mode checkout, a signed webhook delivered and verified, and
the resulting subscription confirmed in both this app's database and Lemon
Squeezy's own dashboard.

One known, honestly-documented gap: `pgvector` is compiled and vendored
but not yet installed into the running Postgres instance (needs one
elevated copy step; a Python fallback is used instead — see
[docs/roadmap.md](docs/roadmap.md) for details).

The product also has a proper interface, not just working endpoints: a
real marketing landing page, a small shared design system (`frontend/src/components/ui/`),
light/dark themes, and consistent branding across the auth flow, workspace
dashboard, document upload, and chat screens.

## Stack

- **Frontend:** Next.js, TypeScript, React, Tailwind CSS
- **Backend:** Python, FastAPI, Pydantic
- **Database:** PostgreSQL + pgvector
- **Infra:** Docker / Docker Compose

## Getting started

See [docs/setup.md](docs/setup.md) for full instructions. Quick version:

```
cp .env.example .env
docker compose up --build
```

Or run the frontend and backend individually without Docker — see the setup
doc for details.

## Project structure

```
thinkdesk/
  frontend/    Next.js app (landing page, auth, workspaces, documents, chat)
    src/components/ui/  Shared design system (Button, Card, Input, etc.)
  backend/     FastAPI app
    app/       auth, organizations, documents, ai, retrieval, chat
    migrations/  Alembic
    tests/     pytest suite
    vendor/    pgvector, compiled from source, pending install
  docs/        Architecture, setup, roadmap, security
  docker-compose.yml
  .env.example
```

## Documentation

- [Architecture](docs/architecture.md)
- [Setup](docs/setup.md)
- [Roadmap](docs/roadmap.md)
