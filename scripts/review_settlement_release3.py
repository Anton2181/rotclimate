"""Independent review of the family-B placement test and the release-3 fantasy positions.

The greedy tiling is re-implemented as an explicit accept/reject loop over
candidates (no blocking raster); scores use dense matching and hand-written
statistics. Only the site-score primitive is shared with the producer.
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from polity import settle

T = ROOT / 'output/settlement_placement_iteration_20261113/family_b'; F3 = ROOT / 'output/settlement_release3_20261113'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(); problems = []


def tiling(density, land, water_km, road, elev, cell, allowed, aridity, prior, seat, marked=(), dry=settle.DRY_WATER_KM):
    coast = ndi.distance_transform_edt(land) * cell
    score, d = settle.site_score(density, land, water_km, coast, road, elev, cell)
    q = ndi.gaussian_filter(np.random.default_rng(1).standard_normal(land.shape), 1.5); score = score * np.exp(.25 * q / q.std())
    ok = land & (d >= 2.) & allowed
    near = np.minimum(np.nan_to_num(water_km, nan=1e9), coast); ok &= (aridity >= .35) | (near <= dry)
    p = np.where(ok, prior, 1.) if prior is not None else np.ones(land.shape)
    rad = np.minimum(np.sqrt(seat / 14.1 * (14.1 / np.maximum(d * p, 1e-9)) ** .7 / np.pi), 60.) / cell * 1.6
    ys, xs = np.nonzero(ok); order = np.argsort(-(score * p)[ok])
    py = [int(y) for y, x in marked]; px = [int(x) for y, x in marked]; pr2 = [float(rad[y, x]) ** 2 for y, x in marked]; out = []
    Y, X, R2 = np.array(py, float), np.array(px, float), np.array(pr2); n = len(py)
    Y = np.concatenate([Y, np.zeros(len(order))]); X = np.concatenate([X, np.zeros(len(order))]); R2 = np.concatenate([R2, np.zeros(len(order))])
    for k in order:
        y, x = ys[k], xs[k]
        if n and np.any((Y[:n] - y) ** 2 + (X[:n] - x) ** 2 <= R2[:n]):
            continue
        Y[n], X[n], R2[n] = y, x, rad[y, x] ** 2; n += 1; out.append((int(y), int(x)))
    return np.array(out)


def ks(a, b):
    a, b = np.sort(a), np.sort(b); v = np.concatenate([a, b])
    return float(np.max(np.abs(np.searchsorted(a, v, side='right') / len(a) - np.searchsorted(b, v, side='right') / len(b))))


def ranks(v):
    v = np.asarray(v); o = np.argsort(v, kind='stable'); r = np.empty(len(v)); s = v[o]; i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and s[j + 1] == s[i]: j += 1
        r[o[i:j + 1]] = (i + j) / 2; i = j + 1
    return r


def quality(obs, pred, allowed, cell):
    d = np.hypot(obs[:, None, 0] - pred[None, :, 0], obs[:, None, 1] - pred[None, :, 1]) * cell
    cost = np.where(d <= 25., -1., 0.); a, b = linear_sum_assignment(cost); f1 = 2 * int((cost[a, b] < 0).sum()) / (len(obs) + len(pred))
    def nn(p):
        dd = np.hypot(p[:, None, 0] - p[None, :, 0], p[:, None, 1] - p[None, :, 1]) * cell; np.fill_diagonal(dd, np.inf); return dd.min(1)
    b_ = max(1, round(100 / cell)); h, w = allowed.shape; ny, nx = (h + b_ - 1) // b_, (w + b_ - 1) // b_
    yy, xx = np.indices((h, w)); block = (yy // b_) * nx + xx // b_
    use = np.bincount(block.ravel(), weights=allowed.ravel(), minlength=ny * nx) / np.bincount(block.ravel(), minlength=ny * nx) >= .3
    cnt = lambda p: np.bincount((p[:, 0] // b_) * nx + p[:, 1] // b_, minlength=ny * nx)[use]
    pc, oc = cnt(pred), cnt(obs); m1 = float(np.corrcoef(ranks(pc), ranks(oc))[0, 1]) if np.ptp(pc) > 0 and np.ptp(oc) > 0 else 0.
    return .6 * f1 + .2 * ((m1 + 1) / 2) + .2 * (1 - ks(nn(obs), nn(pred)))


# ---- Earth test
R = json.loads((T / 'results.json').read_text()); saved = np.load(T / 'positions.npz'); QUADS = ('north_west', 'north_east', 'south_west', 'south_east')
variants = [k.split('__')[1] for k in R['scores'] if k.startswith('han__') and k != 'han__production']; table = {}
for pool in ('han', 'rome'):
    x = np.load(ROOT / R['inputs'][pool]['path']); cell = float(x['cell_km']); allowed = x['allowed']
    D = np.load(ROOT / f'output/core_population_inputs_20261111/{pool}_history.npz')['distance_km']
    ar, ac = np.nonzero(allowed); mr, mc = np.median(ar), np.median(ac); yy, xx = np.indices(allowed.shape)
    mk = dict(whole=np.ones(allowed.shape, bool), north_west=(yy <= mr) & (xx <= mc), north_east=(yy <= mr) & (xx > mc), south_west=(yy > mr) & (xx <= mc), south_east=(yy > mr) & (xx > mc))
    obs = np.column_stack(np.unravel_index(x['real'], allowed.shape))
    for name in ['production'] + variants:
        seat = 40000. if name in ('production', 'Lnone') else R['achieved_counts'][pool][name]['seat_people']
        prior = None if name in ('production', 'Lnone') else np.exp(-D / float(name[1:]))
        towns = tiling(x['density'], x['land'], x['water_km'], x['road'], x['elev'], cell, allowed, x['aridity'], prior, seat)
        if not np.array_equal(towns, saved[f'{pool}__{name}']): problems.append(f'{pool} {name} positions')
        for q, m in mk.items():
            m = m & allowed; o = obs[m[obs[:, 0], obs[:, 1]]]; p = towns[m[towns[:, 0], towns[:, 1]]]
            v = quality(o, p, m, cell); table[pool, name, q] = v
            if abs(v - R['scores'][f'{pool}__{name}'][q]) > 1e-9: problems.append(f'{pool} {name} {q} Q')
qm = lambda pool, v: np.mean([table[pool, v, q] for q in QUADS])
best = lambda pool: max(reversed(variants), key=lambda v: qm(pool, v)); chosen = {'han': best('rome'), 'rome': best('han')}
wins = sum(table[p, chosen[p], q] > table[p, 'production', q] for p in chosen for q in QUADS)
whole = all(table[p, chosen[p], 'whole'] > table[p, 'production', 'whole'] for p in chosen)
overall = max(reversed(variants), key=lambda v: qm('han', v) + qm('rome', v))
if chosen != R['cross_selected'] or wins != R['quadrant_wins'] or bool(wins >= 6 and whole) != R['passed'] or overall != R['best_over_all_eight_quadrants']:
    problems.append('decision')

# ---- fantasy positions
FZ = json.loads((F3 / 'fantasy.json').read_text()); checked = {}
for mode in ('raw', 'corrected'):
    f = np.load(F3 / f'placed_{mode}_fields.npz'); sites = json.loads((F3 / f'placed_{mode}_sites.json').read_text())['sites']
    sys.path.insert(0, str(ROOT / 'scripts')); from settlement_fantasy_inputs import world   # water, aridity, relief inputs
    w = world(mode); c = FZ['climates'][mode]['placement']
    marked = [tuple(int(v) for v in m) for m in f['marked_cells']]
    towns = tiling(f['density'], f['land'], w['water_km'], w['road'], w['elev'], float(f['cell_km']), f['claimed'], w['aridity'], f['prior'], c['seat_people'], marked, w['dry_water_km'])
    new = {(s['row'], s['column']) for s in sites if not s['marked']}
    if {tuple(t) for t in towns} != new or len(towns) != c['unmarked']: problems.append(mode + ' fantasy positions')
    if {(s['row'], s['column']) for s in sites if s['marked']} != set(marked): problems.append(mode + ' marked places moved')
    if len({s['node'] for s in sites}) != len(sites) or not all(f['claimed'][s['row'], s['column']] for s in sites if not s['marked']): problems.append(mode + ' eligibility')
    checked[mode] = dict(unmarked=len(new), marked=len(marked))
out = dict(status='passed' if not problems else 'failed', problems=problems, earth_placements=len(table) // 5, fantasy=checked,
    test_sha256=sha(T / 'results.json'), fantasy_sha256=sha(F3 / 'fantasy.json'), reviewer_sha256=sha(__file__))
(F3 / 'placement_review.json').write_text(json.dumps(out, indent=1) + '\n'); print(out); sys.exit(bool(problems))
