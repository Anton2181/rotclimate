"""Dual-coefficient daily soil-water ledger: crop transpiration separated from
soil evaporation, with explicit drainage (Allen et al. 1998, FAO Irrigation
and Drainage Paper 56, chapter 7, equations 69-79 for the evaporation layer,
and chapter 8, equations 81-88 for the root zone).

One root-zone store (depletion Dr, 0..TAW) is the master account: every
millimetre leaves it once, as transpiration T, soil evaporation E, deep
drainage DP or runoff RO. The surface evaporation layer (depletion De, 0..TEW)
is a sub-account of the same water. It only gates evaporation (Kr, few) and is
never a second source, so the same water cannot be spent twice.

Per day, in this order:
  1. infiltration Pin = P - RO wets both accounts;
  2. evaporation Ke*ET0, Ke = min(Kr (Kcmax - Kcb), few Kcmax) (eq 71),
     Kr from the wetted layer (eq 74), few = 1 - fc (eq 75, rain only),
     limited to the water the exposed layer holds;
  3. transpiration Ks*Kcb*ET0, Ks from the wetted root zone (eq 84);
  4. T + E limited to the root-zone water present; stress acts on T only;
  5. water above field capacity drains (DP).
Transpiration from the exposed layer (eq 77's Tew), capillary rise, snow,
frozen soil and root growth are not represented: the root zone is a fixed
depth that persists across seasons (no free refill at sowing).
Reference: https://www.fao.org/4/x0490e/x0490e0a.htm (chapters 7 and 8).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DualWaterYear:
    initial_depletion: float
    final_depletion: float
    transpiration: np.ndarray
    potential_transpiration: np.ndarray
    evaporation: np.ndarray
    drainage: np.ndarray
    runoff: np.ndarray
    rain: np.ndarray
    root_depletion: np.ndarray        # end-of-day Dr
    layer_depletion: np.ndarray       # end-of-day De
    stress: np.ndarray                # Ks
    ledger_residual: float


def canopy_cover(kcb, kc_min=0.15, kc_max=1.20, height_m=1.0):
    """FAO56 eq 76: effective cover fraction from the basal coefficient."""
    kcb = np.asarray(kcb, float)
    x = np.clip((kcb - kc_min) / max(kc_max - kc_min, 1e-9), 0.0, 1.0)
    return np.clip(x ** (1.0 + 0.5 * height_m), 0.0, 0.99)


def kc_max(kcb, base=1.20):
    """FAO56 eq 72 in the standard climate (u2 = 2 m/s, RHmin = 45 %): max(1.2, Kcb + 0.05)."""
    return np.maximum(base, np.asarray(kcb, float) + 0.05)


def dual_soil_water(rain, reference_et, kcb, *, total_available, depletion_fraction,
                    total_evaporable, readily_evaporable, initial_depletion,
                    initial_layer_depletion=None, cover=None, runoff=0.0):
    """Daily dual-coefficient ledger over one chronological sequence.

    rain, reference_et, kcb, cover, runoff: daily arrays (mm, mm, -, -, mm).
    total_available TAW and readily-available fraction p for the root zone;
    total_evaporable TEW and readily_evaporable REW for the surface layer (mm).
    """
    P, et0, kb = (np.asarray(a, float) for a in np.broadcast_arrays(rain, reference_et, kcb))
    ro = np.broadcast_to(np.asarray(runoff, float), P.shape)
    fc = canopy_cover(kb) if cover is None else np.broadcast_to(np.asarray(cover, float), P.shape)
    if P.ndim != 1 or not len(P) or not all(np.isfinite(a).all() for a in (P, et0, kb, ro, fc)):
        raise ValueError('Finite one-dimensional daily series required')
    if np.any(P < 0) or np.any(et0 < 0) or np.any(kb < 0) or np.any(ro < 0) or np.any(ro > P) or np.any((fc < 0) | (fc >= 1)):
        raise ValueError('Nonnegative rain/ET/Kcb/runoff, runoff <= rain and 0 <= cover < 1 required')
    TAW, TEW, REW = float(total_available), float(total_evaporable), float(readily_evaporable)
    p = float(depletion_fraction)
    if not (TAW > 0 and 0 < REW < TEW <= TAW and 0 < p < 1):
        raise ValueError('Require 0 < REW < TEW <= TAW and 0 < p < 1')
    Dr = float(initial_depletion)
    De = float(TEW if initial_layer_depletion is None else initial_layer_depletion)
    if not (0 <= Dr <= TAW and 0 <= De <= TEW):
        raise ValueError('Initial depletions must lie within their capacities')
    d0 = Dr
    kmax = kc_max(kb)
    n = len(P)
    T = np.zeros(n); Tp = np.zeros(n); E = np.zeros(n); DP = np.zeros(n)
    Drs = np.zeros(n); Des = np.zeros(n); Ks = np.zeros(n)
    for i in range(n):
        pin = P[i] - ro[i]
        # 1. wetting: the layer and the root zone receive the same infiltration
        de = max(De - pin, 0.0)
        dr = Dr - pin                                   # may go below 0 (above field capacity) until drainage
        # 2. evaporation from the exposed, wetted fraction (eq 71-75)
        few = 1.0 - fc[i]
        kr = 1.0 if de <= REW else (TEW - de) / (TEW - REW)
        ke = min(kr * (kmax[i] - kb[i]), few * kmax[i])
        e = max(ke, 0.0) * et0[i]
        e = min(e, few * (TEW - de))                    # the exposed layer cannot give more than it holds
        # 3. transpiration under root-zone stress (eq 84), on the wetted root zone
        dr_pos = max(dr, 0.0)
        ks = 1.0 if dr_pos <= p * TAW else max((TAW - dr_pos) / ((1 - p) * TAW), 0.0)
        tp = kb[i] * et0[i]
        t = ks * tp
        # 4. one store: T + E cannot exceed the water present in the root zone
        present = TAW - dr                              # mm above wilting point after wetting
        if t + e > present:
            scale = max(present, 0.0) / (t + e) if t + e > 0 else 0.0
            t *= scale; e *= scale
        dr = dr + t + e
        # 5. drainage of water above field capacity
        dp = max(-dr, 0.0)
        dr = max(dr, 0.0)
        de = min(de + (e / few if few > 0 else 0.0), TEW)
        Dr, De = dr, de
        T[i], Tp[i], E[i], DP[i], Drs[i], Des[i], Ks[i] = t, tp, e, dp, dr, de, ks
    # ledger: water above wilting point, S = TAW - Dr
    residual = (TAW - d0) + P.sum() - ro.sum() - T.sum() - E.sum() - DP.sum() - (TAW - Dr)
    scale = max(1.0, TAW + P.sum())
    if not np.isfinite(residual) or abs(residual) > 1e-9 * scale:
        raise RuntimeError('Dual soil-water ledger did not close')
    if np.any(Drs < -1e-12) or np.any(Drs > TAW + 1e-9) or np.any(Des < -1e-12) or np.any(Des > TEW + 1e-9):
        raise RuntimeError('Depletion left its bounds')
    return DualWaterYear(d0, Dr, T, Tp, E, DP, np.array(ro), P, Drs, Des, Ks, float(residual))


def kcb_curve(days, sowing_day, harvest_day, *, fractions=(0.35, 0.30, 0.20, 0.15),
              kcb_ini=0.15, kcb_mid=1.10, kcb_end=0.15, kcb_bare=0.0):
    """Piecewise-linear basal coefficient (FAO56 fig. 34 shape) between sowing and harvest.

    days: day indices of the sequence; sowing_day/harvest_day on the same axis.
    fractions: initial, development, mid-season and late-season shares of the
    season (declared assumptions, not values taken from FAO56 table 11).
    Outside the season the ground is bare (kcb_bare).
    """
    d = np.asarray(days, float)
    L = float(harvest_day - sowing_day)
    if L <= 0:
        raise ValueError('Harvest must follow sowing')
    f = np.cumsum(fractions) / np.sum(fractions)
    x = (d - sowing_day) / L
    k = np.full(d.shape, float(kcb_bare))
    ini = (x >= 0) & (x < f[0]); k[ini] = kcb_ini
    dev = (x >= f[0]) & (x < f[1]); k[dev] = kcb_ini + (kcb_mid - kcb_ini) * (x[dev] - f[0]) / (f[1] - f[0])
    mid = (x >= f[1]) & (x < f[2]); k[mid] = kcb_mid
    late = (x >= f[2]) & (x <= 1); k[late] = kcb_mid + (kcb_end - kcb_mid) * (x[late] - f[2]) / (f[3] - f[2])
    return k
