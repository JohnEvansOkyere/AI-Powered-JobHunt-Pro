import type { Metadata } from "next";
import PublicHeader from "@/components/layout/PublicHeader";
import JobDetailActions from "@/components/jobs/JobDetailActions";
import JobDetailBackLink from "@/components/jobs/JobDetailBackLink";
import { notFound } from "next/navigation";
import {
  Briefcase,
  Building2,
  Clock,
  MapPin,
} from "lucide-react";
import type { Job } from "@/lib/api/jobs";
import { cleanJobDescription } from "@/lib/text";
import { SITE_URL, serializeJsonLd } from "@/lib/site";
import { publicApplyUrl, isClosedJob, isIndexableJob, jobPosting } from "@/lib/job-seo";
import PublicFooter from "@/components/layout/PublicFooter";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function getJob(id: string): Promise<Job | null> {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) return null;
  const response = await fetch(`${API_URL}/api/v1/jobs/${id}`, {
    cache: "no-store",
  });

  if (response.status === 404 || response.status === 410) return null;
  if (!response.ok) throw new Error("Failed to load job");
  const job: Job = await response.json();
  return isClosedJob(job) ? null : job;
}

function formatDate(dateString?: string | null) {
  if (!dateString) return "Recently posted";
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return "Recently posted";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export async function generateMetadata({
  params,
}: {
  params: { id: string };
}): Promise<Metadata> {
  const job = await getJob(params.id);
  if (!job) {
    return {
      title: "Job Not Found | VeloxaHire",
      robots: { index: false, follow: true },
    };
  }

  const title = `${job.title} at ${job.company} | VeloxaHire`;
  const description = cleanJobDescription(job.description).slice(0, 155);
  const indexable = isIndexableJob(job);
  return {
    title,
    description,
    alternates: {
      canonical: `/jobs/${job.id}`,
    },
    robots: indexable ? undefined : { index: false, follow: true },
    openGraph: {
      title,
      description,
      type: "article",
      url: `${SITE_URL}/jobs/${job.id}`,
      images: [
        {
          url: "/og-image.png",
          width: 1200,
          height: 630,
          alt: "VeloxaHire — Jobs and personalized matching",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      images: ["/og-image.png"],
    },
  };
}

export default async function JobDetailPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { from?: string | string[] };
}) {
  const job = await getJob(params.id);
  if (!job) notFound();

  const applyUrl = publicApplyUrl(job);
  const postedDate = job.posted_date || job.scraped_at;
  const jsonLd = jobPosting(job);

  return (
    <div className="vh-site vh-job-page">
      <PublicHeader />
      <main id="main-content">
        {jsonLd && (
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }}
          />
        )}

        <article className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
          <JobDetailBackLink fromOverview={searchParams.from === "overview"} />

          <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
            <section className="rounded-lg border border-neutral-200 bg-white p-6 ">
              <div className="mb-4 flex flex-wrap items-center gap-2">
                {job.source === "recruiter" && (
                  <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
                    Direct recruiter role
                  </span>
                )}
                <span className="rounded-full bg-neutral-100 px-2 py-1 text-xs font-semibold text-neutral-500">
                  {formatDate(postedDate)}
                </span>
              </div>

              <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-neutral-900">
                {job.title}
              </h1>
              <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-neutral-500">
                <span className="inline-flex items-center gap-1.5">
                  <Building2 className="h-4 w-4" />
                  {job.company}
                </span>
                {job.location && (
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="h-4 w-4" />
                    {job.location}
                  </span>
                )}
                {job.job_type && (
                  <span className="inline-flex items-center gap-1.5 capitalize">
                    <Briefcase className="h-4 w-4" />
                    {job.job_type}
                  </span>
                )}
                <span className="inline-flex items-center gap-1.5">
                  <Clock className="h-4 w-4" />
                  {formatDate(postedDate)}
                </span>
              </div>

              <div className="mt-8 border-t border-neutral-100 pt-8">
                {job.application_deadline && (
                  <p className="mb-4 text-sm font-semibold">Applications close: {formatDate(job.application_deadline)}</p>
                )}
                <p className="mb-4 text-sm text-neutral-600">
                  Source: {job.source === 'recruiter' ? 'Recruiter posting' : job.source}. Check the original listing for current availability and eligibility before applying.
                </p>
                <h2 className="text-lg font-semibold text-neutral-900">
                  Job description
                </h2>
                <div className="mt-4 whitespace-pre-line text-sm leading-7 text-neutral-700">
                  {cleanJobDescription(job.description)}
                </div>
              </div>

              {job.requirements && (
                <div className="mt-8 border-t border-neutral-100 pt-8">
                  <h2 className="text-lg font-semibold text-neutral-900">
                    Requirements
                  </h2>
                  <div className="mt-4 whitespace-pre-line text-sm leading-7 text-neutral-700">
                    {cleanJobDescription(job.requirements)}
                  </div>
                </div>
              )}
            </section>

            <JobDetailActions jobId={job.id} applyUrl={applyUrl} />
          </div>
        </article>
      </main>
      <PublicFooter />
    </div>
  );
}
