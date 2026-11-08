"""Delta fans on the map (owner, 8 Nov 2026: "I don't see why we couldn't have a Nile-like delta in our world, we
shouldn't prevent it").

Every drawn river that ends at the sea or in a terminal lake builds a fan whose area comes from the Earth fit of
calibration/delta_fans_20261108 (Edmonds et al. 2020 deltas; HydroRIVERS discharge; BQART sediment load, Syvitski &
Milliman 2007; wave exposure of the mouth): A = 10^(c . features), the median delta for such a river. Land within
r = sqrt(2 A / pi) of the mouth (a half disc of area A) is irrigable at s_fan x exp(-H / 5 m), H its height above the
nearest drawn river (the D2 / D2b gate: delta land is low against its channels, not against the mouth); the map takes the larger of this and the river-distance rule.

The model is data/delta_fan_model.json; without it nothing changes.
"""
from __future__ import annotations

import json
from pathlib import Path

import numba
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "data" / "delta_fan_model.json"
HAND_H0 = 5.0


@numba.njit(cache=True)
def _acc_max(order, recv, val):
    out = val.copy()
    for k in range(order.size - 1, -1, -1):
        c = order[k]; r = recv[c]
        if r >= 0 and out[c] > out[r]:
            out[r] = out[c]
    return out


def bqart(q_m3s, area_km2, relief_km, t_c):
    """Pristine sediment load, Mt/yr (Syvitski & Milliman 2007, B = 1): the same formula as the Earth fit."""
    qk = np.asarray(q_m3s, float) * 365.25 * 86400 / 1e9
    base = 0.0006 * qk ** 0.31 * np.asarray(area_km2, float) ** 0.5 * np.maximum(np.asarray(relief_km, float), 0.01)
    return np.where(np.asarray(t_c) >= 2.0, base * np.asarray(t_c), 2.0 * base)


def exposure(y, x, water, px_km, reach_km=1500.0, n=32):
    """Share of n directions from a mouth whose open-water fetch reaches reach_km; the map edge counts as open sea."""
    H, W = water.shape; hits = 0; step = 2.5 / px_km
    for k in range(n):
        az = 2 * np.pi * k / n; at_sea = False; ok = False; s = step
        while s * px_km <= reach_km:
            yy = int(round(y - s * np.cos(az))); xx = int(round(x + s * np.sin(az)))
            if not (0 <= yy < H and 0 <= xx < W):
                ok = at_sea; break
            if water[yy, xx]:
                at_sea = True
            elif at_sea or s * px_km > 10.0:
                break
            s += step
        else:
            ok = at_sea
        hits += ok
    return hits / n


def features(model, q, qs, exp_):
    names = model["features"]
    vals = {"const": 1.0, "log10_q": np.log10(max(q, 1e-6)), "log10_qs": np.log10(max(qs, 1e-6)), "exposure": exp_}
    return np.array([vals[k] for k in names])


def fans(meta, arrays, t_months, p_months, days_per_bin):
    """Irrigable share from delta fans at source resolution (None without a model or a height map) and a list of the
    deltas built."""
    if not MODEL.exists():
        return None, []
    terrain = meta.get("world", {}).get("terrain_file", "")
    if not terrain:
        return None, []
    from rotclimate import routing as R
    from rotclimate.geography import source_layers
    model = json.loads(MODEL.read_text())
    L = source_layers(); land = L["land"].astype(bool); rivers = L["rivers"].astype(bool) & land
    H, W = land.shape
    params = json.loads((ROOT / meta["world"].get("params_file", "")).read_text()) if meta["world"].get("params_file") else {}
    tier_tops = meta["world"]["tier_tops"]; map_width_mi = meta["width"] * meta["mi_per_px"]
    px_km = map_width_mi * 1.609344 / W
    ro = R.runoff_from_months(t_months, p_months, days_per_bin)
    up = lambda a: ndi.map_coordinates(a, np.mgrid[0:H, 0:W].astype(float) * np.array([a.shape[0] / H, a.shape[1] / W])[:, None, None]  # noqa: E731
                                       + (np.array([a.shape[0] / H, a.shape[1] / W])[:, None, None] * 0.5 - 0.5), order=1, mode="nearest")
    lowres_land = ndi.zoom(land.astype(float), (ro.shape[0] / H, ro.shape[1] / W), order=1) > 0.5
    _, (iy, ix) = ndi.distance_transform_edt(~lowres_land, return_indices=True)
    ro_px = up(ro[iy, ix]); t_px = up(np.mean(t_months, axis=0)[iy, ix])
    q, recv, _, _ = R.discharge(ro_px, tier_tops, terrain, map_width_mi)
    z, _, _ = R.surface(tier_tops, terrain)
    level = R.lake_levels(terrain); through = ~land & (level > 0); net = land | through
    recv2, order = R._flood(np.where(land, z, np.where(through, level, -1e9)), net, R.NB)
    cell = np.where(land, px_km * px_km, 0.0).ravel()
    area = R._accumulate(order, recv2, cell).reshape(H, W)
    relief_top = _acc_max(order, recv2, np.where(land, z, 0.0).ravel()).reshape(H, W)
    tsum = R._accumulate(order, recv2, (np.where(land, t_px, 0.0) * np.where(land, px_km * px_km, 0.0)).ravel()).reshape(H, W)
    water = ~net                                                   # the sea and terminal lakes
    near_water = ndi.binary_dilation(water, np.ones((3, 3)), border_value=1)
    mouth_cells = rivers & near_water & (recv2.reshape(H, W) < 0)
    lab, n = ndi.label(rivers, structure=np.ones((3, 3)))
    _, (iy2, ix2) = ndi.distance_transform_edt(~rivers, return_indices=True)
    hand = np.where(land, np.maximum(z - z[iy2, ix2], 0.0), 0.0)        # height above the nearest drawn river (D2)
    out = np.zeros((H, W), np.float32); built = []
    Y, X = np.mgrid[0:H, 0:W]
    for i in range(1, n + 1):
        m = mouth_cells & (lab == i)
        if not m.any():
            continue
        ys, xs = np.nonzero(m); k = int(np.argmax(q[ys, xs])); y0, x0 = int(ys[k]), int(xs[k])
        Q = float(q[y0, x0]); A = float(area[y0, x0]); Rk = max(float(relief_top[y0, x0] - z[y0, x0]), 0.0) / 1000.0
        T = float(tsum[y0, x0] / max(A, 1e-9)); Qs = float(bqart(Q, A, Rk, T)); E = exposure(y0, x0, water, px_km)
        if Q < model.get("min_q_m3s", 10.0):
            continue
        Ad = float(10 ** (features(model, Q, Qs, E) @ np.array(model["coef"])))
        r_px = np.sqrt(2.0 * Ad / np.pi) / px_km
        box = (slice(max(0, int(y0 - r_px) - 1), min(H, int(y0 + r_px) + 2)), slice(max(0, int(x0 - r_px) - 1), min(W, int(x0 + r_px) + 2)))
        inside = land[box] & ((Y[box] - y0) ** 2 + (X[box] - x0) ** 2 <= r_px ** 2)
        hgt = hand[box]
        out[box] = np.maximum(out[box], np.where(inside, model["s_fan"] * np.exp(-hgt / HAND_H0), 0.0))
        built.append(dict(x=x0, y=y0, q_m3s=round(Q, 1), basin_km2=round(A), relief_km=round(Rk, 3), t_c=round(T, 1),
                          qs_mt=round(Qs, 3), exposure=round(E, 3), area_km2=round(Ad, 1), radius_km=round(r_px * px_km, 1)))
    return out, built
