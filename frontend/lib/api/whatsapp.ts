import { apiClient } from './client'

export interface WhatsappStatus {
  whatsapp_opted_in: boolean
  whatsapp_phone_verified: boolean
  phone_masked: string | null
  digest_time_local: string
  timezone: string
}

export async function getWhatsappStatus(): Promise<WhatsappStatus> {
  return apiClient.get<WhatsappStatus>('/api/v1/notifications/whatsapp/status')
}

export async function requestWhatsappOptIn(phone: string): Promise<{ detail: string; expires_in_seconds: number }> {
  return apiClient.post('/api/v1/notifications/whatsapp/opt-in', { phone })
}

export async function verifyWhatsappCode(code: string): Promise<{ detail: string }> {
  return apiClient.post('/api/v1/notifications/whatsapp/verify', { code })
}

export async function optOutWhatsapp(): Promise<{ detail: string }> {
  return apiClient.post('/api/v1/notifications/whatsapp/opt-out')
}

export async function saveWhatsappPreferences(data: {
  digest_time_local?: string
  timezone?: string
}): Promise<{ detail: string }> {
  return apiClient.post('/api/v1/notifications/whatsapp/preferences', data)
}
