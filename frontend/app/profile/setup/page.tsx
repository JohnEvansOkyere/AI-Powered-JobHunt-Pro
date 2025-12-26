'use client'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { ProfileForm } from '@/components/profile/ProfileForm'
import { useRouter } from 'next/navigation'
import { useProfile } from '@/hooks/useProfile'
import { useAuth } from '@/hooks/useAuth'
import { ArrowLeft } from 'lucide-react'

export default function ProfileSetupPage() {
  const router = useRouter()
  const { loading } = useProfile()
  const { logout } = useAuth()

  const handleComplete = () => {
    router.push('/dashboard')
  }

  const handleBack = () => {
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
          {/* Navigation Header */}
          <div className="flex items-center justify-between mb-8">
            <button
              onClick={handleBack}
              className="flex items-center space-x-2 text-neutral-600 hover:text-neutral-800 transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
              <span>Back to Dashboard</span>
            </button>
            <button
              onClick={logout}
              className="text-sm text-neutral-500 hover:text-neutral-700 transition-colors"
            >
              Sign Out
            </button>
          </div>

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

