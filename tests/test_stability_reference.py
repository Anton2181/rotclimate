"""Independent hydrostatic limits and honest nonpositive-stability exclusion."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import G,RD,CP
from scripts.audit_stability_reference import diagnose_height_column,evaluate_column


def test_isothermal_hypsometry_and_stability_on_unequal_pressure_layers():
    p=np.array([92500.,85000.,70000.,50000.,25000.,10000.]);t=265.
    z=-RD*t/G*np.log(p/p[0])+765.
    out=diagnose_height_column(p,z)
    np.testing.assert_allclose(out['hypsometric_virtual_temperature_k'],t,rtol=1e-14)
    np.testing.assert_allclose(out['stability_s2'],G*G/(CP*t),rtol=1e-13)
    np.testing.assert_allclose(out['density_kg_m3']*np.diff(z),-np.diff(p)/G,rtol=1e-14)


def test_lapse_lowest_layer_anchor_recovers_exact_prescribed_base_temperature():
    gamma=.006;t=296.;p=np.array([92500.,85000.,70000.,50000.,25000.,10000.])
    z=(t-t*(p/p[0])**(RD*gamma/G))/gamma
    result=evaluate_column(p,z)
    assert result['conditional_base_temperature_k']==pytest.approx(t,abs=1e-11)
    assert result['valid_stable_proxy']


def test_unstable_profile_is_reported_without_fitted_or_floored_mode_speed():
    p=np.array([92500.,85000.,70000.,50000.,25000.,10000.]);gamma=.012;t=296.
    z=(t-t*(p/p[0])**(RD*gamma/G))/gamma
    result=evaluate_column(p,z)
    assert not result['valid_stable_proxy']
    assert result['nonpositive_interfaces']==list(range(len(p)-2))
    assert result['inferred_first_speed_ms'] is None
    assert np.all(np.array(result['stability_s2'])<0)


@pytest.mark.parametrize('p,z',[(np.array([92500.,85000.,95000.]),np.array([0.,1000.,2000.])),
                              (np.array([92500.,85000.,70000.]),np.array([0.,2000.,1000.]))])
def test_invalid_pressure_or_height_order_rejected(p,z):
    with pytest.raises(ValueError):diagnose_height_column(p,z)
