"""Independent review of the floodplain rule (calibration/floodplain_rule_20261114, amendments A1, A2):
basin capacity equation, qualification rebuilt from stored flow/catchment/rain with separate run-finding code,
regions re-summed with a separate ray-casting polygon test, supply decisions rebuilt from the stored surfaces,
and the fresh-replay hash record."""
import json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write
from review_egypt_sufficiency import crossing

OUT = ROOT / 'output/floodplain_rule_20261114'


def inside(poly, x, y):
    """Even-odd ray casting, vectorised over points."""
    res = np.zeros(x.shape, bool); n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        cond = (y1 > y) != (y2 > y)
        with np.errstate(divide='ignore', invalid='ignore'):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        res ^= cond & (x < xc)
    return res


def last_run_end(flags):
    flags = list(map(bool, flags))
    if all(flags) or not any(flags): return None
    k = flags.index(False); seq = flags[k + 1:] + flags[:k + 1]; order = list(range(k + 1, 12)) + list(range(0, k + 1))
    runs, cur = [], []
    for f, m in zip(seq, order):
        if f: cur.append(m)
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    longest = max(len(r) for r in runs)
    return min(r[-1] + 1 for r in runs if len(r) == longest)


def main():
    plan = json.loads((ROOT / 'calibration/floodplain_rule_20261114/plan.json').read_text()); r = json.loads((OUT / 'results.json').read_text())
    assert r['plan_sha256'] == sha(ROOT / 'calibration/floodplain_rule_20261114/plan.json') and r['producer_sha256'] == sha(ROOT / 'scripts/floodplain_earth.py')
    a = np.load(ROOT / 'output/land_people/earth/earth.npz'); b = np.load(ROOT / 'output/land_people/earth_floodplain/earth.npz'); f = np.load(OUT / 'fields.npz')
    s = f['s']; ca, cb = np.nan_to_num(a['capacity']).astype(float), np.nan_to_num(b['capacity']).astype(float); land = a['land']
    assert np.array_equal(ca[s == 0], cb[s == 0])
    expect = (1 - s) * f['base_capacity_on_basin'] + s * f['basin_unit_capacity'] * 0.95
    err = float(np.max(np.abs(cb[s > 0] - expect[s > 0]) / np.maximum(expect[s > 0], 1e-9))); assert err < 1e-5, err
    flow, cat, rain = f['flow'], f['catchment'], f['flood_rain']; above = flow > 1.0
    ok = np.array([False] + [last_run_end(above[:, k]) in (7, 8, 9, 10) for k in range(1, flow.shape[1])])
    q = land & (cat > 0) & ok[cat] & (rain < 100.0); assert np.array_equal(q, f['qualifying'])
    assert np.all(f['qualifying'][s > 0]) and np.all(s <= f['candidate'] + 1e-12) and np.all(s[~f['qualifying']] == 0)
    import land_people_earth as L
    lat, lon = a['lat'], a['lon']; LAT, LON = np.meshgrid(lat, lon, indexing='ij'); km2 = (111.32 / 12) ** 2 * np.cos(np.radians(LAT)); checks = 0
    for name, reg in L.REGIONS.items():
        m = inside(reg['poly'], LON, LAT) & land
        for key, cap in (('baseline_m', ca), ('A1_F0.95', cb)):
            v = float((cap * km2)[m].sum() / 1e6); assert abs(v - r['regions'][name][key]) <= 1e-6 * max(1, v), (name, key, v); checks += 1
    t1 = all(x['A1_F0.95'] <= 1.05 * x['baseline_m'] + 1e-9 for n, x in r['regions'].items() if n != 'Egypt'); t2 = 3.6 <= r['regions']['Egypt']['A1_F0.95'] <= 6.25
    assert r['primary_pass'] == (t1 and t2)
    sp = json.loads((OUT / 'supply.json').read_text()); shares = json.loads((ROOT / 'calibration/settlement_supply_calibration_20261113/plan.json').read_text())['parameters']['marketed_share_e']
    for n, v in sp['variants'].items():
        ratios = {}
        for Lk, row in v['surface'].items():
            for part in ('all', 'west', 'east'):
                e = crossing(shares, row[part]['fed_share']); assert (e is None and row[part]['e95'] is None) or abs(e - row[part]['e95']) < 1e-12; checks += 1
            w, e = row['west']['e95'], row['east']['e95']; ratios[Lk] = None if not (w and e) else abs(math.log(w / e))
        valid = {k: x for k, x in ratios.items() if x is not None}; best = min(valid, key=lambda k: (valid[k], float(k))) if valid else None
        keep = '270' in valid and (valid['270'] <= math.log(1.25) or valid['270'] <= 1.1 * valid[best]); assert v['decision']['cited_270_kept'] == keep
    assert sp['variants']['A2_floodplain_P2_production_without_egypt']['surface'] == sp['variants']['floodplain_P2_without_egypt']['surface']
    replay = (Path('/tmp/claude-0/-home-user-rotclimate/102a023a-f7ac-5ee0-b069-1ee48d6f8e91/scratchpad/fp_replay.txt')).read_text()
    fresh = all(line.endswith(': OK') for line in replay.strip().splitlines()) and len(replay.strip().splitlines()) == 5
    write(OUT / 'review.json', dict(status='passed' if fresh else 'passed_without_fresh_replay', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'), supply_sha256=sha(OUT / 'supply.json'),
        capacity_equation_max_relative_error=err, qualifying_rebuilt=True, scalar_checks=checks, fresh_replay_hashes_equal=fresh, replay_record=replay.strip().splitlines()))
    print('review', 'passed' if fresh else 'passed without fresh replay', checks, err)


if __name__ == '__main__':
    main()
