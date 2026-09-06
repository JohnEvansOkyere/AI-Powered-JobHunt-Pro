// Run only against a local reset API fixture with /test/clear and /test/state.
// The fixture uses real Redis/routes and mocks DB/Auth/SMS. Never target production.
const assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const base = process.env.TEST_BASE_URL || 'http://127.0.0.1:3027'
const api = 'http://127.0.0.1:8099'
const password = 'Synthetic-new-password-123'

async function main() {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] })
  try {
    for (const width of [390, 1440, 360]) {
      const context = await browser.newContext({ viewport: { width, height: 950 } })
      await context.request.post(`${api}/test/clear`)
      await context.route('**/*', (route) => {
        const origin = new URL(route.request().url()).origin
        return origin === base || origin === api ? route.continue() : route.abort()
      })
      const page = await context.newPage()
      page.setDefaultTimeout(15000)
      const errors = []
      const resetRequests = []
      let grant = ''
      page.on('pageerror', (error) => errors.push(error.message))
      page.on('request', (req) => { if (req.url().includes('/password-reset/')) resetRequests.push({ path: new URL(req.url()).pathname, data: req.postDataJSON() }) })
      page.on('response', async (response) => {
        if (response.url().endsWith('/password-reset/verify') && response.ok()) grant = (await response.json()).reset_token
      })
      await page.goto(`${base}/auth/login`)
      await page.getByRole('link', { name: 'Forgot password?' }).click()
      await page.getByRole('heading', { name: 'Enter your phone number' }).waitFor()
      assert.equal(await page.locator('input[type=email]').count(), 0)
      await page.getByLabel('Registered phone number').fill('024 123 4567')
      await page.screenshot({ path: `/tmp/sms-reset-phone-${width}.png`, fullPage: true })
      await page.getByRole('button', { name: 'Send reset code', exact: true }).click()
      await page.getByRole('heading', { name: 'Check your SMS' }).waitFor()
      assert.deepEqual(resetRequests[0].data, { phone: '024 123 4567' })
      let state
      for (let attempt = 0; attempt < 20; attempt++) {
        state = await (await context.request.get(`${api}/test/state`)).json()
        if (state.code) break
        await page.waitForTimeout(100)
      }
      assert.equal(state.sent, 1)
      const wrong = state.code === '000000' ? '999999' : '000000'
      await page.getByLabel('Six-digit reset code').fill(wrong)
      await page.getByRole('button', { name: 'Verify reset code' }).click()
      await page.getByRole('alert').filter({ hasText: 'invalid or expired' }).waitFor()
      await page.getByLabel('Six-digit reset code').fill(state.code)
      await page.getByRole('button', { name: 'Verify reset code' }).click()
      await page.getByRole('heading', { name: 'Choose a new password' }).waitFor()
      await page.getByLabel('New password', { exact: true }).fill(password)
      await page.getByLabel('Confirm new password', { exact: true }).fill('does-not-match')
      await page.getByRole('button', { name: 'Reset password', exact: true }).click()
      await page.getByRole('alert').filter({ hasText: 'do not match' }).waitFor()
      assert.equal(resetRequests.filter((req) => req.path.endsWith('/complete')).length, 0)
      await page.getByLabel('Confirm new password', { exact: true }).fill(password)
      await page.screenshot({ path: `/tmp/sms-reset-password-${width}.png`, fullPage: true })
      await page.getByRole('button', { name: 'Reset password', exact: true }).click()
      await page.getByRole('heading', { name: 'Password reset complete' }).waitFor()
      const completed = await (await context.request.get(`${api}/test/state`)).json()
      assert.equal(completed.changed, 1)
      assert.equal(completed.password_matches, true)
      assert.equal(resetRequests.filter((req) => req.path.endsWith('/complete')).length, 1)
      const storage = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage }, cookie: document.cookie }))
      assert.ok(grant)
      assert.ok(!storage.includes(grant) && !storage.includes(password))
      assert.ok(!page.url().includes(grant))
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
      await page.getByRole('link', { name: 'Back to sign in' }).click()
      await page.getByLabel('Email address', { exact: true }).waitFor()
      assert.deepEqual(errors, [])
      await context.close()
      console.log(`PASS phone-only reset → real API/Redis → invalid code → password confirmation → password update at ${width}px`)
    }

    const context = await browser.newContext()
    const page = await context.newPage()
    await context.request.post(`${api}/test/clear`)
    await page.clock.install()
    await page.goto(`${base}/auth/reset-password`)
    await page.getByLabel('Registered phone number').fill('020 000 0000')
    await page.getByRole('button', { name: 'Send reset code', exact: true }).click()
    await page.getByRole('heading', { name: 'Check your SMS' }).waitFor()
    const unknown = await (await context.request.get(`${api}/test/state`)).json()
    assert.equal(unknown.sent, 0)
    await page.clock.fastForward(301000)
    await page.getByRole('alert').filter({ hasText: 'Request a new code' }).waitFor()
    await page.reload()
    await page.getByRole('heading', { name: 'Enter your phone number' }).waitFor()
    assert.equal(await page.getByLabel('Registered phone number').inputValue(), '')
    await context.route(`${api}/api/v1/auth/password-reset/request`, (route) => route.fulfill({ status: 429, headers: { 'Access-Control-Allow-Origin': base, 'Access-Control-Expose-Headers': 'Retry-After', 'Retry-After': '120' }, json: { detail: 'Too many reset attempts. Please try again later.' } }))
    await page.getByLabel('Registered phone number').fill('024 123 4567')
    await page.getByRole('button', { name: 'Send reset code', exact: true }).click()
    await page.getByRole('alert').filter({ hasText: 'Too many' }).waitFor()
    assert.ok(await page.getByRole('button', { name: /Try again in/ }).isDisabled())
    await context.close()
    console.log('PASS unknown phone privacy, expiry, reload clears recovery state and server Retry-After')
  } finally { await browser.close() }
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
