# Local Development Setup

## Prerequisites

- Node.js 20+ and npm
- Python 3.11+
- Docker Desktop (for PostgreSQL; optional if you have a local Postgres
  instance with the `pgvector` extension)

## 1. Environment variables

```
cp .env.example .env
```

Adjust values if needed. Defaults work for local development.

## 2. Run everything with Docker Compose (recommended once Docker is installed)

```
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Backend health check: http://localhost:8000/health

## 3. Run services individually (no Docker)

### Backend

```
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Without a running Postgres instance, `/health` will report
`"status": "degraded", "database": "unreachable"` — this is expected and
intentional; the endpoint reflects real database connectivity rather than
assuming success.

### Frontend

```
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000. The homepage calls the backend `/health`
endpoint and displays the live status returned by the API.

## 4. Database only

If you have Docker but want just Postgres:

```
docker compose up postgres
```

Connection string (matches `.env.example`):

```
postgresql+asyncpg://thinkdesk:thinkdesk@localhost:5432/thinkdesk
```
