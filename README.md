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

**Phase 1 (V1) — AI Knowledge Assistant — functionally complete.** Signup
→ login → create workspace → upload a PDF → it gets extracted, chunked,
and embedded locally (no API key needed) → ask a question → get back
retrieved, cited sources → chat history is saved. Full pytest suite (22
tests) covers chunking, auth, and — the part that matters most for a
multi-tenant app — that one organization's data is genuinely unreachable
by another.

Two known, honestly-documented gaps: LLM *answer generation* needs a free
Groq API key (retrieval and citations work without one); `pgvector` is
compiled and vendored but not yet installed (a Python fallback is used
instead). See [docs/roadmap.md](docs/roadmap.md) for details.

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
  frontend/    Next.js app (auth pages, health/status widgets)
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
