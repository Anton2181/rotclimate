"""Check availability controls, all downloads and responsive atlas presentation."""
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:8766');p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True);links=[];errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1000));page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.base+'/atlases/earth_evidence/',wait_until='domcontentloaded')
        detail=page.locator('#settlement-service-controls');assert detail.get_attribute('open') is None
        detail.locator('summary').focus();page.keyboard.press('Enter')
        assert detail.locator('tbody tr').count()==9
        assert '0.6453' in detail.inner_text() and '0.6462' in detail.inner_text()
        expected=None;actual=None
        for a in detail.locator('a').all():
            url=a.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            assert not url.endswith('.csv')
            if url.endswith('settlement_service_controls_fields.json'):
                data=response.json();expected=data['fields_sha256'];assert len(data['ledgers'])==18
            if url.endswith('settlement_service_controls.json'):
                data=response.json();assert not data['adopt'] and data['fitted_parameters']==0
                assert data['prior_service_diagnostics_exact']==378 and len(data['predictors'])==66
            if url.endswith('fields.npz'):actual=hashlib.sha256(response.body()).hexdigest()
            links.append(url)
        assert len(links)==6 and expected==actual
        img=detail.locator('img');assert img.count()==1;img.scroll_into_view_if_needed();img.evaluate('(el)=>el.decode()')
        assert img.evaluate('(el)=>el.naturalWidth==1800')
        usage=page.request.get(args.base+'/atlases/earth_evidence/data/dataset_usage.json').json()
        assert next(e for e in usage['datasets'] if e['id']=='rural_roman_britain')['status']=='exposed_conditional_context_diagnostic'
        assert any(e['id']=='settlement_service_controls_20261111' for e in usage['datasets'])
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for width in [390,344]:
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors
    (args.out/'checks.json').write_text(json.dumps(dict(status='passed',default_collapsed=True,keyboard_open=True,
        rows=9,figures=1,aggregate_links=links,model_npz_download_byte_exact=True,source_exposure_current=True,
        light_dark_mobile=True,page_errors=errors),indent=2)+'\n')
    print('Opportunity panel,9rows/figure/6links,byte-exact NPZ,source exposure and mobile/dark pass.')


if __name__=='__main__':main()
