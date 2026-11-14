from types import SimpleNamespace

import numpy as np
import pytest

from harvest.groundwater_fields import GroundwaterFieldState,groundwater_field_year,periodic_groundwater_fields
from harvest.river_fields import field_year
from harvest.soil_drying import soil_profile,soil_state


def forcing(nt=4,nf=1,days=None):
    dt=np.ones(nt) if days is None else np.array(days,float)
    pond=np.zeros((nt,nf),bool);pond[:max(1,nt//2)]=True
    return dict(profile=soil_profile(.25,.1,.1,.1,9.),area_m2=np.full(nf,1000.),field_nodes=np.zeros(nf,int),source_m3=np.full((nt,1),100.),clock=SimpleNamespace(step_days=dt,river_order=[0],river_receiver=[-1]),rain_mm=np.zeros((nt,nf)),eto_mm_day=np.zeros((nt,nf)),crop_mask=~pond,capture_mask=pond,pond_mask=pond,crop_kcb=.75,pond_capacity_mm=20.,infiltration_mm_day=20.,bare_background=.15)


def run(a,**extra):
    options=dict(aquifer_capacity_mm=30.,capillary_permission_mm_day=3.,recharge_mm_day=5.,recharge_mask=a['pond_mask'])
    options.update(extra)
    return groundwater_field_year(**a,**options)


def closed(a,r):
    nt,nf=len(a['clock'].step_days),len(a['area_m2'])
    before=sum(r['initial'].values());rain=np.broadcast_to(a['rain_mm'],(nt,nf))
    sinks=['surface_evap_mm','bare_diffusion_mm','root_uptake_mm','pond_evap_mm','pond_release_mm','surface_overflow_mm','soil_drainage_mm','rain_excluded_mm','aquifer_loss_mm']
    for t in range(nt):
        after=sum(r[name][t] for name in ['top_mm','deep_mm','bound_mm','pond_mm','aquifer_mm'])
        losses=sum(r[name][t] for name in sinks)
        np.testing.assert_allclose(before+rain[t]+r['delivered_mm'][t]-after-losses,0,atol=2e-12)
        residual=float(np.sum((before+rain[t]-after-losses)*a['area_m2']/1000)+a['source_m3'][t].sum()-r['river_loss_m3'][t].sum()-r['river_outlet_m3'][t].sum())
        assert abs(residual)<2e-10
        before=after


def test_zero_groundwater_replays_every_legacy_array_exactly():
    a=forcing(nf=3,days=[1,.5,.25,1.]);a.update(profile=soil_profile(.25,.1,1.,.1,9.),area_m2=np.array([1000.,2000.,500.]),field_nodes=np.array([0,1,1]),source_m3=np.array([[40.,1.],[20.,0.],[5.,3.],[0.,1.]]),clock=SimpleNamespace(step_days=np.array([1.,.5,.25,1.]),river_order=[1,0],river_receiver=[1,-1]),eto_mm_day=np.full((4,3),3.),rain_mm=np.arange(12).reshape(4,3)/10,efficiency=.5)
    old=field_year(**a);new=run(a,aquifer_capacity_mm=0,capillary_permission_mm_day=0,recharge_mm_day=0)
    for key,value in old.items():
        if key not in ['initial','final']:np.testing.assert_array_equal(new[key],value,err_msg=key)
    for key,value in old['initial'].items():np.testing.assert_array_equal(new['initial'][key],value)
    assert not new['aquifer_mm'].any();closed(a,new)


def test_empty_start_never_creates_capillary_water_or_uptake():
    a=forcing();a.update(source_m3=np.zeros((4,1)),rain_mm=0.,eto_mm_day=5.)
    r=run(a,capillary_permission_mm_day=100.)
    assert not r['capillary_rise_mm'].any() and not r['root_uptake_mm'].any() and not r['aquifer_mm'].any()
    closed(a,r)


def test_paid_pond_recharge_precedes_later_capped_transfer():
    a=forcing();a['eto_mm_day']=np.array([[0.],[0.],[5.],[5.]])
    r=run(a)
    assert r['aquifer_recharge_mm'][0,0]==0
    assert r['aquifer_recharge_mm'][1,0]==5 and r['aquifer_mm'][1,0]==5
    assert r['capillary_rise_mm'][1,0]==0 and r['capillary_rise_mm'][2,0]==0
    assert r['capillary_rise_mm'][3,0]==3 and r['aquifer_mm'][3,0]==2
    closed(a,r)


def test_recharge_consumes_same_infiltration_allowance():
    a=forcing(nt=1);initial=GroundwaterFieldState(soil_state(a['profile']),np.array([20.]),np.zeros(1))
    r=run(a,initial=initial,capillary_permission_mm_day=0.)
    assert r['aquifer_recharge_mm'][0,0]==5 and r['infiltration_mm'][0,0]==15
    assert r['aquifer_recharge_mm'][0,0]+r['infiltration_mm'][0,0]==20
    closed(a,r)


def test_closed_pond_is_released_without_recharge_credit():
    a=forcing(nt=1);a.update(pond_mask=np.array([[False]]),capture_mask=np.array([[False]]),crop_mask=np.array([[True]]),source_m3=np.zeros((1,1)))
    initial=GroundwaterFieldState(soil_state(a['profile']),np.array([20.]),np.zeros(1))
    r=run(a,initial=initial,recharge_mask=np.array([[True]]))
    assert r['aquifer_recharge_mm'][0,0]==0 and r['pond_release_mm'][0,0]==20
    assert r['aquifer_mm'][0,0]==0;closed(a,r)


def test_below_wp_recharge_is_not_root_available():
    a=forcing(nt=1);a.update(source_m3=np.zeros((1,1)),crop_mask=np.array([[True]]),pond_mask=np.array([[False]]),capture_mask=np.array([[False]]),eto_mm_day=5.)
    initial=GroundwaterFieldState(soil_state(a['profile']),np.zeros(1),np.array([3.]))
    r=run(a,initial=initial,capillary_permission_mm_day=10.)
    assert r['capillary_rise_mm'][0,0]==3 and r['root_uptake_mm'][0,0]==0
    assert r['top_mm'][0,0]==0 and r['bound_mm'][0,0]>0;closed(a,r)


def test_explicit_aquifer_loss_is_debited_before_transfer():
    a=forcing(nt=1);a.update(source_m3=np.zeros((1,1)),capture_mask=np.array([[False]]),profile=soil_profile(.25,.1,1.,.1,9.))
    initial=GroundwaterFieldState(soil_state(a['profile']),np.zeros(1),np.array([10.]))
    r=run(a,initial=initial,aquifer_loss_mm_day=3.,capillary_permission_mm_day=100.)
    assert r['aquifer_loss_mm'][0,0]==3 and r['capillary_rise_mm'][0,0]==7 and r['aquifer_mm'][0,0]==0
    closed(a,r)


def test_all_rates_use_actual_fractional_duration():
    a=forcing(nt=1,days=[.25]);a['profile']=soil_profile(.25,.1,1.,.1,9.)
    initial=GroundwaterFieldState(soil_state(a['profile']),np.array([10.]),np.array([2.]))
    r=run(a,initial=initial,aquifer_loss_mm_day=1.)
    assert r['aquifer_loss_mm'][0,0]==.25 and r['capillary_rise_mm'][0,0]==.75
    assert r['aquifer_recharge_mm'][0,0]==1.25
    assert r['infiltration_mm'][0,0]+r['aquifer_recharge_mm'][0,0]<=5+1e-12
    closed(a,r)


def test_periodic_all_five_stocks_converge_and_nonconvergence_is_explicit():
    a=forcing();a['eto_mm_day']=np.array([[0.],[0.],[5.],[5.]])
    options=dict(aquifer_capacity_mm=30.,capillary_permission_mm_day=3.,recharge_mm_day=5.,recharge_mask=a['pond_mask'])
    r=periodic_groundwater_fields(**a,**options)
    assert r['periodic'] and r['periodic_residual_mm']<=1e-6
    assert set(r['initial'])=={'top_mm','deep_mm','bound_mm','pond_mm','aquifer_mm'}
    closed(a,r)
    a=forcing(nt=2);a.update(pond_mask=np.ones((2,1),bool),crop_mask=np.zeros((2,1),bool),capture_mask=np.ones((2,1),bool))
    r=periodic_groundwater_fields(**a,aquifer_capacity_mm=1e6,capillary_permission_mm_day=0,recharge_mm_day=5,recharge_mask=a['pond_mask'],max_years=2)
    assert not r['periodic'] and r['aquifer_mm'][-1,0]>0


@pytest.mark.parametrize('change',[
    {'aquifer_capacity_mm':-1},{'capillary_permission_mm_day':np.nan},{'recharge_mm_day':-1},
    {'aquifer_loss_mm_day':np.inf},{'recharge_mask':1},
])
def test_invalid_groundwater_inputs_rejected(change):
    with pytest.raises(ValueError):run(forcing(),**change)


def test_invalid_initial_capacity_and_clock_rejected():
    a=forcing()
    with pytest.raises(ValueError):run(a,initial=GroundwaterFieldState(soil_state(a['profile']),[0],[31]))
    with pytest.raises(ValueError):GroundwaterFieldState(soil_state(a['profile']),[0],[-1])
    a['clock']=SimpleNamespace(step_days=np.full(4,2.),river_order=[0],river_receiver=[-1])
    with pytest.raises(ValueError):run(a)
