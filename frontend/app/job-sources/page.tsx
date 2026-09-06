import type { Metadata } from 'next'
import Link from 'next/link'
import PublicArticle from '@/components/layout/PublicArticle'

export const metadata: Metadata = {
  title: 'Job Sources, Freshness and Safer Applications | VeloxaHire',
  description: 'Learn where VeloxaHire listings come from, how to check availability, and what to review before sharing information or applying.',
  alternates: { canonical: '/job-sources' },
}

export default function JobSourcesPage() {
  return (
    <PublicArticle title="Know where your application goes." intro="VeloxaHire brings together recruiter postings, external job-board listings and curated imports. Inclusion is not an endorsement or a guarantee of an employer, vacancy or outcome.">
      <section><h2>Recruiter postings</h2><p>Recruiter-posted roles are shared from VeloxaRecruit. Their application links open the recruiter&apos;s public application page. The employer or recruiter manages applications and hiring decisions.</p></section>
      <section><h2>External listings and curated imports</h2><p>Other roles come from job sources outside VeloxaHire, including imported job digests. The source website may have additional details or a later update. A source appearing here does not imply a partnership with its publisher.</p></section>
      <section><h2>Check that the role is still available</h2><p>Listings are collected and updated over time. When a closing date or closure is known to VeloxaHire, the role is removed from active public discovery. Source changes can take time to reach us, so check the original page before preparing your application. A listing&apos;s age alone cannot confirm that it is open or closed.</p></section>
      <section><h2>Before sharing your information</h2><ul><li>Check the employer&apos;s official website and the destination of the application link.</li><li>Confirm country eligibility, work arrangements and the closing date.</li><li>Treat requests for payment, passwords or one-time verification codes as a reason to stop and verify independently.</li><li>Share only the information needed for a legitimate application.</li></ul></section>
      <section><h2>A listing looks wrong</h2><p>Keep the VeloxaHire job-page link and the original listing URL, and describe what appears incorrect or suspicious. Do not send passwords, verification codes or another person&apos;s CV.</p><p><Link href="/contact">Contact and support</Link></p></section>
    </PublicArticle>
  )
}
