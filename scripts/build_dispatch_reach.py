"""Same audited work/food cohorts select frozen potential-travel footprints."""
import itertools
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from build_settlement_dispatch import OUT, PARENT, case_key
from settlement_locations_earth import sha, write


def build(mode):
    x = dict(np.load(PARENT / f'{mode}_inputs.npz')); cache = dict(np.load(PARENT / f'{mode}_footprints.npz'))
    receipt = json.loads((PARENT / f'{mode}_footprints.json').read_text())
    if receipt['status'] != 'passed' or receipt['footprints_sha256'] != sha(PARENT / f'{mode}_footprints.npz'):
        raise ValueError('Checked original source footprints required')
    for path, digest in receipt['sources'].items():
        if sha(ROOT / path) != digest:
            raise ValueError('Frozen transport source changed: ' + path)
    actors = x['actor']; nodes = np.flatnonzero(x['land']); weights = x['area'].ravel()[nodes]
    np.testing.assert_array_equal(nodes, cache['landnodes']); np.testing.assert_array_equal(x['nodes'], cache['nodes'])
    cases = [case_key(mode, *c) for c in itertools.product((600, 300), (60000, 120000), ('all_open', 'bins6_7_8_closed'))]
    masks = np.zeros((len(cases),) + cache['reference'].shape, np.uint16); inputs = {}; summaries = []
    popcount = np.array([i.bit_count() for i in range(4096)], np.uint8)
    for k, key in enumerate(cases):
        folder = OUT / key; result = json.loads((folder / 'results.json').read_text()); review = json.loads((folder / 'review.json').read_text())
        if review['status'] != 'passed' or review['results_sha256'] != sha(folder / 'results.json') or not review['all_positive_collection_work_supported']:
            raise ValueError('Current joint people/food/work review required: ' + key)
        fields = dict(np.load(folder / 'fields.npz')); active = fields['active']
        for path in (folder / 'results.json', folder / 'fields.npz', folder / 'review.json'):
            inputs[str(path.relative_to(ROOT))] = sha(path)
        for i, (month, site) in enumerate(cache['keys']):
            if active[site]:
                cells = cache['covered'][cache['offsets'][i]:cache['offsets'][i + 1]]
                masks[k, actors[site], cells] |= np.uint16(1 << int(month))
        assert not np.any(masks[k] & ~cache['reference'])
        bins = popcount[np.bitwise_or.reduce(masks[k], axis=0)]
        names = json.loads((PARENT / f'{mode}_reach.json').read_text())['summaries'][0]['actors']
        summaries.append(dict(key=key, active_sources=result['active_sources'], town_people=result['town_people'],
            viable_communities=result['viable_communities'], area_weighted_access_bins=float(np.sum(weights * bins) / weights.sum()),
            all_bin_area_km2=float(weights[bins == 12].sum()), any_bin_area_km2=float(weights[bins > 0].sum()),
            actors=[dict(actor=names[a]['actor'], candidate_sources=int((actors == a).sum()),
                active_sources=int((active & (actors == a)).sum()), inventory_scored=bool((actors == a).any()),
                all_bin_area_km2=float(weights[popcount[masks[k, a]] == 12].sum())) for a in range(len(names))]))
    np.savez_compressed(OUT / f'{mode}_reach.npz', masks=masks, landnodes=nodes)
    write(OUT / f'{mode}_reach.json', dict(status='potential_travel_reach_from_joint_qualified_sources', adopt=False,
        mode=mode, cases=cases, summaries=summaries, sources=inputs,
        footprints_receipt_sha256=sha(PARENT / f'{mode}_footprints.json'),
        footprints_sha256=sha(PARENT / f'{mode}_footprints.npz'), reach_sha256=sha(OUT / f'{mode}_reach.npz'),
        producer_sha256=sha(Path(__file__)), actual_geographic_patrol_hours_qualified=False,
        limits='Source food and collection work qualify;footprints are unchanged potential travel access,not funded patrol schedules or political control.'))
    print(mode, 'eight joint source/reach cases assembled', flush=True)


if __name__ == '__main__':
    for mode in ('raw', 'corrected'): build(mode)
