'use client'

import { ReactNode, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { useProfile } from '@/hooks/useProfile'
import { calculateProfileCompletion } from '@/lib/profile-utils'
import {
  User,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  Home,
  Star,
} from 'lucide-react'

interface DashboardLayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Jobs', href: '/dashboard/recommendations', icon: Star },
  { name: 'Applications', href: '/dashboard/applications', icon: FileText },
  { name: 'Profile', href: '/dashboard/profile', icon: User },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
]

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const { profile } = useProfile()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const completionPercentage = calculateProfileCompletion(profile)
  const initials = (user?.email?.[0] || 'U').toUpperCase()

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-neutral-900/30 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-white border-r border-neutral-200 transform transition-transform duration-200 ease-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo / header */}
          <div className="flex items-center justify-between h-16 px-6 border-b border-neutral-100">
            <Link href="/dashboard" className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-lg bg-brand-turquoise-600 flex items-center justify-center">
                <span className="text-white text-sm font-semibold">J</span>
              </div>
              <span className="text-base font-semibold tracking-tight text-neutral-900">
                JobHunt<span className="text-brand-turquoise-600">Pro</span>
              </span>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-neutral-500 hover:text-neutral-900 p-1.5 rounded-md hover:bg-neutral-100 transition-colors"
              aria-label="Close sidebar"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Profile summary */}
          <div className="px-4 py-5 border-b border-neutral-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-brand-turquoise-50 text-brand-turquoise-700 flex items-center justify-center font-semibold text-sm border border-brand-turquoise-100">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-neutral-900 truncate">
                  {profile?.primary_job_title || 'Job seeker'}
                </p>
                <p className="text-xs text-neutral-500 truncate">
                  {user?.email}
                </p>
              </div>
            </div>

            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-neutral-500 mb-1.5">
                <span>Profile completion</span>
                <span className="font-medium text-neutral-900">{completionPercentage}%</span>
              </div>
              <div className="w-full bg-neutral-100 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-brand-turquoise-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${completionPercentage}%` }}
                />
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive =
                item.href === '/dashboard'
                  ? pathname === '/dashboard'
                  : pathname === item.href || pathname.startsWith(item.href + '/')
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-turquoise-50 text-brand-turquoise-700'
                      : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                  }`}
                >
                  <Icon
                    className={`h-4 w-4 flex-shrink-0 ${
                      isActive ? 'text-brand-turquoise-600' : 'text-neutral-400'
                    }`}
                  />
                  <span className="truncate">{item.name}</span>
                </Link>
              )
            })}
          </nav>

          {/* Logout */}
          <div className="px-3 py-3 border-t border-neutral-100">
            <button
              onClick={logout}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900 transition-colors w-full"
            >
              <LogOut className="h-4 w-4 flex-shrink-0 text-neutral-400" />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-72">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-sm border-b border-neutral-100">
          <div className="flex items-center justify-between h-14 px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1.5 rounded-md text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
              aria-label="Open sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex-1" />
            <div className="flex items-center gap-3">
              <span className="hidden sm:block text-sm text-neutral-500">
                {user?.email}
              </span>
              <div className="w-8 h-8 rounded-full bg-brand-turquoise-50 text-brand-turquoise-700 flex items-center justify-center font-semibold text-xs border border-brand-turquoise-100">
                {initials}
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="px-4 sm:px-6 lg:px-8 py-6 sm:py-8 bg-neutral-50 min-h-[calc(100vh-3.5rem)]">
          {children}
        </main>
      </div>
    </div>
  )
}
