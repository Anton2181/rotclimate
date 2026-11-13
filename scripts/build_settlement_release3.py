"""Release 3 fantasy settlements: Earth-tested positions (family B, L 800 km) with release-2 sizes.

Declared in calibration/settlement_placement_iteration_20261113/plan_b.json (if_pass).
Marked places stay. Unmarked towns are re-placed with the prior-weighted catchment
tiling at the same count; tracks, hinterlands, sizes, collection catchments and
ledgers are rebuilt on the new positions.
"""
import argparse, gzip, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_fantasy_inputs as I
from build_settlement_release2 import build
from polity.settlement_locations import prior_tiling_sites, match_count
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_placement_iteration_20261113/plan_b.json'
EARTH = ROOT / 'output/settlement_release2_20261113'
TEST = ROOT / 'output/settlement_placement_iteration_20261113/family_b/results.json'
OUT = ROOT / 'output/settlement_release3_20261113'


def one(mode, earth, out):
    w = I.world(mode); packet = json.loads(gzip.decompress((w['folder'] / 'settled_reach.json.gz').read_bytes()))
    old = packet['sites']; spec = packet['specification']; width = w['shape'][1]
    kw = dict(allowed=w['claimed'], aridity=w['aridity'], marked=w['marked'], dry_water_km=w['dry_water_km'])
    args = (w['density'], w['land'], w['water_km'], w['road'], w['elev'], w['cell'])
    legacy = {(s['row'], s['column']) for s in old if not s['marked']}
    if set(prior_tiling_sites(*args, **kw)) != legacy or {(s['row'], s['column']) for s in old if s['marked']} != set(w['marked']):
        raise ValueError('Published towns not reproduced from reassembled inputs')
    reviewed = np.load(ROOT / f'output/settlement_feedback_20261112/{mode}_inputs.npz')
    check = I.collection_owner(w, [s['node'] for s in old], spec['collection_base_bin'], spec['collection_maximum_days_each_way'])
    loc = np.flatnonzero(check >= 0)
    if not np.array_equal(loc, reviewed['local_index']) or not np.array_equal(check[loc], reviewed['owner']):
        raise ValueError('Reviewed collection catchments not reproduced')
    seat, towns = match_count(lambda sp: prior_tiling_sites(*args, prior=w['prior'], seat_people=sp, **kw), len(legacy))
    if len(towns) != len(legacy):
        raise ValueError('Count budget not matched')
    claim = {}
    for s in old:
        if not s['marked'] and s.get('painted_claim'):
            claim[s['painted_claim']] = (s['actor'], s['actor_index'], s['affiliation_basis'])
    sites = [dict(s) for s in old if s['marked']]
    for y, x in towns:
        name = w['claim_info'][int(w['claim_ids'][y, x])]['name']
        name = name.split(' (')[0] if name else name          # sub-regions share their polity, as in the published sites
        actor, index, basis = claim.get(name, (None, -1, 'unresolved'))
        node = int(y * width + x)
        sites.append(dict(id=f'node_{node}', node=node, row=int(y), column=int(x), name=f'Proposed site {node}', actor=actor,
            actor_index=index, affiliation_basis=basis, painted_claim=name, marked=False))
    sites.sort(key=lambda s: s['node'])
    owner = I.collection_owner(w, [s['node'] for s in sites], spec['collection_base_bin'], spec['collection_maximum_days_each_way'])
    local = np.flatnonzero(owner >= 0); track = I.tracks(w, towns)
    (out / f'placed_{mode}_sites.json').write_text(json.dumps(dict(sites=sites, actors=packet['actors']), ensure_ascii=False, separators=(',', ':')) + '\n')
    c = build(mode, earth, out, custom=dict(sites=sites, local=local, catchment=owner[local], prefix='placed',
        extra=dict(tracks=track, prior=w['prior'], claimed=w['claimed'], density=w['density'], marked_cells=np.array(w['marked']))))
    c['placement'] = dict(rule='prior-weighted catchment tiling, L 800 km', seat_people=seat, unmarked=len(towns),
        same_cell_as_before=len(set(towns) & legacy), moved=len(set(towns) - legacy), track_cells=int(track.sum()),
        controls=dict(published_towns_reproduced=True, reviewed_catchments_reproduced=True),
        unaffiliated_new_sites=int(sum(1 for s in sites if not s['marked'] and s['actor_index'] < 0)))
    c['outputs'][f'placed_{mode}_sites.json'] = sha(out / f'placed_{mode}_sites.json')
    return c


def run(out):
    earth = json.loads((EARTH / 'results.json').read_text()); test = json.loads(TEST.read_text())
    if not test['passed'] or test['best_over_all_eight_quadrants'] != 'L800' or not earth['sizes']['primary']['gate']['passed']:
        raise ValueError('Adoption requires the passed placement test at L800 and the passed size gate')
    out.mkdir(parents=True, exist_ok=True)
    result = dict(status='release3_fantasy_settlements_tested_positions_and_calibrated_sizes', plan_sha256=sha(PLAN),
        placement_test_sha256=sha(TEST), earth_results_sha256=sha(EARTH / 'results.json'), producer_sha256=sha(__file__),
        tracks_rebuilt=True, downstream_layers_rebuilt=False, climates={m: one(m, earth, out) for m in ('raw', 'corrected')})
    write(out / 'fantasy.json', result); return result


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('--out', type=Path, default=OUT); r = run(a.parse_args().out)
    for m, c in r['climates'].items():
        print(m, c['sites'], c['placement'], {k: (round(v['total']), round(v['share_of_world_people'], 4), round(v['largest']), v['local_cereal']['fully_supported_sites'], v['people_ledger']['sites_drawing_wider'], v['people_ledger']['unmet_shortfall']) for k, v in c['residents'].items()}, c['area_quantiles_ha'])
