/**
 * Authentication Utilities
 * 
 * Helper functions for authentication using Supabase Auth.
 */

import { createClient, setRememberSession } from './supabase/client'
import type { User, Session } from '@supabase/supabase-js'

export interface SignUpData {
  email: string
  password: string
  metadata?: {
    full_name?: string
    [key: string]: any
  }
}

export interface SignInData {
  email: string
  password: string
  remember?: boolean
}

export interface PhoneOtpData {
  phone: string
  shouldCreateUser: boolean
  metadata?: {
    full_name?: string
    contact_email?: string
    handoff_email?: string
    source?: string
    ats_job_id?: string
  }
}

/** Normalize Ghana local numbers and accept already-international E.164. */
export function normalizePhoneNumber(value: string): string {
  const compact = value.trim().replace(/[\s()-]/g, '')
  let normalized = compact
  if (/^0\d{9}$/.test(compact)) normalized = `+233${compact.slice(1)}`
  else if (/^233\d{9}$/.test(compact)) normalized = `+${compact}`
  else if (/^\d{9}$/.test(compact)) normalized = `+233${compact}`

  if (!/^\+[1-9]\d{7,14}$/.test(normalized)) {
    throw new Error('Enter a valid phone number, for example 024 123 4567.')
  }
  return normalized
}

/** Ask Supabase Auth to generate an OTP; its signed hook delivers via Arkesel. */
export async function requestPhoneOtp(data: PhoneOtpData) {
  const supabase = createClient()
  const phone = normalizePhoneNumber(data.phone)
  const { data: authData, error } = await supabase.auth.signInWithOtp({
    phone,
    options: {
      shouldCreateUser: data.shouldCreateUser,
      data: data.metadata,
    },
  })
  if (error) throw error
  return { authData, phone }
}

/** Verify a Supabase phone OTP and establish the normal persisted session. */
export async function verifyPhoneOtp(phone: string, token: string) {
  const supabase = createClient()
  const { data, error } = await supabase.auth.verifyOtp({
    phone: normalizePhoneNumber(phone),
    token: token.trim(),
    type: 'sms',
  })
  if (error) throw error
  return data
}

/** Attach a phone to the email account without creating a second identity. */
export async function requestPhoneVerification(value: string) {
  const phone = normalizePhoneNumber(value)
  const { error } = await createClient().auth.updateUser({ phone })
  if (error) throw error
  return phone
}

export async function confirmPhoneVerification(phone: string, token: string) {
  const supabase = createClient()
  const { data, error } = await supabase.auth.verifyOtp({
    phone: normalizePhoneNumber(phone), token: token.trim(), type: 'phone_change',
  })
  if (error) throw error
  if (!data.user?.phone_confirmed_at) throw new Error('Phone verification is incomplete. Try again.')
  const { data: refreshed, error: refreshError } = await supabase.auth.refreshSession()
  if (refreshError) throw refreshError
  if (!refreshed.session) throw new Error('Please sign in to continue.')
  return refreshed
}

export function accountDestination(user: User): string {
  if (!user.email) return '/auth/setup-login'
  if (!user.phone || !user.phone_confirmed_at) return '/auth/verify-phone'
  return '/dashboard'
}

/** Upgrade a legacy phone account in place; Supabase owns email confirmation. */
export async function setEmailPassword(email: string, password: string) {
  const { data, error } = await createClient().auth.updateUser({
    email: email.trim().toLowerCase(), password,
  }, { emailRedirectTo: `${window.location.origin}/auth/setup-login` })
  if (error) throw error
  return data
}

/** Persist the email collected during phone registration as account metadata. */
export async function saveContactEmail(email: string) {
  const supabase = createClient()
  const { data, error } = await supabase.auth.updateUser({
    data: { contact_email: email.trim().toLowerCase() },
  })
  if (error) throw error
  return data
}

/**
 * Sign up a new user
 */
export async function signUp(data: SignUpData) {
  const supabase = createClient()
  const { data: authData, error } = await supabase.auth.signUp({
    email: data.email.trim().toLowerCase(),
    password: data.password,
    options: {
      data: data.metadata,
      emailRedirectTo: `${window.location.origin}/auth/verify-phone`,
    },
  })

  if (error) throw error
  return authData
}

/**
 * Sign in an existing user
 */
export async function signIn(data: SignInData) {
  setRememberSession(Boolean(data.remember))
  const supabase = createClient()
  const { data: authData, error } = await supabase.auth.signInWithPassword({
    email: data.email.trim().toLowerCase(),
    password: data.password,
  })

  if (error) throw error
  return authData
}

/**
 * Sign out current user
 */
export async function signOut() {
  const supabase = createClient()
  const { error } = await supabase.auth.signOut()
  if (error) throw error
}

/**
 * Get current user
 */
export async function getCurrentUser(): Promise<User | null> {
  const supabase = createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  return user
}

/**
 * Get current session
 */
export async function getCurrentSession(): Promise<Session | null> {
  const supabase = createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()
  return session
}

/**
 * Sign in with OAuth provider
 */
export async function signInWithOAuth(provider: 'google' | 'github' | 'linkedin') {
  const supabase = createClient()
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
    },
  })

  if (error) throw error
  return data
}

/**
 * Update password
 */
export async function updatePassword(newPassword: string) {
  const supabase = createClient()
  const { data, error } = await supabase.auth.updateUser({
    password: newPassword,
  })

  if (error) throw error
  return data
}
