"""Greek wall-circuit correction for the Earth supply calibration (calibration/greek_walls_20261114/plan.json)."""
import argparse, csv, io, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import supply_people_level as PL
from settlement_locations_earth import sha, write

FS, SH, ES, S = PL.FS, PL.SH, PL.ES, PL.S; PILOT = S.PILOT; Z = PILOT.Z
PLAN = ROOT / 'calibration/greek_walls_20261114/plan.json'; OUT = ROOT / 'output/greek_walls_20261114'
SCOPES = {'greece': {'Achaea', 'Macedonia', 'Epirus'}, 'greece_and_asia_minor': {'Achaea', 'Macedonia', 'Epirus', 'Asia', 'Lycia et Pamphylia'}}
VARIANTS = [('control', None, False), ('greece', 'greece', False), ('greece_and_asia_minor', 'greece_and_asia_minor', False), ('greece_hansen_150', 'greece', True)]


def factors(scope):
    """Inhabited share per AD 150 catalogue row, in cities() order."""
    rows = list(csv.DictReader(io.StringIO((PILOT.CACHE / 'cities.csv').read_bytes().decode('cp1252'))))
    basis = {r['Primary Key']: (r['Estimate Basis'], float(r['Area'])) for r in csv.DictReader(io.StringIO((PILOT.CACHE / 'areas.csv').read_bytes().decode('utf-8-sig')))}
    keep = [r for r in rows if float(r['Start Date']) <= 150 and (r['End Date'].strip().upper() == 'NULL' or float(r['End Date']) >= 150)]
    f = np.ones(len(keep)); names = []
    for i, r in enumerate(keep):
        b = basis.get(r['Primary Key'])
        if scope and b and r['Province'] in SCOPES[scope] and b[0].startswith('Walls'):
            f[i] = 1 / 3 if b[1] >= 100 else 1 / 2; names.append((r['Ancient Toponym'], r['Province'], b[1], f[i]))
    return f, names


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
    residents = Z.residents; plan = json.loads(S.PLAN.read_text()); shares = plan['parameters']['marketed_share_e']; limits = plan['parameters']['haul_limit_L_road_km']
    ref = json.loads((ROOT / 'output/supply_people_level_20261114/results.json').read_text())['variants']['frier']; rows = {}
    for name, scope, literal in VARIANTS:
        f, changed = factors(scope)
        Z.residents = (lambda area, reading, f=f: np.where(f < 1, 150.0 * np.asarray(area) * f, residents(np.asarray(area), reading))) if literal else (lambda area, reading, f=f: residents(np.asarray(area) * f, reading))
        try:
            x = dict(np.load(S.PILOT.POOL)); land = x['land']; cell = float(x['cell_km']) ** 2
            p2 = np.where(land, SH.capacity(x['lat'], x['lon']) * x['history'], 0.0); allowed = land & x['allowed']
            x['density'] = p2 * PL.FRIER / float((p2[allowed] * cell).sum())
            a, meta = S.prepare(x)
        finally:
            Z.residents = residents
        fed = S.fed_surface(a, shares, limits); west = a['lon'] <= np.median(a['lon']); table, decision = S.decide(shares, limits, fed, a['residents'], west)
        rows[name] = dict(scope=scope, hansen_150_literal=literal, cities_changed=len(changed), changed=[dict(name=n, province=p, walled_ha=h, inhabited_share=s) for n, p, h, s in changed],
                          residents_total=float(a['residents'].sum()), decision=decision, surface=table)
        print(name, len(changed), 'residents %.2f M' % (a['residents'].sum() / 1e6), json.dumps(decision), flush=True)
    control = rows['control']['surface'] == ref['surface'] and rows['control']['decision'] == ref['decision']
    passing = [n for n, r in rows.items() if n != 'control' and r['decision']['cited_270_kept'] and r['decision']['transferable']]
    e = rows['greece']['decision']['e95_all_at_L_used']
    write(out / 'results.json', dict(status='greek_walls_sensitivity', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), control_reproduces=bool(control), variants=rows,
        passing_variants=passing, primary='greece', primary_pass='greece' in passing, adopted_share=0.39226216930113295, greece_e95=e))
    return control, passing


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); print(main(ap.parse_args().out))
