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

## Authorization / multi-tenancy (Step 6)

- Every organization-scoped route depends on `get_organization_membership`
  (`app/organizations/dependencies.py`), which checks membership **before**
  any document, chunk, or conversation is looked up. A non-member gets 403
  without the retrieval layer running at all.
- Conversations are further scoped to the owning user (not just the org),
  so one org member can't read another member's chat history by guessing a
  conversation ID.
- Verified by `backend/tests/test_tenant_isolation.py`: a second user is
  rejected (403) from another org's members, documents, and search
  endpoints; an unauthenticated request is rejected (401) before any org
  check runs at all (so it can't be used to probe whether an org ID
  exists).
- Roles exist (`owner`/`admin`/`manager`/`member`/`viewer`) but nothing yet
  *enforces* role-based restrictions beyond membership — e.g. a `viewer`
  can currently upload documents just like an `owner` can. Role-gated
  permissions per action are a Phase 8 (SaaS/RBAC) refinement, not yet
  built.

## Prompt injection / retrieved-content trust (Steps 13–15)

- The chat system prompt (`app/chat/service.py::GROUNDED_SYSTEM_PROMPT`)
  explicitly tells the model that context excerpts are untrusted document
  content, not instructions, and to treat anything inside them that looks
  like a command as text to quote/summarize, never obey.
- Citations are built directly from the real retrieval results
  (`SearchResultItem`), never parsed from the LLM's generated text — so a
  citation always traces back to an actual chunk that was actually
  retrieved, regardless of what the model claims to have used.
- If no relevant chunks are found, the LLM is never called at all; the
  response says so plainly instead of generating an ungrounded answer.
- Not yet tested: an actual adversarial prompt-injection payload embedded
  in an uploaded PDF. Worth adding once an LLM key is configured and this
  can be exercised for real instead of just by prompt design.

## File upload

- PDF only (`Content-Type: application/pdf`), rejects other types with 415.
- 20MB size limit, rejects empty files.
- Stored on local disk under `backend/data/uploads/{organization_id}/`,
  filename is `{document_id}.pdf` (not user-controlled) — no path traversal
  surface from the original filename, which is stored separately as
  metadata only.
- **Not yet implemented**: virus/malware scanning of uploaded PDFs,
  content-sniffing to confirm the bytes are actually a PDF (currently
  trusts the client's declared `Content-Type`). Should land before
  accepting uploads from untrusted users in production.

## Not yet implemented (intentionally deferred, not forgotten)

- **Email verification** — accounts are usable immediately after signup.
- **Password reset** — no flow yet; needs transactional email first.
- **Rate limiting / brute-force protection** on `/auth/login` — currently
  unlimited attempts. Should land before any public deployment.
- **MFA**.
- **Audit logging** of login/logout/signup/document/chat events (Section 42
  of the project brief) — deferred until there's an audit log table and a
  reason to query it.
- **Role-based permission enforcement** beyond plain membership (see above).
- **Upload content scanning** (see above).
- **Adversarial prompt-injection testing** against real uploaded content
  (see above) — currently only defended by system-prompt design.
