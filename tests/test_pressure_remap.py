import numpy as np
import pytest
from rotclimate.column_thermodynamics import G
from rotclimate.pressure_remap import pressure_overlap,remap_moist_column
from rotclimate.pressure_moist import gas_energy
from rotclimate.fast_liquid_phase import enthalpy_phase_fast


SOURCE=[100000.,85000.,65000.,40000.]
REFINED=[100000.,97500.,95000.,90000.,85000.,75000.,65000.,50000.,40000.]


def test_partial_overlap_conserves_extensive_amount_and_constant_concentration():
    op=pressure_overlap(SOURCE,[100000.,93000.,77000.,60000.,40000.]);rng=np.random.default_rng(93)
    a=rng.uniform(0,100,(3,4,5));b=op.extensive(a)
    np.testing.assert_allclose(b.sum(0),a.sum(0),rtol=2e-15,atol=1e-13)
    np.testing.assert_allclose(op.intensive(np.full((3,4,5),7.)),7.,rtol=2e-15)
    assert np.min(b)>=0 and not op.overlap_mass_kg_m2.flags.writeable


def test_refinement_coarsening_recovers_piecewise_constant_source_integrals():
    forward=pressure_overlap(SOURCE,REFINED);reverse=pressure_overlap(REFINED,SOURCE)
    a=np.array([3.,7.,13.]);np.testing.assert_allclose(reverse.extensive(forward.extensive(a)),a,rtol=2e-15)
    np.testing.assert_allclose(reverse.intensive(forward.intensive(a)),a,rtol=2e-15)


def test_pressure_bounds_cannot_hide_mass_creation_or_lost_upper_layers():
    for target in [[101000,85000,40000],[100000,85000,38000],[100000,100000,40000],[100000,50000,9000]]:
        with pytest.raises(ValueError):pressure_overlap(SOURCE,target)
    op=pressure_overlap(SOURCE,REFINED)
    for values in [[1,2],[1,np.nan,3]]:
        with pytest.raises(ValueError):op.extensive(values)


def test_coarsened_velocity_books_exact_unresolved_variance_without_heating():
    op=pressure_overlap([100000,90000,80000,70000,60000],[100000,80000,60000])
    speed=np.array([2.,-2.,3.,1.]);mean,loss=op.velocity(speed)
    np.testing.assert_allclose(mean,[0,2]);np.testing.assert_allclose(loss,5*10000/G)
    np.testing.assert_allclose((op.source_mass_kg_m2*speed).sum(),(op.target_mass_kg_m2*mean).sum(),atol=1e-12)
    assert np.all(loss>0)


def test_refined_velocities_retain_facewise_momentum_and_kinetic_energy():
    op=pressure_overlap(SOURCE,REFINED);rng=np.random.default_rng(4);a=rng.normal(size=(3,4,6));b,loss=op.velocity(a)
    np.testing.assert_allclose(np.einsum('i,i...->...',op.source_mass_kg_m2,a),np.einsum('i,i...->...',op.target_mass_kg_m2,b),rtol=1e-14,atol=1e-11)
    np.testing.assert_allclose(loss,0,atol=1e-11)


def test_moist_remap_preserves_actual_enthalpy_and_water_including_conversion_rain():
    source=[100000,90000,80000,70000,60000];target=[100000,80000,60000];mass=-np.diff(source)/G
    t=np.array([260.,320.,250.,310.]);w=mass*np.array([.001,.06,.0004,.04])
    r=remap_moist_column(t,w,source,target);newmass=-np.diff(target)/G
    assert r.rain_kg_m2>0
    np.testing.assert_allclose(r.vapor_kg_m2.sum()+r.rain_kg_m2,w.sum(),rtol=1e-13)
    np.testing.assert_allclose(gas_energy(r.temperature_k,r.vapor_kg_m2,newmass).sum()+r.rain_enthalpy_j_m2,gas_energy(t,w,mass).sum(),rtol=1e-13)
    assert r.certificate['relative_energy_error']<1e-13


def test_fast_and_reference_target_phase_agree_for_spatial_refinement():
    rng=np.random.default_rng(287);t=rng.uniform(260,305,(3,4,5));mass=(-np.diff(SOURCE)/G)[:,None,None];w=mass*rng.uniform(.0001,.025,t.shape)
    a=remap_moist_column(t,w,SOURCE,REFINED);b=remap_moist_column(t,w,SOURCE,REFINED,phase_solver=enthalpy_phase_fast)
    for name in ['temperature_k','vapor_kg_m2','rain_kg_m2','rain_enthalpy_j_m2']:
        np.testing.assert_allclose(getattr(a,name),getattr(b,name),rtol=1e-10,atol=1e-5)


def test_no_phase_rain_means_no_unreported_energy_transfer():
    mass=(-np.diff(SOURCE)/G)[:,None,None];t=np.broadcast_to(np.array([295.,275.,250.])[:,None,None],(3,2,3));w=mass*np.full(t.shape,.00001)
    r=remap_moist_column(t,w,SOURCE,REFINED)
    np.testing.assert_array_equal(r.rain_kg_m2,0);np.testing.assert_array_equal(r.rain_enthalpy_j_m2,0)
    np.testing.assert_allclose(r.temperature_k,r.raw_temperature_k,atol=1e-12)
    with pytest.raises(ValueError):remap_moist_column(t,-w,SOURCE,REFINED)
