"""Annual runoff AMOUNT of the routing rule vs GRUN (calibration/runoff_amount_20261121/plan.json).

    .venv/bin/python -I scripts/runoff_amount_grun.py dev
    .venv/bin/python -I scripts/runoff_amount_grun.py blind     # run once, after dev has fixed the choice
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from runoff_grun import grun, climate, DAYS

OUT = ROOT / 'output/runoff_amount_20261121'; CAL = ROOT / 'calibration/runoff_amount_20261121'
VARIANTS = [('cap_k', k) for k in (0.75, 0.3, 0.4, 0.5, 0.6, 0.9)] + [('budyko_fu', w) for w in (1.5, 2.0, 2.6, 3.5)]


def pet_months(t):
    return np.clip(0.0023 * 17.8 * (t + 17.8) * 1.9, 0.1, None) * DAYS[:, None, None]     # the rule's PET, mm/month


def runoff(kind, x, t, p):
    pet = pet_months(t)
    if kind == 'cap_k':
        return np.maximum(p - np.minimum(p, x * pet), 0.0).sum(0)
    P, E0 = p.sum(0), pet.sum(0); phi = E0 / np.maximum(P, 1e-6)
    ratio = 1.0 + phi - (1.0 + phi ** x) ** (1.0 / x)                     # Fu (1981): E / P
    return np.where(P > 0, P * (1.0 - np.clip(ratio, 0.0, 1.0)), 0.0)


def to_half_degree(r, land):
    s = np.where(land, r, 0.0).reshape(112, 6, 274, 6).sum((1, 3)); n = land.reshape(112, 6, 274, 6).sum((1, 3))
    return np.where(n >= 18, s / np.maximum(n, 1), np.nan)


def main(part):
    g = grun().sum(0)                                                     # annual mm, [112, 274], north first
    T, _, _, P, _, land = climate()
    lat = 56 - (np.arange(112) + 0.5) * 0.5; lon = -12 + (np.arange(274) + 0.5) * 0.5
    LA, LO = np.meshgrid(lat, lon, indexing='ij')
    tile = ((np.floor((LA + 5) / 10) + np.floor((LO + 5) / 10)).astype(int)) % 2
    want = 0 if part == 'dev' else 1
    rows = []
    for kind, x in VARIANTS:
        m = to_half_degree(runoff(kind, x, T, P), land)
        ok = np.isfinite(m) & np.isfinite(g) & (g >= 5) & (tile == want)
        a, b = m[ok], g[ok]
        rows.append(dict(variant=kind, value=x, cells=int(ok.sum()), primary=float(np.sqrt(np.mean(np.log((a + 10) / (b + 10)) ** 2))),
                         median_ratio=float(np.median(a / b)), rank=float(spearmanr(a, b)[0])))
        print(part, kind, x, {k: round(v, 4) if isinstance(v, float) else v for k, v in rows[-1].items() if k not in ('variant', 'value')}, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if part == 'dev':
        best = min(rows, key=lambda r: r['primary'])
        res = dict(part='dev', rows=rows, choice=dict(variant=best['variant'], value=best['value']))
        (CAL / 'dev.json').write_text(json.dumps(res, indent=1) + '\n'); print('choice', res['choice'])
    else:
        dev = json.loads((CAL / 'dev.json').read_text()); ch = dev['choice']
        if (CAL / 'blind.json').exists(): raise SystemExit('blind half already run')
        cur = next(r for r in rows if r['variant'] == 'cap_k' and r['value'] == 0.75)
        chosen = next(r for r in rows if r['variant'] == ch['variant'] and r['value'] == ch['value'])
        gates = dict(G1=chosen['primary'] <= 0.85 * cur['primary'], G2=chosen['rank'] >= cur['rank'] - 0.02,
                     G3=0.8 <= chosen['median_ratio'] <= 1.25)
        res = dict(part='blind', rows=rows, choice=ch, current=cur, chosen=chosen, gates=gates, adopt=all(gates.values()))
        (CAL / 'blind.json').write_text(json.dumps(res, indent=1) + '\n'); print(json.dumps(dict(gates=gates, adopt=res['adopt'])))


if __name__ == '__main__':
    main(sys.argv[1])
