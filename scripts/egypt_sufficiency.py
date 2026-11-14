"""Egypt-sufficiency sensitivity (calibration/egypt_sufficiency_20261114/plan.json).

Runs the reviewed whole-empire supply calibration unchanged except for Egyptian yield (and rural people) scaled by k.
The freight network does not depend on k, so it is built once and reused (memoised by month)."""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_supply_calibration as S
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/egypt_sufficiency_20261114/plan.json'; OUT = ROOT / 'output/egypt_sufficiency_20261114'
ARCHIVE = ROOT / 'output/settlement_supply_calibration_20261113/results.json'
VARIANTS = [('control', 1.0, False), ('Y_1.94', 1.94, False), ('Y_2.16', 2.16, False), ('YP_1.94', 1.94, True), ('YP_2.16', 2.16, True)]
STATE = dict(k=1.0)


def egypt(lat, lon):
    return (lon >= 29.0) & (lat <= 32.0)


def memoise():
    nets, dij, costs = {}, {}, {}
    cost_network, dijkstra, costs_from = S.T.cost_network, S.dijkstra, S.T.costs_from
    def cn(world, st, cl, month, ports, river_places):
        if month not in nets: nets[month] = cost_network(world, st, cl, month, ports, river_places)
        return nets[month]
    def dj(graph, **kw):
        key = (graph.shape, graph.nnz, float(graph.data.sum()), kw['limit'], len(kw['indices']))
        if key not in dij: dij[key] = dijkstra(graph, **kw)
        return dij[key]
    def cf(net, nodes, limit, batch):
        key = id(net)
        if key not in costs: costs[key] = list(costs_from(net, nodes, limit=limit, batch=batch))
        return iter(costs[key])
    S.T.cost_network, S.dijkstra, S.T.costs_from = cn, dj, cf


def main(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    out.mkdir(parents=True, exist_ok=True); memoise(); fields = S.earth_fields
    def scaled(lat, lon):
        wheat, barley, arable, inside = fields(lat, lon); f = np.where(egypt(lat, lon), STATE['k'], 1.0)
        return wheat * f, barley * f, arable, inside
    S.earth_fields = scaled
    plan = json.loads(S.PLAN.read_text()); shares = plan['parameters']['marketed_share_e']; limits = plan['parameters']['haul_limit_L_road_km']
    archive = json.loads(ARCHIVE.read_text()); rows = {}
    for name, k, people in VARIANTS:
        x = dict(np.load(S.PILOT.POOL)); STATE['k'] = k
        if people: x['density'] = np.where(egypt(x['lat'], x['lon']), x['density'] * k, x['density'])
        a, meta = S.prepare(x); fed = S.fed_surface(a, shares, limits); west = a['lon'] <= np.median(a['lon'])
        table, decision = S.decide(shares, limits, fed, a['residents'], west)
        eg = egypt(x['lat'], x['lon']).ravel()[a['nodes']]; i270 = limits.index(270)
        rows[name] = dict(k=k, rural_people_scaled=people, decision=decision, surface=table,
            egypt_city_fed_share_at_270={str(e): float(fed[i270, j][eg].sum() / a['residents'][eg].sum()) for j, e in enumerate(shares)},
            surplus_person_years=meta['surplus_person_years'], egypt_surplus_person_years=float(a['surplus'][egypt(x['lat'], x['lon']).ravel()].sum()),
            egypt_residents=float(a['residents'][eg].sum()))
        print(name, json.dumps(decision), flush=True)
    control_exact = rows['control']['surface'] == archive['surface'] and rows['control']['decision'] == archive['decision']
    passing = [n for n, r in rows.items() if n != 'control' and r['decision']['cited_270_kept'] and r['decision']['transferable']]
    write(out / 'results.json', dict(status='egypt_sufficiency_sensitivity', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), calibration_producer_sha256=sha(ROOT / 'scripts/settlement_supply_calibration.py'),
        control_reproduces_archive=bool(control_exact), variants=rows, passing_variants=passing))
    return control_exact, passing


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); print(main(ap.parse_args().out))
