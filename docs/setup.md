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

> Note: the `pgvector` extension is **not** bundled with the plain Windows
> installer. It isn't needed until the embeddings/retrieval milestone
> (roadmap Steps 10–11) — we'll install it then (either by switching to
> Docker if it becomes available, or building it from source against this
> installation).

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
