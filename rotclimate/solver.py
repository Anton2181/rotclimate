"""Steady advection-diffusion-relaxation solver on the model grid.

Solves   u . grad(phi) - K lap(phi) + lam * phi = S
with first-order upwinding (default) or an optional exponentially fitted local
stencil, and Dirichlet values on the outer ring.

The discrete operator is an M-matrix, so symmetric Gauss-Seidel sweeps in
the four diagonal directions ("fast sweeping") converge quickly for these
advection-dominated problems, especially when warm-started from the previous
time step.  Numba makes a sweep over ~100k cells take well under a
millisecond; a SciPy sparse direct solve is used when Numba is missing.
"""
from __future__ import annotations

import numpy as np
import warnings

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
                return it + 1, True, maxd
        return max_iter, False, maxd


class AdvectionSolver:
    def __init__(self, ny: int, nx: int, dx: float, scheme="upwind"):
        if scheme not in ("upwind", "exponential"):
            raise ValueError(f"Unknown transport scheme: {scheme}")
        self.scheme = scheme
        self.ny, self.nx, self.dx = ny, nx, dx
        border = np.zeros((ny, nx), bool)
        border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
        self.border = border
        self.iterations = []
        self.converged = []
        self.final_updates = []
        self.rtol = 1e-3
        self.max_iter = 400
        self.require_convergence = False
        self._warned_limit = False
        self.omega = 1.3          # successive over-relaxation

    def coefficients(self, u, v, K, lam):
        dx = self.dx
        wr = -v                                  # velocity toward increasing row
        Kd = np.broadcast_to(np.asarray(K, float) / dx**2, u.shape)
        if self.scheme == "exponential":
            # Exponentially fitted local stencil: D * B(Pe), with
            # B(Pe)=Pe/(exp(Pe)-1). Retains nonpositive neighbor coefficients
            # and the pure-upwind limit at K=0. For constant flow it exactly
            # balances exponential profiles of u*grad(phi)-K*lap(phi)=0.
            # In variable flow this remains a local approximation to the
            # existing nonconservative equation, not a new flux budget.
            Kx = self._fitted_diffusion(np.abs(u) / dx, Kd)
            Ky = self._fitted_diffusion(np.abs(wr) / dx, Kd)
        else:
            Kx = Ky = Kd
        ce = -np.maximum(-u, 0) / dx - Kx
        cw = -np.maximum(u, 0) / dx - Kx
        cs = -np.maximum(-wr, 0) / dx - Ky
        cn = -np.maximum(wr, 0) / dx - Ky
        diag = lam + (np.abs(u) + np.abs(wr)) / dx + 2 * (Kx + Ky)
        return ce, cw, cs, cn, diag

    @staticmethod
    def _fitted_diffusion(adv, diff):
        pe = np.divide(adv, diff, out=np.full_like(adv, np.inf), where=diff > 0)
        # A finite exponent avoids overflow; beyond Pe=50 the equivalent
        # exp(-Pe) formula safely tends to zero.
        out = np.array(diff, copy=True)
        np.divide(adv, np.expm1(np.minimum(pe, 50.0)), out=out, where=pe > 1e-6)
        large = pe > 50.0
        decay = np.exp(-pe[large])
        out[large] = adv[large] * decay / (1 - decay)
        return out

    def solve(self, u, v, K, lam, S, boundary, guess=None, rtol=None, max_iter=None):
        """u: eastward [m/s], v: northward [m/s] (rows run southward)."""
        ce, cw, cs, cn, diag = self.coefficients(u, v, K, lam)
        rtol = self.rtol if rtol is None else rtol
        max_iter = self.max_iter if max_iter is None else max_iter
        if not np.isfinite(rtol) or rtol <= 0 or max_iter < 1:
            raise ValueError("Solver tolerance and iteration limit must be positive")
        if HAVE_NUMBA:
            phi = np.array(boundary if guess is None else guess, float, copy=True)
            phi[self.border] = boundary[self.border]
            scale = max(np.abs(boundary).max(), 1e-12)
            n, converged, update = _sweeps(phi, ce, cw, cs, cn, diag, np.ascontiguousarray(S, float),
                        rtol * scale, max_iter, self.omega)
            self.iterations.append(n)
            self.converged.append(converged)
            self.final_updates.append(update)
            if not np.isfinite(phi).all():
                raise FloatingPointError("Nonfinite linear solver output")
            if not converged:
                message = f"Linear solve failed its update tolerance after {n} sweeps (rtol={rtol:g})"
                if self.require_convergence:
                    raise RuntimeError(message)
                if not self._warned_limit:
                    warnings.warn(message, RuntimeWarning, stacklevel=2)
                    self._warned_limit = True
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
