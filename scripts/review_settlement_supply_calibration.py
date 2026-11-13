"""Independent review of the Earth supply calibration.

From the stored cost arrays: fed-share surface with a separately written
allocator (pandas group sums, sorted link table), e95 interpolation and the
declared decision rules. Production is recomputed from the harvest grid with
explicit formulas. The freight costs come from the atlas network code.
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/settlement_supply_calibration_20261113'; sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
R = json.loads((OUT / 'results.json').read_text()); z = np.load(OUT / 'calibration.npz'); problems = []
x = np.load(ROOT / 'output/settlement_locations_20261110/rome_inputs.npz'); K = 912500.

# production
e = np.load(ROOT / 'output/land_people/earth/earth.npz'); zl, zo = e['lat'], e['lon']; step = float(zl[0] - zl[1])
r = np.clip(np.rint((zl[0] - x['lat']) / step).astype(int), 0, len(zl) - 1); c = np.clip(np.rint((x['lon'] - zo[0]) / step).astype(int), 0, len(zo) - 1)
wheat, barley, arable = [np.nan_to_num(e[k]).astype(float)[r, c] for k in ('kcal_wheat', 'kcal_barley', 'arable')]
hw = np.where(wheat > 0, 336. / np.where(wheat > 0, wheat, 1), np.inf); hb = np.where(barley > 0, 208. / np.where(barley > 0, barley, 1), np.inf)
use_b = hb <= hw; kcal = np.where(np.isfinite(np.minimum(hw, hb)), np.where(use_b, barley, wheat), 0.)
hours = np.where(kcal > 0, np.where(use_b, 208., 336.) / np.where(kcal > 0, kcal, 1) * 1e6, 0.); reap = np.where(kcal > 0, np.where(use_b, 32., 48.) / np.where(kcal > 0, kcal, 1) * 1e6, 0.)
ok = x['land'] & x['allowed']; pot = np.where(ok, kcal * 100 * 81. * arable * .36, 0.).ravel()
people = np.where(ok, x['density'], 0.).ravel() * 81.; res = z['residents']; rural = people * (1 - res.sum() / people.sum())
workers = rural * .4; annual = workers * 600.; peak = np.minimum(annual, workers * 240.)
with np.errstate(divide='ignore', invalid='ignore'):
    kept = np.minimum(1., np.minimum(np.where(pot > 0, annual / (pot * hours.ravel() / 1e6), 1.), np.where(pot > 0, peak / (pot * reap.ravel() / 1e6), 1.)))
surplus = np.clip(np.where(pot > 0, pot * kept, 0.) - rural * K, 0, None) / K
for name, mine, theirs in (('potential', pot.sum() / K, R['world']['potential_person_years']), ('surplus', surplus.sum(), R['world']['surplus_person_years']), ('rural', rural.sum(), R['world']['rural_people'])):
    if not np.isclose(mine, theirs, rtol=1e-9): problems.append(f'{name}: {mine} vs {theirs}')
if not np.allclose(surplus, z['surplus'], rtol=1e-9, atol=1e-6): problems.append('surplus field')

# surface
shares = [float(v) for v in z['shares']]; limits = [int(v) for v in z['limits']]; owner = z['owner']; dist = z['dist'].astype(float); bc = z['between'].astype(float); west = z['west']
def e95(F):
    for k, f in enumerate(F):
        if f >= .95: return shares[0] if k == 0 else shares[k - 1] + (.95 - F[k - 1]) * (shares[k] - shares[k - 1]) / (f - F[k - 1])
    return None
table = {}
for i, L in enumerate(limits):
    share = np.where((owner >= 0) & np.isfinite(dist), np.clip(1 - dist / L, 0, 1), 0.)
    between = np.where(np.isfinite(bc), np.clip(1 - bc / L, 0, 1), 0.).mean(0); np.fill_diagonal(between, 0.)
    Fs = {k: [] for k in ('all', 'west', 'east')}
    for j, m in enumerate(shares):
        got0 = np.zeros(len(res))
        for s in range(owner.shape[0]):
            t = pd.DataFrame(dict(o=owner[s], g=surplus * m / owner.shape[0] * share[s])); g = t[t.o >= 0].groupby('o').g.sum(); got0[g.index.to_numpy()] += g.to_numpy()
        ex = np.clip(got0 - res, 0, None); de = np.clip(res - got0, 0, None); a, b = np.nonzero((between > 0) & (ex[:, None] > 0) & (de[None, :] > 0))
        links = pd.DataFrame(dict(i=a, j=b, s=between[a, b])).sort_values(['s', 'i', 'j'], ascending=[False, True, True]); got = np.zeros(len(res))
        for a_, b_, sh in zip(links.i.to_numpy(), links.j.to_numpy(), links.s.to_numpy()):
            if ex[a_] <= 0 or de[b_] <= 0: continue
            mv = min(ex[a_], de[b_] / sh); ex[a_] -= mv; de[b_] -= mv * sh; got[b_] += mv * sh
            if de[b_] < 1e-9 * max(1., mv): de[b_] = 0.
        fed = np.minimum(got0, res) + got
        if not np.allclose(fed, z['fed'][i, j], rtol=1e-7, atol=1e-6 * res.max()): problems.append(f'fed L={L} e={m}')
        for k, mask in (('all', np.ones(len(res), bool)), ('west', west), ('east', ~west)): Fs[k].append(float(fed[mask].sum() / res[mask].sum()))
    table[str(L)] = {k: e95(v) for k, v in Fs.items()}
    for k in Fs:
        if not np.allclose(Fs[k], R['surface'][str(L)][k]['fed_share'], rtol=1e-7): problems.append(f'F {L} {k}')
        a_, b_ = table[str(L)][k], R['surface'][str(L)][k]['e95']
        if (a_ is None) != (b_ is None) or (a_ is not None and not np.isclose(a_, b_, rtol=1e-7)): problems.append(f'e95 {L} {k}')
ratio = {L: abs(np.log(v['west'] / v['east'])) for L, v in table.items() if v['west'] and v['east']}
best = min(ratio, key=lambda L: (ratio[L], float(L))); keep = '270' in ratio and (ratio['270'] <= np.log(1.25) or ratio['270'] <= 1.1 * ratio[best])
used = '270' if keep else best; ea = table[used]['all']; verdict = 'low' if 1 / 3 < ea else ('more than needed' if 1 / 3 > 2 * ea else 'Earth-supported')
D = R['decision']
if (best, bool(keep), used, verdict) != (D['best_L_by_west_east_agreement'], D['cited_270_kept'], D['L_used'], D['fantasy_one_third']): problems.append('decision')
out = dict(status='passed' if not problems else 'failed', problems=problems, surface_cells=len(limits) * len(shares),
           results_sha256=sha(OUT / 'results.json'), reviewer_sha256=sha(__file__), scope='production, allocation, statistics and decision rules recomputed; freight costs from the atlas network')
(OUT / 'review.json').write_text(json.dumps(out, indent=1) + '\n'); print(out); sys.exit(bool(problems))
