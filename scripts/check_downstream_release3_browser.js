// Browser check: reach and trade layers display their release-3 rebuild; legacy files stay reachable.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
const root = path.resolve(__dirname, '..'); const out = process.argv[2]; const base = (process.argv[3] || 'http://127.0.0.1:8766') + '/atlases/earth_fit/';
const sha = b => crypto.createHash('sha256').update(b).digest('hex'); const assert = (c, m) => { if (!c) throw new Error(m); };
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'atlases/earth_fit/data/release3_layers.json')));
  const browser = await chromium.launch(); const checks = [];
  for (const [mode, packet] of Object.entries(manifest.packets)) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } }); const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    for (const layer of packet.layers) {
      await page.goto(base + '#layer=' + layer.id + '&climate=' + mode, { waitUntil: 'domcontentloaded' });
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForFunction(m => { const i = document.querySelector('#base'); return i && i.complete && i.naturalWidth > 0 && new URL(i.src).pathname.includes('/data/release3/' + m + '/'); }, mode, { timeout: 120000 });
      const src = new URL(await page.locator('#base').getAttribute('src'), base).pathname.split('/data/')[1];
      const reply = await page.request.get(base + 'data/' + src);
      assert(reply.ok() && sha(await reply.body()) === packet.files[path.basename(src)], 'bytes ' + src);
      assert((await page.locator('body').innerText()).includes('Rebuilt on the release-3 towns'), 'note ' + layer.id);
      checks.push({ climate: mode, layer: layer.id, file: src });
    }
    for (const id of packet.unchanged_layers) {
      await page.goto(base + '#layer=' + id + '&climate=' + mode, { waitUntil: 'domcontentloaded' }); await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => { const i = document.querySelector('#base'); return i && i.complete && i.naturalWidth > 0; }, null, { timeout: 120000 });
      assert(!(await page.locator('#base').getAttribute('src')).includes('release3/'), 'unchanged layer swapped');
    }
    await page.goto(base + '#layer=reach_trade&climate=' + mode, { waitUntil: 'domcontentloaded' }); await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelectorAll('#variant option').length >= 2, null, { timeout: 120000 });
    await page.screenshot({ path: path.join(out, mode + '_trade.png') });
    assert(!errors.length, errors.join('; ')); await page.close();
  }
  await browser.close(); fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify({ status: 'passed', checks }, null, 1) + '\n'); console.log('passed', checks.length);
})().catch(e => { console.error(e); process.exit(1); });
