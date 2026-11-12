"""Check the joint-map evidence and its independently served local links."""
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / 'output/settlement_dispatch_20261112/browser/evidence'; out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(); errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8766/atlases/earth_evidence/', wait_until='networkidle')
        panel = page.locator('#settlement-dispatch'); assert panel.get_attribute('open') is None
        panel.locator('summary').focus(); page.keyboard.press('Enter')
        assert panel.locator('tbody tr').count() == 16 and panel.locator('img').count() == 3
        page.wait_for_function('Array.from(document.querySelectorAll("#settlement-dispatch img")).every(i=>i.naturalWidth>0)')
        links = 0
        for link in panel.locator('a').all():
            url = link.evaluate('(el)=>el.href')
            if urlsplit(url).netloc != '127.0.0.1:8766': continue
            reply = page.request.get(url); assert reply.ok, url
            path = ROOT / unquote(urlsplit(url).path).lstrip('/')
            if path.is_dir(): path /= 'index.html'
            assert reply.body() == path.read_bytes(), str(path); links += 1
        assert 'geographic patrol work and political authority remain unqualified' in panel.inner_text()
        for theme in ('light', 'dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344, 390):
                page.set_viewport_size(dict(width=width, height=844))
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        for selector in ('#monthly-work', '#housing-density', '#settlement-sizes', '#settlement-feedback'):
            assert page.locator(selector).count() == 1
        page.route('**/data/ledger.json', lambda route: route.abort()); page.reload(wait_until='networkidle')
        page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")')
        assert page.locator('#settlement-dispatch tbody tr').count() == 16 and not errors
        browser.close()
    (out / 'review.json').write_text(json.dumps(dict(status='passed', local_links_byte_exact=links, table_rows=16,
        figures=3, keyboard_mobile_themes=True, previous_panels_retained=True, optional_inventory_failure_isolated=True), indent=2) + '\n')
    print('Joint dispatch evidence browser passed:', links, 'byte-exact links,16rows,3figures,mobile/themes/failure checks.')


if __name__ == '__main__': main()
