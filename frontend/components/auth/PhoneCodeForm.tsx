'use client'

import { useEffect, useState } from 'react'
import { accountButton, accountInput, accountLabel } from './AccountForm'

function verificationError(error: unknown, fallback: string) {
  if (!(error instanceof Error) || !error.message || error.message === '{}') return fallback
  if ('status' in error && typeof error.status === 'number' && error.status >= 500) return fallback
  return error.message
}

export function PhoneCodeForm({ initialPhone = '', onRequest, onVerify }: {
  initialPhone?: string
  onRequest: (phone: string) => Promise<string>
  onVerify: (phone: string, code: string) => Promise<void>
}) {
  const [phone, setPhone] = useState(initialPhone)
  const [sentTo, setSentTo] = useState('')
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [cooldown, setCooldown] = useState(0)
  useEffect(() => {
    if (!cooldown) return
    const timer = setTimeout(() => setCooldown((value) => Math.max(0, value - 1)), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  const send = async () => {
    if (busy || cooldown) return
    setBusy(true); setError('')
    // Also throttle ambiguous provider failures: a message may already be queued.
    setCooldown(60)
    try { setSentTo(await onRequest(phone)); setCode('') }
    catch (err) { setError(verificationError(err, 'Could not send the code. Please try again.')) }
    finally { setBusy(false) }
  }
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!sentTo) { await send(); return }
    if (busy) return
    setBusy(true); setError('')
    try { await onVerify(sentTo, code) }
    catch (err) { setError(verificationError(err, 'Could not verify the code. Please try again.')) }
    finally { setBusy(false) }
  }

  return <form method="post" onSubmit={submit} className="mt-8 space-y-5">
    {sentTo ? <>
      <p className="text-sm text-neutral-600" role="status">Enter the code sent to {sentTo}.</p>
      <div><label htmlFor="code" className={accountLabel}>Six-digit code</label>
        <input id="code" name="code" required autoComplete="one-time-code" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} className={accountInput} /></div>
    </> : <div><label htmlFor="phone" className={accountLabel}>Telephone number</label>
      <input id="phone" name="phone" type="tel" required autoComplete="tel" placeholder="024 123 4567" value={phone} onChange={(e) => setPhone(e.target.value)} className={accountInput} /></div>}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <button disabled={busy || (sentTo ? code.length !== 6 : !phone.trim() || cooldown > 0)} className={accountButton}>
      {busy ? 'Please wait…' : sentTo ? 'Verify and continue' : cooldown ? `Try again in ${cooldown}s` : 'Send verification code'}
    </button>
    {sentTo && <div className="flex flex-wrap justify-between gap-3 text-sm">
      <button type="button" disabled={busy || cooldown > 0} onClick={send} className="text-brand-turquoise-700 disabled:text-neutral-400">{cooldown ? `Resend in ${cooldown}s` : 'Resend code'}</button>
      <button type="button" disabled={busy} onClick={() => { setSentTo(''); setCode(''); setError('') }} className="text-neutral-600">Change phone number</button>
    </div>}
  </form>
}
