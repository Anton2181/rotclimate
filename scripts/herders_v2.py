"""Herders v2: marginality herding share (calibration/herders_20261120/plan_v2.json).

    .venv/bin/python -I scripts/herders_v2.py dev     # choose the rule on the 546 (seen) societies
    .venv/bin/python -I scripts/herders_v2.py blind   # the single blind evaluation, Africa south of the equator
"""
import itertools, json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import herders_earth as H1

OUT = ROOT / 'output/herders_20261120'; PLAN = ROOT / 'calibration/herders_20261120/plan_v2.json'
NORTH = ROOT / 'output/land_people/earth/earth.npz'; SOUTH = ROOT / 'output/land_people/earth_south/earth.npz'
FAM = {'L': [(l0, l1) for l0 in (0, 30, 60, 90) for l1 in (120, 150, 180, 210, 240, 270, 300)],
       'N': [(n0, n1) for n0 in (0, 100, 200) for n1 in (400, 600, 800, 1000, 1200)]}
LW, PS = (240, 270, 300), (0.0, 0.25, 0.5, 0.75)


def societies(south):
    import pandas as pd
    s = pd.read_csv(H1.EA / 'societies.csv'); x = pd.read_csv(H1.EA / 'data.csv', low_memory=False)
    v = x[x.Var_ID.isin(['EA004', 'EA005'])].pivot_table(index='Soc_ID', columns='Var_ID', values='Code_ID', aggfunc='first').dropna()
    v = v[~v.EA004.str.endswith('NA') & ~v.EA005.str.endswith('NA')]
    m = s.set_index('ID').join(v, how='inner')
    q = ((m.Latitude < 0) & (m.Latitude >= -36) & (m.Longitude >= 8) & (m.Longitude <= 52)) if south else \
        ((m.Latitude >= 0) & (m.Latitude <= 56) & (m.Longitude >= -12) & (m.Longitude <= 125))
    m = m[q].copy()
    m['hb'] = m.EA004.str.split('-').str[1].astype(int); m['ab'] = m.EA005.str.split('-').str[1].astype(int)
    m['share'] = [H1.MID[h] / (H1.MID[h] + H1.MID[a]) for h, a in zip(m.hb, m.ab)]; m['dominant'] = m.hb > m.ab
    return m


def sample(m, path):
    from harvest.models import settlement_fields
    from rotclimate import biomes
    z = np.load(path); land = z['land']
    biome = biomes.classify(np.nan_to_num(z['T_ann']), np.nan_to_num(z['P_ann']), land)
    irr_d = z['irr_distance'] if 'irr_distance' in z.files else z['irr']
    water_km = np.minimum(-6.0 * np.log(np.maximum(np.nan_to_num(irr_d), 1e-12)), 300.0)
    f = settlement_fields(np.nan_to_num(z['capacity']), np.nan_to_num(z['npp']), biome, np.nan_to_num(z['arable']), water_km, np.nan_to_num(z['malaria']))
    lw = np.maximum(ndi.uniform_filter(land.astype(float), 3, mode='nearest'), 1e-9)
    mean = lambda a: ndi.uniform_filter(np.where(land, np.nan_to_num(a), 0.0), 3, mode='nearest') / lw
    flds = dict(crop=mean(f['crop_capacity'] * f['clearance']), graze=mean(f['pastoral_capacity']), L=mean(z['lgp_days']),
                N=mean(z['npp']), T=mean(z['T_ann']))
    lat, lon = z['lat'], z['lon']; step = float(lat[0] - lat[1])
    r = np.clip(np.round((lat[0] - m.Latitude.values) / step).astype(int), 0, len(lat) - 1)
    c = np.clip(np.round((m.Longitude.values - lon[0]) / step).astype(int), 0, len(lon) - 1)
    _, (iy, ix) = ndi.distance_transform_edt(~land, return_indices=True); r, c = iy[r, c], ix[r, c]
    return {k: v[r, c] for k, v in flds.items()}


def marg(x, fam, lo, hi):
    return np.clip((hi - x[fam]) / (hi - lo), 0, 1)


def rule(x, fam, lo, hi, lw, p):
    return marg(x, fam, lo, hi) * (1 - p * ((x['L'] > lw) & (x['T'] > 20)))


def level(g, y):
    A = np.c_[np.ones_like(g), g]; (b, a), *_ = np.linalg.lstsq(A, y, rcond=None)
    if a < 0:
        a, b = 0.0, float(y.mean())
    return float(b), float(a)


def predict(x, spec):
    return np.clip(spec['b'] + spec['a'] * rule(x, spec['family'], spec['lo'], spec['hi'], spec['lw'], spec['p']), 0, 1)


def sp(a, b):
    return float(spearmanr(np.round(a, 9), b).correlation)


def dev():
    m = societies(False); x = sample(m, NORTH); y = m.share.values; best = None
    for fam, (lo, hi), lw, p in itertools.chain.from_iterable(itertools.product([f], FAM[f], LW, PS) for f in FAM):
        g = rule(x, fam, lo, hi, lw, p)
        if g.std() == 0:
            continue
        b, a = level(g, y); pred = np.clip(b + a * g, 0, 1); s = sp(pred, y); e = float(np.mean((pred - y) ** 2))
        cand = (s, -e, dict(family=fam, lo=lo, hi=hi, lw=lw, p=p, b=b, a=a, spearman=s, mse=e))
        if best is None or cand[:2] > best[:2]:
            best = cand
    spec = best[2]; base = H1.share(x['crop'], x['graze'], 1.0)
    res = dict(plan=str(PLAN.relative_to(ROOT)), n=len(m), chosen=spec, current_spearman=sp(base, y),
               chosen_BA=H1.ba(predict(x, spec) > 0.5, m.dominant.values), current_BA=H1.ba(base > 0.5, m.dominant.values))
    OUT.mkdir(parents=True, exist_ok=True); (OUT / 'v2_dev.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def blind():
    spec = json.loads((OUT / 'v2_dev.json').read_text())['chosen']; m = societies(True); x = sample(m, SOUTH); y = m.share.values
    pred = predict(x, spec); base = H1.share(x['crop'], x['graze'], 1.0); s2, s0 = sp(pred, y), sp(base, y)
    g1, g2 = s2 >= 0.40, s2 >= s0 + 0.15
    res = dict(plan=str(PLAN.relative_to(ROOT)), n=len(m), mainly_herders=int(m.dominant.sum()), spec=spec,
               v2=dict(spearman=s2, BA=H1.ba(pred > 0.5, m.dominant.values), mean=float(pred.mean())),
               current=dict(spearman=s0, BA=H1.ba(base > 0.5, m.dominant.values), mean=float(base.mean())), observed_mean=float(y.mean()),
               gates=dict(G1=bool(g1), G2=bool(g2)), adopt=bool(g1 and g2))
    (OUT / 'v2_blind.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    {'dev': dev, 'blind': blind}[sys.argv[1]]()
