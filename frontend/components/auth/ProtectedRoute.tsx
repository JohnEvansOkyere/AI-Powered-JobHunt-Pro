/**
 * Protected Route Component
 * 
 * Wraps routes that require authentication.
 * Redirects to login if user is not authenticated.
 */

'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { getMyProfile } from '@/lib/api/profiles'
import { getActiveCV, isCVReady } from '@/lib/api/cvs'
import { isMatchingProfileReady } from '@/lib/profile-utils'
import { accountDestination } from '@/lib/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, loading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

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

  if (pathname === '/dashboard' || pathname === '/dashboard/recommendations') {
    return <MatchingProfileGate key={`${user.id}:${pathname}`}>{children}</MatchingProfileGate>
  }
  return <>{children}</>
}

function MatchingProfileGate({ children }: ProtectedRouteProps) {
  const router = useRouter()
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    Promise.all([getMyProfile(), getActiveCV()]).then(([profile, cv]) => {
      if (!active) return
      if (isMatchingProfileReady(profile) && isCVReady(cv)) setState('ready')
      else router.replace('/profile/setup')
    }).catch(() => { if (active) setState('error') })
    return () => { active = false }
  }, [router, attempt])
  if (state === 'ready') return <>{children}</>
  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="max-w-md space-y-4 text-center">
        {state === 'error' ? <>
          <h1 className="text-xl font-semibold">We couldn’t load your profile</h1>
          <p role="alert">Try again to continue setting up your job matches.</p>
          <button className="btn-primary" onClick={() => { setState('loading'); setAttempt((value) => value + 1) }}>Try again</button>
          <Link className="block underline" href="/jobs">Browse jobs</Link>
        </> : <p role="status">Checking your profile…</p>}
      </div>
    </main>
  )
}
