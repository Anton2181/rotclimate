"""Known pressure contributions, local feedback, and continuation equivalence."""
import numpy as np
from scipy.ndimage import gaussian_filter
from experiments.nested_pressure_context import insert_child,nested_pressure


def smooth(a,sigma):
    return gaussian_filter(a,sigma,mode='nearest')


def test_off_child_heat_low_has_known_gaussian_pressure_contribution():
    parent=np.zeros((11,11));child=np.zeros((3,3))
    parent[5,9]=8.
    p=nested_pressure(parent,child,4,1.,.5,1.,0.,smooth)
    k=np.exp(-.5*np.arange(-4,5,dtype=float)**2);k/=k.sum()
    expected=-100.*8.*k[4]*k[8]
    np.testing.assert_allclose(p[1,1],expected,rtol=1e-14,atol=1e-15)
    assert p[1,2]<p[1,0]  # lower pressure toward the external warm anomaly


def test_child_updates_all_its_padded_cells_without_mutating_parent():
    parent=np.full((11,11),2.);child=np.full((3,3),3.)
    p=nested_pressure(parent,child,4,1.,.5,1.,0.,smooth)
    k=np.exp(-.5*np.arange(-4,5,dtype=float)**2);k/=k.sum()
    expected=-100.*(2.+k[3:6].sum()**2)
    np.testing.assert_allclose(p[1,1],expected,rtol=1e-14)
    np.testing.assert_array_equal(parent,np.full((11,11),2.))
    np.testing.assert_array_equal(child,np.full((3,3),3.))


def test_uniform_parent_child_preserves_constant_pressure():
    p=nested_pressure(np.full((21,21),3.),np.full((5,5),3.),8,2.,1.,.7,.2,smooth)
    np.testing.assert_allclose(p,-210.,atol=1e-12)


def test_nearest_continuation_is_recovered_when_it_is_the_supplied_parent():
    child=np.random.default_rng(0).normal(size=(7,9))
    parent=np.pad(child,8,mode='edge')
    p=nested_pressure(parent,child,8,2.,1.,.7,.2,smooth)
    broad=smooth(child,2.)
    expected=-100.*(.7*broad+.2*(smooth(child,1.)-broad))
    np.testing.assert_allclose(p,expected,atol=1e-12)


def test_bad_alignment_cannot_silently_shift_child():
    import pytest
    with pytest.raises(ValueError):
        insert_child(np.zeros((12,11)),np.zeros((3,3)),4)


def test_original_wide_fft_has_known_external_pressure_contribution():
    from rotclimate.model import gauss
    parent=np.zeros((81,81));child=np.zeros((9,9))
    parent[40,52]=8.
    pressure=nested_pressure(parent,child,36,7.,1.,1.,0.,gauss)
    k=np.exp(-.5*(np.arange(-28,29,dtype=float)/7.)**2);k/=k.sum()
    expected=-800.*k[28]*k[40]
    np.testing.assert_allclose(pressure[4,4],expected,rtol=1e-12,atol=1e-12)


def test_exact_parent_sampling_does_not_depend_on_child_window_size():
    from rotclimate.model import gauss
    parent=np.random.default_rng(1).normal(size=(81,81))
    broad=gauss(parent,7.)
    whole=-100.*(.7*broad+.2*(gauss(parent,1.)-broad))
    for offset in [20,30]:
        child=parent[offset:-offset,offset:-offset].copy()
        pressure=nested_pressure(parent,child,offset,7.,1.,.7,.2,gauss)
        np.testing.assert_array_equal(pressure,whole[offset:-offset,offset:-offset])
