"""Herders: the model's herding/farming split against the Ethnographic Atlas (calibration/herders_20261120/plan.json).

    .venv/bin/python -I scripts/herders_earth.py dev     # fit k on the dev tiles
    .venv/bin/python -I scripts/herders_earth.py blind   # the single blind evaluation
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
OUT = ROOT / 'output/herders_20261120'; PLAN = ROOT / 'calibration/herders_20261120/plan.json'
EA = ROOT / 'data/cache/dplace_ea'
KS = (0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 10.0)
MID = [2.5, 10.5, 20.5, 30.5, 40.5, 50.5, 60.5, 70.5, 80.5, 93.0]


def societies():
    import pandas as pd
    s = pd.read_csv(EA / 'societies.csv'); x = pd.read_csv(EA / 'data.csv', low_memory=False)
    v = x[x.Var_ID.isin(['EA004', 'EA005'])].pivot_table(index='Soc_ID', columns='Var_ID', values='Code_ID', aggfunc='first').dropna()
    v = v[~v.EA004.str.endswith('NA') & ~v.EA005.str.endswith('NA')]
    m = s.set_index('ID').join(v, how='inner')
    m = m[(m.Latitude >= 0) & (m.Latitude <= 56) & (m.Longitude >= -12) & (m.Longitude <= 125)].copy()
    m['hb'] = m.EA004.str.split('-').str[1].astype(int); m['ab'] = m.EA005.str.split('-').str[1].astype(int)
    m['share'] = [MID[h] / (MID[h] + MID[a]) for h, a in zip(m.hb, m.ab)]
    m['dominant'] = m.hb > m.ab
    m['tile'] = (np.floor(m.Latitude / 10) + np.floor(m.Longitude / 10)).astype(int) % 2
    return m


def fields():
    from harvest.models import settlement_fields
    from rotclimate import biomes
    z = np.load(ROOT / 'output/land_people/earth/earth.npz')
    biome = biomes.classify(np.nan_to_num(z['T_ann']), np.nan_to_num(z['P_ann']), z['land'])
    irr_d = z['irr_distance'] if 'irr_distance' in z.files else z['irr']
    water_km = np.minimum(-6.0 * np.log(np.maximum(np.nan_to_num(irr_d), 1e-12)), 300.0)
    f = settlement_fields(np.nan_to_num(z['capacity']), np.nan_to_num(z['npp']), biome, np.nan_to_num(z['arable']), water_km, np.nan_to_num(z['malaria']))
    land = z['land']
    crop = np.where(land, f['crop_capacity'] * f['clearance'], 0.0); graze = np.where(land, f['pastoral_capacity'], 0.0)
    m3 = lambda a: ndi.uniform_filter(a, 3, mode='nearest')             # 15 arc-min mean (land-weighted below)
    lw = np.maximum(m3(land.astype(float)), 1e-9)
    return z['lat'], z['lon'], land, m3(crop) / lw, m3(graze) / lw


def sample(m):
    lat, lon, land, crop, graze = fields()
    step = float(lat[0] - lat[1])
    r = np.clip(np.round((lat[0] - m.Latitude.values) / step).astype(int), 0, len(lat) - 1)
    c = np.clip(np.round((m.Longitude.values - lon[0]) / step).astype(int), 0, len(lon) - 1)
    # societies on a sea cell move to the nearest land cell
    _, (iy, ix) = ndi.distance_transform_edt(~land, return_indices=True)
    r, c = iy[r, c], ix[r, c]
    return crop[r, c], graze[r, c]


def share(crop, graze, k):
    return np.divide(k * graze, crop + k * graze, out=np.zeros_like(graze), where=(crop + k * graze) > 0)


def ba(pred, obs):
    tp = (pred & obs).sum() / max(obs.sum(), 1); tn = (~pred & ~obs).sum() / max((~obs).sum(), 1)
    return float(0.5 * (tp + tn))


def score(m, crop, graze, k, mask):
    s = share(crop[mask], graze[mask], k); obs = m.dominant.values[mask]
    return dict(BA=ba(s > 0.5, obs), spearman=float(spearmanr(s, m.share.values[mask]).correlation),
                n=int(mask.sum()), dominant=int(obs.sum()), predicted_dominant=int((s > 0.5).sum()),
                mean_model_share=float(s.mean()), mean_observed_share=float(m.share.values[mask].mean()))


def by_region(m, crop, graze, k, mask):
    out = {}
    for reg in sorted(set(m.region.values[mask])):
        q = mask & (m.region.values == reg)
        if q.sum() >= 5:
            out[reg] = dict(n=int(q.sum()), model=round(float(share(crop[q], graze[q], k).mean()), 3), observed=round(float(m.share.values[q].mean()), 3))
    return out


def dev():
    OUT.mkdir(parents=True, exist_ok=True); m = societies(); crop, graze = sample(m); d = m.tile.values == 0
    bas = {k: score(m, crop, graze, k, d)['BA'] for k in KS}
    best = max(bas.values()); kfit = min([k for k in KS if bas[k] == best], key=lambda k: abs(np.log(k)))
    res = dict(plan=str(PLAN.relative_to(ROOT)), n_total=len(m), BA_by_k=bas, k=kfit, k_at_edge=kfit in (KS[0], KS[-1]),
               M0=score(m, crop, graze, 1.0, d), M1=score(m, crop, graze, kfit, d), regions_M0=by_region(m, crop, graze, 1.0, d))
    (OUT / 'dev.json').write_text(json.dumps(res, indent=1)); print(json.dumps({k: v for k, v in res.items() if k != 'regions_M0'}, indent=1))


def blind():
    m = societies(); crop, graze = sample(m); b = m.tile.values == 1; k = json.loads((OUT / 'dev.json').read_text())['k']
    r0, r1 = score(m, crop, graze, 1.0, b), score(m, crop, graze, k, b)
    g1 = r1['BA'] >= r0['BA'] + 0.05; g2 = r0['spearman'] >= 0.30
    res = dict(plan=str(PLAN.relative_to(ROOT)), k=k, M0=r0, M1=r1, gates=dict(G1=bool(g1), G2=bool(g2)),
               adopt_level=bool(g1 and g2), pattern_supported=bool(g2), regions_M0=by_region(m, crop, graze, 1.0, b), regions_M1=by_region(m, crop, graze, k, b))
    (OUT / 'blind.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    {'dev': dev, 'blind': blind}[sys.argv[1]]()
