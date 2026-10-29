import numpy as np
import pytest
from rotclimate.column_forcing import two_stream_radiation,bulk_surface_exchange,STEFAN_BOLTZMANN


def test_transparent_radiation_exact_surface_limit():
    r=two_stream_radiation([290,260],300,0,0,solar_in_w_m2=400,longwave_in_w_m2=10,surface_albedo=.25,surface_emissivity=.9)
    np.testing.assert_array_equal(r['atmospheric_heating_w_m2'],0)
    np.testing.assert_allclose(r['surface_heating_w_m2'],300+.9*(10-STEFAN_BOLTZMANN*300**4),atol=1e-12)


def test_opaque_layer_analytic_longwave_exchange():
    r=two_stream_radiation([260],300,1000,0,longwave_in_w_m2=12)
    ba,bs=STEFAN_BOLTZMANN*np.array([260.,300.])**4
    np.testing.assert_allclose(r['atmospheric_heating_w_m2'],bs+12-2*ba,atol=1e-12)
    np.testing.assert_allclose(r['surface_heating_w_m2'],ba-bs,atol=1e-12)
    np.testing.assert_allclose(r['longwave_up_w_m2'][-1],ba,atol=1e-12)


def test_isothermal_radiative_cavity_and_kirchhoff_surface_reflection():
    t=280.;r=two_stream_radiation([t]*4,t,[.01,.2,2,10],0,longwave_in_w_m2=STEFAN_BOLTZMANN*t**4,surface_emissivity=.2)
    np.testing.assert_allclose(r['atmospheric_heating_w_m2'],0,atol=1e-12)
    np.testing.assert_allclose(r['surface_heating_w_m2'],0,atol=1e-12)


def test_isothermal_layer_split_preserves_fluxes_and_total_heat():
    a=two_stream_radiation([270],295,1.7,.4,solar_in_w_m2=360,surface_albedo=.3)
    b=two_stream_radiation([270]*16,295,1.7/16,.4/16,solar_in_w_m2=360,surface_albedo=.3)
    for k in ['net_top_incoming_w_m2','surface_heating_w_m2']:
        np.testing.assert_allclose(a[k],b[k],rtol=1e-12,atol=1e-12)
    np.testing.assert_allclose(a['atmospheric_heating_w_m2'].sum(),b['atmospheric_heating_w_m2'].sum(),atol=1e-12)


def test_random_columns_actual_local_energy_and_shortwave_absorption():
    rng=np.random.default_rng(631);t=rng.uniform(220,300,(8,4,5));ts=rng.uniform(280,310,(4,5))
    r=two_stream_radiation(t,ts,rng.uniform(0,2,t.shape),rng.uniform(0,.2,t.shape),solar_in_w_m2=350,surface_albedo=.2,surface_emissivity=.95)
    np.testing.assert_allclose(r['atmospheric_heating_w_m2'].sum(0)+r['surface_heating_w_m2'],r['net_top_incoming_w_m2'],atol=1e-11)
    assert np.all(r['atmospheric_shortwave_heating_w_m2']>=0)


def exchange(ts=290.,ta=290.,q=.005,wind=5.,wet=1.,height=10.,pa=101325.):
    return bulk_surface_exchange(ts,ta,q,101325.,pa,wind,height,.01,scalar_roughness_m=.001,water_availability=wet)


def test_neutral_surface_equilibrium_and_zero_wind():
    es=611.2*np.exp(17.67*(290-273.15)/(290-29.65));qsat=.622*es/(101325-es)
    r=exchange(q=qsat);np.testing.assert_allclose(r['vapor_flux_kg_m2_s'],0,atol=1e-18);np.testing.assert_allclose(r['sensible_heat_w_m2'],0,atol=1e-12)
    r=exchange(ts=300,q=.001,wind=0);assert r['vapor_flux_kg_m2_s']==0 and r['sensible_heat_w_m2']==0


def test_evaporation_water_stress_and_signed_dew():
    wet=exchange(ts=300,q=.001);dry=exchange(ts=300,q=.001,wet=0)
    assert wet['vapor_flux_kg_m2_s']>0 and dry['vapor_flux_kg_m2_s']==0
    dew=exchange(ts=280,q=.02,wet=0)
    assert dew['vapor_flux_kg_m2_s']<0 and dew['phase_heat_flux_w_m2']<0
    assert wet['sensible_heat_w_m2']>0 and dew['sensible_heat_w_m2']<0


def test_reference_pressure_uses_neutral_potential_temperature():
    ts=295.;pa=90000.;ta=ts*(pa/101325.)**(287.05/1004.)
    r=exchange(ts=ts,ta=ta,pa=pa,height=1000)
    np.testing.assert_allclose(r['air_referred_to_surface_k'],ts,atol=1e-12)
    np.testing.assert_allclose(r['sensible_heat_w_m2'],0,atol=1e-10)
    assert exchange(height=1000)['exchange_coefficient']<exchange(height=10)['exchange_coefficient']


def test_actual_vapor_enthalpy_includes_liquid_transport_not_just_latent_heat():
    r=exchange(ts=np.array([270.,290.,320.]),q=np.array([.02,.005,.001]))
    np.testing.assert_allclose(r['vapor_enthalpy_flux_w_m2'],r['phase_heat_flux_w_m2']+r['liquid_enthalpy_transport_w_m2'],rtol=1e-12,atol=1e-12)
    assert r['vapor_flux_kg_m2_s'][0]<0<r['vapor_flux_kg_m2_s'][-1]
    np.testing.assert_allclose(r['vapor_donor_temperature_k'][0],290.)


@pytest.mark.parametrize('bad',[dict(longwave_optical_depth=-1),dict(surface_albedo=1.1)])
def test_invalid_radiation_input(bad):
    args=dict(temperature_k=[280,250],surface_temperature_k=290,longwave_optical_depth=.2,shortwave_optical_depth=.1);args.update(bad)
    with pytest.raises(ValueError):two_stream_radiation(**args)


def test_invalid_exchange_height_and_water_availability():
    with pytest.raises(ValueError):exchange(height=.001)
    with pytest.raises(ValueError):exchange(wet=2)
