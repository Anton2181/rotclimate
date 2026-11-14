"""Flood-basin land rule (calibration/floodplain_rule_20261114, amendments A1/A2; ported in
calibration/fantasy_floodplain_20261114).

Low land beside a navigable river whose flood ends in late summer or early autumn, with little rain during the flood,
is a flood basin: full water, sown every year, one cool-season cereal (better of wheat and barley), farmed share F_B.
"""
import numpy as np
from scipy import ndimage as ndi

HAND_M, NEAR_KM, RAIN_MM, F_B = 5.0, 30.0, 100.0, 0.95
LAST_AFTER_SOLSTICE = (6, 7, 8, 9)          # 0-based months after the winter solstice month (Earth: July-October)


def last_of_longest_run(flags):
    """flags: bool[12]. 0-based index of the last month of the longest cyclic run of True (ties: earliest end); None if none/all."""
    flags = np.asarray(flags, bool)
    if not flags.any() or flags.all(): return None
    best, end = 0, None
    for start in range(12):
        if flags[start] and not flags[(start - 1) % 12]:
            k = 0
            while flags[(start + k) % 12]: k += 1
            e = (start + k - 1) % 12
            if k > best or (k == best and e < end): best, end = k, e
    return end


def candidate(land, z, navigable, km_px):
    """Bool mask: land <= HAND_M above and <= NEAR_KM from the nearest navigable cell (same grid)."""
    d, (iy, ix) = ndi.distance_transform_edt(~navigable, return_indices=True)
    return land & (d * km_px <= NEAR_KM) & (z - z[iy, ix] <= HAND_M)


def qualifying(land, catchment, flow, rain12):
    """flow [12, n+1] (month 0 = winter-solstice month), catchment basin ids, rain12 [12, ...] mm."""
    above = flow > 1.0
    ok = np.zeros(flow.shape[1], bool)
    for b in range(1, flow.shape[1]):
        ok[b] = last_of_longest_run(above[:, b]) in LAST_AFTER_SOLSTICE
    flood_rain = np.zeros(catchment.shape)
    for m in range(12):
        flood_rain += np.where(above[m][catchment], np.nan_to_num(rain12[m]), 0.0)
    return land & (catchment > 0) & ok[catchment] & (flood_rain < RAIN_MM), ok, flood_rain


def basin_unit_capacity(analyse_out, arable, need_kcal):
    """People per km2 per unit farmed share on basin land from an analyse() run at irrigation 1."""
    winter = np.maximum(analyse_out['kcal_wheat'], analyse_out['kcal_barley'])
    return winter * arable * 100.0 / need_kcal


def blend(capacity, share, unit, f_b=F_B):
    return (1 - share) * capacity + share * unit * f_b
