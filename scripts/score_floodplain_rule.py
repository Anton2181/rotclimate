"""Score the floodplain rule (calibration/floodplain_rule_20261114/plan.json, amendment A1): T1 constraints, T2 Egypt,
F_b sensitivity and the original-rule record. Writes output/floodplain_rule_20261114/results.json."""
import json, sys
from pathlib import Path
import numpy as np
from matplotlib.path import Path as Poly

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import land_people_earth as L
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/floodplain_rule_20261114'; PLAN = ROOT / 'calibration/floodplain_rule_20261114/plan.json'


def main():
    a = np.load(ROOT / 'output/land_people/earth/earth.npz'); b = np.load(ROOT / 'output/land_people/earth_floodplain/earth.npz'); f = np.load(OUT / 'fields.npz')
    s = f['s']; ca, cb = np.nan_to_num(a['capacity']), np.nan_to_num(b['capacity']); base = f['base_capacity_on_basin']
    control = bool(np.array_equal(ca[s == 0], cb[s == 0]) and all(np.array_equal(np.nan_to_num(a[k]), np.nan_to_num(b[k])) for k in a.files if k != 'capacity'))
    lat, lon, land = a['lat'], a['lon'], a['land']; LAT, LON = np.meshgrid(lat, lon, indexing='ij'); km2 = (L.KM_DEG / L.RES) ** 2 * np.cos(np.radians(LAT))
    pts = np.stack([LON.ravel(), LAT.ravel()], 1)
    variant = lambda unit, F: np.where(s > 0, (1 - s) * base + s * unit * F, ca)
    caps = {'A1_F0.95': cb, 'A1_F0.60': variant(f['basin_unit_capacity'], 0.60), 'original_F0.95': variant(f['basin_unit_capacity_original_first_crop'], 0.95),
            'original_F0.60': variant(f['basin_unit_capacity_original_first_crop'], 0.60)}
    assert np.allclose(caps['A1_F0.95'], variant(f['basin_unit_capacity'], 0.95), rtol=1e-6, atol=1e-6)
    regions = {}
    for name, r in L.REGIONS.items():
        m = Poly(r['poly']).contains_points(pts).reshape(LAT.shape) & land
        c0 = float((ca * km2)[m].sum() / 1e6)
        regions[name] = dict(baseline_m=c0, basin_km2=float((s * km2)[m].sum()), **{k: float((v * km2)[m].sum() / 1e6) for k, v in caps.items()})
    others = {n: r for n, r in regions.items() if n != 'Egypt'}
    t1 = {k: all(r[k] <= 1.05 * r['baseline_m'] + 1e-9 for r in others.values()) for k in caps}
    t2 = {k: 3.6 <= regions['Egypt'][k] <= 6.25 for k in caps}
    names = [str(n) for n in b['crops']]; mc = f['basin_main_crop_original'][s > 0].astype(int)
    out = dict(status='floodplain_rule_development', plan_sha256=sha(PLAN), producer_sha256=sha(ROOT / 'scripts/floodplain_earth.py'), scorer_sha256=sha(Path(__file__)),
        control_unchanged_off_basin=control, qualifying_cells=int((s > 0).sum()), qualifying_basin_km2_total=float((s * km2).sum()),
        basin_km2_by_lon_band={'west of 40E': float((s * km2)[LON < 40].sum()), '40-60E': float((s * km2)[(LON >= 40) & (LON < 60)].sum()), 'east of 60E': float((s * km2)[LON >= 60].sum())},
        original_basin_main_crop_share={n: float(np.mean(mc == i)) for i, n in enumerate(names)},
        regions=regions, T1_constraints=t1, T2_egypt=t2, primary='A1_F0.95', primary_pass=bool(t1['A1_F0.95'] and t2['A1_F0.95']),
        original_declaration_pass=bool(t1['original_F0.95'] and t2['original_F0.95']), egypt_historical_m=[4.5, 5.0])
    write(OUT / 'results.json', out); print(json.dumps({k: v for k, v in out.items() if k != 'regions'}, indent=1)); print('Egypt', regions['Egypt'])


if __name__ == '__main__':
    main()
