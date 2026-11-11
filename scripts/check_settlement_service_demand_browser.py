"""Check service research, actual model-field download and preserved source status."""
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
        detail=page.locator('#settlement-service-demand');assert detail.get_attribute('open') is None
        detail.locator('summary').focus();page.keyboard.press('Enter')
        assert detail.locator('tbody tr').count()==8
        assert '0.6546' in detail.inner_text() and '0.5479' in detail.inner_text()
        expected=None;npz_digest=None
        for a in detail.locator('a').all():
            url=a.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            assert not url.endswith('.csv')
            if url.endswith('settlement_service_fields.json'):
                data=response.json();expected=data['fields_sha256'];assert len(data['scenarios'])==6
                assert data['request_units_are_not_residents_or_completed_services']
            if url.endswith('settlement_service_demand.json'):
                data=response.json();assert not data['adopt'] and data['fitted_parameters']==0
                assert data['prior_reference_controls_exact']==27
            if url.endswith('fields.npz'):npz_digest=hashlib.sha256(response.body()).hexdigest()
            links.append(url)
        assert len(links)==6 and expected==npz_digest
        assert detail.locator('img').count()==2
        for img in detail.locator('img').all():
            img.scroll_into_view_if_needed()
            img.evaluate('(el)=>el.decode()');assert img.evaluate('(el)=>el.naturalWidth>1500')
        usage=page.request.get(args.base+'/atlases/earth_evidence/data/dataset_usage.json').json()
        assert next(e for e in usage['datasets'] if e['id']=='rural_roman_britain')['status']=='exposed_conditional_context_diagnostic'
        assert any(e['id']=='settlement_service_demand_20261111' for e in usage['datasets'])
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for width in [390,344]:
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors
    (args.out/'checks.json').write_text(json.dumps(dict(status='passed',default_collapsed=True,keyboard_open=True,
        rows=8,figures=2,aggregate_links=links,model_npz_download_byte_exact=True,source_exposure_current=True,
        light_dark_mobile=True,page_errors=errors),indent=2)+'\n')
    print('Service panel,8rows/2figures/6links,byte-exact NPZ,source status and mobile/dark pass.')


if __name__=='__main__':main()
