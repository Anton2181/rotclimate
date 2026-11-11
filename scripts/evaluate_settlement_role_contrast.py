"""Evaluate the declared conditional context contrast, with no fitting/adoption."""
import collections
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import table,identifier,number,sha,write
from polity.observed_role_contrast import context_auc
from polity.settlement_locations import site_fields
from polity.settlement_intensity import intensity_fields
from prepare_settlement_role_contrast import OUT,CACHE,PLAN,INPUT,SOURCE


def main():
    preparation=json.loads((OUT/'preparation.json').read_text())
    checks={'plan_sha256':PLAN,'producer_sha256':ROOT/'scripts/prepare_settlement_role_contrast.py',
        'matching_module_sha256':ROOT/'polity/observed_role_contrast.py','roman_input_sha256':INPUT,
        'original_results_sha256':ROOT/'output/settlement_locations_20261110/results.json',
        'private_matches_sha256':CACHE/'matched.npz'}
    for key,path in checks.items():
        if preparation[key]!=sha(path):raise ValueError('Changed conditional preparation: '+key)
    if not preparation['preparation_gate_passed']:raise ValueError('Declared preparation gate failed; no scores allowed')
    snapshot=ROOT/'output/roman_rural_preparation_20261110/source_snapshot.json'
    if sha(snapshot)!=preparation['original_source_snapshot_sha256']:raise ValueError('Changed source identities')
    for source in json.loads(snapshot.read_text())['files']:
        if sha(SOURCE/source['name'])!=source['sha256']:raise ValueError('Changed source observations')
    x=dict(np.load(INPUT));matches=dict(np.load(CACHE/'matched.npz'));classes=matches['classes']
    score,eligible=site_fields(x['density'],x['land'],x['water_km'],x['road'],x['elev'],float(x['cell_km']),
        allowed=x['allowed'],aridity=x['aridity'])
    old=json.loads((ROOT/'output/settlement_locations_20261110/results.json').read_text())
    for path,digest in old['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed frozen original source: '+path)
    prior_path=ROOT/'output/settlement_intensity_20261110/results.json'
    for path,digest in json.loads(prior_path.read_text())['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed frozen adaptive source: '+path)
    intensity,_=intensity_fields(score,eligible,old['baseline']['rome']['requested'],float(x['cell_km']),
        history=x['history']**(800/450),coefficient=.35)
    predictors={'uniform':np.ones_like(score),'environment':np.where(eligible,score,0),'history_L450_intensity':intensity}
    results=[]
    for k,name in enumerate(matches['scenario_names']):
        row=dict(scenario=str(name),predictors={})
        for predictor,field in predictors.items():
            row['predictors'][predictor]=context_auc(matches['cells'][k],classes,matches['status'][k],field)
        results.append(row)
    core,_=table((SOURCE/'rrs_core_data.csv').read_bytes(),['ID']);byid={identifier(r['id']):r for r in core}
    records=[byid[str(key)] for key in matches['source_ids']]
    def area_bin(record):
        a=number(record['area'])
        return 'missing' if a is None or a<=0 else 'positive_lt0.1ha' if a<.1 else '0.1_to_lt1ha' if a<1 else 'ge1ha'
    strata={}
    for dimension,labels in [('region',[r['region'] or 'unknown' for r in records]),
                             ('fieldwork',[r['fieldworktype'] or 'unknown' for r in records]),
                             ('investigated_area',[area_bin(r) for r in records])]:
        strata[dimension]=[]
        for label in sorted(set(labels)):
            use=np.array([v==label for v in labels]);row=dict(label=label,records=int(use.sum()),predictors={})
            for predictor,field in predictors.items():
                row['predictors'][predictor]=context_auc(matches['cells'][0][use],classes[use],matches['status'][0][use],field)
            strata[dimension].append(row)
    # Equal-block diagnostics expose broad geographic contrasts; no held-out claim.
    h,w=x['land'].shape;index=matches['cells'][0];r,c=np.divmod(index,w);cell=float(x['cell_km'])
    bx=np.floor(c*cell/50).astype(int);by=np.floor(r*cell/50).astype(int)
    blocks=collections.defaultdict(list)
    for k,key in enumerate(zip(by,bx)):
        if matches['status'][0][k]==0:blocks[key].append(k)
    block_scores={key:[] for key in predictors};both=0
    for indices in blocks.values():
        use=np.asarray(indices,int)
        for predictor,field in predictors.items():
            auc=context_auc(index[use],classes[use],matches['status'][0][use],field)['AUC']
            if auc is not None:block_scores[predictor].append(auc)
        both+=len(set(classes[use].tolist()))==2
    block_summary=dict(block_km=50,observed_blocks=len(blocks),blocks_with_both_classes=both,
        equal_block_mean_AUC={key:float(np.mean(v)) if v else None for key,v in block_scores.items()},
        independent_or_held_out=False)
    sources=[Path(__file__),ROOT/'scripts/prepare_settlement_role_contrast.py',ROOT/'polity/observed_role_contrast.py',
             ROOT/'polity/settlement_locations.py',ROOT/'polity/settlement_intensity.py']
    result=dict(status='exposed_conditional_context_diagnostic',adopt=False,plan_sha256=sha(PLAN),
        preparation_sha256=sha(OUT/'preparation.json'),private_matches_sha256=sha(CACHE/'matched.npz'),
        original_results_sha256=sha(ROOT/'output/settlement_locations_20261110/results.json'),
        prior_adaptive_results_sha256=sha(prior_path),
        roman_input_sha256=sha(INPUT),sources={str(p.relative_to(ROOT)):sha(p) for p in sources},
        results=results,primary_strata=strata,spatial_blocks=block_summary,
        fitted_parameters=0,threshold_optimized=False,all_scenarios_retained=True,
        contemporary_AD200_roles_inferred=False,source_map_generated=False,production_maps_changed=False,
        limits='Conditional discrimination within excavated recorded contexts, not settlement completeness, census accuracy or dated role qualification. Unit/cell mixing and coverage matter; strata do not eliminate source selection. No independent transfer or political authority inference.')
    write(OUT/'results.json',result)
    print('Central AUC',{key:row['AUC'] for key,row in results[0]['predictors'].items()},flush=True)
    print('Equal50km-block AUC',block_summary,flush=True)


if __name__=='__main__':main()
