"""Verify source hydraulic tables, published endpoints, downloads and navigation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin,urlsplit

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/capillary_hydraulics_20261114/browser'


def main(base):
    OUT.mkdir(parents=True,exist_ok=True)
    r=json.loads((ROOT/'output/capillary_hydraulics_20261114/reference.json').read_text())
    with (ROOT/'output/capillary_hydraulics_20261114/benchmarks.csv').open() as file:rows=list(csv.DictReader(file))
    endpoints=[]
    for flux in r['fluxes_mm_day']:
        values=[v for v in rows if float(v['flux_mm_day'])==flux];last=values[-1]
        endpoints.append([format(flux,'g'),last['source_z_text'],format(float(last['model_z_cm']),'.6f'),format(float(last['error_cm']),'+.6f'),str(sum(int(v['within_rounding']) for v in values))+' / 41'])
    soils=[[v['code'],*[str(v[key]) for key in ['theta_residual','theta_saturated','ksat_cm_day','alpha_cm_inv','connectivity','n']]] for v in r['soil_parameters_table_a5_4']]
    errors=[];checks=[];target=base+'/atlases/earth_evidence/capillary/'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in [344,390,1440]:
            for theme in ['light','dark']:
                page=browser.new_page(viewport=dict(width=width,height=1000),color_scheme=theme)
                page.on('pageerror',lambda error:errors.append(str(error)))
                assert page.goto(target,wait_until='networkidle').status==200
                assert page.locator('h1').inner_text()=='Capillary hydraulics matches the published example'
                for selector,wanted in [('#endpoints tbody tr',endpoints),('#soils tbody tr',soils)]:
                    assert page.locator(selector).evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==wanted
                text=page.locator('body').inner_text()
                assert 'It supplies no groundwater' in text and 'summer description' in text and 'Egypt calibration still fails' in text
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('img').evaluate('(img)=>img.complete&&img.naturalWidth>0')
                page.keyboard.press('Tab');assert page.locator('nav a').first.evaluate('(a)=>a===document.activeElement')
                links=page.locator('a[download]').all();assert len(links)==7
                for a in links:
                    url=urljoin(target,a.get_attribute('href'));response=page.request.get(url);assert response.ok,url
                    assert hashlib.sha256(response.body()).digest()==hashlib.sha256((ROOT/urlsplit(url).path.lstrip('/')).read_bytes()).digest(),url
                with page.expect_download() as download:page.locator('a[href="benchmarks.csv"]').click()
                assert Path(download.value.path()).read_bytes()==(ROOT/'atlases/earth_evidence/capillary/benchmarks.csv').read_bytes()
                page.screenshot(path=str(OUT/f'{width}_{theme}.png'),full_page=True)
                checks.append(dict(width=width,theme=theme,numeric_rows=34,download_hashes=7,actual_csv_download=True,no_page_overflow=True,keyboard_focus=True));page.close()
        page=browser.new_page()
        for path,selector in [('/atlases/','a[href="earth_evidence/capillary/"]'),('/atlases/earth_evidence/','#capillary-hydraulics a')]:
            page.goto(base+path,wait_until='networkidle');page.locator(selector).click();page.wait_for_url(target)
        page.goto(target)
        for link in page.locator('nav a').all():assert page.request.get(urljoin(target,link.get_attribute('href'))).ok
        browser.close()
    assert not errors,errors
    (OUT/'browser.json').write_text(json.dumps(dict(status='passed',checks=checks,page_errors=errors,hub_and_evidence_navigation=True,return_links=True),indent=2)+'\n')
    print('Passed six viewport/theme cases,34numeric source/endpoint rows,seven downloads and navigation')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',default='http://127.0.0.1:8766')
    main(parser.parse_args().base.rstrip('/'))
