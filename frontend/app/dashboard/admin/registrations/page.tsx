'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { getAdminRegistrations, type AdminRegistrations } from '@/lib/api/admin'
import { getUserErrorMessage } from '@/lib/errors'
import AdminNav from '@/components/admin/AdminNav'

function Registrations() {
  const router = useRouter()
  const params = useSearchParams()
  const requestedDays = Number(params.get('days'))
  const days = [7, 30, 90].includes(requestedDays) ? requestedDays : 30
  const { user, loading: authLoading } = useAuth()
  const [data, setData] = useState<AdminRegistrations | null>(null)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    if (authLoading) return
    if (!user) { router.replace('/auth/login'); return }
    let cancelled = false
    setData(null)
    setError('')
    getAdminRegistrations(days).then(result => { if (!cancelled) setData(result) }).catch(err => {
      if (cancelled) return
      if ([401, 403].includes(err?.status)) { router.replace('/dashboard'); return }
      setError(getUserErrorMessage(err, 'Could not load registration report. Please retry.'))
    })
    return () => { cancelled = true }
  }, [authLoading, user, days, refresh, router])

  if (authLoading || !user) return <p className="p-8">Loading…</p>
  const cards = data ? [
    { label: 'Registered accounts', value: data.signups, filter: 'all', detail: 'Created in this period' },
    { label: 'Complete profiles', value: data.complete, filter: 'complete', detail: '100% profile completion' },
    { label: 'Partially filled', value: data.partial, filter: 'partial', detail: 'Started, with fields still missing' },
    { label: 'Not started', value: data.not_started, filter: 'not_started', detail: 'No scored profile fields filled' },
  ] : []
  return <main className="min-h-screen bg-[#f6f8f7] px-4 py-8 text-neutral-900 sm:px-8">
    <div className="mx-auto max-w-[1500px]">
      <AdminNav days={days} />
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-sm font-semibold text-brand-turquoise-700">VeloxaHire Admin</p><h1 className="mt-2 text-2xl font-bold">Signups & profiles</h1><p className="mt-2 max-w-2xl text-sm text-neutral-500">See who registered and how much of their profile they have filled in. Select a card to view those accounts.</p></div>
        <div className="flex gap-2"><select aria-label="Registration period" value={days} onChange={e => router.replace(`?days=${e.target.value}`)} className="rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm">{[7, 30, 90].map(d => <option key={d} value={d}>Last {d} days</option>)}</select><button onClick={() => setRefresh(v => v + 1)} className="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white">Refresh</button></div>
      </div>
      {error ? <p role="alert" className="rounded-xl bg-red-50 p-5 text-red-700">{error}</p> : !data ? <p role="status" className="p-8">Loading registration report…</p> : <>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(card => <Link key={card.filter} href={`/dashboard/admin/users?days=${days}&profile=${card.filter}`} className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm hover:border-brand-turquoise-500"><p className="text-sm font-medium text-neutral-600">{card.label}</p><p className="my-3 text-3xl font-bold">{card.value.toLocaleString()}</p><p className="text-xs text-neutral-500">{card.detail}</p><p className="mt-4 text-sm font-semibold text-brand-turquoise-700">View users →</p></Link>)}</div>
        <p className="my-5 text-sm text-neutral-600">{data.total_accounts.toLocaleString()} accounts across all time. {data.signups ? `${Math.round(data.complete / data.signups * 100)}% of accounts registered in this period have a complete profile.` : 'No accounts registered in this period.'}</p>
        <div className="grid items-start gap-6 lg:grid-cols-2">
          <section className="rounded-2xl border border-neutral-200 bg-white p-5"><h2 className="font-semibold">Daily registrations</h2><p className="mt-1 text-xs text-neutral-500">UTC dates; the first and last days cover part of a day.</p><div className="mt-4 max-h-[480px] overflow-auto"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-white"><tr><th className="py-3">Date</th><th className="py-3 text-right">Accounts created</th></tr></thead><tbody>{[...data.daily].reverse().map(row => <tr key={row.day} className="border-t border-neutral-100"><td className="py-3">{row.day}</td><td className="py-3 text-right font-semibold">{row.signups}</td></tr>)}</tbody></table></div></section>
          <section className="rounded-2xl border border-neutral-200 bg-white p-5"><h2 className="font-semibold">What these numbers mean</h2><div className="mt-4 space-y-4 text-sm leading-relaxed text-neutral-600"><p>Registrations count saved platform accounts, including administrators and suspended accounts. Deleted accounts are excluded. They do not depend on browser tracking.</p><p>Profile status shows current progress for accounts created during the selected period. It does not show when a profile became complete.</p><p>Completion follows the candidate profile score: career details 30%, skills 30%, work experience 20%, and writing/AI preferences 20%. A CV is separate from this score.</p><Link href="/dashboard/admin/users?days=0" className="inline-block font-semibold text-brand-turquoise-700">Review users across all time →</Link></div></section>
        </div>
      </>}
    </div>
  </main>
}

export default function Page() {
  return <Suspense fallback={<p className="p-8">Loading…</p>}><Registrations /></Suspense>
}
