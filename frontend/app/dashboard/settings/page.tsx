'use client'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { Settings, Bell, Shield, User } from 'lucide-react'

export default function SettingsPage() {
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
              <p className="text-sm text-neutral-600 mb-4">
                Configure how you receive notifications
              </p>
              <div className="text-sm text-neutral-500">
                Coming soon
              </div>
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

