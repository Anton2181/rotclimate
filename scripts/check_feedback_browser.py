"""Exercise optional coupled maps, SAME ledgers, family switching and failures."""
import argparse
import csv
import gzip
import json
from pathlib import Path
from urllib.parse import urlsplit, unquote
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--base', default='http://127.0.0.1:8766')
    p.add_argument('--out', type=Path, required=True); a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / 'atlases/earth_fit/data/settlement_feedback.json').read_text()); checks = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for mode, packet in manifest['packets'].items():
            page = browser.new_page(viewport=dict(width=1440, height=1000)); errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            base = a.base + '/atlases/earth_fit/'; url = base + '#layer=reach_towns&variant=joint365&climate=' + mode
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6', timeout=90000)
            assert page.locator('#variant').input_value() == 'joint365'
            page.locator('#experimental').check()
            model = json.loads(gzip.decompress((ROOT / 'atlases/earth_fit/data' / packet['payload']).read_bytes()))
            tested = 0
            for layer in ('reach_towns', 'reach_defacto'):
                page.click('#layer-' + layer)
                for option in packet['options'][layer]:
                    page.select_option('#variant', option['value'])
                    assert 'experimental' in page.locator('#variant option:checked').inner_text().lower()
                    page.wait_for_function('(file)=>document.querySelectorAll("#settled-readouts .readout").length===8 && document.querySelector("#base").complete && new URL(document.querySelector("#base").src).pathname.endsWith("/data/"+file)', arg=option['file'], timeout=90000)
                    assert 'Moving people changes BOTH workers and rural meals' in page.locator('#settled-work-note').inner_text()
                    assert page.locator('#settled-months tr').count() == 12
                    assert page.locator('#settled-field-grid').is_visible()
                    c = next(c for c in model['cases'] if c['id'] == option['value'])
                    j = max(range(len(c['civilian_people'])), key=lambda j: c['civilian_people'][j])
                    page.select_option('#settled-site', model['sites'][j]['id'])
                    with page.expect_download() as event:page.click('#settled-download')
                    with Path(event.value.path()).open() as f:rows = list(csv.DictReader(f))
                    assert len(rows) == len(model['cases']) * 12
                    for row in rows:
                        cc = next(c for c in model['cases'] if c['id'] == row['scenario'])
                        assert abs(float(row['civilian_people']) - cc['civilian_people'][j]) < 1e-6
                        assert abs(float(row['institutional_people']) - cc['institutional_people'][j]) < 1e-6
                    target = page.locator('#settled-field-grid').get_attribute('href')
                    reply = page.request.head(base + target)
                    assert reply.ok and int(reply.headers['content-length']) == (ROOT / 'atlases/earth_fit' / target).stat().st_size
                    tested += 1
                page.select_option('#variant', 'joint365')
                page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6', timeout=90000)
                assert not page.locator('#settled-work-note').is_visible()
            option = packet['options']['reach_towns'][1]; page.click('#layer-reach_towns'); page.select_option('#variant', option['value'])
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===8')
            c = next(c for c in model['cases'] if c['id'] == option['value'])
            unsupported = next(j for j, supported in enumerate(c['source_supported']) if not supported)
            page.select_option('#settled-site', model['sites'][unsupported]['id'])
            assert 'Unmet rural meals' in page.locator('#settled-readouts').inner_text()
            saved = page.url; page.reload(wait_until='domcontentloaded')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===8', timeout=90000)
            assert page.locator('#variant').input_value() == option['value']
            assert page.locator('#settled-site').input_value() == model['sites'][unsupported]['id']
            page.locator('.mapwrap').first.screenshot(path=str(a.out / (mode + '_feedback.png')))
            for theme in ('light', 'dark'):
                page.emulate_media(color_scheme=theme)
                for width in (344, 390):
                    page.set_viewport_size(dict(width=width, height=844))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert not errors, errors
            checks.append(dict(mode=mode, map_options_checked=tested, csv_and_cell_downloads=True,
                family_switching=True, source_deficit_visible=True, share_link_reload=True, mobile_dark=True, page_errors=errors))
            page.close()
        # Preserve normal defaults and fail only the optional supplement.
        for failure in ('missing_manifest', 'wrong_parent', 'corrupt_grid'):
            page = browser.new_page()
            if failure == 'missing_manifest':
                page.route('**/settlement_feedback.json*', lambda r:r.fulfill(status=404, body='missing'))
            elif failure == 'wrong_parent':
                bad = json.loads(json.dumps(manifest))
                for value in bad['packets'].values():value['parent_payload_sha256'] = 'wrong'
                page.route('**/settlement_feedback.json*', lambda r:r.fulfill(json=bad))
            else:
                page.route('**/feedback/raw/settled_reach.bin.gz*', lambda r:r.fulfill(body=b'corrupt'))
            page.goto(a.base + '/atlases/earth_fit/#layer=reach_towns&variant=joint365&climate=raw', wait_until='domcontentloaded')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6', timeout=90000)
            page.locator('#experimental').check()
            if failure != 'corrupt_grid':
                assert not any(o.startswith('feedback') for o in page.locator('#variant option').evaluate_all('(els)=>els.map(e=>e.value)'))
            else:
                page.select_option('#variant', 'feedback600_75')
                page.wait_for_function('document.querySelector("#settled-site-note").textContent.includes("Detailed ledger unavailable")', timeout=90000)
                page.select_option('#variant', 'joint365')
                page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6')
            checks.append(dict(optional_failure=failure, original_cases_retained=True)); page.close()
        page = browser.new_page(); page.goto(a.base + '/atlases/earth_fit/#layer=reach_defacto&climate=raw', wait_until='domcontentloaded')
        page.wait_for_function('document.querySelector("#variant")?.value==="v21_joint365"', timeout=90000)
        assert not page.locator('#settled-section').is_visible(); checks.append(dict(production_control_default_unchanged=True)); page.close()
        page = browser.new_page(); page.goto(a.base + '/atlases/earth_evidence/', wait_until='domcontentloaded')
        detail = page.locator('#settlement-feedback'); detail.locator('summary').click()
        assert detail.locator('tbody tr').count() == 8 and detail.locator('img').count() == 2
        assert 'not calibrated city sizes' in detail.inner_text()
        for link in detail.locator('a').all():
            url = link.evaluate('(el)=>el.href'); response = page.request.get(url); assert response.ok, url
            path = ROOT / unquote(urlsplit(url).path).lstrip('/')
            if path.is_dir():path /= 'index.html'
            assert response.body() == path.read_bytes(), str(path)
        checks.append(dict(evidence_rows=8, evidence_links_byte_exact=True, empirical_limits_explicit=True));page.close()
        browser.close()
    (a.out / 'review.json').write_text(json.dumps(dict(status='passed', checks=checks), indent=2) + '\n')
    print('Feedback browser passed: all16 map options, exact CSV/cell downloads, family switches, reload/mobile and failures.')


if __name__ == '__main__':main()
