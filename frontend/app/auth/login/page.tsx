'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { signIn } from '@/lib/auth'
import { getRememberSessionPreference } from '@/lib/supabase/client'
import { toast } from 'react-hot-toast'
import { Lock, Mail, Eye, EyeOff } from 'lucide-react'
import { motion } from 'framer-motion'

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
      await signIn({ email, password, remember: rememberMe })
      toast.success('Logged in successfully!')
      router.push('/dashboard')
    } catch (error: any) {
      toast.error(error.message || 'Failed to login')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-brand-turquoise-50/50 via-white to-white px-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md w-full"
      >
        <div className="text-center mb-10">
          <Link href="/" className="inline-flex items-center gap-2.5 group mb-8">
            <Image
              src="/logo.png"
              alt="VeloxaHire"
              width={36}
              height={36}
              priority
              className="object-contain transition-transform group-hover:scale-105"
              style={{ width: 'auto', height: 'auto' }}
            />
            <span className="text-2xl font-semibold tracking-tight text-neutral-900">
              Veloxa<span className="text-brand-turquoise-700">Hire</span>
            </span>
          </Link>
          <h2 className="text-3xl font-semibold tracking-tight text-neutral-900">
            Welcome back
          </h2>
          <p className="mt-2 text-neutral-500">
            Sign in to see your latest matches.
          </p>
        </div>

        <div className="bg-white p-8 rounded-[2.5rem] shadow-2xl border border-neutral-100 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-brand-turquoise-500 to-brand-orange-500"></div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-xs font-black text-neutral-400 uppercase tracking-widest mb-2 ml-1">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="block w-full pl-12 pr-4 py-4 bg-neutral-50 border border-neutral-100 rounded-2xl focus:ring-2 focus:ring-brand-turquoise-500 focus:bg-white transition-all outline-none text-neutral-900 font-medium"
                    placeholder="name@company.com"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-xs font-black text-neutral-400 uppercase tracking-widest mb-2 ml-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="block w-full pl-12 pr-12 py-4 bg-neutral-50 border border-neutral-100 rounded-2xl focus:ring-2 focus:ring-brand-turquoise-500 focus:bg-white transition-all outline-none text-neutral-900 font-medium"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-turquoise-500 focus:ring-offset-0"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between px-1">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 text-brand-turquoise-600 focus:ring-brand-turquoise-500 border-neutral-300 rounded cursor-pointer"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-neutral-500 font-medium cursor-pointer">
                  Stay logged in
                </label>
              </div>

              <Link
                href="/auth/forgot-password"
                className="text-sm font-bold text-brand-turquoise-600 hover:text-brand-turquoise-700"
              >
                Forgot?
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-premium w-full flex justify-center py-4 px-4 bg-brand-turquoise-600 text-white rounded-2xl font-black text-lg shadow-xl shadow-brand-turquoise-500/20 disabled:opacity-50"
            >
              {loading ? 'Authenticating...' : 'Sign In to Dashboard'}
            </button>
          </form>
        </div>

        <p className="mt-10 text-center text-neutral-500 font-medium">
          New here?{' '}
          <Link
            href="/auth/signup"
            className="font-black text-brand-turquoise-600 hover:text-brand-turquoise-700 underline underline-offset-4 decoration-2"
          >
            Create Your Pro Account
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
