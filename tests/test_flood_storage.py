import numpy as np
import pytest
from harvest.flood_storage import periodic_storage,storage_year


def inputs(n=1):
    return [np.zeros((12,n)),np.zeros((12,n)),np.zeros((12,n)),np.ones(n)*1000,np.zeros(n,dtype=int),np.zeros((12,1)),[0],[-1]]


def check_balance(a,r):
    rain=a[0];area=a[3]/1000
    np.testing.assert_allclose(r['start_mm']+rain+r['delivered_mm'],r['end_mm']+r['crop_et_actual_mm']+r['bare_et_actual_mm']+r['rain_spill_mm']+r['rain_excluded_mm'],atol=1e-11)
    np.testing.assert_allclose((r['delivered_mm']*area).sum(1),r['river_delivered_m3'].sum(1),atol=1e-11)
    np.testing.assert_allclose(a[5].sum(1),(r['river_delivered_m3']+r['river_loss_m3']+r['river_outlet_m3']).sum(1),atol=1e-11)


def test_flood_is_carried_into_later_crop_month():
    a=inputs();a[5][9,0]=50;a[1][10,0]=30;a[1][11,0]=30;capture=np.zeros((12,1),bool);capture[9]=True
    r=storage_year(*a,capacity_mm=50,capture_mask=capture)
    assert r['crop_et_actual_mm'][10:,0].tolist()==[30,20] and r['end_mm'][9,0]==50;check_balance(a,r)


def test_shared_source_is_not_reused_for_each_field():
    a=inputs(2);a[3]=np.array([1000,3000.]);a[5][0,0]=100
    r=storage_year(*a,capacity_mm=100,capture_mask=np.ones((12,2),bool),efficiency=.5)
    np.testing.assert_allclose(r['delivered_mm'][0],[12.5,12.5]);assert r['river_loss_m3'][0,0]==50;check_balance(a,r)


def test_monthly_rain_overflow_is_paid_before_capture_and_et():
    a=inputs();a[0][0]=100;a[1][0]=20;a[5][0]=100
    r=storage_year(*a,capacity_mm=50,capture_mask=np.ones((12,1),bool))
    assert r['rain_spill_mm'][0,0]==30 and r['rain_excluded_mm'][0,0]==20
    assert r['delivered_mm'][0,0]==0 and r['end_mm'][0,0]==30;check_balance(a,r)


def test_no_river_and_no_rain_cannot_create_crop_water():
    a=inputs();a[1][:]=10
    r=periodic_storage(*a,capacity_mm=600,capture_mask=np.ones((12,1),bool))
    assert r['periodic'] and r['years']==1 and not r['crop_et_actual_mm'].any();check_balance(a,r)


def test_capture_mask_and_bare_evaporation_are_real_constraints():
    a=inputs();a[5][0]=100;a[2][0]=40;a[1][1]=100
    cap=np.zeros((12,1),bool);cap[0]=True
    r=storage_year(*a,capacity_mm=100,capture_mask=cap)
    assert r['crop_et_actual_mm'][1,0]==60 and r['bare_et_actual_mm'][0,0]==40
    no=storage_year(*a,capacity_mm=100,capture_mask=np.zeros((12,1),bool))
    assert not no['crop_et_actual_mm'].any();check_balance(a,r)


def test_periodic_initial_water_has_a_paid_spinup_history():
    a=inputs();a[5][10]=100;a[1][0]=60;cap=np.zeros((12,1),bool);cap[10]=True
    first=storage_year(*a,capacity_mm=100,capture_mask=cap)
    assert first['crop_et_actual_mm'][0,0]==0
    periodic=periodic_storage(*a,capacity_mm=100,capture_mask=cap)
    assert periodic['periodic'] and periodic['years']==2
    assert periodic['initial_mm'][0]==100 and periodic['crop_et_actual_mm'][0,0]==60;check_balance(a,periodic)


def test_nonconvergence_is_explicit():
    a=inputs();a[0][0]=1
    r=periodic_storage(*a,capacity_mm=600,capture_mask=np.zeros((12,1),bool),max_years=2)
    assert not r['periodic'] and r['years']==2 and r['periodic_residual_mm']>.7


def test_rotation_of_periodic_climate_preserves_rotated_fluxes():
    a=inputs();a[5][9]=100;a[1][10:]=50;a[1][:3]=10
    cap=np.zeros((12,1),bool);cap[9]=True
    r=periodic_storage(*a,capacity_mm=100,capture_mask=cap)
    b=[np.roll(v,4,axis=0) if i in (0,1,2,5) else v for i,v in enumerate(a)]
    s=periodic_storage(*b,capacity_mm=100,capture_mask=np.roll(cap,4,axis=0))
    for k in ('crop_et_actual_mm','delivered_mm','end_mm'):np.testing.assert_allclose(s[k],np.roll(r[k],4,axis=0))


@pytest.mark.parametrize('change',[
    lambda a:a.__setitem__(0,np.zeros((11,1))),lambda a:a[0].__setitem__((0,0),-1),
    lambda a:a[1].__setitem__((0,0),np.inf),lambda a:a.__setitem__(3,np.array([0.])),
    lambda a:a.__setitem__(4,np.array([1])),lambda a:a.__setitem__(4,np.array([0.])),
])
def test_invalid_field_inputs_refused(change):
    a=inputs();change(a)
    with pytest.raises(ValueError):storage_year(*a,capacity_mm=100,capture_mask=np.ones((12,1),bool))


def test_invalid_storage_and_overlapping_et_refused():
    a=inputs()
    for cap,initial in [(-1,0),(100,101),(100,np.nan)]:
        with pytest.raises(ValueError):storage_year(*a,capacity_mm=cap,initial_mm=initial,capture_mask=np.ones((12,1),bool))
    a[1][0]=1;a[2][0]=1
    with pytest.raises(ValueError):storage_year(*a,capacity_mm=100,capture_mask=np.ones((12,1),bool))
