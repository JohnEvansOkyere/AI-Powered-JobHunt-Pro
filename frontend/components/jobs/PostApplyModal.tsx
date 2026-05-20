'use client'

import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
import { X, Sparkles, Bell, BarChart2, BookmarkCheck } from 'lucide-react'

interface PostApplyModalProps {
  open: boolean
  onClose: () => void
}

const VALUE_PROPS = [
  {
    icon: Sparkles,
    title: 'AI-matched roles, just for you',
    body: 'Our AI reads your profile and ranks every job by how well it fits — no more scrolling through irrelevant listings.',
  },
  {
    icon: BarChart2,
    title: 'See your match score on every job',
    body: 'Know at a glance whether a role is a strong fit or a stretch, before you spend time applying.',
  },
  {
    icon: Bell,
    title: 'Get notified when new matches arrive',
    body: 'New recruiter jobs and scraped listings are checked every few hours. You hear about the right ones first.',
  },
  {
    icon: BookmarkCheck,
    title: 'Track every application in one place',
    body: 'Save jobs, mark applications, and keep a clear picture of where you stand — all in your dashboard.',
  },
]

export function PostApplyModal({ open, onClose }: PostApplyModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-neutral-900/60 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 32, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.97 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="fixed inset-x-4 bottom-0 sm:inset-auto sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 z-50 w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Top accent bar */}
            <div className="h-1 w-full bg-gradient-to-r from-brand-turquoise-400 to-brand-turquoise-600" />

            <div className="px-6 pt-6 pb-7">
              {/* Header */}
              <div className="flex items-start justify-between gap-3 mb-1">
                <h2 className="text-lg font-semibold text-neutral-900 leading-snug">
                  Find more roles like this one
                </h2>
                <button
                  onClick={onClose}
                  className="p-1 -mr-1 text-neutral-400 hover:text-neutral-700 transition-colors rounded-md hover:bg-neutral-100 flex-shrink-0"
                  aria-label="Close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <p className="text-sm text-neutral-500 mb-6">
                Create a free account and let AI do the job hunting for you.
              </p>

              {/* Value props */}
              <ul className="space-y-4 mb-7">
                {VALUE_PROPS.map(({ icon: Icon, title, body }) => (
                  <li key={title} className="flex gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-brand-turquoise-50 flex items-center justify-center">
                      <Icon className="w-4 h-4 text-brand-turquoise-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-neutral-900">{title}</p>
                      <p className="text-xs text-neutral-500 mt-0.5 leading-relaxed">{body}</p>
                    </div>
                  </li>
                ))}
              </ul>

              {/* CTAs */}
              <div className="flex flex-col gap-2">
                <Link
                  href="/auth/signup"
                  className="w-full inline-flex items-center justify-center px-4 py-2.5 bg-brand-turquoise-600 hover:bg-brand-turquoise-700 text-white text-sm font-semibold rounded-xl transition-colors"
                >
                  Create free account
                </Link>
                <button
                  onClick={onClose}
                  className="w-full px-4 py-2.5 text-sm font-medium text-neutral-500 hover:text-neutral-800 transition-colors"
                >
                  Maybe later
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
