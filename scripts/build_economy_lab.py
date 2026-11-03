"""Build a small, portable review page for c.200 AD proposals and prototypes."""
from pathlib import Path
import html
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json

STYLE='''
:root{color-scheme:light dark;--bg:#eef2ee;--paper:#fafbf8;--ink:#203a40;--muted:#526a6d;--line:#c8d3cf;--link:#246b70}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:18px/1.6 system-ui,sans-serif}
main{max-width:1120px;margin:0 auto;padding:28px 22px 70px}nav{display:flex;gap:10px 24px;flex-wrap:wrap;font-size:15px}
a{color:var(--link);text-underline-offset:3px}h1,h2{font-family:Georgia,serif;line-height:1.15}h1{font-size:clamp(38px,6vw,62px);margin:20px 0}
h2{font-size:29px;margin:32px 0 16px}.lede{font-size:21px;max-width:800px}.note,figcaption{color:var(--muted);font-size:15px}
section{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:20px;margin-top:24px}
section h2{margin-top:0}figure{margin:22px 0}img{display:block;width:100%;height:auto;border-radius:4px;background:white}
figcaption{margin-top:10px}.table{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:640px;font-size:16px}
th,td{padding:10px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}th{font-weight:650}
.status{display:inline-block;border:1px solid var(--line);border-radius:30px;padding:3px 12px;font-size:14px}
.links{display:flex;gap:10px 24px;flex-wrap:wrap;font-size:16px}li{margin:8px 0}.sources{font-size:16px}
@media(prefers-color-scheme:dark){:root{--bg:#14292c;--paper:#1b3337;--ink:#e2ebe5;--muted:#b2c4be;--line:#416064;--link:#9bd1c5}}
@media(max-width:500px){main{padding:18px 12px 40px}section{padding:15px}h2{font-size:25px}.lede{font-size:18px}}
'''


def main():
    source=ROOT/'output/food_stock_prototype_20261103'
    receipt=json.loads((source/'receipt.json').read_text())
    if receipt['status']!='numerical_prototype' or receipt['production_atlas_changed']:
        raise ValueError('The lab must identify the prototype as a prototype')
    for name,expected in receipt['sources_sha256'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Prototype source changed: '+name)
    for name,key in [('seasonal_storage_demo.png','figure_sha256'),('seasonal_storage_demo.npz','arrays_sha256')]:
        if file_hash(source/name)!=receipt[key]:raise ValueError('Prototype data changed')
    atlas=ROOT/'atlases/economy_lab';data=atlas/'data';data.mkdir(parents=True,exist_ok=True)
    for name in ['seasonal_storage_demo.png','seasonal_storage_demo.npz','receipt.json']:
        shutil.copyfile(source/name,data/name)
    audit=ROOT/'research_notes/economy_proposals_20261103.json'
    proposal=ROOT/'reports/ECONOMY_PROPOSALS_20261103.md'
    if file_hash(proposal)!=json.loads(audit.read_text())['proposal_sha256']:
        raise ValueError('Proposal note and source audit differ')
    shutil.copyfile(audit,data/'proposal_sources.json')
    rows=[]
    for name,result in receipt['results'].items():
        capacity=receipt['minimum_zero_loss_capacity'][name]
        rows.append(f'<tr><td>{html.escape(name)}</td><td>{capacity:g}</td><td>{result["shortfall_days"]:g}</td></tr>')
    proposals=[
        ('Seasonal food stocks','Hungry season, reserves, storage requirement','Numerical prototype'),
        ('Grain provisioning for towns','Import dependence, food hinterlands, vulnerable supply routes','Proposed'),
        ('Household labour','Food-production workload, harvest bottlenecks, labour vs land limits','Proposed'),
        ('Finite irrigation water','Water-constrained irrigable land, downstream shortages','Proposed'),
        ('Seasonal herds','Winter pasture, fodder deficits, transhumance corridors','Proposed'),
        ('State provisioning','Collectable surplus, capital and garrison supply','Proposed'),
    ]
    options=''.join('<tr>'+''.join('<td>'+html.escape(value)+'</td>' for value in row)+'</tr>' for row in proposals)
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Food, farming and society · Rotclimate</title><style>{STYLE}</style>
<main><nav aria-label="Atlas navigation"><a href="../">Three climate atlases</a><a href="../earth_fit/">Earth-fit atlas</a><a href="../climate_accuracy/">Climate evidence</a></nav>
<header><p class="note">c.200 AD model workshop · 3 November 2026</p><h1>Food, farming and society</h1>
<p class="lede">Connect the harvest, the hungry season, the work of farming and the food that reaches a town or a state.</p>
<p><span class="status">One numerical prototype</span> <span class="status">Production proposals under review</span></p></header>
<section aria-labelledby="stocks-h"><h2 id="stocks-h">Seasonality and storage</h2>
<p>The prototype accounts for harvest, meals, stored food, spoilage, overflow and unmet demand. Annual food production alone does not tell us whether food is available through the whole year.</p>
<p><strong>This is a manufactured example.</strong> Each schedule supplies 365 units of food against 365 units of demand per year, with storage for 200 days of that demand and zero spoilage. These are assumed schedules, not ancient crop yields, the world’s harvest dates or famine probabilities.</p>
<figure><a href="data/seasonal_storage_demo.png"><img src="data/seasonal_storage_demo.png" width="1755" height="621" alt="Three identical annual food totals with different harvest schedules, showing stocks and minimum storage"></a>
<figcaption>A single harvest needs 364 days of demand in overnight food storage; two equal harvests need 182. At the assumed capacity of 200, the single-harvest schedule has 164 shortage days in its repeating year. A repeating inventory can still contain shortages.</figcaption></figure>
<div class="table"><table><caption>Manufactured schedules · identical annual harvest and food need</caption><thead><tr><th>Supply schedule</th><th>Minimum no-loss storage, days of demand</th><th>Shortage days at assumed capacity</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>The food ledger closes: initial stocks plus harvest equal meals, spoilage, overflow and final stocks. Reserves are explicit; an enormous inherited store cannot feed an annual deficit forever in a repeating scenario.</p>
<div class="links"><a href="data/receipt.json" download>Example data and scope</a><a href="data/seasonal_storage_demo.npz">Daily stock and shortage arrays</a><a href="../../reports/FOOD_STOCKS_20261103.md">Prototype method and tests</a></div></section>
<section aria-labelledby="next-h"><h2 id="next-h">Proposed mechanics and maps</h2>
<div class="table"><table><thead><tr><th>Mechanic</th><th>Useful maps or views</th><th>Status</th></tr></thead><tbody>{options}</tbody></table></div>
<p>The recommended first integration is crop calendars and food stocks, followed by actual grain provisioning over the existing directed road, river and sea network. Household labour then separates a productive environment from one that is easy to farm.</p>
<div class="links"><a href="../../reports/ECONOMY_PROPOSALS_20261103.md">Full proposals, prerequisites and references</a><a href="data/proposal_sources.json" download>Existing-model and source audit</a></div></section>
<section aria-labelledby="validation-h"><h2 id="validation-h">What must be established before world maps</h2>
<ul><li><strong>Harvest calendars:</strong> preserve alternative feasible seasons. The annual crop model’s tie-breaking is not evidence of one real harvest date. Double crops and perennials need their own timing.</li>
<li><strong>Period storage:</strong> capacity and loss assumptions need ancient or comparable low-input evidence. Seed storage and different food types require separate accounting.</li>
<li><strong>Water and labour:</strong> being near a river is not a finite irrigation supply, and a normalized flow index is not discharge. Food-production work is only part of total subsistence work.</li>
<li><strong>Population and institutions:</strong> market catchment residents are not town inhabitants. Food support, actual settlement, taxation and state formation are separate questions.</li></ul>
<p>The existing FORGE-inspired food-store option was tested without adoption. This agricultural inventory prototype is a separate component. Neither model makes climate or biome a universal score of societal development.</p></section>
<section class="sources" aria-labelledby="sources-h"><h2 id="sources-h">Research foundations</h2>
<p><a href="https://www.fao.org/4/ac301e/AC301e03.htm">FAO post-harvest systems</a> provides the production-to-consumption framework. <a href="https://history.stanford.edu/publications/orbis-stanford-geospatial-network-model-roman-world">Stanford ORBIS</a> supplies a historical transport basis already used by the project.</p>
<p><a href="https://doi.org/10.1073/pnas.2400694122">Bogaard and colleagues, 2025</a> develops the archaeological labour/land-limited farming framework. <a href="https://doi.org/10.1086/718372">Mayshar, Moav and Pascali, 2022</a> motivates testing the appropriability of crops rather than equating total productivity with state power. These works support hypotheses; they do not provide universal c.200 AD coefficients.</p></section>
</main></html>'''
    (atlas/'index.html').write_text(page,encoding='utf-8')
    write_json(source/'publication.json',dict(status='prepared',page_sha256=file_hash(atlas/'index.html'),
        prototype_receipt_sha256=file_hash(source/'receipt.json'),producer_sha256=file_hash(Path(__file__)),
        assets_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in sorted(data.iterdir()) if p.is_file()}))
    print('Built portable economy lab with manufactured prototype and proposals')


if __name__=='__main__':main()
