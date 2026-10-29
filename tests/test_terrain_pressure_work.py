import numpy as np
import pytest
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_apertures import horizontal_apertures,mass_flux_divergence
from rotclimate.terrain_pressure_gradient import common_pressure_force
from rotclimate.terrain_pressure_work import project_column_mass,compression_power


def case(seed=31):
    rng=np.random.default_rng(seed);height=rng.uniform(-100,4500,(3,4));ps=surface_pressure_from_height(height,288.15);grid=terrain_pressure_grid(ps,[1,.9,.65,.3,0]);a=horizontal_apertures(grid);u=rng.normal(size=a.east_kg_m2.shape);v=rng.normal(size=a.south_kg_m2.shape)
    return rng,height,grid,a,u,v


def test_projection_closes_every_actual_column_without_adding_heat():
    _,_,grid,a,u,v=case();original_u=u.copy();original_v=v.copy();ue,vs,receipt=project_column_mass(grid,u,v,224000.)
    assert np.max(abs(mass_flux_divergence(a,ue,vs,224000.).sum(0)))<1e-14
    assert receipt['kinetic_energy_change_j_m2']<0 and receipt['projection_heat_added_j_m2']==0
    np.testing.assert_array_equal(u,original_u);np.testing.assert_array_equal(v,original_v)
    u2,v2,_=project_column_mass(grid,ue,vs,224000.)
    np.testing.assert_allclose(u2,ue,atol=3e-15);np.testing.assert_allclose(v2,vs,atol=3e-15)


@pytest.mark.parametrize('seed',[2,37,91])
def test_independent_pressure_power_and_hydrostatic_compression_cancel(seed):
    rng,height,grid,a,u,v=case(seed);u,v,_=project_column_mass(grid,u,v,224000.);delta=rng.uniform(-3,3,grid.dry_mass_kg_m2.shape)
    force=common_pressure_force(grid,height,delta,224000.);compression=compression_power(grid,u,v,224000.,delta)
    pressure_power=float((a.east_kg_m2*u*force.east_ms2).sum()+(a.south_kg_m2*v*force.south_ms2).sum());compression_power_total=float(compression.layer_power_w_m2.sum())
    assert compression.maximum_lower_boundary_omega_pa_s<1e-12
    assert abs(pressure_power+compression_power_total)<2e-10*max(abs(pressure_power),1.)


def test_common_hydrostatic_reference_has_zero_global_compression_work():
    _,height,grid,a,u,v=case();u,v,_=project_column_mass(grid,u,v,56000.);delta=np.zeros_like(grid.dry_mass_kg_m2)
    result=compression_power(grid,u,v,56000.,delta)
    # Local compression/expansion is allowed; the common reference contributes
    # zero net work to a column-mass-admissible closed-domain flow.
    assert np.max(abs(result.layer_power_w_m2))>1e-6
    assert abs(result.layer_power_w_m2.sum())<1e-10


def test_unclosed_column_mass_is_rejected():
    _,_,grid,_,u,v=case()
    with pytest.raises(ValueError,match='column mass'):compression_power(grid,u,v,224000.,np.zeros_like(grid.dry_mass_kg_m2))


def test_compression_is_linear_in_native_mass_flux():
    _,_,grid,_,u,v=case();u,v,_=project_column_mass(grid,u,v,224000.);delta=np.ones_like(grid.dry_mass_kg_m2)
    one=compression_power(grid,u,v,224000.,delta);two=compression_power(grid,2*u,2*v,224000.,delta)
    np.testing.assert_array_equal(two.layer_power_w_m2,2*one.layer_power_w_m2)
    np.testing.assert_array_equal(two.interface_omega_pa_s,2*one.interface_omega_pa_s)
