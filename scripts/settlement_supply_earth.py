"""Earth pilot for the grain supply scenario on the Roman pool (declared method).

calibration/settlement_supply_earth_20261113/plan.json. Estimates m, the grain
marketed per rural resident needed to feed the catalogued Roman cities.
"""
import argparse, csv, io, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import wide_supply as W, settlement_sizes as Z
from rotclimate.earth import forward
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_supply_earth_20261113/plan.json'
OUT = ROOT / 'output/settlement_supply_earth_20261113'
CACHE = ROOT / 'data/cache/roman_city_source_recovery_20261113'; POOL = ROOT / 'output/settlement_locations_20261110/rome_inputs.npz'
WINDOW = json.loads((ROOT / 'calibration/polity_20261025/plan.json').read_text())['earth_windows']['rome']
M_GRID = (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.5)
SEA, RIVER, ROAD, HARBOUR = 1 / 28, 7.5 / 28, 1.0, 4.0


def graph(x, offroad=2.0):
    land = x['land']; h, w = land.shape; cell = float(x['cell_km'])
    river = land & (np.nan_to_num(x['water_km'], nan=99.) <= 1.5)
    per_km = np.where(land, np.where(x['road'], ROAD, offroad), SEA); per_km = np.where(river & ~x['road'], np.minimum(per_km, RIVER), per_km)
    per_km = np.where(river & x['road'], RIVER, per_km)
    idx = np.arange(h * w).reshape(h, w); rows = []; cols = []; cost = []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        a = idx[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)].ravel()
        b = idx[max(0, dy):h - max(0, -dy) or None, max(0, dx):w - max(0, -dx) or None].ravel()
        c = 0.5 * (per_km.ravel()[a] + per_km.ravel()[b]) * cell * np.hypot(dy, dx)
        c = c + np.where(land.ravel()[a] != land.ravel()[b], HARBOUR, 0.0)
        rows += [a, b]; cols += [b, a]; cost += [c, c]
    return coo_matrix((np.concatenate(cost), (np.concatenate(rows), np.concatenate(cols))), shape=(h * w, h * w)).tocsr()


def cities(x, fill=True):
    rows = list(csv.DictReader(io.StringIO((CACHE / 'cities.csv').read_bytes().decode('cp1252'))))
    areas = {r['Primary Key']: float(r['Area']) for r in csv.DictReader(io.StringIO((CACHE / 'areas.csv').read_bytes().decode('utf-8-sig')))}
    keep = [r for r in rows if float(r['Start Date']) <= 150 and (r['End Date'].strip().upper() == 'NULL' or float(r['End Date']) >= 150)]
    land = x['land']; ny, nx = land.shape; cell = float(x['cell_km'])
    lat = np.array([float(r['Latitude (Y)']) for r in keep]); lon = np.array([float(r['Longitude (X)']) for r in keep])
    px, py = forward(lat, lon, WINDOW['lat0'], WINDOW['lon0'])
    col = np.round(px / cell + (nx - 1) / 2).astype(int); row = np.round((ny - 1) / 2 - py / cell).astype(int)
    inside = (row >= 0) & (row < ny) & (col >= 0) & (col < nx)
    _, (iy, ix) = ndi.distance_transform_edt(~land, return_indices=True)
    rc, cc = np.clip(row, 0, ny - 1), np.clip(col, 0, nx - 1); sr, sc = iy[rc, cc], ix[rc, cc]
    on = inside & x['allowed'][sr, sc]
    known = np.array([areas.get(r['Primary Key'], np.nan) for r in keep])
    q25 = float(np.quantile(known[on & np.isfinite(known)], 0.25))
    area = np.where(np.isfinite(known), known, q25 if fill else 0.0)
    people = Z.residents(area, 'central'); use = on & (people > 0)
    node = (sr * nx + sc)[use]; uniq, inverse = np.unique(node, return_inverse=True)
    res = np.bincount(inverse, weights=people[use]); west = np.bincount(inverse, weights=lon[use] * people[use]) / res
    return uniq, res, west, dict(catalogue_AD150=len(keep), on_roman_land=int(on.sum()), with_area=int((on & np.isfinite(known)).sum()),
        filled_at_q25_ha=q25 if fill else None, city_cells=len(uniq), residents=float(res.sum()), largest=float(res.max()))


def solve(x, g, nodes, res, limit):
    n = x['land'].size; lookup = np.full(n, -1, int); lookup[nodes] = np.arange(len(nodes))
    d, _, src = dijkstra(g, directed=False, indices=nodes, min_only=True, return_predecessors=True, limit=limit)
    owner = np.where(np.isfinite(d) & (src >= 0), lookup[np.maximum(src, 0)], -1)
    share = np.where(owner >= 0, W.delivered_share(d, limit), 0.0)
    between = np.zeros((len(nodes), len(nodes)))
    for i in range(0, len(nodes), 64):
        between[i:i + 64] = W.delivered_share(dijkstra(g, directed=False, indices=nodes[i:i + 64], limit=limit)[:, nodes], limit)
    np.fill_diagonal(between, 0.0)
    people = np.where(x['land'] & x['allowed'], x['density'], 0.0).ravel() * float(x['cell_km']) ** 2
    rural = people * (1 - res.sum() / people.sum())
    curve = []
    for m in M_GRID:
        delivered, _ = W.hinterland_delivery(owner[None], share[None], rural * m, len(nodes))
        _, received = W.ship(np.maximum(delivered - res, 0), np.maximum(res - delivered, 0), between)
        fed = np.minimum(delivered, res) + received
        curve.append(fed)
    return np.array(curve), dict(model_people=float(people.sum()), rural_people=float(rural.sum()), urban_share=float(res.sum() / people.sum()),
        cells_within_reach=float(((owner >= 0) & (people > 0)).sum() / (people > 0).sum()), mean_partners=float((between > 0).sum(1).mean()))


def describe(curve, res, mask=None):
    mask = np.ones(len(res), bool) if mask is None else mask
    F = [float(c[mask].sum() / res[mask].sum()) for c in curve]
    first = lambda level: next((m for m, f in zip(M_GRID, F) if f >= level), None)
    return dict(fed_share=dict(zip(map(str, M_GRID), F)), m50=first(0.5), m95=first(0.95),
                short_cities={str(m): int(((c < res * (1 - 1e-6)) & mask).sum()) for m, c in zip(M_GRID, curve)})


def run(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    out.mkdir(parents=True, exist_ok=True); x = dict(np.load(POOL)); cases = {}; saved = {}
    for name, offroad, limit, fill in (('primary', 2.0, 270.0, True), ('offroad_1.5', 1.5, 270.0, True), ('offroad_3', 3.0, 270.0, True),
                                       ('limit_135', 2.0, 135.0, True), ('limit_540', 2.0, 540.0, True), ('no_area_cities_left_out', 2.0, 270.0, False)):
        nodes, res, lon, info = cities(x, fill); curve, world = solve(x, graph(x, offroad), nodes, res, limit)
        west = lon <= np.median(lon); top = int(np.argmax(res))
        cases[name] = dict(offroad_factor=offroad, limit_road_km=limit, cities=info, world=world, all=describe(curve, res),
            west=describe(curve, res, west), east=describe(curve, res, ~west),
            largest_city_fed_share={str(m): float(c[top] / res[top]) for m, c in zip(M_GRID, curve)})
        if name == 'primary':
            saved = dict(nodes=nodes, residents=res, fed=curve, m=np.array(M_GRID), west=west)
    fantasy = json.loads((ROOT / 'output/settlement_wide_supply_20261113/results.json').read_text())['climates']['corrected']['scenarios']
    np.savez_compressed(out / 'pilot.npz', **saved)
    result = dict(status='earth_supply_pilot_roman_pool_proxy_production', plan_sha256=sha(PLAN), producer_sha256=sha(__file__),
        model_sha256=sha(ROOT / 'polity/wide_supply.py'), inputs=dict(pool=sha(POOL), cities=sha(CACHE / 'cities.csv'), areas=sha(CACHE / 'areas.csv')),
        cases=cases, fantasy_marketed_per_rural_person={k: fantasy[k]['marketed_per_rural_person'] for k in ('central_x33', 'central_x10', 'low_x33', 'low_x10')},
        fantasy_fed_share={k: fantasy[k]['fed_share_of_residents'] for k in ('central_x33', 'central_x10')},
        pilot_sha256=sha(out / 'pilot.npz'), raw_rows_redistributed=False)
    write(out / 'results.json', result); return result


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('--out', type=Path, default=OUT); r = run(a.parse_args().out)
    for k, c in r['cases'].items():
        print(k, c['cities']['city_cells'], round(c['cities']['residents'] / 1e6, 2), 'urban', round(c['world']['urban_share'], 3), 'reach', round(c['world']['cells_within_reach'], 3),
              'm50', c['all']['m50'], 'm95', c['all']['m95'], 'west', c['west']['m95'], 'east', c['east']['m95'])
    p = r['cases']['primary']; print({m: round(f, 3) for m, f in p['all']['fed_share'].items()}); print('Rome', {m: round(f, 2) for m, f in p['largest_city_fed_share'].items()})
    print('fantasy m', {k: round(v, 3) for k, v in r['fantasy_marketed_per_rural_person'].items()})
