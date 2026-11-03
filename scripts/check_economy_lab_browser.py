"""Check the launcher-linked economy lab and its actual prototype receipts."""
from pathlib import Path
import argparse
import json
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1000));errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.base+'/atlases/',wait_until='domcontentloaded')
        page.get_by_role('link',name='Food, farming and society →',exact=True).click()
        page.get_by_role('heading',name='Food, farming and society',exact=True).wait_for()
        assert page.locator('.status').all_inner_texts()==['One numerical prototype','Production proposals under review']
        receipt=page.request.get(args.base+'/atlases/economy_lab/data/receipt.json').json()
        assert receipt['status']=='numerical_prototype' and not receipt['production_atlas_changed']
        assert receipt['results']['One harvest']['shortfall_days']==164
        assert receipt['results']['Two equal harvests']['shortfall_days']==0
        assert receipt['results']['Even daily supply (control)']['shortfall_days']==0
        assert page.locator('tbody tr').count()==9
        for picture in page.locator('img').all():
            page.wait_for_function('(el)=>el.complete && el.naturalWidth>0',arg=picture.element_handle())
        downloads=[]
        for link in page.locator('a[download]').all():
            response=page.request.get(link.evaluate('(el)=>el.href'))
            assert response.ok and response.headers['cache-control']=='no-store'
            response.json();downloads.append(link.inner_text())
        assert len(downloads)==2
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for viewport in [dict(width=1440,height=1000),dict(width=390,height=844)]:
                page.set_viewport_size(viewport)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                if theme=='light' and viewport['width']==1440:
                    page.screenshot(path=str(args.out/'economy_lab.png'),full_page=True)
        assert not errors,errors;browser.close()
    result=dict(status='passed',hub_link='passed',prototype_receipt='passed',downloads=downloads,
        viewports=['1440x1000','390x844'],themes=['light','dark'],mobile_overflow=False,page_errors=errors)
    (args.out/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
