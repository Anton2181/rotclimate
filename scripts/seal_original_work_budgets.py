"""Seal inspected original work-budget figure after all-source numerical review."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import sha,read,write

OUT=ROOT/'output/urban_original_work_map_20261117'


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve qualified work diagnostic map'
    r=read(OUT/'results.json');review=read(OUT/'review.json')
    assert r['status']=='rendered_original_partial_work_budgets_pending_independent_value_review'
    assert review['status']=='passed_independent_all_source_plot_values_masks_and_clipping_checks'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_original_work_budgets.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert review['source_values_checked']==112756 and review['original_work_budgets_exact']
    assert r['plot_panels']==4 and r['original_cases']==2 and not r['raw_budgets_changed']
    for key in ['solver_calls','new_Earth_food_scenarios','new_staff_allocations']:assert r[key]==review[key]==0
    paths=[Path(__file__),ROOT/'scripts/review_original_work_budgets.py',ROOT/'reports/ORIGINAL_WORK_BUDGET_MAP_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/warehouse_handling_exposure.json']
    write(OUT/'qualification.json',dict(status='passed_original_partial_work_map_all_source_values_and_display_limits',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        original_cases=2,source_values_checked=112756,plot_panels=4,raw_budgets_changed=False,
        display_clipping_counts_preserved=True,undefined_workforce_not_free_labor=True,figure_visually_inspected=True,
        solver_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,actual_population_changed=False,
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/warehouse_handling_exposure.json'))
    print('Qualified original work-budget inspection map;112756source values exact,no source/default changes',flush=True)


if __name__=='__main__':main()
