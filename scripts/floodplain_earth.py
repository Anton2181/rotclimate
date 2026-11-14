"""Floodplain land rule on the Earth harvest grid (calibration/floodplain_rule_20261114/plan.json).

Wraps scripts/land_people_earth.py (adopted options: slope arable, HAND-gated irrigation) without changing it:
the crop analysis runs as before, then qualifying flood-basin land gets full water, annual sowing, one crop and
farmed share F_b. Writes output/land_people/earth_floodplain/{earth.npz, regions.json} (F_b 0.95) and
output/floodplain_rule_20261114/fields.npz (ignored)."""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import land_people_earth as L
import land_people as LP
from arable_slope_earth import etopo_window
from polity import seasons as S, transport as X

PLAN = ROOT / 'calibration/floodplain_rule_20261114/plan.json'; OUT = ROOT / 'output/floodplain_rule_20261114'
GRID = ROOT / 'output/land_people/earth_floodplain'
HAND_M, NEAR_KM, RAIN_MM, LAST_MONTHS, F_B, F_SENS = 5.0, 30.0, 100.0, (7, 8, 9, 10), 0.95, 0.60


def candidate_share(shape, land):
    """Share of each 5' cell's 1' land that is <= 5 m above and <= 30 km from a navigable river (banded, as L.irrigation)."""
    nav, _ = L.river_masks(shape); z = etopo_window().astype(float); H = nav.shape[0]; n = L.RES * L.SUB
    cand = np.zeros(nav.shape, bool); band, pad = 4 * n, n // 2
    for b0 in range(0, H, band):
        lo, hi = max(b0 - pad, 0), min(b0 + band + pad, H)
        lat = L.WINDOW['lat'][1] - (b0 + band / 2) / n; samp = (L.KM_DEG / n, L.KM_DEG * np.cos(np.radians(lat)) / n)
        d, (iy, ix) = ndi.distance_transform_edt(~nav[lo:hi], sampling=samp, return_indices=True)
        zz = z[lo:hi]; c = (zz > 0) & (zz - zz[iy, ix] <= HAND_M) & (d <= NEAR_KM)
        cand[b0:min(b0 + band, H)] = c[b0 - lo:b0 - lo + min(band, H - b0)]
    share = cand.reshape(shape[0], L.SUB, shape[1], L.SUB).mean((1, 3))
    return np.where(land, share, 0.0), nav.reshape(shape[0], L.SUB, shape[1], L.SUB).any((1, 3))


def last_of_longest_run(months):
    """months: bool[12]. Last month (1-12) of the longest cyclic run of True; ties -> earliest-ending; None if empty/all."""
    if not months.any(): return None
    if months.all(): return None
    best, best_end = 0, None
    for start in range(12):
        if months[start] and not months[(start - 1) % 12]:
            k = 0
            while months[(start + k) % 12]: k += 1
            end = (start + k - 1) % 12 + 1
            if k > best or (k == best and end < best_end): best, best_end = k, end
    return best_end


def qualifying(shape, land, nav5, T, Tx, Tn, P, LAT):
    f = S.fields(np.nan_to_num(T), np.nan_to_num(Tx), np.nan_to_num(Tn), np.nan_to_num(P), LAT)
    runoff = np.where(land, f['runoff'], 0.0); elev = np.nan_to_num(L.wc('elev')[L.window_slices()])
    basin, nb, _ = X.river_network(nav5 & land, land, ~land, elev); catchment = X.catchments(basin, land, L.KM_DEG / L.RES)
    flow = S.basin_flow(runoff, catchment, nb); above = flow > 1.0
    timing_ok = np.zeros(nb + 1, bool); last = {}
    for b in range(1, nb + 1):
        e = last_of_longest_run(above[:, b]); last[b] = e; timing_ok[b] = e in LAST_MONTHS
    flood_rain = np.zeros(shape)
    for m in range(12):
        flood_rain += np.where(above[m][catchment], np.nan_to_num(P[m]), 0.0)
    q = land & (catchment > 0) & timing_ok[catchment] & (flood_rain < RAIN_MM)
    return q, dict(catchment=catchment, flow=flow, last=last, timing_ok=timing_ok, flood_rain=flood_rain)


def main():
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    OUT.mkdir(parents=True, exist_ok=True); GRID.mkdir(parents=True, exist_ok=True)
    rs, cs = L.window_slices(); elev = L.wc('elev')[rs, cs]
    T = np.stack([L.wc('tavg', m)[rs, cs] for m in range(1, 13)]); P = np.stack([L.wc('prec', m)[rs, cs] for m in range(1, 13)])
    Tx = np.stack([L.wc('tmax', m)[rs, cs] for m in range(1, 13)]); Tn = np.stack([L.wc('tmin', m)[rs, cs] for m in range(1, 13)])
    land = np.isfinite(elev) & np.isfinite(T).all(0) & np.isfinite(P).all(0) & np.isfinite(Tx - Tn).all(0); shape = land.shape
    LAT = np.broadcast_to((L.WINDOW['lat'][1] - (np.arange(shape[0]) + .5) / L.RES)[:, None], shape)
    cand, nav5 = candidate_share(shape, land); print('candidate land', flush=True)
    q, info = qualifying(shape, land, nav5, T, Tx, Tn, P, LAT); s = np.where(q, cand, 0.0); print('qualifying cells', int((s > 0).sum()), flush=True)
    original = L.analyse; store = {}

    def analyse(Tl, Pl, latl, tilt, ws, irr, arable, D, margins=None):
        out, names = original(Tl, Pl, latl, tilt, ws, irr, arable, D, margins=margins)
        sl = s[land]; idx = np.flatnonzero(sl > 0)
        ob, nb = original(Tl[:, idx], Pl[:, idx], latl[idx], tilt, ws, np.ones(len(idx)), arable[idx], D[:, idx], margins=margins)
        assert nb == names
        main_crop = ob['main_crop']; first = np.zeros(len(idx))
        for k, nme in enumerate(names): first = np.where(main_crop == k, ob[f'kcal_{nme}'], first)
        winter = np.maximum(ob['kcal_wheat'], ob['kcal_barley'])                     # amendment A1: cool-season cereal on the receding flood
        unit_first = first * arable[idx] * 100.0 / LP.NEED_KCAL; unit = winter * arable[idx] * 100.0 / LP.NEED_KCAL   # per unit farmed share
        store.update(idx=idx, unit=unit, unit_first=unit_first, main_crop=main_crop, base=out['capacity'][idx].copy(), s=sl[idx])
        cap = out['capacity'].copy(); cap[idx] = (1 - sl[idx]) * cap[idx] + sl[idx] * unit * F_B; out['capacity'] = cap
        return out, names

    L.analyse = analyse
    sys.argv = ['land_people_earth.py', '--out', str(GRID)]; L.main()
    def grid(v):
        g = np.zeros(shape); g.ravel()[np.flatnonzero(land.ravel())[store['idx']]] = v; return g
    np.savez_compressed(OUT / 'fields.npz', s=s, candidate=cand, qualifying=q, catchment=info['catchment'], flood_rain=info['flood_rain'], flow=info['flow'],
                        basin_unit_capacity=grid(store['unit']), basin_unit_capacity_original_first_crop=grid(store['unit_first']), basin_main_crop_original=grid(store['main_crop']), base_capacity_on_basin=grid(store['base']))
    json.dump(dict(last_flood_month={str(k): v for k, v in info['last'].items()}, timing_ok=[int(b) for b in np.flatnonzero(info['timing_ok'])]), open(OUT / 'basins.json', 'w'), indent=1)
    print('done', flush=True)


if __name__ == '__main__':
    main()
