"""Verify conditional diagnostic UI, aggregate links and source-exposure labels."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:8766');p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True);errors=[];links=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'],headless=True)
        page=browser.new_page(viewport=dict(width=1440,height=1000));page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.base+'/atlases/earth_evidence/',wait_until='domcontentloaded')
        detail=page.locator('#settlement-role-contrast');assert detail.get_attribute('open') is None
        detail.locator('summary').focus();page.keyboard.press('Enter')
        assert detail.locator('tbody tr').count()==3 and '0.5478' in detail.inner_text() and '0.5190' in detail.inner_text()
        for a in detail.locator('a').all():
            url=a.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok and not url.endswith('.csv')
            if url.endswith('settlement_role_contrast.json'):
                r=response.json();assert not r['adopt'] and r['fitted_parameters']==0 and len(r['results'])==9
            if url.endswith('settlement_role_contrast_preparation.json'):
                r=response.json();assert not r['private_matches_redistributed'] and r['scenarios'][0]['mixed_cells']==155
            links.append(url)
        assert len(links)==5
        figure=detail.locator('img');figure.scroll_into_view_if_needed();assert figure.evaluate('(el)=>el.complete && el.naturalWidth===1800')
        usage=page.request.get(args.base+'/atlases/earth_evidence/data/dataset_usage.json').json()
        assert next(e for e in usage['datasets'] if e['id']=='rural_roman_britain')['status']=='exposed_conditional_context_diagnostic'
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for width in [390,344]:
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors
    (args.out/'checks.json').write_text(json.dumps(dict(status='passed',default_collapsed=True,keyboard_open=True,aggregate_links=links,
        role_rows=3,figure_loaded=True,source_exposure_current=True,light_dark_mobile=True,page_errors=errors),indent=2)+'\n')
    print('Conditional research panel,5aggregate links,figure,source exposure and mobile/dark pass.')


if __name__=='__main__':main()
