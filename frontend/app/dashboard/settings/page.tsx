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
import { Bell, CheckCircle2, Clock, MessageCircle, Shield, User } from 'lucide-react'
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

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-neutral-800 mb-2">
              Settings
            </h1>
            <p className="text-neutral-600">
              Manage your account settings and preferences
            </p>
          </div>

          {/* Settings Sections */}
          <div className="space-y-6">
            {/* Account Settings */}
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
              <div className="flex items-center space-x-3 mb-4">
                <User className="h-5 w-5 text-primary-600" />
                <h2 className="text-lg font-semibold text-neutral-800">
                  Account Settings
                </h2>
              </div>
              <p className="text-sm text-neutral-600 mb-4">
                Manage your account information and preferences
              </p>
              <div className="text-sm text-neutral-500">
                Coming soon
              </div>
            </div>

            {/* Notifications */}
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
              <div className="flex items-center space-x-3 mb-4">
                <Bell className="h-5 w-5 text-primary-600" />
                <h2 className="text-lg font-semibold text-neutral-800">
                  Notifications
                </h2>
              </div>
              {loading ? (
                <div className="h-36 rounded-md bg-neutral-100 animate-pulse" />
              ) : (
                <div className="space-y-5">
                  <div className="flex items-center justify-between gap-4 rounded-md border border-neutral-200 p-4">
                    <div className="flex items-start gap-3">
                      <MessageCircle className="h-5 w-5 text-emerald-600 mt-0.5" />
                      <div>
                        <div className="font-medium text-neutral-800">WhatsApp job alerts</div>
                        <div className="text-sm text-neutral-500">
                          {status?.whatsapp_opted_in
                            ? `Active for ${status.phone_masked ?? 'your verified number'}`
                            : 'Off'}
                        </div>
                      </div>
                    </div>
                    {status?.whatsapp_opted_in && (
                      <div className="inline-flex items-center gap-1.5 text-sm text-emerald-700">
                        <CheckCircle2 className="h-4 w-4" />
                        On
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
                        className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
                      />
                      <button
                        onClick={handleSendCode}
                        disabled={saving}
                        className="inline-flex items-center justify-center rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
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
                        className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
                      />
                      <button
                        onClick={handleVerify}
                        disabled={saving}
                        className="inline-flex items-center justify-center rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-800 hover:bg-neutral-50 disabled:opacity-50"
                      >
                        Verify
                      </button>
                    </div>
                  )}

                  <div className="grid gap-3 sm:grid-cols-[160px_1fr_auto]">
                    <label className="flex items-center gap-2 text-sm text-neutral-700">
                      <Clock className="h-4 w-4 text-neutral-500" />
                      Digest time
                    </label>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <input
                        type="time"
                        value={digestTime}
                        onChange={(e) => setDigestTime(e.target.value)}
                        className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
                      />
                      <select
                        value={timezone}
                        onChange={(e) => setTimezone(e.target.value)}
                        className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
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
                      className="inline-flex items-center justify-center rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-800 hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Save
                    </button>
                  </div>

                  {status?.whatsapp_opted_in && (
                    <button
                      onClick={handleOptOut}
                      disabled={saving}
                      className="text-sm font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
                    >
                      Turn off WhatsApp alerts
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Privacy & Security */}
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
              <div className="flex items-center space-x-3 mb-4">
                <Shield className="h-5 w-5 text-primary-600" />
                <h2 className="text-lg font-semibold text-neutral-800">
                  Privacy & Security
                </h2>
              </div>
              <p className="text-sm text-neutral-600 mb-4">
                Manage your privacy settings and security preferences
              </p>
              <div className="text-sm text-neutral-500">
                Coming soon
              </div>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
