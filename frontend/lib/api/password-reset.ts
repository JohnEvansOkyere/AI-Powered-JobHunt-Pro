// Recovery grants live only in component memory, never in URLs or storage.
import { apiError, UserFacingError } from '../errors'
const base = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export class PasswordResetError extends UserFacingError {
  constructor(message: string, status: number, public retryAfter = 0) { super(message, status) }
}

async function request<T>(step: string, body: object): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${base}/api/v1/auth/password-reset/${step}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), credentials: 'omit', cache: 'no-store',
      signal: AbortSignal.timeout(20000),
    })
  } catch {
    throw new PasswordResetError('Could not connect. Please try again.', 0)
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw new PasswordResetError(apiError(response, data).message, response.status, Number(response.headers.get('Retry-After')) || 60)
  }
  if (!data || typeof data !== 'object') throw new PasswordResetError('We could not read the response. Please try again.', response.status)
  return data as T
}

export const requestPasswordReset = (phone: string) =>
  request<{ message: string; challenge_id: string; expires_in: number; resend_after: number }>('request', { phone })
export const verifyPasswordReset = (challenge_id: string, code: string) =>
  request<{ reset_token: string; expires_in: number }>('verify', { challenge_id, code })
export const completePasswordReset = (reset_token: string, password: string) =>
  request<{ message: string }>('complete', { reset_token, password })
