# WhatsApp top-match alerts

VeloxaHire sends a daily digest only when a verified, opted-in candidate has
current Tier-1 ("Highly recommended") jobs. The hourly Celery Beat sweep uses
the candidate's chosen local time, and the worker sends at most one digest per
local day. If the rendered Tier-1 list is unchanged from the last successful
send, it is skipped rather than repeating the same jobs.

## Reusing the dormant food-ordering number

The old `whastapp-food-ordering` application and VeloxaHire use the same Meta
Cloud API primitives, but do not copy its conversation/order bot code. Move the
sender credentials into the VeloxaHire backend deployment using this mapping:

| Food-ordering setting | VeloxaHire setting |
|---|---|
| `META_ACCESS_TOKEN` | `WHATSAPP_ACCESS_TOKEN` |
| `META_PHONE_NUMBER_ID` | `WHATSAPP_PHONE_NUMBER_ID` |
| `META_APP_SECRET` | `WHATSAPP_APP_SECRET` |
| `META_VERIFY_TOKEN` | `WHATSAPP_VERIFY_TOKEN` |

Also set `WHATSAPP_APP_ID` and `WHATSAPP_BUSINESS_ACCOUNT_ID` from Meta
WhatsApp Manager. Never copy these values into git.

The old sender was checked read-only on 2026-09-05: Meta accepted its token,
reported verified name `Veloxa Technology Ltd`, and showed a GREEN quality
rating. That proves the account is reachable, not that proactive templates are
approved or that a production send will be delivered.

## Templates required in the same WABA

Create and wait for approval of both templates before enabling live mode.
Template names and language must exactly match the deployed settings.

### `otp_verification` — AUTHENTICATION

- Language: `en_US` (or change `WHATSAPP_TEMPLATE_OTP_LANGUAGE` to the exact
  approved locale)
- Authentication body with one OTP parameter
- Copy-code OTP button at index 0
- Code expiry: 10 minutes

The client supplies the same six-digit code to the body and copy-code button.

### `daily_job_digest` — MARKETING

Use exactly three body parameters:

```text
Hello {{1}}, we found new top job matches for you:

{{2}}

Review and apply: {{3}}

Reply STOP at any time to turn off these alerts.
```

Parameter 1 is the candidate's first name, parameter 2 is the compact job list,
and parameter 3 is `${APP_PUBLIC_URL}/dashboard/recommendations`.
Create it as `en_US`, or set `WHATSAPP_TEMPLATE_DIGEST_LANGUAGE` to the exact
locale approved in Meta.

## Safe cutover

1. Apply `migrations/009_add_whatsapp.sql` if it is not already present in the
   production database.
2. Confirm production Redis is available to the API, Celery worker, and Celery
   Beat. Redis stores verification codes and carries scheduled tasks.
3. Add the mapped secrets and IDs to the VeloxaHire backend, worker, and Beat
   environments. All three processes must use the same configuration.
4. Configure Meta's callback URL as
   `https://<api-host>/api/v1/webhooks/whatsapp`, subscribe to `messages`, and
   complete the GET verification challenge.
5. Start with `WHATSAPP_ENABLED=true`, `WHATSAPP_SEND_MODE=sandbox`, and one or
   more comma-separated test numbers in `WHATSAPP_SANDBOX_RECIPIENTS`.
6. Opt in from Dashboard → Settings, verify the OTP, generate a Tier-1 match,
   and confirm `sent`, `delivered`, and `read` transitions in
   `whatsapp_messages`.
7. Switch to `WHATSAPP_SEND_MODE=live` only after that end-to-end test passes.
8. Disable the old food-ordering backend and remove its webhook subscription
   after VeloxaHire is confirmed live, so it cannot process candidate replies.

Do not enable the switch if the templates are pending/rejected, the webhook
secret is missing, or Celery Beat is not running. Production startup fails
closed when WhatsApp is enabled without its required secrets. Webhook POSTs
also fail closed when signature verification cannot be performed.

## Runtime guardrails

- Explicit opt-in plus OTP verification is mandatory.
- STOP, STOPALL, UNSUBSCRIBE, OPTOUT, END, and CANCEL disable future sends.
- Suspended/inactive accounts receive nothing.
- A unique user/date key prevents same-day duplicate dispatch.
- Unchanged Tier-1 job lists are not resent on later days.
- Global and per-user daily caps bound cost and spam risk.
- Sandbox mode blocks every number not explicitly allowlisted.
- Every attempted send and delivery status is auditable in the database.
