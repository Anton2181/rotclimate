"""Conservative unresolved storm exchange on a padded regional grid.

The supplied Gaussian must be symmetric and normalized (reflecting edges).
Fixed outer-ring water acts as a reservoir when used by the regional solver;
exchange across that ring is a boundary supply, not internal water creation.
This fixes storm exchange only, not the model's mean-wind concentration form.
"""
import numpy as np


def conservative_exchange(rate, gaussian, column_mass=None):
    """Return nonnegative loss coefficient and incoming-water target.

    For q_i=W_i/c_i, the pair conductance is
    G_ij * (rate_i*c_i + rate_j*c_j)/2. Its flux into i is
    C_ij*(q_j-q_i), exactly opposite to its flux into j. Therefore water
    sums to zero even when rates and air-column masses vary. Uniform specific
    humidity is an equilibrium; uniform column water need not be over terrain.
    Units: rates 1/s, relative column mass c dimensionless, water mm.

    The positive incoming term is evaluated explicitly by Picard iteration;
    its loss coefficient enters the existing implicit linear solve.
    """
    rate = np.asarray(rate, float)
    mass = np.ones_like(rate) if column_mass is None else np.asarray(column_mass, float)
    if (rate.ndim != 2 or mass.shape != rate.shape or
            not np.isfinite(rate).all() or not np.isfinite(mass).all() or
            (rate < 0).any() or (mass <= 0).any()):
        raise ValueError('Need finite 2-D nonnegative rates and positive matching column masses')
    conductance = rate * mass
    loss = .5 * (rate + gaussian(conductance) / mass)

    def target(water):
        incoming = .5 * (conductance * gaussian(water / mass) + gaussian(rate * water))
        return np.divide(incoming, loss, out=np.zeros_like(incoming), where=loss > 0)

    return loss, target


def exchange_budget(water, loss, target):
    """Full-domain cancellation and supply from the prescribed outer ring.

    Cell sums are mm/day times cell count, not a planet-wide water budget.
    Multiply by cell area to obtain volume. Positive boundary supply delivers
    water to the solved interior; the ring has the equal and opposite flux.
    """
    incoming = target(water)
    flux = loss * (incoming - water) * 86400.
    interior = float(flux[1:-1, 1:-1].sum())
    throughput = float(np.abs(flux).sum())
    net = float(flux.sum())
    gross = float((loss * (np.abs(incoming) + np.abs(water)) * 86400.).sum())
    return dict(net_cell_mm_day=net, throughput_cell_mm_day=throughput,
                gross_exchange_cell_mm_day=gross,
                relative_closure=abs(net) / max(gross, 1e-30),
                boundary_supply_cell_mm_day=interior)
