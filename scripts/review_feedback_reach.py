"""Independent source-mask assembly and exact frozen transport-reference checks."""
import gzip
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from prepare_settlement_feedback import OUT, DATA, PLAN
from settlement_locations_earth import sha, write


def check(mode):
    r = json.loads((OUT / f'{mode}_reach.json').read_text()); receipt = json.loads((OUT / f'{mode}_footprints.json').read_text())
    assert r['producer_sha256'] == sha(ROOT / 'scripts/build_feedback_reach.py')
    assert r['footprints_receipt_sha256'] == sha(OUT / f'{mode}_footprints.json')
    assert r['reach_sha256'] == sha(OUT / f'{mode}_reach.npz')
    assert receipt['footprints_sha256'] == sha(OUT / f'{mode}_footprints.npz')
    for p, h in {**receipt['sources'], **r['source_results']}.items():
        assert sha(ROOT / p) == h, p
    x = dict(np.load(OUT / f'{mode}_inputs.npz')); cache = dict(np.load(OUT / f'{mode}_footprints.npz'))
    actual = dict(np.load(OUT / f'{mode}_reach.npz')); actors = x['actor']; landnodes = np.flatnonzero(x['land'])
    np.testing.assert_array_equal(actual['landnodes'], landnodes)
    declaration = json.loads(PLAN.read_text()); expected = np.zeros_like(actual['masks']); frozen = np.zeros_like(expected)
    reference = np.zeros_like(cache['reference']); seen = set()
    for i, (month, site) in enumerate(cache['keys']):
        assert (int(month), int(site)) not in seen and 0 <= month < 12 and actors[site] >= 0
        seen.add((int(month), int(site)))
        cells = cache['covered'][cache['offsets'][i]:cache['offsets'][i + 1]]
        assert (cells < len(landnodes)).all() and len(cells) == len(np.unique(cells))
        reference[actors[site], cells] |= np.uint16(1 << int(month))
    assert len(seen) == 12 * int((actors >= 0).sum())
    for k, case in enumerate(declaration['scenarios']):
        key = f'{mode}_h{case["hours_worker_year"]}_f{case["transfer_fraction"]:g}'
        with np.load(OUT / key / 'fields.npz') as f:
            active, old = f['active'], f['frozen_active']
        review = json.loads((OUT / key / 'review.json').read_text())
        assert review['status'] == 'passed' and review['all_positive_catchments_source_supported']
        for i, (month, site) in enumerate(cache['keys']):
            cells = cache['covered'][cache['offsets'][i]:cache['offsets'][i + 1]]
            if active[site]: expected[k, actors[site], cells] |= np.uint16(1 << int(month))
            if old[site]: frozen[k, actors[site], cells] |= np.uint16(1 << int(month))
    np.testing.assert_array_equal(actual['masks'], expected); np.testing.assert_array_equal(actual['frozen_masks'], frozen)
    np.testing.assert_array_equal(reference, cache['reference'])
    folder = DATA / ('corrected' if mode == 'corrected' else '')
    packet = json.loads((DATA / 'settled_reach.json').read_text())['packets'][mode]
    with gzip.open(folder / 'settled_reach.bin.gz', 'rb') as f:
        f.read(packet['offsets']['masks']); old_reference = np.frombuffer(f.read(reference.nbytes), '<u2').reshape(reference.shape)
    np.testing.assert_array_equal(reference, old_reference)
    assert not np.any(expected & ~reference[None])
    pop = np.array([n.bit_count() for n in range(4096)], np.uint8); weights = x['area'].ravel()[landnodes]
    for k, summary in enumerate(r['summaries']):
        bins = pop[np.bitwise_or.reduce(expected[k], axis=0)]
        # Preserve the published float32-area reduction convention.
        np.testing.assert_allclose(summary['area_weighted_access_bins'], np.sum(weights * bins) / weights.sum(), rtol=1e-12)
        assert len(summary['actors']) == reference.shape[0]
    write(OUT / f'{mode}_reach_review.json', dict(status='passed', results_sha256=sha(OUT / f'{mode}_reach.json'),
        reviewer_sha256=sha(Path(__file__)), source_month_footprints=len(seen), cases_checked=len(expected),
        actor_cell_season_masks_exact=True, old_all_source_reference_exact=True,
        same_audited_resident_cohorts=True, all_actors_retained=True,
        scope='Independent mask assembly and frozen-reference equality; not a second shortest-path implementation or empirical control qualification.'))
    print(mode, 'reach review passed: four cases, all source/month footprints and exact old reference', flush=True)


if __name__ == '__main__':
    for mode in ('raw', 'corrected'):check(mode)
