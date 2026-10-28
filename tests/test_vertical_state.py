"""Independent hydrostatics, discrete normal modes, work and continuity."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import CP,G,RD
from rotclimate.vertical_state import build_vertical_state,stable_reference,virtual_potential_buoyancy


def uniform(n=16):
    return build_vertical_state(np.linspace(0,15000,n+1),np.ones(n),np.full(n-1,.01**2))


def test_reference_obeys_ideal_gas_hydrostatics_and_exact_constant_N():
    z=np.linspace(0,15000,151);out=stable_reference(z)
    np.testing.assert_allclose(out.pressure_pa,out.density_kg_m3*RD*out.temperature_k,rtol=1e-14)
    np.testing.assert_allclose(G*np.diff(np.log(out.potential_temperature_k))/np.diff(z),.01**2,rtol=1e-11)
    # Exact integral theta^-1 rather than finite-difference air density.
    pi=out.pressure_pa**(RD/CP)/100000.**(RD/CP)
    exact=-G*G/(CP*300*.01**2)*(np.exp(-.01**2*z[:-1]/G)-np.exp(-.01**2*z[1:]/G))
    np.testing.assert_allclose(np.diff(pi),exact,rtol=1e-10,atol=1e-14)
    np.testing.assert_allclose(virtual_potential_buoyancy(out.temperature_k,out.pressure_pa,0.,out.potential_temperature_k),0.,atol=1e-13)


@pytest.mark.parametrize('n',[2,8,32])
def test_uniform_column_modes_match_independent_discrete_cosines(n):
    col=uniform(n);k=np.arange(1,n);dz=15000/n
    expected=.01*dz/(2*np.sin(k*np.pi/(2*n)))
    np.testing.assert_allclose(col.phase_speeds_ms,expected,rtol=2e-12)
    shape=-np.sqrt(2)*np.cos((np.arange(n)[:,None]+.5)*k[None]*np.pi/n)
    np.testing.assert_allclose(col.pressure_modes,shape,atol=2e-11,rtol=1e-10)


def test_refinement_converges_to_continuous_first_mode_wave_speed():
    target=.01*15000/np.pi
    errors=[abs(uniform(n).phase_speeds_ms[0]-target) for n in [8,16,32]]
    assert errors[1]<.26*errors[0] and errors[2]<.26*errors[1]


def test_hydrostatic_pressure_reconstructs_buoyancy_and_fixes_mass_gauge():
    z=np.array([0.,1000.,3000.,6500.,11000.,15000.]);rho=np.exp(-.5*(z[:-1]+z[1:])/8000.)
    col=build_vertical_state(z,rho,np.array([.008,.01,.015,.012])**2)
    b=np.array([.001,-.002,.004,.003]);p=col.pressure_from_buoyancy(b)
    np.testing.assert_allclose(np.diff(p)/np.diff(col.centers_m),b,rtol=1e-14,atol=1e-15)
    assert np.dot(p,col.cell_mass_kg_m2)==pytest.approx(0.,abs=1e-10)
    np.testing.assert_allclose(col.pressure_from_amplitudes(col.project_pressure(p)),p,atol=1e-12,rtol=1e-12)


def test_variable_density_stability_continuity_and_pressure_work_are_negative_adjoints():
    edges=np.array([0.,700.,2000.,4000.,7500.,11000.,15000.]);centers=.5*(edges[:-1]+edges[1:])
    col=build_vertical_state(edges,np.exp(-centers/8000.),np.array([.008,.01,.014,.013,.018])**2)
    rng=np.random.default_rng(31);div=rng.normal(size=(6,4,5))*1e-6
    mass=col.cell_mass_kg_m2[:,None,None];div-=np.sum(mass*div,axis=0)/mass.sum()
    b=rng.normal(size=(5,4,5))*.001;p=col.pressure_from_buoyancy(b);w=col.vertical_velocity(div)
    # Independent cumulative mass continuity and summation by parts.
    flux=np.zeros((7,4,5));flux[1:]=-np.cumsum(mass*div,axis=0)
    np.testing.assert_allclose(flux[-1],0.,atol=1e-17)
    np.testing.assert_allclose(w*col.interface_density_kg_m3[:,None,None],flux[1:-1],atol=1e-17)
    pressure_work=np.sum(mass*p*div,axis=0)
    potential_change=-np.sum(col.interface_density_kg_m3[:,None,None]*np.diff(centers)[:,None,None]*b*w,axis=0)
    np.testing.assert_allclose(pressure_work,-potential_change,rtol=1e-12,atol=1e-17)


def test_modal_adiabatic_response_matches_state_thermodynamics_and_continuity():
    col=uniform(24);rng=np.random.default_rng(5);divamp=rng.normal(size=23)*1e-6
    div=col.pressure_modes@divamp;w=col.vertical_velocity(div)
    bdot=-col.interface_stability_s2*w
    state_phi_dot=col.project_pressure(col.pressure_from_buoyancy(bdot))
    np.testing.assert_allclose(state_phi_dot,-col.phase_speeds_ms**2*divamp,rtol=1e-11,atol=1e-13)


def test_buoyancy_heating_projection_preserves_actual_work_for_arbitrary_state():
    col=uniform(20);rng=np.random.default_rng(7);amp=rng.normal(size=19)*20
    b=col.buoyancy_modes@amp;q=rng.normal(size=19)*1e-7
    forcing=col.project_buoyancy_source(q)
    actual=np.sum(col.interface_energy_weight*b*q)/col.total_mass
    projected=np.sum(amp*forcing/col.phase_speeds_ms**2)
    assert actual==pytest.approx(projected,rel=1e-12,abs=1e-16)


def test_virtual_buoyancy_uses_dry_mixing_ratio_not_specific_humidity():
    t,p,r,theta0=290.,90000.,.01,300.
    expected=G*(t*(1+r/.622)/(1+r)*(100000/p)**(RD/CP)/theta0-1)
    assert virtual_potential_buoyancy(t,p,r,theta0)==pytest.approx(expected,rel=1e-14)


@pytest.mark.parametrize('n2',[0.,-1e-4,np.nan])
def test_unstable_or_nonfinite_background_is_rejected_without_clipping(n2):
    with pytest.raises(ValueError):build_vertical_state(np.linspace(0,15000,9),np.ones(8),np.full(7,n2))


def test_rigid_lid_does_not_accept_external_column_air_source():
    col=uniform(8)
    with pytest.raises(ValueError):col.vertical_velocity(np.ones(8)*1e-6)
