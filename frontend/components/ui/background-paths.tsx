'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'

import { Button } from '@/components/ui/button'

function FloatingPaths({ position }: { position: number }) {
  const paths = Array.from({ length: 36 }, (_, i) => ({
    id: i,
    d: `M-${380 - i * 5 * position} -${189 + i * 6}C-${
      380 - i * 5 * position
    } -${189 + i * 6} -${312 - i * 5 * position} ${216 - i * 6} ${
      152 - i * 5 * position
    } ${343 - i * 6}C${616 - i * 5 * position} ${470 - i * 6} ${
      684 - i * 5 * position
    } ${875 - i * 6} ${684 - i * 5 * position} ${875 - i * 6}`,
    width: 0.5 + i * 0.03,
  }))

  return (
    <div className="absolute inset-0 pointer-events-none">
      <svg
        // Off-white stroke so the paths glow softly against the ink background.
        className="w-full h-full text-cream-100"
        viewBox="0 0 696 316"
        fill="none"
      >
        <title>Background Paths</title>
        {paths.map((path) => (
          <motion.path
            key={path.id}
            d={path.d}
            stroke="currentColor"
            strokeWidth={path.width}
            strokeOpacity={0.08 + path.id * 0.02}
            initial={{ pathLength: 0.3, opacity: 0.6 }}
            animate={{
              pathLength: 1,
              opacity: [0.3, 0.6, 0.3],
              pathOffset: [0, 1, 0],
            }}
            transition={{
              duration: 20 + Math.random() * 10,
              repeat: Number.POSITIVE_INFINITY,
              ease: 'linear',
            }}
          />
        ))}
      </svg>
    </div>
  )
}

export interface BackgroundPathsProps {
  title?: string
  eyebrow?: string
  lede?: string
  ctaLabel?: string
  ctaHref?: string
  /** Optional secondary CTA, rendered next to the primary one. */
  secondaryCtaLabel?: string
  secondaryCtaHref?: string
}

export function BackgroundPaths({
  title = 'Find the job that fits you',
  eyebrow,
  lede,
  ctaLabel = 'See my matches',
  ctaHref = '/auth/signup',
  secondaryCtaLabel,
  secondaryCtaHref,
}: BackgroundPathsProps) {
  const words = title.split(' ')

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-ink-900">
      {/* Soft forest-green glow in the lower third for warmth. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-forest-700/50 to-transparent"
      />

      <div className="absolute inset-0">
        <FloatingPaths position={1} />
        <FloatingPaths position={-1} />
      </div>

      <div className="relative z-10 container mx-auto px-4 md:px-6 text-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.2 }}
          className="max-w-5xl mx-auto"
        >
          {eyebrow && (
            <div className="mb-6 flex justify-center">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cream-100/10 border border-cream-100/20 text-[11px] tracking-[0.18em] uppercase font-medium text-cream-100/80">
                <span className="w-1.5 h-1.5 rounded-full bg-ember-500 animate-pulse" />
                {eyebrow}
              </span>
            </div>
          )}

          <h1 className="font-display font-bold mb-8 tracking-tight leading-[0.95] text-5xl sm:text-7xl md:text-[6.5rem]">
            {words.map((word, wordIndex) => (
              <span key={wordIndex} className="inline-block mr-3 md:mr-5 last:mr-0">
                {word.split('').map((letter, letterIndex) => (
                  <motion.span
                    key={`${wordIndex}-${letterIndex}`}
                    initial={{ y: 100, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{
                      delay: wordIndex * 0.08 + letterIndex * 0.025,
                      type: 'spring',
                      stiffness: 150,
                      damping: 25,
                    }}
                    className="inline-block text-cream-100"
                  >
                    {letter}
                  </motion.span>
                ))}
              </span>
            ))}
          </h1>

          {lede && (
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.8 }}
              className="max-w-2xl mx-auto mb-10 text-lg md:text-xl text-cream-100/75 leading-relaxed"
            >
              {lede}
            </motion.p>
          )}

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.8 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <div
              className="inline-block group relative bg-gradient-to-b from-cream-100/30 to-cream-100/5
                p-px rounded-full backdrop-blur-lg overflow-hidden
                shadow-lg shadow-ink-950/60 hover:shadow-xl transition-shadow duration-300"
            >
              <Button
                asChild
                variant="ghost"
                className="rounded-full px-8 py-6 text-base font-semibold
                  bg-cream-100 hover:bg-cream-50
                  text-ink-900 hover:text-ink-900 transition-all duration-300
                  group-hover:-translate-y-0.5 border border-cream-100/30"
              >
                <Link href={ctaHref}>
                  <span>{ctaLabel}</span>
                  <span
                    className="ml-3 opacity-70 group-hover:opacity-100 group-hover:translate-x-1
                      transition-all duration-300"
                  >
                    →
                  </span>
                </Link>
              </Button>
            </div>

            {secondaryCtaLabel && secondaryCtaHref && (
              <Link
                href={secondaryCtaHref}
                className="inline-flex items-center gap-2 px-7 py-4 rounded-full text-sm font-semibold text-cream-100/80 hover:text-cream-100 border border-cream-100/25 hover:border-cream-100/50 transition-colors"
              >
                {secondaryCtaLabel}
              </Link>
            )}
          </motion.div>
        </motion.div>
      </div>

      {/* Subtle cream ruler at the bottom — signals the transition into the cream body. */}
      <div
        aria-hidden
        className="pointer-events-none absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cream-100/20 to-transparent"
      />
    </div>
  )
}
