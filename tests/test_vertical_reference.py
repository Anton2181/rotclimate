import numpy as np
import pytest
from scripts.audit_vertical_reference import partial_humidity
from rotclimate.column_thermodynamics import G


def test_pressure_integral_and_layer_means_have_independent_affine_solution():
    p=np.array([925,850,700,600,500,400,300.]);q=(.002+1e-7*p*100)[None,:,None]
    water,ratio=partial_humidity(q,p)
    primitive=lambda x:.002*x+.5e-7*x*x
    np.testing.assert_allclose(water,(primitive(92500)-primitive(30000))/G,rtol=1e-14)
    lower=.002+1e-7*(92500+70000)/2;upper=.002+1e-7*(70000+30000)/2
    np.testing.assert_allclose(ratio,upper/lower,rtol=1e-14)


def test_pressure_units_or_missing_levels_cannot_silently_change_partial_column():
    with pytest.raises(ValueError):partial_humidity(np.ones((12,3,2)),[92500,70000,30000])
    with pytest.raises(ValueError):partial_humidity(np.ones((12,3,2)),[925,600,300])
