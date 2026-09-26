# Deploying ThinkDesk publicly

Two ways to get ThinkDesk reachable from anywhere, both free and requiring
no credit card. Pick based on what you need:

- **[Option A: ngrok tunnel](#option-a-ngrok-tunnel-recommended-right-now)**
  — a real public HTTPS URL in minutes, zero code deployment, zero card.
  The trade-off: your own PC has to stay on and the servers running for the
  link to work. This is what's actually running right now.
- **[Option B: Render + Neon + Vercel](#option-b-independent-cloud-hosting-render--neon--vercel)**
  — real independent cloud hosting that works even if your PC is off.
  Slightly more setup, and Render's free web service asks for a card
  (a refundable $1 authorization, not a charge) — worth it once you want
  ThinkDesk reachable 24/7 regardless of your own machine.

## Option A: ngrok tunnel (recommended right now)

This exposes your already-running local servers through one stable public
URL. **Everything runs through a single tunnel** — the frontend serves
the browser, and Next.js proxies anything under `/api/*` server-side to
the FastAPI backend, so the browser never needs to reach the backend
directly and there's no CORS to configure.

### Why the frontend must run in production mode

`next dev`'s hot-reload feature opens a WebSocket that ngrok's tunnel
doesn't handle cleanly, which silently breaks React hydration on the
public URL specifically (forms stop working, clicks fall back to native
HTML submission). Always use a production build for anything exposed
publicly — it's also simply what a real product should be running.

### Setup

1. **Add the proxy rewrite** (already done in this repo —
   `frontend/next.config.ts` forwards `/api/:path*` to
   `http://localhost:8000/:path*`).
2. **Point the frontend at the proxy**, not the backend directly. In
   `frontend/.env.local`:
   ```
   NEXT_PUBLIC_API_URL=/api
   ```
3. **Build and start the frontend in production mode**:
   ```
   cd frontend
   npm run build
   npm run start
   ```
4. **Start ngrok against the frontend's port** (3000, not 8000 — the
   backend is no longer exposed directly):
   ```
   ngrok http 3000
   ```
   A free ngrok account is tied to one stable domain that's reused across
   restarts (e.g. `https://your-name.ngrok-free.dev`) — it doesn't change
   randomly, so you only need to update redirect URIs once.
5. **Point the backend's redirect URIs at that domain, through `/api`**,
   in `backend/.env`:
   ```
   CORS_ORIGINS=http://localhost:3000,https://your-name.ngrok-free.dev
   FRONTEND_BASE_URL=https://your-name.ngrok-free.dev
   GOOGLE_REDIRECT_URI=https://your-name.ngrok-free.dev/api/connectors/google/callback
   SLACK_REDIRECT_URI=https://your-name.ngrok-free.dev/api/connectors/slack/callback
   ```
   Restart the backend after editing `.env`.
6. **Update the matching settings in each third-party dashboard** —
   these are external services, so this step can't be automated:
   - Google Cloud Console → your OAuth client → Authorized redirect URIs
     → add the same `GOOGLE_REDIRECT_URI` value above
   - Slack app (api.slack.com/apps) → OAuth & Permissions → Redirect URLs
     → add the same `SLACK_REDIRECT_URI` value above
   - Lemon Squeezy → Settings → Webhooks → Callback URL → set to
     `https://your-name.ngrok-free.dev/api/billing/lemonsqueezy/webhook`

That's it — visit `https://your-name.ngrok-free.dev` from any device,
anywhere, and the full app works: signup, upload, chat, connectors, agent
actions, automation, billing. Verified end-to-end with a real signup →
document upload → background processing → ready flow through the public
URL, not just a health check.

**Only limitation**: your PC needs to stay on, connected, and running both
`npm run start` and `uvicorn` for the link to keep working — this is a
tunnel to your machine, not independent hosting. Fine for a demo, a CV
link, or showing a team; move to Option B for real 24/7 uptime.

## Option B: independent cloud hosting (Render + Neon + Vercel)

For hosting that works even when your own machine is off.

### 1. Database (Neon — free forever, no card)

1. Sign up at [neon.tech](https://neon.tech) with GitHub.
2. Create a project → copy the connection string it gives you
   (`postgresql://...`). ThinkDesk's backend automatically adapts a plain
   `postgresql://` URL for its async driver, no editing needed.

### 2. Backend (Render — free web service, asks for a refundable card hold)

1. Sign in at [render.com](https://render.com) with GitHub.
2. **New → Web Service** (not "Blueprint", not "PostgreSQL" — those
   provision Render's own database, which is the part that isn't free
   without a card) → connect the `thinkdesk` repo.
3. Set: **Root Directory** `backend`, **Build Command**
   `pip install -r requirements.txt`, **Start Command**
   `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
   **Instance Type** Free.
4. Environment variables: `DATABASE_URL` (the Neon string), a generated
   `CONNECTOR_ENCRYPTION_KEY` (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`),
   and — after step 3 below — `CORS_ORIGINS` / `FRONTEND_BASE_URL` set to
   your Vercel URL. Optional: `GROQ_API_KEY`, `GOOGLE_*`, `SLACK_*`,
   `LEMONSQUEEZY_*` (the app degrades honestly if these are missing).
5. Create it. Note the resulting URL, e.g.
   `https://thinkdesk-backend.onrender.com`.

(`render.yaml` at the repo root mirrors this configuration if Render ever
offers a card-free Blueprint path.)

Free-tier note: spins down after 15 minutes idle, ~30-60s cold start on
the next request — expected on a free plan.

### 3. Frontend (Vercel — free, no card)

1. Sign in at [vercel.com](https://vercel.com) with GitHub → import the
   `thinkdesk` repo → set **Root Directory** to `frontend`.
2. Add `NEXT_PUBLIC_API_URL` = your Render backend URL (a full origin
   this time, e.g. `https://thinkdesk-backend.onrender.com` — Option B
   doesn't use the `/api` proxy trick since frontend and backend are on
   genuinely separate domains here, so real CORS applies instead).
3. Deploy. Go back to Render and set `CORS_ORIGINS` / `FRONTEND_BASE_URL`
   to this Vercel URL.

### Adding a real custom domain later

Both platforms support this without touching code: Vercel project →
**Settings → Domains**, Render service → **Settings → Custom Domains** —
each gives you a DNS record to add at your registrar. Update
`CORS_ORIGINS`, `FRONTEND_BASE_URL`, and the OAuth/webhook URLs to the new
domain once it's live.

## Local development is unaffected

Nothing above changes local development — `docs/setup.md` still describes
running everything on `localhost` with `next dev` and no ngrok involved.
Both deployment options are purely additional, optional targets.
