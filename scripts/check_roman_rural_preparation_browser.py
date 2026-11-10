"""Check the collapsed S2 preparation panel and aggregate-only downloads."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True);errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1100));page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.base+'/atlases/earth_evidence/',wait_until='domcontentloaded')
        detail=page.locator('#rural-preparation');assert detail.get_attribute('open') is None
        detail.locator('summary').focus();page.keyboard.press('Enter')
        page.wait_for_function('document.querySelector("#rural-preparation").open')
        assert detail.locator('tbody tr').count()==5
        assert '3,652' in detail.inner_text() and '608' in detail.inner_text()
        links=[]
        for link in detail.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            assert not url.endswith('.csv')
            if url.endswith('roman_rural_preparation.json'):
                audit=response.json();assert not audit['model_scores_computed'] and not audit['target_maps_generated']
            if url.endswith('source_csv_correction.json'):
                receipt=response.json();assert receipt['primary_join_and_axis_findings_unchanged']
                assert not receipt['climate_and_settlement_results_changed']
            links.append(url)
        assert len(links)==7
        detail.screenshot(path=str(args.out/'rural_preparation_desktop.png'))
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme);page.set_viewport_size(dict(width=390,height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors,errors
    result=dict(status='passed',default_collapsed=True,keyboard_open=True,aggregate_links=links,
        no_raw_tables=True,no_model_evaluation=True,light_dark_mobile=True,page_errors=errors)
    (args.out/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
