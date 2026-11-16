"""Exact exposed Earth annual controls; isolated restored paths and retained inputs."""
import argparse
import ast
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import greek_walls as G
from harvest.work_maps import cereal_work
from harvest.field_support import field_support

OUT=ROOT/'output/urban_seasonal_transfer_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_readiness.json'
ADAPTER=PLAN.parent/'seasonal_transfer_control_adapter.json'
RESTORE=ROOT/'output/urban_population_recipe_20261116/restored'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')


class CityColumns:
    """Exact retained cc[:,nodes], rejecting every other use of dense costs."""
    def __init__(self,costs,nodes):self.nodes=np.array(nodes,copy=True);self.values=costs[:,nodes].copy()
    def __getitem__(self,key):
        rows,columns=key
        if not isinstance(rows,slice) or rows!=slice(None) or not np.array_equal(columns,self.nodes):
            raise ValueError('Only the declared city-column projection is retained')
        return self.values


def main(stage):
    wind_plan=PLAN.parent/'seasonal_transfer_wind_restoration.json'
    for path in [PLAN,ADAPTER,wind_plan]:
        assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()
    restore=json.loads((RESTORE.parent/'restoration.json').read_text())
    assert restore['status']=='passed_exact_qualified_grid_replay'
    for name,digest in {**restore['sources_sha256'],**restore['files_sha256']}.items():assert sha(ROOT/name)==digest,name
    seasonal=ROOT/'output/urban_candidate_seasonal_20261116'
    prior=json.loads((seasonal/'results.json').read_text());review=json.loads((seasonal/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(seasonal/'results.json')
    for name,digest in {**prior['sources_sha256'],**prior['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    if stage=='low':
        import supply_low_reading as runner
    else:runner=G
    reference=ROOT/('output/supply_low_reading_20261114/results.json' if stage=='low' else 'output/greek_walls_20261114/results.json')
    archived=json.loads(reference.read_text())
    assert sha(runner.__file__)==archived['producer_sha256']
    out=OUT/stage;out.mkdir(parents=True,exist_ok=True);prepared=OUT/'prepared';prepared.mkdir(exist_ok=True)
    S,FS,E=G.S,G.FS,G.S.E
    sources=[PLAN,ADAPTER,wind_plan,OUT/'wind_restoration.json',ROOT/'scripts/restore_urban_transfer_winds.py',
        ROOT/'scripts/prepare_ncep_reference.py',Path(__file__),Path(runner.__file__),RESTORE.parent/'restoration.json',
        RESTORE/'grid/earth.npz',RESTORE/'basin/fields.npz',S.PILOT.POOL,S.PILOT.CACHE/'cities.csv',S.PILOT.CACHE/'areas.csv',reference]
    sources += [ROOT/n for n in ['scripts/settlement_supply_calibration.py','scripts/settlement_supply_earth.py','scripts/greek_walls.py',
        'scripts/supply_people_level.py','scripts/floodplain_supply.py','scripts/supply_heartland_people.py','scripts/egypt_sufficiency.py',
        'scripts/polity_earth_check.py','calibration/settlement_supply_calibration_20261113/plan.json','calibration/polity_20261025/sea.json',
        'polity/earth.py','polity/trade.py','polity/wide_supply.py','polity/network.py','polity/seasons.py','polity/control.py',
        'polity/transport.py','harvest/work_maps.py','harvest/field_support.py']]
    weather=json.loads((ROOT/'data/earth_harvest_public_sources_20261113.json').read_text())
    sources += [ROOT/a['path'] for a in weather['sources']]
    sources += [p for p in (ROOT/'data/cache/ncep_ltm').iterdir() if p.suffix in ['.nc','.npz','.ascii']]
    sourcehash={str(p.relative_to(ROOT)):sha(p) for p in sources}
    FS.GRID=RESTORE/'grid/earth.npz';FS.FIELDS=RESTORE/'basin/fields.npz';E.EARTH_NPZ=FS.GRID
    # Initial E.window density is discarded before constructing the world.
    tree=ast.parse(inspect.getsource(G.S.P.world_of))
    reads={n.slice.value for n in ast.walk(tree) if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id=='g' and isinstance(n.slice,ast.Constant)}
    assert not {'herders','covered'}&reads
    original_costs=S.T.costs_from
    def projected(net,nodes,limit=np.inf,batch=24,predecessors=False):
        assert not predecessors
        for s,c in original_costs(net,nodes,limit=limit,batch=batch):yield s,CityColumns(c,nodes)
    S.T.costs_from=projected
    original_prepare=S.prepare;base_fields=S.earth_fields;captures=[];worlds=[]
    world_of=S.P.world_of
    def observed_world(g,road=None):
        value=world_of(g,road)
        if not worlds:
            np.savez_compressed(prepared/f'{stage}_transport_world.npz',**{k:g[k] for k in ['land','lat','lon','elev','tavg','tmax','tmin','prec','u','v','wind','sigma','density','river']})
        worlds.append(hashlib.sha256(np.asarray(g['density']).tobytes()).hexdigest())
        return value
    S.P.world_of=observed_world
    names=['central','low'] if stage=='low' else [v[0] for v in G.VARIANTS]
    def captured_prepare(x):
        a,meta=original_prepare(x);name=names[len(captures)]
        wheat,barley,arable,inside=S.earth_fields(x['lat'],x['lon'])
        work=cereal_work(np.stack([wheat,barley]),S.HOURS,S.REAP,food_target=1e6)
        supply=x['land']&x['allowed'];kcal_ha=np.where(work.crop>0,1e6/np.where(work.crop>0,work.land,1.),0.)
        potential=np.where(supply,kcal_ha*100*float(x['cell_km'])**2*arable*S.FARMED*S.SOWN,0.).ravel()
        people=np.where(supply,x['density'],0.).ravel()*float(x['cell_km'])**2
        grown=field_support(potential,np.nan_to_num(work.hours).ravel(),np.nan_to_num(work.reaping).ravel(),rural_need_kcal=a['rural']*S.KCAL)
        np.testing.assert_array_equal(potential/S.KCAL,a['potential'])
        np.testing.assert_array_equal(np.maximum(grown.produced_kcal-a['rural']*S.KCAL,0)/S.KCAL,a['surplus'])
        baseline_w,baseline_b,_,_=base_fields(x['lat'],x['lon']);flood,W=FS.basin_on_pool(x['lat'],x['lon'])
        selected=np.where(work.crop==1,baseline_w,np.where(work.crop==2,baseline_b,0.))
        nonbasin=np.where(supply,(1-flood)*selected*100*float(x['cell_km'])**2*arable*S.FARMED*S.SOWN,0.).ravel()
        basin=np.where(supply,flood*W*FS.F_B*100*float(x['cell_km'])**2*arable,0.).ravel()
        np.testing.assert_allclose(nonbasin+basin,potential,atol=.001,rtol=1e-12)
        path=prepared/f'{stage}_{name}.npz'
        np.savez_compressed(path,**a,people=people,potential_kcal=potential,listed=np.nan_to_num(work.hours).ravel(),
            reaping=np.nan_to_num(work.reaping).ravel(),crop=work.crop.ravel(),grown_kcal=grown.produced_kcal,
            land=x['land'],allowed=x['allowed'],lat=x['lat'],grid_lon=x['lon'],cell_km=x['cell_km'],
            density=x['density'],history=x['history'],arable=arable,nonbasin_potential_kcal=nonbasin,
            basin_potential_kcal=basin,basin_share=flood)
        captures.append(dict(name=name,world=meta,prepared_sha256=sha(path),
            source_cells=int(supply.sum()),basin_source_cells=int(((flood>0)&supply).sum()),
            basin_potential_share=float(basin.sum()/potential.sum()),
            calendars_present=False,people_recipe='P2 capacity×history,61.4M empire normalization',
            recruitment_recipe='Uniform removal of the total city share from every empire origin; no destination-specific local migration observed.'))
        return a,meta
    S.prepare=captured_prepare
    try:
        runner.main(out)
        assert (out/'results.json').read_bytes()==reference.read_bytes(),'Annual result JSON differs from archived control'
        assert len(captures)==len(names) and len(set(worlds))==1
        for name,digest in prior['protected_sha256'].items():assert sha(ROOT/name)==digest,name
        receipt=dict(status='passed_byte_exact_archived_annual_controls',stage=stage,
            results_sha256=sha(out/'results.json'),archived_sha256=sha(reference),sources_sha256=sourcehash,
            protected_sha256=prior['protected_sha256'],captures=captures,
            grid_sha256=sha(FS.GRID),basin_fields_sha256=sha(FS.FIELDS),same_transport_density_all_cases=True,
            adapter='Runtime isolated exact-cache paths,unused initial E.window population read,exact requested city-column projection; canonical producers unchanged.',
            new_fit=False,seasonal_trial_performed=False,new_validation_claim=False,adopt=False)
        write(out/'control.json',receipt);print(stage,'ALL archived JSON bytes EXACT',flush=True)
    except BaseException as error:
        write(out/'failure.json',dict(status='preserved_failed_annual_control',stage=stage,error=f'{type(error).__name__}: {error}',
            captures=captures,sources_sha256=sourcehash,adopt=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['greek','low']);a=p.parse_args();main(a.stage)
