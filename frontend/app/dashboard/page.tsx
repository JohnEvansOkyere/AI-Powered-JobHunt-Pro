'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { useProfile } from '@/hooks/useProfile'
import { useAuth } from '@/hooks/useAuth'
import Link from 'next/link'
import { Briefcase, FileText, User, Sparkles, ArrowRight, TrendingUp, Zap, Target, Plus, ExternalLink, CheckCircle2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { AddExternalJobModal } from '@/components/modals/AddExternalJobModal'

export default function DashboardPage() {
  const { profile, loading: profileLoading } = useProfile()
  const { user } = useAuth()
  const router = useRouter()
  const [isModalOpen, setIsModalOpen] = useState(false)

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
                <h2 className="text-3xl md:text-5xl font-black text-white mb-4 leading-tight">
                  Welcome back, <span className="text-brand-turquoise-400">{user?.email?.split('@')[0] || 'Explorer'}</span>!
                  <br />
                  <span className="text-2xl md:text-3xl text-neutral-400 font-bold">
                    {profile.primary_job_title || 'Expert Professional'}
                  </span>
                </h2>
                <p className="text-neutral-500 text-lg max-w-md font-medium">
                  We've found <span className="text-white font-bold">12 new matches</span> that perfectly fit your profile since yesterday.
                </p>
              </div>
              <Link 
                href="/dashboard/jobs" 
                className="btn-premium px-8 py-4 bg-brand-turquoise-500 text-white rounded-2xl font-black flex items-center space-x-3 group"
              >
                <span>View My Matches</span>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>

          {/* Power Actions Section - MORE PROMINENT */}
          <div className="grid grid-cols-1 gap-8">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="group relative overflow-hidden rounded-[3rem] bg-gradient-to-br from-brand-orange-500 via-brand-orange-600 to-orange-700 p-1 md:p-1.5 shadow-2xl shadow-brand-orange-500/30"
            >
              <div className="relative bg-neutral-900 rounded-[2.9rem] p-8 md:p-12 overflow-hidden">
                {/* Background Decor */}
                <div className="absolute top-0 right-0 w-1/2 h-full bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-5 scale-150 rotate-12"></div>
                <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-brand-orange-500/10 rounded-full blur-3xl"></div>
                
                <div className="relative z-10 flex flex-col lg:flex-row items-center justify-between gap-12">
                  <div className="max-w-2xl text-center lg:text-left">
                    <div className="inline-flex items-center space-x-2 bg-brand-orange-500/10 border border-brand-orange-500/20 rounded-full px-4 py-1.5 mb-6">
                      <Sparkles className="w-4 h-4 text-brand-orange-400" />
                      <span className="text-xs font-black text-brand-orange-400 uppercase tracking-widest">Power Feature</span>
                    </div>
                    <h2 className="text-3xl md:text-5xl font-black text-white mb-6 leading-tight">
                      Found a job elsewhere?<br />
                      <span className="text-brand-orange-400">Tailor your application in seconds.</span>
                    </h2>
                    <p className="text-neutral-400 text-lg md:text-xl leading-relaxed mb-8 font-medium">
                      Paste any job URL or description from LinkedIn, Indeed, or company websites. 
                      Our AI extracts the data and helps you generate a <span className="text-white font-bold underline decoration-brand-orange-500 underline-offset-4">winning CV & Cover Letter</span> instantly.
                    </p>
                    <div className="flex flex-wrap items-center justify-center lg:justify-start gap-4">
                      <button
                        onClick={() => setIsModalOpen(true)}
                        className="btn-premium px-10 py-5 bg-brand-orange-500 text-white rounded-2xl font-black text-lg flex items-center space-x-3 group hover:shadow-2xl hover:shadow-brand-orange-500/40 transition-all active:scale-95"
                      >
                        <Plus className="w-6 h-6 group-hover:rotate-90 transition-transform duration-300" />
                        <span>Add External Job Now</span>
                      </button>
                      <div className="text-neutral-500 text-sm font-bold flex items-center gap-2 px-4">
                        <CheckCircle2 className="w-4 h-4 text-brand-orange-500" />
                        No manual entry required
                      </div>
                    </div>
                  </div>

                  <div className="relative lg:w-1/3 flex items-center justify-center">
                    {/* Visual representation of the feature */}
                    <div className="relative w-48 h-48 md:w-64 md:h-64">
                      <div className="absolute inset-0 bg-brand-orange-500/20 rounded-full animate-ping"></div>
                      <div className="relative w-full h-full bg-neutral-800 rounded-full border-4 border-brand-orange-500/30 flex items-center justify-center shadow-inner">
                        <Plus className="w-24 h-24 text-brand-orange-500 drop-shadow-2xl" />
                      </div>
                      {/* Floating icons */}
                      <motion.div 
                        animate={{ y: [0, -10, 0] }} 
                        transition={{ duration: 3, repeat: Infinity }}
                        className="absolute -top-4 -right-4 p-4 bg-white rounded-2xl shadow-xl border border-neutral-100"
                      >
                        <Briefcase className="w-8 h-8 text-brand-turquoise-500" />
                      </motion.div>
                      <motion.div 
                        animate={{ y: [0, 10, 0] }} 
                        transition={{ duration: 4, repeat: Infinity }}
                        className="absolute -bottom-4 -left-4 p-4 bg-white rounded-2xl shadow-xl border border-neutral-100"
                      >
                        <FileText className="w-8 h-8 text-brand-orange-500" />
                      </motion.div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
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

        {/* Add External Job Modal */}
        <AddExternalJobModal 
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSuccess={() => {
            // Don't redirect - let user choose what to do next in the modal
          }}
        />
      </DashboardLayout>
    </ProtectedRoute>
  )
}
