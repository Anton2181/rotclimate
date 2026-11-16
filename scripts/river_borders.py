"""Rivers in ownership between European states (calibration/river_borders_20261116/plan.json).

    .venv/bin/python -I scripts/river_borders.py prep 1200|1400|1500|1600|1000|1100|1800   # nothing scored
    .venv/bin/python -I scripts/river_borders.py dev
    .venv/bin/python -I scripts/river_borders.py blind                                      # run once
"""
import json, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
OUT = ROOT / 'output/river_borders_20261116'; PLAN = ROOT / 'calibration/river_borders_20261116/plan.json'
XS = (0.0, 0.5, 1.0, 2.0, 4.0); DEV = (1200, 1400, 1500, 1600); BLIND = (1000, 1100, 1800)
log = lambda *a: print(*a, flush=True)  # noqa: E731


def prep(year):
    import basin_cantons as BC
    import internal_borders as IB
    import polity_earth_check as P
    import earth_control_round2 as R
    import earth_control_test as T
    import geography_control_a2 as A2
    from scipy.sparse.csgraph import dijkstra
    from polity import control as C
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time(); pool = f'R{year}'
    BC.BLIND[pool] = (year, 'rome')
    g, road, nodes, inside, _, _ = BC.pool_inputs(pool)
    lab, names, overlap = IB.polity_labels(g, year)
    S_ = R.setup(g, nodes, road); land, shp = S_['land'], S_['shape']; W = shp[1]; world = S_['world']
    ff = dict(np.load(T.OUT / 'rome_food.npz'))
    staffed_mask, _ = R.chain(S_, ff, ff['F_joint365'], scaled=True); staffed = nodes[staffed_mask]
    eta = C.terrain_coefficient(world['biome'], world['swamp'], None)
    v1 = C.travel_graph(world['elev'], land, road, eta, world['cell_km'], S_['st']['paths'])
    band = land & (dijkstra(v1, directed=True, indices=nodes, min_only=True).reshape(shp) <= 15)
    places = [(int(v) // W, int(v) % W) for v in nodes]
    nets = A2.nets_with(g, world, places, 1.0)
    roads = np.flatnonzero(road.ravel() & land.ravel())
    d1 = P.year_days(nets, staffed).ravel(); near = roads[d1[roads] <= 2.0] if len(roads) else roads
    held = (P.year_days(nets, np.unique(np.r_[staffed, near])).ravel() <= 2.0).reshape(shp) & land
    src_pol = lab.ravel()[staffed]; pols = sorted(set(int(p) for p in src_pol if p >= 0))
    o0_days = np.stack([P.year_days(nets, staffed[src_pol == p]).reshape(shp) for p in pols]).astype(np.float32)
    river = np.asarray(world['river'], bool) & land
    rx = {}
    for X in XS:
        G = C.travel_graph(world['elev'], land, road, eta, world['cell_km'], S_['st']['paths'], cross=np.where(river, X, 0.0))
        rx[f'R{X:g}'] = np.stack([dijkstra(G, directed=True, indices=np.unique(staffed[src_pol == p]), min_only=True).reshape(shp) for p in pols]).astype(np.float32)
    np.savez_compressed(OUT / f'{pool}.npz', land=land, held=held, band=band, lab=lab, pols=np.array(pols), river=river,
                        O0=o0_days, **rx)
    (OUT / f'{pool}_info.json').write_text(json.dumps(dict(year=year, sources=int(len(nodes)), staffed=int(len(staffed)),
        polities_with_sources=len(pols), overlap_share=overlap, names=[names[p] for p in pols]), indent=1))
    log(pool, 'prepared', f'{time.time() - t0:.0f}s', len(pols), 'polities; not scored')


def score(year, rules=None):
    import internal_borders as IB
    z = dict(np.load(OUT / f'R{year}.npz')); held, lab, pols = z['held'], z['lab'], np.array(z['pols'])
    real = np.where(np.isin(lab, pols), lab, -1); scored = held & (real >= 0); rb = IB.borders(real, held)
    river = ndi.binary_dilation(z['river'], iterations=1) & z['land']; ring = held & ~rb
    enr = lambda b: float(river[b].mean() / max(river[ring].mean(), 1e-9)) if b.any() else None
    near_rb = ndi.distance_transform_edt(~rb) <= 2
    res = dict(scored_cells=int(scored.sum()), real_border_cells=int(rb.sum()), real_river=enr(rb))
    for name in (rules or ['O0'] + [f'R{X:g}' for X in XS]):
        d = z[name]; o = np.where(held & np.isfinite(d.min(0)), pols[d.argmin(0)], -1); mb = IB.borders(o, held)
        res[name] = dict(OA=float((o[scored] == real[scored]).mean()),
                         border_recall=float((ndi.distance_transform_edt(~mb)[rb] <= 2).mean()) if rb.any() else None,
                         border_precision=float(near_rb[mb].mean()) if mb.any() else None, river=enr(mb))
    return res


def show(res):
    for y, r in res.items():
        log(f"{y}: cells {r['scored_cells']:,} real river x{r['real_river']:.2f} | " +
            ' | '.join(f"{k} {v['OA']:.3f} riv x{v['river']:.2f}" for k, v in r.items() if isinstance(v, dict)))


def dev():
    res = {y: score(y) for y in DEV}
    mean = {X: float(np.mean([res[y][f'R{X:g}']['OA'] for y in DEV])) for X in XS}
    choice = max([X for X in XS if X > 0], key=mean.get)
    out = dict(plan=str(PLAN.relative_to(ROOT)), pools=res, mean_OA=dict(O0=float(np.mean([res[y]['O0']['OA'] for y in DEV])), **{f'R{k:g}': v for k, v in mean.items()}),
               chosen_X=choice)
    (OUT / 'dev.json').write_text(json.dumps(out, indent=1)); show(res); log('mean OA', out['mean_OA'], 'chosen X', choice)


def blind():
    X = json.loads((OUT / 'dev.json').read_text())['chosen_X']; k = f'R{X:g}'
    res = {y: score(y, ['O0', 'R0', k]) for y in BLIND}
    g1 = sum(res[y][k]['OA'] >= res[y]['O0']['OA'] + 0.01 for y in BLIND) >= 2
    g2 = all(res[y][k]['OA'] >= res[y]['O0']['OA'] - 0.01 for y in BLIND)
    out = dict(plan=str(PLAN.relative_to(ROOT)), X=X, pools=res, gates=dict(G1=bool(g1), G2=bool(g2)), adopt=bool(g1 and g2))
    (OUT / 'blind.json').write_text(json.dumps(out, indent=1)); show(res); log('gates', out['gates'], 'adopt', out['adopt'])


if __name__ == '__main__':
    {'prep': lambda: prep(int(sys.argv[2])), 'dev': dev, 'blind': blind}[sys.argv[1]]()
