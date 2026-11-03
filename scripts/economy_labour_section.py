"""Verified partial field-work budgets for the portable economy workshop."""
from pathlib import Path
import html
import json
import shutil
from local_benchmark_protocol import file_hash

ROOT=Path(__file__).resolve().parents[1]


def labour_section(destination):
    folder=ROOT/'output/farm_labour_20261103';record=json.loads((folder/'review.json').read_text())
    if record['production_atlas_changed'] or record['independent_historical_validation'] or record['food_output_predicted']:
        raise ValueError('Only an explicit partial field-work experiment belongs here')
    files={**record['sources_sha256'],'research_notes/farm_labour_20261103.json':record['source_manifest_sha256'],
        'output/farm_labour_20261103/seasonal_farm_labour.png':record['figure_sha256']}
    for name,expected in files.items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Field-work evidence changed: '+name)
    for case in record['cases'].values():
        if max(abs(case['maximum_task_residual']),case['maximum_work_budget_overrun'])>1e-7:
            raise ValueError('Operation or work budget failed')
    for name,target in [('review.json','farm_labour.json'),('seasonal_farm_labour.png','seasonal_farm_labour.png')]:
        shutil.copyfile(folder/name,destination/target)
    shutil.copyfile(ROOT/'research_notes/farm_labour_20261103.json',destination/'farm_labour_sources.json')
    target_folder=ROOT/'output/farm_work_targets_20261103';targets=json.loads((target_folder/'review.json').read_text())
    if targets['production_atlas_changed'] or targets['historical_food_yields_estimated'] or targets['total_subsistence_work_estimated']:
        raise ValueError('The food-target example is a conditional partial-work calculation')
    for name,expected in {**targets['sources_sha256'],
        'research_notes/farm_labour_20261103.json':targets['source_manifest_sha256'],
        'output/farm_work_targets_20261103/required_field_work.png':targets['figure_sha256']}.items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Required-work evidence changed: '+name)
    target_rows=[]
    for label,r in targets['cases'].items():
        hours='Infeasible' if r['minimum_listed_work_hours'] is None else f'{r["minimum_listed_work_hours"]:,.0f}'
        target_rows.append(f'<tr><td>{html.escape(label)}</td><td>{r["available_land"]:.1f}</td><td>{r["maximum_food_units"]:.0f}</td><td>{hours}</td></tr>')
    shutil.copyfile(target_folder/'review.json',destination/'required_farm_work.json')
    shutil.copyfile(target_folder/'required_field_work.png',destination/'required_field_work.png')
    rows=[]
    for label,r in record['cases'].items():
        rows.append(f'<tr><td>{html.escape(label)}</td><td>{r["feasible_area_hectares"]:.2f}</td><td>{r["used_work_hours"]:,.0f}</td></tr>')
    section=f'''<section aria-labelledby="labour-h"><h2 id="labour-h">Seasonal field work: the harvest bottleneck</h2>
<p>A new operation scheduler requires every chosen hectare to complete its listed tasks within supplied work windows. Human hours and animal-team hours can be separate simultaneous constraints. Spare winter time cannot pay for a missed harvest, and two crops cannot each claim the same annual field area.</p>
<p><a href="https://www.fao.org/4/w7365e/w7365e0c.htm">FAO whole-farm planning</a> provides the activity-budget method. The historical task counts here come from <a href="https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Columella/de_Re_Rustica/2%2A.html#12">Columella, De re rustica 2.12.1–2</a>: 10.5 listed workdays per iugerum for wheat, 6.5 for barley. They are prescriptive counts <strong>to the threshing floor</strong>, not complete household work or universal 200 AD rates.</p>
<figure><a href="data/seasonal_farm_labour.png"><img src="data/seasonal_farm_labour.png" width="1820" height="756" alt="Partial field-work scenarios: a narrow harvest window limits wheat area despite ample annual hours"></a><figcaption>Manufactured windows and farm-work availability; approximate 0.25 ha/iugerum and an assumed eight-hour workday. Ordinary availability is 40 human hours per five-day step; harvest staffing may rise to 120, within a specified three-worker envelope. The equal-annual-budget comparison changes staffing, not stored labour. Actual scheduling within a window is one optimal solution, not a predicted daily timetable.</figcaption></figure>
<div class="table"><table><caption>Maximum area completing every listed task · same 2,920 available annual farm hours in all cases</caption><thead><tr><th>Scenario</th><th>Completed field area, ha</th><th>Listed-task human hours used</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>Annual aggregation suggests four wheat hectares are feasible. A ten-day reaping window reduces the feasible area to 1.67 ha; wider harvest windows or additional peak staffing permit four. More land or faster preparation alone does not help. Barley’s different task counts permit 2.5 ha in the narrow-window example; this does not compare edible output, nutrition or crop suitability.</p>
<p>Threshing, processing, storage, animal feed/care, other household duties and weather workability are still outside this partial budget. Draft services are assumed available in these examples. Unused farm-allocation hours are <strong>not leisure or surplus labour</strong>. Windows are not climate-derived, and no town population, famine risk or social-development score is calculated.</p>
<p><a href="https://doi.org/10.1073/pnas.2400694122">Bogaard and colleagues’ labour/land framework (2025)</a> motivates examining constraints. Its archaeological classifications require contextual evidence. A binding constraint or numerical shadow value in this linear scenario is not a historical regime or inequality diagnosis.</p>
<h3>Minimum field work for a specified annual food need</h3>
<p>The complementary solver minimizes listed work while meeting a supplied annual net-food target and the same seasonal limits. Infeasible targets remain explicit. This example assumes <strong>300 arbitrary food units</strong> are needed and supplies hypothetical per-hectare outputs of wheat 100 and barley 80. These food coefficients are scenario inputs, not historical yields or climate-model estimates.</p>
<figure><a href="data/required_field_work.png"><img src="data/required_field_work.png" width="1680" height="770" alt="Declared food-target example: tighter land changes crop mix and increases minimum field work, with infeasible cases marked explicitly"></a><figcaption>Same annual food requirement and listed historical task counts, with manufactured windows and availability. The first three cases use a thirty-day reaping window. No minimum workload is reported for infeasible cases; unavailable is not zero.</figcaption></figure>
<div class="table"><table><caption>Declared annual need 300 units · numerical scenario, not ancient subsistence workload</caption><thead><tr><th>Scenario</th><th>Land, ha</th><th>Maximum supplied food units</th><th>Minimum listed work, hours</th></tr></thead><tbody>{''.join(target_rows)}</tbody></table></div>
<p>Tighter land shifts the model from barley toward wheat and increases required listed work from 780 to 1,008 hours. Too little land or a narrow harvest window makes the target infeasible. Seasonal food consumption and stores are not yet coupled to this work planner, and omitted tasks still prevent a total subsistence-work estimate.</p>
<a href="data/required_farm_work.json" download>Food-target assumptions, crop mixes, schedules and infeasibility records</a>
<div class="links"><a href="data/farm_labour.json" download>All operations, schedules, work budgets and numerical marginals</a><a href="data/farm_labour_sources.json" download>Historical transcription and explicit scenario assumptions</a><a href="../../reports/FARM_LABOUR_20261103.md">Method, sources, tests and remaining work</a></div></section>'''
    return section,dict(farm_labour_review_sha256=file_hash(folder/'review.json'),
        required_farm_work_review_sha256=file_hash(target_folder/'review.json'),
        farm_labour_section_producer_sha256=file_hash(Path(__file__)))
