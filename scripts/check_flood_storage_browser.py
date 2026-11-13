"""Check scenario values/filtering, mobile themes, keyboard and real downloads."""
import argparse,hashlib,json
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/flood_basin_storage_20261114/browser'


def main(base):
    OUT.mkdir(parents=True,exist_ok=True);checks=[];errors=[];target=base+'/atlases/earth_evidence/flood_storage/'
    r=json.loads((ROOT/'output/flood_basin_storage_20261114/results.json').read_text())
    labels={'nile':'Nile','mesopotamia_euphrates_only':'Mesopotamia · Euphrates only'}
    expected=[[labels[v['region']],v['crop'],str(v['capacity_mm']),str(v['bare_ET_fraction']),f'{v["efficiency"]:g}','Rain only' if v['capture']=='none' else 'Aug–Oct capture',f'{100*v["mean_crop_ET_coverage"]:.1f}%',f'{v["adequate_area_km2"]:,.0f}',f'{v["delivered_m3"]/1e9:.3f}',f'{v["loss_m3"]/1e9:.3f}'] for v in r['rows']]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in (344,390,1440):
            for theme in ('light','dark'):
                page=browser.new_page(viewport=dict(width=width,height=1000),color_scheme=theme);page.on('pageerror',lambda e:errors.append(str(e)))
                response=page.goto(target,wait_until='networkidle');assert response.status==200
                assert page.locator('h1').inner_text()=='Floodwater must survive until the crop needs it'
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,theme)
                assert page.locator('tbody tr').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==expected
                for image in page.locator('img').all():assert image.evaluate('(im)=>im.complete&&im.naturalWidth>0')
                page.keyboard.press('Tab');assert page.locator('nav a').first.evaluate('(a)=>a===document.activeElement')
                for region in ('','nile','mesopotamia_euphrates_only'):
                    for crop in ('','barley','wheat'):
                        page.select_option('#region',region);page.select_option('#crop',crop)
                        count=sum((not region or v['region']==region) and (not crop or v['crop']==crop) for v in r['rows'])
                        assert page.locator('#count').inner_text()==f'{count} scenarios'
                        assert page.locator('tbody tr:not([hidden])').count()==count
                page.select_option('#region','');page.select_option('#crop','')
                links=page.locator('a[download]').all()
                for a in links:
                    url=urljoin(target,a.get_attribute('href'));reply=page.request.get(url);assert reply.ok,url
                    assert hashlib.sha256(reply.body()).hexdigest()==hashlib.sha256((ROOT/urlsplit(url).path.lstrip('/')).read_bytes()).hexdigest(),url
                with page.expect_download() as d:page.locator('a[href="fields.csv.gz"]').click()
                actual=d.value;assert actual.suggested_filename=='fields.csv.gz'
                assert Path(actual.path()).read_bytes()==(ROOT/'atlases/earth_evidence/flood_storage/fields.csv.gz').read_bytes()
                page.screenshot(path=str(OUT/f'{width}_{theme}.png'),full_page=True)
                checks.append(dict(width=width,theme=theme,numeric_rows=96,filter_combinations=9,download_hashes=len(links),keyboard_focus=True,no_page_overflow=True));page.close()
        page=browser.new_page()
        for path,selector in [('/atlases/','a[href="earth_evidence/flood_storage/"]'),('/atlases/earth_evidence/','#flood-storage-feasibility a')]:
            page.goto(base+path,wait_until='networkidle');page.locator(selector).click();page.wait_for_url(target)
        page.goto(target)
        for a in page.locator('nav a').all():assert page.request.get(urljoin(target,a.get_attribute('href'))).ok
        browser.close()
    assert not errors,errors
    result=dict(status='passed',checks=checks,hub_and_evidence_navigation=True,return_links=True,page_errors=errors)
    (OUT/'browser.json').write_text(json.dumps(result,indent=2)+'\n');print('Passed:6 viewport/theme cases,96 numeric rows,54 filter combinations,download hashes and navigation')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:8766');main(p.parse_args().base.rstrip('/'))
