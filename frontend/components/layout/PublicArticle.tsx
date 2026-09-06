import type { ReactNode } from 'react'
import Link from 'next/link'
import PublicHeader from './PublicHeader'
import PublicFooter from './PublicFooter'

export default function PublicArticle({ title, intro, children }: { title: string; intro: string; children: ReactNode }) {
  return (
    <div className="vh-site"><PublicHeader />
      <main id="main-content" className="mx-auto max-w-3xl px-6 py-12 sm:py-16">
        <Link href="/" className="text-sm font-semibold text-forest-700">VeloxaHire</Link>
        <h1 className="mt-5 font-display text-4xl leading-tight sm:text-5xl">{title}</h1>
        <p className="mt-6 text-lg leading-8 text-ink-700">{intro}</p>
        <div className="mt-10 space-y-9 text-base leading-8 text-ink-700 [&_h2]:mb-3 [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:text-ink-900 [&_a]:text-forest-700 [&_a]:underline [&_ul]:list-disc [&_ul]:pl-6 [&_li]:mb-2">{children}</div>
      </main><PublicFooter />
    </div>
  )
}
