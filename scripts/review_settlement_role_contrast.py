"""Check the context diagnostic by direct pair comparison, not rank sums."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from prepare_settlement_role_contrast import OUT,CACHE,INPUT,PLAN
from audit_roman_rural_preparation import sha,write
from polity.settlement_locations import site_fields
from polity.settlement_intensity import intensity_fields


def main():
    result=json.loads((OUT/'results.json').read_text());prep=json.loads((OUT/'preparation.json').read_text())
    checks={'plan_sha256':PLAN,'preparation_sha256':OUT/'preparation.json',
        'private_matches_sha256':CACHE/'matched.npz','roman_input_sha256':INPUT,
        'original_results_sha256':ROOT/'output/settlement_locations_20261110/results.json',
        'prior_adaptive_results_sha256':ROOT/'output/settlement_intensity_20261110/results.json'}
    for key,path in checks.items():
        if result[key]!=sha(path):raise ValueError('Changed role-contrast evidence: '+key)
    for path,digest in result['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed diagnostic source')
    x=dict(np.load(INPUT));m=dict(np.load(CACHE/'matched.npz'));assert len(np.unique(m['source_ids']))==len(m['classes'])==2475
    score,eligible=site_fields(x['density'],x['land'],x['water_km'],x['road'],x['elev'],float(x['cell_km']),allowed=x['allowed'],aridity=x['aridity'])
    old=json.loads((ROOT/'output/settlement_locations_20261110/results.json').read_text())
    intensity,_=intensity_fields(score,eligible,old['baseline']['rome']['requested'],float(x['cell_km']),history=x['history']**(800/450),coefficient=.35)
    fields={'uniform':np.ones_like(score),'environment':np.where(eligible,score,0),'history_L450_intensity':intensity}
    checked=0
    for k,row in enumerate(result['results']):
        assert row['scenario']==str(m['scenario_names'][k])==prep['scenarios'][k]['name']
        units={cls:np.unique(m['cells'][k][(m['classes']==cls)&(m['status'][k]==0)]) for cls in [0,1]}
        for predictor,field in fields.items():
            positive,negative=(field.ravel()[units[c]] for c in [1,0])
            delta=positive[:,None]-negative[None,:]
            direct=float(np.mean((delta>0)+.5*(delta==0)))
            value=row['predictors'][predictor]
            assert abs(direct-value['AUC'])<1e-13
            assert value['represented_cell_class_units']=={str(c):len(v) for c,v in units.items()}
            assert value['mixed_cells']==len(np.intersect1d(units[0],units[1]))
            checked+=1
    assert checked==27 and result['fitted_parameters']==0 and not result['adopt']
    for rows in result['primary_strata'].values():assert sum(r['records'] for r in rows)==2475
    write(OUT/'review.json',dict(status='passed',source_result_sha256=sha(OUT/'results.json'),
        reviewer_sha256=sha(Path(__file__)),direct_pairwise_AUC_checks=checked,
        cell_class_support_and_mixed_ties=True,all_scenarios_retained=True,
        original_records_retained_in_private_cache=True,production_adopted=False))
    print('Verified27 AUC values by direct pair comparison, all support counts and mixed-cell ties.')


if __name__=='__main__':main()
