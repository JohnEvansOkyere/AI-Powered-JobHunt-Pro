"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useProfile } from "@/hooks/useProfile";
import { useAuth } from "@/hooks/useAuth";
import Link from "next/link";
import { ArrowRight, FileText, MapPin, Bell, Briefcase } from "lucide-react";
import { getApplicationsStats } from "@/lib/api/applications";
import {
  fetchRecommendations,
  type RecommendationItem,
} from "@/lib/api/recommendations";
import { calculateProfileCompletion } from "@/lib/profile-utils";

interface Overview {
  applicationsTotal: number;
  submittedCount: number;
  recommendationsTotal: number;
  matches: RecommendationItem[];
}

export default function DashboardPage() {
  return <ProtectedRoute><DashboardContent /></ProtectedRoute>;
}

function DashboardContent() {
  const { profile, loading: profileLoading, loadProfile } = useProfile();
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let active = true;
    setError(false);
    Promise.all([getApplicationsStats(), fetchRecommendations(undefined, 1, 3)])
      .then(([stats, recs]) => {
        if (active)
          setOverview({
            applicationsTotal: stats.applications_total,
            submittedCount: stats.submitted_count,
            recommendationsTotal: recs.total,
            matches: recs.items,
          });
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [authLoading, isAuthenticated, attempt]);

  if (authLoading || profileLoading)
    return (
        <DashboardLayout>
          <div className="ws-loading" role="status">
            Loading your workspace…
          </div>
        </DashboardLayout>
    );
  if (!profile) return (
    <DashboardLayout>
      <div className="ws-panel p-6 space-y-4">
        <p role="alert">We couldn’t load your profile. Please try again.</p>
        <button className="ws-button" onClick={() => void loadProfile()}>Try again</button>
      </div>
    </DashboardLayout>
  );

  const name = String(
    user?.user_metadata?.full_name ||
      user?.user_metadata?.name ||
      user?.user_metadata?.display_name ||
      "",
  )
    .trim()
    .split(/\s+/)[0];
  const completion = calculateProfileCompletion(profile);

  return (
      <DashboardLayout>
        <div className="ws-page ws-overview">
          <header className="ws-heading">
            <div>
              <p className="ws-eyebrow">Your next chapter</p>
              <h1>Welcome back{name ? `, ${name}` : ""}.</h1>
              <p>A little focus today. A new opportunity tomorrow.</p>
            </div>
            <Link href="/dashboard/jobs" className="ws-button">
              Explore jobs <ArrowRight size={16} />
            </Link>
          </header>

          <section
            className="ws-metrics"
            aria-label="Your job search at a glance"
          >
            {[
              [
                "Matched roles",
                overview?.recommendationsTotal,
                "/dashboard/recommendations",
              ],
              [
                "Applications",
                overview?.applicationsTotal,
                "/dashboard/applications",
              ],
              [
                "Submitted",
                overview?.submittedCount,
                "/dashboard/applications",
              ],
            ].map(([label, value, href]) => (
              <Link href={String(href)} key={String(label)}>
                <span>{label}</span>
                <strong>{value ?? "—"}</strong>
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            ))}
          </section>

          <div className="ws-overview-grid">
            <div>
              <section className="ws-panel">
                <header className="ws-panel-heading">
                  <div>
                    <h2>Selected for your next move</h2>
                    <p>
                      {profile.primary_job_title
                        ? `Based on your interest in ${profile.primary_job_title}.`
                        : "Roles matched to your experience and skills."}
                    </p>
                  </div>
                  <Link href="/dashboard/recommendations">
                    View all <ArrowRight size={15} />
                  </Link>
                </header>
                {error ? (
                  <div className="ws-empty" role="alert">
                    <h3>We couldn’t load your overview.</h3>
                    <p>Your saved work is still there. Please try again.</p>
                    <button
                      className="ws-button ws-button-secondary"
                      onClick={() => setAttempt((a) => a + 1)}
                    >
                      Try again
                    </button>
                  </div>
                ) : !overview ? (
                  <div className="ws-loading" role="status">
                    Finding your matches…
                  </div>
                ) : overview.matches.length ? (
                  overview.matches.map((item) => (
                    <Link
                      className="ws-match-row"
                      href={
                        item.job
                          ? `/jobs/${item.job_id}?from=overview`
                          : "/dashboard/recommendations"
                      }
                      key={item.id}
                    >
                      <span className="ws-company-mark" aria-hidden="true">
                        {(item.job?.company || "J").slice(0, 2).toUpperCase()}
                      </span>
                      <div>
                        <h3>{item.job?.title || "View matched role"}</h3>
                        <p>{item.job?.company || "Company not listed"}</p>
                        <span className="ws-location">
                          <MapPin size={13} />
                          {item.job?.location || "Location not specified"}
                        </span>
                      </div>
                      {!item.catalog_only && (
                        <span className="ws-match-score">
                          {Math.round(item.match_score * 100)}% match
                        </span>
                      )}
                    </Link>
                  ))
                ) : (
                  <div className="ws-empty">
                    <Briefcase size={26} />
                    <h3>No matches to show yet</h3>
                    <p>
                      Check your target role and skills, or browse all available
                      jobs.
                    </p>
                    <Link
                      href="/dashboard/profile"
                      className="ws-button ws-button-secondary"
                    >
                      Review profile
                    </Link>
                  </div>
                )}
              </section>

              <section className="ws-cv-callout">
                <FileText size={24} aria-hidden="true" />
                <div>
                  <h2>A CV that speaks to the role.</h2>
                  <p>
                    Choose a matched job, tailor your CV, then edit every detail
                    before applying.
                  </p>
                  <Link href="/dashboard/recommendations">
                    Find a role to tailor for <ArrowRight size={15} />
                  </Link>
                </div>
              </section>
            </div>

            <aside
              className="ws-support"
              aria-label="Your profile and preferences"
            >
              <section className="ws-panel ws-profile-summary">
                <p className="ws-eyebrow">Your candidate profile</p>
                <h2>{profile.primary_job_title || "Set your target role"}</h2>
                <p>Give employers—and your matches—a clearer picture of you.</p>
                <div className="ws-progress-label">
                  <span>Profile complete</span>
                  <strong>{completion}%</strong>
                </div>
                <progress
                  value={completion}
                  max={100}
                  aria-label="Profile completion"
                />
                <Link
                  href="/dashboard/profile"
                  className="ws-button ws-button-secondary"
                >
                  {completion === 100 ? "Review profile" : "Complete profile"}{" "}
                  <ArrowRight size={15} />
                </Link>
              </section>
              <section className="ws-alert-callout">
                <Bell size={20} aria-hidden="true" />
                <h2>Good roles. Less checking.</h2>
                <p>Manage WhatsApp alerts so you can hear about new matches.</p>
                <Link href="/dashboard/settings">
                  Manage alerts <ArrowRight size={15} />
                </Link>
              </section>
              <p className="ws-footnote">
                Your profile and CV stay in your control.
              </p>
            </aside>
          </div>
        </div>
      </DashboardLayout>
  );
}
