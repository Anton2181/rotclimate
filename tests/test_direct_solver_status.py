"""The optional SciPy backend must earn the same convergence certificate."""
import warnings
import numpy as np
import pytest
import rotclimate.solver as module
from rotclimate.solver import AdvectionSolver


@pytest.mark.parametrize('scheme',['upwind','exponential'])
def test_direct_backend_solves_a_manufactured_variable_flow(monkeypatch,scheme):
    monkeypatch.setattr(module,'HAVE_NUMBA',False)
    y,x=np.mgrid[:9,:11]
    exact=2+.01*x*x-.02*y
    u=.6+np.sin(x);v=.2*np.cos(y);lam=np.full(exact.shape,.3)
    solver=AdvectionSolver(*exact.shape,1.,scheme=scheme)
    ce,cw,cs,cn,diag=solver.coefficients(u,v,.4,lam)
    source=np.zeros_like(exact)
    source[1:-1,1:-1]=(diag[1:-1,1:-1]*exact[1:-1,1:-1]
        +ce[1:-1,1:-1]*exact[1:-1,2:]+cw[1:-1,1:-1]*exact[1:-1,:-2]
        +cs[1:-1,1:-1]*exact[2:,1:-1]+cn[1:-1,1:-1]*exact[:-2,1:-1])
    solver.require_convergence=True
    actual=solver.solve(u,v,.4,lam,source,exact,rtol=1e-11)
    np.testing.assert_allclose(actual,exact,atol=1e-12,rtol=0)
    assert solver.converged==[True] and solver.methods==['direct']
    assert solver.final_updates[0]<1e-11


@pytest.mark.parametrize('backend',['direct','recovery'])
@pytest.mark.parametrize('fault',['interior','boundary'])
def test_finite_wrong_answers_cannot_claim_convergence(monkeypatch,backend,fault):
    monkeypatch.setattr(module,'HAVE_NUMBA',backend=='recovery')
    if backend=='recovery':
        monkeypatch.setattr(module,'_sweeps',lambda *args:(1,False,1.),raising=False)
    zero=np.zeros((5,6));one=np.ones_like(zero);exact=2*one
    wrong=exact.copy()
    if fault=='interior':wrong[2,2]+=.1
    else:wrong[0,2]+=.1
    solver=AdvectionSolver(*zero.shape,1.)
    solver.recover=True;solver.require_convergence=True
    monkeypatch.setattr(solver,'_direct',lambda *args:wrong.copy())
    with pytest.raises(RuntimeError,match='equation/boundary tolerance'):
        solver.solve(zero,zero,0.,one,exact,exact,rtol=1e-6,max_iter=1)
    assert solver.converged==[False] and solver.methods==['direct']
    assert solver.final_updates[0]>.09


def test_nonstrict_direct_backend_warns_once_and_keeps_failure_status(monkeypatch):
    monkeypatch.setattr(module,'HAVE_NUMBA',False)
    one=np.ones((5,6));zero=np.zeros_like(one)
    solver=AdvectionSolver(*one.shape,1.)
    monkeypatch.setattr(solver,'_direct',lambda *args:one.copy())
    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter('always')
        for _ in range(2):solver.solve(zero,zero,0.,one,2*one,one)
    assert len(seen)==1 and issubclass(seen[0].category,RuntimeWarning)
    assert solver.converged==[False,False] and solver.iterations==[0,0]


def test_nonfinite_direct_result_records_failure_before_raising(monkeypatch):
    monkeypatch.setattr(module,'HAVE_NUMBA',False)
    one=np.ones((5,6));zero=np.zeros_like(one)
    solver=AdvectionSolver(*one.shape,1.)
    monkeypatch.setattr(solver,'_direct',lambda *args:one*np.nan)
    with pytest.raises(FloatingPointError,match='Nonfinite direct solver'):
        solver.solve(zero,zero,0.,one,one,one)
    assert solver.converged==[False] and solver.methods==['direct']
