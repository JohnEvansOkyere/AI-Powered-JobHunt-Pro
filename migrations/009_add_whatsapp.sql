-- Migration 009: WhatsApp notifications (opt-in, outbound audit, inbound webhook).
-- Part of docs/RECOMMENDATIONS_V2_PLAN.md §6.3 (Phase 4 — WhatsApp delivery).
--
-- What this does:
--   1. Creates `notification_preferences` (one row per user; WhatsApp is the
--      first channel, others can be added here later).
--   2. Creates `whatsapp_messages` — append-only audit log of every send.
--   3. Creates `whatsapp_incoming_events` — inbound webhook events (status
--      callbacks + user-initiated messages).
--
-- Design notes:
--   - Consent columns live on a dedicated table rather than `user_profiles`
--     so notifications can grow to email/SMS/etc. without bloating profiles.
--   - `whatsapp_messages.user_id` uses `ON DELETE SET NULL` so abuse records
--     survive account deletion long enough for retention policy to handle
--     them (regulatory minimum is 7y in many jurisdictions).
--   - Status uses a CHECK constraint (not an enum) because Meta occasionally
--     adds new states; extending a CHECK is easier than a real enum.
--
-- Rollback (manual):
--   DROP TABLE whatsapp_incoming_events;
--   DROP TABLE whatsapp_messages;
--   DROP TABLE notification_preferences;

BEGIN;

-- 1. Per-user notification preferences.
CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id                     UUID         PRIMARY KEY,
    whatsapp_opted_in           BOOLEAN      NOT NULL DEFAULT FALSE,
    whatsapp_opted_in_at        TIMESTAMPTZ  NULL,
    whatsapp_opt_in_source      TEXT         NULL,
    whatsapp_phone_e164         TEXT         NULL,
    whatsapp_phone_verified_at  TIMESTAMPTZ  NULL,
    whatsapp_digest_time_local  TEXT         NOT NULL DEFAULT '08:00',
    whatsapp_timezone           TEXT         NOT NULL DEFAULT 'UTC',
    whatsapp_opted_out_at       TIMESTAMPTZ  NULL,
    whatsapp_paused_until       TIMESTAMPTZ  NULL,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT notification_preferences_opt_in_source_check
        CHECK (
            whatsapp_opt_in_source IS NULL
            OR whatsapp_opt_in_source IN ('signup', 'profile_page', 'admin')
        ),
    CONSTRAINT notification_preferences_digest_time_format
        CHECK (whatsapp_digest_time_local ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$')
);

COMMENT ON TABLE  notification_preferences                       IS 'Per-user notification channel preferences. WhatsApp is the first channel.';
COMMENT ON COLUMN notification_preferences.whatsapp_phone_e164   IS 'E.164 phone, digits-only with leading + (e.g. +233241234567).';
COMMENT ON COLUMN notification_preferences.whatsapp_timezone     IS 'IANA timezone name used with whatsapp_digest_time_local (e.g. Africa/Accra).';
COMMENT ON COLUMN notification_preferences.whatsapp_paused_until IS 'Optional soft pause (user can unpause themselves). Hard opt-out uses whatsapp_opted_out_at.';

CREATE INDEX IF NOT EXISTS idx_notification_preferences_opted_in
    ON notification_preferences(whatsapp_opted_in)
    WHERE whatsapp_opted_in = TRUE;

CREATE INDEX IF NOT EXISTS idx_notification_preferences_phone
    ON notification_preferences(whatsapp_phone_e164)
    WHERE whatsapp_phone_e164 IS NOT NULL;

-- 2. Outbound message audit log.
CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID         NULL,
    template_name         TEXT         NOT NULL,
    template_language     TEXT         NOT NULL DEFAULT 'en',
    phone_e164            TEXT         NOT NULL,
    payload_hash          TEXT         NOT NULL,
    idempotency_key       TEXT         NULL,
    provider_message_id   TEXT         NULL,
    status                TEXT         NOT NULL DEFAULT 'queued',
    error_code            TEXT         NULL,
    error_message         TEXT         NULL,
    sent_at               TIMESTAMPTZ  NULL,
    delivered_at          TIMESTAMPTZ  NULL,
    read_at               TIMESTAMPTZ  NULL,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT whatsapp_messages_status_check
        CHECK (
            status IN (
                'queued',
                'sent',
                'delivered',
                'read',
                'failed',
                'rate_limited',
                'opt_out_blocked'
            )
        )
);

COMMENT ON TABLE  whatsapp_messages                       IS 'Append-only audit of every outbound WhatsApp send attempt.';
COMMENT ON COLUMN whatsapp_messages.user_id               IS 'Nullable so records survive account deletion for the retention window.';
COMMENT ON COLUMN whatsapp_messages.payload_hash          IS 'SHA-256 of the rendered template + variables, for dedup.';
COMMENT ON COLUMN whatsapp_messages.idempotency_key       IS 'Caller-supplied key (usually hash(user_id|date|template)). Prevents double-sends on retry.';
COMMENT ON COLUMN whatsapp_messages.provider_message_id   IS 'Meta Cloud API message id. Populated on success.';

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_user_id
    ON whatsapp_messages(user_id);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_status
    ON whatsapp_messages(status);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_phone_created
    ON whatsapp_messages(phone_e164, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_whatsapp_messages_idempotency_key
    ON whatsapp_messages(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- 3. Inbound webhook events (status callbacks + user replies).
CREATE TABLE IF NOT EXISTS whatsapp_incoming_events (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_e164    TEXT         NOT NULL,
    user_id       UUID         NULL,
    event_type    TEXT         NOT NULL,
    body          TEXT         NULL,
    raw           JSONB        NOT NULL,
    received_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT whatsapp_incoming_events_type_check
        CHECK (event_type IN ('text', 'status_update', 'button', 'interactive', 'other'))
);

COMMENT ON TABLE  whatsapp_incoming_events            IS 'Raw audit of inbound webhook events. Used to evidence consent + STOP keyword handling.';
COMMENT ON COLUMN whatsapp_incoming_events.raw        IS 'Full webhook payload for this event. Redact in response logs.';

CREATE INDEX IF NOT EXISTS idx_whatsapp_incoming_events_phone
    ON whatsapp_incoming_events(phone_e164);

CREATE INDEX IF NOT EXISTS idx_whatsapp_incoming_events_user
    ON whatsapp_incoming_events(user_id)
    WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_whatsapp_incoming_events_received_at
    ON whatsapp_incoming_events(received_at DESC);

-- 4. Keep `updated_at` fresh on notification_preferences edits.
CREATE OR REPLACE FUNCTION notification_preferences_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notification_preferences_updated_at ON notification_preferences;
CREATE TRIGGER trg_notification_preferences_updated_at
    BEFORE UPDATE ON notification_preferences
    FOR EACH ROW
    EXECUTE FUNCTION notification_preferences_touch_updated_at();

COMMIT;
