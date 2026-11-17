"""Check every displayed source value against fixed archived crop-work budgets."""
import csv
import math
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import sha,read,write

OUT=ROOT/'output/urban_original_work_map_20261117'
WORK=ROOT/'output/urban_component_work_20261116/hours600/cases'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116/wind_1981/prepared'


def main():
    assert not (OUT/'review.json').exists(),'Preserve independent plot-value review'
    r=read(OUT/'results.json');assert r['status']=='rendered_original_partial_work_budgets_pending_independent_value_review'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    with np.load(OUT/'local_plot_values.npz') as z:values=dict(z)
    source=values['source_indices'];assert len(source)==len(set(source.tolist()))==56378
    summary=read(OUT/'summary.json');assert len(summary)==2
    csv_rows=list(csv.DictReader((OUT/'summary.csv').open()));assert len(csv_rows)==2
    previous={s['reading']:s for s in read(ROOT/'output/urban_warehouse_work_20261117/budgets.json')}
    reviews=[]
    for row in summary:
        reading=row['reading'];n=0;negative=percentclip=below=above=zeros=undefined=0
        with np.load(WORK/f'{reading}.npz') as z:workers=z['B_workers'];annual=z['B_annual_available'];used=z['B_annual_used']
        with np.load(ANNUAL/f'low_{reading}.npz') as z:area=float(z['cell_km'])**2
        np.testing.assert_array_equal(values[f'{reading}_annual_available'],annual)
        np.testing.assert_array_equal(values[f'{reading}_annual_used'],used)
        np.testing.assert_array_equal(values[f'{reading}_raw_unused'],annual-used)
        np.testing.assert_array_equal(values[f'{reading}_defined'],workers>0)
        for i,(worker,capacity,spent) in enumerate(zip(workers,annual,used)):
            capacity,spent=float(capacity),float(spent);unused=capacity-spent
            assert unused>=-1e-8*max(1,capacity)
            actual_util=float(values[f'{reading}_plot_utilization'][i]);actual_unspent=float(values[f'{reading}_plot_unused_hours_per_km2'][i])
            assert actual_unspent==max(0,unused)/area
            negative+=int(unused<0)
            if worker>0:
                percent=100*spent/capacity;assert actual_util==min(100,max(0,percent))
                percentclip+=int(percent<0 or percent>100)
                zeros+=int(actual_unspent==0);below+=int(0<actual_unspent<.01);above+=int(actual_unspent>10000)
            else:assert math.isnan(actual_util);undefined+=1
            n+=1
        for key,value in [('display_negative_unused_clips',negative),('display_percent_clips',percentclip),
            ('positive_allowance_below_log_floor',below),('positive_allowance_above_log_ceiling',above),
            ('zero_display_allowance_cells',zeros),('undefined_utilization_cells',undefined)]:assert row[key]==value,key
        expected=previous[reading]
        assert math.isclose(row['raw_unspent_fraction'],expected['unused_fraction_of_listed_allowance'],rel_tol=0,abs_tol=1e-15)
        assert row['sources_at_annual_limit']==expected['sources_at_annual_limit']
        assert row['raw_unspent_listed_hours']==expected['unused_listed_allowance_hours']
        assert row['cell_area_km2']==area==81 and n==56378
        reviews.append(dict(reading=reading,source_values_checked=n,raw_arrays_exact=True,display_formulas_exact=True,
            raw_unspent_fraction=row['raw_unspent_fraction'],clipping_counts_independently_checked=True))
    assert r['plot_panels']==4 and r['percent_scale']==[0,100] and r['positive_log_hours_km2_scale']==[.01,10000]
    assert r['zero_allowance_separate'] and r['undefined_workforce_not_zero_utilization'] and not r['raw_budgets_changed']
    write(OUT/'review.json',dict(status='passed_independent_all_source_plot_values_masks_and_clipping_checks',
        reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),cases=reviews,source_values_checked=112756,
        original_work_budgets_exact=True,source_cohort_changed=False,new_crop_or_calendar_coefficients=False,
        solver_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,actual_population_changed=False,
        new_fit=False,new_validation_claim=False,adopt=False))
    print('Independent work-map review passed:112756source values/masks/clipping;original budgets exact',flush=True)


if __name__=='__main__':main()
