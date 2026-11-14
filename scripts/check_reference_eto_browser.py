"""Verify every published ETo cell, filter, source download and navigation."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
from urllib.parse import urljoin,urlsplit

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/reference_eto_20261114/browser'


def main(base):
    OUT.mkdir(parents=True,exist_ok=True)
    result=json.loads((ROOT/'output/reference_eto_20261114/results.json').read_text())
    labels={'cairo':'Cairo','aswan':'Aswan','hit':'Hit · Euphrates'}
    annual=[]
    for row in result['summaries']:
        annual.append([labels[row['site']],*[format(row[name],',.0f') for name in ['pm_mean_annual_mm','hargreaves_mean_annual_mm','atlas_style_mean_annual_mm']],format(100*row['hargreaves_over_pm'],'.1f')+'%',format(100*row['nov_mar']['hargreaves_over_pm'],'.1f')+'%',str(row['valid_days']),str(row['cloud_ratio_clipped_days'])])
    monthly=[]
    for row in result['climatology']:
        monthly.append([labels[row['site']],str(row['month']),*[format(row[name],'.3f') for name in ['pm_mean_mm_day','hargreaves_mean_mm_day','atlas_style_hargreaves_mm_day','bias_mm_day','aggregation_effect_mm_day','geometry_effect_mm_day']]])
    errors=[];checks=[];target=base+'/atlases/earth_evidence/reference_eto/'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in [344,390,1440]:
            for theme in ['light','dark']:
                page=browser.new_page(viewport=dict(width=width,height=1000),color_scheme=theme)
                page.on('pageerror',lambda error:errors.append(str(error)))
                assert page.goto(target,wait_until='networkidle').status==200
                assert page.locator('h1').inner_text()=='Two reference methods diverge on the same weather'
                assert page.locator('#annual tbody tr').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==annual
                assert page.locator('#climate tbody tr').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==monthly
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('img').evaluate('(img)=>img.complete&&img.naturalWidth>0')
                text=page.locator('body').inner_text()
                assert 'not station observations or ancient weather' in text and 'Egypt calibration still fails' in text
                page.keyboard.press('Tab')
                assert page.locator('nav a').first.evaluate('(a)=>a===document.activeElement')
                combinations=0
                for site,month in itertools.product(['',*labels],['',*[str(m) for m in range(1,13)]]):
                    page.locator('#site').select_option(site);page.locator('#month').select_option(month)
                    wanted=[monthly[i] for i,row in enumerate(result['climatology']) if (not site or row['site']==site) and (not month or str(row['month'])==month)]
                    assert page.locator('#count').inner_text()==f'{len(wanted)} location-months'
                    assert page.locator('#climate tbody tr:not([hidden])').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==wanted
                    combinations+=1
                page.locator('#site').select_option('');page.locator('#month').select_option('')
                links=page.locator('a[download]').all();assert len(links)==10
                for a in links:
                    url=urljoin(target,a.get_attribute('href'));response=page.request.get(url);assert response.ok,url
                    assert hashlib.sha256(response.body()).digest()==hashlib.sha256((ROOT/urlsplit(url).path.lstrip('/')).read_bytes()).digest(),url
                with page.expect_download() as download:page.locator('a[href="daily.csv"]').click()
                assert Path(download.value.path()).read_bytes()==(ROOT/'atlases/earth_evidence/reference_eto/daily.csv').read_bytes()
                page.screenshot(path=str(OUT/f'{width}_{theme}.png'),full_page=True)
                checks.append(dict(width=width,theme=theme,numeric_rows=39,filter_combinations=combinations,download_hashes=10,actual_daily_csv_download=True,no_page_overflow=True,keyboard_focus=True));page.close()
        page=browser.new_page()
        for path,selector in [('/atlases/','a[href="earth_evidence/reference_eto/"]'),('/atlases/earth_evidence/','#reference-eto-audit a')]:
            page.goto(base+path,wait_until='networkidle');page.locator(selector).click();page.wait_for_url(target)
        page.goto(target)
        for a in page.locator('nav a').all():assert page.request.get(urljoin(target,a.get_attribute('href'))).ok
        browser.close()
    assert not errors,errors
    (OUT/'browser.json').write_text(json.dumps(dict(status='passed',checks=checks,page_errors=errors,hub_and_evidence_navigation=True,return_links=True),indent=2)+'\n')
    print('Passed six viewport/theme cases,39numeric rows,312filter combinations,10downloads and navigation')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',default='http://127.0.0.1:8766')
    main(parser.parse_args().base.rstrip('/'))
