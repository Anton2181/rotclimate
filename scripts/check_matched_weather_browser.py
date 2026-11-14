"""Verify matched-weather maps, all case numbers, filters and downloads."""
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
OUT=ROOT/'output/matched_regional_fields_20261114/browser'


def main(base):
    OUT.mkdir(parents=True,exist_ok=True)
    r=json.loads((ROOT/'output/matched_regional_fields_20261114/results.json').read_text())
    regions={'nile':'Nile','mesopotamia_euphrates_only':'Euphrates only'};methods={'hargreaves':'Hargreaves','penman_monteith':'Penman–Monteith'}
    met={'eto_only':'Archived T/P + modern ETo','matched':'Matched modern T/P/ETo'}
    wanted=[[regions[a['region']],'5-bin' if a['calendar']=='old' else '4-bin fractional','Capture' if a['capture'] else 'Rain only',methods[a['method']],met[a['meteorology']],format(100*a['root_coverage'],'.2f')+'%',format(a['eligible_area_km2'],',.0f'),format(a['adequate_root_area_km2'],',.0f'),format(a['delivered_m3']/1e9,'.3f'),str(a['spinup_years'])] for a in r['rows']]
    errors=[];checks=[];target=base+'/atlases/earth_evidence/matched_weather/'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in [344,390,1440]:
            for theme in ['light','dark']:
                page=browser.new_page(viewport=dict(width=width,height=1000),color_scheme=theme)
                page.on('pageerror',lambda error:errors.append(str(error)))
                assert page.goto(target,wait_until='networkidle').status==200
                assert page.locator('h1').inner_text()=='Temperature, rain and evaporation now share a weather period'
                assert page.locator('#cases tbody tr').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==wanted
                assert 'No settlement update is adopted' in page.locator('body').inner_text()
                assert 'Egypt calibration still fails' in page.locator('body').inner_text()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('img').count()==2
                for im in page.locator('img').all():assert im.evaluate('(img)=>img.complete&&img.naturalWidth>0')
                page.keyboard.press('Tab');assert page.locator('nav a').first.evaluate('(a)=>a===document.activeElement')
                for region,method in itertools.product(['',*regions],['',*methods]):
                    page.select_option('#region',region);page.select_option('#method',method)
                    count=sum((not region or a['region']==region) and (not method or a['method']==method) for a in r['rows'])
                    assert page.locator('#cases tbody tr:visible').count()==count
                    assert page.locator('#count').inner_text()==str(count)+' scenarios'
                page.select_option('#region','');page.select_option('#method','')
                links=page.locator('a[download]').all();assert len(links)==14
                for a in links:
                    url=urljoin(target,a.get_attribute('href'));response=page.request.get(url);assert response.ok,url
                    assert hashlib.sha256(response.body()).digest()==hashlib.sha256((ROOT/urlsplit(url).path.lstrip('/')).read_bytes()).digest(),url
                with page.expect_download() as download:page.locator('a[href="bins.csv"]').click()
                assert Path(download.value.path()).read_bytes()==(ROOT/'atlases/earth_evidence/matched_weather/bins.csv').read_bytes()
                response=page.request.get(target+'weather_sources.zip')
                with zipfile.ZipFile(io.BytesIO(response.body())) as archive:
                    assert len(archive.namelist())==31
                    for name in archive.namelist():assert archive.read(name)==(ROOT/'data/source/matched_regional_weather_20261114'/name).read_bytes()
                page.screenshot(path=str(OUT/f'{width}_{theme}.png'),full_page=True)
                checks.append(dict(width=width,theme=theme,numeric_rows=32,filter_combinations=9,download_hashes=14,source_zip_members=31,actual_csv_download=True,no_page_overflow=True,keyboard_focus=True));page.close()
        page=browser.new_page()
        for path,selector in [('/atlases/','a[href="earth_evidence/matched_weather/"]'),('/atlases/earth_evidence/','#matched-weather-fields a')]:
            page.goto(base+path,wait_until='networkidle');page.locator(selector).click();page.wait_for_url(target)
        page.goto(target)
        for link in page.locator('nav a').all():assert page.request.get(urljoin(target,link.get_attribute('href'))).ok
        browser.close()
    assert not errors,errors
    (OUT/'browser.json').write_text(json.dumps(dict(status='passed',checks=checks,page_errors=errors,hub_and_evidence_navigation=True,return_links=True),indent=2)+'\n')
    print('Passed six viewport/theme cases,32numeric rows,54filter cases,14downloads,31source ZIP members and navigation')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',default='http://127.0.0.1:8766')
    main(parser.parse_args().base.rstrip('/'))
