// Verify the identity panel, its served downloads, keyboard opening and mobile themes.
// Usage: serve the checkout root on 127.0.0.1:8766, then
//   NODE_PATH=<playwright node_modules> node scripts/check_settlement_size_identity_browser.js [shape]
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const BASE = 'http://127.0.0.1:8766';
const PANELS = {
  identity: { id: 'settlement-size-identity', folder: 'settlement_size_identity_20261112',
    phrases: ['Still no AD150 size target.', '50 of 50 samples joined by author key'],
    retained: ['settlement-sizes', 'settlement-feedback', 'settlement-feedback-scan'] },
  shape: { id: 'settlement-size-shape', folder: 'settlement_size_shape_20261112',
    phrases: ['The allocator is more equal than every reference.', 'development diagnostic, no fit'],
    retained: ['settlement-size-identity', 'settlement-sizes', 'settlement-feedback', 'settlement-feedback-scan'] } };
const PANEL = PANELS[process.argv[2] || 'identity'];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(BASE + '/atlases/earth_evidence/', { waitUntil: 'domcontentloaded' });
  const panel = page.locator('#' + PANEL.id);
  if (await panel.getAttribute('open') !== null) throw new Error('Panel should start collapsed');
  await panel.locator('summary').focus();
  await page.keyboard.press('Enter');
  if (await panel.getAttribute('open') === null) throw new Error('Keyboard did not open the panel');
  const text = await panel.innerText();
  for (const phrase of PANEL.phrases) {
    if (!text.includes(phrase)) throw new Error('Missing text: ' + phrase);
  }
  await panel.locator('img').scrollIntoViewIfNeeded();
  await page.waitForFunction((id) => document.querySelector('#' + id + ' img').naturalWidth > 0, PANEL.id);
  let links = 0;
  for (const link of await panel.locator('a').all()) {
    const url = new URL(await link.evaluate((el) => el.href));
    if (url.host !== '127.0.0.1:8766') continue;
    const response = await page.request.get(url.href);
    if (!response.ok()) throw new Error('Not served: ' + url.href);
    const local = fs.readFileSync(path.join(ROOT, decodeURIComponent(url.pathname)));
    if (!local.equals(await response.body())) throw new Error('Served bytes differ: ' + url.pathname);
    links += 1;
  }
  for (const theme of ['light', 'dark']) {
    await page.emulateMedia({ colorScheme: theme });
    for (const width of [344, 390]) {
      await page.setViewportSize({ width, height: 844 });
      const fits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1);
      if (!fits) throw new Error(`Horizontal overflow at ${width}px, ${theme}`);
    }
  }
  const retained = {};
  for (const id of PANEL.retained) {
    retained[id] = await page.locator('#' + id).count();
    if (retained[id] !== 1) throw new Error('Preceding panel missing: ' + id);
  }
  if (errors.length) throw new Error(errors.join('; '));
  await page.setViewportSize({ width: 390, height: 844 });
  const out = path.join(ROOT, 'output', PANEL.folder, 'browser');
  fs.mkdirSync(out, { recursive: true });
  await panel.screenshot({ path: path.join(out, 'panel_mobile.png') });
  await browser.close();
  fs.writeFileSync(path.join(out, 'review.json'), JSON.stringify({
    status: 'passed', keyboard_open: true, local_links_byte_exact: links, figure_loaded: true,
    mobile_widths: [344, 390], themes: ['light', 'dark'], preceding_panels_retained: PANEL.retained,
    page_errors: errors }, null, 2) + '\n');
  console.log(`${PANEL.id} passed; ${links} local links byte exact, keyboard/mobile/dark and preceding panels retained.`);
})().catch((e) => { console.error(e); process.exit(1); });
