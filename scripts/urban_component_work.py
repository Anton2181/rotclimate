"""Paired annual mixed-yield/physical-component tasks; no new food season model."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import greek_walls as G
from harvest.field_support import field_support
from harvest.work_maps import cereal_work
from polity.earth_component_work import component_work

OUT=ROOT/'output/urban_component_work_20261116'
CAL=ROOT/'output/urban_earth_calendars_20261116'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116'
RESTORE=ROOT/'output/urban_population_recipe_20261116/restored'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_component_work.json'
ADAPTER=PLAN.parent/'seasonal_transfer_component_control_adapter.json'
SHARES={'central':0.3371937035110408,'low':0.14049021985082757}
KCAL=912500.


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def gate():
    for path in [PLAN,ADAPTER]:assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()
    qualification=read(CAL/'qualification.json');assert qualification['status']=='passed_original_model_calendar_recovery_component_work_gate_open'
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',CAL)]:
        for name,digest in qualification[key].items():assert sha(prefix/name)==digest,name
    cal=read(CAL/'results.json');annual=read(ANNUAL/'results.json')
    for result,base in [(cal,CAL),(annual,ANNUAL)]:
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',base),('protected_sha256',ROOT)]:
            for name,digest in result[key].items():assert sha(prefix/name)==digest,name
    paths=[Path(__file__),ROOT/'polity/earth_component_work.py',ROOT/'tests/test_earth_component_work.py',PLAN,ADAPTER,CAL/'qualification.json',
        CAL/'results.json',CAL/'review.json',CAL/'calendars.npz',ANNUAL/'results.json',ANNUAL/'wind_1981/review.json',
        RESTORE/'grid/earth.npz',RESTORE/'basin/fields.npz',ROOT/'harvest/field_support.py',ROOT/'harvest/work_maps.py',
        ROOT/'polity/wide_supply.py',ROOT/'scripts/greek_walls.py',ROOT/'scripts/supply_low_reading.py',
        ROOT/'scripts/settlement_supply_calibration.py',ROOT/'scripts/settlement_supply_earth.py',
        ROOT/'calibration/settlement_supply_calibration_20261113/plan.json']
    return {str(p.relative_to(ROOT)):sha(p) for p in paths},cal['protected_sha256']


def control(stage):
    sources,protected=gate();out=OUT/'controls'/stage;out.mkdir(parents=True,exist_ok=True)
    assert not (out/'control.json').exists(),'Use an isolated OUT for a fresh completed control replay'
    if stage=='greek':runner=G;reference=ROOT/'output/greek_walls_20261114/results.json'
    else:
        import supply_low_reading as runner
        reference=ROOT/'output/supply_low_reading_20261114/results.json'
    receipt=read(ANNUAL/'wind_1981'/stage/'control.json');capture=receipt['captures'];observations=[]
    sources[str((ANNUAL/'wind_1981'/stage/'control.json').relative_to(ROOT))]=sha(ANNUAL/'wind_1981'/stage/'control.json')
    S=G.S;G.FS.GRID=RESTORE/'grid/earth.npz';G.FS.FIELDS=RESTORE/'basin/fields.npz'
    def prepared(x):
        case=capture[len(observations)];path=ANNUAL/'wind_1981/prepared'/f'{stage}_{case["name"]}.npz'
        assert sha(path)==case['prepared_sha256'];a=dict(np.load(path));sources[str(path.relative_to(ROOT))]=sha(path)
        np.testing.assert_array_equal(x['density'],a['density'])
        nodes,residents,lon,info=S.PILOT.cities(x)
        for key,value in [('nodes',nodes),('residents',residents),('lon',lon)]:np.testing.assert_array_equal(value,a[key])
        wheat,barley,arable,_=S.earth_fields(x['lat'],x['lon'])
        work=cereal_work(np.stack([wheat,barley]),S.HOURS,S.REAP,food_target=1e6)
        np.testing.assert_array_equal(work.crop.ravel(),a['crop'])
        np.testing.assert_array_equal(np.nan_to_num(work.hours).ravel(),a['listed'])
        np.testing.assert_array_equal(np.nan_to_num(work.reaping).ravel(),a['reaping'])
        energy=np.where(work.crop>0,1e6/np.where(work.crop>0,work.land,1.),0.)
        potential=np.where(x['land']&x['allowed'],energy*100.*float(x['cell_km'])**2*arable*S.FARMED*S.SOWN,0).ravel()
        people=np.where(x['land']&x['allowed'],x['density'],0).ravel()*float(x['cell_km'])**2
        rural=people*(1-residents.sum()/people.sum())
        np.testing.assert_array_equal(potential,a['potential_kcal']);np.testing.assert_array_equal(rural,a['rural'])
        grown=field_support(potential,a['listed'],a['reaping'],rural_need_kcal=rural*KCAL)
        np.testing.assert_array_equal(grown.produced_kcal,a['grown_kcal'])
        np.testing.assert_array_equal(np.maximum(grown.produced_kcal-rural*KCAL,0)/KCAL,a['surplus'])
        observations.append(dict(name=case['name'],prepared_sha256=sha(path),population_city_crop_work_arrays_exact=True))
        return {key:a[key] for key in ['nodes','residents','lon','dist','owner','between','surplus','potential','rural']},case['world']
    S.prepare=prepared
    try:
        runner.main(out)
        assert (out/'results.json').read_bytes()==reference.read_bytes(),'Whole archived annual JSON differs'
        assert len(observations)==(4 if stage=='greek' else 2)
        write(out/'control.json',dict(status='passed_original_mixed_work_whole_annual_result_bytes_exact',stage=stage,
            observations=observations,results_sha256=sha(out/'results.json'),reference_sha256=sha(reference),
            sources_sha256=sources,protected_sha256=protected,route_arrays='Verified prior actual1981–2010 snapshots reused unchanged; no new Dijkstra run',
            physical_source_work_recomputed=True,new_fit=False,adopt=False))
        print(stage,'WHOLE original annual JSON EXACT',flush=True)
    except BaseException as error:
        write(out/'failure.json',dict(status='preserved_component_A_control_failure',error=f'{type(error).__name__}: {error}',sources_sha256=sources,adopt=False));raise


def trade(a,surplus,share):
    W=G.S.W
    retention=np.where(a['owner']>=0,W.delivered_share(a['dist'].astype(float),270),0.)
    between=W.delivered_share(a['between'].astype(float),270).mean(0);np.fill_diagonal(between,0.)
    direct,sent=W.hinterland_delivery(a['owner'],retention,surplus*share,len(a['residents']))
    shipments,received=W.ship(np.maximum(direct-a['residents'],0),np.maximum(a['residents']-direct,0),between)
    fed=np.minimum(direct,a['residents'])+received
    return dict(fed=fed,direct=direct,source_sent=sent,inter_received=received,
                shipments=np.array([(i,j,value,value*between[i,j]) for (i,j),value in shipments.items()],float).reshape(-1,4))


def describe(a,produced,surplus,delivered,source):
    need=a['rural'][source]*KCAL;deficit=np.maximum(need-produced,0)/KCAL
    lat=a['lat'].ravel();lon=a['grid_lon'].ravel();town=a['nodes']
    egypt=(lon>=29)&(lon<=32.6)&(lat<=32)
    masks={'all':np.ones(len(town),bool),'west':a['lon']<=np.median(a['lon']),'east':a['lon']>np.median(a['lon']),
           'egypt_proper':egypt[town],'other':~egypt[town]}
    return dict(grown_person_years=float(produced.sum()/KCAL),surplus_person_years=float(surplus.sum()),
        rural_deficit_person_years=float(deficit.sum()),rural_deficit_cells=int((deficit>1e-8).sum()),
        rural_deficit_by_region={name:float(deficit[mask[source]].sum()) for name,mask in [('egypt_proper',egypt),('other',~egypt)]},
        fed_by_region={name:dict(cities=int(mask.sum()),requested_people=float(a['residents'][mask].sum()),
             fed_people=float(delivered['fed'][mask].sum()),fed_share=float(delivered['fed'][mask].sum()/a['residents'][mask].sum())) for name,mask in masks.items()})


def build(hours):
    sources,protected=gate();out=OUT/f'hours{hours}';cases=out/'cases';cases.mkdir(parents=True,exist_ok=True)
    assert not (out/'results.json').exists(),'Preserve completed diagnostics; use isolated OUT for a fresh stage'
    for stage in ['greek','low']:
        path=OUT/'controls'/stage/'control.json';r=read(path)
        assert r['status']=='passed_original_mixed_work_whole_annual_result_bytes_exact'
        for name,digest in r['sources_sha256'].items():assert sha(ROOT/name)==digest,name
        sources[str(path.relative_to(ROOT))]=sha(path)
    if hours==300:
        review=read(OUT/'hours600/review.json');assert review['status']=='passed_shared_component_work_and_fixed_share_supply_review'
        assert review['results_sha256']==sha(OUT/'hours600/results.json')
        sources[str((OUT/'hours600/review.json').relative_to(ROOT))]=sha(OUT/'hours600/review.json')
    cal=dict(np.load(CAL/'calendars.npz'));source=cal['source_indices'];summaries={};towns={};changed=[]
    for reading in ['central','low']:
        path=ANNUAL/'wind_1981/prepared'/f'low_{reading}.npz';a=dict(np.load(path));sources[str(path.relative_to(ROOT))]=sha(path)
        area=100*float(a['cell_km'])**2*a['arable'].ravel()[source];s=a['basin_share'].ravel()[source]
        potential=np.array([cal['base_potential_kcal'],cal['basin_potential_kcal']])
        np.testing.assert_allclose(potential.sum(0),a['potential_kcal'][source],rtol=1e-12,atol=.001)
        crops=np.array([a['crop'][source],cal['basin_crop']]).astype(int)
        crop_hours=np.array([0.,336.,208.])[crops];crop_reap=np.array([0.,48.,32.])[crops]
        phases=np.array([cal['base_boundary'],cal['basin_boundary']])
        raw_area=np.array([area*(1-s)*.6*.6,area*s*.95])
        B=component_work(potential,raw_area,crop_hours,crop_reap,phases,a['rural'][source],hours=hours)
        A=field_support(a['potential_kcal'],a['listed'],a['reaping'],rural_need_kcal=a['rural']*KCAL,hours_worker_year=hours)
        if hours==600:np.testing.assert_array_equal(A.produced_kcal,a['grown_kcal'])
        surplus_A=np.maximum(A.produced_kcal-a['rural']*KCAL,0)/KCAL
        grown_B=np.zeros_like(a['rural']);grown_B[source]=B.produced_total
        surplus_B=np.maximum(grown_B-a['rural']*KCAL,0)/KCAL
        delivery_A=trade(a,surplus_A,SHARES[reading]);delivery_B=trade(a,surplus_B,SHARES[reading])
        assert np.all(B.annual_used<=B.annual_available+1e-8*np.maximum(B.annual_available,1))
        assert np.all(B.monthly_peak_used<=B.peak_available+1e-8*np.maximum(B.peak_available,1))
        outside=s==0;delta=(B.produced_total-A.produced_kcal[source])/KCAL
        assert abs(delta[outside]).max()<1e-7,'Material nonbasin work change not declared'
        values={f'B_{key}':value for key,value in asdict(B).items()}
        values.update(A_produced=A.produced_kcal[source],A_retained=A.retained[source],rural=a['rural'][source],
            potential=potential,raw_area=raw_area,crops=crops,phases=phases,surplus_A=surplus_A,surplus_B=surplus_B,
            **{f'A_{key}':value for key,value in delivery_A.items()},**{f'B_{key}':value for key,value in delivery_B.items()})
        np.savez_compressed(cases/f'{reading}.npz',**values)
        for name,delivery in [('A',delivery_A),('B',delivery_B)]:
            for key in ['fed','direct','source_sent','inter_received']:towns[f'{reading}_{name}_{key}']=delivery[key]
        towns[reading+'_nodes']=a['nodes'];towns[reading+'_request']=a['residents']
        summaries[reading]=dict(marketed_share=SHARES[reading],haul_limit_road_km=270,
            A=describe(a,A.produced_kcal[source],surplus_A,delivery_A,source),
            B=describe(a,B.produced_total,surplus_B,delivery_B,source),
            basin_grain_increased_cells=int(((delta>1e-7)&(s>0)).sum()),basin_grain_reduced_cells=int(((delta< -1e-7)&(s>0)).sum()),
            maximum_nonbasin_grain_difference_person_years=float(abs(delta[outside]).max()),
            annual_limited_B_cells=int(((B.annual_fraction<1)&(B.annual_fraction<=B.peak_fraction)).sum()),
            peak_limited_B_cells=int(((B.peak_fraction<1)&(B.peak_fraction<B.annual_fraction)).sum()),
            maximum_peak_budget_utilization=float(np.divide(B.monthly_peak_used,B.peak_available,out=np.zeros_like(B.monthly_peak_used),where=B.peak_available>0).max()),
            B_workers=float(B.workers.sum()),A_workers=float(A.workers[source].sum()))
        for local in np.flatnonzero(s>0):
            cell=int(source[local]);changed.append(dict(reading=reading,source_cell=cell,
                lat=float(a['lat'].ravel()[cell]),lon=float(a['grid_lon'].ravel()[cell]),basin_share=float(s[local]),
                base_potential_person_years=float(potential[0,local]/KCAL),basin_potential_person_years=float(potential[1,local]/KCAL),
                A_grown_person_years=float(A.produced_kcal[cell]/KCAL),B_grown_person_years=float(B.produced_total[local]/KCAL),
                delta_grown_person_years=float(delta[local]),rural_people=float(a['rural'][cell]),
                annual_work_available=float(B.annual_available[local]),B_annual_work_used=float(B.annual_used[local]),
                base_harvest_boundary=int(phases[0,local]),basin_harvest_boundary=int(phases[1,local])))
        print(hours,reading,json.dumps(summaries[reading]),flush=True)
    import csv
    with (out/'basin_sources.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(changed[0]));writer.writeheader();writer.writerows(changed)
    np.savez_compressed(out/'town_model.npz',**towns)
    files=[cases/'central.npz',cases/'low.npz',out/'town_model.npz',out/'basin_sources.csv']
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    write(out/'results.json',dict(status='paired_annual_component_work_pending_independent_review',hours=hours,cases=summaries,
        sources_sha256=sources,protected_sha256=protected,files_sha256={str(p.relative_to(out)):sha(p) for p in files},
        producer_sha256=sha(Path(__file__)),fixed_shares_not_refitted=True,
        share_note='Existing interpolated e95 values used as fixed settings; actual allocation at those intermediate values need not equal exactly95%.',
        route_note='Same actual1981–2010 four-season matrices and original annual allocation,not seasonal dispatch.',
        seasonal_food_trial=False,new_validation_claim=False,adopt=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--control',choices=['greek','low']);parser.add_argument('--hours',type=int,choices=[600,300]);args=parser.parse_args()
    assert (args.control is None)!=(args.hours is None),'Choose exactly one control or work stage'
    if args.control:control(args.control)
    else:
        try:build(args.hours)
        except BaseException as error:
            out=OUT/f'hours{args.hours}';out.mkdir(parents=True,exist_ok=True)
            if not (out/'failure.json').exists():write(out/'failure.json',dict(status='preserved_component_work_failure',error=f'{type(error).__name__}: {error}',producer_sha256=sha(Path(__file__)),adopt=False))
            raise
