// Browser check of the rain-timing evidence page: rows, filters, chart, downloads, themes, mobile, navigation.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
const root = path.resolve(__dirname, '..'); const out = process.argv[2]; const base = (process.argv[3] || 'http://127.0.0.1:8766') + '/atlases/';
const sha = b => crypto.createHash('sha256').update(b).digest('hex'); const assert = (c, m) => { if (!c) throw new Error(m); };
(async () => {
  fs.mkdirSync(out, { recursive: true }); const pub = JSON.parse(fs.readFileSync(path.join(root, 'output/rain_timing_20261114/publication.json')));
  const browser = await chromium.launch(); const checks = [];
  for (const [viewport, scheme, tag] of [[{ width: 1440, height: 1000 }, 'light', 'desktop_light'], [{ width: 1440, height: 1000 }, 'dark', 'desktop_dark'], [{ width: 390, height: 844 }, 'light', 'mobile_light'], [{ width: 390, height: 844 }, 'dark', 'mobile_dark']]) {
    const page = await browser.newPage({ viewport, colorScheme: scheme }); const errors = []; page.on('pageerror', e => errors.push(String(e)));
    await page.goto(base + 'earth_evidence/rain_timing/', { waitUntil: 'load' });
    assert(await page.locator('tbody tr').count() === 32, 'rows');
    assert(await page.evaluate(() => { const i = document.querySelector('img'); return i.complete && i.naturalWidth > 0; }), 'chart');
    await page.selectOption('#region', 'nile'); assert(await page.locator('tbody tr:visible').count() === 16 && (await page.locator('#count').innerText()) === '16 scenarios', 'region filter');
    await page.selectOption('#access', '1'); assert(await page.locator('tbody tr:visible').count() === 8, 'access filter');
    await page.selectOption('#region', ''); await page.selectOption('#access', ''); assert(await page.locator('tbody tr:visible').count() === 32, 'reset');
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'horizontal page scroll');
    for (const name of ['plan.json', 'results.json', 'review.json', 'fields.npz', 'rain_timing.png']) {
      const reply = await page.request.get(base + 'earth_evidence/rain_timing/' + name);
      assert(reply.ok() && sha(await reply.body()) === pub.files['atlases/earth_evidence/rain_timing/' + name], 'download ' + name);
    }
    await page.keyboard.press('Tab'); assert(await page.evaluate(() => document.activeElement.tagName === 'A'), 'keyboard focus');
    await page.screenshot({ path: path.join(out, tag + '.png') }); assert(!errors.length, errors.join('; ')); checks.push(tag); await page.close();
  }
  const page = await browser.newPage(); await page.goto(base + 'earth_evidence/', { waitUntil: 'load' });
  assert(await page.locator('#rain-timing a').getAttribute('href') === 'rain_timing/', 'evidence panel link');
  await page.goto(base, { waitUntil: 'load' }); assert(await page.locator('a[href="earth_evidence/rain_timing/"]').count() >= 1, 'hub link');
  await browser.close(); fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify({ status: 'passed', viewports: checks, downloads: 5 }, null, 1) + '\n'); console.log('passed', checks.length, 'viewport/theme cases');
})().catch(e => { console.error(e); process.exit(1); });
