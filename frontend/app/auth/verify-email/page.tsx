'use client'

import Link from 'next/link'

export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-secondary-50 px-4">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-2xl shadow-xl text-center">
        <div className="flex justify-center">
          <div className="h-16 w-16 rounded-full bg-accent-100 flex items-center justify-center">
            <svg className="h-8 w-8 text-accent-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
        <div>
          <h2 className="text-2xl font-bold text-neutral-800">
            Check your email
          </h2>
          <p className="mt-2 text-sm text-neutral-600">
            We've sent a verification link to your email address. Please click the link to verify your account.
          </p>
        </div>
        <div className="space-y-4">
          <Link
            href="/auth/login"
            className="block w-full py-2 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-primary-700 hover:bg-primary-800"
          >
            Back to Login
          </Link>
        </div>
      </div>
    </div>
  )
}

