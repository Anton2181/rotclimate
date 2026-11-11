"""Check failed-transfer visibility, downloads, keyboard use and mobile layout."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--base',default='http://127.0.0.1:8766');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);errors=[];bad=[];links=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1000))
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:bad.append(r.url) if r.status>=400 else None)
        page.goto(a.base+'/atlases/',wait_until='domcontentloaded');page.click('a[href="earth_evidence/"]')
        detail=page.locator('#vidarbha-transfer');assert detail.get_attribute('open') is None
        detail.locator('summary').focus();page.keyboard.press('Enter');assert detail.get_attribute('open') is not None
        assert detail.locator('tbody tr').count()==6
        assert 'Failed the predeclared diagnostic.' in detail.inner_text()
        assert '−10.42' in detail.inner_text().replace('-','−') and '6.25%' in detail.inner_text()
        assert 'No fantasy population' in detail.inner_text()
        for link in detail.locator('a').all():
            url=link.evaluate('(el)=>el.href')
            if not url.startswith(a.base):continue
            response=page.request.get(url);assert response.ok,url
            relative=url.removeprefix(a.base+'/');assert response.body()==(ROOT/relative).read_bytes(),relative
            links.append(relative)
        assert len(links)==9
        with page.expect_download() as event:detail.locator('a[href="data/vidarbha_transfer.json"]').click()
        assert Path(event.value.path()).read_bytes()==(ROOT/'atlases/earth_evidence/data/vidarbha_transfer.json').read_bytes()
        for img in detail.locator('img').all():img.evaluate('(el)=>el.decode()');assert img.evaluate('(el)=>el.naturalWidth>1000')
        usage=page.request.get(a.base+'/atlases/earth_evidence/data/dataset_usage.json').json()
        assert next(e for e in usage['datasets'] if e['id']=='vidarbha_field_survey2016')['status']=='exposed_frozen_regional_transfer_failed_guard'
        assert next(e for e in usage['datasets'] if e['id']=='reba2016_modelski_ad100_200')['status'].startswith('exposed_')
        detail.locator('summary').scroll_into_view_if_needed();page.screenshot(path=str(a.out/'transfer_desktop.png'))
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for width in [344,390]:
                page.set_viewport_size(dict(width=width,height=844))
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert page.locator('#institution-scope').count()==1 and page.locator('#settlement-service-capacity').count()==1
        assert page.locator('#rows tr').count()==40
        browser.close()
    assert not errors and not bad,(errors,bad)
    (a.out/'checks.json').write_text(json.dumps(dict(status='passed',default_collapsed=True,keyboard_open=True,
        rows=6,byte_exact_local_downloads=links,images_loaded=2,failed_verdict_explicit=True,
        light_dark_mobile_widths=[344,390],previous_panels_and_inventory_retained=True,page_errors=errors,failed_requests=bad),indent=2)+'\n')
    print('Transfer browser: failed verdict, six rows, nine exact local links, figures, desktop/mobile/dark passed.')


if __name__=='__main__':main()
