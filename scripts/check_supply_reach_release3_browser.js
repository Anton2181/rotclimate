// Browser check: supply-supported reach defaults to the release-3 rebuild; earlier options still work.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
const root = path.resolve(__dirname, '..'); const out = process.argv[2]; const base = (process.argv[3] || 'http://127.0.0.1:8766') + '/atlases/earth_fit/';
const sha = b => crypto.createHash('sha256').update(b).digest('hex'); const assert = (c, m) => { if (!c) throw new Error(m); };
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'atlases/earth_fit/data/release3_reach.json')));
  const browser = await chromium.launch(); const checks = [];
  for (const [mode, packet] of Object.entries(manifest.packets)) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } }); const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto(base + '#layer=reach_defacto&climate=' + mode, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelectorAll('#variant option').length > 2, null, { timeout: 120000 });
    assert(await page.locator('#variant').inputValue() === 'release3_fed_v21', 'default is not the supply-fed release-3 control map');
    console.log(mode, 'default ok');
    for (const option of packet.options.reach_defacto) {
      await page.selectOption('#variant', option.value);
      await page.waitForFunction(f => { const i = document.querySelector('#base'); return i.complete && i.naturalWidth > 0 && new URL(i.src).pathname.endsWith('/data/' + f); }, option.file, { timeout: 120000 });
      const reply = await page.request.get(base + 'data/' + option.file); assert(reply.ok() && sha(await reply.body()) === option.file_sha256, 'bytes');
      assert(/release-3 town(s AND residents| POSITIONS)/.test(await page.locator('body').innerText()), 'note');
      await page.screenshot({ path: path.join(out, `${mode}_${option.value}.png`) }); checks.push({ climate: mode, option: option.value });
    }
    await page.selectOption('#variant', 'v21_joint365');          // earlier default still selectable, with its own image
    await page.waitForFunction(() => { const i = document.querySelector('#base'); return i.complete && i.naturalWidth > 0 && new URL(i.src).pathname.endsWith('settled_control_v21_joint365.webp') && !i.src.includes('release3/'); }, null, { timeout: 60000 });
    assert(!errors.length, errors.join('; ')); await page.close();
  }
  await browser.close(); fs.writeFileSync(path.join(out, 'supply_reach_browser.json'), JSON.stringify({ status: 'passed', checks }, null, 1) + '\n'); console.log('passed', checks.length);
})().catch(e => { console.error(e); process.exit(1); });
