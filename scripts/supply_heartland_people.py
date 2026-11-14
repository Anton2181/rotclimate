"""Supply calibration with the heartland-occupancy people pattern (calibration/supply_heartland_people_20261114/plan.json)."""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import egypt_sufficiency as ES
from settlement_locations_earth import sha, write

S = ES.S; PLAN = ROOT / 'calibration/supply_heartland_people_20261114/plan.json'; OUT = ROOT / 'output/supply_heartland_people_20261114'
ARCHIVE_NO_EGYPT = ROOT / 'output/settlement_supply_calibration_20261113/without_egypt/results.json'
VARIANTS = [('control', False, 1.0, False), ('P2', True, 1.0, False), ('P2_egypt_yield_2.16', True, 2.16, False), ('P2_without_egypt', True, 1.0, True)]
STATE = dict(y=1.0)


def proper(lat, lon):
    return (lon >= 29.0) & (lat <= 32.0) & (lon <= 32.6)


def capacity(lat, lon):
    z = np.load(S.HARVEST); zl, zo = z['lat'], z['lon']; step = float(zl[0] - zl[1])
    r = (zl[0] + step / 2 - lat) / step - 0.5; c = (lon - (zo[0] - step / 2)) / step - 0.5
    inside = (r >= -0.5) & (r <= len(zl) - 0.5) & (c >= -0.5) & (c <= len(zo) - 0.5)
    return np.where(inside, ndi.map_coordinates(np.nan_to_num(z['capacity']).astype(float), [np.clip(r, 0, len(zl) - 1), np.clip(c, 0, len(zo) - 1)], order=0), 0.0)


def main(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    out.mkdir(parents=True, exist_ok=True); costs_from = S.T.costs_from; ES.memoise(); fields = S.earth_fields
    costs = {}                                                    # city-to-city costs depend on the city list (without-Egypt removes cities)
    def cf(net, nodes, limit, batch):
        key = (id(net), np.asarray(nodes).tobytes(), limit, batch)
        if key not in costs: costs[key] = list(costs_from(net, nodes, limit=limit, batch=batch))
        return iter(costs[key])
    S.T.costs_from = cf
    def scaled(lat, lon):
        a, b, c, d = fields(lat, lon); f = np.where(proper(lat, lon), STATE['y'], 1.0); return a * f, b * f, c, d
    S.earth_fields = scaled
    plan = json.loads(S.PLAN.read_text()); shares = plan['parameters']['marketed_share_e']; limits = plan['parameters']['haul_limit_L_road_km']
    archive = json.loads(ES.ARCHIVE.read_text()); rows = {}
    for name, p2, y, no_egypt in VARIANTS:
        x = dict(np.load(S.PILOT.POOL)); STATE['y'] = y; S.NO_EGYPT = no_egypt; land = x['land']
        committed_total = float(x['density'][land].sum())
        if p2:
            pattern = np.where(land, capacity(x['lat'], x['lon']) * x['history'], 0.0)
            x['density'] = pattern * committed_total / pattern[land].sum()
        cell = float(x['cell_km']) ** 2; ep = proper(x['lat'], x['lon']) & land
        a, meta = S.prepare(x); fed = S.fed_surface(a, shares, limits); west = a['lon'] <= np.median(a['lon'])
        table, decision = S.decide(shares, limits, fed, a['residents'], west)
        pc = ep.ravel()[a['nodes']]; i270 = limits.index(270)
        rows[name] = dict(people_pattern='P2 heartland occupancy' if p2 else 'committed', egypt_proper_yield_factor=y, without_egypt=no_egypt, decision=decision, surface=table,
            egypt_proper_people=float((x['density'][ep] * cell).sum()), window_people=float((x['density'][land] * cell).sum()),
            egypt_proper_city_fed_share_at_270=None if no_egypt or not pc.any() else {str(e): float(fed[i270, j][pc].sum() / a['residents'][pc].sum()) for j, e in enumerate(shares)},
            surplus_per_rural_person=meta['surplus_per_rural_person'])
        print(name, json.dumps(decision), flush=True)
    S.NO_EGYPT = False
    control_exact = rows['control']['surface'] == archive['surface'] and rows['control']['decision'] == archive['decision']
    passing = [n for n, r in rows.items() if n != 'control' and r['decision']['cited_270_kept'] and r['decision']['transferable']]
    e_adopted = json.loads(ARCHIVE_NO_EGYPT.read_text())['decision']['e95_all_at_L_used']; e_p2 = rows['P2_without_egypt']['decision']['e95_all_at_L_used']
    robust = e_p2 is not None and abs(np.log(e_p2 / e_adopted)) <= np.log(1.25)
    write(out / 'results.json', dict(status='supply_heartland_people_sensitivity', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), machinery_sha256=sha(ROOT / 'scripts/egypt_sufficiency.py'),
        calibration_producer_sha256=sha(ROOT / 'scripts/settlement_supply_calibration.py'), harvest_grid_sha256=sha(S.HARVEST), control_reproduces_archive=bool(control_exact), variants=rows,
        passing_variants=passing, adopted_share=e_adopted, p2_without_egypt_e95=e_p2, adopted_share_robust_to_people_pattern=bool(robust)))
    return control_exact, passing, e_p2, robust


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); print(main(ap.parse_args().out))
