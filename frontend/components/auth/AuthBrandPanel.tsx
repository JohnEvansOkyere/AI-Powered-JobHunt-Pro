'use client'

import Link from 'next/link'
import Image from 'next/image'
import { motion } from 'framer-motion'
import { CheckCircle2, Sparkles } from 'lucide-react'

const POINTS = [
  'Get a shortlist ranked against your CV — skip the endless scrolling.',
  'Apply once and track every application in one place.',
  'Save roles and let VeloxaHire surface similar jobs automatically.',
  "See recruiter-posted roles you won't find on generic boards.",
]

const METRICS = [
  { value: 'AI', label: 'CV-ranked shortlist' },
  { value: '1-click', label: 'Apply & track' },
  { value: 'Free', label: 'Always for candidates' },
]

function Shape({
  className,
  delay,
  gradient,
}: {
  className: string
  delay: number
  gradient: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
      className={`absolute rounded-full blur-2xl ${gradient} ${className}`}
    />
  )
}

export default function AuthBrandPanel({ variant }: { variant: 'signup' | 'login' }) {
  const headline =
    variant === 'login' ? (
      <>
        Welcome back to{' '}
        <span className="italic font-normal text-ember-400">your shortlist.</span>
      </>
    ) : (
      <>
        Stop scrolling.{' '}
        <span className="italic font-normal text-ember-400">Start matching.</span>
      </>
    )

  const subtext =
    variant === 'login'
      ? 'Sign in to pick up where you left off — your matches, saved roles, and applications are waiting.'
      : 'VeloxaHire reads each role the way a recruiter would and ranks the ones that actually fit your CV. Less noise, better jobs.'

  return (
    <div className="relative hidden lg:flex lg:w-1/2 flex-col justify-center overflow-hidden bg-forest-700 text-cream-100">
      {/* Brand wash */}
      <div className="absolute inset-0 bg-gradient-to-br from-brand-turquoise-500/10 via-transparent to-ember-400/10" />

      {/* Soft geometric glows */}
      <Shape delay={0.2} className="left-[-8%] top-[12%] h-72 w-72" gradient="bg-brand-turquoise-400/20" />
      <Shape delay={0.4} className="right-[-6%] top-[58%] h-80 w-80" gradient="bg-ember-400/12" />
      <Shape delay={0.5} className="left-[10%] bottom-[-6%] h-56 w-56" gradient="bg-forest-400/30" />

      {/* Vignette */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-forest-900/80 via-transparent to-forest-800/40" />

      <div className="relative z-10 flex h-full flex-col justify-center px-14 py-16 xl:px-20">
        {/* Logo */}
        <Link href="/" className="group mb-12 inline-flex w-fit items-center gap-3">
          <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl border border-cream-100/15 bg-cream-100/10 backdrop-blur-md transition-all group-hover:scale-105 group-hover:bg-cream-100/15">
            <Image src="/logo.png" alt="VeloxaHire" width={26} height={26} className="object-contain" style={{ width: 'auto', height: 'auto' }} priority />
          </div>
          <span className="font-display text-xl font-semibold tracking-tight">
            Veloxa<span className="text-ember-400">Hire</span>
          </span>
        </Link>

        {/* Eyebrow */}
        <div className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-cream-100/15 bg-cream-100/5 px-4 py-1.5">
          <Sparkles className="h-3.5 w-3.5 text-ember-400" />
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-ember-400">
            AI job matching for candidates
          </span>
        </div>

        {/* Headline */}
        <h2 className="font-display mb-5 text-4xl font-bold leading-[1.1] tracking-tight xl:text-5xl">
          {headline}
        </h2>
        <p className="mb-10 max-w-xl text-base leading-8 text-cream-100/65 xl:text-lg">{subtext}</p>

        {/* Metrics */}
        <div className="mb-10 grid grid-cols-3 gap-4">
          {METRICS.map((m) => (
            <div key={m.label} className="rounded-2xl border border-cream-100/10 bg-cream-100/5 px-4 py-4 backdrop-blur-sm">
              <div className="mb-1 text-2xl font-bold xl:text-3xl">{m.value}</div>
              <div className="text-[11px] uppercase tracking-[0.12em] text-cream-100/45">{m.label}</div>
            </div>
          ))}
        </div>

        {/* Feature list */}
        <div className="space-y-4 rounded-2xl border border-cream-100/8 bg-cream-100/5 p-6">
          {POINTS.map((point) => (
            <div key={point} className="flex items-start gap-3">
              <div className="mt-0.5 flex-shrink-0 rounded-lg bg-brand-turquoise-400/15 p-1.5 text-brand-turquoise-300">
                <CheckCircle2 size={15} />
              </div>
              <span className="text-sm leading-6 text-cream-100/70">{point}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
