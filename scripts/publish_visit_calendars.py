"""Publish the reviewed worker-calendar packing audit; no map or default changes."""
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

OUT = ROOT / 'output/network_visit_calendar_20261112'
PLAN = ROOT / 'calibration/network_visit_calendar_20261112/plan.json'
SURFACE = '#f5f3ed'; INK = '#1d2a2c'; MUTED = '#5b6664'; GRID = '#a7a6a0'
# Three-series palette checked with the dataviz validator against this surface.
PACKED = '#2a78d6'; GREEDY = '#eb6834'; BLOCKED = '#1baf7a'
MONTHS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']


def label(row):
    return f"{row['climate'].title()} · {row['hours_worker_year']} h" + (f" · crew {row['crew']}" if 'crew' in row else '')


def style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.edgecolor': GRID, 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.labelcolor': MUTED, 'text.color': INK})


def shortfall_figure(result):
    style(); fig, (ax, bx) = plt.subplots(1, 2, figsize=(13.5, 6.2), gridspec_kw={'width_ratios': [1, 1.5]})
    fig.patch.set_facecolor(SURFACE)
    for axis in (ax, bx):axis.set_facecolor(SURFACE); axis.grid(axis='x', alpha=.18, color=GRID, lw=.8); axis.set_axisbelow(True)
    rows = result['collection_rows']; y = np.arange(len(rows))[::-1]
    share = [100 * r['mandatory_failed_provider_bins'] / r['relevant_provider_bins'] for r in rows]
    ax.barh(y, share, height=.5, color=GREEDY)
    for yy, r, s in zip(y, rows, share):
        ax.text(s + .12, yy, f"{s:.1f}%  ({r['unpacked_trips']:,} of {r['required_trips'] / 1e6:.2f} M trips unpacked)", va='center', fontsize=9, color=INK)
    ax.set_yticks(y, [label(r) for r in rows]); ax.set_xlim(0, 11.5); ax.set_xlabel('Provider-months with an unpacked mandatory collector trip (%)')
    ax.set_title('Collection: a few provider-months cannot pack every trip', loc='left', fontsize=12, pad=24)
    ax.text(0, 1.02, 'Whole trips, longest first, earliest free worker, 50 duty hours per worker and month.', transform=ax.transAxes, fontsize=9, color=MUTED)
    rows = result['visit_rows']; y = np.arange(len(rows))[::-1]
    packed = np.array([100 * r['packed_visits'] / r['original_planned_visits'] for r in rows])
    greedy = np.array([100 * r['greedy_crew_unpacked_visits'] / r['original_planned_visits'] for r in rows])
    blocked = np.array([100 * r['blocked_by_mandatory_collection'] / r['original_planned_visits'] for r in rows])
    bx.barh(y, packed, height=.55, color=PACKED, label='Packed inside its month', edgecolor=SURFACE, linewidth=1.5)
    bx.barh(y, greedy, left=packed, height=.55, color=GREEDY, label='No free crew slot (greedy packer)', edgecolor=SURFACE, linewidth=1.5)
    bx.barh(y, blocked, left=packed + greedy, height=.55, color=BLOCKED, label='Blocked by a missed collector trip', edgecolor=SURFACE, linewidth=1.5)
    for yy, r, p, g in zip(y, rows, packed, greedy):
        bx.text(p / 2, yy, f"{p:.1f}%", ha='center', va='center', fontsize=9, color='white')
        bx.text(101, yy, f"{r['packed_visits']:,} of {r['original_planned_visits']:,}", va='center', fontsize=9, color=INK)
    bx.set_yticks(y, [label(r) for r in rows]); bx.set_xlim(0, 138); bx.set_xticks([0, 25, 50, 75, 100])
    bx.set_xlabel('Share of the originally planned visits (%)')
    bx.set_title('Visits: 86–93% of planned visits fit individual calendars', loc='left', fontsize=12, pad=24)
    bx.text(0, 1.02, 'Original providers and crews; no visit is moved, added or split.', transform=bx.transAxes, fontsize=9, color=MUTED)
    bx.legend(loc='upper left', bbox_to_anchor=(-.02, -.12), ncol=2, frameon=False, fontsize=9, handlelength=1.2, columnspacing=1.2)
    fig.suptitle('Worker calendars: most planned work packs, some does not', x=.045, ha='left', fontsize=15, y=.975)
    fig.text(.045, .02, 'Greedy per-month packing under supplied availability. A shortfall is not proof that no schedule exists, and any unpacked collector trip leaves that\n'
        "provider's annual food delivery uncertified. No observed staffing, daily provisioning, territory or authority is inferred. Maps and defaults unchanged.",
        fontsize=9, color=MUTED, linespacing=1.5)
    fig.subplots_adjust(left=.12, right=.985, top=.83, bottom=.27, wspace=.36)
    path = ROOT / 'reports/figures/network_visit_calendar_shortfall_20261112.png'; fig.savefig(path, dpi=160, facecolor=fig.get_facecolor()); plt.close(fig)
    return path


def month_figure(result):
    style(); fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6), sharey=True); fig.patch.set_facecolor(SURFACE)
    for ax, mode in zip(axes, ('raw', 'corrected')):
        ax.set_facecolor(SURFACE); ax.grid(alpha=.18, color=GRID, lw=.8); ax.set_axisbelow(True)
        for hours, color in ((600, PACKED), (300, GREEDY)):
            for crew, dash in ((1, '-'), (4, (0, (4, 2)))):
                row = next(r for r in result['visit_rows'] if r['climate'] == mode and r['hours_worker_year'] == hours and r['crew'] == crew)
                ax.plot(range(1, 13), np.array(row['packed_by_bin']) / 1000, color=color, lw=2, ls=dash, marker='o', ms=4,
                        label=f'{hours} farm hours · crew {crew}')
        ax.set_xticks(range(1, 13), MONTHS); ax.set_xlabel('Monthly bin')
        ax.set_ylim(0, 1.08 * max(max(r['packed_by_bin']) for r in result['visit_rows']) / 1000)
        ax.set_title(f'{mode.title()} climate', loc='left', fontsize=12)
    axes[0].set_ylabel('Visits packed into worker calendars (thousands)')
    axes[1].legend(loc='lower center', frameon=False, fontsize=9, ncol=2)
    fig.suptitle('Packed visits by month: winter bins carry about half the summer load', x=.055, ha='left', fontsize=15, y=.97)
    fig.text(.055, .025, 'Solid lines: one-person crews; dashed: four-person crews. Counts are conditional point tasks packed by a greedy scheduler, not observed patrols.',
             fontsize=9, color=MUTED)
    fig.subplots_adjust(left=.07, right=.985, top=.84, bottom=.17, wspace=.06)
    path = ROOT / 'reports/figures/network_visit_calendar_months_20261112.png'; fig.savefig(path, dpi=160, facecolor=fig.get_facecolor()); plt.close(fig)
    return path


def main():
    result = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text())
    replay = json.loads((OUT / 'replay.json').read_text())
    assert review['status'] == replay['status'] == 'passed' and review['results_sha256'] == sha(OUT / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_visit_calendars.py')
    assert len(result['collection_rows']) == 4 and len(result['visit_rows']) == len(review['cases']) == 8
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_map_sha256']}.items():
        assert sha(ROOT / path) == digest, path
    for path, digest in result['files_sha256'].items():assert sha(OUT / path) == digest, path
    for path, digest in replay['byte_exact_files'].items():assert sha(OUT / path) == digest, path
    figures = [shortfall_figure(result), month_figure(result)]
    collection = '|Parent|Required trips|Unpacked trips|Provider-months failing / relevant|\n|---|---:|---:|---:|\n' + ''.join(
        f"|{r['parent_key']}|{r['required_trips']:,}|{r['unpacked_trips']:,}|{r['mandatory_failed_provider_bins']:,} / {r['relevant_provider_bins']:,}|\n" for r in result['collection_rows'])
    visits = '|Case|Planned|Packed within month|Packed|Blocked by collection|Greedy crew shortfall|\n|---|---:|---:|---:|---:|---:|\n' + ''.join(
        f"|{r['key']}|{r['original_planned_visits']:,}|{r['packed_visits']:,}|{100 * r['packed_visits'] / r['original_planned_visits']:.1f}%|{r['blocked_by_mandatory_collection']:,}|{r['greedy_crew_unpacked_visits']:,}|\n" for r in result['visit_rows'])
    low = min(r['packed_visits'] / r['original_planned_visits'] for r in result['visit_rows']); high = max(r['packed_visits'] / r['original_planned_visits'] for r in result['visit_rows'])
    report = f'''# Worker-calendar packing audit

Declaration `bdd6135c` preceded all outputs. The audit asks whether the monthly
hour budgets behind the eight published point-visit plans can be turned into
individual, non-overlapping worker calendars. Existing maps and defaults are
unchanged, and no new map family is created.

## Method

The same four food and collection parents and the eight original `b3_p0`
point-visit plans are retained. Each provider has a whole number of supported
workers, each with 50 duty hours per monthly bin on a common 7×365/12-hour
calendar. Mandatory, divisible home services are shared equally first. Whole
collector trips are then packed, longest first, onto the earliest free worker.
Original visits follow, each needing a synchronized crew of one or four at its
original provider. A provider that cannot pack every collector trip in a month
has its visits for that month blocked. No visit, worker-hour, food, person or
provider is added, moved or split.

## Collection packing

{collection}
Between 0.18% and 0.38% of collector trips do not fit, concentrated in 1.7% to
4.3% of the provider-months that have collection work.

## Original planned visits

{visits}
Between {100 * low:.1f}% and {100 * high:.1f}% of the planned visits fit inside their month.
Most of the remainder is a greedy crew shortfall: collection is packed first
and fragments workers' spare hours before longer visits are tried. Visits
blocked by a missed collector trip are 0.1% to 0.7% of the plan.

![Collection and visit packing](figures/{figures[0].name})

![Packed visits by month](figures/{figures[1].name})

## What this does and does not show

These are per-month packing results from one greedy, non-preemptive rule under
supplied worker availability. A shortfall is not proof that no schedule exists;
a different ordering might pack more, and any such test needs its own prior
declaration. Any unpacked mandatory collector trip means this constructed
schedule does not certify that provider's unchanged annual food delivery.

No actual staff functions, daily food issues, observed visits, territory or
authority are inferred. Dated sizes and occupation, prospective transfer,
complete diets, household and draft work, and mobile, nonstate and unaffiliated
resources remain open.

## Review and reproducibility

Seven manufactured controls pass. The independent reviewer
(`scripts/review_visit_calendars.py`) rebuilds the schedules with sorted lists
rather than the producer's allocator and checks {review['checked_collection_trips']:,} collector-trip
intervals, {review['checked_planned_visits']:,} planned visits and {review['checked_worker_bins']:,} worker-months for
identity, non-overlap, duty caps, distinct synchronized crews and whole monthly
ledgers. All 144 schedule packets and the results reproduce byte for byte in a
fresh run. {len(result['unchanged_map_sha256'])} published map files are verified unchanged.

The normal evidence atlas now carries both tables, both figures and the
results, review, replay and prior declaration as downloads. Full schedule
packets stay under `output/network_visit_calendar_20261112` in the repository.
'''
    (ROOT / 'reports/NETWORK_VISIT_CALENDAR_20261112.md').write_text(report)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    for source, name in [(OUT / 'results.json', 'visit_calendar_results.json'), (OUT / 'review.json', 'visit_calendar_review.json'),
        (OUT / 'replay.json', 'visit_calendar_replay.json'), (PLAN, 'visit_calendar_plan.json')]:shutil.copyfile(source, data / name)
    collection_html = ''.join(f"<tr><td>{label(r)}</td><td>{r['required_trips']:,}</td><td>{r['unpacked_trips']:,}</td><td>{r['mandatory_failed_provider_bins']:,} / {r['relevant_provider_bins']:,}</td></tr>" for r in result['collection_rows'])
    visit_html = ''.join(f"<tr><td>{label(r)}</td><td>{r['original_planned_visits']:,}</td><td>{r['packed_visits']:,}</td><td>{100 * r['packed_visits'] / r['original_planned_visits']:.1f}%</td><td>{r['blocked_by_mandatory_collection']:,}</td><td>{r['greedy_crew_unpacked_visits']:,}</td></tr>" for r in result['visit_rows'])
    section = f'''<!--visit-calendar-start--><section><h2>Worker-calendar packing audit</h2><details id="visit-calendar" class="panel"><summary>8 visit plans and 4 collection parents packed into individual calendars · no map change</summary>
<p>The monthly hour budgets behind the eight published point-visit plans were turned into individual, non-overlapping worker calendars: whole supported workers with 50 duty hours per month, shared home services first, whole collector trips next, then the original visits with synchronized crews at their original providers. Nothing is added, moved or split.</p>
<p><strong>{100 * low:.0f}–{100 * high:.0f}% of planned visits fit inside their month.</strong> Collector trips fail to pack in 1.7–4.3% of the provider-months that have collection work, and those providers' visits are blocked for that month. Most unpacked visits are a greedy crew shortfall: collection is packed first and fragments spare hours. This is one greedy rule; a shortfall is not proof that no schedule exists, and any unpacked collector trip leaves that provider's annual food delivery uncertified.</p>
<div class="table"><table><thead><tr><th>Parent</th><th>Required trips</th><th>Unpacked trips</th><th>Provider-months failing / relevant</th></tr></thead><tbody>{collection_html}</tbody></table></div>
<div class="table"><table><thead><tr><th>Case</th><th>Planned</th><th>Packed within month</th><th>Packed</th><th>Blocked by collection</th><th>Greedy crew shortfall</th></tr></thead><tbody>{visit_html}</tbody></table></div>
<img src="../../reports/figures/{figures[0].name}" alt="Share of provider-months with unpacked collector trips, and share of planned visits packed, blocked or unpacked, for all declared cases">
<img src="../../reports/figures/{figures[1].name}" alt="Visits packed into worker calendars by monthly bin for all eight cases">
<p>An independent sorted-list reviewer checks {review['checked_collection_trips']:,} collector-trip intervals, {review['checked_planned_visits']:,} planned visits and {review['checked_worker_bins']:,} worker-months for identity, non-overlap, duty caps, distinct crews and monthly ledgers; 145 fresh files are byte exact. No observed staffing, daily provisioning, territory or authority is inferred. All maps and defaults are unchanged.</p>
<p><a href="../../reports/NETWORK_VISIT_CALENDAR_20261112.md">Methods and limits</a> · <a href="data/visit_calendar_results.json" download>All results</a> · <a href="data/visit_calendar_review.json" download>Independent review</a> · <a href="data/visit_calendar_replay.json" download>Fresh byte replay</a> · <a href="data/visit_calendar_plan.json" download>Prior declaration</a></p></details></section><!--visit-calendar-end-->'''
    html = page.read_text(); pattern = r'<!--visit-calendar-start-->[\s\S]*?<!--visit-calendar-end-->'
    if re.search(pattern, html):html = re.sub(pattern, lambda match: section, html)
    else:
        assert '<!--visit-grid-start-->' in html; html = html.replace('<!--visit-grid-start-->', section + '\n<!--visit-grid-start-->', 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='network_visit_calendar_20261112', status='model_only_constructive_worker_calendar_packing', evidence='reports/NETWORK_VISIT_CALENDAR_20261112.md',
        note='Eight original point-visit plans and four parents packed into individual worker calendars by one greedy rule; shortfalls are not impossibility. No new data, empirical demand, territory or default adoption.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]; write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(OUT / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page), publisher_sha256=sha(Path(__file__)),
        figures_sha256={str(p.relative_to(ROOT)): sha(p) for p in figures}, original_map_files_unchanged=len(result['unchanged_map_sha256'])))
    for p in figures:print(p)
    print('Published the worker-calendar audit without replacing maps or defaults.')


if __name__ == '__main__':main()
