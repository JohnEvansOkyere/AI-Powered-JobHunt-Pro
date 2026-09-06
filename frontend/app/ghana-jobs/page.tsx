import type { Metadata } from 'next'
import Link from 'next/link'
import PublicArticle from '@/components/layout/PublicArticle'
import { fetchPublicJobs } from '@/lib/public-job-fetch'
import { isIndexableJob } from '@/lib/job-seo'

export const dynamic = 'force-dynamic'
export const metadata: Metadata = {
  title: 'Jobs in Ghana | Current Listings and Application Guidance | VeloxaHire',
  description: 'Explore listings with Ghana in their location, check requirements and apply on the employer or source website. Find guidance for your next application.',
  alternates: { canonical: '/ghana-jobs' },
}

export default async function GhanaJobsPage() {
  const data = await fetchPublicJobs('location=Ghana&page_size=24')
  const jobs = data?.jobs.filter(isIndexableJob) || []
  return (
    <PublicArticle title="Find your next role in Ghana." intro="Explore roles with Ghana in their listed location. Check the full vacancy for its city, work arrangement and requirements, then follow the application link to the employer or source.">
      <section><h2>Current listings</h2>
        {!data ? <p>We could not load the listings right now. <Link href="/jobs?location=Ghana">Try the job search again</Link>.</p> : !jobs.length ? <p>No complete listings are available here right now. <Link href="/jobs">Browse the full catalogue</Link> or try searching for a city such as Accra or Kumasi.</p> : <div className="space-y-4">{jobs.map(job => <article key={job.id} className="rounded-xl border border-ink-900/10 bg-white p-5"><h3 className="text-lg font-semibold"><Link href={`/jobs/${job.id}`}>{job.title}</Link></h3><p>{job.company} · {job.location}</p></article>)}</div>}
        <p className="mt-5"><Link href="/jobs?location=Ghana">Search all Ghana listings</Link></p>
      </section>
      <section><h2>Make the location work for you</h2><p>Check whether the employer expects you on site, offers hybrid work or allows remote work. Confirm the office location and working hours before committing to an application. Roles using only a city name may be easier to find through the main search.</p></section>
      <section><h2>Prepare for the specific role</h2><p>Read the essential requirements and show relevant evidence from your experience, projects or training. Check the closing date and requested documents on the original listing. Save the application link and date so you can follow up through the right channel.</p></section>
      <section><h2>Considering remote work?</h2><p><Link href="/guides/remote-jobs-from-ghana">Read the checklist for applying from Ghana</Link>. Country eligibility still matters when a vacancy is remote.</p></section>
    </PublicArticle>
  )
}
