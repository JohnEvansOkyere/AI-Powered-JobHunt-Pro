'use client'

import { getUserErrorMessage } from '@/lib/errors'
import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { AccountForm, accountButton, accountInput, accountLabel } from '@/components/auth/AccountForm'
import { PasswordResetError, completePasswordReset, requestPasswordReset, verifyPasswordReset } from '@/lib/api/password-reset'

export default function ResetPasswordPage() {
  const [step, setStep] = useState<'details' | 'code' | 'password' | 'done'>('details')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [challenge, setChallenge] = useState('')
  const [grant, setGrant] = useState('')
  const [expiresAt, setExpiresAt] = useState(0)
  const [retryAt, setRetryAt] = useState(0)
  const [verifyRetryAt, setVerifyRetryAt] = useState(0)
  const [now, setNow] = useState(Date.now())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submitting = useRef(false)
  const heading = useRef<HTMLHeadingElement>(null)
  const cooldown = Math.max(0, Math.ceil((retryAt - now) / 1000))
  const verifyCooldown = Math.max(0, Math.ceil((verifyRetryAt - now) / 1000))
  const expired = expiresAt > 0 && now >= expiresAt
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer) }, [])
  useEffect(() => { heading.current?.focus() }, [step])
  useEffect(() => { if (expired) { setGrant(''); setCode(''); setPassword(''); setConfirm('') } }, [expired])

  const sendCode = async () => {
    if (submitting.current || cooldown) return
    submitting.current = true; setBusy(true); setError('')
    try {
      const result = await requestPasswordReset(phone)
      setChallenge(result.challenge_id); setCode(''); setGrant('')
      setExpiresAt(Date.now() + result.expires_in * 1000)
      setRetryAt(Date.now() + result.resend_after * 1000)
      setStep('code')
    } catch (err) {
      setError(getUserErrorMessage(err, 'Could not request a code.'))
      if (err instanceof PasswordResetError && err.status === 429) setRetryAt(Date.now() + err.retryAfter * 1000)
    } finally { setBusy(false); submitting.current = false }
  }
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (step === 'details') { await sendCode(); return }
    if (submitting.current || expired || verifyCooldown) return
    if (step === 'password' && password !== confirm) { setError('The passwords do not match.'); return }
    submitting.current = true; setBusy(true); setError('')
    try {
      if (step === 'code') {
        const result = await verifyPasswordReset(challenge, code)
        setCode(''); setChallenge(''); setGrant(result.reset_token)
        setExpiresAt(Date.now() + result.expires_in * 1000)
        setStep('password')
      } else {
        await completePasswordReset(grant, password)
        setGrant(''); setPassword(''); setConfirm(''); setExpiresAt(0)
        setStep('done')
      }
    } catch (err) {
      setError(getUserErrorMessage(err, 'Could not complete this step.'))
      if (err instanceof PasswordResetError && err.status === 429) setVerifyRetryAt(Date.now() + err.retryAfter * 1000)
      // An ambiguous completion may have consumed the grant. Never replay it.
      if (step === 'password') { setGrant(''); setPassword(''); setConfirm(''); setExpiresAt(1) }
    } finally { setBusy(false); submitting.current = false }
  }
  const restart = () => {
    setStep('details'); setCode(''); setGrant(''); setChallenge(''); setPassword(''); setConfirm(''); setExpiresAt(0); setError('')
  }

  return <AccountForm title="Reset your password" description="Recover your account with a code sent to your verified phone.">
    <h2 ref={heading} tabIndex={-1} className="mt-7 text-lg font-semibold outline-none">{step === 'details' ? 'Enter your phone number' : step === 'code' ? 'Check your SMS' : step === 'password' ? 'Choose a new password' : 'Password reset complete'}</h2>
    {step === 'done' ? <div className="mt-4 space-y-5"><p>Your password has been changed. Sign in with your email and new password.</p><Link href="/auth/login" className={accountButton}>Back to sign in</Link></div> : <form method="post" onSubmit={submit} className="mt-5 space-y-5">
      {step === 'details' && <>
        <div><label htmlFor="phone" className={accountLabel}>Registered phone number</label><input id="phone" name="phone" type="tel" autoComplete="tel" placeholder="024 123 4567" required maxLength={32} value={phone} onChange={(e) => setPhone(e.target.value)} className={accountInput} aria-describedby="phone-help" /><p id="phone-help" className="mt-2 text-xs text-neutral-500">Use the number you verified on this account. If you no longer have it, contact support.</p></div>
      </>}
      {step === 'code' && <>
        <p className="text-sm text-neutral-600">If this number belongs to an account with a verified phone, a reset code will arrive by SMS. The code expires after 5 minutes.</p>
        <div><label htmlFor="code" className={accountLabel}>Six-digit reset code</label><input id="code" name="code" inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} disabled={expired} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} className={accountInput} /></div>
      </>}
      {step === 'password' && !expired && <>
        <p className="text-sm text-neutral-600">Use at least 12 characters. A longer, unique passphrase works well.</p>
        <div><label htmlFor="password" className={accountLabel}>New password</label><input id="password" name="password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} className={accountInput} /></div>
        <div><label htmlFor="confirm" className={accountLabel}>Confirm new password</label><input id="confirm" name="confirm" type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} className={accountInput} /></div>
      </>}
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      {expired && <p role="alert" className="text-sm text-neutral-700">Request a new code to continue this reset.</p>}
      {!expired && <button className={accountButton} disabled={busy || (step === 'details' && cooldown > 0) || (step !== 'details' && verifyCooldown > 0) || (step === 'code' && code.length !== 6)}>{busy ? 'Please wait…' : step === 'details' ? cooldown ? `Try again in ${cooldown}s` : 'Send reset code' : verifyCooldown ? `Try again in ${verifyCooldown}s` : step === 'code' ? 'Verify reset code' : 'Reset password'}</button>}
      {step === 'code' && <button type="button" disabled={busy || cooldown > 0} onClick={sendCode} className="text-sm text-brand-turquoise-700 disabled:text-neutral-400">{cooldown ? `Resend in ${cooldown}s` : 'Resend code'}</button>}
      {step !== 'details' && <button type="button" disabled={busy} onClick={restart} className="block text-sm text-neutral-600">Start again</button>}
    </form>}
  </AccountForm>
}
