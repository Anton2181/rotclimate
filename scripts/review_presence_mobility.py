"""Check public food/circuit ledgers and refine the finite reserve grid."""
from pathlib import Path
import gzip
import json
import sys
import subprocess

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    from harvest.food_stocks import periodic_food_year
    from harvest.seasonal_mobility import seasonal_circuit
    from local_benchmark_protocol import file_hash,write_json
    out=ROOT/'output/presence_mobility_scale_20261104';checks=[];refinements=[];baseline='b919802e'
    for name in ['free_fit','earth_fit','whittaker_fit']:
        data=ROOT/'atlases'/name/'data';manifest=json.loads((data/'presence_mobility.json').read_text())
        for source,h in manifest['sources_sha256'].items():assert file_hash(ROOT/source)==h,source
        for mode,packet in manifest['packets'].items():
            assert file_hash(data/packet['payload'])==packet['payload_sha256']
            assert file_hash(data/packet['catchments'])==packet['catchments_sha256']
            for image,h in packet['image_sha256'].items():assert file_hash(data/image)==h
            m=json.loads(gzip.decompress((data/packet['payload']).read_bytes()));spec=m['specification'];ps=spec['presence'];ms=spec['mobility']
            previous=json.loads(gzip.decompress(subprocess.check_output(['git','show',baseline+':'+str((data/packet['payload']).relative_to(ROOT))],cwd=ROOT)))
            assert m['mobility']==previous['mobility'],'Original local circuits changed'
            for case in previous['presence']:
                assert next(c for c in m['presence'] if c['id']==case['id'])==case
                assert m['balances'][case['id']]==previous['balances'][case['id']]
            assert (data/packet['catchments']).read_bytes()==subprocess.check_output(['git','show',baseline+':'+str((data/packet['catchments']).relative_to(ROOT))],cwd=ROOT)
            grid=np.frombuffer(gzip.decompress((data/packet['catchments']).read_bytes()),'<u2').reshape(packet['shape'])
            assert grid.max()<=len(m['sites']) and len({s['node'] for s in m['sites']})==len(m['sites'])==151
            reviewed=0
            for case in m['presence']:
                arrival=np.array([r['monthly_arrivals_kcal'] for r in case['sites']]).T;need=np.full_like(arrival,case['people']*ps['ration_kcal_person_day']*spec['year_days']/12)
                year=periodic_food_year(arrival,need,case['people']*ps['ration_kcal_person_day']*case['reserve_days'],
                    loss_fraction_year=ps['stored_energy_loss_fraction_year'],step_days=spec['year_days']/12,record=True)
                np.testing.assert_allclose(1-year.unmet_path/need,np.array([r['monthly_need_met'] for r in case['sites']]).T,atol=1e-10)
                np.testing.assert_allclose(year.stock_path,np.array([r['stock_path_kcal'] for r in case['sites']]).T,rtol=1e-10,atol=1e-4)
                assert np.all(arrival<=ps['freight_kcal_per_site_per_bin']*case.get('freight_multiplier',1)*ps['delivery_retention']+1e-4)
                for r in case['sites']:
                    for dispatch in r['closed_dispatch_bins']:assert r['monthly_arrivals_kcal'][(dispatch+ps['delivery_delay_bins'])%12]==0
                b=m['balances'][case['id']]
                residual=b['harvested']-sum(b[k] for k in ['rural_consumed','rural_storage_loss','uncollected_or_unavailable','collection_storage_loss','transport_loss','site_consumed','site_storage_loss','site_unused'])
                assert abs(residual)/max(b['harvested'],1)<1e-7
                if case.get('rural_store_days',ps['rural_store_demand_days'])==ps['rural_store_demand_days']:
                    assert b['rural_unmet']<1e-7*max(1,b['harvested'])
                if case['id']=='rural180':
                    assert b['rural_unmet']>0 and b['export_withheld_for_rural_deficit']>0 and b['departed']==0
                reviewed+=len(case['sites'])*12
            circuits=0
            groups={'local':m['mobility'],**m.get('mobility_scales',{})}
            for scale,examples in groups.items():
              for e in examples:
                if e['status']!='scored_resource_landscape':continue
                nodes=e.get('ground_nodes',e['patches']);ground_ids=np.array(e.get('patch_ground_nodes',list(range(len(e['patches'])))))
                n=len(nodes);edges=np.array(e['ground_edges']).reshape(-1,3);ground=csr_matrix((edges[:,2],(edges[:,0].astype(int),edges[:,1].astype(int))),shape=(n,n))
                travel=dijkstra(ground,directed=True,indices=ground_ids)[:,ground_ids];travel[travel>ms['maximum_move_days_per_bin']]=np.inf;np.fill_diagonal(travel,0)
                supply=np.array([p['monthly_dm_kg'] for p in e['patches']]).T;daily=ms['reference_feed_units']*ms['intake_kg_dm_reference_unit_day'];demand=daily*spec['year_days']/12
                ground_supply=np.array([p['monthly_dm_kg'] for p in nodes]).T
                fixed=periodic_food_year(ground_supply,np.full_like(ground_supply,demand),daily*ms['reserve_days'],step_days=spec['year_days']/12)
                for case in e['cases']:
                    threshold=case['maximum_mapped_water_distance_km'];allowed_ground=np.ones(n,bool) if threshold is None else np.array([p['water_distance_km']<=threshold for p in nodes])
                    allowed=allowed_ground[ground_ids]
                    if not allowed[e['home']]:assert case['mobile'] is None and case['stationary'] is None
                    for which in ['mobile','stationary']:
                        r=case[which]
                        if r is None:continue
                        pos=np.array(r['locations']);res=np.array(r['reserves']);collected=np.array(r['collected']);eaten=np.array(r['consumed']);unmet=np.array(r['unmet']);trip=np.array(r['travel_days'])
                        assert pos[-1]==e['home'] and res[0]==res[-1] and len(pos)==12
                        assert np.all(allowed[pos]) and np.all(res<=ms['reserve_days']*daily+1e-7)
                        np.testing.assert_allclose(res[:-1]+collected-eaten,res[1:],atol=1e-6)
                        np.testing.assert_allclose(eaten+unmet,demand,atol=1e-6)
                        assert np.all(collected<=supply[np.arange(12),pos]+1e-6)
                        np.testing.assert_allclose(r['discarded'],supply[np.arange(12),pos]-collected,atol=1e-6)
                        assert np.all(unmet>=np.maximum(trip*daily-res[:-1],0)-1e-6)
                        previous=e['home']
                        for t,segment in enumerate(r['segments']):
                            assert segment[0]==ground_ids[previous] and segment[-1]==ground_ids[pos[t]]
                            actual=sum(float(ground[a,b]) for a,b in zip(segment,segment[1:]))
                            assert all(float(ground[a,b])>0 for a,b in zip(segment,segment[1:]))
                            assert abs(actual-trip[t])<1e-8 and trip[t]<=ms['maximum_move_days_per_bin']
                            previous=pos[t]
                        circuits+=1
                    if allowed_ground.any():
                        expected=float(np.max(np.where(allowed_ground,1-fixed.unmet/(12*demand),-1)))
                        assert abs(expected-case['best_fixed_base_continuous']['annual_need_met'])<1e-10
                        if scale!='local':
                            envelope=ground_supply[:,allowed_ground].max(1)
                            np.testing.assert_allclose(envelope,case['resource_upper_bound']['monthly_max_dm_kg'])
                            upper=periodic_food_year(envelope,np.full(12,demand),daily*ms['reserve_days'],step_days=spec['year_days']/12)
                            optimistic=1-float(upper.unmet)/(12*demand)
                            assert abs(optimistic-case['resource_upper_bound']['annual_need_met'])<1e-10
                            assert expected<=optimistic+1e-9
                            if case['mobile']:assert case['mobile']['annual_need_met']<=optimistic+1e-9
                if name=='earth_fit' and mode=='corrected' and scale in ['local','regional_dense']:
                    c=e['cases'][0];refined=seasonal_circuit(supply,travel,e['home'],daily_need=daily,reserve_days=ms['reserve_days'],reserve_quantum_days=.5)
                    refined_met=refined.consumed.sum()/(12*demand)
                    assert refined_met>=c['mobile']['annual_need_met']-1e-9
                    refinements.append(dict(scale=scale,landscape=e['id'],one_day_reserve_need_met=c['mobile']['annual_need_met'],half_day_reserve_need_met=float(refined_met),
                        improvement_percentage_points=float(100*(refined_met-c['mobile']['annual_need_met'])),
                        best_fixed_base_continuous=c['best_fixed_base_continuous']['annual_need_met']))
                    print('Refined',e['id'],refinements[-1],flush=True)
            for a,b in zip(groups['regional_sparse'],groups['regional_dense']):
                assert a['ground_nodes']==b['ground_nodes']
                assert {(p['row'],p['column']) for p in a['patches']}.issubset({(p['row'],p['column']) for p in b['patches']})
                for sparse,dense in zip(a['cases'],b['cases']):
                    if sparse['mobile']:assert dense['mobile']['annual_need_met']>=sparse['mobile']['annual_need_met']-1e-9
                    assert sparse['best_fixed_base_continuous']==dense['best_fixed_base_continuous']
                    assert sparse['resource_upper_bound']==dense['resource_upper_bound']
            for local,regional in zip(groups['local'],groups['regional_sparse']):
                available={(p['row'],p['column']) for p in regional['ground_nodes']}
                assert {(p['row'],p['column']) for p in local['patches']}&available <= {(p['row'],p['column']) for p in regional['patches']}
                for a,b in zip(local['cases'],regional['cases']):
                    if a['mobile']:assert b['mobile']['annual_need_met']>=a['mobile']['annual_need_met']-1e-9
            checks.append(dict(atlas=name,climate=mode,site_bin_ledgers=reviewed,closed_circuits=circuits,old_local_and_seven_presence_cases='byte_equal_values',payload_sha256=packet['payload_sha256']))
            print('Verified',name,mode,checks[-1],flush=True)
    write_json(out/'independent_review.json',dict(status='passed',packets=checks,earth_corrected_reserve_refinements=refinements,
        reviewer_sha256=file_hash(Path(__file__)),scope='Public-ledger consistency, actual route segments, matched controls and reserve-resolution sensitivity; not empirical validation.'))


if __name__=='__main__':main()
