import numpy as np
import pytest
from rotclimate.solver import AdvectionSolver, HAVE_NUMBA


@pytest.mark.skipif(not HAVE_NUMBA, reason='Exercises capped sweep recovery')
def test_capped_sweeps_recover_the_exact_operator_without_loosening_tolerance():
    rng = np.random.default_rng(24)
    shape = (13, 17)
    u, v = rng.normal(0, 5, (2, *shape))
    boundary = rng.uniform(4, 25, shape)
    lam = np.full(shape, 1 / 86400.)
    source = lam * rng.uniform(2, 30, shape)
    s = AdvectionSolver(*shape, 10000.)
    s.rtol = 1e-10; s.max_iter = 1; s.require_convergence = True; s.recover = True
    actual = s.solve(u, v, 60000., lam, source, boundary)
    coefficients = s.coefficients(u, v, 60000., lam)
    expected = s._direct(*coefficients, source, boundary)
    np.testing.assert_allclose(actual, expected, atol=1e-10)
    assert s.converged == [True] and s.methods == ['direct']
    assert s.equation_error(actual, *coefficients, source) < 1e-10
    np.testing.assert_array_equal(actual[s.border], boundary[s.border])


def test_recovery_leaves_an_already_converged_solve_unchanged():
    shape = (9, 11);one = np.ones(shape);zero = np.zeros(shape)
    a = AdvectionSolver(*shape, 10000.);b = AdvectionSolver(*shape, 10000.);b.recover = True
    x = a.solve(zero, zero, 60000., one, 12*one, 12*one)
    y = b.solve(zero, zero, 60000., one, 12*one, 12*one)
    np.testing.assert_array_equal(x, y)
    assert a.iterations == b.iterations
