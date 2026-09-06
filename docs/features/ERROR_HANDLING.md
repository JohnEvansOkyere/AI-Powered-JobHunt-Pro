# Customer-facing errors

Implemented locally on 2026-09-06. Deploy the frontend and backend together.

## Response and UI behavior

- `frontend/lib/errors.ts` maps reviewed auth codes and a small set of exact business messages to customer copy. Unknown exception strings, provider configuration, SQL, paths, HTML and validation objects are never passed through to the interface. Add reviewed mappings here when an action needs more specific guidance.
- The shared API client handles ordinary JSON errors, the backend's nested error envelope, failed downloads, network failures and unreadable responses. Status and request ID remain available on the error object. Permission denials and service outages do not clear a valid session; known invalid-account/session responses retain the existing sign-out behavior.
- Signup, login, phone verification, password recovery, profile/CV editing, settings and admin actions use the same error presentation helper. Wrong credentials, expired SMS codes, phone conflicts and reset retry limits retain actionable guidance. Reset code/grant lifetime and authorization are unchanged.
- Failed profile saves are caught at the event boundary, show a safe message and keep the editor open. Stored CV parser diagnostics and import exception text are replaced with reviewed response/UI copy.
- Backend HTTP 5xx responses and unhandled/database/value errors hide implementation details even with `DEBUG=true`. Existing endpoint/server diagnostic logs remain available. HTTP status, authentication headers and reset `Retry-After` headers are preserved. Existing HTTP 4xx business contracts remain compatible; the frontend still treats their text as untrusted.
- Validation logs include only field location and error type, never Pydantic input, context or message values. Responses omit validation details in all environments. Request logging and error handling share a generated request ID; CORS exposes it and permits reading error responses.
- Route and global Next.js error boundaries already use fixed retry copy. Production must use `next build` followed by `next start` (or Vercel's production deployment), not `next dev`. This change handles the identified rejected promises; it does not conceal programming failures in the development tooling.

Auth code definitions follow the [Supabase Auth error documentation](https://supabase.com/docs/guides/auth/debugging/error-codes). The browser fixtures include the Supabase API version response header so the installed SDK exposes those codes correctly.

## Verification

```bash
cd frontend
npm run type-check
node scripts/verify-errors.cjs
# Against a local production build with synthetic Auth/API configuration:
PLAYWRIGHT_PATH=/path/to/playwright TEST_BASE_URL=http://127.0.0.1:3028 node scripts/verify-error-ui.cjs
PLAYWRIGHT_PATH=/path/to/playwright TEST_BASE_URL=http://127.0.0.1:3028 node scripts/verify-account-auth.cjs
```

Backend regressions: `backend/tests/test_public_errors.py` covers DEBUG on/off, HTTP/server/database failures, validation redaction, status/headers, request IDs, CORS and stored CV parser diagnostics. Run alongside `test_sms_password_reset.py`, `test_phone_verification_gate.py`, `test_arkesel_phone_auth.py`, `test_shared_auth_config.py` and `test_cv_tailoring.py`; provide `PASSWORD_RESET_TEST_REDIS_URL` pointing to an isolated Redis instance for all recovery tests.

Browser checks use synthetic accounts and errors at desktop/mobile sizes, including failed profile saves. Production delivery, deployed environment settings and real account operations require separate hosted verification.
