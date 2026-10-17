/**
 * Capture dashboard screenshots for the README.
 *
 * Drives the real SOC console with Puppeteer: logs in, visits each tab
 * and writes PNGs into docs/screenshots/.
 *
 * Prerequisites (one-off):
 *   npm install --save-dev puppeteer
 *
 * Then, with the stack already running:
 *   # terminal 1 — backend
 *   python -m uvicorn backend.main:app --port 8000
 *   # terminal 2 — frontend
 *   cd frontend && npm run dev
 *   # terminal 3 — demo data + screenshots
 *   python scripts/demo_seed.py
 *   node scripts/capture_screenshots.mjs
 */
import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(__dirname, '..', 'docs', 'screenshots');
const BASE_URL = process.env.SOC_URL || 'http://127.0.0.1:5173';
const USERNAME = process.env.SOC_USER || 'admin';
const PASSWORD = process.env.SOC_PASS || 'admin12345';

const PAGES = [
  { tab: 'Dashboard', file: '01-dashboard.png' },
  { tab: 'Incidents', file: '02-incidents.png' },
  { tab: 'ML Anomalies', file: '03-ml-anomalies.png' },
  { tab: 'Threat Intel', file: '04-threat-intel.png' },
  { tab: 'Security Logs', file: '05-security-logs.png' },
  { tab: 'System Health', file: '06-system-health.png' },
];

/** Click a navbar tab by its visible label. */
async function clickTab(page, label) {
  const clicked = await page.evaluate((text) => {
    const btn = Array.from(document.querySelectorAll('.nav-tab-btn'))
      .find((b) => b.innerText.trim().startsWith(text));
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  }, label);
  if (!clicked) throw new Error(`Nav tab not found: ${label}`);
  // Let the page fetch its data and settle animations
  await new Promise((r) => setTimeout(r, 1500));
}

const main = async () => {
  await mkdir(OUT_DIR, { recursive: true });

  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1000, deviceScaleFactor: 1 });

  console.log(`→ ${BASE_URL}`);
  await page.goto(BASE_URL, { waitUntil: 'networkidle2' });

  // ── Login ──────────────────────────────────────────────────────
  const needsLogin = await page.$('#login-username');
  if (needsLogin) {
    console.log('→ logging in…');
    await page.type('#login-username', USERNAME);
    await page.type('#login-password', PASSWORD);
    await Promise.all([
      page.click('button[type="submit"]'),
      page.waitForSelector('.nav-tabs', { timeout: 15000 }),
    ]);
  }
  await page.waitForSelector('.metric-value', { timeout: 15000 });

  // ── Capture each page ──────────────────────────────────────────
  for (const { tab, file } of PAGES) {
    console.log(`→ capturing ${tab}`);
    await clickTab(page, tab);
    const target = resolve(OUT_DIR, file);
    await page.screenshot({ path: target, fullPage: false });
    console.log(`   saved ${file}`);
  }

  // ── Bonus: incident detail drawer with the AI investigation ────
  console.log('→ capturing incident detail drawer');
  await clickTab(page, 'Incidents');
  const opened = await page.evaluate(() => {
    const row = document.querySelector('.soc-table tbody tr');
    if (row) {
      row.click();
      return true;
    }
    return false;
  });
  if (opened) {
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: resolve(OUT_DIR, '07-incident-detail.png') });
    console.log('   saved 07-incident-detail.png');
  }

  await browser.close();
  console.log(`\nDone — screenshots in ${OUT_DIR}`);
};

main().catch((err) => {
  console.error('Capture failed:', err.message);
  process.exit(1);
});