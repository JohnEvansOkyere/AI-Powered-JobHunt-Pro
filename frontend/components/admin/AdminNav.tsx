'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const pages = [
  ['Overview', '/dashboard/admin'],
  ['Signups & profiles', '/dashboard/admin/registrations'],
  ['Users', '/dashboard/admin/users'],
  ['Traffic & jobs', '/dashboard/admin/traffic'],
  ['Acquisition', '/dashboard/admin/acquisition'],
  ['Activity', '/dashboard/admin/activity'],
  ['Job imports', '/dashboard/admin/job-imports'],
]

export default function AdminNav({ days = 30 }: { days?: number }) {
  const path = usePathname()
  return <nav aria-label="Administration reports" className="mb-6 flex flex-wrap gap-2">
    {pages.map(([label, href]) => <Link key={href} href={`${href}?days=${href.endsWith('/users') ? 0 : days}`} aria-current={path === href ? 'page' : undefined}
      className={`rounded-xl px-4 py-2 text-sm font-semibold ${path === href ? 'bg-brand-turquoise-700 text-white' : 'border border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-100'}`}>
      {label}
    </Link>)}
  </nav>
}
