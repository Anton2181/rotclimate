"""Canonical-bisection stocks and independent fixed-request monthly grain ledger."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from harvest.food_stocks import periodic_food_year

OUT=ROOT/'output/urban_earth_monthly_20261116'
BASE=ROOT/'output/urban_component_work_20261116'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116'
CAL=ROOT/'output/urban_earth_calendars_20261116'
KCAL=912500.


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def total(value):return math.fsum(np.asarray(value).ravel())


def read(path):return json.loads(path.read_text())


def close(a,b,atol=.01,rtol=3e-11):np.testing.assert_allclose(a,b,atol=atol,rtol=rtol)


def inventory(values,prefix,harvest,need,capacity):
    y=periodic_food_year(harvest,need,capacity,loss_fraction_year=.05,step_days=365/12,record=True)
    scale=np.maximum(1,np.maximum(y.harvested,y.needed))
    tolerance=1e-10*scale+100*np.finfo(float).eps*scale
    maximum=0.
    for key in ['initial_stock','final_stock','peak_stock','harvested','needed','consumed','unmet','spoiled','overflow','stock_path','unmet_path']:
        error=abs(values[prefix+'__'+key]-getattr(y,key))
        assert np.all(error<=tolerance),(prefix,key,float((error/tolerance).max()))
        maximum=max(maximum,float((error/tolerance).max()))
    assert y.periodic_converged.all()
    return y,maximum


def main(reading):
    out=OUT/'cases'/reading;r=read(out/'results.json')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    assert sha(out/'fields.npz')==r['fields_sha256']
    c=dict(np.load(out/'fields.npz'));a=dict(np.load(ANNUAL/'wind_1981/prepared'/f'low_{reading}.npz'))
    b=dict(np.load(BASE/'hours600/cases'/f'{reading}.npz'));cal=dict(np.load(CAL/'calendars.npz'))
    source=cal['source_indices'];request=a['residents'];rural=a['rural'][source]
    np.testing.assert_array_equal(c['source_indices'],source);np.testing.assert_array_equal(c['rural'],rural)
    np.testing.assert_array_equal(c['request'],request);np.testing.assert_array_equal(c['people'],a['people'][source])
    np.testing.assert_array_equal(c['produced_components'],b['B_produced_components'])
    np.testing.assert_array_equal(c['boundary'],np.array([cal['base_boundary'],cal['basin_boundary']]))
    moved=c['people']*request.sum()/a['people'].sum()
    np.testing.assert_array_equal(c['withdrawn'],moved)
    np.testing.assert_allclose(c['people']-moved,rural,atol=1e-7,rtol=1e-12)
    assert abs(total(moved)-total(request))<1e-7
    assert r['factorized_population']['implicit_matrix_materialized'] is False and not r['demographic_iteration']
    close(total(rural*.4),b['B_workers'].sum(),atol=1e-7,rtol=1e-15)
    harvest=np.zeros((12,len(source)))
    # Separate source pulses, using explicit cell-wise additions rather than a single mask.
    for cell in range(len(source)):
        for component in range(2):
            grain=c['produced_components'][component,cell]
            if grain<=0:continue
            month=int(c['boundary'][component,cell]);assert 0<=month<12
            harvest[month,cell]+=grain
    np.testing.assert_array_equal(harvest,c['harvest']);np.testing.assert_array_equal(harvest.sum(0),b['B_produced_total'])
    need=np.broadcast_to(rural*KCAL/12,harvest.shape);capacity=rural*KCAL
    ry,ratio_rural=inventory(c,'rural_food',harvest,need,capacity)
    protected=ry.unmet<=1e-8*np.maximum(1,ry.needed)
    recorded_protected=c['rural_food__unmet']<=1e-8*np.maximum(1,c['rural_food__needed'])
    np.testing.assert_array_equal(protected,recorded_protected)
    protected_capacity=c['rural_food__needed']*365/365
    available=np.maximum(c['rural_food__stock_path'][:-1]+harvest-need-protected_capacity,0)
    marketed=available*protected*r['marketed_share']
    close(c['marketed'],marketed,atol=.001)
    assert not (c['marketed'][:,~protected]>1e-6).any()
    owner=a['owner'][:,source];fraction=np.maximum(1-a['dist'][:,source].astype(float)/270,0)
    fraction=np.where(owner>=0,fraction,0)
    np.testing.assert_array_equal(owner,c['owner']);np.testing.assert_array_equal(fraction,c['retention'])
    dispatch=np.broadcast_to(c['marketed'].sum(0)/12,c['marketed'].shape).copy()
    for month in range(12):dispatch[month]*=(owner[month//3]>=0)&(fraction[month//3]>0)
    np.testing.assert_array_equal(dispatch,c['dispatch'])
    ey,ratio_export=inventory(c,'export_food',c['marketed'],dispatch,c['marketed'].sum(0))
    close(c['departures'],dispatch-c['export_food__unmet_path'],atol=.001)
    assert np.all(c['departures']>=-1e-6) and np.all(c['departures']<=dispatch+1e-6)
    assert not (c['departures'][:,~protected]>1e-6).any()
    direct=np.zeros((12,len(request)))
    for month in range(12):
        valid=(owner[month//3]>=0)&(fraction[month//3]>0)
        np.add.at(direct[(month+1)%12],owner[month//3,valid],c['departures'][month,valid]*fraction[month//3,valid])
    close(direct,c['direct'])
    town_need=np.broadcast_to(request*KCAL/12,direct.shape);town_capacity=request*2500*90
    ly,ratio_local=inventory(c,'direct_food',c['direct'],town_need,town_capacity)
    eligible=(request>0)&(c['direct_food__unmet']<=1e-8*np.maximum(1,c['direct_food__needed']))
    np.testing.assert_array_equal(eligible,c['protected_exporters'])
    np.testing.assert_array_equal(eligible,(request>0)&(ly.unmet<=1e-8*np.maximum(1,ly.needed)))
    overflow=np.maximum(c['direct_food__stock_path'][:-1]+c['direct']-town_need-town_capacity,0)*eligible
    between=np.maximum(1-a['between'].astype(float)/270,0)
    for season in range(4):np.fill_diagonal(between[season],0)
    received=np.zeros_like(direct);exported=np.zeros_like(direct);moves=[]
    for month in range(12):
        matrix=between[month//3];excess=overflow[month].copy();deficit=c['direct_food__unmet_path'][(month+1)%12].copy()
        sender,receiver=np.nonzero((matrix>0)&(excess[:,None]>0)&(deficit[None,:]>0))
        links=sorted(zip(sender.tolist(),receiver.tolist()),key=lambda pair:(-matrix[pair],pair[0],pair[1]))
        for i,j in links:
            if excess[i]<=0 or deficit[j]<=0:continue
            sent=min(excess[i],deficit[j]/matrix[i,j]);arrival=sent*matrix[i,j]
            excess[i]-=sent;deficit[j]-=arrival
            if deficit[j]<1e-9*max(1,sent):deficit[j]=0
            exported[month,i]+=sent;received[(month+1)%12,j]+=arrival;moves.append([month,i,j,sent,arrival])
    close(c['shipments'],np.array(moves).reshape(-1,5))
    close(c['inter_exported'],exported);close(c['inter_received'],received)
    assert np.all(exported<=overflow+.01)
    assert not ((exported.sum(0)>0)&(received.sum(0)>0)).any()
    close(c['arrivals'],c['direct']+received)
    ty,ratio_town=inventory(c,'town_food',c['arrivals'],town_need,town_capacity)
    ledger=dict(produced_kcal=total(b['B_produced_total']),rural_meals_kcal=total(c['rural_food__consumed']),
        rural_spoiled_kcal=total(c['rural_food__spoiled']),export_spoiled_kcal=total(c['export_food__spoiled']),
        town_spoiled_kcal=total(c['town_food__spoiled']),
        source_unused_kcal=total(c['rural_food__overflow'])-total(c['marketed'])+total(c['export_food__overflow']),
        town_unused_kcal=total(c['town_food__overflow'])-total(exported),
        source_freight_loss_kcal=total(c['departures'])-total(c['direct']),
        intertown_freight_loss_kcal=total(exported)-total(received),town_meals_kcal=total(c['town_food__consumed']),
        stock_change_kcal=sum(total(c[p+'__final_stock']-c[p+'__initial_stock']) for p in ['rural_food','export_food','town_food']))
    for key,value in ledger.items():close(r['monthly_audit']['ledger'][key],value,atol=.1)
    residual=ledger['produced_kcal']-math.fsum(v for k,v in ledger.items() if k!='produced_kcal')
    assert abs(residual)<1e-9*ledger['produced_kcal']
    transit=r['monthly_audit']['cyclic_transit']
    close(transit['source_to_town_begin_end_kcal'],direct[0].sum())
    close(transit['intertown_begin_end_kcal'],received[0].sum())
    assert transit['annual_transit_stock_change_kcal']==0
    for name,value in [('rural_unmet_person_years',total(c['rural_food__unmet'])/KCAL),
                       ('town_unmet_person_years',total(c['town_food__unmet'])/KCAL),
                       ('town_meals_person_years',total(c['town_food__consumed'])/KCAL)]:
        close(r['monthly_audit'][name],value,atol=1e-7)
    assert r['monthly_audit']['rural_deficit_sources']==int((~protected).sum())
    assert r['monthly_audit']['final_fully_supported_towns']==int((ty.unmet<=1e-8*np.maximum(1,ty.needed)).sum())
    lat=a['lat'].ravel()[a['nodes']];lon=a['grid_lon'].ravel()[a['nodes']]
    egypt=(lon>=29)&(lon<=32.6)&(lat<=32)
    masks={'all':np.ones(len(request),bool),'west':a['lon']<=np.median(a['lon']),'east':a['lon']>np.median(a['lon']),
           'egypt_proper':egypt,'other':~egypt}
    for name,mask in masks.items():
        close(r['regions'][name]['monthly_meals_person_years'],total(c['town_food__consumed'][mask])/KCAL,atol=1e-7)
        close(r['regions'][name]['annual_B_fed_people'],total(b['B_fed'][mask]),atol=1e-7)
    receipt=dict(status='passed_fixed_request_monthly_inventories_routes_and_grain_ledger',reading=reading,
        reviewer_sha256=sha(Path(__file__)),results_sha256=sha(out/'results.json'),fields_sha256=sha(out/'fields.npz'),
        physical_sources=len(source),towns=len(request),inventory_groups=4,
        maximum_fraction_of_original_inventory_tolerance=max(ratio_rural,ratio_export,ratio_local,ratio_town),
        independent_source_arrival_max_difference_kcal=float(abs(direct-c['direct']).max()),
        independent_shipments=len(moves),grain_residual_person_years=residual/KCAL,
        factorized_population_identity_passed=True,annual_B_inputs_unchanged=True,
        rural_support_flags_match_canonical=True,town_support_flags_match_canonical=True,
        demographic_iteration=False,actual_city_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False)
    (out/'review.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('reading',choices=['central','low']);args=parser.parse_args();main(args.reading)
