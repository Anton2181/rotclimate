"""Check all twelve collector food/work outcomes and full calendar archives."""
import json
from pathlib import Path
from urllib.parse import unquote,urlsplit

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/continuous_collection_calendar_20261112/browser/evidence'


def main():
    OUT.mkdir(parents=True,exist_ok=True);r=json.loads((ROOT/'output/continuous_collection_calendar_20261112/results.json').read_text())
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8766/atlases/earth_evidence/',wait_until='networkidle')
        panel=page.locator('#continuous-collection');assert panel.get_attribute('open') is None
        panel.locator('summary').focus();page.keyboard.press('Enter');page.wait_for_function('Array.from(document.querySelectorAll("#continuous-collection img")).every(i=>i.naturalWidth>0)')
        assert panel.locator('tbody tr').count()==12 and panel.locator('img').count()==2
        for i,v in enumerate(r['rows']):
            assert panel.locator('tbody tr').nth(i).locator('td').all_inner_texts()==[v['climate'].title(),str(v['hours_worker_year']),v['accounting'],str(v['scored_providers']),str(v['mandatory_complete']),str(v['food_no_shortage']),str(v['mandatory_and_food']),f'{v["unmet"]:,.3f}',f'{100*v["unmet"]/v["needed"]:.6f}']
        for phrase in ('including partial delivery','A-to-B isolates missing loads','B-to-C isolates phase','counterfactual retained supply','NOT actual transport loss','do not qualify new visit maps','maps/defaults stay byte unchanged'):
            assert phrase.lower() in panel.inner_text().lower(),phrase
        links=0
        for link in panel.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            path=ROOT/unquote(urlsplit(url).path).lstrip('/');assert response.body()==path.read_bytes(),str(path);links+=1
        assert links==13
        for theme in ('light','dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344,390):
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        for selector in ('#continuous-destination','#meal-headroom','#delivery-timing','#provider-year'):assert page.locator(selector).count()==1
        page.route('**/data/ledger.json',lambda route:route.abort());page.reload(wait_until='networkidle');page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")')
        assert page.locator('#continuous-collection tbody tr').count()==12 and not errors,errors;browser.close()
    (OUT/'review.json').write_text(json.dumps(dict(status='passed',exact_rows=12,figures=2,links_byte_exact=links,keyboard_mobile_themes=True,inventory_failure_isolated=True,earlier_panels_retained=True,page_errors=errors),indent=2)+'\n')
    print('New collector browser passed:12exact rows,2figures,13byte-exact links,mobile/themes/keyboard/failure.')


if __name__=='__main__':main()
