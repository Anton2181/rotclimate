"""Physical bounds, pressure-taper interpolation and native aggregation."""
import numpy as np
import pytest
from scripts.audit_boundary_rh import relative_humidity, derive, review_profiles
from scripts.earth_calendar import MONTH_DAYS


def test_surface_anchor_and_pressure_taper_are_bounded_without_a_humidity_fit():
    p = np.array([101325., 92500., 70000., 30000., 2026.5])
    full = relative_humidity(p)
    assert full[0] == pytest.approx(.77)
    assert full[-1] == pytest.approx(0.)
    assert (np.diff(full) < 0).all()
    np.testing.assert_allclose(relative_humidity(p, taper=0), .77)
    np.testing.assert_allclose(relative_humidity(p, taper=.5), .5 * (full + .77))


@pytest.mark.parametrize('pressure,taper', [(0., 1.), (np.nan, .5), (110000., 1.), (92500., -1.), (92500., 1.1)])
def test_invalid_pressure_or_taper_fails_closed(pressure, taper):
    with pytest.raises(ValueError):
        relative_humidity(pressure, taper=taper)


def test_interpolate_specific_humidity_and_water_not_the_integrated_ratio():
    saturation = np.full((12, 7, 1), .01)
    observed = saturation * .6
    outputs = [derive(saturation, observed, np.ones(1), MONTH_DAYS, a)[1] for a in [0., .5, 1.]]
    for key in ['specific_humidity_kg_kg', 'model_total_mm', 'model_lower_mm', 'model_upper_mm']:
        np.testing.assert_allclose(outputs[1][key], .5 * (outputs[0][key] + outputs[2][key]), rtol=1e-14)
    assert not np.allclose(outputs[1]['model_upper_lower_mean_q_ratio'],
                           .5 * (outputs[0]['model_upper_lower_mean_q_ratio'] + outputs[2]['model_upper_lower_mean_q_ratio']))


def test_native_ratio_is_averaged_after_forming_each_cell_ratio():
    saturation = np.empty((12, 7, 2))
    saturation[:, :, 0] = .01
    saturation[:, :, 1] = np.linspace(.02, .0005, 7)
    summary, raw = derive(saturation, saturation * .6, np.array([1., 2.]), MONTH_DAYS, .5)
    annual = summary['seasons']['annual']
    expected = np.average(raw['model_upper_lower_mean_q_ratio'][0], weights=[1., 2.])
    assert annual['model_upper_lower_mean_q_ratio'] == pytest.approx(expected)
    assert annual['model_upper_lower_mean_q_ratio'] != pytest.approx(annual['model_upper_mean_q'] / annual['model_lower_mean_q'])


def test_average_process_gain_can_advance_with_a_regional_tradeoff():
    regions = {}
    for i, value in enumerate([.4, 1.2, .5]):
        regions[str(i)] = {'profiles': {
            'uniform': dict(water_mae_mm=2., shape_mae=.1),
            'half_taper': dict(water_mae_mm=2 * value, shape_mae=.1 * value),
            'mw_taper': dict(water_mae_mm=4., shape_mae=.2)}}
    scores = review_profiles(regions)
    assert scores['uniform']['objective'] == 1.
    assert scores['half_taper']['worst_region'] > 1.
    assert scores['half_taper']['supports_separately_declared_coupled_pilot']
    assert not scores['mw_taper']['supports_separately_declared_coupled_pilot']
