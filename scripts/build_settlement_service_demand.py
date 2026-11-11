"""Build declared service fields independently of observed class labels."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.sparse import coo_matrix

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from polity.settlement_locations import site_fields
from polity.settlement_intensity import intensity_fields
from polity.service_access import walking_graph,bounded_roundtrips
from polity.service_demand import round_trip_weights,allocate_requests

PLAN=ROOT/'calibration/settlement_service_demand_20261111/plan.json'
OUT=ROOT/'output/settlement_service_demand_20261111'
INPUT=ROOT/'output/settlement_locations_20261110/rome_inputs.npz'


def main():
    OUT.mkdir(parents=True,exist_ok=True);plan=json.loads(PLAN.read_text())
    prior=json.loads((ROOT/'output/settlement_role_contrast_20261111/results.json').read_text())
    if sha(INPUT)!=prior['roman_input_sha256']:raise ValueError('Changed Roman reference input')
    for path,digest in prior['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed frozen role reference source')
    x=dict(np.load(INPUT));cell=float(x['cell_km'])
    score,eligible=site_fields(x['density'],x['land'],x['water_km'],x['road'],x['elev'],cell,allowed=x['allowed'],aridity=x['aridity'])
    original=ROOT/'output/settlement_locations_20261110/results.json'
    count=json.loads(original.read_text())['baseline']['rome']['requested']
    intensity,_=intensity_fields(score,eligible,count,cell,history=x['history']**(800/450),coefficient=.35)
    mass=intensity*cell**2
    core=(x['lat']>=49)&(x['lat']<=57)&(x['lon']>=-7)&(x['lon']<=3)
    yy,xx=np.nonzero(core)
    max_days=max(plan['transport']['one_way_budgets_days']);halo=int(np.ceil(2*max_days*30/cell))+2
    h,w=x['land'].shape;y0,y1=max(0,int(yy.min())-halo),min(h,int(yy.max())+halo+1)
    x0,x1=max(0,int(xx.min())-halo),min(w,int(xx.max())+halo+1)
    crop=np.s_[y0:y1,x0:x1];shape=x['land'][crop].shape
    demand_grid=np.where(x['land'][crop]&x['allowed'][crop],x['density'][crop]*cell**2,0.)
    local_mass=mass[crop];origins=np.flatnonzero(demand_grid>0);centres=np.flatnonzero(local_mass>0)
    demand=demand_grid.ravel()[origins];m=local_mass.ravel()[centres]
    fields={'uniform':np.ones_like(score),'environment':np.where(eligible,score,0),
            'history_L450_intensity':intensity,'core_mask':core}
    summaries=[]
    for roads in plan['transport']['road_scenarios']:
        road=x['road'][crop] if roads=='recorded_roads' else np.zeros(shape,bool)
        graph,speed=walking_graph(x['elev'][crop],x['land'][crop],road,cell)
        if speed>30+1e-8:raise ValueError('Walking speed exceeds declared halo bound')
        rr,cc,out,back=bounded_roundtrips(graph,centres,origins,max_days)
        for budget in plan['transport']['one_way_budgets_days']:
            weights=round_trip_weights(out,back,budget)
            kernel=coo_matrix((weights,(rr,cc)),shape=(len(centres),len(origins))).tocsr();kernel.eliminate_zeros()
            allocation=allocate_requests(kernel,demand,m)
            key=f'{roads}_B{budget:g}'
            for suffix,values in [('potential',allocation.accessible_potential),('allocated',allocation.allocated_requests),('per_centre',allocation.requests_per_centre)]:
                local=np.zeros(shape);local.ravel()[centres]=values
                full=np.zeros_like(score);full[crop]=local
                full[~core]=0.;fields[key+'_'+suffix]=full
            summaries.append(dict(scenario=key,roads=roads,budget_days=budget,
                candidate_cells=len(centres),demand_cells=len(origins),kernel_pairs=kernel.nnz,
                reference_demand_units=float(demand.sum()),allocated_request_units=float(allocation.allocated_requests.sum()),
                unallocated_request_units=float(allocation.origin_unallocated.sum()),
                request_balance_error=float(allocation.allocated_requests.sum()+allocation.origin_unallocated.sum()-demand.sum()),
                maximum_origin_excess=float(np.maximum(allocation.origin_allocated-demand,0).max(initial=0)),
                maximum_edge_speed_km_day=speed,global_expected_centre_mass=float(mass.sum()),
                crop_expected_centre_mass=float(m.sum()),halo_fields_not_published_as_valid=True))
            print(key,'pairs',kernel.nnz,'balance',summaries[-1]['request_balance_error'],flush=True)
    np.savez_compressed(OUT/'fields.npz',**fields)
    sources=[Path(__file__),ROOT/'polity/service_demand.py',ROOT/'polity/service_access.py',ROOT/'polity/control.py']
    result=dict(status='declared_exposed_service_fields_no_role_scores_yet',adopt=False,
        plan_sha256=sha(PLAN),input_sha256=sha(INPUT),prior_context_results_sha256=sha(ROOT/'output/settlement_role_contrast_20261111/results.json'),
        original_results_sha256=sha(original),fields_sha256=sha(OUT/'fields.npz'),
        sources={str(p.relative_to(ROOT)):sha(p) for p in sources},
        reference_grid=dict(shape=[h,w],cell_km=cell,projection='spherical azimuthal equidistant',
            latitude_origin=40.,longitude_origin=17.,radius_km=6371.,rows_run_south=True),
        core_geographic_bounds=dict(lat=[49,57],lon=[-7,3]),crop_grid_bounds=[y0,y1,x0,x1],
        halo_cells=halo,halo_equivalence='Core fields match full frozen-window graph under verified30km/day edge bound; original model-window boundaries remain.',
        request_units_are_not_residents_or_completed_services=True,
        centre_mass_is_expected_opportunity_not_staffed_places=True,scenarios=summaries,
        physical_population_food_staff_control_changed=False)
    write(OUT/'fields.json',result)


if __name__=='__main__':main()
