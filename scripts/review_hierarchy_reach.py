"""Second, dense implementation of the hierarchy reach masks and their summaries."""
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from build_hierarchy_reach import BASE, DATA, OUT, scenarios
from settlement_locations_earth import sha, write


def main():
    checked = {}
    for mode in ('raw', 'corrected'):
        reach = json.loads((OUT / f'{mode}_reach.json').read_text()); assert reach['reach_sha256'] == sha(OUT / f'{mode}_reach.npz')
        masks = np.load(OUT / f'{mode}_reach.npz')['masks']; x = dict(np.load(BASE / f'{mode}_inputs.npz'))
        cache = dict(np.load(BASE / f'{mode}_footprints.npz')); assert sha(BASE / f'{mode}_footprints.npz') == reach['footprints_sha256']
        folder = DATA / ('corrected' if mode == 'corrected' else '')
        names = [a['name'] for a in json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))['actors']]
        land = len(cache['landnodes']); weights = x['area'].ravel()[cache['landnodes']].astype(float); keys = cache['keys']; offsets = cache['offsets']
        # One boolean plane per source site and month, combined per case by matrix products.
        sites = np.unique(keys[:, 1]); row = {int(s): i for i, s in enumerate(sites)}
        planes = np.zeros((12, len(sites), land), bool)
        for k, (month, site) in enumerate(keys):planes[month, row[int(site)], cache['covered'][offsets[k]:offsets[k + 1]]] = True
        for i, (c, summary) in enumerate(zip(scenarios(mode), reach['summaries'])):
            f = np.load(c['folder'] / 'fields.npz'); active = f['active'][sites]; expected = np.zeros((len(names), land), np.uint16)
            for a in range(len(names)):
                chosen = active & (x['actor'][sites] == a)
                for month in range(12):
                    expected[a] |= (planes[month, chosen].any(0).astype(np.uint16) << month)
            assert np.array_equal(expected, masks[i]), c['id']
            union = np.zeros(land, np.uint16)
            for a in range(len(names)):union |= expected[a]
            bins = np.array([bin(int(v)).count('1') for v in union])
            assert abs(summary['area_weighted_access_bins'] - float((weights * bins).sum() / weights.sum())) < 1e-9
            assert summary['active_sources'] == int(f['active'].sum()) and summary['id'] == c['id']
            assert not np.any(expected & ~cache['reference'])
        checked[mode] = len(reach['summaries'])
    write(OUT / 'reach_review.json', dict(status='passed', reviewer_sha256=sha(Path(__file__)), cases_checked=checked,
        results_sha256={m: sha(OUT / f'{m}_reach.json') for m in checked},
        method='dense boolean planes per source and month; masks, summaries and reference containment recomputed'))
    print('Hierarchy reach reviewed', checked)


if __name__ == '__main__':main()
