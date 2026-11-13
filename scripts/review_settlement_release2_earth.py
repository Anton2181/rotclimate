"""Independent review of the release-2 Earth calibration.

Separate code paths: pandas tables, distance-transform hinterlands with an
explicit tie rule, normal-equation least squares, hand-written KS and
Spearman, dense minimum-cost matching for unique 25 km F1.
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rotclimate.earth import forward

OUT = ROOT / 'output/settlement_release2_20261113'
CACHE = ROOT / 'data/cache/roman_city_source_recovery_20261113'
POOLS = ROOT / 'output/settlement_locations_20261110'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
R = json.loads((OUT / 'results.json').read_text())
problems = []


def close(a, b, tol, what):
    if not np.allclose(a, b, rtol=tol, atol=tol):
        problems.append(f'{what}: {a} != {b}')


def ks(a, b):
    a, b = np.sort(a), np.sort(b); v = np.concatenate([a, b])
    return float(np.max(np.abs(np.searchsorted(a, v, side='right') / len(a) - np.searchsorted(b, v, side='right') / len(b))))


def ranks(v):
    order = np.argsort(v, kind='stable'); r = np.empty(len(v)); s = np.asarray(v)[order]; i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and s[j + 1] == s[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2; i = j + 1
    return r


def quality(obs, pred, allowed, cell):
    d = np.hypot(obs[:, None, 0] - pred[None, :, 0], obs[:, None, 1] - pred[None, :, 1]) * cell
    cost = np.where(d <= 25., -1., 0.); a, b = linear_sum_assignment(cost)
    f1 = 2 * int((cost[a, b] < 0).sum()) / (len(obs) + len(pred))
    def nn(p):
        dd = np.hypot(p[:, None, 0] - p[None, :, 0], p[:, None, 1] - p[None, :, 1]) * cell
        np.fill_diagonal(dd, np.inf); return dd.min(1)
    m3 = ks(nn(obs), nn(pred))
    b_ = max(1, round(100 / cell)); h, w = allowed.shape; ny, nx = (h + b_ - 1) // b_, (w + b_ - 1) // b_
    yy, xx = np.indices((h, w)); block = (yy // b_) * nx + xx // b_
    cover = np.bincount(block.ravel(), weights=allowed.ravel(), minlength=ny * nx) / np.bincount(block.ravel(), minlength=ny * nx)
    use = cover >= .3
    cnt = lambda p: np.bincount((p[:, 0] // b_) * nx + p[:, 1] // b_, minlength=ny * nx)[use]
    pc, oc = cnt(pred), cnt(obs)
    m1 = float(np.corrcoef(ranks(pc), ranks(oc))[0, 1]) if np.ptp(pc) > 0 and np.ptp(oc) > 0 else 0.
    return .6 * f1 + .4 * .5 * ((m1 + 1) / 2 + 1 - m3)


# ---- placement quadrants
positions = np.load(ROOT / 'output/settlement_joint_locations_20261112/positions.npz')
wins = 0
for row in R['placement']['rows']:
    x = np.load(POOLS / f"{row['pool']}_inputs.npz"); allowed = x['allowed']; cell = float(x['cell_km'])
    ar, ac = np.nonzero(allowed); mr, mc = np.median(ar), np.median(ac); yy, xx = np.indices(allowed.shape)
    mask = {'whole': np.ones(allowed.shape, bool), 'north_west': (yy <= mr) & (xx <= mc), 'north_east': (yy <= mr) & (xx > mc),
            'south_west': (yy > mr) & (xx <= mc), 'south_east': (yy > mr) & (xx > mc)}[row['quadrant']] & allowed
    obs = np.column_stack(np.unravel_index(x['real'], allowed.shape)); obs = obs[mask[obs[:, 0], obs[:, 1]]]
    q = {}
    for variant, label in (('production', 'production'), ('fixed18_L800', 'finalist')):
        p = positions[f"{row['pool']}__{variant}__1"]; p = p[mask[p[:, 0], p[:, 1]]]
        q[label] = quality(obs, p, mask, cell); close(q[label], row[f'{label}_Q'], 1e-9, f"{row['pool']} {row['quadrant']} {label} Q")
    if row['quadrant'] != 'whole':
        wins += q['finalist'] > q['production']
if wins != R['placement']['quadrant_wins'] or R['placement']['passed'] != (wins >= 6 and R['placement']['both_pools_better']):
    problems.append('placement decision')

# ---- size cohort
c = pd.read_csv(CACHE / 'cities.csv', encoding='cp1252', keep_default_na=False, dtype=str)
a = pd.read_csv(CACHE / 'areas.csv', encoding='utf-8-sig', keep_default_na=False, dtype=str)
start = pd.to_numeric(c['Start Date']); end = pd.to_numeric(c['End Date'], errors='coerce')
c = c[(start <= 150) & (end.isna() | (end >= 150))].merge(a, on='Primary Key', how='left')
x = np.load(POOLS / 'rome_inputs.npz'); land = x['land']; cell = float(x['cell_km']); ny, nx = land.shape
core = np.load(ROOT / 'output/core_population_inputs_20261111/rome_history.npz')['distance_km']
px, py = forward(c['Latitude (Y)'].astype(float).to_numpy(), c['Longitude (X)'].astype(float).to_numpy(), 40.0, 17.0)
col = np.rint(px / cell + (nx - 1) / 2).astype(int); row = np.rint((ny - 1) / 2 - py / cell).astype(int)
inside = (row >= 0) & (row < ny) & (col >= 0) & (col < nx)
lr, lc = np.nonzero(land); LEGACY = set(int(v) for v in x['real']); TIES = []
def nearest_land(r0, c0):
    if land[r0, c0]:
        return r0, c0
    d = (lr - r0) ** 2 + (lc - c0) ** 2; best = np.flatnonzero(d == d.min())
    # Equidistant land cells: the legacy record decides, never a new preference.
    known = [b for b in best if lr[b] * nx + lc[b] in LEGACY]
    if len(best) > 1:
        TIES.append(len(best))
    pick = known[0] if known else best[0]
    return int(lr[pick]), int(lc[pick])
snapped = np.array([nearest_land(min(max(r0, 0), ny - 1), min(max(c0, 0), nx - 1)) for r0, c0 in zip(row, col)])
c = c.assign(sr=snapped[:, 0], sc=snapped[:, 1], inside=inside)
cells = np.unique((c.sr * nx + c.sc)[c.inside])
if not np.array_equal(cells, x['real']):
    problems.append('snapped cells differ from legacy')
cr, cc_ = np.unravel_index(cells, land.shape); people = np.where(land, x['density'], 0.) * cell ** 2
Hsum = np.zeros(len(cells))
for i0 in range(0, len(lr), 4000):       # brute-force exact integer distances, equal split of ties
    r_, c_ = lr[i0:i0 + 4000], lc[i0:i0 + 4000]
    d2 = (r_[:, None] - cr[None]) ** 2 + (c_[:, None] - cc_[None]) ** 2
    best = d2.min(1); tie = (d2 == best[:, None]) & (best[:, None] * cell ** 2 <= 3600.)
    share = tie / np.maximum(tie.sum(1, keepdims=True), 1)
    Hsum += (share * people[r_, c_][:, None]).sum(0)
H = pd.Series(Hsum, index=cells)
coast = ndi.distance_transform_edt(land) * cell; roadd = ndi.distance_transform_edt(~x['road']) * cell
water = np.nan_to_num(x['water_km'], nan=1e9)
d = c[c.inside & c['Area'].notna() & x['allowed'][c.sr, c.sc]].copy()
flat = d.sr * nx + d.sc
d = d.assign(area=d['Area'].astype(float), lnH=np.log(H.reindex(flat).to_numpy()), coast=(coast[d.sr, d.sc] <= cell).astype(float),
             river=(water[d.sr, d.sc] <= 3).astype(float), road=(roadd[d.sr, d.sc] <= 1.5 * cell).astype(float), core=core[d.sr, d.sc] / 1000.,
             fold=[hashlib.sha256(p.encode()).digest()[0] % 4 for p in d['Province']])
if len(d) != R['size_cohort']['with_area_on_allowed_land']:
    problems.append('cohort size')
TERMS = {'M0': [], 'M1': ['lnH'], 'M2': ['lnH', 'coast', 'river', 'road'], 'M3': ['lnH', 'coast', 'river', 'road', 'core']}
for label, sub in (('primary', d[~d.area.isin([20., 30.])]), ('all_values', d)):
    rep = R['sizes'][label]; y = np.log(sub.area.to_numpy()); fold = sub.fold.to_numpy()
    if len(sub) != rep['n'] or [int((fold == f).sum()) for f in range(4)] != rep['fold_sizes']:
        problems.append(label + ' folds')
    mae = {}; held = {}
    for name, terms in TERMS.items():
        X = np.column_stack([np.ones(len(sub))] + [sub[t].to_numpy() for t in terms]); pred = np.empty(len(y))
        for f in range(4):
            tr = fold != f; beta = np.linalg.solve(X[tr].T @ X[tr], X[tr].T @ y[tr]); pred[~tr] = X[~tr] @ beta
        mae[name] = float(np.mean(np.abs(y - pred))); held[name] = pred
        close(mae[name], rep['models'][name]['heldout_mae'], 1e-8, f'{label} {name} MAE')
        close(float(np.std(y - pred)), rep['models'][name]['heldout_sigma'], 1e-8, f'{label} {name} sigma')
        close(np.linalg.solve(X.T @ X, X.T @ y), rep['models'][name]['full_coefficients'], 1e-7, f'{label} {name} coefficients')
    chosen = 'M0'
    for name in ('M1', 'M2', 'M3'):
        if mae[name] <= mae[chosen] * .98:
            chosen = name
    if chosen != rep['selected']:
        problems.append(label + ' selection')
    sigma = float(np.std(y - held[chosen])); area = np.exp(y); kss = []; ratios = []
    for s in (1, 7, 19, 43, 97):
        e = np.clip(np.random.default_rng(s).standard_normal(len(y)), -2.5, 2.5)
        g = np.clip(np.exp(held[chosen] + sigma * e), area.min(), area.max()); kss.append(ks(g, area)); ratios.append(g.sum() / area.sum())
    close(np.mean(kss), rep['gate']['mean_ks'], 1e-9, label + ' KS'); close(np.mean(ratios), rep['gate']['mean_total_area_ratio'], 1e-9, label + ' ratio')
    if rep['gate']['passed'] != (np.mean(kss) <= .10 and .8 <= np.mean(ratios) <= 1.25):
        problems.append(label + ' gate')
A = a['Area'].astype(float).to_numpy()
t = np.clip((np.log(A) - np.log(50.)) / (np.log(400.) - np.log(50.)), 0, 1)
close(float((A * (100 + 400 * t)).sum()), R['residents']['central_total_all_885_official_areas'], 1e-9, 'central residents')
result = dict(status='passed' if not problems else 'failed', problems=problems, results_sha256=sha(OUT / 'results.json'),
              reviewer_sha256=sha(__file__), placement_rows=len(R['placement']['rows']), size_models_checked=8,
              off_land_snaps_with_equidistant_land=len(TIES))
(OUT / 'review.json').write_text(json.dumps(result, indent=1) + '\n'); print(result); sys.exit(bool(problems))
