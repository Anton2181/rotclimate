"""Recover only the declared original directed paths, preserving legacy CSR costs."""
import platform
from pathlib import Path
import subprocess
import sys

import numpy as np
import scipy
from scipy import ndimage as ndi
from scipy.sparse.csgraph import dijkstra

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from select_warehouse_routes import OUT,PARENT,ANNUAL,PLAN,sha,read,write
from polity import earth as E,network as N,trade as T,transport as X,control as C
from rotclimate import biomes
import polity_earth_check as P


def array_hash(a):
    import hashlib
    a=np.asarray(a)
    return hashlib.sha256(str(a.dtype).encode()+str(a.shape).encode()+a.tobytes()).hexdigest()


def verify(mapping,prefix=ROOT):
    for name,digest in mapping.items():assert sha(prefix/name)==digest,name


def restore():
    """Complete captured window by the exact original grid/biome recipe, no reader."""
    control=read(ANNUAL/'low/control.json');verify(control['sources_sha256'])
    assert control['same_transport_density_all_cases']
    a={}
    for reading in ['central','low']:
        with np.load(ANNUAL/'prepared'/f'low_{reading}.npz') as z:
            a[reading]={k:z[k] for k in ['nodes','land','density','lat','grid_lon','cell_km','dist','owner','between']}
    for key in a['central']:np.testing.assert_array_equal(a['central'][key],a['low'][key])
    with np.load(ANNUAL/'prepared/low_transport_world.npz') as z:g=dict(z)
    window=read(ROOT/'calibration/polity_20261025/plan.json')['earth_windows']['rome']
    grid=E.grid(**window)
    for key in ['lat','lon']:np.testing.assert_array_equal(grid[key],g[key])
    for key,other in [('land','land'),('density','density'),('lat','lat'),('lon','grid_lon')]:
        np.testing.assert_array_equal(g[key],a['central'][other])
    assert grid['cell_km']==float(a['central']['cell_km'])
    g.update({k:grid[k] for k in ['cell_km','lat0','lon0']})
    # Exact expression used by E.window; no climate read/generation or wind fallback.
    g['biome']=biomes.classify(g['tavg'].mean(0),g['prec'].sum(0),g['land'])
    with np.load(ROOT/'output/settlement_locations_20261110/rome_inputs.npz') as z:
        road=z['road'];np.testing.assert_array_equal(z['land'],g['land'])
    P.apply_sea();world=P.world_of(g,road);st=N.statics(world);cl=N.climate(world,st)
    nodes=a['central']['nodes'];width=g['land'].shape[1]
    places=[(int(n//width),int(n%width)) for n in nodes]
    ports=X.ports_of(places,st['water']);near=ndi.binary_dilation(st['basin']>0,iterations=1)
    river_places=[p for p in places if near[p]]
    for capture in control['captures']:
        assert len(ports)==capture['world']['ports']==179
        assert len(river_places)==capture['world']['river_landings']==206
    receipt=dict(status='restored_original_captured_world_by_exact_grid_and_biome_recipe',
        capture_sha256=sha(ANNUAL/'prepared/low_transport_world.npz'),control_sha256=sha(ANNUAL/'low/control.json'),
        road_sha256=sha(ROOT/'output/settlement_locations_20261110/rome_inputs.npz'),window=window,
        captured_field_hashes={k:array_hash(v) for k,v in g.items()},
        world_field_hashes={k:array_hash(v) for k,v in world.items() if v is not None},
        graph_inputs_and_endpoint_order_identical_across_readings=True,
        archived_dist_owner_between_identical_across_readings=True,
        ports=[int(y*width+x) for y,x in ports],river_places=[int(y*width+x) for y,x in river_places],
        recipe='Captured weather/winds/land/elevation/river/density;E.grid metadata;E.window biome expression;archived road;P.world_of straits;P.apply_sea;N.statics/climate adapters.',
        new_weather_generation=False,wind_reader_calls=0,raw_city_table_read=False)
    return a,g,world,st,cl,ports,river_places,receipt


def chain(parent,start,end,reverse):
    result=[start] if reverse else [end]
    stop=end if reverse else start
    seen=set(result)
    while result[-1]!=stop:
        node=int(parent[result[-1]])
        assert node>=0 and node not in seen,'Invalid/cyclic predecessor chain'
        result.append(node);seen.add(node)
        assert len(result)<=len(parent)
    return result if reverse else result[::-1]


def main():
    selection=read(OUT/'selection.json')
    for path in [PLAN,OUT/'selection.json']:
        assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()
    verify(selection['sources_sha256'])
    previous=read(PARENT/'qualification.json');verify(previous['protected_sha256'])
    assert not (OUT/'results.json').exists() and not (OUT/'failure.json').exists(),'Preserve completed/failed route replay'
    local=OUT/'local';local.mkdir(exist_ok=True)
    a,g,world,st,cl,ports,river_places,receipt=restore()
    write(OUT/'restoration.json',receipt)
    inputs=['scripts/recover_warehouse_routes.py','scripts/select_warehouse_routes.py','polity/earth.py','rotclimate/biomes.py',
        'rotclimate/earth.py','polity/control.py','polity/network.py','polity/seasons.py','polity/trade.py','polity/transport.py',
        'scripts/polity_earth_check.py','calibration/polity_20261025/plan.json','calibration/polity_20261025/sea.json',
        'calibration/settlement_supply_calibration_20261113/plan.json',
        'output/urban_seasonal_transfer_20261116/wind_1981/low/control.json',
        'output/urban_seasonal_transfer_20261116/wind_1981/prepared/low_transport_world.npz',
        'output/settlement_locations_20261110/rome_inputs.npz']
    sources={**selection['sources_sha256'],**{p:sha(ROOT/p) for p in inputs}}
    nodes=a['central']['nodes'];n=g['land'].size
    limit=float(max(read(ROOT/'calibration/settlement_supply_calibration_20261113/plan.json')['parameters']['haul_limit_L_road_km']))
    lookup=np.full(n,-1,int);lookup[nodes]=np.arange(len(nodes))
    graphs=[];certificates=[];calls=0
    for quarter,month in enumerate(T.TRADE_MONTHS):
        # Capture canonical constructor arguments; retain its unchanged COO→CSR sum.
        canonical=C.Network
        class CapturedNetwork(canonical):
            def __init__(self,n_cells,edges,n_extra=0):
                super().__init__(n_cells,edges,n_extra)
                self.raw_edges=edges
        C.Network=CapturedNetwork
        try:net=T.cost_network(world,st,cl,month,ports,river_places)
        finally:C.Network=canonical
        labels=['land','sea']+(['harbour'] if ports else [])+(['river','river_transfer'] if len(st['river_cells']) else [])
        assert len(labels)==len(net.raw_edges)
        raw_r=np.concatenate([v[0] for v in net.raw_edges]);raw_c=np.concatenate([v[1] for v in net.raw_edges]);raw_cost=np.concatenate([v[2] for v in net.raw_edges])
        raw_mode=np.concatenate([np.full(len(v[0]),i,np.uint8) for i,v in enumerate(net.raw_edges)])
        reverse_d,parent,root=dijkstra(net.base.T.tocsr(),directed=True,indices=nodes,min_only=True,return_predecessors=True,limit=limit);calls+=1
        d=reverse_d[:n];src=root[:n];valid=np.isfinite(d)&(src>=0)
        owner=np.full(n,-1,int);owner[valid]=lookup[src[valid]]
        for reading in a:
            np.testing.assert_array_equal(owner,a[reading]['owner'][quarter])
            np.testing.assert_array_equal(np.where(owner>=0,d,np.inf).astype(a[reading]['dist'].dtype),a[reading]['dist'][quarter])
        selected=[r for r in selection['routes'] if r['quarter']==quarter]
        senders=np.array(sorted({r['origin'] for r in selected if r['kind']=='intertown'}),np.int64)
        forward_d,forward_parent=dijkstra(net.base,directed=True,indices=senders,return_predecessors=True,limit=limit);calls+=1
        # Check every selected cost before interpreting any of this snapshot's paths.
        for r in selected:
            if r['kind']=='source':
                distance=d[r['origin']];assert r['destination']==int(root[r['origin']])
            else:
                index=int(np.flatnonzero(senders==r['origin'])[0]);distance=forward_d[index,r['destination']]
            assert np.asarray(distance,dtype=a[r['reading']]['dist'].dtype).item()==r['saved_cost'],r['id']
        cache=local/f'q{quarter}.npz'
        np.savez_compressed(cache,indptr=net.base.indptr,indices=net.base.indices,data=net.base.data,
            raw_r=raw_r,raw_c=raw_c,raw_cost=raw_cost,raw_mode=raw_mode,river_cells=net.river_cells,
            reverse_dist=reverse_d,reverse_parent=parent,reverse_root=root,owner=owner,
            senders=senders,forward_dist=forward_d,forward_parent=forward_parent)
        graphs.append(dict(quarter=quarter,month=month,n_cells=n,n_nodes=net.n,virtual=net.virtual,csr_nnz=net.base.nnz,
            raw_edge_count=len(raw_r),labels=labels,limit=limit,cache=str(cache.relative_to(OUT)),cache_sha256=sha(cache),
            source_owner_and_archived_dtype_distance_exact_both_readings=True))
        for r in selected:
            reverse=r['kind']=='source'
            if reverse:pred=parent;distance=d[r['origin']]
            else:
                index=int(np.flatnonzero(senders==r['origin'])[0]);pred=forward_parent[index];distance=forward_d[index,r['destination']]
            path=chain(pred,r['origin'],r['destination'],reverse)
            assert all(0<=v<net.virtual for v in path)
            edges=[]
            for u,v in zip(path,path[1:]):
                candidates=np.flatnonzero((raw_r==u)&(raw_c==v));assert len(candidates)
                cost=float(net.base[u,v]);assert cost>0 and np.isfinite(cost)
                records=[dict(raw_index=int(i),mode=labels[int(raw_mode[i])],cost=float(raw_cost[i])) for i in candidates]
                edges.append(dict(origin=u,destination=v,cost=cost,raw_records=records,
                    parallel_records_summed=len(candidates)>1,unique_physical_mode_inferred=False))
            cost=float(np.array([edge['cost'] for edge in edges]).sum())
            assert np.isclose(cost,distance,rtol=1e-10,atol=1e-8)
            physical=[v if v<n else int(net.river_cells[v-n]) for v in path]
            certificates.append(dict(**r,nodes=path,physical_cells=physical,edges=edges,replayed_distance=float(distance),
                csr_cost_sum=cost,port_membership=[v for v in path if v<n and v in receipt['ports']],
                river_landing_membership=[v for v in path if v<n and v in receipt['river_places']],
                representative_least_cost_path=True,original_unique_path_proven=False,physical_days=None,
                actual_warehouse_mapping=False))
        write(OUT/f'q{quarter}_identity.json',graphs[-1])
        print('Quarter',quarter,'exact source identities; recovered',len(selected),'selected paths',flush=True)
    write(OUT/'routes.json',certificates)
    verify(previous['protected_sha256'])
    write(OUT/'results.json',dict(status='recovered_bounded_original_routes_pending_independent_review',
        sources_sha256=sources,protected_sha256=previous['protected_sha256'],selection_sha256=sha(OUT/'selection.json'),
        files_sha256={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()},graphs=graphs,
        route_count=len(certificates),graph_rebuilds=4,dijkstra_calls=calls,food_kernel_calls=0,new_Earth_food_scenarios=0,
        new_all_pairs_tables=0,actual_warehouse_mappings=0,actual_population_changed=False,new_fit=False,new_validation_claim=False,
        adopt=False,main_atlas_changed=False,versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__)))


if __name__=='__main__':
    try:main()
    except BaseException as error:
        OUT.mkdir(exist_ok=True)
        if not (OUT/'failure.json').exists():
            write(OUT/'failure.json',dict(status='preserved_original_route_recovery_failure',error=f'{type(error).__name__}: {error}',
                producer_sha256=sha(Path(__file__)),adopt=False))
        raise
