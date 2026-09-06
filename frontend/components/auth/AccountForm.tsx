'use client'

import Link from 'next/link'
import PublicHeader from '@/components/layout/PublicHeader'
import AuthBrandPanel from '@/components/auth/AuthBrandPanel'

export const accountInput = 'block w-full rounded-xl border border-neutral-200 bg-white px-4 py-3.5 text-sm text-neutral-900 outline-none focus:border-brand-turquoise-500 focus:ring-2 focus:ring-brand-turquoise-500/20'
export const accountButton = 'inline-flex w-full items-center justify-center rounded-xl bg-brand-turquoise-600 py-3.5 text-sm font-semibold text-white hover:bg-brand-turquoise-700 disabled:opacity-60'
export const accountLabel = 'mb-1.5 block text-sm font-medium text-neutral-700'

export function AccountForm({ title, description, children, variant = 'signup' }: {
  title: string; description: string; children: React.ReactNode; variant?: 'signup' | 'login'
}) {
  return <div className="vh-auth">
    <PublicHeader />
    <main id="main-content" className="vh-auth-body">
      <AuthBrandPanel variant={variant} />
      <div className="vh-auth-form"><div className="mx-auto w-full max-w-[440px]">
        <h1 className="text-3xl font-bold tracking-tight text-neutral-900">{title}</h1>
        <p className="mt-2 text-neutral-500">{description}</p>
        {children}
        <div className="mt-8 flex flex-wrap gap-4 justify-between border-t border-neutral-200 pt-6 text-sm text-neutral-500">
          <Link href={variant === 'login' ? '/auth/signup' : '/auth/login'} className="font-semibold text-brand-turquoise-700">
            {variant === 'login' ? 'Create a free account' : 'Already a member? Sign in'}
          </Link>
          <Link href="/jobs">Browse jobs →</Link>
        </div>
      </div></div>
    </main>
  </div>
}
