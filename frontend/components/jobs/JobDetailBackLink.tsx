"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function JobDetailBackLink({ fromOverview }: { fromOverview: boolean }) {
  const { isAuthenticated, loading } = useAuth();
  const href = isAuthenticated
    ? fromOverview ? "/dashboard" : "/dashboard/jobs"
    : "/jobs";
  const label = isAuthenticated && fromOverview ? "Back to overview" : "Back to jobs";

  if (loading) {
    return <span className="mb-6 inline-block h-5" aria-hidden="true" />;
  }

  return (
    <Link
      href={href}
      className="mb-6 inline-flex items-center gap-1.5 text-sm font-semibold text-neutral-500 hover:text-neutral-900"
    >
      <ArrowLeft className="h-4 w-4" />
      {label}
    </Link>
  );
}
