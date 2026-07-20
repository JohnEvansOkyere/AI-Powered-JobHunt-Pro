BEGIN;

-- Account suspension is enforced by the backend authentication dependency.
-- Normalize the existing column so every platform account has an explicit status.
UPDATE public.users
SET is_active = TRUE
WHERE is_active IS NULL;

ALTER TABLE public.users
    ALTER COLUMN is_active SET DEFAULT TRUE,
    ALTER COLUMN is_active SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_is_active ON public.users(is_active);

COMMIT;

-- Rollback:
-- ALTER TABLE public.users ALTER COLUMN is_active DROP NOT NULL;
