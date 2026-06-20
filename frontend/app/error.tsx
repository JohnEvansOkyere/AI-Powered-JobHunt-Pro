'use client'

import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function Error({
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <main className="min-h-screen bg-cream-100 text-ink-900 flex items-center justify-center px-6">
      <section className="w-full max-w-md border border-neutral-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-md bg-red-50 text-red-600">
          <AlertTriangle className="h-5 w-5" aria-hidden="true" />
        </div>
        <h1 className="text-xl font-semibold">Something went wrong</h1>
        <p className="mt-2 text-sm leading-6 text-neutral-600">
          The page could not finish loading. Try again, or return to the dashboard.
        </p>
        <div className="mt-6 flex gap-3">
          <Button type="button" onClick={reset} className="gap-2">
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Retry
          </Button>
          <Button asChild variant="outline">
            <a href="/dashboard">Dashboard</a>
          </Button>
        </div>
      </section>
    </main>
  )
}
