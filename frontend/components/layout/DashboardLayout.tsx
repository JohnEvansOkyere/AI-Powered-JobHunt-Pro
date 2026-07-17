'use client'

import { ReactNode, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
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
  Briefcase,
} from 'lucide-react'

interface DashboardLayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Job Match', href: '/dashboard/recommendations', icon: Star },
  { name: 'All Jobs', href: '/dashboard/jobs', icon: Briefcase },
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
  const candidateName = String(
    user?.user_metadata?.full_name ||
    user?.user_metadata?.name ||
    user?.user_metadata?.display_name ||
    'Candidate'
  )
  const initials = candidateName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase() || 'U'

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
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-white/95 backdrop-blur-sm border-r border-neutral-200/80 shadow-lg transform transition-transform duration-200 ease-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo / header */}
          <div className="flex items-center justify-between h-16 px-6 border-b border-neutral-100">
            <Link href="/dashboard" className="flex items-center gap-2.5 group">
              <Image
                src="/logo.png"
                alt="VeloxaHire"
                width={30}
                height={30}
                priority
                className="object-contain transition-transform duration-200 group-hover:scale-105"
              />
              <span className="text-base font-semibold tracking-tight text-neutral-900">
                Veloxa<span className="text-brand-turquoise-600">Hire</span>
              </span>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-neutral-500 hover:text-neutral-900 p-1.5 rounded-md hover:bg-neutral-100 transition-colors cursor-pointer"
              aria-label="Close sidebar"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Profile summary */}
          <div className="px-4 py-5 border-b border-neutral-100">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brand-turquoise-400 to-brand-turquoise-600 p-[2px]">
                  <div className="w-full h-full rounded-full bg-white flex items-center justify-center font-semibold text-sm text-brand-turquoise-700">
                    {initials}
                  </div>
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-neutral-900 truncate">
                  {profile?.primary_job_title || 'Job seeker'}
                </p>
                <p className="text-xs text-neutral-500 truncate">
                  {candidateName}
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
                  className="bg-gradient-to-r from-brand-turquoise-400 to-brand-turquoise-600 h-full rounded-full transition-all duration-700 ease-out"
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
                  className={`relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ease-out ${
                    isActive
                      ? 'bg-brand-turquoise-50 text-brand-turquoise-700 shadow-sm'
                      : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                  }`}
                >
                  {isActive && (
                    <span className="nav-active-bar" />
                  )}
                  <Icon
                    className={`h-[18px] w-[18px] flex-shrink-0 transition-colors duration-150 ${
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
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-neutral-500 hover:bg-red-50 hover:text-red-600 transition-all duration-150 w-full cursor-pointer"
            >
              <LogOut className="h-[18px] w-[18px] flex-shrink-0" />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-72">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-neutral-100/80">
          <div className="flex items-center justify-between h-14 px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1.5 rounded-md text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 transition-colors cursor-pointer"
              aria-label="Open sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex-1" />
            <div className="flex items-center gap-3">
              <span className="hidden sm:block text-sm text-neutral-500">
                {candidateName}
              </span>
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-turquoise-400 to-brand-turquoise-600 p-[1.5px]">
                <div className="w-full h-full rounded-full bg-white flex items-center justify-center font-semibold text-xs text-brand-turquoise-700">
                  {initials}
                </div>
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
