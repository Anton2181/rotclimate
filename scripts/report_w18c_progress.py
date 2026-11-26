"""Snapshot development progress without changing search, selection or gates."""
import csv
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ppe as P
from local_benchmark_protocol import file_hash, write_json

PLAN = ROOT / 'calibration/ppe_20261123/plan_W18c.json'
LIVE = ROOT / 'output/ppe_20261127/W18c/results.jsonl'


def main():
    # Retain a complete append-only prefix; an in-flight partial line is not a result.
    content = LIVE.read_bytes()
    prefix = content[:content.rfind(b'\n') + 1]
    attempted = [json.loads(line) for line in prefix.splitlines()]
    assert attempted and len({r['name'] for r in attempted}) == len(attempted)
    rows = [r for r in attempted if r.get('ok')]
    assert rows
    out = ROOT / f'output/ppe_20261127/W18c_progress_{len(attempted):04d}'
    assert not out.exists(), 'Preserve the completed progress snapshot'
    plan = json.loads(PLAN.read_text())
    names = sorted(rows[0]['regions'])
    assert len(names) == 97
    assert all(sorted(r['regions']) == names for r in rows)
    values = np.array([[r['regions'][n] for n in names] for r in rows])
    assert values.shape == (len(rows), 97, 4) and np.isfinite(values).all()
    reference = values[0, :, 2:]
    for candidate in values:
        np.testing.assert_array_equal(candidate[:, 2:], reference)
    regimes = P.t_names_of(plan)
    assert all(n in regimes for n in names)
    score, temperature, rain, worst = P.gate_terms(values[:, :, :2], reference, names, regimes)
    objective = P.objective(plan, score, temperature, rain, worst)
    best = int(np.argmin(objective))
    y = values[best, :, :2]
    denominators = reference.mean(0)
    contributions = .5 * (y - reference) / denominators / len(names)
    # Independent scalar sum verifies the exact score decomposition, not regional ratios.
    independent = sum(.5 * ((float(y[i, 0]) - float(reference[i, 0])) / float(denominators[0])
                           + (float(y[i, 1]) - float(reference[i, 1])) / float(denominators[1])) / 97
                      for i in range(97))
    np.testing.assert_allclose(independent, float(score[best]) - 1, atol=1e-14, rtol=0)
    np.testing.assert_allclose(contributions.sum(0), [temperature[best] / 2, rain[best] / 2], atol=1e-14, rtol=0)
    groups = {}
    for group in sorted(set(regimes[n] for n in names)):
        ix = [i for i, name in enumerate(names) if regimes[name] == group]
        candidate_mean, ref_mean = y[ix].mean(0), reference[ix].mean(0)
        groups[group] = dict(regions=len(ix), S=float(.5 * np.sum(candidate_mean / ref_mean)),
                             T_ratio=float(candidate_mean[0] / ref_mean[0]), P_loss_ratio=float(candidate_mean[1] / ref_mean[1]))
    np.testing.assert_allclose(max(r['S'] for r in groups.values()), worst[best], atol=1e-14, rtol=0)
    regional = [dict(region=name, regime=regimes[name], ref_temperature_mae_C=float(reference[i, 0]),
        candidate_temperature_mae_C=float(y[i, 0]), ref_rain_loss=float(reference[i, 1]), candidate_rain_loss=float(y[i, 1]),
        temperature_contribution_percentage_points=float(contributions[i, 0] * 100),
        rain_contribution_percentage_points=float(contributions[i, 1] * 100),
        combined_contribution_percentage_points=float(contributions[i].sum() * 100)) for i, name in enumerate(names)]
    ranked = sorted(regional, key=lambda r:r['combined_contribution_percentage_points'])
    out.mkdir(parents=True)
    write_json(out / 'snapshot.json', dict(status='exploratory_development_progress_not_finalist',
        live_results_prefix_sha256=hashlib.sha256(prefix).hexdigest(), completed_records=attempted))
    with (out / 'regions.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(regional[0]))
        writer.writeheader()
        writer.writerows(regional)
    figure(out, rows, score, temperature, rain, worst, best, regional, groups, len(attempted))
    provenance = [PLAN, Path(__file__), ROOT / 'scripts/ppe.py', ROOT / 'scripts/gate_v3.py',
                  ROOT / 'calibration/regimes_20261124/regimes_v2.json', ROOT / 'calibration/ppe_20261123/W18c_runtime_amendment.json',
                  ROOT / 'output/climate_runtime_20261126/qualification.json']
    write_json(out / 'report.json', dict(status='completed_development_progress_snapshot', completed_records=len(attempted),
        successful_records=len(rows), failed_records=[r for r in attempted if not r.get('ok')],
        provisional_leader=rows[best]['name'], selection='Existing penalized development objective ONLY; unchanged',
        S97=float(score[best]), temperature_fractional_change=float(temperature[best]), rain_loss_fractional_change=float(rain[best]),
        worst_regime_S=float(worst[best]), dev_objective=float(objective[best]), knobs=rows[best]['x'],
        regimes=groups, best_six_contributions=ranked[:6], worst_six_contributions=ranked[-6:],
        regions_combined_improved=sum(r['combined_contribution_percentage_points'] < 0 for r in regional),
        regions_combined_worsened=sum(r['combined_contribution_percentage_points'] > 0 for r in regional),
        all_region_contributions_sum_percentage_points=independent * 100,
        sources_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in provenance},
        files_sha256={n:file_hash(out / n) for n in ['snapshot.json', 'regions.csv', 'development_progress.png']},
        full_development_bootstrap_gate_run=False, fine_or_sealed_targets_opened=False,
        search_or_proposal_changed=False, climate_integrations=0, climate_adopted=False,
        interpretation='Equal-region exposed development scores, not planetary area skill, full validation or causal attribution. Contributor rankings do not alter candidate selection.'))
    assert LIVE.read_bytes().startswith(prefix), 'Live result history was rewritten'
    print(json.dumps(dict(folder=str(out.relative_to(ROOT)), leader=rows[best]['name'], S97=float(score[best]),
                          completed=len(attempted), regions_improved=sum(r['combined_contribution_percentage_points'] < 0 for r in regional))))


def figure(out, rows, score, temperature, rain, worst, best, regional, groups, completed):
    fig, axes = plt.subplots(1, 3, figsize=(19, 8))
    coarse_limits = (temperature <= .01) & (rain <= .01) & (worst <= 1.02)
    x = np.arange(len(rows))
    axes[0].scatter(x, score, c=np.where(coarse_limits, '#377d8d', '#b47552'), s=35)
    axes[0].scatter([best], [score[best]], marker='*', s=200, color='#333333', label='Leader by existing objective')
    axes[0].axhline(1, color='#666666', linestyle='--', linewidth=.8, label='r58 reference')
    axes[0].set(xlabel='Successful development record (order)', ylabel='S97: mean normalized development loss',
                title='Point gain still needs full validation')
    axes[0].legend(fontsize=8, loc='upper left')
    axes[0].text(.02, .03, 'Teal: within T/P +1% and regime +2% point limits\nBrown: at least one point limit exceeded',
                 transform=axes[0].transAxes, fontsize=8)
    ranked = sorted(regional, key=lambda r:r['combined_contribution_percentage_points'])
    shown = ranked[:6] + ranked[-6:]
    positions = np.arange(len(shown))
    tt = np.array([r['temperature_contribution_percentage_points'] for r in shown])
    pp = np.array([r['rain_contribution_percentage_points'] for r in shown])
    axes[1].barh(positions, tt, color='#377d8d', label='Temperature MAE')
    axes[1].barh(positions, pp, left=np.where(tt * pp >= 0, tt, 0), color='#b47552', label='Rain loss')
    axes[1].scatter([r['combined_contribution_percentage_points'] for r in shown], positions, color='#333333', s=12, label='Net')
    axes[1].set(yticks=positions, yticklabels=[r['region'] for r in shown],
                xlabel='Contribution to S97 change (percentage points)', title='Largest gains and regressions')
    axes[1].invert_yaxis()
    axes[1].axvline(0, color='#666666', linewidth=.7)
    axes[1].legend(fontsize=8, loc='lower left')
    labels = list(groups)
    yy = np.arange(len(labels))
    axes[2].scatter([groups[g]['S'] for g in labels], yy, color='#377d8d')
    axes[2].axvline(1, color='#777777', linewidth=.7, label='r58')
    axes[2].axvline(1.02, color='#b47552', linestyle='--', linewidth=.9, label='Existing regime point limit')
    axes[2].set(yticks=yy, yticklabels=labels, xlabel='Regime S ratio', title='Group averages can hide local losses')
    axes[2].legend(fontsize=8, loc='lower left')
    for ax in axes:
        ax.grid(alpha=.12)
        ax.set_axisbelow(True)
    fig.suptitle(f'W18c provisional leader {rows[best]["name"]} · {completed}/49 initial records complete', fontsize=16)
    fig.text(.5, .04, 'Development-only snapshot; no finalist, bootstrap gate, fine or sealed evaluation. Equal region weighting, not global area coverage.\n'
             'Negative contributions improve S97. Existing objective and all search/gate rules remain unchanged; no climate adoption.',
             ha='center', fontsize=10)
    fig.subplots_adjust(left=.055, right=.985, top=.86, bottom=.17, wspace=.65)
    fig.savefig(out / 'development_progress.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
