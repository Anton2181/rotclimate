"""Check all twelve collector food/work outcomes and full calendar archives."""
import json
import hashlib
from urllib.request import urlopen
from pathlib import Path
from urllib.parse import unquote,urlsplit

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/source_filled_destination_20261113/browser/evidence'


def main():
    OUT.mkdir(parents=True,exist_ok=True);r=json.loads((ROOT/'output/source_filled_destination_20261113/results.json').read_text())
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8766/atlases/earth_evidence/',wait_until='networkidle')
        panel=page.locator('#source-filled-destination');assert panel.get_attribute('open') is None
        panel.locator('summary').focus();page.keyboard.press('Enter');page.wait_for_function('Array.from(document.querySelectorAll("#source-filled-destination img")).every(i=>i.naturalWidth>0)')
        assert panel.locator('tbody tr').count()==48 and panel.locator('img').count()==2
        for i,v in enumerate(r['rows']):
            expected=[v['climate'].title(),str(v['hours_worker_year']),str(v['crew']),v['policy'],v['accounting'],str(v['scored_providers']),str(v['destination_food_pass']),str(v['mandatory_complete']),str(v['source_export_pass']),str(v['source_rural_pass']),str(v['all_gates_pass']),f'{v["unmet"]:,.3f}',f'{100*v["unmet"]/v["needed"]:.6f}']
            assert panel.locator('tbody tr').nth(i).locator('td').all_inner_texts()==expected
        for phrase in ('A exactly reproduces','SAME fixed jobs','×0.95 ONCE','ZERO providers pass ALL','unfilled source requests are not actual transport loss','All 49 model and 3 export files','Crew-carried food/location'):
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
        assert links==59
        for theme in ('light','dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344,390):
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        for selector in ('#source-pickup-calendars','#source-continuous-meals','#food-checked-visits','#continuous-collection','#continuous-destination','#meal-headroom','#delivery-timing','#provider-year'):assert page.locator(selector).count()==1
        page.route('**/data/ledger.json',lambda route:route.abort());page.reload(wait_until='networkidle');page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")')
        assert page.locator('#source-filled-destination tbody tr').count()==48 and not errors,errors;browser.close()
    (OUT/'review.json').write_text(json.dumps(dict(status='passed',exact_rows=48,figures=2,links_byte_exact=links,browser_headers_and_streamed_static_HTTP_bytes=True,keyboard_mobile_themes=True,inventory_failure_isolated=True,earlier_panels_retained=True,page_errors=errors),indent=2)+'\n')
    print('Source-filled destination browser passed:48exact rows,2figures,59byte-exact links,mobile/themes/keyboard/failure.')


if __name__=='__main__':main()
