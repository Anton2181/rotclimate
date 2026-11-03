# Seasonal field-operation budgets — 3 November 2026

The new `harvest/labour.py` component schedules required work inside explicit operation windows. It maximizes supplied output from complete annual land-use activities, subject to land and per-period resource hours. It does not turn annual spare time into work during an already full harvest window.

## Sources and scope

[FAO Farm Management for Asia, chapter9](https://www.fao.org/4/w7365e/w7365e0c.htm) supplies the whole-farm activity-budget and constrained-planning foundation. The window-based operation scheduler is our adaptation, not a reproduction of a specific FAO farm or its modern coefficients.

[Columella, De re rustica2.12.1–2](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Columella/de_Re_Rustica/2%2A.html#12), gives a period-relevant task breakdown. The transcribed wheat workdays per iugerum are ploughing4, harrowing1, first hoeing2, second hoeing1, weeding1, reaping1.5; total10.5. Barley requires3,1,1.5,1 for ploughing, harrowing, hoeing and reaping; total6.5. These are prescriptive Roman agronomic counts to the threshing floor. They omit major work after that stage and are not a survey of ancient farms or a universal environmental response.

[Bogaard and colleagues (2025)](https://doi.org/10.1073/pnas.2400694122) motivates examining the relative scarcity of work and land. Historical classifications require evidence of practices, assets and institutions. Neither climate alone nor a binding constraint in this prototype establishes a historical labour/land regime, inequality or state formation.

Source links, cached-source hashes, counts and scenario assumptions are recorded in `research_notes/farm_labour_20261103.json`. Raw source pages remain local reference caches, not newly licensed code or a transplanted model implementation.

## Numerical formulation

For each annual activity a, choose hectares x_a. Each activity represents a full crop sequence and claims that land for the year; independent crops cannot each reuse the same hectare. For each required operation q and permitted time step t, choose completed area z_qt. Require the sum over allowed steps to equal the selected area of that operation's activity. Every required task must therefore be completed on every chosen hectare.

In every step, sum each operation's area times its required resource-hours per hectare. This must not exceed that step's supplied availability for each resource. Human work and animal-team time can be simultaneous resources of the same operation; work cannot be done when the required human and team availability occur in different periods. Land use cannot exceed the supplied area. Maximize the sum of supplied per-hectare output times chosen area, using SciPy HiGHS linear programming.

The demo's output coefficient is simply one per hectare: it maximizes area completing all listed tasks, **not grain yield, edible calories, profit or population**. Arbitrary crops or perennial/double-crop sequences require explicit complete activity and operation inputs; no biological feasibility is inferred from a supplied schedule.

Tasks and area are divisible. There is no integer worker count, endogenous hiring, travel, task precedence beyond the supplied windows, weather workability or automatic exchange of labour. Competing activities share each period's budget. Numerical marginals express local objective changes per extra resource unit within this linear model; they are not observed wages or social classifications. Tied optimal schedules can differ, so the exact distribution of work within a window is not a daily prediction.

## Manufactured scenario

The unit conversion is explicit: an approximate0.25ha per iugerum and an assumed8hours per workday. These are convenient scenario conversions, not an inferred Roman working-day length. They give336listed wheat task-hours/ha and208for barley.

Use73five-day steps. Baseline availability is40human task-hours per step, totaling2,920. This is a supplied farm-work allocation, not all available household work or a claim that one person works every day. A three-worker upper envelope with at most8hours per worker/day permits at most120hours per five-day step. The matched annual-budget staffing case raises harvest availability from40to120hours in two steps, while reducing availability by10in16other steps. It changes seasonal allocation within that envelope; it does not bank idle winter labour or prove that displaced nonfarm duties can be rescheduled.

The baseline land limit is4ha. Operation windows are manufactured: ploughing steps0–19, harrowing20–23, first hoeing28–35, second40–43, weeding44–47, reaping50–51. The wider reaping case uses50–55. These are not reconstructed Columella sowing dates, real weather or output from the climate model. Draft services required by the ploughing counts are assumed available in these human-work examples; animal feed/care and equipment are not balanced.

| Scenario | Completed area, ha | Listed-task human hours used |
|---|---:|---:|
| Annual aggregation control: all tasks allowed at any time |4.00|1,344|
| Ten-day reaping window |1.67|560|
| Thirty-day reaping window |4.00|1,344|
| Same annual hours, different harvest staffing |4.00|1,344|
| Half preparation work, same narrow reaping window |1.67|453.3|
| Twice available land, same narrow reaping window |1.67|560|
| Barley with ten-day reaping window |2.50|520|

The wheat bottleneck has a closed-form check:80hours available at reaping divided by48hours/ha permits5/3ha. For barley it is80/32=2.5ha. The annual aggregation control is deliberately not a seasonally feasible calendar; it demonstrates the overstatement made by ignoring deadlines. Faster preparation and more land cannot relax a still-binding reaping window. The barley comparison concerns workable area, not food production or nutritional adequacy.

## Minimum listed work for a supplied annual food target

`minimum_farm_work` uses the same operation, land and resource constraints, adds a minimum supplied output requirement, and minimizes one chosen work resource. Human work is the default resource; animal-team time can instead be the minimized resource. Other resource capacities remain enforced. If the declared output cannot be produced, it raises `InfeasibleFarmPlan`; it does not reduce the need, create spare labour, or silently return the maximum feasible output as if the need were met. Maximum-output and minimum-work marginals are kept separate.

An explicit numerical example supplies wheat100 and barley80 arbitrary annual net-food units per hectare, with a target300units. These food coefficients are **hypothetical scenario inputs**, not measured ancient yields or output from the climate/crop model. Historical listed task counts and the manufactured work windows remain as above. With a thirty-day reaping window, the minimum listed human work is:

| Available land | Selected wheat /barley, ha | Minimum listed work, hours |
|---|---|---:|
|4.0ha|0 /3.75|780|
|3.5ha|1.0 /2.5|856|
|3.0ha|3.0 /0|1,008|

Barley has greater output per listed work-hour under these supplied coefficients, while wheat has greater output per land area. Tighter land changes the optimal crop mix and increases required work for the same annual food target. The two cases with insufficient resources remain explicit:2.9ha can produce at most290units; a ten-day reaping window with4ha permits at most200units. Their minimum-work entries are null, not zero. These ceilings and the feasible mixes have independent closed-form checks.

This is a conditional minimum of the listed field operations, not total subsistence work, a survival threshold estimated from evidence, or an assurance of food availability through the year. Food stocks, harvest pulses, seasonal consumption, complete processing and household work are not yet jointly optimized with labour. Outputs are arbitrary common food units, without a population or calorie conversion. Evidence, assumptions, schedules and numerical marginals are in `output/farm_work_targets_20261103/review.json`; the figure is linked from the same atlas workshop.

## Validation and limits

Thirty focused tests cover seasonal bottlenecks, shared resources, coupled human/team availability, mixed activity allocation, analytical marginal values, rotation of calendar origin, zero resources, invalid inputs and relaxing constraints. Every demo checks operation completion, work capacity and independently derived analytical results. The historical task totals match the cited source; the scenario results are numerical controls, **not independent historical validation**.

Unused farm-allocation hours are not leisure or surplus labour. Threshing, processing, storage, drinking-water and fuel collection, care, animal feed, tool/structure maintenance and other essential work remain outside this budget. The module is not yet coupled to crop maturity, soil workability, inferred yields or town provisioning. Its next integration needs those inputs and historically defensible task/window ranges before estimating food-production workload on the world map.

The normal r43 climate, crop-yield and population layers remain unchanged. The launcher-linked economy lab presents the partial prototype with full assumptions and schedules.

## Reproduction

```
.venv/bin/python -m pytest -q tests/test_farm_labour.py
.venv/bin/python scripts/demo_farm_labour.py
.venv/bin/python scripts/demo_required_farm_work.py
.venv/bin/python scripts/build_economy_lab.py
```

The demonstration verifies the locally cached Columella and FAO pages against the recorded hashes. A fresh research checkout can retrieve those two manifest URLs into the named cache paths; changed source bytes require source review rather than silently overwriting their recorded identities. Browsing the published atlas does not require these caches or SciPy.
