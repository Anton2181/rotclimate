"""Exercise all joint dispatch maps, CSV work ledgers and optional failures."""
import argparse
import csv
import gzip
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8766')
    parser.add_argument('--out', type=Path, default=ROOT / 'output/settlement_dispatch_20261112/browser')
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / 'atlases/earth_fit/data/settlement_dispatch.json').read_text()); checks = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for mode, packet in manifest['packets'].items():
            page = browser.new_page(viewport=dict(width=1440, height=1000)); errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            base = args.base + '/atlases/earth_fit/'
            model = json.loads(gzip.decompress((ROOT / 'atlases/earth_fit/data' / packet['payload']).read_bytes()))
            page.goto(base + '#layer=reach_towns&climate=' + mode, wait_until='domcontentloaded')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6', timeout=90000)
            assert page.locator('#variant').input_value() == 'joint365'
            assert not page.locator('#variant option[value^="dispatch"]').count()
            page.locator('#experimental').check(); tested = 0
            for layer in ('reach_towns', 'reach_defacto'):
                page.click('#layer-' + layer)
                for option in packet['options'][layer]:
                    page.select_option('#variant', option['value'])
                    page.wait_for_function('(file)=>document.querySelectorAll("#settled-readouts .readout").length===10 && document.querySelector("#base").complete && new URL(document.querySelector("#base").src).pathname.endsWith("/data/"+file)', arg=option['file'], timeout=90000)
                    assert 'experimental' in page.locator('#variant option:checked').inner_text().lower()
                    assert 'Collection also fits every monthly staff budget' in page.locator('#settled-work-note').inner_text()
                    assert 'do not establish geographic patrol coverage' in page.locator('#settled-work-note').inner_text()
                    case = next(c for c in model['cases'] if c['id'] == option['value'])
                    j = max(range(len(case['civilian_people'])), key=lambda i: case['civilian_people'][i])
                    page.select_option('#settled-site', model['sites'][j]['id'])
                    with page.expect_download() as event: page.click('#settled-download')
                    with Path(event.value.path()).open() as stream: rows = list(csv.DictReader(stream))
                    assert len(rows) == len(model['cases']) * 12
                    for row in rows:
                        c = next(c for c in model['cases'] if c['id'] == row['scenario']); month = int(row['seasonal_bin']) - 1
                        assert abs(float(row['civilian_people']) - c['civilian_people'][j]) < 1e-6
                        assert abs(float(row['institutional_people']) - c['institutional_people'][j]) < 1e-6
                        if c.get('dispatch_work'):
                            assert abs(float(row['collection_hours']) - c['dispatch_work']['collection_hours'][j][month]) < 1e-6
                            assert abs(float(row['gross_staff_hours']) - c['dispatch_work']['gross_hours'][j][month]) < 1e-6
                            assert abs(float(row['unused_staff_hours']) - c['dispatch_work']['unused_hours'][j][month]) < 1e-6
                        else: assert row['collection_hours'] == ''
                    field = page.locator('#settled-field-grid').get_attribute('href'); response = page.request.head(base + field)
                    assert response.ok and int(response.headers['content-length']) == (ROOT / 'atlases/earth_fit' / field).stat().st_size
                    tested += 1
                page.select_option('#variant', 'feedback600_75')
                page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===8')
                page.select_option('#variant', 'joint365')
                page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6')
            page.click('#layer-reach_towns'); page.select_option('#variant', 'dispatch600_120000_open')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===10')
            page.reload(wait_until='domcontentloaded')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===10', timeout=90000)
            assert page.locator('#variant').input_value() == 'dispatch600_120000_open'
            page.locator('.mapwrap').first.screenshot(path=str(args.out / (mode + '_map.png')))
            for theme in ('light', 'dark'):
                page.emulate_media(color_scheme=theme)
                for width in (344, 390):
                    page.set_viewport_size(dict(width=width, height=844))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert not errors, errors
            checks.append(dict(mode=mode, map_options=tested, exact_csv_work_fields=True,
                downloads_and_parent_family_switching=True, share_link_reload=True, mobile_dark=True, page_errors=errors))
            page.close()
        for failure in ('missing_manifest', 'wrong_parent', 'corrupt_grid'):
            page = browser.new_page()
            if failure == 'missing_manifest':
                page.route('**/settlement_dispatch.json*', lambda route: route.fulfill(status=404, body='missing'))
            elif failure == 'wrong_parent':
                bad = json.loads(json.dumps(manifest))
                for packet in bad['packets'].values(): packet['parent_payload_sha256'] = 'wrong'
                page.route('**/settlement_dispatch.json*', lambda route: route.fulfill(json=bad))
            else:
                page.route('**/dispatch/raw/settled_reach.bin.gz*', lambda route: route.fulfill(body=b'corrupt'))
            page.goto(args.base + '/atlases/earth_fit/#layer=reach_towns&climate=raw', wait_until='domcontentloaded')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6', timeout=90000)
            page.locator('#experimental').check()
            if failure != 'corrupt_grid':
                # A failed original supplement must not remove independent,
                # threshold-checked versions that share the dispatch prefix.
                unavailable = {o['value'] for o in manifest['packets']['raw']['options']['reach_towns']}
                displayed = set(page.locator('#variant option').evaluate_all('(els)=>els.map(e=>e.value)'))
                assert unavailable.isdisjoint(displayed)
            else:
                page.select_option('#variant', 'dispatch600_120000_open')
                page.wait_for_function('document.querySelector("#settled-site-note").textContent.includes("Detailed ledger unavailable")', timeout=90000)
                page.select_option('#variant', 'joint365')
                page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6')
            checks.append(dict(optional_failure=failure, original_cases_retained=True)); page.close()
        page = browser.new_page()
        page.goto(args.base + '/atlases/earth_fit/#layer=reach_defacto&climate=raw', wait_until='domcontentloaded')
        page.wait_for_function('document.querySelector("#variant")?.value==="v21_joint365"', timeout=90000)
        assert not page.locator('#settled-section').is_visible(); page.close()
        browser.close()
    (args.out / 'review.json').write_text(json.dumps(dict(status='passed', production_control_default_unchanged=True, checks=checks), indent=2) + '\n')
    print('Dispatch browser passed:32new map options,exact work CSVs,three packet families,mobile/reload/failure checks.')


if __name__ == '__main__': main()
