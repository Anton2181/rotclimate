"""Check the existing map modes, joint ledgers, links and optional failures."""
from pathlib import Path
import argparse
import csv
import gzip
import json
import math
import numpy as np
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',default='http://127.0.0.1:8766');ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);reviews=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for name,mode in [('free_fit','raw'),('earth_fit','raw'),('earth_fit','corrected'),('whittaker_fit','raw')]:
            data=ROOT/'atlases'/name/'data';manifest=json.loads((data/'settled_reach.json').read_text());p=manifest['packets'][mode];model=json.loads(gzip.decompress((data/p['payload']).read_bytes()))
            url=a.base+'/atlases/'+name+'/#layer=reach_towns'+('&climate=raw' if mode=='raw' else '')
            page=browser.new_page(viewport=dict(width=1440,height=1100));errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url,wait_until='domcontentloaded');page.locator('#settled-readouts .readout').first.wait_for(timeout=90000)
            assert page.locator('#variant').input_value()=='joint365'
            assert not page.locator('#settlement-controls').is_visible()
            assert not page.locator('#coverage-baseline-note').is_visible()
            for layer in ['reach_towns','reach_defacto']:
                page.click('#layer-'+layer)
                for c in model['cases']:
                    page.select_option('#variant',c['id'])
                    page.wait_for_function('(id)=>document.querySelector("#settled-months").textContent.length>0 && document.querySelector("#base").complete && new URL(document.querySelector("#base").src).pathname.includes(id)',arg=('settled_towns_' if layer=='reach_towns' else 'settled_control_')+c['id'])
                    assert page.locator('#settled-section').is_visible()
                    assert not page.locator('#coverage-baseline-note').is_visible()
                    assert page.locator('#settled-months tr').count()==(12 if c['food_constrained'] else 1)
                page.select_option('#variant','legacy_0')
                assert not page.locator('#settled-section').is_visible()
                if layer=='reach_defacto':assert page.locator('#coverage-baseline-note').is_visible()
                page.select_option('#variant','joint365')
            # Values for imperial, nonimperial and unknown marked evidence.
            chosen=[next(s for s in model['sites'] if s['marked'] and (s['actor'] or '').startswith('Xšāça')),next(s for s in model['sites'] if s['marked'] and s['actor'] and not s['actor'].startswith('Xšāça')),next(s for s in model['sites'] if s['marked'] and not s['actor'])]
            count=0
            for s in chosen:
                page.select_option('#settled-site',s['id']);page.locator('#settled-readouts .readout').first.wait_for()
                with page.expect_download() as event:page.click('#settled-download')
                with Path(event.value.path()).open(encoding='utf-8') as f:records=list(csv.DictReader(f))
                assert len(records)==len(model['cases'])*12
                j=model['sites'].index(s)
                for record in records:
                    c=next(c for c in model['cases'] if c['id']==record['scenario']);t=int(record['seasonal_bin'])-1
                    assert record['site_id']==s['id'] and record['climate']==mode
                    for key in ['civilian_people','institutional_people']:assert math.isclose(float(record[key]),c[key][j],rel_tol=1e-10,abs_tol=1e-6)
                    if c['food_constrained']:
                        for key,field in [('arrivals_kcal','monthly_arrivals_kcal'),('need_kcal','monthly_need_kcal')]:assert math.isclose(float(record[key]),c[field][j][t],rel_tol=1e-10,abs_tol=1e-6)
                        assert math.isclose(float(record['end_stock_kcal']),c['stock_path_kcal'][j][t+1],rel_tol=1e-10,abs_tol=1e-6)
                    count+=1
            # Point readouts must reproduce the exact published actor masks,
            # including the unresolved marked site's geographic location.
            grid=gzip.decompress((data/p['binary']).read_bytes());size=int(np.prod(p['shape']))
            lookup=np.frombuffer(grid,'<u4',count=size);masks=np.frombuffer(grid,'<u2',offset=p['offsets']['masks']).reshape(p['masks_shape'])
            index=int(lookup[chosen[-1]['node']])-1
            for i,actor in enumerate(model['actors']):
                text=page.locator('#settled-cell tr').nth(i).locator('td').nth(1).inner_text()
                expected=str(int(masks[1,i,index]).bit_count())+' / 12' if model['summaries'][1]['actors'][i]['inventory_scored'] else 'Unscored'
                assert text==expected,(actor['name'],text,expected)
            assert 'settled_site='+chosen[-1]['id'] in page.url
            # A shared link keeps the site selection despite the default
            # climate-card selection during initialization.
            page.reload(wait_until='domcontentloaded');page.locator('#settled-readouts .readout').first.wait_for(timeout=90000)
            assert page.locator('#settled-site').input_value()==chosen[-1]['id']
            page.select_option('#variant','joint1');page.locator('#settled-readouts .readout').first.wait_for();page.locator('#settled-section').screenshot(path=str(a.out/(name+'_'+mode+'_ledger.png')))
            page.locator('.mapwrap').first.screenshot(path=str(a.out/(name+'_'+mode+'_map.png')))
            page.set_viewport_size(dict(width=390,height=844));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.set_viewport_size(dict(width=1440,height=1100));page.select_option('#map-topic','Overview');page.click('#layer-koppen');assert not page.locator('#settled-section').is_visible()
            assert not errors,errors
            reviews.append(dict(atlas=name,climate=mode,rows_checked=count,existing_modes_updated=True,legacy_and_share_link=True,mobile=True));page.close()
        # A wrong manifest must keep both original modes available.
        for failure in ['manifest','harvest_identity','grid','browser']:
            page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            if failure in ['manifest','harvest_identity']:
                bad=json.loads((ROOT/'atlases/free_fit/data/settled_reach.json').read_text());p=bad['packets']['raw'];p['expected_harvest_fingerprint' if failure=='manifest' else 'expected_harvest_binary_sha256']='bad'
                page.route('**/data/settled_reach.json?*',lambda r:r.fulfill(json=bad))
            elif failure=='grid':page.route('**/settled_reach.bin.gz?*',lambda r:r.fulfill(body=b'corrupt',content_type='application/octet-stream'))
            else:page.add_init_script('window.DecompressionStream=undefined')
            page.goto(a.base+'/atlases/free_fit/#layer=reach_towns',wait_until='domcontentloaded')
            if failure in ['manifest','harvest_identity']:
                page.wait_for_function('document.querySelector("#atlas-data-status").textContent.includes("Settlement integration unavailable")')
                page.locator('#layer-reach_towns').wait_for(state='attached')
                assert page.locator('#layer-reach_towns').count()==1 and page.locator('#layer-reach_defacto').count()==1
                assert not page.locator('#settled-section').is_visible()
            else:page.wait_for_function('document.querySelector("#settled-site-note").textContent.includes("Detailed ledger unavailable")',timeout=90000)
            assert not errors,errors;page.close();reviews.append(dict(failure=failure,isolated=True))
        browser.close()
    (a.out/'review.json').write_text(json.dumps(dict(status='passed',reviews=reviews),indent=2)+'\n');print(json.dumps(reviews,indent=2))


if __name__=='__main__':main()
