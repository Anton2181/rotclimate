"""Detailed forest, stage 1: farming clearing against Zanon et al. 2018 AD 200 forest cover
(calibration/forest_detail_20261116/plan.json).

    .venv/bin/python -I scripts/forest_detail_earth.py dev     # fit F (B2) and F, k (M) on the dev tiles
    .venv/bin/python -I scripts/forest_detail_earth.py blind   # the single blind evaluation
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
OUT = ROOT / 'output/forest_detail_20261116'; PLAN = ROOT / 'calibration/forest_detail_20261116/plan.json'
ZANON = ROOT / 'data/cache/zanon2018/Zanon_et_al_2018_maps/forest_cover/forest_cover_1750.grd'
NEED = 912_500.0
FS = np.round(np.arange(0.30, 1.0001, 0.01), 2); KS = np.round(np.r_[np.arange(0.0, 0.5, 0.05), np.arange(0.5, 8.0001, 0.1)], 2)   # amendment A1: extended below 0.5


def inputs():
    import h5py
    from polity.earth import earth_people
    e = np.load(ROOT / 'output/land_people/earth/earth.npz')
    lat, lon = e['lat'], e['lon']
    with h5py.File(ZANON, 'r') as f:
        zl, zo, z = f['lat'][:], f['lon'][:], f['z'][:].astype(float)
    target = np.full(e['land'].shape, np.nan)
    ri = {round(v, 4): i for i, v in enumerate(lat)}; ci = {round(v, 4): j for j, v in enumerate(lon)}
    rows = np.array([ri.get(round(v, 4), -1) for v in zl]); cols = np.array([ci.get(round(v, 4), -1) for v in zo])
    if (rows >= 0).sum() == 0 or (cols >= 0).sum() == 0:
        raise ValueError('Zanon grid does not align with the Earth run grid')
    rr, cc = np.meshgrid(rows, cols, indexing='ij')
    ok = (rr >= 0) & (cc >= 0)
    target[rr[ok], cc[ok]] = z[ok] / 100.0
    LAT, LON = np.meshgrid(lat, lon, indexing='ij')
    valid = np.isfinite(target) & e['land'] & (LAT >= 29) & (LAT <= 56) & (LON >= -11) & (LON <= 43)
    D, _, _ = earth_people(LAT[valid], LON[valid])
    dens = np.zeros(LAT.shape); dens[valid] = D
    p = np.clip((e['aridity'] - 0.3) / 0.2, 0, 1) * np.clip((e['gdd5'] - 300.0) / 300.0, 0, 1)
    tile = (np.floor(LAT / 5) + np.floor(LON / 5)).astype(int) % 2
    return dict(target=target, valid=valid, p=p, dens=dens, kcal=e['kcal_ha'].astype(float), tile=tile, lat=LAT, lon=LON,
                aligned_rows=int((rows >= 0).sum()), aligned_cols=int((cols >= 0).sum()))


def farm(x, k):
    a = np.where(x['kcal'] > 0, k * x['dens'] * NEED / np.maximum(x['kcal'], 1.0) / 100.0, 0.0)
    return np.minimum(1.0, a)


def blocks(v, valid, n=6):
    h, w = (v.shape[0] // n) * n, (v.shape[1] // n) * n
    vv = np.where(valid, v, 0.0)[:h, :w].reshape(h // n, n, w // n, n); cnt = valid[:h, :w].reshape(h // n, n, w // n, n).sum((1, 3))
    return vv.sum((1, 3)) / np.maximum(cnt, 1), cnt >= 0.5 * n * n


def score(pred, x, part):
    m = x['valid'] & (x['tile'] == part)
    pb, ok = blocks(pred, m); tb, _ = blocks(x['target'], m)
    from scipy.stats import spearmanr
    rm = float(np.sqrt(np.mean((pb[ok] - tb[ok]) ** 2))); sp = float(spearmanr(np.round(pb[ok], 6), np.round(tb[ok], 6)).correlation)   # A1: ties broken consistently
    cell = float(np.sqrt(np.mean((pred[m] - x['target'][m]) ** 2)))
    return dict(rmse=rm, spearman=sp, blocks=int(ok.sum()), cell_rmse=cell, mean_pred=float(pb[ok].mean()), mean_obs=float(tb[ok].mean()))


def fit(x):
    m = x['valid'] & (x['tile'] == 0)
    tb, ok = blocks(x['target'], m); pb, _ = blocks(x['p'], m)
    b2 = min(FS, key=lambda F: np.mean((F * pb[ok] - tb[ok]) ** 2))
    best = (np.inf, None, None)
    for k in KS:
        fb, _ = blocks(x['p'] * (1 - farm(x, k)), m)
        for F in FS:
            r = np.mean((F * fb[ok] - tb[ok]) ** 2)
            if r < best[0]:
                best = (r, F, k)
    return float(b2), float(best[1]), float(best[2])


def models(x, b2, F, k):
    return {'B1_current': 0.60 * x['p'], 'B2_level': b2 * x['p'], 'M_farming': F * x['p'] * (1 - farm(x, k))}


def dev():
    OUT.mkdir(parents=True, exist_ok=True); x = inputs(); b2, F, k = fit(x)
    res = dict(plan=str(PLAN.relative_to(ROOT)), fitted=dict(B2_F=b2, M_F=F, M_k=k), aligned=[x['aligned_rows'], x['aligned_cols']],
               valid_cells=int(x['valid'].sum()), dev={n: score(v, x, 0) for n, v in models(x, b2, F, k).items()},
               k_at_edge=bool(k in (KS[0], KS[-1])), F_at_edge=bool(F in (FS[0], FS[-1])))
    (OUT / 'dev.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def blind():
    x = inputs(); d = json.loads((OUT / 'dev.json').read_text())['fitted']
    sc = {n: score(v, x, 1) for n, v in models(x, d['B2_F'], d['M_F'], d['M_k']).items()}
    g1 = sc['M_farming']['rmse'] <= sc['B1_current']['rmse']
    g2 = sc['M_farming']['spearman'] >= max(0.30, sc['B1_current']['spearman'] + 0.10)
    res = dict(plan=str(PLAN.relative_to(ROOT)), fitted=d, blind=sc, gates=dict(G1=bool(g1), G2=bool(g2)), adopt=bool(g1 and g2))
    (OUT / 'blind.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    {'dev': dev, 'blind': blind}[sys.argv[1]]()
