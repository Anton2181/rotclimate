"""Seal the read-only saved-inventory audit and its next declared control."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_urban_storage_throughput import OUT,PARENT,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed qualification'
    r=read(OUT/'results.json');v=read(OUT/'review.json')
    assert v['status']=='passed_independent_saved_throughput_and_all_local_loss_channels'
    assert v['results_sha256']==sha(OUT/'results.json')
    assert v['reviewer_sha256']==sha(ROOT/'scripts/review_urban_storage_throughput.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert r['food_kernel_calls']==v['food_kernel_calls']==r['new_food_scenarios']==v['new_food_scenarios']==0
    assert v['source_rows']==451024 and v['city_losses']==19 and v['city_month_rows']==228
    assert v['maximum_stock_trace_tolerance_fraction']<=1 and v['maximum_bound_tolerance_fraction']<=1
    for reading,losses in [('central',11),('low',8)]:
        c=v['local_channels'][reading];assert c['losing_cities']==losses
        assert c['annual_direct_decreases']==c['protection_flips']==0
    parent=read(PARENT/'qualification.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():assert sha(prefix/name)==digest,name
    paths=[ROOT/'scripts/audit_urban_storage_throughput.py',ROOT/'scripts/review_urban_storage_throughput.py',Path(__file__),
        ROOT/'reports/URBAN_STORAGE_THROUGHPUT_20261117.md',ROOT/'calibration/urban_diagnosis_20261117/fixed_dispatch_loss_control.json']
    q=dict(status='passed_read_only_storage_throughput_and_all19_local_loss_channels',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        source_rows=451024,city_loss_rows=19,city_loss_month_rows=228,food_kernel_calls=0,new_food_scenarios=0,
        maximum_stock_trace_tolerance_fraction=v['maximum_stock_trace_tolerance_fraction'],
        maximum_bound_tolerance_fraction=v['maximum_bound_tolerance_fraction'],
        maximum_city_delta_ledger_residual_person_years=v['maximum_city_delta_ledger_residual_person_years'],
        historical_storage_calibrated=False,new_fit=False,new_validation_claim=False,actual_population_changed=False,adopt=False,
        main_atlas_changed=False,next_plan='calibration/urban_diagnosis_20261117/fixed_dispatch_loss_control.json')
    write(OUT/'qualification.json',q);print(q['status'],flush=True)


if __name__=='__main__':main()
