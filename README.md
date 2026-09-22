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

**V0 — Engineering Foundation.** Frontend, backend, and database
scaffolding exist and the backend exposes a real `/health` endpoint. No
authentication, document upload, or RAG pipeline yet — that's next.

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
  frontend/    Next.js app
  backend/     FastAPI app
  docs/        Architecture, setup, roadmap
  docker-compose.yml
  .env.example
```

## Documentation

- [Architecture](docs/architecture.md)
- [Setup](docs/setup.md)
- [Roadmap](docs/roadmap.md)
