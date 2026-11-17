"""Seal source/area/work controls and figure correspondence, without adoption."""
import csv
import hashlib
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import OUT, activity, load_packet, read, write, sha, verify_parent


def main():
    assert not (OUT / 'qualification.json').exists()
    verify_parent()
    r = read(OUT / 'results.json'); review = read(OUT / 'review.json'); p = read(OUT / 'presentation.json')
    assert review['status'] == 'passed_all_origin_scalar_retention_area_work_food_and_identity_checks'
    assert review['results_sha256'] == p['results_sha256'] == sha(OUT / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_cereal_activity_packet.py')
    assert p['review_sha256'] == sha(OUT / 'review.json')
    assert p['renderer_sha256'] == sha(ROOT / 'scripts/render_cereal_activity_packet.py')
    for n, h in r['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in {**r['files_sha256'], **p['files_sha256']}.items(): assert sha(OUT / n) == h, n
    for n in ['results.json', *r['files_sha256']]:
        assert (OUT / n).read_bytes() == (OUT / 'fresh' / n).read_bytes(), n
    assert p['native_grid_shape'] == [463, 1000] and p['shared_retained_fraction_scale'] == [0., 1.]
    assert {(v['climate'], v['density']) for v in p['plotted_cases']} == {
        (c, d) for c in ['raw', 'corrected'] for d in ['central', 'low']}
    plotted_origins = 0
    for v in p['plotted_cases']:
        a = activity(load_packet(OUT, v['climate']), 'candidate', v['climate'], v['density'], 600.)
        assert v['category_counts'] == [int((a['limitation_code'] == i).sum()) for i in range(6)]
        assert v['retained_cropped_ha'] == float(np.nansum(a['retained_area_ha']))
        assert v['retained_fraction_sha256'] == hashlib.sha256(a['retained_fraction'].tobytes()).hexdigest()
        assert v['limitation_codes_sha256'] == hashlib.sha256(a['limitation_code'].tobytes()).hexdigest()
        assert v['origins'] == len(a['origin']) == 241889
        plotted_origins += len(a['origin'])
    with (OUT / 'support.csv').open() as f:
        for v in csv.DictReader(f): assert int(v['wheat_origins']) == 0
    next_plan = 'calibration/roman_benchmark_20261117/cereal_operation_demands.json'
    extra = ['scripts/review_cereal_activity_packet.py', 'scripts/render_cereal_activity_packet.py',
        'scripts/seal_cereal_activity_packet.py', 'reports/CEREAL_ACTIVITY_PACKET_20261117.md', next_plan]
    sources = dict(r['sources_sha256']); sources.update({n: sha(ROOT / n) for n in extra})
    files = ['results.json', 'review.json', 'presentation.json', *r['files_sha256'], *p['files_sha256']]
    write(OUT / 'qualification.json', dict(status='passed_fixed_cereal_origin_area_work_packet_not_seasonal_qualification',
        sources_sha256=sources, files_sha256={n: sha(OUT / n) for n in sorted(set(files))},
        physical_cases=16, supply_scenarios=32, origin_case_rows_reviewed=review['origin_case_rows'],
        materialized_values_reviewed=review['materialized_values_checked'],
        exact_original_scalar_controls=416, literal_existing_field_support_replays=16,
        crop_choice_mismatches=0, potential_reconstruction_byte_exact=True, source_ids_match_climates=True,
        plotted_origin_rows_per_figure=plotted_origins, figures_visually_inspected=True,
        fresh_scientific_exports_byte_exact=True, all_productive_origins_select_barley=True,
        complete_household_draft_processing_budget=False, seasonal_work_qualified=False,
        crop_mix_historically_qualified=False, new_scenarios=0, climate_crop_route_placement_calls=0,
        new_fit=False, main_atlas_changed=False, adopt=False, next_plan=next_plan))
    print('Sealed controlled per-origin cereal packet; seasonal/resource/crop-mix limits explicit')


if __name__ == '__main__': main()
