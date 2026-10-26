"""Exercise the served accuracy companion, including native keyboard/deep links."""
from pathlib import Path
import argparse
import json
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1100})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.base.rstrip('/')+'/atlases/',wait_until='domcontentloaded')
        page.get_by_role('link',name='Climate accuracy and joint fit →',exact=True).click()
        page.locator('.experiment').first.wait_for()
        experiments=page.locator('.experiment')
        assert experiments.count()>=1
        assert page.locator('.experiment[open]').count()==1
        newest=experiments.first.get_attribute('id')
        assert experiments.first.get_attribute('open') is not None
        last=experiments.last.get_attribute('id')
        page.locator(f'.research-index a[href="#{last}"]').click()
        # Hash-change handlers run asynchronously after the native click.
        page.wait_for_function('(id)=>document.getElementById(id).open',arg=last)
        summary=page.locator(f'#{last} > summary')
        summary.focus();page.keyboard.press('Enter')
        page.wait_for_function('(id)=>!document.getElementById(id).open',arg=last)
        page.reload(wait_until='domcontentloaded')
        page.wait_for_function('(id)=>document.getElementById(id).open',arg=last)
        for detail in experiments.all():detail.evaluate('(el)=>el.open=true')
        for picture in page.locator('img').all():
            picture.scroll_into_view_if_needed()
            page.wait_for_function('(el)=>el.complete && el.naturalWidth>0',arg=picture.element_handle())
        reference=page.request.get(args.base.rstrip('/')+'/atlases/climate_accuracy/data/summary.json').json()
        profile=reference['physics_profile']
        expected=[f'{reference["earth_development"]["candidate"]["T_monthly_mae"]:.2f} °C',
                  f'{reference["cities"][profile]["monthly_mae_mm"]:.2f} mm',
                  f'{100*reference["cities"][profile]["within_25pct"]:.2f}%']
        assert page.locator('.number').all_inner_texts()==expected
        downloads=[]
        for link in page.locator('a[download]').all():
            response=page.request.get(link.evaluate('(el)=>el.href'))
            assert response.ok and response.headers['cache-control']=='no-store'
            response.json()
            downloads.append(link.inner_text())
        assert len(downloads)>=2
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for viewport in [{'width':1440,'height':1100},{'width':390,'height':844}]:
                page.set_viewport_size(viewport)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        result=dict(status='passed',experiments=experiments.count(),newest_open=newest,
            images=page.locator('img').count(),downloads=downloads,keyboard='passed',hash_reload='passed',
            themes=['light','dark'],mobile_overflow=False,page_errors=errors)
        assert not errors,errors
        browser.close()
    (args.out/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
