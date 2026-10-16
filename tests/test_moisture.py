import numpy as np
import pytest

from rotclimate.config import Params
from rotclimate.moisture import rain_coefficient, solve_moisture
from rotclimate.solver import AdvectionSolver


def problem():
    shape=(5,6)
    solver=AdvectionSolver(*shape, dx=1.)
    solver.rtol=1e-10
    solver.max_iter=2000
    solver.require_convergence=True
    zero=np.zeros(shape)
    return solver, dict(u=zero, v=zero, lamE=np.full(shape,1/86400.),
        ocean_water=np.full(shape,8.),land_source=zero,saturation=np.full(shape,10.),
        dynamics=np.full(shape,2.),instability=1.,boundary=np.full(shape,8.),guess=np.full(shape,1.))


def test_actual_nonlinear_moisture_equation_converges_on_small_grid():
    solver,kw=problem()
    p=Params(moisture_diffusion=1e-6,picard_iters=256,moisture_relaxation=.25,moisture_residual_tol=.005)
    r=solve_moisture(solver,p,**kw)
    assert r.converged and r.iterations<256
    assert r.scaled_residual<=p.moisture_residual_tol
    np.testing.assert_array_equal(r.water[solver.border],kw['boundary'][solver.border])


def test_tiny_relaxation_does_not_fake_equation_convergence():
    solver,kw=problem()
    p=Params(moisture_diffusion=1e-6,picard_iters=2,moisture_relaxation=1e-6,moisture_residual_tol=.005)
    r=solve_moisture(solver,p,**kw)
    assert r.converged is False
    assert r.scaled_residual>p.moisture_residual_tol


@pytest.mark.parametrize('with_exchange', [False, True])
def test_legacy_two_sweeps_reproduce_the_original_arithmetic(with_exchange):
    solver,kw=problem()
    p=Params(moisture_diffusion=1e-6,picard_iters=2)
    if with_exchange:
        kw.update(exchange=np.full_like(kw['guess'], 1/86400.),
                  mix=lambda water: np.full_like(water,water.mean()))
    W=kw['guess']
    for _ in range(2):
        rh=W/kw['saturation']
        gate=np.clip((rh-p.rh_threshold)/(1-p.rh_threshold),0,2)**1.5
        rate=kw['dynamics']*gate*kw['instability']/(p.precip_tau_days*86400.)
        rate=rate+np.maximum(rh-1,0)/rh/86400.
        lam=kw['lamE']+rate
        source=kw['lamE']*kw['ocean_water']+kw['land_source']
        if with_exchange:
            lam=lam+kw['exchange']
            source=source+kw['exchange']*kw['mix'](W)
        new=solver.solve(kw['u'],kw['v'],p.moisture_diffusion,lam,source,kw['boundary'],guess=W)
        W=.5*(W+np.maximum(new,0))
    r=solve_moisture(solver,p,**kw)
    np.testing.assert_array_equal(r.water,W)
    assert r.converged is None and r.iterations==2


def test_dry_zero_water_has_finite_zero_rainout():
    with np.errstate(all='raise'):
        rate=rain_coefficient(np.zeros((2,2)),np.ones((2,2)),1.,1.,.3,6.)
    np.testing.assert_array_equal(rate,0.)
