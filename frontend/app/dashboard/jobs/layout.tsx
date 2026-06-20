import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Jobs | VeloxaHire',
  description:
    'Browse candidate-friendly job listings and recruiter-posted roles, then save or apply from VeloxaHire.',
  openGraph: {
    title: 'Jobs | VeloxaHire',
    description:
      'Browse candidate-friendly job listings and recruiter-posted roles, then save or apply from VeloxaHire.',
    type: 'website',
  },
}

export default function JobsLayout({ children }: { children: React.ReactNode }) {
  return children
}
