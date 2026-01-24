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
  Sparkles,
  PlusCircle,
  Zap,
} from 'lucide-react'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface DashboardLayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Jobs', href: '/dashboard/jobs', icon: Briefcase },
  { name: 'My External Jobs', href: '/dashboard/external-jobs', icon: PlusCircle },
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
    <div className="min-h-screen bg-white">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-neutral-900/20 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-80 sm:w-72 bg-white border-r border-neutral-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo/Header */}
          <div className="flex items-center justify-between h-16 sm:h-20 px-6 sm:px-8 border-b border-neutral-100">
            <div className="flex items-center space-x-3 sm:space-x-4">
              <div className="w-9 h-9 sm:w-10 sm:h-10 bg-brand-turquoise-600 rounded-xl flex items-center justify-center shadow-lg shadow-brand-turquoise-500/20">
                <Sparkles className="h-5 w-5 sm:h-6 sm:w-6 text-white" />
              </div>
              <h1 className="text-lg sm:text-xl font-black tracking-tight text-neutral-900">
                JobHunt<span className="text-brand-turquoise-600">Pro</span>
              </h1>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-neutral-500 hover:text-neutral-700 p-2 hover:bg-neutral-100 rounded-lg transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Profile Summary */}
          <div className="px-6 sm:px-8 py-6 sm:py-8 border-b border-neutral-100 bg-neutral-50/30">
            <div className="flex items-center space-x-3 sm:space-x-4">
              <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-brand-turquoise-50 flex items-center justify-center border border-brand-turquoise-100 shadow-sm">
                <User className="h-6 w-6 sm:h-7 sm:w-7 text-brand-turquoise-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm sm:text-base font-black text-neutral-900 truncate">
                  {profile?.primary_job_title || 'Job Seeker'}
                </p>
                <p className="text-xs sm:text-sm text-neutral-500 truncate font-bold">
                  {user?.email}
                </p>
              </div>
            </div>
            <div className="mt-5 sm:mt-6">
              {/* Profile Completion */}
              <div className="mb-3 sm:mb-4">
                <div className="flex items-center justify-between text-[10px] sm:text-[11px] uppercase tracking-widest font-black mb-2">
                  <span className="text-neutral-400">Profile Completion</span>
                  <span className="text-brand-turquoise-600">
                    {completionPercentage}%
                  </span>
                </div>
                <div className="w-full bg-neutral-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-brand-turquoise-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${completionPercentage}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {profile?.seniority_level && (
                  <div className="px-2.5 sm:px-3 py-1.5 bg-white rounded-lg border border-neutral-100 shadow-sm">
                    <p className="text-[9px] sm:text-[10px] text-neutral-400 uppercase font-black">Level</p>
                    <p className="text-[10px] sm:text-[11px] font-bold text-neutral-700 capitalize truncate">
                      {profile.seniority_level}
                    </p>
                  </div>
                )}
                {profile?.work_preference && (
                  <div className="px-2.5 sm:px-3 py-1.5 bg-white rounded-lg border border-neutral-100 shadow-sm">
                    <p className="text-[9px] sm:text-[10px] text-neutral-400 uppercase font-black">Type</p>
                    <p className="text-[10px] sm:text-[11px] font-bold text-neutral-700 capitalize truncate">
                      {profile.work_preference}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 sm:px-4 py-6 sm:py-8 space-y-1.5 sm:space-y-2 overflow-y-auto custom-scrollbar">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href
              const isExternalJobs = item.href === '/dashboard/external-jobs'

              if (isExternalJobs) {
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`group relative flex items-center space-x-3 px-3.5 sm:px-4 py-3 sm:py-3.5 rounded-xl sm:rounded-2xl text-[15px] sm:text-base font-bold transition-all duration-300 active:scale-95 ${
                      isActive
                        ? 'bg-gradient-to-r from-brand-orange-500 to-brand-orange-600 text-white shadow-xl shadow-brand-orange-500/40'
                        : 'bg-brand-orange-50/50 text-brand-orange-600 border border-dashed border-brand-orange-200 hover:bg-brand-orange-50 hover:border-brand-orange-400'
                    }`}
                  >
                    <Icon className={`h-5 w-5 flex-shrink-0 ${isActive ? 'text-white' : 'text-brand-orange-500'} group-hover:rotate-12 transition-transform duration-300`} />
                    <span className="flex-1 truncate">{item.name}</span>
                    {!isActive && (
                      <Sparkles className="h-4 w-4 flex-shrink-0 text-brand-orange-400 animate-pulse" />
                    )}
                  </Link>
                )
              }

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center space-x-3 px-3.5 sm:px-4 py-3 rounded-xl text-[15px] sm:text-base font-bold transition-all duration-300 active:scale-95 ${
                    isActive
                      ? 'bg-brand-turquoise-600 text-white shadow-lg shadow-brand-turquoise-500/20'
                      : 'text-neutral-500 hover:bg-neutral-50 hover:text-brand-turquoise-600'
                  }`}
                >
                  <Icon className={`h-5 w-5 flex-shrink-0 ${isActive ? 'text-white' : 'group-hover:text-brand-turquoise-600'} transition-colors`} />
                  <span className="truncate">{item.name}</span>
                </Link>
              )
            })}
          </nav>

          {/* Logout */}
          <div className="px-3 sm:px-4 py-4 border-t border-neutral-100">
            <button
              onClick={logout}
              className="flex items-center space-x-3 px-3.5 sm:px-4 py-3 rounded-xl text-[15px] sm:text-base font-bold text-neutral-500 hover:bg-red-50 hover:text-red-600 transition-all duration-300 w-full group active:scale-95"
            >
              <LogOut className="h-5 w-5 flex-shrink-0 group-hover:scale-110 transition-transform" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-72">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-neutral-100">
          <div className="flex items-center justify-between h-16 sm:h-20 px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-xl bg-neutral-50 text-neutral-500 hover:text-brand-turquoise-600 transition-colors active:scale-95"
            >
              <Menu className="h-6 w-6" />
            </button>
            <div className="flex-1" />
            <div className="flex items-center space-x-3 sm:space-x-4">
              <div className="flex flex-col items-end hidden sm:flex">
                <span className="text-sm sm:text-base font-black text-neutral-900 leading-none mb-1">
                  {profile?.primary_job_title || 'User'}
                </span>
                <span className="text-[10px] sm:text-xs text-neutral-400 font-bold uppercase tracking-wider">
                  {user?.email}
                </span>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-brand-turquoise-50 flex items-center justify-center border border-brand-turquoise-100 shadow-sm">
                <User className="h-5 w-5 sm:h-6 sm:w-6 text-brand-turquoise-600" />
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8 bg-white min-h-[calc(100vh-4rem)] sm:min-h-[calc(100vh-5rem)]">{children}</main>
      </div>
    </div>
  )
}

