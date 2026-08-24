import { apiClient } from './client'

export type EmailLocale = 'en' | 'twi'
export type EmailFrequency = 'daily' | 'weekly'

export interface EmailLocaleOption {
  code: EmailLocale
  label: string
}

export interface EmailDigestStatus {
  email_opted_in: boolean
  email_masked: string | null
  suppressed: boolean
  locale: EmailLocale
  digest_time_local: string
  timezone: string
  frequency: EmailFrequency
  weekday: number
  paused_until: string | null
  last_sent_at: string | null
  available_locales: EmailLocaleOption[]
}

export interface EmailOptInPayload {
  email?: string
  locale: EmailLocale
  digest_time_local: string
  timezone: string
  frequency: EmailFrequency
  weekday: number
}

export interface EmailPreferencesPayload {
  locale?: EmailLocale
  digest_time_local?: string
  timezone?: string
  frequency?: EmailFrequency
  weekday?: number
  pause_until?: string | null
}

export interface EmailTestSendResult {
  status: string
  reason?: string
  jobs?: number
  locale?: string
  matches?: number
}

export async function getEmailDigestStatus(): Promise<EmailDigestStatus> {
  return apiClient.get<EmailDigestStatus>('/api/v1/notifications/email/status')
}

export async function optInToEmailDigest(
  data: EmailOptInPayload
): Promise<EmailDigestStatus & { status: string }> {
  return apiClient.post('/api/v1/notifications/email/opt-in', data)
}

export async function optOutOfEmailDigest(): Promise<{ status: string }> {
  return apiClient.post('/api/v1/notifications/email/opt-out')
}

export async function saveEmailDigestPreferences(
  data: EmailPreferencesPayload
): Promise<EmailDigestStatus & { status: string }> {
  return apiClient.post('/api/v1/notifications/email/preferences', data)
}

export async function sendTestEmailDigest(): Promise<EmailTestSendResult> {
  return apiClient.post('/api/v1/notifications/email/test-send')
}
