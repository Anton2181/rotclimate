"""Exercise all fixed-policy rows,matched worker downloads and evidence fallback."""
import csv
import io
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/network_visit_joint_order_20261112/browser/evidence'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = json.loads((ROOT / 'output/network_visit_joint_order_20261112/results.json').read_text())
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport=dict(width=1440, height=1100)); errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8766/atlases/earth_evidence/', wait_until='networkidle')
        panel = page.locator('#joint-order'); assert panel.get_attribute('open') is None
        panel.locator('summary').focus(); page.keyboard.press('Enter')
        page.wait_for_function('Array.from(document.querySelectorAll("#joint-order img")).every(i=>i.naturalWidth>0)')
        assert panel.locator('img').count() == 3
        rows = panel.locator('tbody tr'); assert rows.count() == 16
        for i, r in enumerate(result['rows']):
            assert rows.nth(i).locator('td').all_inner_texts() == [r['climate'].title(), str(r['hours_worker_year']), str(r['crew']),
                'Collection first' if r['policy'] == 'collection_first' else 'Joint duration first', f'{r["physically_scheduled_visits"]:,}',
                f'{r["bin_qualified_visits"]:,}', f'{r["twelve_bin_gated_visits"]:,}', f'{r["unpacked_collector_trips"]:,}']
        for phrase in ('necessary delivery-scheduling test', 'not complete annual food validation', 'no winning policy', 'remain unscored'):
            assert phrase in panel.inner_text()
        links = 0
        for link in panel.locator('a').all():
            url = link.evaluate('(el)=>el.href'); reply = page.request.get(url); assert reply.ok, url
            path = ROOT / unquote(urlsplit(url).path).lstrip('/'); assert reply.body() == path.read_bytes(); links += 1
        with page.expect_download() as event: panel.locator('a[href$="joint_order_example.csv"]').click()
        records = list(csv.DictReader(io.StringIO(Path(event.value.path()).read_text()))); workers = {}
        assert {r['policy'] for r in records} == {'collection_first', 'joint_duration_first'}
        for r in records:
            start, end = float(r['start_working_hour']), float(r['end_working_hour'])
            assert 0 <= start <= end <= float(r['month_calendar_hours'])
            assert abs(end - start - float(r['duty_hours'])) < 1e-10
            if r['provider_twelve_bin_mandatory_complete'] == 'True': assert r['provider_bin_mandatory_complete'] == 'True'
            workers.setdefault((r['policy'], r['worker_index']), []).append((start, end))
        assert len(workers) == 24
        for intervals in workers.values():
            intervals.sort(); assert all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:]))
            assert sum(end - start for start, end in intervals) <= 50 + 1e-9
        for theme in ('light', 'dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344, 390):
                page.set_viewport_size(dict(width=width, height=844)); assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        for selector in ('#visit-calendar', '#visit-grid', '#spare-visits', '#network-visits', '#dispatch-seeded'):
            assert page.locator(selector).count() == 1
        page.route('**/data/ledger.json', lambda route: route.abort()); page.reload(wait_until='networkidle')
        page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")')
        assert page.locator('#joint-order tbody tr').count() == 16 and not errors, errors
        browser.close()
    (OUT / 'review.json').write_text(json.dumps(dict(status='passed', exact_policy_rows=16, figures=3, local_links_byte_exact=links,
        csv_policy_worker_calendars_checked=24, keyboard_mobile_themes=True, previous_panels_retained=True, inventory_failure_isolated=True, page_errors=errors), indent=2) + '\n')
    print('Joint-order browser passed:16exact rows,3figures,6byte-exact links,24worker-policy calendars,mobile/themes/failure.')


if __name__ == '__main__': main()
