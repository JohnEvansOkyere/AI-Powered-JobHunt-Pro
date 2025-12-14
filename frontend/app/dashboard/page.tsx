'use client'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { useAuth } from '@/hooks/useAuth'

export default function DashboardPage() {
  const { user, logout } = useAuth()

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50">
        <nav className="bg-white shadow-sm border-b border-neutral-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-bold text-primary-700">
                  AI Job Platform
                </h1>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-neutral-600">
                  {user?.email}
                </span>
                <button
                  onClick={logout}
                  className="px-4 py-2 text-sm font-medium text-neutral-700 hover:text-neutral-900"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-neutral-800 mb-4">
              Welcome to your Dashboard
            </h2>
            <p className="text-neutral-600">
              Your job application platform is ready. Complete your profile to get started.
            </p>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}

