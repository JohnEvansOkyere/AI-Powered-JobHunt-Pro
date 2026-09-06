# Passwordless phone authentication with Arkesel

VeloxaHire uses Supabase Auth to generate and verify phone OTPs and to issue the
same JWT sessions already accepted by the FastAPI backend. Arkesel is the SMS
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
8. Test with an authorised Ghana number.

Supabase applies its own OTP request limits. Production should also enable
Supabase CAPTCHA to control automated SMS spend. The hook verifies all three
Standard Webhooks headers and fails closed when its secret is absent or wrong.

## Candidate flow

1. Registration collects a required email address and normalizes Ghana local format such as `024 123 4567` to
   `+233241234567` (international E.164 is also accepted).
2. `signInWithOtp` asks Supabase to create the pending phone identity.
3. Supabase signs a Send SMS Hook event containing its generated OTP.
4. The backend verifies that signature and sends the OTP using Arkesel SMS v2.
5. `verifyOtp` verifies the code with Supabase and establishes the session.
6. The client stores the collected email as authenticated `contact_email` metadata. It is used for email alerts and account communication; it is not the OTP identity.

Phone verification is account authentication only. It does not opt the user
into WhatsApp or promotional SMS alerts.

Existing email/password accounts can still use the legacy option on the sign-in
page during migration. New registration verifies by phone but collects an email
for account communication and email alerts.

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

The 2026-09-06 production logs showed a signed hook reaching SMS delivery and
returning `502` with `error_type=ValueError`. The sender previously required a
leading `+`, whereas [Supabase Auth normalizes phone numbers by removing it](https://github.com/supabase/auth/blob/master/internal/api/phone.go).
This mismatch is reproduced by a signed hook test using `233241234567`.
The sender now accepts country-code numbers with or without `+`, normalizes
them back to `+233...` E.164 for Arkesel, and still rejects local `0`-prefixed
or malformed numbers. Arkesel's v2 API examples require the international
recipient form with the leading `+`.

Validation failures now log `error_code=invalid_phone_format` or
`invalid_otp_format`; other delivery failures use `sms_delivery_failed`.
Phone numbers, OTPs, secrets, and provider response bodies are not included in
these diagnostics. A signature failure remains `401`, missing payload fields
remain `422`, and SMS delivery failures remain `502`.

Deploy the updated backend before retrying signup; restarting an older checkout
does not apply this fix. Tests use a mocked Arkesel transport. Actual SMS receipt
and successful Supabase code verification still require a production smoke test.
