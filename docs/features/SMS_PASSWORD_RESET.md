# Password reset by verified phone

## Candidate flow

Login's **Forgot password?** link opens `/auth/reset-password`:

1. Enter the registered phone number only. Ghana local and international formats
   normalize to E.164. The form does not ask for an email address.
2. Enter the six-digit SMS reset code.
3. Choose and confirm a new password (12–128 characters; Supabase's additional
   password policy still applies).
4. Return to normal email/password sign-in. Recovery never establishes an app
   session or turns routine login back into SMS login.

Only an active local account with a current Supabase Auth email identity and
previously verified phone can reset. A phone-only account that has never set up
email login must first use the existing `/auth/setup-login` transition. A missing
or changed phone cannot be replaced through password recovery.

## Server behavior

`POST /api/v1/auth/password-reset/request` accepts `{ "phone": "024 123 4567" }`.
It returns HTTP 202 with the same message, random challenge ID, five-minute expiry
and 60-second resend delay for eligible and unknown numbers. The local users row
is only a lookup hint. Supabase's canonical Auth admin API must confirm the same
user ID, phone and phone-confirmation timestamp. Editable profile metadata cannot
authorize recovery. Disabled/deleted/unverified accounts receive no SMS.

Identity lookup and SMS delivery run after the generic response using FastAPI
BackgroundTasks, so provider/eligibility timing is not exposed by waiting for
delivery. Delivery is **best effort, not a durable queue**: a worker restart can
drop a pending send. The candidate can resend after the cooldown. An accepted
request does not claim delivery. If every provider fails, its challenge is removed;
the server logs safe provider/error categories without codes or contact data.

`POST .../verify` accepts `{ "challenge_id": "...", "code": "123456" }`.
Six-digit codes come from Python's cryptographic random generator. Redis stores
only an HMAC bound to this challenge and recovery purpose. Five incorrect attempts
invalidate the code. Successful verification atomically consumes the code and
creates a separate, random 256-bit reset token valid for five minutes. It returns
no Supabase access/refresh token. Login/signup OTPs cannot be used as reset codes.

`POST .../complete` accepts `{ "reset_token": "...", "password": "..." }`.
The server atomically consumes the reset token, rechecks account activity and the
current Auth identity, and updates **only the password of that bound user ID**.
Contact/confirmation/password/profile updates since the code was requested
invalidate the identity fingerprint and require a fresh reset. Concurrent code or
grant reuse has one winner. Resending invalidates previous codes and reset tokens.
Grants remain consumed after ambiguous provider/network failures; the UI tells
the candidate to try signing in with the new password or request a new code.

Supabase's admin password update enforces its configured strength policy and
revokes refresh sessions. Already-issued access JWTs may remain usable until their
configured expiry; this is not an immediate access-token revocation guarantee.
Verify this behavior against the hosted Auth version at release. Sources:
[admin password update](https://supabase.com/docs/reference/javascript/auth-admin-updateuserbyid),
[Auth UpdatePassword session behavior](https://github.com/supabase/auth/blob/master/internal/models/user.go),
[Supabase session lifetime](https://supabase.com/docs/guides/auth/sessions).

## Abuse and privacy controls

- Redis is mandatory for every recovery operation, including development. Failure
  or a three-second Redis timeout returns 503; there is no memory fallback and
  `RATE_LIMIT_ENABLED=false` cannot disable recovery limits.
- Requests: 10 per IP per 15 minutes, 3 per normalized phone per hour, 10 per phone
  per day, and one request per number per 60 seconds. Verification: 30 per IP per
  15 minutes plus five attempts per challenge. Completion: 20 per IP per 15 minutes.
  Counters and expirations are atomic Lua operations. `Retry-After` is exposed
  through CORS and honored in the UI.
- IP identity uses the ASGI client address, never a raw caller-supplied forwarded
  header. Configure Uvicorn's trusted proxy addresses and make ingress overwrite
  forwarded headers; otherwise proxy users may share a limit.
- Code/grant state expires; phone/IP rate-limit keys and identity fingerprints are
  HMACs. Redis does not store passwords, plaintext codes or raw reset tokens.
- Passwords and grants use redacted request models. Auth validation errors omit
  raw inputs from logs/responses even in debug mode; Auth query strings are not
  logged. Reset endpoints have 4 KiB request limits and no-store responses.
- The browser keeps grants and passwords only in component memory, not URLs,
  cookies, local/session storage or analytics. Reloading restarts the recovery flow.

## Deployment requirements

Deploy backend and frontend together. No new schema migration is required;
`020_add_phone_auth_identity.sql` and the full setup script already supply the
phone identity mirror and Auth insert/update synchronization.

- Ensure the declared `redis>=5.0.0` backend dependency is installed and `REDIS_URL`
  points to a private, available Redis service. Use authentication/TLS as required
  by the hosting environment. Redis 6+ supports the atomic scripts' KEEPTTL command.
- Keep `SECRET_KEY` strong and identical across workers. Rotating it invalidates
  pending recovery codes/grants and resets the associated hashed rate keys.
- `AUTH_SUPABASE_SERVICE_KEY` is a **server-only** key for the canonical Auth
  project. It falls back to `SUPABASE_SERVICE_KEY` only if Auth and data URLs are
  the same. A separate Auth project without its own service key fails closed.
  Never put this key in a NEXT_PUBLIC variable or a client bundle.
- Configure at least one enabled/credentialed Arkesel or Moolre provider in
  `SMS_PROVIDERS`. Recovery reuses these provider adapters with explicit password
  reset wording. It does not call Supabase's Send SMS hook or send recovery email.
- Keep `public.users.phone_e164` synchronized with the canonical Auth phone. Test
  an already-existing account and one created with the current signup flow.
- Configure Supabase password strength/leaked-password protection and a suitably
  short access-token lifetime for the deployment's session-risk requirements.
- Monitor `password_reset_configuration_missing`, `password_reset_state_unavailable`,
  `password_reset_delivery_unavailable`, `password_reset_sms_failed`, and
  `password_reset_update_failed`. An SMS accepted by a provider is not confirmed
  handset delivery. Investigate provider history before repeated resends.

## Verification

`backend/tests/test_sms_password_reset.py` includes real Redis Lua tests for
expiry, limits, attempts, resends, concurrent reuse, account changes, suspension,
unknown-number responses, provider failure and grant consumption on update errors.
It also covers canonical Auth key selection, password-only admin updates,
validation redaction and oversized input. Redis-specific tests require an
**isolated** `PASSWORD_RESET_TEST_REDIS_URL`; they skip when it is absent.

```bash
cd backend
PASSWORD_RESET_TEST_REDIS_URL=redis://127.0.0.1:16389/0 venv/bin/python -m pytest tests/test_sms_password_reset.py tests/test_arkesel_phone_auth.py tests/test_phone_verification_gate.py tests/test_shared_auth_config.py -q --no-cov
```

Local browser acceptance in `frontend/scripts/verify-sms-reset.cjs` targets a
local-only fixture API with `/test/clear` and `/test/state`, never production. The
fixture uses the real routes and Redis, with database/Auth/SMS adapters replaced
by synthetic ones. Browser coverage includes phone-only input, invalid code,
password mismatch, exactly one password update, storage checks, unknown phone,
expiry, reload, Retry-After and 1440/390/360px layouts.

The checked-in fixture is `backend/tests/fixtures/sms_reset_app.py`; it refuses to
start without `PASSWORD_RESET_BROWSER_FIXTURE=1`. Start an isolated Redis on
127.0.0.1:16389, then from `backend/` run:

```bash
PASSWORD_RESET_BROWSER_FIXTURE=1 PYTHONPATH=. venv/bin/uvicorn sms_reset_app:app --app-dir tests/fixtures --host 127.0.0.1 --port 8099
```

Point a local frontend at API port 8099, then run the browser script with
`PLAYWRIGHT_PATH` set to an installed Playwright package and `TEST_BASE_URL` set
to that frontend (default http://127.0.0.1:3027). The fixture is never mounted by
the application router and must never be served publicly.

On 2026-09-06, all 67 focused backend tests passed using isolated Redis 7;
TypeScript checking and the isolated 27-route production build passed. Browser
flows against real reset routes/Redis and mocked external adapters passed at
1440/390/360px without runtime errors. No live SMS or deployment was performed.

Local tests do not prove production SMS receipt, hosted key permissions, session
revocation or live database synchronization. Before release, test one authorized
account end to end, confirm old-password rejection and new-password login, verify
refresh-session revocation, and repeat the invalid/expired-code checks.
