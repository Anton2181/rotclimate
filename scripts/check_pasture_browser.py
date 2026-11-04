"""Check worldwide resource views and numerical readouts, including unclaimed land."""
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
            folder=ROOT/'atlases'/name;meta=json.loads((folder/'data/atlas.json').read_text());manifest=json.loads((folder/'data/pasture.json').read_text())
            packet=manifest['packets'][mode];grid=np.load(folder/'data'/packet['grid'])
            page=browser.new_page(viewport=dict(width=1440,height=1100));errors=[];bad=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:bad.append(r.url) if r.status>=400 and 'pasture' in r.url else None)
            page.goto(args.base+'/atlases/'+name+'/#layer=pasture_seasonal&variant=reserve_days'+('&climate=raw' if mode=='raw' else ''),wait_until='domcontentloaded')
            page.locator('#pasture-readouts .readout').first.wait_for(timeout=90000)
            assert page.locator('#map-topic').input_value()=='Livelihoods'
            assert not page.locator('#harvest-section').is_visible()
            views=0
            for layer in packet['layers']:
                page.click('#layer-'+layer['id'])
                for option in layer.get('variants',{}).get('options',[layer]):
                    if 'variants' in layer:page.select_option('#variant',option['value'])
                    page.wait_for_function('(file)=>{const im=document.querySelector("#base");return im.complete&&im.naturalWidth>0&&new URL(im.src).pathname.endsWith(file)}',arg=option['file'])
                    for selector in ['#settlement-controls','#monthctl','#tiers-control']:
                        assert not page.locator(selector).is_visible(),selector
                    views+=1
            assert views==6
            page.click('#layer-pasture_seasonal');page.select_option('#variant','reserve_days')
            # Cover the nonimperial claim, tribal claim and two patches outside
            # named claims. These are resource cells, not assigned societies.
            records=[]
            for pilot in packet['pilots']:
                page.locator('#base').scroll_into_view_if_needed()
                box=page.locator('#base').bounding_box()
                page.mouse.click(box['x']+pilot['x']/meta['width']*box['width'],box['y']+pilot['y']/meta['height']*box['height'])
                assert page.locator('#pasture-download').is_enabled()
                with page.expect_download() as download:page.click('#pasture-download')
                record=list(csv.DictReader(Path(download.value.path()).open()))[0]
                r,c=int(record['grid_row']),int(record['grid_column'])
                assert (r,c)==(pilot['row'],pilot['column']),(pilot,record)
                assert record['climate']==mode
                for key,array in [('annual_usable_dm_kg_per_land_km2','annual_dm'),('lean_new_growth_fraction','lean_fraction'),
                    ('minimum_zero_loss_reserve_demand_days','reserve_days'),('shortfall_bins_with_90_demand_day_buffer','shortfall_bins'),('mapped_water_distance_km','water_distance')]:
                    expected=float(grid[array][r,c]);value=record[key]
                    if np.isfinite(expected):
                        tolerance=packet['fields'][array]['scale']*.502+abs(expected)*1e-6
                        assert abs(float(value)-expected)<=tolerance,(key,value,expected)
                    else:assert value==''
                annual=float(record['annual_usable_dm_kg_per_land_km2'])
                assert math.isclose(float(record['annual_feed_reference_units_per_land_km2']),annual/(6.25*365),rel_tol=1e-12)
                assert record['test_demand_fraction']=='0.5'
                records.append(dict(pilot=pilot['id'],claim=pilot['map_claim'],csv=record))
            assert len(records)==4 and sum(r['claim'] is None for r in records)==2
            page.reload(wait_until='domcontentloaded');page.locator('#pasture-readouts .readout').first.wait_for(timeout=90000)
            assert page.locator('#variant').input_value()=='reserve_days'
            for selector in ['#pasture-grid','#pasture-method']:
                response=page.request.get(page.locator(selector).evaluate('(a)=>a.href'))
                assert response.ok and response.headers.get('cache-control')=='no-store'
            for theme in ['light','dark']:
                page.emulate_media(color_scheme=theme)
                for width,height in [(1440,1100),(390,844)]:
                    page.set_viewport_size(dict(width=width,height=height))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.set_viewport_size(dict(width=1440,height=1100));page.emulate_media(color_scheme='light')
            page.locator('.plate').screenshot(path=str(args.out/(name+'_'+mode+'.png')))
            page.select_option('#map-topic','Overview');page.click('#layer-land_density')
            assert not page.locator('#pasture-section').is_visible()
            assert page.locator('#settlement-controls').is_visible()
            assert not errors,errors;assert not bad,bad
            checks.append(dict(atlas=name,climate=mode,status='passed',views=views,pilot_records=records,controls_state_downloads_mobile='passed'))
            grid.close();page.close()
        for failure in ['identity','binary']:
            page=browser.new_page()
            if failure=='identity':
                def wrong(route):
                    response=route.fetch();m=response.json()
                    for p in m['packets'].values():p['expected_harvest_binary_sha256']='0'*64
                    route.fulfill(response=response,json=m)
                page.route('**/data/pasture.json?*',wrong)
            else:page.route('**/data/corrected/pasture.bin?*',lambda route:route.fulfill(status=200,body=b'bad grid'))
            page.goto(args.base+'/atlases/earth_fit/#layer=pasture_annual',wait_until='domcontentloaded')
            page.wait_for_function('()=>document.querySelector("#station-h").textContent!=="—"',timeout=90000)
            assert 'Pasture resources unavailable' in page.locator('#atlas-data-status').inner_text()
            assert page.locator('#map-topic option[value="Livelihoods"]').count()==0
            assert not page.locator('#pasture-section').is_visible()
            assert page.locator('#layer-koppen').count()==1 and page.locator('#layer-hierarchy_links').count()==1
            checks.append(dict(status='passed',failure=failure,other_features_remain_usable=True));page.close()
        browser.close()
    (args.out/'review.json').write_text(json.dumps(dict(status='passed',checks=checks),indent=2)+'\n')
    print('Passed: four climate packets ×six views; 16 pilot CSV/NPZ checks, unclaimed/tribal/nonimperial coverage, controls, state, mobile, downloads and mismatch isolation')


if __name__=='__main__':main()
