"""Repeatable mobile/theme, keyboard, evidence-link and download checks."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/flood_basin_seasonality_20261113/browser'


def main(base):
    OUT.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
    target=base+'/atlases/earth_evidence/flood_basin/'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in (344,390,1440):
            for theme in ('light','dark'):
                page=browser.new_page(viewport=dict(width=width,height=1000),color_scheme=theme)
                page.on('pageerror',lambda e:errors.append(str(e)))
                response=page.goto(target,wait_until='networkidle');assert response.status==200
                assert page.locator('h1').inner_text()=='Can flood timing distinguish the Nile from Mesopotamia?'
                assert 'Unscored' in page.locator('table').inner_text()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,theme)
                assert page.locator('img').evaluate('(img)=>img.complete && img.naturalWidth>0')
                page.keyboard.press('Tab');assert page.locator('nav a').first.evaluate('(a)=>a===document.activeElement')
                assert page.locator('nav a').first.evaluate('(a)=>getComputedStyle(a).outlineStyle')!='none'
                links=page.locator('a[download]');count=links.count()
                for i in range(count):
                    url=urljoin(target,links.nth(i).get_attribute('href'));response=page.request.get(url);assert response.ok,url
                    local=ROOT/urlsplit(url).path.lstrip('/')
                    assert hashlib.sha256(response.body()).hexdigest()==hashlib.sha256(local.read_bytes()).hexdigest(),url
                with page.expect_download() as download:links.filter(has_text='phase.csv').click()
                actual=download.value;assert actual.suggested_filename=='phase.csv'
                assert Path(actual.path()).read_bytes()==(ROOT/'atlases/earth_evidence/flood_basin/phase.csv').read_bytes()
                page.screenshot(path=str(OUT/f'{width}_{theme}.png'),full_page=True)
                checks.append(dict(width=width,theme=theme,download_hashes=count,keyboard_focus=True,no_page_overflow=True));page.close()
        page=browser.new_page()
        for path,selector in [('/atlases/','a[href="earth_evidence/flood_basin/"]'),('/atlases/earth_evidence/','#flood-basin-preflight a')]:
            page.goto(base+path,wait_until='networkidle');page.locator(selector).click();page.wait_for_url(target)
        for selector in ('a[href="../"]','a[href="../../"]','a[href="../../earth_fit/"]'):
            page.goto(target);url=urljoin(target,page.locator(selector).get_attribute('href'));assert page.request.get(url).ok
        browser.close()
    assert not errors,errors
    result=dict(status='passed',checks=checks,hub_and_evidence_navigation=True,return_links=True,page_errors=errors)
    (OUT/'browser.json').write_text(json.dumps(result,indent=2)+'\n');print('Browser checks passed:',len(checks),'viewports/themes')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',default='http://127.0.0.1:8766');main(parser.parse_args().base.rstrip('/'))
