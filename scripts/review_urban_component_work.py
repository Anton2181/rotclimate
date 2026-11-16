"""Independent scalar source budgets and sorted-ledger annual grain allocation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_component_work_20261116'
PRIOR=ROOT/'output/urban_seasonal_transfer_20261116'
CAL=ROOT/'output/urban_earth_calendars_20261116'
KCAL=912500.
SHARES={'central':.3371937035110408,'low':.14049021985082757}


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def grain_flow(a,surplus,marketed_share):
    """Scatter source exports; independently ordered exporter/importer ledger."""
    request=a['residents'];local=np.zeros_like(request);sent=np.zeros_like(request)
    for season in range(4):
        fraction=np.maximum(1-a['dist'][season].astype(float)/270,0)
        ok=(a['owner'][season]>=0)&(fraction>0)
        exports=surplus[ok]*marketed_share/4
        np.add.at(local,a['owner'][season,ok],exports*fraction[ok]);np.add.at(sent,a['owner'][season,ok],exports)
    between=np.maximum(1-a['between'].astype(float)/270,0).mean(0);np.fill_diagonal(between,0)
    excess=np.maximum(local-request,0);deficit=np.maximum(request-local,0);received=np.zeros_like(request)
    sender,receiver=np.nonzero((between>0)&(excess[:,None]>0)&(deficit[None,:]>0))
    ledger=sorted(zip(sender.tolist(),receiver.tolist()),key=lambda pair:(-between[pair],pair[0],pair[1]))
    moves=[]
    for source,target in ledger:
        if excess[source]<=0 or deficit[target]<=0:continue
        leaving=min(excess[source],deficit[target]/between[source,target]);arriving=leaving*between[source,target]
        excess[source]-=leaving;deficit[target]-=arriving;received[target]+=arriving
        if deficit[target]<1e-9*max(1.,leaving):deficit[target]=0
        moves.append([source,target,leaving,arriving])
    return dict(fed=np.minimum(local,request)+received,direct=local,source_sent=sent,inter_received=received,
                shipments=np.array(moves).reshape(-1,4))


def main(hours):
    out=OUT/f'hours{hours}';r=read(out/'results.json')
    assert r['hours']==hours and r['fixed_shares_not_refitted'] and not r['seasonal_food_trial']
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',out),('protected_sha256',ROOT)]:
        for path,digest in r[key].items():assert sha(prefix/path)==digest,path
    for stage,archive in [('greek','greek_walls_20261114'),('low','supply_low_reading_20261114')]:
        receipt=read(OUT/'controls'/stage/'control.json')
        assert receipt['status']=='passed_original_mixed_work_whole_annual_result_bytes_exact'
        assert sha(OUT/'controls'/stage/'results.json')==receipt['results_sha256']==receipt['reference_sha256']
        assert (OUT/'controls'/stage/'results.json').read_bytes()==(ROOT/'output'/archive/'results.json').read_bytes()
        for path,digest in receipt['sources_sha256'].items():assert sha(ROOT/path)==digest,path
    c=dict(np.load(CAL/'calendars.npz'));source=c['source_indices'];towns=dict(np.load(out/'town_model.npz'))
    max_grain_error=0.;max_town_error=0.;cases={};source_cases=0;shipment_rows=0
    for reading in ['central','low']:
        a=dict(np.load(PRIOR/'wind_1981/prepared'/f'low_{reading}.npz'));b=dict(np.load(out/'cases'/f'{reading}.npz'))
        assert r['cases'][reading]['marketed_share']==SHARES[reading]
        potential=np.array([c['base_potential_kcal'],c['basin_potential_kcal']]);np.testing.assert_array_equal(potential,b['potential'])
        s=a['basin_share'].ravel()[source];arable=100*float(a['cell_km'])**2*a['arable'].ravel()[source]
        raw_area=np.array([arable*(1-s)*.36,arable*s*.95]);active_area=np.where(potential>0,raw_area,0)
        crops=np.array([a['crop'][source],c['basin_crop']]).astype(int);phases=np.array([c['base_boundary'],c['basin_boundary']])
        np.testing.assert_array_equal(crops,b['crops']);np.testing.assert_array_equal(phases,b['phases'])
        listed=active_area*np.array([0,336,208])[crops];reaping=active_area*np.array([0,48,32])[crops]
        workers=a['rural'][source]*.4;annual=workers*hours;peak=np.minimum(annual,workers*240)
        expected_retention=np.zeros(len(source));monthly=np.zeros((12,len(source)))
        # Each scalar source owns one budget. Group component reaping explicitly by its actual boundary.
        for cell in range(len(source)):
            total=0.;by_boundary={}
            for component in range(2):
                if potential[component,cell]<=0:continue
                total+=listed[component,cell];month=int(phases[component,cell]);assert 0<=month<12
                by_boundary[month]=by_boundary.get(month,0.)+reaping[component,cell]
            if not by_boundary:continue
            constraints=[1.,annual[cell]/total]
            for month,required in by_boundary.items():
                monthly[month,cell]=required;constraints.append(peak[cell]/required)
            expected_retention[cell]=min(constraints)
        produced=potential*expected_retention;grown=produced.sum(0)
        required=listed.sum(0);annual_ratio=np.divide(annual,required,out=np.ones_like(annual),where=required>0)
        max_reaping=monthly.max(0);peak_ratio=np.divide(peak,max_reaping,out=np.ones_like(peak),where=max_reaping>0)
        expected=dict(active_area=active_area,required_listed=listed,required_reaping=reaping,monthly_peak_required=monthly,
            workers=workers,annual_available=annual,peak_available=peak,annual_fraction=annual_ratio,peak_fraction=peak_ratio,
            retained=expected_retention,produced_components=produced,produced_total=grown,
            annual_used=required*expected_retention,monthly_peak_used=monthly*expected_retention)
        for key,value in expected.items():np.testing.assert_allclose(value,b['B_'+key],rtol=1e-12,atol=.01 if 'produced' in key else 1e-7,err_msg=key)
        assert np.all(expected['annual_used']<=annual+1e-8*np.maximum(annual,1))
        assert np.all(expected['monthly_peak_used']<=peak+1e-8*np.maximum(peak,1))
        np.testing.assert_allclose(b['B_workers'].sum(),(a['rural'][source]*.4).sum(),rtol=1e-15,atol=1e-8)
        max_grain_error=max(max_grain_error,float(abs(grown-b['B_produced_total']).max()/KCAL))
        # Original mixed-work control, including its reference-population floating arithmetic.
        mixed=a['potential_kcal'];need=a['rural']*KCAL;old_workers=(need/KCAL)*.4
        year_required=mixed*a['listed']/1e6;peak_required=mixed*a['reaping']/1e6
        old_fraction=np.minimum(1,np.minimum(np.divide(old_workers*hours,year_required,out=np.ones_like(mixed),where=year_required>0),
            np.divide(np.minimum(old_workers*hours,old_workers*240),peak_required,out=np.ones_like(mixed),where=peak_required>0)))
        old_grown=mixed*old_fraction;np.testing.assert_array_equal(old_grown[source],b['A_produced'])
        if hours==600:np.testing.assert_array_equal(old_grown,a['grown_kcal'])
        new_grown=np.zeros_like(mixed);new_grown[source]=grown
        for label,grain in [('A',old_grown),('B',new_grown)]:
            surplus=np.maximum(grain-need,0)/KCAL
            np.testing.assert_allclose(surplus,b['surplus_'+label],rtol=1e-12,atol=1e-7)
            flow=grain_flow(a,surplus,SHARES[reading]);shipment_rows+=len(flow['shipments'])
            for key,value in flow.items():
                np.testing.assert_allclose(value,b[label+'_'+key],rtol=1e-12,atol=1e-7,err_msg=label+key)
                if key!='shipments':np.testing.assert_array_equal(towns[f'{reading}_{label}_{key}'],b[label+'_'+key])
            max_town_error=max(max_town_error,float(abs(flow['fed']-b[label+'_fed']).max()))
            assert np.all(flow['fed']>=0) and np.all(flow['fed']<=a['residents']+1e-7)
            summary=r['cases'][reading][label]
            assert abs(summary['grown_person_years']-grain.sum()/KCAL)<1e-6
            deficit=np.maximum(need-grain,0)/KCAL
            assert abs(summary['rural_deficit_person_years']-deficit.sum())<1e-6
            assert abs(summary['surplus_person_years']-surplus.sum())<1e-6
            town=a['nodes'];lon=a['grid_lon'].ravel();lat=a['lat'].ravel()
            egypt=(lon>=29)&(lon<=32.6)&(lat<=32)
            masks={'all':np.ones(len(town),bool),'west':a['lon']<=np.median(a['lon']),'east':a['lon']>np.median(a['lon']),
                   'egypt_proper':egypt[town],'other':~egypt[town]}
            for name,mask in masks.items():
                assert abs(summary['fed_by_region'][name]['fed_people']-flow['fed'][mask].sum())<1e-6
            for name,mask in [('egypt_proper',egypt),('other',~egypt)]:
                assert abs(summary['rural_deficit_by_region'][name]-deficit[mask].sum())<1e-6
        delta=(b['B_produced_total']-b['A_produced'])/KCAL
        assert abs(delta[s==0]).max()<1e-7
        cases[reading]=dict(physical_sources=len(source),shared_workers=float(workers.sum()),
            peak_limited_cells=int(((peak_ratio<annual_ratio)&(peak_ratio<1)).sum()),
            maximum_reaping_budget_utilization=float(np.divide(expected['monthly_peak_used'],peak,out=np.zeros_like(monthly),where=peak>0).max()),
            outside_basin_max_grain_difference_person_years=float(abs(delta[s==0]).max()),
            increased_basin_cells=int(((delta>1e-7)&(s>0)).sum()),reduced_basin_cells=int(((delta< -1e-7)&(s>0)).sum()))
        source_cases+=len(source)
    rows=list(csv.DictReader((out/'basin_sources.csv').open()));assert len(rows)==910
    for reading in ['central','low']:
        a=dict(np.load(PRIOR/'wind_1981/prepared'/f'low_{reading}.npz'));b=dict(np.load(out/'cases'/f'{reading}.npz'))
        for row in [r for r in rows if r['reading']==reading]:
            cell=int(row['source_cell']);i=int(np.searchsorted(source,cell));assert source[i]==cell
            assert abs(float(row['A_grown_person_years'])-b['A_produced'][i]/KCAL)<1e-8
            assert abs(float(row['B_grown_person_years'])-b['B_produced_total'][i]/KCAL)<1e-8
            assert int(row['base_harvest_boundary'])==c['base_boundary'][i] and int(row['basin_harvest_boundary'])==c['basin_boundary'][i]
    receipt=dict(status='passed_shared_component_work_and_fixed_share_supply_review',hours=hours,
        reviewer_sha256=sha(Path(__file__)),results_sha256=sha(out/'results.json'),
        cases=cases,source_cases=source_cases,independent_town_allocations=4,shipment_rows=shipment_rows,
        basin_csv_rows=len(rows),max_source_grain_residual_person_years=max_grain_error,max_town_fed_residual_people=max_town_error,
        exact_original_annual_controls=6,one_workforce_per_physical_source=True,
        seasonal_food_trial=False,new_fit=False,new_validation_claim=False,adopt=False)
    (out/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--hours',required=True,type=int,choices=[600,300]);args=parser.parse_args();main(args.hours)
