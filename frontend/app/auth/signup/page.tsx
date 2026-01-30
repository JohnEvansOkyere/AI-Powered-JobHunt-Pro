'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { signUp, signInWithOAuth } from '@/lib/auth'
import { toast } from 'react-hot-toast'
import { Sparkles, ArrowRight, User, Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { motion } from 'framer-motion'

export default function SignUpPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await signUp({
        email,
        password,
        metadata: {
          full_name: fullName,
        },
      })
      toast.success('Account created! Please check your email to verify your account.')
      router.push('/auth/verify-email')
    } catch (error: any) {
      toast.error(error.message || 'Failed to create account')
    } finally {
      setLoading(false)
    }
  }

  const handleOAuthSignup = async (provider: 'google' | 'github') => {
    try {
      await signInWithOAuth(provider)
    } catch (error: any) {
      toast.error(error.message || `Failed to sign up with ${provider}`)
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
          <Link href="/" className="inline-flex items-center space-x-3 group mb-8">
            <div className="w-12 h-12 bg-brand-turquoise-600 rounded-2xl flex items-center justify-center shadow-lg shadow-brand-turquoise-500/20 group-hover:scale-110 transition-transform">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <span className="text-2xl font-black tracking-tight text-neutral-900">
              JobHunt<span className="text-brand-turquoise-600">Pro</span>
            </span>
          </Link>
          <h2 className="text-3xl font-black text-neutral-900">
            Join the Elite
          </h2>
          <p className="mt-2 text-neutral-500 font-medium">
            Your career acceleration starts here
          </p>
        </div>

        <div className="bg-white p-8 rounded-[2.5rem] shadow-2xl border border-neutral-100 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-brand-turquoise-500 to-brand-orange-500"></div>
          
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label htmlFor="fullName" className="block text-xs font-black text-neutral-400 uppercase tracking-widest mb-2 ml-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                  <input
                    id="fullName"
                    name="fullName"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="block w-full pl-12 pr-4 py-4 bg-neutral-50 border border-neutral-100 rounded-2xl focus:ring-2 focus:ring-brand-turquoise-500 focus:bg-white transition-all outline-none text-neutral-900 font-medium"
                    placeholder="Jeff Bezos"
                  />
                </div>
              </div>

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
                  Create Password
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
                    minLength={6}
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
                <p className="mt-2 text-[10px] text-neutral-400 font-bold uppercase tracking-wider ml-1">Min. 6 characters for security</p>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-premium w-full flex justify-center py-4 px-4 bg-brand-turquoise-600 text-white rounded-2xl font-black text-lg shadow-xl shadow-brand-turquoise-500/20 disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Create My Free Account'}
            </button>
          </form>

          <div className="mt-8">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-neutral-100" />
              </div>
              <div className="relative flex justify-center text-xs font-bold uppercase tracking-widest">
                <span className="px-4 bg-white text-neutral-400">Fast Signup via</span>
              </div>
            </div>

            <div className="mt-8 grid grid-cols-2 gap-4">
              <button
                onClick={() => handleOAuthSignup('google')}
                className="flex items-center justify-center py-4 px-4 bg-neutral-50 border border-neutral-100 rounded-2xl font-bold text-sm text-neutral-700 hover:bg-neutral-100 transition-colors"
              >
                <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" className="w-5 h-5 mr-3" alt="Google" />
                Google
              </button>
              <button
                onClick={() => handleOAuthSignup('github')}
                className="flex items-center justify-center py-4 px-4 bg-neutral-50 border border-neutral-100 rounded-2xl font-bold text-sm text-neutral-700 hover:bg-neutral-100 transition-colors"
              >
                <svg className="h-5 w-5 mr-3" fill="currentColor" viewBox="0 0 24 24">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
                GitHub
              </button>
            </div>
          </div>
        </div>

        <p className="mt-10 text-center text-neutral-500 font-medium">
          Already a member?{' '}
          <Link
            href="/auth/login"
            className="font-black text-brand-turquoise-600 hover:text-brand-turquoise-700 underline underline-offset-4 decoration-2"
          >
            Sign In Here
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
