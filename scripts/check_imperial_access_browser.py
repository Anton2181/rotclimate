"""Exercise all administration views and compare browser exports with grids."""
from pathlib import Path
import argparse
import csv
import json
import numpy as np
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True);checks=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for name,mode in [('free_fit','raw'),('earth_fit','raw'),('earth_fit','corrected'),('whittaker_fit','raw')]:
            folder=ROOT/'atlases'/name;manifest=json.loads((folder/'data/administrative_access.json').read_text())
            packet=manifest['packets'][mode];grid=np.load(folder/'data'/packet['grid'])
            page=browser.new_page(viewport=dict(width=1440,height=1100));errors=[];bad=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('response',lambda response:bad.append(response.url) if response.status>=400 and any(
                token in response.url for token in ['administration','administrative','imperial_centres']) else None)
            url=args.base+'/atlases/'+name+'/#layer=admin_imperial_access&variant=recorded_centres'+('&climate=raw' if mode=='raw' else '')
            page.goto(url,wait_until='domcontentloaded')
            page.locator('#administration-readouts .readout').first.wait_for(timeout=90000)
            assert page.locator('#map-topic').input_value()=='Administration'
            assert page.locator('#administration-section').is_visible()
            assert not page.locator('#harvest-section').is_visible()
            assert '70 of 72' in page.locator('#administration-inventory-note').inner_text()
            assert 'different places' in page.locator('#administration-unresolved').text_content()
            views=0
            for layer in packet['layers']:
                page.click('#layer-'+layer['id'])
                options=layer.get('variants',{}).get('options',[layer])
                for option in options:
                    if 'variants' in layer:page.select_option('#variant',option['value'])
                    page.wait_for_function('(file)=>{const im=document.querySelector("#base");return im.complete&&im.naturalWidth>0&&new URL(im.src).pathname.endsWith(file)}',arg=option['file'])
                    for selector in ['#settlement-controls','#monthctl','#tiers-control']:
                        assert not page.locator(selector).is_visible(),selector
                    views+=1
            assert views==12
            page.click('#layer-admin_imperial_access');page.select_option('#variant','recorded_centres')
            if not page.locator('#find-input').is_visible():page.click('#searchtoggle')
            page.fill('#find-input','Aēnaha');page.locator('#find-form').evaluate('(form)=>form.requestSubmit()')
            page.wait_for_function('()=>document.querySelector("#administration-place").textContent.includes("Aēnaha")')
            with page.expect_download() as download:page.click('#administration-download')
            rows=list(csv.DictReader(Path(download.value.path()).open()))
            assert len(rows)==6
            for i,row in enumerate(rows):
                r,c=int(row['grid_row']),int(row['grid_column'])
                assert row['climate']==mode and row['source_case']==packet['cases'][i]
                assert int(row['accessible_model_month_bins'])==int(grid['accessible_months'][i,r,c])
                assert int(row['longest_isolation_bins'])==int(grid['longest_isolation'][i,r,c])
                assert (row['annual_mean_inside_cutoff']=='true')==bool(grid['annual_threshold'][i,r,c])
                assert int(row['proposal_runs_within_10km'])==int(grid['proposal_recurrence'][r,c])
            # Exhaust all twelve-bit masks, independent of the point sample.
            values=page.evaluate('()=>Array.from({length:4096},(_,mask)=>AdministrativeAtlas.metrics(mask))')
            for mask,value in enumerate(values):
                bits=[bool(mask&(1<<i)) for i in range(12)];run=longest=0
                for b in bits*2:
                    run=0 if b else min(12,run+1);longest=max(longest,run)
                assert value==dict(months=sum(bits),longest=longest)
            page.select_option('#variant','road_sources');page.reload(wait_until='domcontentloaded')
            page.locator('#administration-readouts .readout').first.wait_for(timeout=90000)
            assert page.locator('#variant').input_value()=='road_sources'
            for selector in ['#administration-grid','#administration-centres','#administration-inventory','#administration-method']:
                response=page.request.get(page.locator(selector).evaluate('(a)=>a.href'))
                assert response.ok and response.headers.get('cache-control')=='no-store',selector
            for theme in ['light','dark']:
                page.emulate_media(color_scheme=theme)
                for width,height in [(1440,1100),(390,844)]:
                    page.set_viewport_size(dict(width=width,height=height))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.set_viewport_size(dict(width=1440,height=1100))
            page.select_option('#map-topic','Overview');page.click('#layer-land_density')
            assert page.locator('#settlement-controls').is_visible()
            assert not page.locator('#administration-section').is_visible()
            assert not errors,errors;assert not bad,bad
            checks.append(dict(atlas=name,climate=mode,status='passed',views=views,point_csv=rows,
                mask_cases=4096,controls_and_state='passed',downloads='passed',mobile_overflow=False))
            page.close();grid.close()
        page=browser.new_page()
        def mismatch(route):
            response=route.fetch();manifest=response.json()
            for packet in manifest['packets'].values():packet['expected_harvest_binary_sha256']='0'*64
            route.fulfill(response=response,json=manifest)
        page.route('**/data/administrative_access.json?*',mismatch)
        page.goto(args.base+'/atlases/earth_fit/#layer=admin_imperial_access',wait_until='domcontentloaded')
        page.wait_for_function('()=>document.querySelector("#station-h").textContent!=="—"',timeout=90000)
        assert 'Administrative access maps unavailable' in page.locator('#atlas-data-status').inner_text()
        assert page.locator('#map-topic option[value="Administration"]').count()==0
        assert not page.locator('#administration-section').is_visible()
        assert page.locator('#layer-koppen').count()==1
        checks.append(dict(status='passed',mismatched_input='failed closed; climate remains usable'))
        browser.close()
    (args.out/'review.json').write_text(json.dumps(dict(status='passed',checks=checks),indent=2)+'\n')
    print('Passed: four climate packets, 48 map views, CSV/grid values, 4096 masks, controls, downloads and mismatch handling')


if __name__=='__main__':main()
