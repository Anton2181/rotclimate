"""Independent vertical integrals and physical first-mode energy/work pairing."""
import numpy as np
import pytest
from scipy.integrate import quad
from rotclimate.baroclinic_heating import project_first_mode
from rotclimate.column_thermodynamics import CP,G

ARGS=dict(depth_m=15000.,buoyancy_frequency_s=.01,reference_temperature_k=275.)


def test_uniform_specific_heating_has_exact_sine_coefficient_and_derived_wave_speed():
    mass=np.array(9000.);edges=np.array([0.,.25,1.]);specific=.003
    heat=mass*np.diff(edges)*specific
    out=project_first_mode(heat,mass,edges,**ARGS)
    expected=4/np.pi*G*specific/(CP*275.)
    assert out.buoyancy_forcing_amplitude_m_s3==pytest.approx(expected,rel=1e-14)
    assert out.wave_speed_ms==pytest.approx(.01*15000/np.pi,rel=1e-14)
    assert out.column_heating_w_m2==pytest.approx(9000*specific)
    assert out.captured_buoyancy_forcing_norm_fraction==pytest.approx(8/np.pi**2,rel=1e-14)


@pytest.mark.parametrize('a',[.2,.25,.5])
def test_layer_average_velocities_match_direct_cosine_integrals(a):
    out=project_first_mode(np.array([10.,20.]),np.array(9000.),[0.,a,1.],lower_fraction=a,**ARGS)
    lower=quad(lambda s:-np.cos(np.pi*s),0,a)[0]/a
    upper=quad(lambda s:-np.cos(np.pi*s),a,1)[0]/(1-a)
    assert -(1-a)*out.velocity_scale==pytest.approx(lower,rel=1e-13)
    assert a*out.velocity_scale==pytest.approx(upper,rel=1e-13)
    assert a*lower+(1-a)*upper==pytest.approx(0.,abs=1e-15)


def test_projection_and_energy_work_match_independent_continuous_integrals():
    edges=np.array([0.,.2,.45,.7,1.]);mass=np.array(9000.)
    heat=np.array([-30.,50.,80.,-10.]);phi_scaled=80.
    out=project_first_mode(heat,mass,edges,**ARGS)
    specific=heat/(mass*np.diff(edges))
    source=lambda k:G*specific[k]/(CP*275.)
    coefficient=2*sum(quad(lambda s:source(k)*np.sin(np.pi*s),left,right)[0]
                      for k,(left,right) in enumerate(zip(edges[:-1],edges[1:])))
    assert out.buoyancy_forcing_amplitude_m_s3==pytest.approx(coefficient,rel=1e-13)
    m=np.pi/15000.;phi_amp=phi_scaled/out.velocity_scale
    physical_work=sum(quad(lambda s: m*phi_amp*np.sin(np.pi*s)*source(k)/.01**2,left,right)[0]
                      for k,(left,right) in enumerate(zip(edges[:-1],edges[1:])))
    projected_work=out.physical_modal_energy_factor*phi_scaled*out.forcing_m2_s3/out.wave_speed_ms**2
    assert projected_work==pytest.approx(physical_work,rel=1e-13)
    # Independent vertical integral of kinetic and available potential energy.
    u,v=3./out.velocity_scale,2./out.velocity_scale
    physical_energy=.5*quad(lambda s:(u*u+v*v)*np.cos(np.pi*s)**2
                               +(m*phi_amp*np.sin(np.pi*s))**2/.01**2,0,1)[0]
    scaled_energy=out.physical_modal_energy_factor*.5*(3**2+2**2+(phi_scaled/out.wave_speed_ms)**2)
    assert scaled_energy==pytest.approx(physical_energy,rel=1e-13)


def test_zero_column_heat_does_not_hide_heating_dipole_or_unresolved_modes():
    out=project_first_mode(np.array([-40.,40.]),np.array(9000.),[0.,.25,1.],**ARGS)
    assert out.column_heating_w_m2==0
    assert out.forcing_m2_s3>0
    assert 0<out.captured_buoyancy_forcing_norm_fraction<1


def test_symmetric_cancelling_heat_has_zero_first_mode_but_nonzero_full_heating():
    out=project_first_mode(np.array([-40.,40.]),np.array(9000.),[0.,.5,1.],lower_fraction=.5,**ARGS)
    assert abs(out.forcing_m2_s3)<1e-17
    assert out.captured_buoyancy_forcing_norm_fraction<1e-30


@pytest.mark.parametrize('changes',[dict(depth_m=0),dict(buoyancy_frequency_s=0),dict(reference_temperature_k=-1),dict(lower_fraction=1)])
def test_invalid_mode_rejected(changes):
    args=dict(ARGS);args.update(changes)
    with pytest.raises(ValueError):project_first_mode(np.array([10.,20.]),np.array(9000.),[0.,.25,1.],**args)
