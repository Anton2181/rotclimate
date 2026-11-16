"""Borders between states (calibration/internal_borders_20261116/plan.json).

    .venv/bin/python -I scripts/internal_borders.py prep D1|D2|D3|B1|B2|B3   # held land, per-polity days, labels; nothing scored
    .venv/bin/python -I scripts/internal_borders.py dev
    .venv/bin/python -I scripts/internal_borders.py blind                     # run once
"""
import json, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
OUT = ROOT / 'output/internal_borders_20261116'; PLAN = ROOT / 'calibration/internal_borders_20261116/plan.json'
POOLS = {'D1': (1200, 'rome'), 'D2': (1500, 'rome'), 'D3': (1200, 'han'), 'B1': (1400, 'rome'), 'B2': (1600, 'rome'), 'B3': (1140, 'han')}
log = lambda *a: print(*a, flush=True)  # noqa: E731


def polity_labels(g, year):
    from polity import earth as E
    import earth_control_blind as B1
    d = json.loads(B1.CLIO.read_text()); names = []; lab = np.full(g['land'].shape, -1, np.int32); hits = np.zeros(lab.shape, np.int16)
    by = {}
    for f in d['features']:
        p = f['properties']
        if p['FromYear'] <= year <= p['ToYear'] and f['geometry']:
            geo = f['geometry']; by.setdefault(p['Name'], []).extend([geo['coordinates']] if geo['type'] == 'Polygon' else geo['coordinates'])
    for name, rings in by.items():
        m = E.inside_polygons(g, rings)
        if not m.any():
            continue
        hits += m; free = m & (lab < 0); lab[free] = len(names); names.append(name)
    return lab, names, float(((hits > 1) & g['land'].astype(bool)).sum() / max((hits > 0).sum(), 1))


def prep(pool):
    import basin_cantons as BC
    import polity_earth_check as P
    import earth_control_round2 as R
    import earth_control_test as T
    import geography_control_a2 as A2
    from scipy.sparse.csgraph import dijkstra
    from polity import control as C
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    BC.BLIND.update(POOLS)
    year, window = POOLS[pool]
    g, road, nodes, inside, band, _ = BC.pool_inputs(pool)
    lab, names, overlap = polity_labels(g, year)
    S_ = R.setup(g, nodes, road); land, shp = S_['land'], S_['shape']; W = shp[1]; world = S_['world']
    ff = dict(np.load(T.OUT / f'{window}_food.npz'))
    staffed_mask, info = R.chain(S_, ff, ff['F_joint365'], scaled=True); staffed = nodes[staffed_mask]
    eta = C.terrain_coefficient(world['biome'], world['swamp'], None)
    v1 = C.travel_graph(world['elev'], land, road, eta, world['cell_km'], S_['st']['paths'])
    band = land & (dijkstra(v1, directed=True, indices=nodes, min_only=True).reshape(shp) <= 15)
    places = [(int(v) // W, int(v) % W) for v in nodes]
    nets = A2.nets_with(g, world, places, 1.0)
    roads = np.flatnonzero(road.ravel() & land.ravel())
    d1 = P.year_days(nets, staffed).ravel(); near = roads[d1[roads] <= 2.0] if len(roads) else roads
    held = (P.year_days(nets, np.unique(np.r_[staffed, near])).ravel() <= 2.0).reshape(shp) & land
    src_pol = lab.ravel()[staffed]; pols = sorted(set(int(p) for p in src_pol if p >= 0))
    days = np.full((len(pols),) + shp, np.inf, np.float32)
    for k, p in enumerate(pols):
        days[k] = P.year_days(nets, staffed[src_pol == p]).reshape(shp)
    # straight-line null: nearest staffed town's polity
    seed = np.full(shp, -1); keep = src_pol >= 0
    seed.ravel()[staffed[keep]] = src_pol[keep]
    _, (iy, ix) = ndi.distance_transform_edt(seed < 0, return_indices=True); e0 = seed[iy, ix]
    basins = {f'basin{lv}': BC.basins(g, lv) for lv in (7, 8)}
    np.savez_compressed(OUT / f'{pool}.npz', land=land, held=held, band=band, lab=lab, pols=np.array(pols), days=days, e0=e0,
                        river=np.asarray(g['river'], bool), **basins)
    (OUT / f'{pool}_info.json').write_text(json.dumps(dict(year=year, window=window, sources=int(len(nodes)), staffed=int(len(staffed)),
        polities_alive=len(names), polities_with_sources=len(pols), overlap_share=overlap, names=[names[p] for p in pols]), indent=1))
    log(pool, 'prepared', f'{time.time() - t0:.0f}s', len(pols), 'polities with staffed towns; not scored')


def canton(owner, held, lab):
    out = owner.copy(); ids = lab[held]; o = owner[held]
    ok = (ids > 0) & (o >= 0)
    keys = ids[ok].astype(np.int64) * 4096 + o[ok]
    u, c = np.unique(keys, return_counts=True)
    best = {}
    for k, n in zip(u, c):
        b, ow = divmod(int(k), 4096)
        if n > best.get(b, (0, -1))[0]:
            best[b] = (n, ow)
    new = o.copy(); bi = ids
    new[ok] = [best[int(b)][1] for b in bi[ok]]
    out[held] = new
    return out


def borders(owner, mask):
    b = np.zeros(owner.shape, bool)
    for sa, sb in (((slice(None), slice(1, None)), (slice(None), slice(None, -1))), ((slice(1, None), slice(None)), (slice(None, -1), slice(None)))):
        diff = (owner[sa] != owner[sb]) & mask[sa] & mask[sb] & (owner[sa] >= 0) & (owner[sb] >= 0)
        b[sa] |= diff; b[sb] |= diff
    return b


def score(pool, level=None):
    import basin_cantons as BC
    z = dict(np.load(OUT / f'{pool}.npz')); held, lab, pols = z['held'], z['lab'], list(z['pols'])
    o0 = np.where(np.isfinite(z['days'].min(0)), np.array(pols)[z['days'].argmin(0)], -1); o0 = np.where(held, o0, -1)
    rules = {'O0_map': o0, 'E0_null': np.where(held, z['e0'], -1)}
    for lv in ((7, 8) if level is None else (level,)):
        rules[f'C{lv}'] = canton(o0, held, z[f'basin{lv}'])
    real = np.where(np.isin(lab, pols), lab, -1); scored = held & (real >= 0)
    rb = borders(real, held)
    div = BC.divides(z['basin8'], z['land']); river = ndi.binary_dilation(z['river'], iterations=1) & z['land']
    ring = held & ~rb
    enr = lambda b, f: float(f[b].mean() / max(f[ring].mean(), 1e-9)) if b.any() else None
    res = dict(scored_cells=int(scored.sum()), real_border_cells=int(rb.sum()),
               real_enrichment=dict(divide=enr(rb, div), river=enr(rb, river)))
    near_rb = ndi.distance_transform_edt(~rb) <= 2
    for name, o in rules.items():
        mb = borders(o, held)
        res[name] = dict(OA=float((o[scored] == real[scored]).mean()),
                         border_recall=float((ndi.distance_transform_edt(~mb)[rb] <= 2).mean()) if rb.any() else None,
                         border_precision=float(near_rb[mb].mean()) if mb.any() else None,
                         enrichment=dict(divide=enr(mb, div), river=enr(mb, river)))
    return res


def show(res):
    for p, r in res.items():
        line = ' | '.join(f"{k} OA {v['OA']:.3f} rec {v['border_recall'] or 0:.2f}" for k, v in r.items() if isinstance(v, dict) and 'OA' in v)
        log(f"{p}: cells {r['scored_cells']:,}, real borders {r['real_border_cells']:,} (divide x{r['real_enrichment']['divide'] or 0:.2f}, "
            f"river x{r['real_enrichment']['river'] or 0:.2f}) | {line}")


def dev():
    res = {p: score(p) for p in ('D1', 'D2', 'D3')}
    mean = {lv: float(np.mean([res[p][f'C{lv}']['OA'] for p in res])) for lv in (7, 8)}
    out = dict(plan=str(PLAN.relative_to(ROOT)), pools=res, mean_OA=dict(O0=float(np.mean([res[p]['O0_map']['OA'] for p in res])), **{f'C{k}': v for k, v in mean.items()}),
               chosen_level=max(mean, key=mean.get))
    (OUT / 'dev.json').write_text(json.dumps(out, indent=1)); show(res); log('mean OA', out['mean_OA'], 'chosen', out['chosen_level'])


def blind():
    lv = json.loads((OUT / 'dev.json').read_text())['chosen_level']
    res = {p: score(p, lv) for p in ('B1', 'B2', 'B3')}
    c = f'C{lv}'
    g1 = sum(res[p][c]['OA'] >= res[p]['O0_map']['OA'] + 0.01 for p in res) >= 2
    g2 = all(res[p][c]['OA'] >= res[p]['O0_map']['OA'] - 0.01 for p in res)
    out = dict(plan=str(PLAN.relative_to(ROOT)), level=lv, pools=res, gates=dict(G1=bool(g1), G2=bool(g2)), adopt=bool(g1 and g2))
    (OUT / 'blind.json').write_text(json.dumps(out, indent=1)); show(res); log('gates', out['gates'], 'adopt', out['adopt'])


if __name__ == '__main__':
    {'prep': lambda: prep(sys.argv[2]), 'dev': dev, 'blind': blind}[sys.argv[1]]()
