"""Check the work audit and served numerical downloads on the normal atlas."""
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / 'output/settlement_monthly_work_20261112/browser'; out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport=dict(width=1440, height=1000)); errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8766/atlases/earth_evidence/', wait_until='networkidle')
        panel = page.locator('#monthly-work')
        assert panel.count() == 1 and panel.get_attribute('open') is None
        panel.locator('summary').focus(); page.keyboard.press('Enter')
        assert panel.get_attribute('open') is not None and panel.locator('tbody tr').count() == 16
        assert 'Refused fixed plans keep their food and work gaps visible.' in panel.inner_text()
        page.wait_for_function('document.querySelector("#monthly-work img").naturalWidth>0')
        links = 0
        for link in panel.locator('a').all():
            url = link.evaluate('(el)=>el.href')
            if urlsplit(url).netloc != '127.0.0.1:8766':
                continue
            response = page.request.get(url); assert response.ok, url
            path = ROOT / unquote(urlsplit(url).path).lstrip('/')
            assert response.body() == path.read_bytes(), str(path)
            links += 1
        for theme in ('light', 'dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344, 390):
                page.set_viewport_size(dict(width=width, height=844))
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.set_viewport_size(dict(width=1440, height=1000)); page.emulate_media(color_scheme='light')
        panel.screenshot(path=str(out / 'panel.png'))
        for selector in ('#housing-density', '#settlement-sizes', '#settlement-feedback', '#settlement-feedback-scan'):
            assert page.locator(selector).count() == 1
        page.route('**/data/ledger.json', lambda route: route.abort())
        page.reload(wait_until='networkidle')
        page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")')
        panel = page.locator('#monthly-work'); panel.locator('summary').click()
        assert panel.locator('tbody tr').count() == 16
        assert not errors, errors
        browser.close()
    (out / 'review.json').write_text(json.dumps(dict(status='passed', local_links_byte_exact=links,
        table_rows=16, figure_loaded=True, keyboard_open=True, mobile_widths=[344, 390], themes=['light', 'dark'],
        preceding_panels_retained=True, inventory_failure_isolated=True, page_errors=errors), indent=2) + '\n')
    print('Monthly work browser passed:', links, 'byte-exact links; mobile/themes/keyboard/failure isolation')


if __name__ == '__main__':
    main()
