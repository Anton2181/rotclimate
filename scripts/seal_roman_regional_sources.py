"""Seal the reviewed period/source contract, preserving its interpretation limits."""
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from qualify_roman_regional_sources import OUT,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed source qualification'
    r=read(OUT/'results.json');review=read(OUT/'review.json');presentation=read(OUT/'presentation.json');cohort=read(OUT/'cohort.json')
    assert review['status']=='passed_independent_period_identity_scalar_polygon_and_format_review'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_roman_regional_sources.py')
    assert presentation['results_sha256']==sha(OUT/'results.json') and presentation['review_sha256']==sha(OUT/'review.json')
    assert presentation['renderer_sha256']==sha(ROOT/'scripts/render_roman_regional_sources.py')
    assert presentation['figure_sha256']==sha(OUT/'source_support.png')
    assert presentation['retained_source_fids']==cohort['selected_fids']
    with np.load(OUT/'observations.npz') as z:
        assert presentation['source_count_bars']==[int((z['source_code']==i).sum()) for i in range(8)]
    for n,d in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/n)==d,n
    for n,d in r['files_sha256'].items():assert sha(OUT/n)==d,n
    for n,d in r['local_source_sha256'].items():assert sha(OUT/'source'/n)==d,n
    for n in ['results.json',*r['files_sha256']]:assert (OUT/n).read_bytes()==(OUT/'fresh'/n).read_bytes(),n
    sources=dict(r['sources_sha256']);nextplan=ROOT/'calibration/roman_benchmark_20261117/levant_spatial_diagnostic.json'
    for p in [Path(__file__),ROOT/'scripts/review_roman_regional_sources.py',ROOT/'scripts/render_roman_regional_sources.py',ROOT/'reports/ROMAN_REGIONAL_SOURCES_20261117.md',nextplan]:sources[str(p.relative_to(ROOT))]=sha(p)
    files=['results.json','review.json','presentation.json','source_support.png',*r['files_sha256']]
    write(OUT/'qualification.json',dict(status='passed_conditional_Levant_period_presence_inputs_not_census_or_uniform_detection',sources_sha256=sources,
        protected_sha256=r['protected_sha256'],local_source_sha256=r['local_source_sha256'],files_sha256={n:sha(OUT/n) for n in sorted(set(files))},
        source_commit=r['source_commit'],candidates=3,phase_rows_checked=14273,source_site_ids=5557,selected_unique_site_ids=565,
        named_survey_envelopes=8,polygon_rows_checked=69,own_source_membership_checks=571,retained_observation_values_checked=3955,
        published_phase='70–324AD',simultaneous_AD200_occupancy_qualified=False,phase_specific_area_qualified=False,
        walked_footprint_qualified=False,uniform_detection_qualified=False,absolute_population_or_count_qualified=False,
        fresh_outputs_byte_exact=True,figure_visually_inspected=True,model_predictions_or_scores_performed=False,
        new_fit=False,new_validation_claim=False,main_atlas_changed=False,adopt=False,next_plan=str(nextplan.relative_to(ROOT))))
    print('Qualified565 period-defined habitation records in eight own-source envelopes; census/detection claims remain unqualified',flush=True)


if __name__=='__main__':main()
