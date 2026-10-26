import numpy as np
import pytest
from experiments.parcel_ascent import ascend,specific_from_relative_humidity,vapor_pressure
from rotclimate.column_thermodynamics import RD,CP,LV,EPSILON,specific_saturation


def test_dry_adiabat_and_work_have_closed_analytic_solution():
    result=ascend(300,100000,0,30000)
    np.testing.assert_allclose(result.temperature_k,300*(result.pressure_pa/100000)**(RD/CP),rtol=1e-14)
    np.testing.assert_array_equal(result.vapor_kg_kg_dry,0)
    np.testing.assert_array_equal(result.condensed_kg_kg_dry,0)
    np.testing.assert_allclose(result.first_law_residual_j_kg_dry,0,atol=1e-10)
    assert result.lcl_pressure_pa is None


def test_unsaturated_short_ascent_does_not_condense_or_invent_latent_heat():
    q=specific_from_relative_humidity(300,100000,.1)
    result=ascend(300,100000,q,90000)
    assert result.lcl_pressure_pa is None
    np.testing.assert_array_equal(result.condensed_kg_kg_dry,0)
    assert result.temperature_k[-1]==pytest.approx(300*.9**(RD/CP))


def test_relative_humidity_and_mixing_ratio_are_distinct_mass_conventions():
    q=specific_from_relative_humidity(300,100000,.6)
    e=q*100000/(EPSILON+(1-EPSILON)*q)
    assert e/vapor_pressure(300)==pytest.approx(.6,rel=1e-14)
    assert abs(q-.6*specific_saturation(300,100000))>1e-5
    result=ascend(300,100000,q,50000)
    np.testing.assert_allclose(result.vapor_kg_kg_dry+result.condensed_kg_kg_dry,q/(1-q),atol=1e-17)
    assert result.condensed_kg_kg_dry[-1]>0
    # Subtracting specific q on changing total mass would lose parcel water.
    wet_q=result.vapor_kg_kg_dry[-1]/(1+result.vapor_kg_kg_dry[-1])
    assert abs((q-wet_q)-result.condensed_kg_kg_dry[-1])>1e-5


def test_lcl_satisfies_dry_adiabat_and_dewpoint_and_saturated_ascent_keeps_first_law():
    q=specific_from_relative_humidity(300,100000,.6)
    result=ascend(300,100000,q,30000)
    plcl=result.lcl_pressure_pa
    assert 50000<plcl<100000
    tlcl=300*(plcl/100000)**(RD/CP)
    np.testing.assert_allclose(specific_saturation(tlcl,plcl),q,rtol=1e-12)
    assert result.temperature_k[-1]>300*.3**(RD/CP)
    assert np.max(np.abs(result.first_law_residual_j_kg_dry))<.001
    for count in [64,128]:
        other=ascend(300,100000,q,30000,steps=count)
        assert abs(other.temperature_k[-1]-result.temperature_k[-1])<1e-5
        assert abs(other.condensed_kg_kg_dry[-1]-result.condensed_kg_kg_dry[-1])<1e-8


def test_null_ascent_preserves_state_exactly():
    q=specific_from_relative_humidity(285,100000,.9)
    result=ascend(285,100000,q,100000)
    np.testing.assert_array_equal(result.temperature_k,[285.])
    np.testing.assert_array_equal(result.condensed_kg_kg_dry,[0.])
    np.testing.assert_array_equal(result.first_law_residual_j_kg_dry,[0.])


def test_saturated_start_condenses_immediately_without_a_spurious_dry_segment():
    q=float(specific_saturation(300,100000))
    result=ascend(300,100000,q,50000)
    assert result.lcl_pressure_pa==100000
    assert result.condensed_kg_kg_dry[1]>0
    assert result.temperature_k[-1]>300*.5**(RD/CP)
    assert np.max(np.abs(result.first_law_residual_j_kg_dry))<.001


@pytest.mark.parametrize('args',[(260,100000,.001,50000),(300,100000,.9,50000),
                               (300,100000,.001,110000),(300,100000,.001,20000)])
def test_unsupported_parcels_fail_closed(args):
    with pytest.raises(ValueError):ascend(*args)
