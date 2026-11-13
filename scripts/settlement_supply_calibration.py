"""Earth calibration of the grain supply model on the Roman pool (real harvests, seasonal network).

calibration/settlement_supply_calibration_20261113/plan.json. Same production,
network and allocation code as the fantasy scenario.
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import earth as E, network as N, trade as T, transport as X, wide_supply as W
from harvest.field_support import field_support
from harvest.work_maps import cereal_work
import polity_earth_check as P
import settlement_supply_earth as PILOT
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_supply_calibration_20261113/plan.json'
OUT = ROOT / 'output/settlement_supply_calibration_20261113'
KCAL = 2500.0 * 365.0; HOURS = np.array([336.0, 208.0]); REAP = np.array([48.0, 32.0]); FARMED, SOWN = 0.6, 0.6


def earth_fields(lat, lon):
    z = np.load(ROOT / 'output/land_people/earth/earth.npz'); zl, zo = z['lat'], z['lon']; step = float(zl[0] - zl[1])
    r = (zl[0] + step / 2 - lat) / step - 0.5; c = (lon - (zo[0] - step / 2)) / step - 0.5
    inside = (r >= -0.5) & (r <= len(zl) - 0.5) & (c >= -0.5) & (c <= len(zo) - 0.5)
    rc = [np.clip(r, 0, len(zl) - 1), np.clip(c, 0, len(zo) - 1)]
    get = lambda k: np.where(inside, ndi.map_coordinates(np.nan_to_num(z[k]).astype(float), rc, order=0), 0.0)
    return get('kcal_wheat'), get('kcal_barley'), get('arable'), inside


def prepare(x):
    plan = json.loads(PLAN.read_text()); P.apply_sea()
    w = PILOT.WINDOW; g = E.window(w['lat0'], w['lon0'], w['width_km'], w['height_km'], w['cell_km'])
    if not np.array_equal(g['land'], x['land']):
        raise ValueError('Rebuilt window land differs from the committed Roman inputs')
    g['density'] = x['density']                      # committed people field (plan: rebuilt grid is not byte-identical)
    world = P.world_of(g, x['road']); st = N.statics(world); cl = N.climate(world, st)
    nodes, res, lon, info = PILOT.cities(x); width = x['land'].shape[1]
    places = [(int(n // width), int(n % width)) for n in nodes]
    ports = X.ports_of(places, st['water']); near = ndi.binary_dilation(st['basin'] > 0, iterations=1)
    river_places = [p for p in places if near[p]]
    n = x['land'].size; lookup = np.full(n, -1, int); lookup[nodes] = np.arange(len(nodes)); limit = float(max(plan['parameters']['haul_limit_L_road_km']))
    dist = []; owner = []; between = []
    for month in T.TRADE_MONTHS:
        net = T.cost_network(world, st, cl, month, ports, river_places)
        d, _, src = dijkstra(net.base.T.tocsr(), directed=True, indices=nodes, min_only=True, return_predecessors=True, limit=limit)
        d, src = d[:n], src[:n]; ok = np.isfinite(d) & (src >= 0); o = np.full(n, -1, int); o[ok] = lookup[src[ok]]
        dist.append(np.where(o >= 0, d, np.inf)); owner.append(o)
        c = np.vstack([cc[:, nodes] for _, cc in T.costs_from(net, nodes, limit=limit, batch=48)]); between.append(c)
        print('month', month, 'network done', flush=True)
    wheat, barley, arable, inside = earth_fields(x['lat'], x['lon'])
    work = cereal_work(np.stack([wheat, barley]), HOURS, REAP, food_target=1e6)
    kcal_ha = np.where(work.crop > 0, 1e6 / np.where(work.crop > 0, work.land, 1.0), 0.0)
    supply_land = x['land'] & x['allowed']
    potential = np.where(supply_land, kcal_ha * 100.0 * float(x['cell_km']) ** 2 * arable * FARMED * SOWN, 0.0).ravel()
    people = np.where(supply_land, x['density'], 0.0).ravel() * float(x['cell_km']) ** 2
    rural = people * (1 - res.sum() / people.sum())
    grown = field_support(potential, np.nan_to_num(work.hours).ravel(), np.nan_to_num(work.reaping).ravel(), rural_need_kcal=rural * KCAL)
    surplus = np.maximum(grown.produced_kcal - rural * KCAL, 0.0) / KCAL            # person-years
    meta = dict(cities=info, ports=len(ports), river_landings=len(river_places), model_people=float(people.sum()), rural_people=float(rural.sum()),
        urban_share=float(res.sum() / people.sum()), potential_person_years=float(potential.sum() / KCAL),
        grown_person_years=float(grown.produced_kcal.sum() / KCAL), surplus_person_years=float(surplus.sum()),
        surplus_per_rural_person=float(surplus.sum() / rural.sum()), cells_below_rural_need=int(((grown.produced_kcal < rural * KCAL - 1) & (rural > 0)).sum()),
        rural_people_in_deficit_cells=float(rural[(grown.produced_kcal < rural * KCAL - 1)].sum()),
        harvest_grid_covers_supply_land=float(inside[supply_land].mean()), wheat_cells=int((work.crop == 1)[supply_land].sum()), barley_cells=int((work.crop == 2)[supply_land].sum()))
    return dict(nodes=nodes, residents=res, lon=lon, dist=np.array(dist, np.float32), owner=np.array(owner, np.int32),
                between=np.array(between, np.float32), surplus=surplus, potential=potential / KCAL, rural=rural), meta


def fed_surface(a, shares, limits):
    res = a['residents']; out = np.zeros((len(limits), len(shares), len(res)))
    for i, L in enumerate(limits):
        share = np.where(a['owner'] >= 0, W.delivered_share(a['dist'].astype(float), L), 0.0)
        between = W.delivered_share(a['between'].astype(float), L).mean(0); np.fill_diagonal(between, 0.0)
        for j, e in enumerate(shares):
            delivered, _ = W.hinterland_delivery(a['owner'], share, a['surplus'] * e, len(res))
            _, received = W.ship(np.maximum(delivered - res, 0), np.maximum(res - delivered, 0), between)
            out[i, j] = np.minimum(delivered, res) + received
    return out


def e95(shares, F, level=0.95):
    for k, f in enumerate(F):
        if f >= level:
            if k == 0: return float(shares[0])
            return float(shares[k - 1] + (level - F[k - 1]) * (shares[k] - shares[k - 1]) / (f - F[k - 1]))
    return None


def decide(shares, limits, fed, res, west):
    table = {}
    for i, L in enumerate(limits):
        row = {}
        for name, mask in (('all', np.ones(len(res), bool)), ('west', west), ('east', ~west)):
            F = [float(fed[i, j][mask].sum() / res[mask].sum()) for j in range(len(shares))]
            row[name] = dict(fed_share=F, e95=e95(shares, F))
        w, e = row['west']['e95'], row['east']['e95']
        row['west_east_log_ratio'] = None if not (w and e) else float(abs(np.log(w / e)))
        table[str(L)] = row
    valid = {L: r['west_east_log_ratio'] for L, r in table.items() if r['west_east_log_ratio'] is not None}
    best = min(valid, key=lambda L: (valid[L], float(L))) if valid else None
    at270 = valid.get('270')
    keep = at270 is not None and (at270 <= np.log(1.25) or at270 <= 1.1 * valid[best])
    L_use = '270' if keep or best is None else best
    e_all = table[L_use]['all']['e95']; third = 1.0 / 3.0
    verdict = None if e_all is None else ('low' if third < e_all else ('more than needed' if third > 2 * e_all else 'Earth-supported'))
    def feeds(src, dst, mask):
        e = table[L_use][src]['e95']
        if e is None: return None
        F = table[L_use][dst]['fed_share']; return float(np.interp(e, shares, F))
    transfer = dict(west_setting_feeds_east=feeds('west', 'east', ~west), east_setting_feeds_west=feeds('east', 'west', west))
    ok = all(v is not None and v >= 0.9 for v in transfer.values())
    return table, dict(best_L_by_west_east_agreement=best, log_ratio_at_270=at270, cited_270_kept=bool(keep), L_used=L_use,
        e95_all_at_L_used=e_all, fantasy_one_third=verdict, transfer=transfer, transferable=bool(ok))


def run(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    plan = json.loads(PLAN.read_text()); out.mkdir(parents=True, exist_ok=True); x = dict(np.load(PILOT.POOL))
    a, meta = prepare(x); shares = plan['parameters']['marketed_share_e']; limits = plan['parameters']['haul_limit_L_road_km']
    fed = fed_surface(a, shares, limits); west = a['lon'] <= np.median(a['lon'])
    table, decision = decide(shares, limits, fed, a['residents'], west)
    top = int(np.argmax(a['residents']))
    np.savez_compressed(out / 'calibration.npz', fed=fed, west=west, shares=np.array(shares), limits=np.array(limits), **a)
    result = dict(status='earth_supply_calibration_roman_pool_real_harvests_seasonal_network', plan_sha256=sha(PLAN), producer_sha256=sha(__file__),
        model_sha256=sha(ROOT / 'polity/wide_supply.py'), world=meta, surface=table, decision=decision,
        largest_city_fed_share_at_270={str(e): float(fed[limits.index(270), j][top] / a['residents'][top]) for j, e in enumerate(shares)},
        marketed_per_rural_person_at_one_third=meta['surplus_per_rural_person'] / 3.0,
        inputs=dict(pool=sha(PILOT.POOL), cities=sha(PILOT.CACHE / 'cities.csv'), areas=sha(PILOT.CACHE / 'areas.csv'),
                    arable_grid=sha(ROOT / 'data/cache/arable_slope_earth/arable_5m.npz'), worldclim_elev=sha(ROOT / 'data/cache/worldclim/wc2.1_5m_elev.zip')),
        arrays_sha256=sha(out / 'calibration.npz'), raw_rows_redistributed=False)
    write(out / 'results.json', result); return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); r = run(ap.parse_args().out)
    print(json.dumps(r['world'], indent=1)); print(json.dumps(r['decision'], indent=1))
    for L, row in r['surface'].items():
        print(L, 'all', [round(f, 2) for f in row['all']['fed_share']], 'e95 all/west/east', row['all']['e95'], row['west']['e95'], row['east']['e95'])
    print('Rome', {k: round(v, 2) for k, v in r['largest_city_fed_share_at_270'].items()})
