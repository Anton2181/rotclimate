"""Independently union qualified actor/month sources on exact original footprints."""
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/settlement_dispatch_20261112'
PARENT = ROOT / 'output/settlement_feedback_20261112'
DATA = ROOT / 'atlases/earth_fit/data'


def review(mode):
    r = json.loads((OUT / f'{mode}_reach.json').read_text()); x = dict(np.load(PARENT / f'{mode}_inputs.npz'))
    cache = dict(np.load(PARENT / f'{mode}_footprints.npz')); actual = dict(np.load(OUT / f'{mode}_reach.npz'))
    assert r['reach_sha256'] == sha(OUT / f'{mode}_reach.npz')
    assert r['producer_sha256'] == sha(ROOT / 'scripts/build_dispatch_reach.py')
    assert r['footprints_receipt_sha256'] == sha(PARENT / f'{mode}_footprints.json')
    assert r['footprints_sha256'] == sha(PARENT / f'{mode}_footprints.npz')
    for p, digest in r['sources'].items(): assert sha(ROOT / p) == digest, p
    actors = x['actor']; landnodes = np.flatnonzero(x['land']); weights = x['area'].ravel()[landnodes]
    np.testing.assert_array_equal(actual['landnodes'], landnodes)
    popcount = np.array([n.bit_count() for n in range(4096)], np.uint8)
    def assemble(active):
        result = np.zeros_like(cache['reference'])
        for actor in range(len(result)):
            for month in range(12):
                pieces = [cache['covered'][cache['offsets'][i]:cache['offsets'][i + 1]]
                    for i, (m, site) in enumerate(cache['keys']) if m == month and actors[site] == actor and active[site]]
                if pieces:
                    result[actor, np.unique(np.concatenate(pieces))] |= np.uint16(1 << month)
        return result
    reference = assemble(np.ones(len(actors), bool)); np.testing.assert_array_equal(reference, cache['reference'])
    parent_manifest = json.loads((DATA / 'settled_reach.json').read_text())['packets'][mode]
    original_folder = DATA / ('corrected' if mode == 'corrected' else '')
    with gzip.open(original_folder / 'settled_reach.bin.gz', 'rb') as stream:
        stream.read(parent_manifest['offsets']['masks'])
        original = np.frombuffer(stream.read(reference.nbytes), '<u2').reshape(reference.shape)
    np.testing.assert_array_equal(reference, original)
    assert len(actual['masks']) == len(r['cases']) == len(r['summaries']) == 8
    for k, key in enumerate(r['cases']):
        f = dict(np.load(OUT / key / 'fields.npz')); check = json.loads((OUT / key / 'review.json').read_text())
        assert check['status'] == 'passed' and check['all_positive_collection_work_supported']
        assert check['results_sha256'] == sha(OUT / key / 'results.json')
        expected = assemble(f['active']); np.testing.assert_array_equal(actual['masks'][k], expected)
        bins = popcount[np.bitwise_or.reduce(expected, axis=0)]; summary = r['summaries'][k]
        assert summary['active_sources'] == int(f['active'].sum())
        np.testing.assert_allclose(summary['town_people'], f['total'].sum(), rtol=1e-12)
        np.testing.assert_allclose(summary['area_weighted_access_bins'], np.sum(weights * bins) / weights.sum(), rtol=1e-12)
        assert len(summary['actors']) == len(reference)
        for a, item in enumerate(summary['actors']):
            assert item['candidate_sources'] == int((actors == a).sum())
            assert item['active_sources'] == int((f['active'] & (actors == a)).sum())
    write(OUT / f'{mode}_reach_review.json', dict(status='passed', results_sha256=sha(OUT / f'{mode}_reach.json'),
        reviewer_sha256=sha(Path(__file__)), cases_checked=8, all_actors_retained=True,
        same_audited_people_food_and_collection_sources=True, original_reference_actor_cell_seasons_exact=True,
        actual_geographic_patrol_work_qualified=False))
    print(mode, 'independent eight-case potential-reach review passed', flush=True)


if __name__ == '__main__':
    for mode in ('raw', 'corrected'): review(mode)
