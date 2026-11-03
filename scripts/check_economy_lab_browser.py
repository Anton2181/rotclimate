"""Check the launcher-linked economy lab and its actual prototype receipts."""
from pathlib import Path
import argparse
import csv
import io
import json
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1000));errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.base+'/atlases/',wait_until='domcontentloaded')
        page.get_by_role('link',name='Food, farming and society →',exact=True).click()
        page.get_by_role('heading',name='Food, farming and society',exact=True).wait_for()
        assert page.locator('.status').all_inner_texts()==['Experimental calendars and food stocks','Agronomic validation pending']
        older=page.locator('details > summary').filter(has_text='Earlier crop-calendar and reserve experiments')
        older.focus();page.keyboard.press('Enter')
        receipt=page.request.get(args.base+'/atlases/economy_lab/data/receipt.json').json()
        assert receipt['status']=='numerical_prototype' and not receipt['production_atlas_changed']
        assert receipt['results']['One harvest']['shortfall_days']==164
        assert receipt['results']['Two equal harvests']['shortfall_days']==0
        assert receipt['results']['Even daily supply (control)']['shortfall_days']==0
        calendar=page.request.get(args.base+'/atlases/economy_lab/data/calendar_receipt.json').json()
        assert calendar['status']=='diagnostic_only' and not calendar['production_atlas_changed']
        assert calendar['sample_cells']==4096 and calendar['rotation_changed_mix_cells']==226
        assert calendar['alternative_tied_calendar_pair_cells']==58
        assert calendar['maximum_annual_crop_yield_drift']==0
        page.get_by_role('heading',name='Choose crop seasons together',exact=True).wait_for()
        sequence=page.request.get(args.base+'/atlases/economy_lab/data/sequence_receipt.json').json()
        reserve=page.request.get(args.base+'/atlases/economy_lab/data/storage_receipt.json').json()
        assert sequence['scenarios']['0']['improved_cells']==113 and not sequence['independent_agronomic_validation']
        assert reserve['calendar_dependent_reserve_cells']==162 and reserve['unknown_perennial_timing_cells']==5
        assert not reserve['production_atlas_changed']
        observed=page.request.get(args.base+'/atlases/economy_lab/data/observed_calendar_result.json').json()
        assert observed['unflagged_records']==472 and observed['source_flagged_records']==9
        assert observed['groups']['wheat · Winter']['outside_envelope']['0.0']['count']==55
        assert not observed['parameters_tuned'] and not observed['full_agronomic_validation']
        page.get_by_role('heading',name='Daily cereal development: test the mechanisms',exact=True).wait_for()
        cereal=page.request.get(args.base+'/atlases/economy_lab/data/cereal_development.json').json()
        scores=cereal['result']['scores']
        assert scores['published_heat_only']['evaluation']['country_mean_penalized_error_days']<scores['legacy_heat_only']['evaluation']['country_mean_penalized_error_days']
        assert scores['selected_global']['evaluation']['nonmature_records']==2
        food=page.request.get(args.base+'/atlases/economy_lab/data/seasonal_food_system.json').json()
        assert len(food['cases'])==6 and not food['population_predicted']
        assert food['cases']['Ample farm storage']['town_consumed']>food['cases']['Ample storage, seasonal closure']['town_consumed']
        for case in food['cases'].values():
            assert abs(case['food_ledger_residual'])<1e-6 and abs(case['water_ledger_residual'])<1e-6
        page.get_by_role('heading',name='What observed crop calendars reveal',exact=True).wait_for()
        page.get_by_role('heading',name='Seasonal freight routes on the current world',exact=True).wait_for()
        freight=page.request.get(args.base+'/atlases/economy_lab/data/freight_corridors.json').json()
        assert not freight['production_atlas_changed'] and len(freight['routes'])==24
        assert all(abs(sum(r['leg_days'])-r['travel_days'])<1e-7 for r in freight['routes'])
        assert all(abs(r['annual_food_ledger_residual'])<1e-7 for r in freight['provisioning'].values())
        months=page.locator('details > summary').filter(has_text='All 12 months and both directions')
        months.focus();page.keyboard.press('Enter')
        audit=page.request.get(args.base+'/atlases/economy_lab/data/parallel_freight.json').json()
        assert not audit['production_atlas_changed'] and len(audit['pair_samples'])==360
        assert max(r['legacy_cost']-r['alternative_cost'] for r in audit['pair_samples'])==0
        assert page.locator('tbody tr').count()==40
        summary=page.locator('details > summary').filter(has_text='Earlier checks:');summary.focus();page.keyboard.press('Enter')
        page.get_by_role('heading',name='Before harvest calendars can drive maps',exact=True).wait_for()
        for picture in page.locator('img').all():
            page.wait_for_function('(el)=>el.complete && el.naturalWidth>0',arg=picture.element_handle())
        downloads=[]
        for link in page.locator('a[download]').all():
            response=page.request.get(link.evaluate('(el)=>el.href'))
            assert response.ok and response.headers['cache-control']=='no-store'
            if link.evaluate('(el)=>el.href').endswith('.csv'):
                rows=list(csv.DictReader(io.StringIO(response.text())))
                assert len(rows)==4096
                assert sum(row['minimum_reserve_days_5day_clock']=='' for row in rows)==5
                assert sum(row['unknown_perennial_timing']=='True' for row in rows)==5
            else:
                response.json()
            downloads.append(link.inner_text())
        assert len(downloads)==13
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for viewport in [dict(width=1440,height=1000),dict(width=390,height=844)]:
                page.set_viewport_size(viewport)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                if theme=='light' and viewport['width']==1440:
                    page.screenshot(path=str(args.out/'economy_lab.png'),full_page=True)
        assert not errors,errors;browser.close()
    result=dict(status='passed',hub_link='passed',prototype_receipt='passed',calendar_receipt='passed',
        joint_calendar_and_storage_receipts='passed',observed_calendar_diagnostic='passed',
        daily_cereal_evaluation='passed',closed_water_food_provisioning='passed',same_path_world_routes='passed',
        csv_unknowns_preserved=True,earlier_checks_keyboard='passed',downloads=downloads,
        viewports=['1440x1000','390x844'],themes=['light','dark'],mobile_overflow=False,page_errors=errors)
    (args.out/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
