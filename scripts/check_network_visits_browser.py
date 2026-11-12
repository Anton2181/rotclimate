"""Exercise optional walking visit maps and their exact task/hour downloads."""
import argparse
import csv
import gzip
import io
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--base', default='http://127.0.0.1:8766')
    parser.add_argument('--out', type=Path, default=ROOT / 'output/network_duty_visits_20261112/browser')
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / 'atlases/earth_fit/data/network_duty_visits.json').read_text()); checks = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for mode, packet in manifest['packets'].items():
            page = browser.new_page(viewport=dict(width=1440, height=1000)); errors = []
            page.on('pageerror', lambda error: errors.append(str(error))); base = args.base + '/atlases/earth_fit/'
            model = json.loads(gzip.decompress((ROOT / 'atlases/earth_fit/data' / packet['payload']).read_bytes()))
            page.goto(base + '#layer=reach_towns&variant=joint365&climate=' + mode, wait_until='domcontentloaded')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6', timeout=90000)
            assert not page.locator('#variant option[value^="visits"]').count()
            page.locator('#experimental').check(); page.click('#layer-reach_defacto')
            for option in packet['options']['reach_defacto']:
                page.select_option('#variant', option['value'])
                page.wait_for_function('(file)=>document.querySelectorAll("#settled-readouts .readout").length===12 && document.querySelector("#base").complete && new URL(document.querySelector("#base").src).pathname.endsWith("/data/"+file)', arg=option['file'], timeout=90000)
                assert 'experimental' in page.locator('#variant option:checked').inner_text().lower()
                case = next(c for c in model['cases'] if c['id'] == option['value']); v = case['point_visits']
                assert f'{v["completed"]:,}' in page.locator('#settled-global').inner_text()
                assert 'whole visits compete' in page.locator('#settled-work-note').inner_text()
                assert 'not held blocks' in page.locator('#settled-work-note').inner_text()
                j = max(range(len(model['sites'])), key=lambda j: sum(v['completed_by_provider'][j]))
                page.select_option('#settled-site', model['sites'][j]['id'])
                with page.expect_download() as event: page.click('#settled-download')
                with Path(event.value.path()).open() as stream: rows = list(csv.DictReader(stream))
                assert len(rows) == 12 * len(model['cases'])
                for row in rows:
                    c = next(c for c in model['cases'] if c['id'] == row['scenario']); v = c.get('point_visits'); month = int(row['seasonal_bin']) - 1
                    if not v: assert row['visit_hours_used'] == ''; continue
                    for field, key in [('completed_point_visits', 'completed_by_provider'), ('reserved_patrol_hours', 'reserved_hours'), ('visit_hours_used', 'used_hours'), ('unused_patrol_hours', 'unused_hours')]:
                        assert float(row[field]) == v[key][j][month]
                    assert float(row['unused_staff_hours']) == c['dispatch_work']['unused_hours'][j][month]
                point_link = page.locator('#settled-point-grid'); assert point_link.is_visible()
                response = page.request.get(base + point_link.get_attribute('href')); assert response.ok
                raw = response.body(); expected = (ROOT / 'atlases/earth_fit' / point_link.get_attribute('href')).read_bytes(); assert raw == expected
                points = list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode())))
                assert sum(int(p['completed_bins']) for p in points) == case['point_visits']['completed']
                for p in points:
                    masks = [int(p[k]) for k in ('served_bin_mask', 'route_unreachable_bin_mask', 'provider_work_unavailable_bin_mask', 'capacity_unmet_bin_mask')]
                    assert sum(masks) == 4095 and int(p['completed_bins']) == masks[0].bit_count()
                if option['value'] == 'visits600_crew1':
                    point = next(p for p in points if int(p['completed_bins']) > 0)
                    page.locator('#viewport').scroll_into_view_if_needed(); rect = page.locator('#viewport').bounding_box()
                    width, height = packet['shape'][1], packet['shape'][0]
                    xx = rect['x'] + (int(point['target_column']) + .5) / width * rect['width']
                    yy = rect['y'] + (int(point['target_row']) + .5) / height * rect['height']
                    page.mouse.click(xx, yy); page.mouse.click(xx, yy)
                    table = page.locator('#settled-cell tr'); assert table.count() == len(model['actors'])
                    i = next(i for i, a in enumerate(model['actors']) if a['name'] == point['actor'])
                    assert table.nth(i).locator('td').last.inner_text() == point['completed_bins'] + ' / 12'
                    node = int(point['target_grid_node'])
                    for i, requested in enumerate(model['point_requested_targets']):
                        if node not in requested: assert table.nth(i).locator('td').last.inner_text() == 'Unrequested / unscored'
                audit = page.request.head(base + page.locator('#settled-field-grid').get_attribute('href')); assert audit.ok
                checks.append(dict(mode=mode, scenario=option['value'], exact_provider_csv=True, exact_point_download=True, point_partitions=True))
            page.reload(wait_until='domcontentloaded'); page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===12', timeout=90000)
            page.locator('.mapwrap').first.screenshot(path=str(args.out / (mode + '_map.png')))
            for theme in ('light', 'dark'):
                page.emulate_media(color_scheme=theme)
                for width in (344, 390):
                    page.set_viewport_size(dict(width=width, height=844)); assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            for value, readouts in [('dispatchv2600_120000_open', 10), ('dispatch600_120000_open', 10), ('feedback600_75', 8), ('joint365', 6)]:
                page.select_option('#variant', value); page.wait_for_function('(n)=>document.querySelectorAll("#settled-readouts .readout").length===n', arg=readouts)
                assert not page.locator('#settled-point-grid').is_visible()
            assert not errors, errors; page.close()
        for failure in ('missing_manifest', 'wrong_parent', 'corrupt_grid'):
            page = browser.new_page()
            if failure == 'missing_manifest': page.route('**/network_duty_visits.json*', lambda route: route.fulfill(status=404, body='missing'))
            elif failure == 'wrong_parent':
                bad = json.loads(json.dumps(manifest))
                for packet in bad['packets'].values(): packet['parent_payload_sha256'] = 'wrong'
                page.route('**/network_duty_visits.json*', lambda route: route.fulfill(json=bad))
            else: page.route('**/network_visits/raw/settled_reach.bin.gz*', lambda route: route.fulfill(body=b'corrupt'))
            page.goto(args.base + '/atlases/earth_fit/#layer=reach_towns&variant=joint365&climate=raw', wait_until='domcontentloaded')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6', timeout=90000)
            page.locator('#experimental').check(); page.click('#layer-reach_defacto')
            if failure != 'corrupt_grid': assert not page.locator('#variant option[value^="visits"]').count()
            else:
                page.select_option('#variant', 'visits600_crew1'); page.wait_for_function('document.querySelector("#settled-site-note").textContent.includes("Detailed ledger unavailable")', timeout=90000)
                page.select_option('#variant', 'joint365'); page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6')
            checks.append(dict(optional_failure=failure, other_families_retained=True)); page.close()
        page = browser.new_page(); page.goto(args.base + '/atlases/earth_fit/#layer=reach_defacto&climate=raw', wait_until='domcontentloaded')
        page.wait_for_function('document.querySelector("#variant")?.value==="v21_joint365"', timeout=90000); assert not page.locator('#settled-section').is_visible()
        browser.close()
    (args.out / 'review.json').write_text(json.dumps(dict(status='passed', eight_maps=True, five_packet_families=True,
        default_unchanged=True, share_reload_mobile_themes=True, checks=checks), indent=2) + '\n')
    print('Eight point-visit maps,exact provider/point downloads,all five families,mobile/themes/reload/failure checks passed.')


if __name__ == '__main__': main()
