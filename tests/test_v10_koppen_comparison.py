"""Calendar, units, masking and surface-temperature policy for diagnostic maps."""
import numpy as np
import pytest
from scripts import plot_v10_koppen as maps
from rotclimate.koppen import CODES


def climate():
    temperature = np.array([8, 9, 11, 13, 16, 20, 23, 23, 20, 16, 11, 8.])[:, None, None]
    rain = np.array([100, 100, 100, 50, 20, 5, 1, 2, 10, 60, 100, 100.])[:, None, None]
    return temperature, rain, np.ones((1, 1), bool)


def test_monthly_mm_and_real_earth_seasons_produce_expected_mediterranean_code():
    t, p, mask = climate()
    assert CODES[maps.classify_months(t, p, mask).item()] == 'Csa'
    p[:] = 80.;p[9] = 1.  # October is winter, unlike the fantasy default.
    assert CODES[maps.classify_months(t, p, mask).item()] == 'Cwa'
    assert np.flatnonzero(maps.SUMMER).tolist() == [3, 4, 5, 6, 7, 8]


def test_invalid_outside_mask_is_excluded_from_classes_and_agreement():
    t, p, _ = climate()
    t = np.tile(t, (1, 2, 2));p = np.tile(p, (1, 2, 2))
    mask = np.array([[True, False], [False, True]])
    t[:, ~mask] = np.nan;p[:, ~mask] = np.nan
    target = maps.classify_months(t, p, mask)
    simulated = maps.classify_months(t, np.broadcast_to(np.where(mask[None], 0., np.nan), t.shape), mask)
    assert (target[~mask] == -1).all()
    result = maps.comparison(target, simulated, mask)
    assert result['scored_cells'] == 2
    assert result['exact_class_agreement'] == 0.
    assert result['desert_share'] == result['target_mediterranean_to_arid'] == 1.
    assert result['class_counts'] == {'BWk': 2}
    p[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match='Invalid scored'):
        maps.classify_months(t, p, mask)


def test_surface_proxy_adds_departure_not_absolute_free_air_temperature():
    surface = np.full((12, 2, 2), 15.)
    target = np.full((12, 4, 2, 2), -10.)
    model = target.copy();model[:, 0] += 2.
    proxy = maps.surface_proxy(surface, (None, None, model, target))
    np.testing.assert_allclose(proxy, 17.)


def test_identical_climates_match_exactly_and_keep_confusion_counts():
    t, p, mask = climate()
    target = maps.classify_months(t, p, mask)
    result = maps.comparison(target, target, mask)
    assert result['exact_class_agreement'] == result['main_group_agreement'] == 1.
    assert result['target_mediterranean_retained'] == 1.
    assert result['confusion_cells'] == {'Csa': {'Csa': 1}}


def test_default_does_not_write_figures_or_change_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(maps, 'collect', lambda *args: ({'sources': {}, 'regions': {}}, {}, {}))
    monkeypatch.setattr(maps, 'draw', lambda *a, **k: pytest.fail('Unexpected figure write'))
    out = tmp_path/'not_created'
    assert maps.main(['--out', str(out)]) == 0
    assert not out.exists()
