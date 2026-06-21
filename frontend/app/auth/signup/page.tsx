'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { signUp } from '@/lib/auth'
import { apiClient } from '@/lib/api/client'
import { toast } from 'react-hot-toast'
import { User, Mail, Lock, Eye, EyeOff, ArrowRight, CheckCircle2 } from 'lucide-react'
import { motion } from 'framer-motion'
import AuthBrandPanel from '@/components/auth/AuthBrandPanel'
import PasswordStrength, { isPasswordStrong } from '@/components/auth/PasswordStrength'

interface HandoffVerifyResponse {
  valid: boolean
  email?: string | null
  full_name?: string | null
  phone?: string | null
  job_id?: string | null
}

const handoffVerifyCache = new Map<string, Promise<HandoffVerifyResponse>>()

function verifyHandoffToken(token: string) {
  const cached = handoffVerifyCache.get(token)
  if (cached) return cached

  const request = apiClient.post<HandoffVerifyResponse>('/auth/handoff/verify', { token })
  handoffVerifyCache.set(token, request)
  return request
}

const inputCls =
  'block w-full rounded-xl border border-neutral-200 bg-white py-3.5 pl-11 pr-4 text-sm font-medium text-neutral-900 outline-none transition-all placeholder:text-neutral-400 focus:border-brand-turquoise-500 focus:ring-2 focus:ring-brand-turquoise-500/20'

function SignUpContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState<string | null>(null)
  const [handoffJobId, setHandoffJobId] = useState<string | null>(null)
  const [handoffPrefilled, setHandoffPrefilled] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const token = searchParams.get('h')
    if (!token) return

    let cancelled = false
    verifyHandoffToken(token)
      .then((result) => {
        if (cancelled || !result.valid) return
        if (result.email) setEmail(result.email)
        if (result.full_name) setFullName(result.full_name)
        if (result.phone) setPhone(result.phone)
        if (result.job_id) setHandoffJobId(result.job_id)
        setHandoffPrefilled(Boolean(result.email || result.full_name))
      })
      .catch(() => {
        // Expired or invalid handoffs fall back to normal signup.
      })

    return () => {
      cancelled = true
    }
  }, [searchParams])

  const passwordsMatch = password === confirmPassword
  const canSubmit = isPasswordStrong(password) && passwordsMatch

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isPasswordStrong(password)) {
      toast.error('Please choose a stronger password.')
      return
    }
    if (!passwordsMatch) {
      toast.error('Passwords do not match.')
      return
    }
    setLoading(true)

    try {
      await signUp({
        email,
        password,
        metadata: {
          full_name: fullName,
          phone: phone || undefined,
          source: handoffPrefilled ? 'veloxarecruit_apply_handoff' : undefined,
          ats_job_id: handoffJobId || undefined,
        },
      })
      toast.success('Account created! You can sign in now.')
      router.push('/auth/login')
    } catch (error: any) {
      toast.error(error.message || 'Failed to create account')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-cream-50">
      <AuthBrandPanel variant="signup" />

      {/* Form panel */}
      <div className="relative flex w-full flex-col justify-center px-6 py-12 sm:px-10 lg:w-1/2 xl:px-20">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mx-auto w-full max-w-[440px]"
        >
          {/* Mobile logo */}
          <Link href="/" className="mb-10 inline-flex items-center gap-2.5 lg:hidden">
            <Image src="/logo.png" alt="VeloxaHire" width={32} height={32} priority className="object-contain" style={{ width: 'auto', height: 'auto' }} />
            <span className="text-xl font-semibold tracking-tight text-neutral-900">
              Veloxa<span className="text-brand-turquoise-700">Hire</span>
            </span>
          </Link>

          <h1 className="text-3xl font-bold tracking-tight text-neutral-900">
            {handoffPrefilled ? 'Finish your application' : 'Create your free account'}
          </h1>
          <p className="mt-2 text-neutral-500">
            {handoffPrefilled
              ? 'Your application details are ready — just set a password to continue.'
              : 'Browse free, then get a shortlist built around your CV.'}
          </p>

          {handoffPrefilled && (
            <div className="mt-5 flex items-center gap-2 rounded-xl border border-emerald-100 bg-emerald-50 px-3.5 py-2.5 text-sm font-medium text-emerald-700">
              <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
              Application details imported from VeloxaRecruit
            </div>
          )}

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="fullName" className="mb-1.5 block text-sm font-medium text-neutral-700">
                Full name
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className={inputCls}
                  placeholder="Ama Mensah"
                />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-neutral-700">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  readOnly={handoffPrefilled}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={`${inputCls} read-only:bg-neutral-50 read-only:text-neutral-500`}
                  placeholder="you@email.com"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-neutral-700">
                Create password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`${inputCls} pr-11`}
                  placeholder="••••••••"
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-2 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <PasswordStrength password={password} />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="mb-1.5 block text-sm font-medium text-neutral-700">
                Confirm password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={`${inputCls} pr-4`}
                  placeholder="••••••••"
                />
              </div>
              {confirmPassword && !passwordsMatch && (
                <p className="mt-1.5 text-xs font-medium text-red-500">Passwords do not match.</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !canSubmit}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-turquoise-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-turquoise-500/20 transition-all hover:bg-brand-turquoise-700 disabled:opacity-60"
            >
              {loading ? 'Creating account…' : 'Create my free account'}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>

          <div className="mt-8 flex items-center justify-between border-t border-neutral-200 pt-6 text-sm text-neutral-500">
            <span>
              Already a member?{' '}
              <Link href="/auth/login" className="font-semibold text-brand-turquoise-700 hover:text-brand-turquoise-800">
                Sign in
              </Link>
            </span>
            <Link href="/jobs" className="transition-colors hover:text-neutral-800">
              Browse jobs →
            </Link>
          </div>

          <p className="mt-4 text-xs text-neutral-400">
            By creating an account you agree to our{' '}
            <Link href="/terms" className="underline hover:text-neutral-600">Terms</Link> and{' '}
            <Link href="/privacy" className="underline hover:text-neutral-600">Privacy Policy</Link>.
          </p>
        </motion.div>
      </div>
    </div>
  )
}

export default function SignUpPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-cream-50" />}>
      <SignUpContent />
    </Suspense>
  )
}
