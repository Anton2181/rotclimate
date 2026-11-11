"""Replay the declared count families on independently checked complete inputs."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from settlement_counts_earth import source_cells,aggregate,metrics,clean,BETAS
from polity.settlement_counts import count_exposure,fit_scale
from polity.population_coverage import require_population_coverage
from polity import earth as E

OUT=ROOT/'output/settlement_count_extension_20261111'
EXT=ROOT/'output/earth_population_extension_20261111'
PARENT=ROOT/'output/settlement_counts_20261111'
ORIGINAL=ROOT/'output/settlement_locations_20261110'


def run(out=OUT):
    review=json.loads((EXT/'review.json').read_text());correction=json.loads((EXT/'correction.json').read_text())
    assert review['status']=='passed' and review['correction_sha256']==sha(EXT/'correction.json')
    assert correction['new_han_input_created'] and correction['new_han_input_sha256']==sha(EXT/'han_corrected_inputs.npz')
    out.mkdir(parents=True,exist_ok=True);blocks={};meta={};saved={};matching={};sources={}
    with np.load(ORIGINAL/'positions.npz') as positions:
        for pool in ['han','rome']:
            path=EXT/'han_corrected_inputs.npz' if pool=='han' else ORIGINAL/'rome_inputs.npz'
            sources[str(path.relative_to(ROOT))]=sha(path)
            with np.load(path) as z:x=dict(z)
            records,matching[pool]=source_cells(pool,x)
            _,_,old_covered=E.earth_people(x['lat'],x['lon'])
            covered=x['population_covered'] if pool=='han' else old_covered
            require_population_coverage(covered,x['land']&x['allowed'])
            for domain in ['full_corrected','old_supported_corrected']:
                for nominal in [100,300]:
                    mode='full_frozen' if domain=='full_corrected' else 'covered_only'
                    b,m=aggregate(x,positions[pool+'__baseline'],nominal,records,old_covered,mode)
                    key=f'{domain}_{pool}_{nominal}km';blocks[key]=b;meta[key]=m
                    for name,value in b.items():saved[key+'__'+name]=value
    rows=[];predictions={}
    for domain in ['full_corrected','old_supported_corrected']:
      for nominal in [100,300]:
       for target in ['record_count','distinct_cell_count']:
        for beta in BETAS:
         for scope in ['role_specific','shared_scale_control']:
          for pool in ['han','rome']:
            key=f'{domain}_{pool}_{nominal}km';b=blocks[key];exposure=count_exposure(b['area'],b['population'],beta)
            predicted=np.zeros(len(exposure));folds={};scales={}
            for fold in range(4):
                train=[];counts=[]
                for other in ([pool] if scope=='role_specific' else ['han','rome']):
                    o=blocks[f'{domain}_{other}_{nominal}km'];mask=o['fold']!=fold
                    train.append(count_exposure(o['area'],o['population'],beta)[mask]);counts.append(o[target][mask])
                scale=fit_scale(np.concatenate(train),np.concatenate(counts));scales[str(fold)]=scale
                held=b['fold']==fold;predicted[held]=exposure[held]*(scale if scale is not None else 0)
                folds[str(fold)]=dict(metrics(b[target][held],predicted[held],b['area'][held]),
                    training_scale_identified=scale is not None,training_count=int(np.concatenate(counts).sum()),training_exposure=float(np.concatenate(train).sum()))
            model=f'{scope}_beta{beta:g}';predictions[key+'__'+target+'__'+model]=predicted
            row=dict(domain=domain,pool=pool,nominal_km=nominal,target=target,model=model,beta=beta,scale_scope=scope,
                training_scales=scales,folds=folds,total=metrics(b[target],predicted,b['area']))
            rows.append(row)
            if nominal==100 and target=='record_count':print(domain,pool,model,row['total']['deviance_per_source_record'],flush=True)
    ranking={}
    for domain in ['full_corrected','old_supported_corrected']:
        values=[]
        for beta in BETAS:
            subset=[r for r in rows if r['domain']==domain and r['nominal_km']==100 and r['target']=='record_count' and r['model']==f'role_specific_beta{beta:g}']
            values.append(dict(beta=beta,equal_pool_deviance_per_source_record=float(np.mean([r['total']['deviance_per_source_record'] for r in subset])),
                pools={r['pool']:r['total']['deviance_per_source_record'] for r in subset}))
        ranking[domain]=sorted(values,key=lambda r:r['equal_pool_deviance_per_source_record'])
    parent=json.loads((PARENT/'results.json').read_text());same_domain=[]
    for old in parent['rows']:
        if old['domain']!='covered_only' or old['model']=='archived_production_descriptive':continue
        new=next(r for r in rows if r['domain']=='old_supported_corrected' and all(r[k]==old[k] for k in ['pool','nominal_km','target','model']))
        same_domain.append(dict(pool=new['pool'],nominal_km=new['nominal_km'],target=new['target'],model=new['model'],
            original_deviance_per_record=old['total']['deviance_per_source_record'],corrected_deviance_per_record=new['total']['deviance_per_source_record']))
    np.savez_compressed(out/'blocks.npz',**saved);np.savez_compressed(out/'predictions.npz',**predictions)
    result=dict(status='complete_population_input_count_development_not_production_qualification',adopt=False,
        original_count_plan_sha256=sha(ROOT/'calibration/settlement_counts_20261111/plan.json'),
        extension_plan_sha256=sha(ROOT/'calibration/earth_population_extension_20261111/plan.json'),
        correction_plan_sha256=sha(ROOT/'calibration/earth_population_extension_20261111/nodata_correction.json'),
        correction_sha256=sha(EXT/'correction.json'),correction_review_sha256=sha(EXT/'review.json'),
        parent_count_results_sha256=sha(PARENT/'results.json'),producer_sha256=sha(Path(__file__)),
        frozen_count_producer_sha256=sha(ROOT/'scripts/settlement_counts_earth.py'),count_module_sha256=sha(ROOT/'polity/settlement_counts.py'),
        sources=sources,source_matching=matching,blocks=meta,rows=rows,ranking=ranking,same_domain_comparisons=same_domain,
        blocks_sha256=sha(out/'blocks.npz'),predictions_sha256=sha(out/'predictions.npz'),
        all_required_population_inputs_covered=True,history_or_point_placement_qualified=False,resident_size_model_calibrated=False,
        population_food_staff_control_atlas_changed=False,chosen_for_production=None,
        limits='Exposed development on source-record counts,not complete village/urban census. New source domain and coastal NoData correction;no freephysics or population-scale fit. Separate same-domain comparisons from full-coverage support. Coretravel remains to rebuild;no history-point qualification or fantasy ledger adoption.')
    write(out/'results.json',clean(result));print('Full-input ranking',clean(ranking['full_corrected']),flush=True)


if __name__=='__main__':run()
