-- =====================================================
-- Auto-Create User Profile on Signup
-- =====================================================
-- This trigger automatically creates a user_profile entry
-- when a new user is created in auth.users

-- Function to create user profile when user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING; -- Prevent duplicate if trigger fires twice
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to call the function when a new user is created
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- =====================================================
-- For Existing Users
-- =====================================================
-- If you have existing users without profiles, run this:
-- INSERT INTO public.user_profiles (user_id)
-- SELECT id FROM auth.users
-- WHERE id NOT IN (SELECT user_id FROM public.user_profiles)
-- ON CONFLICT (user_id) DO NOTHING;

