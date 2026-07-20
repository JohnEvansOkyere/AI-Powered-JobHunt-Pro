'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  LogOut,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  UserCheck,
  UserX,
  Users,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import {
  getAdminIdentity,
  getAdminUsers,
  revokeAdminUser,
  updateAdminUserStatus,
  type AdminUser,
} from '@/lib/api/admin'
import { signOut } from '@/lib/auth'

type UserFilter = 'all' | 'active' | 'suspended'

function formatWhen(value: string | null) {
  if (!value) return 'Never'
  return new Date(value).toLocaleDateString([], { dateStyle: 'medium' })
}

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${active ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-emerald-500' : 'bg-red-500'}`} />
      {active ? 'Active' : 'Suspended'}
    </span>
  )
}

function UserRow({
  user,
  busy,
  onToggleStatus,
  onRevoke,
}: {
  user: AdminUser
  busy: boolean
  onToggleStatus: (user: AdminUser) => void
  onRevoke: (user: AdminUser) => void
}) {
  return (
    <div className="grid gap-4 border-b border-neutral-100 px-5 py-5 last:border-0 lg:grid-cols-[minmax(0,1.7fr)_minmax(150px,0.8fr)_minmax(120px,0.7fr)_minmax(230px,1fr)] lg:items-center">
      <div className="min-w-0">
        <p className="truncate font-semibold text-neutral-900">{user.full_name || 'Unnamed user'}</p>
        <p className="mt-1 truncate text-sm text-neutral-500">{user.email || 'No email address'}</p>
        <p className="mt-1 text-xs text-neutral-400">Joined {formatWhen(user.created_at)}</p>
      </div>
      <div><StatusBadge active={user.is_active} /></div>
      <div className="text-sm text-neutral-500">
        {user.is_admin ? <span className="inline-flex items-center gap-1.5 font-semibold text-brand-turquoise-700"><ShieldCheck className="h-4 w-4" /> Admin</span> : 'Candidate'}
      </div>
      <div className="flex flex-wrap gap-2 lg:justify-end">
        <button
          type="button"
          disabled={busy}
          onClick={() => onToggleStatus(user)}
          className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${user.is_active ? 'border-amber-200 text-amber-700 hover:bg-amber-50' : 'border-emerald-200 text-emerald-700 hover:bg-emerald-50'}`}
        >
          {user.is_active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
          {user.is_active ? 'Suspend' : 'Reactivate'}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => onRevoke(user)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Trash2 className="h-4 w-4" /> Revoke & delete
        </button>
      </div>
    </div>
  )
}

export default function AdminUsersPage() {
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [counts, setCounts] = useState({ total: 0, active: 0, suspended: 0 })
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<UserFilter>('all')
  const [loading, setLoading] = useState(true)
  const [busyUserId, setBusyUserId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadUsers = async () => {
    setLoading(true)
    setError('')
    try {
      const result = await getAdminUsers(search, filter)
      setUsers(result.users)
      setCounts({ total: result.total, active: result.active, suspended: result.suspended })
    } catch (requestError) {
      if ((requestError as { status?: number })?.status === 401 || (requestError as { status?: number })?.status === 403) {
        router.replace('/dashboard')
        return
      }
      setError(getErrorMessage(requestError, 'Could not load users.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!authLoading && !user) router.replace('/auth/login')
  }, [authLoading, router, user])

  useEffect(() => {
    if (!authLoading && user) {
      void getAdminIdentity().catch(() => router.replace('/dashboard'))
      void loadUsers()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user, filter])

  const handleSearch = (event: React.FormEvent) => {
    event.preventDefault()
    void loadUsers()
  }

  const handleToggleStatus = async (target: AdminUser) => {
    if (target.is_active && !window.confirm(`Suspend ${target.email || 'this user'}? They will be blocked from authenticated platform features immediately.`)) return
    setBusyUserId(target.id)
    setError('')
    setNotice('')
    try {
      await updateAdminUserStatus(target.id, !target.is_active)
      setNotice(`${target.email || 'User'} is now ${target.is_active ? 'suspended' : 'active'}.`)
      await loadUsers()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Could not update this user.'))
    } finally {
      setBusyUserId(null)
    }
  }

  const handleRevoke = async (target: AdminUser) => {
    const confirmation = window.prompt(`Type REVOKE to permanently delete ${target.email || 'this user'} and their platform data.`)
    if (confirmation !== 'REVOKE') return
    setBusyUserId(target.id)
    setError('')
    setNotice('')
    try {
      const result = await revokeAdminUser(target.id)
      setNotice(result.warning ? `${target.email || 'User'} was removed locally. ${result.warning}` : `${target.email || 'User'} was permanently revoked.`)
      await loadUsers()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Could not revoke this user.'))
    } finally {
      setBusyUserId(null)
    }
  }

  if (authLoading || !user) return <div className="min-h-screen bg-neutral-950" />

  return (
    <div className="min-h-screen bg-[#f6f8f7] text-neutral-900">
      <header className="border-b border-white/10 bg-neutral-950 text-white">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-brand-turquoise-500/15 p-2 text-brand-turquoise-300"><ShieldCheck className="h-5 w-5" /></div>
            <div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-turquoise-300">VeloxaHire Admin</p><h1 className="mt-1 text-xl font-semibold">User control</h1></div>
          </div>
          <div className="flex items-center gap-2 text-sm text-white/60">
            <span className="hidden sm:inline">{user.email}</span>
            <button onClick={() => signOut().then(() => router.replace('/auth/login'))} className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-3 py-2 text-white hover:bg-white/10"><LogOut className="h-4 w-4" /> Sign out</button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-4 py-7 sm:px-6 lg:px-8">
        <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2 text-sm font-medium">
              <button onClick={() => router.push('/dashboard/admin')} className="inline-flex items-center gap-1.5 text-neutral-500 hover:text-neutral-900"><BarChart3 className="h-4 w-4" /> Analytics</button>
              <span className="text-neutral-300">/</span><span className="text-neutral-900">Users</span>
            </div>
            <p className="text-sm text-neutral-500">Control who can access the platform. Suspension blocks authenticated API access; revoke permanently deletes the account and its stored data.</p>
          </div>
          <button onClick={() => void loadUsers()} className="inline-flex items-center justify-center gap-2 rounded-xl bg-neutral-900 px-3 py-2 text-sm font-semibold text-white hover:bg-neutral-800"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh</button>
        </div>

        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          {[
            { label: 'All accounts', value: counts.total, icon: Users, color: 'text-neutral-700 bg-neutral-100' },
            { label: 'Active', value: counts.active, icon: CheckCircle2, color: 'text-emerald-700 bg-emerald-50' },
            { label: 'Suspended', value: counts.suspended, icon: AlertTriangle, color: 'text-red-700 bg-red-50' },
          ].map((card) => <div key={card.label} className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><span className="text-sm font-medium text-neutral-500">{card.label}</span><span className={`rounded-xl p-2 ${card.color}`}><card.icon className="h-4 w-4" /></span></div><p className="mt-3 text-3xl font-bold tracking-tight">{card.value}</p></div>)}
        </div>

        <section className="rounded-2xl border border-neutral-200 bg-white shadow-sm">
          <div className="flex flex-col gap-3 border-b border-neutral-100 p-5 sm:flex-row sm:items-center sm:justify-between">
            <form onSubmit={handleSearch} className="flex flex-1 gap-2 sm:max-w-xl">
              <label className="relative flex-1"><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-neutral-400" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by name or email" className="w-full rounded-xl border border-neutral-200 py-2 pl-9 pr-3 text-sm outline-none transition focus:border-brand-turquoise-500 focus:ring-2 focus:ring-brand-turquoise-100" /></label>
              <button type="submit" className="rounded-xl bg-neutral-100 px-4 py-2 text-sm font-semibold text-neutral-700 hover:bg-neutral-200">Search</button>
            </form>
            <select value={filter} onChange={(event) => setFilter(event.target.value as UserFilter)} className="rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-semibold text-neutral-700 outline-none focus:border-brand-turquoise-500"><option value="all">All statuses</option><option value="active">Active only</option><option value="suspended">Suspended only</option></select>
          </div>

          {error && <div className="mx-5 mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
          {notice && <div className="mx-5 mt-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</div>}
          <div className="hidden border-b border-neutral-100 px-5 py-3 text-xs font-bold uppercase tracking-wide text-neutral-400 lg:grid lg:grid-cols-[minmax(0,1.7fr)_minmax(150px,0.8fr)_minmax(120px,0.7fr)_minmax(230px,1fr)]"><span>User</span><span>Status</span><span>Access</span><span className="text-right">Actions</span></div>
          {loading ? <div className="p-8 text-center text-sm text-neutral-500">Loading user accounts…</div> : users.length === 0 ? <div className="p-10 text-center"><Users className="mx-auto h-8 w-8 text-neutral-300" /><p className="mt-3 text-sm font-medium text-neutral-600">No users match this filter.</p></div> : users.map((target) => <UserRow key={target.id} user={target} busy={busyUserId === target.id} onToggleStatus={handleToggleStatus} onRevoke={handleRevoke} />)}
        </section>
      </main>
    </div>
  )
}
