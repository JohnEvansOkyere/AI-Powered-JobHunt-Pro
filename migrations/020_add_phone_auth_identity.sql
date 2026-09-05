BEGIN;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS phone_e164 TEXT,
    ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_e164_unique
    ON public.users(phone_e164)
    WHERE phone_e164 IS NOT NULL;

CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (
        id,
        email,
        phone_e164,
        email_verified,
        phone_verified,
        full_name,
        metadata
    )
    VALUES (
        NEW.id,
        NEW.email,
        NEW.phone,
        COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
        COALESCE(NEW.phone_confirmed_at IS NOT NULL, false),
        NULLIF(NEW.raw_user_meta_data->>'full_name', ''),
        COALESCE(NEW.raw_user_meta_data, '{}'::jsonb)
    )
    ON CONFLICT (id) DO UPDATE
    SET
        email = EXCLUDED.email,
        phone_e164 = EXCLUDED.phone_e164,
        email_verified = COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
        phone_verified = COALESCE(NEW.phone_confirmed_at IS NOT NULL, false),
        full_name = COALESCE(EXCLUDED.full_name, public.users.full_name),
        metadata = COALESCE(NEW.raw_user_meta_data, '{}'::jsonb),
        updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

INSERT INTO public.users (
    id,
    email,
    phone_e164,
    email_verified,
    phone_verified,
    full_name,
    metadata
)
SELECT
    id,
    email,
    phone,
    COALESCE(email_confirmed_at IS NOT NULL, false),
    COALESCE(phone_confirmed_at IS NOT NULL, false),
    NULLIF(raw_user_meta_data->>'full_name', ''),
    COALESCE(raw_user_meta_data, '{}'::jsonb)
FROM auth.users
ON CONFLICT (id) DO UPDATE
SET
    email = EXCLUDED.email,
    phone_e164 = EXCLUDED.phone_e164,
    email_verified = EXCLUDED.email_verified,
    phone_verified = EXCLUDED.phone_verified,
    full_name = COALESCE(EXCLUDED.full_name, public.users.full_name),
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

COMMIT;

-- Rollback (only after returning the app to email-only identity):
-- DROP INDEX IF EXISTS public.idx_users_phone_e164_unique;
-- ALTER TABLE public.users DROP COLUMN IF EXISTS phone_verified;
-- ALTER TABLE public.users DROP COLUMN IF EXISTS phone_e164;
