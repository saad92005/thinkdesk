# Deploying ThinkDesk publicly

This gets ThinkDesk reachable from anywhere at a free, real HTTPS URL —
no credit card, no domain purchase required. A custom domain can be layered
on top afterward (see the bottom of this doc).

Three pieces, deployed separately, **none of which require a credit card**:

- **Database** (Postgres) → [Neon](https://neon.tech) — genuinely free
  forever, no card, no expiry.
- **Backend** (FastAPI) → [Render](https://render.com) — free web
  services don't require a card either. (Render's own *managed Postgres*
  does require one, which is why this guide uses Neon instead.)
- **Frontend** (Next.js) → [Vercel](https://vercel.com).

## 1. Create the database (Neon)

1. Sign up at [neon.tech](https://neon.tech) with GitHub — no card asked.
2. Create a project (any name, e.g. `thinkdesk`). It gives you a
   **connection string** immediately, something like:
   ```
   postgresql://neondb_owner:AbC123@ep-cool-name-12345.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
3. Copy that whole string — you'll paste it into Render in the next step.
   (ThinkDesk's backend automatically adapts a plain `postgresql://` URL
   for its async driver, so no editing needed.)

## 2. Deploy the backend (Render)

1. Sign in at [render.com](https://render.com) with your GitHub account —
   you can create a **free Web Service** without ever being asked for a
   card. If you're prompted for payment info at any point, you've been
   routed into creating a *database* or a *paid* service by mistake —
   back out and choose **New → Web Service** specifically, not Blueprint
   or Postgres.
2. **New → Web Service** → connect the `thinkdesk` repo.
3. Set:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
4. Under **Environment**, add:
   - `DATABASE_URL` — the Neon connection string from step 1
   - `CONNECTOR_ENCRYPTION_KEY` — generate one locally with
     `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
     and paste the result
   - `CORS_ORIGINS` and `FRONTEND_BASE_URL` — set these **after** step 3
     below, to your Vercel URL (e.g. `https://thinkdesk.vercel.app`)
   - Optional (the app degrades honestly if these are missing, it won't
     crash): `GROQ_API_KEY`, `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/
     `GOOGLE_REDIRECT_URI`, `SLACK_CLIENT_ID`/`SLACK_CLIENT_SECRET`/
     `SLACK_REDIRECT_URI`, `LEMONSQUEEZY_*`
5. Click **Create Web Service**. First deploy takes a few minutes (it runs
   `alembic upgrade head` before starting the server, creating the schema
   on Neon automatically).
6. Note the backend's public URL, e.g. `https://thinkdesk-backend.onrender.com`.

(`render.yaml` at the repo root mirrors this exact configuration — if
Render ever offers a card-free way to deploy a Blueprint from it directly,
that works too; the manual steps above are the guaranteed card-free path.)

Free-tier note: Render's free web services spin down after 15 minutes of
inactivity and take ~30-60 seconds to wake back up on the next request —
expected on a free plan, not a bug. Fine for a demo/portfolio link; upgrade
the plan before relying on it for real traffic.

## 3. Deploy the frontend (Vercel)

1. Sign in at [vercel.com](https://vercel.com) with GitHub.
2. **Add New → Project** → import the `thinkdesk` repo.
3. Vercel will ask for the project root — set **Root Directory** to
   `frontend` (this is a monorepo; the Next.js app isn't at the repo root).
   It auto-detects Next.js after that, no other config needed.
4. Add one environment variable before deploying:
   - `NEXT_PUBLIC_API_URL` = the Render backend URL from step 2
     (e.g. `https://thinkdesk-backend.onrender.com`)
5. Deploy. You'll get a URL like `https://thinkdesk.vercel.app` immediately.
6. Go back to Render and set `CORS_ORIGINS` / `FRONTEND_BASE_URL` to this
   exact Vercel URL (step 2.4) — until you do, the browser will get CORS
   errors and OAuth redirects will bounce to the wrong place.

## 4. Verify

Visit your Vercel URL, sign up, create a workspace, upload a PDF, and ask
a question — the full pipeline (retrieval, chat, connectors, agent,
automation, billing) runs exactly as it does locally, against the same
codebase, just publicly reachable now.

## Adding a real custom domain later

Both platforms support this without touching code:

- **Frontend**: Vercel project → **Settings → Domains** → add your domain
  → it gives you a CNAME/A record to add at your registrar (Namecheap,
  GoDaddy, etc.) → HTTPS is provisioned automatically.
- **Backend**: Render service → **Settings → Custom Domains** → same idea.
- Update `CORS_ORIGINS`, `FRONTEND_BASE_URL`, and the two OAuth redirect
  URIs (Google Cloud Console, Slack app settings) to the new domain once
  it's live — these are the only places a URL is hardcoded anywhere.

## Local development is unaffected

Nothing above changes how local development works — `docs/setup.md` still
describes running everything on `localhost`. This is purely an additional,
optional deployment target.
