"""Conditional role diagnostics with all predeclared opportunity/null controls."""
import collections
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import table,identifier,number,sha,write
from polity.observed_role_contrast import context_auc,cell_class_summary
from build_settlement_service_controls import OUT,PLAN,PRIOR,INPUT


def main():
    manifest=json.loads((OUT/'fields.json').read_text());prior_path=PRIOR/'results.json';prior=json.loads(prior_path.read_text())
    for key,path in {'plan_sha256':PLAN,'input_sha256':INPUT,'fields_sha256':OUT/'fields.npz'}.items():
        if manifest[key]!=sha(path):raise ValueError('Changed opportunity evidence: '+key)
    for path,digest in manifest['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed opportunity source')
    private=ROOT/'data/cache/settlement_role_contrast_20261111/matched.npz'
    if sha(private)!=prior['private_matches_sha256']:raise ValueError('Changed private matches')
    snapshot=ROOT/'output/roman_rural_preparation_20261110/source_snapshot.json'
    if sha(snapshot)!=prior['source_snapshot_sha256']:raise ValueError('Changed source identities')
    source=ROOT/'data/cache/roman_rural_britain_2018'
    for item in json.loads(snapshot.read_text())['files']:
        if sha(source/item['name'])!=item['sha256']:raise ValueError('Changed source observations')
    m=dict(np.load(private));classes=m['classes'];fields=dict(np.load(OUT/'fields.npz'));core=fields.pop('core_mask')
    if not np.all(core.ravel()[m['cells']][m['status']==0]):raise ValueError('Previously included cells outside declared core')
    roles,_=table((source/'rrs_site_t_minor.csv').read_bytes(),['ID'],'STMID')
    roadside={identifier(r['id']) for r in roles if r['sitetypeminor'].strip().casefold()=='roadside settlement'}
    masks={'full':np.ones(len(classes),bool),'strict_nonroadside':np.array([str(i) not in roadside for i in m['source_ids']])}
    records,_=table((source/'rrs_core_data.csv').read_bytes(),['ID']);byid={identifier(r['id']):r for r in records}
    records=[byid[str(i)] for i in m['source_ids']]
    def area(r):
        a=number(r['area'])
        return 'missing' if a is None or a<=0 else 'positive_lt0.1ha' if a<.1 else '0.1_to_lt1ha' if a<1 else 'ge1ha'
    labels={'region':[r['region'] or 'unknown' for r in records],
            'fieldwork':[r['fieldworktype'] or 'unknown' for r in records],'investigated_area':[area(r) for r in records]}
    aliases={key:key for key in ['uniform','environment','history_L450_intensity']}
    for key in fields:
        if key.startswith('history_L450__') and len(key.split('__'))==3:
            _,scenario,suffix=key.split('__');aliases[key]=scenario+'_'+suffix
    subsets={};replayed=0;w=core.shape[1];cell=float(np.load(INPUT)['cell_km'])
    interaction_keys=[key for key in fields if len(key.split('__'))==3]
    for subset,use in masks.items():
        support=cell_class_summary(m['cells'][0][use],classes[use],m['status'][0][use]);rows=[];strata={};blocks={}
        if support['preparation_gate_passed']:
            for k,name in enumerate(m['scenario_names']):
                predictors={key:context_auc(m['cells'][k][use],classes[use],m['status'][k][use],field) for key,field in fields.items()}
                for key,old_key in aliases.items():
                    if predictors[key]!=prior['subsets'][subset]['results'][k]['predictors'][old_key]:raise ValueError('Historical service diagnostic changed')
                    replayed+=1
                deltas={}
                for key in interaction_keys:
                    mass,scenario,field=key.split('__');null=mass+'__'+('zero_travel_per_centre' if field=='per_centre' else 'local_demand')
                    a,b=predictors[key]['AUC'],predictors[null]['AUC'];deltas[key]=None if a is None or b is None else a-b
                rows.append(dict(coordinate_scenario=str(name),predictors=predictors,interaction_minus_local_null_AUC=deltas))
            for dimension,values in labels.items():
                strata[dimension]=[]
                for label in sorted(set(values)):
                    selected=use&np.array([v==label for v in values])
                    strata[dimension].append(dict(label=label,source_records=int(selected.sum()),predictors={key:context_auc(m['cells'][0][selected],classes[selected],m['status'][0][selected],field) for key,field in fields.items()}))
            index=m['cells'][0];rr,cc=np.divmod(index,w);groups=collections.defaultdict(list)
            for k,key in enumerate(zip(np.floor(rr*cell/50).astype(int),np.floor(cc*cell/50).astype(int))):
                if use[k] and m['status'][0][k]==0:groups[key].append(k)
            scores={key:[] for key in fields}
            for selected in groups.values():
                selected=np.asarray(selected,int)
                for key,field in fields.items():
                    a=context_auc(index[selected],classes[selected],m['status'][0][selected],field)['AUC']
                    if a is not None:scores[key].append(a)
            means={key:float(np.mean(v)) if v else None for key,v in scores.items()}
            differences={}
            for key in interaction_keys:
                mass,_,field=key.split('__');null=mass+'__'+('zero_travel_per_centre' if field=='per_centre' else 'local_demand')
                differences[key]=None if means[key] is None or means[null] is None else means[key]-means[null]
            blocks=dict(block_km=50,observed_blocks=len(groups),blocks_with_both_classes=len(scores['uniform']),
                equal_block_mean_AUC=means,interaction_minus_local_null_AUC=differences,independent_or_held_out=False)
        subsets[subset]=dict(central_support=support,results=rows,primary_strata=strata,spatial_blocks=blocks)
    assert replayed==378 and len(fields)==66
    result=dict(status='exposed_service_opportunity_control_diagnostic',adopt=False,plan_sha256=sha(PLAN),
        fields_manifest_sha256=sha(OUT/'fields.json'),fields_sha256=sha(OUT/'fields.npz'),
        prior_service_results_sha256=sha(prior_path),private_matches_sha256=sha(private),
        source_snapshot_sha256=sha(snapshot),producer_sha256=sha(Path(__file__)),
        frozen_context_module_sha256=sha(ROOT/'polity/observed_role_contrast.py'),subsets=subsets,predictors=list(fields),
        prior_service_diagnostics_exact=replayed,all_scenarios_retained=True,fitted_parameters=0,chosen_predictor=None,
        population_food_staff_control_changed=False,
        limits='Opportunity and local null controls explain conditional ranking; inverse mass is not an adopted role prediction. No source-completeness,datedAD200 roles,political authority or independent-transfer qualification.')
    write(OUT/'results.json',result)
    for subset,s in subsets.items():
        p=s['results'][0]['predictors'];local=s['spatial_blocks']['equal_block_mean_AUC']
        print(subset,flush=True)
        for mass in ['uniform','environment','history_L450']:
            keys=[mass+'__zero_travel_per_centre',mass+'__inverse_mass',mass+'__recorded_roads_B1__per_centre']
            print(mass,{key:(round(p[key]['AUC'],4),round(local[key],4)) for key in keys},flush=True)


if __name__=='__main__':main()
