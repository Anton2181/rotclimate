// Browser check: the administration access panel shows the audit rebuilt on release-3 towns.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
const root = path.resolve(__dirname, '..'); const out = process.argv[2]; const base = (process.argv[3] || 'http://127.0.0.1:8766') + '/atlases/earth_fit/';
const sha = b => crypto.createHash('sha256').update(b).digest('hex'); const assert = (c, m) => { if (!c) throw new Error(m); };
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'atlases/earth_fit/data/release3/admin/administrative_access.json')));
  const browser = await chromium.launch(); const checks = [];
  for (const [mode, packet] of Object.entries(manifest.packets)) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } }); const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    const layer = packet.layers[0];
    for (const option of layer.variants.options) {
      await page.goto(base + '#layer=' + layer.id + '&variant=' + option.value + '&climate=' + mode, { waitUntil: 'domcontentloaded' }); await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForFunction(f => { const i = document.querySelector('#base'); return i && i.complete && i.naturalWidth > 0 && new URL(i.src).pathname.endsWith('/data/' + f); }, option.file, { timeout: 120000 });
      const reply = await page.request.get(base + 'data/' + option.file);
      assert(reply.ok() && sha(await reply.body()) === packet.image_sha256[option.file], 'bytes ' + option.file);
      checks.push({ climate: mode, case: option.value, file: option.file });
    }
    const bin = await page.request.get(base + 'data/' + packet.binary); assert(bin.ok() && sha(await bin.body()) === packet.binary_sha256, 'binary');
    await page.screenshot({ path: path.join(out, mode + '_administration.png') });
    assert(!errors.length, errors.join('; ')); await page.close();
  }
  await browser.close(); fs.writeFileSync(path.join(out, 'administration_browser.json'), JSON.stringify({ status: 'passed', checks }, null, 1) + '\n'); console.log('passed', checks.length);
})().catch(e => { console.error(e); process.exit(1); });
