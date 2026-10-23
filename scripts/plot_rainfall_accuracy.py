"""Plot local annual rainfall errors and city-cell samples from saved comparisons."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--review', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    sources = sorted((a.baseline/'cases').glob('baseline_*.json'))
    baseline = {d['region']:d for d in (json.loads(p.read_text()) for p in sources)}
    candidate = None
    if a.review:
        review = json.loads(a.review.read_text()); candidate = review['candidate']
        if set(baseline) != set(candidate): raise ValueError('Unpaired plot regions')
        sources.append(a.review)
    if not baseline or any(d.get('status') != 'passed' for d in baseline.values()):
        raise ValueError('Missing or failed baseline')
    names = sorted(baseline)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = ['#226b91', '#d97931']
    fig, axs = plt.subplots(1, 3, figsize=(15, 8.7), gridspec_kw={'width_ratios':[1, 1, 1.2]})
    rows = []
    y = np.arange(len(names))
    for i, (label, data) in enumerate([('Published baseline', baseline)] + ([('Rainfall candidate', candidate)] if candidate else [])):
        width = .36 if candidate else .62
        yy = y + ((i-.5)*width if candidate else 0)
        fractions = [100*data[n]['rainfall']['annual_within_25pct'] for n in names]
        biases = [100*(data[n]['rainfall']['sim_mean_annual_mm']/data[n]['rainfall']['obs_mean_annual_mm']-1) for n in names]
        axs[0].barh(yy, fractions, height=width, color=colors[i], label=label)
        axs[1].barh(yy, biases, height=width, color=colors[i])
        for name, fraction, bias in zip(names, fractions, biases):
            r = data[name]['rainfall']; rows.append(dict(fit=label, region=name,
                annual_within_25pct=fraction/100, annual_bias_percent=bias,
                monthly_mae_mm=r['monthly_mae_mm'], annual_mae_mm=r['annual_mae_mm'], loss=r['loss']))
        observed, simulated = [], []
        for region in names:
            for city in data[region]['stations'].values():
                o, s = sum(city['obs_P']), sum(city['sim_P'])
                if o > 0 and s > 0: observed.append(o); simulated.append(s)
        axs[2].scatter(observed, simulated, s=22, alpha=.65, color=colors[i], label=f'{label} ({len(observed)} samples)')
    for ax in axs[:2]:
        ax.set_yticks(y, [n.replace('_', ' ').title() for n in names] if ax is axs[0] else [])
        ax.invert_yaxis(); ax.grid(axis='x', alpha=.18); ax.set_axisbelow(True)
    axs[0].set_xlim(0, 100); axs[0].set_xlabel('Scored locations within ±25% (%)')
    axs[0].set_title('Local annual accuracy', fontsize=12); axs[0].legend(loc='lower right', fontsize=8)
    axs[1].axvline(0, color='#444444', lw=.8)
    axs[1].set_xlabel('Regional annual mean bias (%)')
    axs[1].set_title('Regional totals can hide local errors', fontsize=11)
    limits = [max(5, min(observed)*.6), max(max(observed), max(simulated))*1.4]
    vals = np.geomspace(*limits, 200)
    axs[2].fill_between(vals, vals*.75, vals*1.25, color='#999999', alpha=.15, label='±25% of observed')
    axs[2].plot(vals, vals, color='#555555', lw=1)
    axs[2].set_xscale('log'); axs[2].set_yscale('log')
    axs[2].set_xlim(limits); axs[2].set_ylim(limits); axs[2].set_aspect('equal', adjustable='box')
    axs[2].set_xlabel('Observed annual rain (mm)'); axs[2].set_ylabel('Simulated annual rain (mm)')
    axs[2].set_title('Named city grid cells', fontsize=12); axs[2].legend(fontsize=7, loc='upper left')
    axs[2].grid(alpha=.15)
    wet = sum(r['rainfall']['wet_scored_cells'] for r in baseline.values())
    fraction = sum(r['rainfall']['annual_within_25pct']*r['rainfall']['wet_scored_cells'] for r in baseline.values())/wet
    mae = np.mean([r['rainfall']['monthly_mae_mm'] for r in baseline.values()])
    title = 'Rainfall accuracy: paired candidate comparison' if candidate else 'Rainfall accuracy: published Earth physics'
    fig.suptitle(title, fontsize=17, x=.51, y=.97)
    fig.text(.51, .925, f'WorldClim 2.1 monthly normals (1970–2000) · 56 km cells · {len(names)} reused development regions', ha='center', fontsize=10)
    fig.text(.03, .045, f'Baseline: {fraction:.1%} of {wet:,} eligible land cells within ±25% annually; equal-region monthly MAE {mae:.1f} mm.\n'
             'Annual percentages exclude observed totals below 50 mm/year. City samples use containing cells and are not station observations or independent validation.', fontsize=9)
    fig.subplots_adjust(left=.145, right=.975, top=.87, bottom=.14, wspace=.29)
    a.out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(a.out, dpi=145); plt.close(fig)
    with a.out.with_suffix('.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
    a.out.with_suffix('.json').write_text(json.dumps(dict(
        sources_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        image_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest()), indent=2)+'\n')
    print(a.out)


if __name__ == '__main__': main()
