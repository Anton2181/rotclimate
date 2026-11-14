"""Check all displayed daily water cases, filters, downloads and navigation."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/daily_river_fields_20261114/browser'


def main(base):
    OUT.mkdir(parents=True, exist_ok=True)
    target = base + '/atlases/earth_evidence/daily_fields/'
    rows = json.loads((ROOT / 'output/daily_river_fields_20261114/results.json').read_text())['rows']
    labels = {'nile': 'Nile', 'mesopotamia_euphrates_only': 'Mesopotamia · Euphrates only'}
    expected = []
    for r in rows:
        expected.append([
            labels[r['region']], r['crop'], format(r['root_depth_m'], 'g'),
            {'old': '5-bin', 'fractional': '4-bin fractional'}[r['calendar']],
            format(r['bare_background'], 'g'), format(r['pond_capacity_mm'], 'g'),
            format(r['efficiency'], 'g'), 'Capture' if r['capture'] else 'Rain only',
            format(100 * r['root_coverage'], '.1f') + '%' if r['root_coverage'] is not None else 'Unscored',
            format(r['eligible_area_km2'], ',.0f'),
            format(r['adequate_root_area_km2'], ',.0f') if r['adequate_root_area_km2'] is not None else 'Unscored',
            format(r['delivered_m3'] / 1e9, '.3f'), format(r['pond_evap_m3'] / 1e9, '.3f'),
        ])
    checks, errors = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        for width in (344, 390, 1440):
            for theme in ('light', 'dark'):
                page = browser.new_page(viewport=dict(width=width, height=1000), color_scheme=theme)
                page.on('pageerror', lambda e: errors.append(str(e)))
                assert page.goto(target, wait_until='networkidle').status == 200
                assert page.locator('h1').inner_text() == 'River water now reaches finite ponds and daily soil stores'
                assert page.locator('tbody tr').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))') == expected
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                for img in page.locator('img').all():
                    assert img.evaluate('(im)=>im.complete && im.naturalWidth>0')
                page.keyboard.press('Tab')
                assert page.locator('nav a').first.evaluate('(a)=>a===document.activeElement')
                combinations = 0
                for region, crop, calendar in itertools.product(('', *labels), ('', 'barley', 'wheat'), ('', 'old', 'fractional')):
                    for field, value in [('region', region), ('crop', crop), ('calendar', calendar)]:
                        page.locator('#' + field).select_option(value)
                    wanted = [expected[i] for i, r in enumerate(rows) if (not region or r['region'] == region) and (not crop or r['crop'] == crop) and (not calendar or r['calendar'] == calendar)]
                    assert page.locator('#count').inner_text() == f'{len(wanted)} scenarios'
                    assert page.locator('tbody tr:not([hidden])').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))') == wanted
                    combinations += 1
                for field in ('region', 'crop', 'calendar'):
                    page.locator('#' + field).select_option('')
                links = page.locator('a[download]').all()
                assert len(links) == 9
                for a in links:
                    url = urljoin(target, a.get_attribute('href'))
                    response = page.request.get(url)
                    assert response.ok, url
                    assert hashlib.sha256(response.body()).digest() == hashlib.sha256((ROOT / urlsplit(url).path.lstrip('/')).read_bytes()).digest(), url
                with page.expect_download() as download:
                    page.locator('a[href="fields.csv.gz"]').click()
                actual = download.value
                assert actual.suggested_filename == 'fields.csv.gz'
                assert Path(actual.path()).read_bytes() == (ROOT / 'atlases/earth_evidence/daily_fields/fields.csv.gz').read_bytes()
                page.screenshot(path=str(OUT / f'{width}_{theme}.png'), full_page=True)
                checks.append(dict(width=width, theme=theme, numeric_rows=len(rows), filter_combinations=combinations, download_hashes=len(links), actual_csv_download=True, keyboard_focus=True, no_page_overflow=True))
                page.close()
        page = browser.new_page()
        for path, selector in [('/atlases/', 'a[href="earth_evidence/daily_fields/"]'), ('/atlases/earth_evidence/', '#daily-river-fields a')]:
            assert page.goto(base + path, wait_until='networkidle').status == 200
            page.locator(selector).click()
            page.wait_for_url(target)
        page.goto(target)
        for a in page.locator('nav a').all():
            assert page.request.get(urljoin(target, a.get_attribute('href'))).ok
        browser.close()
    assert not errors, errors
    (OUT / 'browser.json').write_text(json.dumps(dict(status='passed', checks=checks, page_errors=errors, hub_and_evidence_navigation=True, return_links=True), indent=2) + '\n')
    print('Passed six viewport/theme cases, all 256 rows, 162 filter combinations, nine downloads and navigation')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8766')
    main(parser.parse_args().base.rstrip('/'))
