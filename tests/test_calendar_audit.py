import numpy as np

from harvest.calendar_audit import calendar_origin_audit
from scripts.land_people import crop_yield


def crop(length, grain=1.):
    return dict(window=(10.,30.),base=0.,heat=1.,months=(length,length),
                kc=1.,ky=1.,grain=grain,edible=1.,kcal=1.,seed=0.,need_warm=10.)


def test_tied_seasons_can_hide_a_feasible_second_crop_without_changing_yields():
    t=np.full((12,2),20.);p=np.full_like(t,100.);soil=np.zeros_like(t)
    result=calendar_origin_audit(t,p,p,soil,1.,[True,False],crops={'a':crop(4),'b':crop(3)})
    # The legacy first-choice masks overlap; alternative tied masks fit.
    np.testing.assert_allclose(result.original_total,1000.)
    np.testing.assert_allclose(result.attainable_tied_total,[1500.,1000.])
    np.testing.assert_allclose(result.rotation_minimum,result.rotation_maximum)
    assert result.crop_mask_varies['a'].all() and result.maximum_crop_yield_drift==0


def test_single_crop_does_not_silently_gain_an_extra_same_crop_harvest():
    t=np.full(12,20.);p=np.full(12,100.)
    r=calendar_origin_audit(t,p,p,p,1.,True,crops={'a':crop(3)})
    assert r.original_total==r.attainable_tied_total==1000


def test_unique_season_across_year_boundary_is_mapped_back_correctly():
    t=np.zeros(12);t[[10,11,0]]=20.;p=np.full(12,100.)
    r=calendar_origin_audit(t,p,p,p,1.,True,crops={'a':crop(3),'b':crop(3,.8)})
    assert not r.crop_mask_varies['a']
    assert not r.crop_mask_varies['b']
    assert r.attainable_tied_total==r.original_total==1000


def test_perennials_do_not_enter_second_crop_pairs_and_inputs_are_preserved():
    t=np.full((12,1),20.);p=np.full_like(t,100.);before=t.copy()
    r=calendar_origin_audit(t,p,p,p,1.,True,perennial_kcal=[2000.],crops={'a':crop(3),'b':crop(3)})
    np.testing.assert_allclose(r.attainable_tied_total,2000.)
    np.testing.assert_array_equal(t,before)


def test_audit_preserves_production_float32_irrigation_arithmetic():
    t=np.full((12,1),20.);p=np.full_like(t,40.);pet=np.full_like(t,100.)
    irr=np.array([.123456789],dtype=np.float32)
    expected,_=crop_yield(t,p,pet,np.zeros_like(t),irr,crop(4))
    result=calendar_origin_audit(t,p,pet,np.zeros_like(t),irr,False,crops={'a':crop(4)})
    np.testing.assert_array_equal(result.original_total,expected)
