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
            await page.locator('#layer-whittaker').wait_for(state='attached',timeout=60000)
            await page.wait_for_function("document.querySelector('#station-h').textContent !== '—'", timeout=60000)
            assert await page.locator('#settlement-controls').is_hidden()
            async def layer(id):
                button=page.locator('#layer-'+id)
                if await page.locator('#map-topic').count():
                    await page.locator('#map-topic').select_option(await button.get_attribute('data-topic'))
                await button.click()
            async def loaded(fragment):
                await page.wait_for_function("fragment => {const im=document.querySelector('#base');return im.complete && im.naturalWidth>0 && im.src.includes(fragment)}",arg=fragment)

            await layer('whittaker')
            await page.wait_for_function("document.querySelector('#base').complete && document.querySelector('#base').naturalWidth > 0 && document.querySelector('#base').src.includes('whittaker.webp')")
            assert await page.locator('#legend').get_by_text('Climate diagram',exact=True).count()==1
            assert await page.locator('#layer-whittaker').get_attribute('aria-pressed')=='true'
            # Named-place search exercises biome lookup and seasonally corrected station series.
            meta=await page.evaluate("fetch('data/atlas.json').then(r=>r.json())")
            if meta.get('reach',{}).get('trade',{}).get('model')=='inbound-directed':
                assert 'Directed markets · 3 trade views.' in await page.locator('#atlas-data-status').inner_text()
            if any(layer['id']=='biome_targets' for layer in meta['layers']):
                await layer('biome_targets')
                await page.wait_for_function("document.querySelector('#base').complete && document.querySelector('#base').src.includes('biome_targets.webp')")
                assert 'Proposed target-to-biome' in await page.locator('#legend').inner_text()
                await page.locator('.plate').screenshot(path=str(out/(Path(path).name+'_targets.png')))
                await layer('biome_match')
                await page.wait_for_function("document.querySelector('#base').complete && document.querySelector('#base').src.includes('biome_match.webp')")
                assert 'Allowed biome' in await page.locator('#legend').inner_text()
                await layer('whittaker')
            town=meta['places'][0]['name']
            await page.locator('#find-input').fill(town)
            await page.locator('#find-form').evaluate('(form)=>form.requestSubmit()')
            await page.wait_for_function("document.querySelector('#kdesc').textContent.includes('Whittaker:')")
            assert 'NaN' not in await page.locator('#readouts').inner_text()
            await page.locator('#searchtoggle').click()
            await page.locator('.plate').screenshot(path=str(out/(Path(path).name+'_biomes.png')))
            await layer('t_month')
            await page.locator('#mslider').fill('6')
            await page.locator('#mslider').dispatch_event('input')
            await page.wait_for_function("document.querySelector('#base').complete && document.querySelector('#base').naturalWidth > 0")
            harvest_checks=None
            if meta.get('harvest'):
                await layer('land_density');await loaded('land_density_central_endemic.webp')
                assert await page.locator('#occupation-control').is_visible()
                assert await page.locator('#disease-control').is_visible()
                assert not await page.locator('#harvest-section').is_hidden()
                original=await page.locator('#harvest-totals').inner_text()
                await page.locator('#occupation').select_option('core')
                await loaded('land_density_core_endemic.webp')
                assert await page.locator('#harvest-totals').inner_text()!=original
                assert 'Settled core' in await page.locator('#legend').inner_text()
                await page.locator('#disease').select_option('absent')
                await loaded('land_density_core_absent.webp')
                assert 'NaN' not in await page.locator('#harvest-readouts').inner_text()
                await page.locator('.plate').screenshot(path=str(out/(Path(path).name+'_density.png')))
                await layer('land_livability');await loaded('land_livability_absent.webp')
                assert await page.locator('#occupation-control').is_hidden()
                assert await page.locator('#disease-control').is_visible()
                await layer('land_crop');await loaded('land_crop.webp')
                assert await page.locator('#settlement-controls').is_hidden()
                assert 'second crop' in await page.locator('#legend').inner_text()
                await page.locator('#province-sort').evaluate("el=>el.closest('details').open=true")
                await page.locator('#province-sort').select_option('wealth')
                await page.locator('#province-rows button').first.click()
                assert await page.locator('#province-overlay polygon').count()>0
                await page.locator('#province-clear').click()
                assert await page.locator('#province-overlay polygon').count()==0
                await layer('land_density')
                await page.locator('#occupation').select_option('central')
                await page.locator('#disease').select_option('endemic')
                await layer('land_density');await loaded('land_density_central_endemic.webp')
                assert await page.locator('#harvest-totals').inner_text()==original
                visible=await page.locator('#layers button:visible').count()
                assert visible<=7,visible
                assert 'layer=land_density' in page.url and 'occupation=central' in page.url
                for link in await page.locator('.atlas-nav a').all():
                    href=await link.get_attribute('href')
                    if '_fit/' in href: assert '#layer=land_density' in href
                await page.reload(wait_until='domcontentloaded')
                await page.wait_for_function("document.querySelector('#station-h').textContent !== '—'",timeout=60000)
                await loaded('land_density_central_endemic.webp')
                assert await page.locator('#layer-land_density').get_attribute('aria-pressed')=='true'
                harvest_checks=dict(scenarios='passed',provinces='passed',deep_links='passed',visible_layer_buttons=visible)
            political_checks=None
            variant_layer=next((item for item in meta['layers'] if item['id']=='reach_defacto' and item.get('variants')),None)
            if variant_layer:
                await layer('reach_defacto')
                assert await page.locator('#variant-controls').is_visible()
                assert await page.locator('#settlement-controls').is_hidden()
                options=variant_layer['variants']['options']
                for option in options:
                    await page.locator('#variant').select_option(option['value'])
                    await loaded(option['file'])
                    assert 'variant='+option['value'] in page.url
                await page.reload(wait_until='domcontentloaded')
                await loaded(options[-1]['file'])
                assert await page.locator('#variant').input_value()==options[-1]['value']
                await page.locator('.plate').screenshot(path=str(out/(Path(path).name+'_political.png')))
                await layer('reach_trade')
                await loaded('reach_trade.webp')
                trade=next(item for item in meta['layers'] if item['id']=='reach_trade')
                trade_options=trade.get('variants',{}).get('options',[])
                if trade_options:
                    assert await page.locator('#variant-controls').is_visible()
                    for option in trade_options:
                        await page.locator('#variant').select_option(option['value'])
                        await loaded(option['file'])
                        assert await page.locator('#settlement-controls').is_hidden()
                    await page.reload(wait_until='domcontentloaded')
                    await loaded(trade_options[-1]['file'])
                    assert await page.locator('#variant').input_value()==trade_options[-1]['value']
                else:
                    assert await page.locator('#variant-controls').is_hidden()
                await layer('whittaker')
                assert await page.locator('#variant-controls').is_hidden()
                political_checks=dict(variants=len(options),trade_variants=len(trade_options),deep_links='passed',trade='passed',conditional_controls='passed')
            if meta.get('harvest'):
                await page.locator('#province-sort').evaluate("el=>el.closest('details').open=true")
                await page.locator('#earth-reference').evaluate("el=>el.closest('details').open=true")
            await page.set_viewport_size({'width':390,'height':844})
            await layer('whittaker')
            await page.screenshot(path=str(out/(Path(path).name+'_mobile.png')))
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'Page overflows mobile viewport'
            for button in await page.locator('#layers button:visible').all():
                assert (await button.bounding_box())['width']>0
            assert not errors,errors
            results.append(dict(atlas=path,layer_count=len(meta['layers']),town=town,page_errors=errors,status='passed',
                                biome_target_layers=any(layer['id']=='biome_targets' for layer in meta['layers']),harvest=harvest_checks,
                                political=political_checks))
            await context.close()
        await browser.close()
    (out/'browser_checks.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlases',nargs='+')
    ap.add_argument('--base',default='http://127.0.0.1:8000');ap.add_argument('--out',required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    asyncio.run(check(a.atlases,a.base,out))
