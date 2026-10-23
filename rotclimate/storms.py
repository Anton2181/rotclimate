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


class RainoutExchange:
    """Short conservative storm hops with condensation left where it forms.

    A hop is a nonnegative Markov step of the symmetric exchange operator.
    Its frequency bounds every local loss coefficient, so no hop exports more
    vapor than a cell holds. After each hop, vapor above the local capacity
    condenses; only the remaining vapor takes the next hop. Thus the event's
    final vapor plus accumulated local condensate sums to its initial water.

    The caller supplies a Gaussian of width sigma/sqrt(steps). At uniform
    rate and mass, without condensation, the steps approximate one Gaussian
    of width sigma. The generator is frequency * (event - identity).
    This is an unresolved storm closure, not a resolved cloud trajectory.
    """

    def __init__(self, rate, gaussian, capacity, column_mass=None, steps=6):
        if not isinstance(steps, int) or isinstance(steps, bool) or steps < 1:
            raise ValueError('Storm rainout needs a positive integer hop count')
        self.loss, self.target = conservative_exchange(rate, gaussian, column_mass)
        self.capacity = np.asarray(capacity, float).copy()
        if (self.capacity.shape != self.loss.shape or
                not np.isfinite(self.capacity).all() or (self.capacity < 0).any()):
            raise ValueError('Need finite nonnegative matching storm capacities')
        self.frequency = float(self.loss.max())
        self.steps = steps
        self._water = None
        self._partition = None

    def partition(self, water):
        """Return final vapor and local condensate, both in mm per event."""
        water = np.asarray(water, float)
        if (water.shape != self.loss.shape or not np.isfinite(water).all() or
                (water < 0).any()):
            raise ValueError('Need finite nonnegative matching column water')
        # Moisture iteration and diagnostics request both parts at the same W.
        # Compare values, rather than identity: the solver can update borders
        # in place. Cached arrays are internal; callers must not mutate them.
        if self._water is not None and np.array_equal(water, self._water):
            return self._partition
        vapor = water.copy()
        condensed = np.zeros_like(water)
        if self.frequency > 0:
            fraction = self.loss / self.frequency
            for _ in range(self.steps):
                vapor = (1. - fraction) * vapor + fraction * self.target(vapor)
                excess = np.maximum(vapor - self.capacity, 0.)
                vapor = np.minimum(vapor, self.capacity)
                condensed += excess
        self._water = water.copy()
        self._partition = vapor, condensed
        return self._partition

    def __call__(self, water):
        return self.partition(water)[0]

    def condensate(self, water):
        return self.partition(water)[1]

    def transport(self, water):
        """Balanced target for diagnostics before subtracting rain as a sink."""
        vapor, condensed = self.partition(water)
        return vapor + condensed


def exchange_budget(water, loss, target, condensate=None):
    """Full-domain cancellation and supply from the prescribed outer ring.

    Cell sums are mm/day times cell count, not a planet-wide water budget.
    Multiply by cell area to obtain volume. Positive boundary supply delivers
    water to the solved interior; the ring has the equal and opposite flux.
    With rainout, transport includes vapor plus local condensate; condensate
    is subsequently counted as rain. Vapor exchange alone loses that water.
    """
    incoming = target(water)
    extra = {}
    if condensate is not None:
        condensed = condensate(water)
        extra = dict(condensation_cell_mm_day=float((loss * condensed * 86400.).sum()),
                     vapor_net_cell_mm_day=float((loss * (incoming-water) * 86400.).sum()))
        incoming = incoming + condensed
    flux = loss * (incoming - water) * 86400.
    interior = float(flux[1:-1, 1:-1].sum())
    throughput = float(np.abs(flux).sum())
    net = float(flux.sum())
    gross = float((loss * (np.abs(incoming) + np.abs(water)) * 86400.).sum())
    return dict(net_cell_mm_day=net, throughput_cell_mm_day=throughput,
                gross_exchange_cell_mm_day=gross,
                relative_closure=abs(net) / max(gross, 1e-30),
                boundary_supply_cell_mm_day=interior, **extra)
