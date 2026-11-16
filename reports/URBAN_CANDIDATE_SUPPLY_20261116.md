# Candidate annual grain supply — 16 November 2026

The declared wider-supply comparison is complete, with exact published controls
and an independent review of all 32 annual cases. The candidate improves support
on the corrected map, while the raw map's central reading is slightly worse.
Neither map supplies every town or every rural origin; no adoption is implied.

Open the [corrected central comparison](../output/urban_candidate_supply_20261116/comparison_corrected_central_x34.png),
[raw central comparison](../output/urban_candidate_supply_20261116/comparison_raw_central_x34.png),
[corrected flat-density comparison](../output/urban_candidate_supply_20261116/comparison_corrected_low_x14.png)
or [raw flat-density comparison](../output/urban_candidate_supply_20261116/comparison_raw_low_x14.png).
All markers are fixed town locations; colours show annual support and change.

## Controlled comparison

The [declaration](../calibration/urban_diagnosis_20261116/candidate_supply_robustness.json)
was committed in `9f7a65633` before these results. Source coefficients, seed 1,
climate, population, sites, density scenarios, food/work packets and travel rules
are fixed. The unmodified canonical annual supply builder uses calibrated
extraction fractions **0.3371937035110408** and **0.14049021985082757**, the existing
0.10 alternative, 600 annual field hours/worker and the existing 300-hour
high-extraction sensitivity. Both density readings cross all four supply cases
on both maps/models: 32 scenarios. There is no new fit or extraction search.

Missing released full supply arrays were reconstructed in isolation. Both CSVs,
both complete supply NPZs and the **entire unrounded released results receipt**
match exactly before the candidate is run. These four file identities include
the freight network arrays and every shipment/support scenario.

The published supply world regenerates minor tracks from the routed, node-sorted
site list. These track masks differ from the size/placement packet's earlier
track order: raw 16,229 versus 16,158 cells (1,011 differing cells), corrected
16,438 versus 16,348 (932 differing cells). This pre-existing chain distinction
is preserved and recorded, rather than silently replacing the supply network
with the size packet's tracks. The exact released supply controls establish
which network was actually used. Candidate supply reuses this same network;
this is not independent validation of the freight physics or track construction.

Full-precision network shares are cached explicitly. Reusing the float32 shares
in published supply NPZs would not give an exact source-delivery replay. Models
share the full-precision network only after their fixed nodes and protected
travel inputs are checked. **Each model's own remaining rural population** feeds
its own rural meals, field workers, constrained production and marketed surplus.
No legacy rural production is substituted into the candidate.

The isolated downstream candidate packet retains `adopt=False` and
`gate.passed=False`. Canonical code/defaults and published atlas files are intact.

## Headline results

At 600 annual field hours/worker, with each density's calibrated extraction:

| Map / reading | Share of town grain need met, old → candidate | Short towns, old → candidate | Supported resident equivalents, old → candidate |
| --- | ---: | ---: | ---: |
| Raw / central, 33.719% | 81.144% → 80.994% | 47 → 52 | 10,770,014 → 10,667,330 |
| Corrected / central, 33.719% | 84.245% → 86.614% | 43 → 42 | 11,343,567 → 11,532,285 |
| Raw / low, 14.049% | 96.705% → 96.790% | 21 → 21 | 5,262,242 → 5,283,023 |
| Corrected / low, 14.049% | 98.197% → 98.995% | 12 → 9 | 5,417,138 → 5,464,240 |

These are ration equivalents in an annual grain accounting scenario, not new
allocated populations. Town resident requests remain the actual finite-population
seed-1 candidate from the preceding map stage. Actual support is not replaced
by a claim that every requested resident is fed.

At 300 hours and high extraction, central town support falls to **35.623% raw /
36.375% corrected** in the candidate (published 35.415% / 35.861%). Labour
assumptions materially affect the result. All 10% and cross-density extraction
alternatives remain in `comparison.csv` and the full manifests.

## Rural deficits and conservation

Work-limited rural shortfalls remain explicit even where other origins export
a surplus. In the central 600-hour cases, they change from **40,823 → 40,064**
person-years raw and **28,362 → 28,182** corrected. Those deficits affect 4,983
raw / 4,041 corrected land cells. Under the candidate 300-hour central scenario,
they rise to **242,239 raw / 218,871 corrected** person-years. The corrected
300-hour rural shortfall is worse than its control (212,614), despite a small
improvement in town support.

The diagnostic records workers, annual and reaping hours available/used,
production forgone to work limits, fixed rural need, surplus, marketed grain,
town shortfall and the canonical complete grain ledger. Source grain closes
through uncollected grain, hinterland loss, local consumption, inter-town loss,
received grain and unused excess. Source exports cannot exceed their surplus;
destinations cannot receive more than their need; exporters cannot simultaneously
import. No added grain or population closes deficits artificially.

The annual recipe samples travel costs in four seasons but does not construct
a continuous harvest/export/store/meal schedule. It therefore **does not qualify
seasonal source food/work, delivery continuity, a complete household/draft budget
or a civilian/staff shared origin ledger**. The existing finite seasonal
`allocate_residents` / `audit_origin_food` gates still precede adoption.

## Review and reproduction

The independent reviewer checks all **32 scenarios / 33,392 town-scenario rows**.
It uses separate field-work equations, explicit sorted source groups with
compensated sums and a separate sorted-link shipment allocator. It checks all
source/work diagnostics, shipment arrays, per-town results, headline CSVs and
grain ledgers. Freight costs themselves are reused and disclosed.

Maximum differences are 1.51e−10 person-years for source delivery and 6.69e−11
for received grain. Maximum independently summed grain residual is 2.15e−9
person-years. Scientific compact artifacts and manifests reproduce byte for
byte in a fresh directory. Protected sources/main assets match. The presentation
review checks all 4,174 plotted town/scenario pairs, their coordinates and four
image identities; maps were also visually inspected.

Artifacts: `output/urban_candidate_supply_20261116/`. `town_model.npz` retains
every town's delivered/imported/exported grain, fed share and shipments in all
cases. Canonical scenario/ledger receipts, exact controls and candidate CSVs,
diagnostics, maps and reviews are tracked. Full network, input field caches and
fresh duplicates remain ignored.

```sh
.venv/bin/python scripts/urban_candidate_wide_supply.py
.venv/bin/python scripts/urban_candidate_wide_supply.py --out output/urban_candidate_supply_20261116/fresh
.venv/bin/python scripts/review_urban_candidate_supply.py
.venv/bin/python scripts/render_urban_candidate_supply.py
.venv/bin/python scripts/review_urban_candidate_supply_maps.py
```

Next settlement work must address seasonal coupling on these actual source
calendars and fixed nodes. The annual people catchments, seasonal freight owners
and the one-owner-per-origin interface of the existing joint allocator differ;
an explicit nonduplicating source/destination representation is needed before
claiming equivalence or rerunning staff/reach/trade. The raw rural deficits
already block an all-world food-feasible claim. The prior five-seed sensitivity
also remains in force: single-town changes and the sign of aggregate population
change are not stable across every seed. No new evidence pool or adoption gate
was opened by this annual comparison.
