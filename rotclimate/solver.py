"""Steady advection-diffusion-relaxation solver on the model grid.

Solves   u . grad(phi) - K lap(phi) + lam * phi = S
with first-order upwinding (default) or an optional exponentially fitted local
stencil, and Dirichlet values on the outer ring. Opt-in form="flux" replaces
the concentration derivative by shared-face div(u*phi), with upwind fluxes.

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
    def __init__(self, ny: int, nx: int, dx: float, scheme="upwind", form="concentration"):
        if scheme not in ("upwind", "exponential"):
            raise ValueError(f"Unknown transport scheme: {scheme}")
        self.scheme = scheme
        if form not in ('concentration','flux') or (form == 'flux' and scheme != 'upwind'):
            raise ValueError('Flux transport requires the upwind face stencil')
        self.form = form
        self.ny, self.nx, self.dx = ny, nx, dx
        border = np.zeros((ny, nx), bool)
        border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
        self.border = border
        self.iterations = []
        self.converged = []
        self.final_updates = []
        self.methods = []
        self.rtol = 1e-3
        self.max_iter = 400
        self.require_convergence = False
        self.recover = False
        self._warned_limit = False
        self.omega = 1.0 if form == 'flux' else 1.3  # monotone sweeps for column-dominant flux operator

    def coefficients(self, u, v, K, lam):
        dx = self.dx
        wr = -v                                  # velocity toward increasing row
        Kd = np.broadcast_to(np.asarray(K, float) / dx**2, u.shape)
        if self.form == 'flux':
            if np.ndim(K) != 0:
                raise ValueError('Flux stencil currently requires uniform diffusivity')
            # One shared velocity per face; upwind outgoing/incoming water.
            # Opposite signs at the adjacent cells make interior fluxes cancel.
            ue=.5*(u+np.roll(u,-1,axis=1)); uw=.5*(u+np.roll(u,1,axis=1))
            vs=.5*(wr+np.roll(wr,-1,axis=0)); vn=.5*(wr+np.roll(wr,1,axis=0))
            ce=np.minimum(ue,0)/dx-Kd
            cw=-np.maximum(uw,0)/dx-Kd
            cs=np.minimum(vs,0)/dx-Kd
            cn=-np.maximum(vn,0)/dx-Kd
            diag=(lam+(np.maximum(ue,0)-np.minimum(uw,0)+np.maximum(vs,0)-np.minimum(vn,0))/dx+4*Kd)
            return ce,cw,cs,cn,diag
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
        scale = max(np.abs(boundary).max(), 1e-12)
        if HAVE_NUMBA:
            start = np.array(boundary if guess is None else guess, float, copy=True)
            start[self.border] = boundary[self.border]
            phi = start.copy()
            Sc = np.ascontiguousarray(S, float)
            n, converged, update = _sweeps(phi, ce, cw, cs, cn, diag, Sc, rtol * scale, max_iter, self.omega)
            # the exact solution of this M-matrix problem is bounded by its
            # boundary values and S / lam (discrete maximum principle)
            bound = max(np.abs(boundary).max(), float(np.max(np.abs(Sc) / np.maximum(np.asarray(lam, float), 1e-30))))
            # Converging flux may physically exceed the concentration-form
            # S/lam bound. It uses monotone sweeps instead of that heuristic.
            diverged = not np.isfinite(phi).all() or (self.form == 'concentration' and np.abs(phi).max() > 2.0 * bound + 1.0)
            method = 'sor' if self.omega != 1.0 else 'gauss_seidel'
            if diverged and self.omega != 1.0:
                # Over-relaxation is only guaranteed to converge for omega <= 1;
                # strongly advection-dominated flow (fast local winds) can make
                # it diverge. Plain Gauss-Seidel converges for this diagonally
                # dominant M-matrix, so redo the solve without it (solves that
                # did not diverge are unchanged).
                phi = start.copy()
                n2, converged, update = _sweeps(phi, ce, cw, cs, cn, diag, Sc, rtol * scale, max_iter, 1.0)
                n += n2
                self.fallbacks = getattr(self, "fallbacks", 0) + 1
                method = 'gauss_seidel'
            if not converged and self.recover:
                # A bounded oscillation can miss tolerance without crossing
                # the divergence bound. Plain sweeps solve the same operator.
                if method != 'gauss_seidel':
                    phi = start.copy() if diverged else phi
                    n2, converged, update = _sweeps(phi, ce, cw, cs, cn, diag, Sc,
                                                   rtol * scale, max_iter, 1.0)
                    n += n2
                    self.fallbacks = getattr(self, 'fallbacks', 0) + 1
                    method = 'gauss_seidel'
                if not converged:
                    phi = self._direct(ce, cw, cs, cn, diag, Sc, boundary)
                    update, converged = self._direct_status(phi, ce, cw, cs, cn, diag, Sc, boundary, rtol * scale)
                    method = 'direct'
            self.iterations.append(n)
            self.converged.append(converged)
            self.final_updates.append(update)
            self.methods.append(method)
            if not np.isfinite(phi).all():
                raise FloatingPointError("Nonfinite linear solver output")
            if not converged:
                criterion = 'equation/boundary' if method == 'direct' else 'update'
                message = f"Linear solve failed its {criterion} tolerance after {n} sweeps (rtol={rtol:g})"
                if self.require_convergence:
                    raise RuntimeError(message)
                if not self._warned_limit:
                    warnings.warn(message, RuntimeWarning, stacklevel=2)
                    self._warned_limit = True
            return phi
        phi = self._direct(ce, cw, cs, cn, diag, S, boundary)
        update, converged = self._direct_status(phi, ce, cw, cs, cn, diag, S, boundary, rtol * scale)
        self.iterations.append(0); self.converged.append(converged)
        self.final_updates.append(update); self.methods.append('direct')
        if not np.isfinite(phi).all() or not np.isfinite(update):
            raise FloatingPointError('Nonfinite direct solver output')
        if not converged:
            message = f"Linear direct solve failed its equation/boundary tolerance (error={update:g}, rtol={rtol:g})"
            if self.require_convergence:
                raise RuntimeError(message)
            if not self._warned_limit:
                warnings.warn(message, RuntimeWarning, stacklevel=2)
                self._warned_limit = True
        return phi

    def _direct_status(self, phi, ce, cw, cs, cn, diag, source, boundary, tolerance):
        """Certify the solved equation and prescribed boundary, for either backend."""
        if not np.isfinite(phi).all():
            return float('inf'), False
        equation = self.equation_error(phi, ce, cw, cs, cn, diag, source)
        boundary_error = float(np.max(np.abs(phi[self.border] - boundary[self.border])))
        error = max(equation, boundary_error)
        # Only floating-point roundoff is allowed beyond the requested tolerance.
        roundoff = 50 * np.finfo(float).eps * max(1., float(np.max(np.abs(phi))))
        return error, bool(np.isfinite(error) and error <= tolerance + roundoff)

    @staticmethod
    def equation_error(phi, ce, cw, cs, cn, diag, source):
        """Maximum diagonal-scaled interior residual, in the field's units."""
        source = np.broadcast_to(source, phi.shape)
        residual = (diag[1:-1, 1:-1] * phi[1:-1, 1:-1]
                    + ce[1:-1, 1:-1] * phi[1:-1, 2:]
                    + cw[1:-1, 1:-1] * phi[1:-1, :-2]
                    + cs[1:-1, 1:-1] * phi[2:, 1:-1]
                    + cn[1:-1, 1:-1] * phi[:-2, 1:-1] - source[1:-1, 1:-1])
        return float(np.max(np.abs(residual / diag[1:-1, 1:-1])))

    def _direct(self, ce, cw, cs, cn, diag, S, boundary):  # pragma: no cover
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla

        ny, nx = self.ny, self.nx
        S = np.broadcast_to(S, (ny, nx))
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
