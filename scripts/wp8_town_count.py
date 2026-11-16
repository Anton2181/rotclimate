"""WP8 development fit (calibration/wp8_town_count_20261116/plan.json): placement exponent vs block town counts."""
import json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import settle
IN = ROOT / 'output/settlement_locations_20261110'; OUT = ROOT / 'output/wp8_town_count_20261116'


def place(d, beta, sp):
    return settle.place_towns(d['density'], d['land'], d['water_km'], d['road'], d['elev'], float(d['cell_km']), [], allowed=d['allowed'],
                              seed=1, aridity=d['aridity'], beta=beta, seat_people=sp)[0]


def blocks(d, pts):
    cell = float(d['cell_km']); b = max(1, round(100 / cell)); h, w = d['land'].shape; ny, nx = (h + b - 1) // b, (w + b - 1) // b
    yy, xx = np.indices((h, w)); blk = (yy // b) * nx + xx // b
    cov = np.bincount(blk.ravel(), weights=d['allowed'].ravel(), minlength=ny * nx) / np.bincount(blk.ravel(), minlength=ny * nx)
    peo = np.bincount(blk.ravel(), weights=(d['density'] * d['allowed']).ravel(), minlength=ny * nx) / np.maximum(np.bincount(blk.ravel(), weights=d['allowed'].ravel(), minlength=ny * nx), 1)
    cnt = lambda p: np.bincount((p[:, 0] // b) * nx + p[:, 1] // b, minlength=ny * nx)
    return cov >= 0.3, cnt(pts), peo


def score(d, towns):
    real = d['real']; real = real[d['allowed'].ravel()[real]]; obs = np.column_stack(np.unravel_index(real, d['land'].shape))
    pred = np.asarray(towns, int).reshape(-1, 2)
    use, m, peo = blocks(d, pred); _, o, _ = blocks(d, obs); m, o, peo = m[use].astype(float), o[use].astype(float), peo[use]
    mu = np.maximum(m, 0.5); dev = 2 * np.sum(np.where(o > 0, o * np.log(o / mu), 0) - (o - mu))
    top = peo >= np.quantile(peo, 0.9)
    return dict(n_model=len(pred), n_real=len(obs), deviance_per_record=float(dev / o.sum()), rank=float(spearmanr(m, o).statistic),
                dense_decile_ratio=float(m[top].sum() / max(o[top].sum(), 1)))


def main():
    OUT.mkdir(parents=True, exist_ok=True); res = {}
    for pool in ('han', 'rome'):
        d = dict(np.load(IN / f'{pool}_inputs.npz')); real = d['real']; target = int(d['allowed'].ravel()[real].sum())
        for beta in (0.7, 0.5, 0.3, 0.0):
            lo, hi = 2e3, 1e6
            for _ in range(22):                       # bisection on seat_people for the catalogue count
                sp = np.sqrt(lo * hi); n = len(place(d, beta, sp))
                if n > target: lo = sp
                else: hi = sp
            sp = np.sqrt(lo * hi); t = place(d, beta, sp); r = score(d, t); r.update(seat_people=float(sp), target=target)
            res[f'{pool}_beta{beta}'] = r; print(pool, beta, json.dumps(r), flush=True)
    sel = {b: float(np.mean([res[f'{p}_beta{b}']['deviance_per_record'] for p in ('han', 'rome')])) for b in (0.7, 0.5, 0.3, 0.0)}
    res['mean_deviance_per_record'] = sel; (OUT / 'results.json').write_text(json.dumps(res, indent=1) + '\n'); print(sel)


if __name__ == '__main__':
    main()
