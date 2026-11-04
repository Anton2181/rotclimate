"""Check dynamic worldwide coverage against independently decoded grid words."""
from pathlib import Path
import argparse
import csv
import json
from urllib.parse import urlencode
import numpy as np
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def decode_mask(word,b):
    return sum((1<<m) for m in range(12) if ((int(word)>>(2*m))&3)>=3-b)


def longest(mask):
    run=best=0
    for t in range(24):
        run=0 if mask&(1<<(t%12)) else min(12,run+1);best=max(best,run)
    return best


def main():
    from publish_world_coverage import load_fields
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True);checks=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for name,mode in [('free_fit','raw'),('earth_fit','raw'),('earth_fit','corrected'),('whittaker_fit','raw')]:
            data=ROOT/'atlases'/name/'data';manifest=json.loads((data/'coverage.json').read_text());p=manifest['packets'][mode]
            lookup,words,unknown=load_fields(data/Path(p['binary']).parent,p);k=len(p['actors']);actor_names=[a['name'] for a in p['actors']]
            page=browser.new_page(viewport=dict(width=1440,height=1100));errors=[];bad=[];gzip_requests=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:bad.append(r.url) if r.status>=400 and 'coverage' in r.url else None)
            page.on('request',lambda r:gzip_requests.append(r.url) if 'coverage.bin.gz' in r.url else None)
            page.goto(args.base+'/atlases/'+name+'/#layer=koppen'+('&climate=raw' if mode=='raw' else ''),wait_until='domcontentloaded')
            page.wait_for_function('()=>document.querySelector("#station-h").textContent!=="—"',timeout=90000)
            assert not gzip_requests,'Coverage must load lazily'
            page.select_option('#map-topic','Political reach');page.click('#layer-reach_coverage_audit')
            def ready():
                page.wait_for_function('()=>document.querySelector("#base").src.startsWith("data:image/")&&!document.querySelector("#coverage-message").textContent.includes("Loading")',timeout=90000)
            ready();assert len(gzip_requests)==1
            for option in p['layers'][0]['variants']['options']:
                page.select_option('#variant',option['value']);ready()
                assert page.locator('#coverage-section').is_visible()
                assert not page.locator('#harvest-section').is_visible()
                for selector in ['#settlement-controls','#monthctl','#tiers-control']:
                    assert not page.locator(selector).is_visible()
                assert page.locator('#coverage-actor-control').is_visible()==(option['value']!='unknown')
                assert page.locator('#coverage-source-control').is_visible()==(option['value'] not in ['unknown','source_gain'])
            page.select_option('#variant','coverage');ready()
            if not page.locator('#find-input').is_visible():page.click('#searchtoggle')
            page.fill('#find-input','Lakui');page.locator('#find-form').evaluate('(f)=>f.requestSubmit()')
            page.wait_for_function('()=>document.querySelector("#coverage-place").textContent.includes("Lakui")')
            exported=[]
            for b,budget in enumerate(p['budgets_days']):
                page.select_option('#coverage-budget',str(b));ready()
                with page.expect_download() as download:page.click('#coverage-download')
                rows=list(csv.DictReader(Path(download.value.path()).open()))
                assert len(rows)==3*k
                for j,row in enumerate(rows):
                    s,a=divmod(j,k);r,c=int(row['grid_row']),int(row['grid_column']);index=int(lookup[r,c])-1
                    assert index>=0 and row['climate']==mode and float(row['per_leg_days'])==budget
                    sources=p['actors'][a]['source_counts'][s]
                    assert int(row['source_nodes'])==sources and row['actor']==actor_names[a]
                    out=decode_mask(words[s,a,0,index],b);both=decode_mask(words[s,a,1,index],b)
                    if not sources:
                        assert row['status']=='missing_source_inventory'
                        assert row['outward_bins']==row['same_site_two_way_bins']==row['longest_two_way_gap']==''
                    else:
                        assert int(row['outward_bins'])==out.bit_count()
                        assert int(row['same_site_two_way_bins'])==both.bit_count()
                        assert int(row['longest_two_way_gap'])==longest(both)
                    assert int(row['unaffiliated_site_two_way_bins'])==decode_mask(unknown[1,index],b).bit_count()
                exported.append(dict(budget=budget,rows_checked=len(rows),point=[r,c]))
            tribal=actor_names.index('Avādāyā Tribes')
            page.select_option('#coverage-actor',str(tribal));page.select_option('#coverage-sources','0');ready()
            assert 'Unscored' in page.locator('#coverage-readouts').inner_text()
            page.select_option('#variant','source_gain');ready()
            assert 'Missing inventory' in page.locator('#legend').inner_text()
            page.select_option('#variant','coverage');page.select_option('#coverage-sources','2');ready()
            assert 'Unscored' not in page.locator('#coverage-readouts').inner_text()
            page.select_option('#coverage-actor','all');page.select_option('#coverage-budget','1');page.select_option('#coverage-sources','0');ready()
            assert len(gzip_requests)==1,'Changing controls must reuse the loaded grids'
            values=page.evaluate('()=>Array.from({length:4096},(_,m)=>{let w=0;for(let t=0;t<12;t++)if(m&(1<<t))w|=3<<(2*t);return [0,1,2].map(b=>CoverageAtlas.mask(w,b));})')
            assert all(v==[i,i,i] for i,v in enumerate(values))
            page.select_option('#coverage-actor',str(actor_names.index('Kingdom of Tarani')));page.select_option('#coverage-sources','1');page.select_option('#coverage-budget','2');ready()
            page.reload(wait_until='domcontentloaded');ready()
            assert page.locator('#coverage-actor').input_value()==str(actor_names.index('Kingdom of Tarani'))
            assert page.locator('#coverage-sources').input_value()=='1' and page.locator('#coverage-budget').input_value()=='2'
            assert len(gzip_requests)==2
            for selector in ['#coverage-grid','#coverage-registry','#coverage-source-csv','#coverage-method']:
                response=page.request.get(page.locator(selector).evaluate('(a)=>a.href'))
                assert response.ok and response.headers.get('cache-control')=='no-store',selector
            for theme in ['light','dark']:
                page.emulate_media(color_scheme=theme)
                for width,height in [(1440,1100),(390,844)]:
                    page.set_viewport_size(dict(width=width,height=height))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.set_viewport_size(dict(width=1440,height=1100));page.emulate_media(color_scheme='light')
            page.select_option('#coverage-actor','all');page.select_option('#coverage-sources','0');page.select_option('#coverage-budget','1');ready()
            page.locator('.plate').screenshot(path=str(args.out/(name+'_'+mode+'.png')))
            page.click('#coverage-compare');assert page.locator('#coverage-baseline-note').is_visible()
            assert not page.locator('#coverage-controls').is_visible()
            page.click('#coverage-open-audit');ready()
            page.select_option('#map-topic','Overview');page.click('#layer-land_density')
            assert not page.locator('#coverage-controls').is_visible() and not page.locator('#coverage-section').is_visible()
            assert page.locator('#settlement-controls').is_visible()
            assert not errors,errors;assert not bad,bad
            checks.append(dict(atlas=name,climate=mode,status='passed',views=6,csv=exported,packing_cases=4096,
                missing_inventories_unscored=True,lazy_load_and_state='passed',controls_mobile_downloads_baseline='passed'))
            page.close();del lookup,words,unknown
        for failure in ['identity','gzip','unsupported_browser']:
            page=browser.new_page()
            if failure=='identity':
                def wrong(route):
                    response=route.fetch();m=response.json()
                    for p in m['packets'].values():p['expected_harvest_binary_sha256']='0'*64
                    route.fulfill(response=response,json=m)
                page.route('**/data/coverage.json?*',wrong)
            elif failure=='gzip':page.route('**/data/corrected/coverage.bin.gz?*',lambda route:route.fulfill(status=200,body=b'bad grid'))
            else:page.add_init_script('window.DecompressionStream=undefined')
            page.goto(args.base+'/atlases/earth_fit/#layer=reach_coverage_audit',wait_until='domcontentloaded')
            page.wait_for_function('()=>document.querySelector("#atlas-data-status").textContent.includes("Coverage audit unavailable")',timeout=90000)
            assert page.locator('#layer-reach_coverage_audit').count()==0
            assert not page.locator('#coverage-section').is_visible()
            assert page.locator('#layer-reach_defacto').count()==1 and page.locator('#layer-koppen').count()==1
            checks.append(dict(status='passed',failure=failure,original_atlas_remains_usable=True));page.close()
        browser.close()
    (args.out/'review.json').write_text(json.dumps(dict(status='passed',checks=checks),indent=2)+'\n')
    print('Passed:4packets×6views;648actor/scenario/budget CSV rows;4096 packing cases;missing evidence, lazy loading, state, controls, mobile, downloads and failure isolation')


if __name__=='__main__':main()
