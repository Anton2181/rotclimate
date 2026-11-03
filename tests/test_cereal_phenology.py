import numpy as np
import pytest

from harvest.phenology import (CerealParameters,cereal_development,
                                photoperiod_factor,vernalization_effectiveness)


def test_published_chilling_temperature_breakpoints_and_warm_cold_limits():
    np.testing.assert_allclose(vernalization_effectiveness([-10,-4,-.5,3,7,10,13.5,17,30]),
                               [0,0,.5,1,1,1,.5,0,0])


def test_spring_clock_reproduces_an_analytic_degree_day_sum_and_stops_at_maturity():
    r=cereal_development(np.full(100,20.),12,CerealParameters(1500),record=True)
    assert r.maturity_days==75 and r.heat_accumulated==1500 and r.fraction==1
    assert np.all(r.fraction_path[75:]==1) and r.vernalization_accumulated==0


def test_winter_variety_requires_effective_chilling_but_tolerates_dormant_cold_days():
    p=CerealParameters(100,vernalization_days=30)
    warm=cereal_development(np.full(100,20.),12,p)
    assert warm.maturity_days==-1 and warm.fraction==0
    t=np.r_[np.full(30,-10.),np.full(30,5.),np.full(100,20.)]
    winter=cereal_development(t,12,p,record=True)
    assert winter.maturity_days>30 and winter.fraction==1
    assert np.all(winter.fraction_path[:31]==0)
    assert winter.vernalization_accumulated>=30


def test_pvd_ten_and_zero_have_defined_nonsingular_behavior():
    with np.errstate(all='raise'):
        r=cereal_development(np.full(15,5.),12,CerealParameters(100,vernalization_days=10),record=True)
        assert np.all(r.fraction_path[:10]==0) and r.fraction_path[10]>0
        assert np.isfinite(r.fraction_path).all()
        assert cereal_development([20.],12,CerealParameters(20)).maturity_days==1


def test_photoperiod_parameter_convention_and_release_after_senescence():
    p=CerealParameters(100,photoperiod_floor=0,photoperiod_base_hours=8,photoperiod_saturation_hours=16)
    np.testing.assert_allclose(photoperiod_factor([6,8,12,16,20],p),[0,0,.5,1,1])
    assert cereal_development(np.full(20,20.),6,p).maturity_days==-1
    t=np.full(10,20.);light=np.r_[np.full(4,16.),np.full(6,6.)]
    assert cereal_development(t,light,p).maturity_days==5
    assert np.all(photoperiod_factor([0,12,24],CerealParameters(100))==1)


def test_vector_cells_equal_separate_runs_without_changing_forcing():
    rng=np.random.default_rng(505);t=rng.uniform(-10,25,(365,4));original=t.copy()
    p=CerealParameters(700,vernalization_days=30)
    allcells=cereal_development(t,12,p)
    for i in range(4):
        single=cereal_development(t[:,i],12,p)
        assert single.maturity_days==allcells.maturity_days[i]
        assert single.heat_accumulated==allcells.heat_accumulated[i]
    np.testing.assert_array_equal(t,original)


def test_vector_cultivar_fields_match_separately_parameterized_clocks():
    t=np.broadcast_to(np.r_[np.full(45,5.),np.full(320,20.)][:,None],(365,3))
    heat=[500,1000,1500];chill=[0,30,60]
    allcells=cereal_development(t,12,CerealParameters(1000),heat_units=heat,vernalization_days=chill)
    for i in range(3):
        single=cereal_development(t[:,i],12,CerealParameters(heat[i],vernalization_days=chill[i]))
        assert allcells.maturity_days[i]==single.maturity_days


@pytest.mark.parametrize('kwargs',[{'heat_units':0},{'heat_units':100,'vernalization_days':61},
    {'heat_units':100,'photoperiod_floor':-1},{'heat_units':100,'photoperiod_base_hours':16}])
def test_invalid_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):CerealParameters(**kwargs)
