"""Check foraging topic controls/readouts; fixture mode never changes atlas files."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import numpy as np
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
KEYS=['density','effort','shortfall','carnivory']


def fixture_packet():
    fields={
        'land_fraction':np.ones((2,2),dtype='<f4'),
        'density_people_km2':np.array([[1.,2.],[3.,4.]],dtype='<f4'),
        'foraging_hours_day':np.full((2,2),4.25,dtype='<f4'),
        'meat_fraction':np.full((2,2),.3,dtype='<f4'),
        'scarcity_days_year':np.full((2,2),12.,dtype='<f4'),
        'density_cv':np.full((2,2),1.2,dtype='<f4'),
        'averaging_years_used':np.full((2,2),50.,dtype='<f4'),
        'converged':np.array([[1,0],[0,1]],dtype='u1'),
        'floor_limited':np.array([[0,1],[1,0]],dtype='u1'),
        'unsupported':np.array([[0,0],[1,0]],dtype='u1')}
    blob=bytearray();arrays={}
    for name,value in fields.items():
        while len(blob)%4:blob.append(0)
        arrays[name]=dict(dtype='uint8' if value.dtype==np.dtype('u1') else 'float32',
            shape=[2,2],offset_bytes=len(blob),nodata=None,scale=1,offset=0)
        blob.extend(value.tobytes())
    metadata=dict(shape=[2,2],fingerprint='foraging-viewer-fixture',arrays=arrays,
        binary_sha256=hashlib.sha256(blob).hexdigest(),model_note='Manufactured foraging browser fixture.',
        summary=dict(total_scenario_people=1000,converged_scenario_people=600,converged_land_share=.5,
            unsupported_land_share=.25),sources=[])
    return metadata,bytes(blob)


def install_fixture(page,*,with_foraging,corrupt=False):
    metadata,blob=fixture_packet()
    atlas=json.loads((ROOT/'atlases/earth_fit/data/atlas.json').read_text())
    atlas['layers']=[layer for layer in atlas['layers'] if layer.get('group')!='Foraging']
    atlas.pop('foraging',None)
    if with_foraging:
        atlas['foraging']=dict(metadata='foraging.json',binary='foraging.bin',fingerprint=metadata['fingerprint'])
        for key in KEYS:
            atlas['layers'].append(dict(id='forage_'+key,label='Foraging '+key,group='Foraging',controls=[],
                file='koppen.webp',kind='ramp',stops=['#eeeed8','#265f57'],vmin=0,vmax=10,unit='fixture units'))
    template=(ROOT/'atlas/index.html').read_text()
    script=(ROOT/'atlas/foraging.js').read_text()+'''
const fixtureLoad=ForagingAtlas.load;
ForagingAtlas.load=async(...args)=>{const ui=await fixtureLoad(...args);window.foragingFixtureUI=ui;return ui;};
'''
    requests=[]
    def route(request):
        path=urlsplit(request.request.url).path
        if path=='/atlases/earth_fit/':request.fulfill(body=template,content_type='text/html')
        elif path.endswith('/foraging.js'):request.fulfill(body=script,content_type='text/javascript')
        elif path.endswith('/data/atlas.json'):request.fulfill(json=atlas)
        elif path.endswith('/data/foraging.json'):
            requests.append('metadata');request.fulfill(json=metadata)
        elif path.endswith('/data/foraging.bin'):
            requests.append('binary');request.fulfill(body=blob[:-1]+b'!' if corrupt else blob,
                                                    content_type='application/octet-stream')
        else:request.continue_()
    page.route('**/*',route)
    return requests


def ready(page):
    # Whittaker fit deliberately starts on its biome map, rather than Koppen.
    page.wait_for_function("!!document.querySelector('#layers button[aria-pressed=true]')",timeout=60000)


def check_topic(page):
    page.locator('#map-topic').select_option('Foraging')
    page.locator('#foraging-section').wait_for(state='visible')
    assert page.locator('#harvest-section').is_hidden()
    assert page.locator('#population-section').is_hidden()
    assert page.locator('#settlement-controls').is_hidden()
    assert page.locator('#occupation-control').is_hidden()
    assert page.locator('#disease-control').is_hidden()
    assert page.locator('#population-controls').is_hidden()
    assert page.locator('#layers button:visible').count()==4
    for key in KEYS:
        page.locator('#layer-forage_'+key).click()
        assert page.locator('#foraging-section').is_visible()
        assert page.locator('#occupation-control').is_hidden()
        assert page.locator('#disease-control').is_hidden()
    page.locator('#map-topic').select_option('Overview')
    assert page.locator('#foraging-section').is_hidden()
    page.locator('#layer-land_density').click()
    assert page.locator('#occupation-control').is_visible()
    assert page.locator('#harvest-section').is_visible()
    page.locator('#map-topic').select_option('Foraging')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--fixture',action='store_true')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        names=['earth_fit'] if args.fixture else ['free_fit','earth_fit','whittaker_fit']
        for name in names:
            page=browser.new_page(viewport={'width':1440,'height':1050});errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            if args.fixture:install_fixture(page,with_foraging=True)
            page.goto(args.base.rstrip('/')+f'/atlases/{name}/',wait_until='domcontentloaded');ready(page)
            check_topic(page)
            page.wait_for_function("document.querySelector('#foraging-context').textContent.length>0",timeout=60000)
            page.wait_for_function("!document.querySelector('#foraging-status').textContent.includes('Loading')",timeout=60000)
            assert 'could not' not in page.locator('#foraging-status').inner_text()
            if args.fixture:
                page.wait_for_function('!!window.foragingFixtureUI')
                page.evaluate("foragingFixtureUI.select(1,1,'fixture land',false)")
                text=page.locator('#foraging-readouts').inner_text()
                assert '1 /km²' in text and '4.25 h/person/day' in text and '30%' in text and '12 days/year' in text
                page.evaluate("foragingFixtureUI.select(1999,1,'trial',false)")
                assert '2 /km²' in page.locator('#foraging-readouts').inner_text()
                assert '50-year mean' in page.locator('#foraging-readouts').inner_text()
                assert '120%' in page.locator('#foraging-readouts').inner_text()
                assert 'not an annual equilibrium' in page.locator('#foraging-status').inner_text()
                assert 'floor re-inoculation' in page.locator('#foraging-status').inner_text()
                page.evaluate("foragingFixtureUI.select(1,925,'floor',false)")
                assert 'did not sustain' in page.locator('#foraging-readouts').inner_text()
                page.evaluate("foragingFixtureUI.select(1,1,'sea',true)")
                assert 'Choose land' in page.locator('#foraging-readouts').inner_text()
            for theme in ['light','dark']:
                page.emulate_media(color_scheme=theme)
                for viewport in [{'width':1440,'height':1050},{'width':390,'height':844}]:
                    page.set_viewport_size(viewport)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert 'NaN' not in page.locator('#foraging-section').inner_text()
            assert not errors,errors
            results.append(dict(atlas=name,status='passed',controls='passed',map_modes=4,
                                mobile='passed',themes=['light','dark'],page_errors=errors))
            page.close()
        if args.fixture:
            old=browser.new_page();requests=install_fixture(old,with_foraging=False)
            old.goto(args.base.rstrip('/')+'/atlases/earth_fit/',wait_until='domcontentloaded');ready(old)
            assert old.locator('#map-topic option[value="Foraging"]').count()==0
            assert old.locator('#foraging-section').is_hidden() and not requests
            old.close();results.append(dict(older_atlas='passed',foraging_data_requests=0))
            bad=browser.new_page();install_fixture(bad,with_foraging=True,corrupt=True)
            bad.goto(args.base.rstrip('/')+'/atlases/earth_fit/',wait_until='domcontentloaded');ready(bad)
            bad.locator('#map-topic').select_option('Foraging')
            bad.wait_for_function("document.querySelector('#foraging-status').textContent.includes('do not match')",timeout=60000)
            assert bad.locator('#foraging-section').is_visible()
            bad.close();results.append(dict(corrupt_binary='rejected'))
        browser.close()
    output=dict(status='passed',fixture=args.fixture,checks=results)
    (args.out/'browser_checks.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
