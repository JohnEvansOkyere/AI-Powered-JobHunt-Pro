// Run with: node scripts/verify-errors.cjs. No network or live accounts.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')
const Module = require('node:module')
let signOuts = 0
const modules = new Map()
function load(relative) {
  const filename = path.resolve(__dirname, '..', relative)
  if (modules.has(filename)) return modules.get(filename).exports
  const mod = new Module(filename, module)
  modules.set(filename, mod)
  mod.filename = filename
  mod.paths = module.paths
  mod.require = (name) => {
    if (name === '../auth') return { getCurrentSession: async () => null, signOut: async () => { signOuts++ } }
    if (name === '../errors') return load('lib/errors.ts')
    return require(name)
  }
  mod._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, filename)
  return mod.exports
}
const { getUserErrorMessage } = load('lib/errors.ts')
const { ApiClient } = load('lib/api/client.ts')
const { requestPasswordReset, PasswordResetError } = load('lib/api/password-reset.ts')
const privateMessage = 'SQLAlchemyError SELECT secret FROM users /srv/app.py Hook requires authorization token'
async function main() {
  assert.equal(getUserErrorMessage(new Error(privateMessage), 'Please retry.'), 'Please retry.')
  assert.match(getUserErrorMessage({ code: 'invalid_credentials', message: privateMessage, status: 400 }), /email or password is incorrect/)
  assert.match(getUserErrorMessage({ code: 'otp_expired', message: privateMessage, status: 403 }), /invalid or expired/)
  assert.match(getUserErrorMessage({ code: 'phone_provider_disabled', message: privateMessage, status: 400 }), /temporarily unavailable/)
  assert.equal(typeof getUserErrorMessage({ code: '__proto__', message: privateMessage }), 'string')
  const client = new ApiClient('https://synthetic.test')
  for (const body of [{ detail: privateMessage }, { error: { message: privateMessage } }, { detail: [{ msg: privateMessage }] }]) {
    for (const status of [400, 403, 500, 503]) {
      global.fetch = async () => Response.json(body, { status, headers: { 'X-Request-ID': 'test-reference' } })
      for (const call of [() => client.get('/test'), () => client.getBlob('/test')]) {
        await assert.rejects(call, (error) => {
          assert.equal(error.status, status)
          assert.equal(error.requestId, 'test-reference')
          assert.doesNotMatch(error.message, /SQLAlchemy|SELECT|srv|authorization token|\[object Object\]/)
          return true
        })
      }
    }
  }
  assert.equal(signOuts, 0, 'Service errors and ordinary permission denials must not sign users out')
  global.fetch = async () => Response.json({ detail: 'Invalid authentication credentials' }, { status: 401 })
  await assert.rejects(() => client.get('/test'), /sign in again/)
  assert.equal(signOuts, 1)
  global.fetch = async () => new Response('<html>private proxy trace</html>', { status: 502 })
  await assert.rejects(() => client.get('/test'), /temporarily unavailable/)
  global.fetch = async () => new Response('<html>private proxy trace</html>', { status: 200 })
  await assert.rejects(() => client.get('/test'), /could not read the response/)
  global.fetch = async () => { throw new TypeError('Failed to fetch private host') }
  await assert.rejects(() => client.get('/test'), /Check your connection/)
  await assert.rejects(() => client.getBlob('/test'), /Check your connection/)
  global.fetch = async () => Response.json({ detail: privateMessage }, { status: 429, headers: { 'Retry-After': '90' } })
  await assert.rejects(() => requestPasswordReset('0241234567'), (error) => {
    assert.ok(error instanceof PasswordResetError)
    assert.equal(error.retryAfter, 90)
    assert.match(error.message, /Too many attempts/)
    return true
  })
  global.fetch = async () => Response.json({ detail: 'This reset has expired or was already used. Request a new code.' }, { status: 400 })
  await assert.rejects(() => requestPasswordReset('0241234567'), /Request a new code/)
  global.fetch = async () => new Response(null, { status: 204 })
  assert.equal(await client.delete('/test'), undefined)
  console.log('PASS: safe API/auth messages, downloads, malformed responses, network failures, auth cleanup and reset retry semantics')
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
