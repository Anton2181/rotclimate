"""Check source-context tables, benchmark cells and served component downloads."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin,urlsplit

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/crop_stage_20261114/browser'


def main(base):
    OUT.mkdir(parents=True,exist_ok=True)
    r=json.loads((ROOT/'output/crop_stage_20261114/reference.json').read_text())
    expected={
        'points':[[str(v['day']),v['published'],f"{v['value']:.6f}"] for v in r['example30']['points']],
        'stages':[[v['crop'],' / '.join(map(str,v['stage_days'])),str(v['total_days']),v['planting'],v['region'] or 'Unspecified in row'] for v in r['table11']],
        'coefficients':[[v['crop'],v['kcb_initial_text']+(' (cereal heading)' if v['initial_inherited_from_cereals'] else ''),v['kcb_mid_text'],v['kcb_end_text']] for v in r['table17']],
    }
    target=base+'/atlases/earth_evidence/crop_stage/'
    errors=[];checks=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in [344,390,1440]:
            for theme in ['light','dark']:
                page=browser.new_page(viewport=dict(width=width,height=1000),color_scheme=theme)
                page.on('pageerror',lambda error:errors.append(str(error)))
                assert page.goto(target,wait_until='networkidle').status==200
                for name,wanted in expected.items():
                    assert page.locator('#'+name+' tbody tr').evaluate_all('(rows)=>rows.map(r=>Array.from(r.cells,c=>c.textContent))')==wanted
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('img').evaluate('(im)=>im.complete&&im.naturalWidth>0')
                text=page.locator('body').inner_text()
                assert 'residual diffusion' in text and 'not adopted for Nile barley' in text
                assert 'Egypt calibration still fails' in text
                page.keyboard.press('Tab')
                assert page.locator('nav a').first.evaluate('(a)=>a===document.activeElement')
                links=page.locator('a[download]').all();assert len(links)==5
                for a in links:
                    url=urljoin(target,a.get_attribute('href'));response=page.request.get(url);assert response.ok,url
                    assert hashlib.sha256(response.body()).digest()==hashlib.sha256((ROOT/urlsplit(url).path.lstrip('/')).read_bytes()).digest(),url
                with page.expect_download() as download:page.locator('a[href="intervals.csv"]').click()
                assert Path(download.value.path()).read_bytes()==(ROOT/'atlases/earth_evidence/crop_stage/intervals.csv').read_bytes()
                page.screenshot(path=str(OUT/f'{width}_{theme}.png'),full_page=True)
                checks.append(dict(width=width,theme=theme,displayed_rows=18,download_hashes=5,actual_csv_download=True,no_page_overflow=True,keyboard_focus=True));page.close()
        page=browser.new_page()
        for path,selector in [('/atlases/','a[href="earth_evidence/crop_stage/"]'),('/atlases/earth_evidence/','#crop-stage-component a')]:
            page.goto(base+path,wait_until='networkidle');page.locator(selector).click();page.wait_for_url(target)
        page.goto(target)
        for link in page.locator('nav a').all():assert page.request.get(urljoin(target,link.get_attribute('href'))).ok
        browser.close()
    assert not errors,errors
    (OUT/'browser.json').write_text(json.dumps(dict(status='passed',checks=checks,page_errors=errors,hub_and_evidence_navigation=True,return_links=True),indent=2)+'\n')
    print('Passed six viewport/theme cases, 18 source/benchmark rows, five downloads and navigation')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',default='http://127.0.0.1:8766')
    main(parser.parse_args().base.rstrip('/'))
