"""An isolated optimization must preserve water, rain and convergence history."""
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from probe_moisture_mix_reuse import proposed_function
from rotclimate.moisture import solve_moisture
from rotclimate.config import Params
from rotclimate.solver import AdvectionSolver
from rotclimate.storms import RainoutExchange


@pytest.mark.parametrize('tolerance',[0.,1e-7])
@pytest.mark.parametrize('condensation',[False,True])
def test_mix_reuse_retains_legacy_and_residual_checked_solutions(tolerance,condensation):
    proposal=proposed_function()[2]
    results=[];histories=[];calls=[]
    for function in (solve_moisture,proposal):
        shape=(5,6);zero=np.zeros(shape)
        solver=AdvectionSolver(*shape,dx=1.)
        solver.rtol,solver.max_iter,solver.require_convergence=1e-12,2000,True
        p=Params(moisture_diffusion=0.,picard_iters=256 if tolerance else 2,
                 moisture_relaxation=.25,moisture_residual_tol=tolerance)
        count=[0]
        if condensation:
            storm=RainoutExchange(np.full(shape,1/86400.),lambda a:a,np.full(shape,2.))
            target=storm;extra=dict(condensate=storm.condensate);dynamics=zero
        else:
            target=lambda a:gaussian_filter(a,1.,mode='reflect');extra={};dynamics=np.full(shape,2.)
        def counted(water):
            count[0]+=1
            return target(water)
        result=function(solver,p,u=zero,v=zero,lamE=np.full(shape,1/86400.),
            ocean_water=np.full(shape,8.),land_source=zero,saturation=np.full(shape,100.),
            dynamics=dynamics,instability=1.,boundary=np.full(shape,8.),guess=np.ones(shape),
            exchange=1/86400.,mix=counted,**extra)
        results.append(result);calls.append(count[0])
        histories.append((solver.iterations,solver.final_updates,solver.converged,solver.methods))
    before,after=results
    np.testing.assert_array_equal(before.water,after.water)
    np.testing.assert_array_equal(before.rain,after.rain)
    assert (before.iterations,before.converged,before.scaled_residual)==(
        after.iterations,after.converged,after.scaled_residual)
    assert histories[0]==histories[1]
    assert calls[1]<calls[0] if tolerance else calls[1]==calls[0]
