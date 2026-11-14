"""Verify source/model tables, clock metrics, downloads and responsive navigation."""
import argparse,csv,hashlib,json
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/soil_drying_20261114/browser'


def main(base):
    OUT.mkdir(parents=True,exist_ok=True);checks=[];errors=[];target=base+'/atlases/earth_evidence/soil_drying/'
    result=json.loads((ROOT/'output/soil_drying_20261114/results.json').read_text())
    with (ROOT/'output/soil_drying_20261114/benchmarks.csv').open() as f:rows=list(csv.DictReader(f))
    expected=[]
    for example,column in [(31,5),(37,6)]:
        for v in rows:
            if int(v['example'])==example and int(v['column'])==column:expected.append([v['day'],v['source_text'],f'{float(v["model_value"]):.6f}',f'{float(v["tolerance"]):.3g}'])
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in (344,390,1440):
            for theme in ('light','dark'):
                page=browser.new_page(viewport=dict(width=width,height=1000),color_scheme=theme);page.on('pageerror',lambda e:errors.append(str(e)))
                reply=page.goto(target,wait_until='networkidle');assert reply.status==200
                assert page.locator('h1').inner_text()=='Surface drying and root water share a finite supply'
                assert page.locator('tbody tr').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,c=>c.textContent))')==expected
                text=page.locator('body').inner_text();assert f"{result['clock']['steps']} segments" in text
                assert f"{result['clock']['capture_days']:.6f} days" in text and f"{result['clock']['crop_days']:.6f} days" in text
                assert 'No new Earth field, yield or population score' in text
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                for img in page.locator('img').all():assert img.evaluate('(im)=>im.complete&&im.naturalWidth>0')
                page.keyboard.press('Tab');assert page.locator('nav a').first.evaluate('(a)=>a===document.activeElement')
                links=page.locator('a[download]').all()
                for a in links:
                    url=urljoin(target,a.get_attribute('href'));response=page.request.get(url);assert response.ok
                    assert hashlib.sha256(response.body()).hexdigest()==hashlib.sha256((ROOT/urlsplit(url).path.lstrip('/')).read_bytes()).hexdigest(),url
                with page.expect_download() as download:page.locator('a[href="benchmarks.csv"]').click()
                actual=download.value;assert actual.suggested_filename=='benchmarks.csv'
                assert Path(actual.path()).read_bytes()==(ROOT/'atlases/earth_evidence/soil_drying/benchmarks.csv').read_bytes()
                page.screenshot(path=str(OUT/f'{width}_{theme}.png'),full_page=True)
                checks.append(dict(width=width,theme=theme,numeric_rows=20,clock_metrics=True,download_hashes=len(links),keyboard_focus=True,no_page_overflow=True));page.close()
        page=browser.new_page()
        for path,selector in [('/atlases/','a[href="earth_evidence/soil_drying/"]'),('/atlases/earth_evidence/','#soil-drying-components a')]:
            page.goto(base+path,wait_until='networkidle');page.locator(selector).click();page.wait_for_url(target)
        page.goto(target)
        for a in page.locator('nav a').all():assert page.request.get(urljoin(target,a.get_attribute('href'))).ok
        browser.close()
    assert not errors,errors
    (OUT/'browser.json').write_text(json.dumps(dict(status='passed',checks=checks,page_errors=errors,hub_and_evidence_navigation=True,return_links=True),indent=2)+'\n')
    print('Passed6viewport/theme cases,20numeric rows,clock metrics,9downloads and navigation')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',default='http://127.0.0.1:8766');main(parser.parse_args().base.rstrip('/'))
