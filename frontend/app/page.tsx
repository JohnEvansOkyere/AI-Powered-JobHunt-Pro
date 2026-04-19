'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { motion, useReducedMotion } from 'framer-motion'
import {
  ArrowRight,
  Target,
  ShieldCheck,
  CheckCircle2,
  FileText,
  Layers,
  Crosshair,
  LineChart,
  Quote,
  Mail,
  Phone,
  MapPin,
  Linkedin,
  Menu,
  X,
  ChevronDown,
} from 'lucide-react'
import { BackgroundPaths } from '@/components/ui/background-paths'

// ---------------------------------------------------------------------------
// Small building blocks
// ---------------------------------------------------------------------------

function WordMark({ className = '' }: { className?: string }) {
  return (
    <span className={`font-display font-semibold tracking-tight ${className}`}>
      Veloxa<span className="italic font-light">Hire</span>
    </span>
  )
}

function Logo({ size = 32 }: { size?: number }) {
  return (
    <Image
      src="/logo.png"
      alt="VeloxaHire"
      width={size}
      height={size}
      priority
      className="object-contain"
    />
  )
}

// Minimal "live match" tile shown inside the demo card.
function MatchTile({
  title,
  company,
  location,
  score,
  highlight,
  delay = 0,
}: {
  title: string
  company: string
  location: string
  score: number
  highlight?: boolean
  delay?: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className={`rounded-xl border px-4 py-3 flex items-center justify-between gap-4 ${
        highlight
          ? 'border-forest-500/30 bg-forest-500/5'
          : 'border-ink-900/10 bg-cream-50'
      }`}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border ${
              highlight
                ? 'bg-forest-600 text-cream-100 border-forest-600'
                : 'bg-cream-100 text-ink-500 border-ink-900/10'
            }`}
          >
            {score}% match
          </span>
          {highlight && (
            <span className="inline-flex items-center gap-1 text-[11px] text-ember-700 bg-ember-500/15 border border-ember-500/30 rounded-md px-2 py-0.5 font-semibold uppercase tracking-wider">
              Top pick
            </span>
          )}
        </div>
        <p className="text-sm font-semibold text-ink-900 mt-1.5 truncate">{title}</p>
        <p className="text-xs text-ink-500 truncate">
          {company} · {location}
        </p>
      </div>
      <ArrowRight className="w-4 h-4 text-ink-400 flex-shrink-0" />
    </motion.div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function HomePage() {
  const { isAuthenticated, loading } = useAuth()
  const router = useRouter()
  const reduceMotion = useReducedMotion()
  const [navOpen, setNavOpen] = useState(false)
  const [openFaq, setOpenFaq] = useState<number | null>(0)

  useEffect(() => {
    if (!loading && isAuthenticated) router.push('/dashboard')
  }, [isAuthenticated, loading, router])

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-cream-100">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-forest-600" />
      </main>
    )
  }

  const fadeUp = reduceMotion
    ? {}
    : {
        initial: { opacity: 0, y: 16 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true, margin: '-80px' },
        transition: { duration: 0.5, ease: 'easeOut' },
      }

  return (
    <div className="min-h-screen bg-cream-100 text-ink-900 selection:bg-forest-500/20 selection:text-forest-700">
      {/* ================================================================ */}
      {/* Nav — dark-glass so it reads over the ink hero and the cream body */}
      {/* ================================================================ */}
      <nav className="fixed top-0 inset-x-0 z-50 backdrop-blur-md bg-ink-900/70 border-b border-cream-100/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-2.5 group">
              <Logo size={30} />
              <WordMark className="text-base text-cream-100 group-hover:text-ember-400 transition-colors" />
            </Link>

            <div className="hidden md:flex items-center gap-8 text-sm">
              <Link
                href="#how"
                className="text-cream-100/70 hover:text-cream-100 transition-colors"
              >
                How it works
              </Link>
              <Link
                href="#features"
                className="text-cream-100/70 hover:text-cream-100 transition-colors"
              >
                Features
              </Link>
              <Link
                href="#faq"
                className="text-cream-100/70 hover:text-cream-100 transition-colors"
              >
                FAQ
              </Link>
              <Link
                href="#contact"
                className="text-cream-100/70 hover:text-cream-100 transition-colors"
              >
                Contact
              </Link>
            </div>

            <div className="hidden md:flex items-center gap-2">
              <Link
                href="/auth/login"
                className="px-4 py-2 text-sm font-medium text-cream-100/80 hover:text-cream-100 transition-colors rounded-lg"
              >
                Sign in
              </Link>
              <Link
                href="/auth/signup"
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-ink-900 bg-cream-100 hover:bg-cream-50 rounded-full shadow-sm transition-colors"
              >
                Get started
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <button
              onClick={() => setNavOpen((v) => !v)}
              className="md:hidden p-2 -mr-2 text-cream-100"
              aria-label="Toggle menu"
            >
              {navOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
          {navOpen && (
            <div className="md:hidden border-t border-cream-100/10 py-4 space-y-2 text-sm">
              {[
                ['How it works', '#how'],
                ['Features', '#features'],
                ['FAQ', '#faq'],
                ['Contact', '#contact'],
              ].map(([label, href]) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setNavOpen(false)}
                  className="block px-2 py-2 text-cream-100/80"
                >
                  {label}
                </Link>
              ))}
              <div className="flex gap-2 pt-2 border-t border-cream-100/10">
                <Link
                  href="/auth/login"
                  className="flex-1 text-center py-2 border border-cream-100/30 rounded-full font-medium text-cream-100"
                >
                  Sign in
                </Link>
                <Link
                  href="/auth/signup"
                  className="flex-1 text-center py-2 bg-cream-100 text-ink-900 rounded-full font-semibold"
                >
                  Get started
                </Link>
              </div>
            </div>
          )}
        </div>
      </nav>

      {/* ================================================================ */}
      {/* Hero — dark ink background, off-white serif title                */}
      {/* ================================================================ */}
      <BackgroundPaths
        eyebrow="Built for candidates, not job boards"
        title="Find the job that fits you"
        lede="Upload your CV once. We'll read between the lines, learn what you actually want next, and hand you a short, honest shortlist of roles worth your Monday morning."
        ctaLabel="Build my shortlist — it's free"
        ctaHref="/auth/signup"
        secondaryCtaLabel="See how it works"
        secondaryCtaHref="#how"
      />

      {/* ================================================================ */}
      {/* Quiet reassurance bullets — sit below the hero                   */}
      {/* ================================================================ */}
      <section className="py-8 px-4 sm:px-6 lg:px-8 border-b border-ink-900/10 bg-cream-50">
        <div className="max-w-4xl mx-auto flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-sm text-ink-500">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-forest-500" />
            Free to start
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-forest-500" />
            No credit card
          </div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-forest-500" />
            Your CV stays private
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Live-match demo                                                  */}
      {/* ================================================================ */}
      <section className="relative py-24 px-4 sm:px-6 lg:px-8 overflow-hidden">
        <div className="max-w-3xl mx-auto text-center mb-14">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-forest-600">
            A peek inside your shortlist
          </p>
          <h2 className="mt-4 font-display font-bold text-4xl sm:text-5xl leading-[1.05] tracking-tight text-ink-900">
            The jobs worth your time,{' '}
            <span className="italic font-medium text-forest-600">waiting</span> when you log in.
          </h2>
          <p className="mt-5 text-base sm:text-lg text-ink-500 leading-relaxed">
            No endless scrolling. No twenty tabs open. Just a short list you can actually read over
            coffee &mdash; with the best roles already at the top.
          </p>
        </div>

        <div className="max-w-2xl mx-auto">
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
          >
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-br from-forest-500/15 to-ember-500/10 rounded-[2.5rem] blur-2xl -z-10" />

              <div className="bg-cream-50 rounded-3xl border border-ink-900/10 shadow-xl shadow-ink-900/5 overflow-hidden">
                <div className="flex items-center gap-2 px-5 py-3 border-b border-ink-900/10 bg-cream-100">
                  <span className="w-2.5 h-2.5 rounded-full bg-ink-900/10" />
                  <span className="w-2.5 h-2.5 rounded-full bg-ink-900/10" />
                  <span className="w-2.5 h-2.5 rounded-full bg-ink-900/10" />
                  <span className="ml-3 text-xs text-ink-500 font-medium">
                    Your matches · updated just now
                  </span>
                </div>

                <div className="p-5 space-y-3 bg-cream-50">
                  <MatchTile
                    title="Senior Data Scientist — ML"
                    company="Northwind Labs"
                    location="Remote"
                    score={96}
                    highlight
                    delay={0.2}
                  />
                  <MatchTile
                    title="Applied AI Engineer"
                    company="Lumen AI"
                    location="Hybrid · London"
                    score={88}
                    delay={0.35}
                  />
                  <MatchTile
                    title="Machine Learning Scientist"
                    company="Wave"
                    location="Remote"
                    score={82}
                    delay={0.5}
                  />

                  <div className="pt-2">
                    <div className="flex items-center justify-between text-xs text-ink-500 mb-2">
                      <span>Scanning 8,421 new roles</span>
                      <span className="font-semibold text-forest-600">Live</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-cream-200 overflow-hidden">
                      <motion.div
                        initial={{ width: '0%' }}
                        animate={{ width: ['0%', '100%'] }}
                        transition={{
                          duration: 2.4,
                          repeat: Infinity,
                          ease: 'easeInOut',
                        }}
                        className="h-full bg-gradient-to-r from-forest-500 to-forest-700"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <motion.div
                initial={reduceMotion ? false : { opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="hidden md:flex absolute -bottom-6 -left-6 bg-cream-50 rounded-2xl border border-ink-900/10 shadow-lg p-4 items-center gap-3"
              >
                <div className="w-10 h-10 rounded-xl bg-forest-500/10 border border-forest-500/20 flex items-center justify-center">
                  <Target className="w-5 h-5 text-forest-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-ink-900">3× more interviews</p>
                  <p className="text-xs text-ink-500">Average across early users</p>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Trust strip                                                      */}
      {/* ================================================================ */}
      <section className="py-10 border-y border-ink-900/10 bg-cream-200/40">
        <div className="max-w-6xl mx-auto px-4 flex flex-col md:flex-row items-center justify-center gap-4 md:gap-10 text-xs">
          <span className="uppercase tracking-[0.22em] font-semibold text-ink-500">
            Trusted across the Veloxa family
          </span>
          <div className="flex flex-wrap items-center justify-center gap-6 md:gap-10 font-display font-semibold text-ink-500">
            <span>Veloxa Recruit</span>
            <span className="w-1 h-1 rounded-full bg-ink-500/40 hidden md:block" />
            <span>VeloxaHire</span>
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* How it works                                                     */}
      {/* ================================================================ */}
      <section id="how" className="py-24 px-4 sm:px-6 lg:px-8 bg-cream-100">
        <div className="max-w-6xl mx-auto">
          <motion.div {...fadeUp} className="max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-forest-600">
              How it works
            </p>
            <h2 className="mt-4 font-display font-bold text-4xl sm:text-5xl leading-[1.05] tracking-tight text-ink-900">
              Tell us your story once.
              <span className="block italic font-medium text-forest-600">
                We&rsquo;ll do the hunting forever.
              </span>
            </h2>
            <p className="mt-5 text-ink-500 leading-relaxed text-lg">
              Three small steps on your side. After that we keep watch on every new role posted
              &mdash; and only tap you on the shoulder when something&rsquo;s genuinely worth it.
            </p>
          </motion.div>

          <div className="mt-16 grid md:grid-cols-3 gap-6">
            {[
              {
                n: '01',
                icon: FileText,
                title: 'Bring your CV',
                body:
                  "Drop it in. We'll turn it into a profile you can tidy, tweak, or add to — no retyping, no forms that go on forever.",
              },
              {
                n: '02',
                icon: Crosshair,
                title: 'Tell us what good looks like',
                body:
                  "The kind of role, where you'd love to work, remote or office, the salary you're after. The clearer you are, the better we get at finding you the right ones.",
              },
              {
                n: '03',
                icon: LineChart,
                title: 'Open your shortlist',
                body:
                  "While you get on with life, we're reading thousands of new roles for you — and saving only the ones that actually fit. You open it like opening your inbox, calmly.",
              },
            ].map((step, i) => (
              <motion.div
                key={step.n}
                {...fadeUp}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="relative rounded-2xl border border-ink-900/10 bg-cream-50 p-8 hover:border-forest-500/30 hover:shadow-sm transition-all"
              >
                <span className="font-display text-sm font-semibold tracking-[0.18em] text-ember-600">
                  {step.n}
                </span>
                <div className="mt-5 w-11 h-11 rounded-xl bg-forest-500/10 border border-forest-500/20 flex items-center justify-center">
                  <step.icon className="w-5 h-5 text-forest-600" />
                </div>
                <h3 className="mt-6 font-display font-semibold text-xl text-ink-900">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm text-ink-500 leading-relaxed">{step.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Features bento                                                   */}
      {/* ================================================================ */}
      <section
        id="features"
        className="py-24 px-4 sm:px-6 lg:px-8 bg-cream-200/40 border-y border-ink-900/10"
      >
        <div className="max-w-6xl mx-auto">
          <motion.div {...fadeUp} className="max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-forest-600">
              What you get
            </p>
            <h2 className="mt-4 font-display font-bold text-4xl sm:text-5xl leading-[1.05] tracking-tight text-ink-900">
              A calmer,{' '}
              <span className="italic font-medium text-forest-600">kinder</span> way to job-hunt.
            </h2>
            <p className="mt-5 text-ink-500 leading-relaxed text-lg max-w-xl">
              You&rsquo;re not looking for a thousand jobs. You&rsquo;re looking for the right one.
              Here&rsquo;s how VeloxaHire helps you get there without the burnout.
            </p>
          </motion.div>

          <div className="mt-16 grid md:grid-cols-6 gap-5">
            <motion.div
              {...fadeUp}
              className="md:col-span-4 rounded-2xl bg-cream-50 border border-ink-900/10 p-8 flex flex-col justify-between min-h-[280px]"
            >
              <div>
                <div className="w-11 h-11 rounded-xl bg-forest-500/10 border border-forest-500/20 flex items-center justify-center">
                  <Target className="w-5 h-5 text-forest-600" />
                </div>
                <h3 className="mt-6 font-display font-semibold text-2xl text-ink-900 leading-tight">
                  We read the job. We don&rsquo;t just match words.
                </h3>
                <p className="mt-3 text-ink-500 text-sm leading-relaxed max-w-lg">
                  A good recruiter reads a job spec end to end and thinks &ldquo;would this person
                  be happy here?&rdquo; We do the same &mdash; quietly, for thousands of roles,
                  every day. So when something lands at the top of your list, there&rsquo;s a
                  proper reason.
                </p>
              </div>
              <div className="mt-6 flex flex-wrap gap-2">
                {[
                  'Right kind of role',
                  'Your skills',
                  'Right level',
                  'Fresh today',
                  'Remote-friendly',
                ].map((t) => (
                  <span
                    key={t}
                    className="text-xs font-medium bg-cream-100 border border-ink-900/10 text-ink-500 rounded-full px-2.5 py-1"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </motion.div>

            <motion.div
              {...fadeUp}
              transition={{ duration: 0.5, delay: 0.05 }}
              className="md:col-span-2 rounded-2xl bg-cream-50 border border-ink-900/10 p-8 min-h-[280px] flex flex-col"
            >
              <div className="w-11 h-11 rounded-xl bg-forest-500/10 border border-forest-500/20 flex items-center justify-center">
                <Layers className="w-5 h-5 text-forest-600" />
              </div>
              <h3 className="mt-6 font-display font-semibold text-xl text-ink-900">
                Know where to look first.
              </h3>
              <p className="mt-3 text-sm text-ink-500 leading-relaxed">
                Your <strong className="font-semibold text-ink-700">Top picks</strong> for busy
                days, <strong className="font-semibold text-ink-700">strong fits</strong> when you
                want to explore, and a fresh catalogue of everything new &mdash; so you never miss
                the door you didn&rsquo;t know was open.
              </p>
            </motion.div>

          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Testimonial + stats                                              */}
      {/* ================================================================ */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-cream-100">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-16 items-center">
          <motion.div {...fadeUp}>
            <div className="w-10 h-10 rounded-xl bg-forest-500/10 border border-forest-500/20 flex items-center justify-center mb-7">
              <Quote className="w-5 h-5 text-forest-600" />
            </div>
            <p className="font-display text-3xl sm:text-4xl text-ink-900 leading-[1.15] tracking-tight">
              <span className="italic text-ink-500">&ldquo;</span>
              I was spending evenings refreshing job boards. VeloxaHire does that for me now, and
              it picks <em className="text-forest-600 not-italic font-medium">better</em> than I do.
              I stopped guessing which roles were worth my time.
              <span className="italic text-ink-500">&rdquo;</span>
            </p>
            <div className="mt-7 flex items-center gap-3">
              <div className="w-11 h-11 rounded-full bg-forest-500/15 border border-forest-500/20 flex items-center justify-center font-display font-semibold text-forest-700">
                P
              </div>
              <div>
                <p className="font-semibold text-ink-900">Nana Kwasi Agyeman, Senior ML Engineer</p>
                <p className="text-sm text-ink-500">Early-access user</p>
              </div>
            </div>
          </motion.div>

          <motion.div {...fadeUp} className="grid grid-cols-2 gap-5">
            {[
              { big: '3×', small: 'More interviews worth taking' },
              { big: '10h', small: 'Hours handed back to your week' },
              { big: '2×', small: 'Fresh shortlists, every day' },
              { big: '96%', small: 'Top picks candidates open' },
            ].map((s) => (
              <div
                key={s.small}
                className="rounded-2xl border border-ink-900/10 bg-cream-50 p-6 hover:border-forest-500/30 transition-colors"
              >
                <p className="font-display text-4xl sm:text-5xl font-bold tracking-tight text-forest-600">
                  {s.big}
                </p>
                <p className="mt-3 text-xs font-semibold uppercase tracking-[0.18em] text-ink-500">
                  {s.small}
                </p>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* FAQ                                                              */}
      {/* ================================================================ */}
      <section
        id="faq"
        className="py-24 px-4 sm:px-6 lg:px-8 bg-cream-200/40 border-y border-ink-900/10"
      >
        <div className="max-w-3xl mx-auto">
          <motion.div {...fadeUp} className="text-center">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-forest-600">
              FAQ
            </p>
            <h2 className="mt-4 font-display font-bold text-4xl sm:text-5xl leading-[1.05] tracking-tight text-ink-900">
              Honest <span className="italic font-medium text-forest-600">answers.</span>
            </h2>
          </motion.div>

          <div className="mt-14 space-y-3">
            {[
              {
                q: 'Is VeloxaHire really free?',
                a: "Yes. Signing up, uploading your CV, and getting your shortlist costs nothing. We'll add optional power-user features later, but finding you good jobs will always have a free plan — candidates shouldn't pay to be seen.",
              },
              {
                q: 'Who can see my CV?',
                a: "Only you. Your CV is locked to your account. No recruiter, no employer, nobody in the \u201cVeloxa family\u201d can peek at it. An employer only sees your profile when you click apply. And if you change your mind, one click deletes the lot.",
              },
              {
                q: 'How is this different from a job board?',
                a: "Job boards list everything and leave you to sift. We read each role the way a recruiter would, compare it to you, and only put the genuine fits in front of you. Less scrolling, better jobs — every time.",
              },
              {
                q: 'Where do the jobs come from?',
                a: "From the big job boards, specialist sites, and roles our partners across the Veloxa family are hiring for. You get a full picture of the market — in one calm list, refreshed twice a day.",
              },
              {
                q: 'Will I get spammed?',
                a: "No. VeloxaHire doesn't share your email with anyone. We'll only email you when there's something genuinely worth your time — and you can dial that down to weekly in one click.",
              },
            ].map((f, i) => {
              const open = openFaq === i
              return (
                <motion.div
                  key={f.q}
                  {...fadeUp}
                  transition={{ duration: 0.35, delay: i * 0.05 }}
                  className={`rounded-xl border bg-cream-50 overflow-hidden transition-colors ${
                    open ? 'border-forest-500/30' : 'border-ink-900/10'
                  }`}
                >
                  <button
                    onClick={() => setOpenFaq(open ? null : i)}
                    className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left"
                  >
                    <span className="font-display font-semibold text-lg text-ink-900">
                      {f.q}
                    </span>
                    <ChevronDown
                      className={`w-4 h-4 text-ink-400 transition-transform flex-shrink-0 ${
                        open ? 'rotate-180 text-forest-600' : ''
                      }`}
                    />
                  </button>
                  <motion.div
                    initial={false}
                    animate={{
                      height: open ? 'auto' : 0,
                      opacity: open ? 1 : 0,
                    }}
                    transition={{ duration: 0.25 }}
                    className="overflow-hidden"
                  >
                    <p className="px-5 pb-5 text-sm text-ink-500 leading-relaxed">{f.a}</p>
                  </motion.div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Final CTA — deep ink + forest gradient, mirrors the hero          */}
      {/* ================================================================ */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-cream-100">
        <motion.div
          {...fadeUp}
          className="max-w-5xl mx-auto rounded-3xl bg-gradient-to-br from-ink-900 via-ink-800 to-forest-700 text-cream-100 px-8 py-16 md:py-20 md:px-16 relative overflow-hidden"
        >
          <div className="absolute -top-20 -right-20 w-80 h-80 rounded-full bg-ember-500/20 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 w-80 h-80 rounded-full bg-forest-500/25 blur-3xl" />
          <div className="relative z-10 max-w-2xl">
            <h2 className="font-display font-bold text-4xl sm:text-5xl tracking-tight leading-[1.05]">
              The best job you&rsquo;ll have next year is{' '}
              <span className="italic font-medium text-ember-400">
                probably posted this week.
              </span>
            </h2>
            <p className="mt-6 text-cream-100/75 text-lg max-w-xl leading-relaxed">
              Let VeloxaHire find it quietly in the background. Sign up in under a minute &mdash;
              the first shortlist is on us.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Link
                href="/auth/signup"
                className="inline-flex items-center gap-2 px-7 py-3.5 bg-cream-100 text-ink-900 rounded-full font-semibold hover:bg-cream-50 transition-colors shadow-sm"
              >
                Build my shortlist
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/auth/login"
                className="inline-flex items-center gap-2 px-7 py-3.5 border border-cream-100/30 text-cream-100 rounded-full font-semibold hover:bg-cream-100/10 transition-colors"
              >
                I&rsquo;ve got an account
              </Link>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ================================================================ */}
      {/* Footer — forest-green canvas, cream text, ember accents          */}
      {/* ================================================================ */}
      <footer id="contact" className="relative bg-forest-700 text-cream-100/85 overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              'radial-gradient(circle at 1px 1px, rgba(247,243,236,1) 1px, transparent 0)',
            backgroundSize: '28px 28px',
          }}
        />
        <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-forest-500/30 blur-3xl pointer-events-none" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-10">
          <div className="grid md:grid-cols-12 gap-12">
            <div className="md:col-span-5">
              <Link href="/" className="flex items-center gap-2.5">
                <Logo size={36} />
                <WordMark className="text-lg text-cream-100" />
              </Link>
              <p className="mt-5 text-sm text-cream-100/70 leading-relaxed max-w-sm">
                VeloxaHire is the candidate-side platform of the Veloxa family — built with the
                same hiring specialists behind Veloxa Recruit.
              </p>
              <div className="mt-7 space-y-3 text-sm">
                <a
                  href="mailto:hello@veloxarecruit.com"
                  className="flex items-center gap-3 text-cream-100/80 hover:text-ember-400 transition-colors"
                >
                  <Mail className="w-4 h-4 text-ember-500" />
                  hello@veloxarecruit.com
                </a>
                <div className="flex items-start gap-3 text-cream-100/80">
                  <Phone className="w-4 h-4 text-ember-500 mt-0.5 flex-shrink-0" />
                  <span className="flex flex-wrap items-center gap-x-2">
                    <a
                      href="tel:+233544954643"
                      className="hover:text-ember-400 transition-colors"
                    >
                      +233 544 954 643
                    </a>
                    <span className="text-cream-100/40">/</span>
                    <a
                      href="tel:+233556272090"
                      className="hover:text-ember-400 transition-colors"
                    >
                      +233 556 272 090
                    </a>
                  </span>
                </div>
                <a
                  href="https://www.linkedin.com/company/veloxa-technology-limited"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 text-cream-100/80 hover:text-ember-400 transition-colors"
                >
                  <Linkedin className="w-4 h-4 text-ember-500" />
                  Veloxa Technology Limited
                </a>
                <div className="flex items-start gap-3 text-cream-100/80">
                  <MapPin className="w-4 h-4 text-ember-500 mt-0.5 flex-shrink-0" />
                  <span>Accra, Ghana</span>
                </div>
              </div>
            </div>

            <div className="md:col-span-2">
              <h4 className="font-display text-xs font-semibold uppercase tracking-[0.22em] text-ember-400 mb-5">
                Product
              </h4>
              <ul className="space-y-3 text-sm text-cream-100/80">
                <li>
                  <Link href="#how" className="hover:text-ember-400 transition-colors">
                    How it works
                  </Link>
                </li>
                <li>
                  <Link href="#features" className="hover:text-ember-400 transition-colors">
                    Features
                  </Link>
                </li>
                <li>
                  <Link href="#faq" className="hover:text-ember-400 transition-colors">
                    FAQ
                  </Link>
                </li>
                <li>
                  <Link href="/auth/signup" className="hover:text-ember-400 transition-colors">
                    Create account
                  </Link>
                </li>
              </ul>
            </div>

            <div className="md:col-span-2">
              <h4 className="font-display text-xs font-semibold uppercase tracking-[0.22em] text-ember-400 mb-5">
                Family
              </h4>
              <ul className="space-y-3 text-sm text-cream-100/80">
                <li>
                  <a
                    href="https://veloxarecruit.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-ember-400 transition-colors"
                  >
                    Veloxa Recruit
                  </a>
                </li>
                <li>
                  <Link href="/" className="hover:text-ember-400 transition-colors">
                    VeloxaHire
                  </Link>
                </li>
              </ul>
            </div>

            <div className="md:col-span-3">
              <h4 className="font-display text-xs font-semibold uppercase tracking-[0.22em] text-ember-400 mb-5">
                Legal
              </h4>
              <ul className="space-y-3 text-sm text-cream-100/80">
                <li>
                  <Link href="#" className="hover:text-ember-400 transition-colors">
                    Privacy policy
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-ember-400 transition-colors">
                    Terms of service
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-ember-400 transition-colors">
                    Cookie policy
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-16 pt-6 border-t border-cream-100/10 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-cream-100/55">
              &copy; {new Date().getFullYear()} VeloxaHire. Part of the Veloxa family. All rights
              reserved.
            </p>
            <p className="text-xs text-cream-100/45 font-display italic">
              Built in Accra · for candidates, not recruiters.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
