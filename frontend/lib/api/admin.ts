import { apiClient } from './client'

export interface AdminOverview {
  range: { days: number; start: string; end: string }
  system: { ats_sync: { status: string; stale: boolean; last_success_at: string | null; last_error: string | null; counts?: Record<string, number> } }
  metrics: Record<string, number>
  daily: Array<{ day: string; sessions: number; events: number }>
  top_paths: Array<{ path: string; count: number }>
  top_clicks: Array<{ target: string; label: string | null; count: number }>
  top_jobs: Array<{ path: string; views: number }>
  acquisition_sources: Array<{
    source: string
    medium: string
    campaign: string | null
    sessions: number
    visitors: number
    job_views: number
    apply_clicks: number
    signups: number
  }>
  recent_events: Array<{
    id: string
    event_name: string
    path: string
    target: string | null
    label: string | null
    metadata: Record<string, unknown>
    occurred_at: string | null
    anonymous_id: string
    email: string | null
    referrer: string | null
    acquisition_source: string | null
    acquisition_medium: string | null
    acquisition_campaign: string | null
  }>
  recent_sessions: Array<{
    id: string
    anonymous_id: string
    email: string | null
    landing_path: string | null
    last_path: string | null
    page_views: number
    event_count: number
    engaged_seconds: number
    first_seen_at: string | null
    last_seen_at: string | null
    signed_in: boolean
    converted: boolean
  }>
}

export function getAdminOverview(days = 30) {
  return apiClient.get<AdminOverview>(`/api/v1/admin/overview?days=${days}`)
}

export function getAdminIdentity() {
  return apiClient.get<{ is_admin: boolean; email: string }>('/api/v1/admin/me')
}
