"""Malaria suitability vs sickle-cell and G6PD gene frequencies (calibration/malaria_genetics_20261120/plan.json).

    .venv/bin/python -I scripts/malaria_genetics.py dev
    .venv/bin/python -I scripts/malaria_genetics.py blind     # run once
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
OUT = ROOT / 'output/malaria_genetics_20261120'; PLAN = ROOT / 'calibration/malaria_genetics_20261120/plan.json'
GEN = ROOT / 'data/cache/map_genetics'
TARGETS = {'HbS': 'Explorer__2013_Sickle_Haemoglobin_HbS_Allele_Freq_Global_5k_Decompressed',
           'G6PD': 'Explorer__2012_G6PDd_Allele_Frequency_Global_5k_Decompressed'}
P1S = (20, 40, 80, 120, 160, 240, None)          # None: no rain gate
ROWS, COLS = slice(408, 1080), slice(2016, 3660)  # Earth run window in the global 5' WorldClim grid


def targets():
    import tifffile
    out = {}
    for k, name in TARGETS.items():
        a = tifffile.imread(GEN / f'{name}.tif').astype(float); a[(a < 0) | ~np.isfinite(a)] = np.nan
        v = np.isfinite(a); s = np.where(v, a, 0).reshape(672, 2, 1644, 2).sum((1, 3)); n = v.reshape(672, 2, 1644, 2).sum((1, 3))
        out[k] = np.where(n > 0, s / np.maximum(n, 1), np.nan)            # 2.5' -> 5'
    return out


def inputs():
    from rotclimate.earth import _wc
    z = np.load(ROOT / 'output/land_people/earth/earth.npz')
    T = np.stack([_wc('tavg', m + 1)[ROWS, COLS] for m in range(12)]); P = np.stack([_wc('prec', m + 1)[ROWS, COLS] for m in range(12)])
    return z, np.nan_to_num(T), np.nan_to_num(P)


def variant(T, P, irr, p1, summary):
    from harvest.models import malaria_thermal, specification
    from scripts.land_people import smoothstep
    spec = specification(); th = malaria_thermal(T)
    moist = np.ones_like(P) if p1 is None else np.maximum(smoothstep(P, 0, p1), irr * spec['irrigation_mosquito_water'])
    monthly = th * np.clip(moist, 0, 1)
    return monthly.mean(0) if summary == 'mean' else (monthly >= spec['malaria_season_threshold']).mean(0)


def blocks(a, ok, n=12):
    v = np.where(ok, a, 0.0).reshape(56, n, 137, n).sum((1, 3)); c = ok.reshape(56, n, 137, n).sum((1, 3))
    return np.where(c > 0, v / np.maximum(c, 1), np.nan), c


def setup():
    z, T, P = inputs(); land = z['land']; irr = np.nan_to_num(z['irr']); tg = targets()
    lat = z['lat']; lon = z['lon']
    blat = lat.reshape(56, 12).mean(1); blon = lon.reshape(137, 12).mean(1)
    BL, BO = np.meshgrid(blat, blon, indexing='ij')
    tile = ((np.floor(BL / 10) + np.floor(BO / 10)).astype(int)) % 2
    africa = (BO < 52) & (BL < 37) & ~((BO > 32) & (BL > 30))      # Africa (rough box; Sinai/Levant excluded)
    tb = {}
    for k, a in tg.items():
        ok = land & np.isfinite(a); b, c = blocks(np.nan_to_num(a), ok); _, cl = blocks(np.ones_like(a), land)
        tb[k] = (b, (c >= 72) & (cl >= 72))                          # >= 50 % valid target and >= 50 % land of 144 cells
    return z, T, P, land, irr, tb, tile, africa


def score(m, land, tb, tile, africa, part):
    mb, _ = blocks(m, land); res = {}
    for k, (b, ok) in tb.items():
        for name, sel in (('all', ok & (tile == part)), ('africa', ok & (tile == part) & africa), ('outside_africa', ok & (tile == part) & ~africa)):
            res[f'{k}_{name}'] = (float(spearmanr(mb[sel], b[sel]).correlation) if sel.sum() >= 10 else None, int(sel.sum()))
    return res


def control(z, T, P, irr):
    """Amendment A1: M0 must equal the map's own malaria function (harvest.models.malaria_fields) on these inputs.
    (The Earth run's stored 'malaria' is the older MARA index, a different definition.)"""
    from harvest.models import malaria_fields
    land = z['land']; ref = malaria_fields(T[:, land], P[:, land], irr[land])['malaria']
    return float(np.max(np.abs(variant(T, P, irr, 80, 'mean')[land] - ref)))


def run(part):
    z, T, P, land, irr, tb, tile, africa = setup()
    res = dict(plan=str(PLAN.relative_to(ROOT)), control_max_abs_diff_vs_map_function=control(z, T, P, irr), variants={})
    for p1 in P1S:
        for summ in ('mean', 'months'):
            key = f"P1={p1 or 'none'}|{summ}"; res['variants'][key] = score(variant(T, P, irr, p1, summ), land, tb, tile, africa, part)
    return res


def dev():
    OUT.mkdir(parents=True, exist_ok=True); res = run(0)
    best = max(res['variants'], key=lambda k: res['variants'][k]['HbS_all'][0]); res['chosen'] = best
    (OUT / 'dev.json').write_text(json.dumps(res, indent=1))
    print('control', res['control_max_abs_diff_vs_map_function'])
    for k, v in res['variants'].items():
        print(k.ljust(18), ' '.join(f"{n}={s[0]:.2f}" if s[0] is not None else f"{n}=NA" for n, s in v.items()))
    print('chosen', best, 'blocks', res['variants'][best]['HbS_all'][1])


def blind():
    chosen = json.loads((OUT / 'dev.json').read_text())['chosen']; r = run(1); v = r['variants']; m0 = v['P1=80|mean']; c = v[chosen]
    V = m0['HbS_all'][0] >= 0.30; g1 = c['HbS_all'][0] >= m0['HbS_all'][0] + 0.05; g2 = c['G6PD_all'][0] >= m0['G6PD_all'][0] - 0.02
    res = dict(plan=str(PLAN.relative_to(ROOT)), chosen=chosen, M0=m0, chosen_scores=c, gates=dict(V=bool(V), G1=bool(g1), G2=bool(g2)),
               adopt=bool(g1 and g2 and chosen != 'P1=80|mean'))
    (OUT / 'blind.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    {'dev': dev, 'blind': blind}[sys.argv[1]]()
