/**
 * useProfile Hook
 * 
 * React hook for managing user profile state and operations.
 */

import { useState, useEffect } from 'react'
import { getMyProfile, createProfile, updateProfile } from '@/lib/api/profiles'
import { useAuth } from '@/hooks/useAuth'
import type { UserProfile, UserProfileFormData } from '@/types/profile'
import { toast } from 'react-hot-toast'

export function useProfile() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const { isAuthenticated, loading: authLoading } = useAuth()

  useEffect(() => {
    if (authLoading) {
      return
    }

    if (!isAuthenticated) {
      setProfile(null)
      setLoading(false)
      return
    }

    void loadProfile()
  }, [authLoading, isAuthenticated])

  const loadProfile = async () => {
    try {
      setLoading(true)
      const data = await getMyProfile()
      setProfile(data)
    } catch (error: any) {
      const isAuthFailure =
        error?.message === 'Email verification required' ||
        error?.status === 401 ||
        error?.status === 403

      if (!isAuthFailure) {
        console.error('Error loading profile:', error)
      }
      
      // Don't show error toast for 404 - profile will be created
      // Only show error for actual connection/server errors
      if (error.message?.includes('404') || error.message?.includes('not found')) {
        // Profile doesn't exist yet - backend will auto-create on next request
        // Don't set profile to null, let it be handled by the component
        setProfile(null)
      } else if (error.message?.includes('Database') || error.message?.includes('connection')) {
        // Database connection error - show error but don't redirect
        toast.error('Database connection error. Please check your configuration.')
        setProfile(null)
      } else if (isAuthFailure) {
        // Auth redirect will handle this path; avoid repeated toasts while the session clears.
        setProfile(null)
      } else {
        // Other errors
        toast.error(error.message || 'Failed to load profile')
        setProfile(null)
      }
    } finally {
      setLoading(false)
    }
  }

  const saveProfile = async (data: UserProfileFormData) => {
    try {
      setSaving(true)
      let updatedProfile: UserProfile

      if (profile) {
        // Update existing profile
        updatedProfile = await updateProfile(data)
      } else {
        // Create new profile
        updatedProfile = await createProfile(data)
      }

      setProfile(updatedProfile)
      toast.success('Profile saved successfully!')
      return updatedProfile
    } catch (error: any) {
      console.error('Error saving profile:', error)
      toast.error(error.message || 'Failed to save profile')
      throw error
    } finally {
      setSaving(false)
    }
  }

  return {
    profile,
    loading,
    saving,
    hasProfile: !!profile,
    loadProfile,
    saveProfile,
  }
}
