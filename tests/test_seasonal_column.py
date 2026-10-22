import numpy as np
from test_earth import _toy_case
from rotclimate import earth
from rotclimate.config import Params


def test_column_option_is_exactly_inert_without_seasonal_lapse():
    p=Params(steps_per_year=13,t_iters=6,picard_iters=32,moisture_residual_tol=.01,
             moisture_require_convergence=True,solver_rtol=1e-6)
    off=earth.run_case(p,_toy_case(),steps=13)
    on=earth.run_case(p.replace(seasonal_column_lapse=True),_toy_case(),steps=13)
    assert np.array_equal(off.T,on.T) and np.array_equal(off.P,on.P)


def test_seasonal_column_changes_rain_with_converged_moisture():
    p=Params(steps_per_year=13,t_iters=6,picard_iters=64,moisture_residual_tol=.01,
             moisture_require_convergence=True,solver_rtol=1e-6,lapse_seasonal=.25)
    off=earth.run_case(p,_toy_case(),steps=13)
    on=earth.run_case(p.replace(seasonal_column_lapse=True),_toy_case(),steps=13)
    assert np.all(np.isfinite(on.P)) and np.all(on.P>=0)
    assert np.max(np.abs(off.P-on.P)) > 1e-4
