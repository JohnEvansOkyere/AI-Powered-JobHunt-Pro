// Recovery grants live only in component memory, never in URLs or storage.
const base = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export class PasswordResetError extends Error {
  constructor(message: string, public status: number, public retryAfter = 0) { super(message) }
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
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new PasswordResetError(typeof data.detail === 'string' ? data.detail : 'Could not complete this step. Check your details and try again.', response.status, Number(response.headers.get('Retry-After')) || 60)
  }
  return data as T
}

export const requestPasswordReset = (phone: string) =>
  request<{ message: string; challenge_id: string; expires_in: number; resend_after: number }>('request', { phone })
export const verifyPasswordReset = (challenge_id: string, code: string) =>
  request<{ reset_token: string; expires_in: number }>('verify', { challenge_id, code })
export const completePasswordReset = (reset_token: string, password: string) =>
  request<{ message: string }>('complete', { reset_token, password })
