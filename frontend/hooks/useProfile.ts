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
import { getUserErrorMessage } from '@/lib/errors'

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
      // Missing profiles and auth redirects are handled by the page/gate.
      if (![401, 403, 404].includes(error?.status)) {
        toast.error(getUserErrorMessage(error, 'Could not load your profile. Please try again.'))
      }
      setProfile(null)
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
      toast.error(getUserErrorMessage(error, 'Could not save your profile. Please try again.'))
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
