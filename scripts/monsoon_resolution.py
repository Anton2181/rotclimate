"""Monsoon resolution diagnostic (calibration/monsoon_resolution_20261121/plan.json): peak-season and annual rain ratios at 56/28/14 km.

    .venv/bin/python -I scripts/monsoon_resolution.py
"""
import glob, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'output/monsoon_resolution_20261121'
REF = ROOT / 'output/plateau_height_20261120/refit/j29_convective_rain_0.5497'
TARGET = ['mexico', 'texas_plains', 'sahel_niger']; GUARD = ['bengal', 'najd_arabia']


def cells(km, region):
    pats = [str(REF / 'candidate_*' / 'cells' / f'{region}.npz')] if km == 56 else [str(OUT / f'k{km}_g*' / 'cells' / f'{region}.npz')]
    f = [p for pat in pats for p in glob.glob(pat)]
    return np.load(f[0]) if f else None


def ratios(z):
    Ps, Po = z['Ps'].mean(1), z['Po'].mean(1); peak = np.argsort(Po)[-3:]
    return dict(peak=float(Ps[peak].sum() / Po[peak].sum()), annual=float(Ps.sum() / Po.sum()), peak_months=sorted(int(m) + 1 for m in peak),
                sim_cycle=[round(float(x), 1) for x in Ps], obs_cycle=[round(float(x), 1) for x in Po])


if __name__ == '__main__':
    res = {}
    for r in TARGET + GUARD:
        res[r] = {km: (ratios(z) if (z := cells(km, r)) is not None else None) for km in (56, 28, 14)}
    gains = {r: res[r][14]['peak'] - res[r][56]['peak'] for r in TARGET if res[r][14] and res[r][56]}
    verdict = None
    if len(gains) == 3:
        verdict = 'RESOLUTION' if sum(g >= 0.25 for g in gains.values()) >= 2 else 'PHYSICS'
    (OUT / 'result.json').write_text(json.dumps(dict(plan='calibration/monsoon_resolution_20261121/plan.json', regions=res, gain_14_vs_56=gains, verdict=verdict), indent=1) + '\n')
    for r, v in res.items():
        print(r.ljust(13), ' '.join(f"{km}km peak {x['peak']:.2f} ann {x['annual']:.2f}" if x else f'{km}km  --' for km, x in v.items()))
    print('gains', {k: round(v, 3) for k, v in gains.items()}, 'verdict', verdict)
