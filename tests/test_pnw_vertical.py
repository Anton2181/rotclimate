import numpy as np
import pytest
from scripts.audit_pnw_vertical import partial_integrals,summarize_arrays
from rotclimate.column_thermodynamics import G
from scripts.earth_calendar import MONTH_DAYS


def test_partial_water_and_pressure_mean_ratios_match_affine_analytic_integrals():
    p=np.array([925,850,700,600,500,400,300.])
    q=np.broadcast_to((.002+1e-7*p*100)[None,:,None],(12,7,2))
    actual=partial_integrals(q,p)
    integral=lambda x:.002*x+.5e-7*x*x
    np.testing.assert_allclose(actual['total_mm'],(integral(92500)-integral(30000))/G,rtol=1e-14)
    np.testing.assert_allclose(actual['lower_mm']+actual['upper_mm'],actual['total_mm'],rtol=1e-14)
    lower=.002+1e-7*(92500+70000)/2;upper=.002+1e-7*(70000+30000)/2
    np.testing.assert_allclose(actual['upper_lower_mean_q_ratio'],upper/lower,rtol=1e-14)


def test_native_pressure_and_month_axes_survive_true_area_and_day_weighting():
    value=np.arange(12)[:,None,None]+np.array([0.,10])[None,:,None]+np.array([0.,100])[None,None,:]
    out=summarize_arrays({'profile':value},np.array([1.,3.]),MONTH_DAYS)
    np.testing.assert_allclose(out['monthly']['profile'],np.arange(12)[:,None]+[75.,85.])
    np.testing.assert_allclose(out['seasons']['DJF']['profile'],[79.1,89.1])
    np.testing.assert_allclose(out['seasons']['JJA']['profile'],75+553/92+np.array([0.,10.]))
    with pytest.raises(ValueError):summarize_arrays({'profile':value},np.array([1.,0.]),MONTH_DAYS)
