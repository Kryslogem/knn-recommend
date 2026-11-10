// Captures UI screenshots for the report: node scripts/screenshots.mjs
// Needs: backend on :8000, frontend dev server on :5173, seeded DB, Edge/Chrome installed.
// Uses the local seed accounts from .env (admin / datasci / demo); passwords are never printed.
// The demo account's ratings are removed again at the end, so the database is left as it was found.
import { readFileSync, mkdirSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(join(root, 'frontend', 'package.json'))
const puppeteer = require('puppeteer-core')

const BASE = process.env.UI_URL ?? 'http://localhost:5173'
const OUT = join(root, 'docs', 'screenshots')
mkdirSync(OUT, { recursive: true })

const env = Object.fromEntries(
  readFileSync(join(root, '.env'), 'utf8')
    .split(/\r?\n/)
    .filter((l) => l.includes('=') && !l.startsWith('#'))
    .map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1)]),
)
const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(existsSync)
if (!CHROME) throw new Error('No Chrome/Edge found')

async function api(path, { token, method = 'GET', body } = {}) {
  const r = await fetch(`${BASE}/api/v1${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(`${method} ${path} -> ${r.status}`)
  return r.json()
}
const login = async (u, p) => (await api('/auth/login', { method: 'POST', body: { username: u, password: p } })).access_token

const tokens = {
  user: await login(env.KNN_SEED_USER_USERNAME, env.KNN_SEED_USER_PASSWORD),
  admin: await login(env.KNN_SEED_ADMIN_USERNAME, env.KNN_SEED_ADMIN_PASSWORD),
  ds: await login(env.KNN_SEED_DS_USERNAME, env.KNN_SEED_DS_PASSWORD),
}

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox'] })

async function shot(name, { token, path, width = 1440, height = 900, full = true, wait = 1200, act }) {
  const page = await browser.newPage()
  await page.setViewport({ width, height })
  if (token) await page.evaluateOnNewDocument((t) => localStorage.setItem('token', t), token)
  await page.goto(BASE + path, { waitUntil: 'networkidle0' })
  await new Promise((r) => setTimeout(r, wait))
  if (act) await act(page)
  await page.screenshot({ path: join(OUT, `${name}.png`), fullPage: full })
  const errors = await page.evaluate(() => document.querySelectorAll('[role="alert"]').length)
  console.log(`${name}.png${errors ? `  (!) ${errors} alert element(s) on page` : ''}`)
  await page.close()
}

try {
  await shot('01-login', { path: '/login', full: false })
  await shot('02-onboarding', { token: tokens.user, path: '/onboarding', full: false })

  // Build a profile for the demo user so recommendations are personalized.
  const pop = await api('/movies/popular?n=12', { token: tokens.user })
  const ratings = [5, 4, 5, 2, 4, 5, 1, 4]
  for (const [i, r] of ratings.entries()) await api(`/ratings/${pop.items[i].id}`, { token: tokens.user, method: 'PUT', body: { rating: r } })

  await shot('03-catalog', { token: tokens.user, path: '/movies', full: false })
  await shot('04-recommendations', { token: tokens.user, path: '/recommendations', full: false })
  await shot('05-explain', {
    token: tokens.user,
    path: '/recommendations',
    full: false,
    act: async (page) => {
      const btn = await page.evaluateHandle(() => [...document.querySelectorAll('button')].find((b) => /^why\?/i.test(b.textContent.trim())))
      await btn.asElement().click()
      await new Promise((r) => setTimeout(r, 600))
    },
  })
  await shot('06-history', { token: tokens.user, path: '/history', full: false })
  await shot('07-mobile-recommendations', { token: tokens.user, path: '/recommendations', width: 390, height: 844, full: false })
  await shot('08-admin-overview', { token: tokens.admin, path: '/admin' })
  await shot('09-admin-users', { token: tokens.admin, path: '/admin/users', full: false })
  await shot('10-ds-data', { token: tokens.ds, path: '/ds', wait: 2000 })
  await shot('11-ds-training', { token: tokens.ds, path: '/ds/train', full: false })
  await shot('12-ds-models', { token: tokens.ds, path: '/ds/models', full: false })
  await shot('13-ds-evaluation', { token: tokens.ds, path: '/ds/evaluation', wait: 2500 })
} finally {
  const mine = await api('/ratings/me?page_size=100', { token: tokens.user })
  for (const it of mine.items) await api(`/ratings/${it.movie.id}`, { token: tokens.user, method: 'DELETE' })
  await browser.close()
}
