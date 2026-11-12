"""Check provider-year research tables,all local evidence links and failure isolation."""
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/network_visit_year_complete_20261112/browser/evidence'


def main():
    OUT.mkdir(parents=True, exist_ok=True); result = json.loads((ROOT / 'output/network_visit_year_complete_20261112/results.json').read_text())
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(); errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8766/atlases/earth_evidence/', wait_until='networkidle')
        panel = page.locator('#provider-year'); assert panel.get_attribute('open') is None
        panel.locator('summary').focus(); page.keyboard.press('Enter')
        page.wait_for_function('Array.from(document.querySelectorAll("#provider-year img")).every(i=>i.naturalWidth>0)')
        assert panel.locator('img').count() == 3 and panel.locator('tbody tr').count() == 8
        for i, r in enumerate(result['rows']):
            assert panel.locator('tbody tr').nth(i).locator('td').all_inner_texts() == [r['climate'].title(), str(r['hours_worker_year']), str(r['crew']),
                f'{r["original_funded_visits"]:,}', f'{r["baseline_twelve_bin_visits"]:,}', f'{r["qualified_visits"]:,}', f'+{r["added_visits"]:,}', str(r['qualified_providers'])]
        for phrase in ('necessary delivery-scheduling gate', 'not daily provisioning', 'Individual job successes are never merged', 'remain unscored'):
            assert phrase in panel.inner_text()
        links = 0
        for link in panel.locator('a').all():
            url = link.evaluate('(el)=>el.href'); response = page.request.get(url); assert response.ok, url
            path = ROOT / unquote(urlsplit(url).path).lstrip('/')
            if path.is_dir(): path /= 'index.html'
            assert response.body() == path.read_bytes(), str(path); links += 1
        for theme in ('light', 'dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344, 390):
                page.set_viewport_size(dict(width=width, height=844)); assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        for selector in ('#joint-order', '#visit-calendar', '#visit-grid', '#spare-visits', '#network-visits', '#dispatch-seeded'):
            assert page.locator(selector).count() == 1
        page.route('**/data/ledger.json', lambda route: route.abort()); page.reload(wait_until='networkidle')
        page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")')
        assert page.locator('#provider-year tbody tr').count() == 8 and not errors, errors
        browser.close()
    (OUT / 'review.json').write_text(json.dumps(dict(status='passed', exact_rows=8, figures=3, local_links_byte_exact=links,
        keyboard_mobile_themes=True, earlier_panels_retained=True, inventory_failure_isolated=True, page_errors=errors), indent=2) + '\n')
    print('Provider-year research browser passed:8exact rows,3figures,9byte-exact links,mobile/themes/failure checks.')


if __name__ == '__main__': main()
