"""T3 of calibration/floodplain_rule_20261114: whole-empire supply calibration on the floodplain harvest grid with the
heartland people pattern (capacity x exp(-D/800) on the NEW capacity, rescaled to the committed window total)."""
import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import supply_heartland_people as SH
from settlement_locations_earth import sha, write

ES = SH.ES; S = SH.S; OUT = ROOT / 'output/floodplain_rule_20261114'; GRID = ROOT / 'output/land_people/earth_floodplain/earth.npz'
VARIANTS = [('floodplain_P2', False, False), ('floodplain_P2_without_egypt', True, False), ('A2_floodplain_P2_production', False, True), ('A2_floodplain_P2_production_without_egypt', True, True)]
FIELDS = ROOT / 'output/floodplain_rule_20261114/fields.npz'; F_B = 0.95; NEED = 1.1e6; STATE = dict(on=False)


def basin_on_pool(lat, lon):
    z = np.load(GRID); f = np.load(FIELDS); zl, zo = z['lat'], z['lon']; step = float(zl[0] - zl[1])
    r = (zl[0] + step / 2 - lat) / step - 0.5; c = (lon - (zo[0] - step / 2)) / step - 0.5
    inside = (r >= -0.5) & (r <= len(zl) - 0.5) & (c >= -0.5) & (c <= len(zo) - 0.5); rc = [np.clip(r, 0, len(zl) - 1), np.clip(c, 0, len(zo) - 1)]
    from scipy import ndimage as ndi
    get = lambda a: np.where(inside, ndi.map_coordinates(np.nan_to_num(a).astype(float), rc, order=0), 0.0)
    arable = np.nan_to_num(z['arable']); W = np.where(arable > 0, f['basin_unit_capacity'] * NEED / (100.0 * np.maximum(arable, 1e-9)), 0.0)
    return get(f['s']), get(W)


def main(out):
    out.mkdir(parents=True, exist_ok=True); costs_from = S.T.costs_from; ES.memoise(); costs = {}
    def cf(net, nodes, limit, batch):
        key = (id(net), np.asarray(nodes).tobytes(), limit, batch)
        if key not in costs:
            for k in [k for k in costs if k[1:] != key[1:]]: del costs[k]
            costs[key] = list(costs_from(net, nodes, limit=limit, batch=batch))
        return iter(costs[key])
    S.T.costs_from = cf; S.HARVEST = GRID; fields = S.earth_fields
    def with_basin(lat, lon):
        wheat, barley, arable, inside = fields(lat, lon)
        if not STATE['on']: return wheat, barley, arable, inside
        sb, W = basin_on_pool(lat, lon); boost = W * F_B / (S.FARMED * S.SOWN)
        return (1 - sb) * wheat + sb * boost, (1 - sb) * barley + sb * boost, arable, inside
    S.earth_fields = with_basin
    plan = json.loads(S.PLAN.read_text()); shares = plan['parameters']['marketed_share_e']; limits = plan['parameters']['haul_limit_L_road_km']; rows = {}
    for name, no_egypt, on in VARIANTS:
        x = dict(np.load(S.PILOT.POOL)); S.NO_EGYPT = no_egypt; STATE['on'] = on; land = x['land']; total = float(x['density'][land].sum())
        pattern = np.where(land, SH.capacity(x['lat'], x['lon']) * x['history'], 0.0); x['density'] = pattern * total / pattern[land].sum()
        ep = SH.proper(x['lat'], x['lon']) & land; cell = float(x['cell_km']) ** 2
        a, meta = S.prepare(x); fed = S.fed_surface(a, shares, limits); west = a['lon'] <= np.median(a['lon'])
        table, decision = S.decide(shares, limits, fed, a['residents'], west); pc = ep.ravel()[a['nodes']]; i270 = limits.index(270)
        rows[name] = dict(without_egypt=no_egypt, basin_rule_in_production=on, decision=decision, surface=table, egypt_proper_people=float((x['density'][ep] * cell).sum()),
            egypt_proper_city_fed_share_at_270=None if no_egypt else {str(e): float(fed[i270, j][pc].sum() / a['residents'][pc].sum()) for j, e in enumerate(shares)},
            surplus_per_rural_person=meta['surplus_per_rural_person'])
        print(name, json.dumps(decision), flush=True)
    S.NO_EGYPT = False; STATE['on'] = False
    passing = [n for n, r in rows.items() if r['decision']['cited_270_kept'] and r['decision']['transferable']]
    write(out / 'supply.json', dict(status='floodplain_rule_T3_supply', plan_sha256=sha(ROOT / 'calibration/floodplain_rule_20261114/plan.json'), producer_sha256=sha(Path(__file__)),
        harvest_grid_sha256=sha(GRID), variants=rows, passing_variants=passing))
    return passing


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); print(main(ap.parse_args().out))
