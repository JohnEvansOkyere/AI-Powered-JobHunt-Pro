'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { accountDestination, confirmPhoneVerification, requestPhoneVerification } from '@/lib/auth'
import { AccountForm } from '@/components/auth/AccountForm'
import { PhoneCodeForm } from '@/components/auth/PhoneCodeForm'
import { trackEvent } from '@/lib/analytics'
import { toast } from 'react-hot-toast'

export default function VerifyPhonePage() {
  const { user, loading, logout } = useAuth()
  const router = useRouter()
  useEffect(() => {
    if (loading) return
    if (!user) router.replace('/auth/login')
    else if (accountDestination(user) !== '/auth/verify-phone') router.replace(accountDestination(user))
  }, [user, loading, router])

  return <AccountForm title="Verify your account" description="Enter your phone number. You only need to verify it once; future sign-ins use your email and password.">
    {loading ? <p className="mt-8" role="status">Loading your account…</p> : user && accountDestination(user) === '/auth/verify-phone' ? <>
      <PhoneCodeForm initialPhone={user.phone || user.user_metadata?.handoff_phone || ''} onRequest={requestPhoneVerification} onVerify={async (phone, code) => {
        await confirmPhoneVerification(phone, code)
        void trackEvent({ event_name: 'signup_completed', path: '/auth/verify-phone', metadata: { method: 'email_password' } })
        toast.success('Phone verified. You’re signed in.')
        router.replace('/dashboard')
      }} />
      <button type="button" onClick={() => void logout()} className="mt-5 text-sm text-neutral-600">Use a different account</button>
    </> : null}
  </AccountForm>
}
