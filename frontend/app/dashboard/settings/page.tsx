'use client'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import {
  getWhatsappStatus,
  optOutWhatsapp,
  requestWhatsappOptIn,
  saveWhatsappPreferences,
  verifyWhatsappCode,
  type WhatsappStatus,
} from '@/lib/api/whatsapp'
import { deleteMyAccount, exportMyData } from '@/lib/api/users'
import { signOut } from '@/lib/auth'
import {
  Bell,
  CheckCircle2,
  Clock,
  Download,
  ExternalLink,
  MessageCircle,
  Shield,
  Trash2,
  User,
} from 'lucide-react'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

const TIMEZONE_OPTIONS = ['UTC', 'Africa/Accra', 'Europe/London', 'America/New_York']

export default function SettingsPage() {
  const [status, setStatus] = useState<WhatsappStatus | null>(null)
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [digestTime, setDigestTime] = useState('08:00')
  const [timezone, setTimezone] = useState('UTC')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [accountAction, setAccountAction] = useState<'export' | 'delete' | null>(null)
  const [verificationSent, setVerificationSent] = useState(false)

  useEffect(() => {
    let mounted = true
    getWhatsappStatus()
      .then((data) => {
        if (!mounted) return
        setStatus(data)
        setDigestTime(data.digest_time_local || '08:00')
        setTimezone(data.timezone || 'UTC')
      })
      .catch(() => {
        toast.error('Could not load notification settings')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const refreshStatus = async () => {
    const data = await getWhatsappStatus()
    setStatus(data)
    setDigestTime(data.digest_time_local || '08:00')
    setTimezone(data.timezone || 'UTC')
  }

  const handleSendCode = async () => {
    if (!phone.trim()) {
      toast.error('Enter a WhatsApp phone number')
      return
    }
    setSaving(true)
    try {
      await requestWhatsappOptIn(phone.trim())
      setVerificationSent(true)
      toast.success('Verification code sent')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not send code')
    } finally {
      setSaving(false)
    }
  }

  const handleVerify = async () => {
    if (!code.trim()) {
      toast.error('Enter the verification code')
      return
    }
    setSaving(true)
    try {
      await verifyWhatsappCode(code.trim())
      setCode('')
      setVerificationSent(false)
      await refreshStatus()
      toast.success('WhatsApp alerts are on')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not verify code')
    } finally {
      setSaving(false)
    }
  }

  const handleSavePreferences = async () => {
    setSaving(true)
    try {
      await saveWhatsappPreferences({
        digest_time_local: digestTime,
        timezone,
      })
      await refreshStatus()
      toast.success('Notification preferences saved')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not save preferences')
    } finally {
      setSaving(false)
    }
  }

  const handleOptOut = async () => {
    setSaving(true)
    try {
      await optOutWhatsapp()
      await refreshStatus()
      toast.success('WhatsApp alerts turned off')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not opt out')
    } finally {
      setSaving(false)
    }
  }

  const handleExportData = async () => {
    setAccountAction('export')
    try {
      const data = await exportMyData()
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `veloxahire-data-export-${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
      toast.success('Data export downloaded')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not export your data')
    } finally {
      setAccountAction(null)
    }
  }

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm(
      'Delete your VeloxaHire account data? This removes your profile, CVs, applications, recommendations, external jobs, and notification data. This cannot be undone.'
    )
    if (!confirmed) return

    setAccountAction('delete')
    try {
      const response = await deleteMyAccount()
      if (response.warning) {
        toast.error(response.warning)
      } else {
        toast.success('Account data deleted')
      }
      await signOut().catch(() => undefined)
      window.location.href = '/'
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not delete your account')
      setAccountAction(null)
    }
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold text-neutral-900 tracking-tight mb-1.5">
              Settings
            </h1>
            <p className="text-sm text-neutral-500 leading-relaxed">
              Manage your account settings and notification preferences
            </p>
          </div>

          {/* Settings Sections */}
          <div className="space-y-6">
            {/* Account Settings */}
            <div className="card p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="stat-icon bg-brand-turquoise-50">
                  <User className="h-5 w-5 text-brand-turquoise-600" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-neutral-900">
                    Account Settings
                  </h2>
                  <p className="text-xs text-neutral-500">
                    Manage your account information and preferences
                  </p>
                </div>
              </div>
              <div className="border-t border-neutral-100 pt-5">
                <div className="flex items-center gap-4 p-4 rounded-xl bg-neutral-50 border border-neutral-100">
                  <div className="w-10 h-10 rounded-xl bg-white border border-neutral-200 flex items-center justify-center">
                    <User className="h-4 w-4 text-neutral-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-700">Profile management</p>
                    <p className="text-xs text-neutral-500">Update your name, email, and password settings</p>
                  </div>
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-brand-turquoise-600 bg-brand-turquoise-50 border border-brand-turquoise-100 rounded-lg px-2.5 py-1">
                    Soon
                  </span>
                </div>
              </div>
            </div>

            {/* Notifications */}
            <div className="card p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="stat-icon bg-amber-50">
                  <Bell className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-neutral-900">
                    Notifications
                  </h2>
                  <p className="text-xs text-neutral-500">
                    Configure how you receive job alerts and updates
                  </p>
                </div>
              </div>
              {loading ? (
                <div className="h-36 rounded-xl bg-neutral-50 animate-pulse border border-neutral-100" />
              ) : (
                <div className="border-t border-neutral-100 pt-5 space-y-5">
                  <div className="flex items-center justify-between gap-4 rounded-xl border border-neutral-200 p-4 hover:border-neutral-300 transition-colors">
                    <div className="flex items-start gap-3">
                      <div className="stat-icon bg-emerald-50 flex-shrink-0 mt-0.5">
                        <MessageCircle className="h-5 w-5 text-emerald-600" />
                      </div>
                      <div>
                        <div className="font-semibold text-neutral-900 text-sm">WhatsApp job alerts</div>
                        <div className="text-xs text-neutral-500 mt-0.5">
                          {status?.whatsapp_opted_in
                            ? `Active for ${status.phone_masked ?? 'your verified number'}`
                            : 'Get daily job digests delivered to your WhatsApp'}
                        </div>
                      </div>
                    </div>
                    {status?.whatsapp_opted_in && (
                      <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-2.5 py-1">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Active
                      </div>
                    )}
                  </div>

                  {!status?.whatsapp_opted_in && (
                    <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
                      <input
                        type="tel"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        placeholder="+233241234567"
                        className="w-full rounded-xl border border-neutral-200 px-4 py-2.5 text-sm focus:border-brand-turquoise-500 focus:outline-none focus:ring-2 focus:ring-brand-turquoise-100 transition-all duration-150 bg-white"
                      />
                      <button
                        onClick={handleSendCode}
                        disabled={saving}
                        className="inline-flex items-center justify-center rounded-xl bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-all duration-200 hover:shadow-md disabled:opacity-50 cursor-pointer"
                      >
                        Send code
                      </button>
                    </div>
                  )}

                  {verificationSent && !status?.whatsapp_opted_in && (
                    <div className="grid gap-3 sm:grid-cols-[180px_auto]">
                      <input
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        inputMode="numeric"
                        maxLength={6}
                        placeholder="6-digit code"
                        className="w-full rounded-xl border border-neutral-200 px-4 py-2.5 text-sm focus:border-brand-turquoise-500 focus:outline-none focus:ring-2 focus:ring-brand-turquoise-100 transition-all duration-150 bg-white"
                      />
                      <button
                        onClick={handleVerify}
                        disabled={saving}
                        className="inline-flex items-center justify-center rounded-xl border border-neutral-200 px-5 py-2.5 text-sm font-semibold text-neutral-800 hover:bg-neutral-50 hover:border-neutral-300 transition-all duration-200 disabled:opacity-50 cursor-pointer"
                      >
                        Verify
                      </button>
                    </div>
                  )}

                  <div className="grid gap-3 sm:grid-cols-[160px_1fr_auto] items-center">
                    <label className="flex items-center gap-2 text-sm font-medium text-neutral-700">
                      <Clock className="h-4 w-4 text-neutral-400" />
                      Digest time
                    </label>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <input
                        type="time"
                        value={digestTime}
                        onChange={(e) => setDigestTime(e.target.value)}
                        className="w-full rounded-xl border border-neutral-200 px-4 py-2.5 text-sm focus:border-brand-turquoise-500 focus:outline-none focus:ring-2 focus:ring-brand-turquoise-100 transition-all duration-150 bg-white"
                      />
                      <select
                        value={timezone}
                        onChange={(e) => setTimezone(e.target.value)}
                        className="w-full rounded-xl border border-neutral-200 px-4 py-2.5 text-sm focus:border-brand-turquoise-500 focus:outline-none focus:ring-2 focus:ring-brand-turquoise-100 transition-all duration-150 bg-white cursor-pointer"
                      >
                        {TIMEZONE_OPTIONS.map((tz) => (
                          <option key={tz} value={tz}>
                            {tz}
                          </option>
                        ))}
                      </select>
                    </div>
                    <button
                      onClick={handleSavePreferences}
                      disabled={saving}
                      className="inline-flex items-center justify-center rounded-xl border border-neutral-200 px-5 py-2.5 text-sm font-semibold text-neutral-800 hover:bg-neutral-50 hover:border-neutral-300 transition-all duration-200 disabled:opacity-50 cursor-pointer"
                    >
                      Save
                    </button>
                  </div>

                  {status?.whatsapp_opted_in && (
                    <button
                      onClick={handleOptOut}
                      disabled={saving}
                      className="text-sm font-semibold text-rose-600 hover:text-rose-700 disabled:opacity-50 transition-colors cursor-pointer"
                    >
                      Turn off WhatsApp alerts
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Privacy & Security */}
            <div className="card p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="stat-icon bg-blue-50">
                  <Shield className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-neutral-900">
                    Privacy & Security
                  </h2>
                  <p className="text-xs text-neutral-500">
                    Manage your privacy settings and data
                  </p>
                </div>
              </div>
              <div className="border-t border-neutral-100 pt-5 space-y-3">
                <div className="flex flex-col gap-4 p-4 rounded-xl bg-neutral-50 border border-neutral-100 sm:flex-row sm:items-center">
                  <div className="w-10 h-10 rounded-xl bg-white border border-neutral-200 flex items-center justify-center">
                    <Shield className="h-4 w-4 text-neutral-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-700">Data export & deletion</p>
                    <p className="text-xs text-neutral-500">Download your candidate data or permanently delete your account data</p>
                  </div>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <button
                      type="button"
                      onClick={handleExportData}
                      disabled={accountAction !== null}
                      className="inline-flex items-center justify-center gap-2 rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-sm font-semibold text-neutral-800 hover:bg-neutral-50 hover:border-neutral-300 transition-all duration-200 disabled:opacity-50"
                    >
                      <Download className="h-4 w-4" />
                      {accountAction === 'export' ? 'Exporting' : 'Export'}
                    </button>
                    <button
                      type="button"
                      onClick={handleDeleteAccount}
                      disabled={accountAction !== null}
                      className="inline-flex items-center justify-center gap-2 rounded-xl border border-rose-200 bg-white px-4 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-50 transition-all duration-200 disabled:opacity-50"
                    >
                      <Trash2 className="h-4 w-4" />
                      {accountAction === 'delete' ? 'Deleting' : 'Delete'}
                    </button>
                  </div>
                </div>
                <div className="flex flex-col gap-4 p-4 rounded-xl bg-neutral-50 border border-neutral-100 sm:flex-row sm:items-center">
                  <div className="w-10 h-10 rounded-xl bg-white border border-neutral-200 flex items-center justify-center">
                    <Bell className="h-4 w-4 text-neutral-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-700">Legal notices</p>
                    <p className="text-xs text-neutral-500">Review how VeloxaHire handles candidate data</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link
                      href="/privacy"
                      className="inline-flex items-center justify-center gap-2 rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-sm font-semibold text-neutral-800 hover:bg-neutral-50 hover:border-neutral-300 transition-all duration-200"
                    >
                      Privacy
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                    <Link
                      href="/terms"
                      className="inline-flex items-center justify-center gap-2 rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-sm font-semibold text-neutral-800 hover:bg-neutral-50 hover:border-neutral-300 transition-all duration-200"
                    >
                      Terms
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
