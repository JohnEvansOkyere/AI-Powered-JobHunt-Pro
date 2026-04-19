/**
 * Applications API Client
 *
 * Minimal tracker for the candidate's relationship to a job:
 *   saved, applied, dismissed, hidden, interviewing, rejected, offer.
 *
 * CV tailoring and cover-letter generation were removed in v2
 * (see docs/RECOMMENDATIONS_V2_PLAN.md §4).
 */

import { apiClient } from './client'

export type ApplicationStatus =
  | 'saved'
  | 'applied'
  | 'dismissed'
  | 'hidden'
  | 'interviewing'
  | 'rejected'
  | 'offer'

export interface Application {
  id: string
  user_id: string
  job_id: string
  cv_id?: string | null
  status: ApplicationStatus
  saved_at?: string | null
  expires_at?: string | null
  created_at: string
  updated_at: string
}

export interface JobDetails {
  id: string
  title: string
  company: string
  location?: string | null
  job_link?: string | null
  source?: string
  posted_date?: string | null
  salary_range?: string | null
  job_type?: string | null
  remote_type?: string | null
}

export interface ApplicationWithJob extends Application {
  job?: JobDetails | null
}

export interface DashboardApplicationsStats {
  applications_total: number
  submitted_count: number
}

export async function getApplication(applicationId: string): Promise<Application> {
  return apiClient.get<Application>(`/api/v1/applications/${applicationId}`)
}

export async function getApplicationForJob(jobId: string): Promise<Application | null> {
  return apiClient.get<Application | null>(`/api/v1/applications/job/${jobId}`)
}

export async function listApplications(
  status?: ApplicationStatus
): Promise<ApplicationWithJob[]> {
  const params = status ? `?status_filter=${status}` : ''
  return apiClient.get<ApplicationWithJob[]>(`/api/v1/applications/${params}`)
}

export async function getApplicationsStats(): Promise<DashboardApplicationsStats> {
  return apiClient.get<DashboardApplicationsStats>('/api/v1/applications/stats')
}

export async function updateApplicationStatus(
  jobId: string,
  status: ApplicationStatus
): Promise<Application> {
  return apiClient.patch<Application>(
    `/api/v1/applications/update-status/${jobId}`,
    { status }
  )
}

export async function markJobApplied(jobId: string): Promise<Application> {
  return apiClient.post<Application>(`/api/v1/applications/mark-applied/${jobId}`, {})
}

export async function saveJob(jobId: string): Promise<Application> {
  return apiClient.post<Application>(`/api/v1/applications/save-job/${jobId}`, {})
}

export async function unsaveJob(jobId: string): Promise<void> {
  return apiClient.delete<void>(`/api/v1/applications/unsave-job/${jobId}`)
}
