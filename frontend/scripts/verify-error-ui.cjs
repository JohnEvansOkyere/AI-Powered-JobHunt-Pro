// Uses synthetic responses only; no real accounts, passwords, CVs or SMS.
const assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const { fixture, fillSignup, newUser } = require('./verify-account-auth.cjs')
const base = process.env.TEST_BASE_URL || 'http://127.0.0.1:3027'
const privateDetail = 'SQLAlchemyError SELECT secret FROM users synthetic-private-detail /srv/app.py'
async function checkSafe(f) {
  assert.doesNotMatch(await f.page.locator('body').innerText(), /synthetic-private-detail|SQLAlchemy|SELECT secret|\/srv\/|\[object Object\]/)
  assert.equal(await f.page.locator('nextjs-portal').count(), 0, 'No runtime error overlay')
  assert.deepEqual(f.errors, [], 'No unhandled promise rejection or runtime exception')
  await f.context.close()
}
async function main() {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] })
  try {
    for (const width of [1440, 390]) {
      for (const code of ['invalid_credentials', 'unexpected_failure']) {
        const f = await fixture(browser, { width, loginError: { code, msg: privateDetail } })
        await f.page.goto(`${base}/auth/login`)
        await f.page.getByLabel('Email address', { exact: true }).fill('candidate@example.test')
        await f.page.getByLabel('Password', { exact: true }).fill('Synthetic-password-123')
        await f.page.getByRole('button', { name: 'Sign in', exact: true }).click()
        await f.page.getByText(code === 'invalid_credentials' ? 'The email or password is incorrect.' : 'Check the details you entered and try again.', { exact: true }).waitFor()
        await checkSafe(f)
      }
      const signup = await fixture(browser, { width, signupError: { msg: privateDetail } })
      await signup.page.goto(`${base}/auth/signup`)
      await fillSignup(signup.page)
      await signup.page.getByText('This service is temporarily unavailable. Please try again later.', { exact: true }).waitFor()
      await checkSafe(signup)

      const reset = await fixture(browser, { width })
      await reset.page.goto(`${base}/auth/reset-password`)
      await reset.page.getByLabel('Registered phone number').fill('0241234567')
      await reset.page.getByRole('button', { name: 'Send reset code', exact: true }).click()
      await reset.page.getByRole('alert').filter({ hasText: 'temporarily unavailable' }).waitFor()
      await checkSafe(reset)

      const profile = await fixture(browser, {
        width, signedIn: true, user: { ...newUser(), phone: '233241234567', phone_confirmed_at: '2026-09-06T00:00:00Z' },
        profileSaveError: privateDetail,
        cv: { id: 'synthetic-cv', file_name: 'test.pdf', file_size: 100, parsing_status: 'failed', parsing_error: privateDetail, created_at: '2026-09-06' },
      })
      await profile.page.goto(`${base}/dashboard/profile`)
      await profile.page.getByText('We could not read this CV. Try uploading a clear PDF or Word document.', { exact: true }).waitFor()
      const career = profile.page.locator('section').filter({ has: profile.page.getByRole('heading', { name: 'Career targeting', exact: true }) })
      await career.getByRole('button', { name: 'Edit', exact: true }).click()
      await career.getByRole('button', { name: 'Save', exact: true }).click()
      await profile.page.getByText('This service is temporarily unavailable. Please try again later.', { exact: true }).waitFor()
      assert.equal(await career.getByRole('button', { name: 'Cancel', exact: true }).count(), 1, 'Failed save keeps editor open')
      await profile.page.screenshot({ path: `/tmp/jobhunt-safe-errors-${width}.png`, fullPage: true })
      await checkSafe(profile)
    }
    console.log('PASS: desktop/mobile login, signup, reset, CV parsing and failed profile save show safe copy without runtime errors')
  } finally { await browser.close() }
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
