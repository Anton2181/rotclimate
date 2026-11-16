"""WP3 confluence factor: blind position test on the Buringh pool
(calibration/wp3_site_factors_20261116/blind_buringh.json, amendment A1). Raw rows stay in the ignored cache."""
import csv, json, subprocess, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import earth as E
import settlement_model_earth as S
import polity_earth_check as P
import population_cores as PC
from settlement_locations_earth import metrics, sha, write
from wp3_site_factors import confluence, run
PLAN = ROOT / 'calibration/wp3_site_factors_20261116/blind_buringh.json'; OUT = ROOT / 'output/wp3_buringh_blind_20261116'
TAB = ROOT / 'data/cache/buringh2021/buringh.tab'


def cohort():
    rows = list(csv.reader(open(TAB, encoding='utf-8', errors='replace'), delimiter='\t')); h = rows[0]; ix = {k: i for i, k in enumerate(h)}
    f = lambda s: float(s.replace(',', '.')) if s not in ('', None) else np.nan
    out, dropped = [], 0
    for r in rows[1:]:
        la, lo = f(r[ix['latitudeindegrees']]), f(r[ix['longitudeindegrees']])
        if not (-90 <= la <= 90 and -180 <= lo <= 180): dropped += 1; continue
        if float(r[ix['year']].replace(',', '.')) != 1300.0 or r[ix['natureofestimate']] == 'imputed': continue
        pop = f(r[ix['inhabitantsin000-s']])
        if np.isfinite(pop) and pop >= 5.0: out.append((la, lo, pop))
    return np.array(out), dropped


def main():
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    OUT.mkdir(parents=True, exist_ok=True)
    from rotclimate.earth import _wc
    g = E.grid(49.0, 6.0, 1400., 1000., 9.0); lat, lon = g['lat'], g['lon']
    elev = E.sample_global(_wc('elev'), lat, lon); g.update(land=np.isfinite(elev), elev=np.nan_to_num(elev, nan=0.0))
    for var in ('tavg', 'tmin', 'tmax', 'prec'):
        g[var] = np.stack([np.nan_to_num(E.sample_global(_wc(var, m + 1), lat, lon)) for m in range(12)])
    g['density'], _, _ = E.earth_people(lat, lon); g['river'] = E.rivers(g) & g['land']; g['cell_km'] = 9.0
    data = S.inputs(g, np.zeros(g['land'].shape, bool), g['land'].astype(bool))
    with np.load(ROOT / 'output/land_people/earth/earth.npz') as z:
        dist = PC.travel_distance(z, PC.CORE_SETS['cradles + Rome'], forest_cost=2., sea_cost=1., relief_cost=1.)
    data['history'] = S.sample_earth(np.exp(-dist / 800.), lat, lon)
    C, dropped = cohort()
    y, x, ok = P.snap(g, C[:, 0], C[:, 1]) if len(C) else (np.array([]), np.array([]), np.array([], bool))
    inwin = ok & data['allowed'][np.clip(y, 0, None), np.clip(x, 0, None)]
    data['real'] = np.unique((y * g['land'].shape[1] + x)[inwin]); target = int(len(data['real']))
    c, nj = confluence(data); res = dict(status='wp3_buringh_blind', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), source_sha256=sha(TAB),
                                         dropped_bad_coordinates=dropped, cohort_cities_1300=int(len(C)), cohort_in_window_distinct_cells=target, junction_cells=nj, models={})
    for k in (0.0, 1.0):
        t = run(data, data['history'] * (1 + k * c), target); m = metrics(data, t)
        res['models'][f'k{k}'] = {q: m[q] for q in ('composite', 'F1', 'recall', 'precision', 'M1', 'M3', 'n_model', 'n_real')}
        print(k, json.dumps(res['models'][f'k{k}']), flush=True)
    res['composite_gain'] = res['models']['k1.0']['composite'] - res['models']['k0.0']['composite']; res['pass'] = bool(res['composite_gain'] >= 0.01)
    res['raw_rows_redistributed'] = False; write(OUT / 'results.json', res); print('gain', res['composite_gain'], 'PASS' if res['pass'] else 'FAIL')


if __name__ == '__main__':
    main()
