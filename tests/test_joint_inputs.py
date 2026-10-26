from dataclasses import asdict
import numpy as np
import pytest

from rotclimate import earth, joint
from rotclimate.config import Params


def physics():
    return Params.from_json('calibration/local_accuracy_20261023/r39_params.json')


@pytest.mark.parametrize('changes', [
    dict(solar_flux=1.08), dict(greenhouse_wm2=7.4), dict(planet_radius=.8),
    dict(tilt=33.5, retrograde=True, year_days=400, winter_solstice_day=22),
    dict(lat_center=50, north_bearing=70, tier_tops=(200, 500, 1500, 5000), ebm_land='uniform'),
])
def test_invented_planet_never_changes_earth_inputs(changes):
    p = physics()
    baseline = joint.earth_profile(p)
    changed = joint.earth_profile(p.replace(**changes))
    assert asdict(changed) == asdict(baseline)
    world = joint.world_profile(p, Params().replace(**changes))
    for name, value in changes.items():
        assert getattr(world, name) == value


@pytest.mark.parametrize('region', ['california', 'chile'])
def test_explicit_earth_boundary_reproduces_adopted_profile_in_both_hemispheres(region):
    from types import SimpleNamespace
    case = SimpleNamespace(name=region)
    p = physics()
    old = earth.earth_params(p, case)
    new = earth.earth_params(joint.earth_profile(p), case)
    # Unused fantasy geometry is reset. Every shared law/numerical setting and
    # all active regional planet inputs must be identical to the adopted run.
    for name in joint.SHARED_FIELDS | joint.NUMERICAL_FIELDS | joint.EARTH_FORCING.keys() | {'lat_center'}:
        assert getattr(new, name) == getattr(old, name)


def test_world_keeps_shared_physics_and_strict_numerics_from_theta():
    p = physics()
    world = Params(orographic=900, solver_require_convergence=False, downsample=32)
    composed = joint.world_profile(p, world)
    for name in joint.SHARED_FIELDS | joint.NUMERICAL_FIELDS:
        assert getattr(composed, name) == getattr(p, name)
    description = joint.describe(p, world)
    assert description['ignored_world_profile_values']['orographic'] == 900
    assert description['ignored_world_profile_values']['solver_require_convergence'] is False


@pytest.mark.parametrize('block,changes', [
    ('physics', dict(solar_flux=1.1)), ('world', dict(orographic=3)),
    ('physics', dict(solver_rtol=.1)), ('world', dict(solver_require_convergence=False)),
    ('numerics', dict(planet_radius=.8)),
])
def test_wrong_optimizer_block_is_rejected(block, changes):
    with pytest.raises(ValueError, match='outside'):
        joint.update_block(physics(), block, changes)


@pytest.mark.parametrize('changes', [dict(t_require_convergence=False),
    dict(moisture_residual_tol=0), dict(solver_require_convergence=False),
    dict(sst_source='observed'), dict(cloud_radiation=1, cloud_reference='earth')])
def test_relaxed_or_observation_substituted_profiles_cannot_enter_a_joint_fit(changes):
    with pytest.raises(ValueError):
        joint.world_profile(physics().replace(**changes), Params())


def test_new_uncategorized_parameter_fails_closed(monkeypatch):
    monkeypatch.setattr(joint, 'SHARED_FIELDS', joint.SHARED_FIELDS - {'orographic'})
    with pytest.raises(ValueError, match='Classify'):
        joint.earth_profile(physics())


def test_real_solver_is_identical_when_only_world_forcing_changes():
    from test_earth import _toy_case
    from rotclimate.model import ClimateModel
    case = _toy_case()
    p = physics().replace(steps_per_year=13)
    reference = earth.earth_params(joint.earth_profile(p), case)
    changed = earth.earth_params(joint.earth_profile(p.replace(
        solar_flux=1.08, greenhouse_wm2=7.4, planet_radius=.8)), case)
    a = ClimateModel(reference, grid=case.grid).run()
    b = ClimateModel(changed, grid=case.grid).run()
    assert a.numerics['all_checks_passed'] and b.numerics['all_checks_passed']
    for field in ['T', 'Tsl', 'P', 'W', 'u', 'v', 'E']:
        np.testing.assert_array_equal(getattr(a, field), getattr(b, field))
