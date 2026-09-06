// Synthetic browser fixtures only. API/SQL authorization is tested separately.
// Run against a preview configured with https://admin-report-test.supabase.co.
const assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const base = process.env.TEST_BASE_URL || 'http://127.0.0.1:3033'
const user = { id: '11111111-1111-4111-8111-111111111111', email: 'admin@example.test', role: 'authenticated', aud: 'authenticated', user_metadata: {} }
const session = { access_token: 'synthetic-test-token', refresh_token: 'synthetic-refresh', token_type: 'bearer', expires_in: 3600, expires_at: Math.floor(Date.now() / 1000) + 3600, user }
const registrations = { range: { days: 30, start: '2026-08-07', end: '2026-09-06' }, total_accounts: 80, signups: 50, complete: 20, partial: 25, not_started: 5, daily: [{ day: '2026-09-06', signups: 3 }, { day: '2026-09-05', signups: 0 }] }
const overview = { range: registrations.range, system: { ats_sync: { status: 'success', stale: false, last_success_at: null } }, metrics: { unique_visitors: 123, authenticated_visitors: 20, sessions: 150, page_views: 300, total_events: 400, clicks: 60, job_apply_clicks: 10, signups: 15, signup_starts: 30, engaged_seconds: 500, avg_session_seconds: 30, users_total: 80, active_jobs: 200, applications_total: 15 }, daily: [{ day: '2026-09-06', sessions: 12, events: 30 }], top_paths: [{ path: '/jobs', count: 75 }], top_clicks: [{ target: 'browse', label: 'Browse jobs', count: 15 }], top_jobs: [{ path: '/jobs/11111111-1111-4111-8111-111111111111', views: 4 }], acquisition_sources: [{ source: 'google', medium: 'organic', campaign: null, visitors: 10, sessions: 12, job_views: 8, apply_clicks: 2, signups: 1 }], recent_sessions: [], recent_events: [] }

async function main() {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] })
  try {
    for (const width of [1440, 390]) {
      const context = await browser.newContext({ viewport: { width, height: 1000 } })
      const errors = []
      let mode = 'normal'
      await context.addInitScript(value => sessionStorage.setItem('sb-admin-report-test-auth-token', JSON.stringify(value)), session)
      await context.addCookies([{ name: 'sb-admin-report-test-auth-token', value: `base64-${Buffer.from(JSON.stringify(session)).toString('base64url')}`, url: base, sameSite: 'Lax' }])
      await context.route('https://admin-report-test.supabase.co/**', route => route.fulfill({ json: user }))
      await context.route('**/api/v1/**', route => {
        const url = new URL(route.request().url())
        const path = url.pathname
        if (path.endsWith('/analytics/events')) return route.fulfill({ status: 202, json: {} })
        if (path.endsWith('/admin/me')) return route.fulfill({ json: { is_admin: true } })
        if (path.endsWith('/admin/registrations')) {
          if (mode === 'error') return route.fulfill({ status: 500, json: { detail: 'Unexpected internal failure' } })
          if (mode === 'denied') return route.fulfill({ status: 403, json: { detail: 'Administrator access required' } })
          return route.fulfill({ json: mode === 'empty' ? { ...registrations, signups: 0, complete: 0, partial: 0, not_started: 0, daily: [] } : registrations })
        }
        if (path.endsWith('/admin/overview')) return route.fulfill({ json: overview })
        if (path.endsWith('/admin/users')) {
          const profile = url.searchParams.get('profile') || 'all'
          const page = Number(url.searchParams.get('page') || 1)
          const empty = url.searchParams.get('search') === 'nobody'
          return route.fulfill({ json: { total: 80, active: 75, suspended: 5, filtered_total: empty ? 0 : 50, page, page_size: 25, users: empty ? [] : [{ ...user, id: `${page}`, full_name: `${profile === 'complete' ? 'Complete' : 'Partial'} Candidate ${page}`, phone: null, is_active: true, is_admin: false, email_verified: true, phone_verified: false, created_at: '2026-09-05', last_login_at: null, updated_at: null, profile_updated_at: null, profile_completion: profile === 'complete' ? 100 : 40, profile_status: profile === 'complete' ? 'complete' : 'partial', missing_fields: profile === 'complete' ? [] : ['Work experience', 'AI preferences'] }] } })
        }
        return route.fulfill({ json: {} })
      })
      const page = await context.newPage()
      page.on('pageerror', e => errors.push(e.message))
      await page.goto(`${base}/dashboard/admin/registrations?days=30`)
      try { await page.getByText('50', { exact: true }).waitFor() } catch (error) {
        await page.screenshot({ path: '/tmp/admin-report-failure.png', fullPage: true })
        console.log('Initial report failure', page.url(), errors, await page.evaluate(() => Object.keys(sessionStorage)))
        throw error
      }
      await page.getByRole('link', { name: /Complete profiles/ }).click()
      await page.getByText('Complete Candidate 1', { exact: true }).waitFor()
      assert.match(page.url(), /profile=complete/)
      await page.getByText('Profile details', { exact: true }).click()
      await page.getByText('All scored fields filled.', { exact: true }).waitFor()
      await page.getByRole('button', { name: 'Next', exact: true }).click()
      await page.getByText('Complete Candidate 2', { exact: true }).waitFor()
      await page.getByLabel('Profile completion', { exact: true }).selectOption('partial')
      await page.getByText('Partial Candidate 1', { exact: true }).waitFor()
      await page.getByText('Profile details', { exact: true }).click()
      await page.getByText('Missing: Work experience, AI preferences', { exact: true }).waitFor()
      await page.screenshot({ path: `/tmp/admin-users-${width}.png`, fullPage: true })
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
      await page.getByLabel('Search users').fill('nobody')
      await page.getByRole('button', { name: 'Search', exact: true }).click()
      await page.getByText('No users match this filter.', { exact: true }).waitFor()
      for (const [label, heading] of [['Overview', 'Admin overview'], ['Traffic & jobs', 'Traffic & jobs'], ['Acquisition', 'Acquisition'], ['Activity', 'Recent activity']]) {
        await page.getByRole('navigation', { name: 'Administration reports' }).getByRole('link', { name: label, exact: true }).click()
        await page.getByRole('heading', { name: heading, exact: true }).waitFor()
        await page.getByRole('button', { name: 'Refresh', exact: true }).waitFor()
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${label} overflow at ${width}`)
      }
      await page.getByRole('link', { name: 'Signups & profiles', exact: true }).click()
      await page.getByText('50', { exact: true }).waitFor()
      await page.getByLabel('Registration period').selectOption('7')
      await page.waitForURL('**/registrations?days=7')
      await page.getByText('50', { exact: true }).waitFor()
      await page.screenshot({ path: `/tmp/admin-registrations-${width}.png`, fullPage: true })
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
      mode = 'empty'
      await page.getByRole('button', { name: 'Refresh', exact: true }).click()
      await page.getByText(/No accounts registered in this period/).waitFor()
      mode = 'error'
      await page.getByRole('button', { name: 'Refresh', exact: true }).click()
      await page.getByRole('alert').waitFor()
      assert.equal(await page.getByText('Unexpected internal failure', { exact: true }).count(), 0)
      mode = 'denied'
      await page.getByRole('button', { name: 'Refresh', exact: true }).click()
      await page.waitForURL(`${base}/dashboard`)
      assert.deepEqual(errors, [])
      await context.close()
      console.log(`PASS ${width}px: report navigation, signup drill-down, profile filters, pagination, missing fields, search, date filter, empty/error/access-denied states, no overflow or page errors`)
    }
    const anonymous = await browser.newContext()
    const page = await anonymous.newPage()
    await page.goto(`${base}/dashboard/admin/registrations`)
    await page.waitForURL('**/auth/login')
    await anonymous.close()
    console.log('PASS anonymous redirect')
  } finally { await browser.close() }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
