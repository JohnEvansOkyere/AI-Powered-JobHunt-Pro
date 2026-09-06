/**
 * Protected Route Component
 * 
 * Wraps routes that require authentication.
 * Redirects to login if user is not authenticated.
 */

'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { accountDestination } from '@/lib/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (loading) {
      return
    }

    if (!user) {
      router.push('/auth/login')
    } else if (accountDestination(user) !== '/dashboard') {
      router.replace(accountDestination(user))
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-700"></div>
      </div>
    )
  }

  if (!user || accountDestination(user) !== '/dashboard') {
    return null
  }

  return <>{children}</>
}
