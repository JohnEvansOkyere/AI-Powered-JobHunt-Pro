'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import {
  fetchRecommendations,
  triggerRegenerate,
  type RecommendationItem,
  type Tier,
} from '@/lib/api/recommendations'
import { saveJob, markJobApplied } from '@/lib/api/applications'
import {
  Star,
  Zap,
  List,
  RefreshCw,
  ExternalLink,
  Bookmark,
  BookmarkCheck,
  MapPin,
  Clock,
  AlertCircle,
  User,
  ArrowRight,
  BadgeCheck,
  ChevronRight,
} from 'lucide-react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'

// ---- Types ---------------------------------------------------------------

interface TierState {
  items: RecommendationItem[]
  total: number
  loading: boolean
  error: string | null
}

const INITIAL_TIER_STATE: TierState = {
  items: [],
  total: 0,
  loading: true,
  error: null,
}

type TabId = Tier

// ---- Tier config ---------------------------------------------------------

const TIER_CONFIG: {
  id: TabId
  label: string
  mobileLabel: string
  icon: typeof Star
  iconColor: string
  dotColor: string
  description: string
}[] = [
  {
    id: 'tier1',
    label: 'Highly recommended',
    mobileLabel: 'Top picks',
    icon: Star,
    iconColor: 'text-amber-500',
    dotColor: 'bg-amber-500',
    description: 'Strong match on your target title and core skills.',
  },
  {
    id: 'tier2',
    label: 'Likely a fit',
    mobileLabel: 'Worth a look',
    icon: Zap,
    iconColor: 'text-brand-turquoise-600',
    dotColor: 'bg-brand-turquoise-500',
    description: 'Adjacent roles with strong semantic match.',
  },
  {
    id: 'tier3',
    label: 'All roles',
    mobileLabel: 'All',
    icon: List,
    iconColor: 'text-neutral-500',
    dotColor: 'bg-neutral-400',
    description: 'Everything in your target area, sorted by freshness.',
  },
]

// ---- Helpers -------------------------------------------------------------

function freshnessLabel(item: RecommendationItem): string {
  const dateStr = item.job?.posted_date || item.job?.scraped_at
  if (!dateStr) return ''
  const diffH = (Date.now() - new Date(dateStr).getTime()) / 3_600_000
  if (diffH < 48) return 'Today'
  if (diffH < 168) return `${Math.round(diffH / 24)}d ago`
  if (diffH < 720) return `${Math.round(diffH / 168)}w ago`
  return `${Math.round(diffH / 720)}mo ago`
}

function applyUrl(item: RecommendationItem): string | null {
  return item.job?.job_link || item.job?.source_url || null
}

// ---- Components ----------------------------------------------------------

function MatchBadge({ score, tier }: { score: number; tier: Tier }) {
  const pctStr = `${Math.round(score * 100)}%`
  const cls =
    tier === 'tier1'
      ? 'bg-amber-50 text-amber-700 border-amber-100'
      : tier === 'tier2'
      ? 'bg-brand-turquoise-50 text-brand-turquoise-700 border-brand-turquoise-100'
      : 'bg-neutral-50 text-neutral-600 border-neutral-200'
  return (
    <span className={`text-[11px] font-medium border rounded-md px-1.5 py-0.5 ${cls}`}>
      {pctStr} match
    </span>
  )
}

interface RecCardProps {
  item: RecommendationItem
  savedSet: Set<string>
  onSave: (jobId: string) => void
  onApply: (jobId: string) => void
}

function RecCard({ item, savedSet, onSave, onApply }: RecCardProps) {
  const job = item.job
  const url = applyUrl(item)
  const isSaved = savedSet.has(item.job_id)
  const tier = item.tier as Tier
  const freshness = freshnessLabel(item)

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className="bg-white rounded-xl border border-neutral-200 hover:border-neutral-300 transition-colors p-4 flex flex-col gap-3"
    >
      {/* Header: meta + save */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-2">
            <MatchBadge score={item.match_score} tier={tier} />
            {job?.source === 'recruiter' && (
              <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-md px-1.5 py-0.5 font-medium">
                <BadgeCheck className="w-3 h-3" />
                Recruiter
              </span>
            )}
          </div>
          <h3 className="font-semibold text-neutral-900 text-sm leading-snug line-clamp-2">
            {job?.title || 'Untitled role'}
          </h3>
          <p className="text-xs text-neutral-500 mt-0.5 truncate">
            {job?.company || 'Unknown company'}
          </p>
        </div>
        <button
          onClick={() => onSave(item.job_id)}
          aria-label={isSaved ? 'Remove from saved' : 'Save for later'}
          className={`p-1.5 -mr-1 rounded-md transition-colors flex-shrink-0 ${
            isSaved
              ? 'text-brand-turquoise-600'
              : 'text-neutral-300 hover:text-neutral-600 hover:bg-neutral-50'
          }`}
        >
          {isSaved ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
        </button>
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-neutral-500">
        {job?.location && (
          <span className="inline-flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            <span className="truncate max-w-[10rem]">{job.location}</span>
          </span>
        )}
        {job?.remote_type && <span className="capitalize">{job.remote_type}</span>}
        {freshness && (
          <span className="inline-flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {freshness}
          </span>
        )}
      </div>

      {/* Reason */}
      {item.match_reason && (
        <p className="text-xs text-neutral-600 leading-relaxed line-clamp-2">
          {item.match_reason}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        {url ? (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer nofollow"
            onClick={() => onApply(item.job_id)}
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-brand-turquoise-600 hover:bg-brand-turquoise-700 text-white rounded-lg text-xs font-medium transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Apply
          </a>
        ) : (
          <button
            onClick={() => onApply(item.job_id)}
            className="flex-1 px-3 py-2 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg text-xs font-medium transition-colors"
          >
            Mark applied
          </button>
        )}
      </div>
    </motion.div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-neutral-200 p-4 animate-pulse space-y-3">
      <div className="flex gap-1.5">
        <div className="h-4 w-16 bg-neutral-100 rounded-md" />
      </div>
      <div className="h-4 w-4/5 bg-neutral-100 rounded" />
      <div className="h-3 w-2/5 bg-neutral-100 rounded" />
      <div className="h-3 w-3/5 bg-neutral-100 rounded" />
      <div className="h-8 bg-neutral-50 rounded-lg" />
    </div>
  )
}

function EmptyTier1() {
  return (
    <div className="bg-white rounded-xl border border-dashed border-neutral-200 py-10 px-4 text-center">
      <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center mx-auto mb-3">
        <Star className="w-5 h-5 text-amber-500" />
      </div>
      <h3 className="text-sm font-semibold text-neutral-900 mb-1">
        Nothing highly recommended yet
      </h3>
      <p className="text-xs text-neutral-500 max-w-xs mx-auto leading-relaxed mb-4">
        We need a bit more signal. Add a target title, key skills, and an active CV.
      </p>
      <Link
        href="/dashboard/profile"
        className="inline-flex items-center gap-1.5 px-3 py-2 bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium rounded-lg transition-colors"
      >
        <User className="w-3.5 h-3.5" />
        Enrich profile
        <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  )
}

function EmptyGeneric({ tier }: { tier: Tier }) {
  const cfg = TIER_CONFIG.find((t) => t.id === tier)!
  return (
    <div className="bg-white rounded-xl border border-dashed border-neutral-200 py-10 px-4 text-center">
      <div className="w-10 h-10 bg-neutral-50 rounded-lg flex items-center justify-center mx-auto mb-3">
        <cfg.icon className="w-5 h-5 text-neutral-400" />
      </div>
      <h3 className="text-sm font-semibold text-neutral-900 mb-1">
        No {cfg.label.toLowerCase()} yet
      </h3>
      <p className="text-xs text-neutral-500 max-w-xs mx-auto leading-relaxed">
        Matching runs every 12 hours. Come back later or tap Refresh.
      </p>
    </div>
  )
}

// ---- Main page -----------------------------------------------------------

export default function RecommendationsPage() {
  const [tierStates, setTierStates] = useState<Record<Tier, TierState>>({
    tier1: { ...INITIAL_TIER_STATE },
    tier2: { ...INITIAL_TIER_STATE },
    tier3: { ...INITIAL_TIER_STATE },
  })
  const [activeTab, setActiveTab] = useState<TabId>('tier1')
  const [savedSet, setSavedSet] = useState<Set<string>>(new Set())
  const [regenerating, setRegenerating] = useState(false)

  const loadedRef = useRef<Set<Tier>>(new Set())

  const loadTier = useCallback(async (tier: Tier) => {
    if (loadedRef.current.has(tier)) return
    loadedRef.current.add(tier)
    setTierStates((prev) => ({
      ...prev,
      [tier]: { ...prev[tier], loading: true, error: null },
    }))
    try {
      const data = await fetchRecommendations(tier, 1, tier === 'tier3' ? 50 : 30)
      setTierStates((prev) => ({
        ...prev,
        [tier]: { items: data.items, total: data.total, loading: false, error: null },
      }))
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load recommendations'
      setTierStates((prev) => ({
        ...prev,
        [tier]: { items: [], total: 0, loading: false, error: msg },
      }))
    }
  }, [])

  useEffect(() => {
    loadTier('tier1')
  }, [loadTier])

  const handleTabChange = (tier: TabId) => {
    setActiveTab(tier)
    loadTier(tier)
  }

  const handleSave = async (jobId: string) => {
    const wasSaved = savedSet.has(jobId)
    setSavedSet((prev) => {
      const next = new Set(prev)
      wasSaved ? next.delete(jobId) : next.add(jobId)
      return next
    })
    try {
      if (!wasSaved) await saveJob(jobId)
    } catch {
      setSavedSet((prev) => {
        const next = new Set(prev)
        wasSaved ? next.add(jobId) : next.delete(jobId)
        return next
      })
      toast.error('Could not save job. Try again.')
    }
  }

  const handleApply = async (jobId: string) => {
    try {
      await markJobApplied(jobId)
    } catch {
      // non-blocking — user is already opening the external link
    }
  }

  const handleRegenerate = async () => {
    setRegenerating(true)
    try {
      const res = await triggerRegenerate()
      if (res.status === 'already_fresh') {
        toast.success('Your recommendations are already up to date.')
      } else {
        toast.success('Refreshing recommendations. Check back in a minute.')
        loadedRef.current.clear()
        setTierStates({
          tier1: { ...INITIAL_TIER_STATE, loading: false },
          tier2: { ...INITIAL_TIER_STATE, loading: false },
          tier3: { ...INITIAL_TIER_STATE, loading: false },
        })
      }
    } catch {
      toast.error('Could not refresh. Try again later.')
    } finally {
      setRegenerating(false)
    }
  }

  const activeCfg = TIER_CONFIG.find((t) => t.id === activeTab)!

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-7xl mx-auto">
          {/* Page header */}
          <div className="flex items-start justify-between gap-3 mb-6">
            <div>
              <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight">
                Recommendations
              </h1>
              <p className="text-sm text-neutral-500 mt-0.5">
                Updated every 12 hours · ranked by AI
              </p>
            </div>
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-neutral-200 hover:border-neutral-300 text-neutral-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${regenerating ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>

          {/* Mobile: segmented tabs */}
          <div className="lg:hidden mb-4">
            <div className="flex bg-neutral-100 rounded-lg p-1 gap-1">
              {TIER_CONFIG.map((cfg) => {
                const count = tierStates[cfg.id].total
                const isActive = activeTab === cfg.id
                return (
                  <button
                    key={cfg.id}
                    onClick={() => handleTabChange(cfg.id)}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-md text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-white shadow-sm text-neutral-900'
                        : 'text-neutral-500 hover:text-neutral-700'
                    }`}
                  >
                    <cfg.icon className={`w-3.5 h-3.5 ${isActive ? cfg.iconColor : ''}`} />
                    <span>{cfg.mobileLabel}</span>
                    {count > 0 && (
                      <span
                        className={`text-[10px] rounded-full px-1.5 py-0.5 ${
                          isActive
                            ? 'bg-neutral-100 text-neutral-700'
                            : 'bg-white text-neutral-500'
                        }`}
                      >
                        {count}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
            <div className="mt-2 flex items-center justify-between gap-2 px-1">
              <p className="text-xs text-neutral-500">{activeCfg.description}</p>
              {tierStates[activeTab].total > 0 && (
                <Link
                  href={`/dashboard/jobs?tier=${activeTab}`}
                  className="inline-flex items-center gap-1 text-xs font-medium text-brand-turquoise-700 whitespace-nowrap"
                >
                  See all
                  <ChevronRight className="w-3 h-3" />
                </Link>
              )}
            </div>

            <div className="mt-4 space-y-3">
              <AnimatePresence mode="wait">
                <MobileColumn
                  key={activeTab}
                  tier={activeTab}
                  state={tierStates[activeTab]}
                  savedSet={savedSet}
                  onSave={handleSave}
                  onApply={handleApply}
                />
              </AnimatePresence>
            </div>
          </div>

          {/* Desktop: 3 columns */}
          <div className="hidden lg:grid lg:grid-cols-3 gap-5">
            {TIER_CONFIG.map((cfg) => {
              const state = tierStates[cfg.id]
              const hasItems = state.items.length > 0
              const showSeeAll = hasItems && state.total > state.items.length
              return (
                <section key={cfg.id} className="flex flex-col min-w-0">
                  {/* Column header — clickable when there are items */}
                  <header className="mb-3 pb-3 border-b border-neutral-200">
                    <Link
                      href={`/dashboard/jobs?tier=${cfg.id}`}
                      className="group flex items-center gap-2 -mx-1 px-1 py-1 rounded-md hover:bg-neutral-50 transition-colors"
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dotColor}`} />
                      <h2 className="text-sm font-semibold text-neutral-900 flex-1 group-hover:text-brand-turquoise-700">
                        {cfg.label}
                      </h2>
                      {state.total > 0 && (
                        <span className="text-xs text-neutral-500 tabular-nums">
                          {state.total}
                        </span>
                      )}
                      <ChevronRight className="w-3.5 h-3.5 text-neutral-300 group-hover:text-brand-turquoise-600 group-hover:translate-x-0.5 transition-all" />
                    </Link>
                    <p className="text-xs text-neutral-500 mt-1">{cfg.description}</p>
                  </header>

                  <div className="space-y-3 min-h-[200px]">
                    <AnimatePresence>
                      <ColumnContent
                        tier={cfg.id}
                        state={state}
                        savedSet={savedSet}
                        onSave={handleSave}
                        onApply={handleApply}
                      />
                    </AnimatePresence>

                    {showSeeAll && (
                      <Link
                        href={`/dashboard/jobs?tier=${cfg.id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-brand-turquoise-700 hover:text-brand-turquoise-800 px-1 py-1"
                      >
                        See all {state.total} with filters
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    )}
                  </div>
                </section>
              )
            })}
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

// ---- Column content (shared between mobile + desktop) -------------------

interface ColumnProps {
  tier: Tier
  state: TierState
  savedSet: Set<string>
  onSave: (id: string) => void
  onApply: (id: string) => void
}

function ColumnContent({ tier, state, savedSet, onSave, onApply }: ColumnProps) {
  if (state.loading) {
    return (
      <>
        {[1, 2, 3].map((i) => (
          <SkeletonCard key={i} />
        ))}
      </>
    )
  }
  if (state.error) {
    return (
      <div className="flex items-center gap-2 text-sm text-rose-600 py-3 px-3 bg-rose-50 border border-rose-100 rounded-lg">
        <AlertCircle className="w-4 h-4 flex-shrink-0" />
        {state.error}
      </div>
    )
  }
  if (state.items.length === 0) {
    return tier === 'tier1' ? <EmptyTier1 /> : <EmptyGeneric tier={tier} />
  }
  return (
    <>
      {state.items.map((item) => (
        <RecCard key={item.id} item={item} savedSet={savedSet} onSave={onSave} onApply={onApply} />
      ))}
    </>
  )
}

function MobileColumn({ tier, state, savedSet, onSave, onApply }: ColumnProps) {
  return (
    <motion.div
      key={tier}
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -12 }}
      transition={{ duration: 0.15 }}
      className="space-y-3"
    >
      <ColumnContent tier={tier} state={state} savedSet={savedSet} onSave={onSave} onApply={onApply} />
    </motion.div>
  )
}
