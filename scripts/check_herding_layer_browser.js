// Browser check: the forest layer loads in both climates without page errors.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const out = process.argv[2]; const base = (process.argv[3] || 'http://127.0.0.1:8766') + '/atlases/earth_fit/';
(async () => {
  fs.mkdirSync(out, { recursive: true }); const browser = await chromium.launch(); const checks = [];
  for (const mode of ['raw', 'corrected']) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } }); const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto(base + '#layer=land_herding&climate=' + mode, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => { const i = document.querySelector('#base'); return i && i.complete && i.naturalWidth > 0 && i.src.includes('land_herding'); }, null, { timeout: 120000 });
    const text = await page.locator('body').innerText(); if (!text.includes('Herders')) throw new Error('label missing ' + mode);
    if (errors.length) throw new Error(errors.join('; '));
    await page.screenshot({ path: path.join(out, mode + '_forest.png') }); checks.push(mode); await page.close();
  }
  await browser.close(); fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify({ status: 'passed', checks }, null, 1) + '\n'); console.log('passed', checks.length);
})().catch(e => { console.error(e); process.exit(1); });
