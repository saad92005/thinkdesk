# ThinkDesk Architecture

## Current state (V0 + Step 5 — Authentication)

```
User
  |
  v
Next.js frontend (frontend/)
  |  fetch() with credentials: "include"
  v
FastAPI backend (backend/)
  |  app/auth/  -> app/models/ (User, Session)
  |  SQLAlchemy (async) + asyncpg
  v
PostgreSQL 16 (native local install)
```

- **Frontend**: Next.js 15, App Router, TypeScript, Tailwind CSS. Renders the
  homepage and calls the backend `/health` endpoint client-side to display
  live, real status (never a hardcoded "all systems operational").
  `/signup` and `/login` pages post credentials to the backend; `AuthStatus`
  reads `/auth/me` to show the signed-in user or login/signup links.
- **Backend**: FastAPI, layered as `api/` (route handlers) → `core/`
  (configuration) → `database.py` (async SQLAlchemy engine + `Base` +
  `get_db` dependency). Settings are loaded from environment variables via
  `pydantic-settings`.
- **Auth** (`app/auth/`): `security.py` (argon2id password hashing, session
  token generation/hashing), `service.py` (signup/authenticate/session
  business logic, independent of FastAPI), `dependencies.py`
  (`get_current_user`, reads the session cookie), `router.py` (`/auth/signup`,
  `/auth/login`, `/auth/logout`, `/auth/me`). See
  [security.md](./security.md) for the specific choices and known gaps.
- **Database**: PostgreSQL 16. This machine runs it as a native Windows
  install (Docker isn't available here), so the `pgvector` extension is
  **not yet installed** — it isn't needed until the embeddings/retrieval
  milestone (roadmap Steps 10–11). The `docker-compose.yml` still targets
  `pgvector/pgvector:pg16` for anyone running this project with Docker.
  Schema changes go through Alembic migrations (`backend/migrations/`) —
  never hand-edited.

Nothing yet talks to an LLM or stores documents — those are later
milestones (see [roadmap.md](./roadmap.md)). There is also no
organization/workspace model yet, so authorization scoping (Step 6) isn't
implemented; a logged-in user currently has no notion of a tenant.

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
