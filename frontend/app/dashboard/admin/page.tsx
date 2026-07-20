'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Activity,
  ArrowLeft,
  BarChart3,
  Clock3,
  Eye,
  LogOut,
  MousePointerClick,
  RefreshCw,
  ShieldCheck,
  UserPlus,
  Users,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { getAdminIdentity, getAdminOverview, type AdminOverview } from '@/lib/api/admin'
import { signOut } from '@/lib/auth'

function formatDuration(seconds: number) {
  if (seconds < 60) return `${Math.round(seconds)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

function formatWhen(value: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
}

function metricLabel(key: string) {
  return key.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function MetricCard({ icon: Icon, label, value, detail }: { icon: typeof Users; label: string; value: string | number; detail?: string }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-neutral-500">{label}</p>
        <span className="rounded-xl bg-brand-turquoise-50 p-2 text-brand-turquoise-700"><Icon className="h-4 w-4" /></span>
      </div>
      <p className="mt-4 text-3xl font-bold tracking-tight text-neutral-900">{value}</p>
      {detail && <p className="mt-1 text-xs text-neutral-500">{detail}</p>}
    </div>
  )
}

function ListBlock({ title, rows, empty }: { title: string; rows: Array<{ label: string; count: number }>; empty: string }) {
  const max = Math.max(...rows.map((row) => row.count), 1)
  return (
    <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <h2 className="font-semibold text-neutral-900">{title}</h2>
      {rows.length === 0 ? <p className="mt-5 text-sm text-neutral-500">{empty}</p> : (
        <div className="mt-4 space-y-4">
          {rows.map((row) => (
            <div key={`${row.label}-${row.count}`}>
              <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                <span className="min-w-0 truncate text-neutral-600" title={row.label}>{row.label}</span>
                <span className="font-semibold text-neutral-900">{row.count}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-neutral-100"><div className="h-full rounded-full bg-brand-turquoise-500" style={{ width: `${Math.max(4, (row.count / max) * 100)}%` }} /></div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function AcquisitionTable({ rows }: { rows: AdminOverview['acquisition_sources'] }) {
  return (
    <section className="mt-6 rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end"><div><h2 className="font-semibold text-neutral-900">Acquisition sources</h2><p className="mt-1 text-xs text-neutral-500">UTM campaigns where available; referrer inference for organic and referral traffic.</p></div><span className="text-xs text-neutral-400">Source → job intent → signup</span></div>
      <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="border-b border-neutral-200 text-xs uppercase tracking-wide text-neutral-400"><tr><th className="pb-3 pr-4">Source</th><th className="pb-3 pr-4">Medium</th><th className="pb-3 pr-4">Campaign</th><th className="pb-3 pr-4">Visitors</th><th className="pb-3 pr-4">Sessions</th><th className="pb-3 pr-4">Job views</th><th className="pb-3 pr-4">Apply clicks</th><th className="pb-3">Signups</th></tr></thead><tbody className="divide-y divide-neutral-100">{rows.map((row) => <tr key={`${row.source}-${row.medium}-${row.campaign || 'none'}`}><td className="py-3 pr-4 font-semibold text-neutral-900">{row.source}</td><td className="py-3 pr-4 text-neutral-600">{row.medium}</td><td className="max-w-48 truncate py-3 pr-4 text-neutral-500">{row.campaign || '—'}</td><td className="py-3 pr-4 text-neutral-600">{row.visitors}</td><td className="py-3 pr-4 text-neutral-600">{row.sessions}</td><td className="py-3 pr-4 text-neutral-600">{row.job_views}</td><td className="py-3 pr-4 text-neutral-600">{row.apply_clicks}</td><td className="py-3 font-bold text-brand-turquoise-700">{row.signups}</td></tr>)}</tbody></table>{rows.length === 0 && <p className="py-5 text-sm text-neutral-500">No acquisition data yet. Tagged links will appear here after visitors arrive.</p>}</div>
    </section>
  )
}

export default function AdminDashboardPage() {
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [days, setDays] = useState(30)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      await getAdminIdentity()
      setOverview(await getAdminOverview(days))
    } catch (requestError: any) {
      if (requestError?.status === 401 || requestError?.status === 403) {
        router.replace('/dashboard')
        return
      }
      setError(requestError?.message || 'Could not load admin analytics.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!authLoading && !user) router.replace('/auth/login')
  }, [authLoading, router, user])

  useEffect(() => {
    if (!authLoading && user) void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user, days])

  const anonymousJobVisitors = useMemo(
    () => overview?.recent_sessions.filter((session) => !session.signed_in && !session.converted && (session.landing_path?.startsWith('/jobs') || session.last_path?.startsWith('/jobs'))) || [],
    [overview],
  )

  if (authLoading || !user) return <div className="min-h-screen bg-neutral-950" />

  const metrics = overview?.metrics || {}
  const maxDaily = Math.max(...(overview?.daily.map((row) => row.sessions) || [1]), 1)

  return (
    <div className="min-h-screen bg-[#f6f8f7] text-neutral-900">
      <header className="border-b border-white/10 bg-neutral-950 text-white">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3"><div className="rounded-xl bg-brand-turquoise-500/15 p-2 text-brand-turquoise-300"><ShieldCheck className="h-5 w-5" /></div><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-turquoise-300">VeloxaHire Admin</p><h1 className="mt-1 text-xl font-semibold">Product command center</h1></div></div>
          <div className="flex items-center gap-2 text-sm text-white/60"><span className="hidden sm:inline">{user.email}</span><button onClick={() => signOut().then(() => router.replace('/auth/login'))} className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-3 py-2 text-white hover:bg-white/10"><LogOut className="h-4 w-4" /> Sign out</button></div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-4 py-7 sm:px-6 lg:px-8">
        <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><div className="mb-3 flex flex-wrap items-center gap-3"><button onClick={() => router.push('/dashboard')} className="inline-flex items-center gap-1.5 text-sm font-medium text-neutral-500 hover:text-neutral-900"><ArrowLeft className="h-4 w-4" /> Candidate dashboard</button><button onClick={() => router.push('/dashboard/admin/users')} className="inline-flex items-center gap-1.5 rounded-lg bg-white px-2.5 py-1.5 text-sm font-semibold text-neutral-700 shadow-sm ring-1 ring-neutral-200 hover:bg-neutral-50"><Users className="h-4 w-4" /> User control</button></div><p className="text-sm text-neutral-500">Anonymous traffic, signed-in activity, conversion, and operational health in one view.</p></div><div className="flex items-center gap-2"><select value={days} onChange={(event) => setDays(Number(event.target.value))} className="rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium"><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option></select><button onClick={() => void load()} className="inline-flex items-center gap-2 rounded-xl bg-neutral-900 px-3 py-2 text-sm font-semibold text-white hover:bg-neutral-800"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh</button></div></div>

        {error && <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        {loading && !overview ? <div className="rounded-2xl border border-neutral-200 bg-white p-8 text-sm text-neutral-500">Loading live analytics…</div> : overview && <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard icon={Users} label="Unique visitors" value={metrics.unique_visitors} detail={`${metrics.authenticated_visitors} signed-in visitors`} />
            <MetricCard icon={Activity} label="Sessions" value={metrics.sessions} detail={`${formatDuration(metrics.avg_session_seconds)} average engagement`} />
            <MetricCard icon={Eye} label="Page views" value={metrics.page_views} detail={`${metrics.total_events} tracked events`} />
            <MetricCard icon={MousePointerClick} label="Clicks" value={metrics.clicks} detail={`${metrics.job_apply_clicks} apply intents`} />
            <MetricCard icon={UserPlus} label="Signup funnel" value={metrics.signups} detail={`${metrics.signup_starts} signup starts`} />
            <MetricCard icon={Clock3} label="Engaged time" value={formatDuration(metrics.engaged_seconds)} detail="Across all tracked sessions" />
            <MetricCard icon={BarChart3} label="Jobs visitors" value={metrics.anonymous_job_sessions_without_signup} detail="Anonymous job sessions without signup" />
            <MetricCard icon={Activity} label="System records" value={metrics.users_total + metrics.active_jobs + metrics.applications_total} detail={`${metrics.users_total} users · ${metrics.active_jobs} active jobs · ${metrics.applications_total} applications`} />
          </div>
          <div className="mt-4 flex flex-col justify-between gap-3 rounded-2xl border border-neutral-200 bg-white px-5 py-4 text-sm shadow-sm sm:flex-row sm:items-center"><div><span className="font-semibold text-neutral-900">ATS job mirror</span><span className="ml-2 text-neutral-500">{overview.system.ats_sync.last_success_at ? `Last success ${formatWhen(overview.system.ats_sync.last_success_at)}` : 'No successful sync recorded yet'}</span></div><div className={`inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-xs font-bold ${overview.system.ats_sync.status === 'success' && !overview.system.ats_sync.stale ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}><span className="h-2 w-2 rounded-full bg-current" />{overview.system.ats_sync.status}{overview.system.ats_sync.stale ? ' · stale' : ''}</div></div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
            <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><div><h2 className="font-semibold text-neutral-900">Traffic trend</h2><p className="mt-1 text-xs text-neutral-500">Sessions per day</p></div><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">Live collection</span></div><div className="mt-6 flex h-44 items-end gap-1.5 overflow-x-auto">{overview.daily.map((row) => <div key={row.day} className="flex min-w-5 flex-1 flex-col items-center justify-end gap-2"><div className="w-full rounded-t-md bg-brand-turquoise-500/80" style={{ height: `${Math.max(5, (row.sessions / maxDaily) * 100)}%` }} title={`${row.sessions} sessions`} /><span className="text-[10px] text-neutral-400">{new Date(row.day).toLocaleDateString([], { month: 'short', day: 'numeric' })}</span></div>)}</div></section>
            <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><h2 className="font-semibold text-neutral-900">Signup funnel</h2><p className="mt-1 text-xs text-neutral-500">Intent to account creation</p><div className="mt-5 space-y-4">{[['Signup starts', metrics.signup_starts], ['Completed signups', metrics.signups], ['Login completions', metrics.login_completions]].map(([label, value]) => <div key={String(label)} className="flex items-center justify-between rounded-xl bg-neutral-50 px-4 py-3"><span className="text-sm text-neutral-600">{label}</span><span className="text-lg font-bold text-neutral-900">{value}</span></div>)}<p className="text-xs leading-relaxed text-neutral-500">Conversion rate: {metrics.signup_starts ? `${Math.round((metrics.signups / metrics.signup_starts) * 100)}%` : '—'} of tracked signup starts completed.</p></div></section>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-3"><ListBlock title="Top paths" empty="No page views yet." rows={overview.top_paths.map((row) => ({ label: row.path, count: row.count }))} /><ListBlock title="Top click targets" empty="No clicks yet." rows={overview.top_clicks.map((row) => ({ label: row.label || row.target || 'Unnamed click', count: row.count }))} /><ListBlock title="Most viewed job pages" empty="No job detail views yet." rows={overview.top_jobs.map((row) => ({ label: row.path, count: row.views }))} /></div>
          <AcquisitionTable rows={overview.acquisition_sources} />

          <section className="mt-6 rounded-2xl border border-amber-200 bg-amber-50/70 p-5 shadow-sm"><div className="flex items-start justify-between gap-4"><div><h2 className="font-semibold text-neutral-900">Anonymous job visitors who did not sign up</h2><p className="mt-1 text-sm text-neutral-600">These sessions reached the job experience without a linked account or recorded signup completion.</p></div><span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">{anonymousJobVisitors.length} shown</span></div><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-amber-200 text-xs uppercase tracking-wide text-amber-800"><tr><th className="pb-3 pr-4">First seen</th><th className="pb-3 pr-4">Landing</th><th className="pb-3 pr-4">Last path</th><th className="pb-3 pr-4">Pages</th><th className="pb-3">Engaged</th></tr></thead><tbody className="divide-y divide-amber-200/70">{anonymousJobVisitors.map((session) => <tr key={session.id}><td className="py-3 pr-4 text-neutral-600">{formatWhen(session.first_seen_at)}</td><td className="py-3 pr-4 font-medium text-neutral-900">{session.landing_path || '—'}</td><td className="py-3 pr-4 text-neutral-600">{session.last_path || '—'}</td><td className="py-3 pr-4 text-neutral-600">{session.page_views}</td><td className="py-3 font-semibold text-neutral-900">{formatDuration(session.engaged_seconds)}</td></tr>)}</tbody></table>{anonymousJobVisitors.length === 0 && <p className="py-5 text-sm text-neutral-500">No anonymous non-converting job sessions in the latest activity window.</p>}</div></section>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_1fr]"><section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><h2 className="font-semibold text-neutral-900">Recent sessions</h2><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead className="border-b border-neutral-200 text-xs uppercase tracking-wide text-neutral-400"><tr><th className="pb-3 pr-3">When</th><th className="pb-3 pr-3">Visitor</th><th className="pb-3 pr-3">Landing</th><th className="pb-3 pr-3">Pages</th><th className="pb-3">Time</th></tr></thead><tbody className="divide-y divide-neutral-100">{overview.recent_sessions.slice(0, 12).map((session) => <tr key={session.id}><td className="py-3 pr-3 text-xs text-neutral-500">{formatWhen(session.last_seen_at)}</td><td className="py-3 pr-3">{session.email || <span className="font-mono text-xs text-neutral-400">{session.anonymous_id.slice(0, 8)}…</span>}</td><td className="max-w-40 truncate py-3 pr-3 text-neutral-500">{session.landing_path || '—'}</td><td className="py-3 pr-3 text-neutral-500">{session.page_views}</td><td className="py-3 font-medium">{formatDuration(session.engaged_seconds)}</td></tr>)}</tbody></table></div></section><section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><h2 className="font-semibold text-neutral-900">Recent event stream</h2><div className="mt-4 space-y-3">{overview.recent_events.slice(0, 12).map((event) => <div key={event.id} className="rounded-xl border border-neutral-100 bg-neutral-50 px-3 py-2.5"><div className="flex items-center justify-between gap-3"><span className="text-xs font-bold text-brand-turquoise-700">{metricLabel(event.event_name)}</span><span className="text-[11px] text-neutral-400">{formatWhen(event.occurred_at)}</span></div><p className="mt-1 truncate text-xs text-neutral-600">{event.path}{event.label ? ` · ${event.label}` : ''}</p><p className="mt-1 text-[10px] text-neutral-400">{event.email || `anonymous ${event.anonymous_id.slice(0, 8)}…`}</p></div>)}{overview.recent_events.length === 0 && <p className="text-sm text-neutral-500">No events collected yet.</p>}</div></section></div>
        </>}
      </main>
    </div>
  )
}
