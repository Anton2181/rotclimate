"""Report, figures and evidence panel for the declared cohort-protected forwarding test."""
import json
from pathlib import Path
import re
import shutil
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from build_hierarchy_reach import COHORT, DATA, OUT, scenarios
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_cohort_forwarding_20261112/plan.json'
SURFACE = '#f5f3ed'; INK = '#1d2a2c'; MUTED = '#5b6664'; GRID = '#a7a6a0'
# Three-series palette checked with the dataviz validator against this surface.
COLOR = {'flat': '#2a78d6', 'excess': '#eb6834', 'capped': '#1baf7a'}
NAME = {'flat': 'Flat share (published earlier)', 'excess': 'Share of what is above the cohort', 'capped': 'Flat share, cohort kept'}
MARKER = {6: 'o', 12: 's'}


def rows(mode):
    reach = {s['id']: s for s in json.loads((OUT / f'{mode}_reach.json').read_text())['summaries']}; out = []
    for c in scenarios(mode):
        if c['share'] != .5 or c['range_days'] == 2:continue
        r = json.loads((c['folder'] / 'results.json').read_text()); m = r['shape_metrics']['all_places']
        states = [r['shape_verdict'][t][n]['state'] for t in r['shape_verdict'] for n in ('gini', 'log10_sd')]
        out.append(dict(id=c['id'], climate=mode, range_days=c['range_days'], rule=c.get('rule', 'flat'), residents=r['town_people'],
            largest=r['largest_towns'][0]['residents'], gini=m['gini'], largest_over_median=m['largest_over_median'],
            checks_within=sum(s == 'within_reference_band' for s in states), cohorts=r['active_sources'], base_cohorts=r['base_active_sources'],
            viable=r['viable_communities'], base_viable=r['base_viable_communities'], reach=reach[c['id']]['area_weighted_access_bins'],
            base_reach=reach[c['id']]['base_area_weighted_access_bins'], base_gini=r['base_shape_metrics']['all_places']['gini'],
            passed=r['people_passed_up'], at_floor=r.get('towns_left_exactly_at_floor'),
            cohorts_lost=r.get('cohorts_lost_against_base', r.get('cohorts_lost')), cohorts_gained=r.get('cohorts_gained_against_base', r.get('cohorts_gained')),
            grain_lost=r['grain_lost_on_forwarding_legs_kcal'] / r['grain_sent_on_forwarding_legs_kcal']))
    return out


def map_figure(table):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'text.color': INK})
    panels = [('6-day legs, flat 50% share: small towns lose their cohort', 'market6_50'), ('6-day legs, 50% share with the cohort kept', 'market6_50_capped')]
    fig, axes = plt.subplots(2, 1, figsize=(12.5, 12.6)); fig.patch.set_facecolor(SURFACE)
    for ax, (title, ident) in zip(axes, panels):
        ax.imshow(Image.open(DATA / f'market/corrected/{ident}_towns.webp').convert('RGB')); ax.set_xticks([]); ax.set_yticks([])
        for side in ax.spines.values():side.set_edgecolor(GRID)
        r = next(x for x in table if x['id'] == ident and x['climate'] == 'corrected')
        ax.set_title(title, loc='left', fontsize=13, pad=22)
        ax.text(0, 1.012, f"{r['cohorts']} of {r['base_cohorts']} staffed sources · reach {r['reach']:.2f} of {r['base_reach']:.2f} bins · largest town {r['largest']:,.0f} · Gini {r['gini']:.2f}",
                transform=ax.transAxes, fontsize=10, color=MUTED)
    fig.suptitle('Keeping the cohort keeps the sources and most of the hierarchy', x=.03, ha='left', fontsize=16, y=.99)
    fig.text(.03, .012, 'Corrected climate, 600 farm hours, 7.5% transfer. Circle size follows residents; dark centres mark towns with a staffed cohort;\n'
        'lines join a town to the larger market it passes people and grain to. Research scenarios on generated towns; nothing is calibrated and\n'
        'no city size, date or authority is implied. Defaults are unchanged.', fontsize=9.5, color=MUTED, linespacing=1.5)
    fig.subplots_adjust(left=.03, right=.97, top=.925, bottom=.08, hspace=.16)
    path = ROOT / 'reports/figures/settlement_cohort_maps_20261112.png'; fig.savefig(path, dpi=140, facecolor=fig.get_facecolor()); plt.close(fig)
    return path


def tradeoff_figure(table, band):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.edgecolor': GRID, 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.labelcolor': MUTED, 'text.color': INK})
    fig, ax = plt.subplots(figsize=(11.5, 6.8)); fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    ax.grid(alpha=.18, color=GRID, lw=.8); ax.set_axisbelow(True)
    ax.axhspan(band[0], band[1], color='#dfe5ea', zorder=0); ax.text(4.63, band[1] - .035, 'Range of Roman relative-size references', fontsize=9, color=MUTED, ha='right')
    chosen = [r for r in table if r['climate'] == 'corrected']; base = chosen[0]
    ax.scatter([base['base_reach']], [base['base_gini']], c='#8a9391', marker='D', s=90, edgecolors=INK, linewidths=1.4, zorder=4)
    ax.annotate('No forwarding', (base['base_reach'], base['base_gini']), xytext=(12, 0), textcoords='offset points', fontsize=9, color=INK, ha='left', va='center')
    for rule in ('flat', 'excess', 'capped'):
        for r in (x for x in chosen if x['rule'] == rule):
            ax.scatter([r['reach']], [r['gini']], c=COLOR[rule], marker=MARKER[r['range_days']], s=95, edgecolors=SURFACE, linewidths=1.5, zorder=3,
                       label=NAME[rule] if r['range_days'] == 6 else None)
            ax.annotate(f"{r['range_days']} d", (r['reach'], r['gini']), xytext=(0, 11), textcoords='offset points', fontsize=9, color=INK, ha='center')
    ax.set_xlim(4.6, 6.6); ax.set_ylim(.3, .92); ax.invert_xaxis()
    ax.set_xlabel('Seasonal two-way reach of staffed sources (area-weighted bins out of 12; fewer to the right)')
    ax.set_ylabel('Gini coefficient of town sizes')
    ax.set_title('A size hierarchy does not have to cost reach', loc='left', fontsize=14, pad=26)
    ax.text(0, 1.02, 'Corrected climate, 50% share. Circles: 6-day market legs; squares: 12-day legs. The raw climate gives the same pattern (table in the report).',
            transform=ax.transAxes, fontsize=9, color=MUTED)
    ax.legend(loc='lower right', bbox_to_anchor=(.98, .04), frameon=False, fontsize=9)
    fig.text(.07, .02, 'Relative sizes only. The flat share drains small towns below the 150-resident cohort threshold; letting a cohort-capable town keep 150 residents\n'
        'returns reach to the no-forwarding level. Nothing is fitted: every declared case is shown and none is adopted.', fontsize=9, color=MUTED, linespacing=1.5)
    fig.subplots_adjust(left=.07, right=.98, top=.86, bottom=.19)
    path = ROOT / 'reports/figures/settlement_cohort_tradeoff_20261112.png'; fig.savefig(path, dpi=160, facecolor=fig.get_facecolor()); plt.close(fig)
    return path


def main():
    review = json.loads((COHORT / 'review.json').read_text()); replay = json.loads((COHORT / 'replay.json').read_text())
    assert review['status'] == replay['status'] == 'passed' and review['plan_sha256'] == sha(PLAN)
    for path, digest in review['results_sha256'].items():assert sha(ROOT / path) == digest, path
    for path, digest in replay['byte_exact_files'].items():assert sha(COHORT / path) == digest, path
    reach_review = json.loads((OUT / 'reach_review.json').read_text()); assert reach_review['status'] == 'passed'
    for mode, digest in reach_review['results_sha256'].items():assert sha(OUT / f'{mode}_reach.json') == digest
    publication = json.loads((OUT / 'atlas_publication.json').read_text()); assert publication['manifest_sha256'] == sha(DATA / 'settlement_market.json')
    browser = json.loads((OUT / 'browser/review.json').read_text()); assert browser['status'] == 'passed' and all(c['maps'] == 20 for c in browser['cases'])
    table = rows('raw') + rows('corrected')
    band = json.loads((ROOT / 'output/settlement_size_shape_20261112/results.json').read_text())['reference_band']['all_places']['gini']
    figures = [map_figure(table), tradeoff_figure(table, band)]
    md = '|Climate|Range (days)|Passing rule|Largest town|Gini|Checks inside band|Staffed sources|Reach (bins)|People passed up|Towns held at 150|\n|---|---:|---|---:|---:|---:|---:|---:|---:|---:|\n'
    html_rows = ''
    for mode in ('raw', 'corrected'):
        b = next(r for r in table if r['climate'] == mode)
        md += f"|{mode}|–|no forwarding|{'3,066' if mode == 'raw' else '2,789'}|{b['base_gini']:.2f}|0 of 6|{b['base_cohorts']}|{b['base_reach']:.2f}|0|–|\n"
        html_rows += f"<tr><td>{mode.title()}</td><td>–</td><td>No forwarding</td><td>{b['base_gini']:.2f}</td><td>0 of 6</td><td>{b['base_cohorts']}</td><td>{b['base_reach']:.2f}</td></tr>"
        for r in sorted((x for x in table if x['climate'] == mode), key=lambda x: (x['range_days'], ['flat', 'excess', 'capped'].index(x['rule']))):
            md += (f"|{mode}|{r['range_days']}|{NAME[r['rule']].lower()}|{r['largest']:,.0f}|{r['gini']:.2f}|{r['checks_within']} of 6|{r['cohorts']}|{r['reach']:.2f}|"
                   f"{r['passed']:,.0f}|{'–' if r['at_floor'] is None else r['at_floor']}|\n")
            html_rows += (f"<tr><td>{mode.title()}</td><td>{r['range_days']} days</td><td>{NAME[r['rule']]}</td><td>{r['gini']:.2f}</td><td>{r['checks_within']} of 6</td>"
                          f"<td>{r['cohorts']}</td><td>{r['reach']:.2f}</td></tr>")
    pick = lambda ident, mode='corrected': next(r for r in table if r['id'] == ident and r['climate'] == mode)
    f6, c6, e6, c12, f12 = pick('market6_50'), pick('market6_50_capped'), pick('market6_50_excess'), pick('market12_50_capped'), pick('market12_50')
    r6 = pick('market6_50_capped', 'raw')
    report = f'''# Cohort-protected forwarding: does a size hierarchy have to cost reach?

No. When a town that can hold a cohort keeps its 150 residents and forwards
from the rest, staffed sources and reach return to the no-forwarding level
while most of the size hierarchy remains. This was the owner's chosen next test
after the market-hierarchy maps. Nothing is fitted or adopted; all defaults are
unchanged, and the eight new cases are selectable beside the earlier twelve.

## Why the test is a retention floor

The question started as "should larger centres carry larger cohorts?". In this
model a staffed town either is a source of reach or is not, and project rules
forbid turning staff numbers into a travel-strength multiplier, so a bigger
cohort living at a centre changes no reach. Larger institutions at centres
matter for reach only if their people are posted at the smaller towns. Posting
a cohort and its grain at a tributary town gives the same final distribution as
that town not sending those people and that grain up, and avoids losing grain
twice on the leg. The declared test (8e798f32) is therefore a floor: the
existing 100-person cohort plus the existing 50-person civilian minimum.

Two passing rules were declared for towns that can hold a cohort (affiliated,
civilian request of at least 50):

- **Share of what is above the cohort:** pass 50% of what the town holds above
  150 residents.
- **Flat share, cohort kept:** pass the flat 50%, reduced only as far as needed
  to stay at 150. A town holding less than 150 has no cohort to protect and
  passes the flat share as before.

Links, the 6- and 12-day ranges, grain loss of 5% per travel day, the solver,
the feasibility test and the ledgers are unchanged. People and grain leave each
town in the same proportion. The catchment draws are identical to the published
flat-share cases, and a zero floor reproduces those cases exactly; both are
hard gates in the code.

## Results

{md}
- **Keeping the cohort keeps the sources.** With 6-day legs and the flat share
  capped at the floor, {c6['cohorts']} of {c6['base_cohorts']} corrected-climate sources stay staffed
  ({f6['cohorts']} under the plain flat share) and reach is {c6['reach']:.2f} bins against {c6['base_reach']:.2f} with
  no forwarding. In the raw climate {r6['cohorts']} sources are staffed against {r6['base_cohorts']} with no
  forwarding, because a few receiving towns rise above the threshold.
- **Most of the hierarchy survives.** The largest town is {c6['largest']:,.0f} residents
  ({f6['largest']:,.0f} under the plain flat share), the Gini is {c6['gini']:.2f} ({f6['gini']:.2f}), and all six
  declared checks stay inside the reference range in both climates at 6 days.
  The reason is that most forwarded people come from towns well above the
  floor: {c6['passed']:,.0f} people are passed up against {f6['passed']:,.0f}, and {c6['at_floor']} towns are
  held exactly at 150.
- **Passing only the excess is weaker.** It keeps {e6['cohorts']} sources but the Gini falls
  to {e6['gini']:.2f} and only {e6['checks_within']} of 6 checks stay inside the range.
- **Twelve-day legs still lose some sources.** {c12['cohorts']} of {c12['base_cohorts']} stay staffed
  ({f12['cohorts']} under the plain flat share). The remaining loss is not the passing
  rule: longer legs lose more grain, the solver draws fewer people from some
  catchments, and those towns never reach 150.
- **Small unstaffed places still shrink under the capped rule.** Communities
  meeting the 50-civilian minimum fall from {c6['base_viable']:,} to {c6['viable']} (corrected, 6 days),
  because towns below the floor pass the flat share. The excess rule keeps {e6['viable']:,}.

![Settlement maps with and without the cohort floor](figures/{figures[0].name})

![Size hierarchy against reach under three passing rules](figures/{figures[1].name})

## What this does and does not show

As fixed in advance: the cost in reach seen in the flat-share scenarios was a
consequence of the passing rule, not of hierarchy itself, within this ledger.
It does not show that either rule is how markets or institutions worked, and
neither is selected as calibrated.

- The floor, the 50% share, the ranges and same-actor links are scenarios.
- The cases use the original coupled parents. Staff collection hours, the
  continuous destination inventories and the worker calendars developed on the
  other line do not yet constrain forwarded grain.
- The cohort is still one fixed group of 100 per town. Whether large centres
  should hold additional institutions is not tested; under the binary source
  rule it would not change reach.
- Relative sizes only; the Roman references are conditional, area-based and
  from one exposed catalogue. Cereal only.

## Review

The independent reviewer recomputes what every town holds and passes by
recursion from the roots, with its own implementation of both rules, then
redistributes grain, recomputes pooled food with a separate monthly recurrence
and checks that the floor is honoured, that draws equal the published
flat-share cases, population and grain closure, the cohort rule, work-limited
production, the rural source gate and all metrics for all eight cases. Reach
masks for all twenty hierarchy cases are rebuilt by a second, dense
implementation. Fresh runs reproduce all 16 result and field files byte for
byte. Seventeen unit tests cover the passing rules.

In the atlas the market-hierarchy family now holds ten cases per climate (40
map options over Settlements and Supply-supported reach); all load with exact
audit downloads, other families still load, the default is unchanged, and
{publication['existing_data_files_unchanged']:,} existing atlas data files are verified unchanged.

## Whole-plan review and next work

Release 2 now has a forwarding rule that reaches the reference shape without
losing sources, still as an uncalibrated scenario. The remaining step on this
line is to re-run forwarding on the other line's dispatch-limited parents, so
that collection work, destination inventories and worker calendars constrain
forwarded grain; that needs its own declaration and should follow the other
line's continuous collection calendar. Absolute sizes, urban share, dated
occupancy, the failed geographic transfer, complete diets and work, and S5
remain open on the [live queue](SETTLEMENT_CONTROL_ROADMAP_20261110.md).

Reproduce:

```sh
.venv/bin/python -I scripts/build_settlement_cohort_forwarding.py --mode corrected --days 6 --rule capped
.venv/bin/python -I scripts/review_settlement_cohort_forwarding.py
.venv/bin/python -I scripts/replay_settlement_cohort_forwarding.py
.venv/bin/python -I scripts/build_hierarchy_reach.py --mode corrected
.venv/bin/python -I scripts/review_hierarchy_reach.py
.venv/bin/python -I scripts/publish_settlement_market.py
.venv/bin/python -I scripts/publish_settlement_cohort_evidence.py
```
'''
    (ROOT / 'reports/SETTLEMENT_COHORT_FORWARDING_20261112.md').write_text(report)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    write(COHORT / 'summary.json', dict(status='eight_declared_cases_reported_with_flat_share_comparators', adopt=False, rows=table, reference_band_gini_all_places=band))
    for source, name in [(COHORT / 'summary.json', 'settlement_cohort_summary.json'), (COHORT / 'review.json', 'settlement_cohort_review.json'),
        (COHORT / 'replay.json', 'settlement_cohort_replay.json'), (PLAN, 'settlement_cohort_plan.json')]:shutil.copyfile(source, data / name)
    section = f'''<!--settlement-cohort-start--><section><h2>Cohort-protected forwarding: hierarchy without losing reach</h2><details id="settlement-cohort" class="panel"><summary>8 declared cases · keeping each town's cohort restores reach and keeps most of the hierarchy · no fit</summary>
<p>The earlier market-hierarchy maps showed large centres at a cost in staffed sources and reach. A staffed town is a source of reach or it is not, so larger cohorts living at a centre would change nothing; what matters is whether the smaller towns keep theirs. The declared test lets a town that can hold a cohort keep 150 residents (the existing cohort plus civilian minimum) and forward from the rest, under two rules.</p>
<p><strong>A size hierarchy does not have to cost reach.</strong> With 6-day legs and the flat 50% share capped at the floor, {c6['cohorts']} of {c6['base_cohorts']} corrected-climate sources stay staffed ({f6['cohorts']} under the plain flat share) and reach is {c6['reach']:.2f} bins against {c6['base_reach']:.2f} with no forwarding. The largest town is still {c6['largest']:,.0f} residents, the Gini {c6['gini']:.2f}, and all six declared checks stay inside the range of the Roman relative-size references in both climates. Passing only what is above the cohort keeps the sources too but weakens the hierarchy (Gini {e6['gini']:.2f}). With 12-day legs {c12['cohorts']} sources remain; the rest is grain lost on long legs, not the passing rule.</p>
<div class="table"><table><thead><tr><th>Climate</th><th>Market range</th><th>Passing rule</th><th>Gini</th><th>Checks inside band</th><th>Staffed sources</th><th>Reach (bins)</th></tr></thead><tbody>{html_rows}</tbody></table></div>
<img src="../../reports/figures/{figures[0].name}" alt="Two settlement maps with 6-day legs: flat share, and flat share with the cohort kept">
<img src="../../reports/figures/{figures[1].name}" alt="Gini coefficient of town sizes against seasonal reach for the flat share and the two cohort-protected rules">
<p>The floor, share, ranges and rules are scenarios; every declared case is shown and none is adopted. The cases use the original coupled parents, so collection work and worker calendars do not yet constrain forwarded grain. Relative sizes say nothing about absolute city size, date, location or authority. The eight maps are selectable in the Earth atlas under Experimental &amp; diagnostics, in Settlements and Supply-supported reach. All defaults are unchanged.</p>
<p><a href="../../reports/SETTLEMENT_COHORT_FORWARDING_20261112.md">Methods, full table and limits</a> · <a href="../earth_fit/#layer=reach_towns&amp;climate=corrected">Open the Settlements map</a> · <a href="data/settlement_cohort_summary.json" download>All results with comparators</a> · <a href="data/settlement_cohort_review.json" download>Independent review</a> · <a href="data/settlement_cohort_replay.json" download>Fresh byte replay</a> · <a href="data/settlement_cohort_plan.json" download>Prior declaration</a></p></details></section><!--settlement-cohort-end-->'''
    html = page.read_text(); pattern = r'<!--settlement-cohort-start-->[\s\S]*?<!--settlement-cohort-end-->'
    if re.search(pattern, html):html = re.sub(pattern, lambda match: section, html)
    else:
        assert '<!--settlement-market-start-->' in html; html = html.replace('<!--settlement-market-start-->', section + '\n<!--settlement-market-start-->', 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='settlement_cohort_forwarding_20261112', status='model_only_declared_mechanism_scenarios_scored_on_exposed_shape_band', evidence='reports/SETTLEMENT_COHORT_FORWARDING_20261112.md',
        note='Eight declared cohort-protected forwarding cases (6 and 12 day legs, 50 percent share, two passing rules) compared with the exposed Roman relative-size band. Development only; no floor, rule, size or default adopted.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]; write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(COHORT / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page), publisher_sha256=sha(Path(__file__)),
        figures_sha256={str(p.relative_to(ROOT)): sha(p) for p in figures}))
    for p in figures:print(p)
    print('Published the cohort-protected forwarding panel, report and figures; defaults unchanged.')


if __name__ == '__main__':main()
