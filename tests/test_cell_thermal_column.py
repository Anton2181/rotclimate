"""Cell thermal hydrostatic adjoints, analytical dispersion and visible null energy."""
import numpy as np
import pytest
from rotclimate.cell_thermal_column import build_cell_thermal_column
from rotclimate.lapse_reference import lapse_reference


def irregular_column():
    edges=np.array([0.,300.,1000.,2400.,4500.,8000.,12000.,16000.])
    ref=lapse_reference(.5*(edges[:-1]+edges[1:]),surface_temperature_k=292.)
    return build_cell_thermal_column(edges,ref.density_kg_m3,ref.stability_s2)


@pytest.mark.parametrize('n',[4,8,16,32,128,256])
def test_uniform_column_matches_independent_lorenz_grid_dispersion(n):
    dz=500.;freq=.01;col=build_cell_thermal_column(np.arange(n+1)*dz,np.ones(n),np.full(n,freq**2))
    k=np.arange(1,n);expected=freq*dz/(2*np.tan(k*np.pi/(2*n)))
    np.testing.assert_allclose(col.phase_speeds_ms,expected,rtol=2e-11)
    np.testing.assert_allclose(col.hydrostatic_matrix@col.cell_buoyancy_modes,col.pressure_modes,rtol=1e-10,atol=1e-10)


def test_actual_unequal_grid_pressure_work_cancels_thermal_energy_tendency():
    col=irregular_column();rng=np.random.default_rng(57);shape=(len(col.centers_m),3,4)
    b=rng.normal(scale=.005,size=shape);div=rng.normal(scale=1e-5,size=shape)
    mass=col.cell_mass_kg_m2[:,None,None];div-=np.sum(mass*div,axis=0,keepdims=True)/col.total_mass
    p=col.pressure_from_buoyancy(b);tendency=col.adiabatic_buoyancy_tendency(div)
    pressure_work=np.sum(mass*div*p,axis=0)
    thermal_work=np.sum(col.thermal_energy_weight[:,None,None]*b*tendency,axis=0)
    np.testing.assert_allclose(pressure_work+thermal_work,0,atol=2e-14)
    # Independent hydrostatic integral with linearly interpolated buoyancy.
    expected=(col.interface_interpolation@b.reshape(shape[0],-1)).reshape((shape[0]-1,3,4))
    np.testing.assert_allclose(np.diff(p,axis=0)/np.diff(col.centers_m)[:,None,None],expected,atol=2e-17)
    np.testing.assert_allclose(np.sum(mass*p,axis=0),0,atol=1e-10)


def test_uniform_grid_adiabatic_update_is_adjacent_vertical_velocity_mean():
    n=8;col=build_cell_thermal_column(np.arange(n+1)*1000.,np.ones(n),np.full(n,.0001))
    interfaces=np.r_[0.,np.sin(np.arange(1,n)*np.pi/n),0.]
    div=-np.diff(interfaces)/1000.
    np.testing.assert_allclose(col.vertical_velocity(div),interfaces[1:-1],atol=1e-15)
    np.testing.assert_allclose(col.adiabatic_buoyancy_tendency(div),-.0001*.5*(interfaces[:-1]+interfaces[1:]),atol=1e-18)


def test_pressure_invisible_checkerboard_is_exposed_and_energy_is_partitioned():
    col=irregular_column();null=col.pressure_invisible_thermal_mode
    np.testing.assert_allclose(col.pressure_from_buoyancy(null),0,atol=1e-12)
    pure=col.energy_partition(null)
    assert pure['pressure_invisible_available_energy_m2_s2']==pytest.approx(.5,abs=1e-12)
    assert pure['pressure_active_available_energy_m2_s2']<1e-20
    mixed=2.3*col.cell_buoyancy_modes[:,0]+.7*null;parts=col.energy_partition(mixed)
    assert parts['pressure_active_available_energy_m2_s2']==pytest.approx(.5*(2.3/col.phase_speeds_ms[0])**2,rel=1e-10)
    assert parts['pressure_invisible_available_energy_m2_s2']==pytest.approx(.5*.7**2,abs=1e-12)
    assert abs(parts['partition_residual_m2_s2'])<1e-12


def test_adiabatic_motion_does_not_silently_generate_or_remove_null_amplitude():
    col=irregular_column();div=np.linspace(-1e-5,1e-5,len(col.centers_m))
    div-=np.dot(col.cell_mass_kg_m2,div)/col.total_mass
    tendency=col.adiabatic_buoyancy_tendency(div)
    work=np.dot(col.thermal_energy_weight*col.pressure_invisible_thermal_mode,tendency)
    assert abs(work)<1e-14


def test_open_column_or_nonpositive_reference_is_rejected():
    col=irregular_column()
    with pytest.raises(ValueError):col.vertical_velocity(np.ones(len(col.centers_m)))
    with pytest.raises(ValueError):build_cell_thermal_column([0,1,2],[1,1],[.001,-.001])
