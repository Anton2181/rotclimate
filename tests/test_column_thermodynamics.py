import numpy as np
import pytest
from scipy.integrate import quad
from rotclimate.column_thermodynamics import saturation_column,specific_saturation,G,RD,EPSILON


def test_isothermal_integral_matches_independent_closed_form():
    t=12.;ps=101325.;e=611.2*np.exp(17.67*t/(t+243.5));a=(1-EPSILON)*e
    analytic=lambda hi,lo:EPSILON*e/G*np.log((hi-a)/(lo-a))
    column=saturation_column(t,ps,profile='isothermal')
    np.testing.assert_allclose(column.water_mm,[analytic(ps,.75*ps),analytic(.75*ps,10000)],rtol=1e-10)
    np.testing.assert_allclose(column.interface_temperature_k,t+273.15)
    np.testing.assert_allclose(column.air_mass_kg_m2.sum(),ps/G)


def test_environmental_lapse_matches_independent_hydrostatic_quadrature():
    ts=310.;ps=101325.;lapse=6.;alpha=RD*lapse/1000/G
    expected=[]
    for hi,lo in [(ps,.75*ps),(.75*ps,10000.)]:
        def integrand(p):
            t=ts*(p/ps)**alpha;c=t-273.15;e=611.2*np.exp(17.67*c/(c+243.5))
            return EPSILON*e/(p-(1-EPSILON)*e)/G
        expected.append(quad(integrand,lo,hi,epsabs=1e-10)[0])
    column=saturation_column(ts-273.15,ps,profile='lapse',lapse_k_km=lapse,steps=128)
    np.testing.assert_allclose(column.water_mm,expected,rtol=2e-8)
    np.testing.assert_allclose(column.interface_temperature_k[-1],ts*(10000/ps)**alpha,rtol=1e-10)


def test_moist_adiabat_warmer_and_holds_more_water_than_dry_adiabat():
    moist=saturation_column(25.,101325.,profile='moist')
    dry=saturation_column(25.,101325.,profile='lapse',lapse_k_km=G/1004*1000)
    assert (moist.interface_temperature_k>=dry.interface_temperature_k).all()
    assert (moist.water_mm>dry.water_mm).all()


def test_pressure_quadrature_converges_in_cold_warm_and_elevated_columns():
    t=np.array([-50.,-20.,0.,25.,35.]);p=np.array([65000.,80000.,101325.,101325.,90000.])
    a=saturation_column(t,p,steps=64);b=saturation_column(t,p,steps=128)
    # The prescribed isothermal tropopause is a nonsmooth thermal boundary.
    # Require a sub-micron water error there, in addition to relative accuracy.
    np.testing.assert_allclose(a.water_mm,b.water_mm,rtol=2e-5,atol=1e-4)
    assert (np.diff(a.total_mm)>0).all()
    assert (a.lower_water_fraction>0).all() and (a.lower_water_fraction<1).all()


def test_cold_water_keeps_decreasing_instead_of_old_minus45C_floor():
    water=saturation_column(np.array([-65.,-55.,-45.]),101325.).total_mm
    assert (np.diff(water)>0).all()


@pytest.mark.parametrize('changes',[dict(temperature_c=np.nan),dict(surface_pressure_pa=30000.),dict(profile='unknown'),dict(steps=0),dict(lapse_k_km=12)])
def test_unsupported_profiles_fail_instead_of_hidden_thermodynamic_clips(changes):
    kwargs=dict(temperature_c=20.,surface_pressure_pa=101325.);kwargs.update(changes)
    with pytest.raises(ValueError):saturation_column(**kwargs)


def test_specific_humidity_is_not_mixing_ratio():
    q=specific_saturation(300.,100000.);c=300-273.15;e=611.2*np.exp(17.67*c/(c+243.5))
    r=EPSILON*e/(100000-e)
    np.testing.assert_allclose(q,r/(1+r),rtol=1e-14)


@pytest.mark.parametrize('scheme',['pressure-lapse','pressure-moist'])
def test_coupled_model_uses_profile_in_actual_water_equation(scheme):
    from rotclimate.model import ClimateModel
    from rotclimate import earth
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    case=_toy_case();p=earth.earth_params(strict_params().replace(moisture_transport_form='flux',flux_convergence=0,
        eddy_moisture_scheme='conservative',moisture_mass_balance=True,moisture_two_layer=True,
        moisture_mass_tracer=True,moisture_relaxation=.1,picard_iters=1024,column_saturation_scheme=scheme),case)
    result=ClimateModel(p,grid=case.grid).run(diagnose_moisture=True)
    assert result.numerics['all_checks_passed']
    certificate=result.numerics['column_thermodynamics']
    assert certificate['scheme']==scheme and certificate['steps']
    assert all(s['minimum_column_capacity_mm']>0 for s in certificate['steps'])
    assert result.numerics['vapor_flux_budget']['max_scaled_equation_residual']<=p.moisture_residual_tol


def test_invalid_model_column_scheme_rejected():
    from rotclimate.model import ClimateModel
    from rotclimate.config import Params
    with pytest.raises(ValueError,match='column_saturation_scheme'):
        ClimateModel(Params(column_saturation_scheme='arbitrary'))
