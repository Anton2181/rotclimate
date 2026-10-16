"""Fast experiment-design checks; these never run a climate model."""
from dataclasses import asdict

from rotclimate.config import Params
from scripts.diagnose_numerics import case_params


def test_one_factor_cases_preserve_physical_world():
    base = Params(downsample=8, steps_per_year=25, picard_iters=2, north_bearing=-18.6)
    expected = {'baseline': set(), 'picard3': {'picard_iters'},
                'steps73': {'steps_per_year'}, 'grid4': {'downsample'},
                'render': {'downsample', 'steps_per_year', 'picard_iters'}}
    for name, p in case_params(base, list(expected), base.beyond_seed):
        changes = {k for k, v in asdict(p).items() if v != asdict(base)[k]}
        assert changes == expected[name]


def test_every_case_uses_requested_world():
    cases = case_params(Params(), ['baseline', 'picard6', 'picard12'], 101)
    assert all(p.beyond_seed == 101 for _, p in cases)
    assert [p.picard_iters for _, p in cases[1:]] == [6, 12]


def test_temperature_probes_only_change_iteration_cap_on_fine_grid():
    base = Params(downsample=8, steps_per_year=25, picard_iters=2, t_iters=12)
    cases = dict(case_params(base, ['grid4', 'grid4_t48', 'grid4_t96'], 1))
    for name, cap in [('grid4_t48', 48), ('grid4_t96', 96)]:
        expected = asdict(cases['grid4'])
        expected['t_iters'] = cap
        assert asdict(cases[name]) == expected


def test_fitted_pair_only_changes_resolution():
    cases = dict(case_params(Params(downsample=8), ['coarse_fitted', 'fine_fitted'], 1))
    expected = asdict(cases['coarse_fitted'])
    expected['downsample'] = 4
    assert asdict(cases['fine_fitted']) == expected
    assert cases['fine_fitted'].transport_scheme == 'exponential'


def test_tight_solver_pair_has_identical_physics_and_preserves_default():
    base = Params(downsample=8, t_iters=12)
    cases = dict(case_params(base, ['coarse_tight', 'fine_tight'], 1))
    expected = asdict(base)
    expected.update(t_iters=48, solver_rtol=1e-6)
    assert asdict(cases['coarse_tight']) == expected
    expected['downsample'] = 4
    assert asdict(cases['fine_tight']) == expected
    assert Params().solver_rtol == 1e-3


def test_final_verification_changes_only_cap_and_failure_policy():
    cases = dict(case_params(Params(), ['fine_tight', 'fine_verified'], 1))
    expected = asdict(cases['fine_tight'])
    expected.update(solver_max_iter=2000, solver_require_convergence=True)
    assert asdict(cases['fine_verified']) == expected
