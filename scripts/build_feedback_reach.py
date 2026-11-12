"""The SAME coupled residents select sources on the unchanged transport world.

Every source footprint also rebuilds the old all-source reference, which must
match every published actor/cell/season mask exactly before new masks are saved.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import sys

import numpy as np
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from prepare_settlement_feedback import OUT, DATA, PLAN
from settlement_locations_earth import sha, write
from polity.administrative_world import audit_world
from polity.administrative_hierarchy import month_graph
from polity.settlement_support import paired_reach


def build(mode):
    declaration = json.loads(PLAN.read_text()); x = dict(np.load(OUT / f'{mode}_inputs.npz'))
    folder = DATA / ('corrected' if mode == 'corrected' else '')
    original = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))
    packet = json.loads((DATA / 'settled_reach.json').read_text())['packets'][mode]
    nodes = x['nodes']; actors = x['actor']; landnodes = np.flatnonzero(x['land'])
    cases = []; case_fields = []; source_results = {}
    for c in declaration['scenarios']:
        key = f'{mode}_h{c["hours_worker_year"]}_f{c["transfer_fraction"]:g}'; origin = OUT / key
        result = json.loads((origin / 'results.json').read_text()); review = json.loads((origin / 'review.json').read_text())
        if review['status'] != 'passed' or review['results_sha256'] != sha(origin / 'results.json'):
            raise ValueError('Current final cell-food review required: ' + key)
        source_results[str((origin / 'results.json').relative_to(ROOT))] = sha(origin / 'results.json')
        source_results[str((origin / 'fields.npz').relative_to(ROOT))] = sha(origin / 'fields.npz')
        cases.append(result); case_fields.append(dict(np.load(origin / 'fields.npz')))
    paths = [DATA / 'atlas.json', DATA / 'winds12.npz', folder / 'atlas.bin', folder / 'harvest.json',
        folder / 'harvest.bin', folder / 'settled_reach.json.gz', folder / 'settled_reach.bin.gz']
    paths += [ROOT / p for p in ['polity/administrative_world.py', 'polity/economic_world.py', 'polity/fields.py',
        'polity/settle.py', 'polity/network.py', 'polity/control.py', 'polity/seasons.py', 'polity/transport.py',
        'polity/administrative_hierarchy.py', 'polity/settlement_support.py']]
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    footprints_file = OUT / f'{mode}_footprints.npz'; receipt_file = OUT / f'{mode}_footprints.json'
    if receipt_file.exists():
        old = json.loads(receipt_file.read_text())
        if old['sources'] != sources or old['footprints_sha256'] != sha(footprints_file):
            raise ValueError('Changed frozen footprint inputs; create a new provenance rather than reuse')
        cache = dict(np.load(footprints_file)); print(mode, 'reusing checked source footprints', flush=True)
    else:
        print(mode, 'rebuilding matching current town/track transport', flush=True)
        r, _ = audit_world(DATA.parent, mode)
        if set(nodes) != {t['row'] * x['land'].shape[1] + t['col'] for t in r['towns']}:
            raise ValueError('Current town/track reconstruction changed site nodes')
        if not np.array_equal(x['land'], r['land']):
            raise ValueError('Transport reconstruction changed land')
        reference = np.zeros((len(original['actors']), len(landnodes)), np.uint16)
        fragments = []; offsets = [0]; keys = []
        for month in range(12):
            graph, _ = month_graph(r['world'], r['statics'], r['climate'], month, r['ports'], r['river_places'])
            reverse = graph.T.tocsr()
            def footprint(j):
                outward = dijkstra(graph, directed=True, indices=int(nodes[j]), limit=2.)[landnodes]
                inward = dijkstra(reverse, directed=True, indices=int(nodes[j]), limit=2.)[landnodes]
                return j, np.flatnonzero(paired_reach(outward, inward, leg_days=2., ration_days=4.)).astype(np.uint32)
            with ThreadPoolExecutor(max_workers=4) as workers:
                for j, covered in workers.map(footprint, np.flatnonzero(actors >= 0)):
                    reference[actors[j], covered] |= 1 << month
                    fragments.append(covered); offsets.append(offsets[-1] + len(covered)); keys.append((month, j))
            print(mode, 'source footprints month', month + 1, flush=True)
        with gzip.open(folder / 'settled_reach.bin.gz', 'rb') as f:
            f.read(packet['offsets']['masks'])
            expected = np.frombuffer(f.read(reference.nbytes), '<u2').reshape(reference.shape)
        if not np.array_equal(reference, expected):
            raise ValueError('All-source actor/season reference did not exactly reproduce the published transport')
        np.savez_compressed(footprints_file, keys=np.asarray(keys, int), offsets=np.asarray(offsets, np.int64),
            covered=np.concatenate(fragments), reference=reference, nodes=nodes, landnodes=landnodes)
        write(receipt_file, dict(status='passed', sources=sources, footprints_sha256=sha(footprints_file),
            producer_sha256=sha(Path(__file__)), reference_actor_cell_seasons_exact=True,
            source_month_footprints=len(keys), all_actors_retained=True))
        cache = dict(np.load(footprints_file))
    masks = np.zeros((len(cases), len(original['actors']), len(landnodes)), np.uint16)
    frozen_masks = np.zeros_like(masks)
    for k, (month, site) in enumerate(cache['keys']):
        cells = cache['covered'][cache['offsets'][k]:cache['offsets'][k + 1]]
        for i, f in enumerate(case_fields):
            if f['active'][site]:
                masks[i, actors[site], cells] |= 1 << int(month)
            if f['frozen_active'][site]:
                frozen_masks[i, actors[site], cells] |= 1 << int(month)
    if np.any(masks & ~cache['reference'][None]):
        raise ValueError('Removing unsupported sources increased reach beyond the exact common reference')
    popcount = np.array([i.bit_count() for i in range(4096)], np.uint8)
    weights = x['area'].ravel()[landnodes]; summaries = []
    for i, (case, fields) in enumerate(zip(cases, case_fields)):
        union = np.bitwise_or.reduce(masks[i], axis=0); bins = popcount[union]
        frozen_bins = popcount[np.bitwise_or.reduce(frozen_masks[i], axis=0)]
        actor_summary = []
        for a, actor in enumerate(original['actors']):
            actor_summary.append(dict(actor=actor['name'], candidate_sources=int(np.sum(actors == a)),
                active_sources=int(np.sum(fields['active'] & (actors == a))), inventory_scored=bool(np.any(actors == a)),
                all_bin_area_km2=float(weights[popcount[masks[i, a]] == 12].sum())))
        summaries.append(dict(key=case['key'], active_sources=case['active_sources'], town_people=case['town_people'],
            viable_communities=case['viable_communities'], area_weighted_access_bins=float(np.sum(weights * bins) / weights.sum()),
            frozen_area_weighted_access_bins=float(np.sum(weights * frozen_bins) / weights.sum()),
            all_bin_area_km2=float(weights[bins == 12].sum()), any_bin_area_km2=float(weights[bins > 0].sum()), actors=actor_summary))
    output = OUT / f'{mode}_reach.npz'; np.savez_compressed(output, masks=masks, frozen_masks=frozen_masks, landnodes=landnodes)
    write(OUT / f'{mode}_reach.json', dict(status='same_plan_source_reach', adopt=False, mode=mode,
        footprints_receipt_sha256=sha(receipt_file), reach_sha256=sha(output), source_results=source_results,
        producer_sha256=sha(Path(__file__)), summaries=summaries, unchanged_transport_reference_exact=True,
        empirical_control_or_occupancy_fit=False, global_rural_food_qualification=False))
    print(mode, 'four coupled source/reach cases ready', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=('raw', 'corrected'), required=True)
    build(p.parse_args().mode)
