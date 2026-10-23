"""Exercise live census budgets, food limits, map controls and downloadable totals."""
import argparse
import asyncio
import csv
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def check(base,out):
    results=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for name in ['free_fit','earth_fit','whittaker_fit']:
            page=await browser.new_page(viewport={'width':1440,'height':1050},accept_downloads=True);errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.goto(f'{base}/atlases/{name}/#layer=pop_density&population=20000000&pattern=markets',wait_until='domcontentloaded')
            async def ready(text):
                await page.wait_for_function("text=>document.querySelector('#population-message').textContent.includes(text)&&document.querySelector('#base').src.startsWith('data:')",arg=text,timeout=60000)
            async def layer(key):
                await page.locator('#layer-pop_'+key).click();await ready('supported' if key not in ['travel','attraction'] else 'Walking access')
            async def census(label,requested):
                await page.locator('#population-provinces').evaluate("e=>e.closest('details').open=true")
                async with page.expect_download() as event:await page.locator('#population-download').click()
                download=await event.value;file=out/f'{name}_{label}.csv';await download.save_as(file)
                rows=list(csv.DictReader(file.open()))
                allocated=float(next(r['allocated_people'] for r in rows if r['province']=='TOTAL ALLOCATED'))
                unallocated=float(next(r['allocated_people'] for r in rows if r['province']=='UNALLOCATED'))
                regions=[r for r in rows if r['province'] not in ['TOTAL ALLOCATED','UNALLOCATED']]
                assert abs(sum(float(r['allocated_people']) for r in regions)-allocated)<.02
                assert abs(allocated+unallocated-requested)<.02
                return dict(allocated=allocated,unallocated=unallocated,provinces=len(regions))
            await ready('20 M supplied')
            assert await page.locator('#occupation-control').is_hidden()
            assert await page.locator('#disease-control').is_visible()
            assert await page.locator('#population-controls').is_visible()
            assert await page.locator('#harvest-section').is_hidden()
            initial=await census('markets_20m',20000000)
            original=await page.locator('#base').get_attribute('src')
            await page.locator('#population-budget').fill('10');await page.locator('#population-budget').dispatch_event('change')
            await ready('10 M supplied');assert await page.locator('#base').get_attribute('src')!=original
            low=await census('markets_10m',10000000);assert low['allocated']<initial['allocated']
            await page.locator('#population-pattern').select_option('dispersed');await ready('10 M supplied')
            await layer('shift');assert 'Even occupation' in await page.locator('#legend').inner_text()
            dispersed=await census('dispersed_10m',10000000)
            await layer('headroom');await layer('pressure')
            await page.locator('#disease').select_option('absent');await ready('10 M supplied')
            assert 'No malaria penalty' in await page.locator('#legend').inner_text()
            await page.locator('#population-budget').fill('500');await page.locator('#population-budget').dispatch_event('change')
            await ready('500 M supplied');high=await census('over_capacity_500m',500000000)
            assert high['unallocated']>100000000
            assert 'remain outside' in await page.locator('#population-balance').inner_text()
            await page.locator('#population-budget').fill('20');await page.locator('#population-budget').dispatch_event('change')
            await ready('20 M supplied')
            await page.locator('#population-provinces button').first.click()
            assert await page.locator('#province-overlay polygon').count()>0
            await page.locator('#population-clear').click();assert await page.locator('#province-overlay polygon').count()==0
            for key in ['travel','attraction']:
                await layer(key);assert await page.locator('#settlement-controls').is_hidden()
                assert await page.locator('#population-controls').is_hidden()
            await layer('density')
            for link in await page.locator('.atlas-nav a').all():
                href=await link.get_attribute('href')
                if '_fit/' in href:assert 'population=20000000' in href and 'pattern=dispersed' in href
            await page.reload(wait_until='domcontentloaded');await ready('20 M supplied')
            assert await page.locator('#population-budget').input_value()=='20'
            assert await page.locator('#population-pattern').input_value()=='dispersed'
            await page.locator('#population-pattern').select_option('markets');await ready('20 M supplied')
            await page.locator('.plate').screenshot(path=str(out/f'{name}_population.png'))
            await page.set_viewport_size({'width':390,'height':844});await layer('pressure')
            await page.locator('#population-provinces').evaluate("e=>e.closest('details').open=true")
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert await page.locator('#occupation-control').is_hidden()
            assert await page.locator('#layers button:visible').count()==6
            assert 'NaN' not in await page.locator('#population-section').inner_text()
            await page.screenshot(path=str(out/f'{name}_mobile.png'),full_page=True)
            assert not errors,errors
            results.append(dict(atlas=name,status='passed',page_errors=errors,map_modes=6,initial=initial,low_budget=low,dispersed=dispersed,over_capacity=high,
                                controls='passed',province_highlight='passed',saved_link='passed',mobile='passed'))
            await page.close()
        await browser.close()
    (out/'browser_checks.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',default='http://127.0.0.1:8003');ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);asyncio.run(check(a.base,a.out))
