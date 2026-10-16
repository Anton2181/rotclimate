from dataclasses import asdict

import numpy as np
import pytest

from rotclimate.config import Params
from rotclimate.model import ClimateModel, eddy_exchange_rate
from scripts.diagnose_moisture import case_options


def test_zero_contrast_preserves_existing_exchange_including_background_floor():
    storm = np.array([0., .2, 1.])
    np.testing.assert_array_equal(eddy_exchange_rate(.998, storm, .8), .998*(.15+storm)/86400.)
    assert Params.from_json('calibration/round20_retrograde_mediterranean.json').eddy_seasonality == 0.


def test_seasonal_exchange_has_the_intended_winter_summer_direction():
    storm = np.array([0., .2, 1.])
    base = eddy_exchange_rate(1., storm, 0.)
    np.testing.assert_allclose(eddy_exchange_rate(1.,storm,-1.,.4), 1.4*base)
    np.testing.assert_allclose(eddy_exchange_rate(1.,storm,1.,.4), .6*base)
    np.testing.assert_allclose(eddy_exchange_rate(1.,storm,0.,.4), base)
    # Storm/background scaling remains positive even near the allowed limit.
    assert (eddy_exchange_rate(1.,storm,1.,.999)>0).all()


def test_seasonal_test_changes_only_one_physical_parameter_on_verified_numerics():
    options = case_options(True)
    current, seasonal = options['current'], options['seasonal']
    changed={k for k,v in asdict(seasonal).items() if v!=asdict(current)[k]}
    assert changed=={'eddy_seasonality'}
    assert seasonal.moisture_require_convergence and seasonal.solver_require_convergence
    assert seasonal.eddy_rate==current.eddy_rate and seasonal.storm_width==current.storm_width


def test_poleward_probe_changes_only_belt_position_from_the_seasonal_fit():
    options=case_options(True)
    seasonal, poleward=options['seasonal'],options['poleward']
    changed={k for k,v in asdict(poleward).items() if v!=asdict(seasonal)[k]}
    assert changed=={'hadley_edge'}
    assert poleward.hadley_edge-seasonal.hadley_edge==4.
    assert poleward.moisture_require_convergence


def test_stronger_contrast_probe_preserves_the_best_fit_geometry_and_solver():
    options=case_options(True)
    seasonal,strong=options['seasonal'],options['strong_seasonal']
    changed={k for k,v in asdict(strong).items() if v!=asdict(seasonal)[k]}
    assert changed=={'eddy_seasonality'}
    assert strong.eddy_seasonality==.7 and strong.moisture_require_convergence


def test_interaction_probe_combines_exact_previously_tested_controls():
    options=case_options(True)
    focused,combined=options['focused'],options['focused_seasonal']
    changed={k for k,v in asdict(combined).items() if v!=asdict(focused)[k]}
    assert changed=={'eddy_seasonality'}
    assert combined.eddy_seasonality==options['strong_seasonal'].eddy_seasonality
    assert combined.moisture_require_convergence


@pytest.mark.parametrize('value', [-.1, 1., float('nan')])
def test_invalid_seasonality_is_rejected_before_grid_construction(value):
    with pytest.raises(ValueError, match='eddy_seasonality'):
        ClimateModel(Params(eddy_seasonality=value))
