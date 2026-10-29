import numpy as np
import pytest
from scipy.integrate import quad
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_pressure_gradient import common_pressure_force,_mean_log_pressure
from rotclimate.terrain_apertures import horizontal_apertures
from rotclimate.column_thermodynamics import G,RD


def test_hydrostatic_rest_over_steep_mountains_has_no_spurious_wind_force():
    h=np.array([[0,4500,1000],[6000,-200,3000.]])
    for lapse in [0.,.0065,.0098]:
        ps=surface_pressure_from_height(h,300.,lapse_k_m=lapse);grid=terrain_pressure_grid(ps,[1,.98,.9,.65,.3,0],top_pressure_pa=30000.)
        result=common_pressure_force(grid,h,np.zeros_like(grid.dry_mass_kg_m2),56000.,reference_temperature_k=300.,reference_lapse_k_m=lapse)
        assert max(abs(result.east_ms2).max(),abs(result.south_ms2).max())<1e-14


def test_flat_uniform_warming_does_not_generate_pressure_gradients():
    grid=terrain_pressure_grid(np.full((3,4),101325.),[1,.9,.5,0]);delta=np.broadcast_to(np.array([2.,-1.,3.])[:,None,None],grid.dry_mass_kg_m2.shape)
    result=common_pressure_force(grid,np.zeros((3,4)),delta,224000.)
    assert not result.east_ms2.any() and not result.south_ms2.any()


def test_flat_warm_neighbor_has_analytic_aloft_pressure_force():
    ps=101325.;pt=38000.;grid=terrain_pressure_grid(np.full((2,2),ps),[1,0],top_pressure_pa=pt);delta=np.zeros_like(grid.dry_mass_kg_m2);delta[:,:,1]=2.
    result=common_pressure_force(grid,np.zeros((2,2)),delta,100000.)
    mean_log=quad(np.log,pt,ps,epsabs=1e-5)[0]/(ps-pt);expected=-RD*2*(np.log(ps)-mean_log)/100000.
    np.testing.assert_allclose(result.east_ms2,expected,rtol=2e-13)
    assert not result.south_ms2.any()


def test_mountain_layer_pair_matches_independent_hydrostatic_pressure_integral():
    h=np.array([[0.,3000.],[500.,2000.]]);ps=surface_pressure_from_height(h,288.15);grid=terrain_pressure_grid(ps,[1,.7,.3,0]);delta=np.array([[[1.,-2.],[3.,1.]],[[0.,2.],[1.,-1.]],[[3.,0.],[0.,2.]]]);p=grid.edges_pa;dx=224000.
    result=common_pressure_force(grid,h,delta,dx)
    def phi_anomaly(pressure,y,x):
        # Independent direct hydrostatic integration across every lower layer.
        value=0.
        for k in range(3):
            lo=max(pressure,p[k+1,y,x]);hi=p[k,y,x]
            if hi>lo:value+=quad(lambda q:RD*delta[k,y,x]/q,lo,hi,epsabs=1e-9)[0]
        return value
    for left in range(3):
        for right in range(3):
            bottom=min(p[left,0,0],p[right,0,1]);top=max(p[left+1,0,0],p[right+1,0,1])
            if bottom<=top:assert result.east_ms2[left,right,0,0]==0;continue
            expected=quad(lambda q:(phi_anomaly(q,0,0)-phi_anomaly(q,0,1))/dx,top,bottom,epsabs=1e-8)[0]/(bottom-top)
            assert result.east_ms2[left,right,0,0]==pytest.approx(expected,abs=3e-15)


def test_neighbor_reversal_changes_force_sign_and_transposes_levels():
    h=np.array([[0.,1000.,4000.],[2000.,500.,3000.]]);ps=surface_pressure_from_height(h,288.15);a=terrain_pressure_grid(ps,[1,.8,.3,0]);b=terrain_pressure_grid(ps[:,::-1],[1,.8,.3,0]);delta=np.arange(18.).reshape(3,2,3)*.1
    fa=common_pressure_force(a,h,delta,56000.);fb=common_pressure_force(b,h[:,::-1],delta[:,:,::-1],56000.)
    np.testing.assert_allclose(fa.east_ms2,-fb.east_ms2.transpose(1,0,2,3)[:,:,:,::-1],atol=1e-16)


def test_thin_pressure_intervals_remain_accurate_and_finite():
    top=np.array([100000.,100000.,38000.]);bottom=top+np.array([1e-6,.1,20000.]);mean=_mean_log_pressure(bottom,top)
    for lo,hi,value in zip(top,bottom,mean):assert value==pytest.approx(quad(np.log,lo,hi,epsabs=1e-8)[0]/(hi-lo),abs=3e-14)
    assert np.isfinite(_mean_log_pressure(top,top)).all()


def test_bad_states_and_reference_shape_are_rejected():
    grid=terrain_pressure_grid(np.ones((2,2))*101325,[1,0]);zero=np.zeros_like(grid.dry_mass_kg_m2)
    with pytest.raises(ValueError):common_pressure_force(grid,np.zeros((2,2)),zero,0.)
    with pytest.raises(ValueError):common_pressure_force(grid,np.zeros((2,2)),zero,1.,reference_temperature_k=np.ones((2,2))*288.15)
    with pytest.raises(ValueError):common_pressure_force(grid,np.zeros((2,2)),zero+np.nan,1.)
