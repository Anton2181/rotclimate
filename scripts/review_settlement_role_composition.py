"""Independently reconstruct source partitions and every emitted rank diagnostic."""
import collections
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import table,identifier,number,sha,write
from evaluate_settlement_role_composition import OUT,PLAN,PRIOR,PRIVATE


def main():
    result=json.loads((OUT/'results.json').read_text())
    for key,path in {'plan_sha256':PLAN,'parent_results_sha256':PRIOR/'results.json','parent_fields_manifest_sha256':PRIOR/'fields.json',
        'semantic_sources_sha256':PLAN.parent/'semantic_sources.json',
        'parent_fields_sha256':PRIOR/'fields.npz','private_matches_sha256':PRIVATE,
        'producer_sha256':ROOT/'scripts/evaluate_settlement_role_composition.py','partition_module_sha256':ROOT/'polity/role_composition.py',
        'scorer_sha256':ROOT/'polity/observed_role_contrast.py'}.items():
        assert result[key]==sha(path),key
    for path,digest in result['parent_artifacts_unchanged'].items():assert sha(ROOT/path)==digest
    source=ROOT/'data/cache/roman_rural_britain_2018';snapshot=ROOT/'output/roman_rural_preparation_20261110/source_snapshot.json'
    assert sha(snapshot)==result['source_snapshot_sha256']
    for item in json.loads(snapshot.read_text())['files']:assert sha(source/item['name'])==item['sha256']
    minor,_=table((source/'rrs_site_t_minor.csv').read_bytes(),['ID'],'STMID');tags=collections.defaultdict(set)
    for row in minor:tags[identifier(row['id'])].add(row['sitetypeminor'].strip().casefold())
    core,_=table((source/'rrs_core_data.csv').read_bytes(),['ID']);byid={identifier(r['id']):r for r in core}
    m=dict(np.load(PRIVATE));classes=m['classes'];groups=[];strict=[];records=[]
    for i in m['source_ids']:
        labels=tags[str(i)];selected=labels&{'village','vicus',"unwalled 'small town'"};strict.append('roadside settlement' not in labels);records.append(byid[str(i)])
        group='not_nucleated'
        if len(selected)>1:group='mixed_nonroadside_labels'
        elif selected:group={'village':'village_only','vicus':'vicus_only',"unwalled 'small town'":'small_town_only'}[next(iter(selected))]
        elif 'roadside settlement' in labels:group='roadside_only'
        groups.append(group)
    groups=np.array(groups);strict=np.array(strict)
    assert np.sum(classes==1)==result['parent_positive_records']==426
    assert np.sum(classes==0)==result['parent_negative_records']==2049
    assert np.all(groups[classes==0]=='not_nucleated') and np.all(groups[classes==1]!='not_nucleated')
    fields=dict(np.load(PRIOR/'fields.npz'));mask=fields.pop('core_mask');w=mask.shape[1]
    cell=float(np.load(ROOT/'output/settlement_locations_20261110/rome_inputs.npz')['cell_km'])
    def area(r):
        a=number(r['area'])
        return 'missing' if a is None or a<=0 else 'positive_lt0.1ha' if a<.1 else '0.1_to_lt1ha' if a<1 else 'ge1ha'
    strata={'region':np.array([r['region'] or 'unknown' for r in records]),
        'fieldwork':np.array([r['fieldworktype'] or 'unknown' for r in records]),'investigated_area':np.array([area(r) for r in records])}
    def direct(selected,k,field):
        units=[np.unique(m['cells'][k][selected&(classes==c)&(m['status'][k]==0)]) for c in [0,1]]
        if any(len(u)==0 for u in units):return None
        score=field.ravel();a,b=score[units[1],None],score[units[0]][None,:]
        return float(np.mean((a>b)+.5*(a==b)))
    def equal(a,b):
        assert (a is None and b is None) or (a is not None and b is not None and abs(a-b)<1e-13),(a,b)
    global_checks=strata_checks=block_checks=gated=0
    for name,s in result['cases'].items():
        cohort=np.ones(len(classes),bool) if s['cohort']=='full' else strict
        selected=cohort&((classes==0)|(groups==s['source_group']))
        assert int(np.sum(selected&(classes==1)))==s['source_positive_records']
        assert int(np.sum(selected&(classes==0)))==s['source_negative_records']
        assert len(s['coordinate_support'])==9
        for k,item in enumerate(s['coordinate_support']):
            for c in [0,1]:
                statuses=item['statuses_by_class'][str(c)]
                for code,label in enumerate(['included','out_of_window','nonland','disallowed']):
                    assert statuses[label]==int(np.sum(selected&(classes==c)&(m['status'][k]==code)))
                assert sum(statuses.values())==int(np.sum(selected&(classes==c)))
        units=[set(m['cells'][0][selected&(classes==c)&(m['status'][0]==0)].tolist()) for c in [0,1]]
        expected_gate=all(len(u)>=30 for u in units)
        assert expected_gate==s['central_support']['preparation_gate_passed']
        assert {str(c):len(units[c]) for c in [0,1]}==s['central_support']['represented_cell_class_units']
        assert len(units[0]&units[1])==s['central_support']['mixed_cells']
        if not expected_gate:
            assert not s['results'] and not s['spatial_blocks'] and not s['primary_strata'];continue
        gated+=1;assert len(s['results'])==9
        for k,row in enumerate(s['results']):
            assert set(row['predictors'])==set(fields)
            for key,score in row['predictors'].items():equal(direct(selected,k,fields[key]),score['AUC']);global_checks+=1
        for dimension,rows in s['primary_strata'].items():
            assert {r['label'] for r in rows}==set(strata[dimension])
            for row in rows:
                use=selected&(strata[dimension]==row['label']);assert int(use.sum())==row['source_records']
                for key,score in row['predictors'].items():equal(direct(use,0,fields[key]),score['AUC']);strata_checks+=1
        rr,cc=np.divmod(m['cells'][0],w);block_keys=list(zip((rr*cell//50).astype(int),(cc*cell//50).astype(int)))
        blocks=collections.defaultdict(list)
        for i,key in enumerate(block_keys):
            if selected[i] and m['status'][0][i]==0:blocks[key].append(i)
        assert len(blocks)==s['spatial_blocks']['observed_blocks']
        for key,field in fields.items():
            values=[]
            for indices in blocks.values():
                use=np.zeros(len(classes),bool);use[indices]=True;a=direct(use,0,field)
                if a is not None:values.append(a)
            assert len(values)==s['spatial_blocks']['blocks_with_both_classes']
            equal(float(np.mean(values)) if values else None,s['spatial_blocks']['equal_block_mean_AUC'][key]);block_checks+=1
    assert len(result['cases'])==10 and gated==result['gated_cases'] and global_checks==result['global_AUCs_computed']
    write(OUT/'review.json',dict(status='passed',source_result_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),
        source_partition_cases=10,gated_cases=gated,unscored_cases=10-gated,direct_global_AUC_checks=global_checks,
        direct_stratum_AUC_checks=strata_checks,direct_block_mean_checks=block_checks,parent_artifacts_unchanged=len(result['parent_artifacts_unchanged']),
        chosen_predictor=None,population_food_staff_control_changed=False))
    print('Reviewed',global_checks,'global,',strata_checks,'stratum and',block_checks,'block means;all10gates reconstructed.')


if __name__=='__main__':main()
