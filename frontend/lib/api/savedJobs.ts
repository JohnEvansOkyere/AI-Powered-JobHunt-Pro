import { apiClient } from './client'

export interface Application {
  id: string
  user_id: string
  job_id: string
  cv_id?: string
  tailored_cv_path?: string
  cover_letter?: string
  application_email?: string
  status: string
  saved_at?: string
  expires_at?: string
  created_at: string
  updated_at: string
}

export async function saveJob(jobId: string): Promise<Application> {
  const response = await apiClient.post<Application>(
    `/api/v1/applications/save-job/${jobId}`
  )
  return response.data
}

export async function unsaveJob(jobId: string): Promise<void> {
  await apiClient.delete(`/api/v1/applications/unsave-job/${jobId}`)
}

export async function getSavedJobs(): Promise<Application[]> {
  const response = await apiClient.get<Application[]>(
    '/api/v1/applications/saved-jobs'
  )
  return response.data
}

export async function checkIfJobSaved(jobId: string, savedJobs: Application[]): boolean {
  return savedJobs.some(app => app.job_id === jobId)
}
