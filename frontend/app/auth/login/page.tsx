'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { accountDestination, signIn } from '@/lib/auth'
import { getRememberSessionPreference } from '@/lib/supabase/client'
import { toast } from 'react-hot-toast'
import { trackEvent } from '@/lib/analytics'
import { AccountForm, accountInput, accountButton, accountLabel } from '@/components/auth/AccountForm'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)
  const [loading, setLoading] = useState(false)
  useEffect(() => setRemember(getRememberSessionPreference()), [])

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (loading) return
    setLoading(true)
    try {
      void trackEvent({ event_name: 'login_started', path: '/auth/login', metadata: { method: 'email_password' } })
      const result = await signIn({ email, password, remember })
      if (!result.user || !result.session) throw new Error('Please try signing in again.')
      void trackEvent({ event_name: 'login_completed', path: '/auth/login', metadata: { method: 'email_password' } })
      router.replace(accountDestination(result.user))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to sign in.')
    } finally { setLoading(false) }
  }

  return <AccountForm variant="login" title="Welcome back" description="Sign in with your email and password.">
    <form method="post" onSubmit={submit} className="mt-8 space-y-5">
      <div><label htmlFor="email" className={accountLabel}>Email address</label>
        <input id="email" name="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={accountInput} /></div>
      <div><label htmlFor="password" className={accountLabel}>Password</label>
        <input id="password" name="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className={accountInput} /></div>
      <label className="flex items-center gap-2 text-sm text-neutral-600"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />Keep me signed in</label>
      <button disabled={loading} className={accountButton}>{loading ? 'Signing in…' : 'Sign in'}</button>
    </form>
    <Link href="/auth/reset-password" className="mt-5 block text-sm font-semibold text-brand-turquoise-700">Forgot password?</Link>
    <p className="mt-5 text-sm text-neutral-500">Previously signed up with only a phone? <Link href="/auth/setup-login" className="font-semibold text-brand-turquoise-700">Set up email sign-in</Link></p>
  </AccountForm>
}
