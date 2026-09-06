import Link from 'next/link'

export default function PublicFooter() {
  return (
    <footer className="border-t border-ink-900/10 bg-cream-100 px-6 py-10 text-ink-900">
      <div className="mx-auto grid max-w-6xl gap-8 sm:grid-cols-3">
        <div><Link href="/" className="text-xl font-semibold">VeloxaHire.</Link><p className="mt-3 max-w-xs text-sm leading-6 text-ink-700">Job discovery and CV-based matching for your next career move.</p></div>
        <nav aria-label="Explore jobs" className="flex flex-col items-start gap-3 text-sm">
          <Link href="/jobs">Browse jobs</Link><Link href="/ghana-jobs">Jobs in Ghana</Link><Link href="/remote-jobs">Remote jobs</Link><Link href="/guides/remote-jobs-from-ghana">Applying for remote jobs from Ghana</Link>
        </nav>
        <nav aria-label="About VeloxaHire" className="flex flex-col items-start gap-3 text-sm">
          <Link href="/about">About VeloxaHire</Link><Link href="/how-it-works">How matching works</Link><Link href="/job-sources">Job sources and safety</Link><Link href="/contact">Contact and support</Link>
          <div className="flex gap-4"><Link href="/privacy">Privacy</Link><Link href="/terms">Terms</Link></div>
        </nav>
      </div>
    </footer>
  )
}
