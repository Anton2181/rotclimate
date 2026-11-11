"""Unchanged service routes with declared opportunity masses and local controls."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.sparse import coo_matrix

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from polity.service_access import walking_graph,bounded_roundtrips
from polity.service_demand import round_trip_weights,allocate_requests
from polity.service_opportunity import normalize_opportunities,local_controls

PLAN=ROOT/'calibration/settlement_service_controls_20261111/plan.json'
OUT=ROOT/'output/settlement_service_controls_20261111'
PRIOR=ROOT/'output/settlement_service_demand_20261111'
INPUT=ROOT/'output/settlement_locations_20261110/rome_inputs.npz'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    prior=json.loads((PRIOR/'fields.json').read_text())
    if sha(INPUT)!=prior['input_sha256'] or sha(PRIOR/'fields.npz')!=prior['fields_sha256']:
        raise ValueError('Changed frozen service inputs/fields')
    for path,digest in prior['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed frozen service source')
    x=dict(np.load(INPUT));old=dict(np.load(PRIOR/'fields.npz'));core=old['core_mask'];cell=float(x['cell_km'])
    eligible=old['environment']>0;total=1292.
    masses={'history_L450':old['history_L450_intensity']*cell**2,
        'environment':normalize_opportunities(old['environment'],eligible,total),
        'uniform':normalize_opportunities(np.ones_like(old['environment']),eligible,total)}
    for mass in masses.values():assert np.isclose(mass.sum(),total,rtol=0,atol=1e-8)
    fields={key:old[key] for key in ['uniform','environment','history_L450_intensity']};fields['core_mask']=core
    y0,y1,x0,x1=prior['crop_grid_bounds'];crop=np.s_[y0:y1,x0:x1];shape=x['land'][crop].shape
    demand_grid=np.where(x['land']&x['allowed'],x['density']*cell**2,0.)
    local_demand=demand_grid[crop];origins=np.flatnonzero(local_demand>0);centres=np.flatnonzero(eligible[crop])
    demand=local_demand.ravel()[origins];summaries=[];controls=0
    for name,mass in masses.items():
        for suffix,field in local_controls(demand_grid,mass).items():
            field[~core]=0;fields[name+'__'+suffix]=field
    for roads in ['no_roads','recorded_roads']:
        graph,speed=walking_graph(x['elev'][crop],x['land'][crop],x['road'][crop] if roads=='recorded_roads' else np.zeros(shape,bool),cell)
        if speed>30+1e-8:raise ValueError('Declared halo speed bound exceeded')
        rr,cc,out,back=bounded_roundtrips(graph,centres,origins,2.)
        for budget in [.5,1.,2.]:
            weights=round_trip_weights(out,back,budget)
            kernel=coo_matrix((weights,(rr,cc)),shape=(len(centres),len(origins))).tocsr();kernel.eliminate_zeros()
            scenario=f'{roads}_B{budget:g}'
            for name,mass in masses.items():
                m=mass[crop].ravel()[centres];allocation=allocate_requests(kernel,demand,m)
                for suffix,values in [('potential',allocation.accessible_potential),('allocated',allocation.allocated_requests),('per_centre',allocation.requests_per_centre)]:
                    local=np.zeros(shape);local.ravel()[centres]=np.where(m>0,values,0.)
                    full=np.zeros_like(mass);full[crop]=local;full[~core]=0.
                    fields[name+'__'+scenario+'__'+suffix]=full
                    if name=='history_L450':
                        if not np.array_equal(full,old[scenario+'_'+suffix]):raise ValueError('Prior historical service field changed')
                        controls+=1
                summaries.append(dict(mass_case=name,transport=scenario,
                    global_expected_centre_mass=float(mass.sum()),positive_opportunity_cells=int(np.sum(mass>0)),
                    reference_demand_units=float(demand.sum()),allocated_request_units=float(allocation.allocated_requests.sum()),
                    unallocated_request_units=float(allocation.origin_unallocated.sum()),
                    request_balance_error=float(allocation.allocated_requests.sum()+allocation.origin_unallocated.sum()-demand.sum()),
                    maximum_origin_excess=float(np.maximum(allocation.origin_allocated-demand,0).max(initial=0))))
        print(roads,'complete',flush=True)
    assert controls==18 and len(fields)==67 #66 predictor fields plus core mask
    np.savez_compressed(OUT/'fields.npz',**fields)
    paths=[Path(__file__),ROOT/'polity/service_opportunity.py',ROOT/'polity/service_access.py',ROOT/'polity/service_demand.py',ROOT/'polity/control.py']
    result=dict(status='declared_opportunity_and_null_control_fields',adopt=False,plan_sha256=sha(PLAN),
        input_sha256=sha(INPUT),prior_fields_manifest_sha256=sha(PRIOR/'fields.json'),prior_fields_sha256=sha(PRIOR/'fields.npz'),
        fields_sha256=sha(OUT/'fields.npz'),sources={str(p.relative_to(ROOT)):sha(p) for p in paths},
        prior_historical_fields_exact=controls,reference_grid=prior['reference_grid'],crop_grid_bounds=prior['crop_grid_bounds'],
        ledgers=summaries,predictors=[key for key in fields if key!='core_mask'],
        nulls_are_explanatory_not_adopted_predictions=True,population_food_staff_control_changed=False)
    write(OUT/'fields.json',result)


if __name__=='__main__':main()
