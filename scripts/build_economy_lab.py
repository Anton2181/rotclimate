"""Build a small, portable review page for c.200 AD proposals and prototypes."""
from pathlib import Path
import html
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from economy_component_sections import component_sections
from economy_freight_section import freight_section
from economy_labour_section import labour_section

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
    calendar_source=ROOT/'output/crop_calendar_audit_20261103'
    calendar=json.loads((calendar_source/'receipt.json').read_text())
    if calendar['status']!='diagnostic_only' or calendar['production_atlas_changed']:
        raise ValueError('Calendar audit must remain explicitly diagnostic')
    for name,expected in {**calendar['sources_sha256'],**calendar['inputs_sha256']}.items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Calendar audit source/input changed: '+name)
    if file_hash(calendar_source/'crop_calendar_ties.png')!=calendar['figure_sha256']:
        raise ValueError('Calendar figure changed')
    shutil.copyfile(calendar_source/'crop_calendar_ties.png',data/'crop_calendar_ties.png')
    shutil.copyfile(calendar_source/'receipt.json',data/'calendar_receipt.json')
    newest={}
    for key,folder,files in [
        ('sequence','crop_sequences_20261103',['joint_crop_sequences.png']),
        ('storage','calendar_storage_20261103',['calendar_storage_bounds.png','calendar_reserves.csv']),
    ]:
        origin=ROOT/'output'/folder
        record=json.loads((origin/'receipt.json').read_text())
        if record['production_atlas_changed'] or record['independent_agronomic_validation']:
            raise ValueError('This page describes experimental comparisons')
        for name,expected in {**record['sources_sha256'],**record['inputs_sha256']}.items():
            if file_hash(ROOT/name)!=expected:raise ValueError('Experimental source/input changed: '+name)
        for name in files:
            expected=record['csv_sha256' if name.endswith('.csv') else 'figure_sha256']
            if file_hash(origin/name)!=expected:raise ValueError('Experimental asset changed: '+name)
            shutil.copyfile(origin/name,data/name)
        shutil.copyfile(origin/'receipt.json',data/(key+'_receipt.json'))
        newest[key]=record
    manifest=ROOT/'research_notes/crop_sequences_20261103.json'
    if any(file_hash(manifest)!=record['literature_manifest_sha256'] for record in newest.values()):
        raise ValueError('Literature and assumption manifest changed')
    shutil.copyfile(manifest,data/'sequence_sources.json')
    sequences=newest['sequence'];storage=newest['storage']
    current_sections,component_identity=component_sections(data)
    freight_html,freight_identity=freight_section(data)
    labour_html,labour_identity=labour_section(data)
    observed_origin=ROOT/'output/observed_crop_durations_20261103'
    observed=json.loads((observed_origin/'result.json').read_text())
    observed_plan=ROOT/'calibration/crop_calendar_observations_20261103/plan.json'
    if observed['parameters_tuned'] or observed['full_agronomic_validation'] or observed['production_atlas_changed']:
        raise ValueError('Observed calendars are a descriptive check, not adoption')
    for name,expected in [('scripts/check_observed_crop_durations.py',observed['observer_sha256']),
                          ('scripts/land_people.py',observed['production_source_sha256'])]:
        if file_hash(ROOT/name)!=expected:raise ValueError('Observed check source changed')
    if file_hash(observed_plan)!=observed['plan_sha256'] or file_hash(observed_origin/'observed_durations.png')!=observed['figure_sha256']:
        raise ValueError('Observed check plan or figure changed')
    shutil.copyfile(observed_origin/'result.json',data/'observed_calendar_result.json')
    shutil.copyfile(observed_origin/'observed_durations.png',data/'observed_durations.png')
    shutil.copyfile(observed_plan,data/'observed_calendar_plan.json')
    observed_rows=[]
    for key,label in [('wheat · Winter','Winter wheat'),('barley · Winter','Winter barley'),('rice · Unqualified','Rice, unqualified')]:
        g=observed['groups'][key];envelope=list(g['outside_envelope'].values())
        observed_rows.append(f'<tr><td>{label}</td><td>{g["records"]}</td><td>{envelope[0]["count"]}</td><td>{envelope[-1]["count"]}</td><td>{g["cold_exposure_records"]}/{g["cold_summary_available"]}</td></tr>')
    sequence_rows=''.join(f'<tr><td>{label}</td><td>{sequences["scenarios"][key]["improved_cells"]}</td><td>{sequences["scenarios"][key]["paired_cells"]}</td></tr>'
        for key,label in [('0','No turnaround bin'),('1','One bin after each crop')])
    rows=[]
    for name,result in receipt['results'].items():
        capacity=receipt['minimum_zero_loss_capacity'][name]
        rows.append(f'<tr><td>{html.escape(name)}</td><td>{capacity:g}</td><td>{result["shortfall_days"]:g}</td></tr>')
    proposals=[
        ('Seasonal food stocks','Hungry season, reserves, storage requirement','Conserved prototype; map validation pending'),
        ('Grain provisioning for towns','Import dependence, food hinterlands, vulnerable supply routes','Conserving prototype and world-route connector; production inputs pending'),
        ('Household labour','Food-production workload, harvest bottlenecks, labour vs land limits','Partial field-operation scheduler; full household budget pending'),
        ('Finite irrigation water','Water-constrained irrigable land, downstream shortages','Field budget prototype; basin allocation proposed'),
        ('Seasonal herds','Winter pasture, fodder deficits, transhumance corridors','Proposed'),
        ('State provisioning','Collectable surplus, capital and garrison supply','Proposed'),
    ]
    options=''.join('<tr>'+''.join('<td>'+html.escape(value)+'</td>' for value in row)+'</tr>' for row in proposals)
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Food, farming and society · Rotclimate</title><style>{STYLE}</style>
<main><nav aria-label="Atlas navigation"><a href="../">Three climate atlases</a><a href="../earth_fit/">Earth-fit atlas</a><a href="../climate_accuracy/">Climate evidence</a></nav>
<header><p class="note">c.200 AD model workshop · 3 November 2026</p><h1>Food, farming and society</h1>
<p class="lede">Connect the harvest, the hungry season, the work of farming and the food that reaches a town or a state.</p>
<p><span class="status">Experimental seasonal food system</span> <span class="status">Agronomic validation pending</span></p></header>
{current_sections}
{freight_html}
{labour_html}
<details><summary>Earlier crop-calendar and reserve experiments</summary>
<section aria-labelledby="observed-h"><h2 id="observed-h">What observed crop calendars reveal</h2>
<p>A declared check against <a href="https://doi.org/10.1111/j.1466-8238.2010.00551.x">Sacks and colleagues’ published calendars (2010)</a> finds a gap in the current crop windows, especially for winter cereals. These are modern regional records, not ancient cultivars or pointwise yield validation. No model parameters were tuned.</p>
<div class="table"><table><caption>Selected unflagged groups · complete qualifier groups and exclusions are downloadable</caption><thead><tr><th>Crop group</th><th>Records</th><th>Duration outside model range</th><th>Still outside with 30-day margin</th><th>Cold exposure /available climate summaries</th></tr></thead><tbody>{''.join(observed_rows)}</tbody></table></div>
<p>This diagnostic identified missing winter-cereal development in the production evaluator. An isolated daily clock is now implemented and evaluated above, using <a href="https://doi.org/10.5194/gmd-11-1343-2018">Schaphoff and colleagues’ LPJmL4 description (2018)</a>. The complete crop/yield model still requires validation.</p>
<details><summary>All observed crop and qualifier groups</summary>
<figure><a href="data/observed_durations.png"><img src="data/observed_durations.png" width="1755" height="1161" alt="All parsed crop qualifier groups: observed duration ranges, model duration envelopes and available cold-exposure summaries"></a>
<figcaption>{observed['unflagged_records']} unflagged records and {observed['source_flagged_records']} original Exclude-qualified records are retained separately. Missing climate summaries are unavailable, not zero. Cold exposure comes from interpolated source climatology; its percentage is not an exact model-rejection rate. Model duration coverage is a necessary timing check, not a predicted-date score.</figcaption></figure></details>
<div class="links"><a href="data/observed_calendar_result.json" download>Observed-calendar records and full diagnostics</a><a href="data/observed_calendar_plan.json" download>Declared diagnostic and source identity</a><a href="../../reports/OBSERVED_CROP_CALENDARS_20261103.md">Findings, caveats and reproduction</a></div></section>
<section aria-labelledby="sequences-h"><h2 id="sequences-h">Choose crop seasons together</h2>
<p>The calendar prototype retains every annual growing window and compares compatible crop sequences. It can trade a little yield from one crop for a better annual combination. Each individual crop’s maximum still exactly matches the existing yield model.</p>
<p><a href="https://doi.org/10.1016/j.gloenvcha.2012.11.001">Waha and colleagues (2013)</a> motivates considering sowing dates and crop sequences together; <a href="https://doi.org/10.1016/j.gloenvcha.2020.102131">their global multiple-cropping study (2020)</a> supports checking non-overlapping seasons and limits to intensification. This is our simplified prototype, not a reproduction of those models or a reconstruction of ancient farming.</p>
<figure><a href="data/joint_crop_sequences.png"><img src="data/joint_crop_sequences.png" width="1620" height="648" alt="Energy changes from joint crop selection and two turnaround sensitivity scenarios"></a>
<figcaption>The same {sequences['sample_cells']:,} raw-r43 fantasy sample cells. The inherited half-weight second crop and water-access gate are retained for comparison; neither is established here as a universal 200 AD rule. One climate bin is about 30 days, so the turnaround cases are coarse sensitivity scenarios.</figcaption></figure>
<div class="table"><table><caption>Diagnostic sample counts · higher modeled energy is not independent agronomic validation</caption><thead><tr><th>Turnaround scenario</th><th>Higher-energy combination than current selection</th><th>Chosen crop pairs</th></tr></thead><tbody>{sequence_rows}</tbody></table></div>
<p>Changing the calendar origin preserves optimal energy and the alternatives. There are still several equally good schedules in {sequences['scenarios']['0']['ambiguous_cells']:,} samples. The model retains those alternatives; its example schedule is not an observed harvest date.</p>
<div class="links"><a href="data/sequence_receipt.json" download>Joint-calendar results and checks</a><a href="data/sequence_sources.json" download>Academic sources and our assumptions</a><a href="../../reports/CROP_SEQUENCES_20261103.md">Method, literature and validation requirements</a></div></section>
<section aria-labelledby="reserve-h"><h2 id="reserve-h">Equal harvest totals, different reserve needs</h2>
<p>Across equally productive annual calendars, {storage['calendar_dependent_reserve_cells']} samples have different minimum storage requirements, with a range of up to {storage['maximum_reserve_range_days']:.0f} days of the specified food need.</p>
<p><strong>This is a conditional inventory scenario:</strong> harvests arrive at rounded climate-bin maturity boundaries, annual consumption equals the edible harvest, consumption is uniform and storage has zero loss. No ancient granary capacity, loss rate, famine frequency or population is fitted.</p>
<figure><a href="data/calendar_storage_bounds.png"><img src="data/calendar_storage_bounds.png" width="1620" height="648" alt="Minimum and maximum reserve requirements across equally productive annual calendars"></a>
<figcaption>Bounds use every tied-optimal annual schedule. Five-day and daily accounting differ by at most {storage['maximum_5day_vs_daily_bound_difference_days']:.0f} days here. {storage['unknown_perennial_timing_cells']} perennial-only samples retain unknown timing and blank CSV bounds. Reserve days are a food-budget unit, not a measured granary size.</figcaption></figure>
<p>The reserve equation is derived from the food ledger and independently checked against its cyclic-deficit calculation. <a href="https://www.fao.org/4/ac301e/AC301e03.htm">FAO’s post-harvest framework</a> motivates separate production, storage and consumption accounts; it does not supply period-specific loss coefficients. Crop-water dynamics and observed-calendar checks remain necessary before food-security maps.</p>
<div class="links"><a href="data/storage_receipt.json" download>Reserve scenario and numerical checks</a><a href="data/calendar_reserves.csv" download>Per-sample reserve ranges (CSV)</a><a href="../../reports/CALENDAR_STORAGE_20261103.md">Inventory assumptions and limits</a></div></section>
<details><summary>Earlier checks: manufactured storage example and calendar tie audit</summary>
<section aria-labelledby="stocks-h"><h2 id="stocks-h">Seasonality and storage</h2>
<p>The prototype accounts for harvest, meals, stored food, spoilage, overflow and unmet demand. Annual food production alone does not tell us whether food is available through the whole year.</p>
<p><strong>This is a manufactured example.</strong> Each schedule supplies 365 units of food against 365 units of demand per year, with storage for 200 days of that demand and zero spoilage. These are assumed schedules, not ancient crop yields, the world’s harvest dates or famine probabilities.</p>
<figure><a href="data/seasonal_storage_demo.png"><img src="data/seasonal_storage_demo.png" width="1755" height="621" alt="Three identical annual food totals with different harvest schedules, showing stocks and minimum storage"></a>
<figcaption>A single harvest needs 364 days of demand in overnight food storage; two equal harvests need 182. At the assumed capacity of 200, the single-harvest schedule has 164 shortage days in its repeating year. A repeating inventory can still contain shortages.</figcaption></figure>
<div class="table"><table><caption>Manufactured schedules · identical annual harvest and food need</caption><thead><tr><th>Supply schedule</th><th>Minimum no-loss storage, days of demand</th><th>Shortage days at assumed capacity</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>The food ledger closes: initial stocks plus harvest equal meals, spoilage, overflow and final stocks. Reserves are explicit; an enormous inherited store cannot feed an annual deficit forever in a repeating scenario.</p>
<div class="links"><a href="data/receipt.json" download>Example data and scope</a><a href="data/seasonal_storage_demo.npz">Daily stock and shortage arrays</a><a href="../../reports/FOOD_STOCKS_20261103.md">Prototype method and tests</a></div></section>
<section aria-labelledby="calendar-h"><h2 id="calendar-h">Before harvest calendars can drive maps</h2>
<p>On {calendar['sample_cells']:,} systematic samples of the raw r43 fantasy geography, shifting only the calendar’s starting point changes the selected crop mix in <strong>{calendar['rotation_changed_mix_cells']} cells</strong>, although individual annual crop yields stay identical. Retaining alternative tied-best seasons finds a better feasible crop pair in <strong>{calendar['alternative_tied_calendar_pair_cells']} cells</strong>.</p>
<figure><a href="data/crop_calendar_ties.png"><img src="data/crop_calendar_ties.png" width="1620" height="648" alt="Crop-calendar ambiguity by crop, and the distribution of attainable energy improvements in 58 sampled cells"></a>
<figcaption>Diagnostic sample results, not whole-map area estimates or observed agronomic accuracy. The right-hand histogram shows improved cells only. Different crops, the existing water gate and half-weight second crop are retained. No published yield or population estimate has changed.</figcaption></figure>
<p>The next step is to preserve feasible season alternatives and choose compatible crop sequences together, then test the resulting calendars before feeding food stocks. A tie-breaking choice is not evidence of a real harvest date.</p>
<div class="links"><a href="data/calendar_receipt.json" download>Calendar audit data and scope</a><a href="../../reports/CROP_CALENDARS_20261103.md">Calendar audit method and prerequisites</a></div></section>
</details></details><section aria-labelledby="next-h"><h2 id="next-h">Proposed mechanics and maps</h2>
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
        calendar_receipt_sha256=file_hash(calendar_source/'receipt.json'),
        sequence_receipt_sha256=file_hash(ROOT/'output/crop_sequences_20261103/receipt.json'),
        storage_receipt_sha256=file_hash(ROOT/'output/calendar_storage_20261103/receipt.json'),
        observed_calendar_result_sha256=file_hash(observed_origin/'result.json'),
        **component_identity,**freight_identity,**labour_identity,
        assets_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in sorted(data.iterdir()) if p.is_file()}))
    print('Built portable economy lab with manufactured prototype and proposals')


if __name__=='__main__':main()
