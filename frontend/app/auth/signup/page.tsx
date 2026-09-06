'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { signUp, accountDestination } from '@/lib/auth'
import { useAuth } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api/client'
import { toast } from 'react-hot-toast'
import { trackEvent } from '@/lib/analytics'
import { AccountForm, accountInput, accountButton, accountLabel } from '@/components/auth/AccountForm'

interface HandoffVerifyResponse {
  valid: boolean; email?: string | null; full_name?: string | null; phone?: string | null; job_id?: string | null
}
const handoffVerifyCache = new Map<string, Promise<HandoffVerifyResponse>>()
function verifyHandoffToken(token: string) {
  const cached = handoffVerifyCache.get(token)
  if (cached) return cached
  const request = apiClient.post<HandoffVerifyResponse>('/auth/handoff/verify', { token })
  handoffVerifyCache.set(token, request)
  return request
}

function SignUpContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user } = useAuth()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [handoff, setHandoff] = useState<HandoffVerifyResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [emailPending, setEmailPending] = useState(false)

  useEffect(() => { if (user) router.replace(accountDestination(user)) }, [user, router])
  useEffect(() => {
    const token = searchParams.get('h')
    if (!token) return
    let cancelled = false
    verifyHandoffToken(token).then((result) => {
      if (cancelled || !result.valid) return
      setHandoff(result)
      if (result.full_name) setFullName(result.full_name)
      if (result.email) setEmail(result.email)
    }).catch(() => undefined)
    return () => { cancelled = true }
  }, [searchParams])

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (loading) return
    setLoading(true)
    try {
      void trackEvent({ event_name: 'signup_started', path: '/auth/signup' })
      const result = await signUp({ email, password, metadata: {
        full_name: fullName.trim(), contact_email: email.trim().toLowerCase(),
        handoff_email: handoff?.email || undefined,
        handoff_phone: handoff?.phone || undefined,
        source: handoff ? 'veloxarecruit_apply_handoff' : undefined,
        ats_job_id: handoff?.job_id || undefined,
      } })
      setPassword('')
      if (!result.session) { setEmailPending(true); return }
      router.replace('/auth/verify-phone')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not create your account.')
    } finally { setLoading(false) }
  }

  return <AccountForm title={emailPending ? 'Check your email' : 'Create your free account'}
    description={emailPending ? 'Open the confirmation link, then continue with phone verification. If you already have an account, sign in below.' : 'Create your account, then verify your phone once.'}>
    {handoff && <p className="mt-5 text-sm text-emerald-700">Application details imported from VeloxaRecruit.</p>}
    {!emailPending && <form method="post" onSubmit={submit} className="mt-8 space-y-5">
      <div><label htmlFor="fullName" className={accountLabel}>Full name</label>
        <input id="fullName" name="fullName" autoComplete="name" required maxLength={150} value={fullName} onChange={(e) => setFullName(e.target.value)} className={accountInput} /></div>
      <div><label htmlFor="email" className={accountLabel}>Email address</label>
        <input id="email" name="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={accountInput} /></div>
      <div><label htmlFor="password" className={accountLabel}>Password</label>
        <input id="password" name="password" type="password" autoComplete="new-password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className={accountInput} aria-describedby="password-help" />
        <p id="password-help" className="mt-2 text-xs text-neutral-500">Use at least 8 characters.</p></div>
      <button disabled={loading || !fullName.trim()} className={accountButton}>{loading ? 'Creating account…' : 'Create account'}</button>
    </form>}
    <p className="mt-4 text-xs text-neutral-500">By creating an account you agree to our <Link href="/terms" className="underline">Terms</Link> and <Link href="/privacy" className="underline">Privacy Policy</Link>.</p>
  </AccountForm>
}

export default function SignUpPage() {
  return <Suspense fallback={<div className="min-h-screen bg-cream-50" />}><SignUpContent /></Suspense>
}
