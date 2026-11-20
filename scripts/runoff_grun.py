"""Runoff seasonality vs GRUN (calibration/runoff_20261120/plan.json).

    .venv/bin/python -I scripts/runoff_grun.py dev
    .venv/bin/python -I scripts/runoff_grun.py blind     # run once
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
OUT = ROOT / 'output/runoff_20261120'; PLAN = ROOT / 'calibration/runoff_20261120/plan.json'
ROWS, COLS = slice(408, 1080), slice(2016, 3660)         # Earth run window in the global 5' WorldClim grid
BUCKETS = (25, 50, 100, 150, 200, 300); PETS = ('hargreaves', 'droogers_allen'); DAYS = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


def grun():
    z = np.load(ROOT / 'data/cache/grun/grun_clim_1970_2000.npz'); r = z['runoff_mm_day'].astype(float); r[r < -100] = np.nan
    lat, lon = z['lat'], z['lon']                          # ascending lat (south first), lon -179.75..
    i = np.flatnonzero((lat > 0) & (lat < 56))[::-1]; j = np.flatnonzero((lon > -12) & (lon < 125))
    return r[:, i][:, :, j] * DAYS[:, None, None]          # [12, 112, 274], north first, mm/month


def climate():
    from rotclimate.earth import _wc
    get = lambda v: np.nan_to_num(np.stack([_wc(v, m + 1)[ROWS, COLS] for m in range(12)]))
    land = np.isfinite(_wc('tavg', 1)[ROWS, COLS])
    lat = (56 - (np.arange(672) + 0.5) / 12)[:, None] * np.ones((1, 1644))
    return get('tavg'), get('tmax'), get('tmin'), get('prec'), lat, land


def model_runoff(cl, bucket, pet):
    from polity import seasons as S
    T, Tx, Tn, P, lat, land = cl; old = S.SOIL_MM
    try:
        S.SOIL_MM = float(bucket); f = S.fields(T, Tx, Tn, P, lat, pet_method=pet)
    finally:
        S.SOIL_MM = old
    r = np.where(land, f['runoff'], 0.0)
    s = r.reshape(12, 112, 6, 274, 6).sum((2, 4)); n = land.reshape(112, 6, 274, 6).sum((1, 3))
    return np.where(n >= 18, s / np.maximum(n, 1), np.nan)   # 0.5-deg mean over land (>= 50 % land)


def setup():
    g = grun(); cl = climate()
    ok = np.isfinite(g).all(0)
    bl = 5; nb_y, nb_x = 112 // bl, 274 // bl
    blat = 56 - (np.arange(nb_y) + 0.5) * 2.5; blon = -12 + (np.arange(nb_x) + 0.5) * 2.5
    BL, BO = np.meshgrid(blat, blon, indexing='ij'); tile = ((np.floor(BL / 10) + np.floor(BO / 10)).astype(int)) % 2
    return g, cl, ok, tile


def block_cycle(r, ok):
    v = np.where(ok, r, 0.0)[:, :110, :270].reshape(12, 22, 5, 54, 5).sum((2, 4)); n = ok[:110, :270].reshape(22, 5, 54, 5).sum((1, 3))
    return np.where(n >= 13, v / np.maximum(n, 1), np.nan), n >= 13


def score(m, g, ok, tile, part):
    both = ok & np.isfinite(m).all(0)
    mb, mv = block_cycle(np.nan_to_num(m), both); gb, gv = block_cycle(np.nan_to_num(g), both)
    sel = mv & gv & (gb.sum(0) >= 20) & (tile == part)
    rel = lambda a: a / np.maximum(a.mean(0), 1e-9)
    mr, gr = rel(mb[:, sel]), rel(gb[:, sel])
    cor = np.array([np.corrcoef(mr[:, k], gr[:, k])[0, 1] if mr[:, k].std() > 1e-9 else 0.0 for k in range(mr.shape[1])])
    fm, fg = mr > 1.5, gr > 1.5; tp = (fm & fg).sum(); f1 = 2 * tp / max(fm.sum() + fg.sum(), 1)
    lm, lg = mr < 0.4, gr < 0.4; tl = (lm & lg).sum(); f1l = 2 * tl / max(lm.sum() + lg.sum(), 1)
    ann_m, ann_g = mb.sum(0)[sel], gb.sum(0)[sel]           # annual runoff of the same blocks
    return dict(primary_shape=float(np.median(cor)), shape_q25=float(np.percentile(cor, 25)), flood_F1=float(f1), lowwater_F1=float(f1l),
                blocks=int(sel.sum()), annual_spearman=float(spearmanr(ann_m, ann_g).correlation),
                annual_ratio_median=float(np.median(ann_m / np.maximum(ann_g, 1))))


def run(part):
    g, cl, ok, tile = setup(); res = {}
    for b in BUCKETS:
        for p in PETS:
            res[f'{b}|{p}'] = score(model_runoff(cl, b, p), g, ok, tile, part)
    return res


def dev():
    OUT.mkdir(parents=True, exist_ok=True); res = run(0); best = max(res, key=lambda k: res[k]['primary_shape'])
    (OUT / 'dev.json').write_text(json.dumps(dict(plan=str(PLAN.relative_to(ROOT)), variants=res, chosen=best), indent=1))
    for k, v in res.items():
        print(k.ljust(20), ' '.join(f'{n}={x:.3f}' if isinstance(x, float) else f'{n}={x}' for n, x in v.items()))
    print('chosen', best)


def blind():
    chosen = json.loads((OUT / 'dev.json').read_text())['chosen']; r = run(1); cur = r['100|hargreaves']; c = r[chosen]
    V = cur['primary_shape'] >= 0.6; g1 = c['primary_shape'] >= cur['primary_shape'] + 0.05; g2 = c['flood_F1'] >= cur['flood_F1'] - 0.02
    res = dict(plan=str(PLAN.relative_to(ROOT)), chosen=chosen, current=cur, chosen_scores=c, all_variants=r,
               gates=dict(V=bool(V), G1=bool(g1), G2=bool(g2)), adopt=bool(g1 and g2 and chosen != '100|hargreaves'))
    (OUT / 'blind.json').write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != 'all_variants'}, indent=1))


if __name__ == '__main__':
    {'dev': dev, 'blind': blind}[sys.argv[1]]()
