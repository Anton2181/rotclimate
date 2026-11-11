"""Rebuild the fixed core prior on known support before any new point fit."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from polity.core_travel import travel_distance_supported
from population_cores import travel_distance,CORE_SETS,FOREST_SHARE
from polity.core_travel import FOREST_SHARE as NEW_FOREST_SHARE
from correct_population_extension import sample

OUT=ROOT/'output/core_population_inputs_20261111';EXT=ROOT/'output/earth_population_extension_20261111'
CONFIG=ROOT/'calibration/core_population_inputs_20261111'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert NEW_FOREST_SHARE==FOREST_SHARE
    correction=json.loads((EXT/'correction.json').read_text());review=json.loads((EXT/'review.json').read_text())
    assert review['status']=='passed' and review['correction_sha256']==sha(EXT/'correction.json')
    assert correction['new_han_input_sha256']==sha(EXT/'han_corrected_inputs.npz')
    paths=['output/land_people/earth/earth.npz','output/earth_population_extension_20261111/tile.npz',
        'output/earth_population_extension_20261111/global_nodata_patch.npz','output/earth_population_extension_20261111/correction.json',
        'output/earth_population_extension_20261111/review.json','scripts/population_cores.py','polity/core_travel.py',
        'rotclimate/biomes.py','scripts/correct_population_extension.py']
    sources={p:sha(ROOT/p) for p in paths}
    with np.load(ROOT/paths[0]) as z:parent={k:z[k] for k in ['lat','lon','land','T_ann','P_ann','relief']}
    with np.load(EXT/'tile.npz') as z:tile={k:z[k] for k in parent}
    with np.load(EXT/'global_nodata_patch.npz') as z:patch=dict(z)
    print('A: exact original-domain compatibility',flush=True)
    frozen=travel_distance(parent,CORE_SETS['cradles + Rome'],forest_cost=2.,sea_cost=1.,relief_cost=1.)
    a=travel_distance_supported(parent,CORE_SETS['cradles + Rome'])
    if not np.array_equal(a.distance_km,frozen):raise ValueError('Complete-support algorithm differs from frozen baseline')
    corrected=dict(parent);corrected['relief']=parent['relief'].copy();corrected['relief'].ravel()[patch['indices']]=patch['new_relief']
    print('B: same domain,corrected coastal relief',flush=True)
    b=travel_distance_supported(corrected,CORE_SETS['cradles + Rome'])
    max_b=float((b.distance_km-a.distance_km).max())
    if max_b>1e-7:raise ValueError('Decreased relief cost increased old-domain shortest paths')
    print('C: corrected supported eastern extension',flush=True)
    n_extra=108;shape=(len(parent['lat']),len(parent['lon'])+n_extra)
    longitude=np.r_[parent['lon'],parent['lon'][-1]+np.arange(1,n_extra+1)/12]
    supported=np.zeros(shape,bool);supported[:,:len(parent['lon'])]=True;supported[96:288,1644:1752]=True
    expanded=dict(lat=parent['lat'].copy(),lon=longitude)
    for key in ['land','T_ann','P_ann','relief']:
        expanded[key]=np.zeros(shape,bool) if key=='land' else np.full(shape,np.nan,np.float32)
        expanded[key][:,:1644]=corrected[key]
        expanded[key][96:288,1644:1752]=tile[key][:,60:168]
    np.testing.assert_allclose(expanded['lat'][96:288],tile['lat'],rtol=0,atol=1e-12)
    np.testing.assert_allclose(expanded['lon'][1644:1752],tile['lon'][60:168],rtol=0,atol=1e-12)
    c=travel_distance_supported(expanded,CORE_SETS['cradles + Rome'],covered=supported)
    max_c=float((c.distance_km[:,:1644]-b.distance_km).max())
    if max_c>1e-7:raise ValueError('Added supported nodes increased old-domain shortest paths')
    distance_path=OUT/'distances.npz'
    np.savez_compressed(distance_path,original=frozen,coast_corrected=b.distance_km,extended=c.distance_km,
        covered=c.covered,connected=c.connected,lat=expanded['lat'],lon=expanded['lon'])
    rows={}
    for pool in ['han','rome']:
        path=EXT/'han_corrected_inputs.npz' if pool=='han' else ROOT/'output/settlement_locations_20261110/rome_inputs.npz'
        with np.load(path) as z:x=dict(z)
        original=sample(np.exp(-frozen/800),x['lat'],x['lon'],parent['lat'],parent['lon'])
        if not np.array_equal(original,x['history']):raise ValueError('Archived history did not reconstruct: '+pool)
        d=sample(c.distance_km,x['lat'],x['lon'],expanded['lat'],expanded['lon'])
        # Coverage and connection sampled independently of the exponential prior.
        support=sample(c.covered.astype(float),x['lat'],x['lon'],expanded['lat'],expanded['lon']).astype(bool)
        connected=sample(c.connected.astype(float),x['lat'],x['lon'],expanded['lat'],expanded['lon']).astype(bool)
        required=x['land']&x['allowed']
        if not support[required].all() or not connected[required].all() or not np.isfinite(d[required]).all():
            raise ValueError('Required history outside connected known geography: '+pool)
        old_d=sample(frozen,x['lat'],x['lon'],parent['lat'],parent['lon']);delta=d[required]-old_d[required]
        output=OUT/f'{pool}_history.npz'
        np.savez_compressed(output,distance_km=d,history450=np.exp(-d/450),history800=np.exp(-d/800),
            covered=support,connected=connected,old_clipped_history800=original)
        rows[pool]=dict(input_path=str(path.relative_to(ROOT)),input_sha256=sha(path),history_sha256=sha(output),
            required_land_cells=int(required.sum()),required_land_covered_and_connected=True,
            original_history_exactly_reproduced=True,maximum_distance_change_km=float(delta.max()),
            minimum_distance_change_km=float(delta.min()),mean_distance_change_km=float(delta.mean()),
            longer_than_old_clipped_distance_cells=int((delta>1e-7).sum()),point_placement_scores_computed=False)
        print(pool,rows[pool],flush=True)
    result=dict(status='supported_core_input_reconstruction_no_point_fit',adopt=False,
        plan_sha256=sha(CONFIG/'plan.json'),producer_sha256=sha(Path(__file__)),sources=sources,
        distance_archive_sha256=sha(distance_path),baseline_exact=True,
        coast_monotonic_max_increase_km=max_b,extension_old_node_max_increase_km=max_c,
        cases={name:dict(coarse_nodes=r.coarse_nodes,coarse_directed_edges=r.coarse_edges,sources=len(r.source_nodes),
            covered_fine_cells=int(r.covered.sum()),connected_fine_cells=int(r.connected.sum())) for name,r in [('A_original',a),('B_coast_corrected',b),('C_supported_extension',c)]},
        pools=rows,history_scales_km=[450,800],forest_cost=2.,sea_cost=1.,relief_cost=1.,coarsen=3,
        point_placement_scores_computed=False,history_or_occupation_age_calibrated=False,atlas_or_food_staff_control_changed=False,
        limits='Fixed spatial-prior scenario,not politicalauthority or datedoccupation. Shortestpaths restricted to knownsourcegeometry. Alloldpools andVidarbhaspent. Nextfreezeandrunactualpointcomparison;no adoptionfromsourcechecks.')
    for p,digest in sources.items():assert sha(ROOT/p)==digest
    write(OUT/'results.json',result)


if __name__=='__main__':main()
