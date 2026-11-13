"""Check all twelve collector food/work outcomes and full calendar archives."""
import json
import hashlib
from urllib.request import urlopen
from pathlib import Path
from urllib.parse import unquote,urlsplit

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/source_food_events_20261113/browser/evidence'


def main():
    OUT.mkdir(parents=True,exist_ok=True);r=json.loads((ROOT/'output/source_food_events_20261113/results.json').read_text())
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8766/atlases/earth_evidence/',wait_until='networkidle')
        panel=page.locator('#source-pickup-calendars');assert panel.get_attribute('open') is None
        panel.locator('summary').focus();page.keyboard.press('Enter');page.wait_for_function('Array.from(document.querySelectorAll("#source-pickup-calendars img")).every(i=>i.naturalWidth>0)')
        assert panel.locator('tbody tr').count()==24 and panel.locator('img').count()==2
        for i,v in enumerate(r['rows']):
            expected=[v['climate'].title(),str(v['hours_worker_year']),str(v['crew']),v['policy'],str(v['active_providers']),str(v['export_request_pass_providers']),str(v['both_providers']),f'{v["raw_requested"]:,.3f}',f'{v["raw_unfilled"]:,.3f}',f'{100*v["raw_unfilled"]/v["raw_requested"]:.6f}',f'{v["rural_unmet"]:,.3f}']
            assert panel.locator('tbody tr').nth(i).locator('td').all_inner_texts()==expected
        for phrase in ('ONLY overflow quota','ZERO providers pass rural meals AND source export requests','No transport retention at source','not actual transport loss','remain unchanged','37 controls','crew-carried food/location'):
            assert phrase.lower() in panel.inner_text().lower(),phrase
        links=0
        for link in panel.locator('a').all():
            url=link.evaluate('(el)=>el.href');path=ROOT/unquote(urlsplit(url).path).lstrip('/')
            response=page.request.head(url);assert response.ok,url
            # Resolve each link through the browser, then stream the same static
            # HTTP asset to avoid Chromium's batch automatic-download restriction.
            digest=hashlib.sha256()
            with urlopen(url) as stream:
                while chunk:=stream.read(1024*1024):digest.update(chunk)
            assert digest.digest()==hashlib.sha256(path.read_bytes()).digest(),str(path)
            links+=1
        assert links==36
        for theme in ('light','dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344,390):
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        for selector in ('#source-continuous-meals','#food-checked-visits','#continuous-collection','#continuous-destination','#meal-headroom','#delivery-timing','#provider-year'):assert page.locator(selector).count()==1
        page.route('**/data/ledger.json',lambda route:route.abort());page.reload(wait_until='networkidle');page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")')
        assert page.locator('#source-pickup-calendars tbody tr').count()==24 and not errors,errors;browser.close()
    (OUT/'review.json').write_text(json.dumps(dict(status='passed',exact_rows=24,figures=2,links_byte_exact=links,browser_headers_and_streamed_static_HTTP_bytes=True,keyboard_mobile_themes=True,inventory_failure_isolated=True,earlier_panels_retained=True,page_errors=errors),indent=2)+'\n')
    print('Source pickup browser passed:24exact rows,2figures,36byte-exact links,mobile/themes/keyboard/failure.')


if __name__=='__main__':main()
