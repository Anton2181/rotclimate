"""Publish the verified world-route connector in the portable economy lab."""
from pathlib import Path
import json
import shutil
from local_benchmark_protocol import file_hash

ROOT=Path(__file__).resolve().parents[1]


def freight_section(destination):
    folder=ROOT/'output/freight_corridors_20261103'
    review=json.loads((folder/'review.json').read_text());presentation=json.loads((folder/'presentation.json').read_text())
    if presentation['status']!='verified' or review['production_atlas_changed']:
        raise ValueError('Only a verified experimental connector belongs here')
    expected_files={**review['sources_sha256'],**review['inputs_sha256'],
        'output/freight_corridors_20261103/review.json':presentation['review_sha256'],
        'scripts/publish_freight_corridors.py':presentation['publisher_sha256'],
        'output/freight_corridors_20261103/freight_corridors_readable.png':presentation['figure_sha256'],
        'calibration/freight_corridors_20261103/plan.json':review['plan_sha256']}
    for name,expected in expected_files.items():
        if file_hash(ROOT/name)!=expected:raise ValueError('World-route evidence changed: '+name)
    audit_path=ROOT/'output/parallel_freight_20261103/review.json'
    audit=json.loads(audit_path.read_text())
    if audit['production_atlas_changed']:raise ValueError('Aggregation audit must remain isolated')
    for name,expected in {**audit['sources_sha256'],**audit['inputs_sha256'],
        'calibration/parallel_freight_20261103/plan.json':audit['plan_sha256']}.items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Aggregation audit source/input changed: '+name)
    shutil.copyfile(audit_path,destination/'parallel_freight.json')
    shutil.copyfile(folder/'freight_corridors_readable.png',destination/'freight_corridors.png')
    shutil.copyfile(folder/'review.json',destination/'freight_corridors.json')
    rows=[]
    for month in range(1,13):
        cells=[]
        for direction in ['A to B','B to A']:
            r=next(r for r in review['routes'] if r['model_month']==month and r['direction']==direction)
            cells.extend([f'{r["cost_road_km"]:,.0f}',f'{r["travel_days"]:.1f}'] if r['status']=='routed' else ['Unavailable','Unavailable'])
        rows.append('<tr><td>'+str(month)+'</td>'+''.join('<td>'+s+'</td>' for s in cells)+'</tr>')
    audit_rows=[]
    for month in audit['results']:
        samples=month['sources']
        broad=max(s['market_access']['270']['relative_change'] or 0. for s in samples)
        local=max(s['market_access']['30']['relative_change'] or 0. for s in samples)
        affected=max(s['reachable_people_fraction_with_material_reduction'] for s in samples)
        audit_rows.append(f'<tr><td>{month["model_month"]}</td><td>{100*local:.4f}%</td><td>{100*broad:.4f}%</td><td>{100*affected:.2f}%</td></tr>')
    section=f'''<section aria-labelledby="freight-h"><h2 id="freight-h">Seasonal freight routes on the current world</h2>
<p>The connector now carries freight cost, physical duration and transport mode along the <strong>same directed route</strong> on the raw-r43 geography. A cheap voyage can be slow; road-kilometre cost equivalents are not travel days. The routes reuse the project’s <a href="https://history.stanford.edu/publications/orbis-stanford-geospatial-network-model-roman-world">ORBIS-based transport assumptions</a> and climate-sensitive sailing, roads and rivers.</p>
<figure><a href="data/freight_corridors.png"><img src="data/freight_corridors.png" width="2100" height="1148" alt="Actual-world least-cost corridors in both directions and two seasons, with white-outlined sea legs"></a><figcaption>A/B are distinct marked ports chosen by a fixed drawing-position rule before routing. Nearby place names are context, not verified town identities. Model months 1 and 7 were selected in advance; the drawing keeps its original orientation. Blue is sea, brown land, purple river, gray transfers. White outlines separate sea routes from the water.</figcaption></figure>
<p>Season and direction change the path. Under the supplied food budgets, stores and departure capacities, both directions meet all 146 units of town food need, as well as the farm’s 365. The budgets are deliberately identical manufactured inputs at A and B. This demonstrates a connected food ledger; it does not establish local production, cargo tonnage, prices or town population.</p>
<details><summary>All 12 months and both directions</summary><div class="table"><table><caption>One least-cost path per month and direction · not necessarily the fastest path</caption><thead><tr><th>Model month</th><th>A→B cost, road-km equivalents</th><th>A→B days</th><th>B→A cost, road-km equivalents</th><th>B→A days</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></details>
<p>These are monthly snapshots: the departure month’s conditions remain fixed through the voyage. The connector uses edgewise sailing expectations, rather than the separate whole-voyage weather-spell model. Departure capacity and storage are prescribed; ships, return voyages and fleet availability are not modeled.</p>
<p>The audit also found 155 directed node pairs with parallel transport alternatives per month. The connector chooses an alternative instead of adding their costs. Existing atlas trade/travel graphs are unchanged; their parallel-edge handling needs a separate measured review before replacement.</p>
<details><summary>How much does choosing parallel alternatives change the result?</summary>
<p>A paired check holds topology and every coefficient fixed for ten predetermined source locations and four seasons. None of 360 sampled directed town-to-town costs changes. Broad market access changes by at most 0.0107%; local access by at most 0.0735%. Some nearby map cells become cheaper to reach. This confirms a real edge-handling problem with a small effect on these sampled aggregate measures.</p>
<div class="table"><table><caption>Maximum across the ten sources in each month · fixed cost scales 30 /270 road-km</caption><thead><tr><th>Model month</th><th>Local market access change</th><th>Broad market access change</th><th>Reachable claimed population with cost reduction &gt;1 road-km equivalent</th></tr></thead><tbody>{''.join(audit_rows)}</tbody></table></div>
<p>Market access is discounted catchment population, not food tonnage or town size. This source sample does not cover every town pair, fit or political travel mode. Reducing the cost of parallel alternatives cannot make a shortest path dearer; that mathematical property does not establish historical accuracy.</p>
<a href="data/parallel_freight.json" download>All paired aggregation results, source selection and invariants</a></details>
<div class="links"><a href="data/freight_corridors.json" download>All 24 paths, cost/time legs, graph audits and food ledgers</a><a href="../../reports/FREIGHT_CORRIDORS_20261103.md">Transport basis, route assumptions and integration limits</a></div></section>'''
    return section,dict(freight_review_sha256=presentation['review_sha256'],
        freight_aggregation_review_sha256=file_hash(audit_path),
        freight_presentation_sha256=file_hash(folder/'presentation.json'),freight_section_producer_sha256=file_hash(Path(__file__)))
