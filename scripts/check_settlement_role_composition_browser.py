"""Check explicit unscored source groups, aggregate downloads and mobile layout."""
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:8766');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);errors=[];links=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1000));page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(a.base+'/atlases/earth_evidence/',wait_until='domcontentloaded');detail=page.locator('#settlement-role-composition')
        assert detail.get_attribute('open') is None;detail.locator('summary').focus();page.keyboard.press('Enter')
        assert detail.locator('tbody tr').count()==10
        assert detail.locator('td[colspan="2"]').count()==5
        assert '0.3930' in detail.inner_text() and '0.8899' in detail.inner_text()
        expected=actual=None
        for link in detail.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            if url.endswith('settlement_role_composition.json'):
                data=response.json();assert len(data['cases'])==10 and data['global_AUCs_computed']==2970
                assert not data['adopt'] and data['chosen_predictor'] is None
                actual=hashlib.sha256(response.body()).hexdigest()
            if url.endswith('settlement_role_composition_review.json'):expected=response.json()['source_result_sha256']
            links.append(url)
        assert len(links)==5 and expected==actual
        img=detail.locator('img');assert img.count()==1;img.scroll_into_view_if_needed();img.evaluate('(el)=>el.decode()');assert img.evaluate('(el)=>el.naturalWidth==1800')
        usage=page.request.get(a.base+'/atlases/earth_evidence/data/dataset_usage.json').json()
        assert next(e for e in usage['datasets'] if e['id']=='rural_roman_britain')['status']=='exposed_conditional_context_diagnostic'
        assert any(e['id']=='settlement_role_composition_20261111' for e in usage['datasets'])
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for width in [390,344]:
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors
    (a.out/'checks.json').write_text(json.dumps(dict(status='passed',default_collapsed=True,keyboard_open=True,rows=10,
        explicit_unscored_rows=5,aggregate_links=links,download_matches_review=True,light_dark_mobile=True,page_errors=errors),indent=2)+'\n')
    print('Composition10rows/5unscored,figure,5links,review identity,source status and mobile/dark pass.')


if __name__=='__main__':main()
