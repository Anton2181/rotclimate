"""Check path optimality and consumers without rerunning the new Dijkstra kernel."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from rotclimate import biomes
from population_cores import CORE_SETS,FOREST_SHARE

OUT=ROOT/'output/core_population_inputs_20261111';EXT=ROOT/'output/earth_population_extension_20261111'


def optimality(fields,covered,distance):
    land=fields['land'];ny,nx=land.shape[0]//3,land.shape[1]//3
    reduce=lambda a:a.reshape(ny,3,nx,3).mean((1,3))
    valid=reduce(covered.astype(float))==1
    np.testing.assert_array_equal(distance,np.repeat(np.repeat(distance[::3,::3],3,0),3,1))
    d=distance[::3,::3];assert np.isinf(d[~valid]).all() and np.isfinite(d[valid]).all()
    kind=biomes.classify(np.nan_to_num(fields['T_ann']),np.nan_to_num(fields['P_ann']),land)
    forest=np.zeros(land.shape)
    for code,share in FOREST_SHARE.items():forest[kind==code]=share
    frac=reduce(land.astype(float));relief=np.clip(np.nan_to_num(fields['relief']),0,3000)/1000.
    cost=np.where(frac>=.5,1.+reduce(forest*land)/np.maximum(frac,1e-9)+reduce(relief*land)/np.maximum(frac,1e-9),1.)
    lat=fields['lat'].reshape(ny,3).mean(1);lon=fields['lon'].reshape(nx,3).mean(1)
    pred=np.zeros((ny,nx),bool)
    for a,b in CORE_SETS['cradles + Rome'].values():
        row,col=int(np.argmin(abs(lat-a))),int(np.argmin(abs(lon-b)))
        assert valid[row,col] and d[row,col]==0;pred[row,col]=True
    idx=np.arange(ny*nx).reshape(ny,nx);edges=0;maximum=0.
    for di,dj in [(0,1),(1,0),(1,1),(1,-1)]:
        a=idx[max(0,-di):ny-max(0,di),max(0,-dj):nx-max(0,dj)]
        b=idx[max(0,di):ny-max(0,-di) or None,max(0,dj):nx-max(0,-dj) or None]
        ok=valid.ravel()[a]&valid.ravel()[b];a=a[ok];b=b[ok]
        dx=abs(lon[1]-lon[0])*111.32*np.cos(np.radians((lat[a//nx]+lat[b//nx])/2))
        dy=abs(lat[1]-lat[0])*111.32
        weight=(cost.ravel()[a]+cost.ravel()[b])/2*np.hypot(di*dy,dj*dx)
        u,v=d.ravel()[a],d.ravel()[b];assert (weight>0).all()
        violation=np.abs(u-v)-weight;maximum=max(maximum,float(violation.max()))
        assert np.all(violation<=1e-6),'Bellman edge bound violated'
        pred.ravel()[b[np.abs(v-u-weight)<=1e-6]]=True
        pred.ravel()[a[np.abs(u-v-weight)<=1e-6]]=True
        edges+=2*len(a)
    # With strictly positive weights, every non-source tight predecessor descends
    # to a source; together with edge bounds this certifies shortest paths.
    assert pred[valid].all(),'Finite node lacks a tight predecessor/source path'
    return dict(valid_coarse_nodes=int(valid.sum()),directed_edges_checked=edges,max_edge_violation_km=maximum,
        all_finite_nodes_have_tight_predecessor=True)


def nearest(grid_lat,grid_lon,lat,lon):
    step=float(grid_lat[0]-grid_lat[1])
    r=(grid_lat[0]+step/2-lat)/step-.5;c=(lon-(grid_lon[0]-step/2))/step-.5
    return np.clip(np.floor(r+.5).astype(int),0,len(grid_lat)-1),np.clip(np.floor(c+.5).astype(int),0,len(grid_lon)-1)


def main():
    r=json.loads((OUT/'results.json').read_text())
    assert r['plan_sha256']==sha(ROOT/'calibration/core_population_inputs_20261111/plan.json')
    assert r['producer_sha256']==sha(ROOT/'scripts/build_core_population_inputs.py')
    for path,digest in r['sources'].items():assert sha(ROOT/path)==digest
    assert r['distance_archive_sha256']==sha(OUT/'distances.npz')
    with np.load(ROOT/'output/land_people/earth/earth.npz') as z:parent={k:z[k] for k in ['lat','lon','land','T_ann','P_ann','relief']}
    with np.load(EXT/'tile.npz') as z:tile={k:z[k] for k in parent}
    with np.load(EXT/'global_nodata_patch.npz') as z:patch=dict(z)
    with np.load(OUT/'distances.npz') as z:dist=dict(z)
    corrected=dict(parent);corrected['relief']=parent['relief'].copy();corrected['relief'].ravel()[patch['indices']]=patch['new_relief']
    expanded=dict(lat=parent['lat'],lon=dist['lon']);shape=dist['extended'].shape
    support=np.zeros(shape,bool);support[:,:1644]=True;support[96:288,1644:]=True
    for key in ['land','T_ann','P_ann','relief']:
        v=np.zeros(shape,bool) if key=='land' else np.full(shape,np.nan,np.float32)
        v[:,:1644]=corrected[key];v[96:288,1644:]=tile[key][:,60:];expanded[key]=v
    np.testing.assert_array_equal(dist['covered'],support)
    np.testing.assert_array_equal(dist['connected'],support)
    checks={}
    for name,fields,known,values in [('A_original',parent,np.ones(parent['land'].shape,bool),dist['original']),
        ('B_coast_corrected',corrected,np.ones(parent['land'].shape,bool),dist['coast_corrected']),
        ('C_supported_extension',expanded,support,dist['extended'])]:
        checks[name]=optimality(fields,known,values)
        assert checks[name]['valid_coarse_nodes']==r['cases'][name]['coarse_nodes']
        assert checks[name]['directed_edges_checked']==r['cases'][name]['coarse_directed_edges']
    assert np.all(dist['coast_corrected']<=dist['original']+1e-7)
    assert np.all(dist['extended'][:,:1644]<=dist['coast_corrected']+1e-7)
    for pool,p in r['pools'].items():
        assert sha(ROOT/p['input_path'])==p['input_sha256'] and sha(OUT/f'{pool}_history.npz')==p['history_sha256']
        with np.load(ROOT/p['input_path']) as z:x=dict(z)
        with np.load(OUT/f'{pool}_history.npz') as z:h=dict(z)
        rr,cc=nearest(parent['lat'],parent['lon'],x['lat'],x['lon'])
        np.testing.assert_array_equal(np.exp(-dist['original']/800)[rr,cc],x['history'])
        np.testing.assert_array_equal(h['old_clipped_history800'],x['history'])
        rr,cc=nearest(expanded['lat'],expanded['lon'],x['lat'],x['lon'])
        np.testing.assert_array_equal(h['distance_km'],dist['extended'][rr,cc])
        np.testing.assert_array_equal(h['covered'],support[rr,cc])
        for scale in [450,800]:np.testing.assert_array_equal(h[f'history{scale}'],np.exp(-h['distance_km']/scale))
        needed=x['land']&x['allowed'];assert h['covered'][needed].all() and h['connected'][needed].all()
    assert not r['adopt'] and not r['point_placement_scores_computed'] and not r['atlas_or_food_staff_control_changed']
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),
        method='Independent edge-bound and tight-predecessor optimality certificates,not a second run of the new Dijkstra kernel',
        cases=checks,total_directed_edge_constraints=sum(v['directed_edges_checked'] for v in checks.values()),
        all_source_nodes_zero=True,unsupported_geometry_excluded=True,consumer_fields_independently_sampled=True,
        monotonic_cost_and_domain_checks=True,no_new_point_or_occupation_qualification=True))
    print('Independent path review passed:',sum(v['directed_edges_checked'] for v in checks.values()),'directed edges;both consumer grids checked.')


if __name__=='__main__':main()
