"""Column empirical convection and conservative rain evaporation limits."""
import numpy as np
import pytest
from rotclimate.config import Params
from rotclimate.moisture import rain_coefficient
from rotclimate.reservoir_moisture import reservoir_rain_coefficients,reservoir_rain_partition

DAY=86400.


def settings(**changes):
    return Params(moisture_reservoir_rain_scheme='column-convection',rh_threshold=.36774492725507657,
        precip_tau_days=11.078614585004903).replace(**changes)


def closure(**changes):
    return dict(conv=.3647612418951105,r0=.6829148729649469,evap=.3772388409328513,T=20.,fT=1.,**changes)


def test_disabled_scheme_preserves_exact_historical_layer_arithmetic():
    rng=np.random.default_rng(91);water=rng.uniform(0,40,(2,3,4));f=np.array([.6,.4])[:,None,None]
    p=settings(moisture_reservoir_rain_scheme='layer');c=closure()
    expected=rain_coefficient(water/f,40.,1.5,1.2,p.rh_threshold,p.precip_tau_days,c,spread=p.rh_spread)
    actual,transfer=reservoir_rain_partition(water,f,40.,1.5,1.2,p,c)
    np.testing.assert_array_equal(actual,expected);assert transfer==0.


@pytest.mark.parametrize('total',[0.,.03,20.,40.,52.])
def test_proportional_profile_ground_rain_matches_original_column_including_water_floor(total):
    f=np.array([.25,.75])[:,None,None];water=f*np.full((2,3),total);p=settings(rh_spread=.05)
    rate=reservoir_rain_coefficients(water,f,40.,1.5,1.2,p,closure())
    ground=(rate*water).sum(0)*DAY
    expected=rain_coefficient(np.full((2,3),total),40.,1.5,1.2,p.rh_threshold,p.precip_tau_days,closure(),spread=.05)*total*DAY
    np.testing.assert_allclose(ground,expected,atol=2e-14,rtol=2e-14)


def test_column_convective_relation_cannot_be_amplified_by_unequal_layer_humidity():
    f=np.array([.6,.4])[:,None,None];water=f*40*np.array([.9,.4])[:,None,None]
    p=settings();c=closure();c['evap']=0.
    actual=reservoir_rain_coefficients(water,f,40.,0.,1.,p,c)
    total=water.sum(0);expected=c['conv']*np.exp(11.4*(total/40-c['r0']))
    np.testing.assert_allclose((actual*water).sum(0)*DAY,expected,rtol=1e-14)
    historical=reservoir_rain_coefficients(water,f,40.,0.,1.,p.replace(moisture_reservoir_rain_scheme='layer'),c)
    assert float((historical*water).sum()/(actual*water).sum())>3.


def test_dry_lower_air_evaporates_upper_rain_into_lower_vapor_with_no_column_source():
    f=np.array([.6,.4])[:,None,None];water=f*40*np.array([.2,.9])[:,None,None];p=settings()
    wet=closure();wet['evap']=0.
    ground,recycled=reservoir_rain_partition(water,f,40.,1.5,1.,p,closure())
    gross=reservoir_rain_coefficients(water,f,40.,1.5,1.,p,wet)
    attenuation=np.exp(-closure()['evap']*24.*80./3000.)
    np.testing.assert_allclose(ground/gross,attenuation,rtol=1e-14)
    np.testing.assert_allclose(recycled,(1-attenuation)*gross[1],rtol=1e-14)
    # Upper loss minus ground rain is the equal lower vapor gain.
    upper_loss=gross[1]*water[1]
    transfer=recycled*water[1]
    np.testing.assert_allclose(upper_loss-ground[1]*water[1],transfer,rtol=1e-14)
    np.testing.assert_array_equal(np.stack([transfer,-transfer]).sum(0),0.)


def test_local_dynamic_gate_remains_local_and_saturation_overflow_cannot_evaporate():
    f=np.array([.6,.4])[:,None,None];water=f*40*np.array([1.2,1.3])[:,None,None];p=settings()
    c=closure();c.update(conv=0.,evap=1e6)
    actual,recycled=reservoir_rain_partition(water,f,40.,0.,1.,p,c)
    np.testing.assert_allclose(actual*water*DAY,np.maximum(water-f*40,0),rtol=1e-14)
    np.testing.assert_array_equal(recycled,0.)
    water=f*40*np.array([.8,.4])[:,None,None]
    actual=reservoir_rain_coefficients(water,f,40.,1.5,1.2,p,None)
    expected=rain_coefficient(water/f,40.,1.5,1.2,p.rh_threshold,p.precip_tau_days)
    np.testing.assert_array_equal(actual,expected)


def test_analytic_two_box_precipitation_recycling_changes_profile_without_creating_water(monkeypatch):
    from test_reservoir_moisture import solver,params
    import rotclimate.reservoir_moisture as module
    p=params(moisture_reservoir_rain_scheme='column-convection');s=solver();shape=s.column_mass.shape
    # Gross rate.1/day and half of rain survives the same lower cloud base.
    # Upper evaporation is an upper loss AND an equal lower vapor source.
    monkeypatch.setattr(module,'reservoir_rain_partition',lambda w,*args:
        (np.ones_like(w)*.05/DAY,np.ones(shape)*.05/DAY))
    zero=np.zeros(shape);ones=np.ones(shape)
    result=module.solve_reservoir_moisture(s,p,zero,zero,zero,zero,ones/DAY,1000*ones,
        zero,1.,14*ones,14*ones,sink=ones/(50*DAY),lower_capacity_fraction=.625,ocean_lower_fraction=.625)
    expected=np.linalg.solve([[.22,-.10],[-.15,.17]],[1.,0.])
    np.testing.assert_allclose(result.layer_water[:,1:-1,1:-1],np.broadcast_to(expected[:,None,None],(2,3,4)),atol=2e-6)
    np.testing.assert_allclose(result.rain[1:-1,1:-1],.05*expected.sum(),atol=2e-7)
    np.testing.assert_allclose(result.water[1:-1,1:-1]/50+result.rain[1:-1,1:-1],1.,atol=2e-7)
    assert result.certificate['all_layer_checks_passed']
    assert result.certificate['maximum_internal_precipitation_transfer_residual_mm_day']==0.
    assert result.certificate['maximum_recycled_precipitation_mm_day']==pytest.approx(.05*expected[1],abs=1e-7)


def test_new_scheme_coupled_climate_passes_both_layer_and_column_ledgers():
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth
    from rotclimate.model import ClimateModel
    case=_toy_case();p=earth.earth_params(strict_params().replace(moisture_transport_form='flux',flux_convergence=0,
        eddy_moisture_scheme='conservative',moisture_mass_balance=True,moisture_two_layer=True,
        moisture_mass_tracer=True,moisture_reservoirs=True,moisture_relaxation=.1,picard_iters=1024,
        moisture_reservoir_rain_scheme='column-convection',convective_rain=.3,subcloud_evaporation=.4),case)
    result=ClimateModel(p,grid=case.grid).run(diagnose_moisture=True)
    assert result.numerics['all_checks_passed']
    cert=result.numerics['moisture_reservoirs']
    assert cert['rain_scheme']=='column-convection'
    assert all(s['rain_scheme']=='column-convection' for s in cert['steps'])
    assert cert['max_scaled_layer_residual']<=p.moisture_residual_tol
    assert result.numerics['vapor_flux_budget']['max_scaled_equation_residual']<=p.moisture_residual_tol
    assert all(s['maximum_internal_precipitation_transfer_residual_mm_day']==0 for s in cert['steps'])


@pytest.mark.parametrize('changes',[dict(moisture_reservoir_rain_scheme='unknown'),
                                   dict(moisture_reservoir_rain_scheme='column-convection')])
def test_invalid_or_silently_inactive_rain_scheme_is_rejected(changes):
    from rotclimate.model import ClimateModel
    with pytest.raises(ValueError):ClimateModel(Params(**changes))
