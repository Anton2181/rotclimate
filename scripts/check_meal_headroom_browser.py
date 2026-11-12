"""Check every conditional meal bound and byte-exact research download."""
import json
from pathlib import Path
from urllib.parse import unquote,urlsplit

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/network_visit_meal_headroom_20261112/browser/evidence'


def main():
    OUT.mkdir(parents=True,exist_ok=True);r=json.loads((ROOT/'output/network_visit_meal_headroom_20261112/results.json').read_text())
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8766/atlases/earth_evidence/',wait_until='networkidle')
        panel=page.locator('#meal-headroom');assert panel.get_attribute('open') is None
        panel.locator('summary').focus();page.keyboard.press('Enter');page.wait_for_function('Array.from(document.querySelectorAll("#meal-headroom img")).every(i=>i.naturalWidth>0)')
        assert panel.locator('tbody tr').count()==16 and panel.locator('img').count()==2
        for i,v in enumerate(r['rows']):
            assert panel.locator('tbody tr').nth(i).locator('td').all_inner_texts()==[v['climate'].title(),str(v['hours_worker_year']),str(v['crew']),v['accounting'],str(v['scored_providers']),str(v['staff_infeasible']),str(v['full_demand_passes']),f'{v["civilian_meal_equivalent_reduction"]:,.3f}',f'{100*v["civilian_meal_equivalent_reduction"]/v["parent_civilian"]:.5f}']
        for phrase in ('ORIGINAL physical storage','staff meals','not a census','source within-bin food','Existing maps/defaults remain byte unchanged','other providers remain explicitly unscored','floating-point uncertainty'):
            assert phrase.lower() in panel.inner_text().lower(),phrase
        links=0
        for link in panel.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            path=ROOT/unquote(urlsplit(url).path).lstrip('/');assert response.body()==path.read_bytes(),str(path);links+=1
        assert links==8
        for theme in ('light','dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344,390):
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        for selector in ('#delivery-timing','#provider-year','#joint-order','#visit-calendar'):assert page.locator(selector).count()==1
        page.route('**/data/ledger.json',lambda route:route.abort());page.reload(wait_until='networkidle');page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")')
        assert page.locator('#meal-headroom tbody tr').count()==16 and not errors,errors;browser.close()
    (OUT/'review.json').write_text(json.dumps(dict(status='passed',exact_rows=16,figures=2,links_byte_exact=links,keyboard_mobile_themes=True,inventory_failure_isolated=True,earlier_panels_retained=True,page_errors=errors),indent=2)+'\n')
    print('Meal-headroom browser passed:16exact rows,2figures,8byte-exact links,mobile/themes/keyboard/failure.')


if __name__=='__main__':main()
