'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { useProfile } from '@/hooks/useProfile'
import Link from 'next/link'
import { Briefcase, FileText, User, Sparkles, ArrowRight, TrendingUp, Zap, Target } from 'lucide-react'
import { motion } from 'framer-motion'

export default function DashboardPage() {
  const { profile, loading: profileLoading } = useProfile()
  const router = useRouter()

  useEffect(() => {
    if (!profileLoading && !profile) {
      const timer = setTimeout(() => {
        if (!profile) {
          router.push('/profile/setup')
        }
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [profile, profileLoading, router])

  if (profileLoading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-turquoise-600"></div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (!profile) return null

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-6xl mx-auto space-y-10">
          {/* Welcome Section */}
          <div className="relative overflow-hidden rounded-[2.5rem] bg-neutral-900 p-8 md:p-12 shadow-2xl">
            <div className="absolute top-0 right-0 w-1/3 h-full bg-gradient-to-l from-brand-turquoise-500/20 to-transparent"></div>
            <div className="relative z-10 flex flex-col md:flex-row justify-between items-center gap-8">
              <div className="text-center md:text-left">
                <h2 className="text-3xl md:text-4xl font-black text-white mb-4">
                  Welcome back, <span className="text-brand-turquoise-400">{profile.primary_job_title || 'Expert'}</span>!
                </h2>
                <p className="text-neutral-400 text-lg max-w-md">
                  We've found <span className="text-white font-bold">12 new matches</span> that perfectly fit your profile since yesterday.
                </p>
              </div>
              <Link 
                href="/dashboard/jobs" 
                className="btn-premium px-8 py-4 bg-brand-turquoise-500 text-white rounded-2xl font-black flex items-center space-x-3 shadow-xl"
              >
                <span>View My Matches</span>
                <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>

          {/* Stats / Insights Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              { label: 'Market Match', val: '98%', icon: Target, color: 'brand-turquoise' },
              { label: 'CV Strength', val: 'High', icon: Zap, color: 'brand-orange' },
              { label: 'Applied', val: '24', icon: Briefcase, color: 'brand-turquoise' },
              { label: 'Interviews', val: '3', icon: TrendingUp, color: 'brand-orange' },
            ].map((stat, i) => (
              <div key={i} className="bg-white rounded-3xl p-6 border border-neutral-100 shadow-sm hover:shadow-md transition-shadow">
                <div className={`w-10 h-10 bg-${stat.color}-50 rounded-xl flex items-center justify-center mb-4`}>
                  <stat.icon className={`h-5 w-5 text-${stat.color}-600`} />
                </div>
                <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-1">{stat.label}</p>
                <p className="text-2xl font-black text-neutral-900">{stat.val}</p>
              </div>
            ))}
          </div>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Quick Actions */}
            <div className="lg:col-span-2 grid md:grid-cols-2 gap-6">
              <Link
                href="/dashboard/jobs"
                className="group bg-white rounded-[2rem] p-8 border border-neutral-100 hover:border-brand-turquoise-200 hover:shadow-2xl transition-all duration-300"
              >
                <div className="flex items-start justify-between mb-8">
                  <div className="w-14 h-14 bg-brand-turquoise-50 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Briefcase className="h-7 w-7 text-brand-turquoise-600" />
                  </div>
                  <ArrowRight className="h-6 w-6 text-neutral-200 group-hover:text-brand-turquoise-600 transform group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="text-xl font-bold text-neutral-900 mb-2">Job Recommendations</h3>
                <p className="text-neutral-500 leading-relaxed">Discover AI-matched roles that align with your 42 unique career markers.</p>
              </Link>

              <Link
                href="/dashboard/applications"
                className="group bg-white rounded-[2rem] p-8 border border-neutral-100 hover:border-brand-orange-200 hover:shadow-2xl transition-all duration-300"
              >
                <div className="flex items-start justify-between mb-8">
                  <div className="w-14 h-14 bg-brand-orange-50 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                    <FileText className="h-7 w-7 text-brand-orange-600" />
                  </div>
                  <ArrowRight className="h-6 w-6 text-neutral-200 group-hover:text-brand-orange-600 transform group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="text-xl font-bold text-neutral-900 mb-2">My Applications</h3>
                <p className="text-neutral-500 leading-relaxed">Track your journey through the pipeline and manage interview schedules.</p>
              </Link>

              <Link
                href="/profile/setup"
                className="group bg-white rounded-[2rem] p-8 border border-neutral-100 hover:border-brand-turquoise-200 hover:shadow-2xl transition-all duration-300"
              >
                <div className="flex items-start justify-between mb-8">
                  <div className="w-14 h-14 bg-brand-turquoise-50 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                    <User className="h-7 w-7 text-brand-turquoise-600" />
                  </div>
                  <ArrowRight className="h-6 w-6 text-neutral-200 group-hover:text-brand-turquoise-600 transform group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="text-xl font-bold text-neutral-900 mb-2">Optimized Profile</h3>
                <p className="text-neutral-500 leading-relaxed">Keep your professional identity sharp and up-to-date for maximum match accuracy.</p>
              </Link>

              <div className="bg-neutral-50 rounded-[2rem] p-8 border border-neutral-100 border-dashed flex flex-col items-center justify-center text-center">
                <div className="w-14 h-14 bg-white rounded-2xl flex items-center justify-center shadow-sm mb-6">
                  <Sparkles className="h-7 w-7 text-neutral-300" />
                </div>
                <h3 className="text-xl font-bold text-neutral-300 mb-1">Upload CV</h3>
                <p className="text-neutral-400 text-sm italic">Feature coming soon</p>
              </div>
            </div>

            {/* Side Panel / Career Insights */}
            <div className="bg-white rounded-[2rem] p-8 border border-neutral-100 shadow-sm">
              <h3 className="text-xl font-bold text-neutral-900 mb-8 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-brand-turquoise-600" />
                Career Insights
              </h3>
              
              <div className="space-y-8">
                <div className="p-5 bg-brand-turquoise-50 rounded-2xl border border-brand-turquoise-100">
                  <p className="text-xs font-bold text-brand-turquoise-700 uppercase mb-3">Trending Skill</p>
                  <p className="text-lg font-bold text-neutral-900 mb-1">React Server Components</p>
                  <p className="text-sm text-neutral-500">Found in 45% of matches this week.</p>
                </div>

                <div className="space-y-4">
                  <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest">Active Search Status</p>
                  <div className="flex items-center justify-between">
                    <span className="text-neutral-600 font-medium">Daily Scrapes</span>
                    <span className="text-brand-turquoise-600 font-bold">Active</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-neutral-600 font-medium">CV Auto-Tailor</span>
                    <span className="text-brand-turquoise-600 font-bold">Ready</span>
                  </div>
                </div>

                <div className="pt-6 border-t border-neutral-100">
                  <div className="p-5 bg-brand-orange-50 rounded-2xl border border-brand-orange-100">
                    <p className="text-xs font-bold text-brand-orange-700 uppercase mb-2 italic">Pro Tip</p>
                    <p className="text-sm text-neutral-700 leading-relaxed">
                      "Users with complete profiles are 3x more likely to receive interview invites."
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
