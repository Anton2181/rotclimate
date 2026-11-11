"""Check complete-input count replay without reusing its fitting code."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from review_settlement_counts import direct_metrics,equal
from polity import earth as E

OUT=ROOT/'output/settlement_count_extension_20261111';EXT=ROOT/'output/earth_population_extension_20261111'
PARENT=ROOT/'output/settlement_counts_20261111';ORIGINAL=ROOT/'output/settlement_locations_20261110'


def main():
    r=json.loads((OUT/'results.json').read_text());parent=json.loads((PARENT/'results.json').read_text())
    for key,path in {'original_count_plan_sha256':ROOT/'calibration/settlement_counts_20261111/plan.json',
        'extension_plan_sha256':ROOT/'calibration/earth_population_extension_20261111/plan.json',
        'correction_plan_sha256':ROOT/'calibration/earth_population_extension_20261111/nodata_correction.json',
        'correction_sha256':EXT/'correction.json','correction_review_sha256':EXT/'review.json','parent_count_results_sha256':PARENT/'results.json',
        'producer_sha256':ROOT/'scripts/count_population_extension.py','frozen_count_producer_sha256':ROOT/'scripts/settlement_counts_earth.py',
        'count_module_sha256':ROOT/'polity/settlement_counts.py','blocks_sha256':OUT/'blocks.npz','predictions_sha256':OUT/'predictions.npz'}.items():assert r[key]==sha(path)
    for path,digest in r['sources'].items():assert sha(ROOT/path)==digest
    assert r['source_matching']==parent['source_matching']
    with np.load(PARENT/'blocks.npz') as z:old_blocks=dict(z)
    with np.load(OUT/'blocks.npz') as z:blocks=dict(z)
    with np.load(OUT/'predictions.npz') as z:predictions=dict(z)
    rebuilt={};block_checks=0
    for pool in ['han','rome']:
        path=EXT/'han_corrected_inputs.npz' if pool=='han' else ORIGINAL/'rome_inputs.npz'
        with np.load(path) as z:x=dict(z)
        _,_,old_covered=E.earth_people(x['lat'],x['lon']);land=x['allowed']&x['land'];h,w=land.shape;cell=float(x['cell_km'])
        assert (x['population_covered'][land].all() if pool=='han' else old_covered[land].all())
        for domain,old_domain in [('full_corrected','full_frozen'),('old_supported_corrected','covered_only')]:
          for nominal in [100,300]:
            key=f'{domain}_{pool}_{nominal}km';oldkey=f'{old_domain}_{pool}_{nominal}km'
            b={k.removeprefix(key+'__'):v for k,v in blocks.items() if k.startswith(key+'__')}
            for field in b:
                if field!='population':np.testing.assert_array_equal(b[field],old_blocks[oldkey+'__'+field])
            step=round(nominal/cell);nbx=(w+step-1)//step;population=[]
            valid=land if domain=='full_corrected' else land&old_covered
            for bid in b['block_id']:
                yy,xx=divmod(int(bid),nbx);ys=slice(yy*step,min(h,(yy+1)*step));xs=slice(xx*step,min(w,(xx+1)*step))
                population.append(float(x['density'][ys,xs][valid[ys,xs]].sum()*cell**2));block_checks+=1
            np.testing.assert_allclose(b['population'],population,rtol=1e-12,atol=1e-5);rebuilt[key]=b
    assert len(r['rows'])==160;checks=fold_cases=0
    for row in r['rows']:
        key=f'{row["domain"]}_{row["pool"]}_{row["nominal_km"]}km';b=rebuilt[key];y=b[row['target']];p=np.zeros(len(y))
        for fold in range(4):
            pools=[row['pool']] if row['scale_scope']=='role_specific' else ['han','rome']
            observations=exposure=0.
            for pool in pools:
                o=rebuilt[f'{row["domain"]}_{pool}_{row["nominal_km"]}km'];train=o['fold']!=fold
                observations+=o[row['target']][train].sum()
                exposure+=(o['area'][train]*(o['population'][train]/o['area'][train])**row['beta']).sum()
            scale=observations/exposure if exposure else (0. if observations==0 else None)
            equal(row['training_scales'][str(fold)],scale)
            held=b['fold']==fold;p[held]=(scale or 0)*b['area'][held]*(b['population'][held]/b['area'][held])**row['beta']
            f=row['folds'][str(fold)];equal(f['training_count'],observations);equal(f['training_exposure'],exposure)
            assert f['training_scale_identified']==(scale is not None)
            for field,value in direct_metrics(y[held],p[held],b['area'][held]).items():equal(f[field],value);checks+=1
            fold_cases+=1
        for field,value in direct_metrics(y,p,b['area']).items():equal(row['total'][field],value);checks+=1
        label=key+'__'+row['target']+'__'+row['model'];np.testing.assert_allclose(p,predictions[label],rtol=1e-10,atol=1e-10)
    for comparison in r['same_domain_comparisons']:
        a=next(q for q in parent['rows'] if q['domain']=='covered_only' and all(q[k]==comparison[k] for k in ['pool','nominal_km','target','model']))
        b=next(q for q in r['rows'] if q['domain']=='old_supported_corrected' and all(q[k]==comparison[k] for k in ['pool','nominal_km','target','model']))
        equal(comparison['original_deviance_per_record'],a['total']['deviance_per_source_record'])
        equal(comparison['corrected_deviance_per_record'],b['total']['deviance_per_source_record'])
    for domain,ranking in r['ranking'].items():
        for item in ranking:
            rows=[q for q in r['rows'] if q['domain']==domain and q['nominal_km']==100 and q['target']=='record_count' and q['model']==f'role_specific_beta{item["beta"]:g}']
            for row in rows:equal(item['pools'][row['pool']],row['total']['deviance_per_source_record'])
            equal(item['equal_pool_deviance_per_source_record'],float(np.mean([row['total']['deviance_per_source_record'] for row in rows])))
    assert not r['adopt'] and not r['population_food_staff_control_atlas_changed'] and r['chosen_for_production'] is None
    assert not r['history_or_point_placement_qualified'] and not r['resident_size_model_calibrated']
    full=[row for row in r['rows'] if row['domain']=='full_corrected']
    assert all(row['total']['positive_observation_zero_prediction_blocks']==0 for row in full)
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),
        population_blocks_checked=block_checks,fold_cases=fold_cases,scalar_metric_checks=checks,all160_rows_checked=True,
        all_nonpopulation_block_fields_unchanged=True,source_multiplicity_unchanged=True,all_full_region_source_count_predictions_positive=True,
        original_supported_domain_comparisons_checked=len(r['same_domain_comparisons']),no_production_adoption=True))
    print('Complete-input count review passed:',block_checks,'blocks',fold_cases,'fold cases',checks,'scalar metrics.')


if __name__=='__main__':main()
