"""Independent scalar food integration and original cargo/clock reconstruction."""
import csv
import gzip
import io
import json
from math import exp, expm1, fsum, log1p
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/network_visit_delivery_timing_20261112'
YEAR = ROOT / 'output/network_visit_year_complete_20261112'


def integrate(times, cargo, rate, cap, initial, *, monthly=False):
    h = -log1p(-.05) / 365; stock = initial; peak = initial
    eaten = []; missing = []; losses = []; spilled = []; days = []; previous = 0.
    if monthly:
        for q in cargo:
            available = stock + q; meal = min(available, rate*365/12)
            remaining = available - meal; spill = max(remaining-cap, 0.); remaining = min(remaining, cap)
            lost = remaining * -expm1(-h*365/12); stock = remaining-lost; peak = max(peak, remaining)
            eaten.append(meal); missing.append(rate*365/12-meal); losses.append(lost); spilled.append(spill)
            days.append(365/12 if rate*365/12-meal > 1e-10*max(1.,fsum(cargo),rate*365) else 0.)
    else:
        for t, q in list(zip(times,cargo)) + [(365., 0.)]:
            dt = float(t)-previous
            until_empty = log1p(stock*h/rate)/h if rate else float('inf')
            duration = min(until_empty, dt)
            retained = stock * exp(-h*duration)
            meal = rate*duration
            after = max(0., retained + rate*expm1(-h*duration)/h)
            if until_empty <= dt: after = 0.
            lost = max(0., stock-after-meal)
            eaten.append(meal); missing.append(rate*(dt-duration)); losses.append(lost); days.append(dt-duration if rate else 0.)
            stock = after + float(q); spill = max(0.,stock-cap); spilled.append(spill); stock = min(stock,cap)
            peak = max(peak,stock); previous = float(t)
    eaten, missing, losses, spilled, days = map(fsum,(eaten,missing,losses,spilled,days))
    supply = fsum(cargo)
    return dict(initial_stock=initial,final_stock=stock,peak_stock=peak,harvested=supply,needed=rate*365,consumed=eaten,
        unmet=missing,spoiled=losses,overflow=spilled,shortfall_days=days,ledger_residual=fsum((initial,supply,-stock,-eaten,-losses,-spilled)),periodic_residual=stock-initial)


def main():
    r = json.loads((OUT / 'results.json').read_text()); y = dict(np.load(YEAR / 'fields.npz')); a = dict(np.load(OUT / 'fields.npz'))
    parent = json.loads((YEAR / 'results.json').read_text())
    for path,digest in {**r['sources'], **r['producers'], **r['unchanged_atlas_sha256']}.items(): assert sha(ROOT/path)==digest,path
    for path,digest in r['files_sha256'].items(): assert sha(OUT/path)==digest,path
    controls=json.loads((OUT/'controls.json').read_text());assert controls['status']=='passed_before_production' and controls['producers']==r['producers']
    checked_trips=0; checked_events=0; checked_inventories=0; largest_error=0.; independent_rows=[]
    provider_csv=list(csv.DictReader(io.StringIO(gzip.decompress((OUT/'providers.csv.gz').read_bytes()).decode())))
    csv_index={(v['case'],v['accounting'],int(v['provider'])):v for v in provider_csv};assert len(csv_index)==len(provider_csv)
    for case in parent['rows']:
        key,mode,pk=(case[k] for k in ('key','climate','parent_key'));scored=y[key+'__mandatory_complete'];policy=y[key+'__policy'];n=len(scored)
        x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'));f=dict(np.load(ROOT/'output/settlement_dispatch_seeded_20261112'/pk/'fields.npz'))
        recorded=dict(np.load(OUT/f'{key}_events.npz')); expected={}; bins=np.zeros((12,n)); total_raw=0
        for month in range(12):
            originals={}; selected=[]
            for pol,path in [(0,ROOT/'output/network_visit_calendar_20261112'/pk/f'collection_{month:02d}.npz'),(1,ROOT/'output/network_visit_joint_order_20261112'/key/f'calendar_{month:02d}.npz')]:
                c=np.load(path)
                for origin,serial,site,end in zip(c['collection_origin'].tolist(),c['collection_serial'].tolist(),c['collection_site'].tolist(),c['collection_end'].tolist()):
                    if scored[site] and policy[site]==pol:
                        assert x['owner'][origin]==site and 0<=end<7*365/12
                        identity=(origin,serial);assert identity not in originals;originals[identity]=site
                        q=min(120000.,f['origin_departures'][month,origin]-120000.*serial);assert q>0
                        time=((month+1)*365/12+end/7)%365
                        assert int(time*12/365)==(month+1)%12
                        expected.setdefault((site,time),[]).append(q*.95);bins[(month+1)%12,site]+=q*.95
                        total_raw+=1
            for origin in np.flatnonzero(scored[x['owner']]):
                count=int(f['origin_trips'][month,origin]);assert count==f['origin_trips'][month,origin]
                cargos=[]
                for serial in range(count):
                    assert originals.pop((int(origin),serial))==x['owner'][origin]
                    cargos.append(min(120000.,f['origin_departures'][month,origin]-120000.*serial))
                assert abs(fsum(cargos)-f['origin_departures'][month,origin])<=1e-6
            assert not originals
        np.testing.assert_allclose(bins,np.where(scored,f['arrivals'],0),rtol=1e-12,atol=1e-6)
        assert len(expected)==len(recorded['site'])
        for site,time,cargo,count in zip(recorded['site'],recorded['time'],recorded['cargo'],recorded['trips']):
            originals=expected.pop((int(site),float(time)));assert len(originals)==count
            assert abs(fsum(originals)-cargo)<=1e-7*max(1.,cargo)
        assert not expected and recorded['trips'].sum()==total_raw
        checked_trips+=total_raw;checked_events+=len(recorded['site'])
        offsets=np.searchsorted(recorded['site'],np.arange(n+1));summary={v:{} for v in 'ABC'}
        for site in np.flatnonzero(scored):
            rate=float(f['total'][site]*2500);cap=rate*90;sl=slice(offsets[site],offsets[site+1])
            for account,times,cargo in [('A',np.arange(12)*365/12,f['arrivals'][:,site]),('B',np.arange(12)*365/12,f['arrivals'][:,site]),('C',recorded['time'][sl],recorded['cargo'][sl])]:
                monthly=account=='A'
                def residual(initial):return integrate(times,cargo,rate,cap,initial,monthly=monthly)['periodic_residual']
                minimum=0. if residual(0.)<=1e-10*max(1.,rate*365) else brentq(residual,0.,cap,xtol=1e-7,rtol=1e-14)
                stored_initial=a[f'{key}__{account}__initial_stock'][site]
                assert abs(minimum-stored_initial)<=1e-8*max(1.,rate*365)
                values=integrate(times,cargo,rate,cap,float(stored_initial),monthly=monthly)
                csv_row=csv_index.pop((key,account,int(site)))
                assert int(csv_row['actor'])==x['actor'][site] and int(csv_row['year_policy'])==policy[site]
                for name,value in values.items():
                    actual=a[f'{key}__{account}__{name}'][site];error=abs(value-actual);largest_error=max(largest_error,error)
                    assert error<=2e-9*max(1.,rate*365,values['harvested']), (key,account,site,name,value,actual)
                    assert float(csv_row[name])==actual
                    summary[account].setdefault(name,[]).append(actual)
                assert abs(values['consumed']+values['unmet']-values['needed'])<=1e-8*max(1.,values['needed'])
                assert abs(values['ledger_residual'])<=1e-8*max(1.,values['needed'])
                assert abs(values['periodic_residual'])<=1e-8*max(1.,values['needed'])
                assert 0<=values['initial_stock']<=cap and values['peak_stock']<=cap
                no_shortage=values['unmet']<=1e-8*max(1.,values['needed']);assert bool(a[f'{key}__{account}__no_shortage'][site])==no_shortage
                assert csv_row['no_shortage']==str(no_shortage)
                checked_inventories+=1
        for account in 'ABC':
            row=next(v for v in r['rows'] if v['key']==key and v['accounting']==account)
            mask=scored;assert row['scored_providers']==int(mask.sum()) and row['unscored_providers']==int((~mask).sum())
            assert row['no_shortage_providers']==int(a[f'{key}__{account}__no_shortage'].sum())
            for name in ('initial_stock','final_stock','peak_stock','harvested','needed','consumed','unmet','spoiled','overflow'):
                assert abs(fsum(summary[account][name])-row[name])<=1e-7*max(1.,abs(row[name]))
            for actor in row['actors']:
                mask=scored & (x['actor']==actor['actor_index']);assert actor['scored_providers']==int(mask.sum())
                assert actor['no_shortage_providers']==int(a[f'{key}__{account}__no_shortage'][mask].sum())
                for name in summary[account]:assert abs(a[f'{key}__{account}__{name}'][mask].sum()-actor[name])<=1e-7*max(1.,abs(actor[name]))
            independent_rows.append(dict(key=key,accounting=account,scored_providers=row['scored_providers'],no_shortage_providers=row['no_shortage_providers']))
        for account in ('B','C'):
            np.testing.assert_allclose(a[f'{key}__{account}__harvested'][scored],f['arrivals'][:,scored].sum(0),rtol=1e-12,atol=1e-6)
        print('Independently checked',key,total_raw,'original trips',flush=True)
    assert not csv_index and len(independent_rows)==24
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),
        original_trip_identities_checked=checked_trips,aggregated_delivery_events_checked=checked_events,scalar_provider_inventories_checked=checked_inventories,
        scalar_initial_stocks_independently_bisected=True,original_one_bin_delay_preserved=True,transport_retention_once=True,matched_monthly_and_annual_supplies=True,
        independent_accounting_rows=independent_rows,max_scalar_field_difference=largest_error,all_provider_csv_fields_exact=True,all_actor_and_cohort_rows_checked=True,
        original_atlas_unchanged=True,scope='Destination-only cereal accounting;not source within-bin validation,crew ration/location accounting,complete diets,observed hunger or calibrated authority.'))


if __name__=='__main__':main()
