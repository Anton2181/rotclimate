"""Independent source-fate and pressure-quadrature/velocity checks."""
from types import SimpleNamespace
import numpy as np
import pytest
from scripts import review_v10_water_sources as review, audit_v10_source_forcing as audit
from tests.test_v10_mass_projection import fixture


def test_source_fates_keep_storage_and_whole_domain_sinks_distinct():
    row = {'totals': {'import_mm': [0., 100., 0., 0.], 'evaporation_mm': [0., 0., 200., 10.],
        'rain_mm': [2., 10., 20., 1.], 'export_mm': [3., 89., 181., 9.]},
        'initial_store_mm': [5., 2., 4., 1.], 'end_store_mm': [0., 3., 3., 1.]}
    fates = review.source_fates(row)
    assert 'initial' not in fates
    assert fates['boundary']['precipitation_to_supply'] == .1
    assert fates['boundary']['export_to_supply'] == .89
    assert fates['boundary']['store_change_to_supply'] == .01
    assert fates['ocean_evaporation']['export_to_supply'] == .905
    assert fates['ocean_evaporation']['store_change_to_supply'] == -.005
    for value in fates.values():
        assert value['precipitation_to_supply']+value['export_to_supply']+value['store_change_to_supply'] == pytest.approx(1.)


def test_descriptive_spans_do_not_claim_confidence_intervals():
    assert review.span([1., 3., 5.]) == {'mean': 3., 'min': 1., 'max': 5.}
    with pytest.raises(ValueError, match='finite'):
        review.span([1., np.nan])


def test_pressure_integral_of_constant_specific_q_and_cell_varying_bounds():
    pressure = np.array([1000., 925., 850., 700., 600., 500., 400., 300.])
    values = np.full((2, 8, 3), .004)
    bottom = np.array([92500., 80000., 70000.]);top = np.array([30000., 50000., 60000.])
    result = audit.pressure_integral(values, pressure, bottom, top)
    expected = .004*(bottom-top)/audit.m.base.G
    np.testing.assert_allclose(result, np.broadcast_to(expected, (2, 3)), atol=1e-12)


def test_linear_q_in_pressure_is_integrated_exactly_across_cut_native_intervals():
    pressure = np.array([1000., 925., 850., 700., 600., 500., 400., 300.])
    gradient = 1e-7;offset = .001
    values = np.broadcast_to((pressure*100*gradient+offset)[None, :, None], (12, 8, 2))
    bottom,top = 60795.,30000.
    expected = (.5*gradient*(bottom**2-top**2)+offset*(bottom-top))/audit.m.base.G
    np.testing.assert_allclose(audit.pressure_integral(values, pressure, bottom, top), expected, atol=1e-12)
    midpoint = .5*(bottom+top)
    assert (gradient*midpoint+offset)*(bottom-top)/audit.m.base.G == pytest.approx(expected)


@pytest.mark.parametrize('bottom,top', [(100100., 30000.), (92500., 29900.), (60000., 70000.)])
def test_pressure_integral_refuses_unobserved_extrapolation_or_reversed_bounds(bottom, top):
    with pytest.raises(ValueError, match='extrapolate'):
        audit.pressure_integral(np.ones((12, 8, 2)), np.array([1000., 925., 850., 700., 600., 500., 400., 300.]), bottom, top)


def test_partial_model_layer_weights_conserve_exact_window_mass():
    interfaces = np.broadcast_to(np.array([101325., 91192.5, 75993.75, 60795., 0.])[:, None], (5, 2))
    weights = audit.clipped_layer_weights(interfaces)
    np.testing.assert_allclose(weights.sum(0), (92500-30000)/audit.m.base.G)
    assert weights[-1, 0] == pytest.approx((60795-30000)/audit.m.base.G)


def test_raw_and_projected_velocity_use_face_mass_on_uneven_terrain():
    case, profile, settings, geometry, air = fixture()
    projector = audit.CapturedProjection(case.domain, geometry)
    raw_x = projector.mx*3.;raw_y = projector.my*(-2.)
    flow = projector.project(raw_x, raw_y)
    (u,v), projected = audit.raw_projected_velocity(projector, flow)
    np.testing.assert_allclose(u, 3., atol=1e-14)
    np.testing.assert_allclose(v, 2., atol=1e-14)
    expected = audit.m.winds.mass_model.cell_velocity(flow, projector)
    for a,b in zip(projected, expected):
        np.testing.assert_array_equal(a,b)
