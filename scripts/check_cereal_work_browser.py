"""Check real atlas cereal-work maps, controls and exported numerical values."""
from pathlib import Path
import argparse
import csv
import json
import math
import tempfile
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
            folder=ROOT/'atlases'/name;meta=json.loads((folder/'data/atlas.json').read_text())
            manifest=json.loads((folder/'data/farm_work.json').read_text());packet=manifest['packets'][mode]
            grid=np.load(folder/'data'/packet['grid']);shape=packet['shape'];cp=packet['cell_px']
            climate_meta=meta['corrected_climate'] if mode=='corrected' else meta
            climate_bin=folder/'data'/('corrected/atlas.bin' if mode=='corrected' else 'atlas.bin')
            spec=climate_meta['arrays']['cls']
            cls=np.frombuffer(climate_bin.read_bytes(),dtype=spec['dtype'],offset=spec['offset'],count=int(np.prod(spec['shape']))).reshape(spec['shape'])
            places=[]
            for p in meta['places']:
                x,y=round(p['x']),round(p['y']);r=min(shape[0]-1,int(y/cp));c=min(shape[1]-1,int(x/cp))
                kr=min(cls.shape[0]-1,y//2);kc=min(cls.shape[1]-1,x//2)
                if grid['cereal'][r,c]>0 and cls[kr,kc]!=255:places.append(p)
            assert places,'No selectable productive named place'
            place=places[len(places)//2]
            page=browser.new_page(viewport=dict(width=1440,height=1100));errors=[];bad=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('response',lambda r:bad.append(str(r.status)+' '+r.url) if r.status>=400 and 'farm_work' in r.url else None)
            url=args.base+'/atlases/'+name+'/#layer=farm_cereal_work&variant=hours'+('&climate=raw' if mode=='raw' else '')
            page.goto(url,wait_until='domcontentloaded')
            page.locator('#farm-work-readouts .readout').first.wait_for(timeout=90000)
            assert page.locator('#map-topic').input_value()=='Food and work'
            assert page.locator('#farm-work-section').is_visible()
            assert not page.locator('#settlement-controls').is_visible()
            assert not page.locator('#monthctl').is_visible()
            assert not page.locator('#tiers-control').is_visible()
            for view in ['hours','land','staff_10','staff_20','staff_30']:
                page.select_option('#variant',view)
                page.wait_for_function('(key)=>{const im=document.querySelector("#base");return im.complete&&im.naturalWidth>0&&im.src.includes("farm_work_"+key+".webp")}',arg=view)
                assert not page.locator('#settlement-controls').is_visible()
            page.select_option('#variant','hours')
            if not page.locator('#find-input').is_visible():page.click('#searchtoggle')
            page.fill('#find-input',place['name']);page.locator('#find-form').evaluate('(form)=>form.requestSubmit()')
            page.wait_for_function('(name)=>document.querySelector("#farm-work-place").textContent.includes(name)',arg=place['name'])
            with page.expect_download() as download:
                page.click('#farm-work-download')
            row=list(csv.DictReader(Path(download.value.path()).open()))[0]
            r,c=int(row['grid_row']),int(row['grid_column'])
            assert row['climate']==mode and row['status']=='partial_cereal_work_scenario'
            for key,array in [('listed_hours','listed_hours_per_million_kcal'),('cropped_hectares','cropped_ha_per_million_kcal'),('reaping_hours','reaping_hours_per_million_kcal')]:
                assert math.isclose(float(row[key]),float(grid[array][r,c]),rel_tol=2e-6),key
            assert int(row['harvest_boundary_options'])==int(grid['harvest_boundaries'][r,c]).bit_count()
            assert math.isclose(float(row['staff_10_days']),2*float(row['staff_20_days']),rel_tol=1e-10)
            assert math.isclose(float(row['staff_10_days']),3*float(row['staff_30_days']),rel_tol=1e-10)
            page.click('#layer-farm_cereal_calendars')
            assert not page.locator('#variant-controls').is_visible()
            assert not page.locator('#settlement-controls').is_visible()
            page.wait_for_function('()=>{const im=document.querySelector("#base");return im.complete&&im.naturalWidth>0&&im.src.includes("farm_work_calendar.webp")}')
            page.reload(wait_until='domcontentloaded');page.locator('#farm-work-readouts .readout').first.wait_for(timeout=90000)
            assert '#layer=farm_cereal_calendars' in page.url
            assert page.locator('#map-topic').input_value()=='Food and work'
            for selector in ['#farm-work-grid','#farm-work-method']:
                response=page.request.get(page.locator(selector).evaluate('(a)=>a.href'))
                assert response.ok and response.headers.get('cache-control')=='no-store'
            for theme in ['light','dark']:
                page.emulate_media(color_scheme=theme)
                for viewport in [dict(width=1440,height=1100),dict(width=390,height=844)]:
                    page.set_viewport_size(viewport)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    if theme=='light' and viewport['width']==1440:
                        page.locator('.plate').screenshot(path=str(args.out/(name+'_'+mode+'_calendar.png')))
            page.set_viewport_size(dict(width=1440,height=1100))
            page.select_option('#map-topic','Overview');page.click('#layer-land_density')
            assert page.locator('#settlement-controls').is_visible()
            assert not page.locator('#farm-work-section').is_visible()
            assert not errors,errors;assert not bad,bad
            checks.append(dict(atlas=name,climate=mode,status='passed',views=6,numerical_csv=row,
                state_restoration=True,irrelevant_controls_hidden=True,occupation_restored_for_density=True,
                downloads='passed',mobile_overflow=False,page_errors=errors))
            page.close();grid.close()
        page=browser.new_page()
        def wrong_identity(route):
            response=route.fetch();manifest=response.json()
            for packet in manifest['packets'].values():packet['harvest_binary_sha256']='0'*64
            route.fulfill(response=response,json=manifest)
        page.route('**/data/farm_work.json?*',wrong_identity)
        page.goto(args.base+'/atlases/earth_fit/#layer=farm_cereal_work',wait_until='domcontentloaded')
        page.wait_for_function('()=>document.querySelector("#station-h").textContent!=="—"',timeout=90000)
        assert 'Cereal-work maps unavailable' in page.locator('#atlas-data-status').inner_text()
        assert page.locator('#map-topic option[value="Food and work"]').count()==0
        assert not page.locator('#farm-work-section').is_visible()
        assert page.locator('#layer-koppen').count()==1
        page.close();browser.close()
    (args.out/'checks.json').write_text(json.dumps(dict(status='passed',packets=checks,mismatched_packet_hidden=True),indent=2)+'\n')
    print(json.dumps(dict(status='passed',packets=len(checks),views_per_packet=6,numerical_exports='passed'),indent=2))


if __name__=='__main__':main()
