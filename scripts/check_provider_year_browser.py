"""Exercise eight provider-year maps,source ledgers,point masks and six families."""
import csv
import gzip
import io
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'atlases/earth_fit/data'
OUT = ROOT / 'output/network_visit_year_complete_20261112/browser/maps'
BASE = 'http://127.0.0.1:8766/atlases/earth_fit/'


def check_provider_csv(page, model, j):
    page.select_option('#settled-site', model['sites'][j]['id'])
    with page.expect_download() as event: page.click('#settled-download')
    rows = list(csv.DictReader(io.StringIO(Path(event.value.path()).read_text())))
    assert len(rows) == len(model['cases']) * 12
    for row in rows:
        c = next(c for c in model['cases'] if c['id'] == row['scenario']); y = c.get('year_schedule'); month = int(row['seasonal_bin']) - 1
        if not y:
            assert row['provider_year_policy'] == row['selected_worker_hours'] == ''; continue
        assert row['provider_year_policy'] == ('joint_duration_first' if y['policy'][j] else 'collection_first')
        assert row['all_twelve_mandatory_bins_complete'] == str(y['mandatory_complete'][j]).lower()
        for name, field in [('selected_worker_hours', 'work_hours'), ('selected_max_worker_duty_hours', 'max_worker_hours'), ('selected_max_calendar_end', 'max_calendar_end')]:
            assert float(row[name]) == y[field][j][month]
        for name, field in [('completed_point_visits', 'completed_by_provider'), ('reserved_patrol_hours', 'reserved_hours'), ('visit_hours_used', 'used_hours'), ('unused_patrol_hours', 'unused_hours')]:
            assert float(row[name]) == c['point_visits'][field][j][month]
        assert float(row['unused_staff_hours']) == c['dispatch_work']['unused_hours'][j][month]
        assert float(row['selected_max_worker_duty_hours']) <= 50 and float(row['selected_max_calendar_end']) <= 7 * 365 / 12
        if not y['mandatory_complete'][j]: assert float(row['completed_point_visits']) == 0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((DATA / 'network_visit_year_complete.json').read_text()); checks = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for mode, packet in manifest['packets'].items():
            model = json.loads(gzip.decompress((DATA / packet['payload']).read_bytes()))
            page = browser.new_page(viewport=dict(width=1440, height=1100)); errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(BASE + '#layer=reach_towns&climate=' + mode, wait_until='domcontentloaded')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6', timeout=90000)
            assert not page.locator('#variant option[value^="yearvisits"]').count()
            page.locator('#experimental').check(); page.click('#layer-reach_defacto')
            for option in packet['options']['reach_defacto']:
                page.select_option('#variant', option['value'])
                page.wait_for_function('(file)=>document.querySelectorAll("#settled-readouts .readout").length===14&&document.querySelector("#base").complete&&new URL(document.querySelector("#base").src).pathname.endsWith("/data/"+file)', arg=option['file'], timeout=90000)
                c = next(c for c in model['cases'] if c['id'] == option['value']); y = c['year_schedule']
                assert 'experimental' in page.locator('#variant option:checked').inner_text().lower()
                assert f'{c["point_visits"]["completed"]:,}' in page.locator('#settled-global').inner_text()
                assert 'necessary provider-year schedule gate' in page.locator('#settled-global').inner_text()
                assert 'No individual job successes are merged' in page.locator('#settled-work-note').inner_text()
                candidates = [j for j in range(len(model['sites'])) if y['mandatory_complete'][j] and y['policy'][j] == 1]
                assert candidates
                j = max(candidates, key=lambda j: sum(c['point_visits']['completed_by_provider'][j])); check_provider_csv(page, model, j)
                failed = next(j for j in range(len(model['sites'])) if not y['mandatory_complete'][j] and c['institutional_people'][j] > 0)
                check_provider_csv(page, model, failed)
                assert 'Incomplete / unassigned' in page.locator('#settled-readouts').inner_text()
                link = page.locator('#settled-point-grid'); assert link.is_visible()
                response = page.request.get(BASE + link.get_attribute('href')); assert response.ok
                data = response.body(); assert data == (ROOT / 'atlases/earth_fit' / link.get_attribute('href')).read_bytes()
                points = list(csv.DictReader(io.StringIO(gzip.decompress(data).decode())))
                assert sum(int(p['qualified_bins']) for p in points) == c['point_visits']['completed']
                for p in points:
                    masks = [int(p[name]) for name in ('qualified_bin_mask', 'calendar_unqualified_bin_mask', 'route_unreachable_bin_mask', 'provider_work_unavailable_bin_mask', 'capacity_unmet_bin_mask')]
                    assert sum(masks) == 4095 and int(p['qualified_bins']) == masks[0].bit_count()
                    assert int(p['baseline_twelve_bin_mask']) & ~masks[0] == 0 and masks[0] & ~int(p['original_funded_bin_mask']) == 0
                assert page.request.head(BASE + page.locator('#settled-field-grid').get_attribute('href')).ok
                if option['value'] == 'yearvisits600_crew1':
                    point = next(p for p in points if int(p['qualified_bins']) > 0)
                    page.locator('#viewport').scroll_into_view_if_needed(); rect = page.locator('#viewport').bounding_box()
                    xx = rect['x'] + (int(point['target_column']) + .5) / packet['shape'][1] * rect['width']
                    yy = rect['y'] + (int(point['target_row']) + .5) / packet['shape'][0] * rect['height']
                    page.mouse.click(xx, yy); page.mouse.click(xx, yy)
                    actor = next(i for i, a in enumerate(model['actors']) if a['name'] == point['actor'])
                    assert page.locator('#settled-cell tr').nth(actor).locator('td').last.inner_text() == point['qualified_bins'] + ' / 12'
                checks.append(dict(climate=mode, scenario=option['value'], complete_and_incomplete_provider_csv=True, point_download_and_partitions=True, baseline_task_inclusion=True))
            page.reload(wait_until='domcontentloaded'); page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===14', timeout=90000)
            for theme in ('light', 'dark'):
                page.emulate_media(color_scheme=theme)
                for width in (344, 390):
                    page.set_viewport_size(dict(width=width, height=844)); assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            for value, readouts in [('visits600_crew1', 12), ('dispatchv2600_120000_open', 10), ('dispatch600_120000_open', 10), ('feedback600_75', 8), ('joint365', 6)]:
                page.select_option('#variant', value); page.wait_for_function('(n)=>document.querySelectorAll("#settled-readouts .readout").length===n', arg=readouts)
                assert 'one chosen calendar' not in page.locator('#settled-readouts').inner_text()
            assert not errors, errors; page.close()
        for failure in ('missing_manifest', 'wrong_parent', 'corrupt_binary'):
            page = browser.new_page()
            if failure == 'missing_manifest': page.route('**/network_visit_year_complete.json*', lambda route: route.fulfill(status=404, body='missing'))
            elif failure == 'wrong_parent':
                bad = json.loads(json.dumps(manifest))
                for p in bad['packets'].values(): p['parent_payload_sha256'] = 'wrong'
                page.route('**/network_visit_year_complete.json*', lambda route: route.fulfill(json=bad))
            else: page.route('**/year_complete/raw/settled_reach.bin.gz*', lambda route: route.fulfill(body=b'corrupt'))
            page.goto(BASE + '#layer=reach_towns&climate=raw', wait_until='domcontentloaded')
            page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===6', timeout=90000)
            page.locator('#experimental').check(); page.click('#layer-reach_defacto')
            if failure != 'corrupt_binary': assert not page.locator('#variant option[value^="yearvisits"]').count()
            else:
                page.select_option('#variant', 'yearvisits600_crew1')
                page.wait_for_function('document.querySelector("#settled-site-note").textContent.includes("Detailed ledger unavailable")', timeout=90000)
                assert page.locator('#settled-download').is_disabled() and not page.locator('#settled-point-grid').is_visible()
                page.select_option('#variant', 'visits600_crew1'); page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===12')
            checks.append(dict(optional_failure=failure, earlier_families_retained=True)); page.close()
        page = browser.new_page(); page.goto(BASE + '#layer=reach_defacto&climate=raw', wait_until='domcontentloaded')
        page.wait_for_function('document.querySelector("#variant")?.value==="v21_joint365"', timeout=90000)
        assert not page.locator('#settled-section').is_visible(); browser.close()
    (OUT / 'review.json').write_text(json.dumps(dict(status='passed', maps=8, exact_provider_and_point_downloads=True,
        qualified_pixel_selection=True, six_packet_families=True, mobile_themes_reload=True, defaults_unchanged=True, checks=checks), indent=2) + '\n')
    print('Provider-year browser passed:8maps,complete/incomplete provider CSVs,point partitions,six families,mobile/reload/failures.')


if __name__ == '__main__': main()
