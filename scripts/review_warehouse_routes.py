"""Independent archived selection, directed CSR and predecessor certificate checks."""
import math
from pathlib import Path
import sys

import numpy as np
from scipy.sparse import coo_matrix,csr_matrix

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from select_warehouse_routes import OUT,PARENT,ANNUAL,MONTHLY,sha,read,write


def main():
    assert not (OUT/'review.json').exists(),'Preserve completed route review'
    r=read(OUT/'results.json');assert r['status']=='recovered_bounded_original_routes_pending_independent_review'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    selection=read(OUT/'selection.json');routes=read(OUT/'routes.json');restoration=read(OUT/'restoration.json')
    assert sha(OUT/'selection.json')==r['selection_sha256'] and len(routes)==len(selection['routes'])==16
    selected={row['id']:row for row in selection['routes']};assert len(selected)==16
    arrays={}
    # Independent ranking from all the original observations, not just selected rows.
    for reading in ['central','low']:
        with np.load(ANNUAL/'prepared'/f'low_{reading}.npz') as z:
            arrays[reading]={k:z[k] for k in ['nodes','dist','owner','between']}
        with np.load(MONTHLY/'cases'/reading/'fields.npz') as z:
            origin=z['source_indices'];departures=z['departures'];owner=z['owner'];retention=z['retention'];shipments=z['shipments']
        nodes=arrays[reading]['nodes']
        for q in range(4):
            amounts=[sum(float(v) for v in departures[q*3:q*3+3,i]) for i in range(len(origin))]
            eligible=[i for i,v in enumerate(amounts) if v>0 and owner[q,i]>=0 and retention[q,i]>0]
            best=min(eligible,key=lambda i:(-amounts[i],int(origin[i])))
            s=selected[f'{reading}_q{q}_source']
            assert s['origin']==int(origin[best]) and s['destination']==int(nodes[owner[q,best]])
            assert s['sent_kcal']==amounts[best]
            groups={}
            for month,i,j,sent,got in shipments:
                if int(month)//3==q and sent>0 and got>0:groups.setdefault((int(i),int(j)),[]).append(float(sent))
            totals={pair:math.fsum(values) for pair,values in groups.items()}
            pair=min(totals,key=lambda p:(-totals[p],int(nodes[p[0]]),int(nodes[p[1]])))
            s=selected[f'{reading}_q{q}_intertown']
            assert (s['origin'],s['destination'])==(int(nodes[pair[0]]),int(nodes[pair[1]]))
            # A display total may differ by floating summation order; no solver tolerances change.
            assert math.isclose(s['sent_kcal'],totals[pair],rel_tol=1e-15,abs_tol=0)
    checked=[];parallel=0;edges_checked=0;max_error=0.
    for graph in r['graphs']:
        q=graph['quarter'];cache=OUT/graph['cache'];assert sha(cache)==graph['cache_sha256']
        with np.load(cache) as archive:
            z=dict(archive)
            shape=(graph['n_nodes'],)*2
            base=csr_matrix((z['data'],z['indices'],z['indptr']),shape=shape)
            # Independent assembly of raw canonical constructor records, preserving duplicate sums.
            rebuilt=coo_matrix((z['raw_cost'],(z['raw_r'],z['raw_c'])),shape=shape).tocsr()
            for key in ['indptr','indices','data']:np.testing.assert_array_equal(getattr(rebuilt,key),getattr(base,key))
            n=graph['n_cells'];assert graph['virtual']==shape[0]-1 and shape[0]==n+len(z['river_cells'])+1
            assert base[graph['virtual']].nnz==base[:,graph['virtual']].nnz==0
            d=z['reverse_dist'];root=z['reverse_root'];p=z['reverse_parent'];own=z['owner']
            town_nodes=arrays['central']['nodes'];lookup={int(node):i for i,node in enumerate(town_nodes)}
            expected=np.array([lookup.get(int(v),-1) if np.isfinite(c) else -1 for v,c in zip(root[:n],d[:n])])
            np.testing.assert_array_equal(own,expected)
            for reading,a in arrays.items():
                np.testing.assert_array_equal(own,a['owner'][q])
                np.testing.assert_array_equal(d[:n].astype(a['dist'].dtype),a['dist'][q])
            for c in [c for c in routes if c['quarter']==q]:
                s=selected[c['id']]
                for key,value in s.items():assert c[key]==value,(c['id'],key)
                path=c['nodes'];assert path[0]==s['origin'] and path[-1]==s['destination']
                assert len(path)==len(set(path)) and all(0<=v<graph['virtual'] for v in path)
                if s['kind']=='source':
                    assert root[s['origin']]==s['destination']
                    assert all(int(p[u])==v for u,v in zip(path,path[1:]))
                    distance=float(d[s['origin']])
                else:
                    row=int(np.flatnonzero(z['senders']==s['origin'])[0]);pred=z['forward_parent'][row]
                    assert all(int(pred[v])==u for u,v in zip(path,path[1:]))
                    distance=float(z['forward_dist'][row,s['destination']])
                assert np.asarray(distance,dtype=arrays[s['reading']]['dist'].dtype).item()==s['saved_cost']
                costs=[];physical=[]
                for node in path:physical.append(node if node<n else int(z['river_cells'][node-n]))
                assert c['physical_cells']==physical
                assert len(c['edges'])==len(path)-1
                for i,(u,v) in enumerate(zip(path,path[1:])):
                    edge=c['edges'][i];assert (edge['origin'],edge['destination'])==(u,v)
                    assert edge['cost']==float(base[u,v])>0
                    raw=np.flatnonzero((z['raw_r']==u)&(z['raw_c']==v))
                    assert [rec['raw_index'] for rec in edge['raw_records']]==raw.tolist()
                    assert edge['parallel_records_summed']==(len(raw)>1)
                    for rec,j in zip(edge['raw_records'],raw):
                        assert rec['mode']==graph['labels'][int(z['raw_mode'][j])]
                        assert rec['cost']==float(z['raw_cost'][j])
                    assert np.isclose(math.fsum(rec['cost'] for rec in edge['raw_records']),edge['cost'],rtol=1e-10,atol=1e-8)
                    costs.append(edge['cost']);parallel+=int(len(raw)>1);edges_checked+=1
                cost=math.fsum(costs);error=abs(cost-distance);max_error=max(max_error,error)
                assert np.isclose(cost,distance,rtol=1e-10,atol=1e-8) and np.isclose(cost,c['csr_cost_sum'],rtol=1e-10,atol=1e-8)
                assert c['port_membership']==[v for v in path if v<n and v in restoration['ports']]
                assert c['river_landing_membership']==[v for v in path if v<n and v in restoration['river_places']]
                assert c['physical_days'] is None and not c['original_unique_path_proven'] and not c['actual_warehouse_mapping']
                checked.append(c['id'])
    assert len(checked)==len(set(checked))==16
    previous=read(PARENT/'qualification.json')
    for name,digest in previous['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    write(OUT/'review.json',dict(status='passed_independent_original_route_selection_direction_edge_and_cost_checks',
        reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),selection_rankings_checked=16,
        source_owners_and_archived_dtype_distances_exact_readings_times_quarters=8,
        selected_forward_costs_exact=8,route_certificates_checked=16,directed_edge_records_checked=edges_checked,
        selected_edges_with_summed_parallel_records=parallel,max_path_cost_sum_absolute_error=max_error,
        canonical_graph_rebuilds=0,independent_CSR_assemblies_from_saved_raw_records=4,dijkstra_calls=0,food_kernel_calls=0,
        new_Earth_food_scenarios=0,actual_warehouse_mappings=0,physical_duration_inferred=False,
        new_fit=False,new_validation_claim=False,adopt=False))
    print('Independent review passed:',len(checked),'routes,',edges_checked,'edges;',parallel,'summed parallel edges',flush=True)


if __name__=='__main__':main()
