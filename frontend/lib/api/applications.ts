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

export interface GenerateCVResponse {
  application_id: string
  cv_path: string
  public_url?: string
  status: string
  created_at?: string
}

export interface Application {
  id: string
  user_id: string
  job_id: string
  cv_id?: string
  tailored_cv_path?: string
  cover_letter?: string
  application_email?: string
  status: 'draft' | 'reviewed' | 'finalized' | 'sent'
  created_at: string
  updated_at: string
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
 * List all applications for the current user
 */
export async function listApplications(status?: string): Promise<Application[]> {
  const params = status ? `?status_filter=${status}` : ''
  return apiClient.get<Application[]>(`/api/v1/applications/${params}`)
}

/**
 * Get download URL for tailored CV
 */
export async function getCVDownloadUrl(applicationId: string): Promise<{ download_url: string }> {
  return apiClient.get<{ download_url: string }>(`/api/v1/applications/${applicationId}/download-url`)
}


