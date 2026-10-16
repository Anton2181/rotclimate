"""Fast, offline label-policy probes; never runs a climate simulation.

These deliberately fixed probes diagnose tradeoffs on one saved world. They
are not fitted parameters or evidence of improvement on unseen worlds.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rotclimate.geography import TARGET_CLASSES
from rotclimate.koppen import CODES
from rotclimate.score import ZONE_KOPPEN, best_zone, display_zones


def label_metrics(labels, target, valid):
    painted = valid & (target > 0)
    zones = {}
    for cid, key, _, _ in TARGET_CLASSES:
        own, predicted = painted & (target == cid), painted & (labels == cid)
        tp = int((own & predicted).sum())
        recall = tp / int(own.sum()) if own.any() else None
        precision = tp / int(predicted.sum()) if predicted.any() else 0.0
        zones[key] = dict(recall=recall, precision=precision,
                          f1=2 * tp / (int(own.sum()) + int(predicted.sum()))
                          if own.any() or predicted.any() else None)
    return dict(accuracy=float((labels[painted] == target[painted]).mean()),
                macro_recall=float(np.mean([z['recall'] for z in zones.values()
                                            if z['recall'] is not None])), zones=zones)


def probe_fields(fields):
    target, valid, kop = fields['target'], fields['valid'], fields['koppen']
    mem = {key: fields[f'membership_{key}'] for _, key, _, _ in TARGET_CLASSES}
    ix = {k[6:]: fields[k] for k in fields.files if k.startswith('index_')}
    baseline = best_zone(mem, koppen=kop)
    variants = {'strict_current': baseline,
                'atlas_current': display_zones(mem, valid, ix=ix,
                                               elev=fields['elev'], koppen=kop)}
    # Keep the existing swamp priority and Koppen gates in every probe.
    for weight in (0.9, 0.8, 0.75):
        variants[f'forest_weight_{weight}'] = best_zone(mem, weights={'tree': weight}, koppen=kop)
    allowed = np.array([ZONE_KOPPEN['warm_wet'](c) for c in CODES] + [False])[kop]
    for threshold in (0.5, 0.7, 0.9):
        z = baseline.copy()
        z[allowed & (mem['warm_wet'] >= threshold) & (z != 5)] = 3
        variants[f'warm_wet_priority_{threshold}'] = z
    # Remove a factor everywhere, not just where swamp was painted. This
    # exposes false positives hidden by a recall-only attribution calculation.
    names = [k for k in fields.files if k.startswith('factor_swamp_')]
    for removed in names:
        relaxed = np.prod([fields[k] for k in names if k != removed], axis=0)
        variants[f'probe_remove_{removed}'] = best_zone({**mem, 'swamp': relaxed}, koppen=kop)
    return dict(scope='one_saved_model_grid',
                note='Diagnostic counterfactuals only. No climate fields, production rules or atlas labels changed. Precision is exclusive-label precision on painted land, unlike the fuzzy hierarchical calibration score.',
                variants={name: label_metrics(z, target, valid) for name, z in variants.items()})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fields', type=Path, default=Path('output/rule_fields.npz'))
    ap.add_argument('--out', type=Path, default=Path('output/rule_policy_probes.json'))
    a = ap.parse_args()
    with np.load(a.fields, allow_pickle=False) as fields:
        report = probe_fields(fields)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + '\n')
    for name, row in report['variants'].items():
        print(f"{name:45s} correct {row['accuracy']:.1%}, balanced recall {row['macro_recall']:.1%}")


if __name__ == '__main__':
    main()
