"""Two conservative transport branches sharing a fixed column humidity profile.

Opposed branches are upwinded separately; averaging their velocities first
would discard counterflow exchange. This is not vertically prognostic humidity
or thermodynamics, nor a momentum model.
"""
import numpy as np
from .solver import AdvectionSolver


def return_branches(lower_u, lower_v, balanced_u, balanced_v, upper_q_ratio, *, lower_mass_fraction=.25):
    """Return (water_fraction,u,v) branches and their humidity-weighted mean.

    eta*Ulower+(1-eta)*Uupper=Ubalanced. With q_upper/q_lower=r,
    lower water fraction is eta/[eta+(1-eta)r]. The common column W is
    redistributed to this fixed profile implicitly, without a column source.
    """
    eta, ratio = lower_mass_fraction, upper_q_ratio
    if not np.isfinite(eta) or not 0 < eta < 1 or not np.isfinite(ratio) or not 0 <= ratio <= 1:
        raise ValueError('Need mass fraction in(0,1) and upper/lower humidity ratio in[0,1]')
    arrays = [np.asarray(a, float) for a in (lower_u, lower_v, balanced_u, balanced_v)]
    if any(a.shape != arrays[0].shape or not np.isfinite(a).all() for a in arrays) or arrays[0].ndim != 2:
        raise ValueError('Need finite matching2-D branch wind fields')
    ul, vl, ub, vb = arrays
    upper_u, upper_v = (ub-eta*ul)/(1-eta), (vb-eta*vl)/(1-eta)
    low_weight = eta/(eta+(1-eta)*ratio)
    high_weight = 1-low_weight
    branches = ((low_weight, ul, vl), (high_weight, upper_u, upper_v))
    return branches, low_weight*ul+high_weight*upper_u, low_weight*vl+high_weight*upper_v


class LayerFluxSolver(AdvectionSolver):
    """Weighted sum of actual directional flux operators; reaction counted once."""
    def __init__(self, ny, nx, dx):
        super().__init__(ny, nx, dx, scheme='upwind', form='flux')
        self.layers = None

    def set_layers(self, branches):
        if (not branches or not np.isfinite([b[0] for b in branches]).all()
                or any(b[0] < 0 for b in branches) or abs(sum(b[0] for b in branches)-1) > 1e-12):
            raise ValueError('Branch water fractions must be nonnegative and sum to1')
        for _, u, v in branches:
            if u.shape != (self.ny, self.nx) or v.shape != u.shape or not np.isfinite(u).all() or not np.isfinite(v).all():
                raise ValueError('Need matching finite branch velocities')
        self.layers = branches

    def coefficients(self, u, v, K, lam):
        if self.layers is None:
            raise ValueError('Configure branch winds before a layered solve')
        result = None
        for weight, east, north in self.layers:
            if weight == 0:
                continue
            own = super().coefficients(east, north, K, lam)
            if result is None:
                result = [weight*a for a in own]
            else:
                for i, value in enumerate(own):
                    result[i] += weight*value
        return tuple(result)
