"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export const recruiterUrl =
  process.env.NEXT_PUBLIC_VELOXARECRUIT_URL ||
  "https://www.veloxarecruit.com/register";

export default function PublicHeader() {
  const path = usePathname();
  const { isAuthenticated, loading } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <header className="vh-header">
      <a href="#main-content" className="vh-skip">
        Skip to content
      </a>
      <div className="vh-wrap vh-nav">
        <Link href="/" className="vh-logo" aria-label="VeloxaHire home">
          <Image src="/logo.png" alt="" width={30} height={30} priority />
          VeloxaHire<span className="vh-logo-dot">.</span>
        </Link>
        <nav className="vh-desktop-nav" aria-label="Main navigation">
          <Link
            href="/jobs"
            aria-current={path.startsWith("/jobs") ? "page" : undefined}
          >
            Find a job
          </Link>
          <Link href="/#how-it-works">How it works</Link>
          <a href={recruiterUrl}>For employers</a>
        </nav>
        <div className="vh-nav-actions">
          {!loading && (
            <>
              <Link
                href={isAuthenticated ? "/dashboard/profile" : "/auth/login"}
                className="vh-signin"
              >
                {isAuthenticated ? "My profile" : "Sign in"}
              </Link>
              <Link
                href={isAuthenticated ? "/dashboard" : "/auth/signup"}
                className="vh-button vh-small"
              >
                {isAuthenticated ? "Dashboard" : "Create account"}
              </Link>
            </>
          )}
          <button
            className="vh-menu-button"
            aria-label={open ? "Close navigation" : "Open navigation"}
            aria-expanded={open}
            aria-controls="public-mobile-nav"
            onClick={() => setOpen(!open)}
          >
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>
      {open && (
        <nav
          id="public-mobile-nav"
          className="vh-mobile-nav"
          aria-label="Mobile navigation"
        >
          <Link href="/jobs" onClick={() => setOpen(false)}>
            Find a job
          </Link>
          <Link href="/#how-it-works" onClick={() => setOpen(false)}>
            How it works
          </Link>
          <a href={recruiterUrl}>For employers</a>
          {!loading && (
            <>
              <Link
                href={isAuthenticated ? "/dashboard/profile" : "/auth/login"}
                onClick={() => setOpen(false)}
              >
                {isAuthenticated ? "My profile" : "Sign in"}
              </Link>
              <Link
                href={isAuthenticated ? "/dashboard" : "/auth/signup"}
                onClick={() => setOpen(false)}
              >
                {isAuthenticated ? "Dashboard" : "Create account"}
              </Link>
            </>
          )}
        </nav>
      )}
    </header>
  );
}
