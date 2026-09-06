# Email/password accounts with one-time phone verification

VeloxaHire creates accounts with name, email and password, then uses Supabase
Auth to verify a phone number once. Future sign-ins use email and password.
Supabase owns the account and JWT session. Arkesel is the SMS
delivery provider; it never creates the session and the Arkesel API key never
goes to the browser.

## Required backend variables

Set these in `/var/www/veloxahire/backend/.env` on the DigitalOcean server (and
in `backend/.env` for local testing):

```env
ARKESEL_SMS_ENABLED=true
ARKESEL_API_KEY=<Arkesel Main API key>
ARKESEL_SENDER_ID=VeloxaHire
SUPABASE_SEND_SMS_HOOK_SECRETS=v1,whsec_<secret shown by Supabase>
```

`ARKESEL_SENDER_ID` must be approved in Arkesel and cannot exceed 11
characters. Never put the Arkesel key or hook secret in `frontend/.env.local`
or in any `NEXT_PUBLIC_*` variable.

Keep `ARKESEL_SMS_ENABLED=false` until the backend hook is deployed and
`SUPABASE_SEND_SMS_HOOK_SECRETS` is set. Production startup intentionally fails
closed if Arkesel is enabled with incomplete credentials.

## Supabase dashboard configuration

1. Deploy the backend over HTTPS.
2. Under Authentication > Hooks, configure the **Send SMS** HTTP hook first.
3. Set its URL to:
   `https://api.veloxahire.org/api/v1/auth/hooks/send-sms`
4. Copy the complete generated hook secret into
   `SUPABASE_SEND_SMS_HOOK_SECRETS` on the backend.
5. Set `ARKESEL_SMS_ENABLED=true` and restart the backend.
6. Return to Supabase Authentication > Providers and enable Phone. Keep phone
   confirmations enabled; the Send SMS hook replaces the built-in provider.
7. Apply `migrations/020_add_phone_auth_identity.sql`.
8. Enable the Email provider and **turn off Confirm email** for the requested
   direct signup → phone verification flow. Keep **Confirm phone on**. With email
   confirmation enabled, Supabase creates no signup session; the UI safely shows
   a check-email message instead of attempting an unauthenticated phone update.
   Turning off Confirm email auto-confirms emails in Supabase; this is not proof
   of mailbox ownership. Phone possession is the registration verification here.
9. Allow the frontend `/auth/verify-phone` and `/auth/setup-login` URLs in Auth
   redirect settings. Keep secure email-change confirmation for existing-account
   email changes; the account setup page handles a pending confirmation.
10. Deploy frontend and backend together and test with an authorised Ghana number.

Supabase applies its own OTP request limits. Production should also enable
Supabase CAPTCHA to control automated SMS spend. The hook verifies all three
Standard Webhooks headers and fails closed when its secret is absent or wrong.

## Candidate flow

Password recovery is a separate phone-only SMS flow. See
[SMS_PASSWORD_RESET.md](SMS_PASSWORD_RESET.md) for security, setup and verification.

1. `/auth/signup` collects full name, email and password (at least eight characters)
   and calls `signUp({ email, password })`. Supabase password policy still applies.
   Handoff details remain on this same user. Passwords are never stored in profile
   metadata or analytics.
2. The new session opens `/auth/verify-phone`. This separate page collects the
   number and normalizes Ghana local format such as `024 123 4567` to E.164.
3. Authenticated `updateUser({ phone })` requests a code for the existing account.
   It does not call `signInWithOtp` or create another phone identity.
4. The signed Send SMS hook delivers the code through the configured providers.
5. `verifyOtp({ phone, token, type: 'phone_change' })` confirms the number and the
   client refreshes its session, then continues automatically to `/dashboard`.
   The existing profile-completion gate can then open `/profile/setup`.
6. Every later login calls `signInWithPassword({ email, password })`. Confirmed
   users proceed without SMS. An interrupted signup resumes phone verification
   after password login; merely visiting/reloading that page sends no SMS.

The UI blocks protected pages until `phone` and `phone_confirmed_at` exist.
FastAPI independently enforces the same requirement on protected APIs. Standard
JWTs omit the confirmation timestamp, so the backend fetches the authoritative
Supabase Auth user even when the token's signature can be verified locally. It
does not trust editable `user_metadata.phone_verified` or a local profile flag.
Suspended/revoked-account checks and resource ownership checks still apply.
Anonymous job browsing remains available. This does not add a new Supabase
Storage/PostgREST policy; existing direct-access policies remain separate.

SMS requests retain Supabase's provider-side rate limits and the signature-protected
hook. The UI adds a 60-second retry/resend cooldown, including ambiguous delivery
failures. Provider errors, duplicate numbers and invalid/expired codes remain
visible without replacing or merging accounts. No new schema migration is needed;
migration `020` and the complete setup script already sync phone confirmation on
Auth user insert/update.

Phone verification is account authentication only. It does not opt the user
into WhatsApp or promotional SMS alerts.

Existing email/password users sign in normally and verify a phone once if needed.
Existing phone-only users follow **Set up email sign-in** from `/auth/login`.
`/auth/setup-login` uses one recovery OTP with `shouldCreateUser: false`, then
updates the same authenticated user with an email and password. Already-signed-in
phone users go straight to credential setup. If Supabase requires an email-change
confirmation, the page waits for it; contact email metadata alone is never treated
as an email login identity. Existing profiles/CVs stay attached to the same user ID.

API contracts: [Supabase phone updates](https://supabase.com/docs/guides/auth/phone-login),
[password signup/session behavior](https://supabase.com/docs/guides/auth/passwords),
and [authenticated user updates](https://supabase.com/docs/reference/javascript/auth-updateuser).

## Verification evidence — 2026-09-06

- 39 focused backend tests passed across phone-verification enforcement, signed
  SMS delivery, shared Auth configuration and authentication (live health tests
  excluded). Coverage includes metadata spoofing, missing confirmation, repeat
  verified requests, revoked/suspended accounts and Auth lookup failure.
- `npm run type-check` passed. An isolated production build with synthetic
  public configuration passed for all 26 routes; the existing dev server and
  environment files were left intact.
- `frontend/scripts/verify-account-auth.cjs` passed with synthetic Supabase/API
  responses: signup without phone input, same-user phone change, invalid code,
  automatic session and reload, repeat password login without SMS, unverified
  route guard, existing phone-account conversion, pending email confirmation
  across reload, provider error/retry throttle, and 1440/390/360px layouts.
  Browser tests found no runtime errors. These are fixture tests, not proof of
  hosted SMS delivery, production Auth settings or production database writes.
- No deployment or real SMS was performed. Existing onboarding edits were
  preserved. Before release, verify the configured signup session, actual phone
  change OTP, same Auth user ID, repeat password login and old-account conversion.

## Provider failover

The hook supports an ordered `SMS_PROVIDERS` chain (default
`arkesel,moolre`). It calls one provider for an OTP and moves to the next only
when the first provider fails; it never sends through both after one success.
Moolre uses `MOOLRE_VAS_KEY`, `MOOLRE_SENDER_ID`, and its `X-API-VASKEY` API
contract. Configure `MOOLRE_SMS_ENABLED=true` and put `moolre` first when
Moolre should be the active provider. Keep only providers with verified
credentials in the chain; a provider with missing credentials is skipped.
Successful hook responses return an explicit JSON object with
`Content-Type: application/json`; Supabase rejects a bare `200` response with
no content type as `Invalid Content-Type: Missing Content-Type header` even
when the SMS provider accepted the message.

## Troubleshooting delivery failures

### Existing accounts verifying a phone

The signed hook now selects the OTP destination from `sms.phone`. For older
payloads without that field, it uses `user.new_phone` when populated, then
`user.phone` for ordinary phone sign-in. Previously it always read `user.phone`,
which can be empty or still contain the old number during `updateUser({ phone })`.
This reproduced a `502` for an existing email account and could send a phone-change
code to the previous number. Explicit malformed destinations fail closed rather
than falling back to a different phone. Signature verification remains mandatory.

Contract references: [Supabase OTP destination construction](https://github.com/supabase/auth/blob/master/internal/api/phone.go),
[SMS hook schema](https://github.com/supabase/auth/blob/master/internal/hooks/v0hooks/v0hooks.go),
and [pending phone JSON field](https://github.com/supabase/auth/blob/master/internal/models/user.go).
Regression tests cover empty and previous phone values, current and legacy hook
payloads, destination precedence, malformed payloads and leading-zero OTPs using
a mocked SMS transport. The owner's reported generic error is not independently
confirmed as this failure without the live Auth response or hook logs. Deploy the
backend fix and verify actual SMS receipt and `phone_change` completion on the same
account; no account deletion, verification bypass or schema change is required.

### Provider phone-number format

The 2026-09-06 production logs showed a signed hook reaching SMS delivery and
returning `502` with `error_type=ValueError`. The sender previously required a
leading `+`, whereas [Supabase Auth normalizes phone numbers by removing it](https://github.com/supabase/auth/blob/master/internal/api/phone.go).
This mismatch is reproduced by a signed hook test using `233241234567`.
The sender now accepts country-code numbers with or without `+`, normalizes
them back to `+233...` E.164 for Arkesel, and still rejects local `0`-prefixed
or malformed numbers. Arkesel's v2 API examples require the international
recipient form with the leading `+`.

Validation failures now log `error_code=invalid_phone_format` or
`invalid_otp_format`. Arkesel failures include a safe `error_code` and a
bounded, redacted response preview so the actual provider reason is visible:
`arkesel_credentials_rejected` (401),
`arkesel_sender_or_account_not_authorized` (403),
`arkesel_request_rejected` (other 4xx), `arkesel_rate_limited` (429), and
`arkesel_provider_unavailable` (5xx). Phone numbers, OTPs, API keys, and
secrets are redacted from the preview. A signature failure remains `401`,
missing payload fields remain `422`, and SMS delivery failures remain `502`.
The Arkesel client allows up to 4.5 seconds for the provider response, staying
below Supabase HTTP Hook's five-second deadline. A timeout is logged as
`arkesel_timeout`; check Arkesel SMS History before retrying because a message
can be accepted and queued even if the response reaches the timeout.

Deploy the updated backend before retrying signup; restarting an older checkout
does not apply this fix. Tests use a mocked Arkesel transport. Actual SMS receipt
and successful Supabase code verification still require a production smoke test.
