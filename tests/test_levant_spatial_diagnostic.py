import math

import numpy as np
import pytest

pytest.importorskip('pyproj',reason='Install requirements-roman-benchmark.txt for regional GIS diagnostics')
pytest.importorskip('shapely',reason='Install requirements-roman-benchmark.txt for regional GIS diagnostics')

from scripts.levant_spatial_diagnostic import score


def test_constant_field_is_uniform_opportunity_even_with_unequal_areas():
    result,p=score(np.array([1.,3.]),np.array([1,2]),np.array([5.,5.]))
    np.testing.assert_array_equal(p,[.25,.75])
    assert abs(result['mean_log_gain'])<1e-15
    assert result['presence_background_auc']==.5


def test_exact_two_cell_likelihood_penalizes_unhelpful_concentration():
    result,p=score(np.array([1.,1.]),np.array([1,1]),np.array([1.,3.]))
    np.testing.assert_array_equal(p,[.25,.75])
    assert math.isclose(result['mean_log_gain'],.5*math.log(.75),abs_tol=1e-15)
    assert result['presence_background_auc']==.5


def test_zero_intensity_at_a_recorded_site_is_not_smoothed_away():
    result,p=score(np.array([1.,1.]),np.array([1,0]),np.array([0.,1.]))
    assert result['normalization_valid']
    assert result['mean_log_gain']==result['log_likelihood']=='-inf'
    assert result['zero_weight_occupied_cells']==1 and p[0]==0


def test_all_zero_model_refuses_normalization_without_uniform_fallback():
    result,p=score(np.array([1.,2.]),np.array([2,1]),np.array([0.,0.]))
    assert not result['normalization_valid']
    assert result['mean_log_gain']=='-inf'
    np.testing.assert_array_equal(p,[0.,0.])
