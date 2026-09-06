import type { Metadata } from 'next'
import Link from 'next/link'
import PublicArticle from '@/components/layout/PublicArticle'

export const metadata: Metadata = {
  title: 'About VeloxaHire | Job Discovery and CV Matching',
  description: 'Learn what VeloxaHire does for job seekers, where applications go, and how profiles and CVs help you find relevant opportunities.',
  alternates: { canonical: '/about' },
}

export default function AboutPage() {
  return (
    <PublicArticle title="A more focused job search." intro="VeloxaHire is a job discovery and CV-based matching platform from Veloxa Technology. It brings recruiter-posted roles and external job listings together so you can explore opportunities and decide what to pursue.">
      <section><h2>Who it is for</h2><p>Job seekers exploring opportunities in Ghana and beyond, including remote roles. Coverage depends on the listings available. A remote label does not mean an employer can hire in every country; always check the eligibility and work-authorisation requirements.</p></section>
      <section><h2>Start with the jobs</h2><p>You can browse and follow application links without an account. Applications open on the employer, recruiter or original job-board website. VeloxaHire does not submit applications on your behalf.</p><p><Link href="/jobs">Explore the current listings</Link></p></section>
      <section><h2>Build your personal shortlist</h2><p>Create an account, verify your phone, complete your career preferences and upload your CV to get personalized matches. Your profile helps you move from browsing everything to considering roles relevant to your experience.</p><p><Link href="/how-it-works">See how matching works</Link></p></section>
      <section><h2>Candidate and employer tools</h2><p>VeloxaHire serves job seekers. VeloxaRecruit is the separate recruiter-facing product. A recruiter-posted role can lead you to its public application page; an external listing leads to its source. Hiring decisions belong to the employer.</p></section>
      <section><h2>What to expect</h2><p>Matching helps you assess relevance. It does not guarantee that a vacancy is still open, that you meet every requirement, or that you will receive an interview or offer. Read the original listing and review your application before sending it.</p><p><Link href="/job-sources">Read about job sources and safety</Link> or <Link href="/contact">get support</Link>.</p></section>
    </PublicArticle>
  )
}
