import numpy as np
from rotclimate.column_mass import ColumnMassProjection
from rotclimate.layer_transport import return_branches
from rotclimate.thermal_layer_winds import hydrostatic_thermal_shear,project_thermal_branches
from rotclimate.divergent_thermal_winds import divergent_thermal_branches
from rotclimate.reservoir_transport import ReservoirTransport


def manufactured():
    j,i=np.mgrid[:17,:21];dx=56000.;x=(i-10)*dx;y=(j-8)*dx
    lower=(-2e-6*x,2e-6*y);p=ColumnMassProjection(np.zeros(x.shape),dx)
    shear,_=hydrostatic_thermal_shear(285+.3*i+.2*j,np.full(x.shape,101325.),dx,7e-5)
    return p,lower,shear


def test_common_projection_suppresses_convergence_but_split_retains_it():
    p,lower,shear=manufactured();mean_u,mean_v,_=p.project(*lower)
    old,_,_=return_branches(*lower,mean_u,mean_v,.2)
    original=ReservoirTransport(p.mass,old[0][1:],old[1][1:],p.cell_m)
    common=project_thermal_branches(p,lower,shear)
    common_op=ReservoirTransport(p.mass,common.lower,common.upper,p.cell_m)
    split=divergent_thermal_branches(p,lower,shear)
    split_op=ReservoirTransport(p.mass,split.lower,split.upper,p.cell_m)
    assert np.abs(original.upward_air[1:-1,1:-1]).mean()>9e-7
    assert np.abs(common_op.upward_air[1:-1,1:-1]).mean()<1e-15
    np.testing.assert_array_equal(split.lower,np.array(lower))
    np.testing.assert_array_equal(split_op.upward_air,original.upward_air)
    assert split_op.dry_residual<1e-10


def test_zero_thermal_shear_recovers_historical_branch_values():
    p,lower,_=manufactured();zero=np.zeros(p.shape);u,v,_=p.project(*lower)
    old,_,_=return_branches(*lower,u,v,.2)
    result=divergent_thermal_branches(p,lower,(zero,zero))
    np.testing.assert_array_equal(result.lower,np.array(lower))
    np.testing.assert_array_equal(result.upper,np.array(old[1][1:]))


def test_split_preserves_uniform_specific_humidity_over_terrain():
    j,i=np.mgrid[:7,:9];p=ColumnMassProjection(150*i+30*j,56000.);lower=(np.full(p.shape,5.),np.ones(p.shape))
    shear,_=hydrostatic_thermal_shear(285+.3*i-.4*j,101325*p.mass,56000.,7e-5)
    result=divergent_thermal_branches(p,lower,shear);op=ReservoirTransport(p.mass,result.lower,result.upper,p.cell_m)
    expected=18*op.layer_mass
    actual,_=op.solve(np.zeros_like(expected),np.zeros_like(expected),expected,diffusion=60000.)
    np.testing.assert_allclose(actual,expected,atol=1e-10,rtol=1e-10)
