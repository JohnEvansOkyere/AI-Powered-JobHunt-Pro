BEGIN;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_users_is_admin ON public.users(is_admin);

-- Grant the existing owner account access during the migration. Future
-- operators can be promoted by changing this Boolean in Supabase Table Editor.
UPDATE public.users
SET is_admin = TRUE
WHERE lower(email) = 'okyerevansjohn@gmail.com';

COMMIT;

-- Rollback:
-- DROP INDEX IF EXISTS idx_users_is_admin;
-- ALTER TABLE public.users DROP COLUMN IF EXISTS is_admin;
