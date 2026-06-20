import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Terms of Service | VeloxaHire',
  description: 'Terms for using VeloxaHire candidate job discovery and recommendation tools.',
}

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-cream-100 text-ink-900">
      <div className="mx-auto max-w-3xl px-6 py-12">
        <Link href="/" className="text-sm font-semibold text-forest-700 hover:text-forest-800">
          VeloxaHire
        </Link>
        <h1 className="mt-6 text-3xl font-bold tracking-tight">Terms of Service</h1>
        <p className="mt-2 text-sm text-ink-500">Last updated: June 2, 2026</p>

        <div className="mt-8 space-y-7 text-sm leading-7 text-ink-700">
          <section>
            <h2 className="text-lg font-semibold text-ink-900">Use Of The Service</h2>
            <p className="mt-2">
              VeloxaHire provides job discovery, candidate profile management, CV parsing,
              recommendation, application tracking, and optional notification tools. You are
              responsible for the accuracy of information you provide and for decisions you make
              based on jobs or recommendations shown in the service.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-ink-900">Candidate Data</h2>
            <p className="mt-2">
              You must only upload CVs and profile information that you have the right to use.
              VeloxaHire processes this data to provide the service and to maintain account,
              security, and notification workflows.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-ink-900">Jobs And Applications</h2>
            <p className="mt-2">
              Job listings may come from external job boards, user-provided URLs, or mirrored
              recruiter postings. VeloxaHire does not guarantee that external listings remain open,
              accurate, or available. Applications submitted on external websites are governed by
              those websites' terms.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-ink-900">Notifications</h2>
            <p className="mt-2">
              WhatsApp job alerts are sent only after opt-in and phone verification. You can update
              preferences or opt out from Settings.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-ink-900">Account Closure</h2>
            <p className="mt-2">
              You can export or delete your account data from Settings. Deletion is permanent for
              the candidate-platform data removed by that workflow.
            </p>
          </section>
        </div>
      </div>
    </main>
  )
}
