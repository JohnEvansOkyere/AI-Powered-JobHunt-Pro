/** Only reviewed copy reaches the interface; provider messages are untrusted. */
export class UserFacingError extends Error {
  constructor(message: string, public status = 0, public requestId?: string) {
    super(message)
    this.name = 'UserFacingError'
  }
}

const codeMessages: Record<string, string> = {
  invalid_credentials: 'The email or password is incorrect.',
  email_not_confirmed: 'Please confirm your email before signing in.',
  phone_not_confirmed: 'Please verify your phone number to continue.',
  email_address_invalid: 'Enter a valid email address.',
  email_exists: 'An account already uses this email. Sign in or reset your password.',
  user_already_exists: 'An account already exists. Sign in or reset your password.',
  phone_exists: 'This phone number is already linked to an account.',
  weak_password: 'Choose a stronger password with a mix of letters, numbers and symbols.',
  same_password: 'Choose a password you have not used for this account.',
  otp_expired: 'The code is invalid or expired. Request a new code if needed.',
  over_sms_send_rate_limit: 'Please wait a minute before requesting another code.',
  over_email_send_rate_limit: 'Please wait before requesting another email.',
  over_request_rate_limit: 'Too many attempts. Please wait and try again.',
  session_expired: 'Your session has expired. Please sign in again.',
  session_not_found: 'Your session has expired. Please sign in again.',
  refresh_token_not_found: 'Your session has expired. Please sign in again.',
  refresh_token_already_used: 'Your session has expired. Please sign in again.',
  reauthentication_needed: 'Please sign in again before changing your password.',
  phone_provider_disabled: 'Phone verification is temporarily unavailable. Please try again later.',
  hook_timeout: 'We could not confirm the code was sent. Please wait a minute before trying again.',
  hook_timeout_after_retry: 'We could not confirm the code was sent. Please wait a minute before trying again.',
}

// Compatibility for existing endpoints and locally validated form errors.
// Match whole strings; never pass through arbitrary prefixes or server text.
const messageAliases: Record<string, string> = {
  'Invalid login credentials': codeMessages.invalid_credentials,
  'Token has expired or is invalid': codeMessages.otp_expired,
  'Email verification required': codeMessages.email_not_confirmed,
  'Phone verification required': codeMessages.phone_not_confirmed,
  'Invalid authentication credentials': codeMessages.session_expired,
  'Could not validate credentials': codeMessages.session_expired,
  'Account is not available': 'Your account is unavailable. Please contact support.',
  'Invalid or expired verification code.': codeMessages.otp_expired,
  'Database integrity constraint violated': 'This change conflicts with an existing record. Refresh and try again.',
  'Saved jobs limit reached (20). Remove some before saving more.': 'You have reached the saved jobs limit. Remove a saved job before adding another.',
}
const approvedMessages = new Set([
  'Enter a valid phone number, for example 024 123 4567.',
  'Phone verification is incomplete. Try again.',
  'Please sign in to continue.',
  'Please try signing in again.',
  'Please try verifying your phone again.',
  'Open the confirmation link in your email first.',
  'The code is invalid or expired. Request a new code if needed.',
  'This reset has expired or was already used. Request a new code.',
  'Choose a stronger password and request a new reset code.',
  'Password reset is temporarily unavailable.',
  'Could not confirm the reset. Try signing in with your new password, or request a new code.',
  'Too many reset attempts. Please try again later.',
  'Enter the 6-digit code from WhatsApp.',
  'No phone pending verification. Request a new code.',
])

export function errorFields(value: unknown): { message?: string; code?: string; status?: number } {
  if (!value || typeof value !== 'object') return {}
  const data = value as Record<string, unknown>
  const nested = data.error && typeof data.error === 'object'
    ? data.error as Record<string, unknown> : data
  return {
    message: typeof nested.message === 'string' ? nested.message : typeof data.detail === 'string' ? data.detail : undefined,
    code: typeof nested.code === 'string' ? nested.code : undefined,
    status: typeof data.status === 'number' ? data.status : undefined,
  }
}

export function getUserErrorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (error instanceof UserFacingError) return error.message
  const { message, code, status } = errorFields(error)
  // Reviewed recovery messages include guidance for an ambiguous password update.
  if (message && approvedMessages.has(message)) return message
  if (status && status >= 500) return 'This service is temporarily unavailable. Please try again later.'
  if (code && Object.hasOwn(codeMessages, code)) return codeMessages[code]
  if (message && Object.hasOwn(messageAliases, message)) return messageAliases[message]
  if (status === 429) return 'Too many attempts. Please wait and try again.'
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return 'You do not have access to this action.'
  if (status === 404) return 'This item is no longer available. Refresh and try again.'
  if (status === 409) return 'This change conflicts with an existing record. Refresh and try again.'
  if (status === 413) return 'This file is too large. Choose a smaller file.'
  if (status === 422 || status === 400) return 'Check the details you entered and try again.'
  return fallback
}

export function apiError(response: Response, body: unknown): UserFacingError {
  const fields = errorFields(body)
  return new UserFacingError(
    getUserErrorMessage({ ...fields, status: response.status }),
    response.status,
    response.headers.get('X-Request-ID') || undefined,
  )
}

export function connectionError(): UserFacingError {
  return new UserFacingError('Could not connect. Check your connection and try again.')
}
