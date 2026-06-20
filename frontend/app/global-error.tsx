'use client'

import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html lang="en">
      <body>
        <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24 }}>
          <section style={{ maxWidth: 420, border: '1px solid #ddd', padding: 24, fontFamily: 'sans-serif' }}>
            <AlertTriangle aria-hidden="true" />
            <h1>Something went wrong</h1>
            <p>The application could not finish loading.</p>
            <button type="button" onClick={reset}>
              <RefreshCw aria-hidden="true" />
              Retry
            </button>
          </section>
        </main>
      </body>
    </html>
  )
}
