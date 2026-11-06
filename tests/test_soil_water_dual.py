import numpy as np
import pytest

from harvest.soil_water import soil_water_year
from harvest.soil_water_dual import canopy_cover, dual_soil_water, kcb_curve

KW = dict(total_available=150.0, depletion_fraction=0.55, total_evaporable=23.0, readily_evaporable=9.0)


def test_ledger_closes_and_stays_in_bounds():
    rng = np.random.default_rng(1)
    n = 730
    rain = np.where(rng.random(n) < 0.3, rng.gamma(1.2, 6.0, n), 0.0)
    et0 = 1.5 + 2.5 * np.sin(np.linspace(0, 4 * np.pi, n)) ** 2
    kcb = kcb_curve(np.arange(n), 30, 300) + kcb_curve(np.arange(n), 395, 665)
    r = dual_soil_water(rain, et0, kcb, initial_depletion=40.0, **KW)
    assert abs(r.ledger_residual) < 1e-8
    stored0, stored1 = 150 - r.initial_depletion, 150 - r.final_depletion
    assert stored0 + rain.sum() - r.transpiration.sum() - r.evaporation.sum() - r.drainage.sum() == pytest.approx(stored1, abs=1e-8)
    assert r.root_depletion.min() >= 0 and r.root_depletion.max() <= 150 + 1e-9
    assert r.layer_depletion.min() >= 0 and r.layer_depletion.max() <= 23 + 1e-9
    assert np.all(r.transpiration <= r.potential_transpiration + 1e-12)


def test_bare_soil_dries_only_the_surface_layer():
    n = 120
    r = dual_soil_water(np.zeros(n), np.full(n, 5.0), np.zeros(n), initial_depletion=0.0,
                        initial_layer_depletion=0.0, **KW)
    assert r.transpiration.sum() == 0
    assert r.evaporation.sum() <= 23.0 + 1e-9          # below the layer, bare ground keeps its water
    assert r.final_depletion == pytest.approx(r.evaporation.sum())
    # stage 1 at the full rate until REW is gone, then falling
    assert r.evaporation[0] == pytest.approx(1.2 * 5.0)
    assert r.evaporation[-1] < 0.05


def test_no_double_spending_without_rain():
    n = 200
    r = dual_soil_water(np.zeros(n), np.full(n, 6.0), np.full(n, 1.1), initial_depletion=30.0,
                        initial_layer_depletion=0.0, **KW)
    assert r.transpiration.sum() + r.evaporation.sum() <= 150 - 30 + 1e-9
    assert r.final_depletion <= 150 + 1e-9
    assert r.drainage.sum() == 0


def test_reduces_to_single_store_when_evaporation_is_shut():
    rng = np.random.default_rng(3)
    n = 365
    rain = np.where(rng.random(n) < 0.25, rng.gamma(1.0, 8.0, n), 0.0)
    et0 = np.full(n, 3.0)
    kc = np.full(n, 1.0)
    single = soil_water_year(rain, et0, kc, total_available=150.0, depletion_fraction=0.55, initial_stored=110.0, record=True)
    dual = dual_soil_water(rain, et0, kc, cover=np.full(n, 0.9999), initial_depletion=40.0, **KW)
    assert dual.evaporation.sum() < 0.2
    assert dual.transpiration.sum() == pytest.approx(single.evapotranspiration.sum(), rel=2e-3)
    assert dual.drainage.sum() == pytest.approx(single.drainage.sum(), rel=2e-3, abs=0.2)


def test_rain_rewets_the_surface_and_restores_stage_one():
    n = 40
    rain = np.zeros(n); rain[20] = 15.0
    r = dual_soil_water(rain, np.full(n, 4.0), np.zeros(n), initial_depletion=0.0, initial_layer_depletion=0.0, **KW)
    assert r.evaporation[19] < r.evaporation[20]
    assert r.evaporation[20] == pytest.approx(1.2 * 4.0)


def test_cover_and_curve_shapes():
    k = kcb_curve(np.arange(400), 50, 350)
    assert k[0] == 0 and k[60] == pytest.approx(0.15) and k.max() == pytest.approx(1.10) and k[399] == 0
    assert canopy_cover(0.15) == 0 and 0.8 < canopy_cover(1.10) < 1
    with pytest.raises(ValueError):
        dual_soil_water(np.zeros(3), np.ones(3), np.zeros(3), initial_depletion=200.0, **KW)
