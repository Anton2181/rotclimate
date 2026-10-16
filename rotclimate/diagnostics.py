"""Explain zone-rule misses using an existing simulation, without retuning it."""
from functools import reduce
from dataclasses import asdict
import json

import numpy as np

from .geography import TARGET_CLASSES
from .koppen import CODES, classify
from .score import RULES, ZONE_KOPPEN, best_zone, display_zones, membership_factors, terrain_slope


def audit_rules(mem, factors, koppen, target, valid, indices=None, elev=None):
    pred = best_zone(mem, koppen=koppen)
    displayed = display_zones(mem, valid, ix=indices, elev=elev, koppen=koppen)
    keys = ['unmatched'] + [c[1] for c in TARGET_CLASSES]
    display_keys = keys + ['mountain', 'grassland', 'transitional']
    zones = {}
    for cid, key, _, _ in TARGET_CLASSES:
        own = valid & (target == cid)
        n = int(own.sum())
        if not n:
            continue
        local_kop = koppen[own]
        allowed = np.array([ZONE_KOPPEN[key](c) for c in CODES] + [False])[local_kop]
        scores = mem[key][own]
        correct = pred[own] == cid
        # Mutually exclusive explanations, with class eligibility tested first.
        weak = allowed & ~correct & (scores < 0.3)
        lost = allowed & ~correct & ~weak
        names = list(factors[key])
        values = np.stack([np.broadcast_to(f, target.shape)[own] for f in factors[key].values()])
        least = values.argmin(0)
        local_mem = {k: v[own] for k, v in mem.items()}
        factor_summary = {}
        for i, name in enumerate(names):
            other = [v for j, v in enumerate(values) if j != i]
            relaxed = reduce(np.multiply, other) if other else np.ones(n)
            relaxed_pred = best_zone({**local_mem, key: relaxed}, koppen=local_kop)
            factor_summary[name] = dict(
                mean=float(values[i].mean()), median=float(np.median(values[i])),
                below_half_share=float((values[i] < 0.5).mean()),
                smallest_factor_share=float((least == i).mean()),
                recall_if_factor_removed=float((relaxed_pred == cid).mean()))
        codes, counts = np.unique(local_kop, return_counts=True)
        zones[key] = dict(
            rule=RULES[key], cells=n, membership_mean=float(scores.mean()),
            all_factor_strengths_at_least_half_share=float((values >= 0.5).all(0).mean()),
            membership_at_least_half_share=float((scores >= 0.5).mean()),
            strict_recall=float(correct.mean()), display_recall=float((displayed[own] == cid).mean()),
            failure_partition=dict(correct=float(correct.mean()),
                                   incompatible_koppen=float((~allowed).mean()),
                                   eligible_but_membership_below_threshold=float(weak.mean()),
                                   eligible_but_other_label_wins=float(lost.mean())),
            strict_labels={k: float((pred[own] == i).mean()) for i, k in enumerate(keys)},
            display_labels={k: float((displayed[own] == i).mean()) for i, k in enumerate(display_keys)},
            koppen_share={CODES[int(c)] if c >= 0 else 'unclassified': float(v / n) for c, v in zip(codes, counts)},
            factors=factor_summary,
            climate_quantiles={k: np.percentile(indices[k][own], [10, 50, 90]).tolist()
                               for k in ('MAT', 'Tcold', 'Thot', 'MAP', 'aridity', 'Psdry', 'Pwwet')
                               if indices is not None and k in indices})
    return dict(
        scope='model_grid', quantile_percentiles=[10, 50, 90], zones=zones,
        interpretation='Factors are fuzzy rule strengths, not probabilities. The smallest factor is a diagnostic; ties choose the first factor.',
        counterfactual_note='Removing a factor is an attribution probe on unchanged climate fields, not a physical improvement or a recommendation to loosen rules.')


def analyse_rules(result, evaluation, snapshot=None):
    g, st = result.grid, evaluation['monthly']
    kop = classify(st['Tm'], st['Pm'], st['summer'])
    factors = membership_factors(evaluation['indices'], slope=terrain_slope(g))
    if snapshot is not None:
        # Keep exact cropped fields so later label/rule experiments need no
        # extra climate run. This archive does not replace a simulation cache.
        sl = g.map_slice()
        fields = dict(target=g.target[sl], land=g.land[sl], valid=(g.inmap & g.land)[sl],
                      elev=g.elev[sl], koppen=kop[sl], schema_version=np.array(1),
                      params_json=np.array(json.dumps(asdict(result.params))))
        fields.update({f'index_{key}': value[sl] for key, value in evaluation['indices'].items()})
        fields.update({f'membership_{key}': value[sl] for key, value in evaluation['memberships'].items()})
        fields.update({f'factor_{key}_{name}': np.broadcast_to(value, g.target.shape)[sl]
                       for key, group in factors.items() for name, value in group.items()})
        np.savez_compressed(snapshot, **fields)
    return audit_rules(evaluation['memberships'], factors,
                       kop, g.target, g.inmap & g.land, evaluation['indices'], g.elev)
