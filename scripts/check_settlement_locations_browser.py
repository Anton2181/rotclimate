"""Check the new settlement research section on the normal served atlas."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',default='http://127.0.0.1:8766')
    p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1100))
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.base+'/atlases/',wait_until='domcontentloaded')
        page.click('a[href="earth_evidence/"]')
        section=page.locator('#settlement-locations')
        section.wait_for()
        assert 'no main-map adoption' in section.inner_text()
        table=page.locator('#settlement-locations-results')
        assert table.locator('tbody tr').count()==4
        assert '0.592' in table.inner_text() and '0.358' in table.inner_text()
        picture=section.locator('img')
        page.wait_for_function('(el)=>el.complete && el.naturalWidth>0',arg=picture.element_handle())
        checked=[]
        for link in section.locator('a').all():
            url=link.evaluate('(el)=>el.href')
            if not url.startswith(args.base):continue
            response=page.request.get(url);assert response.ok,url
            if url.endswith('settlement_locations.json'):
                result=response.json()
                assert len(result['rows'])==72 and result['adopt'] is False
                assert result['development_lead']=='draw_9km_old_cores_L800'
            checked.append(url)
        assert len(checked)==4
        section.screenshot(path=str(args.out/'settlement_research_desktop.png'))
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            page.set_viewport_size(dict(width=390,height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors,errors
    result=dict(status='passed',local_links=checked,result_rows=72,no_production_adoption=True,
        figure_loaded=True,light_dark_mobile=True,page_errors=errors)
    (args.out/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
