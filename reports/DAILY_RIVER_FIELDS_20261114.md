# Daily river, pond and field-water coupling — 14 November 2026

The river withdrawal ledger now drives finite ponds and the shared-water soil
model on the exact supplied clock. All 256 declared Earth development cases and
matched rain-only controls are retained. These are conditional water diagnostics;
there is no calibrated crop-yield, irrigated-area, population or settlement update.

Open [the normal evidence page](../atlases/earth_evidence/daily_fields/index.html)
for all scenarios, field maps and downloadable states. Protocol commit `30726ae4`
and candidate-area amendment `e4e26b46` preceded the new Earth outputs. Both
regions were already exposed development data, with no independent test region.

## Water accounting

`harvest/river_fields.py` couples the existing upstream-first forest router,
three disjoint soil stocks and a fourth pond stock. Source inputs are cubic
metres **per step**, rain is millimetres per step, field areas are square metres,
and ETo/infiltration are daily rates multiplied by actual segment duration.
Fields request useful water for their finite infiltration allowance and permitted
pond room after accounting for existing pond water and 80% of rain. The other
20% of rain is an explicit excluded-runoff sink. Useful requests share node
withdrawals proportionally; delivery losses spend the same river volume.

At the start of a step, existing pond water is released if ponding is no longer
allowed. Paid infiltration is bounded by soil deficit and 20 mm/day. Remaining
surface water fills the permitted finite pond, then overflows externally. Pond
ET is paid before soil ET. Pond presence after infiltration suppresses soil
surface evaporation and bare diffusion for the whole step, even when pond ET
empties it during that step. This is an explicit approximation, not a resolved
subdaily pond-cover model. Crop and pond-permitted masks may not overlap.
Drainage, releases and overflow leave the model without downstream reuse.

Top plant-available, deep plant-available and surface below-wilting-point water
remain separate; overlapping TEW/TAW is counted once. Bare background evaporation
now spends only the deep available stock, separately from surface evaporation
and with zero crop uptake. This reproduces the complete ten-day FAO56 Example31,
including its 0.15 ETo background term. Its later depletion behaviour remains an
unqualified bounded approximation. Crop root uptake uses the existing constant
legacy crop coefficient solely as a **supplied root-demand coefficient**; it is
not a qualified stage-dependent basal curve or the old total-ET/yield model.

All stocks start empty and carry between annual repeats. Convergence requires
every stock to change by at most 1e-6 mm, with no field-capacity reset. All cases
converged in 2–12 cycles; nonconvergence is explicit in the generic operator.

## Declared development grid

The grid is two regions × two crops × two root depths × two calendars × two
bare coefficients × two pond capacities × two efficiencies × capture/control:
256 rows. Crops are barley and wheat; supplied root depths 1/1.5 m give
TAW 150/225 mm at FC 0.25, WP 0.10. The evaporation layer is 0.10 m, REW 9 mm;
background coefficients are 0/0.15, ponds 0/200 mm, efficiencies 0.5/1. Pond ET
coefficient is 1, Kcmax 1.2, exposed crop fraction 0.25, depletion fraction 0.55.
None of these is a measured local profile. No 600 mm root zone is selected.

The five-bin crop uses capture phases 7–10 and crop 10–3, wrapping year end.
The fractional four-bin crop uses capture 7–10.5 and crop 10.5–2.5. Phase bins
are equal climate intervals, not exact Gregorian dates. Thermal eligibility
integrates actual crop-step durations without substituting another season.
All 489 Nile and 1,018 Mesopotamian climate fields remain water consumers;
thermal ineligibility removes only crop uptake/scoring, never field water demand.
Actual latitude-dependent candidate areas are 24,497.044 and 63,986.271 km²,
not an inference about cultivated land or fallow shares.

Each region has one optimistic shared river node. The source is positive
monthly gauge excess above its annual mean, converted to bin volume. Both this
volume and monthly rain are distributed uniformly within bins. Aswan and Hit
are noncontemporaneous exposed gauge series; **Mesopotamia receives Euphrates
water only, with no Tigris**. Rain-only controls retain the same calendar,
pond/drainage policy and soil parameters while disabling river capture.

## Results and interpretation

The mapped illustration fixes barley, 1.5 m supplied roots, bare coefficient
0.15, 200 mm pond and efficiency 1. It is not a chosen or fitted winner.

|Region|Supplied crop duration|Rain-only root demand met|Capture root demand met|Useful capture delivered, km³/year|
|---|---|---:|---:|---:|
|Nile|5 bins|0.46%|65.33%|21.913|
|Nile|4 fractional bins|0.58%|79.00%|22.459|
|Euphrates only|5 bins|3.69%|3.69%|0.595|
|Euphrates only|4 fractional bins|4.76%|4.76%|0.595|

Root coverage is actual/potential root transpiration on eligible fields. It is
**not comparable directly with the earlier monthly total-crop ET percentages**,
and cannot be inserted into a yield-response rule unchanged. Shorter supplied
crop duration changes demand; its higher coverage does not validate that calendar.
The unchanged Euphrates root scores despite paid capture reflect its timing and
losses in this scenario, not a complete regional non-inflation result.

Uniform small rain additions can repeatedly evaporate from the surface before
reaching deeper roots. This makes rainfall disaggregation a structural
uncertainty, especially for rain-only comparisons. Do not tune storms, soil,
calendar or crop coefficients after seeing these scores to close Egypt's gap.
First declare a timing sensitivity that preserves each original bin's rain
volume and uses independently specified event patterns; keep all outcomes.
Local observations and independent regions must then qualify any adopted rule.

## Verification and reproducibility

- 105 controls pass (15 new coupling controls plus 90 prior controls). The core
  audit includes complete FAO31 surface/background/total ET and 100 synthetic
  forests, with 7,532 joint field-steps compared against a scalar reference.
  Maximum state-history difference is 1.14e-13 mm. Fresh synthetic NPZ bytes match.
- A separate compiled scalar implementation imports neither producer nor coupler.
  It replays every case from empty stocks through convergence, checks spin-up
  counts, balances 72,914,688 final-cycle field-steps, and compares annual
  per-field initial/final stocks and 11 fluxes, monthly basin ledgers, daily basin
  stocks, thermal eligibility, root coverage and all 192,896 CSV rows.
  Full daily per-field trajectories are reconstructed by the reference, not
  exported or directly trajectory-compared. Maximum annual field difference is
  4.89e-12 mm; maximum reference daily closure residual is 1.38e-13 mm.
- All three fresh numeric files (`results.json`, `fields.npz`, `fields.csv.gz`)
  reproduce byte for byte. 910 protected files remain unchanged: 904 Earth-fit
  assets and the six earlier field/component numeric files. Largest joint
  annual residual is 1.15e-5 m³ against billion-m³ flows; this demonstrates
  numerical closure, not empirical accuracy.
- Browser receipt: `output/daily_river_fields_20261114/browser/browser.json`.
  It checks all 256 displayed rows, 162 filter combinations across six
  viewport/theme cases, nine byte-checked downloads, real gzip-CSV downloads,
  image loading, keyboard access, page width and hub/evidence/return navigation.
  The staged Windows-style checkout receipt is `windows_checkout.json` in the
  same output directory; the normal launcher verifies the complete release.

Canonical numerical outputs and receipts live in
`output/daily_river_fields_20261114/`; normal-page copies ship independently.
A full reproduction, using the project venv for numerical scripts and the system
Python with Playwright for browser checks, is:

```sh
.venv/bin/python scripts/audit_river_fields.py
.venv/bin/python scripts/daily_river_fields.py
.venv/bin/python scripts/daily_river_fields.py --out output/daily_river_fields_20261114/fresh
.venv/bin/python scripts/review_daily_river_fields.py
.venv/bin/python scripts/publish_daily_river_fields.py
.venv/bin/python scripts/build_fit_hub.py --date 2026-11-14
python scripts/check_daily_river_fields_browser.py
```

Each 256-case producer run takes roughly eight minutes with four workers here.
The producer pins the canonical core receipt even for a fresh output directory.
For a verification-only core rerun use `audit_river_fields.py --out
output/daily_river_fields_20261114/core/fresh`; regenerating the canonical core
receipt changes its test-runtime text and requires regenerating downstream
provenance. A complete replay may intentionally regenerate those receipts.
Serve the repository on port 8766 for the browser runner. Stage the final site
before `scripts/check_atlas_checkout.py --out
output/daily_river_fields_20261114/windows_checkout.json`, which checks staged
files with Windows-style checkout settings.

## Remaining programme

Daily coupling is complete. Next qualify forcing timing, soil/root development,
stage crop coefficients, deeper bare evaporation, infiltration, pond access and
drainage. Add the Tigris, shared Earth/fantasy generated river flow and independent
regional evidence. Freeze any harvest translation before comparing Nile gain
and Mesopotamian non-inflation, then rerun whole-empire supply calibration.
ET coverage does not establish grain yield, historical area or occupancy.

The release-3 settlement atlas and adopted marketed share 0.3923 remain current:
850 self-fed towns, 174 importers, 29 short, 91% fed; reach staffing 1042.
Whole-empire calibration still fails through Egypt. Dated occupancy/provider
measurements, S3–S5, complete resources/diets/work, mobile actors and political
authority remain separate unresolved programme obligations. This implementation
and its water maps do not complete those gates.
