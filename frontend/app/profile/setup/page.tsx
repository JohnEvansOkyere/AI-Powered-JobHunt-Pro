'use client'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { ProfileForm } from '@/components/profile/ProfileForm'
import { useRouter } from 'next/navigation'
import { useProfile } from '@/hooks/useProfile'

export default function ProfileSetupPage() {
  const router = useRouter()
  const { loading } = useProfile()

  const handleComplete = () => {
    router.push('/dashboard')
  }

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-700"></div>
        </div>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-neutral-800 mb-2">
              Complete Your Profile
            </h1>
            <p className="text-neutral-600">
              Help us match you with the perfect jobs by completing your profile
            </p>
          </div>
          <ProfileForm onComplete={handleComplete} />
        </div>
      </div>
    </ProtectedRoute>
  )
}

