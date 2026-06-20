import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Privacy Policy | VeloxaHire',
  description: 'How VeloxaHire collects, uses, protects, exports, and deletes candidate data.',
}

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-cream-100 text-ink-900">
      <div className="mx-auto max-w-3xl px-6 py-12">
        <Link href="/" className="text-sm font-semibold text-forest-700 hover:text-forest-800">
          VeloxaHire
        </Link>
        <h1 className="mt-6 text-3xl font-bold tracking-tight">Privacy Policy</h1>
        <p className="mt-2 text-sm text-ink-500">Last updated: June 2, 2026</p>

        <div className="mt-8 space-y-7 text-sm leading-7 text-ink-700">
          <section>
            <h2 className="text-lg font-semibold text-ink-900">Data We Collect</h2>
            <p className="mt-2">
              VeloxaHire collects account details, career profile data, CV uploads and parsed CV
              content, saved jobs, application tracking data, job recommendations, notification
              preferences, and WhatsApp delivery audit records when you use those features.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-ink-900">How We Use Data</h2>
            <p className="mt-2">
              We use candidate data to authenticate users, maintain profiles, parse CVs, match jobs,
              generate recommendations, track applications, deliver opted-in notifications, protect
              the service from abuse, and operate the platform.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-ink-900">AI Processing</h2>
            <p className="mt-2">
              Profile, CV, and job text may be processed by configured AI providers to parse CVs,
              create embeddings, rank jobs, and generate match explanations. Inputs are bounded and
              sanitized before provider calls.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-ink-900">Data Export And Deletion</h2>
            <p className="mt-2">
              Authenticated users can export their VeloxaHire candidate data or delete their account
              data from the Settings page. Deletion removes profile data, CV records and stored CV
              files, application tracking data, recommendations, user embeddings, external jobs added
              by the user, and notification records tied to the account.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-ink-900">Contact</h2>
            <p className="mt-2">
              For privacy requests, use the account tools in Settings or contact the VeloxaHire team
              through the contact details provided in the application.
            </p>
          </section>
        </div>
      </div>
    </main>
  )
}
