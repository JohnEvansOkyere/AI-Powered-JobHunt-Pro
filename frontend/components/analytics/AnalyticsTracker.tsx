'use client'

import { useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import { trackEvent } from '@/lib/analytics'

function pageEvent(path: string) {
  if (path === '/jobs') return 'jobs_page_view'
  if (path.startsWith('/jobs/')) return 'job_detail_view'
  return 'page_view'
}

export function AnalyticsTracker() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const query = searchParams.toString()

  useEffect(() => {
    const path = pathname || window.location.pathname
    const startedAt = Date.now()
    let lastReportedAt = startedAt
    void trackEvent({
      event_name: pageEvent(path),
      path,
      metadata: query ? { query } : {},
    })

    const heartbeat = window.setInterval(() => {
      const now = Date.now()
      const duration = now - lastReportedAt
      lastReportedAt = now
      void trackEvent({ event_name: 'page_heartbeat', path, duration_ms: duration })
    }, 15000)

    const onClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null
      const element = target?.closest('a,button,[data-analytics]') as HTMLElement | null
      if (!element || element.dataset.analyticsIgnore === 'true') return
      const isFormControl = ['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName)
      if (isFormControl) return
      const explicitName = element.dataset.analytics
      const href = element.getAttribute('href') || element.getAttribute('data-analytics-target') || undefined
      const label = (element.textContent || element.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 300)
      void trackEvent({
        event_name: explicitName || 'click',
        path,
        target: href,
        label,
        metadata: element.dataset.jobId ? { job_id: element.dataset.jobId } : {},
      })
    }

    const onVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        const now = Date.now()
        void trackEvent({ event_name: 'page_exit', path, duration_ms: now - lastReportedAt })
        lastReportedAt = now
      }
    }

    document.addEventListener('click', onClick, true)
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => {
      window.clearInterval(heartbeat)
      document.removeEventListener('click', onClick, true)
      document.removeEventListener('visibilitychange', onVisibilityChange)
      void trackEvent({ event_name: 'page_exit', path, duration_ms: Date.now() - lastReportedAt })
    }
  }, [pathname, query])

  return null
}
