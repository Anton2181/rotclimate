# Test local boundary humidity before another rain adjustment

## Completed result — 16 October 2026

All twelve cases finish: four exact controls and eight three-cycle candidates,
28 saved years, 34.68 integration minutes. A new independent saved-data review
verifies every source/config/evidence hash, annual water/energy balance,
signed thermal ledger, monthly actual gross import, first eligible settling
point, parcel/total layer split and reconstructed summary. Maximum annual
water residual is 4.2e-12mm; energy residual 2.5e-5J/m². All temperature guards
pass. The frozen source and parent evidence are unchanged.

The primary **local-matched lower-interface** comparison gives:

| Response | California uniform → local matched | Iberia-domain uniform → local matched |
|---|---:|---:|
| Coastal winter rain | 91.83 → 92.96mm, target 534.82 | 59.10 → 61.28mm, target 439.18 |
| Reference-Mediterranean winter rain | 139.66 → 141.81mm, target 693.96 | 68.52 → 72.80mm, target 475.17 |
| Reference-arid summer rain | 12.39 → 17.87mm, target 81.06 | 86.35 → 73.08mm, target 57.17 |
| Reference-arid summer cell/month MAE | 11.810 → 11.386mm | 16.051 → 14.137mm |
| Reference-Mediterranean cells still arid | 75.4% → 78.3% | 94.9% → 94.4% |

Both lower-cloud cases pass the small declared process screen. California's
improvement reduces an existing dry bias; it is not removal of excess summer
rain. Iberia's improvement mainly reduces the positive summer error: the
mean positive cell/month bias falls 10.46 → 8.39mm, while the mean deficit
increases 5.59 → 5.74mm. These signed components are spatial/monthly error
decompositions, not the bias of the area mean. The Iberia domain includes
North Africa. Coastal and interior masks overlap the climate-regime groups.

Redistribution is useful but cannot explain the dominant winter drought.
The unmatched local pattern adds 11.9%/4.5% gross input and raises coastal
winter rain by 10.07/5.01mm, confounding amount with pattern. Matched cases
add only 1.13/2.18mm. Do not select the extra-water version by its headline
rain gain or promote either to the fantasy atlas. California's worse class
result also shows why aggregate MAE alone cannot guide selection.

See [verified seasonal and Köppen comparison](../output/v10_spatial_humidity_review/review.md).
The next step is four exact diagnostic replays separating moist upward
transport, cloud formation at coarse vertical paths and dry receiving air;
see [cloud-geometry protocol](v10_cloud_geometry.md). No additional parameter
sweep, NOAA request or atlas update is prepared.

The original design below is retained as declared before completion.

## Original protocol

16 October 2026. The [completed source replay review](../output/v10_cloud_source_review/review.md)
verifies four exact physical replays, 8.81 integration minutes. In the
lower-interface cloud case, reference-arid land in the Iberia domain receives
86.35mm of summer rain: 74.9% last entered the atmosphere at a boundary,
16.9% through local ocean evaporation and 8.2% through land recycling. The
unknown initial atmospheric share is negligible in summer. California's
corresponding boundary share is 90.7%. These are last-vapor-entry labels, not
original soil ancestry or the causal effect of removing a source.

The existing boundary humidity applies one offshore-mean profile to every
edge, including inflow at land cells. This is an explicit prototype
simplification; the source labels do not prove it caused the misplaced rain.
Cached native monthly humidity permits a fixed comparison of that pattern.

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_spatial_humidity.py --run
```

Twelve cases: four exact saved-year controls followed by eight fixed regional
comparisons. Estimated 45–75 minutes, 90-minute invocation cap, monthly
checkpoints and same-command resume. The assistant has not launched a real
annual integration. No calibration, download or atlas update.

## Fixed input comparison

Use California/Iberia, seed67 and the unchanged stronger-lifting/linked
forcing. Test both the bulk rain rule and the lower-interface cloud bound.

- **Uniform controls:** reconstruct the original three-hour boundary values
  exactly and replay each saved final year from the exact preceding-year state.
  Every physical array and original ledger must reproduce, except elapsed time.
- **Local:** sample cached NCEP/NCAR 1981–2010 monthly humidity at each
  boundary cell and actual model pressure, with the original nominal event
  pulse and safe local saturation caps. Both pattern and total input can change.
- **Local matched:** use the same local pattern, normalized so that actual
  gross incoming vapor in every month equals the original control. This
  isolates redistribution at fixed total input; it is a control, not a claim
  that the normalized humidity is the unmodified observed climatology.

Each new climate starts from its paired settled baseline final state and runs
three to six cycles. All outcomes remain labelled, including unsettled cases.
Dry horizontal/vertical fluxes, original event catalogue, nominal pulse timing,
temperature targets, terrain and physical operators stay fixed. Actual humidity
means, variance and pulse shape after caps/normalization need not match.

Local samples use the verified cached specific-humidity-to-mixing-ratio
conversion, nearest native horizontal cells and log-pressure interpolation.
All four observed model pressures lie within native 1000–300hPa coverage.
The unobserved 150hPa incoming layer stays explicitly dry. No extrapolation or
new NOAA request. A 2.5° monthly climatology is not observed hourly weather or
independent validation against WorldClim's different reference period.

## Cheap forcing evidence, before new climates

The two complete 2920-tick forcing tables are prepared. Uniform reconstruction
is byte-identical to the parent boundary; circulation is unchanged. In the
Iberia domain's summer (April–September), the matched local pattern retains
554.42mm of gross incoming vapor while redistributing:

| Boundary cell category | Original | Local, matched total |
|---|---:|---:|
| Land | 110.82mm | 94.13mm |
| Marine | 443.60mm | 460.29mm |

Land-cell input falls 15.1%. In winter it falls 25.5%. These categories refer
to boundary cells inside the regional grid, not outside-domain molecular
ancestry or a traced fraction of rain. The unconstrained local pattern raises
annual gross input by about 4.5% in Iberia and 11.9% in California, illustrating
why the matched-input control is necessary. This is forcing evidence only;
it does not establish any annual rainfall benefit.

## Decision after completion

The primary mechanism contrast is local-matched versus uniform under the same
cloud rule. Examine continuous reference-arid summer error, Mediterranean
winter rain, coastal winter rain and full spatial error maps. A useful response
reduces misplaced arid-land summer error while preserving coastal winter rain
within 2mm of its paired baseline, and passes settling/temperature checks.
This is a declared process screen, not a production-selection rule. Retain the
unmatched local case to distinguish amount changes from spatial redistribution.
Do not select whichever case has the lowest aggregate MAE or publish the atlas
from this single synthetic catalogue. If the local pattern does not resolve
placement, focus on circulation and the unmixed cloud/fallout assumptions.

## Readiness

162 focused tests pass. New tests cover native-pressure sampling/dry lid,
identical original boundary reconstruction, fixed-flow drivers, feasible and
infeasible monthly dose control, real case-summary/checkpoint paths on tiny
manufactured climates, restart, integrity and read-only default use. Twelve
independent regional probes of at most 60 simulated seconds pass water/energy
and signed temperature checks. No real annual case was started by the assistant.

Source:
`97afe7ac31cf7e9d9409f9d75b87a81314ec78a21a5c7c696717b38f4c2e662e`.
Prepared data: `output/v10_spatial_humidity_preflight/`. New outputs:
`output/v10_spatial_humidity/{progress.json,state.json,summary.md,cases/}`.
All prior sources/evidence and the current fantasy atlas stay unchanged.
