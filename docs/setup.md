# Local Development Setup

This machine runs PostgreSQL natively (installed via winget), not Docker.
Both paths are documented below — use whichever matches your environment.

## Option A — Native PostgreSQL (used for local dev on this machine)

### Prerequisites

- Node.js 20+ and npm
- Python 3.11+
- PostgreSQL 16 (Windows: `winget install --id PostgreSQL.PostgreSQL.16`)

### 1. One-time database setup

After installing PostgreSQL, create the app role and database (run as the
`postgres` superuser):

```sql
CREATE ROLE thinkdesk WITH LOGIN PASSWORD 'thinkdesk';
CREATE DATABASE thinkdesk OWNER thinkdesk;
```

> Note: `pgvector` isn't bundled with the plain Windows installer, but it
> has been compiled from source (v0.8.0) against this install and is
> vendored at `backend/vendor/pgvector-win64/` — see that folder's README
> for the one remaining elevated install step. Until that's done, semantic
> search uses a pure-Python cosine-similarity fallback (see
> `docs/architecture.md`), which works correctly, just without a native
> index.

Also create the test database (used by `pytest`, kept separate from your
working data):

```sql
CREATE DATABASE thinkdesk_test OWNER thinkdesk;
```

If the PostgreSQL Windows service (`postgresql-x64-16`) isn't running,
start it from an elevated PowerShell or via `services.msc` — starting/
stopping Windows services requires administrator rights.

### 2. Backend

```
cd backend
cp .env.example .env      # points DATABASE_URL at localhost:5432
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Check http://localhost:8000/health — with the database reachable it
returns `"status": "ok", "database": "connected"`. If Postgres isn't
running, it honestly reports `"status": "degraded", "database":
"unreachable"` rather than assuming success.

Apply database migrations before first run (and after pulling any change
that touches `app/models/`):

```
alembic upgrade head
```

#### Enabling LLM chat generation

Embeddings and retrieval work with no external account at all (they run
locally via `fastembed`). Chat *generation* needs an LLM, though — get a
free API key at https://console.groq.com and add it to `backend/.env`:

```
GROQ_API_KEY=your-key-here
```

Without it, `/chat` still runs the full retrieval + citation pipeline, but
returns a plain "no LLM configured" message instead of a generated answer.

#### Running tests

```
pip install -r requirements-dev.txt
pytest -v
```

22 tests: chunking unit tests, auth security unit tests, the full signup/
login/logout flow, tenant-isolation security tests, and a full upload →
process → search → chat round trip against a real (but generated,
throwaway) PDF. Tests run against `thinkdesk_test`, not your working
database.

### 3. Frontend

```
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000. The homepage calls the backend `/health`
endpoint client-side and displays the live status returned by the API.

## Option B — Docker Compose

If Docker Desktop is available:

```
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Backend health check: http://localhost:8000/health

This path uses the `pgvector/pgvector:pg16` image, so the vector extension
is available out of the box — unlike Option A.

To run just the database:

```
docker compose up postgres
```
