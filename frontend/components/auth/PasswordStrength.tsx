'use client'

import { Check, X } from 'lucide-react'

export interface PwChecks {
  length: boolean
  upper: boolean
  number: boolean
  special: boolean
}

export function getPwChecks(pw: string): PwChecks {
  return {
    length: pw.length >= 8,
    upper: /[A-Z]/.test(pw),
    number: /[0-9]/.test(pw),
    special: /[^A-Za-z0-9]/.test(pw),
  }
}

export function isPasswordStrong(pw: string): boolean {
  const c = getPwChecks(pw)
  return c.length && c.upper && c.number && c.special
}

const LABELS = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong']
const BAR_COLORS = ['bg-red-500', 'bg-red-500', 'bg-amber-500', 'bg-lime-500', 'bg-emerald-500']
const TEXT_COLORS = ['text-red-500', 'text-red-500', 'text-amber-600', 'text-lime-600', 'text-emerald-600']

export default function PasswordStrength({ password }: { password: string }) {
  if (!password) return null

  const checks = getPwChecks(password)
  const score = Object.values(checks).filter(Boolean).length // 0–4

  const items = [
    { ok: checks.length, label: '8+ characters' },
    { ok: checks.upper, label: 'Capital letter' },
    { ok: checks.number, label: 'Number' },
    { ok: checks.special, label: 'Special character' },
  ]

  return (
    <div className="mt-2.5">
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-neutral-200">
          <div
            className={`h-full rounded-full transition-all duration-300 ${BAR_COLORS[score]}`}
            style={{ width: `${(score / 4) * 100}%` }}
          />
        </div>
        <span className={`w-16 text-right text-xs font-semibold ${TEXT_COLORS[score]}`}>{LABELS[score]}</span>
      </div>
      <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
        {items.map((it) => (
          <li
            key={it.label}
            className={`flex items-center gap-1.5 text-xs ${it.ok ? 'text-emerald-600' : 'text-neutral-400'}`}
          >
            {it.ok ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
            {it.label}
          </li>
        ))}
      </ul>
    </div>
  )
}
