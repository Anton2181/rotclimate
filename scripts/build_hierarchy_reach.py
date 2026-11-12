"""Seasonal two-way reach from the cohorts left after market forwarding, on the unchanged transport world."""
import argparse
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from prepare_settlement_feedback import DATA, OUT as BASE
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/settlement_market_range_20261112'
TWO_DAY = ROOT / 'output/settlement_hierarchy_20261112'


def scenarios(mode):
    """Publication order: the two-day test, then the longer legs."""
    rows = [dict(id=f'market2_{s}', folder=TWO_DAY / f'{mode}_share{s}', range_days=2, share=s / 100) for s in (25, 50)]
    rows += [dict(id=f'market{d}_{s}', folder=OUT / f'{mode}_range{d}_share{s}', range_days=d, share=s / 100)
             for d in (6, 12) for s in (25, 50)]
    return rows


def build(mode):
    x = dict(np.load(BASE / f'{mode}_inputs.npz')); folder = DATA / ('corrected' if mode == 'corrected' else '')
    original = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))
    receipt = json.loads((BASE / f'{mode}_footprints.json').read_text()); footprints = BASE / f'{mode}_footprints.npz'
    if receipt['status'] != 'passed' or sha(footprints) != receipt['footprints_sha256']:
        raise ValueError('Reviewed source footprints changed')
    cache = dict(np.load(footprints)); actors = x['actor']; landnodes = cache['landnodes']
    cases = scenarios(mode); fields = []; sources = {}
    for family in (TWO_DAY, OUT):
        review = json.loads((family / 'review.json').read_text())
        if review['status'] != 'passed' or any(sha(ROOT / p) != d for p, d in review['results_sha256'].items()):
            raise ValueError('Current independent scenario review required')
    for c in cases:
        result = json.loads((c['folder'] / 'results.json').read_text())
        if sha(c['folder'] / 'fields.npz') != result['fields_sha256']:
            raise ValueError('Scenario fields changed')
        sources[str((c['folder'] / 'fields.npz').relative_to(ROOT))] = result['fields_sha256']
        fields.append(dict(np.load(c['folder'] / 'fields.npz'), result=result))
    masks = np.zeros((len(cases), len(original['actors']), len(landnodes)), np.uint16)
    for k, (month, site) in enumerate(cache['keys']):
        cells = cache['covered'][cache['offsets'][k]:cache['offsets'][k + 1]]
        for i, f in enumerate(fields):
            if f['active'][site]:
                masks[i, actors[site], cells] |= 1 << int(month)
    if np.any(masks & ~cache['reference'][None]):
        raise ValueError('Reach exceeds the exact common reference')
    popcount = np.array([i.bit_count() for i in range(4096)], np.uint8); weights = x['area'].ravel()[landnodes].astype(float)   # float64 sums; the base packet summed in float32
    base_reach = json.loads((BASE / f'{mode}_reach.json').read_text())
    base_summary = next(s for s in base_reach['summaries'] if s['key'] == f'{mode}_h600_f0.075'); summaries = []
    for i, (c, f) in enumerate(zip(cases, fields)):
        bins = popcount[np.bitwise_or.reduce(masks[i], axis=0)]; r = f['result']
        actor_summary = [dict(actor=actor['name'], candidate_sources=int(np.sum(actors == a)),
            active_sources=int(np.sum(f['active'] & (actors == a))), inventory_scored=bool(np.any(actors == a)),
            all_bin_area_km2=float(weights[popcount[masks[i, a]] == 12].sum())) for a, actor in enumerate(original['actors'])]
        summaries.append(dict(id=c['id'], key=r['key'], active_sources=r['active_sources'], town_people=r['town_people'],
            viable_communities=r['viable_communities'], area_weighted_access_bins=float(np.sum(weights * bins) / weights.sum()),
            base_area_weighted_access_bins=base_summary['area_weighted_access_bins'],
            all_bin_area_km2=float(weights[bins == 12].sum()), any_bin_area_km2=float(weights[bins > 0].sum()), actors=actor_summary))
    output = OUT / f'{mode}_reach.npz'; np.savez_compressed(output, masks=masks, landnodes=landnodes)
    write(OUT / f'{mode}_reach.json', dict(status='same_cohort_source_reach_after_forwarding', adopt=False, mode=mode,
        footprints_sha256=receipt['footprints_sha256'], reach_sha256=sha(output), source_fields=sources,
        producer_sha256=sha(Path(__file__)), summaries=summaries, unchanged_transport_reference_exact=True,
        empirical_control_or_occupancy_fit=False))
    print(mode, 'reach for', len(cases), 'hierarchy cases', [round(s['area_weighted_access_bins'], 3) for s in summaries], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=('raw', 'corrected'), required=True)
    build(p.parse_args().mode)
