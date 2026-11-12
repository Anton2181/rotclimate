"""Show all paired job-order tradeoffs and the same workers under both rules."""
import csv
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
OUT = ROOT / 'output/network_visit_joint_order_20261112'
BASE = ROOT / 'output/network_visit_calendar_20261112'
FIG = ROOT / 'reports/figures'


def comparisons(result):
    keys = list(dict.fromkeys(r['key'] for r in result['rows']))
    pairs = [(next(r for r in result['rows'] if r['key'] == key and r['policy'] == 'collection_first'),
              next(r for r in result['rows'] if r['key'] == key and r['policy'] == 'joint_duration_first')) for key in keys]
    labels = [f'{a["climate"].title()} · {a["hours_worker_year"]}h · crew {a["crew"]}' for a, _ in pairs]; y = np.arange(8)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.8), sharey=True)
    for ax, field, title in [(axes[0], 'bin_qualified_visits', 'Visits with all mandatory work in their bin'),
                             (axes[1], 'twelve_bin_gated_visits', 'Visits at twelve-bin-complete providers'),
                             (axes[2], 'unpacked_collector_trips', 'Required collector trips left unpacked')]:
        delta = [b[field] - a[field] for a, b in pairs]
        ax.barh(y, delta, color=['#487e70' if (v <= 0 if field == 'unpacked_collector_trips' else v >= 0) else '#ac7157' for v in delta])
        ax.axvline(0, color='#777', linewidth=.6); ax.set_title(title, fontsize=9); ax.set_xlabel('Joint duration first − collection first', fontsize=9)
        bound = max(max(abs(v) for v in delta), 1); ax.set_xlim(min(min(delta), 0) - bound * .42, max(max(delta), 0) + bound * .48)
        for i, value in enumerate(delta): ax.text(value + bound * (.025 if value >= 0 else -.025), i, f'{value:+,}', ha='left' if value >= 0 else 'right', va='center', fontsize=8)
        ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True); ax.ticklabel_format(axis='x', style='plain')
    axes[0].set_yticks(y, labels); axes[0].invert_yaxis()
    fig.suptitle('A different job order improves monthly visit packing while exposing delivery tradeoffs', fontsize=12)
    fig.text(.5, .025, 'All eight paired scenarios,unchanged jobs/workers/providers/budgets. Green denotes a favorable change in the named quantity.\n'
        'The twelve-bin gate is a necessary delivery-scheduling test,not complete annual food validation or observed staffing.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.17, right=.99, top=.86, bottom=.20, wspace=.35)
    path = FIG / 'network_visit_joint_order_deltas_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.2), sharey=True)
    for ax, field, title in [(axes[0], 'bin_qualified_visits', 'All mandatory work packed in the visit bin'),
                             (axes[1], 'twelve_bin_gated_visits', 'Provider passes all twelve mandatory bins')]:
        ax.barh(y - .18, [a[field] for a, _ in pairs], height=.34, color='#7c8780', label='Collection first')
        ax.barh(y + .18, [b[field] for _, b in pairs], height=.34, color='#467f98', label='Joint duration first')
        ax.set_title(title, fontsize=10); ax.set_xlabel('Original planned point visits retained by the gate'); ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
    axes[0].set_yticks(y, labels); axes[0].invert_yaxis()
    handles, legends = axes[0].get_legend_handles_labels()
    fig.legend(handles, legends, frameon=False, fontsize=9, loc='lower center', bbox_to_anchor=(.5, .10), ncol=2)
    fig.suptitle('Monthly and twelve-bin delivery gates answer different questions', fontsize=12)
    fig.text(.5, .025, 'Every scenario and both fixed policies retained. Original point maps/defaults are unchanged;no winning policy is adopted.\n'
        'Supplied availability and divisible services;daily provisioning,within-bin grain timing and actual institutional functions remain unqualified.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.21, right=.99, top=.88, bottom=.24, wspace=.18)
    second = FIG / 'network_visit_joint_order_gates_20261112.png'; fig.savefig(second, dpi=160); plt.close(fig)
    return [path, second]


def calendar_example(result, gates):
    selected = None
    for row in result['rows']:
        if row['policy'] != 'joint_duration_first' or row['crew'] != 4: continue
        parent_key = f'{row["climate"]}_h{row["hours_worker_year"]}_load120000_all_open'
        for month in range(12):
            joint = dict(np.load(OUT / row['key'] / f'calendar_{month:02d}.npz'))
            old_c = dict(np.load(BASE / parent_key / f'collection_{month:02d}.npz')); old_v = dict(np.load(BASE / row['key'] / f'visits_{month:02d}.npz'))
            eligible = np.flatnonzero((joint['provider_scheduled_visits'] > 0) & (old_v['provider_packed'] > 0) & (old_c['provider_packed_counts'] > 0) & (joint['worker_counts'] >= 12))
            if len(eligible): selected = row, month, int(eligible[0]), joint, old_c, old_v; break
        if selected: break
    if selected is None: raise ValueError('No matched recorded calendar illustration')
    row, month, site, joint, old_c, old_v = selected; workers = list(range(12)); records = []
    def record(policy, worker, duty, task, start, end, complete):
        records.append(dict(policy=policy, scenario=row['key'], seasonal_bin=month + 1, provider_index=site, worker_index=worker,
            duty=duty, task=task, start_working_hour=float(start), end_working_hour=float(end), duty_hours=float(end - start),
            provider_bin_mandatory_complete=bool(complete), provider_twelve_bin_mandatory_complete=bool(gates[f'{policy}__{row["key"]}__annual'][site]),
            worker_duty_cap_hours=50., month_calendar_hours=7 * 365 / 12))
    for policy in ('collection_first', 'joint_duration_first'):
        if policy == 'collection_first':
            c, v = old_c, old_v; mask = (v['site'] == site) & v['packed']; members, starts, ends = v['crew_workers'], v['start'], v['end']
            actor, target = v['actor'], v['target_index']; complete = c['collection_complete'][site] & c['service_packed'][site]
        else:
            c, v = joint, joint; mask = (v['visit_site'] == site) & v['visit_scheduled']; members, starts, ends = v['visit_crew'], v['visit_start'], v['visit_end']
            actor, target = v['visit_actor'], v['visit_target']; complete = c['collection_complete'][site] & c['service_packed'][site]
        count = int(c['worker_counts'][site]); service = float(c['home_service_hours'][site] / count)
        for worker in workers:
            record(policy, worker, 'home', 'divisible services A/B', 0., service, complete)
            for i in np.flatnonzero((c['collection_site'] == site) & (c['collection_worker'] == worker)):
                record(policy, worker, 'collection', f'origin {c["collection_origin"][i]} trip {c["collection_serial"][i]}', c['collection_start'][i], c['collection_end'][i], complete)
            for i in np.flatnonzero(mask & (members == worker).any(axis=1)):
                record(policy, worker, 'visit', f'actor {actor[i]} target {target[i]}', starts[i], ends[i], complete)
    csv_path = OUT / 'example_policy_calendars.csv'
    with csv_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    colors = dict(home='#bcc1bb', collection='#af8354', visit='#467f98'); fig, axes = plt.subplots(1, 2, figsize=(14, 6.3), sharey=True)
    for ax, policy, data, title in [(axes[0], 'collection_first', old_v, 'Collection first'), (axes[1], 'joint_duration_first', joint, 'Joint duration first')]:
        offset = int(data['worker_offsets'][site])
        for j, worker in enumerate(workers):
            for kind, color in colors.items():
                spans = [(v['start_working_hour'], v['duty_hours']) for v in records if v['policy'] == policy and v['worker_index'] == worker and v['duty'] == kind]
                ax.broken_barh(spans, (j - .34, .68), facecolors=color, edgecolors='white', linewidths=.3)
            ax.text(1.01, j, f'{data["worker_work_hours"][offset + worker]:.1f}h', transform=ax.get_yaxis_transform(), va='center', fontsize=8)
        ax.set_title(title); ax.set_xlabel('Working-hour calendar coordinates · 7 per day'); ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
        ax.set_xlim(0, max(v['end_working_hour'] for v in records) + 2)
    axes[0].set_yticks(range(12), [f'Worker {w+1}' for w in workers]); axes[0].invert_yaxis()
    fig.suptitle(f'Same workers and jobs · {row["key"]} · bin {month+1} · provider {site}', fontsize=12)
    fig.legend(handles=[Patch(color=color, label=kind.title()) for kind, color in colors.items()], ncol=3, loc='lower center', bbox_to_anchor=(.5, .13), frameon=False, fontsize=9)
    fig.text(.5, .025, 'Illustration:first eligible four-person case/bin/provider,workers0–11. Labels show duty time;calendar gaps are not extra duty work.\n'
        'Full month horizon212.92 coordinates;axes zoom to shown tasks. Both monthly and twelve-bin mandatory flags are retained in the CSV.', ha='center', fontsize=8)
    fig.subplots_adjust(left=.10, right=.95, top=.88, bottom=.25, wspace=.18)
    path = FIG / 'network_visit_joint_order_example_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig)
    return path, dict(scenario=row['key'], seasonal_bin=month+1, provider_index=site, worker_indexes=workers, worker_task_rows=len(records),
        selection='First eligible four-person case/bin,lowest provider with both policies physically scheduling visits and collection;workers0–11.')


def plot(result, gates):
    figures = comparisons(result); example, context = calendar_example(result, gates)
    return figures + [example], context
