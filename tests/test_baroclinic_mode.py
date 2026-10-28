"""Analytic periodic wave solutions, energy identity and heating convergence."""
import numpy as np
import pytest
from rotclimate.baroclinic_mode import solve_mode


@pytest.mark.parametrize('f',[0.,7e-5,-7e-5])
def test_single_fourier_wave_matches_independent_c_grid_dispersion(f):
    ny,nx=9,24;dx=100000.;c=50.;r=1/(5*86400.);rt=1/(20*86400.)
    phase=2*np.pi*np.arange(nx)/nx;phi=120*np.cos(phase)[None]*np.ones((ny,1))
    kd=2*np.sin(np.pi/nx)/dx;interpolation=np.cos(np.pi/nx)
    response=r/(r*r+f*f*interpolation**2)
    forcing=(rt+c*c*kd*kd*response)*phi
    result=solve_mode(forcing,dx,f,wave_speed_ms=c,momentum_drag_s=r,thermal_drag_s=rt)
    expected_u=120*kd*response*np.sin(phase+np.pi/nx)[None]*np.ones((ny,1))
    expected_v=f*interpolation/r*120*kd*response*np.sin(phase)[None]*np.ones((ny,1))
    np.testing.assert_allclose(result.geopotential,phi,atol=3e-10,rtol=1e-10)
    np.testing.assert_allclose(result.u_east,expected_u,atol=3e-10,rtol=1e-10)
    np.testing.assert_allclose(result.v_south,expected_v,atol=3e-10,rtol=1e-10)


def test_uniform_heating_has_relaxation_balance_without_spurious_motion():
    q=np.full((7,11),.001);c=50.;r=1/(5*86400.);rt=1/(20*86400.)
    out=solve_mode(q,100000.,7e-5,wave_speed_ms=c,momentum_drag_s=r,thermal_drag_s=rt)
    np.testing.assert_allclose(out.geopotential,q/rt,atol=1e-8,rtol=1e-10)
    assert np.hypot(out.u_east,out.v_south).max()<1e-10


def test_variable_rotation_keeps_energy_and_integral_thermal_balance():
    j,i=np.mgrid[:11,:17];q=.001*np.cos(2*np.pi*i/17)*np.sin(2*np.pi*j/11)+.0001
    f=7e-5+1e-5*np.sin(2*np.pi*i/17)*np.cos(2*np.pi*j/11)
    c=50.;r=1/(5*86400.);rt=1/(20*86400.)
    out=solve_mode(q,100000.,f,wave_speed_ms=c,momentum_drag_s=r,thermal_drag_s=rt)
    diss=np.mean(r*(out.u_east**2+out.v_south**2)+rt*(out.geopotential/c)**2)
    supply=np.mean(out.geopotential*q/c**2)
    assert diss==pytest.approx(supply,rel=1e-11)
    assert rt*out.geopotential.mean()==pytest.approx(q.mean(),rel=1e-11)
    assert out.certificate['relative_modal_energy_error']<1e-11


def test_heating_drives_lower_convergence_with_balanced_upper_return():
    j,i=np.mgrid[:21,:25];q=np.exp(-((i-12)**2+(j-10)**2)/10)*.001;q-=q.mean()
    out=solve_mode(q,100000.,7e-5,wave_speed_ms=50.,momentum_drag_s=1/(5*86400.),thermal_drag_s=1/(20*86400.))
    # Row increases south; pressure/thickness mode divergence is positive above
    # heating, hence lower-layer flow(-.75*mode) converges there.
    div=(out.u_east-np.roll(out.u_east,1,axis=1)+out.v_south-np.roll(out.v_south,1,axis=0))/100000.
    assert div[10,12]>0
    lower_u,upper_u=-.75*out.u_east,.25*out.u_east
    lower_v,upper_v=-.75*out.v_south,.25*out.v_south
    np.testing.assert_array_equal(.25*lower_u+.75*upper_u,0.)
    np.testing.assert_array_equal(.25*lower_v+.75*upper_v,0.)
    assert abs(div.mean())<1e-20


@pytest.mark.parametrize('changes',[{'wave_speed_ms':0},{'momentum_drag_s':0},{'thermal_drag_s':-1}])
def test_invalid_mode_rejected(changes):
    args=dict(wave_speed_ms=50.,momentum_drag_s=1e-6,thermal_drag_s=1e-6);args.update(changes)
    with pytest.raises(ValueError):solve_mode(np.zeros((4,5)),100000.,7e-5,**args)
