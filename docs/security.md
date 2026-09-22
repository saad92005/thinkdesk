# Security Notes

This documents the actual current state of security-relevant decisions.
Nothing here is aspirational — if a control isn't implemented, it's listed
under "Not yet implemented" instead of glossed over.

## Authentication (Step 5)

- **Password storage**: argon2id via `argon2-cffi`, using that library's
  default work factors. Never stored or logged in plaintext.
- **Sessions**: server-side, stored in the `sessions` table. The cookie
  holds a random 32-byte token (`secrets.token_urlsafe(32)`); only its
  SHA-256 hash is stored in the database, so a database leak alone does not
  yield usable session tokens (the same principle as hashing passwords,
  applied to session tokens).
- **Cookie flags**: `HttpOnly` (not readable by JS), `SameSite=Lax`,
  `Secure` when `ENVIRONMENT != "development"` (plain HTTP is used for
  local dev only).
- **Session lifetime**: fixed 7-day expiry from creation (`session_ttl_days`
  in `core/config.py`). No sliding refresh yet — a session simply expires
  and the user logs in again.
- **Logout**: deletes the session row server-side (not just the cookie), so
  a stolen cookie from before logout stops working immediately.

## Not yet implemented (intentionally deferred, not forgotten)

- **Email verification** — accounts are usable immediately after signup.
- **Password reset** — no flow yet; needs transactional email first.
- **Rate limiting / brute-force protection** on `/auth/login` — currently
  unlimited attempts. Should land before any public deployment.
- **MFA**.
- **Audit logging** of login/logout/signup events (Section 42 of the
  project brief) — deferred until there's an audit log table and a reason
  to query it.
- **Multi-tenancy / authorization** — there is no organization model yet
  (Step 6), so every authenticated user currently has equal, ungated access
  to whatever endpoints exist. This is fine today because no tenant data
  exists yet, but authorization must land *before* any document or
  knowledge-base endpoint is added, per the project's core security rule:
  the retrieval layer filters access, never the LLM.

## Prompt injection / retrieved-content trust

Not applicable yet — no RAG pipeline exists. When it's built (Phase 1
milestone), retrieved document content must be treated as untrusted data,
never as instructions (see the master project brief, Section 41).
