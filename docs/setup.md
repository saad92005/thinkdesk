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

100 tests: chunking unit tests, auth security unit tests, the full signup/
login/logout flow, tenant-isolation security tests, hybrid search ranking
(BM25 + reciprocal rank fusion), reranking and query rewriting unit tests,
document delete, member invites/role editing/removal, RAG evaluation
scoring, document comparison/extraction/report generation, research mode's
source-verification logic, the Gmail/Slack/Notion connectors, both agent
actions' (email-summary and document-digest) propose/approve/execute
split, Lemon Squeezy webhook signature verification and subscription
upsert logic, and
free-plan usage limit enforcement (mostly mocked against
Google/Slack/Lemon Squeezy, no real accounts needed in CI -- except one
test that hits the real Notion API with a configured token), plus a full
upload → process → search → chat round trip against a real
(but generated, throwaway) PDF. Tests run against `thinkdesk_test`, not your
working database.

#### Enabling connectors (optional)

All connectors need the encryption key first (required for any connector
to work):
```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CONNECTOR_ENCRYPTION_KEY=...
```
Then apply the migration that adds the connectors table:
```
alembic upgrade head
```

**Gmail:**
1. [Google Cloud Console](https://console.cloud.google.com) → new project
   → **APIs & Services → Library** → enable "Gmail API"
2. **APIs & Services → OAuth consent screen** → configure (External user
   type is fine) → add your own email under test users
3. **APIs & Services → Credentials → Create Credentials → OAuth client
   ID** → Application type **Web application** → add redirect URI
   `http://localhost:8000/connectors/google/callback`
4. Copy the Client ID and Client Secret into `backend/.env`:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```

Until Google reviews the OAuth consent screen (only needed once you want
people besides your own test-user account to connect), you'll see an
"unverified app" warning during connect -- expected, click through it.

**Slack:**
1. [api.slack.com/apps](https://api.slack.com/apps) → **Create New App →
   Blank app** (not "AI agent" or "Starter app" -- those add scopes/features
   this connector doesn't use) → name it, pick a workspace
2. **OAuth & Permissions** → **Redirect URLs** → add
   `http://localhost:8000/connectors/slack/callback` → Save
3. Same page → **Scopes → Bot Token Scopes** → add `channels:read` (and
   `chat:write` later, once an agent action actually needs to post)
4. **Basic Information → App Credentials** → copy Client ID and Client
   Secret into `backend/.env`:
   ```
   SLACK_CLIENT_ID=...
   SLACK_CLIENT_SECRET=...
   ```

Note: Slack's "Your App Configuration Tokens" section (visible on the
Your Apps page) is for the Slack CLI, unrelated to the OAuth Client ID/
Secret this connector needs -- easy to confuse, ignore it.

**Notion:** no OAuth setup needed.
1. [notion.so/my-integrations](https://www.notion.so/my-integrations) →
   **New integration** → name it → copy the token it gives you (starts
   with `ntn_`)
2. Paste that token directly into the Connectors page in the app -- there's
   nothing to add to `backend/.env` for this one, since each workspace
   connects with its own token, not a shared app-level credential
3. In Notion itself, open any page you want ThinkDesk to see → **"..."
   menu → Connections** → add your integration. Until you do this for at
   least one page, the connector will correctly show "no pages shared
   yet" -- that's expected, not an error.

#### Enabling billing (optional)

1. Create a free store at [lemonsqueezy.com](https://lemonsqueezy.com) and
   grab an API key from **Settings → API**, and your store ID from
   `GET https://api.lemonsqueezy.com/v1/stores` with that key.
2. **Settings → Webhooks → Add webhook**. The signing secret here is one
   *you* choose (6-40 characters, any random string) -- Lemon Squeezy
   doesn't generate it for you. Check `subscription_created`,
   `subscription_updated`, `subscription_cancelled`.
3. The Callback URL must be a real, internet-reachable HTTPS address --
   `localhost` won't work, since Lemon Squeezy's servers can't reach your
   own machine directly. For local development, use
   [ngrok](https://ngrok.com) (`ngrok http 8000`) and paste the printed
   `https://....ngrok-free.dev/billing/lemonsqueezy/webhook` URL in. This
   URL changes every time the ngrok tunnel restarts.
4. Add all four values to `backend/.env`:
   ```
   LEMONSQUEEZY_API_KEY=...
   LEMONSQUEEZY_STORE_ID=...
   LEMONSQUEEZY_WEBHOOK_SECRET=...     # the one you chose in step 2
   ```
5. Create a **Product** and at least one **Variant** (the actual plan
   you're selling, e.g. "Pro Monthly") in the dashboard, then set:
   ```
   LEMONSQUEEZY_VARIANT_ID=...
   ```
   Without this, `/billing/checkout` returns a clear "not fully
   configured" error instead of attempting a checkout -- the webhook
   receiver and signature verification work independently of this step.

### 3. Frontend

```
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000. The homepage calls the backend `/health`
endpoint client-side and displays the live status returned by the API.

The frontend talks to the backend via `NEXT_PUBLIC_API_URL` (defaults to
`http://localhost:8000` if unset; override it in `frontend/.env.local` and
restart `npm run dev` if you ever run the backend on a different port --
Next.js only reads `NEXT_PUBLIC_*` vars at startup, not on hot reload).

**Windows gotcha with `uvicorn --reload`:** its reload mechanism spawns a
`multiprocessing` worker subprocess. If the parent (reloader) process is
killed directly -- rather than stopped cleanly -- the worker can be left
running as an orphan, still bound to the port and still serving the old
code, while `netstat`/`tasklist` show the *original* parent PID as the
"owner" even though that PID no longer exists. Symptom: you edit a route,
restart what you think is the server, and the new route still 404s. Fix:
find the real culprit with
`Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select ProcessId,CommandLine`
(look for `multiprocessing.spawn_main`) and kill that PID directly, not
just the one `netstat` lists against the port. Running without `--reload`
and restarting manually after backend changes avoids this entirely.

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
