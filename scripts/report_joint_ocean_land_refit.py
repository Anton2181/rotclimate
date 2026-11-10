"""Read-only progress and final diagnostics for the frozen joint-response search.

This does not change an optimizer, select new starts, or adopt model parameters.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, write_json

SOURCE = ROOT / 'output/joint_ocean_land_20261110'
CAMPAIGN = ROOT / 'calibration/joint_ocean_land_20261110/campaign.json'
LABELS = {'r44_start': 'r44 start', 'warm_start': 'Warmer-sea start',
          'warm_C3_start': 'Warmer-sea + C3 start'}
COLORS = {'r44_start': '#25678d', 'warm_start': '#39865d', 'warm_C3_start': '#c36a34'}


def read_records(path):
    """Ignore only an unfinished final write; reject gaps or malformed full lines."""
    if not path.exists():
        return []
    payload = path.read_text()
    lines = payload.splitlines(keepends=True)
    records = []
    for i, line in enumerate(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            if i == len(lines) - 1 and not line.endswith('\n'):
                break
            raise
        if row['n'] != len(records):
            raise ValueError(f'Nonsequential evaluation index in {path}: {row["n"]}')
        records.append(row)
    return records


def eligible(row):
    return ('S' in row and row['S'] <= .995 and
            row['T_relative'] <= .01 and row['P_relative'] <= .01)


def summarize(source=SOURCE, campaign_path=CAMPAIGN):
    driver_path = source / 'driver_identity.json'
    if driver_path.exists():
        driver = json.loads(driver_path.read_text())
        for filename, digest in driver['inputs_sha256'].items():
            if file_hash(ROOT / filename) != digest:
                raise ValueError('Changed frozen campaign/driver input: ' + filename)
    campaign = json.loads(campaign_path.read_text())
    references = {}
    for name, digest in campaign['reference_sha256'].items():
        path = ROOT / name
        if file_hash(path) != digest:
            raise ValueError('Changed reference: ' + name)
        summary = json.loads(path.read_text())
        if summary.get('complete') is not True:
            raise ValueError('Incomplete reference: ' + name)
        if references.keys() & summary['regions'].keys():
            raise ValueError('Duplicate reference regions')
        for region, row in summary['regions'].items():
            if row['status'] != 'passed' or not row['numerics']['all_checks_passed']:
                raise ValueError('Unverified reference: ' + region)
            references[region] = row
    assert len(references) == 49
    tr = sum(r['temperature']['monthly_mae_C'] for r in references.values()) / 49
    pr = sum(r['rain']['loss'] for r in references.values()) / 49
    chains = {}
    for name in campaign['starts']:
        identity_path = source / name / 'search_identity.json'
        if identity_path.exists():
            identity = json.loads(identity_path.read_text())
            for filename, digest in identity['sources'].items():
                if file_hash(ROOT / filename) != digest:
                    raise ValueError('Changed frozen search source: ' + filename)
        path = source / name / 'evals.jsonl'
        rows = read_records(path)
        if len(rows) > campaign['budget']['per_start']:
            raise ValueError('Budget exceeded: ' + name)
        for row in rows:
            if set(row['regions']) != set(references):
                raise ValueError('Changed evaluation footprint: ' + name)
            if 'S' not in row:
                if row['cost'] != 99 or not row.get('failed'):
                    raise ValueError('Unaccounted failed evaluation')
                continue
            values = list(row['regions'].values())
            if any(v is None or not all(math.isfinite(x) for x in v) for v in values):
                raise ValueError('Invalid scored regional values')
            t, p = (sum(v[i] for v in values) / 49 for i in (0, 1))
            expected = {'T': t, 'P': p, 'S': .5*t/tr + .5*p/pr,
                        'T_relative': t/tr - 1, 'P_relative': p/pr - 1}
            for key, value in expected.items():
                if not math.isclose(row[key], value, rel_tol=0, abs_tol=1e-11):
                    raise ValueError('Score disagrees with regional rows: ' + key)
            if not math.isclose(row['cost'], row['S'] + row['penalty'], abs_tol=1e-11):
                raise ValueError('Cost disagrees with S + penalty')
        best = min(rows, key=lambda r: r['cost']) if rows else None
        chains[name] = dict(evaluations=len(rows), budget=campaign['budget']['per_start'],
            numerical_failures=sum('S' not in r for r in rows),
            eligible_evaluations=[r['n'] for r in rows if eligible(r)], best=best, records=rows,
            records_sha256=file_hash(path) if path.exists() else None)
    complete = all(c['evaluations'] == c['budget'] for c in chains.values())
    if complete:
        # A full JSONL alone must not be mistaken for a clean driver completion.
        status = json.loads((source / 'status.json').read_text())
        complete = status['status'] == 'completed'
    return dict(status='completed_development_search' if complete else 'running',
        campaign_sha256=file_hash(campaign_path),
        completed_evaluations=sum(c['evaluations'] for c in chains.values()),
        planned_evaluations=campaign['budget']['total_evaluations'],
        reference=dict(n_regions=49, T_mae_c=tr, P_loss=pr), starts=chains,
        adopted='r44', independent_validation=False,
        limits='Two CMA generations per start; not convergence or a global-optimum proof. '
               'All 49 regions are development data. Component guards are aggregate only. '
               'Fresh matched references include the recovered 182-cell Tripolitania input.')


def plot(result, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6), layout='constrained')
    left, right = axes
    for name, chain in result['starts'].items():
        rows = chain['records']; good = [r for r in rows if 'S' in r]
        if not rows:
            continue
        color = COLORS[name]
        best = np.minimum.accumulate([r['cost'] for r in rows])
        finite = best < 99
        left.plot(np.arange(1, len(rows)+1)[finite], best[finite], color=color,
                  label=f"{LABELS[name]} ({len(rows)}/17)", lw=2)
        left.scatter([r['n']+1 for r in good], [r['cost'] for r in good],
                     color=color, s=23, alpha=.6)
        if good:
            right.scatter([100*r['T_relative'] for r in good],
                          [100*r['P_relative'] for r in good], color=color, s=25, alpha=.6)
            right.scatter(100*good[0]['T_relative'], 100*good[0]['P_relative'],
                          color=color, s=85, marker='s', edgecolor='white', linewidth=.8)
        best_row = chain['best']
        if best_row and 'S' in best_row:
            right.scatter(100*best_row['T_relative'], 100*best_row['P_relative'],
                          color=color, s=130, marker='*', edgecolor='#222', linewidth=.6)
    left.axhline(1, color='#555', ls='--', lw=1, label='Fresh r44 reference')
    left.set(xlabel='Evaluations per start (including control)',
             ylabel='v3 search cost = S49 + aggregate T/P penalty',
             title='Every completed trial and best cost so far', xlim=(.5, 17.5))
    left.set_xticks([1, 5, 9, 13, 17]); left.legend(fontsize=8, loc='best')
    for axis in (left, right):
        axis.grid(alpha=.18)
    right.axhline(0, color='#888', lw=.8); right.axvline(0, color='#888', lw=.8)
    right.axhline(1, color='#a33', ls=':', lw=1); right.axvline(1, color='#a33', ls=':', lw=1)
    # S49 <= .995 corresponds to T% + P% <= -1; only draw where the
    # aggregate component bounds also permit a candidate.
    x0, x1 = right.get_xlim(); y0, y1 = right.get_ylim()
    right.set_xlim(min(x0, -2), max(x1, 2)); right.set_ylim(min(y0, -2), max(y1, 2))
    x = np.linspace(right.get_xlim()[0], min(1, right.get_xlim()[1]), 100)
    right.plot(x, -1-x, color='#666', ls='--', lw=1, label='S49 = 0.995')
    right.set(xlabel='Aggregate temperature MAE change · %', ylabel='Aggregate rainfall-loss change · %',
              title='Squares: starts · stars: lowest-cost profiles')
    right.legend(fontsize=8, loc='best')
    state = 'complete' if result['status'].startswith('completed') else 'in progress'
    failures = sum(c['numerical_failures'] for c in result['starts'].values())
    fig.suptitle(f"Joint ocean/land refit · {result['completed_evaluations']}/51 evaluations · {state}", fontsize=13)
    fig.supxlabel(f"49 development regions · {failures} failed evaluations · r44 remains adopted\n"
                  "Shared responses with fixed Earth forcing; this budget cannot establish a global minimum.", fontsize=9)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=SOURCE)
    args = ap.parse_args()
    result = summarize()
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / 'progress.json', result)
    plot(result, args.out / 'joint_refit_progress.png')
    print(json.dumps({k: v for k, v in result.items() if k != 'starts'}, indent=2))
    for name, chain in result['starts'].items():
        print(name, chain['evaluations'], 'best', (chain['best'] or {}).get('cost'),
              'eligible indices', chain['eligible_evaluations'])


if __name__ == '__main__':
    main()
