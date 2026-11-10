"""Check the collapsed S2 preparation panel and aggregate-only downloads."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True);errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1100));page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.base+'/atlases/earth_evidence/',wait_until='domcontentloaded')
        detail=page.locator('#rural-preparation');assert detail.get_attribute('open') is None
        detail.locator(':scope > summary').focus();page.keyboard.press('Enter')
        page.wait_for_function('document.querySelector("#rural-preparation").open')
        assert detail.locator('#rural-preparation-results tbody tr').count()==5
        assert '3,652' in detail.inner_text() and '608' in detail.inner_text()
        role=detail.locator('#rural-role-evidence');assert role.get_attribute('open') is None
        role.locator('summary').focus();page.keyboard.press('Enter')
        assert role.locator('tbody tr').count()==11
        assert '153 records' in role.inner_text() and 'not physical-place merges' in role.inner_text()
        coord=detail.locator('#rural-coordinate-evidence');assert coord.get_attribute('open') is None
        coord.locator('summary').focus();page.keyboard.press('Enter')
        assert 'all three references' in coord.inner_text() and 'median 54 m' in coord.inner_text()
        figure=coord.locator('img');figure.scroll_into_view_if_needed()
        assert figure.evaluate('(el)=>el.complete && el.naturalWidth===1600')
        links=[]
        for link in detail.locator('a').all():
            url=link.evaluate('(el)=>el.href');response=page.request.get(url);assert response.ok,url
            assert not url.endswith('.csv')
            if url.endswith('roman_rural_preparation.json'):
                audit=response.json();assert not audit['model_scores_computed'] and not audit['target_maps_generated']
            if url.endswith('source_csv_correction.json'):
                receipt=response.json();assert receipt['primary_join_and_axis_findings_unchanged']
                assert not receipt['climate_and_settlement_results_changed']
            if url.endswith('roman_rural_roles.json'):
                audit=response.json();assert audit['unknown_source_labels']=={}
                assert not audit['population_allocated'] and not audit['model_scores_computed']
                assert audit['association_blocking']['all_keys_contained']
            if url.endswith('roman_rural_coordinates.json'):
                audit=response.json();assert audit['all_declared_anchors_retained']
                assert not audit['settlement_climate_model_scored'] and not audit['production_adopted']
                assert audit['hypotheses']['X_easting_Y_northing_metres']['reference_points_within_1km']==8
            links.append(url)
        assert len(links)==15
        detail.screenshot(path=str(args.out/'rural_preparation_desktop.png'))
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme);page.set_viewport_size(dict(width=390,height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors,errors
    result=dict(status='passed',default_collapsed=True,keyboard_open=True,aggregate_links=links,
        no_raw_tables=True,no_model_evaluation=True,role_channels=11,coordinate_figure_loaded=True,nested_keyboard_open=True,
        light_dark_mobile=True,page_errors=errors)
    (args.out/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
