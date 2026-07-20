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
  }>
  recent_sessions: Array<{
    id: string
    anonymous_id: string
    email: string | null
    landing_path: string | null
    last_path: string | null
    referrer: string | null
    acquisition_source: string | null
    acquisition_medium: string | null
    acquisition_campaign: string | null
    page_views: number
    event_count: number
    engaged_seconds: number
    first_seen_at: string | null
    last_seen_at: string | null
    signed_in: boolean
    converted: boolean
  }>
}

export interface AdminUser {
  id: string
  email: string | null
  full_name: string | null
  is_active: boolean
  is_admin: boolean
  email_verified: boolean
  last_login_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface AdminUsersResponse {
  users: AdminUser[]
  total: number
  active: number
  suspended: number
}

export function getAdminOverview(days = 30) {
  return apiClient.get<AdminOverview>(`/api/v1/admin/overview?days=${days}`)
}

export function getAdminIdentity() {
  return apiClient.get<{ is_admin: boolean; email: string }>('/api/v1/admin/me')
}

export function getAdminUsers(search = '', status: 'all' | 'active' | 'suspended' = 'all') {
  const params = new URLSearchParams({ status })
  if (search.trim()) params.set('search', search.trim())
  return apiClient.get<AdminUsersResponse>(`/api/v1/admin/users?${params.toString()}`)
}

export function updateAdminUserStatus(userId: string, isActive: boolean) {
  return apiClient.patch<{ user: AdminUser }>(`/api/v1/admin/users/${userId}/status`, { is_active: isActive })
}

export function revokeAdminUser(userId: string) {
  return apiClient.delete<{
    status: 'revoked'
    user_id: string
    deleted_counts: Record<string, number>
    cv_files_deleted: number
    auth_user_deleted: boolean
    warning?: string | null
  }>(`/api/v1/admin/users/${userId}`)
}
