"""Declared fixed-request Earth monthly cereal pilot; no demographic iteration."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.earth_component_work import component_work
from polity.earth_fixed_food import fixed_request_food
from harvest.food_stocks import FoodYear
from urban_component_work import trade

OUT=ROOT/'output/urban_earth_monthly_20261116'
BASE=ROOT/'output/urban_component_work_20261116'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116'
CAL=ROOT/'output/urban_earth_calendars_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_fixed_request_pilot.json'
ADAPTER=PLAN.parent/'seasonal_transfer_fixed_request_adapter.json'
KCAL=912500.;SHARES={'central':.3371937035110408,'low':.14049021985082757}


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def total(value):return math.fsum(np.asarray(value).ravel())


def gate():
    for path in [PLAN,ADAPTER]:assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()
    previous=read(BASE/'qualification.json');assert previous['status']=='passed_paired_annual_component_work_primary_and_stress'
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',BASE),('protected_sha256',ROOT)]:
        for name,digest in previous[key].items():assert sha(prefix/name)==digest,name
    kernel=read(ROOT/'output/urban_candidate_seasonal_20261116/kernel_review.json')
    assert kernel['status']=='passed' and kernel['module_sha256']==sha(ROOT/'polity/seasonal_settlement_network.py')
    assert kernel['max_fraction_of_original_inventory_tolerance']<=1
    paths=[Path(__file__),PLAN,ADAPTER,BASE/'qualification.json',BASE/'hours600/results.json',BASE/'hours600/review.json',
        CAL/'qualification.json',CAL/'calendars.npz',ROOT/'polity/earth_fixed_food.py',ROOT/'tests/test_earth_fixed_food.py',
        ROOT/'polity/earth_component_work.py',ROOT/'polity/seasonal_settlement_network.py',ROOT/'harvest/food_stocks.py',
        ROOT/'harvest/field_support.py',ROOT/'polity/wide_supply.py',ROOT/'scripts/urban_component_work.py',
        ROOT/'output/urban_candidate_seasonal_20261116/kernel_review.json']
    return {str(p.relative_to(ROOT)):sha(p) for p in paths},previous['protected_sha256']


def inspect(c,rural,request,work):
    ry,ey,ty=c['rural_food'],c['export_food'],c['town_food']
    for year in [ry,ey,c['direct_food'],ty]:assert year.periodic_converged.all()
    protected=ry.unmet<=1e-8*np.maximum(1,ry.needed)
    assert not (c['marketed'][:,~protected]>1e-6).any()
    assert not (c['departures'][:,~protected]>1e-6).any()
    assert np.all(c['departures']>=-1e-6) and np.all(c['departures']<=c['dispatch']+1e-6)
    assert not ((c['inter_exported'].sum(0)>0)&(c['inter_received'].sum(0)>0)).any()
    ledger=dict(produced_kcal=total(work.produced_total),rural_meals_kcal=total(ry.consumed),
        rural_spoiled_kcal=total(ry.spoiled),export_spoiled_kcal=total(ey.spoiled),town_spoiled_kcal=total(ty.spoiled),
        source_unused_kcal=total(ry.overflow)-total(c['marketed'])+total(ey.overflow),
        town_unused_kcal=total(ty.overflow)-total(c['inter_exported']),
        source_freight_loss_kcal=total(c['departures'])-total(c['direct']),
        intertown_freight_loss_kcal=total(c['inter_exported'])-total(c['inter_received']),
        town_meals_kcal=total(ty.consumed),
        stock_change_kcal=sum(total(y.final_stock-y.initial_stock) for y in [ry,ey,ty]))
    residual=ledger['produced_kcal']-math.fsum(v for k,v in ledger.items() if k!='produced_kcal')
    assert abs(residual)<1e-9*ledger['produced_kcal']
    for key in ['source_unused_kcal','town_unused_kcal','source_freight_loss_kcal','intertown_freight_loss_kcal']:
        assert ledger[key]>=-1e-8*max(1,ledger['produced_kcal']),key
    return dict(ledger=ledger,grain_residual_person_years=residual/KCAL,
        rural_unmet_person_years=total(ry.unmet)/KCAL,town_unmet_person_years=total(ty.unmet)/KCAL,
        town_meals_person_years=total(ty.consumed)/KCAL,town_meal_fraction=total(ty.consumed)/(total(request)*KCAL),
        rural_deficit_sources=int((~protected).sum()),exporting_sources=int((c['departures'].sum(0)>0).sum()),
        local_fully_supported_towns=int(c['protected_exporters'].sum()),
        final_fully_supported_towns=int((ty.unmet<=1e-8*np.maximum(1,ty.needed)).sum()),
        rural_all_meals=bool(protected.all()),town_all_meals=bool(np.all(ty.unmet<=1e-8*np.maximum(1,ty.needed))),
        independent_workforce_people=total(rural*.4),
        repeating_stock_max_fraction_of_original_tolerance=max(float((y.periodic_residual/(1e-10*np.maximum(1,np.maximum(y.harvested,y.needed)))).max()) for y in [ry,ey,c['direct_food'],ty]),
        cyclic_transit=dict(source_to_town_begin_end_kcal=total(c['direct'][0]),
            intertown_begin_end_kcal=total(c['inter_received'][0]),annual_transit_stock_change_kcal=0.))


def main(reading):
    sources,protected=gate();out=OUT/'cases'/reading;out.mkdir(parents=True,exist_ok=True)
    assert not (out/'results.json').exists(),'Preserve completed monthly results; use an isolated OUT'
    a_path=ANNUAL/'wind_1981/prepared'/f'low_{reading}.npz';b_path=BASE/'hours600/cases'/f'{reading}.npz'
    sources.update({str(path.relative_to(ROOT)):sha(path) for path in [a_path,b_path]})
    a=dict(np.load(a_path));b=dict(np.load(b_path));cal=dict(np.load(CAL/'calendars.npz'));source=cal['source_indices']
    potential=np.array([cal['base_potential_kcal'],cal['basin_potential_kcal']])
    area=100*float(a['cell_km'])**2*a['arable'].ravel()[source];s=a['basin_share'].ravel()[source]
    crop=np.array([a['crop'][source],cal['basin_crop']]).astype(int)
    boundary=np.array([cal['base_boundary'],cal['basin_boundary']])
    work=component_work(potential,np.array([area*(1-s)*.6*.6,area*s*.95]),
        np.array([0.,336.,208.])[crop],np.array([0.,48.,32.])[crop],boundary,a['rural'][source],hours=600)
    for key,value in asdict(work).items():np.testing.assert_array_equal(value,b['B_'+key])
    for key,value in trade(a,b['surplus_B'],SHARES[reading]).items():np.testing.assert_array_equal(value,b['B_'+key])
    people=a['people'][source];request=a['residents'];rural=a['rural'][source];population_total=float(a['people'].sum())
    withdrawn=people*request.sum()/population_total;reconstructed=people-withdrawn
    np.testing.assert_allclose(reconstructed,rural,rtol=1e-12,atol=1e-7)
    assert abs(total(withdrawn)-total(request))<1e-7
    owner=a['owner'][:,source]
    retention=np.maximum(1-a['dist'][:,source].astype(float)/270,0);retention=np.where(owner>=0,retention,0)
    between=np.maximum(1-a['between'].astype(float)/270,0)
    for season in range(4):np.fill_diagonal(between[season],0)
    c=fixed_request_food(work.produced_components,boundary,rural,request,owner,retention,between,marketed_share=SHARES[reading])
    np.testing.assert_array_equal(c['harvest'].sum(0),work.produced_total)
    audit=inspect(c,rural,request,work)
    values=dict(source_indices=source,people=people,withdrawn=withdrawn,rural=rural,request=request,
        produced_components=work.produced_components,boundary=boundary,owner=owner,retention=retention)
    for key,value in c.items():
        if isinstance(value,FoodYear):
            for field,array in asdict(value).items():
                if array is not None:values[key+'__'+field]=array
        else:values[key]=value
    np.savez_compressed(out/'fields.npz',**values)
    lat=a['lat'].ravel();lon=a['grid_lon'].ravel();town=a['nodes']
    egypt=(lon[town]>=29)&(lon[town]<=32.6)&(lat[town]<=32)
    regions={}
    for name,mask in [('all',np.ones(len(request),bool)),('west',a['lon']<=np.median(a['lon'])),('east',a['lon']>np.median(a['lon'])),('egypt_proper',egypt),('other',~egypt)]:
        regions[name]=dict(requested_people=total(request[mask]),annual_B_fed_people=total(b['B_fed'][mask]),
            monthly_meals_person_years=total(c['town_food'].consumed[mask])/KCAL,
            monthly_meal_fraction=total(c['town_food'].consumed[mask])/(total(request[mask])*KCAL))
    result=dict(status='fixed_request_monthly_food_pending_independent_review',reading=reading,hours=600,marketed_share=SHARES[reading],
        source_count=len(source),city_cells=len(request),sources_sha256=sources,protected_sha256=protected,
        fields_sha256=sha(out/'fields.npz'),annual_B_work_and_fixed_share_allocations_exact=True,
        factorized_population=dict(implicit_matrix_materialized=False,total_people=population_total,requested_city_people=total(request),
            actual_rural_people=total(rural),withdrawn_people=total(withdrawn),max_rural_reconstruction_error_people=float(abs(reconstructed-rural).max()),
            population_ledger_residual_people=total(people)-total(rural)-total(request)),
        annual_B_fed_people=total(b['B_fed']),annual_B_fed_share=total(b['B_fed'])/total(request),
        monthly_audit=audit,regions=regions,shipment_rows=len(c['shipments']),
        food_year_repeatability_is_not_demographic_convergence=True,demographic_iteration=False,
        actual_city_population_changed=False,work_scenario='Reviewed physical component work B600h',
        new_fit=False,new_validation_claim=False,adopt=False)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    write(out/'results.json',result);print(reading,json.dumps({k:v for k,v in result.items() if not k.endswith('sha256')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('reading',choices=['central','low']);args=parser.parse_args()
    try:main(args.reading)
    except BaseException as error:
        out=OUT/'cases'/args.reading;out.mkdir(parents=True,exist_ok=True)
        if not (out/'failure.json').exists():write(out/'failure.json',dict(status='preserved_fixed_request_monthly_failure',error=f'{type(error).__name__}: {error}',producer_sha256=sha(Path(__file__)),adopt=False))
        raise
