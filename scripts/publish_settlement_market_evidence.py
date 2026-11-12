"""Report, figures and evidence panel for the two declared market-hierarchy tests."""
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
from build_hierarchy_reach import BASE, DATA, OUT, TWO_DAY, scenarios
from settlement_locations_earth import sha, write

SURFACE = '#f5f3ed'; INK = '#1d2a2c'; MUTED = '#5b6664'; GRID = '#a7a6a0'
COLOR = {'corrected': '#2a78d6', 'raw': '#ad643b'}; MARKER = {'corrected': 'o', 'raw': 'D'}   # validated pair on this surface
PLANS = [ROOT / 'calibration/settlement_hierarchy_20261112/plan.json', ROOT / 'calibration/settlement_market_range_20261112/plan.json']


def rows(mode):
    reach = {s['id']: s for s in json.loads((OUT / f'{mode}_reach.json').read_text())['summaries']}
    base = json.loads((BASE / f'{mode}_h600_f0.075/results.json').read_text()); out = []
    for c in scenarios(mode):
        if c.get('rule'):continue                      # cohort-protected variants have their own report
        r = json.loads((c['folder'] / 'results.json').read_text()); m = r['shape_metrics']['all_places']
        states = [r['shape_verdict'][t][n]['state'] for t in r['shape_verdict'] for n in ('gini', 'log10_sd')]
        out.append(dict(id=c['id'], climate=mode, range_days=c['range_days'], share=c['share'], residents=r['town_people'],
            largest=r['largest_towns'][0]['residents'], gini=m['gini'], top1=m['share_largest_1_percent'],
            largest_over_median=m['largest_over_median'], slope=m['rank_size_slope_top100'],
            checks_within=sum(s == 'within_reference_band' for s in states), supported=r['shape_supported'],
            cohorts=r['active_sources'], viable=r['viable_communities'], reach=reach[c['id']]['area_weighted_access_bins'],
            parents=r['forest']['towns_with_parent'], towns=r['forest']['towns'], max_children=r['forest']['maximum_children'],
            leg_median=r['legs']['days_median'], grain_lost=r['grain_lost_on_forwarding_legs_kcal'] / max(1., r['grain_sent_on_forwarding_legs_kcal']),
            base_residents=base['town_people'], base_cohorts=base['active_sources'], base_viable=base['viable_communities'],
            base_gini=r['base_shape_metrics']['all_places']['gini'], base_largest=float(max(r['base_shape_metrics']['all_places']['largest_over_median'], 0)),
            base_reach=reach[c['id']]['base_area_weighted_access_bins']))
    return out


def map_figure(table):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'text.color': INK})
    panels = [('Coupled scenario without forwarding', DATA / 'feedback/corrected/feedback600_75_towns.webp', None),
              ('6-day market legs, 50% passed up', DATA / 'market/corrected/market6_50_towns.webp', 'market6_50'),
              ('12-day market legs, 50% passed up', DATA / 'market/corrected/market12_50_towns.webp', 'market12_50')]
    fig, axes = plt.subplots(3, 1, figsize=(12.5, 18.2)); fig.patch.set_facecolor(SURFACE)
    for ax, (title, path, ident) in zip(axes, panels):
        ax.imshow(Image.open(path).convert('RGB')); ax.set_xticks([]); ax.set_yticks([])
        for side in ax.spines.values():side.set_edgecolor(GRID)
        if ident:
            r = next(x for x in table if x['id'] == ident and x['climate'] == 'corrected')
            detail = f"largest town {r['largest']:,.0f} residents · Gini {r['gini']:.2f} · {r['cohorts']} staffed sources · {r['residents']:,.0f} town residents"
        else:
            r = next(x for x in table if x['climate'] == 'corrected')
            detail = f"largest town 2,789 residents · Gini {r['base_gini']:.2f} · {r['base_cohorts']} staffed sources · {r['base_residents']:,.0f} town residents"
        ax.set_title(title, loc='left', fontsize=13, pad=22); ax.text(0, 1.012, detail, transform=ax.transAxes, fontsize=10, color=MUTED)
    fig.suptitle('Settlements with market forwarding: larger centres appear, small towns shrink', x=.03, ha='left', fontsize=16, y=.993)
    fig.text(.03, .012, 'Corrected climate, 600 farm hours, 7.5% transfer. Circle size follows residents; dark centres mark towns that keep a staffed cohort;\n'
        'lines join a town to the larger market it passes its share to. Research scenarios on generated towns: the share and range are not\n'
        'calibrated, and no city size, date or authority is implied. Defaults are unchanged.', fontsize=9.5, color=MUTED, linespacing=1.5)
    fig.subplots_adjust(left=.03, right=.97, top=.94, bottom=.055, hspace=.13)
    path = ROOT / 'reports/figures/settlement_market_maps_20261112.png'; fig.savefig(path, dpi=140, facecolor=fig.get_facecolor()); plt.close(fig)
    return path


def tradeoff_figure(table, band):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.edgecolor': GRID, 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.labelcolor': MUTED, 'text.color': INK})
    fig, ax = plt.subplots(figsize=(11.5, 6.6)); fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    ax.grid(alpha=.18, color=GRID, lw=.8); ax.set_axisbelow(True)
    ax.axhspan(band[0], band[1], color='#dfe5ea', zorder=0); ax.text(4.23, band[1] - .035, 'Range of Roman relative-size references', fontsize=9, color=MUTED, ha='right')
    for mode in ('corrected', 'raw'):
        chosen = [r for r in table if r['climate'] == mode]; first = chosen[0]
        ax.scatter([first['base_reach']], [first['base_gini']], c=COLOR[mode], marker=MARKER[mode], s=90, edgecolors=INK, linewidths=1.4, zorder=4,
                   label=f'{mode.title()} climate')
        for r in chosen:
            ax.scatter([r['reach']], [r['gini']], c=COLOR[mode], marker=MARKER[mode], s=60, edgecolors=SURFACE, linewidths=1.3, zorder=3)
    for ident in sorted({r['id'] for r in table}):            # one label per scenario, above its pair of climate points
        pair = [r for r in table if r['id'] == ident]; r = pair[0]
        if r['range_days'] == 2 and r['share'] == .25:continue
        text = 'No forwarding, and 2-day links' if r['range_days'] == 2 else f"{r['range_days']}-day legs · {round(100 * r['share'])}% passed up"
        below = r['range_days'] == 6 and r['share'] == .25
        ax.annotate(text, (np.mean([q['reach'] for q in pair]), (min if below else max)(q['gini'] for q in pair)), xytext=(0, -20 if below else 12),
                    textcoords='offset points', fontsize=9, color=INK, ha='center')
    ax.set_xlim(4.2, 6.5); ax.set_ylim(.3, .92); ax.invert_xaxis()
    ax.set_xlabel('Seasonal two-way reach of staffed sources (area-weighted bins out of 12; fewer to the right)')
    ax.set_ylabel('Gini coefficient of town sizes')
    ax.set_title('More size hierarchy costs staffed sources and reach', loc='left', fontsize=14, pad=26)
    ax.text(0, 1.02, 'Each point is one declared scenario: market range in days each way, and the share of residents and grain passed up. Outlined points: no forwarding.',
            transform=ax.transAxes, fontsize=9, color=MUTED)
    ax.legend(loc='upper left', frameon=False, fontsize=9)
    fig.text(.07, .02, 'Relative sizes only. Reach shrinks because small towns that pass people up fall below the 150-resident cohort threshold; the cohort rule is unchanged.\n'
        'Nothing is fitted: both shares and both ranges are reported, and none is adopted.', fontsize=9, color=MUTED, linespacing=1.5)
    fig.subplots_adjust(left=.07, right=.98, top=.86, bottom=.19)
    path = ROOT / 'reports/figures/settlement_market_tradeoff_20261112.png'; fig.savefig(path, dpi=160, facecolor=fig.get_facecolor()); plt.close(fig)
    return path


def main():
    for family in (TWO_DAY, OUT):
        review = json.loads((family / 'review.json').read_text()); replay = json.loads((family / 'replay.json').read_text())
        assert review['status'] == replay['status'] == 'passed'
        for path, digest in review['results_sha256'].items():assert sha(ROOT / path) == digest, path
        for path, digest in replay['byte_exact_files'].items():assert sha(family / path) == digest, path
    publication = json.loads((OUT / 'atlas_publication.json').read_text()); assert publication['manifest_sha256'] == sha(DATA / 'settlement_market.json')
    browser = json.loads((OUT / 'browser/review.json').read_text()); assert browser['status'] == 'passed'
    table = rows('raw') + rows('corrected')
    band = json.loads((ROOT / 'output/settlement_size_shape_20261112/results.json').read_text())['reference_band']['all_places']['gini']
    figures = [map_figure(table), tradeoff_figure(table, band)]
    md = '|Climate|Range (days)|Share|Towns with a market|Town residents|Largest town|Gini|Largest / median|Checks inside band|Staffed sources|Reach (bins)|Grain lost on legs|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    html_rows = ''
    for mode in ('raw', 'corrected'):
        b = next(r for r in table if r['climate'] == mode)
        md += f"|{mode}|none|–|0|{b['base_residents']:,.0f}|{'3,066' if mode == 'raw' else '2,789'}|{b['base_gini']:.2f}|{b['base_largest']:.1f}|0 of 6|{b['base_cohorts']}|{b['base_reach']:.2f}|–|\n"
        html_rows += f"<tr><td>{mode.title()}</td><td>No forwarding</td><td>–</td><td>{b['base_residents']:,.0f}</td><td>{b['base_gini']:.2f}</td><td>0 of 6</td><td>{b['base_cohorts']}</td><td>{b['base_reach']:.2f}</td></tr>"
        for r in (x for x in table if x['climate'] == mode):
            md += (f"|{mode}|{r['range_days']}|{round(100 * r['share'])}%|{r['parents']:,} of {r['towns']:,}|{r['residents']:,.0f}|{r['largest']:,.0f}|{r['gini']:.2f}|"
                   f"{r['largest_over_median']:.1f}|{r['checks_within']} of 6|{r['cohorts']}|{r['reach']:.2f}|{100 * r['grain_lost']:.0f}%|\n")
            html_rows += (f"<tr><td>{mode.title()}</td><td>{r['range_days']} days</td><td>{round(100 * r['share'])}%</td><td>{r['residents']:,.0f}</td><td>{r['gini']:.2f}</td>"
                          f"<td>{r['checks_within']} of 6</td><td>{r['cohorts']}</td><td>{r['reach']:.2f}</td></tr>")
    c6 = next(r for r in table if r['id'] == 'market6_50' and r['climate'] == 'corrected'); c12 = next(r for r in table if r['id'] == 'market12_50' and r['climate'] == 'corrected')
    c2 = next(r for r in table if r['id'] == 'market2_50' and r['climate'] == 'corrected')
    report = f'''# Market hierarchy: can forwarding between towns produce large centres?

Two declared mechanism tests follow the size-shape diagnostic, which found that
the coupled allocator has no large centres. Both use one mechanism inside the
existing finite ledger. Twelve research maps are now selectable in the normal
Earth atlas; nothing is fitted or adopted, and all defaults are unchanged.

## Mechanism

Every town passes a fixed share of the residents and of the collected grain it
holds to a larger market: the linked town of the same actor with the largest
catchment budget, if that budget is larger than its own. The receiving town
passes the same share of everything it holds to its own market, and so on. A
catchment's draw of people is found by the existing coupled solver with its
existing upper bound, so people leave their origin cells once and rural work
and meals are recomputed exactly as before. Each forwarding leg loses grain and
adds the existing one-month delay. A catchment's draw is accepted only if the
stream that travels its whole chain is still fed every month. The 100-person
cohort and 50-person minimum apply to the people actually present afterwards.

The tests differ only in which towns are linked:

- **Two-day links** (declaration f17deb2a): a town inside the cached two-way
  patrol footprint in all twelve monthly bins. Each leg keeps 95% of the grain.
- **Longer market legs** (declaration 2b2fea71): at most 6 or 12 days each way in
  all twelve bins on the seasonal transport graph (foot, roads, tracks, ferries,
  rivers, harbours, sailing). Each leg keeps 95% per day of its slowest month.

Shares of 25% and 50% are tested in both. With no forwarding the code must
reproduce the published coupled scenario exactly, and it does.

## Results

All scenarios use 600 farm hours and the 7.5% transfer allowance. "Checks
inside band" counts the six declared checks (Gini and log standard deviation at
three tail levels) that fall inside the range of the Roman relative-size
references. Reach is the area-weighted number of monthly bins with two-way
access from a staffed source.

{md}
- **Two-day links are nearly inert.** Only {c2['parents']} of {c2['towns']:,} corrected towns can reach a
  larger same-actor town all year within two days. The Gini moves from {c2['base_gini']:.2f} to
  {c2['gini']:.2f}. Towns sit four to six travel days apart.
- **Longer legs produce a hierarchy.** With a 50% share the Gini reaches
  {c6['gini']:.2f} at 6 days and {c12['gini']:.2f} at 12 days (corrected), the largest town grows from
  2,789 to {c6['largest']:,.0f} and {c12['largest']:,.0f} residents, and all six declared checks sit inside
  the reference range in both climates. A 25% share gets partway: the upper
  tail is inside the range, the full distribution is still too equal.
- **The hierarchy has a price.** At 50% the staffed sources fall from {c6['base_cohorts']} to
  {c6['cohorts']} and {c12['cohorts']}, because small towns that pass people up drop below the
  150-resident cohort threshold; reach falls from {c6['base_reach']:.2f} to {c6['reach']:.2f} and {c12['reach']:.2f} bins.
  Forwarding legs lose {100 * c6['grain_lost']:.0f}% of the grain sent at 6 days and {100 * c12['grain_lost']:.0f}% at 12
  days, and total town residents fall by {100 * (1 - c6['residents'] / c6['base_residents']):.1f}% and {100 * (1 - c12['residents'] / c12['base_residents']):.1f}%.

![Settlement maps before and after forwarding](figures/{figures[0].name})

![Size hierarchy against reach](figures/{figures[1].name})

## What this does and does not show

As fixed in advance: entering the reference range shows that this mechanism
*can* produce a Roman-like relative hierarchy under these assumptions. It does
not validate the share, the range, the link rule, absolute sizes, locations or
dates. Both shares and both ranges are published side by side and none is
selected as calibrated.

- The scenarios are built on the original coupled parents (061e6ef8). The later
  dispatch versions also limit collection by staff hours; forwarding has not
  been re-run on them, so staff work does not yet constrain forwarded grain.
- The cohort is a fixed 100 people per town. A larger centre gets no more staff,
  which is why hierarchy only removes sources here. Whether large centres
  should support more or different institutions is an open S3 question.
- Same-actor links only. Sites without an actor stay unlinked, which is missing
  evidence and not a claim that they have no markets.
- The Roman references are conditional area-based sizes from an exposed
  catalogue; one empire at one date is not a universal target.
- Cereal only. Other foods, household and draft work, mobile and nonstate
  communities remain open.

## Review

The independent reviewer rebuilds the links (from footprints or travel times)
and the forest with its own code, walks every catchment up its chain for
people and grain, recomputes pooled and full-chain food with a separate monthly
recurrence, and checks population and grain closure, the cohort rule,
work-limited production, the rural source gate and all metrics for all twelve
cases. Stored travel times are spot-checked by reverse searches (about 9,900
town pairs per climate). Reach masks are rebuilt by a second, dense
implementation. Fresh runs reproduce all 24 result and field files byte for
byte. Ten unit tests cover the forwarding rules.

In the atlas, all 24 map options (12 per climate, Settlements and
Supply-supported reach) load with exact audit downloads; other scenario
families still load, the default is unchanged and a missing manifest leaves
everything else available. {publication['existing_data_files_unchanged']:,} existing atlas data files are verified
unchanged.

## Whole-plan review and next work

Release 2 gains a mechanism that can reach the reference shape, not a
calibrated size model. The next declared steps on this line are: re-run the
forwarding on the threshold-seeded dispatch parents so collection work limits
forwarded grain; and test whether larger centres should carry larger
institutions, which decides whether hierarchy must cost reach. Absolute sizes,
urban share, dated occupancy, the failed geographic transfer, complete diets
and work, and S5 remain open on the [live queue](SETTLEMENT_CONTROL_ROADMAP_20261110.md).

Reproduce:

```sh
.venv/bin/python -I scripts/build_settlement_hierarchy.py --mode corrected --share 0.5
.venv/bin/python -I scripts/build_settlement_market_range.py --mode corrected --travel
.venv/bin/python -I scripts/build_settlement_market_range.py --mode corrected --days 6 --share 0.5
.venv/bin/python -I scripts/review_settlement_hierarchy.py --family market
.venv/bin/python -I scripts/replay_settlement_hierarchy.py --family market
.venv/bin/python -I scripts/build_hierarchy_reach.py --mode corrected
.venv/bin/python -I scripts/review_hierarchy_reach.py
.venv/bin/python -I scripts/publish_settlement_market.py
.venv/bin/python -I scripts/publish_settlement_market_evidence.py
```
'''
    (ROOT / 'reports/SETTLEMENT_HIERARCHY_20261112.md').write_text(report)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    write(OUT / 'summary.json', dict(status='twelve_declared_cases_reported', adopt=False, rows=table, reference_band_gini_all_places=band))
    for source, name in [(OUT / 'summary.json', 'settlement_market_summary.json'), (TWO_DAY / 'review.json', 'settlement_market_review_two_day.json'),
        (OUT / 'review.json', 'settlement_market_review_longer_legs.json'), (OUT / 'replay.json', 'settlement_market_replay.json'),
        (PLANS[0], 'settlement_market_plan_two_day.json'), (PLANS[1], 'settlement_market_plan_longer_legs.json')]:shutil.copyfile(source, data / name)
    section = f'''<!--settlement-market-start--><section><h2>Market hierarchy: forwarding between towns</h2><details id="settlement-market" class="panel"><summary>12 declared scenarios · longer market legs can produce large centres, at a cost in reach · no fit</summary>
<p>The size-shape diagnostic found no large centres in the coupled allocator. Two declared tests let every town pass a fixed share of its residents and collected grain to the largest same-actor town it can reach all year, inside the same finite people, work and grain ledger. People are counted once and every forwarding leg loses grain.</p>
<p><strong>Two-day links do almost nothing; 6- and 12-day market legs produce a hierarchy.</strong> Only {c2['parents']} of {c2['towns']:,} corrected towns have a larger town within two days. With longer legs and a 50% share the Gini coefficient rises from {c6['base_gini']:.2f} to {c6['gini']:.2f} and {c12['gini']:.2f}, the largest town from 2,789 to {c6['largest']:,.0f} and {c12['largest']:,.0f} residents, and all six declared checks fall inside the range of the Roman relative-size references in both climates. The price: staffed sources fall from {c6['base_cohorts']} to {c6['cohorts']} and {c12['cohorts']}, and seasonal reach from {c6['base_reach']:.2f} to {c6['reach']:.2f} and {c12['reach']:.2f} bins, because small towns drop below the cohort threshold.</p>
<div class="table"><table><thead><tr><th>Climate</th><th>Market range</th><th>Share passed up</th><th>Town residents</th><th>Gini</th><th>Checks inside band</th><th>Staffed sources</th><th>Reach (bins)</th></tr></thead><tbody>{html_rows}</tbody></table></div>
<img src="../../reports/figures/{figures[0].name}" alt="Three settlement maps: without forwarding, with 6-day legs and with 12-day legs at a 50 percent share">
<img src="../../reports/figures/{figures[1].name}" alt="Gini coefficient of town sizes against seasonal reach for all declared scenarios in both climates">
<p>Share and range are scenarios, not calibrated values; both are shown and neither is adopted. The scenarios use the original coupled parents, a fixed 100-person cohort and same-actor links only; relative sizes say nothing about absolute city size, date, location or authority. The twelve maps are selectable in the Earth atlas under Experimental &amp; diagnostics, in Settlements and Supply-supported reach. All defaults are unchanged.</p>
<p><a href="../../reports/SETTLEMENT_HIERARCHY_20261112.md">Methods, full table and limits</a> · <a href="../earth_fit/#layer=reach_towns&amp;climate=corrected">Open the Settlements map</a> · <a href="data/settlement_market_summary.json" download>All 12 results</a> · <a href="data/settlement_market_review_two_day.json" download>Review, two-day links</a> · <a href="data/settlement_market_review_longer_legs.json" download>Review, longer legs</a> · <a href="data/settlement_market_replay.json" download>Fresh byte replay</a> · <a href="data/settlement_market_plan_two_day.json" download>Prior declaration, two-day</a> · <a href="data/settlement_market_plan_longer_legs.json" download>Prior declaration, longer legs</a></p></details></section><!--settlement-market-end-->'''
    html = page.read_text(); pattern = r'<!--settlement-market-start-->[\s\S]*?<!--settlement-market-end-->'
    if re.search(pattern, html):html = re.sub(pattern, lambda match: section, html)
    else:
        assert '<!--visit-calendar-start-->' in html; html = html.replace('<!--visit-calendar-start-->', section + '\n<!--visit-calendar-start-->', 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='settlement_market_hierarchy_20261112', status='model_only_declared_mechanism_scenarios_scored_on_exposed_shape_band', evidence='reports/SETTLEMENT_HIERARCHY_20261112.md',
        note='Twelve declared forwarding scenarios (2, 6, 12 day links; 25 and 50 percent shares) compared with the exposed Roman relative-size band. Development only; no share, range, size or default adopted.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]; write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(OUT / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page), publisher_sha256=sha(Path(__file__)),
        figures_sha256={str(p.relative_to(ROOT)): sha(p) for p in figures}))
    for p in figures:print(p)
    print('Published the market-hierarchy evidence panel, report and figures; defaults unchanged.')


if __name__ == '__main__':main()
