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

**Phase 1 (V1) — AI Knowledge Assistant — functionally complete**, plus
hybrid search (Phase 2, Step 17). Signup → login → create workspace →
upload a PDF → it gets extracted, chunked, and embedded locally (no API
key needed) → ask a question → retrieval fuses vector + BM25 keyword
search (Reciprocal Rank Fusion), then reranks with a local cross-encoder
→ Groq generates a real grounded answer with citations → chat history is
saved and browsable across past conversations. Invite teammates (if they
already have an account) and manage roles per workspace. Full pytest
suite (36 tests) covers chunking, auth, hybrid search + reranking, and —
the part that matters most for a multi-tenant app — that one
organization's data is genuinely unreachable by another.

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
