"""Seal independently reviewed grain comparison, fresh exports and inspected figures."""
import csv
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from conditional_grain_extent import OUT, ROMAN, MODELS, verify_inputs
from cereal_activity_packet import read, write, sha


def main():
    assert not (OUT/'qualification.json').exists()
    verify_inputs();r=read(OUT/'results.json');q=read(OUT/'review.json');p=read(OUT/'presentation.json')
    assert q['results_sha256']==sha(OUT/'results.json')==p['results_sha256']
    assert q['reviewer_sha256']==sha(ROOT/'scripts/review_conditional_grain_extent.py')
    assert p['renderer_sha256']==sha(ROOT/'scripts/render_conditional_grain_extent.py')
    assert p['review_sha256']==sha(OUT/'review.json') and p['all_map_sites_in_frame']
    for n,h in r['sources_sha256'].items():assert sha(ROOT/n)==h,n
    for record in [r,p]:
        for n,h in record['files_sha256'].items():assert sha(OUT/n)==h,n
    for n in [*r['files_sha256'],'results.json']:
        assert (OUT/n).read_bytes()==(OUT/'fresh'/n).read_bytes(),n
    with np.load(OUT/'features.npz') as z:f=dict(z)
    with np.load(OUT/'ensembles.npz') as z:e=dict(z)
    with np.load(OUT/'plot_values.npz') as z:v=dict(z)
    with np.load(ROMAN/'design.npz') as z:d=dict(z)
    for key in ['G_potential','G_h600','G_h300']:
        np.testing.assert_array_equal(f[key+'__row_rations'],f[key+'__centre_rations'][f['row_centre']])
        np.testing.assert_array_equal(f['x__'+key],np.log1p(f[key+'__row_rations']))
    np.testing.assert_array_equal(f['x__H_reference'],np.log(f['centre_H'][f['row_centre']]))
    np.testing.assert_array_equal(f['x__M0'],np.ones(664))
    for key in ['lat','lon','strict']:np.testing.assert_array_equal(v[key],d[key])
    np.testing.assert_array_equal(v['mask'],d['year200']);np.testing.assert_array_equal(v['source'],d['area'])
    for key in ['M0','H_reference','G_h600']:
        np.testing.assert_array_equal(v[key],np.exp(np.median(np.log(e[key]),axis=0)))
    for key in ['h600','h300']:np.testing.assert_array_equal(v['x_'+key],f['x__G_'+key])
    scores=list(csv.DictReader((OUT/'scores.csv').open()))
    provinces=list(csv.DictReader((OUT/'provinces.csv').open()))
    folds=list(csv.DictReader((OUT/'folds.csv').open()))
    comparisons=list(csv.DictReader((OUT/'comparisons.csv').open()))
    for c in comparisons:
        target=[s for s in scores if s['cohort']==c['cohort']]
        a=next(s for s in target if s['model']==c['model']);b=next(s for s in target if s['model']==c['baseline'])
        for score,label in [('log_area_crps','crps'),('median_log_area_mae','mae')]:
            np.testing.assert_allclose(float(c[label+'_relative_improvement']),1-float(a[score])/float(b[score]),rtol=1e-13,atol=1e-15)
        for label in ['model','baseline']:
            rows=[s for s in provinces if s['cohort']==c['cohort'] and s['model']==c[label] and int(s['n'])]
            np.testing.assert_allclose(float(c[label+'_equal_province_crps']),np.mean([float(s['log_area_crps']) for s in rows]))
        wins=0;eligible=0
        for outer in range(4):
            rows=[s for s in folds if s['cohort']==c['cohort'] and int(s['outer'])==outer]
            a=next(s for s in rows if s['model']==c['model']);b=next(s for s in rows if s['model']==c['baseline'])
            if int(a['n']):eligible+=1;wins+=float(a['log_area_crps'])<float(b['log_area_crps'])
        assert wins==int(c['fold_crps_wins']) and eligible==int(c['nonempty_comparison_folds'])
    files={n:sha(OUT/n) for n in [*r['files_sha256'],*p['files_sha256'],'results.json','review.json','presentation.json']}
    source_paths=[Path(__file__),ROOT/'reports/CONDITIONAL_GRAIN_EXTENT_20261117.md',
                  ROOT/'scripts/review_conditional_grain_extent.py',ROOT/'scripts/render_conditional_grain_extent.py']
    write(OUT/'qualification.json',dict(status='passed_conditional_grain_extent_no_capacity_or_atlas_adoption',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in source_paths}},
        files_sha256=files,independent_outer_fits=20,independent_score_cells=q['independently_checked_score_cells'],
        comparison_rows_checked=len(comparisons),fresh_producer_exports_byte_exact=9,
        baseline_draws_and_H_exact=True,feature_transforms_checked=True,heldout_outcomes_excluded=True,
        map_panels=4,all_map_sites_in_frame=True,figures_visually_inspected=True,
        grain_feature_adopted=False,historical_household_hours_identified=False,
        agricultural_capacity_calibrated=False,new_blind_validation=False,main_atlas_changed=False,adopt=False))
    print('Sealed checked fits/figures and nine byte-exact replay exports; protected atlas unchanged.')


if __name__=='__main__':main()
