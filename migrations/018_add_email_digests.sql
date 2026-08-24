-- Migration 018: Email recommendation digests (opt-in, outbound audit, suppressions).
-- Companion to migrations/009_add_whatsapp.sql — email is the second delivery
-- channel and reuses the channel-aware `notification_preferences` table.
--
-- What this does:
--   1. Adds `email_*` columns to `notification_preferences`.
--   2. Creates `email_messages` — append-only audit log of every send attempt.
--   3. Creates `email_suppressions` — hard blocklist fed by bounces/complaints.
--
-- Design notes:
--   - `email_locale` drives which language pack renders the digest
--     ('en' | 'twi'). Job titles/companies always stay verbatim.
--   - `email_unsubscribe_token` backs one-click unsubscribe links (RFC 8058 /
--     CAN-SPAM). It is a per-user random secret so the link needs no auth
--     session, and it is regenerated on re-opt-in so leaked old links die.
--   - `email_suppressions` is checked before EVERY send. A hard bounce or a
--     spam complaint must permanently stop mail to that address even if the
--     user row still says opted-in — deliverability depends on honouring it.
--   - `email_messages.user_id` uses ON DELETE SET NULL, matching
--     whatsapp_messages, so abuse/compliance evidence outlives the account.
--
-- Rollback (manual):
--   DROP TABLE email_suppressions;
--   DROP TABLE email_messages;
--   ALTER TABLE notification_preferences
--     DROP COLUMN email_opted_in, DROP COLUMN email_opted_in_at,
--     DROP COLUMN email_opt_in_source, DROP COLUMN email_address,
--     DROP COLUMN email_verified_at, DROP COLUMN email_digest_time_local,
--     DROP COLUMN email_timezone, DROP COLUMN email_locale,
--     DROP COLUMN email_digest_frequency, DROP COLUMN email_digest_weekday,
--     DROP COLUMN email_opted_out_at, DROP COLUMN email_paused_until,
--     DROP COLUMN email_unsubscribe_token;

BEGIN;

-- 1. Email consent + delivery preferences on the shared channel table.
ALTER TABLE notification_preferences
    ADD COLUMN IF NOT EXISTS email_opted_in          BOOLEAN     NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS email_opted_in_at       TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS email_opt_in_source     TEXT        NULL,
    ADD COLUMN IF NOT EXISTS email_address           TEXT        NULL,
    ADD COLUMN IF NOT EXISTS email_verified_at       TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS email_digest_time_local TEXT        NOT NULL DEFAULT '07:00',
    ADD COLUMN IF NOT EXISTS email_timezone          TEXT        NOT NULL DEFAULT 'UTC',
    ADD COLUMN IF NOT EXISTS email_locale            TEXT        NOT NULL DEFAULT 'en',
    ADD COLUMN IF NOT EXISTS email_digest_frequency  TEXT        NOT NULL DEFAULT 'daily',
    ADD COLUMN IF NOT EXISTS email_digest_weekday    SMALLINT    NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS email_opted_out_at      TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS email_paused_until      TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS email_unsubscribe_token TEXT        NULL;

ALTER TABLE notification_preferences
    DROP CONSTRAINT IF EXISTS notification_preferences_email_opt_in_source_check;
ALTER TABLE notification_preferences
    ADD CONSTRAINT notification_preferences_email_opt_in_source_check
    CHECK (
        email_opt_in_source IS NULL
        OR email_opt_in_source IN ('signup', 'profile_page', 'admin')
    );

ALTER TABLE notification_preferences
    DROP CONSTRAINT IF EXISTS notification_preferences_email_digest_time_format;
ALTER TABLE notification_preferences
    ADD CONSTRAINT notification_preferences_email_digest_time_format
    CHECK (email_digest_time_local ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$');

ALTER TABLE notification_preferences
    DROP CONSTRAINT IF EXISTS notification_preferences_email_locale_check;
ALTER TABLE notification_preferences
    ADD CONSTRAINT notification_preferences_email_locale_check
    CHECK (email_locale IN ('en', 'twi'));

ALTER TABLE notification_preferences
    DROP CONSTRAINT IF EXISTS notification_preferences_email_frequency_check;
ALTER TABLE notification_preferences
    ADD CONSTRAINT notification_preferences_email_frequency_check
    CHECK (email_digest_frequency IN ('daily', 'weekly'));

ALTER TABLE notification_preferences
    DROP CONSTRAINT IF EXISTS notification_preferences_email_weekday_check;
ALTER TABLE notification_preferences
    ADD CONSTRAINT notification_preferences_email_weekday_check
    CHECK (email_digest_weekday BETWEEN 0 AND 6);

ALTER TABLE notification_preferences
    DROP CONSTRAINT IF EXISTS notification_preferences_email_unsub_token_key;
ALTER TABLE notification_preferences
    ADD CONSTRAINT notification_preferences_email_unsub_token_key
    UNIQUE (email_unsubscribe_token);

COMMENT ON COLUMN notification_preferences.email_address           IS 'Delivery address. NULL means fall back to public.users.email.';
COMMENT ON COLUMN notification_preferences.email_locale            IS 'Language pack: en (Ghanaian-register English) | twi.';
COMMENT ON COLUMN notification_preferences.email_timezone          IS 'IANA timezone used with email_digest_time_local (e.g. Africa/Accra).';
COMMENT ON COLUMN notification_preferences.email_digest_weekday    IS 'Weekly sends only. 0=Monday .. 6=Sunday, matching Python weekday().';
COMMENT ON COLUMN notification_preferences.email_unsubscribe_token IS 'Random secret backing one-click unsubscribe links. Rotated on re-opt-in.';

CREATE INDEX IF NOT EXISTS idx_notification_preferences_email_opted_in
    ON notification_preferences(email_opted_in)
    WHERE email_opted_in = TRUE;

CREATE INDEX IF NOT EXISTS idx_notification_preferences_email_address
    ON notification_preferences(LOWER(email_address))
    WHERE email_address IS NOT NULL;

-- 2. Outbound audit log.
CREATE TABLE IF NOT EXISTS email_messages (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NULL,
    email_address       TEXT        NOT NULL,
    template_name       TEXT        NOT NULL,
    locale              TEXT        NOT NULL DEFAULT 'en',
    subject             TEXT        NOT NULL,
    payload_hash        TEXT        NOT NULL,
    idempotency_key     TEXT        NULL UNIQUE,
    provider_message_id TEXT        NULL,
    status              TEXT        NOT NULL DEFAULT 'queued',
    job_count           INTEGER     NOT NULL DEFAULT 0,
    error_code          TEXT        NULL,
    error_message       TEXT        NULL,
    sent_at             TIMESTAMPTZ NULL,
    delivered_at        TIMESTAMPTZ NULL,
    opened_at           TIMESTAMPTZ NULL,
    clicked_at          TIMESTAMPTZ NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT email_messages_status_check
        CHECK (status IN (
            'queued', 'sent', 'delivered', 'opened', 'clicked',
            'bounced', 'complained', 'failed', 'rate_limited', 'opt_out_blocked'
        ))
);

ALTER TABLE email_messages
    DROP CONSTRAINT IF EXISTS fk_email_messages_user_id;
ALTER TABLE email_messages
    ADD CONSTRAINT fk_email_messages_user_id
    FOREIGN KEY (user_id)
    REFERENCES public.users(id)
    ON DELETE SET NULL;

COMMENT ON TABLE email_messages IS 'Append-only audit of every outbound marketing/digest email attempt.';

CREATE INDEX IF NOT EXISTS idx_email_messages_user_id     ON email_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_status      ON email_messages(status);
CREATE INDEX IF NOT EXISTS idx_email_messages_created_at  ON email_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_email_messages_provider_id ON email_messages(provider_message_id)
    WHERE provider_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_email_messages_addr_created
    ON email_messages(LOWER(email_address), created_at);

-- 3. Hard suppression list (bounces, complaints, manual blocks).
CREATE TABLE IF NOT EXISTS email_suppressions (
    email_address TEXT        PRIMARY KEY,
    reason        TEXT        NOT NULL,
    detail        TEXT        NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT email_suppressions_reason_check
        CHECK (reason IN ('hard_bounce', 'complaint', 'manual', 'invalid'))
);

COMMENT ON TABLE email_suppressions IS 'Addresses we must never mail again. Checked before every send.';

COMMIT;
