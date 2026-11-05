"""Check evidence filters, empirical result labels, local links and failure UI."""
from pathlib import Path
import argparse
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',default='http://127.0.0.1:8766');ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    ledger=json.loads((ROOT/'atlases/earth_evidence/data/ledger.json').read_text());checks=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1100));errors=[];bad=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:bad.append(r.url) if r.status>=400 else None)
        page.goto(a.base+'/atlases/',wait_until='domcontentloaded');page.click('a[href="earth_evidence/"]');page.wait_for_function('document.querySelector("#rows").children.length===40')
        assert page.locator('#count').inner_text()==str(len(ledger['parameters']))+' matching numeric records'
        assert page.locator('#benchmark').inner_text().find('0.459')>=0 and '0.176' in page.locator('#benchmark').inner_text()
        assert 'full split failed' in page.locator('body').inner_text().lower()
        assert 'no eligible case passes' in page.locator('body').inner_text().lower()
        for component in ledger['components']:
            page.select_option('#component',component['id']);assert page.locator('#count').inner_text().startswith(str(sum(r['component']==component['id'] for r in ledger['parameters']))+' ')
        page.select_option('#component','labour');page.select_option('#status','scenario');page.fill('#search','worker_fraction')
        assert page.locator('#rows tr').count()==1 and '0.4' in page.locator('#rows').inner_text()
        page.select_option('#component','');page.select_option('#status','');page.fill('#search','')
        page.click('#next');assert page.locator('#page').inner_text()=='41–80';page.click('#previous');assert page.locator('#page').inner_text()=='1–40'
        with page.expect_download() as event:page.click('a[href="data/parameters.csv"]')
        assert Path(event.value.path()).read_bytes()==(ROOT/'atlases/earth_evidence/data/parameters.csv').read_bytes()
        assert page.request.get(a.base+'/reports/EARTH_COMPONENT_CALIBRATION_20261105.md').ok
        page.screenshot(path=str(a.out/'earth_evidence_desktop.png'),full_page=True)
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme);page.set_viewport_size(dict(width=390,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(a.out/('earth_evidence_mobile_'+theme+'.png')))
        assert not errors and not bad,(errors,bad);checks.append(dict(filters='11 components and evidence/search',pagination=True,download_exact=True,mobile_and_dark=True,page_errors=errors,failed_requests=bad));page.close()
        page=browser.new_page();page.route('**/earth_evidence/data/ledger.json',lambda r:r.fulfill(status=404,body='missing'))
        page.goto(a.base+'/atlases/earth_evidence/',wait_until='domcontentloaded');page.wait_for_function('document.querySelector("#count").textContent.includes("Detailed inventory unavailable")');assert page.locator('#benchmark').is_visible();checks.append(dict(optional_ledger_failure_visible=True,static_results_retained=True));page.close();browser.close()
    (a.out/'review.json').write_text(json.dumps(dict(status='passed',checks=checks),indent=2)+'\n');print(json.dumps(checks,indent=2))


if __name__=='__main__':main()
