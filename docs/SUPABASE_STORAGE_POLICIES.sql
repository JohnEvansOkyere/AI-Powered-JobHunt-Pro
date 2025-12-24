-- =====================================================
-- Supabase Storage Policies for CV Management
-- =====================================================
-- 
-- These policies allow users to manage their own CV files
-- in the 'cvs' storage bucket.
--
-- Run this in Supabase SQL Editor after creating the 'cvs' bucket.
-- =====================================================

-- Enable RLS on storage.objects (should already be enabled)
-- ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Policy: Users can upload their own CVs
-- Files are stored as: {user_id}/{cv_id}.{ext}
CREATE POLICY "Users can upload their own CVs"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'cvs' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Policy: Users can read their own CVs
CREATE POLICY "Users can read their own CVs"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'cvs' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Policy: Users can update their own CVs
CREATE POLICY "Users can update their own CVs"
ON storage.objects FOR UPDATE
TO authenticated
USING (
  bucket_id = 'cvs' 
  AND auth.uid()::text = (storage.foldername(name))[1]
)
WITH CHECK (
  bucket_id = 'cvs' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Policy: Users can delete their own CVs
CREATE POLICY "Users can delete their own CVs"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'cvs' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Note: Service role key bypasses RLS, so backend can manage files
-- on behalf of users using the service client.

