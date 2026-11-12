"""Independent metric, matching and physical-constraint replay of all224 draws.

Uses dense distances and a minimum-cost assignment rather than the producer's
KD-tree/sparse maximum matching. Does not rerun its placement allocator.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from scipy.stats import ks_2samp, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_joint_locations_earth import OUT, PLAN
from settlement_locations_earth import sha, write
from polity.settlement_locations import site_fields
from polity import settle


def independent_metrics(x, points):
    shape = x['land'].shape; cell = float(x['cell_km'])
    real = x['real'][x['allowed'].ravel()[x['real']]]
    obs = np.column_stack(np.unravel_index(real, shape))
    distances = cdist(obs * cell, points * cell)
    recall, precision = np.mean(distances.min(1) <= 25), np.mean(distances.min(0) <= 25)
    i, j = linear_sum_assignment(distances > 25)
    matched = int(np.sum(distances[i, j] <= 25))
    prefix = distances[:, :len(obs)]
    pr, pp = np.mean(prefix.min(1) <= 25), np.mean(prefix.min(0) <= 25)
    def nearest(p):
        d = cdist(p * cell, p * cell); np.fill_diagonal(d, np.inf)
        return d.min(1)
    onn, pnn = nearest(obs), nearest(points)
    b = max(1, round(100 / cell)); ny, nx = [(n + b - 1) // b for n in shape]
    def histogram(p):
        return np.histogram2d(p[:, 0], p[:, 1], bins=(np.arange(ny + 1) * b, np.arange(nx + 1) * b))[0].ravel()
    yy, xx = np.indices(shape)
    all_cells = np.column_stack((yy.ravel(), xx.ravel()))
    allowed_cells = np.column_stack(np.nonzero(x['allowed']))
    use = histogram(allowed_cells) / histogram(all_cells) >= .3
    oc, pc = histogram(obs)[use], histogram(points)[use]
    rank = float(spearmanr(oc, pc).statistic) if np.ptp(oc) and np.ptp(pc) else 0.
    ks = float(ks_2samp(onn, pnn).statistic)
    f1 = float(2 * precision * recall / max(precision + recall, 1e-30))
    return dict(F1=f1, precision=float(precision), recall=float(recall), M1=rank, M3=ks,
        composite=(f1 + (rank + 1) / 2 + 1 - ks) / 3, n_real=len(obs), n_model=len(points),
        unique_matches=matched, unique_F1=2 * matched / (len(obs) + len(points)),
        historical_best_prefix=dict(n_model=prefix.shape[1], recall=float(pr), precision=float(pp),
                                    F1=float(2 * pr * pp / max(pr + pp, 1e-30))),
        observed_nn_km=np.quantile(onn, [.1, .5, .9]).tolist(),
        model_nn_km=np.quantile(pnn, [.1, .5, .9]).tolist())


def compare(actual, expected):
    if isinstance(actual, dict):
        for k, v in actual.items():
            compare(v, expected[k])
    else:
        np.testing.assert_allclose(actual, expected, rtol=1e-11, atol=1e-12)


def q(m, weight=.6):
    return weight * m['unique_F1'] + (1 - weight) * ((m['M1'] + 1) / 2 + 1 - m['M3']) / 2


def check(out=OUT):
    result = json.loads((out / 'results.json').read_text())
    assert result['plan_sha256'] == sha(PLAN) and len(result['rows']) == 224
    assert not result['adopt'] and not result['prospective_validation']
    for group in ('sources', 'upstream', 'protected'):
        for p, digest in result[group].items():
            assert sha(ROOT / p) == digest, p
    assert sha(out / 'positions.npz') == result['positions_sha256']
    positions = dict(np.load(out / 'positions.npz')); checked = []; replayed = []
    assert len(positions) == 224
    for pool, receipt in result['inputs'].items():
        assert sha(ROOT / receipt['path']) == receipt['sha256']
        assert sha(ROOT / receipt['history_path']) == receipt['history_sha256']
        x = dict(np.load(ROOT / receipt['path'])); h = dict(np.load(ROOT / receipt['history_path']))
        cell = float(x['cell_km']); required = x['land'] & x['allowed']
        assert h['covered'][required].all() and h['connected'][required].all()
        legacy, eligible = site_fields(x['density'], x['land'], x['water_km'], x['road'], x['elev'], cell,
                                       allowed=x['allowed'], aridity=x['aridity'])
        smooth = ndi.gaussian_filter(np.where(x['land'], x['density'], 0.), 1.)
        selected = [r for r in result['rows'] if r['pool'] == pool]
        assert len(selected) == 112
        budget = next(r['requested'] for r in selected if r['family'] == 'production')
        frozen_production = settle.place_towns(x['density'], x['land'], x['water_km'], x['road'], x['elev'],
            cell, [], allowed=x['allowed'], seed=1, aridity=x['aridity'])[0]
        np.testing.assert_array_equal(positions[f'{pool}__production__1'], frozen_production)
        assert budget == len(frozen_production)
        for row in selected:
            p = positions[f'{pool}__{row["variant"]}__{row["seed"]}']
            assert p.ndim == 2 and p.shape[1] == 2 and np.issubdtype(p.dtype, np.integer)
            assert (p >= 0).all() and (p < np.array(eligible.shape)).all()
            assert len(p) == row['n_model'] == row['requested'] == budget and row['shortfall'] == 0
            assert len(np.unique(p, axis=0)) == len(p) and eligible[p[:, 0], p[:, 1]].all()
            pairs = cdist(p * cell, p * cell); np.fill_diagonal(pairs, np.inf)
            if row['family'] in ('adaptive', 'ablation'):
                if row['family'] == 'adaptive':
                    prior = row['floor'] + (1 - row['floor']) * np.exp(-h['distance_km'] / row['scale_km'])
                else:
                    prior = h['old_clipped_history800'] ** (800. / 450.)
                weights = legacy[eligible] * smooth[eligible] ** (row['power'] - 1.) * prior[eligible]
                intensity = weights / weights.sum() * budget / cell ** 2
                assert abs(intensity.sum() * cell ** 2 - budget) < 1e-8
                spacing = np.zeros(eligible.shape)
                spacing[eligible] = np.minimum(.35 / np.sqrt(np.maximum(intensity, np.finfo(float).tiny)), 45.)
                local = spacing[p[:, 0], p[:, 1]]
                assert np.all(pairs > (local[:, None] + local[None, :]) / 2 - 1e-10)
            elif row['family'] == 'fixed':
                assert pairs.min() > 18. - 1e-10
            else:
                local = settle.SPACING * np.minimum(np.sqrt(settle.SEAT_PEOPLE / settle.SEAT_REF_DENSITY
                    * (settle.SEAT_REF_DENSITY / np.maximum(smooth[p[:, 0], p[:, 1]], 1e-9))
                    ** settle.SEAT_BETA / np.pi), settle.MAX_RADIUS_KM)
                i, j = np.triu_indices(len(p), 1)
                # The old sequential kernel excludes later sites with each
                # earlier site's radius; it does not use a symmetric radius.
                assert np.all(pairs[i, j] > local[i] - 1e-10)
            m = independent_metrics(x, p); compare(m, row); compare(q(m), row['Q'])
            replayed.append(dict(row, **m))
            checked.append(dict(pool=pool, variant=row['variant'], seed=row['seed'], count=len(p)))
        expected = {(power, scale, floor, seed) for power in (.5, .7, 1.) for scale in (450, 800)
                    for floor in (0., .1, .3, 1.) if not (scale == 800 and floor == 1.)
                    for seed in (1, 7, 19, 43, 97)}
        actual = {(r['power'], r['scale_km'], r['floor'], r['seed']) for r in selected if r['family'] == 'adaptive'}
        assert actual == expected and sum(r['family'] == 'ablation' for r in selected) == 5
    ranking = []
    for item in result['ranking']:
        pools = {}
        for pool in ('han', 'rome'):
            rr = [r for r in replayed if r['pool'] == pool and r['variant'] == item['variant']]
            average = {k: float(np.mean([r[k] for r in rr])) for k in ('unique_F1', 'F1', 'M1', 'M3')}
            compare(average, item['pools'][pool]); compare(q(average), item['pools'][pool]['Q'])
            for k in average:
                compare([min(r[k] for r in rr), max(r[k] for r in rr)], item['pools'][pool]['seed_range'][k])
            pools[pool] = average
        m = {k: (pools['han'][k] + pools['rome'][k]) / 2 for k in pools['han']}
        compare(m, item['mean']); compare(q(m), item['Q'])
        assert item['feasible'] and item['family'] != 'ablation'
        ranking.append(dict(variant=item['variant'], mean=m))
    ordered = sorted(ranking, key=lambda r: (-q(r['mean']), r['variant']))
    assert [r['variant'] for r in ordered] == [r['variant'] for r in result['ranking']]
    assert ordered[0]['variant'] == result['development_lead']
    for weight in (.4, .6, .8):
        lead = min(ranking, key=lambda r: (-q(r['mean'], weight), r['variant']))
        assert lead['variant'] == result['location_weight_sensitivity'][str(weight)]['variant']
        compare(q(lead['mean'], weight), result['location_weight_sensitivity'][str(weight)]['Q'])
    def vector(r):
        return np.array([r['mean']['unique_F1'], r['mean']['M1'], -r['mean']['M3']])
    frontier = [r['variant'] for r in ordered if not any(
        (vector(o) >= vector(r)).all() and (vector(o) > vector(r)).any() for o in ordered)]
    assert frontier == result['pareto_frontier']
    review = dict(status='passed', results_sha256=sha(out / 'results.json'), reviewer_sha256=sha(Path(__file__)),
        placements_checked=len(checked), independently_recomputed_metrics=True,
        matching_method='Dense25km distance matrix and minimum-cost full assignment; producer uses sparse maximum matching.',
        count_eligibility_uniqueness_spacing=True, all21_variants_and5_seeds=True,
        ranking_frontier_and_weight_sensitivity=True, protected_artifacts_unchanged=True,
        population_food_staff_control_changed=False, rows=checked)
    write(out / 'review.json', review)
    print('Independent review passed for all224placements, metrics, ranking and constraints.', flush=True)
    return review


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT)
    check(parser.parse_args().out)
