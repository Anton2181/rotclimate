"""Check new research panels, aggregate downloads and preserved mobile layouts."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8766');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True);errors=[];links=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport=dict(width=1440,height=1000));page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.base+'/atlases/earth_evidence/',wait_until='domcontentloaded')
        assert 'RESEARCH UPDATED 11 NOVEMBER 2026' in page.locator('header').inner_text()
        for id_,rows in [('settlement-history-boundary',10),('settlement-phase-evidence',5)]:
            detail=page.locator('#'+id_);assert detail.get_attribute('open') is None
            detail.locator('summary').focus();page.keyboard.press('Enter')
            assert detail.locator('tbody tr').count()==rows
            for link in detail.locator('a').all():
                url=link.evaluate('(el)=>el.href');response=page.request.get(url)
                assert response.ok and not url.endswith('.csv'),url
                if url.endswith('settlement_history_boundary.json'):
                    result=response.json();assert not result['adopt'] and len(result['rows'])==100
                    assert result['overlap_controls_exact']==20 and result['Q_gain_over_prior_adaptive']==0
                if url.endswith('settlement_phase_evidence.json'):
                    audit=response.json();assert audit['records_without_dated_role_intervals']==3652
                    assert audit['phase_status']['changes_require_review']==10
                    assert not audit['identity']['physical_place_merges_performed']
                links.append(url)
        assert len(links)==10
        figure=page.locator('#history-boundary-figure');figure.scroll_into_view_if_needed()
        assert figure.evaluate('(el)=>el.complete && el.naturalWidth===2100')
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            for width in [390,344]:
                page.set_viewport_size(dict(width=width,height=844))
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    assert not errors,errors
    receipt=dict(status='passed',keyboard_open=True,default_collapsed=True,history_rows=10,phase_rows=5,
        aggregate_links=links,figure_loaded=True,light_dark_mobile=True,page_errors=errors)
    (args.out/'checks.json').write_text(json.dumps(receipt,indent=2)+'\n');print('New research panels,10 links,figure and mobile/dark layouts pass.')


if __name__=='__main__':main()
