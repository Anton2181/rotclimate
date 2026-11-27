# Wind errors involve different active components

All four declared diagnostic replays passed their original numerical
certificates. Archived scored monthly T/P/E/W/u/v, instantaneous gain/sink/W/P,
calendar and complete local budget arrays match in dtype, shape and bytes.
The instance wrappers changed no return value, parameter or model source.
No observed wind or pressure entered a solver, and no integration was retried.

The independent review reconstructs pressure-driven velocity from actual
current pressure, Pa/m gradients, signed Coriolis and friction, then reconstructs
total velocity from actual returned belt/turning and pressure parts plus drag.
Both velocity components match the saved raw solver samples to floating-point
precision. Heat and moisture winds are exactly equal at every saved scored
sample in these configurations. The pressure gate is reconstructed from its
actual previous-step pressure input, with clipping and crossing masks evaluated
before monthly averaging.

## July surface circulation, in physical east/north coordinates

| Case | Model eastward / northward m/s | NCEP eastward / northward m/s | Model belt contribution, east / north | Model pressure contribution, east / north |
|---|---|---|---|---|
| Somalia 1100 km | -6.808 / +1.512 | +2.498 / +6.332 | -7.115 / +2.525 | +0.307 / -1.012 |
| Somalia 4012 km | -4.018 / +3.296 | +2.498 / +6.332 | -4.557 / +2.399 | +0.539 / +0.897 |
| Sahara | +1.473 / +2.439 | -1.423 / -4.325 | -0.513 / -0.179 | +1.987 / +2.618 |
| North India | +4.394 / +3.450 | +1.080 / +1.211 | +1.986 / +1.786 | +2.408 / +1.665 |

Somalia's missing summer reversal is dominated by the prescribed belt/turning
part. Its small pressure contribution cannot reverse the strong westward
belt flow. The larger domain improves both components but retains the wrong
east/west sign. Full-year descriptive vector RMSE falls from 6.201 to
4.799 m/s. Rain nevertheless stays excessive: these same physical runs have
3556 versus 3589 mm/year, with compensating marine/advection sources recorded
in the earlier budget study. Better circulation under larger padding does
not imply a corresponding rainfall correction.

Sahara differs: its weak southward/westward belt contribution is overwhelmed
by a northward/eastward thermal-pressure contribution, giving a total direction
opposite to the reference. North India's two contributions reinforce a summer
flow stronger than the surface reference, even though its rain is already
too low. A universal extra turning/pressure strength is not supported by
these different responses. These are model-component identities; the reference
does not supply a matching decomposition into independently causal parts.

## Which gate is active

| Case | July cross-equatorial eligibility fraction | July mean pressure gate / maximum | Mean previous model pressure fall, hPa/1000 km |
|---|---:|---:|---:|
| Somalia 1100 km | 100.0% | 1.34% | -0.0569 |
| Somalia 4012 km | 100.0% | 33.09% | +1.1859 |
| Sahara | 0.0% | 67.32% | +2.4123 |
| North India | 99.51% | 98.33% | +4.1186 |

Somalia's gate peaks in spring and collapses during its modeled wet summer,
despite crossing eligibility remaining high. At the Saharan scored cells,
the crossing mask is inactive; changing the gate there is not a direct local
wind intervention. Regional changes outside the scored footprint and coupled
feedback can still affect those cells, as the earlier global-floor experiment
demonstrated. Do not equate a positive gate diagnostic to an active local turn.

The gate uses a smoothed previous-step **thermal pressure anomaly**, not full
sea-level pressure. Full NCEP SLP and its global-zonal anomaly were both processed
with the same regional grid stencil and retained as distinct diagnostic slopes.
Neither is an interchangeable physical target for this gate, and neither was
copied into it. The model's positive SLP coefficients select `pressure_wind`;
the alternative `thermal_wind` monsoon-strength scaling is not the active branch.

## Reference, geometry and precision

The public NOAA PSL NCEP/NCAR Reanalysis 1 reference is the verified 1991-2020
monthly sigma0.995 **surface** climatology on a 2.5-degree grid. It is not850hPa
or a resolved coastal jet profile. Period, scale factors, missing values,
latitude/longitude ordering and units were checked from raw files. Source SLP
is millibars and was converted explicitly to Pa. It is used only for diagnostics;
the existing Earth boundary PW/descent conditioning remains unchanged.

The initial review/figure compares projected grid-right/up model components
with a geographic reference. A supplemental review preserves those artifacts
and converts the model vectors and both contributions using the existing tested
inverse azimuthal-equidistant projection Jacobian, including metric factors.
Use **geographic_review.json** and **geographic_wind_components.png** for the
table/comparison above. The sign conclusions are unchanged; North India's
correction is larger than Somalia's. No physical run or gate was repeated.

The final figure was visually inspected: all four cases, two geographic wind
components, reference/total/component curves and stepwise gate/crossing fractions
are readable. Interpolated model-cell samples do not constitute independent
observed wind measurements. Resolution, terrain, climatological-period and
pressure-definition differences limit this to a descriptive mechanism audit,
not a new climate qualification or proof of a causal rainfall share.

Five new reference/momentum tests and the seven existing coordinate/aggregation
checks pass together (12 total). A test filename collision was corrected before
any replay: the existing test file was restored byte-exact and the new checks
moved to `tests/test_surface_wind_reference.py`. Production code/data were not
affected. Raw source URLs/hashes and normalized data are under
`output/circulation_reference_20261127/`; four captures and both reviews/figures
are under `output/circulation_components_20261127/`.

## Next intervention

Before changing the predictor, declare a bounded model-versus-observed-surface-
wind diagnostic on Somalia, Sahara and North India, with exact legacy controls
and unchanged SST/other coefficients/numerical criteria. Existing observed-wind
mode changes heat and moisture velocities together; retain all coupled changes
and source accounts. Project geographic reference velocities properly into
the model grid and verify actual solver wind samples against the prescribed
time interpolation. This can test whether correcting circulation improves
rain/temperature, without assuming it does from the vector mismatch alone.

That diagnostic would not be a deployable solution for fictional maps and
would need its own prospective integration budget before execution. Do not
increase a global turning floor, tune against W18c fine results or reopen it.
R58 parameters remain the retained profile, atlas r51 unchanged, AA unopened.
