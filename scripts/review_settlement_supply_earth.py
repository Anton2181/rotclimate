"""Independent review of the Roman grain-supply pilot.

Own heap-based shortest paths on an implicitly defined grid (no sparse matrix)
for a sample of cities; demand and supply totals with pandas; fed-share curve
with a separately written allocator.
"""
import hashlib, heapq, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_supply_earth as P
from rotclimate.earth import forward

OUT = ROOT / 'output/settlement_supply_earth_20261113'; sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
R = json.loads((OUT / 'results.json').read_text()); z = np.load(OUT / 'pilot.npz'); x = dict(np.load(P.POOL)); problems = []
land = x['land']; h, w = land.shape; road = x['road']; river = land & (np.nan_to_num(x['water_km'], nan=99.) <= 1.5)
rate = np.where(~land, 1 / 28, np.where(river, 7.5 / 28, np.where(road, 1., 2.))).ravel(); L = land.ravel()


def own_paths(source, limit=270.):
    best = {source: 0.}; heap = [(0., source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > best.get(u, np.inf): continue
        r, c = divmod(u, w)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if (dr or dc) and 0 <= r + dr < h and 0 <= c + dc < w:
                    v = (r + dr) * w + c + dc
                    nd = d + .5 * (rate[u] + rate[v]) * 9. * (2 ** .5 if dr and dc else 1.) + (4. if L[u] != L[v] else 0.)
                    if nd <= limit and nd < best.get(v, np.inf):
                        best[v] = nd; heapq.heappush(heap, (nd, v))
    return best


nodes, res = z['nodes'], z['residents']; g = P.graph(x)
order = np.argsort(-res); sample = [int(nodes[order[0]]), int(nodes[order[len(order) // 2]]), int(nodes[order[-1]])]
for s in sample:
    mine = own_paths(s); theirs = dijkstra(g, directed=False, indices=s, limit=270.)
    reach = np.flatnonzero(np.isfinite(theirs))
    if set(reach.tolist()) != set(mine) or max(abs(mine[int(v)] - theirs[v]) for v in reach) > 1e-6: problems.append(f'paths from {s}')

# demand
c = pd.read_csv(P.CACHE / 'cities.csv', encoding='cp1252', keep_default_na=False, dtype=str); a = pd.read_csv(P.CACHE / 'areas.csv', encoding='utf-8-sig', dtype=str)
s_, e_ = pd.to_numeric(c['Start Date']), pd.to_numeric(c['End Date'], errors='coerce')
c = c[(s_ <= 150) & (e_.isna() | (e_ >= 150))].merge(a, on='Primary Key', how='left')
px, py = forward(c['Latitude (Y)'].astype(float).to_numpy(), c['Longitude (X)'].astype(float).to_numpy(), 40., 17.)
col = np.rint(px / 9. + (w - 1) / 2).astype(int); row = np.rint((h - 1) / 2 - py / 9.).astype(int); ok = (row >= 0) & (row < h) & (col >= 0) & (col < w)
info = R['cases']['primary']['cities']
area = c['Area'].astype(float); known = area.notna().to_numpy()
t = np.clip((np.log(area.fillna(info['filled_at_q25_ha'])) - np.log(50)) / (np.log(400) - np.log(50)), 0, 1); people = area.fillna(info['filled_at_q25_ha']) * (100 + 400 * t)
if abs(res.sum() - info['residents']) > 1e-6 * res.sum() or res.sum() > people[ok].sum() + 1 or len(nodes) != info['city_cells']: problems.append('demand totals')
pop = np.where(land & x['allowed'], x['density'], 0.).ravel() * 81.; world = R['cases']['primary']['world']
if not np.isclose(pop.sum(), world['model_people']) or not np.isclose(res.sum() / pop.sum(), world['urban_share']): problems.append('supply totals')

# fed-share curve with own allocator
n = land.size; lookup = np.full(n, -1); lookup[nodes] = np.arange(len(nodes))
d, _, src = dijkstra(g, directed=False, indices=nodes, min_only=True, return_predecessors=True, limit=270.)
owner = np.where(np.isfinite(d) & (src >= 0), lookup[np.maximum(src, 0)], -1); share = np.where(owner >= 0, np.clip(1 - d / 270., 0, 1), 0.)
between = np.vstack([np.clip(1 - dijkstra(g, directed=False, indices=nodes[i:i + 64], limit=270.)[:, nodes] / 270., 0, 1) for i in range(0, len(nodes), 64)])
between[~np.isfinite(between)] = 0.; np.fill_diagonal(between, 0.); rural = pop * (1 - res.sum() / pop.sum())
for k, m in enumerate(z['m']):
    grain = rural * m; tab = pd.DataFrame(dict(o=owner, g=grain * share)); got0 = np.zeros(len(nodes)); gs = tab[tab.o >= 0].groupby('o').g.sum(); got0[gs.index.to_numpy()] = gs.to_numpy()
    ex = np.clip(got0 - res, 0, None); de = np.clip(res - got0, 0, None); i, j = np.nonzero((between > 0) & (ex[:, None] > 0) & (de[None, :] > 0))
    links = pd.DataFrame(dict(i=i, j=j, s=between[i, j])).sort_values(['s', 'i', 'j'], ascending=[False, True, True]); got = np.zeros(len(nodes))
    for a_, b_, sh in zip(links.i.to_numpy(), links.j.to_numpy(), links.s.to_numpy()):
        if ex[a_] <= 0 or de[b_] <= 0: continue
        mv = min(ex[a_], de[b_] / sh); ex[a_] -= mv; de[b_] -= mv * sh; got[b_] += mv * sh
        if de[b_] < 1e-9 * max(1., mv): de[b_] = 0.
    fed = np.minimum(got0, res) + got
    if not np.allclose(fed, z['fed'][k], rtol=1e-8, atol=1e-6 * res.max()): problems.append(f'fed curve m={m}')
    if not np.isclose(fed.sum() / res.sum(), R['cases']['primary']['all']['fed_share'][str(float(m)) if str(float(m)) in R['cases']['primary']['all']['fed_share'] else str(m)], rtol=1e-8): problems.append(f'F({m})')
F = [float(f.sum() / res.sum()) for f in z['fed']]; m95 = next((float(m) for m, f in zip(z['m'], F) if f >= .95), None)
if m95 != R['cases']['primary']['all']['m95']: problems.append('m95')
out = dict(status='passed' if not problems else 'failed', problems=problems, path_samples=len(sample), m_values=len(z['m']),
           results_sha256=sha(OUT / 'results.json'), reviewer_sha256=sha(__file__))
(OUT / 'review.json').write_text(json.dumps(out, indent=1) + '\n'); print(out); sys.exit(bool(problems))
