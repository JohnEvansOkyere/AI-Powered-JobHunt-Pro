"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowUpRight,
  Bookmark,
  Briefcase,
  MapPin,
  Search,
  Globe,
  RefreshCw,
} from "lucide-react";
import { type Job, type JobSearchParams, type JobSearchResponse } from "@/lib/api/jobs";
import { jobSearchHref } from '@/lib/job-search';
import PublicFooter from '@/components/layout/PublicFooter';
import { cleanJobDescription } from "@/lib/text";
import { useAuth } from "@/hooks/useAuth";
import PublicHeader from "@/components/layout/PublicHeader";
import { PostApplyModal } from "@/components/jobs/PostApplyModal";

function companyInitials(company: string) {
  return (company || "?")
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}
function postedAt(value: string | null) {
  if (!value) return "Recently added";
  const days = Math.max(
    0,
    Math.floor((Date.now() - new Date(value).getTime()) / 86400000),
  );
  if (!Number.isFinite(days)) return "Recently added";
  return days === 0
    ? "Added today"
    : days === 1
      ? "1 day ago"
      : days + " days ago";
}
function readable(value: string | null | undefined) {
  return value?.replace(/[_-]/g, " ") || "";
}
function applyUrl(job: Job) {
  const value = job.job_link || job.source_url;
  if (!value) return null;
  try {
    return ["https:", "http:"].includes(new URL(value).protocol) ? value : null;
  } catch {
    return null;
  }
}

export default function JobsClient({ filters, data }: { filters: JobSearchParams; data: JobSearchResponse | null }) {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [query, setQuery] = useState(filters.q || '');
  const [location, setLocation] = useState(filters.location || '');
  const jobs = data?.jobs || [];
  const total = data?.total || 0;
  const totalPages = Math.max(1, data?.total_pages || 1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, startTransition] = useTransition();
  const failed = data === null;
  const [showPrompt, setShowPrompt] = useState(false);
  const selected = jobs.find((job) => job.id === selectedId) || jobs[0];
  const page = filters.page || 1;
  const hasFilters = Boolean(
    filters.q ||
    filters.location ||
    filters.remote_type ||
    filters.source ||
    filters.min_posted_days,
  );

  const updateFilter = (patch: Partial<JobSearchParams>) =>
    startTransition(() => router.push(jobSearchHref({ ...filters, ...patch, page: 1 }), { scroll: false }));
  const clearFilters = () => {
    setQuery("");
    setLocation("");
    startTransition(() => router.push('/jobs', { scroll: false }));
  };

  return (
    <div className="vh-site vh-board">
      <PublicHeader />
      <main id="main-content">
        <section className="vh-search-bar" aria-label="Search jobs">
          <div className="vh-wrap">
            <form
              className="vh-search-form"
              role="search"
              action="/jobs"
              onSubmit={(event) => {
                event.preventDefault();
                updateFilter({ q: query.trim(), location: location.trim() });
              }}
            >
              <label className="vh-search-field">
                <Search size={19} />
                <span className="sr-only">Job title, company or keyword</span>
                <input
                  name="q"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Job title, company or keyword"
                />
              </label>
              <label className="vh-search-field">
                <MapPin size={19} />
                <span className="sr-only">Location</span>
                <input
                  name="location"
                  value={location}
                  onChange={(event) => setLocation(event.target.value)}
                  placeholder="City or country"
                />
              </label>
              <button className="vh-button" type="submit">
                Search jobs
              </button>
            </form>
            <div className="vh-filter-row">
              <button
                aria-pressed={!filters.source}
                onClick={() => updateFilter({ source: undefined })}
              >
                All jobs
              </button>
              <button
                aria-pressed={filters.source === "recruiter"}
                onClick={() =>
                  updateFilter({
                    source: filters.source ? undefined : "recruiter",
                  })
                }
              >
                Recruiter posted
              </button>
              <button
                aria-pressed={filters.remote_type === "remote"}
                onClick={() =>
                  updateFilter({
                    remote_type: filters.remote_type ? undefined : "remote",
                  })
                }
              >
                Remote
              </button>
              <label>
                <span className="sr-only">Date posted</span>
                <select
                  aria-label="Date posted"
                  value={filters.min_posted_days || ""}
                  onChange={(event) =>
                    updateFilter({
                      min_posted_days: event.target.value
                        ? Number(event.target.value)
                        : undefined,
                    })
                  }
                >
                  <option value="">Any time</option>
                  <option value="1">Past 24 hours</option>
                  <option value="7">Past week</option>
                  <option value="30">Past month</option>
                </select>
              </label>
              {hasFilters && (
                <button className="vh-clear" onClick={clearFilters}>
                  Clear filters
                </button>
              )}
            </div>
          </div>
        </section>

        <section className="vh-wrap vh-board-main" aria-label="Job results">
          <div className="vh-board-title">
            <h1>
              {filters.q ? filters.q + " jobs" : "Find your next opportunity"}
            </h1>
            <p role="status">
              {loading
                ? "Finding opportunities…"
                : failed
                  ? "Search unavailable"
                  : total.toLocaleString() + " opportunities"}
              {!loading && !failed && filters.location
                ? " · " + filters.location
                : ""}
            </p>
          </div>
          {loading ? (
            <div
              className="vh-workspace"
              aria-busy="true"
              aria-label="Loading jobs"
            >
              <div className="vh-result-list">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="vh-board-skeleton" />
                ))}
              </div>
              <div className="vh-detail">
                <div className="vh-board-skeleton" style={{ height: 590 }} />
              </div>
            </div>
          ) : failed ? (
            <div className="vh-board-empty">
              <h2>We could not load the jobs.</h2>
              <p>Your search is still here. Please try again.</p>
              <button
                className="vh-button"
                onClick={() => startTransition(() => router.refresh())}
              >
                <RefreshCw size={16} />
                Try again
              </button>
            </div>
          ) : !jobs.length ? (
            <div className="vh-board-empty">
              <h2>No matches for this search.</h2>
              <p>Try another job title or location, or broaden your filters.</p>
              {hasFilters && (
                <button className="vh-button" onClick={clearFilters}>
                  Clear filters
                </button>
              )}
            </div>
          ) : (
            <div className="vh-workspace">
              <div className="vh-result-list" role="region" tabIndex={0} aria-label="Available roles">
                {jobs.map((job) => (
                  <article
                    key={job.id}
                    className={
                      "vh-result-row" +
                      (selected?.id === job.id ? " is-selected" : "")
                    }
                  >
                    <button
                      className="vh-result-main"
                      onClick={() => {
                        if (window.matchMedia("(max-width: 760px)").matches)
                          router.push("/jobs/" + job.id);
                        else setSelectedId(job.id);
                      }}
                      aria-pressed={selected?.id === job.id}
                      aria-label={"Preview " + job.title + " at " + job.company}
                    >
                      <span className="vh-company-icon" aria-hidden="true">
                        {companyInitials(job.company)}
                      </span>
                      <div>
                        <h2>{job.title}</h2>
                        <p>{job.company}</p>
                        <p>
                          {job.location || "Location not specified"}
                          {job.remote_type
                            ? " · " + readable(job.remote_type)
                            : ""}
                        </p>
                        <div className="vh-result-meta">
                          <span>
                            {postedAt(job.posted_date || job.scraped_at)}
                          </span>
                          {job.source === "recruiter" && (
                            <span>Recruiter posted</span>
                          )}
                        </div>
                      </div>
                    </button>
                    <Link
                      className="vh-result-detail-link"
                      href={"/jobs/" + job.id}
                      data-job-id={job.id}
                    >
                      View full job <span aria-hidden="true">↗</span>
                    </Link>
                  </article>
                ))}
              </div>
              {selected && (
                <article className="vh-detail" aria-label="Selected job">
                  <div className="vh-detail-heading">
                    <div className="vh-company-icon" aria-hidden="true">
                      {companyInitials(selected.company)}
                    </div>
                    <h2>{selected.title}</h2>
                    <p>{selected.company}</p>
                    <div className="vh-detail-facts">
                      {selected.location && (
                        <span>
                          <MapPin size={15} />
                          {selected.location}
                        </span>
                      )}
                      {selected.job_type && (
                        <span>
                          <Briefcase size={15} />
                          {readable(selected.job_type)}
                        </span>
                      )}
                      {selected.remote_type && (
                        <span>
                          <Globe size={15} />
                          {readable(selected.remote_type)}
                        </span>
                      )}
                    </div>
                    {selected.salary_range && <p>{selected.salary_range}</p>}
                    <div className="vh-detail-actions">
                      {applyUrl(selected) ? (
                        <a
                          className="vh-button"
                          href={applyUrl(selected)!}
                          target="_blank"
                          rel="noopener noreferrer nofollow"
                          data-analytics="job_apply_click"
                          data-job-id={selected.id}
                        >
                          Apply for this job <ArrowUpRight size={17} />
                        </a>
                      ) : (
                        <Link
                          className="vh-button"
                          href={"/jobs/" + selected.id}
                        >
                          View application details
                        </Link>
                      )}
                      {isAuthenticated ? (
                        <Link
                          href="/dashboard/jobs"
                          className="vh-button vh-secondary"
                        >
                          <Bookmark size={16} />
                          Save in dashboard
                        </Link>
                      ) : (
                        <button
                          className="vh-button vh-secondary"
                          onClick={() => setShowPrompt(true)}
                        >
                          <Bookmark size={16} />
                          Save job
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="vh-detail-body">
                    <h3>About the role</h3>
                    <div className="vh-description">
                      {cleanJobDescription(selected.description) ||
                        "Open the full job listing for the role description and application instructions."}
                    </div>
                  </div>
                  <div className="vh-detail-footer">
                    <span>Check the full listing before applying.</span>
                    <Link href={"/jobs/" + selected.id}>
                      Full job details ↗
                    </Link>
                  </div>
                </article>
              )}
            </div>
          )}
          {!loading && !failed && totalPages > 1 && (
            <nav className="vh-pagination" aria-label="Results pages">
              {page > 1 ? <Link href={jobSearchHref({ ...filters, page: page - 1 })} prefetch={false}>Previous</Link> : <span aria-disabled="true">Previous</span>}
              <span>
                Page {page} of {totalPages}
              </span>
              {page < totalPages ? <Link href={jobSearchHref({ ...filters, page: page + 1 })} prefetch={false}>Next</Link> : <span aria-disabled="true">Next</span>}
            </nav>
          )}
          {!isAuthenticated && (
            <aside className="vh-board-prompt">
              <div>
                <h2>Find the roles that fit your experience.</h2>
                <p>
                  Create a profile for a personal shortlist and editable,
                  role-specific CVs.
                </p>
              </div>
              <Link href="/auth/signup" className="vh-button">
                Create account
              </Link>
            </aside>
          )}
        </section>
      </main>
      <PublicFooter />
      <PostApplyModal
        open={showPrompt}
        onClose={() => setShowPrompt(false)}
        heading="Keep this opportunity."
        description="Create a free account to save jobs and build your shortlist."
        ctaLabel="Create account"
      />
    </div>
  );
}
