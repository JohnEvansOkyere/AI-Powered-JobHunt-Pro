import type { Metadata } from 'next'
import Link from 'next/link'
import PublicArticle from '@/components/layout/PublicArticle'

export const metadata: Metadata = {
  title: 'Contact and Candidate Support | VeloxaHire',
  description: 'Find help with your VeloxaHire account, privacy controls and incorrect job listings.',
  alternates: { canonical: '/contact' },
}

export default function ContactPage() {
  const email = process.env.NEXT_PUBLIC_SUPPORT_EMAIL?.trim()
  const hasEmail = email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  return (
    <PublicArticle title="Help with your next step." intro="Use the account tools for your preferences and data. For a job application already sent, contact the employer or recruiter shown on the original listing.">
      {hasEmail && <section><h2>Contact VeloxaHire</h2><p><a href={`mailto:${email}`}>{email}</a></p><p>For a listing issue, include its VeloxaHire page link and a brief description. Never include passwords, verification codes or someone else&apos;s CV.</p></section>}
      <section><h2>Your account</h2><p><Link href="/dashboard/settings">Open Settings</Link> to manage preferences and use the available data export and deletion tools. If you cannot sign in, use <Link href="/auth/reset-password">password recovery</Link>.</p></section>
      <section><h2>Your application</h2><p>Applications are submitted on the employer, recruiter or source website. That organisation can answer questions about application status, deadlines and hiring decisions.</p></section>
      <section><h2>Privacy and job safety</h2><p><Link href="/privacy">Read the privacy policy</Link> for how career information is used, and <Link href="/job-sources">review the job-source guidance</Link> before sharing information with an unfamiliar employer.</p></section>
    </PublicArticle>
  )
}
