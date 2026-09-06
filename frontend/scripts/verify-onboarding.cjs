// Browser regression using synthetic sessions and API fixtures only.
// Run against a frontend configured for onboarding-test.supabase.co and API port 8099:
// PLAYWRIGHT_PATH=/path/to/playwright node scripts/verify-onboarding.cjs
const assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const base = process.env.TEST_BASE_URL || 'http://127.0.0.1:3027'
const user = { id: '11111111-1111-4111-8111-111111111111', aud: 'authenticated', role: 'authenticated', email: 'candidate@example.test', phone: '233200000000', phone_confirmed_at: '2026-09-01T00:00:00Z', user_metadata: { full_name: 'Test Candidate' } }
const session = { access_token: 'synthetic-test-token', refresh_token: 'synthetic-refresh', token_type: 'bearer', expires_in: 3600, expires_at: Math.floor(Date.now() / 1000) + 3600, user }
const empty = { id: '22222222-2222-4222-8222-222222222222', user_id: user.id, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }

async function main() {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] })
  const errors = []
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
    await context.addInitScript((value) => {
      sessionStorage.setItem('sb-onboarding-test-auth-token', JSON.stringify(value))
    }, session)
    await context.addCookies([{ name: 'sb-onboarding-test-auth-token', value: `base64-${Buffer.from(JSON.stringify(session)).toString('base64url')}`, url: base }])
    let profile = { ...empty }
    let failRead = false
    let failSave = false
    let failMatch = false
    let matchingCalls = 0
    let activeCV = null
    let failCVRead = false
    let uploadStatus = 'failed'
    let uploads = 0
    const writes = []
    await context.route('**/*', async (route) => {
      const request = route.request()
      const url = new URL(request.url())
      if (url.origin === base) return route.continue()
      if (url.hostname === 'onboarding-test.supabase.co') return route.fulfill({ json: user })
      if (url.origin !== 'http://127.0.0.1:8099') return route.abort()
      if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': base, 'Access-Control-Allow-Headers': '*', 'Access-Control-Allow-Methods': '*' } })
      const reply = (json, status = 200) => route.fulfill({ status, json, headers: { 'Access-Control-Allow-Origin': base } })
      if (url.pathname === '/api/v1/cvs/active') return failCVRead ? reply({ detail: 'Unavailable' }, 503) : reply(activeCV)
      if (url.pathname === '/api/v1/cvs/upload') {
        uploads++
        assert.match(request.headers()['content-type'], /multipart\/form-data/)
        assert.equal(request.headers().authorization, 'Bearer synthetic-test-token')
        activeCV = { id: '33333333-3333-4333-8333-333333333333', user_id: user.id, file_name: 'candidate.pdf', file_size: 100, file_type: 'pdf', created_at: empty.created_at, is_active: true, parsing_status: uploadStatus, parsed_content: null }
        return reply(activeCV)
      }
      if (url.pathname.startsWith('/api/v1/profiles')) {
        assert.equal(request.headers().authorization, 'Bearer synthetic-test-token')
        if (request.method() === 'GET') return failRead ? reply({ detail: 'Unavailable' }, 503) : reply(profile)
        assert.equal(request.method(), 'PUT')
        if (failSave) return reply({ detail: 'Unavailable' }, 503)
        const data = request.postDataJSON()
        writes.push(data)
        profile = { ...profile, ...data }
        return reply(profile)
      }
      if (url.pathname.endsWith('/regenerate')) {
        matchingCalls++
        return failMatch ? reply({ detail: 'Rate limited' }, 429) : reply({ status: 'queued', message: 'Queued' }, 202)
      }
      if (url.pathname.includes('recommendations')) return reply({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 })
      if (url.pathname.includes('applications')) return reply({ applications: [], total: 0 })
      if (url.pathname.includes('admin')) return reply({ is_admin: false })
      return reply({ items: [], jobs: [], total: 0 })
    })
    const page = await context.newPage()
    page.on('pageerror', (error) => { errors.push(error.message); console.error('Page error:', error.message) })
    const heading = async (name) => {
      try { await page.getByRole('heading', { name, exact: true }).waitFor() }
      catch (error) { console.error('At:', page.url(), 'Body:', (await page.locator('body').innerText()).slice(0, 1200)); throw error }
    }
    await page.goto(`${base}/dashboard`)
    await heading('What kind of work are you looking for?')
    assert.equal(new URL(page.url()).pathname, '/profile/setup')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    assert.equal(writes.length, 0, 'empty required fields cannot save')
    await page.getByLabel('Target job title').fill('Accountant')
    await page.getByLabel('Experience level').selectOption('entry')
    await page.getByLabel('Work preference').selectOption('flexible')
    await page.getByLabel('Preferred job market').fill('Ghana')
    await page.screenshot({ path: '/tmp/onboarding-desktop.png', fullPage: true })
    failSave = true
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await page.getByText('Your changes weren’t saved.', { exact: false }).waitFor()
    assert.equal(await page.getByLabel('Target job title').inputValue(), 'Accountant')
    assert.equal(matchingCalls, 0)
    failSave = false
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await heading('What skills will you bring?')
    await page.reload()
    await heading('What skills will you bring?')
    await page.getByRole('button', { name: 'Back', exact: true }).click()
    assert.equal(await page.getByLabel('Target job title').inputValue(), 'Accountant')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await heading('What skills will you bring?')
    await page.getByLabel('Your skills', { exact: true }).fill(' , ')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await page.getByText('Add between 1 and 30 skills', { exact: false }).waitFor()
    assert.equal(matchingCalls, 0)
    await page.getByLabel('Your skills', { exact: true }).fill('Excel, Bookkeeping')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await heading('Upload your CV to complete setup')
    assert.equal(matchingCalls, 0)
    assert.equal(await page.getByRole('button', { name: 'Find my job matches' }).isDisabled(), true)
    await page.reload()
    await heading('Upload your CV to complete setup')
    await page.locator('input[type=file]').setInputFiles({ name: 'candidate.txt', mimeType: 'text/plain', buffer: Buffer.from('fixture') })
    await page.getByText('Only PDF and DOCX files are supported.').waitFor()
    assert.equal(uploads, 0)
    await page.locator('input[type=file]').setInputFiles({ name: 'candidate.pdf', mimeType: 'application/pdf', buffer: Buffer.from('synthetic fixture') })
    await page.getByText('Failed', { exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: 'Find my job matches' }).isDisabled(), true)
    uploadStatus = 'processing'
    await page.locator('input[type=file]').setInputFiles({ name: 'candidate.pdf', mimeType: 'application/pdf', buffer: Buffer.from('synthetic fixture') })
    await page.getByText('Processing', { exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: 'Find my job matches' }).isDisabled(), true)
    activeCV = { ...activeCV, parsing_status: 'completed', parsed_content: { summary: 'Accountant', skills: { technical: ['Bookkeeping'] } } }
    await page.getByText('Parsed', { exact: true }).waitFor()
    await page.setViewportSize({ width: 360, height: 844 })
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
    await page.screenshot({ path: '/tmp/onboarding-cv-360.png', fullPage: true })
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.getByRole('button', { name: 'Find my job matches' }).click()
    await heading('Your profile is ready for matching')
    assert.equal(matchingCalls, 1)
    assert.deepEqual(profile.technical_skills, [{ skill: 'Excel' }, { skill: 'Bookkeeping' }])
    await page.getByRole('link', { name: 'View job matches' }).click()
    await heading('Your job matches')
    assert.equal(new URL(page.url()).pathname, '/dashboard/recommendations')
    await page.reload()
    await heading('Your job matches')
    // An optional section must survive setup edits; existing skill evidence is preserved.
    profile = { ...profile, personal_branding_summary: 'Existing summary', technical_skills: [{ skill: 'Excel', years: 3, confidence: 4 }] }
    await page.goto(`${base}/profile/setup`)
    await heading('Upload your CV to complete setup')
    await page.getByRole('button', { name: 'Back', exact: true }).click()
    await heading('What skills will you bring?')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await heading('Upload your CV to complete setup')
    await page.getByText('Parsed', { exact: true }).waitFor()
    failMatch = true
    await page.getByRole('button', { name: 'Find my job matches' }).click()
    await heading('Your profile is ready for matching')
    await page.getByText('Your details are saved, but', { exact: false }).waitFor()
    assert.equal(profile.personal_branding_summary, 'Existing summary')
    assert.equal(profile.technical_skills[0].years, 3)
    activeCV = null
    await page.goto(`${base}/dashboard/recommendations`)
    await heading('Upload your CV to complete setup')
    assert.equal(await page.getByRole('button', { name: 'Find my job matches' }).isDisabled(), true)
    failCVRead = true
    await page.reload()
    await page.getByRole('button', { name: 'Retry CV check' }).waitFor()
    assert.equal(await page.getByRole('button', { name: 'Find my job matches' }).isDisabled(), true)
    failCVRead = false
    await page.getByRole('button', { name: 'Retry CV check' }).click()
    await page.getByRole('button', { name: 'Choose file' }).waitFor()
    failRead = true
    await page.goto(`${base}/dashboard`)
    await heading('We couldn’t load your profile')
    assert.equal(new URL(page.url()).pathname, '/dashboard')
    failRead = false
    profile = { ...empty }
    await page.getByRole('button', { name: 'Try again' }).click()
    await heading('What kind of work are you looking for?')
    for (const width of [390, 360]) {
      await page.setViewportSize({ width, height: 844 })
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
      await page.screenshot({ path: `/tmp/onboarding-${width}.png`, fullPage: true })
    }
    await page.goto(`${base}/dashboard/jobs`)
    await page.getByRole('heading').first().waitFor()
    assert.equal(new URL(page.url()).pathname, '/dashboard/jobs', 'browsing remains available')
    await page.goto(`${base}/dashboard/recommendations`)
    await heading('What kind of work are you looking for?')
    failRead = true
    await page.reload()
    await page.getByText('We couldn’t load your saved details.', { exact: false }).waitFor()
    assert.equal(await page.getByLabel('Target job title').count(), 0, 'failed reads do not expose an empty writable form')
    failRead = false
    await page.getByRole('button', { name: 'Try again' }).click()
    await heading('What kind of work are you looking for?')
    const anonymous = await browser.newContext()
    const anonymousPage = await anonymous.newPage()
    await anonymousPage.goto(`${base}/profile/setup`)
    await anonymousPage.waitForURL('**/auth/login')
    assert.deepEqual(errors, [])
    console.log('PASS: required CV upload, rejected formats, failed/pending parsing, automatic processing refresh, removed CV gate, CV read retry, profile resume/validation, matching success/failure, preserved fields, mobile layout, browse access, anonymous redirect; no page errors. Synthetic API fixtures only.')
  } finally {
    await browser.close()
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
