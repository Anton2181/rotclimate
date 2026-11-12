"""Check all declared destination timing outcomes and downloadable evidence."""
import json
from pathlib import Path
from urllib.parse import unquote,urlsplit

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/network_visit_delivery_timing_20261112/browser/timing'


def main():
    OUT.mkdir(parents=True,exist_ok=True);r=json.loads((ROOT/'output/network_visit_delivery_timing_20261112/results.json').read_text())
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8766/atlases/earth_evidence/',wait_until='networkidle')
        panel=page.locator('#delivery-timing');assert panel.get_attribute('open') is None
        panel.locator('summary').focus();page.keyboard.press('Enter')
        page.wait_for_function('Array.from(document.querySelectorAll("#delivery-timing img")).every(i=>i.naturalWidth>0)')
        assert panel.locator('tbody tr').count()==24 and panel.locator('img').count()==3
        for i,v in enumerate(r['rows']):
            assert panel.locator('tbody tr').nth(i).locator('td').all_inner_texts()==[v['climate'].title(),str(v['hours_worker_year']),str(v['crew']),v['accounting'],str(v['scored_providers']),str(v['no_shortage_providers']),f'{v["unmet"]:,.3f}',f'{100*v["unmet"]/v["needed"]:.6f}',f'{v["provider_shortfall_days"]/v["scored_providers"]:.4f}']
        for phrase in ('one-bin dispatch lag','retention ONCE','only B-to-C','other providers remain explicitly unscored','not observed hunger','maps/defaults remain unchanged'):
            assert phrase in panel.inner_text(),phrase
        count=0
        for link in panel.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            file=ROOT/unquote(urlsplit(url).path).lstrip('/');assert response.body()==file.read_bytes(),str(file);count+=1
        assert count==16
        for theme in ('light','dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344,390):
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                assert panel.locator('tbody tr').count()==24
        for selector in ('#provider-year','#joint-order','#visit-calendar','#network-visits','#dispatch-seeded'):assert page.locator(selector).count()==1
        page.route('**/data/ledger.json',lambda route:route.abort());page.reload(wait_until='networkidle')
        page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")')
        assert page.locator('#delivery-timing tbody tr').count()==24 and not errors,errors
        browser.close()
    (OUT/'review.json').write_text(json.dumps(dict(status='passed',exact_rows=24,figures=3,links_byte_exact=count,keyboard_mobile_themes=True,inventory_failure_isolated=True,earlier_panels_retained=True,page_errors=errors),indent=2)+'\n')
    print('Destination timing browser passed:24exact rows,3figures,16byte-exact links,mobile/themes/keyboard/failure.')


if __name__=='__main__':main()
