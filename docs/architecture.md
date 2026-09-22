# ThinkDesk Architecture

## Current state (V0 — Engineering Foundation)

```
User
  |
  v
Next.js frontend (frontend/)
  |  fetch()
  v
FastAPI backend (backend/)
  |  SQLAlchemy (async) + asyncpg
  v
PostgreSQL 16 (native local install)
```

- **Frontend**: Next.js 15, App Router, TypeScript, Tailwind CSS. Renders the
  homepage and calls the backend `/health` endpoint client-side to display
  live, real status (never a hardcoded "all systems operational").
- **Backend**: FastAPI, layered as `api/` (route handlers) → `core/`
  (configuration) → `database.py` (async SQLAlchemy engine). Settings are
  loaded from environment variables via `pydantic-settings`.
- **Database**: PostgreSQL 16. This machine runs it as a native Windows
  install (Docker isn't available here), so the `pgvector` extension is
  **not yet installed** — it isn't needed until the embeddings/retrieval
  milestone (roadmap Steps 10–11). The `docker-compose.yml` still targets
  `pgvector/pgvector:pg16` for anyone running this project with Docker.

Nothing in V0 talks to an LLM, stores documents, or implements
authentication yet — those are later milestones (see
[roadmap.md](./roadmap.md)).

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
services, services call repositories/data access.

## Multi-tenancy

ThinkDesk is a multi-tenant SaaS. Every table that stores customer data will
carry an `organization_id`, and authorization is enforced in the retrieval
layer — before any data reaches an LLM — not left to the model to decide.
This is not yet implemented in V0; it lands with the organizations/workspace
milestone (Step 6).
