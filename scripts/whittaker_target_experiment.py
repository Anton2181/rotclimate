"""Audit saved atlas climates or compare a biome-target pilot on a finer grid."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from rotclimate import biome_targets as B, biomes
from rotclimate.config import Params
from rotclimate.geography import TARGET_CLASSES


def metrics(result):
    from rotclimate.score import evaluate, objective
    from rotclimate.calibrate import mediterranean_shares
    ev = evaluate(result)
    g = result.grid
    valid = g.inmap & g.land
    codes = biomes.classify(ev['indices']['MAT'], ev['indices']['MAP'])
    confusion = []
    for cid, *_ in TARGET_CLASSES:
        confusion.append(np.bincount(codes[valid & (g.target == cid)], minlength=10).tolist())
    climates = {}
    for cid, key, *_ in TARGET_CLASSES:
        mask = valid & (g.target == cid)
        climates[key] = {name: float(np.median(ev['indices'][name][mask])) for name in ('MAT', 'MAP')}
    return dict(strict=B.evaluate(ev['indices'], g.target, valid),
                broad=B.evaluate(ev['indices'], g.target, valid, 'broad'),
                zonefit=objective(ev, 'zonefit'), zone_accuracy=ev['accuracy'],
                zone_recall=ev['recall'], mediterranean=mediterranean_shares(result, ev),
                zone_memberships=ev['per_class'], realism=ev['realism'], confusion=confusion,
                target_climate_medians=climates)


def plot_alignment(rows, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, axes = plt.subplots(1, len(rows), figsize=(8 * len(rows), 6), layout='constrained', squeeze=False)
    labels = ['Outside', 'Trop. seasonal', 'Subtrop. desert', 'Temp. rainforest', 'Trop. rainforest',
              'Woodland / shrub', 'Tundra', 'Boreal forest', 'Temp. grass/desert', 'Temp. seasonal']
    mapping = B.specification()['profiles']['strict']
    for ax, (name, row) in zip(axes[0], rows.items()):
        conf = np.asarray(row['confusion'], float)
        share = conf / np.maximum(conf.sum(1, keepdims=True), 1)
        im = ax.imshow(share, vmin=0, vmax=1, cmap='YlGnBu', aspect='auto')
        for i, (_, key, _, _) in enumerate(TARGET_CLASSES):
            for j in mapping[key]:ax.add_patch(Rectangle((j-.48, i-.48), .96, .96, fill=False, ec='black', lw=2))
            for j, v in enumerate(share[i]):
                if v >= .005:ax.text(j, i, f'{v:.0%}', ha='center', va='center', fontsize=8,
                                     color='white' if v > .5 else 'black')
        ax.set(xticks=range(10), xticklabels=labels, yticks=range(7),
               yticklabels=[c[2] for c in TARGET_CLASSES],
               title=f'{name} | macro biome match {row["strict"]["macro_hard"]:.1%}')
        ax.tick_params(axis='x', rotation=65)
    fig.colorbar(im, ax=list(axes[0]), label='Fraction of each painted target zone', shrink=.7)
    fig.suptitle('Current climates against the proposed Whittaker targets · boxes = allowed strict biome')
    fig.savefig(out, dpi=150);plt.close(fig)


def baseline(out):
    rows = {}
    for name in ['free', 'earth']:
        file = ROOT / f'output/autonomous_20261021/{name}_atlas_result.pkl'
        with file.open('rb') as f:cache = pickle.load(f)  # trusted locally generated climate fields
        rows[name] = metrics(cache['result'])
        rows[name]['field_provenance'] = cache['identity']
        print(name, 'strict', rows[name]['strict']['score'], 'broad', rows[name]['broad']['score'], flush=True)
    (out / 'baseline.json').write_text(json.dumps(rows, indent=2) + '\n')
    plot_alignment(rows, out / 'baseline_alignment.png')
    from rotclimate.geography import source_layers, target_fullres
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    target = target_fullres();land = source_layers()['land']
    mapped = np.where(land, 0, 255).astype(np.uint8)
    for cid, key, *_ in TARGET_CLASSES:mapped[land & (target == cid)] = B.specification()['profiles']['strict'][key][0]
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.imshow(biomes.rgb_image(mapped));ax.axis('off')
    ax.set_title('Proposed Whittaker targets · strict crosswalk (hypothesis)', loc='left')
    handles = [Patch(facecolor=biomes.COLORS[B.specification()['profiles']['strict'][key][0]],
                     label=f'{label} → {biomes.LABELS[B.specification()["profiles"]["strict"][key][0]]}')
               for _, key, label, _ in TARGET_CLASSES]
    fig.legend(handles=handles, loc='lower center', ncol=2, fontsize=9, frameon=False)
    fig.subplots_adjust(left=.01, right=.99, top=.94, bottom=.2)
    fig.savefig(out / 'proposed_target_biomes.png', dpi=150);plt.close(fig)


def review_one(job):
    name, param_path, ds, seed, destination = job
    from rotclimate.model import ClimateModel
    p = Params.from_json(param_path).replace(downsample=ds, beyond_seed=seed)
    identity = dict(params=json.loads(json.dumps(asdict(p))), sources={
        str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()
        for f in [*(ROOT / 'rotclimate').glob('*.py'), ROOT / 'data/biome_target_crosswalk.json']})
    checkpoint = Path(destination) / 'checkpoints' / f'{name}_ds{ds}_layout{seed}.pkl'
    try:
        if checkpoint.exists():
            with checkpoint.open('rb') as f:cache = pickle.load(f)
            if cache['identity'] != identity:raise ValueError('Review cache inputs changed')
            result = cache['result']
        else:
            result = ClimateModel(p).run()
            checkpoint.parent.mkdir(exist_ok=True)
            with checkpoint.with_suffix('.tmp').open('wb') as f:pickle.dump(dict(identity=identity, result=result), f)
            checkpoint.with_suffix('.tmp').replace(checkpoint)
        return dict(name=name, downsample=ds, layout=seed, status='complete', **metrics(result))
    except Exception as exc:
        return dict(name=name, downsample=ds, layout=seed, status='failed', error=repr(exc))


def review(args, out):
    search_summary(args.calibration, out)
    jobs = [(name, str(path), args.downsample, seed, str(out))
            for name, path in [('baseline', args.baseline_params), ('candidate', args.candidate)] for seed in [1, 2]]
    rows = []
    with mp.get_context('spawn').Pool(args.workers) as pool:
        for row in pool.imap_unordered(review_one, jobs, chunksize=1):
            rows.append(row)
            (out / f'review_{row["name"]}_layout{row["layout"]}.json').write_text(json.dumps(row, indent=2) + '\n')
            print(row['name'], 'layout', row['layout'], row['status'],
                  row.get('strict', {}).get('score', row.get('error')), flush=True)
    (out / 'review.json').write_text(json.dumps(rows, indent=2) + '\n')
    if not summarize_review(out, args.downsample):
        raise SystemExit('A finer-grid comparison failed; inspect review.json and review_summary.json')


def summarize_review(out, ds):
    rows = json.loads((out / 'review.json').read_text())
    paired = [seed for seed in [1, 2]
              if all(any(r['name'] == name and r['layout'] == seed and r['status'] == 'complete'
                         for r in rows) for name in ['baseline', 'candidate'])]
    audits = {str(seed):zone_guards(next(r for r in rows if r['name'] == 'candidate' and r['layout'] == seed),
                                   next(r for r in rows if r['name'] == 'baseline' and r['layout'] == seed))
              for seed in paired}
    (out / 'review_guard_audit.json').write_text(json.dumps(audits, indent=2) + '\n')
    failed = [dict(name=r['name'], layout=r['layout'], error=r.get('error'))
              for r in rows if r['status'] != 'complete']
    summary = dict(status='complete' if not failed else 'partial', paired_layouts=paired,
                   failed_cases=failed, downsample=ds)
    (out / 'review_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    if 1 in paired:plot_review(rows, ds, out)
    return not failed


def zone_guards(candidate, reference):
    """The existing five seasonal-zone guard limits, evaluated as hard checks."""
    ca = candidate.get('zone_accuracy', candidate.get('accuracy'))
    ra = reference.get('zone_accuracy', reference.get('accuracy'))
    cr = candidate.get('zone_recall', candidate.get('recall'))
    rr = reference.get('zone_recall', reference.get('recall'))
    cm, rm = candidate['mediterranean'], reference['mediterranean']
    checks = dict(overall=ca >= ra-.01, cold_dry=cr['cold_dry'] >= rr['cold_dry']-.02,
                  hot_dry=cr['hot_dry'] >= rr['hot_dry']-.03,
                  med_dry=cm['dry_share'] <= max(rm['dry_share'], .05),
                  med_cs=cm['cs_share'] >= rm['cs_share']-.02)
    return dict(passed=all(checks.values()), checks=checks)


def search_summary(folder, out):
    rows = [json.loads(s) for s in (folder / 'evals.jsonl').read_text().splitlines()]
    good = [r for r in rows if not r.get('error') and not r.get('raced')]
    best = max(good, key=lambda r:r['score'])
    summary = dict(evaluations=len(rows), failures=sum(bool(r.get('error')) for r in rows),
                   initial=rows[0], best=best,
                   guard_audit=dict(passing_evaluations=[r['eval'] for r in good if zone_guards(r, rows[0])['passed']],
                                    best=zone_guards(best, rows[0])))
    (out / 'search_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 6), layout='constrained')
    points = ax.scatter([r['score'] for r in good], [r['zonefit_score'] for r in good],
                        c=[r['eval'] for r in good], cmap='viridis', s=25, alpha=.7)
    fig.colorbar(points, ax=ax, label='Evaluation number')
    for row, label, marker, color in [(rows[0], 'Starting fit', '*', '#a63535'),
                                      (best, 'Selected biome fit', 'D', '#172430')]:
        ax.scatter(row['score'], row['zonefit_score'], marker=marker, c=color, s=130, label=label)
    ax.set(xlabel='Whittaker-target objective (strict profile)', ylabel='Original zone-fit objective',
           title='Annual-biome calibration tradeoff · same grid and layout')
    ax.legend();fig.savefig(out / 'search_tradeoff.png', dpi=150);plt.close(fig)


def plot_review(rows, ds, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from rotclimate.koppen import climate_indices, monthly_stats
    panels = []
    for name in ['baseline', 'candidate']:
        with (out / 'checkpoints' / f'{name}_ds{ds}_layout1.pkl').open('rb') as f:r = pickle.load(f)['result']
        st = monthly_stats(r.T, r.P, r.days, r.params.year_days,
                           summer_solstice=r.params.winter_solstice_day + r.params.year_days / 2)
        ix = climate_indices(st['Tm'], st['Pm'], st['summer'])
        sl = r.grid.map_slice();land = r.grid.land[sl]
        if not panels:
            mapped = np.where(land, 0, 255).astype(np.uint8)
            for cid, key, *_ in TARGET_CLASSES:
                mapped[land & (r.grid.target[sl] == cid)] = B.specification()['profiles']['strict'][key][0]
            panels.append(('Proposed biome targets', mapped))
        metric = next(row for row in rows if row['name'] == name and row['layout'] == 1)
        panels.append((f'{name.title()} · biome match {metric["strict"]["macro_hard"]:.1%}',
                       biomes.classify(ix['MAT'][sl], ix['MAP'][sl], land)))
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    for ax, (label, codes) in zip(axes, panels):
        ax.imshow(biomes.rgb_image(codes), interpolation='nearest');ax.axis('off');ax.set_title(label, loc='left')
    handles = [Patch(facecolor=color, label=label) for color, label in zip(biomes.COLORS, biomes.LABELS)]
    fig.legend(handles=handles, loc='lower center', ncol=5, fontsize=9, frameon=False, bbox_to_anchor=(.5, .05))
    fig.suptitle(f'Whittaker-target calibration pilot · downsample {ds} · fitted layout 1', fontsize=18)
    fig.text(.5, .015, 'Grey means unpainted land on the proposed target, or outside the diagram on simulated maps. Annual-climate potential; seasonal audits are separate.',
             ha='center', fontsize=9)
    fig.text(.5, .035, 'Experimental scores remain provisional; the layout-2 baseline failed convergence.',
             ha='center', fontsize=9, color='#8c4533')
    fig.subplots_adjust(left=.01, right=.99, top=.88, bottom=.25, wspace=.03)
    fig.savefig(out / 'pilot_biomes.png', dpi=150);plt.close(fig)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage', choices=['baseline', 'review', 'summary', 'review-summary'])
    ap.add_argument('--out', type=Path, default=ROOT / 'output/whittaker_targets_20261022')
    ap.add_argument('--baseline-params', type=Path, default=ROOT / 'calibration/autonomous_20261021/free_polish/best_params.json')
    ap.add_argument('--candidate', type=Path, default=ROOT / 'calibration/whittaker_20261022/free/best_params.json')
    ap.add_argument('--downsample', type=int, default=16)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--calibration', type=Path, default=ROOT / 'calibration/whittaker_20261022/free')
    args = ap.parse_args();args.out.mkdir(parents=True, exist_ok=True)
    if args.stage == 'baseline':baseline(args.out)
    elif args.stage == 'summary':search_summary(args.calibration, args.out)
    elif args.stage == 'review-summary':summarize_review(args.out, args.downsample)
    else:review(args, args.out)
