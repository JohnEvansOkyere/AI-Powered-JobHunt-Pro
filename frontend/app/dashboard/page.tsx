'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { useProfile } from '@/hooks/useProfile'
import Link from 'next/link'
import { Briefcase, FileText, User, Sparkles, ArrowRight } from 'lucide-react'

export default function DashboardPage() {
  const { profile, loading: profileLoading } = useProfile()
  const router = useRouter()

  useEffect(() => {
    // Only redirect if profile loading is complete AND profile is null
    if (!profileLoading && !profile) {
      const timer = setTimeout(() => {
        if (!profile) {
          router.push('/profile/setup')
        }
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [profile, profileLoading, router])

  if (profileLoading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-700"></div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (!profile) {
    return null // Will redirect
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-7xl mx-auto">
          {/* Welcome Section */}
          <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 mb-6">
            <h2 className="text-2xl font-bold text-neutral-800 mb-2">
              Welcome back, {profile.primary_job_title || 'Job Seeker'}!
            </h2>
            <p className="text-neutral-600">
              Your profile is set up. Start finding your dream job!
            </p>
          </div>

          {/* Profile Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
              <h3 className="text-sm font-medium text-neutral-500 mb-2">
                Job Title
              </h3>
              <p className="text-lg font-semibold text-neutral-800">
                {profile.primary_job_title || 'Not set'}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
              <h3 className="text-sm font-medium text-neutral-500 mb-2">
                Seniority
              </h3>
              <p className="text-lg font-semibold text-neutral-800 capitalize">
                {profile.seniority_level || 'Not set'}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
              <h3 className="text-sm font-medium text-neutral-500 mb-2">
                Work Preference
              </h3>
              <p className="text-lg font-semibold text-neutral-800 capitalize">
                {profile.work_preference || 'Not set'}
              </p>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Link
              href="/dashboard/jobs"
              className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 hover:shadow-md transition-shadow group"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-primary-100 rounded-lg">
                  <Briefcase className="h-6 w-6 text-primary-700" />
                </div>
                <ArrowRight className="h-5 w-5 text-neutral-400 group-hover:text-primary-600 transition-colors" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-800 mb-2">
                Job Recommendations
              </h3>
              <p className="text-sm text-neutral-600">
                Discover AI-matched jobs based on your profile
              </p>
            </Link>

            <Link
              href="/dashboard/applications"
              className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 hover:shadow-md transition-shadow group"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <FileText className="h-6 w-6 text-blue-700" />
                </div>
                <ArrowRight className="h-5 w-5 text-neutral-400 group-hover:text-blue-600 transition-colors" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-800 mb-2">
                My Applications
              </h3>
              <p className="text-sm text-neutral-600">
                View and manage your job applications
              </p>
            </Link>

            <Link
              href="/profile/setup"
              className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 hover:shadow-md transition-shadow group"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-green-100 rounded-lg">
                  <User className="h-6 w-6 text-green-700" />
                </div>
                <ArrowRight className="h-5 w-5 text-neutral-400 group-hover:text-green-600 transition-colors" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-800 mb-2">
                Edit Profile
              </h3>
              <p className="text-sm text-neutral-600">
                Update your profile information and preferences
              </p>
            </Link>

            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 opacity-50">
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <Sparkles className="h-6 w-6 text-purple-700" />
                </div>
              </div>
              <h3 className="text-lg font-semibold text-neutral-800 mb-2">
                Upload CV
              </h3>
              <p className="text-sm text-neutral-600">Coming soon</p>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

