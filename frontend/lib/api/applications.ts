/**
 * Applications API Client
 * 
 * Handles API calls for application generation and management.
 */

import { apiClient } from './client'

export interface GenerateCVRequest {
  tone?: 'professional' | 'confident' | 'friendly'
  highlight_skills?: boolean
  emphasize_relevant_experience?: boolean
}

export interface GenerateCustomCVRequest {
  job_title?: string
  company_name?: string
  job_description?: string
  job_link?: string
  location?: string
  job_type?: string
  remote_type?: string
  tone?: 'professional' | 'confident' | 'friendly' | 'enthusiastic'
  highlight_skills?: boolean
  emphasize_relevant_experience?: boolean
}

export interface GenerateCoverLetterRequest {
  job_title?: string
  company_name?: string
  job_description?: string
  job_link?: string
  location?: string
  job_type?: string
  remote_type?: string
  tone?: 'professional' | 'confident' | 'friendly' | 'enthusiastic'
  length?: 'short' | 'medium' | 'long'
}

export interface GenerateCoverLetterResponse {
  application_id: string
  cover_letter: string
  status: string
  created_at?: string
}

export interface GenerateCVResponse {
  application_id: string
  cv_path: string
  public_url?: string
  status: string
  created_at?: string
}

export type ApplicationStatus =
  | 'saved'
  | 'draft'
  | 'reviewed'
  | 'finalized'
  | 'sent'
  | 'submitted'
  | 'interviewing'
  | 'rejected'
  | 'offer'

export interface Application {
  id: string
  user_id: string
  job_id: string
  cv_id?: string
  tailored_cv_path?: string
  cover_letter?: string
  application_email?: string
  status: ApplicationStatus
  created_at: string
  updated_at: string
}

export interface JobDetails {
  id: string
  title: string
  company: string
  location?: string
  job_link?: string
  source?: string
  posted_date?: string
  salary_range?: string
  job_type?: string
  remote_type?: string
}

export interface ApplicationWithJob extends Application {
  job?: JobDetails | null
}

/**
 * Generate a tailored CV for a specific job
 */
export async function generateTailoredCV(
  jobId: string,
  request: GenerateCVRequest = {}
): Promise<GenerateCVResponse> {
  return apiClient.post<GenerateCVResponse>(
    `/api/v1/applications/generate-cv/${jobId}`,
    request
  )
}

/**
 * Generate a tailored CV from a custom job description
 */
export async function generateCustomTailoredCV(
  request: GenerateCustomCVRequest
): Promise<GenerateCVResponse> {
  return apiClient.post<GenerateCVResponse>(
    `/api/v1/applications/generate-cv-custom`,
    request
  )
}

/**
 * Generate a cover letter from a custom job description
 */
export async function generateCustomCoverLetter(
  request: GenerateCoverLetterRequest
): Promise<GenerateCoverLetterResponse> {
  return apiClient.post<GenerateCoverLetterResponse>(
    `/api/v1/applications/generate-cover-letter-custom`,
    request
  )
}

/**
 * Get a specific application by ID
 */
export async function getApplication(applicationId: string): Promise<Application> {
  return apiClient.get<Application>(`/api/v1/applications/${applicationId}`)
}

/**
 * Get application for a specific job
 */
export async function getApplicationForJob(jobId: string): Promise<Application | null> {
  return apiClient.get<Application | null>(`/api/v1/applications/job/${jobId}`)
}

/**
 * List all applications for the current user (with job details)
 */
export async function listApplications(status?: string): Promise<ApplicationWithJob[]> {
  const params = status ? `?status_filter=${status}` : ''
  return apiClient.get<ApplicationWithJob[]>(`/api/v1/applications/${params}`)
}

export interface DashboardApplicationsStats {
  applications_total: number
  submitted_count: number
}

/**
 * Get dashboard stats: total applications and submitted count
 */
export async function getApplicationsStats(): Promise<DashboardApplicationsStats> {
  return apiClient.get<DashboardApplicationsStats>('/api/v1/applications/stats')
}

/**
 * Get download URL for tailored CV
 */
export async function getCVDownloadUrl(applicationId: string): Promise<{ download_url: string }> {
  return apiClient.get<{ download_url: string }>(`/api/v1/applications/${applicationId}/download-url`)
}


