"""Read-only source-store throughput and local zero-loss meal-loss channels.

Never imports or calls a food kernel. All quantities derive from frozen paths.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_storage_throughput_20261117'
PARENT=ROOT/'output/urban_storage_loss_20261117'
BASE=ROOT/'output/urban_earth_monthly_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/storage_throughput_audit.json'
KCAL=912500.
LABELS=['loss05_days365','loss05_days90','loss00_days365','loss00_days90']


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())
def total(values):return math.fsum(np.asarray(values).ravel())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def table(name,rows):
    with (OUT/name).open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def gate():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    q=read(PARENT/'qualification.json');assert q['status']=='passed_six_fixed_infrastructure_storage_loss_cases_and_exact_original_controls'
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in q[key].items():assert sha(prefix/name)==digest,name
    sources={str(path.relative_to(ROOT)):sha(path) for path in [PLAN,PARENT/'qualification.json',Path(__file__)]}
    for reading in ['central','low']:
        for label in LABELS:
            path=(BASE/'cases'/reading if label==LABELS[0] else PARENT/'cases'/f'{reading}_{label}')/'fields.npz'
            sources[str(path.relative_to(ROOT))]=sha(path)
    return sources,q['protected_sha256']


def load(reading,label):
    folder=BASE/'cases'/reading if label==LABELS[0] else PARENT/'cases'/f'{reading}_{label}'
    r=read(folder/'results.json');assert sha(folder/'fields.npz')==r['fields_sha256']
    return dict(np.load(folder/'fields.npz'))


def main():
    sources,protected=gate();OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'results.json').exists(),'Preserve completed read-only audit'
    source_rows=[];city_rows=[];month_rows=[];summaries=[];compact={};maximum=0.
    for reading in ['central','low']:
        cases={label:load(reading,label) for label in LABELS};baseline=cases[LABELS[0]]
        reference=baseline['marketed'].sum(0)
        a=dict(np.load(ROOT/f'output/urban_seasonal_transfer_20261116/wind_1981/prepared/low_{reading}.npz'))
        for label,c in cases.items():
            loss=.05 if label.startswith('loss05') else 0.;days=365 if label.endswith('365') else 90
            capacity=reference if days==365 else reference*90/365
            h=c['marketed'];dispatch=c['dispatch'];stocks=c['export_food__stock_path'];paid=c['departures']
            available=stocks[:-1]+h;eaten=np.minimum(available,dispatch)
            extra=np.maximum(available-eaten-capacity,0);held=np.minimum(available-eaten,capacity)
            lost=held*-np.expm1(np.log1p(-loss)/np.full(12,365/12).sum()*(365/12))
            annual=h.sum(0);departure=paid.sum(0);spoil=lost.sum(0);spill=extra.sum(0);change=stocks[-1]-stocks[0]
            scale=np.maximum(1,np.maximum(annual,dispatch.sum(0)));tol=1e-10*scale+100*np.finfo(float).eps*scale
            for actual,expected in [(paid,eaten),(c['export_food__overflow'],spill),(c['export_food__spoiled'],spoil),(stocks[1:],held-lost)]:
                error=abs(actual-expected);assert np.all(error<=tol)
                maximum=max(maximum,float((error/tol).max()))
            residual=annual-departure-spoil-spill-change
            assert np.all(abs(residual)<=tol)
            pulse=(h>0).sum(0);open_quarters=(c['owner']>=0)&(c['retention']>0)
            open_months=open_quarters.sum(0)*3
            eligible=(loss==0)&(pulse==1)&(open_months==12)
            bound=np.minimum(annual,annual/12+capacity)
            if eligible.any():assert np.all(abs(departure[eligible]-bound[eligible])<=tol[eligible])
            maxbound=float((abs(departure-bound)[eligible]/tol[eligible]).max()) if eligible.any() else 0.
            summary=dict(reading=reading,scenario=label,loss_fraction_year=loss,commercial_days=days,
                marketed_person_years=total(annual)/KCAL,departures_person_years=total(departure)/KCAL,
                dispatch_request_person_years=total(dispatch)/KCAL,unfunded_dispatch_person_years=total(c['export_food__unmet'])/KCAL,
                commercial_spoilage_person_years=total(spoil)/KCAL,commercial_overflow_person_years=total(spill)/KCAL,
                stock_change_person_years=total(change)/KCAL,grain_residual_person_years=total(residual)/KCAL,
                one_pulse_all_open_origins=int(eligible.sum()),bound_marketed_share=total(annual[eligible])/max(1,total(annual)),
                bound_departure_share=total(departure[eligible])/max(1,total(departure)),maximum_bound_tolerance_fraction=maxbound)
            summaries.append(summary)
            # Compact one row for every physical source,including zero grain origins.
            for i,source in enumerate(c['source_indices']):
                source_rows.append(dict(reading=reading,scenario=label,source=int(source),marketed_pulses=int(pulse[i]),
                    route_open_months=int(open_months[i]),commercial_capacity_person_years=float(capacity[i]/KCAL),
                    marketed_person_years=float(annual[i]/KCAL),departures_person_years=float(departure[i]/KCAL),
                    spoilage_person_years=float(spoil[i]/KCAL),overflow_person_years=float(spill[i]/KCAL),
                    stock_change_person_years=float(change[i]/KCAL),ledger_residual_kcal=float(residual[i]),
                    one_pulse_zero_loss_bound_applicable=bool(eligible[i]),
                    bound_departures_person_years=float(bound[i]/KCAL) if eligible[i] else ''))
            # Public compact audit vectors avoid tracking the large monthly caches.
            for key,value in dict(source=c['source_indices'],capacity=capacity,marketed=annual,departures=departure,
                                  spoiled=spoil,overflow=spill,stock_change=change,pulses=pulse,open_months=open_months,bound_eligible=eligible).items():
                compact[reading+'_'+label+'_'+key]=value
        old=cases['loss05_days90'];new=cases['loss00_days90']
        delta=(new['town_food__consumed']-old['town_food__consumed'])/KCAL
        losing=np.flatnonzero(delta< -1e-7);assert len(losing)==(11 if reading=='central' else 8)
        for i in losing:
            def difference(key):return float((new[key][i]-old[key][i])/KCAL)
            direct=float((new['direct'][:,i]-old['direct'][:,i]).sum()/KCAL)
            received=float((new['inter_received'][:,i]-old['inter_received'][:,i]).sum()/KCAL)
            spoil=difference('town_food__spoiled');spill=difference('town_food__overflow')
            initial=difference('town_food__initial_stock');final=difference('town_food__final_stock')
            prediction=direct+received-spoil-spill+initial-final
            tolerance=1e-10*max(1,old['town_food__harvested'][i],new['town_food__harvested'][i],old['town_food__needed'][i])/KCAL
            assert abs(prediction-delta[i])<=tolerance
            node=int(a['nodes'][i]);city_rows.append(dict(reading=reading,city_index=int(i),cell=node,
                lat=float(a['lat'].ravel()[node]),lon=float(a['grid_lon'].ravel()[node]),requested_people=float(old['request'][i]),
                delta_meals_person_years=float(delta[i]),delta_percentage_points=float(100*delta[i]/old['request'][i]),
                delta_direct_arrivals_person_years=direct,delta_intertown_arrivals_person_years=received,
                delta_spoilage_person_years=spoil,delta_overflow_person_years=spill,
                delta_initial_stock_person_years=initial,delta_final_stock_person_years=final,
                delta_intertown_exports_person_years=float((new['inter_exported'][:,i]-old['inter_exported'][:,i]).sum()/KCAL),
                old_protected_exporter=bool(old['protected_exporters'][i]),new_protected_exporter=bool(new['protected_exporters'][i]),
                meal_delta_ledger_residual_person_years=float(delta[i]-prediction)))
            for month in range(12):
                month_rows.append(dict(reading=reading,cell=node,month=month+1,
                    delta_meals_person_years=float((old['town_food__unmet_path'][month,i]-new['town_food__unmet_path'][month,i])/KCAL),
                    delta_direct_arrivals_person_years=float((new['direct'][month,i]-old['direct'][month,i])/KCAL),
                    delta_intertown_arrivals_person_years=float((new['inter_received'][month,i]-old['inter_received'][month,i])/KCAL)))
    table('sources.csv',source_rows);table('summary.csv',summaries);table('city_losses.csv',city_rows);table('city_loss_months.csv',month_rows)
    np.savez_compressed(OUT/'source_accounting.npz',**compact)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    result=dict(status='completed_read_only_saved_storage_throughput_and_local_loss_audit_pending_review',
        sources_sha256=sources,protected_sha256=protected,summary=summaries,source_rows=len(source_rows),
        city_loss_rows=len(city_rows),city_loss_month_rows=len(month_rows),maximum_ledger_tolerance_fraction=maximum,
        food_kernel_calls=0,new_food_scenarios=0,new_observations=False,actual_population_changed=False,
        new_fit=False,new_validation_claim=False,adopt=False,
        files_sha256={path.name:sha(path) for path in OUT.iterdir() if path.is_file()})
    write(OUT/'results.json',result);print('Completed read-only audit',len(source_rows),'sources,',len(city_rows),'local losses',flush=True)


if __name__=='__main__':main()
