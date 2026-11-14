"""Check paired maps, every displayed number, filters and complete downloads."""
import argparse
import hashlib
import io
import itertools
import json
from pathlib import Path
from urllib.parse import urljoin,urlsplit
import zipfile

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/regional_reference_forcing_20261114/browser'


def main(base):
    OUT.mkdir(parents=True,exist_ok=True)
    result=json.loads((ROOT/'output/regional_reference_forcing_20261114/results.json').read_text())
    weather=json.loads((ROOT/'output/regional_reference_forcing_20261114/weather.json').read_text())
    regions={'nile':'Nile','mesopotamia_euphrates_only':'Mesopotamia · Euphrates only'}
    forcings={'legacy_archive':'Archived forcing','power_hargreaves':'Regional Hargreaves','power_penman_monteith':'Regional Penman–Monteith'}
    expected=[]
    for row in result['rows']:
        expected.append([regions[row['region']],'5-bin' if row['calendar']=='old' else '4-bin fractional','Capture' if row['capture'] else 'Rain only',forcings[row['forcing']],format(100*row['root_coverage'],'.2f')+'%',format(row['eligible_area_km2'],',.0f'),format(row['adequate_root_area_km2'],',.0f'),format(row['delivered_m3']/1e9,'.3f'),format(row['pond_evap_m3']/1e9,'.3f'),str(row['spinup_years'])])
    coverage=[]
    for region,row in weather['regions'].items():
        coverage.append([regions[region],str(row['candidate_fields']),str(row['weather_cells']),format(row['area_weighted_distance_km'],'.2f'),format(row['maximum_distance_km'],'.2f'),*[format(row[name],',.1f') for name in ['legacy_area_weighted_annual_eto_mm','power_hargreaves_area_weighted_annual_eto_mm','power_penman_monteith_area_weighted_annual_eto_mm']]])
    source=json.loads((ROOT/'data/source/regional_reference_forcing_20261114/sources.json').read_text())
    errors=[];checks=[];target=base+'/atlases/earth_evidence/regional_forcing/'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in [344,390,1440]:
            for theme in ['light','dark']:
                page=browser.new_page(viewport=dict(width=width,height=1000),color_scheme=theme)
                page.on('pageerror',lambda error:errors.append(str(error)))
                assert page.goto(target,wait_until='networkidle').status==200
                assert page.locator('h1').inner_text()=='Regional evaporation forcing changes the field-water result'
                assert page.locator('#cases tbody tr').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==expected
                assert page.locator('#coverage tbody tr').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==coverage
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                for img in page.locator('img').all():assert img.evaluate('(img)=>img.complete&&img.naturalWidth>0')
                text=page.locator('body').inner_text()
                assert 'period/input mismatch' in text and 'Tigris is absent' in text and 'Egypt calibration still fails' in text
                page.keyboard.press('Tab');assert page.locator('nav a').first.evaluate('(a)=>a===document.activeElement')
                combinations=0
                for region,calendar,access in itertools.product(['',*regions],['','old','fractional'],['','0','1']):
                    for key,value in [('region',region),('calendar',calendar),('access',access)]:page.locator('#'+key).select_option(value)
                    wanted=[expected[i] for i,row in enumerate(result['rows']) if (not region or row['region']==region) and (not calendar or row['calendar']==calendar) and (not access or int(row['capture'])==int(access))]
                    assert page.locator('#count').inner_text()==f'{len(wanted)} scenarios'
                    assert page.locator('#cases tbody tr:not([hidden])').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==wanted
                    combinations+=1
                for key in ['region','calendar','access']:page.locator('#'+key).select_option('')
                links=page.locator('a[download]').all();assert len(links)==14
                for a in links:
                    url=urljoin(target,a.get_attribute('href'));response=page.request.get(url);assert response.ok,url
                    assert hashlib.sha256(response.body()).digest()==hashlib.sha256((ROOT/urlsplit(url).path.lstrip('/')).read_bytes()).digest(),url
                    if a.get_attribute('href')=='weather_sources.zip':
                        with zipfile.ZipFile(io.BytesIO(response.body())) as archive:
                            assert set(archive.namelist())=={'sources.json',*[Path(v['file']).name for v in source['sources']]}
                            for v in source['sources']:assert hashlib.sha256(archive.read(Path(v['file']).name)).hexdigest()==v['sha256']
                with page.expect_download() as download:page.locator('a[href="fields.csv.gz"]').click()
                assert Path(download.value.path()).read_bytes()==(ROOT/'atlases/earth_evidence/regional_forcing/fields.csv.gz').read_bytes()
                page.screenshot(path=str(OUT/f'{width}_{theme}.png'),full_page=True)
                checks.append(dict(width=width,theme=theme,numeric_rows=26,filter_combinations=combinations,download_hashes=14,raw_source_zip_members=31,actual_field_csv_download=True,no_page_overflow=True,keyboard_focus=True));page.close()
        page=browser.new_page()
        for path,selector in [('/atlases/','a[href="earth_evidence/regional_forcing/"]'),('/atlases/earth_evidence/','#regional-reference-forcing a')]:
            page.goto(base+path,wait_until='networkidle');page.locator(selector).click();page.wait_for_url(target)
        page.goto(target)
        for link in page.locator('nav a').all():assert page.request.get(urljoin(target,link.get_attribute('href'))).ok
        browser.close()
    assert not errors,errors
    (OUT/'browser.json').write_text(json.dumps(dict(status='passed',checks=checks,page_errors=errors,hub_and_evidence_navigation=True,return_links=True),indent=2)+'\n')
    print('Passed six viewport/theme cases,26numeric rows,162filter combinations,14downloads,31source ZIP members and navigation')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',default='http://127.0.0.1:8766')
    main(parser.parse_args().base.rstrip('/'))
