# The existing annual agricultural budget, in compatible units

17 November 2026. The annual grain-support scenario is now traced from rural
people through work, production, retention and delivery. **The main unresolved
agricultural definition is what the supplied field-work allowance can actually
fund on a shared human, draft and land budget.** Its 300/600 hours are not
measured Roman annual occupations. Do not add detailed logistics workers to
the unused portion of this partial allowance.

This completes the [declared read-only trace](../calibration/roman_benchmark_20261117/annual_agricultural_budget.json).
The [32-row budget](../output/annual_agricultural_budget_20261117/budget.csv)
contains both cohorts, both fixed climate scenarios and every available density/
marketed-share/work alternative. No crop, field-work, freight or climate model
is rerun. The [recipe record](../output/annual_agricultural_budget_20261117/recipe.json)
pins the code and unit definitions; the preceding
[sensitivity assessment](ANNUAL_ASSUMPTION_IMPACT_20261117.md) supplies the impact ranking.

## From people and land to cereal production

| Link | Existing definition | Evidence status / limitation |
| --- | --- | --- |
| Rural people → workers | 40% of the same density scenario's remaining rural people | Supplied effective workforce share; no age/sex/occupation observation here |
| Workers → annual listed allowance | 600 or300 hours/worker, hence240 or120 hours/rural person | Scenarios, not a full time-use reconstruction |
| Harvest-window allowance | Same workers ×30days ×8hours, capped by annual allowance |96 hours/rural person in both cases; a subset, never extra annual work |
| Task counts → hours/ha | Wheat336 listed/48 reaping; barley208/32 | Columella's prescribed task days; approximate0.25ha/iugerum and assumed8-hour conversion |
| Crop choice | Least listed hours per net kcal among wheat/barley | A single cereal activity, not an observed crop mix or the population model's broader crop portfolio |
| Potential cropped area |100 ×land-fraction cell km² ×arable ×0.6 farmed ×0.6 annually sown |36% of modeled arable hectares before work constraints; not36% of all terrain |
| Annual sowing share |0.6 | Inherited Han AD2 development calibration; not a measured Roman rotation fraction |
| Potential grain | Selected cereal's net kcal/ha ×potential cropped hectares | Seed and edible deductions already upstream; do not subtract them again |
| Work-constrained grain | Per-cell potential ×minimum of1, annual-work ratio and reaping-work ratio | Each retained crop activity pays both listed task totals; omitted tasks remain omitted |
| Grain ration-year |2500 kcal/day ×365 =912,500 kcal | Common annual accounting unit; does not establish a complete diet or actual new residents |

The existing broad land/population recipe uses **1.1million kcal per person-year**,
whose code comment includes storage and draft overhead. The annual cereal-flow
ledger uses912,500 kcal per ration-year. Those quantities have different scopes:
the former does not authenticate measured animal feed or storage labour in the
latter. Do not silently substitute one denominator for the other or add another
generic seed/loss deduction to already net crop energy. Physical processing
work and material losses need separate explicit accounts.

Actual retained cropped hectares cannot be uniquely recovered from these
aggregate work totals without cell crop identities and their retained areas.
They remain unavailable here. Dividing all hours by wheat's336 would silently
assign wheat to barley activities. The fixed land/crop recipe is traced, but a
new complete land-use balance is not claimed.

## What the corrected candidate actually budgets

These four rows keep marketed share at33.719% to expose the work/density
differences. The CSV retains all other existing shares. Figures are rounded;
population stays fixed within each work comparison.

| Quantity | Central600h | Central300h | Low600h | Low300h |
| --- | ---: | ---: | ---: | ---: |
| Rural people, million |40.114|40.114|47.909|47.909|
| Effective rural workers, million |16.046|16.046|19.164|19.164|
| Listed hours used per rural person |234.98|119.97|231.83|119.90|
| Potential grain, million ration-years |240.092|240.092|240.092|240.092|
| Produced grain, million ration-years |128.674|65.759|151.569|78.511|
| Potential retained after work limits |53.59%|27.39%|63.13%|32.70%|
| Rural grain shortfall, thousand ration-years |28.182|218.871|32.932|259.595|
| Positive source surplus, million ration-years |88.588|25.864|103.693|30.862|
| Marketed grain, million ration-years |29.871|8.721|34.965|10.406|
| Town grain consumed, million ration-years |11.532|4.843|5.520|5.000|

In the raw central600h case, production is126.693million ration-years,53.43%
of its237.108million potential; the same limitation appears in both climate
scenarios. The central corrected difference of111.418million potential
ration-years is **output excluded by the supplied work limits**, not an estimate
of historically recoverable food. Additional labour, land or seed cannot simply
be assumed available to produce it.

## Retention, marketing and transport are separate claims

The corrected central600h/high-share ledger is:

| Stage | Million grain ration-years |
| --- | ---: |
| Work-constrained production |128.674|
| Rural grain actually retained (need minus local shortfall) |40.086|
| Positive source surplus |88.588|
| Surplus outside the modeled marketed fraction |58.717|
| Modeled marketed grain |29.871|
| Marketed grain left at source cells |6.022|
| Transport cost paid in grain equivalents, both legs |10.540|
| Grain consumed in towns |11.532|
| Unused town excess |1.777|

Production equals rural retention plus positive surplus, including the rural
shortfall explicitly. Marketed grain equals source leftovers, transport cost,
town consumption and unused town excess. No global surplus cancels a local
rural deficit. The unmarketed portion has **no modeled alternative allocation**;
it is not an observed spoilage quantity or verified household/animal reserve.
The transport charge is the existing grain-equivalent cost convention, not a
measurement of literal grain eaten en route. Its historical freight realism
is not revalidated by a closing arithmetic ledger.

## Concrete next change

Recover a **per-origin cereal activity packet from the existing archived inputs**:
stable source IDs, cereal identity, potential/retained cropped area, net yield,
listed work and reaping as a subset, actual rural need and fixed scenario
provenance. Require exact controls against all existing aggregate grain/work
outputs before it can feed a seasonal schedule. This makes missing land/resource
claims visible and prevents reusing the same hectare, worker or source surplus.
It is an accounting preparation, not a new hours calibration.

After that control, high-impact seasonal work needs actual non-reaping tasks,
compatible operation windows and shared human/draft resources. Columella's
prescriptions can inform task definitions; the unresolved calendar witness and
regional/weather qualifications remain. Unknown windows or competing duties
must remain unknown or explicit scenarios. A calendar solver cannot supply
missing evidence. Density alternatives and the failed Karanis match stay visible;
climate development remains deferred.

## Verification

The producer checks288 existing scalar identities across32 cases, invariant
potential production within climate, historical supply/field-support source
hashes and the preceding qualification chains. AST inspection checks actual
field-support defaults and land-use constants without importing model modules.
A separate scalar reviewer checks every exported column against archived
results/diagnostics; fresh budget/recipe/results outputs match byte for byte.
These checks establish the trace, not a new farm, nutrition or demographic
validation. The atlas, parameters and source scenarios remain unchanged.

```sh
.venv/bin/python scripts/annual_agricultural_budget.py
.venv/bin/python scripts/annual_agricultural_budget.py --out output/annual_agricultural_budget_20261117/fresh
.venv/bin/python scripts/review_annual_agricultural_budget.py
```

Completed receipts are preserved; reproduce into a fresh directory.
