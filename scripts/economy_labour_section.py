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
<div class="links"><a href="data/farm_labour.json" download>All operations, schedules, work budgets and numerical marginals</a><a href="data/farm_labour_sources.json" download>Historical transcription and explicit scenario assumptions</a><a href="../../reports/FARM_LABOUR_20261103.md">Method, sources, tests and remaining work</a></div></section>'''
    return section,dict(farm_labour_review_sha256=file_hash(folder/'review.json'),
        farm_labour_section_producer_sha256=file_hash(Path(__file__)))
