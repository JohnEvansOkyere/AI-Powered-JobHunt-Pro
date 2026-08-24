# Email Job Digest (automated, localised)

Automated marketing email that sends each opted-in candidate the jobs that
actually match their profile, written in the language they choose.

This is the email sibling of the WhatsApp digest
(`docs/RECOMMENDATIONS_V2_PLAN.md` §6) and reuses the same
`notification_preferences` table, the same idempotency model and the same
per-user/global send caps.

---

## 1. What a subscriber gets

* Their top recommendations (Tier-1 first, topped up from Tier-2), capped at
  `EMAIL_DIGEST_MAX_JOBS`.
* Each job shows title, company, location, salary/type where known, a match
  percentage, and the AI's one-line "why this fits" reason.
* Daily or weekly, at a time and timezone they choose.
* In English or Twi.

### Languages

| Locale code | Language | Sample opening |
|---|---|---|
| `en` | English (Ghanaian register) | "Good morning Kwame, we went through today's postings and 5 of them match your profile." |
| `twi` | Twi / Akan | "Maakye Kwame! Yɛanya adwuma 5 a ɛfata dwuma a wotumi yɛ." |

**No pidgin.** An earlier draft shipped a "Ghanaian Pidgin" pack that was in fact
written in Nigerian Pidgin markers (*how body*, *wey*, *sabi*, *we don check am*)
— which reads as foreign to a Ghanaian candidate and lands worse than plain
English. The English pack is now written the way a Ghanaian colleague would
write it: warm, courteous and direct ("Do well to apply early", "All the best
with your applications"), with no slang. `test_english_pack_carries_no_pidgin_markers`
guards against the regression.

Copy is **hand-written per locale** in
[`backend/app/services/email_copy.py`](../../backend/app/services/email_copy.py),
not LLM-generated. A digest lands in a candidate's inbox with no human review
step, so the phrasing has to be predictable and on-brand; an LLM writing fresh
copy per send would cost a call per email and could drift.

Each locale carries three variants of every subject, greeting, intro and
sign-off. `variant_index()` picks one from `sha256(user_id) + date.toordinal()`,
so a subscriber does not read the same sentence every morning and two
subscribers usually differ on the same day — with no rotation state stored.

Job titles, companies, locations and match reasons are **never** translated.
They are scraped, untrusted content and are HTML-escaped before rendering.

---

## 2. Moving parts

| Concern | File |
|---|---|
| Language packs + HTML/text rendering | `backend/app/services/email_copy.py` |
| Eligibility, idempotency, caps, suppression | `backend/app/services/email_digest.py` |
| Resend API client + Svix signature check | `backend/app/integrations/email.py` |
| Celery dispatch + per-user send task | `backend/app/tasks/email_digest.py` |
| Opt-in / preferences / unsubscribe / webhook | `backend/app/api/v1/endpoints/email_notifications.py` |
| Preference + audit models | `backend/app/models/notification.py` |
| Schema | `migrations/018_add_email_digests.sql` |
| Settings UI | `frontend/components/settings/EmailDigestSettings.tsx` |
| Typed client | `frontend/lib/api/email-digest.ts` |
| Tests | `backend/tests/test_email_digest.py` |

### Flow

```
Celery Beat (hourly, :30)
  └─ notifications.dispatch_email_digests
       ├─ EmailDigestDispatcher.due_users()      # local time + frequency match
       └─ fan out → notifications.send_email_digest (one task per user)
            └─ EmailDigestDispatcher.send_digest_for_user()
                 ├─ consent / pause / suppression checks
                 ├─ idempotency key: email:digest:{user_id}:{local_date}
                 ├─ global + per-user daily caps
                 ├─ fetch Tier-1 (+Tier-2 top-up) recommendations
                 ├─ skip if < EMAIL_DIGEST_MIN_JOBS
                 ├─ skip if identical to last send (payload_hash)
                 ├─ render via locale pack
                 ├─ INSERT email_messages (status=queued)   ← audit before send
                 └─ POST https://api.resend.com/emails
```

---

## 3. Guardrails

Every one of these is enforced before the provider call:

1. **Consent** — `email_opted_in` is the single source of truth. A verified
   Supabase address is *not* consent.
2. **Suppression** — a hard bounce or spam complaint writes to
   `email_suppressions`, and that blocks all future mail to the address even if
   the user row still says opted-in. Re-opt-in from a suppressed address is
   rejected with 409.
3. **Idempotency** — one `email:digest:{user}:{local_date}` key per day. A
   re-run finds the existing row and returns `duplicate`.
4. **Caps** — `EMAIL_MAX_SENDS_PER_USER_PER_DAY` (default 1) and
   `EMAIL_MAX_SENDS_PER_DAY` (default 10000, a global circuit breaker).
5. **Thin-digest skip** — fewer than `EMAIL_DIGEST_MIN_JOBS` matches means no
   send at all. Silence beats a weak digest.
6. **Repeat skip** — recommendations refresh every 12h; if today's job list
   hashes identical to the last one sent, the send is skipped.
7. **Escaping** — all scraped/AI text goes through `html.escape(quote=True)`.
   Covered by `test_untrusted_job_fields_are_html_escaped`.
8. **Master switch** — `EMAIL_SEND_MODE=dry_run` (the default) logs the payload
   and makes no network call. Live sends additionally require `EMAIL_ENABLED=true`.

### Unsubscribe

Every email carries `List-Unsubscribe` and `List-Unsubscribe-Post`
(RFC 8058) plus a visible footer link — Gmail and Yahoo require these from bulk
senders, and without them the digest gets filtered.

Both routes are **intentionally unauthenticated**, authorised by a per-user
random token (`email_unsubscribe_token`) rather than a session, because a
recipient must be able to unsubscribe from their mail client without logging in.
The token is rotated on re-opt-in so a leaked old link stops working. The GET
route answers identically for valid and invalid tokens so it cannot be used to
probe for live tokens.

---

## 4. Setup

### 4.1 Resend

1. Create a Resend account and **verify your sending domain** (SPF + DKIM
   records). Mail from an unverified domain will not deliver.
2. Set a DMARC record on the domain — Gmail/Yahoo bulk-sender rules require it.
3. Create an API key → `RESEND_API_KEY`.
4. Add a webhook pointing at `https://<your-api>/api/v1/webhooks/email`,
   subscribed to `email.delivered`, `email.bounced`, `email.complained`,
   `email.opened`. Copy its signing secret → `RESEND_WEBHOOK_SECRET`.

### 4.2 Environment

```bash
EMAIL_ENABLED=true
EMAIL_SEND_MODE=live
RESEND_API_KEY=re_...
RESEND_WEBHOOK_SECRET=whsec_...
EMAIL_FROM_ADDRESS=jobs@yourdomain.com
EMAIL_FROM_NAME="VeloxaHire Jobs"
EMAIL_POSTAL_ADDRESS="Your registered business address"
API_PUBLIC_URL=https://api.yourdomain.com
APP_PUBLIC_URL=https://app.yourdomain.com
```

Leave `EMAIL_SEND_MODE=dry_run` in development. The whole code path runs,
including the audit row, but nothing leaves the machine.

### 4.3 Migration

```bash
psql "$DATABASE_URL" -f migrations/018_add_email_digests.sql
```

Fresh projects get this from `docs/SUPABASE_SETUP_COMPLETE.sql` (Part 9).

### 4.4 Run it

```bash
cd backend && ./start_celery_worker.sh
cd backend && ./start_celery_beat.sh
```

Beat entry `dispatch-email-digests-hourly` runs at minute 30 of every hour,
offset from the WhatsApp sweep at minute 0.

---

## 5. API

Authenticated, under `/api/v1/notifications/email`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/opt-in` | Record consent; set language, time, cadence |
| POST | `/opt-out` | Withdraw consent (preferences retained) |
| GET | `/status` | Current subscription state + available languages |
| POST | `/preferences` | Update language / time / cadence / pause |
| POST | `/test-send` | Send yourself today's digest now |

Unauthenticated:

| Method | Path | Auth |
|---|---|---|
| GET | `/api/v1/notifications/email/unsubscribe?token=` | unsubscribe token |
| POST | `/api/v1/notifications/email/unsubscribe?token=` | unsubscribe token (RFC 8058) |
| POST | `/api/v1/webhooks/email` | Svix HMAC signature |

`/test-send` still honours opt-in, suppression and the daily per-user cap, so it
cannot be used to spam an address.

---

## 6. Adding a language

1. Add a `LocalePack` to `LOCALE_PACKS` in `email_copy.py` (all fields required;
   tuple fields want three variants).
2. Add the code to `SUPPORTED_LOCALES`.
3. Extend the `email_locale` CHECK constraint — new migration **and**
   `docs/SUPABASE_SETUP_COMPLETE.sql`.
4. Add the code to `EmailLocale` in `frontend/lib/api/email-digest.ts` and to
   `LOCALE_PREVIEW` in `EmailDigestSettings.tsx`.
5. `test_every_locale_renders_subject_html_and_text` is parametrised over
   `SUPPORTED_LOCALES` and will pick the new locale up automatically.

Have a native speaker read the pack before shipping it. This is not a
formality — the first Ghanaian Pidgin pack had to be pulled because it was
written in Nigerian Pidgin. Copy that is *almost* someone's language reads worse
than plain English and damages trust.

---

## 7. Testing

```bash
cd backend && venv/bin/python -m pytest tests/test_email_digest.py -q
```

Covers scheduling windows, timezones, weekly cadence, opt-out/pause, HTML
escaping of hostile job data, locale fallback, variant rotation, absence of
pidgin markers in the English pack, and Svix signature verification
(valid / tampered / replayed / missing).

To eyeball a rendered email:

```python
from datetime import date
from app.services.email_copy import DigestJob, render_digest

jobs = [DigestJob("Data Analyst", "MTN Ghana", "Accra", "https://x/1", 0.91,
                  "Your SQL experience matches.", "GHS 6,000", "Full-time")]
out = render_digest(locale="en", first_name="Kwame", jobs=jobs,
                    user_id="u1", on_date=date.today(), cta_url="https://app/x",
                    unsubscribe_url="https://api/u?token=t", settings_url="https://app/s")
open("/tmp/preview.html", "w").write(out["html"])
```

---

## 8. Known gaps

* `EMAIL_POSTAL_ADDRESS` is wired into config but not yet rendered in the email
  footer. CAN-SPAM requires a physical mailing address on marketing mail — add
  it to `footer_reason` rendering before sending to US recipients.
* Locale is chosen by the user in settings; it is not inferred from
  `user_profiles.local_job_market` or signup country. New users default to
  `EMAIL_DEFAULT_LOCALE` (`en`).
* No engagement-based cooling: a subscriber who never opens keeps receiving.
  Consider pausing after N unopened digests once `opened_at` data accumulates.
* Bounce classification trusts Resend's `bounce_type`; anything not explicitly
  soft/transient is treated as a hard bounce.
