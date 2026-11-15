"""M1 + capital term size refit (calibration/size_capital_term_20261115/plan.json)."""
import csv, io, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.stats import ks_2samp
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_release2_earth as R
from polity import settlement_sizes as Z
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/size_capital_term_20261115/plan.json'; OUT = ROOT / 'output/size_capital_term_20261115'
CAP = ROOT / 'output/capital_effect_20261115/results.json'; GREEK = {'Achaea', 'Macedonia', 'Epirus'}


def main():
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    OUT.mkdir(parents=True, exist_ok=True)
    basis = {r['Primary Key']: r['Estimate Basis'] for r in csv.DictReader(io.StringIO((R.CACHE / 'areas.csv').read_bytes().decode('utf-8-sig')))}
    city = {r['Primary Key']: r['Ancient Toponym'] for r in csv.DictReader(io.StringIO((R.CACHE / 'cities.csv').read_bytes().decode('cp1252')))}
    rows, _, _ = R.cohort(); rows = [dict(r) for r in rows if r['area'] not in (20.0, 30.0)]
    for r in rows:
        if r['province'] in GREEK and basis.get(r['key'], '').startswith('Walls'): r['area'] *= 1 / 3 if r['area'] >= 100 else 1 / 2
    capnames = {(m['town'], m['province']) for m in json.loads(CAP.read_text())['matched']}
    cap = np.array([(city[r['key']], r['province']) in capnames for r in rows], float)
    assert int(cap.sum()) == len(capnames), (cap.sum(), len(capnames))
    y = np.log([r['area'] for r in rows]); fold = np.array([Z.province_fold(r['province']) for r in rows])
    cols = dict(lnH=np.array([r['lnH'] for r in rows]), capital=cap)
    take = lambda m: {k: v[m] for k, v in cols.items()}
    out = dict(status='size_capital_term_development', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), capital_source_sha256=sha(CAP), n=len(rows), capitals=int(cap.sum()), models={})
    area = np.exp(y)
    for name, names in (('M1', ('lnH',)), ('M1C', ('lnH', 'capital'))):
        pred = np.empty(len(y)); fold_coef = []
        for f in range(4):
            coef = Z.fit(take(fold != f), names, y[fold != f]); fold_coef.append([float(c) for c in coef])
            pred[fold == f] = Z.predict(take(fold == f), names, coef)
        res = y - pred; sigma = float(np.std(res)); full = Z.fit(cols, names, y)
        ks, ratio = [], []
        for s in R.SEEDS:
            gen = Z.generate_area(pred, sigma, Z.draws(len(y), s), area.min(), area.max()); ks.append(float(ks_2samp(gen, area).statistic)); ratio.append(float(gen.sum() / area.sum()))
        c = cap.astype(bool)
        out['models'][name] = dict(terms=['intercept', *names], heldout_mae=float(np.mean(np.abs(res))), heldout_sigma=sigma, full_coefficients=[float(v) for v in full],
            fold_coefficients=fold_coef, heldout_mae_capitals=float(np.mean(np.abs(res[c]))), heldout_mean_residual_capitals=float(np.mean(res[c])),
            gate=dict(mean_ks=float(np.mean(ks)), mean_total_area_ratio=float(np.mean(ratio)), passed=bool(np.mean(ks) <= 0.10 and 0.80 <= np.mean(ratio) <= 1.25)))
    m1, mc = out['models']['M1'], out['models']['M1C']
    out['adopt_M1C'] = bool(mc['heldout_mae'] <= 0.98 * m1['heldout_mae'] and mc['gate']['passed'] and all(fc[2] > 0 for fc in mc['fold_coefficients']))
    write(OUT / 'results.json', out); print(json.dumps(out, indent=1)[:2500])


if __name__ == '__main__':
    main()
