"""Publish an honest saved snapshot of the joint refit in the local atlas hub."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from local_benchmark_protocol import write_json
from report_joint_ocean_land_refit import SOURCE, LABELS, COLORS, eligible, summarize, plot
from organize_climate_accuracy import organize

DATA = ROOT/'atlases/climate_accuracy/data'
REPORT = ROOT/'reports/JOINT_OCEAN_LAND_20261110.md'


def marine_metrics(summary):
    import numpy as np
    rows = summary['rows']
    configs = list(dict.fromkeys(r['config'] for r in rows))
    reference = {r['region']: r for r in rows if r['config'] == 'r44'}
    metrics = {}
    for config in configs:
        selected = [r for r in rows if r['config'] == config]
        if len(selected) != 6 or {r['region'] for r in selected} != set(reference):
            raise ValueError('Incomplete marine diagnosis: '+config)
        for row in selected:
            if not row['numerics']['all_checks_passed'] or row['case_sha256'] != reference[row['region']]['case_sha256']:
                raise ValueError('Unverified or unmatched marine run')
        metrics[config] = dict(
            sst_curve_mae_c=float(np.mean([np.abs(np.asarray(r['monthly']['surface_c'])-
                r['monthly']['woa_surface_c']).mean() for r in selected])),
            air_curve_mae_c=float(np.mean([np.abs(np.asarray(r['monthly']['air_c'])-
                r['monthly']['ncep_air_c']).mean() for r in selected])))
    return metrics


def marine_plot(metrics, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    names = ['r44', *LABELS]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), layout='constrained', sharey=True)
    for ax, key, title in zip(axes, ['sst_curve_mae_c', 'air_curve_mae_c'],
                            ['Sea temperature vs WOA18', 'Coastal air vs NCEP sigma0.995']):
        for i, name in enumerate(names):
            value = metrics[name][key]
            ax.scatter(value, i, color=COLORS.get(name, '#555'), s=70)
            ax.annotate(f'{value:.3f}', (value, i), xytext=(8, 3), textcoords='offset points', fontsize=9)
        ax.axvline(metrics['r44'][key], color='#888', lw=1, ls='--')
        ax.set(title=title, xlabel='Monthly regional-mean curve MAE · °C (lower is better)')
        ax.grid(axis='x', alpha=.2); ax.margins(x=.25)
    axes[0].set_yticks(np.arange(4), ['r44 reference', *[LABELS[n]+' · best' for n in LABELS]])
    axes[0].invert_yaxis()
    fig.suptitle('Six known coasts · all three cost-best profiles · separate observational references', fontsize=11)
    fig.supxlabel('Different reference periods; these are diagnostic curve errors, not observed heat fluxes.', fontsize=9)
    fig.savefig(path, dpi=150); plt.close(fig)


def main():
    result = summarize()
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    follow_path = SOURCE/'followup/summary.json'
    follow = json.loads(follow_path.read_text()) if follow_path.exists() else None
    complete = (result['status'] == 'completed_development_search' and follow is not None and
                follow['status'] == 'completed_development_followup')
    result['snapshot_utc'] = stamp
    result['followup'] = follow
    plot(result, DATA/'joint_refit_progress.png')
    write_json(DATA/'joint_refit_progress.json', result)
    write_json(SOURCE/'progress.json', result)
    links = []
    for name, chain in result['starts'].items():
        # Export precisely the parsed records, never a concurrently appended half-line.
        filename = 'joint_refit_'+name+'.jsonl'
        (DATA/filename).write_text(''.join(json.dumps(r, allow_nan=False)+'\n' for r in chain['records']))
        links.append(f'<a href="data/{filename}" download>{LABELS[name]} trials</a>')
    rows=[]; report_rows=[]
    for name, chain in result['starts'].items():
        best = chain['best']
        label = LABELS[name]
        if best is None or 'S' not in best:
            rows.append(f'<tr><th>{label}</th><td>{chain["evaluations"]}/17</td><td colspan="5">Pending valid result</td></tr>')
            continue
        passes = 'Clears development screen' if eligible(best) else 'Does not clear development screen'
        rows.append(f'<tr><th>{label}</th><td>{chain["evaluations"]}/17</td><td>{best["T"]:.3f}</td>'
                    f'<td>{best["P"]:.5f}</td><td>{best["S"]:.4f}</td><td>{best["cost"]:.4f}</td><td>{passes}</td></tr>')
        report_rows.append(f'| {label} | {chain["evaluations"]}/17 | {best["T"]:.6f} | {best["P"]:.6f} | '
                           f'{best["S"]:.6f} | {best["cost"]:.6f} | {passes} |')
    state = 'Completed search and development checks' if complete else (
        'Search complete; follow-up checks pending' if result['status'].startswith('completed') else 'Calibration in progress')
    status_text = (f'{result["completed_evaluations"]}/51 evaluations complete in this saved snapshot ({stamp}). '
                   'Refresh from Git for a later published snapshot. The chart does not stream a local running optimizer.')
    section = f'''<section id="joint-refit-status"><h2>{state}: joint ocean/land response</h2>
<p>{status_text} Each of three starts receives 17 evaluations: its starting control and two CMA generations of eight candidates. No start is dropped for an early bad score.</p>
<figure><img src="data/joint_refit_progress.png" alt="All completed trials, best cost per start, and aggregate temperature versus rainfall changes"><figcaption>r44, warmer-sea and warmer-sea/C3 starts vary six shared response parameters. Earth forcing, geography, modeled SST/winds and numerical criteria stay fixed. The search cost adds aggregate component penalties to S49; group scores never veto a trial. Two generations cannot establish convergence or a global optimum.</figcaption></figure>
<div class="table"><table><thead><tr><th>Start</th><th>Completed</th><th>T MAE, °C</th><th>Rain loss</th><th>S49</th><th>Cost</th><th>Best-profile status</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>Fresh r44 reference: T MAE {result['reference']['T_mae_c']:.6f} °C; rain loss {result['reference']['P_loss']:.6f}. These are matched current inputs. Tripolitania uses the documented recovered 182-cell footprint, while 48 regions reproduce the historical r44 error pairs. All 49 are development regions; no new independent pool has been opened.</p>'''
    marine = None
    if follow is not None:
        marine = json.loads((ROOT/follow['marine_summary']).read_text())
        metrics = marine_metrics(marine)
        write_json(DATA/'joint_refit_marine.json', dict(metrics=metrics, runs=marine, independent_validation=False))
        marine_plot(metrics, DATA/'joint_refit_marine.png')
        section += '''<figure><img src="data/joint_refit_marine.png" alt="Marine SST and air errors for all three best profiles against r44"><figcaption>Each cost-best profile is compared with a fresh r44 run on six known coasts. SST and air reference periods differ; no observed heat-flux inference or resolved ocean budget is claimed.</figcaption></figure><p><a href="data/joint_refit_marine.json" download>Marine diagnostics and individual runs</a></p>'''
        if follow['checks']:
            check_rows=[]
            for name, checks in follow['checks'].items():
                check_rows.append(f'<tr><th>{LABELS[name]}</th><td>{checks["dev49"]["S"]:.5f}</td>'
                                  f'<td>{checks["fine28"]["S"]:.5f}</td><td>{checks["spent_h"]["S"]:.5f}</td></tr>')
            section += '<div class="table"><table><thead><tr><th>Cost-best profile</th><th>Fresh S49</th><th>Paired S28</th><th>Spent-h stress S</th></tr></thead><tbody>'+''.join(check_rows)+'</tbody></table></div><p>The h regions were already evaluated; their scores are stress checks, never new independent validation.</p>'
        else:
            section += '<p>No cost-best profile cleared the development screen, so no finalist advanced to additional 28-km or spent-h checks.</p>'
    section += f'''<p><strong>r44/v2.2 remains adopted.</strong> This campaign cannot replace the physical atlas or retrain its correction models automatically.</p>
<p><a href="data/joint_refit_progress.json" download>Snapshot and all regional trial scores</a> · {' · '.join(links)} · <a href="../../reports/JOINT_OCEAN_LAND_20261110.md">Methods, input reconstruction and limits</a></p></section>'''
    page=ROOT/'atlases/climate_accuracy/index.html';html=page.read_text()
    for key in ('joint-refit-running', 'joint-ocean-land'):
        html=re.sub(f'<!--{key}-start-->[\\s\\S]*?<!--{key}-end-->', '', html)
    key='joint-ocean-land' if complete else 'joint-refit-running'
    wrapped=f'<!--{key}-start-->{section}<!--{key}-end-->'
    if complete:
        html=html.replace('</main>',wrapped+'\n</main>')
    else:
        html=html.replace('<!--research-list-start-->',wrapped+'\n<!--research-list-start-->')
    html,_=organize(html)
    if organize(html)[0] != html:
        raise ValueError('Research organizer is not idempotent')
    page.write_text(html)
    REPORT.write_text(f'''# Joint ocean/land response refit — 10 November 2026

**{state}. Saved {stamp}; {result['completed_evaluations']}/51 evaluations. r44 remains adopted.**

Three frozen starts receive equal budgets of one starting control plus two CMA generations of eight:
r44, a +1.5 K SST-offset/-1.5 K current-strength start, and the same warmer sea with previously rejected
C3 exchange. The searched shared parameters are SST offset/current strength and land equilibrium offset,
seasonal amplitude, thermal time and radiative time. Earth orbital/radiative forcing, regional geography,
modeled SST/winds and numerical acceptance criteria stay fixed. These are existing phenomenological
responses, not a resolved coupled ocean energy budget. The regional monsoon-descent driver remains
conditional on existing observed large-scale rainfall information.

The existing v3 objective gives equal weight to normalized aggregate temperature MAE and rainfall loss
over all 49 development regions. Only aggregate component penalties affect the optimizer; groups are
reported without vetoes. Cost-best profiles must meet S49 <= 0.995 and both aggregate component changes
<= +1% before the declared additional checks. Numerical failures remain in the trial logs at cost 99.

| Start | Evaluations | Best T MAE, °C | Best rain loss | S49 | Search cost | Development screen |
|---|---:|---:|---:|---:|---:|---|
{chr(10).join(report_rows)}

![Every completed trial](../atlases/climate_accuracy/data/joint_refit_progress.png)

The baseline is freshly paired: T MAE {result['reference']['T_mae_c']:.12f} °C, rainfall loss
{result['reference']['P_loss']:.12f}. Forty-eight regional pairs reproduce the historical r44 scores.
Tripolitania uses the recovered 182-cell footprint documented on 2 November, instead of the archived
195-cell footprint. A direct WorldClim rebuild exactly reproduces the current cached land fraction,
elevation and climate fields. The original historical scores are retained, not rewritten. The fresh
reference prevents an input-footprint change from becoming a free model gain.

The frozen campaign and starts are in `calibration/joint_ocean_land_20261110/`. Search inputs, code,
policy and software versions are hashed. Actual per-case inputs are checked against reference hashes
before every scored solve. NumPy random state is restored across staged resumes; the generation-boundary
resume test reproduces uninterrupted trial records exactly. Output receipts are under
`output/joint_ocean_land_20261110/`. The public JSON contains every completed trial and regional error pair.

All three cost-best profiles receive the same six-coast marine diagnosis. Qualifiers receive fresh paired
49-region replay, four-region 28-km checks and all spent-h regions as stress. No alternative finalist is
substituted after those results. h/f/g remain spent; this campaign opens no independent pool and adopts
no new physics. A later qualified replacement would require a separately declared independent milestone
before retraining corrections and rebuilding the physical atlas.

This is an early bounded multistart refit, not a convergence test or a global-optimum proof. Different seeds
and starting profiles compare attainable candidates under equal budgets; they cannot isolate starting-point
effects from random-seed effects. Agreement within two generations cannot exclude other basins. C3 is also
a distinct fixed exchange branch rather than a continuous variable of the same search.
''')
    if marine is not None:
        with REPORT.open('a') as stream:
            stream.write('\n![Separate sea and air diagnostics](../atlases/climate_accuracy/data/joint_refit_marine.png)\n\n')
            stream.write('Final follow-up measurements (h is spent, not independent):\n\n```json\n'+
                         json.dumps(follow['checks'], indent=2)+'\n```\n')
    register=ROOT/'calibration/earth_components_20261105/dataset_usage.json'
    exposure=json.loads(register.read_text());exposure['date']='2026-11-10'
    entry=dict(id='joint_ocean_land_refit_p8d',status='development_and_spent_diagnostics',
        evidence='reports/JOINT_OCEAN_LAND_20261110.md',
        note='49 development regions fitted from three starts. Six known coasts diagnosed; h/f/g remain spent. '
             'Any finer-grid and h follow-up is development/stress, not independent validation. No new adoption.')
    exposure['datasets']=[r for r in exposure['datasets'] if r['id']!=entry['id']]+[entry]
    write_json(register,exposure)
    (ROOT/'atlases/earth_evidence/data/dataset_usage.json').write_bytes(register.read_bytes())
    print(state, result['completed_evaluations'], 'of 51; snapshot', stamp)


if __name__ == '__main__':
    main()
