"""Review request conservation, direct AUCs and crop versus full-window access."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.sparse.csgraph import dijkstra

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write,table,identifier
from polity.service_access import walking_graph
from polity.service_demand import round_trip_weights
from build_settlement_service_demand import OUT,PLAN,INPUT


def main():
    result=json.loads((OUT/'results.json').read_text());manifest=json.loads((OUT/'fields.json').read_text())
    checks={'plan_sha256':PLAN,'fields_manifest_sha256':OUT/'fields.json','fields_sha256':OUT/'fields.npz',
        'producer_sha256':ROOT/'scripts/evaluate_settlement_service_demand.py',
        'frozen_context_module_sha256':ROOT/'polity/observed_role_contrast.py'}
    for key,path in checks.items():
        if result[key]!=sha(path):raise ValueError('Changed service evidence: '+key)
    for path,digest in manifest['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed service source')
    for row in manifest['scenarios']:
        assert abs(row['request_balance_error'])<=1e-10*max(1,row['reference_demand_units'])
        assert row['maximum_origin_excess']<1e-8 and row['maximum_edge_speed_km_day']<=30+1e-8
    fields=dict(np.load(OUT/'fields.npz'));core=fields.pop('core_mask')
    private=ROOT/'data/cache/settlement_role_contrast_20261111/matched.npz'
    assert sha(private)==result['private_matches_sha256'];m=dict(np.load(private))
    roles,_=table((ROOT/'data/cache/roman_rural_britain_2018/rrs_site_t_minor.csv').read_bytes(),['ID'],'STMID')
    roadside={identifier(r['id']) for r in roles if r['sitetypeminor'].strip().casefold()=='roadside settlement'}
    masks={'full':np.ones(len(m['classes']),bool),'strict_nonroadside':np.array([str(i) not in roadside for i in m['source_ids']])}
    auc_checks=0
    for name,subset in result['subsets'].items():
        use=masks[name]
        for k,row in enumerate(subset['results']):
            samples={cls:np.unique(m['cells'][k][use&(m['classes']==cls)&(m['status'][k]==0)]) for cls in [0,1]}
            for key,predictor in row['predictors'].items():
                f=fields[key].ravel();delta=f[samples[1],None]-f[samples[0]][None,:]
                direct=float(np.mean((delta>0)+.5*(delta==0)))
                assert abs(direct-predictor['AUC'])<1e-13;auc_checks+=1
    assert auc_checks==378 and result['prior_reference_controls_exact']==27
    # Full original-window graph checks ensure the optimization did not cut rivals.
    x=dict(np.load(INPUT));cell=float(x['cell_km']);population=np.where(x['land']&x['allowed'],x['density']*cell**2,0).ravel()
    intensity=fields['history_L450_intensity'];mass=(intensity*cell**2).ravel()
    candidates=np.flatnonzero(mass>0);core_candidates=np.flatnonzero((mass>0)&core.ravel())
    selected=core_candidates[[0,len(core_candidates)//2,-1]];checks=[]
    for roads in ['no_roads','recorded_roads']:
        graph,_=walking_graph(x['elev'],x['land'],x['road'] if roads=='recorded_roads' else np.zeros_like(x['road']),cell)
        reverse=graph.T.tocsr()
        for centre in selected:
            out=dijkstra(graph,directed=True,indices=[centre],limit=2.)[0]
            back=dijkstra(reverse,directed=True,indices=[centre],limit=2.)[0]
            for budget in [.5,1.,2.]:
                weight=round_trip_weights(out,back,budget)
                origins=np.flatnonzero((weight>0)&(population>0));denominator=[]
                for first in range(0,len(origins),8):
                    roots=origins[first:first+8]
                    a=dijkstra(graph,directed=True,indices=roots,limit=budget)[:,candidates]
                    b=dijkstra(reverse,directed=True,indices=roots,limit=budget)[:,candidates]
                    denominator.extend(round_trip_weights(a,b,budget)@mass[candidates])
                z=np.asarray(denominator)
                potential=float(np.sum(population[origins]*weight[origins]))
                assigned=float(mass[centre]*np.sum(population[origins]*weight[origins]/z))
                key=f'{roads}_B{budget:g}'
                for suffix,value in [('potential',potential),('allocated',assigned),('per_centre',assigned/mass[centre])]:
                    assert np.isclose(value,fields[key+'_'+suffix].ravel()[centre],rtol=1e-10,atol=1e-7)
                checks.append(dict(scenario=key,model_grid_node=int(centre),origin_pairs=len(origins)))
    assert len(checks)==18
    write(OUT/'review.json',dict(status='passed',source_result_sha256=sha(OUT/'results.json'),
        fields_manifest_sha256=sha(OUT/'fields.json'),reviewer_sha256=sha(Path(__file__)),
        direct_pairwise_AUC_checks=auc_checks,prior_reference_controls_exact=27,
        request_budget_conserved_all_scenarios=True,full_window_crop_checks=checks,
        no_population_food_staff_control_changes=True))
    print('Verified378 direct AUCs,6 request ledgers,27 reference controls and18 full-window crop checks.')


if __name__=='__main__':main()
