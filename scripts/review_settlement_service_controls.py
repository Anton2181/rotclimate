"""Independent opportunity, rank and full-window checks for service ablations."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.sparse.csgraph import dijkstra

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import table,identifier,sha,write
from polity.service_access import walking_graph
from build_settlement_service_controls import OUT,PLAN,INPUT,PRIOR


def main():
    result=json.loads((OUT/'results.json').read_text());manifest=json.loads((OUT/'fields.json').read_text())
    for key,path in {'plan_sha256':PLAN,'fields_manifest_sha256':OUT/'fields.json','fields_sha256':OUT/'fields.npz',
        'prior_service_results_sha256':PRIOR/'results.json','producer_sha256':ROOT/'scripts/evaluate_settlement_service_controls.py',
        'frozen_context_module_sha256':ROOT/'polity/observed_role_contrast.py'}.items():
        if result[key]!=sha(path):raise ValueError('Changed control evidence: '+key)
    for path,digest in manifest['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed control source')
    fields=dict(np.load(OUT/'fields.npz'));core=fields.pop('core_mask');old=dict(np.load(PRIOR/'fields.npz'))
    x=dict(np.load(INPUT));cell=float(x['cell_km']);ok=old['environment']>0;count=1292.
    # Independently form masses by ordinary sums, not the producer normalizer.
    masses={'history_L450':old['history_L450_intensity']*cell**2,
        'environment':np.where(ok,old['environment'],0.)/old['environment'][ok].sum()*count,
        'uniform':ok.astype(float)/ok.sum()*count}
    demand=np.where(x['land']&x['allowed'],x['density']*cell**2,0.)
    for name,mass in masses.items():
        assert abs(mass.sum()-count)<1e-8
        good=(mass>0)&core
        for suffix,values in [('local_demand',demand),('zero_travel_per_centre',np.divide(demand,mass,out=np.zeros_like(mass),where=mass>0)),
                              ('inverse_mass',np.divide(1.,mass,out=np.zeros_like(mass),where=mass>0))]:
            np.testing.assert_allclose(fields[name+'__'+suffix],np.where(good,values,0),rtol=1e-12,atol=1e-10)
    for ledger in manifest['ledgers']:
        assert abs(ledger['request_balance_error'])<1e-10*max(1,ledger['reference_demand_units'])
        assert ledger['maximum_origin_excess']<1e-8
    private=ROOT/'data/cache/settlement_role_contrast_20261111/matched.npz';assert sha(private)==result['private_matches_sha256']
    matches=dict(np.load(private));roles,_=table((ROOT/'data/cache/roman_rural_britain_2018/rrs_site_t_minor.csv').read_bytes(),['ID'],'STMID')
    roadside={identifier(r['id']) for r in roles if r['sitetypeminor'].strip().casefold()=='roadside settlement'}
    masks={'full':np.ones(len(matches['classes']),bool),'strict_nonroadside':np.array([str(i) not in roadside for i in matches['source_ids']])}
    checked=0
    for subset,s in result['subsets'].items():
        for k,row in enumerate(s['results']):
            units={c:np.unique(matches['cells'][k][masks[subset]&(matches['classes']==c)&(matches['status'][k]==0)]) for c in [0,1]}
            for key,value in row['predictors'].items():
                score=fields[key].ravel();delta=score[units[1],None]-score[units[0]][None,:]
                direct=float(np.mean((delta>0)+.5*(delta==0)))
                assert abs(direct-value['AUC'])<1e-13;checked+=1
    prior=json.loads((PRIOR/'results.json').read_text());replayed=0;field_checks=0
    for key,field in fields.items():
        if key.startswith('history_L450__') and len(key.split('__'))==3:
            _,scenario,suffix=key.split('__')
            assert np.array_equal(field,old[scenario+'_'+suffix]);field_checks+=1
    for subset,s in result['subsets'].items():
        for k,row in enumerate(s['results']):
            for key,value in row['predictors'].items():
                alias=key if key in ['uniform','environment','history_L450_intensity'] else None
                if key.startswith('history_L450__') and len(key.split('__'))==3:
                    _,scenario,suffix=key.split('__');alias=scenario+'_'+suffix
                if alias:
                    assert value==prior['subsets'][subset]['results'][k]['predictors'][alias];replayed+=1
    assert checked==1188 and replayed==378 and field_checks==18
    # Changing rival masses must not make the crop normalization an unnoticed cause.
    common=core.copy()
    for mass in masses.values():common &= mass>0
    centres=np.flatnonzero(common);selected=centres[[0,len(centres)//2,-1]]
    candidate_nodes=np.flatnonzero(ok);mass_vectors={name:mass.ravel()[candidate_nodes] for name,mass in masses.items()}
    population=demand.ravel();samples=[]
    for roads in ['no_roads','recorded_roads']:
        graph,_=walking_graph(x['elev'],x['land'],x['road'] if roads=='recorded_roads' else np.zeros_like(x['road']),cell);reverse=graph.T.tocsr()
        for centre in selected:
            out=dijkstra(graph,directed=True,indices=[centre],limit=2.)[0]
            back=dijkstra(reverse,directed=True,indices=[centre],limit=2.)[0]
            for budget in [.5,1.,2.]:
                weights=np.where(np.isfinite(out)&np.isfinite(back)&(out<=budget)&(back<=budget),np.exp(-(out+back)/budget),0.)
                origins=np.flatnonzero((weights>0)&(population>0));normalizers={name:[] for name in masses}
                for first in range(0,len(origins),8):
                    roots=origins[first:first+8]
                    a=dijkstra(graph,directed=True,indices=roots,limit=budget)[:,candidate_nodes]
                    b=dijkstra(reverse,directed=True,indices=roots,limit=budget)[:,candidate_nodes]
                    kernel=np.where(np.isfinite(a)&np.isfinite(b)&(a<=budget)&(b<=budget),np.exp(-(a+b)/budget),0.)
                    for name,vector in mass_vectors.items():normalizers[name].extend(kernel@vector)
                for name,mass in masses.items():
                    z=np.asarray(normalizers[name]);at_centre=mass.ravel()[centre]
                    potential=float(np.sum(population[origins]*weights[origins]))
                    assigned=float(at_centre*np.sum(population[origins]*weights[origins]/z))
                    key=f'{name}__{roads}_B{budget:g}'
                    for suffix,value in [('potential',potential),('allocated',assigned),('per_centre',assigned/at_centre)]:
                        assert np.isclose(value,fields[key+'__'+suffix].ravel()[centre],rtol=1e-10,atol=1e-7)
                    samples.append(dict(mass_case=name,roads=roads,budget_days=budget,model_grid_node=int(centre)))
    assert len(samples)==54 and len(manifest['ledgers'])==18
    write(OUT/'review.json',dict(status='passed',source_result_sha256=sha(OUT/'results.json'),
        reviewer_sha256=sha(Path(__file__)),direct_pairwise_AUC_checks=checked,
        prior_diagnostic_controls_exact=replayed,prior_historical_fields_exact=field_checks,
        request_ledgers_checked=18,local_nulls_checked=9,full_window_cases=samples,
        chosen_predictor=None,population_food_staff_control_changed=False))
    print('Verified1188 AUCs,378 old diagnostics,18 ledgers,9 local nulls and54 full-window comparisons.')


if __name__=='__main__':main()
