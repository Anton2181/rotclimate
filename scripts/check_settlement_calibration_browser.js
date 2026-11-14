// Browser check of atlases/earth_evidence/settlement_calibration/ (serve repo root on 8766).
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const base = 'http://127.0.0.1:8766/atlases/earth_evidence/settlement_calibration/';
  for (const [w, scheme] of [[390, 'light'], [390, 'dark'], [1280, 'light']]) {
    const p = await b.newPage({ viewport: { width: w, height: 900 }, colorScheme: scheme }); const bad = [];
    p.on('response', r => { if (r.status() >= 400) bad.push(r.url()); }); p.on('pageerror', e => bad.push(String(e)));
    await p.goto(base, { waitUntil: 'networkidle' });
    const s = await p.evaluate(() => ({ over: document.documentElement.scrollWidth - innerWidth, rows: document.querySelectorAll('tbody tr').length,
      imgs: [...document.images].every(i => i.complete && i.naturalWidth > 0), bg: getComputedStyle(document.body).backgroundColor }));
    const links = await p.$$eval('a[href]', a => a.map(x => x.href).filter(h => !h.endsWith('.md')));
    for (const h of links) { const r = await p.request.get(h); if (r.status() >= 400) bad.push(h); }
    if (s.over > 0 || s.rows !== 8 || !s.imgs || bad.length) { console.error('FAIL', w, scheme, s, bad); process.exit(1); }
    if (w === 390) await p.screenshot({ path: `/tmp/claude-0/-home-user-rotclimate/102a023a-f7ac-5ee0-b069-1ee48d6f8e91/scratchpad/sc_${scheme}.png`, fullPage: false });
    console.log('ok', w, scheme, s.bg, links.length, 'links'); await p.close();
  }
  const p = await b.newPage(); await p.goto('http://127.0.0.1:8766/atlases/earth_evidence/');
  if (!(await p.$('a[href="settlement_calibration/"]'))) { console.error('FAIL evidence index link'); process.exit(1); }
  await p.goto('http://127.0.0.1:8766/atlases/');
  if (!(await p.$('a[href="earth_evidence/settlement_calibration/"]'))) { console.error('FAIL hub link'); process.exit(1); }
  console.log('ok index and hub links'); await b.close();
})();
