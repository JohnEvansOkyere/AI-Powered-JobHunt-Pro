import type { Metadata } from 'next'
import HomeClient from './HomeClient'

export const metadata: Metadata = {
  title: 'Jobs in Ghana, Remote Roles and CV Matching | VeloxaHire',
  description: 'Explore recruiter-posted and external job listings in Ghana and beyond. Build a CV-based shortlist with VeloxaHire and apply on the employer or source website.',
  alternates: { canonical: '/' },
}

export default function HomePage() {
  return <HomeClient />
}
