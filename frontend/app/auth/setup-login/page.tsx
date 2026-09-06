'use client'

import { getUserErrorMessage } from '@/lib/errors'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { accountDestination, getCurrentUser, requestPhoneOtp, setEmailPassword, verifyPhoneOtp } from '@/lib/auth'
import { AccountForm, accountButton, accountInput, accountLabel } from '@/components/auth/AccountForm'
import { PhoneCodeForm } from '@/components/auth/PhoneCodeForm'

export default function SetupLoginPage() {
  const { user, loading, logout } = useAuth()
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const emailPending = pending || Boolean(user?.new_email)
  const savedEmail = user?.new_email || user?.email || user?.user_metadata?.contact_email || ''
  useEffect(() => { setEmail((value) => value || savedEmail) }, [savedEmail])
  useEffect(() => {
    if (user?.email && !user.new_email) router.replace(accountDestination(user))
  }, [user, router])
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (busy) return
    setBusy(true); setError('')
    try {
      const result = await setEmailPassword(email, password)
      setPassword('')
      if (!result.user.email || result.user.new_email) { setPending(true); return }
      router.replace(accountDestination(result.user))
    } catch (err) { setError(getUserErrorMessage(err, 'Could not set up email sign-in.')) }
    finally { setBusy(false) }
  }
  const checkConfirmation = async () => {
    setBusy(true); setError('')
    try {
      const current = await getCurrentUser()
      if (!current?.email || current.new_email) throw new Error('Open the confirmation link in your email first.')
      router.replace(accountDestination(current))
    } catch (err) { setError(getUserErrorMessage(err, 'Could not check your email confirmation.')) }
    finally { setBusy(false) }
  }

  return <AccountForm title={emailPending ? 'Confirm your email' : 'Set up email sign-in'} description={emailPending ? 'Open the link sent to your email, then continue. Your profile stays on this account.' : user ? 'Add your email and a password. You’ll use these for future sign-ins.' : 'For existing phone-only accounts: confirm your phone to add an email and password.'}>
    {loading ? <p className="mt-8" role="status">Loading your account…</p> : !user ? <PhoneCodeForm
      onRequest={async (phone) => (await requestPhoneOtp({ phone, shouldCreateUser: false })).phone}
      onVerify={async (phone, code) => {
        const result = await verifyPhoneOtp(phone, code)
        if (!result.session) throw new Error('Please try verifying your phone again.')
        setEmail(result.user?.email || result.user?.user_metadata?.contact_email || '')
      }} /> : emailPending ? <button onClick={checkConfirmation} disabled={busy} className={`${accountButton} mt-8`}>{busy ? 'Checking…' : 'I’ve confirmed my email'}</button> : <form method="post" onSubmit={submit} className="mt-8 space-y-5">
      <div><label htmlFor="email" className={accountLabel}>Email address</label>
        <input id="email" name="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={accountInput} /></div>
      <div><label htmlFor="password" className={accountLabel}>Create a password</label>
        <input id="password" name="password" type="password" autoComplete="new-password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className={accountInput} />
        <p className="mt-2 text-xs text-neutral-500">Use at least 8 characters.</p></div>
      <button disabled={busy} className={accountButton}>{busy ? 'Saving…' : 'Save and continue'}</button>
    </form>}
    {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
    {user && <button type="button" onClick={() => void logout()} className="mt-5 text-sm text-neutral-600">Use a different account</button>}
  </AccountForm>
}
