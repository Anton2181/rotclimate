"""Check joint-location evidence, exact downloads and normal hub navigation."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8766')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    errors, bad, links = [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport=dict(width=1440, height=1000))
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('response', lambda r: bad.append(r.url) if r.status >= 400 else None)
        page.goto(args.base + '/atlases/', wait_until='domcontentloaded')
        page.click('a[href="earth_evidence/"]')
        detail = page.locator('#settlement-joint')
        assert detail.get_attribute('open') is None
        detail.locator('summary').focus(); page.keyboard.press('Enter')
        assert detail.get_attribute('open') is not None
        assert detail.locator('tbody tr').count() == 6
        assert 'No production adoption' in detail.inner_text()
        assert 'not a new blind validation' in detail.inner_text()
        assert '1,239' in detail.inner_text() and '1,292' in detail.inner_text()
        for link in detail.locator('a').all():
            url = link.evaluate('(el)=>el.href'); response = page.request.get(url)
            assert response.ok, url
            relative = url.removeprefix(args.base + '/')
            assert response.body() == (ROOT / relative).read_bytes(), relative
            links.append(relative)
        assert len(links) == 7
        with page.expect_download() as event:
            detail.locator('a[href="data/settlement_joint_locations_positions.npz"]').click()
        assert Path(event.value.path()).read_bytes() == (ROOT / 'output/settlement_joint_locations_20261112/positions.npz').read_bytes()
        for img in detail.locator('img').all():
            img.evaluate('(el)=>el.decode()')
            assert img.evaluate('(el)=>el.naturalWidth>1000')
        detail.locator('summary').scroll_into_view_if_needed()
        page.screenshot(path=str(args.out / 'joint_desktop.png'))
        usage = page.request.get(args.base + '/atlases/earth_evidence/data/dataset_usage.json').json()
        assert next(e for e in usage['datasets'] if e['id'] == 'settlement_joint_locations_20261112')['status'] == 'exposed_development_only'
        for theme in ('light', 'dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344, 390):
                page.set_viewport_size(dict(width=width, height=844))
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert page.locator('#population-extension').count() == 1
        assert page.locator('#vidarbha-transfer').count() == 1
        page.wait_for_function('document.querySelectorAll("#rows tr").length===40')
        assert not errors and not bad, (errors, bad)
        page.close()
        page = browser.new_page()
        page.route('**/earth_evidence/data/ledger.json', lambda route: route.fulfill(status=404, body='missing'))
        page.goto(args.base + '/atlases/earth_evidence/', wait_until='domcontentloaded')
        page.wait_for_function('document.querySelector("#count").textContent.includes("Detailed inventory unavailable")')
        page.locator('#settlement-joint summary').click()
        assert page.locator('#settlement-joint-results').is_visible()
        browser.close()
    receipt = dict(status='passed', default_collapsed=True, keyboard_open=True, rows=6,
        byte_exact_local_links=links, figures_loaded=2, exact_positions_download=True,
        desktop_mobile_light_dark=True, previous_panels_retained=True, optional_inventory_failure_isolated=True,
        page_errors=errors, failed_requests=bad)
    (args.out / 'checks.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Joint browser passed: six rows, seven byte-exact links, two figures and mobile/dark/failure UI.')


if __name__ == '__main__':
    main()
