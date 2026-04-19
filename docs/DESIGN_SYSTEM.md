# VeloxaHire Design System

Last updated: 2026-04-19

This document describes the editorial design system that powers the VeloxaHire
marketing surface (landing page + auth screens). It is the single source of truth
for typography, color, voice, motion, and shadcn-compatible tokens.

If you're about to add a new marketing section, component, or CTA: read this first.

---

## 1. Design philosophy

VeloxaHire is a candidate-side product in a market full of shouty,
keyword-stuffed job boards. The design has to do the opposite of that.

Three principles, in order of priority:

1. **Calm** — cream canvas, generous whitespace, no confetti, no 5-color
   gradients, no neon CTAs. The candidate is exhausted when they arrive.
   The page should feel like an exhale.
2. **Editorial, not SaaS-templated** — we use a serif display font, italics
   for emphasis, and magazine-like rhythm. It should feel curated, not
   auto-generated.
3. **Real outcomes, not technical claims** — every headline and paragraph
   names something the candidate *gets* (a shortlist, their Monday back,
   peace of mind). Engineering vocabulary (embeddings, re-rankers, signed
   URLs, rescan cadence) is banned from marketing copy.

If a change makes the page louder, busier, or more technical, it is almost
always the wrong change.

---

## 2. Typography

### 2.1 Typefaces

| Role | Family | Variable | CSS var | Tailwind class |
| --- | --- | --- | --- | --- |
| Display (all headlines, wordmark) | **Fraunces** (variable serif, `normal` + `italic`) | Yes | `--font-fraunces` | `font-display`, `font-serif` |
| Body, UI, nav, form text | **Inter** (variable) | Yes | `--font-inter` | `font-sans` (default) |

Both fonts are loaded through `next/font/google` in `frontend/app/layout.tsx`
with `display: 'swap'` so first paint is never blocked.

```frontend/app/layout.tsx
const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

const fraunces = Fraunces({
  subsets: ['latin'],
  variable: '--font-fraunces',
  style: ['normal', 'italic'],
  display: 'swap',
})
```

### 2.2 Headline scale

All marketing headlines use `font-display` (Fraunces) with `tracking-tight` and
`leading-[1.05]` unless otherwise noted.

| Level | Tailwind classes | Use |
| --- | --- | --- |
| Hero (h1) | `font-display font-bold text-5xl sm:text-7xl md:text-[6.5rem] leading-[0.95] tracking-tight` | Hero only |
| Section (h2) | `font-display font-bold text-4xl sm:text-5xl leading-[1.05] tracking-tight` | One per section |
| Feature card (h3, large) | `font-display font-semibold text-2xl leading-tight` | Wide bento card |
| Feature card (h3, default) | `font-display font-semibold text-xl` | Narrow bento cards, steps |
| FAQ question | `font-display font-semibold text-lg` | FAQ accordion |

### 2.3 Italic emphasis

Italics are a real tool in this system — they do the work a coloured
pull-quote would in a SaaS site. Recommended pattern:

```tsx
<h2 className="font-display font-bold">
  Tell us your story once.
  <span className="block italic font-medium text-forest-600">
    We&rsquo;ll do the hunting forever.
  </span>
</h2>
```

Rules:

- Italic phrases are always a supporting clause, never the whole headline.
- Use `font-medium` (500) on italics — italic + bold at display sizes looks
  heavy.
- Colour italics with `text-forest-600` on cream backgrounds or
  `text-ember-400` on dark backgrounds.

### 2.4 Eyebrows and labels

Short uppercase labels (kicker text, eyebrows, tag pills, section numbers)
use Inter, not Fraunces:

```tsx
<p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-forest-600">
  How it works
</p>
```

Tracking of `0.22em` is intentional — tighter than a typical uppercase
Tailwind label, looser than engineering kicker text. Do not change it.

### 2.5 Body copy

- Default: `text-ink-500` at `text-base` or `text-lg` with
  `leading-relaxed`.
- On ink backgrounds: `text-cream-100/75`.
- Inline emphasis: `<strong className="font-semibold text-ink-700">…</strong>`
  (or `text-ember-400` on dark).

---

## 3. Color system

### 3.1 Palette overview

VeloxaHire has four semantic families and two legacy families. The semantic
families are what you should reach for. The legacy families stay available
only because other parts of the app (dashboard, auth forms) still reference
them.

| Family | Role | Notable stops |
| --- | --- | --- |
| `cream` | Canvas, cards, off-white on dark | `cream-50`, `cream-100`, `cream-200` |
| `ink` | Text, dark hero, dark accents | `ink-500`, `ink-700`, `ink-900` |
| `forest` | Primary brand, accent | `forest-500`, `forest-600`, `forest-700` |
| `ember` | Highlight on dark surfaces only | `ember-400`, `ember-500`, `ember-600` |
| `brand-turquoise` (legacy) | Dashboard + older screens | `brand-turquoise-600/700` |
| `brand-orange` (legacy) | Dashboard + older screens | `brand-orange-500` |

Full scales are defined in `frontend/tailwind.config.ts`.

### 3.2 Semantic guidance

Use this table when picking a color — never freestyle a hex.

| Surface | Use |
| --- | --- |
| Page canvas | `bg-cream-100` |
| Card on canvas | `bg-cream-50 border-ink-900/10` |
| Secondary band (how-it-works, FAQ) | `bg-cream-200/40 border-y border-ink-900/10` |
| Dark hero | `bg-ink-900` |
| Dark card on dark | `bg-ink-900 text-cream-100` with a `bg-forest-500/25` glow |
| Footer | `bg-forest-700` with `bg-forest-500/30` glow |
| Final CTA banner | `bg-gradient-to-br from-ink-900 via-ink-800 to-forest-700` |

| Text | Use |
| --- | --- |
| Primary (on cream) | `text-ink-900` |
| Primary (on ink / forest) | `text-cream-100` |
| Body (on cream) | `text-ink-500` |
| Body (on ink / forest) | `text-cream-100/75` |
| Muted / meta (on cream) | `text-ink-400` |
| Muted / meta (on ink / forest) | `text-cream-100/50` |
| Accent emphasis (on cream) | `text-forest-600` |
| Accent emphasis (on ink / forest) | `text-ember-400` |

| Borders | Use |
| --- | --- |
| Default on cream | `border-ink-900/10` |
| Subtle divider | `border-ink-900/5` |
| Highlighted on cream | `border-forest-500/30` |
| On dark | `border-cream-100/10` (subtle), `border-cream-100/20` (card), `border-cream-100/30` (button) |

### 3.3 Primary actions (CTAs)

| Surface | CTA |
| --- | --- |
| On cream | `bg-forest-600 hover:bg-forest-700 text-cream-100` *(via shadcn Button default)* |
| On ink / forest | `bg-cream-100 hover:bg-cream-50 text-ink-900` |
| Secondary / ghost on cream | `border border-ink-900/10 hover:border-forest-500/30 text-ink-900` |
| Secondary on dark | `border border-cream-100/25 hover:border-cream-100/50 text-cream-100/80 hover:text-cream-100` |

Rule: only **one** filled primary CTA per viewport.

### 3.4 Selection and focus

Defined globally in `frontend/app/globals.css`:

- Selection: `bg-forest-500/20 text-forest-700`
- Focus ring: 2px `outline-forest-500` with 2px offset — do not override on
  individual components unless there's a strong visual reason.

---

## 4. shadcn/ui integration

VeloxaHire is shadcn-compatible. The CSS variables in
`frontend/app/globals.css` are wired to the editorial palette so any shadcn
component dropped into `frontend/components/ui/` renders in-brand.

### 4.1 Token map

| shadcn token | Editorial meaning | HSL source |
| --- | --- | --- |
| `--background` | cream-100 (canvas) | `40 56% 95%` |
| `--foreground` | ink-900 (body text) | `156 13% 7%` |
| `--primary` | forest-600 (primary CTA fill) | `164 53% 18%` |
| `--primary-foreground` | cream-100 | `40 56% 95%` |
| `--secondary` / `--accent` / `--muted` | cream-200 band | `38 40% 87%` |
| `--muted-foreground` | ink-500 | `156 8% 27%` |
| `--border` / `--input` | faint ink on cream | `38 20% 78%` |
| `--ring` | forest-500 | `166 48% 24%` |
| `--destructive` | red (unchanged) | `0 70% 45%` |
| `--radius` | `0.5rem` (base), Tailwind also exposes `md` and `sm` via `calc()` | — |

Tailwind mappings (in `frontend/tailwind.config.ts`) expose these as
`bg-background`, `text-foreground`, `bg-primary text-primary-foreground`, etc.
New shadcn components can use these directly and will match the editorial
palette automatically.

### 4.2 Files that implement the shadcn layer

- `frontend/lib/utils.ts` — `cn()` helper (`clsx` + `tailwind-merge`).
- `frontend/components/ui/button.tsx` — stock shadcn Button with
  `default / destructive / outline / secondary / ghost / link` variants and
  `default / sm / lg / icon` sizes. Supports `asChild` for use with
  `next/link`.
- `frontend/components/ui/background-paths.tsx` — hero component. Dark-only
  fork of the 21st.dev "BackgroundPaths" template; the `dark:` utilities
  were intentionally removed because the rest of the marketing page is
  light-themed.

We do **not** have a dark theme variant of the editorial palette. Dark
surfaces (hero, CV-privacy card, final CTA, footer) hard-code ink/forest/
cream values directly. If a future feature needs app-wide dark mode, add a
`.dark` token block in `globals.css` — but keep the marketing surface
light-only unless there's a reason.

---

## 5. Layout rhythm

- Page container: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` (nav, footer).
- Section container: `max-w-6xl mx-auto` for most content, `max-w-3xl` for
  FAQ, `max-w-4xl` for centered hero body, `max-w-2xl` for the demo card
  and copy-heavy blocks.
- Vertical rhythm: `py-24` between major sections, `py-10`–`py-20` for
  transitional strips.
- Cards: `rounded-2xl` or `rounded-3xl`. Avoid square corners and avoid
  rounded-full on blocks.
- Buttons: always `rounded-full` on marketing. Dashboard CTAs can use
  shadcn's `rounded-md` default.

Each section alternates its background to give the page rhythm:

1. `bg-ink-900` (hero)
2. `bg-cream-50` (thin reassurance strip)
3. `bg-cream-100` (demo, how-it-works, testimonial, final CTA wrapper)
4. `bg-cream-200/40` (features bento, FAQ)
5. `bg-forest-700` (footer)

Never put two sections with the same background next to each other.

---

## 6. Motion

Motion is provided by `framer-motion`. Rules:

- Every animated element must respect `useReducedMotion()` — see
  `HomePage` for the `fadeUp` pattern (`initial` falls back to `false` when
  motion is reduced).
- Default entrance: `initial={{ opacity: 0, y: 16 }}` → `{ opacity: 1, y: 0 }`
  with `duration: 0.5, ease: 'easeOut'`.
- Hero paths: `motion.path` with a 20–30s linear loop (see
  `FloatingPaths`). Do not speed this up — it's meant to be barely
  perceptible.
- Hero text: letter-by-letter spring entrance with
  `stiffness: 150, damping: 25`. Delay per letter is `0.025s`. Do not
  stagger on secondary headlines; it looks busy.
- Demo "scanning" bar: 2.4s looped `width: 0% -> 100%`. Read as a live
  system, not as a decoration.
- Card hover: raise via `hover:-translate-y-0.5` + subtle shadow. Never
  scale.

---

## 7. Iconography

- Library: `lucide-react`. No other icon libraries.
- Semantic choices we've committed to:
  - `Target` — precision / matching
  - `Layers` — the three tiers
  - `Crosshair` — "tell us what you want"
  - `LineChart` — "open your shortlist" (progress)
  - `FileText` — CV upload
  - `ShieldCheck` — privacy assurance (reassurance strip under the hero)
  - `Quote` — testimonial
  - `Linkedin`, `Mail`, `Phone`, `MapPin` — footer contact
  - `CheckCircle2` — trust strip under hero
- Icon chip pattern on cream: `w-11 h-11 rounded-xl bg-forest-500/10 border border-forest-500/20` containing `w-5 h-5 text-forest-600`.
- Icon chip pattern on dark: `w-11 h-11 rounded-xl bg-cream-100/10 border border-cream-100/15` containing `w-5 h-5 text-ember-400`.
- Do not invent new icons; if none of the above fit, push back on the copy.

---

## 8. Logo and wordmark

- Logo file: `frontend/public/logo.png` (canonical source:
  `frontend/logo/logo.png`). Always render through `next/image` with
  `priority` when above the fold.
- Wordmark component in `frontend/app/page.tsx`:

  ```tsx
  function WordMark({ className = '' }) {
    return (
      <span className={`font-display font-semibold tracking-tight ${className}`}>
        Veloxa<span className="italic font-light">Hire</span>
      </span>
    )
  }
  ```

  `Hire` is lighter weight and italic — this is the locked signature of the
  brand. Do not regular-case it, do not all-caps it, do not swap the
  italic.

- Always pair the logo icon with the wordmark when space allows. Solo logo
  icon is acceptable in a 32 px favicon and nowhere else.

---

## 9. Voice and copy rules

This is where most brand drift happens, so be strict.

### 9.1 Tone

- Warm, quiet, candidate-first. Think "a friend who works in recruitment"
  rather than "a growth-hacked SaaS".
- Short sentences. Use the em-dash freely — it's part of the voice.
- Use contractions (`we'll`, `you're`, `don't`).

### 9.2 Banned vocabulary (marketing surface only)

Do not ship any of these words to the landing page, auth screens, or
marketing emails:

> embeddings, re-ranker, LLM, vector, semantic search, cadence, rescan,
> aggregate, signed URL, per-user isolation, pipeline, orchestration,
> fine-tune, parse, inference, scoring function, keyword density

If a feature description seems to require one of these, rewrite it as an
outcome. Example from the features bento:

- Bad: "Embeddings + an LLM re-ranker weigh title alignment, skill
  overlap, seniority and freshness."
- Good: "A good recruiter reads a job spec end to end and thinks 'would
  this person be happy here?' We do the same, quietly, for thousands of
  roles."

### 9.3 CTA copy

- Primary on hero: **"Build my shortlist — it's free"**
- Primary on final banner: **"Build my shortlist"**
- Secondary everywhere: **"See how it works"** or **"I've got an account"**

Never use "Sign up", "Get started now", "Try it free" — they're SaaS
defaults and dilute the voice.

### 9.4 Person

- First person singular for CTAs ("Build **my** shortlist", "See **my**
  matches"). First person plural for promises we make ("**We'll** read
  between the lines").
- Never "users" or "candidates" in body copy — use "you".

---

## 10. Responsive rules

- All sections must work at **375 px** (iPhone SE) width.
- Hero drops to `text-5xl` on narrow screens — acceptable because the
  viewport is still visually anchored by the background paths.
- Bento grid collapses to a single column below `md`. Order: wide "meaning"
  card first, then tiers, rescan, tracker, privacy.
- Footer grid collapses to a single column below `md` with the contact
  block first.
- Mobile nav: hamburger opens a vertical stack inside the same dark-glass
  bar. Do not introduce a full-screen overlay.

---

## 11. File index

Design-system-relevant files:

| Concern | File |
| --- | --- |
| Typography loading | `frontend/app/layout.tsx` |
| CSS tokens + base styles | `frontend/app/globals.css` |
| Tailwind palette + fonts | `frontend/tailwind.config.ts` |
| `cn()` helper | `frontend/lib/utils.ts` |
| shadcn Button | `frontend/components/ui/button.tsx` |
| Hero component | `frontend/components/ui/background-paths.tsx` |
| Landing page (all sections) | `frontend/app/page.tsx` |
| Auth screens (use same palette) | `frontend/app/auth/login/page.tsx`, `frontend/app/auth/signup/page.tsx` |
| Dashboard shell (legacy palette, do not migrate without a plan) | `frontend/components/layout/DashboardLayout.tsx` |

---

## 12. Extending the system

When adding a new marketing section, in order:

1. Pick the section background from the rhythm table in §5.
2. Pick the headline (Fraunces display, bold, section scale) and one
   italic accent phrase.
3. Write the body copy — then re-read it with the banned-vocabulary list
   from §9.2 in mind.
4. Choose two icons max from §7. If you need a third, cut a word from your
   copy instead.
5. Use `fadeUp` for entrance animation. Respect `useReducedMotion`.
6. Run `npm run type-check` and `npm run build`. Visual verify at 375 px,
   768 px, 1440 px.
7. If you introduce a new Tailwind utility or color, add it to this
   document in the same PR.

If you're tempted to add a new color, a new font, or a new animation
style: the answer is almost always "don't". The restraint is what makes
the brand feel real.
