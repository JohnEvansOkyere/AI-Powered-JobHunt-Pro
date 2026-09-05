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

1. Registration normalizes Ghana local format such as `024 123 4567` to
   `+233241234567` (international E.164 is also accepted).
2. `signInWithOtp` asks Supabase to create the pending phone identity.
3. Supabase signs a Send SMS Hook event containing its generated OTP.
4. The backend verifies that signature and sends the OTP using Arkesel SMS v2.
5. `verifyOtp` verifies the code with Supabase and establishes the session.

Phone verification is account authentication only. It does not opt the user
into WhatsApp or promotional SMS alerts.

Existing email/password accounts can still use the legacy option on the sign-in
page during migration. New registration is phone-only.
