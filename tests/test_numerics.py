"""Small analytic checks, without seasonal climate simulations."""
import warnings

import numpy as np
import pytest

from rotclimate.numerics import matrix_product
from rotclimate.solver import AdvectionSolver


@pytest.mark.parametrize('columns', [None, 7])
def test_matrix_product_matches_explicit_sums_without_backend_warnings(columns):
    rng = np.random.default_rng(24)
    a = rng.uniform(0.001, 0.01, (180, 180))
    b = rng.uniform(1, 50, (180,) if columns is None else (180, columns)).astype(np.float32)
    expected = (a * b[None, :]).sum(1) if columns is None else (a[:, :, None] * b[None, :, :]).sum(1)
    with warnings.catch_warnings():
        warnings.simplefilter('error', RuntimeWarning)
        result = matrix_product(a, b)
    np.testing.assert_allclose(result, expected, rtol=2e-14)


@pytest.mark.parametrize('velocity', [-2.0, 2.0])
def test_fitted_transport_preserves_analytic_boundary_layer_on_both_grids(velocity):
    K, length = 2e4, 200000.0
    errors = {}
    for nx in [21, 41]:
        ny, dx = 9, length / (nx - 1)
        x = np.linspace(0, length, nx)
        profile = np.exp(velocity * (x - (length if velocity > 0 else 0)) / K)
        exact = np.broadcast_to(profile, (ny, nx)).copy()
        u, v = np.full_like(exact, velocity), np.zeros_like(exact)
        lam = np.full_like(exact, 1e-6)
        for scheme in ['upwind', 'exponential']:
            s = AdvectionSolver(ny, nx, dx, scheme=scheme)
            coeffs = s.coefficients(u, v, K, lam)
            actual = s._direct(*coeffs, lam * exact, exact)
            errors[scheme, nx] = np.max(np.abs(actual - exact))
    assert max(errors['exponential', nx] for nx in [21, 41]) < 1e-10
    assert errors['upwind', 21] > 1e-3
    assert errors['upwind', 41] < errors['upwind', 21]


def test_fitted_coefficients_remain_monotone_and_handle_zero_diffusion():
    rng = np.random.default_rng(9)
    u, v = rng.normal(0, 10, (13, 17)), rng.normal(0, 10, (13, 17))
    s = AdvectionSolver(13, 17, 10000, scheme='exponential')
    for K in [0.0, 1e-12, 6e4, 1e9]:
        with np.errstate(all='raise', under='ignore'):
            *off, diag = s.coefficients(u, v, K, np.full_like(u, 1e-5))
        assert all(np.isfinite(a).all() and (a <= 0).all() for a in off)
        np.testing.assert_allclose(diag + sum(off), 1e-5, rtol=1e-9, atol=2e-14)
    zero = np.zeros_like(u)
    coeffs = s.coefficients(zero, zero, 0.0, np.ones_like(u))
    assert all(np.isfinite(a).all() for a in coeffs)


def test_fitted_zero_wind_is_the_existing_diffusion_operator():
    zero = np.zeros((9, 11))
    a = AdvectionSolver(9, 11, 10000).coefficients(zero, zero, 6e4, np.ones_like(zero))
    b = AdvectionSolver(9, 11, 10000, scheme='exponential').coefficients(zero, zero, 6e4, np.ones_like(zero))
    for x, y in zip(a, b):
        np.testing.assert_array_equal(x, y)


def test_fitted_sweep_solver_matches_direct_solve():
    rng = np.random.default_rng(2)
    shape = (20, 24)
    u, v = rng.normal(0, 3, (2,) + shape)
    boundary = rng.uniform(1, 5, shape)
    lam = np.full(shape, 1e-5)
    s = AdvectionSolver(*shape, 10000.0, scheme='exponential')
    actual = s.solve(u, v, 6e4, lam, lam * boundary, boundary, rtol=1e-9, max_iter=2000)
    expected = s._direct(*s.coefficients(u, v, 6e4, lam), lam * boundary, boundary)
    np.testing.assert_allclose(actual, expected, atol=1e-6)


def test_monthly_aggregation_preserves_constant_fields():
    from rotclimate.koppen import monthly_stats

    days = (np.arange(25) + 0.5) * 365 / 25
    with warnings.catch_warnings():
        warnings.simplefilter('error', RuntimeWarning)
        result = monthly_stats(np.full((25, 9, 11), 17, dtype=np.float32),
                               np.full((25, 9, 11), 2, dtype=np.float32), days)
    np.testing.assert_allclose(result['Tm'], 17)
    np.testing.assert_allclose(result['Pm'].sum(0), 730)


def test_solver_distinguishes_convergence_on_last_sweep_from_failure():
    from rotclimate.solver import HAVE_NUMBA
    if not HAVE_NUMBA:
        pytest.skip('Sweep status requires Numba')
    shape = (5, 6)
    zero, one = np.zeros(shape), np.ones(shape)
    s = AdvectionSolver(*shape, 10000)
    s.omega = 1.0
    s.require_convergence = True
    s.max_iter = 1
    with pytest.raises(RuntimeError, match='failed its update tolerance'):
        s.solve(zero, zero, 0.0, one, 2 * one, 2 * one, guess=zero)
    assert s.converged == [False]
    s.max_iter = 2
    actual = s.solve(zero, zero, 0.0, one, 2 * one, 2 * one, guess=zero)
    np.testing.assert_array_equal(actual, 2 * one)
    assert s.iterations[-1] == 2
    assert s.converged[-1] is True
