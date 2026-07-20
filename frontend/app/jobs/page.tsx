import type { Metadata } from 'next'
import JobsClient from './JobsClient'

export const metadata: Metadata = {
  title: 'Browse Jobs | VeloxaHire',
  description:
    'Browse recruiter-posted roles and curated job listings on VeloxaHire before creating a profile for personalized AI recommendations.',
  alternates: {
    canonical: '/jobs',
  },
}

export default function JobsPage() {
  return <JobsClient />
}
