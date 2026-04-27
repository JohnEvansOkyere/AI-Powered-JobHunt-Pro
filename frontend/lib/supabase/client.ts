/**
 * Supabase Client for Client Components
 * 
 * This client is used in client-side React components.
 * For server components, use the server client.
 */

import { createBrowserClient } from '@supabase/ssr'

const REMEMBER_SESSION_KEY = 'veloxahire-remember-session'

function shouldPersistSession() {
  if (typeof window === 'undefined') {
    return false
  }

  return window.localStorage.getItem(REMEMBER_SESSION_KEY) === 'true'
}

const browserSessionStorage = {
  getItem(key: string) {
    if (typeof window === 'undefined') {
      return null
    }

    const storage = shouldPersistSession() ? window.localStorage : window.sessionStorage
    return storage.getItem(key)
  },
  setItem(key: string, value: string) {
    if (typeof window === 'undefined') {
      return
    }

    const primaryStorage = shouldPersistSession() ? window.localStorage : window.sessionStorage
    const secondaryStorage = shouldPersistSession() ? window.sessionStorage : window.localStorage

    primaryStorage.setItem(key, value)
    secondaryStorage.removeItem(key)
  },
  removeItem(key: string) {
    if (typeof window === 'undefined') {
      return
    }

    window.localStorage.removeItem(key)
    window.sessionStorage.removeItem(key)
  },
}

export function setRememberSession(remember: boolean) {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(REMEMBER_SESSION_KEY, String(remember))
}

export function getRememberSessionPreference() {
  if (typeof window === 'undefined') {
    return false
  }

  return shouldPersistSession()
}

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        storage: browserSessionStorage,
      },
    }
  )
}
