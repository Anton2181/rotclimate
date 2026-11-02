// Exercise a current launch while a browser has an old, cacheable hub open.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');

async function main() {
  const out = path.resolve(process.argv[2] || 'output/launcher_refresh_20261102');
  fs.mkdirSync(out, { recursive: true });
  const stale = http.createServer((req, res) => {
    res.writeHead(200, {'Content-Type': 'text/html', 'Cache-Control': 'public, max-age=31536000'});
    res.end('<!doctype html><h1>Old atlas hub</h1><p>22 OCTOBER 2026</p>');
  });
  await new Promise(resolve => stale.listen(0, '127.0.0.1', resolve));
  const oldURL = `http://127.0.0.1:${stale.address().port}/atlases/`;
  const python = fs.existsSync('.venv/bin/python') ? '.venv/bin/python' : 'python3';
  const server = spawn(python, ['scripts/serve_atlases.py', '--no-browser']);
  let log = '', browser;
  const ready = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Launcher did not print a fresh URL')), 20000);
    server.stdout.on('data', bytes => {
      log += bytes.toString();
      const match = log.match(/Open (http:\/\/[^\s]+)/);
      if (match) { clearTimeout(timer); resolve(match[1]); }
    });
    server.stderr.on('data', bytes => { log += bytes.toString(); });
    server.on('exit', code => { clearTimeout(timer); reject(new Error('Launcher exited: ' + code + '\n' + log)); });
  });
  try {
    const freshURL = await ready;
    assert.notEqual(new URL(freshURL).origin, new URL(oldURL).origin);
    assert(new URL(freshURL).searchParams.has('launch'));
    assert(new URL(freshURL).searchParams.has('snapshot'));
    browser = await chromium.launch({headless: true, executablePath: '/usr/bin/chromium', args: ['--no-sandbox']});
    const page = await browser.newPage({viewport: {width: 1440, height: 1050}});
    await page.goto(oldURL);
    assert((await page.textContent('body')).includes('22 OCTOBER 2026'));
    const response = await page.goto(freshURL, {waitUntil: 'domcontentloaded'});
    assert.equal(response.headers()['cache-control'], 'no-store');
    const header = await page.textContent('header');
    assert(header.includes('updated') && !header.includes('22 OCTOBER 2026'));
    assert((await page.textContent('body')).includes('Earth r42 physics'));
    const modes = await page.evaluate(async () => {
      const earth = await (await fetch('earth_fit/data/atlas.json')).json();
      const whittaker = await (await fetch('whittaker_fit/data/atlas.json')).json();
      return {earthModes: earth.layers.length, whittakerOutside: whittaker.biomes[0].share};
    });
    assert.equal(modes.earthModes, 70);
    assert(Math.abs(modes.whittakerOutside - .014363342453405828) < 1e-12);
    await page.screenshot({path: path.join(out, 'current_hub.png'), fullPage: false});
    const result = {passed: true, oldURL, freshURL, header: header.trim(), ...modes, launcherOutput: log};
    fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify(result, null, 2));
  } finally {
    if (browser) await browser.close();
    server.kill();
    await new Promise(resolve => stale.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
