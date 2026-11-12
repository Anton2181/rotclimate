"""Publish the reviewed comparison inside the standard atlas evidence page."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_joint_locations_earth import OUT, PLAN
from settlement_locations_earth import sha, write


def main():
    r = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text())
    replay = json.loads((OUT / 'replay.json').read_text())
    if r['adopt'] or len(r['rows']) != 224 or r['plan_sha256'] != sha(PLAN):
        raise ValueError('Wrong or incomplete joint comparison')
    if review['status'] != 'passed' or review['results_sha256'] != sha(OUT / 'results.json'):
        raise ValueError('Stale independent review')
    if review['reviewer_sha256'] != sha(ROOT / 'scripts/review_settlement_joint_locations.py'):
        raise ValueError('Changed independent reviewer')
    for group in ('sources', 'upstream', 'protected'):
        for p, digest in r[group].items():
            if sha(ROOT / p) != digest:
                raise ValueError('Changed comparison source/evidence: ' + p)
    if replay['status'] != 'passed':
        raise ValueError('Fresh replay required')
    for name, digest in replay['byte_exact_outputs'].items():
        if sha(OUT / name) != digest:
            raise ValueError('Stale replay: ' + name)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    for source, target in [(OUT / 'results.json', 'settlement_joint_locations.json'),
        (OUT / 'review.json', 'settlement_joint_locations_review.json'),
        (OUT / 'replay.json', 'settlement_joint_locations_replay.json'),
        (OUT / 'positions.npz', 'settlement_joint_locations_positions.npz'),
        (PLAN, 'settlement_joint_locations_plan.json')]:
        shutil.copyfile(source, data / target)
    lead = r['ranking'][0]; production = next(q for q in r['ranking'] if q['variant'] == 'production')
    fixed = next(q for q in r['ranking'] if q['variant'] == 'fixed18_L800')
    table = []
    for pool, label in [('han', 'Han AD2'), ('rome', 'Rome AD150')]:
        for name, row in [('Production control', production), ('Fixed18km control', fixed),
                          ('Joint lead · five-seed mean', lead)]:
            m = row['pools'][pool]
            table.append(f'<tr><th>{label}</th><td>{name}</td>' + ''.join(
                f'<td>{m[k]:.3f}</td>' for k in ('unique_F1', 'M1', 'M3', 'Q')) + '</tr>')
    counts = {p: next(q['requested'] for q in r['rows'] if q['pool'] == p) for p in ('han', 'rome')}
    weights = '; '.join(f'{w}: {v["variant"]}' for w, v in r['location_weight_sensitivity'].items())
    section = f'''<!--settlement-joint-start--><section><h2>Settlement locations on complete, supported inputs</h2>
<details id="settlement-joint" class="panel"><summary>224 comparisons reviewed · intensity and historical pull kept separate from people</summary>
<p id="settlement-joint-verdict"><strong>Development lead: {lead['variant']}. No production adoption.</strong> The declared comparison is complete:21 density/history variants, five seeds, two Earth pools;10 old-history ablations; four paired controls. All224 outcomes remain downloadable. All data have already been exposed; this is development selection, not a new blind validation.</p>
<p>Every alternative preserves the common natural production budget: {counts['han']:,} Han / {counts['rome']:,} Roman centres. No observed-site count sets that budget. Han uses repaired population coverage; Rome retains its original population control. Both use checked travel fields that exclude unsupported geography. The fixed18km control is rerun on those same inputs.</p>
<div class="table"><table id="settlement-joint-results"><thead><tr><th>Pool</th><th>Placement</th><th>Unique F1 ↑</th><th>Block rank ↑</th><th>Spacing KS ↓</th><th>Q ↑</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>The declared60% location-weight score is {lead['Q']:.4f}, versus {fixed['Q']:.4f} for fixed18km and {production['Q']:.4f} for production. Q combines different diagnostics; it is not a percentage accuracy. Regional tradeoffs and all {len(r['pareto_frontier'])} Pareto alternatives are retained. Weight sensitivity: {weights}.</p>
<img src="../../reports/figures/settlement_joint_maps_20261112.png" alt="Observed Han and Roman centres compared with production and the joint development lead on common complete inputs; seed1 maps">
<img src="../../reports/figures/settlement_joint_tradeoffs_20261112.png" alt="All21 variants and paired controls, showing unique matching, spacing errors and per-region development scores">
<p>Independent replay uses dense distances and minimum-cost assignment, separately recalculating every placement metric, ranking and spacing constraint. A fresh producer run reproduces both numerical archives byte for byte. The old clipped-history experiment is an ablation, excluded from winner selection; older studies retain their original inputs and scores.</p>
<p><strong>Next release work:</strong> resident-size evidence and catchment allocation must consume the same finite people and food before fantasy settlements, tracks or control can change. Historical pull is a spatial hypothesis, not observed occupation age, allegiance or institutional staffing. All actors, unaffiliated communities and mobile/nonstate populations remain on the roadmap.</p>
<p><a href="../../reports/SETTLEMENT_JOINT_LOCATIONS_20261112.md">Methods, all tradeoffs and next work</a> · <a href="../../reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md">Full release roadmap</a> · <a href="data/settlement_joint_locations.json" download>All224 outcomes and ranking</a> · <a href="data/settlement_joint_locations_review.json" download>Independent metric and constraint review</a> · <a href="data/settlement_joint_locations_replay.json" download>Fresh byte-exact replay</a> · <a href="data/settlement_joint_locations_positions.npz" download>All generated centre locations</a> · <a href="data/settlement_joint_locations_plan.json" download>Protocol committed before comparison</a></p>
</details></section><!--settlement-joint-end-->'''
    html = page.read_text(); pattern = r'<!--settlement-joint-start-->[\s\S]*?<!--settlement-joint-end-->'
    if re.search(pattern, html):
        html = re.sub(pattern, lambda m: section, html)
    else:
        marker = '<!--population-extension-start-->'
        if marker not in html:
            raise ValueError('Publish source-repair evidence before its location consumer')
        html = html.replace(marker, section + '\n' + marker, 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'
    usage = json.loads(registry.read_text()); usage['date'] = '2026-11-12'
    entry = dict(id='settlement_joint_locations_20261112', status='exposed_development_only',
        evidence='reports/SETTLEMENT_JOINT_LOCATIONS_20261112.md',
        note='224placements on already-spent Han/Roman pools, repaired Han population and supported histories. No fresh geographic qualification, resident-size calibration or fantasy adoption.')
    usage['datasets'] = [x for x in usage['datasets'] if x['id'] != entry['id']] + [entry]
    write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(OUT / 'presentation.json', dict(status='published', page_sha256=sha(page), publisher_sha256=sha(Path(__file__))))
    print('Published the full224-placement comparison in the normal atlas evidence page.')


if __name__ == '__main__':
    main()
