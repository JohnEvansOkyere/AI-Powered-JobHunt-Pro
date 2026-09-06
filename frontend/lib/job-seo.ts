import type { Job } from './api/jobs'
import { cleanJobDescription } from './text'
import { SITE_URL } from './site'

export function publicApplyUrl(job: Job): string {
  for (const value of [job.job_link, job.source_url]) {
    if (!value) continue
    try {
      const url = new URL(value.trim())
      if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) return url.href
    } catch { /* Try the alternate source link. */ }
  }
  return ''
}

export function isClosedJob(job: Job, now = Date.now()): boolean {
  return job.processing_status === 'archived' || Boolean(job.application_deadline && Date.parse(job.application_deadline) <= now)
}

export function isIndexableJob(job: Job): boolean {
  return !isClosedJob(job) && job.processing_status === 'processed' &&
    Number.isFinite(Date.parse(job.posted_date || '')) && Boolean(job.title.trim() && job.company.trim() && cleanJobDescription(job.description) && publicApplyUrl(job))
}

const employmentTypes: Record<string, string> = {
  'full-time': 'FULL_TIME', 'full time': 'FULL_TIME', full_time: 'FULL_TIME',
  'part-time': 'PART_TIME', 'part time': 'PART_TIME', part_time: 'PART_TIME',
  contract: 'CONTRACTOR', contractor: 'CONTRACTOR', freelance: 'CONTRACTOR',
  temporary: 'TEMPORARY', seasonal: 'TEMPORARY', intern: 'INTERN', internship: 'INTERN',
  volunteer: 'VOLUNTEER', per_diem: 'PER_DIEM', other: 'OTHER',
}

// Only explicit country names/codes are recognized. Never guess a country from
// a city, the employer's office, or an AI-normalized location.
const countries: Record<string, string> = {
  ghana: 'GH', gh: 'GH', nigeria: 'NG', ng: 'NG', kenya: 'KE', ke: 'KE',
  'south africa': 'ZA', za: 'ZA', rwanda: 'RW', uganda: 'UG', tanzania: 'TZ',
  egypt: 'EG', morocco: 'MA', senegal: 'SN', ethiopia: 'ET',
  'united states': 'US', 'united states of america': 'US', usa: 'US', us: 'US',
  'united kingdom': 'GB', uk: 'GB', gb: 'GB', canada: 'CA',
  germany: 'DE', france: 'FR', netherlands: 'NL', ireland: 'IE', spain: 'ES',
  portugal: 'PT', poland: 'PL', sweden: 'SE', switzerland: 'CH',
  australia: 'AU', 'new zealand': 'NZ', india: 'IN', pakistan: 'PK',
  singapore: 'SG', philippines: 'PH', brazil: 'BR', mexico: 'MX',
  'united arab emirates': 'AE', uae: 'AE',
}

export function jobPosting(job: Job): Record<string, unknown> | null {
  if (!isIndexableJob(job)) return null
  const location = (job.location || '').trim()
  const remote = (job.remote_type || job.remote_option || '').trim().toLowerCase() === 'remote'
  const parts = location.split(',').map((part) => part.trim()).filter(Boolean)
  const country = countries[(parts[parts.length - 1] || '').toLowerCase()]
  // For remote jobs, only a country-only eligibility label (optionally prefixed
  // with "Remote,") is unambiguous enough. Unknown/worldwide/multi-region labels
  // remain readable and indexable pages without speculative JobPosting markup.
  if (!country || (remote && !(parts.length === 1 || (parts.length === 2 && parts[0].toLowerCase() === 'remote')))) return null

  return {
    '@context': 'https://schema.org', '@type': 'JobPosting',
    title: job.title,
    description: cleanJobDescription([job.description, job.requirements].filter(Boolean).join('\n\n')),
    datePosted: job.posted_date,
    ...(job.application_deadline && Number.isFinite(Date.parse(job.application_deadline)) ? { validThrough: job.application_deadline } : {}),
    employmentType: employmentTypes[(job.job_type || '').toLowerCase()],
    hiringOrganization: { '@type': 'Organization', name: job.company },
    ...(remote ? {
      jobLocationType: 'TELECOMMUTE',
      applicantLocationRequirements: { '@type': 'Country', name: country },
    } : {
      jobLocation: { '@type': 'Place', address: { '@type': 'PostalAddress', addressCountry: country, ...(parts.length > 1 ? { addressLocality: parts.slice(0, -1).join(', ') } : {}) } },
    }),
    url: `${SITE_URL}/jobs/${job.id}`,
  }
}
