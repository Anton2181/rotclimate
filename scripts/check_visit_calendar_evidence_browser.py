"""Check served calendar tables,figures,downloads and worker-interval CSV."""
import csv
import io
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/network_visit_calendar_20261112/browser/evidence'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = json.loads((ROOT / 'output/network_visit_calendar_20261112/results.json').read_text())
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport=dict(width=1440, height=1100)); errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8766/atlases/earth_evidence/', wait_until='networkidle')
        panel = page.locator('#visit-calendar'); assert panel.get_attribute('open') is None
        panel.locator('summary').focus(); page.keyboard.press('Enter')
        page.wait_for_function('Array.from(document.querySelectorAll("#visit-calendar img")).every(i=>i.naturalWidth>0)')
        assert panel.locator('img').count() == 3
        collection_rows = panel.locator('[data-calendar-collection] tbody tr')
        assert collection_rows.count() == 4
        for index, r in enumerate(result['collection_rows']):
            assert collection_rows.nth(index).locator('td').all_inner_texts() == [r['climate'].title(), str(r['hours_worker_year']),
                f'{r["required_trips"]:,}', f'{r["unpacked_trips"]:,}', f'{r["mandatory_failed_provider_bins"]:,} / {r["relevant_provider_bins"]:,}']
        visit_rows = panel.locator('[data-calendar-visits] tbody tr'); assert visit_rows.count() == 8
        for index, r in enumerate(result['visit_rows']):
            assert visit_rows.nth(index).locator('td').all_inner_texts() == [r['climate'].title(), str(r['hours_worker_year']), str(r['crew']),
                f'{r["original_planned_visits"]:,}', f'{r["packed_visits"]:,}', f'{r["blocked_by_mandatory_collection"]:,}', f'{r["greedy_crew_unpacked_visits"]:,}']
        for phrase in ('not annual food-supported visit counts', 'Greedy failure does not prove', 'unaffiliated'):
            assert phrase.lower() in panel.inner_text().lower()
        links = 0
        for link in panel.locator('a').all():
            url = link.evaluate('(el)=>el.href'); reply = page.request.get(url); assert reply.ok, url
            path = ROOT / unquote(urlsplit(url).path).lstrip('/'); assert reply.body() == path.read_bytes(), str(path); links += 1
        with page.expect_download() as event: panel.locator('a[href$="visit_calendar_example.csv"]').click()
        rows = list(csv.DictReader(io.StringIO(Path(event.value.path()).read_text())))
        assert rows and {r['duty'] for r in rows} == {'home', 'collection', 'visit'}
        workers = {}
        for r in rows:
            start, end = float(r['start_working_hour']), float(r['end_working_hour'])
            assert 0 <= start <= end <= float(r['month_calendar_hours'])
            assert abs((end - start) - float(r['duty_hours'])) < 1e-10
            key = r['scenario'], r['seasonal_bin'], r['provider_index'], r['worker_index']
            workers.setdefault(key, []).append((start, end))
        for intervals in workers.values():
            intervals.sort(); assert all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:]))
            assert sum(end - start for start, end in intervals) <= 50 + 1e-9
        assert len(workers) == 12
        for theme in ('light', 'dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344, 390):
                page.set_viewport_size(dict(width=width, height=844)); assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        for selector in ('#visit-grid', '#spare-visits', '#network-visits', '#dispatch-seeded', '#monthly-work', '#housing-density'):
            assert page.locator(selector).count() == 1
        page.route('**/data/ledger.json', lambda route: route.abort()); page.reload(wait_until='networkidle')
        page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")')
        assert page.locator('#visit-calendar tbody tr').count() == 12 and not errors, errors
        browser.close()
    (OUT / 'review.json').write_text(json.dumps(dict(status='passed', collection_rows=4, visit_rows=8, figures=3,
        local_links_byte_exact=links, worker_csv_download=True, independently_checked_csv_workers=len(workers),
        keyboard_mobile_themes=True, prior_panels_retained=True, optional_inventory_failure_isolated=True, page_errors=errors), indent=2) + '\n')
    print('Calendar evidence browser passed:12exact rows,3figures,6byte-exact links,12worker CSV intervals,mobile/themes/failure checks.')


if __name__ == '__main__': main()
