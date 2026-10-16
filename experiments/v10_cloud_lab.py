"""Small closed-parcel laboratory; never advances a regional climate.

Compare thermodynamic path integration and symmetric exchange between two
air populations. Constant dry-air Cp/Lv and liquid-only saturation deliberately
match the frozen prototype. Precipitate leaves vapor instantly, with the same
zero exported enthalpy convention; diagnosed pressure work is explicit.

This is not a convection closure, grid-refinement experiment or cloud/rain
storage scheme. Two-population exchange conserves BOTH populations rather
than diluting a parcel with an unlimited external water/heat reservoir.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from experiments import v10_parcel_condensation as frozen

base = frozen.base
RD = 287.05
KAPPA = RD/base.CP


@dataclass(frozen=True)
class Air:
    temperature_c: float
    vapor_ratio: float

    def validate(self, pressure_pa):
        values = [self.temperature_c, self.vapor_ratio, pressure_pa]
        if not np.isfinite(values).all() or self.vapor_ratio < 0 or pressure_pa <= 0:
            raise ValueError('Need finite temperature, nonnegative vapor and positive pressure.')
        saturation(self.temperature_c, pressure_pa)


def saturation(temperature_c, pressure_pa):
    return float(base.saturation(np.array([temperature_c], float), np.array([pressure_pa], float))[0])


def enthalpy(temperature_c, vapor_ratio):
    """Prototype sensible + vapor latent energy per kg of dry air, without gz."""
    return base.CP*(np.asarray(temperature_c)+273.15)+base.LV*np.asarray(vapor_ratio)


def adjust(temperature_c, vapor_ratio, pressure_pa):
    t, q = np.broadcast_arrays(np.asarray(temperature_c, float), np.asarray(vapor_ratio, float))
    p = np.broadcast_to(np.asarray(pressure_pa, float), t.shape)
    if not np.isfinite(q).all() or (q < 0).any() or not np.isfinite(p).all() or (p <= 0).any():
        raise ValueError('Invalid parcel water/pressure.')
    energy = enthalpy(t, q)
    remaining, condensed, after = base.adjust(q, energy, np.ones_like(q), np.zeros_like(q), p)
    return after, remaining, condensed


def pressure_path(start_pa, end_pa, intervals):
    if not np.isfinite([start_pa, end_pa]).all() or min(start_pa, end_pa) <= 0 or end_pa > start_pa:
        raise ValueError('Ascending path needs positive, nonincreasing pressure.')
    if isinstance(intervals, bool) or not isinstance(intervals, (int, np.integer)) or not 1 <= intervals <= 4096:
        raise ValueError('Use one to 4096 integer pressure intervals.')
    path = np.exp(np.linspace(np.log(start_pa), np.log(end_pa), intervals+1))
    path[0] = start_pa; path[-1] = end_pa
    return path


def exchange(temperature_c, vapor_ratio, masses, fraction):
    """Symmetric dry-mass exchange, preserving each population's dry mass.

Equivalent to swapping fraction*m0*m1/(m0+m1) dry mass in both directions.
At fraction=1 both populations have the original weighted mean T and vapor.
At fraction=0 neither changes. No extra environmental source is introduced.
"""
    t = np.asarray(temperature_c, float); q = np.asarray(vapor_ratio, float); m = np.asarray(masses, float)
    if t.shape != (2,) or q.shape != (2,) or m.shape != (2,) or not np.isfinite([*t, *q, *m, fraction]).all() or (q < 0).any() or (m <= 0).any() or not 0 <= fraction <= 1:
        raise ValueError('Invalid two-population exchange.')
    if fraction == 0:
        return t.copy(), q.copy()
    mean_t = np.average(t, weights=m); mean_q = np.average(q, weights=m)
    return (1-fraction)*t+fraction*mean_t, (1-fraction)*q+fraction*mean_q


def _finish(path, history_t, history_q, history_rain, masses, work):
    t = np.array(history_t); q = np.array(history_q); rain = np.array(history_rain); m = np.asarray(masses)
    if not all(np.isfinite(a).all() for a in (t, q, rain, m)) or not np.isfinite(work) or (q < 0).any() or (rain < 0).any():
        raise FloatingPointError('Invalid closed-parcel trajectory.')
    water_error = np.sum(m*q[-1])+rain[-1]-np.sum(m*q[0])
    energy_error = np.sum(m*enthalpy(t[-1], q[-1]))-np.sum(m*enthalpy(t[0], q[0]))-work
    if abs(water_error) > 1e-11 or abs(energy_error) > 1e-6:
        raise FloatingPointError('Closed-parcel water/enthalpy ledger failed.')
    return {'pressure_pa': np.asarray(path), 'temperature_c': t, 'vapor_ratio': q,
        'cumulative_rain_kg_per_kg_initial_dry_air': rain, 'dry_mass_kg': m,
        'pressure_work_j_per_kg_initial_dry_air': float(work),
        'water_error_kg_per_kg_dry_air': float(water_error), 'enthalpy_error_j_per_kg_dry_air': float(energy_error)}


def ascend(air, start_pa, end_pa, intervals):
    """Same endpoints; dry pressure step followed by coupled liquid adjustment."""
    air.validate(start_pa); path = pressure_path(start_pa, end_pa, intervals)
    t = np.array([air.temperature_c]); q = np.array([air.vapor_ratio])
    temperatures = [t.copy()]; vapors = [q.copy()]; rain = [0.]; work = 0.
    for old_p, p in zip(path[:-1], path[1:]):
        dry = (t+273.15)*(p/old_p)**KAPPA-273.15
        work += float(base.CP*(dry-t).sum())
        t, q, condensed = adjust(dry, q, p)
        temperatures.append(t.copy()); vapors.append(q.copy()); rain.append(rain[-1]+float(condensed.sum()))
    return _finish(path, temperatures, vapors, rain, [1.], work)


def ascend_pair(parcel, environment, fraction, start_pa, end_pa, intervals, total_exchange):
    """Both populations traverse the same path; mixing exposure is grid-invariant.

Environmental starting T/q are declared manufactured inputs. This does not
replenish an entraining plume or prescribe a real environment along a column.
"""
    parcel.validate(start_pa); environment.validate(start_pa)
    if not np.isfinite([fraction, total_exchange]).all() or not 0 < fraction < 1 or not 0 <= total_exchange <= 1:
        raise ValueError('Invalid population mass or total exchange fraction.')
    path = pressure_path(start_pa, end_pa, intervals)
    per_step = 1. if total_exchange == 1 else -np.expm1(np.log1p(-total_exchange)/intervals)
    masses = np.array([fraction, 1-fraction])
    t = np.array([parcel.temperature_c, environment.temperature_c]); q = np.array([parcel.vapor_ratio, environment.vapor_ratio])
    temperatures = [t.copy()]; vapors = [q.copy()]; rain = [0.]; work = 0.
    for old_p, p in zip(path[:-1], path[1:]):
        dry = (t+273.15)*(p/old_p)**KAPPA-273.15
        work += float(np.sum(masses*base.CP*(dry-t)))
        mixed_t, mixed_q = exchange(dry, q, masses, per_step)
        t, q, condensed = adjust(mixed_t, mixed_q, p)
        temperatures.append(t.copy()); vapors.append(q.copy()); rain.append(rain[-1]+float(np.sum(masses*condensed)))
    result = _finish(path, temperatures, vapors, rain, masses, work)
    result.update(total_exchange_fraction=float(total_exchange), per_step_exchange_fraction=float(per_step))
    return result


def continuous_reference(air, start_pa, end_pa):
    """Independent ODE integration of this prototype's liquid-only thermodynamics.

Cp*dT/dln(p) = Rd*T - Lv*dr/dln(p). After first saturation r=rs(T,p),
including the exact derivatives of the project's saturation formula. This
avoids treating an endpoint saturation adjustment as the reference solution.
"""
    air.validate(start_pa); pressure_path(start_pa, end_pa, 1)
    t0 = air.temperature_c; q0 = air.vapor_ratio
    if q0 > saturation(t0, start_pa)+1e-12:
        raise ValueError('Reference starts with unsaturated or saturated vapor, not a supersaturated initial adjustment.')
    dry = lambda p: (t0+273.15)*(p/start_pa)**KAPPA-273.15
    if q0 <= saturation(dry(end_pa), end_pa) or start_pa == end_pa:
        t = dry(end_pa); rain = 0.; work = base.CP*(t-t0); q = q0; onset = None
    else:
        if abs(q0-saturation(t0, start_pa)) <= 1e-14:
            root = np.log(start_pa); onset = float(start_pa)
        else:
            root = brentq(lambda logp: saturation(dry(np.exp(logp)), np.exp(logp))-q0,
                          np.log(end_pa), np.log(start_pa), xtol=1e-13)
            onset = float(np.exp(root))
        at_lcl = dry(onset)
        def rhs(logp, state):
            temp = state[0]; p = np.exp(logp)
            rs, derivative_t = base.saturation(np.array([temp-273.15]), np.array([p]), True)
            # rs = epsilon*es/(p-es), so partial rs / partial ln(p) at fixed T.
            derivative_logp = -rs[0]*(1+rs[0]/.622)
            slope = (RD*temp-base.LV*derivative_logp)/(base.CP+base.LV*derivative_t[0])
            return [slope, RD*temp]
        solution = solve_ivp(rhs, (root, np.log(end_pa)), [at_lcl+273.15, 0.], method='DOP853', rtol=1e-11, atol=[1e-10, 1e-6])
        if not solution.success:
            raise FloatingPointError('Independent saturated-path ODE failed.')
        t = float(solution.y[0, -1]-273.15); q = saturation(t, end_pa)
        rain = q0-q; work = base.CP*(at_lcl-t0)+float(solution.y[1, -1])
        if rain < -1e-12:
            raise FloatingPointError('Ascending saturated reference gained vapor.')
    error = float(enthalpy(t, q)-enthalpy(t0, q0)-work)
    if abs(error) > 1e-5:
        raise FloatingPointError('Independent reference enthalpy/work balance failed.')
    return {'temperature_c': float(t), 'vapor_ratio': float(q), 'rain_kg_per_kg_dry_air': float(rain),
        'first_saturation_pressure_pa': onset, 'pressure_work_j_per_kg_dry_air': float(work),
        'enthalpy_error_j_per_kg_dry_air': error}


def dry_descent(air, start_pa, end_pa):
    """Toy lee-side compression after rain has already left; no re-evaporation."""
    air.validate(start_pa)
    if not np.isfinite(end_pa) or end_pa < start_pa:
        raise ValueError('Descent needs increasing positive pressure.')
    temperature = (air.temperature_c+273.15)*(end_pa/start_pa)**KAPPA-273.15
    result = Air(float(temperature), air.vapor_ratio)
    result.validate(end_pa)
    return result
