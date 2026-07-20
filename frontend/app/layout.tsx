import type { Metadata } from 'next'
import { Inter, Fraunces } from 'next/font/google'
import './globals.css'
import { Toaster } from 'react-hot-toast'
import { Suspense } from 'react'
import { AnalyticsTracker } from '@/components/analytics/AnalyticsTracker'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

// Editorial display serif — used for all marketing headlines.
// Variable font: all weights 100–900 + italic are available via CSS.
const fraunces = Fraunces({
  subsets: ['latin'],
  variable: '--font-fraunces',
  style: ['normal', 'italic'],
  display: 'swap',
})

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'https://veloxahire.org'),
  title: 'AI Job Search & Personalized Job Matching | VeloxaHire',
  description:
    'Browse remote and recruiter-posted jobs, then use your CV and profile to find the roles most worth your time with VeloxaHire.',
  alternates: {
    canonical: '/',
  },
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon.ico',
    apple: '/logo.png',
  },
  openGraph: {
    type: 'website',
    siteName: 'VeloxaHire',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'VeloxaHire — AI job search and personalized job matching',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    images: ['/og-image.png'],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${fraunces.variable}`}
      suppressHydrationWarning
    >
      <body className="antialiased bg-cream-100 text-ink-900" suppressHydrationWarning>
        <Suspense fallback={null}><AnalyticsTracker /></Suspense>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#14201c',
              color: '#f5f0e7',
              border: '1px solid #26332e',
            },
            success: {
              iconTheme: {
                primary: '#06b6d4',
                secondary: '#f8fafc',
              },
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#f8fafc',
              },
            },
          }}
        />
      </body>
    </html>
  )
}
