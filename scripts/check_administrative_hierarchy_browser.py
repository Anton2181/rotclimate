"""Check hierarchy maps, directed data, budget scenarios and failure isolation."""
from pathlib import Path
import argparse
import csv
import json
import math
import numpy as np
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True);checks=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for name,mode in [('free_fit','raw'),('earth_fit','raw'),('earth_fit','corrected'),('whittaker_fit','raw')]:
            folder=ROOT/'atlases'/name;manifest=json.loads((folder/'data/administrative_hierarchy.json').read_text())
            packet=manifest['packets'][mode];registry=manifest['registry']['links'];by_id={c['commandery_id']:i for i,c in enumerate(registry)}
            with np.load(folder/'data'/packet['grid']) as grid:days=grid['days']
            page=browser.new_page(viewport=dict(width=1440,height=1100));errors=[];bad=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('response',lambda r:bad.append(r.url) if r.status>=400 and 'hierarchy' in r.url else None)
            page.goto(args.base+'/atlases/'+name+'/#layer=hierarchy_links&variant=chain_marked&commandery=IC3C1&reply_budget=14'+('&climate=raw' if mode=='raw' else ''),wait_until='domcontentloaded')
            page.locator('#hierarchy-readouts .readout').first.wait_for(timeout=90000)
            assert page.locator('#map-topic').input_value()=='Administration'
            assert page.locator('#hierarchy-commandery').input_value()=='IC3C1'
            assert page.locator('#hierarchy-budget').input_value()=='14'
            assert not page.locator('#administration-section').is_visible()
            options=packet['layers'][0]['variants']['options']
            for option in options:
                page.select_option('#variant',option['value'])
                page.wait_for_function('(file)=>{const im=document.querySelector("#base");return im.complete&&im.naturalWidth>0&&new URL(im.src).pathname.endsWith(file)}',arg=option['file'])
                for control in ['#settlement-controls','#monthctl','#tiers-control']:
                    assert not page.locator(control).is_visible(),control
            page.select_option('#variant','chain_marked')
            counts=[]
            for budget in [7,14,30,60]:
                page.select_option('#hierarchy-budget',str(budget))
                text=page.locator('#hierarchy-readouts .v').nth(2).inner_text();count=int(text.split('/')[0]);counts.append(count)
                chain=days[0,:,by_id['IC3C1']].sum(axis=1)
                assert count==int(np.sum(chain<=budget))
            assert counts==sorted(counts)
            with page.expect_download() as download:page.click('#hierarchy-download')
            rows=list(csv.DictReader(Path(download.value.path()).open()))
            assert len(rows)==24
            for i,row in enumerate(rows):
                s=i//12;m=i%12;expected=days[s,m,by_id[row['commandery_id']]]
                assert row['climate']==mode and row['reply_budget_days']=='60'
                for j,key in enumerate(['capital_to_province','province_to_seat','seat_to_province','province_to_capital']):
                    assert math.isclose(float(row[key]),expected[j],rel_tol=1e-12),key
                assert math.isclose(float(row['imperial_reply_days']),expected.sum(),rel_tol=1e-12)
            page.select_option('#hierarchy-commandery','IC2C4')
            assert float(page.locator('#hierarchy-readouts .v').nth(0).inner_text())==0
            assert float(page.locator('#hierarchy-readouts .v').nth(1).inner_text())>0
            page.select_option('#hierarchy-commandery','CAPITAL')
            assert float(page.locator('#hierarchy-readouts .v').nth(1).inner_text())==0
            for cid in ['IC4C3','IP4C4']:
                page.select_option('#hierarchy-commandery',cid)
                assert 'unresolved' in page.locator('#hierarchy-readouts').inner_text()
                assert page.locator('#hierarchy-download').is_disabled()
            if not page.locator('#find-input').is_visible():page.click('#searchtoggle')
            page.fill('#find-input','Kudā');page.locator('#find-form').evaluate('(form)=>form.requestSubmit()')
            page.wait_for_function('()=>document.querySelector("#hierarchy-commandery").value==="IC4C3"')
            assert page.locator('#hierarchy-download').is_disabled()
            page.select_option('#hierarchy-commandery','IC3C1');page.select_option('#hierarchy-budget','14')
            page.select_option('#variant','local_proposed');page.reload(wait_until='domcontentloaded')
            page.locator('#hierarchy-readouts .readout').first.wait_for(timeout=90000)
            assert page.locator('#hierarchy-commandery').input_value()=='IC3C1'
            assert page.locator('#hierarchy-budget').input_value()=='14'
            assert page.locator('#variant').input_value()=='local_proposed'
            for selector in ['#hierarchy-grid','#hierarchy-csv','#hierarchy-method']:
                response=page.request.get(page.locator(selector).evaluate('(a)=>a.href'))
                assert response.ok and response.headers.get('cache-control')=='no-store'
            values=page.evaluate('()=>[AdministrativeHierarchy.stats([null,...Array(10).fill(2),null],3),AdministrativeHierarchy.stats(Array(12).fill(0),0)]')
            assert values[0]==dict(best=2,worst=None,within=10,longest=2)
            assert values[1]==dict(best=0,worst=0,within=12,longest=0)
            for theme in ['light','dark']:
                page.emulate_media(color_scheme=theme)
                for width,height in [(1440,1100),(390,844)]:
                    page.set_viewport_size(dict(width=width,height=height))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.set_viewport_size(dict(width=1440,height=1100));page.select_option('#variant','chain_marked')
            page.locator('.plate').screenshot(path=str(args.out/(name+'_'+mode+'.png')))
            page.select_option('#map-topic','Overview');page.click('#layer-land_density')
            assert not page.locator('#hierarchy-section').is_visible()
            assert page.locator('#settlement-controls').is_visible()
            assert not errors,errors;assert not bad,bad
            checks.append(dict(atlas=name,climate=mode,status='passed',views=6,point_csv=rows,budget_counts=counts,
                self_links_and_unresolved_seats='passed',state_controls_downloads_mobile='passed'))
            page.close()
        for failure in ['identity','days']:
            page=browser.new_page()
            if failure=='identity':
                def mismatch(route):
                    response=route.fetch();manifest=response.json()
                    for packet in manifest['packets'].values():packet['expected_harvest_binary_sha256']='0'*64
                    route.fulfill(response=response,json=manifest)
                page.route('**/data/administrative_hierarchy.json?*',mismatch)
            else:page.route('**/data/corrected/hierarchy_links.json?*',lambda route:route.fulfill(status=200,body='{}'))
            page.goto(args.base+'/atlases/earth_fit/#layer=hierarchy_links',wait_until='domcontentloaded')
            page.wait_for_function('()=>document.querySelector("#station-h").textContent!=="—"',timeout=90000)
            assert 'Administrative links unavailable' in page.locator('#atlas-data-status').inner_text()
            assert page.locator('#layer-hierarchy_links').count()==0
            assert page.locator('#layer-admin_imperial_access').count()==1
            assert not page.locator('#hierarchy-section').is_visible()
            checks.append(dict(status='passed',failure=failure,old_access_and_climate_remain_usable=True));page.close()
        browser.close()
    (args.out/'review.json').write_text(json.dumps(dict(status='passed',checks=checks),indent=2)+'\n')
    print('Passed: four climate packets × six views, directed CSV/NPZ values, budgets, unresolved seats, state, controls and failure isolation')


if __name__=='__main__':main()
