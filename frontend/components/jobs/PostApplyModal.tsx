"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef } from "react";
import Link from "next/link";
import { X } from "lucide-react";

interface PostApplyModalProps {
  open: boolean;
  onClose: () => void;
  heading?: string;
  description?: string;
  ctaLabel?: string;
}

export function PostApplyModal({
  open,
  onClose,
  heading = "Find more roles like this one",
  description = "Create an account to save jobs and build your personal shortlist.",
  ctaLabel = "Create free account",
}: PostApplyModalProps) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panel.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab") return;
      const items = panel.current?.querySelectorAll<HTMLElement>(
        "a[href],button:not([disabled])",
      );
      if (!items?.length) return;
      const first = items[0],
        last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener("keydown", handleKey);
      previous?.focus();
    };
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-neutral-900/60 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Panel */}
          <div className="pointer-events-none fixed inset-0 z-50 grid place-items-center p-4">
            <motion.div
              ref={panel}
              key="panel"
              initial={{ opacity: 0, y: 18, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.97 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              role="dialog"
              aria-modal="true"
              aria-labelledby="post-apply-title"
              aria-describedby="post-apply-description"
              className="pointer-events-auto max-h-[calc(100svh-2rem)] w-full max-w-sm overflow-y-auto rounded-lg border border-neutral-200 bg-white shadow-2xl"
            >
              {/* Top accent bar */}
              <div className="h-1 w-full bg-forest-600" />

              <div className="px-6 pb-6 pt-5 sm:px-7 sm:pb-7 sm:pt-6">
                {/* Header */}
                <div className="mb-2 flex items-start justify-between gap-3">
                  <h2
                    id="post-apply-title"
                    className="text-xl font-semibold leading-tight text-neutral-900"
                  >
                    {heading}
                  </h2>
                  <button
                    onClick={onClose}
                    className="-mr-1 flex-shrink-0 rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
                    aria-label="Close"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <p
                  id="post-apply-description"
                  className="mb-5 text-sm leading-relaxed text-neutral-600"
                >
                  {description}
                </p>

                {/* CTAs */}
                <div className="flex flex-col gap-1.5">
                  <Link
                    href="/auth/signup"
                    className="inline-flex w-full items-center justify-center rounded-md bg-forest-600 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-forest-700"
                  >
                    {ctaLabel}
                  </Link>
                  <button
                    onClick={onClose}
                    className="w-full px-4 py-2.5 text-sm font-medium text-neutral-500 hover:text-neutral-800 transition-colors"
                  >
                    Maybe later
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
