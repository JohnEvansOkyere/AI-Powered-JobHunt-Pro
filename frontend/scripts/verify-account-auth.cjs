// Synthetic Supabase/API browser regression. No live accounts or SMS.
// PLAYWRIGHT_PATH=/path/to/playwright TEST_BASE_URL=http://127.0.0.1:3027 node scripts/verify-account-auth.cjs
const assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const base = process.env.TEST_BASE_URL || 'http://127.0.0.1:3027'
const authHost = process.env.TEST_AUTH_HOST || 'onboarding-test.supabase.co'
const storageKey = `sb-${authHost.split('.')[0]}-auth-token`
const id = '11111111-1111-4111-8111-111111111111'
const newUser = () => ({ id, aud: 'authenticated', role: 'authenticated', email: 'candidate@example.test', phone: '', user_metadata: { full_name: 'Test Candidate' }, created_at: '2026-09-06T00:00:00Z' })
const session = (user) => ({ access_token: 'synthetic-access-token', refresh_token: 'synthetic-refresh', token_type: 'bearer', expires_in: 3600, expires_at: Math.floor(Date.now() / 1000) + 3600, user })

async function fixture(browser, options = {}) {
  let user = options.user || newUser()
  const calls = []
  const errors = []
  const context = await browser.newContext({ viewport: { width: options.width || 390, height: 900 } })
  if (options.signedIn) {
    await context.addInitScript(({ key, value }) => {
      if (!sessionStorage.getItem(key)) sessionStorage.setItem(key, JSON.stringify(value))
    }, { key: storageKey, value: session(user) })
    await context.addCookies([{ name: storageKey, value: `base64-${Buffer.from(JSON.stringify(session(user))).toString('base64url')}`, url: base }])
  }
  await context.route('**/*', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.origin === base) return route.continue()
    const reply = (json, status = 200) => route.fulfill({ status, json, headers: { 'Access-Control-Allow-Origin': base, 'X-Supabase-Api-Version': '2024-01-01', 'Access-Control-Expose-Headers': 'X-Supabase-Api-Version' } })
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': base, 'Access-Control-Allow-Headers': '*', 'Access-Control-Allow-Methods': '*' } })
    if (url.hostname === authHost && url.pathname.startsWith('/auth/v1/')) {
      const body = request.postData() ? request.postDataJSON() : {}
      calls.push({ path: url.pathname, method: request.method(), body, grant: url.searchParams.get('grant_type') })
      if (url.pathname.endsWith('/signup')) {
        if (options.signupError) return reply(options.signupError, 500)
        assert.equal(body.email, 'candidate@example.test')
        assert.equal(body.password, 'Synthetic-password-123')
        assert.equal(body.data.full_name, 'Test Candidate')
        assert.equal(body.phone, undefined)
        user = { ...user, user_metadata: body.data }
        return options.emailConfirmation ? reply({ user, session: null }) : reply(session(user))
      }
      if (url.pathname.endsWith('/token')) {
        if (options.loginError) return reply(options.loginError, 400)
        if (url.searchParams.get('grant_type') === 'password') {
          assert.equal(body.email, 'candidate@example.test')
          assert.equal(body.password, 'Synthetic-password-123')
        }
        return reply(session(user))
      }
      if (url.pathname.endsWith('/otp')) {
        assert.equal(body.create_user, false, 'Legacy setup must not create a second account')
        return reply({})
      }
      if (url.pathname.endsWith('/verify')) {
        if (body.token !== '123456') return reply({ msg: 'The code is invalid or expired.', code: 'otp_expired' }, 403)
        assert.equal(body.type, options.legacy ? 'sms' : 'phone_change')
        user = { ...user, phone: body.phone, phone_confirmed_at: '2026-09-06T00:00:00Z' }
        return reply(session(user))
      }
      if (url.pathname.endsWith('/user')) {
        if (request.method() === 'PUT') {
          assert.ok(request.headers().authorization, 'Phone/credentials update must be authenticated')
          if (body.phone) assert.equal(body.phone, '+233241234567')
          if (body.phone && options.smsFailure) return reply({ msg: 'Hook requires authorization token: synthetic-private-detail' }, 503)
          if (body.email) {
            assert.equal(body.password, 'Synthetic-password-123')
            user = options.pendingEmail ? { ...user, new_email: body.email } : { ...user, email: body.email }
          }
        }
        return reply(user)
      }
      if (url.pathname.endsWith('/logout')) return reply({})
      throw new Error(`Unhandled Auth fixture: ${url.pathname}`)
    }
    if (url.pathname.includes('/api/v1/') || url.pathname === '/auth/handoff/verify') {
      if (url.pathname === '/auth/handoff/verify') return reply({ valid: true, full_name: 'Test Candidate', email: 'candidate@example.test', phone: '024 123 4567', job_id: 'test-job' })
      if (url.pathname.includes('/profiles')) {
        if (request.method() === 'PUT' && options.profileSaveError) return reply({ error: { message: options.profileSaveError } }, 500)
        return reply({ id: 'profile', user_id: id, primary_job_title: 'Engineer', technical_skills: [{ skill: 'Testing' }], created_at: '2026-09-06', updated_at: '2026-09-06', ...options.profile })
      }
      if (url.pathname.includes('/cvs/active')) return reply(options.cv || null)
      if (url.pathname.includes('/password-reset/')) return reply({ error: { message: 'Redis connection rejected: synthetic-private-detail' } }, 503)
      if (url.pathname.includes('/admin')) return reply({ is_admin: false })
      if (url.pathname.includes('/applications')) return reply({ applications: [], total: 0 })
      return reply({ items: [], total: 0, page: 1, total_pages: 0 })
    }
    return route.abort()
  })
  const page = await context.newPage()
  page.on('pageerror', (error) => errors.push(error.message))
  page.setDefaultTimeout(15000)
  return { context, page, calls, errors }
}

async function fillSignup(page) {
  await page.getByLabel('Full name', { exact: true }).fill('Test Candidate')
  await page.getByLabel('Email address', { exact: true }).fill('Candidate@example.test')
  await page.getByLabel('Password', { exact: true }).fill('Synthetic-password-123')
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
}

async function main() {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] })
  try {
    const f = await fixture(browser)
    await f.page.goto(`${base}/auth/signup?h=synthetic-handoff`)
    await f.page.getByText('Application details imported from VeloxaRecruit.').waitFor()
    assert.equal(await f.page.getByLabel('Telephone number').count(), 0)
    await fillSignup(f.page)
    await f.page.waitForURL('**/auth/verify-phone')
    await f.page.getByLabel('Telephone number').fill('024 123 4567')
    await f.page.getByRole('button', { name: 'Send verification code' }).click()
    await f.page.getByLabel('Six-digit code').fill('000000')
    await f.page.getByRole('button', { name: 'Verify and continue' }).click()
    await f.page.getByRole('alert').filter({ hasText: 'invalid or expired' }).waitFor()
    await f.page.getByLabel('Six-digit code').fill('123456')
    await f.page.getByRole('button', { name: 'Verify and continue' }).click()
    await f.page.waitForURL((url) => ['/dashboard', '/profile/setup'].includes(url.pathname))
    await f.page.reload()
    await f.page.waitForURL((url) => ['/dashboard', '/profile/setup'].includes(url.pathname))
    assert.equal(f.calls.filter((c) => c.path.endsWith('/signup')).length, 1)
    assert.equal(f.calls.filter((c) => c.path.endsWith('/otp')).length, 0)
    assert.equal(f.calls.filter((c) => c.body.phone && c.method === 'PUT').length, 1)
    await f.page.evaluate(() => { localStorage.clear(); sessionStorage.clear() })
    await f.context.clearCookies()
    await f.page.goto(`${base}/auth/login`)
    await f.page.getByLabel('Email address', { exact: true }).fill('candidate@example.test')
    await f.page.getByLabel('Password', { exact: true }).fill('Synthetic-password-123')
    await f.page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await f.page.waitForURL((url) => ['/dashboard', '/profile/setup'].includes(url.pathname))
    assert.equal(f.calls.filter((c) => c.body.phone && c.method === 'PUT').length, 1, 'Repeat login must not request SMS')
    assert.equal(f.calls.filter((c) => c.grant === 'password').length, 1)
    assert.deepEqual(f.errors, [])
    await f.context.close()
    console.log('PASS signup → one phone verification → automatic session → reload → email/password login without SMS')

    const gate = await fixture(browser, { signedIn: true })
    await gate.page.goto(`${base}/dashboard`)
    await gate.page.waitForURL('**/auth/verify-phone')
    await gate.page.reload()
    await gate.page.getByLabel('Telephone number').waitFor()
    await gate.page.screenshot({ path: '/tmp/job-auth-verify-phone-390.png', fullPage: true })
    assert.equal(gate.calls.filter((c) => c.method === 'PUT').length, 0)
    assert.deepEqual(gate.errors, [])
    await gate.context.close()
    console.log('PASS unverified session cannot skip verification; reload sends no SMS')

    const legacy = await fixture(browser, { legacy: true, user: { ...newUser(), email: '', phone: '233241234567', phone_confirmed_at: '2026-09-06' } })
    await legacy.page.goto(`${base}/auth/setup-login`)
    await legacy.page.getByLabel('Telephone number').fill('024 123 4567')
    await legacy.page.getByRole('button', { name: 'Send verification code' }).click()
    await legacy.page.getByLabel('Six-digit code').fill('123456')
    await legacy.page.getByRole('button', { name: 'Verify and continue' }).click()
    await legacy.page.getByLabel('Email address').fill('candidate@example.test')
    await legacy.page.getByLabel('Create a password').fill('Synthetic-password-123')
    await legacy.page.getByRole('button', { name: 'Save and continue' }).click()
    await legacy.page.waitForURL((url) => ['/dashboard', '/profile/setup'].includes(url.pathname))
    assert.equal(legacy.calls.filter((c) => c.path.endsWith('/signup')).length, 0)
    assert.deepEqual(legacy.errors, [])
    await legacy.context.close()
    console.log('PASS legacy phone account adds email/password on the same identity')

    const pending = await fixture(browser, { emailConfirmation: true, width: 1440 })
    await pending.page.goto(`${base}/auth/signup`)
    await fillSignup(pending.page)
    await pending.page.getByRole('heading', { name: 'Check your email' }).waitFor()
    assert.equal(pending.calls.filter((c) => c.method === 'PUT').length, 0)
    assert.deepEqual(pending.errors, [])
    await pending.context.close()
    console.log('PASS unexpected email-confirmation setting handled without duplicate signup or SMS')

    const changing = await fixture(browser, { signedIn: true, pendingEmail: true, user: { ...newUser(), email: '', phone: '233241234567', phone_confirmed_at: '2026-09-06' } })
    await changing.page.goto(`${base}/auth/setup-login`)
    await changing.page.getByLabel('Email address').fill('candidate@example.test')
    await changing.page.getByLabel('Create a password').fill('Synthetic-password-123')
    await changing.page.getByRole('button', { name: 'Save and continue' }).click()
    await changing.page.getByRole('heading', { name: 'Confirm your email' }).waitFor()
    await changing.page.reload()
    await changing.page.getByRole('heading', { name: 'Confirm your email' }).waitFor()
    assert.deepEqual(changing.errors, [])
    await changing.context.close()
    console.log('PASS existing-account email confirmation survives reload')

    const failed = await fixture(browser, { signedIn: true, smsFailure: true })
    await failed.page.goto(`${base}/auth/verify-phone`)
    await failed.page.getByLabel('Telephone number').fill('024 123 4567')
    await failed.page.getByRole('button', { name: 'Send verification code' }).click()
    await failed.page.getByRole('alert').filter({ hasText: 'temporarily unavailable' }).waitFor()
    assert.equal(await failed.page.getByLabel('Six-digit code').count(), 0)
    assert.ok(await failed.page.getByRole('button', { name: /Try again in/ }).isDisabled())
    assert.deepEqual(failed.errors, [])
    await failed.context.close()
    console.log('PASS provider failure stays recoverable and retry is throttled')

    for (const width of [1440, 390, 360]) {
      const visual = await fixture(browser, { width })
      for (const route of ['signup', 'login', 'setup-login']) {
        await visual.page.goto(`${base}/auth/${route}`)
        await visual.page.locator('h1').waitFor()
        assert.ok(await visual.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${route} overflow at ${width}`)
        await visual.page.screenshot({ path: `/tmp/job-auth-${route}-${width}.png`, fullPage: true })
      }
      assert.deepEqual(visual.errors, [])
      await visual.context.close()
    }
    console.log('PASS desktop/390px/360px layouts and no browser runtime errors')
  } finally { await browser.close() }
}
if (require.main === module) main().catch((error) => { console.error(error); process.exitCode = 1 })
module.exports = { fixture, fillSignup, newUser }
