"""Steady advection-diffusion-relaxation solver on the model grid.

Solves   u . grad(phi) - K lap(phi) + lam * phi = S
with first-order upwinding and Dirichlet values on the outer ring.

The discrete operator is an M-matrix, so symmetric Gauss-Seidel sweeps in
the four diagonal directions ("fast sweeping") converge quickly for these
advection-dominated problems, especially when warm-started from the previous
time step.  Numba makes a sweep over ~100k cells take well under a
millisecond; a SciPy sparse direct solve is used when Numba is missing.
"""
from __future__ import annotations

import numpy as np

try:
    import numba

    HAVE_NUMBA = True
except ImportError:  # pragma: no cover
    HAVE_NUMBA = False


if HAVE_NUMBA:

    @numba.njit(cache=True, fastmath=True)
    def _sweeps(phi, ce, cw, cs, cn, diag, S, tol, max_iter, omega):
        ny, nx = phi.shape
        for it in range(max_iter):
            maxd = 0.0
            for order in range(4):
                for ii in range(1, ny - 1):
                    i = ii if order < 2 else ny - 1 - ii
                    for jj in range(1, nx - 1):
                        j = jj if (order % 2 == 0) else nx - 1 - jj
                        new = (S[i, j] - ce[i, j] * phi[i, j + 1] - cw[i, j] * phi[i, j - 1]
                               - cs[i, j] * phi[i + 1, j] - cn[i, j] * phi[i - 1, j]) / diag[i, j]
                        d = new - phi[i, j]
                        if abs(d) > maxd:
                            maxd = abs(d)
                        phi[i, j] += omega * d
            if maxd < tol:
                return it + 1
        return max_iter


class AdvectionSolver:
    def __init__(self, ny: int, nx: int, dx: float):
        self.ny, self.nx, self.dx = ny, nx, dx
        border = np.zeros((ny, nx), bool)
        border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
        self.border = border
        self.iterations = []
        self.rtol = 1e-3
        self.omega = 1.3          # successive over-relaxation

    def coefficients(self, u, v, K, lam):
        dx = self.dx
        wr = -v                                  # velocity toward increasing row
        Kd = np.broadcast_to(np.asarray(K, float) / dx**2, u.shape)
        ce = -np.maximum(-u, 0) / dx - Kd
        cw = -np.maximum(u, 0) / dx - Kd
        cs = -np.maximum(-wr, 0) / dx - Kd
        cn = -np.maximum(wr, 0) / dx - Kd
        diag = lam + (np.abs(u) + np.abs(wr)) / dx + 4 * Kd
        return ce, cw, cs, cn, diag

    def solve(self, u, v, K, lam, S, boundary, guess=None, rtol=None, max_iter=400):
        """u: eastward [m/s], v: northward [m/s] (rows run southward)."""
        ce, cw, cs, cn, diag = self.coefficients(u, v, K, lam)
        rtol = self.rtol if rtol is None else rtol
        if HAVE_NUMBA:
            phi = np.array(boundary if guess is None else guess, float, copy=True)
            phi[self.border] = boundary[self.border]
            scale = max(np.abs(boundary).max(), 1e-12)
            n = _sweeps(phi, ce, cw, cs, cn, diag, np.ascontiguousarray(S, float),
                        rtol * scale, max_iter, self.omega)
            self.iterations.append(n)
            return phi
        return self._direct(ce, cw, cs, cn, diag, S, boundary)

    def _direct(self, ce, cw, cs, cn, diag, S, boundary):  # pragma: no cover
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla

        ny, nx = self.ny, self.nx
        idx = np.arange(ny * nx).reshape(ny, nx)
        inner = ~self.border
        c = idx[inner]
        nbrs = [(ce, idx[1:-1, 2:]), (cw, idx[1:-1, :-2]), (cs, idx[2:, 1:-1]), (cn, idx[:-2, 1:-1])]
        rows = [c] + [c] * 4 + [idx[self.border]]
        cols = [c] + [nb.ravel() for _, nb in nbrs] + [idx[self.border]]
        vals = [diag[inner]] + [co[inner] for co, _ in nbrs] + [np.ones(self.border.sum())]
        A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                          shape=(ny * nx, ny * nx))
        rhs = np.empty(ny * nx)
        rhs[c] = S[inner]
        rhs[idx[self.border]] = boundary[self.border]
        return spla.spsolve(A, rhs).reshape(ny, nx)
