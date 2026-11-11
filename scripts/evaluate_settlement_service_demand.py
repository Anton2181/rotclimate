"""Score every declared service scenario on full and strict non-roadside contexts."""
import collections
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import table,identifier,number,sha,write
from polity.observed_role_contrast import context_auc,cell_class_summary
from build_settlement_service_demand import PLAN,OUT,INPUT


def main():
    manifest=json.loads((OUT/'fields.json').read_text());prior_path=ROOT/'output/settlement_role_contrast_20261111/results.json'
    prior=json.loads(prior_path.read_text());prep_path=ROOT/'output/settlement_role_contrast_20261111/preparation.json'
    prep=json.loads(prep_path.read_text());private=ROOT/'data/cache/settlement_role_contrast_20261111/matched.npz'
    checks={'plan_sha256':PLAN,'input_sha256':INPUT,'fields_sha256':OUT/'fields.npz','prior_context_results_sha256':prior_path}
    for key,path in checks.items():
        if manifest[key]!=sha(path):raise ValueError('Changed service field evidence: '+key)
    for path,digest in manifest['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed service source')
    if sha(prep_path)!=prior['preparation_sha256'] or sha(private)!=prior['private_matches_sha256']:
        raise ValueError('Changed original context preparation or private matches')
    source=ROOT/'data/cache/roman_rural_britain_2018';snapshot=ROOT/'output/roman_rural_preparation_20261110/source_snapshot.json'
    if sha(snapshot)!=prep['original_source_snapshot_sha256']:raise ValueError('Changed source identities')
    for item in json.loads(snapshot.read_text())['files']:
        if sha(source/item['name'])!=item['sha256']:raise ValueError('Changed source observations')
    matches=dict(np.load(private));all_fields=dict(np.load(OUT/'fields.npz'))
    core=all_fields.pop('core_mask');fields=all_fields;classes=matches['classes']
    if not np.all(core.ravel()[matches['cells']][matches['status']==0]):raise ValueError('Core crop excludes previously included matches')
    labels=collections.defaultdict(set);roles,_=table((source/'rrs_site_t_minor.csv').read_bytes(),['ID'],'STMID')
    for row in roles:labels[identifier(row['id'])].add(row['sitetypeminor'].strip().casefold())
    keep={'full':np.ones(len(classes),bool),'strict_nonroadside':np.array(['roadside settlement' not in labels[str(key)] for key in matches['source_ids']])}
    core_rows,_=table((source/'rrs_core_data.csv').read_bytes(),['ID']);byid={identifier(row['id']):row for row in core_rows}
    records=[byid[str(key)] for key in matches['source_ids']]
    def area(row):
        v=number(row['area'])
        return 'missing' if v is None or v<=0 else 'positive_lt0.1ha' if v<.1 else '0.1_to_lt1ha' if v<1 else 'ge1ha'
    stratum_labels={'region':[r['region'] or 'unknown' for r in records],
                    'fieldwork':[r['fieldworktype'] or 'unknown' for r in records],
                    'investigated_area':[area(r) for r in records]}
    shape=core.shape;w=shape[1];cell=float(np.load(INPUT)['cell_km']);subsets={}
    controls=0
    for subset,use in keep.items():
        support=cell_class_summary(matches['cells'][0][use],classes[use],matches['status'][0][use])
        rows=[];strata={};blocks={}
        if support['preparation_gate_passed']:
            for k,name in enumerate(matches['scenario_names']):
                predictors={key:context_auc(matches['cells'][k][use],classes[use],matches['status'][k][use],field) for key,field in fields.items()}
                if subset=='full':
                    for key,expected in prior['results'][k]['predictors'].items():
                        if predictors[key]!=expected:raise ValueError('Prior reference diagnostic changed')
                        controls+=1
                rows.append(dict(coordinate_scenario=str(name),predictors=predictors))
            for dimension,values in stratum_labels.items():
                strata[dimension]=[]
                for label in sorted(set(values)):
                    selected=use&np.array([v==label for v in values])
                    strata[dimension].append(dict(label=label,source_records=int(selected.sum()),predictors={
                        key:context_auc(matches['cells'][0][selected],classes[selected],matches['status'][0][selected],field) for key,field in fields.items()}))
            index=matches['cells'][0];r,c=np.divmod(index,w);groups=collections.defaultdict(list)
            for k,key in enumerate(zip(np.floor(r*cell/50).astype(int),np.floor(c*cell/50).astype(int))):
                if use[k] and matches['status'][0][k]==0:groups[key].append(k)
            local={key:[] for key in fields};both=0
            for selected in groups.values():
                selected=np.asarray(selected,int);both+=len(set(classes[selected].tolist()))==2
                for key,field in fields.items():
                    auc=context_auc(index[selected],classes[selected],matches['status'][0][selected],field)['AUC']
                    if auc is not None:local[key].append(auc)
            blocks=dict(block_km=50,observed_blocks=len(groups),blocks_with_both_classes=both,
                equal_block_mean_AUC={key:float(np.mean(v)) if v else None for key,v in local.items()},independent_or_held_out=False)
        subsets[subset]=dict(source_class_records={str(k):int(np.sum(use&(classes==k))) for k in [0,1]},
            central_support=support,results=rows,primary_strata=strata,spatial_blocks=blocks)
    if controls!=27:raise ValueError('Incomplete prior reference replay')
    result=dict(status='exposed_service_demand_context_diagnostic',adopt=False,plan_sha256=sha(PLAN),
        fields_manifest_sha256=sha(OUT/'fields.json'),fields_sha256=sha(OUT/'fields.npz'),
        prior_context_results_sha256=sha(prior_path),private_matches_sha256=sha(private),
        source_snapshot_sha256=sha(snapshot),producer_sha256=sha(Path(__file__)),
        frozen_context_module_sha256=sha(ROOT/'polity/observed_role_contrast.py'),subsets=subsets,
        prior_reference_controls_exact=controls,predictors=list(fields),all_scenarios_retained=True,
        fitted_parameters=0,chosen_predictor=None,physical_population_food_staff_control_changed=False,
        limits='Finite potential requests, not completed services/people. Fractional candidate opportunities are not staffed settlements. Conditional source labels can be successive; no census, datedAD200 role, authority, independent transfer or production qualification.')
    write(OUT/'results.json',result)
    for name,subset in subsets.items():
        print(name,'support',subset['central_support'],'source',subset['source_class_records'],flush=True)
        if subset['results']:
            print('Central AUC',{key:round(row['AUC'],4) for key,row in subset['results'][0]['predictors'].items()},flush=True)


if __name__=='__main__':main()
