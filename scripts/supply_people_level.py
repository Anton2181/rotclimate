"""People level for the supply calibration (calibration/supply_people_level_20261114/plan.json): heartland pattern on the
floodplain grid, anchored to Frier's 61.4 M on Roman allowed land (primary) or absolute (sensitivity), with the
floodplain rule in production (amendment A2 machinery of scripts/floodplain_supply.py)."""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import floodplain_supply as FS
from settlement_locations_earth import sha, write

SH = FS.SH; ES = FS.ES; S = FS.S
PLAN = ROOT / 'calibration/supply_people_level_20261114/plan.json'; OUT = ROOT / 'output/supply_people_level_20261114'
FRIER = 61.4e6; VARIANTS = [('frier', False), ('frier_without_egypt', True), ('absolute', False), ('absolute_without_egypt', True)]


def main(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    out.mkdir(parents=True, exist_ok=True); costs_from = S.T.costs_from; ES.memoise(); costs = {}
    def cf(net, nodes, limit, batch):
        key = (id(net), np.asarray(nodes).tobytes(), limit, batch)
        if key not in costs:
            for k in [k for k in costs if k[1:] != key[1:]]: del costs[k]
            costs[key] = list(costs_from(net, nodes, limit=limit, batch=batch))
        return iter(costs[key])
    S.T.costs_from = cf; S.HARVEST = FS.GRID; fields = S.earth_fields
    def with_basin(lat, lon):
        wheat, barley, arable, inside = fields(lat, lon); sb, W = FS.basin_on_pool(lat, lon); boost = W * FS.F_B / (S.FARMED * S.SOWN)
        return (1 - sb) * wheat + sb * boost, (1 - sb) * barley + sb * boost, arable, inside
    S.earth_fields = with_basin
    plan = json.loads(S.PLAN.read_text()); shares = plan['parameters']['marketed_share_e']; limits = plan['parameters']['haul_limit_L_road_km']; rows = {}
    for name, no_egypt in VARIANTS:
        x = dict(np.load(S.PILOT.POOL)); S.NO_EGYPT = no_egypt; land = x['land']; cell = float(x['cell_km']) ** 2
        p2 = np.where(land, SH.capacity(x['lat'], x['lon']) * x['history'], 0.0)       # people per km2
        allowed = land & x['allowed']; empire = float((p2[allowed] * cell).sum())
        factor = FRIER / empire if name.startswith('frier') else 1.0; x['density'] = p2 * factor
        ep = SH.proper(x['lat'], x['lon']) & land
        a, meta = S.prepare(x); fed = S.fed_surface(a, shares, limits); west = a['lon'] <= np.median(a['lon'])
        table, decision = S.decide(shares, limits, fed, a['residents'], west); pc = ep.ravel()[a['nodes']]; i270 = limits.index(270)
        rows[name] = dict(without_egypt=no_egypt, level_factor=factor, p2_empire_people_unscaled=empire, window_people=float((x['density'][land] * cell).sum()),
            empire_people=float((x['density'][allowed] * cell).sum()), egypt_proper_people=float((x['density'][ep] * cell).sum()), urban_share=meta['urban_share'],
            decision=decision, surface=table, surplus_per_rural_person=meta['surplus_per_rural_person'],
            egypt_proper_city_fed_share_at_270=None if no_egypt else {str(e): float(fed[i270, j][pc].sum() / a['residents'][pc].sum()) for j, e in enumerate(shares)})
        print(name, 'factor %.3f egypt %.2f M' % (factor, rows[name]['egypt_proper_people'] / 1e6), json.dumps(decision), flush=True)
    S.NO_EGYPT = False
    passing = [n for n, r in rows.items() if r['decision']['cited_270_kept'] and r['decision']['transferable']]
    adopted = 0.39226216930113295; e = rows['frier']['decision']['e95_all_at_L_used']
    write(out / 'results.json', dict(status='supply_people_level', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), machinery_sha256=dict(floodplain_supply=sha(ROOT / 'scripts/floodplain_supply.py'),
        supply_heartland_people=sha(ROOT / 'scripts/supply_heartland_people.py'), egypt_sufficiency=sha(ROOT / 'scripts/egypt_sufficiency.py')), harvest_grid_sha256=sha(FS.GRID),
        variants=rows, passing_variants=passing, primary='frier', primary_pass='frier' in passing, adopted_share=adopted, frier_e95=e,
        adopted_share_within_x1_25=None if e is None else bool(abs(np.log(e / adopted)) <= np.log(1.25))))
    return passing


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); print(main(ap.parse_args().out))
