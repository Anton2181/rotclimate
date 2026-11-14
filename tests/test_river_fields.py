import numpy as np
import pytest
from harvest.field_clock import field_clock
from harvest.soil_drying import soil_profile,soil_state
from harvest.river_fields import bare_soil_step,field_year,periodic_fields,RiverClock


def setup(nf=1,receiver=(-1,)):
    clock=field_clock(np.linspace(0,1,13))
    nt=len(clock.step_days)
    # Twelve short mathematical steps, not a geographical year.
    return dict(profile=soil_profile(.25,.1,1.,.1,9.),area_m2=np.full(nf,1000.),field_nodes=np.zeros(nf,dtype=int),source_m3=np.zeros((nt,len(receiver))),clock=RiverClock(clock,np.arange(len(receiver)),receiver),rain_mm=np.zeros((nt,nf)),eto_mm_day=np.zeros((nt,nf)),crop_mask=np.zeros((nt,nf),bool),capture_mask=np.zeros((nt,nf),bool),pond_mask=np.zeros((nt,nf),bool),crop_kcb=.75)


def check_balance(a,r):
    initial=r['initial'];stock=r['top_mm']+r['deep_mm']+r['bound_mm']+r['pond_mm']
    first=sum(initial[k] for k in ('top_mm','deep_mm','bound_mm','pond_mm'))
    starts=np.concatenate([first[None,:],stock[:-1]],axis=0)
    sinks=sum(r[k] for k in ('surface_evap_mm','bare_diffusion_mm','root_uptake_mm','pond_evap_mm','pond_release_mm','surface_overflow_mm','soil_drainage_mm','rain_excluded_mm'))
    np.testing.assert_allclose(starts+a['rain_mm']+r['delivered_mm'],stock+sinks,atol=1e-10)
    np.testing.assert_allclose((r['delivered_mm']*a['area_m2']/1000).sum(1),r['river_delivered_m3'].sum(1),atol=1e-10)
    np.testing.assert_allclose(a['source_m3'].sum(1),(r['river_delivered_m3']+r['river_loss_m3']+r['river_outlet_m3']).sum(1),atol=1e-10)


def test_complete_bare_fao31_has_paid_deep_diffusion_and_no_crop_uptake():
    profile=soil_profile(.25,.1,1.,.1,9.);state=soil_state(profile,1.)
    expected=[4.73,4.73,4.53,2.59,1.47,.84,.48,.27,.16,.09];total=0.
    for printed in expected:
        r=bare_soil_step(profile,state,0.,4.5,.15)
        assert abs(float(r.evaporation_mm)-printed)<=.005000001
        assert r.diffusion_mm==pytest.approx(.675)
        assert float(state.total_mm-r.state.total_mm)==pytest.approx(float(r.evaporation_mm+r.diffusion_mm))
        total+=float(r.evaporation_mm+r.diffusion_mm);state=r.state
    assert state.deep_mm==pytest.approx(128.25)
    assert total==pytest.approx(155-float(state.total_mm))


def test_bare_diffusion_is_capped_by_deep_stock():
    p=soil_profile(.25,.1,1.,.1,9.);s=soil_state(p)
    r=bare_soil_step(p,s,0.,5,.15)
    assert r.diffusion_mm==0 and r.evaporation_mm==0


def test_shared_node_rations_by_area_and_pays_losses():
    a=setup(2);a['area_m2']=np.array([1000.,3000.]);a['capture_mask'][0]=True;a['source_m3'][0]=40
    r=field_year(**a,efficiency=.5,infiltration_mm_day=1200.)
    np.testing.assert_allclose(r['delivered_mm'][0],[5,5]);assert r['river_loss_m3'][0,0]==20
    check_balance(a,r)


def test_upstream_field_cannot_deliver_same_water_to_downstream_field():
    a=setup(2,receiver=(-1,0));a['field_nodes']=np.array([1,0]);a['source_m3'][0,1]=5;a['capture_mask'][0]=True
    r=field_year(**a,infiltration_mm_day=1200.)
    np.testing.assert_allclose(r['delivered_mm'][0],[5,0]);check_balance(a,r)


def test_pond_closure_drains_paid_stock_and_does_not_refill_soil():
    a=setup();a['source_m3'][0]=10;a['capture_mask'][0]=True;a['pond_mask'][0]=True
    r=field_year(**a,pond_capacity_mm=10,infiltration_mm_day=0)
    assert r['pond_mm'][0,0]==10 and r['pond_release_mm'][1,0]==10
    assert not r['infiltration_mm'].any();check_balance(a,r)


def test_pond_evaporation_suppresses_soil_evaporation_and_diffusion():
    a=setup();a['source_m3'][0]=100;a['capture_mask'][0]=True;a['pond_mask'][0]=True;a['eto_mm_day'][0]=4
    r=field_year(**a,pond_capacity_mm=10,infiltration_mm_day=120.,bare_background=.15)
    assert r['pond_evap_mm'][0,0]==pytest.approx(4/12)
    assert r['surface_evap_mm'][0,0]==0 and r['bare_diffusion_mm'][0,0]==0
    check_balance(a,r)


def test_rain_partition_overflow_and_rate_limit_are_explicit():
    a=setup();a['rain_mm'][0]=20;a['pond_mask'][0]=True
    r=field_year(**a,pond_capacity_mm=10,infiltration_mm_day=60.)
    assert r['infiltration_mm'][0,0]==5 and r['pond_mm'][0,0]==10
    assert r['surface_overflow_mm'][0,0]==1 and r['rain_excluded_mm'][0,0]==4
    check_balance(a,r)


def test_empty_initial_state_with_no_water_never_creates_et():
    a=setup();a['crop_mask'][:]=True;a['eto_mm_day'][:]=5
    r=periodic_fields(**a)
    assert r['periodic'] and r['years']==1 and not r['root_uptake_mm'].any()
    check_balance(a,r)


def test_nonconvergence_is_reported():
    a=setup();a['rain_mm'][:]=1
    r=periodic_fields(**a,max_years=1)
    assert not r['periodic'] and r['periodic_residual_mm']>0


@pytest.mark.parametrize('kind',['overlap','nonbool','badnode','badsource','badarea','badefficiency'])
def test_invalid_bindings_and_forcing_are_refused(kind):
    a=setup();extra={}
    if kind=='overlap':a['crop_mask'][:]=True;a['pond_mask'][:]=True
    if kind=='nonbool':a['capture_mask']=np.ones_like(a['rain_mm'])
    if kind=='badnode':a['field_nodes'][:]=1
    if kind=='badsource':a['source_m3'][:]=-1
    if kind=='badarea':a['area_m2'][:]=0
    if kind=='badefficiency':extra['efficiency']=0
    with pytest.raises(ValueError):field_year(**a,**extra)
