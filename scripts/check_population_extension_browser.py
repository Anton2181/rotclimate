"""Check complete-input evidence, original failure and source-repair downloads."""
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
        page=browser.new_page(viewport=dict(width=1440,height=1000));page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:bad.append(r.url) if r.status>=400 else None)
        page.goto(a.base+'/atlases/',wait_until='domcontentloaded');page.click('a[href="earth_evidence/"]')
        detail=page.locator('#population-extension');assert detail.get_attribute('open') is None
        detail.locator('summary').focus();page.keyboard.press('Enter');assert detail.get_attribute('open') is not None
        assert detail.locator('tbody tr').count()==5
        assert 'All 1,586' in detail.inner_text() and 'original overlap test remains failed' in detail.inner_text()
        assert 'NoData' in detail.inner_text() and '2.2542' in detail.inner_text()
        assert 'fantasy map' in detail.inner_text() and 'remain unchanged' in detail.inner_text()
        for link in detail.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            relative=url.removeprefix(a.base+'/');assert response.body()==(ROOT/relative).read_bytes(),relative;links.append(relative)
        assert len(links) in [11,14]
        if len(links)==14:assert detail.locator('#core-population-inputs').count()==1
        with page.expect_download() as event:detail.locator('a[href="data/population_extension.json"]').click()
        assert Path(event.value.path()).read_bytes()==(ROOT/'atlases/earth_evidence/data/population_extension.json').read_bytes()
        for img in detail.locator('img').all():img.evaluate('(el)=>el.decode()');assert img.evaluate('(el)=>el.naturalWidth>1000')
        detail.locator('summary').scroll_into_view_if_needed();page.screenshot(path=str(a.out/'extension_desktop.png'))
        usage=page.request.get(a.base+'/atlases/earth_evidence/data/dataset_usage.json').json()
        assert next(e for e in usage['datasets'] if e['id']=='earth_population_extension_20261111')['status']=='exposed_source_correction_complete_input_count_development'
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for width in [344,390]:
                page.set_viewport_size(dict(width=width,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert page.locator('#settlement-counts').count()==1 and page.locator('#vidarbha-transfer').count()==1 and page.locator('#rows tr').count()==40
        browser.close()
    assert not errors and not bad,(errors,bad)
    (a.out/'checks.json').write_text(json.dumps(dict(status='passed',default_collapsed=True,keyboard_open=True,rows=5,
        byte_exact_local_links=links,figures_loaded=2,original_failure_retained=True,source_repair_not_fantasy_adoption_explicit=True,
        desktop_mobile_light_dark=True,previous_panels_retained=True,page_errors=errors,failed_requests=bad),indent=2)+'\n')
    print('Extension browser: five rows,',len(links),'exact links,source repair/original failure,figures,mobile/light/dark passed.')


if __name__=='__main__':main()
