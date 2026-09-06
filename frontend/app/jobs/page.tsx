import type { Metadata } from "next";
import { Suspense } from "react";
import JobsClient from "./JobsClient";
import { notFound } from 'next/navigation';
import { parseJobSearch, jobSearchQuery, jobSearchHref, type SearchValues } from '@/lib/job-search';
import { fetchPublicJobs } from '@/lib/public-job-fetch';

export const dynamic = 'force-dynamic';

export async function generateMetadata({ searchParams }: { searchParams: SearchValues }): Promise<Metadata> {
  const filters = parseJobSearch(searchParams);
  const data = await fetchPublicJobs(jobSearchQuery(filters));
  const filtered = Boolean(filters.q || filters.location || filters.source || filters.remote_type || filters.min_posted_days);
  return {
  title: `Browse Jobs${(filters.page || 1) > 1 ? ` — Page ${filters.page}` : ''} | VeloxaHire`,
  description:
    "Browse recruiter-posted roles and curated job listings on VeloxaHire before creating a profile for personalized AI recommendations.",
  alternates: {
    canonical: jobSearchHref(filters),
  },
  robots: filtered || !data || data.total === 0 ? { index: false, follow: true } : undefined,
  };
}

export default async function JobsPage({ searchParams }: { searchParams: SearchValues }) {
  const filters = parseJobSearch(searchParams);
  const data = await fetchPublicJobs(jobSearchQuery(filters));
  if (data && (filters.page || 1) > Math.max(1, data.total_pages)) notFound();
  return (
    <Suspense
      fallback={<main className="min-h-screen bg-white" aria-busy="true" />}
    >
      <JobsClient key={jobSearchQuery(filters)} filters={filters} data={data} />
    </Suspense>
  );
}
