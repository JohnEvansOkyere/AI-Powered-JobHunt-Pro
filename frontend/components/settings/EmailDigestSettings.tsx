'use client'

import {
  getEmailDigestStatus,
  optInToEmailDigest,
  optOutOfEmailDigest,
  saveEmailDigestPreferences,
  sendTestEmailDigest,
  type EmailDigestStatus,
  type EmailFrequency,
  type EmailLocale,
} from '@/lib/api/email-digest'
import { CheckCircle2, Clock, Mail, Send } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

const TIMEZONE_OPTIONS = ['UTC', 'Africa/Accra', 'Africa/Lagos', 'Europe/London', 'America/New_York']

const WEEKDAYS = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' },
]

// Sample of the greeting each pack opens with, so the choice is concrete.
const LOCALE_PREVIEW: Record<EmailLocale, string> = {
  en: '“Good morning Kwame, we went through today’s postings and 5 of them match your profile.”',
  twi: '“Maakye Kwame! Yɛanya adwuma 5 a ɛfata dwuma a wotumi yɛ.”',
}

const LOCALE_FALLBACK: { code: EmailLocale; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'twi', label: 'Twi' },
]

const SKIP_REASONS: Record<string, string> = {
  not_enough_matches: 'Not enough strong matches yet — we’ll email you once there are.',
  not_opted_in: 'Turn on job match emails first.',
  suppressed: 'This address is blocked because earlier mail bounced.',
  user_cap: 'You already received a digest today.',
  global_cap: 'Daily sending limit reached. Try again tomorrow.',
  unchanged_since_last_send: 'Your matches haven’t changed since the last digest.',
  no_address: 'No email address on file for your account.',
}

export function EmailDigestSettings() {
  const [status, setStatus] = useState<EmailDigestStatus | null>(null)
  const [locale, setLocale] = useState<EmailLocale>('en')
  const [digestTime, setDigestTime] = useState('07:00')
  const [timezone, setTimezone] = useState('Africa/Accra')
  const [frequency, setFrequency] = useState<EmailFrequency>('daily')
  const [weekday, setWeekday] = useState(1)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)

  const applyStatus = (data: EmailDigestStatus) => {
    setStatus(data)
    setLocale(data.locale || 'en')
    setDigestTime(data.digest_time_local || '07:00')
    setTimezone(data.timezone || 'Africa/Accra')
    setFrequency(data.frequency || 'daily')
    setWeekday(typeof data.weekday === 'number' ? data.weekday : 1)
  }

  useEffect(() => {
    let mounted = true
    getEmailDigestStatus()
      .then((data) => {
        if (mounted) applyStatus(data)
      })
      .catch(() => {
        toast.error('Could not load email digest settings')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const handleSubscribe = async () => {
    setSaving(true)
    try {
      const data = await optInToEmailDigest({
        locale,
        digest_time_local: digestTime,
        timezone,
        frequency,
        weekday,
      })
      applyStatus(data)
      toast.success('Job match emails are on')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not turn on job match emails')
    } finally {
      setSaving(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const data = await saveEmailDigestPreferences({
        locale,
        digest_time_local: digestTime,
        timezone,
        frequency,
        weekday,
      })
      applyStatus(data)
      toast.success('Email preferences saved')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not save preferences')
    } finally {
      setSaving(false)
    }
  }

  const handleOptOut = async () => {
    setSaving(true)
    try {
      await optOutOfEmailDigest()
      const data = await getEmailDigestStatus()
      applyStatus(data)
      toast.success('Job match emails turned off')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not turn off job match emails')
    } finally {
      setSaving(false)
    }
  }

  const handleTestSend = async () => {
    setTesting(true)
    try {
      const result = await sendTestEmailDigest()
      if (result.status === 'sent') {
        toast.success(`Sent ${result.jobs ?? 0} matches to your inbox`)
      } else if (result.status === 'duplicate') {
        toast.success('Today’s digest is already in your inbox')
      } else {
        toast(SKIP_REASONS[result.reason ?? ''] ?? 'Nothing to send right now')
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not send the test digest')
    } finally {
      setTesting(false)
    }
  }

  const localeOptions =
    status?.available_locales?.length ? status.available_locales : LOCALE_FALLBACK
  const isOn = Boolean(status?.email_opted_in)

  const inputClass =
    'w-full rounded-xl border border-neutral-200 px-4 py-2.5 text-sm focus:border-brand-turquoise-500 focus:outline-none focus:ring-2 focus:ring-brand-turquoise-100 transition-all duration-150 bg-white'

  return (
    <div className="card p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="stat-icon bg-indigo-50">
          <Mail className="h-5 w-5 text-indigo-600" />
        </div>
        <div>
          <h2 className="text-base font-bold text-neutral-900">Job match emails</h2>
          <p className="text-xs text-neutral-500">
            A digest of the roles that actually fit you, written in your language
          </p>
        </div>
      </div>

      {loading ? (
        <div className="h-36 rounded-xl bg-neutral-50 animate-pulse border border-neutral-100" />
      ) : (
        <div className="border-t border-neutral-100 pt-5 space-y-5">
          <div className="flex items-center justify-between gap-4 rounded-xl border border-neutral-200 p-4">
            <div>
              <div className="font-semibold text-neutral-900 text-sm">
                {isOn ? 'Job match emails are on' : 'Job match emails are off'}
              </div>
              <div className="text-xs text-neutral-500 mt-0.5">
                {isOn
                  ? `Going to ${status?.email_masked ?? 'your account email'}${
                      status?.last_sent_at
                        ? ` · last sent ${new Date(status.last_sent_at).toLocaleDateString()}`
                        : ''
                    }`
                  : 'We’ll only email you when there are roles worth your time.'}
              </div>
            </div>
            {isOn && (
              <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-2.5 py-1 flex-shrink-0">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Active
              </div>
            )}
          </div>

          {status?.suppressed && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-800">
              Earlier mail to this address bounced or was reported as spam, so we’ve
              stopped sending to it. Contact support to use a different address.
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Language
            </label>
            <div className="grid gap-2 sm:grid-cols-2">
              {localeOptions.map((option) => (
                <button
                  key={option.code}
                  type="button"
                  onClick={() => setLocale(option.code)}
                  className={`rounded-xl border px-4 py-2.5 text-sm font-semibold transition-all duration-150 cursor-pointer ${
                    locale === option.code
                      ? 'border-brand-turquoise-500 bg-brand-turquoise-50 text-brand-turquoise-700'
                      : 'border-neutral-200 text-neutral-700 hover:border-neutral-300'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <p className="mt-2.5 text-xs text-neutral-500 italic leading-relaxed">
              {LOCALE_PREVIEW[locale]}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                How often
              </label>
              <select
                aria-label="Email digest frequency"
                value={frequency}
                onChange={(e) => setFrequency(e.target.value as EmailFrequency)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="daily">Every day</option>
                <option value="weekly">Once a week</option>
              </select>
            </div>
            {frequency === 'weekly' && (
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Which day
                </label>
                <select
                  aria-label="Email digest weekday"
                  value={weekday}
                  onChange={(e) => setWeekday(Number(e.target.value))}
                  className={`${inputClass} cursor-pointer`}
                >
                  {WEEKDAYS.map((day) => (
                    <option key={day.value} value={day.value}>
                      {day.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-neutral-700 mb-2">
              <Clock className="h-4 w-4 text-neutral-400" />
              Send time
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                type="time"
                aria-label="Email digest time"
                value={digestTime}
                onChange={(e) => setDigestTime(e.target.value)}
                className={inputClass}
              />
              <select
                aria-label="Email digest timezone"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                {TIMEZONE_OPTIONS.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <button
              onClick={isOn ? handleSave : handleSubscribe}
              disabled={saving}
              className="inline-flex items-center justify-center rounded-xl bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-all duration-200 hover:shadow-md disabled:opacity-50 cursor-pointer"
            >
              {isOn ? 'Save preferences' : 'Turn on job match emails'}
            </button>
            {isOn && (
              <button
                onClick={handleTestSend}
                disabled={testing}
                className="inline-flex items-center gap-2 rounded-xl border border-neutral-200 px-5 py-2.5 text-sm font-semibold text-neutral-800 hover:bg-neutral-50 hover:border-neutral-300 transition-all duration-200 disabled:opacity-50 cursor-pointer"
              >
                <Send className="h-3.5 w-3.5" />
                {testing ? 'Sending…' : 'Send me one now'}
              </button>
            )}
            {isOn && (
              <button
                onClick={handleOptOut}
                disabled={saving}
                className="text-sm font-semibold text-rose-600 hover:text-rose-700 disabled:opacity-50 transition-colors cursor-pointer"
              >
                Turn off
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
