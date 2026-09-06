// Synthetic account/job fixtures only; no real credentials or account writes.
// Frontend env: AUTH_SUPABASE and SUPABASE public URLs https://job-detail-test.supabase.co,
// public keys fixture-public-key, NEXT_PUBLIC_API_URL=http://127.0.0.1:8107.
// TEST_BASE_URL=http://127.0.0.1:3037 PLAYWRIGHT_PATH=/path/to/playwright node scripts/verify-job-detail-session.cjs
const assert = require('node:assert/strict')
const http = require('node:http')
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const base = process.env.TEST_BASE_URL || 'http://127.0.0.1:3037'
const user = { id: '11111111-1111-4111-8111-111111111111', aud: 'authenticated', role: 'authenticated', email: 'candidate@example.test', phone: '233200000000', phone_confirmed_at: '2026-09-01T00:00:00Z', user_metadata: { full_name: 'Test Candidate' } }
const session = { access_token: 'synthetic-test-token', refresh_token: 'synthetic-refresh', token_type: 'bearer', expires_in: 3600, expires_at: Math.floor(Date.now() / 1000) + 3600, user }
const job = { id: '22222222-2222-4222-8222-222222222222', title: 'Senior Data Scientist', company: 'Example Company', location: 'Remote', description: 'Analyse data and build useful models.', job_type: 'Full-Time', posted_date: '2026-08-31T00:00:00Z', processing_status: 'processed', job_link: 'https://employer.example.test/apply', source: 'fixture' }
const profile = { id: '33333333-3333-4333-8333-333333333333', user_id: user.id, primary_job_title: 'Data Scientist', seniority_level: 'senior', work_preference: 'remote', technical_skills: [{ skill: 'Python' }] }
const cv = { id: '44444444-4444-4444-8444-444444444444', user_id: user.id, is_active: true, parsing_status: 'completed', parsed_content: { skills: ['Python'] } }
const noApplyId = '55555555-5555-4555-8555-555555555555'

async function main() {
  const api = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', base)
    res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type')
    res.setHeader('Access-Control-Allow-Methods', '*')
    res.setHeader('Content-Type', 'application/json')
    if (req.method === 'OPTIONS') { res.writeHead(204); return res.end() }
    const path = new URL(req.url, base).pathname
    let data = {}
    if (path === `/api/v1/jobs/${job.id}`) data = job
    else if (path === `/api/v1/jobs/${noApplyId}`) data = { ...job, id: noApplyId, job_link: null, source_url: null }
    else if (path.startsWith('/api/v1/profiles')) data = profile
    else if (path === '/api/v1/cvs/active') data = cv
    else if (path.includes('/recommendations')) data = { items: [{ id: 'match-1', job_id: job.id, job, match_score: 0.9, tier: 'tier1' }], total: 1, page: 1, page_size: 3, total_pages: 1 }
    else if (path.includes('/applications')) data = { applications_total: 0, submitted_count: 0, applications: [], total: 0 }
    else if (path.includes('/admin')) data = { is_admin: true }
    res.end(JSON.stringify(data))
  })
  await new Promise(resolve => api.listen(8107, '127.0.0.1', resolve))
  let browser
  const errors = []
  try {
    browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] })
    for (const width of [1440, 390, 360]) {
      for (const signedIn of [true, false]) {
        const context = await browser.newContext({ viewport: { width, height: 1000 } })
        await context.route('https://job-detail-test.supabase.co/**', route => route.fulfill({ json: user }))
        if (signedIn) {
          await context.addInitScript(value => sessionStorage.setItem('sb-job-detail-test-auth-token', JSON.stringify(value)), session)
          await context.addCookies([{ name: 'sb-job-detail-test-auth-token', value: `base64-${Buffer.from(JSON.stringify(session)).toString('base64url')}`, url: base }])
        }
        const page = await context.newPage()
        page.on('pageerror', error => errors.push(error.message))
        if (signedIn) {
          await page.goto(`${base}/dashboard`)
          const role = page.locator('.ws-match-row').filter({ hasText: job.title })
          try { await role.waitFor() }
          catch (error) { console.error('Fixture page:', page.url(), await page.locator('body').innerText()); throw error }
          assert.equal(await role.getAttribute('href'), `/jobs/${job.id}?from=overview`)
          await role.click()
        } else {
          // An anonymous visitor cannot turn a return hint into authenticated navigation.
          await page.goto(`${base}/jobs/${job.id}?from=overview`)
        }
        await page.getByRole('heading', { name: job.title, exact: true }).waitFor()
        const action = page.getByRole('link', { name: signedIn ? 'Back to job matches' : 'Create free profile', exact: true })
        await action.waitFor()
        assert.equal(await action.getAttribute('href'), signedIn ? '/dashboard/recommendations' : '/auth/signup')
        const header = page.locator('header')
        if (signedIn) {
          assert.equal(await page.locator('a[href^="/auth/"]').count(), 0)
          assert.equal(await header.getByRole('link', { name: 'My profile', exact: true }).getAttribute('href'), '/dashboard/profile')
          assert.equal(await header.getByRole('link', { name: 'Dashboard', exact: true, includeHidden: true }).getAttribute('href'), '/dashboard')
          assert.equal(await page.getByText('Create a profile afterwards', { exact: false }).count(), 0)
        } else {
          await header.getByRole('link', { name: 'Sign in', exact: true }).waitFor()
          assert.equal(await header.getByRole('link', { name: 'Create account', exact: true, includeHidden: true }).getAttribute('href'), '/auth/signup')
        }
        assert.equal(await page.getByRole('link', { name: 'Apply now', exact: true }).getAttribute('href'), job.job_link)
        assert.equal(await page.getByRole('link', { name: signedIn ? 'Back to overview' : 'Back to jobs', exact: true }).getAttribute('href'), signedIn ? '/dashboard' : '/jobs')
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
        await page.screenshot({ path: `/tmp/job-detail-${signedIn ? 'signed-in' : 'anonymous'}-${width}.png`, fullPage: true })
        if (width < 768) {
          await page.getByRole('button', { name: 'Open navigation' }).click()
          const mobile = page.getByRole('navigation', { name: 'Mobile navigation' })
          await mobile.getByRole('link', { name: signedIn ? 'Dashboard' : 'Create account', exact: true }).waitFor()
          assert.equal(await mobile.getByRole('link', { name: signedIn ? 'My profile' : 'Sign in', exact: true }).getAttribute('href'), signedIn ? '/dashboard/profile' : '/auth/login')
          await page.getByRole('button', { name: 'Close navigation' }).click()
        }
        if (signedIn) {
          await page.getByRole('link', { name: 'Back to overview', exact: true }).click()
          await page.waitForURL(`${base}/dashboard`)
          await page.locator('.ws-match-row').click()
          await page.getByRole('link', { name: 'Back to overview', exact: true }).waitFor()
          await page.goBack()
          await page.waitForURL(`${base}/dashboard`)
          await page.locator('.ws-match-row').waitFor()
          await page.goto(`${base}/jobs/${job.id}`)
          await page.getByRole('link', { name: 'Back to job matches', exact: true }).waitFor()
          assert.equal(await page.getByRole('link', { name: 'Back to jobs', exact: true }).getAttribute('href'), '/dashboard/jobs')
          await page.reload()
          await page.getByRole('link', { name: 'Back to job matches', exact: true }).waitFor()
          assert.equal(await page.locator('a[href^="/auth/"]').count(), 0)
        }
        await page.goto(`${base}/jobs/${noApplyId}`)
        await page.getByText('Apply link unavailable', { exact: true }).waitFor()
        assert.equal(await page.getByRole('link', { name: 'Apply now', exact: true }).count(), 0)
        await context.close()
        console.log(`PASS ${signedIn ? 'signed-in' : 'anonymous'} ${width}px`)
      }
    }
    assert.deepEqual(errors, [])
    console.log('PASS Overview round trip, browser Back, reload, direct entry, mobile menu, anonymous access, apply links, no page errors')
  } finally {
    if (browser) await browser.close()
    await new Promise(resolve => api.close(resolve))
  }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
