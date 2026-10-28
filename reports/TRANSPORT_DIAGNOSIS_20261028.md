# Six-case layer-transport diagnosis — 28 October 2026

This is a diagnostic milestone, not a new calibration or climate improvement.
The previous finite broad searches have not established a global optimum, and
repeated rainfall biases justify inspecting the physical equations before
another coefficient search. Only six regional reruns are authorized by the
literal plan: North India, Mexico and the Pacific Northwest, at the existing
legacy3.5m/s (global04) and hydrostatic-half3.5m/s (global06) profiles. No knob,
background, objective or adopted atlas climate changes.

The observer is isolated from the physical solution: its arrays and closure
inputs are copies, and its return is unused. The default and enabled coupled
toy climates reproduce the pre-edit T/P/W/layer-water/days bit-for-bit. Tests
also attempt to corrupt callback payloads and check that current and next-step
water remain unchanged; reconstruct nonzero counterflow/diffusion/storm terms;
and distinguish mean(q*u) from mean(q)*mean(u).

Source transition: committed5917086 →985ba41 changes only the core
reservoir_moisture observer hook. The new runner verifies both Git bytes,
replaces only that one parent source hash, verifies every other parent source,
and freezes new exporter/recorder/reference code and all cached inputs before
any real integrations. The literal six-run plan must be committed first.
Every original climate NPZ field and actual case/parameters must reproduce the
saved ocean-pilot counterpart exactly. Failures are preserved and counted.

The sidecars save all33 solved seasonal steps, including8 primer steps and25
scored steps: actual branch winds, layer water and relative dry mass, dry donor
exchange and vertical water flux, simultaneous upwind vapor faces, diffusion,
surface evaporation, storm exchange, drying, recycled upper rain, ground-rain
components and equation residual. Projected velocities point right/up; y-face
flux points down; signed vertical water flux points upward. Flux divergences
and equation residuals apply only to the solved interior. These are steady
seasonal balances, without an atmospheric storage tendency. Relative dry mass
must be multiplied by101325Pa/g before interpreting W/mass as kg/kg.

New925–300hPa winds integrate the two-box piecewise q and branch velocity over
actual pressure overlaps at every step before averaging, instead of comparing
a full-column modeled wind against a partial observed column. Both old audit
arrays and new matched arrays remain available, with their distinct definitions.
Land P/PW/winds use identical observed-rain land pixels, Gregorian month overlap,
true projected area and fully covered native footprints (>=80%). Low925hPa
reference heights and modeled surface pressure exclude below-ground columns.
The geometry-only preflight finds11 matched India land cells,1 Mexico land
cell,0 PNW land cells; Mexico has1 matched ocean cell and PNW3. No fallback
pressure or footprint is selected after seeing results. Full-score land budgets
are separate. NCEP monthly q*u omits submonthly covariance, and WorldClim rain
has a different reference period; these inputs cannot close an observed water
budget or establish independent validation.

Mexico's new NOAA PSL NCEP/NCAR1981–2010 monthly subset is held in a separate
cache with exact URL/byte/SHA provenance. Earlier frozen caches and outcomes
remain untouched. The new reference plan and sources manifest are fixed before
outcomes. No observed humidity or winds enter the climate forcing. Inherited
WorldClim cloud and remote-monsoon backgrounds still make the regional solver
conditional, rather than a fully independent global forecast.

Before this diagnosis:1879 actual Earth integrations,1875 strict passes and4
historical failures. A completed six-case diagnosis brings this to1885 attempts;
all attempts, failures and interrupted jobs are retained. Toy and geometry-only
preflights do not count as Earth climate runs.

After the six cases, use transport, storm redistribution and rain conversion
signatures to choose one bounded physical hypothesis with a predicted response.
Actual rainfall gains must be reported independently of native-state objective
improvements. No parameter proposal or adoption follows automatically from a
signed budget term. See the [recovery plan](RAINFALL_RECOVERY_PLAN_20261028.md).

## Controller recovery declared before remaining integrations

Two original global04 integrations (India and Mexico) completed with strict
checks and every original climate field exact. A controller parameter check
then compared in-memory tuples to lists in the old JSON record and raised
before reading the second completed row. PNW was interrupted by worker-pool
teardown. Saved parameter values are identical after JSON canonicalization.
The original runner, protocol, review, log, rows and arrays are preserved.
The separate recovery plan binds them by SHA, reuses the two completed cases,
counts the interrupted attempt, and runs only the four missing cases. Thus
there are seven total attempts for six completed diagnostic cases, bringing
the cumulative counter to1886 attempts if recovery completes. The controller
fix is tested to preserve true numerical parameter differences. No scientific
criterion, physical source, input, mask or original result is changed.

## Completed results and interpretation

Recovery completed all four remaining cases. All six final cases pass their
strict numerical checks and reproduce every original climate NPZ field exactly
(22fields for India and15each for Mexico/PNW). PNW's extra native archive also
matches exactly. Independent analysis verifies592 frozen files,198 actual
primer/scored solves, simultaneous upwind and diffusion faces, dry donor flux,
layer equations and ground-rain/recycling coefficients. The largest discrepancy
between independently reconstructed and saved residuals is below1e-12mm/day.
The cumulative counter is1886 attempts,1881 strict passes,4 historical failures
and1 controller interruption. No scientific failure occurred in the six
completed cases; no parameter search or atlas climate adoption occurred.

These diagnostic summaries use the original full scoring land mask, true
projected area and Gregorian month overlap. The original score arrays and
unweighted/equal-month metrics remain unchanged.

| Region / season | Legacy rain mm | Hydrostatic-half rain mm | Observed mm | Half storm supply mm | Half empirical convection mm | Half overflow rain mm |
|---|---:|---:|---:|---:|---:|---:|
| North India / JJA | 187 | 216 | 515 | −80 | 6.5 | 4 |
| Mexico / SON | 265 | 323 | 158 | −93 | 45.5 | 129 |
| Pacific NW / DJF | 427 | 416 | 340 | +83 | 0 | 102 |

India's hydrostatic-half JJA lower layer receives240mm horizontal advective
supply and146mm surface evaporation, and exports288mm upward. Upper rain is
157mm versus58mm lower rain;22mm upper rain evaporates back into lower air.
The vertical288mm is an internal redistribution, not a column loss. Total
horizontal advection is+212mm, with−80mm storms and−63mm drying. Those signed
terms cannot be interpreted as independent recoverable parts of the300mm rain
deficit. Only6.5mm is the explicit empirical convective component: blindly
amplifying that coefficient is poorly motivated without evaluating its humidity
and circulation feedbacks. Dynamic/orographic rain dominates in this model.

Mexico's upper layer produces269mm of323mm autumn rain, including129mm local
supersaturation overflow. Storm exchange supplies66mm below but removes159mm
above. Rain is excessive in autumn despite near-correct summer amplitude;
any mechanism test must retain that seasonal distinction. PNW's winter ocean
wind comparison uses3 native ocean cells, never nonexistent lowland land cells.
Full land rainfall is overestimated even though partial ocean water is low.

### Circulation, separated from humidity weighting

The new925–300hPa vector integrates actual per-step q×wind before spatial and
calendar averaging. This fixes the old full-column versus partial-column
comparison mismatch; it does not retroactively change any historical score.
On11 India lowland footprints, JJA partial water is about28.5mm versus37.7mm
reference. The mean modeled moisture wind is westward/northward while the
reference is eastward/southward. Both ocean settings have nearly identical
wind errors. Mexico's one matched land cell also has large circulation errors;
it cannot stand in for the full mountainous region.

A supplementary, explicitly exploratory pressure-node comparison uses the SAME
925hPa-valid footprints, with no new fallback masks. It tests925/850/700/500/
300hPa model two-box velocities against reference vectors; hence wind errors
can be seen independently of errors in the humidity weighting. The three-month
means below are illustrative equally weighted monthly vectors; the download
also contains all area/day-weighted errors and every month.

| Region / sample / season | Pressure | Model east/north m/s | Reference east/north m/s |
|---|---:|---:|---:|
| India /11 land / JJA |925hPa| −0.48 / +0.95 | +2.21 / +1.56 |
| India /11 land / JJA |700hPa| −0.46 / +1.36 | +0.43 / −1.98 |
| Mexico /1 land / SON |925hPa| −1.34 / −0.80 | −1.46 / +3.30 |
| Mexico /1 land / SON |700hPa| −1.48 / +0.73 | +3.87 / +1.02 |
| PNW /3 ocean / DJF |925hPa| +6.06 / +4.07 | +2.43 / +4.05 |
| PNW /3 ocean / DJF |700hPa| +4.56 / +3.42 | +8.29 / +3.08 |

This supports testing the lower/upper circulation structure before more ocean
RH or rainfall-coefficient calibration. Existing upper winds are obtained by
algebraically completing a stationary dry-column projection. Their shear is
not independently tied to the thermodynamic horizontal gradient. The two-box
representation is too crude to reproduce the full observed vertical profile,
even if its native partial-column mean improves. This is evidence of a
structural limitation, not proof that a proposed replacement will improve rain.

The next single hypothesis is to derive a lower-to-upper wind difference from
hydrostatic/geostrophic thermal wind, then apply a common mass-weighted
projection that preserves that shear and exact dry continuity. Use fixed
pressure-layer geometry and Earth constants, no observed wind forcing or
region-specific correction. First verify uniform/isothermal limits, thermal
wind signs, projection continuity and uniform-q transport in an isolated
operator. Only then declare a small paired coupled pilot, with rainfall primary
and all regional temperature/conservation tradeoffs exposed. Do not attach
new search knobs before this process mechanism is tested.

All four figures and full monthly/seasonal/native diagnostics are published in
the current launcher-served climate accuracy companion. The maps are fixed
reference/model comparisons, not a new atlas climate. The reference periods,
submonthly covariance gap and small/empty native samples remain material limits.
