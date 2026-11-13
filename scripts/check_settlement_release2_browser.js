// Browser check: release-2 size maps load as normal Settlements options; defaults unchanged.
// Usage: node scripts/check_settlement_release2_browser.js <out-dir> [base-url]
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
const root = path.resolve(__dirname, '..'); const out = process.argv[2]; const base = (process.argv[3] || 'http://127.0.0.1:8766') + '/atlases/earth_fit/';
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const assert = (c, m) => { if (!c) throw new Error(m); };
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'atlases/earth_fit/data/settlement_release2.json')));
  const browser = await chromium.launch(); const checks = [];
  for (const [mode, packet] of Object.entries(manifest.packets)) {
    for (const [viewport, tag] of [[{ width: 1440, height: 1000 }, 'desktop'], [{ width: 390, height: 844 }, 'mobile']]) {
      const page = await browser.newPage({ viewport, deviceScaleFactor: tag === 'desktop' ? 2 : 1 }); const errors = [];
      page.on('pageerror', e => errors.push(String(e)));
      await page.goto(base + '#layer=reach_towns&climate=' + mode, { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => document.querySelectorAll('#variant option').length > 2, null, { timeout: 120000 });
      const initial = await page.locator('#variant').inputValue();
      assert(initial === 'joint365', 'default changed: ' + initial);
      const values = await page.$$eval('#variant option', o => o.map(x => x.value));
      for (const option of packet.options.reach_towns) {
        assert(values.includes(option.value), 'option hidden without the experimental switch');
        await page.selectOption('#variant', option.value);
        await page.waitForFunction(f => { const i = document.querySelector('#base'); return i.complete && i.naturalWidth > 0 && new URL(i.src).pathname.endsWith('/data/' + f); }, option.file, { timeout: 120000 });
        assert(await page.locator('#settled-section').isHidden(), 'legacy ledger panel shown for a size map');
        const text = await page.locator('body').innerText();
        assert((await page.locator('#variant option:checked').innerText()).includes('Earth-calibrated sizes'), 'label');
        assert(text.includes('NOT changed') && text.includes('density scenario'), 'limits note missing');
        let reply = await page.request.get(base + 'data/' + option.file);
        assert(reply.ok() && sha(await reply.body()) === option.file_sha256, 'map bytes');
        reply = await page.request.get(base + 'data/' + option.download);
        assert(reply.ok() && sha(await reply.body()) === packet.towns_csv_sha256, 'csv bytes');
        const shot = `${mode}_${option.value}_${tag}.png`; await page.screenshot({ path: path.join(out, shot) });
        checks.push({ climate: mode, option: option.value, viewport: tag, screenshot: shot });
      }
      await page.selectOption('#variant', 'joint365');
      await page.waitForFunction(() => document.querySelectorAll('#settled-readouts .readout').length === 6, null, { timeout: 120000 });
      assert(!errors.length, errors.join('; ')); await page.close();
    }
  }
  await browser.close();
  fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify({ status: 'passed', checks }, null, 1) + '\n'); console.log('passed', checks.length);
})().catch(e => { console.error(e); process.exit(1); });
