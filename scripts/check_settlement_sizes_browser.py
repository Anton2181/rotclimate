"""Verify the new evidence panel and served downloads, including mobile themes."""
import json
from pathlib import Path
from urllib.parse import unquote,urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:8766/atlases/earth_evidence/',wait_until='domcontentloaded')
        panel=page.locator('#settlement-sizes');assert not panel.get_attribute('open')
        panel.locator('summary').focus();page.keyboard.press('Enter');assert panel.get_attribute('open') is not None
        assert 'No AD150 size target yet clears all gates.' in panel.inner_text()
        image=panel.locator('img');image.scroll_into_view_if_needed()
        page.wait_for_function('document.querySelector("#settlement-sizes img").naturalWidth>0')
        links=0
        for link in panel.locator('a').all():
            url=link.evaluate('(el)=>el.href')
            if urlsplit(url).netloc!='127.0.0.1:8766':continue
            response=page.request.get(url);assert response.ok,url
            path=ROOT/unquote(urlsplit(url).path).lstrip('/')
            assert response.body()==path.read_bytes(),str(path)
            links+=1
        for theme in ('light','dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344,390):
                page.set_viewport_size(dict(width=width,height=844))
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert page.locator('#settlement-feedback').count()==1 and page.locator('#settlement-feedback-scan').count()==1
        assert not errors,errors
        browser.close()
    out=ROOT/'output/settlement_size_evidence_20261112/browser';out.mkdir(exist_ok=True,parents=True)
    (out/'review.json').write_text(json.dumps(dict(status='passed',keyboard_open=True,local_links_byte_exact=links,
        figure_loaded=True,mobile_widths=[344,390],themes=['light','dark'],preceding_feedback_and_scan_retained=True,
        page_errors=errors),indent=2)+'\n')
    print('Housing evidence browser passed;'+str(links)+'local links byte exact,keyboard/mobile/dark and preceding panels retained.')


if __name__=='__main__':main()
