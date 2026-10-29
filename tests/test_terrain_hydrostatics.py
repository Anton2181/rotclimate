import numpy as np
import pytest
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,reference_geopotential,terrain_pressure_grid
from rotclimate.column_thermodynamics import G,RD


def test_standard_atmosphere_and_below_sea_level():
    p=surface_pressure_from_height(np.array([-400.,0.,1500.,3000.,5000.]),288.15)
    np.testing.assert_allclose(p,[106223.7,101325.,84555.99,70108.27,54019.55],rtol=2e-5)
    assert np.all(np.diff(p)<0)


def test_hydrostatic_differential_equation_over_mountains():
    height=np.linspace(-300,6000,51);temperature=294.-.0065*height;dz=.01
    upper=surface_pressure_from_height(height+dz,294.);lower=surface_pressure_from_height(height-dz,294.)
    numerical=(np.log(upper)-np.log(lower))/(2*dz)
    np.testing.assert_allclose(numerical,-G/(RD*temperature),rtol=2e-9)


@pytest.mark.parametrize('lapse',[0.,1e-12,.0065,.0098])
def test_pressure_geopotential_round_trip(lapse):
    heights=np.array([[-400,0,1000],[2500,4000,6000.]])
    temperatures=np.array([[290.],[305.]])
    pressure=surface_pressure_from_height(heights,temperatures,lapse_k_m=lapse)
    np.testing.assert_allclose(reference_geopotential(pressure,temperatures,lapse_k_m=lapse),G*heights,rtol=2e-14,atol=1e-9)


def test_isothermal_limit():
    h=np.array([-400,0,5000.]);expected=101325*np.exp(-G*h/(RD*288.15))
    np.testing.assert_array_equal(surface_pressure_from_height(h,288.15,lapse_k_m=0),expected)
    np.testing.assert_allclose(surface_pressure_from_height(h,288.15,lapse_k_m=1e-10),expected,rtol=6e-8)


def test_column_mass_has_no_air_below_terrain():
    pressure=surface_pressure_from_height(np.array([[0.,3000.],[500.,5000.]]),288.15);original=pressure.copy()
    grid=terrain_pressure_grid(pressure,[1.,.8,.5,.2,0.])
    np.testing.assert_array_equal(grid.edges_pa[0],pressure)
    np.testing.assert_array_equal(grid.edges_pa[-1],np.full_like(pressure,38000.))
    np.testing.assert_allclose(grid.dry_mass_kg_m2.sum(0),(pressure-38000)/G,rtol=3e-16)
    assert grid.dry_mass_kg_m2[:,0,1].sum()<grid.dry_mass_kg_m2[:,0,0].sum()
    np.testing.assert_array_equal(pressure,original)
    pressure[:]=1;assert np.all(grid.surface_pressure_pa>38000.)


@pytest.mark.parametrize('pressure,sigma',[(38000,[1,0]),(37000,[1,0]),(100000,[1,.3,.5,0]),(100000,[.9,0]),(100000,[1,.1]),(np.nan,[1,0])])
def test_invalid_or_underground_grid_rejected(pressure,sigma):
    with pytest.raises(ValueError):terrain_pressure_grid(pressure,sigma)


def test_unphysical_reference_is_not_silently_clipped():
    with pytest.raises(ValueError):surface_pressure_from_height(30000.,288.15)
    with pytest.raises(ValueError):surface_pressure_from_height(0.,288.15,lapse_k_m=-.005)
