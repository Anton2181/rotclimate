"""Archive calendar and actual two-reservoir/energy-conserving initial transfer."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import G,RD,CP
from rotclimate.pressure_initialization import select_recorded_day,initialize_archived_column
from rotclimate.pressure_moist import gas_energy


def inputs():
    edges=np.r_[101325.,85493.75,np.geomspace(85493.75,38000.,6)[1:]]
    ts=np.full((2,3),26.);lower=np.array([[5.,10.,20.],[0.,12.,30.]]);upper=np.full((2,3),15.)
    return edges,ts,lower,upper,np.zeros((2,3))


def test_selected_scored_record_does_not_accidentally_use_same_day_spinup():
    assert select_recorded_day([7.3,21.9],[1,2],[21.9,7.3,21.9],21.9)==2


def test_mismatched_calendar_or_missing_declared_day_rejected():
    with pytest.raises(ValueError):select_recorded_day([7.3,21.9],[0,1],[21.9,7.3,21.9],21.9)
    with pytest.raises(ValueError):select_recorded_day([7.3,21.9],[1,2],[21.9,7.3,21.9],18.)


def test_actual_lower_upper_water_and_initial_phase_energy_are_preserved():
    edges,ts,lower,upper,z=inputs();result=initialize_archived_column(ts,lower,upper,z,edges)
    np.testing.assert_allclose(result.raw_vapor_kg_m2[:1].sum(0),lower,atol=1e-12)
    np.testing.assert_allclose(result.raw_vapor_kg_m2[1:].sum(0),upper,atol=1e-12)
    np.testing.assert_allclose(result.vapor_kg_m2.sum(0)+result.initial_rain_kg_m2,lower+upper,atol=1e-11)
    m=np.broadcast_to((-np.diff(edges)/G)[:,None,None],result.temperature_k.shape)
    before=gas_energy(result.raw_temperature_k,result.raw_vapor_kg_m2,m).sum(0)
    after=gas_energy(result.temperature_k,result.vapor_kg_m2,m).sum(0)+result.initial_rain_enthalpy_j_m2
    np.testing.assert_allclose(after,before,rtol=1e-13,atol=1e-6)
    assert result.certificate['lower_dry_mass_fraction']==pytest.approx(.25)


def test_dry_flat_profile_matches_hydrostatic_fixed_lapse_without_reset_rain():
    edges,ts,lower,upper,z=inputs();lower*=0;upper*=0;out=initialize_archived_column(ts,lower,upper,z,edges)
    p=np.sqrt(edges[:-1]*edges[1:])[:,None,None];expected=(ts+273.15)[None]*(p/edges[0])**(RD*.006/G)
    np.testing.assert_allclose(out.temperature_k,expected,atol=1e-11)
    assert out.initial_rain_kg_m2.max()==0


def test_declared_elevation_reduction_uses_same_global_lapse():
    edges,ts,lower,upper,z=inputs();lower*=0;upper*=0;z[:]=1000
    out=initialize_archived_column(ts,lower,upper,z,edges)
    p=np.sqrt(edges[:-1]*edges[1:])[:,None,None]
    np.testing.assert_allclose(out.raw_temperature_k,(ts+273.15+6.)[None]*(p/edges[0])**(RD*.006/G),atol=1e-12)


def test_zero_reservoir_stays_empty_during_raw_remap():
    edges,ts,lower,upper,z=inputs();upper*=0;out=initialize_archived_column(ts,lower,upper,z,edges)
    assert out.raw_vapor_kg_m2[1:].max()==0


def test_invalid_water_or_out_of_domain_temperature_rejected_without_clipping():
    edges,ts,lower,upper,z=inputs()
    with pytest.raises(ValueError):initialize_archived_column(ts,-lower,upper,z,edges)
    with pytest.raises(ValueError):initialize_archived_column(ts+100,lower,upper,z,edges)
