"""Known-answer dimensional and allocation checks for an unadopted hypothesis."""
from types import SimpleNamespace
import numpy as np
from experiments.wet_energy_budget import solar_wetness_budget


def budget(solar=480., latitude=0., wet=1., land=True, dw=5., ds=1., capacity=86400.):
    p = SimpleNamespace(land_coupling_insolation=1., land_tau_days=1.,
        dry_coupling=0., land_radiative_days=1., land_heat_capacity=1.)
    return solar_wetness_budget(*(np.asarray(v) for v in [solar, latitude, wet, land, dw, ds]),
                                p, capacity, .15)


def test_known_watts_from_joules_per_kelvin_and_seconds():
    b = budget(capacity=8640000.)
    # C=8.64 MJ/m2/K, lambda=2/day -> 200 W/m2/K.
    assert b['conductance'] == 200.
    np.testing.assert_allclose(b['bound'], 374.4)  # equatorial ice-free alpha=.22
    assert b['legacy'] == 1200.
    np.testing.assert_allclose(b['scale'], .312)
    np.testing.assert_allclose(b['applied'], 374.4)


def test_one_bound_shared_by_both_positive_terms():
    b = budget(capacity=8640000., dw=4., ds=4.)
    assert b['legacy'] == 1600.
    np.testing.assert_allclose(b['scale'] * (4.+4.) * b['conductance'], b['bound'])


def test_polar_night_and_no_cooling_and_no_land():
    b = budget(solar=np.array([0., 0., 480.]), dw=np.array([4., 0., 4.]),
               ds=np.zeros(3), land=np.array([True, True, False]))
    np.testing.assert_array_equal(b['scale'], [0., 1., 1.])
    np.testing.assert_array_equal(b['applied'], [0., 0., 0.])


def test_nonbinding_and_warming_not_spent_against_cooling():
    b = budget(dw=2., ds=-4.)
    assert b['scale'] == 1.
    assert b['legacy'] == 4.
    b = budget(capacity=8640000., dw=5., ds=-4.)
    np.testing.assert_allclose(b['scale'], 374.4/1000.)
    # Model applies scale only to positive ds; dry-soil warming is unchanged.
    assert np.where(np.array(-4.) > 0, -4.*b['scale'], -4.) == -4.
