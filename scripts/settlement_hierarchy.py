"""Settlement-hierarchy size model: fit and province-fold validation on Roman AD 150 towns
(calibration/settlement_hierarchy_20261115/plan.json). Centres = provincial capitals (capital_effect matches)."""
import csv, io, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.stats import ks_2samp
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_release2_earth as R
from polity import settlement_sizes as Z
from polity.survey_transfer import sphere_distance
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_hierarchy_20261115/plan.json'; OUT = ROOT / 'output/settlement_hierarchy_20261115'
CAP = ROOT / 'output/capital_effect_20261115/results.json'; M1C = ROOT / 'output/size_capital_term_20261115/results.json'
GREEK = {'Achaea', 'Macedonia', 'Epirus'}; RADIUS = 75.0; SEEDS = [1, 7, 19, 43, 97]


def cohort():
    basis = {r['Primary Key']: r['Estimate Basis'] for r in csv.DictReader(io.StringIO((R.CACHE / 'areas.csv').read_bytes().decode('utf-8-sig')))}
    city = {r['Primary Key']: r for r in csv.DictReader(io.StringIO((R.CACHE / 'cities.csv').read_bytes().decode('cp1252')))}
    rows, _, _ = R.cohort(); rows = [dict(r) for r in rows if r['area'] not in (20.0, 30.0)]
    for r in rows:
        if r['province'] in GREEK and basis.get(r['key'], '').startswith('Walls'): r['area'] *= 1 / 3 if r['area'] >= 100 else 1 / 2
    caps = {(m['town'], m['province']) for m in json.loads(CAP.read_text())['matched']}
    lat = np.array([float(city[r['key']]['Latitude (Y)']) for r in rows]); lon = np.array([float(city[r['key']]['Longitude (X)']) for r in rows])
    cap = np.array([(city[r['key']]['Ancient Toponym'], r['province']) in caps for r in rows])
    return rows, lat, lon, cap


def main():
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    OUT.mkdir(parents=True, exist_ok=True)
    rows, lat, lon, cap = cohort(); n = len(rows)
    y = np.log([r['area'] for r in rows]); lnH = np.array([r['lnH'] for r in rows]); fold = np.array([Z.province_fold(r['province']) for r in rows])
    C = np.flatnonzero(cap); centre = np.full(n, -1); dist = np.zeros(n)
    for i in np.flatnonzero(~cap):
        d = sphere_distance(lat[C], lon[C], lat[i], lon[i]); j = int(np.argmin(d))
        if d[j] <= RADIUS: centre[i] = C[j]; dist[i] = d[j]
    sub = centre >= 0
    def design(idx): return np.column_stack([np.ones(len(idx)), lnH[idx] - lnH[centre[idx]], dist[idx] / 100.0])
    delta = np.zeros(n); delta[sub] = y[sub] - y[centre[sub]]
    m1c = json.loads(M1C.read_text())['models']['M1C']; area = np.exp(y)
    # held-out: M1C fold coefficients for every town; delta model fitted on subordinates of the other folds
    pred_m1c = np.empty(n); pred_delta = np.full(n, np.nan); sd = {}; coefs = []
    for f in range(4):
        tr, te = fold != f, fold == f
        c = m1c['fold_coefficients'][f]; pred_m1c[te] = c[0] + c[1] * lnH[te] + c[2] * cap[te]
        s_tr = np.flatnonzero(sub & tr); beta, *_ = np.linalg.lstsq(design(s_tr), delta[s_tr], rcond=None); coefs.append([float(b) for b in beta])
        sd[f] = float(np.std(delta[s_tr] - design(s_tr) @ beta))
        s_te = np.flatnonzero(sub & te); pred_delta[s_te] = design(s_te) @ beta
    sig_m1c = m1c['heldout_sigma']; runs = []
    for seed in SEEDS:
        e = Z.draws(n, seed); gen = np.clip(np.exp(pred_m1c + sig_m1c * e), area.min(), area.max())          # centres and towns beyond 75 km
        e2 = Z.draws(n, seed + 1000)
        for i in np.flatnonzero(sub):
            gen[i] = np.clip(gen[centre[i]] * np.exp(pred_delta[i] + sd[fold[i]] * e2[i]), area.min(), area.max())
        runs.append(dict(seed=seed, ks=float(ks_2samp(gen, area).statistic), total_ratio=float(gen.sum() / area.sum()),
                         share_sub_larger=float(np.mean(gen[sub] > gen[centre[sub]])), median_ratio=float(np.median(gen[sub] / gen[centre[sub]]))))
    obs = dict(subordinates=int(sub.sum()), share_sub_larger=float(np.mean(area[sub] > area[centre[sub]])), median_ratio=float(np.median(area[sub] / area[centre[sub]])))
    mean = lambda k: float(np.mean([r[k] for r in runs]))
    gate = dict(ks=mean('ks'), total_ratio=mean('total_ratio'), share_sub_larger=mean('share_sub_larger'), median_ratio=mean('median_ratio'))
    passed = bool(gate['ks'] <= 0.10 and 0.80 <= gate['total_ratio'] <= 1.25 and abs(gate['share_sub_larger'] - obs['share_sub_larger']) <= 0.05
                  and abs(np.log(gate['median_ratio'] / obs['median_ratio'])) <= np.log(1.25))
    sfull = np.flatnonzero(sub); full, *_ = np.linalg.lstsq(design(sfull), delta[sfull], rcond=None); sd_full = float(np.std(delta[sfull] - design(sfull) @ full))
    # reference: the published M1C alone (no hierarchy) on the same held-out metrics
    ref = []
    for seed in SEEDS:
        gen = np.clip(np.exp(pred_m1c + sig_m1c * Z.draws(n, seed)), area.min(), area.max())
        ref.append(dict(share_sub_larger=float(np.mean(gen[sub] > gen[centre[sub]])), median_ratio=float(np.median(gen[sub] / gen[centre[sub]]))))
    out = dict(status='settlement_hierarchy_development', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), cohort=n, centres=int(cap.sum()), radius_km=RADIUS,
               observed=obs, delta_model=dict(terms=['intercept', 'lnH_u - lnH_c', 'distance_km / 100'], full_coefficients=[float(b) for b in full], scatter_sd=sd_full,
               fold_coefficients=coefs, fold_scatter=sd), runs=runs, gate=gate, passed=passed,
               m1c_only_reference=dict(share_sub_larger=float(np.mean([r['share_sub_larger'] for r in ref])), median_ratio=float(np.mean([r['median_ratio'] for r in ref]))))
    write(OUT / 'results.json', out); print(json.dumps({k: v for k, v in out.items() if k not in ('runs',)}, indent=1))


if __name__ == '__main__':
    main()
