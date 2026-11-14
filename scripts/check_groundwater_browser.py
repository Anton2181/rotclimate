"""Check published synthetic groundwater numbers, downloads and navigation."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin,urlsplit

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/paid_groundwater_20261114/browser'


def main(base):
    OUT.mkdir(parents=True,exist_ok=True)
    r=json.loads((ROOT/'output/paid_groundwater_20261114/results.json').read_text())
    labels={'groundwater_disabled':'Groundwater disabled','stored_no_permission':'Stored, no upward permission','finite_groundwater':'Finite groundwater transfer'}
    keys=['recharge_mm','capillary_mm','final_aquifer_mm','root_uptake_mm','root_potential_mm','river_delivered_m3']
    wanted=[[labels[row['case']],*[format(row[key],'.3f') for key in keys]] for row in r['demonstrations']]
    errors=[];checks=[];target=base+'/atlases/earth_evidence/groundwater_budget/'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in [344,390,1440]:
            for theme in ['light','dark']:
                page=browser.new_page(viewport=dict(width=width,height=1000),color_scheme=theme)
                page.on('pageerror',lambda error:errors.append(str(error)))
                assert page.goto(target,wait_until='networkidle').status==200
                assert page.locator('h1').inner_text()=='Groundwater transfer spends finite, paid storage'
                assert page.locator('#demos tbody tr').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==wanted
                text=page.locator('body').inner_text()
                assert 'No Earth groundwater fields are scored' in text and 'Egypt calibration still fails' in text
                assert '40 m³ of extra river delivery' in text and 'below wilting point' in text
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('img').evaluate('(img)=>img.complete&&img.naturalWidth>0')
                page.keyboard.press('Tab');assert page.locator('nav a').first.evaluate('(a)=>a===document.activeElement')
                links=page.locator('a[download]').all();assert len(links)==8
                for a in links:
                    url=urljoin(target,a.get_attribute('href'));response=page.request.get(url);assert response.ok,url
                    assert hashlib.sha256(response.body()).digest()==hashlib.sha256((ROOT/urlsplit(url).path.lstrip('/')).read_bytes()).digest(),url
                with page.expect_download() as download:page.locator('a[href="demonstrations.csv"]').click()
                assert Path(download.value.path()).read_bytes()==(ROOT/'atlases/earth_evidence/groundwater_budget/demonstrations.csv').read_bytes()
                page.screenshot(path=str(OUT/f'{width}_{theme}.png'),full_page=True)
                checks.append(dict(width=width,theme=theme,numeric_rows=3,download_hashes=8,actual_csv_download=True,no_page_overflow=True,keyboard_focus=True));page.close()
        page=browser.new_page()
        for path,selector in [('/atlases/','a[href="earth_evidence/groundwater_budget/"]'),('/atlases/earth_evidence/','#groundwater-budget a')]:
            page.goto(base+path,wait_until='networkidle');page.locator(selector).click();page.wait_for_url(target)
        page.goto(target)
        for link in page.locator('nav a').all():assert page.request.get(urljoin(target,link.get_attribute('href'))).ok
        browser.close()
    assert not errors,errors
    (OUT/'browser.json').write_text(json.dumps(dict(status='passed',checks=checks,page_errors=errors,hub_and_evidence_navigation=True,return_links=True),indent=2)+'\n')
    print('Passed six viewport/theme cases,three numeric rows,eight downloads and navigation')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',default='http://127.0.0.1:8766')
    main(parser.parse_args().base.rstrip('/'))
