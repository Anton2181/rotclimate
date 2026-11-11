"""Check finite-work research/downloads and explicit non-calibrated status."""
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:8766');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);links=[];errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1000));page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(a.base+'/atlases/earth_evidence/',wait_until='domcontentloaded');detail=page.locator('#settlement-service-capacity')
        assert detail.get_attribute('open') is None;detail.locator('summary').focus();page.keyboard.press('Enter')
        assert detail.locator('tbody tr').count()==6
        assert 'not Earth-calibrated' in detail.inner_text() and '98.39%' in detail.inner_text()
        expected=actual=None
        for link in detail.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            if url.endswith('settlement_service_capacity.json'):
                data=response.json();expected=data['fields_sha256']
                assert len(data['scenarios'])==60 and len(data['food_replays'])==20
                assert not data['adopt'] and not data['earth_calibrated_service_rates'] and not data['population_food_staff_control_changed']
            if url.endswith('fields.npz'):actual=hashlib.sha256(response.body()).hexdigest()
            links.append(url)
        assert len(links)==6 and expected==actual
        img=detail.locator('img');assert img.count()==1;img.scroll_into_view_if_needed();img.evaluate('(el)=>el.decode()');assert img.evaluate('(el)=>el.naturalWidth==2250')
        usage=page.request.get(a.base+'/atlases/earth_evidence/data/dataset_usage.json').json()
        assert next(e for e in usage['datasets'] if e['id']=='rural_roman_britain')['status']=='exposed_conditional_context_diagnostic'
        assert next(e for e in usage['datasets'] if e['id']=='settlement_service_capacity_20261111')['status']=='implementation_work_budget_diagnostic_not_calibrated'
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for width in [390,344]:
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors
    (a.out/'checks.json').write_text(json.dumps(dict(status='passed',default_collapsed=True,keyboard_open=True,rows=6,
        aggregate_links=links,model_fields_byte_exact=True,non_calibrated_status_explicit=True,light_dark_mobile=True,page_errors=errors),indent=2)+'\n')
    print('Capacity6rows/figure/6links,byte-exact fields,non-calibrated status and mobile/dark pass.')


if __name__=='__main__':main()
