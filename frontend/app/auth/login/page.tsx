'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { signIn } from '@/lib/auth'
import { getRememberSessionPreference } from '@/lib/supabase/client'
import { toast } from 'react-hot-toast'
import { Lock, Mail, Eye, EyeOff, ArrowRight } from 'lucide-react'
import { motion } from 'framer-motion'
import AuthBrandPanel from '@/components/auth/AuthBrandPanel'
import { trackEvent } from '@/lib/analytics'

const inputCls =
  'block w-full rounded-xl border border-neutral-200 bg-white py-3.5 pl-11 pr-4 text-sm font-medium text-neutral-900 outline-none transition-all placeholder:text-neutral-400 focus:border-brand-turquoise-500 focus:ring-2 focus:ring-brand-turquoise-500/20'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setRememberMe(getRememberSessionPreference())
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      void trackEvent({ event_name: 'login_started', path: '/auth/login' })
      await signIn({ email, password, remember: rememberMe })
      void trackEvent({ event_name: 'login_completed', path: '/auth/login' })
      toast.success('Logged in successfully!')
      router.push('/dashboard')
    } catch (error: any) {
      toast.error(error.message || 'Failed to login')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-cream-50">
      <AuthBrandPanel variant="login" />

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
            <Image src="/logo.png" alt="VeloxaHire" width={32} height={32} priority className="object-contain" />
            <span className="text-xl font-semibold tracking-tight text-neutral-900">
              Veloxa<span className="text-brand-turquoise-700">Hire</span>
            </span>
          </Link>

          <h1 className="text-3xl font-bold tracking-tight text-neutral-900">Welcome back</h1>
          <p className="mt-2 text-neutral-500">Sign in to see your latest matches and saved roles.</p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
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
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputCls}
                  placeholder="you@email.com"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-neutral-700">
                Password
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
            </div>

            <div className="flex items-center justify-between">
              <label className="flex cursor-pointer items-center gap-2 text-sm text-neutral-600">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 cursor-pointer rounded border-neutral-300 text-brand-turquoise-600 focus:ring-brand-turquoise-500"
                />
                Stay logged in
              </label>
              <Link href="/auth/forgot-password" className="text-sm font-semibold text-brand-turquoise-700 hover:text-brand-turquoise-800">
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-turquoise-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-turquoise-500/20 transition-all hover:bg-brand-turquoise-700 disabled:opacity-60"
            >
              {loading ? 'Signing in…' : 'Sign in'}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>

          <div className="mt-8 flex items-center justify-between border-t border-neutral-200 pt-6 text-sm text-neutral-500">
            <span>
              New here?{' '}
              <Link href="/auth/signup" className="font-semibold text-brand-turquoise-700 hover:text-brand-turquoise-800">
                Create a free account
              </Link>
            </span>
            <Link href="/jobs" className="transition-colors hover:text-neutral-800">
              Browse jobs →
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
