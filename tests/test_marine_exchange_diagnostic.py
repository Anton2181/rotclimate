"""A certified moisture solve needs signed land marine relaxation in its budget."""
import numpy as np
import pytest

from rotclimate.config import Params
from rotclimate.moisture import solve_moisture
from rotclimate.solver import AdvectionSolver
from rotclimate.transport import moisture_terms
from scripts.somalia_marine_exchange_trace import marine_exchange


@pytest.mark.parametrize('land_mm_day,sign',[(.1,1),(20.,-1)])
def test_omitted_land_marine_exchange_breaks_a_certified_equation_budget(land_mm_day,sign):
    shape=(5,6);zero=np.zeros(shape);target=np.full(shape,8.)
    rate=np.full(shape,1/86400.);source=np.full(shape,land_mm_day/86400.)
    solver=AdvectionSolver(*shape,dx=1.)
    solver.rtol=1e-11;solver.max_iter=2000;solver.require_convergence=True
    p=Params(moisture_diffusion=1e-6,picard_iters=512,moisture_relaxation=.25,
             moisture_residual_tol=1e-6,ocean_sink=1.)
    r=solve_moisture(solver,p,zero,zero,rate,target,source,np.full(shape,10.),
                     np.full(shape,2.),1.,target,np.ones(shape))
    assert r.converged and r.scaled_residual<=p.moisture_residual_tol
    marine=marine_exchange(rate,target,r.water)
    assert sign*marine[2,2]>0
    missing=moisture_terms(r.water,zero,zero,solver.dx,p.moisture_diffusion,
                           source*86400.,r.rain,0.,r.water)
    complete=moisture_terms(r.water,zero,zero,solver.dx,p.moisture_diffusion,
                            source*86400.+marine,r.rain,0.,r.water)
    interior=(slice(1,-1),slice(1,-1))
    assert np.max(missing['absolute_residual'][interior])>.05
    denominator=np.maximum(r.rain+np.abs(source*86400.+marine),.1)
    assert np.max((complete['absolute_residual']/denominator)[interior])<=p.moisture_residual_tol
    np.testing.assert_allclose((complete['residual']-missing['residual'])[interior],marine[interior],atol=1e-12)
