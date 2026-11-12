// Exercise the optional market-hierarchy maps in the normal Earth atlas.
//   serve the checkout root on 127.0.0.1:8766, then
//   NODE_PATH=<playwright node_modules> node scripts/check_settlement_market_browser.js
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const DATA = path.join(ROOT, 'atlases/earth_fit/data');
const BASE = 'http://127.0.0.1:8766/atlases/earth_fit/';
const OUT = path.join(ROOT, 'output/settlement_market_range_20261112/browser');
const fmt = (v) => Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 });

(async () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(DATA, 'settlement_market.json')));
  const browser = await chromium.launch(); const checks = []; fs.mkdirSync(OUT, { recursive: true });
  for (const [mode, packet] of Object.entries(manifest.packets)) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } }); const errors = [];
    page.on('pageerror', (e) => errors.push(String(e)));
    const model = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(DATA, packet.payload))));
    await page.goto(BASE + '#layer=reach_towns&climate=' + mode, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelectorAll('#settled-readouts .readout').length === 11, null, { timeout: 90000 });
    const initial = await page.locator('#variant').inputValue();
    if (initial !== manifest.default_settlements) throw new Error('Settlements does not open on the adopted default: ' + initial);
    if (await page.locator('#variant option[value^="market"]').count() !== 1) throw new Error('Only the default market option may show before the experimental switch');
    if (!await page.locator('#variant option[value="joint365"]').count()) throw new Error('Previous default is not selectable in the core view');
    const badge = (await page.locator('#variant option:checked').innerText()).toLowerCase();
    if (badge.includes('experimental') || !badge.includes('default')) throw new Error('Default option mislabelled: ' + badge);
    await page.locator('#experimental').check();
    let maps = 0;
    for (const layer of ['reach_towns', 'reach_defacto']) {
      await page.click('#layer-' + layer);
      for (const option of packet.options[layer]) {
        await page.selectOption('#variant', option.value);
        await page.waitForFunction((file) => document.querySelectorAll('#settled-readouts .readout').length === 11 && document.querySelector('#base').complete
          && document.querySelector('#base').naturalWidth > 0 && new URL(document.querySelector('#base').src).pathname.endsWith('/data/' + file), option.file, { timeout: 90000 });
        const label = (await page.locator('#variant option:checked').innerText()).toLowerCase();
        const isDefault = layer === 'reach_towns' && option.value === manifest.default_settlements;
        if (label.includes('experimental') === isDefault) throw new Error('Wrong evidence tier for ' + option.value + ': ' + label);
        const c = model.cases.find((x) => x.id === option.value); const h = c.market_hierarchy;
        const totals = c.civilian_people.map((v, i) => v + c.institutional_people[i]); const j = totals.indexOf(Math.max(...totals));
        await page.selectOption('#settled-site', model.sites[j].id);
        const readouts = await page.locator('#settled-readouts').innerText();
        for (const value of [fmt(c.civilian_people[j]), fmt(h.forwarded_in_people[j]), fmt(h.own_catchment_people[j])]) {
          if (!readouts.includes(value)) throw new Error(`Readout ${value} missing for ${option.value}`);
        }
        const note = await page.locator('#settled-work-note').innerText();
        if (!note.includes('Market forwarding') || !note.includes('not calibrated values')) throw new Error('Scenario note missing');
        const href = await page.locator('#settled-field-grid').getAttribute('href');
        const served = await page.request.get(BASE + href);
        if (!served.ok() || !fs.readFileSync(path.join(ROOT, 'atlases/earth_fit', href)).equals(await served.body())) throw new Error('Audit grid not served exactly');
        if (layer === 'reach_towns' && option.value === 'market6_50') {
          const [download] = await Promise.all([page.waitForEvent('download'), page.click('#settled-download')]);
          const rows = fs.readFileSync(await download.path(), 'utf8').trim().split('\r\n');
          if (rows.length !== 1 + 12 * model.cases.length) throw new Error('Unexpected CSV rows: ' + rows.length);
          await page.locator('#viewport').screenshot({ path: path.join(OUT, `${mode}_market6_50_towns.png`) });
        }
        maps += 1;
      }
    }
    // Other families still load after the new family was used, and the default is unchanged.
    await page.click('#layer-reach_towns'); await page.selectOption('#variant', 'feedback600_75');
    await page.waitForFunction(() => document.querySelectorAll('#settled-readouts .readout').length === 8, null, { timeout: 90000 });
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.goto(BASE + '#layer=reach_towns&climate=' + mode, { waitUntil: 'domcontentloaded' }); await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelectorAll('#settled-readouts .readout').length === 11, null, { timeout: 90000 });
    if (await page.locator('#variant').inputValue() !== initial) throw new Error('Default scenario changed');
    // The previous default is one selection away, and reach keeps its Earth-tested default.
    await page.locator('#experimental').uncheck();            // the normal view; with the switch on, scenarios carry across layers by design
    await page.click('#layer-reach_defacto');
    await page.waitForFunction(() => document.querySelector('#variant')?.value === 'v21_joint365', null, { timeout: 90000 });
    await page.click('#layer-reach_towns');
    await page.waitForFunction((value) => document.querySelector('#variant')?.value === value, initial, { timeout: 90000 });
    await page.selectOption('#variant', 'joint365');
    await page.waitForFunction(() => document.querySelectorAll('#settled-readouts .readout').length === 6, null, { timeout: 90000 });
    // Phone widths with a market option selected, as for the other optional families.
    await page.locator('#experimental').check(); await page.selectOption('#variant', 'market6_50');
    await page.waitForFunction(() => document.querySelectorAll('#settled-readouts .readout').length === 11, null, { timeout: 90000 });
    for (const width of [344, 390]) {
      await page.setViewportSize({ width, height: 844 });
      if (!await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)) throw new Error('Horizontal overflow at ' + width);
    }
    if (errors.length) throw new Error(errors.join('; '));
    checks.push({ mode, maps, default_variant: initial }); await page.close();
  }
  // A missing optional manifest must leave the original scenarios available.
  const page = await browser.newPage(); await page.route('**/data/settlement_market.json*', (route) => route.abort());
  await page.goto(BASE + '#layer=reach_towns&climate=corrected', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelectorAll('#settled-readouts .readout').length === 6, null, { timeout: 90000 });
  if (await page.locator('#variant').inputValue() !== 'joint365') throw new Error('Missing manifest did not fall back to the previous default');
  await page.locator('#experimental').check();
  if (await page.locator('#variant option[value^="market"]').count()) throw new Error('Market options listed without their manifest');
  if (!await page.locator('#variant option[value="feedback600_75"]').count()) throw new Error('Other families lost when the market manifest is missing');
  await browser.close();
  fs.writeFileSync(path.join(OUT, 'review.json'), JSON.stringify({ status: 'passed', cases: checks, readouts_per_market_case: 11,
    audit_grids_byte_exact: true, csv_rows_checked: true, other_families_still_load: true, settlements_default: manifest.default_settlements, previous_default_selectable: true,
    reach_default: 'v21_joint365', missing_manifest_falls_back_to: 'joint365',
    mobile_widths: [344, 390], missing_manifest_isolated: true,
    note: 'The default, non-experimental Settlements view scrolls sideways at 344 and 390 px (page width 400 and 423 px); measured independently of this family and not changed here.' }, null, 2) + '\n');
  console.log('Market hierarchy atlas check passed', JSON.stringify(checks));
})().catch((e) => { console.error(e); process.exit(1); });
