import { apiClient } from './api/client'

const SESSION_KEY = 'veloxahire:analytics-session'
const ANONYMOUS_KEY = 'veloxahire:analytics-anonymous'
const ATTRIBUTION_KEY = 'veloxahire:analytics-attribution'

interface Attribution {
  utm_source?: string
  utm_medium?: string
  utm_campaign?: string
  utm_content?: string
  utm_term?: string
  source?: string
  medium?: string
}

function idForStorage(key: string): string {
  try {
    const existing = window.sessionStorage.getItem(key)
    if (existing) return existing
    const value = crypto.randomUUID()
    window.sessionStorage.setItem(key, value)
    return value
  } catch {
    return crypto.randomUUID()
  }
}

function anonymousId(): string {
  try {
    const existing = window.localStorage.getItem(ANONYMOUS_KEY)
    if (existing) return existing
    const value = crypto.randomUUID()
    window.localStorage.setItem(ANONYMOUS_KEY, value)
    return value
  } catch {
    return crypto.randomUUID()
  }
}

function attribution(): Attribution {
  const params = new URLSearchParams(window.location.search)
  const tagged: Attribution = {}
  for (const key of ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']) {
    const value = params.get(key)
    if (value) tagged[key as keyof Attribution] = value.slice(0, 160)
  }

  try {
    const existing = window.sessionStorage.getItem(ATTRIBUTION_KEY)
    if (Object.keys(tagged).length === 0 && existing) return JSON.parse(existing) as Attribution
    if (Object.keys(tagged).length > 0) {
      window.sessionStorage.setItem(ATTRIBUTION_KEY, JSON.stringify(tagged))
      return tagged
    }
  } catch {
    // Fall through to referrer inference on the backend.
  }
  return tagged
}

export interface AnalyticsEventInput {
  event_name: string
  path?: string
  referrer?: string
  target?: string
  label?: string
  metadata?: Record<string, string | number | boolean | null>
  duration_ms?: number
}

export async function trackEvent(event: AnalyticsEventInput): Promise<void> {
  if (typeof window === 'undefined') return
  try {
    const campaign = attribution()
    await apiClient.post('/api/v1/analytics/events', {
      session_id: idForStorage(SESSION_KEY),
      anonymous_id: anonymousId(),
      event_name: event.event_name,
      path: event.path || window.location.pathname,
      referrer: event.referrer || document.referrer || undefined,
      target: event.target,
      label: event.label,
      metadata: { ...campaign, ...(event.metadata || {}) },
      duration_ms: event.duration_ms,
      user_agent: navigator.userAgent,
    })
  } catch {
    // Analytics must never block candidate navigation or authentication.
  }
}
