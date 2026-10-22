"""Browser integration check for locally served active atlas variants.

Requires optional Playwright and Chromium. Start a server in the repository,
then pass atlas directories as URL paths (e.g. atlases/free_fit).
"""
import argparse
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def check(paths, base, out):
    results=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for path in paths:
            context=await browser.new_context(viewport={'width':1440,'height':1100},
                permissions=['clipboard-read','clipboard-write'])
            page=await context.new_page();errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.goto(base.rstrip('/')+'/'+path.strip('/')+'/',wait_until='domcontentloaded')
            await page.locator('#layer-whittaker').wait_for(timeout=60000)
            await page.locator('#layer-whittaker').click()
            await page.wait_for_function("document.querySelector('#base').complete && document.querySelector('#base').naturalWidth > 0 && document.querySelector('#base').src.includes('whittaker.webp')")
            assert await page.locator('#legend').get_by_text('Climate diagram',exact=True).count()==1
            assert await page.locator('#layer-whittaker').get_attribute('aria-pressed')=='true'
            # Named-place search exercises biome lookup and seasonally corrected station series.
            meta=await page.evaluate("fetch('data/atlas.json').then(r=>r.json())")
            if any(layer['id']=='biome_targets' for layer in meta['layers']):
                await page.locator('#layer-biome_targets').click()
                await page.wait_for_function("document.querySelector('#base').complete && document.querySelector('#base').src.includes('biome_targets.webp')")
                assert 'Proposed target-to-biome' in await page.locator('#legend').inner_text()
                await page.locator('.plate').screenshot(path=str(out/(Path(path).name+'_targets.png')))
                await page.locator('#layer-biome_match').click()
                await page.wait_for_function("document.querySelector('#base').complete && document.querySelector('#base').src.includes('biome_match.webp')")
                assert 'Allowed biome' in await page.locator('#legend').inner_text()
                await page.locator('#layer-whittaker').click()
            town=meta['places'][0]['name']
            await page.locator('#find-input').fill(town)
            await page.locator('#find-form').evaluate('(form)=>form.requestSubmit()')
            await page.wait_for_function("document.querySelector('#kdesc').textContent.includes('Whittaker:')")
            assert 'NaN' not in await page.locator('#readouts').inner_text()
            await page.locator('#searchtoggle').click()
            await page.locator('.plate').screenshot(path=str(out/(Path(path).name+'_biomes.png')))
            await page.locator('#layer-t_month').click()
            await page.locator('#mslider').fill('6')
            await page.locator('#mslider').dispatch_event('input')
            await page.wait_for_function("document.querySelector('#base').complete && document.querySelector('#base').naturalWidth > 0")
            await page.set_viewport_size({'width':390,'height':844})
            await page.locator('#layer-whittaker').click()
            await page.screenshot(path=str(out/(Path(path).name+'_mobile.png')))
            assert not errors,errors
            results.append(dict(atlas=path,layer_count=len(meta['layers']),town=town,page_errors=errors,status='passed',
                                biome_target_layers=any(layer['id']=='biome_targets' for layer in meta['layers'])))
            await context.close()
        await browser.close()
    (out/'browser_checks.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlases',nargs='+')
    ap.add_argument('--base',default='http://127.0.0.1:8000');ap.add_argument('--out',required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    asyncio.run(check(a.atlases,a.base,out))
