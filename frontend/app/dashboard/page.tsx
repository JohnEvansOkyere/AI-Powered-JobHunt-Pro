'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { useProfile } from '@/hooks/useProfile'
import { useAuth } from '@/hooks/useAuth'
import Link from 'next/link'
import { Briefcase, FileText, User, ArrowRight, Target, Star } from 'lucide-react'
import { getApplicationsStats } from '@/lib/api/applications'
import { fetchRecommendations } from '@/lib/api/recommendations'

interface Stats {
  applicationsTotal: number
  submittedCount: number
  recommendationsTotal: number
}

export default function DashboardPage() {
  const { profile, loading: profileLoading } = useProfile()
  const { user, isAuthenticated, loading: authLoading } = useAuth()
  const router = useRouter()
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    if (authLoading || !isAuthenticated) {
      return
    }

    if (!profileLoading && !profile) {
      const timer = setTimeout(() => {
        if (!profile) router.push('/profile/setup')
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [authLoading, isAuthenticated, profile, profileLoading, router])

  useEffect(() => {
    async function loadStats() {
      try {
        const [appStats, recs] = await Promise.all([
          getApplicationsStats(),
          fetchRecommendations(undefined, 1, 1),
        ])
        setStats({
          applicationsTotal: appStats.applications_total,
          submittedCount: appStats.submitted_count,
          recommendationsTotal: recs.total ?? 0,
        })
      } catch {
        setStats({ applicationsTotal: 0, submittedCount: 0, recommendationsTotal: 0 })
      }
    }

    if (!authLoading && isAuthenticated) {
      void loadStats()
    }
  }, [authLoading, isAuthenticated])

  if (authLoading || profileLoading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-neutral-200 border-t-brand-turquoise-600" />
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (!profile) return null

  const firstName = user?.email?.split('@')[0] || 'there'
  const recCount = stats?.recommendationsTotal ?? null

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Header */}
          <header className="space-y-1">
            <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight">
              Good to see you, {firstName}
            </h1>
            <p className="text-sm text-neutral-500">
              {profile.primary_job_title
                ? `Tracking roles for ${profile.primary_job_title}.`
                : 'Add your target role in your profile to get sharper matches.'}
            </p>
          </header>

          {/* Stats row */}
          <section className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <StatCard
              label="Recommendations"
              value={formatStat(stats?.recommendationsTotal)}
              icon={Target}
              href="/dashboard/recommendations"
            />
            <StatCard
              label="Applications"
              value={formatStat(stats?.applicationsTotal)}
              icon={Briefcase}
              href="/dashboard/applications"
            />
            <StatCard
              label="Submitted"
              value={formatStat(stats?.submittedCount)}
              icon={FileText}
              href="/dashboard/applications"
            />
          </section>

          {/* Primary CTA card */}
          <section className="bg-white rounded-xl border border-neutral-200 p-6 sm:p-8">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="max-w-xl">
                <div className="flex items-center gap-2 text-brand-turquoise-700 text-xs font-medium mb-2">
                  <Star className="w-3.5 h-3.5" />
                  <span>Recommendations</span>
                </div>
                <h2 className="text-lg sm:text-xl font-semibold text-neutral-900 mb-1">
                  {recCount && recCount > 0
                    ? `${recCount} role${recCount === 1 ? '' : 's'} ranked for you`
                    : 'Your first batch is on the way'}
                </h2>
                <p className="text-sm text-neutral-500 leading-relaxed">
                  We rank every role into three tiers — highly recommended, likely a fit, and
                  all roles — so you know where to spend your time.
                </p>
              </div>
              <Link
                href="/dashboard/recommendations"
                className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-turquoise-600 hover:bg-brand-turquoise-700 text-white rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
              >
                View recommendations
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </section>

          {/* Secondary actions */}
          <section className="grid sm:grid-cols-2 gap-3">
            <ActionCard
              href="/dashboard/applications"
              icon={FileText}
              title="My applications"
              description="Track saved roles, applications in flight, and past outcomes."
            />
            <ActionCard
              href="/dashboard/profile"
              icon={User}
              title="Profile"
              description="Keep your target role and skills sharp to get sharper matches."
            />
          </section>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

function formatStat(value: number | undefined | null): string {
  if (value == null) return '—'
  return String(value)
}

function StatCard({
  label,
  value,
  icon: Icon,
  href,
}: {
  label: string
  value: string
  icon: typeof Target
  href: string
}) {
  return (
    <Link
      href={href}
      className="bg-white rounded-xl border border-neutral-200 p-4 hover:border-neutral-300 transition-colors"
    >
      <div className="flex items-center gap-2 text-neutral-500 mb-2">
        <Icon className="w-3.5 h-3.5" />
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="text-2xl font-semibold text-neutral-900 tabular-nums">{value}</p>
    </Link>
  )
}

function ActionCard({
  href,
  icon: Icon,
  title,
  description,
}: {
  href: string
  icon: typeof Target
  title: string
  description: string
}) {
  return (
    <Link
      href={href}
      className="group bg-white rounded-xl border border-neutral-200 p-5 hover:border-neutral-300 transition-colors"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="w-9 h-9 rounded-lg bg-neutral-50 flex items-center justify-center">
          <Icon className="w-4 h-4 text-neutral-600" />
        </div>
        <ArrowRight className="w-4 h-4 text-neutral-300 group-hover:text-neutral-600 group-hover:translate-x-0.5 transition-all" />
      </div>
      <h3 className="text-sm font-semibold text-neutral-900 mb-1">{title}</h3>
      <p className="text-xs text-neutral-500 leading-relaxed">{description}</p>
    </Link>
  )
}
