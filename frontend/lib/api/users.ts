import { apiClient } from './client'

export type AccountDeleteResponse = {
  status: 'deleted'
  deleted_counts: Record<string, number>
  cv_files_deleted: number
  auth_user_deleted: boolean
  warning?: string | null
}

export async function exportMyData(): Promise<Record<string, unknown>> {
  return apiClient.get<Record<string, unknown>>('/api/v1/users/me/export')
}

export async function deleteMyAccount(): Promise<AccountDeleteResponse> {
  return apiClient.delete<AccountDeleteResponse>('/api/v1/users/me')
}
