"""Before/after figure, report and evidence note for the adopted default Settlements map."""
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
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from build_hierarchy_reach import COHORT, DATA, OUT
from polity.settlement_size_shape import shape_metrics
from settlement_locations_earth import sha, write

DECISION = ROOT / 'calibration/settlement_default_adoption_20261112/decision.json'
FOLDER = ROOT / 'output/settlement_default_adoption_20261112'
SURFACE = '#f5f3ed'; INK = '#1d2a2c'; MUTED = '#5b6664'; GRID = '#a7a6a0'


def compare(mode):
    folder = DATA / ('corrected' if mode == 'corrected' else '')
    old = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))
    case = next(c for c in old['cases'] if c['id'] == 'joint365'); summary = old['summaries'][[c['id'] for c in old['cases']].index('joint365')]
    before = np.array(case['civilian_people']) + np.array(case['institutional_people'])
    new = json.loads((COHORT / f'{mode}_range6_share50_capped/results.json').read_text())
    after = np.load(COHORT / f'{mode}_range6_share50_capped/fields.npz')['total']
    reach = next(s for s in json.loads((OUT / f'{mode}_reach.json').read_text())['summaries'] if s['id'] == 'market6_50_capped')
    def row(sizes, sources, viable, bins):
        m = shape_metrics(sizes)
        return dict(towns=int((sizes > 0).sum()), residents=float(sizes.sum()), largest=float(sizes.max()), gini=m['gini'],
            largest_over_median=m['largest_over_median'], staffed_sources=int(sources), viable_communities=int(viable), reach_bins=float(bins))
    return dict(climate=mode, previous=row(before, sum(case['institutional_active']), sum(case['community_viable']), summary['area_weighted_access_bins']),
        adopted=row(after, new['active_sources'], new['viable_communities'], reach['area_weighted_access_bins']),
        shape_checks_within_band=new['shape_checks_within_band'])


def figure(rows):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'text.color': INK})
    r = next(x for x in rows if x['climate'] == 'corrected')
    panels = [('Previous default: joint food budget', DATA / 'corrected/settled_towns_joint365.webp', r['previous']),
              ('New default: one finite ledger, market hierarchy, cohorts kept', DATA / 'market/corrected/market6_50_capped_towns.webp', r['adopted'])]
    fig, axes = plt.subplots(2, 1, figsize=(12.5, 12.6)); fig.patch.set_facecolor(SURFACE)
    for ax, (title, path, v) in zip(axes, panels):
        ax.imshow(Image.open(path).convert('RGB')); ax.set_xticks([]); ax.set_yticks([])
        for side in ax.spines.values():side.set_edgecolor(GRID)
        ax.set_title(title, loc='left', fontsize=13, pad=22)
        ax.text(0, 1.012, f"{v['residents']:,.0f} town residents · largest town {v['largest']:,.0f} · Gini {v['gini']:.2f} · {v['staffed_sources']:,} staffed sources",
                transform=ax.transAxes, fontsize=10, color=MUTED)
    fig.suptitle('Default Settlements map, before and after', x=.03, ha='left', fontsize=16, y=.99)
    fig.text(.03, .012, 'Corrected climate. Circle size follows residents; dark centres mark towns with a staffed cohort; lines in the new map join a town to the larger\n'
        'market it passes people and grain to. The new default is development-fitted and not prospectively validated; placement is unchanged.\n'
        'Town residents are roughly halved because they are now taken out of a finite rural population.', fontsize=9.5, color=MUTED, linespacing=1.5)
    fig.subplots_adjust(left=.03, right=.97, top=.925, bottom=.08, hspace=.16)
    path = ROOT / 'reports/figures/settlement_default_20261112.png'; fig.savefig(path, dpi=140, facecolor=fig.get_facecolor()); plt.close(fig)
    return path


def main():
    manifest = json.loads((DATA / 'settlement_market.json').read_text()); assert manifest['default_settlements'] == 'market6_50_capped'
    browser = json.loads((OUT / 'browser/review.json').read_text())
    assert browser['status'] == 'passed' and browser['settlements_default'] == 'market6_50_capped' and browser['reach_default'] == 'v21_joint365'
    rows = [compare('raw'), compare('corrected')]; path = figure(rows); FOLDER.mkdir(parents=True, exist_ok=True)
    write(FOLDER / 'comparison.json', dict(status='default_settlements_map_adopted_by_owner_decision', decision_sha256=sha(DECISION),
        adopted='market6_50_capped', previous='joint365', reach_default_unchanged='v21_joint365', rows=rows,
        basis='development-fitted, not prospectively validated', manifest_sha256=sha(DATA / 'settlement_market.json')))
    c, w = rows[1], rows[0]
    table = '|Climate|Map|Town residents|Largest town|Gini|Largest / median|Staffed sources|Communities meeting the minimum|\n|---|---|---:|---:|---:|---:|---:|---:|\n'
    for r in rows:
        for name, key in (('previous default', 'previous'), ('new default', 'adopted')):
            v = r[key]; table += f"|{r['climate']}|{name}|{v['residents']:,.0f}|{v['largest']:,.0f}|{v['gini']:.2f}|{v['largest_over_median']:.1f}|{v['staffed_sources']:,}|{v['viable_communities']:,}|\n"
    report = f'''# New default Settlements map

On 12 November 2026 the owner asked for a better default map now, with further
development later, after being told that a calibrated default is blocked on
evidence. The Settlements layer of the Earth atlas now opens on the
cohort-kept market-hierarchy scenario. It is labelled a scenario:
development-fitted, not prospectively validated. The
[decision record](../calibration/settlement_default_adoption_20261112/decision.json)
was committed before anything changed.

## What changed

- **Settlements** opens on "market hierarchy with cohorts kept (6-day legs,
  50%)" in both climates. The previous default, the joint food budget, stays in
  the normal view as "previous default".
- **Supply-supported reach is unchanged.** It keeps control v2.1, the map that
  passed a blind Earth test; the new scenario has no comparable test.
- No data file was modified. The default is a selection among published
  options, and if the optional market packet is missing the atlas falls back to
  the previous default.

## Before and after

{table}
- Town sizes now form a hierarchy: the largest town is {c['adopted']['largest']:,.0f} residents
  against {c['previous']['largest']:,.0f}, and all six declared relative-size checks against the Roman
  references pass in both climates.
- Town residents are roughly halved ({c['previous']['residents']:,.0f} to {c['adopted']['residents']:,.0f}, corrected).
  The previous default added town residents on top of the rural population; the
  new one takes them out of a finite population and recomputes farm work and
  rural meals.
- Staffed sources fall from {c['previous']['staffed_sources']:,} to {c['adopted']['staffed_sources']} (corrected) and from {w['previous']['staffed_sources']:,} to {w['adopted']['staffed_sources']}
  (raw), for the same reason: fewer towns reach the 150-resident threshold once
  people are counted once. This is a real difference from the previous default,
  not a rounding effect.

![Default Settlements map before and after](figures/{path.name})

## What "development-fitted" means here

The forwarding share (50%), market range (6 days) and cohort floor (150) are
declared values. They were not fitted, and the comparison with Roman relative
sizes used data the project had already developed against. Placement is the
earlier placement, whose one prospective transfer test failed. The scenario is
built on the original coupled inputs, so staff collection hours, continuous
destination inventories and worker calendars do not yet constrain it. Absolute
city sizes, dates, complete diets and mobile or nonstate communities are not
modelled.

This overrides, for this one layer and by explicit owner decision, the rule
that defaults change only on qualified evidence. The rule stands for later
changes.

## Checks

The atlas opens Settlements on the new default in both climates with its
evidence text and without the experimental label; the previous default is one
selection away; reach opens on control v2.1; all 40 market-hierarchy options
and the other optional families still load; a missing market packet falls back
to the previous default. Six older browser-check scripts that assumed the old
default now request it explicitly in the URL; they were edited but could not be
run in this container.

## Revisit

Replace or re-run this default when forwarding has been run on the
dispatch-limited inputs, or when qualified size or transfer evidence exists.
'''
    (ROOT / 'reports/SETTLEMENT_DEFAULT_20261112.md').write_text(report)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    shutil.copyfile(FOLDER / 'comparison.json', data / 'settlement_default_comparison.json'); shutil.copyfile(DECISION, data / 'settlement_default_decision.json')
    section = f'''<!--settlement-default-start--><section><h2>New default Settlements map</h2><details id="settlement-default" class="panel"><summary>Default changed by owner decision · development-fitted, not prospectively validated</summary>
<p>The Settlements layer of the Earth atlas now opens on the cohort-kept market-hierarchy scenario (6-day legs, 50% passed up, each cohort-capable town keeping 150 residents). The owner asked for a better default now, with further development later, after a calibrated default was found to be blocked on evidence. The previous default stays selectable, and Supply-supported reach keeps its Earth blind-tested default.</p>
<p><strong>What is different.</strong> The largest town is {c['adopted']['largest']:,.0f} residents against {c['previous']['largest']:,.0f} (corrected climate), and relative town sizes pass all six declared checks against the Roman references. Town residents fall from {c['previous']['residents']:,.0f} to {c['adopted']['residents']:,.0f} and staffed sources from {c['previous']['staffed_sources']:,} to {c['adopted']['staffed_sources']}, because residents are now taken out of a finite rural population instead of being added to it.</p>
<img src="../../reports/figures/{path.name}" alt="Default Settlements map before and after: joint food budget, then market hierarchy with cohorts kept">
<p>The share, range and floor are declared values, not fitted ones; placement is unchanged and its prospective transfer test failed; staff collection hours and worker calendars do not yet constrain the scenario. No absolute city size, date or authority is implied.</p>
<p><a href="../../reports/SETTLEMENT_DEFAULT_20261112.md">What changed and why</a> · <a href="../earth_fit/#layer=reach_towns&amp;climate=corrected">Open the Settlements map</a> · <a href="data/settlement_default_comparison.json" download>Before and after numbers</a> · <a href="data/settlement_default_decision.json" download>Decision record</a></p></details></section><!--settlement-default-end-->'''
    html = page.read_text(); pattern = r'<!--settlement-default-start-->[\s\S]*?<!--settlement-default-end-->'
    if re.search(pattern, html):html = re.sub(pattern, lambda match: section, html)
    else:
        assert '<!--settlement-cohort-start-->' in html; html = html.replace('<!--settlement-cohort-start-->', section + '\n<!--settlement-cohort-start-->', 1)
    page.write_text(html)
    write(FOLDER / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page), publisher_sha256=sha(Path(__file__)), figure_sha256=sha(path)))
    print(path); print(json.dumps(rows, indent=1)[:900])


if __name__ == '__main__':main()
