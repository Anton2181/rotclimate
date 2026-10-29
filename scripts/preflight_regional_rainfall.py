"""Validate frozen benchmark geometry, reference identities and initial ensembles."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import case_hash,file_hash,write_json
from rotclimate import earth
from rotclimate.config import Params
from rotclimate.rainfall_validation import aggregate_footprints
from circulation_reference import projection_jacobian
import rainfall_month_pilot


def run(path,out):
    plan=json.loads(path.read_text())
    for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
    records={};prototypes={}
    for spec in plan['cases']:
        p=json.loads((ROOT/spec['plan']).read_text());region=spec['region']
        if spec['kind']=='legacy':
            earth.REGIONS[region]=p['region_spec'];base=Params.from_json(ROOT/p['physics']);case=earth.region_case(region,p['cell_km']);prior=json.loads((ROOT/p['archived_case']).read_text());identity=case_hash(case,observed_sea=base.sst_source=='observed');assert identity==prior['case_identity']
            g=case.grid;definition=p['region_spec'];area=g.cell_km**2/projection_jacobian(g.lat,case.lon,definition['lat0'],definition['lon0'])[-1]
            valid=g.inmap&g.land&np.isfinite(case.obs_P).all(0);aggregated=aggregate_footprints(case.obs_P,valid,area,stride=4)
            mask=g.land[::4,::4]&g.inmap[::4,::4]&(aggregated['coverage']>=.8);mask[[0,-1]]=False;mask[:,[0,-1]]=False;assert mask.any()
            elevation=aggregate_footprints(g.elev,valid,area,stride=4)['mean'];coast=aggregate_footprints(case.coast_km,valid,area,stride=4)['mean']
            fields=dict(observed_monthly_rain=aggregated['mean'],valid_area_km2=aggregated['valid_area_km2'],available_area_km2=aggregated['available_area_km2'],coverage=aggregated['coverage'],score_mask=mask,latitude=g.lat[::4,::4],longitude=case.lon[::4,::4],land=g.land[::4,::4],mean_elevation_m=elevation,mean_coast_km=coast)
            target=path.parent/(region+'_footprints.npz')
            if target.exists():
                with np.load(target) as a:
                    assert set(a.files)==set(fields)
                    for k,v in fields.items():np.testing.assert_array_equal(a[k],v)
            else:np.savez_compressed(target,**fields)
            records[region]=dict(r39_identity_exact=True,eligible_cells=int(mask.sum()),scored_area_km2=float(aggregated['valid_area_km2'][mask].sum()),footprints_file=str(target.relative_to(ROOT)),footprints_sha256=file_hash(target),shape=list(mask.shape))
        else:
            values=rainfall_month_pilot.prepare(p,region);base,a,model,state,surface=values[:5]
            assert model.nz==9 and base['maximum_convective_sweeps']==1024
            assert base['regions'][region]['model_day']==p['calendar']['integration_start_day']
            assert np.array_equal(a['latitude'],np.load(path.parent/(region+'_footprints.npz'))['latitude'])
            for dt in p['timesteps_s']:assert p['duration_s']%dt==0
            prototypes[spec['name']]=dict(levels=model.nz,steps=p['duration_s']//p['timesteps_s'][0],duration_days=p['duration_s']/86400,initial_land_liquid_setting=p['surface']['land_initial_liquid_kg_m2'],atmospheric_temperature_sha256=__import__('hashlib').sha256(state.temperature_k.tobytes()).hexdigest(),atmospheric_vapor_sha256=__import__('hashlib').sha256(state.vapor_kg_m2.tobytes()).hexdigest())
    for region in records:
        branches=[v for k,v in prototypes.items() if k.startswith(region+'_')];assert len({v['atmospheric_temperature_sha256'] for v in branches})==1 and len({v['atmospheric_vapor_sha256'] for v in branches})==1
    result=dict(status='benchmark_inputs_and_fixed_footprints_prepared',actual_earth_integrations_started=0,legacy_controls_prepared=3,prototype_trials_prepared=7,regions=records,prototype_preparations=prototypes,literal_plan_sha256=file_hash(path),scope='Input/geometry preparation only. No forecast, observed-error computation or initialization selection. Each region has identical initial atmosphere across water/timestep scenarios.')
    write_json(out,result);print(json.dumps({k:v for k,v in result.items() if k!='prototype_preparations'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.plan.resolve(),a.out)
