"""Check provider/source preparation status, aggregate identities and mobile UI."""
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:8766');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);links=[];errors=[];digests={};review=None
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1000));page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(a.base+'/atlases/earth_evidence/',wait_until='domcontentloaded');detail=page.locator('#institution-evidence')
        assert detail.get_attribute('open') is None;detail.locator('summary').focus();page.keyboard.press('Enter')
        assert detail.locator('#institution-provider-results tbody tr').count()==2
        assert detail.locator('#institution-source-results tbody tr').count()==10
        assert '86.05%' in detail.inner_text() and 'source preparation only' in detail.inner_text()
        for link in detail.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            if url.endswith('institution_earth_preparation.json'):
                data=response.json();assert not data['model_scores_computed'] and not data['independent_or_sealed'] and not data['adopt']
                assert data['polity_records']==626 and len(data['variables'])==10
                digests['earth_preparation_sha256']=hashlib.sha256(response.body()).hexdigest()
            if url.endswith('institution_provider_audit.json'):
                data=response.json();assert len(data['atlases']['corrected']['actors'])==19 and not data['physical_population_food_staff_control_changed']
                digests['provider_audit_sha256']=hashlib.sha256(response.body()).hexdigest()
            if url.endswith('institution_review.json'):review=response.json()
            assert not url.endswith(('.xlsx','.csv'));links.append(url)
        assert len(links)==6 and review and all(review[k]==v for k,v in digests.items())
        img=detail.locator('img');assert img.count()==1;img.scroll_into_view_if_needed();img.evaluate('(el)=>el.decode()');assert img.evaluate('(el)=>el.naturalWidth==1950')
        usage=page.request.get(a.base+'/atlases/earth_evidence/data/dataset_usage.json').json()
        assert next(e for e in usage['datasets'] if e['id']=='rural_roman_britain')['status']=='exposed_conditional_context_diagnostic'
        assert next(e for e in usage['datasets'] if e['id']=='seshat_polaris2026')['status'] in ['prepared_institution_schema_no_model_scores','prepared_institution_date_scopes_no_model_scores']
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for width in [390,344]:
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors
    (a.out/'checks.json').write_text(json.dumps(dict(status='passed',default_collapsed=True,keyboard_open=True,provider_rows=2,source_rows=10,
        aggregate_links=links,downloads_match_review=True,raw_workbook_not_linked=True,source_exposure_correct=True,light_dark_mobile=True,page_errors=errors),indent=2)+'\n')
    print('Institution2provider/10source rows,figure/6aggregate links,review identities,source exposure and mobile/dark pass.')


if __name__=='__main__':main()
