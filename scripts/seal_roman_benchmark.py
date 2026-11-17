"""Check every plotted value and seal the limited conditional-size benchmark."""
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_roman_benchmark import OUT,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed benchmark qualification'
    r=read(OUT/'results.json');review=read(OUT/'review.json');prep=read(OUT/'preparation.json');presentation=read(OUT/'presentation.json')
    assert review['status']=='passed_independent_baseline_hierarchy_draws_pairwise_scores_and_all_regions'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_roman_benchmark.py')
    assert presentation['results_sha256']==sha(OUT/'results.json') and presentation['review_sha256']==sha(OUT/'review.json')
    assert presentation['renderer_sha256']==sha(ROOT/'scripts/render_roman_benchmark.py')
    for n,digest in {**prep['sources_sha256'],**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/n)==digest,n
    for group in [r['files_sha256'],presentation['files_sha256']]:
        for n,digest in group.items():assert sha(OUT/n)==digest,n
    with np.load(OUT/'design.npz') as z:d=dict(z)
    with np.load(OUT/'ensemble.npz') as z:ensemble=dict(z)
    with np.load(OUT/'plot_values.npz') as z:values=dict(z)
    for a,b in [('source_area','area'),('lat','lat'),('lon','lon'),('AD200','year200'),('strict','strict'),('province','province')]:np.testing.assert_array_equal(values[a],d[b])
    for key,label in [('baseline_median','baseline'),('hierarchy_median','hierarchy')]:np.testing.assert_array_equal(values[key],np.exp(np.median(np.log(ensemble[label]),axis=0)))
    plot=read(OUT/'plot_data.json');assert len(plot['panels'])==6 and plot['same_ha_scale'] and plot['source_areas_phase_undated']
    for panel in plot['panels']:
        mask=d['year200'].copy()
        if panel['region']=='egypt':mask &= d['province']==prep['province_names'].index('Aegyptus')
        assert panel['source_rows']==np.flatnonzero(mask).tolist()
        assert panel['size_intercept']==4. and panel['size_per_ha']==.14
        limits=panel['extent'];outside=mask&((d['lon']<limits[0])|(d['lon']>limits[1])|(d['lat']<limits[2])|(d['lat']>limits[3]))
        assert not outside.any(),'All scored map points must be in the declared frame'
    for name in ['results.json',*r['files_sha256']]:assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name
    sources={**prep['sources_sha256'],**r['sources_sha256']}
    nextplan=ROOT/'calibration/roman_benchmark_20261117/dated_regional_evidence.json'
    for p in [Path(__file__),ROOT/'scripts/review_roman_benchmark.py',ROOT/'scripts/render_roman_benchmark.py',ROOT/'reports/ROMAN_BENCHMARK_20261117.md',nextplan]:sources[str(p.relative_to(ROOT))]=sha(p)
    files=['preparation.json','preparation_review.json','coverage.csv','readiness.json','design.npz','results.json','review.json','presentation.json',*r['files_sha256'],*presentation['files_sha256']]
    write(OUT/'qualification.json',dict(status='passed_conditional_Roman_size_baseline_benchmark_not_dated_demographic_validation',
        sources_sha256=sources,protected_sha256=r['protected_sha256'],files_sha256={n:sha(OUT/n) for n in sorted(set(files))},
        targets=prep['targets'],historical_publication_remappings=len(prep['historical_publication_remappings']),current_protected_identities=len(r['protected_sha256']),
        baseline_fits=4,hierarchy_refit=False,old_five_seed_control_exact=True,evaluation_draws_per_model=256,
        independent_draw_values_checked=review['draw_values_checked'],independent_aggregate_cells_checked=review['aggregate_cells_checked'],
        plot_values_checked=sum(v.size for v in values.values()),regional_map_panels=6,all_map_sites_in_frame=True,figures_visually_inspected=True,
        fresh_outputs_byte_exact=True,conditional_size_skill_positive=True,AD200_extent_phase_certifications=0,
        survey_coverage_qualified=False,population_forecast_qualified=False,location_forecast_qualified=False,
        independent_new_validation=False,food_work_climate_route_solver_calls=0,main_atlas_changed=False,adopt=False,
        next_plan=str(nextplan.relative_to(ROOT))))
    print('Sealed conditional size benchmark; dated demographics/location claims remain unqualified',flush=True)


if __name__=='__main__':main()
