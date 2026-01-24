'use client'

import { ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { useProfile } from '@/hooks/useProfile'
import { calculateProfileCompletion } from '@/lib/profile-utils'
import {
  Briefcase,
  User,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  Home,
} from 'lucide-react'
import { useState } from 'react'

interface DashboardLayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Jobs', href: '/dashboard/jobs', icon: Briefcase },
  { name: 'Applications', href: '/dashboard/applications', icon: FileText },
  { name: 'CV Management', href: '/dashboard/cv', icon: FileText },
  { name: 'Profile', href: '/dashboard/profile', icon: User },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
]

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const { profile } = useProfile()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const completionPercentage = calculateProfileCompletion(profile)

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-neutral-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo/Header */}
          <div className="flex items-center justify-between h-20 px-6 border-b border-neutral-100">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-brand-turquoise-600 rounded-lg flex items-center justify-center shadow-lg shadow-brand-turquoise-500/20">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-lg font-bold tracking-tight text-neutral-900">
                JobHunt<span className="text-brand-turquoise-600">Pro</span>
              </h1>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-neutral-500 hover:text-neutral-700"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Profile Summary */}
          <div className="px-6 py-6 border-b border-neutral-100">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 rounded-2xl bg-brand-turquoise-50 flex items-center justify-center border border-brand-turquoise-100">
                <User className="h-6 w-6 text-brand-turquoise-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-neutral-900 truncate">
                  {profile?.primary_job_title || 'Job Seeker'}
                </p>
                <p className="text-xs text-neutral-500 truncate font-medium">
                  {user?.email}
                </p>
              </div>
            </div>
            <div className="mt-5">
              {/* Profile Completion */}
              <div className="mb-4">
                <div className="flex items-center justify-between text-[10px] uppercase tracking-widest font-bold mb-2">
                  <span className="text-neutral-400">Profile Completion</span>
                  <span className="text-brand-turquoise-600">
                    {completionPercentage}%
                  </span>
                </div>
                <div className="w-full bg-neutral-100 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-brand-turquoise-500 h-1.5 rounded-full transition-all duration-500"
                    style={{ width: `${completionPercentage}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {profile?.seniority_level && (
                  <div className="px-2 py-1 bg-neutral-50 rounded-md border border-neutral-100">
                    <p className="text-[9px] text-neutral-400 uppercase font-bold">Level</p>
                    <p className="text-[10px] font-bold text-neutral-700 capitalize truncate">
                      {profile.seniority_level}
                    </p>
                  </div>
                )}
                {profile?.work_preference && (
                  <div className="px-2 py-1 bg-neutral-50 rounded-md border border-neutral-100">
                    <p className="text-[9px] text-neutral-400 uppercase font-bold">Type</p>
                    <p className="text-[10px] font-bold text-neutral-700 capitalize truncate">
                      {profile.work_preference}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center space-x-3 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
                    isActive
                      ? 'bg-brand-turquoise-600 text-white shadow-lg shadow-brand-turquoise-500/20'
                      : 'text-neutral-500 hover:bg-neutral-50 hover:text-brand-turquoise-600'
                  }`}
                >
                  <Icon className={`h-5 w-5 ${isActive ? 'text-white' : ''}`} />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </nav>

          {/* Logout */}
          <div className="px-4 py-4 border-t border-neutral-100">
            <button
              onClick={logout}
              className="flex items-center space-x-3 px-4 py-2.5 rounded-xl text-sm font-semibold text-neutral-500 hover:bg-red-50 hover:text-red-600 transition-colors w-full"
            >
              <LogOut className="h-5 w-5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-neutral-100">
          <div className="flex items-center justify-between h-20 px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-xl bg-neutral-50 text-neutral-500 hover:text-brand-turquoise-600 transition-colors"
            >
              <Menu className="h-6 w-6" />
            </button>
            <div className="flex-1" />
            <div className="flex items-center space-x-4">
              <div className="flex flex-col items-end hidden sm:flex">
                <span className="text-sm font-bold text-neutral-900 leading-none mb-1">
                  {profile?.primary_job_title || 'User'}
                </span>
                <span className="text-[10px] text-neutral-400 font-bold uppercase tracking-wider">
                  {user?.email}
                </span>
              </div>
              <div className="w-10 h-10 rounded-full bg-brand-turquoise-50 flex items-center justify-center border border-brand-turquoise-100">
                <User className="h-5 w-5 text-brand-turquoise-600" />
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8 bg-white min-h-[calc(100vh-5rem)]">{children}</main>
      </div>
    </div>
  )
}

