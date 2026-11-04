"""Check all climate packets, scenario readouts, exports and failure isolation."""
from pathlib import Path
import argparse
import copy
import csv
import gzip
import hashlib
import io
import json
import math
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',default='http://127.0.0.1:8766');ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True);checks=[]
    def download(page):
        with page.expect_download() as event:page.click('#pm-download')
        return list(csv.DictReader(Path(event.value.path()).open(encoding='utf-8')))
    def near(actual,expected):assert math.isclose(float(actual),expected,rel_tol=1e-10,abs_tol=1e-6),(actual,expected)
    def ready(page):page.locator('#pm-readouts .readout').first.wait_for(timeout=90000)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for name,mode in [('free_fit','raw'),('earth_fit','raw'),('earth_fit','corrected'),('whittaker_fit','raw')]:
            data=ROOT/'atlases'/name/'data';manifest=json.loads((data/'presence_mobility.json').read_text());packet=manifest['packets'][mode];model=json.loads(gzip.decompress((data/packet['payload']).read_bytes()))
            page=browser.new_page(viewport=dict(width=1440,height=1100));errors=[];bad=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:bad.append(r.url) if r.status>=400 and any(s in r.url for s in ['presence_','mobility_','presence-mobility']) else None)
            url=args.base+'/atlases/'+name+'/';climate='&climate=raw' if mode=='raw' else ''
            page.goto(url+'#layer=presence_food'+climate,wait_until='domcontentloaded');ready(page)
            assert page.locator('#map-topic').input_value()=='Political reach'
            assert page.locator('#pm-site-control').is_visible() and not page.locator('#pm-mobility-controls').is_visible()
            for case,option in zip(model['presence'],packet['layers'][0]['variants']['options']):
                page.select_option('#variant',case['id'])
                page.wait_for_function('(file)=>{const i=document.querySelector("#base");return i.complete&&i.naturalWidth>0&&new URL(i.src).pathname.endsWith(file)}',arg=option['file'])
                assert page.locator('#pm-months tr').count()==12
                for control in ['#settlement-controls','#monthctl','#tiers-control']:
                    assert not page.locator(control).is_visible(),control
                assert 'variant='+case['id'] in page.url
            # All scenario/bin values for an imperial, a nonimperial and an
            # unresolved-affiliation source; map evidence stays distinct.
            chosen=[model['sites'][0],next(s for s in model['sites'] if (s['actor'] or '').startswith('Xšāça')),next(s for s in model['sites'] if s['actor'] is None)]
            count=0
            for site in chosen:
                page.select_option('#pm-site',site['id']);records=download(page);assert len(records)==len(model['presence'])*12
                j=model['sites'].index(site)
                for record in records:
                    c=next(c for c in model['presence'] if c['id']==record['scenario']);r=c['sites'][j];t=int(record['seasonal_bin'])-1
                    assert record['site_id']==site['id'] and record['climate']==mode
                    assert record['recorded_actor']==(site['actor'] or '')
                    for key,field in [('need_met','monthly_need_met'),('arrivals_kcal','monthly_arrivals_kcal'),('unmet_kcal','monthly_unmet_kcal')]:near(record[key],r[field][t])
                    near(record['end_stock_kcal'],r['stock_path_kcal'][t+1])
                    assert (record['closed_dispatch']=='true')==(t in r['closed_dispatch_bins'])
                    count+=1
            assert 'pm_site='+chosen[-1]['id'] in page.url
            # Click actual fixed collection cell: the source selector must
            # follow the raster accounting partition, not station-card snaps.
            import numpy as np
            grid=np.frombuffer(gzip.decompress((data/packet['catchments']).read_bytes()),'<u2').reshape(packet['shape'])
            r,c=np.argwhere(grid==1)[0];meta=json.loads((data/'atlas.json').read_text())
            page.locator('#base').scroll_into_view_if_needed();box=page.locator('#base').bounding_box()
            page.mouse.click(box['x']+(c+.5)/grid.shape[1]*box['width'],box['y']+(r+.5)/grid.shape[0]*box['height'])
            assert page.locator('#pm-site').input_value()==model['sites'][0]['id']
            page.select_option('#variant','closure_no_store');page.locator('#pm-section').screenshot(path=str(args.out/(name+'_'+mode+'_food.png')))
            page.set_viewport_size(dict(width=390,height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert 'Outside this experiment' not in page.locator('#pm-point-note').inner_text()
            page.set_viewport_size(dict(width=1440,height=1100))
            # Both mobility views, all landscapes and water exclusions.
            page.select_option('#map-topic','Livelihoods');page.click('#layer-mobility_circuits')
            assert not page.locator('#pm-site-control').is_visible() and page.locator('#pm-mobility-controls').is_visible()
            for option in packet['layers'][1]['variants']['options']:
                page.select_option('#variant',option['value'])
                page.wait_for_function('(file)=>{const i=document.querySelector("#base");return i.complete&&new URL(i.src).pathname.endsWith(file)}',arg=option['file'])
            route_rows=0;unscored=0
            groups={'local':model['mobility'],**model.get('mobility_scales',{})}
            for scale,examples in groups.items():
              page.select_option('#pm-scale',scale)
              for e in examples:
                page.select_option('#pm-landscape',e['id'])
                for wc in e['cases']:
                    page.select_option('#pm-water',wc['id'])
                    for v in packet['layers'][1]['variants']['options']:
                        page.select_option('#variant',v['value'])
                        file=v.get('scale_water_files',{}).get(scale,{}).get(wc['id'],v.get('scale_files',{}).get(scale,v['file']))
                        page.wait_for_function('(file)=>{const i=document.querySelector("#base");return i.complete&&new URL(i.src).pathname.endsWith(file)}',arg=file)
                    if wc['mobile'] is None:
                        assert page.locator('#pm-download').is_disabled()
                        assert 'unscored' in page.locator('#pm-readouts').inner_text().lower();unscored+=1;continue
                    records=download(page);assert len(records)==24
                    for record in records:
                        t=int(record['seasonal_bin'])-1;expected=wc[record['case']];patch=e['patches'][expected['locations'][t]]
                        assert record['climate']==mode and int(record['patch_row'])==patch['row'] and int(record['patch_column'])==patch['column']
                        assert record['landscape_scale']==scale
                        for key,field in [('collected_kg_dm','collected'),('consumed_kg_dm','consumed'),('unmet_kg_dm','unmet'),('travel_days','travel_days')]:near(record[key],expected[field][t])
                        near(record['start_reserve_kg_dm'],expected['reserves'][t]);near(record['end_reserve_kg_dm'],expected['reserves'][t+1]);route_rows+=1
                    assert page.locator('#pm-inset svg polyline').count()==2
                    assert 'best fixed base anywhere' in page.locator('#pm-readouts').inner_text()
                    if scale!='local':assert 'optimistic resource-only upper bound' in page.locator('#pm-readouts').inner_text()
            page.select_option('#pm-landscape','tribal_claim');page.select_option('#pm-water','water10');page.select_option('#variant','circuits')
            saved=page.url;page.goto('about:blank');page.goto(saved,wait_until='domcontentloaded');ready(page)
            assert page.locator('#pm-landscape').input_value()=='tribal_claim' and page.locator('#pm-water').input_value()=='water10'
            assert page.locator('#pm-scale').input_value()=='regional_dense'
            assert page.locator('#pm-overlay circle').count()==4
            page.locator('#pm-section').screenshot(path=str(args.out/(name+'_'+mode+'_circuit.png')))
            page.set_viewport_size(dict(width=390,height=844));page.emulate_media(color_scheme='dark');page.wait_for_timeout(100)
            # Page/table containers may scroll internally; viewport must not.
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(args.out/(name+'_'+mode+'_mobile.png')))
            page.select_option('#map-topic','Overview');page.click('#layer-koppen');assert not page.locator('#pm-section').is_visible()
            assert page.locator('#pm-overlay').evaluate('(e)=>getComputedStyle(e).display')=='none'
            assert not errors and not bad,(errors,bad)
            checks.append(dict(atlas=name,climate=mode,presence_views=len(model['presence']),mobility_views=2,scales=len(groups),site_csv_rows=count,route_csv_rows=route_rows,unscored_water_cases=unscored,state_and_mobile_passed=True))
            page.close()
        failures=[];manifest=json.loads((ROOT/'atlases/earth_fit/data/presence_mobility.json').read_text())
        for fixture in ['wrong_identity','corrupt_gzip','unsupported_browser','pasture_failure_retains_circuits']:
            page=browser.new_page(viewport=dict(width=1100,height=900))
            if fixture=='pasture_failure_retains_circuits':
                page.route('**/data/corrected/pasture.bin*',lambda route:route.fulfill(status=200,body=b'bad grid'))
                page.goto(args.base+'/atlases/earth_fit/#layer=mobility_circuits',wait_until='domcontentloaded');ready(page)
                assert page.locator('#map-topic').input_value()=='Livelihoods' and page.locator('#pm-section').is_visible()
                assert page.locator('#layer-pasture_annual').count()==0
                failures.append(dict(fixture=fixture,status='retains_other_livelihood_layer'));page.close();continue
            elif fixture=='unsupported_browser':page.add_init_script('window.DecompressionStream=undefined')
            else:
                changed=copy.deepcopy(manifest)
                if fixture=='wrong_identity':changed['packets']['corrected']['payload_sha256']='0'*64
                else:
                    badgzip=b'not a gzip';changed['packets']['corrected']['payload_sha256']=hashlib.sha256(badgzip).hexdigest()
                    page.route('**/corrected/presence_mobility.json.gz*',lambda route:route.fulfill(status=200,body=badgzip))
                page.route('**/data/presence_mobility.json?*',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(changed)))
            page.goto(args.base+'/atlases/earth_fit/#layer=presence_food',wait_until='domcontentloaded')
            page.wait_for_function('document.querySelector("#atlas-data-status").textContent.includes("Presence/circuit scenarios unavailable")',timeout=90000)
            assert page.locator('#layer-presence_food').count()==0 and page.locator('#layer-mobility_circuits').count()==0
            assert page.locator('#layer-koppen').count()==1 and not page.locator('#pm-section').is_visible()
            failures.append(dict(fixture=fixture,status='isolated_optional_layers'));page.close()
        browser.close()
    (args.out/'review.json').write_text(json.dumps(dict(status='passed',packets=checks,failure_isolation=failures),indent=2)+'\n')
    print(json.dumps(dict(status='passed',packets=checks,failure_isolation=failures),indent=2))


if __name__=='__main__':main()
