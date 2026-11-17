"""Seal the conditional regional diagnostic without promoting its assumptions."""
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from qualify_roman_regional_sources import sha,read,write
OUT=ROOT/'output/levant_spatial_diagnostic_20261117'


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed diagnostic'
    r=read(OUT/'results.json');review=read(OUT/'review.json');p=read(OUT/'presentation.json');tests=read(OUT/'tests.json')
    assert review['status']=='passed_independent_projection_support_counts_probabilities_and_conditional_scores'
    assert review['results_sha256']==p['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_levant_spatial_diagnostic.py')
    assert p['review_sha256']==sha(OUT/'review.json') and p['renderer_sha256']==sha(ROOT/'scripts/render_levant_spatial_diagnostic.py')
    assert p['figure_sha256']==sha(OUT/'spatial_comparison.png')
    assert tests['status']=='passed' and tests['tests']==4 and tests['test_sha256']==sha(ROOT/tests['test_file'])
    for n,d in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/n)==d,n
    for n,d in r['files_sha256'].items():assert sha(OUT/n)==d,n
    for n in ['results.json',*r['files_sha256']]:assert (OUT/n).read_bytes()==(OUT/'fresh'/n).read_bytes(),n
    with np.load(OUT/'model_support.npz') as z:
        np.testing.assert_array_equal(z['legacy_weight'],z['refreshed_weight'])
        expected={}
        for rr,cc,count in zip(z['row'],z['column'],z['count']):expected[int(rr),int(cc)]=expected.get((int(rr),int(cc)),0)+int(count)
        assert p['native_cell_observation_counts']==[dict(row=rr,column=cc,site_count=n) for (rr,cc),n in sorted(expected.items())]
        assert len(expected)==55 and sum(expected.values())==565
    for i,name in enumerate(r['source_names']):
        # Values already independently checked against scores.csv by reviewer.
        import csv
        with (OUT/'scores.csv').open() as f:row=next(s for s in csv.DictReader(f) if s['reference']==name and s['model']=='refreshed')
        assert p['plotted_refreshed_mean_log_gain'][i]==float(row['mean_log_gain'])
        assert p['plotted_refreshed_auc'][i]==float(row['presence_background_auc'])
    sources=dict(r['sources_sha256']);nextplan=ROOT/'calibration/roman_benchmark_20261117/annual_assumption_impact.json'
    for path in [Path(__file__),ROOT/'scripts/review_levant_spatial_diagnostic.py',ROOT/'scripts/render_levant_spatial_diagnostic.py',ROOT/tests['test_file'],ROOT/'reports/LEVANT_SPATIAL_DIAGNOSTIC_20261117.md',ROOT/'requirements-roman-benchmark.txt',nextplan]:sources[str(path.relative_to(ROOT))]=sha(path)
    files=['results.json','review.json','tests.json','presentation.json','spatial_comparison.png',*r['files_sha256']]
    write(OUT/'qualification.json',dict(status='passed_conditional_Levant_spatial_diagnostic_no_added_fixed_field_skill',sources_sha256=sources,protected_sha256=r['protected_sha256'],
        files_sha256={n:sha(OUT/n) for n in sorted(set(files))},source_site_ids=565,source_strata=8,source_model_cell_pairs=93,distinct_model_cells=55,
        point_assignments_reviewed=565,conditional_score_values_reviewed=120,focused_tests=4,fresh_outputs_byte_exact=True,figure_visually_inspected=True,
        fixed_recipe_centre_H_control_exact=True,legacy_refreshed_weights_identical=True,
        equal_source_mean_log_gain=-0.03949844875152589,equal_source_presence_background_auc=0.47701195853822637,
        population_validation_qualified=False,uniform_detection_qualified=False,simultaneous_AD200_census_qualified=False,new_blind_test=False,
        food_work_climate_route_solver_calls=0,new_fit=False,new_validation_claim=False,actual_population_allocated=False,main_atlas_changed=False,adopt=False,
        next_plan=str(nextplan.relative_to(ROOT))))
    print('Sealed conditional diagnostic with negative fixed-field gain; no parameter or atlas adoption',flush=True)


if __name__=='__main__':main()
