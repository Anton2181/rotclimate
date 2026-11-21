"""Forage-growth seasonality vs FLUXCOM-X GPP (calibration/forage_season_20261121/plan.json).

    .venv/bin/python -I scripts/forage_season_gpp.py dev
    .venv/bin/python -I scripts/forage_season_gpp.py blind     # run once
"""
import itertools, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from runoff_grun import climate

CAL = ROOT / 'calibration/forage_season_20261121'
VARIANTS = list(itertools.product((-2, 0, 2, 5), (10, 15, 20), (20, 50, 100), (0, 1)))
CURRENT = (0, 15, 50, 0)


def gpp():
    import h5py
    acc = None
    files = sorted((ROOT / 'data/cache/fluxcom').glob('GPP_20*_050_monthly.nc'))
    for f in files:
        g = h5py.File(f)['GPP'][:].astype(float)                          # [12, 360, 720], lat 89.75 -> -89.75, lon -179.75 ->
        acc = g if acc is None else acc + g
    g = acc / len(files)
    i = np.arange(360)[(89.75 - np.arange(360) * 0.5 < 56) & (89.75 - np.arange(360) * 0.5 > 0)]
    j = np.arange(720)[(-179.75 + np.arange(720) * 0.5 > -12) & (-179.75 + np.arange(720) * 0.5 < 125)]
    return g[:, i][:, :, j], len(files)                                  # [12, 112, 274], north first


def half(a, land):
    s = np.where(land, a, 0.0).reshape(12, 112, 6, 274, 6).sum((2, 4)); n = land.reshape(112, 6, 274, 6).sum((1, 3))
    return np.where(n >= 18, s / np.maximum(n, 1), np.nan)


def weights(T, P, floor, span, rain_half, memory):
    if memory: P = 0.5 * (P + np.roll(P, 1, axis=0))
    return np.clip((T - floor) / span, 0, 1) * P / (P + rain_half)


def blocks(a, ok):
    v = np.where(ok, a, 0.0)[:, :110, :270].reshape(12, 22, 5, 54, 5).sum((2, 4)); n = ok[:110, :270].reshape(22, 5, 54, 5).sum((1, 3))
    return np.where(n >= 13, v / np.maximum(n, 1), np.nan), n >= 13


def main(part):
    obs, years = gpp()
    T, _, _, P, _, land = climate()
    Th, Ph = half(T, land), half(P, land)
    blat = 56 - (np.arange(22) + 0.5) * 2.5; blon = -12 + (np.arange(54) + 0.5) * 2.5
    BL, BO = np.meshgrid(blat, blon, indexing='ij'); tile = ((np.floor((BL + 5) / 10) + np.floor((BO + 5) / 10)).astype(int)) % 2
    want = 0 if part == 'dev' else 1
    base_ok = np.isfinite(obs).all(0) & np.isfinite(Th).all(0) & (np.nansum(obs, 0) * 30.4 >= 100)
    rows = []
    for v in VARIANTS:
        w = weights(Th, Ph, *v); ok = base_ok & (w.sum(0) > 0)
        mb, valid = blocks(w / np.where(ok, w.sum(0), 1), ok); gb, _ = blocks(obs / np.where(ok, obs.sum(0), 1), ok)
        sel = valid & (tile == want)
        a, b = mb[:, sel], gb[:, sel]
        a, b = a - a.mean(0), b - b.mean(0)
        r = (a * b).sum(0) / np.sqrt((a * a).sum(0) * (b * b).sum(0) + 1e-30)
        d = np.abs(np.argmax(mb[:, sel], 0) - np.argmax(gb[:, sel], 0)); d = np.minimum(d, 12 - d)
        rows.append(dict(variant=list(v), blocks=int(sel.sum()), primary=float(np.median(r)), q25=float(np.quantile(r, .25)), peak=float(np.mean(d <= 1))))
    rows.sort(key=lambda r: -r['primary'])
    cur = next(r for r in rows if tuple(r['variant']) == CURRENT)
    print(part, 'years', years, 'blocks', cur['blocks'], 'current', {k: round(cur[k], 4) for k in ('primary', 'q25', 'peak')})
    for r in rows[:6]: print(' ', r['variant'], {k: round(r[k], 4) for k in ('primary', 'q25', 'peak')})
    if part == 'dev':
        (CAL / 'dev.json').write_text(json.dumps(dict(part='dev', years=years, rows=rows, choice=rows[0]['variant']), indent=1) + '\n')
        print('choice', rows[0]['variant'])
    else:
        if (CAL / 'blind.json').exists(): raise SystemExit('blind half already run')
        ch = json.loads((CAL / 'dev.json').read_text())['choice']; chosen = next(r for r in rows if r['variant'] == ch)
        gates = dict(V=cur['primary'] >= 0.6, G1=chosen['primary'] >= cur['primary'] + 0.03, G2=chosen['peak'] >= cur['peak'] - 0.02)
        res = dict(part='blind', rows=rows, current=cur, chosen=chosen, gates=gates, adopt=gates['G1'] and gates['G2'])
        (CAL / 'blind.json').write_text(json.dumps(res, indent=1) + '\n'); print(json.dumps(dict(chosen=chosen, gates=gates, adopt=res['adopt'])))


if __name__ == '__main__':
    main(sys.argv[1])
