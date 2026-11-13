// Browser check: grain supply maps load as Settlements options; the default map keeps loading with its new legend.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
const root = path.resolve(__dirname, '..'); const out = process.argv[2]; const base = (process.argv[3] || 'http://127.0.0.1:8766') + '/atlases/earth_fit/';
const sha = b => crypto.createHash('sha256').update(b).digest('hex'); const assert = (c, m) => { if (!c) throw new Error(m); };
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const read = f => JSON.parse(fs.readFileSync(path.join(root, 'atlases/earth_fit/data', f)));
  const supply = read('release3_supply.json'), towns = read('settlement_release3.json');
  const browser = await chromium.launch(); const checks = [];
  for (const mode of Object.keys(supply.packets)) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } }); const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto(base + '#layer=reach_towns&climate=' + mode, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelectorAll('#variant option').length > 2, null, { timeout: 120000 });
    assert(await page.locator('#variant').inputValue() === 'release3_central', 'default changed');
    for (const option of [...towns.packets[mode].options.reach_towns, ...supply.packets[mode].options.reach_towns]) {
      await page.selectOption('#variant', option.value);
      await page.waitForFunction(f => { const i = document.querySelector('#base'); return i.complete && i.naturalWidth > 0 && new URL(i.src).pathname.endsWith('/data/' + f); }, option.file, { timeout: 120000 });
      const reply = await page.request.get(base + 'data/' + option.file); assert(reply.ok() && sha(await reply.body()) === option.file_sha256, 'bytes ' + option.file);
      const text = await page.locator('body').innerText();
      assert(text.includes(option.value.includes('supply') ? 'Transport is paid in grain' : 'can be fed when grain may travel'), 'note ' + option.value);
      if (option.value.includes('supply')) await page.screenshot({ path: path.join(out, `${mode}_${option.value}.png`) });
      checks.push({ climate: mode, option: option.value });
    }
    assert(!errors.length, errors.join('; ')); await page.close();
  }
  await browser.close(); fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify({ status: 'passed', checks }, null, 1) + '\n'); console.log('passed', checks.length);
})().catch(e => { console.error(e); process.exit(1); });
