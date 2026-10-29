"""Independent pressure hydrostatics, compression and actual work identities."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import G,RD
from rotclimate.pressure_coordinate import pressure_coordinate


def test_isothermal_hydrostatic_geopotential_matches_exact_log_pressure():
    col=pressure_coordinate([101325.,95000.,82000.,60000.,38000.,18000.]);t=np.full(5,278.)
    expected=RD*278*np.log(col.centers_pa[0]/col.centers_pa)
    expected-=np.dot(col.cell_mass_kg_m2,expected)/col.cell_mass_kg_m2.sum()
    np.testing.assert_allclose(col.geopotential(t),expected,atol=3e-11)


def test_temperature_linear_in_log_pressure_has_exact_integral():
    col=pressure_coordinate([101325.,90000.,70000.,55000.,32000.,12000.]);x=np.log(col.centers_pa[0]/col.centers_pa)
    t=300-38*x;expected=RD*(300*x-19*x*x)
    expected-=np.dot(col.cell_mass_kg_m2,expected)/col.cell_mass_kg_m2.sum()
    np.testing.assert_allclose(col.geopotential(t),expected,atol=3e-11)


def test_unequal_pressure_grid_actual_pressure_and_compression_work_cancel():
    col=pressure_coordinate([101325.,95000.,82000.,60000.,38000.,18000.]);rng=np.random.default_rng(52)
    t=270+rng.normal(size=(5,3,4));div=rng.normal(scale=1e-5,size=t.shape);m=col.cell_mass_kg_m2[:,None,None]
    div-=np.sum(m*div,axis=0,keepdims=True)/m.sum()
    pressure_work=np.sum(m*div*col.geopotential(t),axis=0)
    compression=col.compression_power_w_m2(t,div).sum(0)
    np.testing.assert_allclose(pressure_work+compression,0,atol=2e-12)


@pytest.mark.parametrize('n',[8,16,32])
def test_compression_recovers_pressure_coordinate_adiabatic_limit(n):
    edges=np.geomspace(101325.,20000.,n+1);col=pressure_coordinate(edges);m=col.cell_mass_kg_m2
    flux=np.r_[0.,.01*np.sin(np.arange(1,n)*np.pi/n),0.];div=-np.diff(flux)/m;t=np.full(n,280.)
    omega=-G*flux;omega_center=.5*(omega[:-1]+omega[1:])
    continuous=RD*t*omega_center/col.centers_pa
    h=np.log(edges[0]/edges[-1])/n;quadrature=h/(2*np.sinh(h/2))
    np.testing.assert_allclose(col.compression_power_w_m2(t,div)/m,continuous*quadrature,rtol=2e-13,atol=1e-15)
    np.testing.assert_allclose(col.pressure_velocity(div),omega[1:-1],atol=1e-15)


def test_invalid_order_and_open_pressure_lid_rejected():
    with pytest.raises(ValueError):pressure_coordinate([100000.,110000.,50000.])
    col=pressure_coordinate([100000.,80000.,50000.])
    with pytest.raises(ValueError):col.upward_mass_flux([1e-5,1e-5])
