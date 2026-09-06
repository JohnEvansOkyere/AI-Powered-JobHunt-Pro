// Run unit assertions: node scripts/verify-seo.cjs --unit
// Browser/HTML checks: NEXT_PUBLIC_API_URL=http://127.0.0.1:8119 in an isolated
// Next build, then TEST_BASE_URL=http://127.0.0.1:3049 PLAYWRIGHT_PATH=/path/to/playwright node scripts/verify-seo.cjs
// Uses synthetic jobs and a local API only. No candidate accounts or live services.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const http = require('node:http')
const path = require('node:path')
const ts = require('typescript')
require.extensions['.ts'] = (module, filename) => module._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, filename)
const { publicApplyUrl, isClosedJob, isIndexableJob, jobPosting } = require('../lib/job-seo.ts')
const { serializeJsonLd, canonicalOrigin } = require('../lib/site.ts')
const { parseJobSearch, jobSearchHref } = require('../lib/job-search.ts')

const id = index => `22222222-2222-4222-8222-${String(index).padStart(12, '0')}`
const now = new Date().toISOString()
const job = {
  id: id(1), title: 'Data Analyst', company: 'Example Employer', location: 'Accra, Ghana',
  description: 'Analyse data using SQL and Excel.', requirements: 'Experience presenting findings.',
  posted_date: now, scraped_at: now, created_at: now, updated_at: now,
  application_deadline: new Date(Date.now() + 86400000 * 3).toISOString(),
  processing_status: 'processed', source: 'fixture', source_id: null,
  job_link: 'https://employer.example.test/apply', source_url: null,
  job_type: 'full-time', remote_type: 'onsite', normalized_title: null, normalized_location: null, salary_range: null,
}

function unitChecks() {
  assert.equal(canonicalOrigin('http://veloxahire.org/'), 'https://www.veloxahire.org')
  assert.equal(canonicalOrigin('http://localhost:3049/path'), 'http://localhost:3049')
  assert.equal(jobPosting(job).jobLocation.address.addressCountry, 'GH')
  assert.equal(jobPosting(job).employmentType, 'FULL_TIME')
  assert.equal(jobPosting(job).validThrough, job.application_deadline)
  assert.equal(jobPosting({ ...job, application_deadline: null }).validThrough, undefined)
  assert.equal(jobPosting({ ...job, location: 'Accra' }), null)
  assert.equal(jobPosting({ ...job, location: 'Worldwide', remote_type: 'remote' }), null)
  assert.equal(jobPosting({ ...job, location: 'Ghana', remote_type: 'remote' }).applicantLocationRequirements.name, 'GH')
  assert.equal(jobPosting({ ...job, location: 'Accra, Ghana', remote_type: 'remote' }), null)
  assert.equal(jobPosting({ ...job, remote_type: 'not-remote' }).jobLocationType, undefined)
  assert.equal(jobPosting({ ...job, processing_status: 'pending' }), null)
  assert.equal(isClosedJob({ ...job, application_deadline: '2020-01-01T00:00:00Z' }), true)
  assert.equal(isIndexableJob({ ...job, application_deadline: '2020-01-01T00:00:00Z' }), false)
  assert.equal(publicApplyUrl({ ...job, job_link: 'javascript:alert(1)', source_url: 'https://example.test/apply' }), 'https://example.test/apply')
  assert.equal(publicApplyUrl({ ...job, job_link: 'https://user:secret@example.test/' }), '')
  const hostile = '</script><script>alert(1)</script>'
  assert.equal(serializeJsonLd({ title: hostile }).includes('<'), false)
  assert.equal(JSON.parse(serializeJsonLd({ title: hostile })).title, hostile)
  assert.equal(jobSearchHref(parseJobSearch({ q: 'SQL & Excel', page: '2', utm_source: 'chatgpt' })), '/jobs?q=SQL+%26+Excel&page=2')
  assert.equal(jobSearchHref(parseJobSearch({ page: '-3' })), '/jobs')
  console.log('PASS: 20 SEO data, schema and query assertions')
}

async function browserChecks() {
  const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
  const base = process.env.TEST_BASE_URL || 'http://127.0.0.1:3049'
  let apiFailed = false
  let leakedAuth = false
  const inventory = Array.from({ length: 21 }, (_, index) => ({ ...job, id: id(index + 1), title: `Data Analyst ${index + 1}` }))
  const api = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', base)
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    res.setHeader('Content-Type', 'application/json')
    if (req.method === 'OPTIONS') { res.writeHead(204); return res.end() }
    const url = new URL(req.url, base)
    if (url.pathname.startsWith('/api/v1/jobs')) leakedAuth ||= Boolean(req.headers.authorization || req.headers.cookie)
    if (url.pathname === '/api/v1/jobs/sitemap') return res.end(JSON.stringify(inventory.map(({ id, updated_at }) => ({ id, updated_at }))))
    if (url.pathname === '/api/v1/jobs/') {
      if (apiFailed || url.searchParams.get('q') === 'outage') { res.writeHead(503); return res.end('{}') }
      const page = Number(url.searchParams.get('page') || 1)
      const pageSize = Number(url.searchParams.get('page_size') || 20)
      const filtered = url.searchParams.get('q') ? inventory.filter(j => j.title.includes(url.searchParams.get('q'))) : inventory
      return res.end(JSON.stringify({ jobs: filtered.slice((page - 1) * pageSize, page * pageSize), page, page_size: pageSize, total: filtered.length, total_pages: Math.ceil(filtered.length / pageSize) }))
    }
    if (url.pathname === `/api/v1/jobs/${id(99)}`) return res.end(JSON.stringify({ ...job, id: id(99), application_deadline: '2020-01-01T00:00:00Z' }))
    if (url.pathname === `/api/v1/jobs/${id(98)}`) return res.end(JSON.stringify({ ...job, id: id(98), processing_status: 'pending' }))
    if (url.pathname.startsWith('/api/v1/jobs/')) {
      const found = inventory.find(j => url.pathname.endsWith(j.id))
      if (!found) { res.writeHead(404); return res.end('{}') }
      return res.end(JSON.stringify(found))
    }
    return res.end('{}')
  })
  await new Promise(resolve => api.listen(8119, '127.0.0.1', resolve))
  let browser
  try {
    browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] })
    const errors = []
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
    await context.route('https://seo-test.supabase.co/**', route => route.fulfill({ json: {} }))
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    for (const route of ['/', '/jobs', '/about', '/how-it-works', '/job-sources', '/contact', '/ghana-jobs', '/guides/remote-jobs-from-ghana', '/privacy', '/terms', '/remote-jobs']) {
      const response = await page.goto(base + route)
      assert.equal(response.status(), 200, route)
      await page.locator('h1').waitFor()
      assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://www.veloxahire.org' + (route === '/' ? '' : route))
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, route)
    }
    await page.goto(base + '/jobs')
    await page.getByRole('link', { name: 'Next', exact: true }).click()
    await page.waitForURL('**/jobs?page=2')
    await page.getByRole('heading', { name: 'Data Analyst 21', exact: true }).first().waitFor()
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://www.veloxahire.org/jobs?page=2')
    await page.goBack()
    await page.getByRole('link', { name: 'Next', exact: true }).waitFor()
    await page.getByPlaceholder('Job title, company or keyword').fill('Data Analyst 21')
    await page.getByRole('button', { name: 'Search jobs', exact: true }).click()
    await page.waitForURL('**/jobs?q=Data+Analyst+21')
    assert.match(await page.locator('meta[name="robots"]').getAttribute('content'), /noindex/)
    await page.goto(base + '/jobs?utm_source=chatgpt.com')
    assert.equal(await page.locator('meta[name="robots"]').count(), 0)
    const raw = await context.request.get(base + '/jobs')
    assert.match(await raw.text(), new RegExp('/jobs/' + id(1)))
    assert.match(await raw.text(), /\/jobs\?page=2/)
    await page.goto(base + '/jobs/' + id(1))
    const schema = await page.locator('script[type="application/ld+json"]').allTextContents()
    const posting = schema.map(JSON.parse).find(value => value['@type'] === 'JobPosting')
    assert.equal(posting.jobLocation.address.addressCountry, 'GH')
    assert.equal(posting.validThrough, job.application_deadline)
    assert.equal(await page.getByRole('link', { name: 'Apply now', exact: true }).getAttribute('href'), job.job_link)
    for (const route of ['/jobs/not-a-uuid', '/jobs/' + id(99), '/jobs/' + id(777), '/jobs?page=999']) {
      const response = await context.request.get(base + route)
      assert.equal(response.status(), 404, route)
      assert.doesNotMatch(await response.text(), /"@type":"JobPosting"/)
    }
    await page.goto(base + '/jobs/' + id(98))
    assert.match(await page.locator('meta[name="robots"]').getAttribute('content'), /noindex/)
    for (const route of ['/auth/login', '/dashboard', '/profile/setup', '/register']) {
      const response = await context.request.get(base + route, { maxRedirects: 0 })
      assert.match(response.headers()['x-robots-tag'], /noindex/)
    }
    const sitemap = await context.request.get(base + '/sitemap.xml')
    assert.match(sitemap.headers()['content-type'], /xml/)
    const xml = await sitemap.text()
    assert.match(xml, /https:\/\/www.veloxahire.org\/about/)
    assert.match(xml, new RegExp(id(21)))
    assert.doesNotMatch(xml, /<loc>https:\/\/veloxahire.org/)
    const robots = await (await context.request.get(base + '/robots.txt')).text()
    assert.match(robots, /Sitemap: https:\/\/www.veloxahire.org\/sitemap.xml/)
    assert.doesNotMatch(robots, /Disallow: \/auth/)
    apiFailed = true
    await page.goto(base + '/jobs?q=outage')
    await page.getByRole('heading', { name: 'We could not load the jobs.' }).waitFor()
    assert.match(await page.locator('meta[name="robots"]').getAttribute('content'), /noindex/)
    apiFailed = false
    // Clear the outage query and verify the preserved form can recover.
    await page.getByPlaceholder('Job title, company or keyword').fill('Data Analyst 1')
    await page.getByRole('button', { name: 'Search jobs', exact: true }).click()
    await page.getByRole('link', { name: 'View full job' }).first().waitFor()
    for (const width of [390, 360]) {
      await page.setViewportSize({ width, height: 900 })
      for (const route of ['/jobs', '/about', '/ghana-jobs', '/jobs/' + id(1)]) {
        await page.goto(base + route)
        await page.locator('h1').waitFor()
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${route} ${width}`)
      }
      await page.screenshot({ path: `/tmp/veloxa-seo-mobile-${width}.png`, fullPage: true })
    }
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto(base + '/about')
    await page.screenshot({ path: '/tmp/veloxa-seo-about.png', fullPage: true })
    const noJs = await browser.newContext({ javaScriptEnabled: false })
    const crawlerPage = await noJs.newPage()
    await crawlerPage.goto(base + '/jobs')
    assert.equal(await crawlerPage.getByRole('link', { name: 'View full job' }).count(), 20)
    await crawlerPage.getByRole('link', { name: 'Next', exact: true }).click()
    assert.equal(await crawlerPage.getByRole('link', { name: 'View full job' }).count(), 1)
    assert.equal(leakedAuth, false)
    assert.deepEqual(errors, [])
    await noJs.close()
    await context.close()
    console.log('PASS: public pages, canonical metadata, raw HTML, no-JS pagination, filters/back navigation, schema, deadlines/404s, robots, sitemap, outage recovery and 360/390px layouts')
  } finally {
    if (browser) await browser.close()
    await new Promise(resolve => api.close(resolve))
  }
}

unitChecks()
if (!process.argv.includes('--unit')) browserChecks().catch(error => { console.error(error); process.exitCode = 1 })
