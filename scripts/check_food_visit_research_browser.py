"""Check all 80 numeric rows,all downloads and optional map deep link."""
import gzip,json
from pathlib import Path
from urllib.parse import unquote,urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/continuous_food_visit_calendars_20261112/browser/evidence'

def main():
    OUT.mkdir(parents=True,exist_ok=True);r=json.loads((ROOT/'output/continuous_food_visit_calendars_20261112/results.json').read_text())
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from publish_food_visit_research import visit_cells,food_cells
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:8766/atlases/earth_evidence/',wait_until='networkidle');panel=page.locator('#food-checked-visits');assert panel.get_attribute('open') is None;panel.locator('summary').focus();page.keyboard.press('Enter');page.wait_for_function('Array.from(document.querySelectorAll("#food-checked-visits img")).every(i=>i.naturalWidth>0)')
        assert panel.locator('tbody tr').count()==80 and panel.locator('img').count()==2
        for i,cells in enumerate([visit_cells(v) for v in r['visit_rows']]+[food_cells(v) for v in r['food_rows']]):assert panel.locator('tbody tr').nth(i).locator('td').all_inner_texts()==cells
        links=0
        for link in panel.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url;path=ROOT/unquote(urlsplit(url).path).lstrip('/');path=path/'index.html' if path.is_dir() else path;assert response.body()==path.read_bytes(),str(path);links+=1
        for theme in ('light','dark'):
            page.emulate_media(color_scheme=theme)
            for width in (344,390):page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        for selector in ('#continuous-collection','#continuous-destination','#meal-headroom','#delivery-timing','#provider-year'):assert page.locator(selector).count()==1
        link=panel.locator('a').nth(1);page.goto(link.evaluate('(el)=>el.href'),wait_until='domcontentloaded');page.wait_for_function('document.querySelectorAll("#settled-readouts .readout").length===16',timeout=90000);assert page.locator('#variant').input_value()=='foodvisits600_crew1';assert page.locator('#experimental').is_checked()
        page.goto('http://127.0.0.1:8766/atlases/earth_evidence/',wait_until='networkidle');page.route('**/data/ledger.json',lambda route:route.abort());page.reload(wait_until='networkidle');page.wait_for_function('document.querySelector("#count").textContent.includes("unavailable")');assert page.locator('#food-checked-visits tbody tr').count()==80;assert not errors,errors;browser.close()
    (OUT/'review.json').write_text(json.dumps(dict(status='passed',exact_numeric_rows=80,figures=2,links_byte_exact=links,keyboard_mobile_themes=True,optional_map_deep_link=True,earlier_panels_retained=True,inventory_failure_isolated=True,page_errors=errors),indent=2)+'\n');print('Research browser passed80exact rows,2figures,',links,'byte-exact links,deep link,mobile,themes,keyboard,failure.')
if __name__=='__main__':main()
