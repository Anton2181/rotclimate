"""Plot reviewed collection/crew packing gaps and one explicit worker calendar."""
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
OUT = ROOT / 'output/network_visit_calendar_20261112'
FIGURES = ROOT / 'reports/figures'
COLORS = dict(home='#b8bfbb', collection='#af8354', visit='#467f98')


def shortfalls(result):
    rows = result['collection_rows']; labels = [f'{r["climate"].title()} · {r["hours_worker_year"]} farm hours' for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7)); y = np.arange(len(rows))
    for ax, metric, denominator, title in [
        (axes[0], 'unpacked_trips', 'required_trips', 'Required collector trips left unpacked'),
        (axes[1], 'mandatory_failed_provider_bins', 'relevant_provider_bins', 'Provider / bins with mandatory-work gaps')]:
        values = [100 * r[metric] / r[denominator] for r in rows]
        ax.barh(y, values, color='#ae7952'); ax.set_yticks(y, labels); ax.invert_yaxis()
        ax.set_xlim(0, max(values) * 1.45); ax.set_xlabel('% of the specified denominator'); ax.set_title(title, fontsize=10)
        for i, (r, value) in enumerate(zip(rows, values)):
            ax.text(value + max(values) * .025, i, f'{r[metric]:,} / {r[denominator]:,}', va='center', fontsize=8)
        ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
    fig.suptitle('Whole collector trips leave gaps despite passing aggregate staff-hour budgets', fontsize=12)
    fig.text(.5, .035, 'Collection-first greedy packing under supplied availability;failure does not prove that no schedule exists.\n'
        'A missing mandatory trip leaves the unchanged annual delivery plan uncertified.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.20, right=.99, top=.82, bottom=.23, wspace=.75)
    path = FIGURES / 'network_visit_calendar_collection_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig)
    rows = result['visit_rows']; y = np.arange(len(rows)); fig, ax = plt.subplots(figsize=(11, 5.8)); left = np.zeros(len(rows))
    for metric, label, color in [
        ('packed_visits', 'Packed within bin', '#487e70'),
        ('blocked_by_mandatory_collection', 'Blocked by mandatory collection', '#ac6656'),
        ('greedy_crew_unpacked_visits', 'Greedy crew shortfall', '#c09c60')]:
        values = np.array([100 * r[metric] / r['original_planned_visits'] for r in rows])
        ax.barh(y, values, left=left, label=label, color=color); left += values
    labels = [f'{r["climate"].title()} · {r["hours_worker_year"]}h · crew {r["crew"]}' for r in rows]
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel('% of the original planned visits')
    for i, r in enumerate(rows): ax.text(3, i, f'{r["packed_visits"]:,} / {r["original_planned_visits"]:,}', va='center', color='white', fontsize=9)
    ax.set_title('Collection-first worker calendars partition every original planned visit', fontsize=12)
    ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True); ax.legend(loc='upper center', bbox_to_anchor=(.5, -.14), ncol=3, frameon=False, fontsize=8)
    fig.text(.5, .025, 'Per-bin packing only:these counts do not certify unchanged annual food deliveries or observed patrols.\n'
        'Providers,people,food plans and original point maps are preserved;no extra tasks or reassigned visits.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.24, right=.98, top=.90, bottom=.25)
    visits = FIGURES / 'network_visit_calendar_visits_20261112.png'; fig.savefig(visits, dpi=160); plt.close(fig)
    return [path, visits]


def example_calendar(result):
    # Illustration selection is deterministic and is never used as a scored
    # cohort:canonical case/bin order,then lowest provider with both job types.
    selected = None
    for r in result['visit_rows']:
        if r['crew'] != 4: continue
        for month in range(12):
            c = dict(np.load(OUT / r['parent_key'] / f'collection_{month:02d}.npz'))
            v = dict(np.load(OUT / r['key'] / f'visits_{month:02d}.npz'))
            candidates = np.flatnonzero((c['provider_packed_counts'] > 0) & (v['provider_packed'] > 0) & (c['worker_counts'] >= 12))
            if len(candidates): selected = r, month, int(candidates[0]), c, v; break
        if selected is not None: break
    if selected is None: raise ValueError('No declared calendar illustration is available')
    r, month, site, c, v = selected; eligible = (v['site'] == site) & v['packed']
    crew_workers = sorted(set(v['crew_workers'][eligible].ravel().tolist()))
    workers = crew_workers[:12]
    workers += [w for w in range(int(c['worker_counts'][site])) if w not in workers][:12 - len(workers)]
    workers.sort(); offset = int(v['worker_offsets'][site]); service_each = float(c['home_service_hours'][site] / c['worker_counts'][site])
    records = []
    def record(worker, kind, task, start, end):
        records.append(dict(scenario=r['key'], climate=r['climate'], seasonal_bin=month + 1, provider_index=site,
            worker_index=worker, duty=kind, task=task, start_working_hour=float(start), end_working_hour=float(end),
            duty_hours=float(end - start), worker_duty_cap_hours=50., month_calendar_hours=7 * 365 / 12))
    for worker in workers:
        record(worker, 'home', 'divisible services A/B', 0., service_each)
        for i in np.flatnonzero((c['collection_site'] == site) & (c['collection_worker'] == worker)):
            record(worker, 'collection', f'origin {c["collection_origin"][i]} trip {c["collection_serial"][i]}', c['collection_start'][i], c['collection_end'][i])
        for i in np.flatnonzero(eligible & (v['crew_workers'] == worker).any(axis=1)):
            record(worker, 'visit', f'actor {v["actor"][i]} target {v["target_index"][i]}', v['start'][i], v['end'][i])
        own = sorted((d for d in records if d['worker_index'] == worker), key=lambda d: (d['start_working_hour'], d['end_working_hour']))
        assert all(a['end_working_hour'] <= b['start_working_hour'] for a, b in zip(own, own[1:]))
        np.testing.assert_allclose(sum(d['duty_hours'] for d in own), v['worker_work_hours'][offset + worker], atol=1e-9)
    path = OUT / 'example_worker_calendar.csv'
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    fig, ax = plt.subplots(figsize=(12, 6.1))
    for j, worker in enumerate(workers):
        for kind in COLORS:
            spans = [(d['start_working_hour'], d['duty_hours']) for d in records if d['worker_index'] == worker and d['duty'] == kind]
            ax.broken_barh(spans, (j - .34, .68), facecolors=COLORS[kind], edgecolors='white', linewidths=.4)
    labels = [f'Worker {w + 1} · {v["worker_work_hours"][offset + w]:.1f} / 50 duty h' for w in workers]
    ax.set_yticks(range(len(workers)), labels); ax.invert_yaxis(); ax.set_xlim(0, max(d['end_working_hour'] for d in records) + 3)
    ax.set_xlabel('Calendar in working-hour coordinates · 7 hours per day'); ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
    ax.set_title(f'Recorded model calendar · {r["key"]} · bin {month + 1} · provider {site}', fontsize=11)
    ax.legend(handles=[Patch(color=COLORS[k], label=label) for k, label in [('home', 'Home services'), ('collection', 'Collector trip'), ('visit', 'Four-person visit')]], loc='upper center', bbox_to_anchor=(.5, -.12), ncol=3, frameon=False, fontsize=9)
    fig.text(.5, .025, 'Gaps consume elapsed calendar time,not duty hours. Full month horizon:212.92 working-hour coordinates;axis shows the illustrated tasks.\n'
        'First eligible case/bin/provider;first12 visit participants,filled with lowest remaining worker IDs. Supplied availability,not observed staffing.', ha='center', fontsize=8)
    fig.subplots_adjust(left=.25, right=.98, top=.90, bottom=.24)
    figure = FIGURES / 'network_visit_calendar_example_20261112.png'; fig.savefig(figure, dpi=160); plt.close(fig)
    return figure, dict(scenario=r['key'], seasonal_bin=month + 1, provider_index=site, worker_indexes=workers, worker_task_rows=len(records),
        selection='Canonical four-person case/bin order,lowest provider with both job types;first12 visit participants,filled with lowest other worker IDs.',
        scope='Recorded per-bin illustration;not an annual food or observed staffing qualification.')


def plot(result):
    figures = shortfalls(result); example, context = example_calendar(result)
    return figures + [example], context
