"""Verified current component sections for the portable economy workshop."""
from pathlib import Path
import html
import json
import shutil

from local_benchmark_protocol import file_hash

ROOT=Path(__file__).resolve().parents[1]


def component_sections(destination):
    cereal=ROOT/'output/cereal_phenology_20261103';food=ROOT/'output/seasonal_food_system_20261103'
    review=json.loads((cereal/'review.json').read_text());result=review['result'];system=json.loads((food/'receipt.json').read_text())
    if review['adoption'] or result['adoption'] or system['production_atlas_changed'] or system['population_predicted']:
        raise ValueError('Workshop describes unadopted numerical/scenario components')
    for name,expected in {**result['sources_sha256'],**system['sources_sha256']}.items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Component source changed: '+name)
    if file_hash(cereal/'result.json')!=review['result_sha256'] or file_hash(ROOT/'scripts/publish_cereal_development.py')!=review['publisher_sha256']:
        raise ValueError('Cereal evidence changed')
    for origin,filename,expected in [(cereal,'cereal_development.png',review['figure_sha256']),
                                     (food,'seasonal_food_system.png',system['figure_sha256'])]:
        if file_hash(origin/filename)!=expected:raise ValueError('Component image changed')
        shutil.copyfile(origin/filename,destination/filename)
    shutil.copyfile(cereal/'review.json',destination/'cereal_development.json')
    shutil.copyfile(food/'receipt.json',destination/'seasonal_food_system.json')
    rows=[]
    for name,label in [('legacy_heat_only','Existing heat thresholds, thermal ablation'),('published_heat_only','Published heat adaptation'),
                       ('reference_chilling','Plus fixed winter chilling'),('selected_global','Training-selected heat/chilling')]:
        train=result['scores'][name]['training'];test=result['scores'][name]['evaluation']
        rows.append(f'<tr><td>{label}</td><td>{train["country_mean_penalized_error_days"]:.1f}</td><td>{test["country_mean_penalized_error_days"]:.1f}</td><td>{test["nonmature_records"]}/{test["records"]}</td></tr>')
    cases=[]
    for name,r in system['cases'].items():
        if abs(r['food_ledger_residual'])>1e-6 or abs(r['water_ledger_residual'])>1e-6:
            raise ValueError('Scenario ledger failed')
        cases.append(f'<tr><td>{html.escape(name)}</td><td>{r["assumed_farm_store"]:.0f}</td><td>{100*r["rural_consumed"]/r["rural_need"]:.1f}%</td><td>{100*r["town_consumed"]/r["town_need"]:.1f}%</td></tr>')
    section=f'''<section aria-labelledby="development-h"><h2 id="development-h">Daily cereal development: test the mechanisms</h2>
<p>The new daily clock implements heat accumulation, vernalization and optional day-length response from <a href="https://doi.org/10.5194/gmd-11-1343-2018">Schaphoff and colleagues’ LPJmL4 description (2018)</a>. Its reference assumption is day-length insensitivity. It is an isolated clock, not the full vegetation, yield or winter-survival model.</p>
<p>One shared heat scale and winter chilling requirement were fitted on 237 records from 62 countries. The selected parameters were committed before scoring 29 records from 16 evaluation countries. Sowing is prescribed from observed calendars; temperature is interpolated modern climatology at approximate regional centroids.</p>
<div class="table"><table><caption>Equal-country mean conditional duration error, days · no maturity within 365 days costs 365 days</caption><thead><tr><th>Predeclared clock</th><th>Training error</th><th>Evaluation error</th><th>Evaluation nonmaturity</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<figure><a href="data/cereal_development.png"><img src="data/cereal_development.png" width="1755" height="688" alt="Country-separated conditional cereal-duration results including failed generic chilling"></a><figcaption>Climate-adapted heat requirements help this limited test. Generic chilling makes it worse, including after training. The existing-threshold comparator is a thermal ablation, not the normal atlas’s date-prediction accuracy. No ancient yield, sowing-date or population validation is claimed.</figcaption></figure>
<p>The country split prevents parameter selection from using evaluation-country scores. The dataset had already been inspected diagnostically; neighboring countries can remain correlated. These results support further work on thermal adaptation and cultivar requirements, rather than adopting a blanket winter chilling rule.</p>
<div class="links"><a href="data/cereal_development.json" download>All maturity records, predictions and frozen evaluation rules</a><a href="../../reports/CEREAL_DEVELOPMENT_20261103.md">Published equations, adaptations and limits</a></div></section>
<section aria-labelledby="system-h"><h2 id="system-h">From field water to stored grain and town food</h2>
<p>The daily development clock determines maturity from prescribed sowing and a manufactured temperature year, then a continuous field-water ledger connects those windows to harvest pulses and a directed food-provisioning solver. The water equations follow <a href="https://www.fao.org/4/x0490e/x0490e0e.htm">FAO56 chapter8</a> and reproduce its published depletion example within 0.05 mm. Harvest and sowing do not refill the soil, and irrigation cannot exceed the specified field supply.</p>
<p>The provisioning component uses capacitated flows with transit times, following the network-flow foundation of <a href="https://doi.org/10.1287/opre.6.3.419">Ford and Fulkerson (1958)</a>. Food, stocks, shipments and losses have one closed ledger. Costs do not consume calories, gravity weights do not become tonnes, and consumption priorities are an explicit scenario policy.</p>
<figure><a href="data/seasonal_food_system.png"><img src="data/seasonal_food_system.png" width="2160" height="662" alt="Manufactured example linking daily crop maturity, root-zone water, storage and directed seasonal town provisioning"></a><figcaption><strong>Manufactured example:</strong> prescribed wheat/millet sowing, temperature, rain, evaporation, net irrigation, granaries, transport and food need. The clock determines maturity; no sowing-date optimization is claimed. One food unit is 10,000 kcal. No town population, ancient storage capacity, famine frequency or river withdrawal is estimated.</figcaption></figure>
<div class="table"><table><caption>Supplied annual food need: farm 365 units, town 146 · no arbitrary half-weight second crop</caption><thead><tr><th>Scenario</th><th>Farm store capacity, food units</th><th>Farm need met</th><th>Town need met</th></tr></thead><tbody>{''.join(cases)}</tbody></table></div>
<p>Small stores can lose harvest surplus and leave later needs unmet. A route closure can add little while storage already binds. With ample farm storage, the paired closure case isolates a transport limit. All six scenarios close separate water and food budgets.</p>
<p>World-map integration still needs verified crop/cultivar behaviour, soil and seasonal water supply, historical storage and labour evidence, town-demand scenarios and cost/time/capacity for the same directed route. The existing freight-cost graph is not a travel-time or cargo-capacity dataset.</p>
<div class="links"><a href="data/seasonal_food_system.json" download>All food-system assumptions, harvests and water/food ledgers</a><a href="../../reports/SEASONAL_FOOD_SYSTEM_20261103.md">Academic basis, scenario contract and remaining integration</a></div></section>'''
    return section,dict(cereal_result_sha256=review['result_sha256'],food_system_receipt_sha256=file_hash(food/'receipt.json'),
                        component_producer_sha256=file_hash(Path(__file__)))
