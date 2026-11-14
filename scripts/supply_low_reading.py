"""Earth supply calibration at the flat 100/ha reading (calibration/supply_low_reading_20261114/plan.json)."""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import greek_walls as G
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/supply_low_reading_20261114/plan.json'; OUT = ROOT / 'output/supply_low_reading_20261114'


def main(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    S, FS, SH, PL, Z = G.S, G.FS, G.SH, G.PL, G.Z
    out.mkdir(parents=True, exist_ok=True); costs_from = S.T.costs_from; G.ES.memoise(); costs = {}
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
    residents = Z.residents; f, changed = G.factors('greece'); plan = json.loads(S.PLAN.read_text())
    shares = plan['parameters']['marketed_share_e']; limits = plan['parameters']['haul_limit_L_road_km']; rows = {}
    for reading in ('central', 'low'):
        Z.residents = lambda area, _r, f=f, reading=reading: residents(np.asarray(area) * f, reading)
        try:
            x = dict(np.load(S.PILOT.POOL)); land = x['land']; cell = float(x['cell_km']) ** 2
            p2 = np.where(land, SH.capacity(x['lat'], x['lon']) * x['history'], 0.0); allowed = land & x['allowed']
            x['density'] = p2 * PL.FRIER / float((p2[allowed] * cell).sum()); a, meta = S.prepare(x)
        finally:
            Z.residents = residents
        fed = S.fed_surface(a, shares, limits); west = a['lon'] <= np.median(a['lon']); table, decision = S.decide(shares, limits, fed, a['residents'], west)
        rows[reading] = dict(residents_total=float(a['residents'].sum()), urban_share=meta['urban_share'], decision=decision, surface=table)
        print(reading, 'residents %.2f M' % (a['residents'].sum() / 1e6), json.dumps(decision), flush=True)
    ref = json.loads((ROOT / 'output/greek_walls_20261114/results.json').read_text())['variants']['greece']['surface']
    diff = max(abs(p - q) for L in ref for part in ('all', 'west', 'east') for p, q in zip(ref[L][part]['fed_share'], rows['central']['surface'][L][part]['fed_share']))
    d = rows['low']['decision']
    write(out / 'results.json', dict(status='supply_low_reading', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), control_max_abs_difference=diff,
        readings=rows, low_pass=bool(d['cited_270_kept'] and d['transferable']), low_e95=d['e95_all_at_L_used']))
    return diff, d


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); print(main(ap.parse_args().out))
