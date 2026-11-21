"""Rain-fed cereal yield pattern vs GAEZ v4 low-input (calibration/crop_yield_gaez_20261121/plan.json).

    .venv/bin/python -I scripts/crop_yield_gaez.py dev
    .venv/bin/python -I scripts/crop_yield_gaez.py blind     # run once
"""
import itertools, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from runoff_grun import climate
from land_people import CROPS, DAYS, hargreaves, sunlight_top, bucket, smoothstep, crop_yield

CAL = ROOT / 'calibration/crop_yield_gaez_20261121'
VARIANTS = list(itertools.product((0.6, 0.8, 1.0), ((0.2, 0.4), (0.3, 0.5), (0.4, 0.6)), (0, 3), (0.25, 0.35, 0.5)))
CURRENT = (0.8, (0.3, 0.5), 0, 0.35)
GAEZ = {'wheat': 'yxLr0_whe', 'barley': 'yxLr0_brl'}


def gaez(name):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    a = np.array(Image.open(ROOT / f'data/cache/gaez/{name}.tif')).astype(float)   # 2160 x 4320, 90 N first, 180 W first
    a[a < 0] = np.nan
    r0, c0 = int((90 - 56) * 12), int((180 - 12) * 12)
    a = a[r0:r0 + 672, c0:c0 + 1644]
    v = np.isfinite(a)
    s = np.where(v, a, 0).reshape(112, 6, 274, 6).sum((1, 3)); n = v.reshape(112, 6, 274, 6).sum((1, 3))
    return np.where(n >= 18, s / np.maximum(n, 1), np.nan) / 1000.0          # t DW/ha at 0.5 deg


def half(a, land):
    s = np.where(land, a, 0.0).reshape(12, 112, 6, 274, 6).sum((2, 4)); n = land.reshape(112, 6, 274, 6).sum((1, 3))
    return np.where(n >= 18, s / np.maximum(n, 1), np.nan)


def grain(T, P, PET, S0, c, eff, band, shift):
    """Mirror of land_people.crop_yield with irr 0, returning grain t/ha (equal to it at the current setting)."""
    best = np.zeros(T.shape[1:]); lo, hi = c['window']; hi = hi + shift
    for L in range(c['months'][0], c['months'][1] + 1):
        for s in range(12):
            idx = [(s + k) % 12 for k in range(L)]
            Ts, Ps, Es = T[idx], P[idx], PET[idx]
            ok = np.all((Ts >= lo) & (Ts <= hi), axis=0) & (Ts.max(0) >= c['need_warm'])
            ok &= np.sum(np.maximum(Ts - c['base'], 0.0), axis=0) * DAYS >= c['heat']
            fw = np.clip((eff * Ps.sum(0) + S0[idx[0]]) / np.maximum(c['kc'] * Es.sum(0), 1.0), 0.0, 1.0)
            yf = np.clip(1.0 - c['ky'] * (1.0 - fw), 0.0, 1.0) * smoothstep(fw, *band)
            best = np.maximum(best, np.where(ok, yf, 0.0) * c['grain'])
    return best


def main(part):
    T, Tx, Tn, P, _, land = climate()
    Th, Ph, Dh = half(T, land), half(P, land), half(Tx - Tn, land)
    lat = 56 - (np.arange(112) + 0.5) * 0.5; lon = -12 + (np.arange(274) + 0.5) * 0.5
    LA, LO = np.meshgrid(lat, lon, indexing='ij')
    ok0 = np.isfinite(Th).all(0)
    Tf, Pf, Df = (np.nan_to_num(a) for a in (Th, Ph, Dh))
    PET = hargreaves(Tf, Df, sunlight_top(LA, 23.44, 355.0))
    S0 = bucket(Pf, PET)
    ai = Pf.sum(0) / np.maximum(PET.sum(0), 1.0); cold = np.clip((Tf.mean(0) + 2.0) / 12.0, 0, 1)
    # the mirror equals the production function at the current setting
    c = CROPS['wheat']; ref = crop_yield(Tf, Pf, PET, S0, 0.0, c)[0] / (1000.0 * c['edible'] * c['kcal'] * (1 - c['seed']))
    np.testing.assert_allclose(grain(Tf, Pf, PET, S0, c, 0.8, (0.3, 0.5), 0), ref, rtol=1e-12, atol=1e-12)
    obs = {k: gaez(v) for k, v in GAEZ.items()}
    tile = ((np.floor((LA + 5) / 10) + np.floor((LO + 5) / 10)).astype(int)) % 2; want = 0 if part == 'dev' else 1
    cache = {}
    rows = []
    for eff, band, shift, dry_hi in VARIANTS:
        sc = {}
        for crop, o in obs.items():
            key = (crop, eff, band, shift)
            if key not in cache: cache[key] = grain(Tf, Pf, PET, S0, CROPS[crop], eff, band, shift)
            m = cache[key] * cold * np.clip(ai / dry_hi, 0, 1)
            sel = ok0 & np.isfinite(o) & (tile == want)
            a, b = m[sel], o[sel]
            gm, go = a >= 0.05, b >= 0.1
            tp = np.sum(gm & go); f1 = 2 * tp / max(gm.sum() + go.sum(), 1)
            both = gm & go
            sc[crop] = dict(spearman=float(spearmanr(a, b)[0]), f1=float(f1), level=float(np.median(a[both] / b[both])), cells=int(sel.sum()))
        rows.append(dict(variant=[eff, list(band), shift, dry_hi], primary=float(np.mean([s['spearman'] for s in sc.values()])),
                         f1=float(np.mean([s['f1'] for s in sc.values()])), crops=sc))
    rows.sort(key=lambda r: -r['primary'])
    cur = next(r for r in rows if r['variant'] == [CURRENT[0], list(CURRENT[1]), CURRENT[2], CURRENT[3]])
    show = lambda r: dict(primary=round(r['primary'], 4), f1=round(r['f1'], 4), **{k: (round(v['spearman'], 3), round(v['level'], 2)) for k, v in r['crops'].items()})
    print(part, 'current', show(cur))
    for r in rows[:6]: print(' ', r['variant'], show(r))
    if part == 'dev':
        (CAL / 'dev.json').write_text(json.dumps(dict(part='dev', rows=rows, choice=rows[0]['variant']), indent=1) + '\n'); print('choice', rows[0]['variant'])
    else:
        if (CAL / 'blind.json').exists(): raise SystemExit('blind half already run')
        ch = json.loads((CAL / 'dev.json').read_text())['choice']; chosen = next(r for r in rows if r['variant'] == ch)
        gates = dict(G1=chosen['primary'] >= cur['primary'] + 0.03, G2=chosen['f1'] >= cur['f1'] - 0.02,
                     G3='not needed (no window shift)' if ch[2] == 0 else 'PENDING: rerun the observed crop-calendar diagnostic')
        res = dict(part='blind', rows=rows, current=cur, chosen=chosen, gates=gates)
        (CAL / 'blind.json').write_text(json.dumps(res, indent=1) + '\n'); print(json.dumps(dict(chosen=show(chosen), gates=gates)))


if __name__ == '__main__':
    main(sys.argv[1])
