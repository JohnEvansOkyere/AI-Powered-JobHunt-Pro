/**
 * useAuth Hook
 * 
 * React hook for managing authentication state.
 */

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getCurrentUser, getCurrentSession, signOut } from '@/lib/auth'
import { createClient } from '@/lib/supabase/client'
import type { User, Session } from '@supabase/supabase-js'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    // Add timeout to prevent infinite loading
    const timeout = setTimeout(() => {
      setLoading(false)
    }, 3000) // 3 second timeout

    // Get initial session
    getCurrentSession()
      .then((session) => {
        setSession(session)
        setUser(session?.user ?? null)
        setLoading(false)
        clearTimeout(timeout)
      })
      .catch((error) => {
        console.error('Error getting session:', error)
        setLoading(false)
        clearTimeout(timeout)
      })

    // Listen for auth changes
    const supabase = createClient()
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    })

    return () => {
      clearTimeout(timeout)
      subscription.unsubscribe()
    }
  }, [])

  const logout = async () => {
    await signOut()
    setUser(null)
    setSession(null)
    router.push('/auth/login')
  }

  return {
    user,
    session,
    loading,
    isAuthenticated: !!user,
    logout,
  }
}

