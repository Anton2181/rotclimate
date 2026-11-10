"""Verify adaptive settlement research and source-audit downloads in the normal atlas."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766')
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True);errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1100))
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.base+'/atlases/',wait_until='domcontentloaded')
        page.click('a[href="earth_evidence/"]')
        section=page.locator('#settlement-intensity');section.wait_for()
        assert section.locator('#settlement-intensity-results tbody tr').count()==6
        assert '0.521' in section.inner_text() and '0.055' in section.inner_text()
        assert 'no production adoption' in section.inner_text().lower()
        assert 'zero ID joins' in section.inner_text()
        for img in section.locator('img').all():
            page.wait_for_function('(el)=>el.complete&&el.naturalWidth>0',arg=img.element_handle())
        links=[]
        for link in section.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            if url.endswith('settlement_intensity.json'):
                r=response.json();assert len(r['rows'])==108 and not r['adopt']
            if url.endswith('vidarbha_preparation.json'):
                r=response.json();assert not r['model_scores_computed'] and r['joins']['common_ids']==0
            links.append(url)
        assert len(links)==7
        assert page.locator('#settlement-locations-results tbody tr').count()==4
        section.screenshot(path=str(args.out/'adaptive_desktop.png'))
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme);page.set_viewport_size(dict(width=390,height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors,errors
    result=dict(status='passed',declared_evaluations=108,images_loaded=2,local_links=links,
        previous_study_retained=True,unscored_source_failure_label=True,mobile_light_dark=True,page_errors=errors)
    (args.out/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
