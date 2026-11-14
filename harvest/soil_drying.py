"""Surface drying and root stress with shared water counted once.

FAO-56 TEW and TAW overlap: surface plant-available water participates in both
diagnostics. Physical stocks partition that overlap rather than adding them.
All amounts are mm above fixed, inaccessible reference floors.
"""
from dataclasses import dataclass
import numpy as np


def _arrays(*values):
    arrays = np.broadcast_arrays(*[np.asarray(v, dtype=float) for v in values])
    if not all(np.isfinite(v).all() for v in arrays):
        raise ValueError('Finite soil water inputs required')
    return arrays


def _frozen(values):
    result = []
    for value in values:
        value = np.array(value, dtype=float, copy=True)
        value.setflags(write=False)
        result.append(value)
    return result


@dataclass(frozen=True)
class SoilProfile:
    top_capacity_mm: np.ndarray
    deep_capacity_mm: np.ndarray
    bound_capacity_mm: np.ndarray
    rew_mm: np.ndarray

    def __post_init__(self):
        values = _arrays(self.top_capacity_mm, self.deep_capacity_mm,
                         self.bound_capacity_mm, self.rew_mm)
        top, deep, bound, rew = values
        if np.any(top <= 0) or np.any(deep < 0) or np.any(bound < 0) or np.any(rew < 0) or np.any(rew >= top + bound):
            raise ValueError('Positive top capacity, nonnegative other capacities and REW < TEW required')
        for name, value in zip(self.__dataclass_fields__, _frozen(values)):
            object.__setattr__(self, name, value)

    @property
    def taw_mm(self):
        return self.top_capacity_mm + self.deep_capacity_mm

    @property
    def tew_mm(self):
        return self.top_capacity_mm + self.bound_capacity_mm


@dataclass(frozen=True)
class SoilState:
    top_mm: np.ndarray
    deep_mm: np.ndarray
    bound_mm: np.ndarray

    def __post_init__(self):
        values = _arrays(self.top_mm, self.deep_mm, self.bound_mm)
        if any(np.any(v < 0) for v in values):
            raise ValueError('Soil stocks must be nonnegative')
        for name, value in zip(self.__dataclass_fields__, _frozen(values)):
            object.__setattr__(self, name, value)

    @property
    def total_mm(self):
        return self.top_mm + self.deep_mm + self.bound_mm

    @property
    def root_available_mm(self):
        return self.top_mm + self.deep_mm


def soil_profile(theta_fc, theta_wp, root_depth_m, evaporation_depth_m, rew_mm):
    """Construct capacities from supplied water contents and effective depths."""
    fc, wp, zr, ze, rew = _arrays(theta_fc, theta_wp, root_depth_m, evaporation_depth_m, rew_mm)
    if np.any(wp < 0) or np.any(fc <= wp) or np.any(fc >= 1) or np.any(ze <= 0) or np.any(zr < ze):
        raise ValueError('Require 0 <= WP < FC < 1 and root depth >= evaporation depth > 0')
    with np.errstate(over='ignore', invalid='ignore'):
        available = 1000. * (fc - wp)
        return SoilProfile(available * ze, available * (zr - ze), 500. * wp * ze, rew)


def soil_state(profile, wet_fraction=0.):
    """Explicit initial fraction of each stock; initial water must be accounted."""
    fraction, top, deep, bound = _arrays(wet_fraction, profile.top_capacity_mm,
                                        profile.deep_capacity_mm, profile.bound_capacity_mm)
    if np.any((fraction < 0) | (fraction > 1)):
        raise ValueError('Initial wet fraction must be in [0,1]')
    return SoilState(top * fraction, deep * fraction, bound * fraction)


def surface_coefficients(depletion_mm, rew_mm, tew_mm, kcb, kcmax, exposed_fraction=1.):
    """FAO-56 equations 71/74. No water is created or removed by diagnostics."""
    de, rew, tew, basal, maximum, exposed = _arrays(depletion_mm, rew_mm, tew_mm, kcb, kcmax, exposed_fraction)
    if np.any(tew <= 0) or np.any(rew < 0) or np.any(rew >= tew) or np.any((de < 0) | (de > tew)):
        raise ValueError('Require 0 <= depletion <= TEW and 0 <= REW < TEW')
    if np.any(basal < 0) or np.any(maximum < basal) or np.any((exposed < 0) | (exposed > 1)):
        raise ValueError('Require 0 <= Kcb <= Kcmax and exposed fraction in [0,1]')
    kr = np.where(de <= rew, 1., (tew - de) / (tew - rew))
    ke = np.minimum(kr * (maximum - basal), exposed * maximum)
    return kr, ke


def root_stress(available_mm, taw_mm, depletion_fraction):
    """FAO-56 equation 84, written in available-water coordinates."""
    available, taw, p = _arrays(available_mm, taw_mm, depletion_fraction)
    if np.any(taw <= 0) or np.any((available < 0) | (available > taw)) or np.any((p < 0) | (p >= 1)):
        raise ValueError('Require 0 <= available <= TAW, TAW > 0 and 0 <= p < 1')
    return np.minimum(1., available / ((1. - p) * taw))


def adjusted_depletion_fraction(p_at_5mm, crop_et_mm_day):
    """FAO-56 daily demand adjustment; caller supplies the appropriate crop ET."""
    p, et = _arrays(p_at_5mm, crop_et_mm_day)
    if np.any((p < 0) | (p >= 1)) or np.any(et < 0):
        raise ValueError('Nonnegative crop ET and reference p in [0,1) required')
    return np.clip(p + .04 * (5. - et), .1, .8)


@dataclass(frozen=True)
class SoilStep:
    state: SoilState
    evaporation_mm: np.ndarray
    root_uptake_mm: np.ndarray
    drainage_mm: np.ndarray
    kr: np.ndarray
    ke: np.ndarray
    ks: np.ndarray
    root_potential_mm: np.ndarray


def soil_step(profile, state, water_mm, eto_mm_day, kcb, kcmax, depletion_fraction,
              *, exposed_fraction=1., step_days=1.):
    """Paid wetting/drainage, surface evaporation, then proportional root uptake.

    The explicit operator is an approximation, not an inferred local soil model.
    Incoming water fills the surface's below-WP pool, top available and then deep
    available pools. Excess drains before ET. No pond or groundwater is implied.
    """
    if isinstance(step_days, bool) or not np.isfinite(step_days) or not 0 < step_days <= 1:
        raise ValueError('Step duration must be in (0,1] days')
    top, deep, bound, ct, cd, cb, rew, water, eto, basal, maximum, p, exposed = _arrays(
        state.top_mm, state.deep_mm, state.bound_mm, profile.top_capacity_mm,
        profile.deep_capacity_mm, profile.bound_capacity_mm, profile.rew_mm,
        water_mm, eto_mm_day, kcb, kcmax, depletion_fraction, exposed_fraction)
    if np.any(top > ct) or np.any(deep > cd) or np.any(bound > cb) or np.any(water < 0) or np.any(eto < 0):
        raise ValueError('Bounded soil stocks and nonnegative input water/ETo required')
    remaining = water.copy()
    def fill(stock, capacity):
        nonlocal remaining
        new = np.minimum(capacity, stock + remaining)
        remaining = np.maximum(remaining - (new - stock), 0.)
        return new
    bound = fill(bound, cb)
    top = fill(top, ct)
    deep = fill(deep, cd)
    drainage = remaining
    kr, ke = surface_coefficients((ct + cb) - (top + bound), rew, ct + cb, basal, maximum, exposed)
    ks = root_stress(top + deep, ct + cd, p)
    with np.errstate(over='ignore', invalid='ignore'):
        potential = basal * eto * step_days
        evaporation_demand = ke * eto * step_days
    if not np.isfinite(potential).all() or not np.isfinite(evaporation_demand).all():
        raise ValueError('ET demand overflow')
    evaporation = np.minimum(evaporation_demand, top + bound)
    top_after = np.maximum(top - evaporation, 0.)
    bound_after = np.maximum(bound - np.maximum(evaporation - top, 0.), 0.)
    evaporation = (top - top_after) + (bound - bound_after)
    available = top_after + deep
    target = np.minimum(ks * potential, available)
    fraction = np.divide(target, available, out=np.zeros_like(available), where=available > 0)
    top_out = top_after * (1. - fraction)
    deep_out = deep * (1. - fraction)
    uptake = (top_after - top_out) + (deep - deep_out)
    return SoilStep(SoilState(top_out, deep_out, bound_after), evaporation, uptake,
                    drainage, kr, ke, ks, potential)
