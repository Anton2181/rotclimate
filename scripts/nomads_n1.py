"""T9 N1: pastoral nomads on Earth vs climate (calibration/nomads_20261121/plan_n1.json).

    .venv/bin/python -I scripts/nomads_n1.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import herders_earth as H1  # noqa: E402
import herders_v2 as H2  # noqa: E402

OUT = ROOT / 'calibration/nomads_20261121'
MODELS = {'P0': ['H'], 'P1': ['H', 'A'], 'P2': ['H', 'A', 'T', 'L']}


def societies(south):
    import pandas as pd
    m = H2.societies(south)
    x = pd.read_csv(H1.EA / 'data.csv', low_memory=False)
    v = x[x.Var_ID == 'EA030'].set_index('Soc_ID').Code_ID
    m = m.join(v.rename('EA030'), how='inner')
    m = m[~m.EA030.str.endswith('NA')].copy()
    m['sp'] = m.EA030.str.split('-').str[1].astype(int)
    m['nomad'] = m.sp.isin([1, 2]) & m.dominant
    return m


def sample(m, path):
    z = np.load(path)
    land = z['land']
    x = H2.sample(m, path)
    lw = np.maximum(ndi.uniform_filter(land.astype(float), 3, mode='nearest'), 1e-9)
    mean = lambda a: ndi.uniform_filter(np.where(land, np.nan_to_num(a), 0.0), 3, mode='nearest') / lw
    A = mean(np.log(np.maximum(np.nan_to_num(z['P_ann']), 1.0) / np.maximum(np.nan_to_num(z['PET_ann']), 1.0)))
    lat, lon = z['lat'], z['lon']
    step = float(lat[0] - lat[1])
    r = np.clip(np.round((lat[0] - m.Latitude.values) / step).astype(int), 0, len(lat) - 1)
    c = np.clip(np.round((m.Longitude.values - lon[0]) / step).astype(int), 0, len(lon) - 1)
    _, (iy, ix) = ndi.distance_transform_edt(~land, return_indices=True)
    x['A'] = A[iy[r, c], ix[r, c]]
    spec = json.loads((ROOT / 'output/herders_20261120/v2_dev.json').read_text())['chosen']
    x['H'] = H2.predict(x, spec)
    return x


def logistic(X, y, iters=100):
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ beta))
        g = X.T @ (y - p)
        Hs = X.T @ (X * (p * (1 - p))[:, None]) + 1e-6 * np.eye(X.shape[1])
        step = np.linalg.solve(Hs, g)
        beta += step
        if np.abs(step).max() < 1e-8:
            break
    return beta


def auc(p, y):
    from scipy.stats import rankdata
    r = rankdata(p)
    n1 = y.sum(); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main():
    import pandas as pd
    parts = []
    for south, path in [(False, H2.NORTH), (True, H2.SOUTH)]:
        m = societies(south)
        x = sample(m, path)
        for k, v in x.items():
            m[k] = v
        parts.append(m)
    m = pd.concat(parts)
    y = m.nomad.values.astype(bool)
    tile = (np.floor(m.Latitude / 10) * 100 + np.floor(m.Longitude / 10)).astype(int).values
    fold = tile % 5
    stats = {k: (float(m[k].mean()), float(m[k].std())) for k in ['H', 'A', 'T', 'L']}
    Z = {k: (m[k].values - mu) / sd for k, (mu, sd) in stats.items()}
    res = dict(n=int(len(m)), nomads=int(y.sum()), standardise=stats, models={})
    for name, keys in MODELS.items():
        X = np.column_stack([np.ones(len(m))] + [Z[k] for k in keys])
        oof = np.zeros(len(m))
        for f in range(5):
            tr, te = fold != f, fold == f
            b = logistic(X[tr], y[tr].astype(float))
            oof[te] = 1 / (1 + np.exp(-X[te] @ b))
        b = logistic(X, y.astype(float))
        eps = 1e-9
        ll = float(-np.mean(y * np.log(oof + eps) + (~y) * np.log(1 - oof + eps)))
        res['models'][name] = dict(keys=keys, coefficients=dict(zip(['const'] + keys, map(float, b))),
                                   oof_auc=auc(oof, y), oof_logloss=ll)
        print(f'{name} {keys}: OOF AUC {auc(oof, y):.3f}  log loss {ll:.3f}  coef {np.round(b, 2).tolist()}')
    best = max(v['oof_auc'] for v in res['models'].values())
    chosen = next(k for k, v in res['models'].items() if v['oof_auc'] >= best - 0.01)
    res['chosen'] = chosen
    res['adopt'] = res['models'][chosen]['oof_auc'] >= 0.80
    print('chosen', chosen, 'adopt', res['adopt'], f'({int(y.sum())} nomads of {len(m)})')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'n1_results.json').write_text(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
