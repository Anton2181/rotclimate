"""Analytical one-operation controls of the supplied-resource adapter."""
import argparse
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from harvest.plough_resources import plan_plough_package
from cereal_activity_packet import read, write, sha, table, verify_parent

OUT = ROOT / 'output/plough_completion_adapter_20261117'
PLAN = ROOT / 'calibration/roman_benchmark_20261117/plough_completion_adapter.json'
PARENT = ROOT / 'output/plough_resource_contract_20261117'


CONTROLS = [
    ('paired_binding', 10., [True], [[20., 6., 9.]]),
    ('human_binding', 10., [True], [[8., 8., 100.]]),
    ('operator_binding', 10., [True], [[100., 4., 100.]]),
    ('draft_binding', 10., [True], [[100., 100., 3.]]),
    ('zero_draft_supply', 10., [True], [[100., 100., 0.]]),
    ('disjoint_operator_and_team', 10., [True, True], [[20., 20., 0.], [20., 0., 30.]]),
    ('hours_outside_window', 10., [False, True], [[100., 100., 100.], [0., 0., 0.]]),
    ('fractional_package_ceiling', 1.5, [True], [[20., 6., 9.]]),
    ('wrapped_window', 10., [True, False, True], [[4., 2., 3.], [0., 0., 0.], [8., 4., 6.]]),
]


def main(out):
    assert not (out / 'results.json').exists()
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    verify_parent(); q = read(PARENT / 'qualification.json')
    for n, h in q['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in q['files_sha256'].items(): assert sha(PARENT / n) == h, n
    rates = np.array([4., 2., 3.]); rows = []; details = []
    for name, maximum, mask, capacity in CONTROLS:
        p = plan_plough_package(origin_id='manufactured-origin', maximum_package_hectares=maximum,
            human_hours_per_hectare=4., operator_hours_per_hectare=2., draft_team_hours_per_hectare=3.,
            allowed=mask, available_hours=capacity)
        bound = min(maximum, sum(min(c / r for c, r in zip(caps, rates)) for allowed, caps in zip(mask, capacity) if allowed))
        np.testing.assert_allclose(p.completed_hectares, bound, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(p.completed_hectares_by_period.sum(), bound, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(p.resource_hours_used, p.completed_hectares_by_period[:, None] * rates,
                                   rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(p.resource_hours_used + p.unused_resource_hours, capacity, rtol=1e-12, atol=1e-12)
        assert np.all(p.resource_hours_used <= np.asarray(capacity) + 1e-12)
        assert not p.completed_hectares_by_period[~np.asarray(mask)].any()
        assert p.scope == 'plough_package_only' and not p.complete_crop_activity
        rows.append(dict(case=name, maximum_package_ha=maximum, expected_completed_ha=bound,
                         actual_completed_ha=p.completed_hectares, total_human_hours=float(p.resource_hours_used[:, 0].sum()),
                         operator_subset_hours=float(p.resource_hours_used[:, 1].sum()),
                         draft_team_hours=float(p.resource_hours_used[:, 2].sum())))
        details.append(dict(case=name, rates_hours_per_ha=rates.tolist(), supplied_capacity=capacity, allowed=mask,
                            completed_ha_by_period=p.completed_hectares_by_period.tolist(),
                            used_hours=p.resource_hours_used.tolist(), raw_unused_hours=p.unused_resource_hours.tolist()))
    out.mkdir(parents=True, exist_ok=True)
    table(out / 'controls.csv', rows); write(out / 'controls.json', details)
    paths = [PLAN, PARENT / 'qualification.json', ROOT / 'harvest/plough_resources.py', ROOT / 'harvest/labour.py',
             ROOT / 'tests/test_plough_resources.py', ROOT / 'tests/test_farm_labour.py', Path(__file__)]
    write(out / 'results.json', dict(status='passed_nine_analytical_plough_package_controls_not_crop_feasibility',
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths},
        files_sha256={n: sha(out / n) for n in ['controls.csv', 'controls.json']},
        manufactured_scheduler_calls=9, atlas_model_calls=0, numerical_defaults_from_Roman_sources=0,
        operator_is_subset=True, raw_unused_residuals_preserved=True, complete_crop_activity=False,
        grain_or_population_output=False, new_fit=False, main_atlas_changed=False, adopt=False))
    print('Nine analytical controls pass; supplied total-human/operator/team accounting only')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
