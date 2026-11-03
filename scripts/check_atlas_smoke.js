// Browser smoke check of served atlas pages, local or packaged for publishing.
//
//   python3 -m http.server 8765 --bind 127.0.0.1 &   (from the repository root)
//   node scripts/check_atlas_smoke.js http://127.0.0.1:8765/atlases/earth_fit/ [more URLs] > report.json
//
// Opens each page in Chromium, waits for the climate card, then visits every
// map topic and checks the panels that load their own data packets: Foraging
// (FORGE), Population, Land and people, the directed-trade views and, where the
// atlas has them, the surroundings-sensitivity layers, the initialization
// check under Fit checks and, where the atlas has the Earth-corrected climate, that it opens on it
// (images from data/corrected/) and that the raw simulation loads with #climate=raw. Any page error or failed data load fails the page.
const { chromium } = require('playwright');

async function checkPage(browser, url) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const errors = [], failed = [];
  page.on('pageerror', e => errors.push(String(e)));
  // atlas.bin first, atlas.wasm (published copies) second: a missing atlas.bin is the page's own fallback probe
  const loaded = [];
  page.on('response', r => { if (r.status() < 400) loaded.push(r.url()); });
  page.on('response', r => { if (r.status() >= 400 && !/r19_|favicon|data\/atlas\.bin/.test(r.url())) failed.push(`${r.status()} ${r.url()}`); });
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelector('#station-h')?.textContent !== '—', null, { timeout: 90000 });
  const meta = await page.evaluate(async () => (await fetch('data/atlas.json')).json());
  const topics = await page.$$eval('#map-topic option', o => o.map(x => x.value));
  const result = { url, topics, layers: meta.layers.length, checks: {} };
  const showLayer = async id => {
    const topic = await page.getAttribute('#layer-' + id, 'data-topic');
    await page.selectOption('#map-topic', topic);
    await page.click('#layer-' + id);
  };
  if (meta.foraging) {
    await showLayer('forage_density');
    await page.waitForFunction(() => document.querySelector('#foraging-totals')?.children.length > 0, null, { timeout: 60000 });
    result.checks.foraging = {
      section_visible: await page.isVisible('#foraging-section'),
      totals: await page.$eval('#foraging-totals', e => e.innerText.replace(/\s+/g, ' ').trim()),
      status: await page.$eval('#foraging-status', e => e.textContent.trim().slice(0, 120)),
    };
  }
  if (meta.population) {
    await showLayer('pop_density');
    await page.waitForFunction(() => /supplied/.test(document.querySelector('#population-message')?.textContent || ''), null, { timeout: 60000 });
    result.checks.population = await page.$eval('#population-message', e => e.textContent.trim());
  }
  if (meta.harvest) {
    await showLayer('land_density');
    result.checks.harvest = await page.$eval('#harvest-totals', e => e.innerText.replace(/\s+/g, ' ').trim().slice(0, 160));
  }
  const trade = meta.layers.find(L => L.id === 'reach_trade');
  if (trade) {
    await showLayer('reach_trade');
    result.checks.trade_views = await page.$$eval('#variant option', o => o.length);
  }
  const sensitivity = meta.layers.filter(L => L.id.startsWith('surroundings_')).map(L => L.id);
  if (sensitivity.length) {
    await showLayer(sensitivity[0]);
    result.checks.sensitivity = { layers: sensitivity, download_link: await page.locator('#legend a[download]').count() };
  }
  if (meta.corrected_climate) {
    // the page opens on the Earth-corrected climate: images, station packet and food packets from data/corrected/
    const ids = ['koppen', 't_annual', 'precip', 't_month', 'land_density', 'pop_density', 'reach_control', 'forage_density']
      .filter(id => meta.corrected_climate.layers.some(L => L.id === id));
    const shown = [];
    for (const id of ids) {
      await showLayer(id);
      // population layers are drawn in the page from the population packet: there the
      // corrected packet must have loaded and the drawn image must be showing
      const dynamic = meta.corrected_climate.layers.some(L => L.id === id && L.population_dynamic);
      const ok = await page.waitForFunction(dyn => { const i = document.querySelector('#base');
        return (i.src.includes('/corrected/') || (dyn && i.src.startsWith('data:'))) && i.complete && i.naturalWidth > 0; },
        dynamic, { timeout: 20000 }).then(() => true, () => false)
        && (!dynamic || loaded.some(u => /\/data\/corrected\/population\.(bin|wasm)/.test(u)));
      shown.push({ id, corrected_image: ok });
    }
    const changes = meta.layers.filter(L => L.id.startsWith('correction_')).map(L => ({ id: L.id, group: L.group }));
    result.checks.corrected_climate = { control_visible: await page.isVisible('#climate-mode-control'),
      choice: await page.$eval('#climate-mode', e => e.value), layers: shown, change_maps: changes,
      no_corrected_topic: !topics.includes('Corrected'),
      status: await page.$eval('#atlas-data-status', e => e.textContent.trim().slice(-40)) };
  }
  if (meta.initialization_check) {
    await showLayer('zones');
    result.checks.initialization_link = await page.locator('#legend a[data-initialization-check]').count();
  }
  if (meta.corrected_climate) {
    // the raw simulation, one switch away (#climate=raw reloads every packet)
    await page.goto('about:blank');               // a hash-only change would not reload the page
    await page.goto(url.split('#')[0] + '#climate=raw&layer=koppen', { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelector('#station-h')?.textContent !== '—', null, { timeout: 90000 });
    await page.waitForFunction(() => { const i = document.querySelector('#base'); return i.complete && i.naturalWidth > 0; }, null, { timeout: 30000 });
    let forage = '';
    if (meta.foraging) {
      await showLayer('forage_density');
      await page.waitForFunction(() => document.querySelector('#foraging-totals')?.children.length > 0, null, { timeout: 60000 });
      forage = await page.$eval('#foraging-totals', e => e.innerText.replace(/\s+/g, ' ').trim());
    }
    result.checks.raw_climate = { choice: await page.$eval('#climate-mode', e => e.value), foraging: forage,
      image: await page.$eval('#base', e => (e.src.split('/data/')[1] || e.src).slice(0, 120)), hash: await page.evaluate(() => location.hash) };
  }
  await page.waitForTimeout(1500);
  result.errors = errors; result.failed_requests = failed;
  result.passed = !errors.length && !failed.length && (!meta.foraging || /people/.test(result.checks.foraging.totals))
    && (!result.checks.corrected_climate || (result.checks.corrected_climate.choice === 'corrected' && result.checks.corrected_climate.control_visible
        && result.checks.corrected_climate.no_corrected_topic && result.checks.corrected_climate.layers.every(L => L.corrected_image)
        && (!meta.earth_correction || result.checks.corrected_climate.change_maps.filter(L => L.group === 'Fit checks').length === 3)))
    && (!result.checks.raw_climate || (result.checks.raw_climate.choice === 'raw' && !/corrected\//.test(result.checks.raw_climate.image)
        && /climate=raw/.test(result.checks.raw_climate.hash) && (!meta.foraging || /people/.test(result.checks.raw_climate.foraging))));
  await page.close();
  return result;
}

(async () => {
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  const results = [];
  for (const url of process.argv.slice(2)) {
    try { results.push(await checkPage(browser, url)); }
    catch (error) { results.push({ url, passed: false, errors: [String(error)] }); }
  }
  await browser.close();
  console.log(JSON.stringify(results, null, 1));
  process.exit(results.every(r => r.passed) ? 0 : 1);
})();
