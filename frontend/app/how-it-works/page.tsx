import type { Metadata } from 'next'
import Link from 'next/link'
import PublicArticle from '@/components/layout/PublicArticle'

export const metadata: Metadata = {
  title: 'How CV-Based Job Matching Works | VeloxaHire',
  description: 'Understand the steps from browsing jobs to building your profile, uploading a CV, reviewing matches and applying on the source website.',
  alternates: { canonical: '/how-it-works' },
}

export default function HowItWorksPage() {
  return (
    <PublicArticle title="From your experience to a shortlist." intro="Browse first. When you want a more personal search, give VeloxaHire the career context it needs to recommend relevant roles.">
      <section><h2>1. Explore the available jobs</h2><p>Search by title, company or location. Open a full listing to check the description and requirements. You can follow the application link without creating an account.</p></section>
      <section><h2>2. Set up your profile and CV</h2><p>Create an account and verify your phone. Add your target role, seniority, work preference and skills, then upload your CV. Matching requires your career essentials and a CV that the platform has successfully parsed. Review your information so it represents your experience accurately.</p></section>
      <section><h2>3. Review your matches</h2><p>VeloxaHire compares your career information with job information to suggest relevant opportunities. Your shortlist is a starting point: check required skills, experience, location, working hours and application deadlines yourself.</p><div className="mt-4 rounded-xl border border-ink-900/10 bg-white p-5"><p className="font-semibold text-ink-900">An illustrative example</p><p>A candidate seeking a data analyst role with Excel and SQL experience may find an analyst vacancy relevant. If the employer only hires residents of another country, skill overlap does not make that candidate eligible. Confirm both fit and eligibility before applying.</p></div></section>
      <section><h2>4. Prepare and apply</h2><p>Save roles you want to revisit and track your applications. If you create a tailored CV draft, check every statement and edit it before downloading. Follow the job&apos;s application link to submit your application to the employer or source site.</p></section>
      <section><h2>Your data and your decisions</h2><p>Profile, CV and job text may be processed by AI providers to support parsing and matching. AI can misunderstand information; recommendations and drafts need your review. The employer makes the hiring decision.</p><p><Link href="/privacy">Read how your data is used</Link> or <Link href="/auth/signup">create your account</Link>.</p></section>
    </PublicArticle>
  )
}
