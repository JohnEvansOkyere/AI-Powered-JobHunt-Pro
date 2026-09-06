"use client";

import Link from "next/link";
import { ArrowRight, Bookmark } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function JobDetailActions({
  jobId,
  applyUrl,
}: {
  jobId: string;
  applyUrl: string;
}) {
  const { isAuthenticated, loading } = useAuth();

  return (
    <aside className="space-y-4">
      <div className="rounded-lg border border-neutral-200 bg-white p-5">
        {applyUrl ? (
          <a
            href={applyUrl}
            data-analytics="job_apply_click"
            data-job-id={jobId}
            target="_blank"
            rel="noopener noreferrer nofollow"
            className="vh-button w-full"
          >
            Apply now
            <ArrowRight className="h-4 w-4" />
          </a>
        ) : (
          <p className="rounded-md bg-neutral-100 px-4 py-3 text-center text-sm font-semibold text-neutral-500">
            Apply link unavailable
          </p>
        )}
        <p className="mt-3 text-xs leading-relaxed text-neutral-500">
          Applications open on the employer or recruiter page.
          {!loading && !isAuthenticated &&
            " Create a profile afterwards to track roles and get similar jobs."}
        </p>
      </div>

      {!loading && (
        <div className="rounded-lg border border-brand-turquoise-100 bg-brand-turquoise-50 p-5">
          <Bookmark className="h-5 w-5 text-brand-turquoise-700" />
          <h2 className="mt-3 font-semibold text-neutral-900">
            {isAuthenticated ? "Your job matches" : "Get roles like this ranked for you"}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-neutral-600">
            {isAuthenticated
              ? "Continue exploring roles matched to your profile and CV."
              : "Upload your CV once and VeloxaHire will score matching jobs, save your shortlist, and keep track of applications."}
          </p>
          <Link
            href={isAuthenticated ? "/dashboard/recommendations" : "/auth/signup"}
            className="mt-4 inline-flex w-full items-center justify-center rounded-md bg-brand-turquoise-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-turquoise-700"
          >
            {isAuthenticated ? "Back to job matches" : "Create free profile"}
          </Link>
        </div>
      )}
    </aside>
  );
}
