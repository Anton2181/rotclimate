import json

import numpy as np

from rotclimate.config import Params
from rotclimate.geography import TARGET_CLASSES
from rotclimate.koppen import CODES
from scripts.mediterranean_pilot import candidates, saved_metrics, convergence_summary, previous_comparisons, dry_patch_changes


def test_probes_change_only_planned_settings_and_preserve_the_run_configuration():
    from dataclasses import asdict
    base = Params.from_json('calibration/round20_retrograde_selected.json')
    for name, p in candidates(base).items():
        changed = {k for k, v in asdict(p).items() if v != asdict(base)[k]}
        expected = {'seasonal_belts': {'hadley_shift'}, 'storm_mixing': {'eddy_rate'},
                    'combined': {'hadley_shift', 'eddy_rate'},
                    'focused_storms': {'storm_width', 'eddy_rate'}}
        assert changed == expected[name]
        assert p.beyond_seed == base.beyond_seed
        assert p.solver_require_convergence


def test_dry_area_includes_steppe_but_desert_is_reported_separately(tmp_path):
    path = tmp_path / 'fields.npz'
    fields = dict(target=np.full(4, 4), valid=np.ones(4, bool),
                  koppen=np.array([CODES.index(c) for c in ['Csa', 'BSh', 'BWh', 'Cfa']]),
                  index_MAP=np.array([700., 450., 200., 1200.]),
                  index_Pth=np.full(4, 50.), index_Pwin=np.full(4, 300.),
                  params_json=np.array(json.dumps({'retrograde': True})))
    fields.update({f'membership_{key}': np.ones(4) for _, key, _, _ in TARGET_CLASSES})
    np.savez(path, **fields)
    row = saved_metrics(path)
    med = row['mediterranean']
    assert med['dry_share'] == 0.5
    assert med['desert_share'] == 0.25
    assert med['cs_share'] == 0.25
    assert med['dry_cells_median_fixed_threshold_gap_mm'] == 175


def test_linear_convergence_alone_cannot_validate_a_physical_comparison():
    detail = dict(solver={'unconverged_solves': 0}, temperature_convergence={
        'unconverged_steps': 20, 'final_update_max_c': [0.04, 15.]})
    assert not convergence_summary(detail)['usable_for_comparison']
    detail['temperature_convergence'].update(unconverged_steps=0, final_update_max_c=[0.04])
    assert convergence_summary(detail)['usable_for_comparison']
    detail['solver']['unconverged_solves'] = 1
    assert not convergence_summary(detail)['usable_for_comparison']
    detail['solver']['unconverged_solves'] = 0
    detail['moisture_convergence'] = {'enabled': True, 'unconverged_steps': 1}
    assert not convergence_summary(detail)['usable_for_comparison']


def test_incremental_comparison_keeps_results_but_rejects_other_worlds(tmp_path):
    from dataclasses import asdict
    base = Params(t_relaxation=0.25, t_iters=192)
    options = candidates(base)
    path = tmp_path / 'comparison.json'
    rows = {'baseline': {'params': asdict(base)},
            'storm_mixing': {'params': asdict(options['storm_mixing']), 'accuracy': 0.51},
            'seasonal_belts': {'params': asdict(options['seasonal_belts'].replace(beyond_seed=99))}}
    path.write_text(json.dumps(rows))
    assert list(previous_comparisons(path, base, options)) == ['storm_mixing']
    assert not previous_comparisons(path, base.replace(beyond_seed=99), options)


def test_equal_total_dry_area_cannot_hide_a_moving_patch(tmp_path):
    common = dict(target=np.full(3, 4), valid=np.ones(3, bool),
                  index_Pwin=np.full(3, 300.), index_Psum=np.full(3, 150.), index_MAP=np.full(3, 450.))
    b, c = tmp_path / 'before.npz', tmp_path / 'after.npz'
    np.savez(b, **common, koppen=[CODES.index(code) for code in ['BSh', 'BSh', 'Csa']])
    common['index_Pwin'] += 20
    common['index_MAP'] += 20
    np.savez(c, **common, koppen=[CODES.index(code) for code in ['Csa', 'BSh', 'BSh']])
    changes = dry_patch_changes(b, c)
    assert changes['original_dry_cells'] == 2
    assert changes['cured_cells'] == changes['persistent_cells'] == changes['new_dry_cells'] == 1
    assert changes['original_dry_patch_rain_change_median_mm']['winter'] == 20
