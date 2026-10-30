import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from rotclimate.correction import (FEATURES, TemperatureCorrection, TreeEnsemble, feature_stack,
                                   season_phase, static_features)

ADOPTED = Path('calibration/earth_correction_20261030')


def toy_grid(cell_km=28.0, ny=40, nx=50):
    yy, xx = np.mgrid[0:ny, 0:nx]
    land = xx > nx // 3
    elev = np.where(land, 30.0 * (xx - nx // 3) + 200.0 * np.sin(yy / 4.0) ** 2, 0.0)
    return SimpleNamespace(land=land, elev=elev, lat=35.0 + 0.25 * (ny / 2 - yy), cell_km=cell_km)


def toy_climate(grid):
    m = np.arange(12)[:, None, None]
    T = 15.0 - 0.3 * (grid.lat - 35.0) + 10.0 * np.cos(2 * np.pi * (m - 6.5) / 12) * np.where(grid.land, 1.0, 0.5)
    P = 40.0 + 30.0 * np.cos(2 * np.pi * m / 12) + 0.02 * grid.elev
    return T, np.broadcast_to(P, T.shape).copy()


def toy_ensemble(seed, n_trees=6):
    rng = np.random.default_rng(seed)
    parts, offsets, start = [], [0], 0
    for _ in range(n_trees):                       # depth-2 trees: root, two splits, four leaves
        f = rng.integers(0, len(FEATURES), 3)
        thr = rng.normal(0, 1, 3) * np.array([1.0, 1.0, 1.0])
        left = np.array([1, 3, 5, -1, -1, -1, -1]) + start
        right = np.array([2, 4, 6, -1, -1, -1, -1]) + start
        leaf = np.array([0, 0, 0, 1, 1, 1, 1], bool)
        value = np.r_[0, 0, 0, rng.normal(0, .5, 4)]
        parts.append((np.r_[f, 0, 0, 0, 0], np.r_[thr, 0, 0, 0, 0], left, right, leaf, value))
        start += 7
        offsets.append(start)
    cat = [np.concatenate([p[i] for p in parts]) for i in range(6)]
    return TreeEnsemble(0.1, np.array(offsets), cat[0].astype(np.int32), cat[1], cat[2], cat[3], cat[4], cat[5])


def test_numpy_trees_match_scikit_learn():
    sklearn = pytest.importorskip('sklearn.ensemble')
    rng = np.random.default_rng(3)
    X = rng.normal(size=(3000, len(FEATURES)))
    y = np.sin(X[:, 0]) + X[:, 5] * (X[:, 7] > 0) + 0.1 * rng.normal(size=3000)
    model = sklearn.HistGradientBoostingRegressor(max_iter=40, early_stopping=False, random_state=0).fit(X, y)
    test = rng.normal(size=(500, len(FEATURES))) * 1.5
    assert np.allclose(TreeEnsemble.from_sklearn(model).predict(test), model.predict(test), atol=1e-10)


def test_shape_component_has_zero_annual_mean_and_rain_and_sea_stay_raw(tmp_path):
    grid = toy_grid()
    T, P = toy_climate(grid)
    corr = TemperatureCorrection(toy_ensemble(1), toy_ensemble(2), dict(shape_weight=0.8, level_weight=0.3))
    static = static_features(grid)
    mask = grid.land
    shape, level = corr.components({k: v[mask] for k, v in static.items()}, T[:, mask], P[:, mask], season_phase())
    assert np.allclose(shape.mean(0), 0.0, atol=1e-12)
    Tc = corr.apply(T, P, grid)
    assert np.array_equal(Tc[:, ~grid.land], T[:, ~grid.land])
    assert np.allclose(Tc[:, mask] - T[:, mask], 0.8 * shape + 0.3 * level[None])
    path = tmp_path / 'c.npz'
    corr.save(path)
    again = TemperatureCorrection.load(path)
    assert np.array_equal(again.apply(T, P, grid), Tc)


def test_static_fields_are_defined_in_km_not_cells():
    coarse, fine = toy_grid(56.0, 20, 25), toy_grid(28.0, 40, 50)
    a, b = static_features(coarse), static_features(fine)
    # the same physical point (cell centres coincide every other fine cell)
    assert a['coast_km'][10, 20] == pytest.approx(b['coast_km'][20, 41], abs=40.0)
    assert np.isfinite(np.stack(list(a.values()))).all()
    assert (a['lat'] >= 0).all()


def test_season_is_measured_from_the_winter_solstice():
    earth = season_phase(365.0, 354.5)
    shifted = season_phase(365.0, 354.5 + 365.0 / 12.0)
    # a solstice one month later: each month sits where the previous one did
    assert np.allclose(np.angle(np.exp(1j * (shifted - np.roll(earth, 1)))), 0.0)
    grid = toy_grid()
    T, P = toy_climate(grid)
    X = feature_stack({k: v[grid.land] for k, v in static_features(grid).items()}, T[:, grid.land], P[:, grid.land], earth)
    assert X.shape == (grid.land.sum(), 12, len(FEATURES)) and np.isfinite(X).all()


@pytest.mark.skipif(not (ADOPTED / 'correction.npz').exists(), reason='adopted correction not present')
def test_adopted_correction_records_its_physics_and_evidence():
    corr = TemperatureCorrection.load(ADOPTED / 'correction.npz')
    meta = corr.meta
    params = Path(meta['physics_params'])
    assert hashlib.sha256(params.read_bytes()).hexdigest() == meta['physics_params_sha256']
    assert (meta['shape_weight'], meta['level_weight']) == (0.8, 0.3)
    evaluation = json.loads((ADOPTED / 'evaluation.json').read_text())
    assert evaluation['selected']['eligible'] and evaluation['selected']['monthly_mae_C'] < evaluation['groups']['raw']['monthly_mae_C']['all']
    protocol = json.loads((ADOPTED / 'protocol.json').read_text())
    for name, digest in protocol['files'].items():
        assert hashlib.sha256((ADOPTED / name).read_bytes()).hexdigest() == digest
    assert sorted(meta['trained_on']) == sorted(sum(meta['clusters'].values(), []))
