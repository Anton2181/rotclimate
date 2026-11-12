"""Publish all declared grid outcomes,phase/spacing charts and POINT comparisons."""
import gzip
import json
from pathlib import Path
import re
import shutil
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from publish_network_duty_visits import point_image

OUT = ROOT / 'output/network_visit_target_grid_20261112'
PLAN = ROOT / 'calibration/network_visit_target_grid_20261112/plan.json'
DATA = ROOT / 'atlases/earth_fit/data'


def charts(result):
    rows = result['rows']; figures = []
    for kind, designs, xlabel in [('phase', ['b3_p0', 'b3_p1', 'b3_p2'], 'Diagonal phase · cells'),
                                  ('spacing', ['b2_p0', 'b3_p0', 'b5_p0'], 'Nominal target spacing · km')]:
        fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout='constrained')
        for i, mode in enumerate(('raw', 'corrected')):
            for j, crew in enumerate((1, 4)):
                ax = axes[i, j]
                for hours, color in [(600, '#3d7b76'), (300, '#b17b43')]:
                    selected = [next(r for r in rows if r['design'] == design and r['climate'] == mode and r['crew'] == crew and r['hours_worker_year'] == hours) for design in designs]
                    x = [r['row_phase'] if kind == 'phase' else r['actual_spacing_km'] for r in selected]
                    ax.plot(x, [r['completed_fraction'] * 100 for r in selected], marker='o', color=color, label=f'{hours} farm hours')
                    if kind == 'spacing':
                        for xx, r in zip(x, selected): ax.annotate(f'{r["requested_visits"]/1000:.0f}k requests', (xx, r['completed_fraction'] * 100), xytext=(0, 7 if hours == 600 else -13), textcoords='offset points', ha='center', fontsize=7)
                ax.set_title(f'{mode.title()} climate · crew {crew}', fontsize=11); ax.set_ylabel('Completed conditional visits · %'); ax.set_xlabel(xlabel)
                ax.set_xticks(x, [str(v) if kind == 'phase' else f'{v:.2f}' for v in x]); ax.grid(alpha=.18); ax.legend(frameon=False, fontsize=8)
                if kind == 'spacing': ax.margins(x=.16, y=.18)
        fig.suptitle('Fixed ~11 km spacing:phase changes the selected point geography' if kind == 'phase' else 'Spacing changes BOTH supplied task density and selected point geography', fontsize=12)
        fig.supxlabel('All declared cases reported;original assign-once allocator and SAME reserved patrol budgets.\n'
            'Conditional tasks,not observed demand,held territory,global optimality or numerical-convergence qualification.', fontsize=9)
        path = ROOT / f'reports/figures/network_visit_grid_{kind}_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig); figures.append(path)
    meta = json.loads((DATA / 'atlas.json').read_text()); manifest = json.loads((DATA / 'network_duty_visits.json').read_text())
    designs = json.loads(PLAN.read_text())['designs']
    for mode in ('raw', 'corrected'):
        x = dict(np.load(ROOT / f'output/settlement_feedback_20261112/{mode}_inputs.npz'))
        model = json.loads(gzip.decompress((DATA / manifest['packets'][mode]['payload']).read_bytes()))
        fig, axes = plt.subplots(2, 5, figsize=(21, 5.9), layout='constrained')
        for j, design in enumerate(designs):
            ident = design['id']; arrays = dict(np.load(OUT / (ident + '_fields.npz'))); targets = dict(np.load(OUT / mode / ident / 'targets.npz'))
            for i, hours in enumerate((600, 300)):
                key = f'{mode}_h{hours}_crew4'; row = next(r for r in rows if r['design'] == ident and r['key'] == key)
                axes[i, j].imshow(point_image(x, targets, arrays[key + '__served'], model['actors'], meta))
                axes[i, j].set_title(f'{row["actual_spacing_km"]:.2f} km · phase {row["row_phase"]} · {hours}h\n{row["completed_visits"]:,}/{row["requested_visits"]:,} ({row["completed_fraction"]*100:.1f}%)', fontsize=9)
                axes[i, j].set_xticks([]); axes[i, j].set_yticks([])
            del arrays
        fig.suptitle(f'{mode.title()} climate · four-person crews · all five declared target designs', fontsize=13)
        fig.supxlabel('Dots are completed target-point tasks;no surrounding block or intervening land is assigned. Size reflects completed bins;white centres indicate overlapping actors.\n'
            'Top/bottom:600/300 farm hours. Spacing changes supplied workload as well as geography;all budgets and original allocator remain matched.\n'
            'No empirical demand,individual daily roster,political authority or mobile/unaffiliated occupancy qualification.', fontsize=9)
        path = ROOT / f'reports/figures/network_visit_grid_{mode}_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig); figures.append(path)
    return figures


def main():
    result = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text()); replay = json.loads((OUT / 'replay.json').read_text())
    assert review['status'] == replay['status'] == 'passed' and review['results_sha256'] == sha(OUT / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_visit_target_grid.py')
    assert len(result['rows']) == len(review['cases']) == 40
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    for path, digest in replay['byte_exact_files'].items(): assert sha(OUT / path) == digest, path
    figures = charts(result); phase = []
    for mode in ('raw', 'corrected'):
        for hours in (600, 300):
            for crew in (1, 4):
                rows = [r for r in result['rows'] if r['climate'] == mode and r['hours_worker_year'] == hours and r['crew'] == crew and r['block_cells'] == 3]
                values = [r['completed_fraction'] * 100 for r in rows]
                phase.append(dict(climate=mode, hours_worker_year=hours, crew=crew, phase_completion_percent=values,
                    range_percentage_points=max(values) - min(values)))
    write(OUT / 'summary.json', dict(status='forty_cases_reported', phase_comparisons=phase, original_baseline_npz_byte_exact=True,
        all_original_maps_unchanged=True, spacing_changes_supplied_task_density=True))
    assert sha(OUT / 'b3_p0_fields.npz') == sha(ROOT / 'output/network_duty_visits_20261112/fields.npz')
    table = '|Design|Climate|Farm hours|Crew|Targets|Completed / requested|Completed|No route|No affordable crew|Capacity unmet|\n|---|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    for r in result['rows']:
        table += f'|{r["design"]}|{r["climate"]}|{r["hours_worker_year"]}|{r["crew"]}|{r["target_points"]:,}|{r["completed_visits"]:,} / {r["requested_visits"]:,}|{100*r["completed_fraction"]:.3f}%|{r["route_unreachable"]:,}|{r["provider_work_unavailable"]:,}|{r["capacity_unmet"]:,}|\n'
    report = '''# Target-grid spacing and phase audit

Declaration `4f592bfe` preceded all outputs. Five designs × eight original
raw/corrected,600/300 farm-hour,crew1/4 scenarios produce forty reported cases.
Every scenario uses the original assign-once allocator and SAME reserved patrol
slice;the spare-provider extension is excluded to isolate grid definitions.
All original point maps,other packet files and production defaults are retained.

## Geometry and matched physical checks

The declared designs are block2/3/5 with phase0,plus block3 with diagonal phases
1 and2. Nominal edges are 7.3605,11.0407 and18.4012 km. Tile from negative phase
offsets in block-size steps,clip at raster bounds,and select the majority-land
cell nearest each clipped tile's geometric centre;lowest global grid ID breaks
ties. Every land cell belongs to one represented tile. Target IDs match exactly
between climates. Neither population,roads,actors nor outcomes select targets.

Retain the original conditional actor/point demand definition and one task per
bin,including unreachable bins. Same directed walking graphs,seasonal costs,
two-day leg/four-day roundtrip-plus-on-site limits,crew support,integer work and
collection/service commitments apply. No ferries or sea/river auxiliary edges
are introduced. Raw/corrected paths use the same graph hashes as the original.

## Findings and scope

At fixed nominal11.04km spacing,the three declared phases change completed
fractions by 0.185–0.265 percentage points across the eight scenarios. This
measures these three diagonal phases only;it does not establish invariance to
all target placements or unseen occupations.

Spacing changes workload strongly. In corrected600h/four-person scenarios,
7.36km targets request575,040 tasks and complete254,850(44.319%);11.04km requests
260,496 and completes163,423(62.735%);18.40km requests97,212 and completes66,645
(68.556%). Finer spacing completes more total tasks while meeting a smaller
fraction of its larger request set. This combines supplied task-density and
geographic-sampling effects;it is not numerical-convergence evidence or a
reason to choose the coarsest grid. All forty cases follow.

''' + table + '\n' + '\n'.join(f'![Declared grid comparison](figures/{p.name})' for p in figures) + '''

## Independent review and reproducibility

Four manufactured geometry controls check clipping,phases,ties,full land/area
coverage,input preservation and exact original zero-phase geometry. The
independent reviewer imports neither the new selector nor allocation code.
It groups land cells independently,rebuilds directed graphs,checks every path
edge/cost/endpoint,recomputes eligible source-target sets and confirms all
walking land footprints remain within the old full-network reference. It uses
the same established SciPy shortest-path algorithm,not a second path algorithm.
Scalar assignment,whole tasks,all actor/bin partitions,zero-budget controls and
full monthly provider ledgers pass for every scenario.

The original b3_p0 targets,recorded paths and all allocation arrays reproduce
exactly;its complete NPZ is byte identical to the original eight-case packet.
Fresh route/target packets,results and all five field bundles are byte exact.
Route packets are split by month/design to bound memory and individual file
sizes. No failed design is dropped and no source/food/work gate is relaxed.

The normal evidence atlas includes all forty cases,four figures,results,
review,replay,summary and prior declaration. Full source/route/allocation arrays
are preserved under output/network_visit_target_grid_20261112 in the repository.
Earlier optional point maps and all normal defaults remain unchanged.

This remains conditional monthly staff-hour accounting. Observed demand,
institutional functions,dated residents/occupation,prospective transfer,
individual crew calendars and daily provisioning remain unqualified. Complete
diets,household/draft work and mobile/nonstate/unaffiliated resource integration
remain open throughout release1–4/S1–S5. No territorial authority is inferred.
'''
    (ROOT / 'reports/NETWORK_VISIT_TARGET_GRID_20261112.md').write_text(report)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    for source, name in [(OUT / 'results.json', 'visit_grid_results.json'), (OUT / 'review.json', 'visit_grid_review.json'),
        (OUT / 'replay.json', 'visit_grid_replay.json'), (OUT / 'summary.json', 'visit_grid_summary.json'), (PLAN, 'visit_grid_plan.json')]: shutil.copyfile(source, data / name)
    table_html = ''.join(f'<tr><td>{r["design"]}</td><td>{r["climate"].title()}</td><td>{r["hours_worker_year"]}</td><td>{r["crew"]}</td><td>{r["target_points"]:,}</td><td>{r["completed_visits"]:,} / {r["requested_visits"]:,}</td><td>{100*r["completed_fraction"]:.3f}%</td></tr>' for r in result['rows'])
    section = '''<!--visit-grid-start--><section><h2>Target-grid spacing and phase audit</h2><details id="visit-grid" class="panel"><summary>40 declared point-task scenarios · phase and supplied workload distinguished</summary>
<p>Five fixed designs use roughly7.36/11.04/18.40km spacing,plus three diagonal phases at11.04km. Every design uses the same eight food/collection-qualified parents,original assign-once visit rule and SAME reserved patrol slice. The baseline reproduces all original targets,paths and allocation arrays;its complete NPZ is byte identical. All original point maps and defaults remain unchanged.</p>
<p><strong>Phase spreads are 0.185–0.265 percentage points across the three declared phases.</strong> Spacing changes BOTH supplied task density and target geography. Corrected600h/four-person crews complete254,850/575,040 requests at7.36km,163,423/260,496 at11.04km,and66,645/97,212 at18.40km. More fine-grid tasks are completed in absolute terms while a smaller fraction of the larger request set is met. This is not numerical-convergence evidence or a basis for choosing the coarsest grid.</p>
<div class="table"><table><thead><tr><th>Design</th><th>Climate</th><th>Farm hours</th><th>Crew</th><th>Targets</th><th>Completed / requested</th><th>Completed</th></tr></thead><tbody>''' + table_html + '</tbody></table></div>\n' + '\n'.join(f'<img src="../../reports/figures/{p.name}" alt="All declared {p.stem.replace("_", " ")} comparisons;conditional tasks,not territory">' for p in figures) + '''
<p>Independent geometry,directed route edges,recomputed eligibility,scalar integer assignments,all actor/bin partitions and full monthly ledgers pass for all forty cases. Every walking land footprint stays within its old full-network reference. Zero-budget controls complete zero visits. Fresh route/result/field files are byte exact. These are supplied point tasks,not empirical demand,whole-block territory,individual daily rosters,observed patrols or political authority. Unaffiliated/mobile/missing-inventory contexts remain unscored.</p>
<p><a href="../../reports/NETWORK_VISIT_TARGET_GRID_20261112.md">Methods and complete deficit table</a> · <a href="data/visit_grid_results.json" download>All40 results</a> · <a href="data/visit_grid_review.json" download>Independent review</a> · <a href="data/visit_grid_replay.json" download>Fresh byte replay</a> · <a href="data/visit_grid_summary.json" download>All phase comparisons</a> · <a href="data/visit_grid_plan.json" download>Prior declaration</a></p></details></section><!--visit-grid-end-->'''
    html = page.read_text(); pattern = r'<!--visit-grid-start-->[\s\S]*?<!--visit-grid-end-->'
    if re.search(pattern, html): html = re.sub(pattern, lambda match: section, html)
    else:
        assert '<!--spare-visits-start-->' in html; html = html.replace('<!--spare-visits-start-->', section + '\n<!--spare-visits-start-->', 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='network_visit_target_grid_20261112', status='model_only_declared_grid_task_sensitivity', evidence='reports/NETWORK_VISIT_TARGET_GRID_20261112.md',
        note='All40fixedgridscenarios reported;phase and suppliedtaskdensity distinct,baselinebyteexact,no newdata,empiricaldemand,territory ordefaultadoption.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]; write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(OUT / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page), publisher_sha256=sha(Path(__file__)),
        figures_sha256={str(p.relative_to(ROOT)): sha(p) for p in figures}, original_map_files_unchanged=len(result['unchanged_map_sha256'])))
    for p in figures: print(p)
    print('Published all40 declared target-grid scenarios without replacing maps or defaults.')


if __name__ == '__main__': main()
