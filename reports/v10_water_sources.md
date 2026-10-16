# A 2–3 hour batch: trace water supply and paired storm variability

15 October 2026. Prepared at the user's request for a run while away. The
six-hourly NOAA audit has paused on HTTP 429, so this experiment is entirely
independent of downloads. It implements the research strategy's source-water
diagnosis and checks whether the uniform/spatial-wind contrast survives several
synthetic storm catalogues. It is not another parameter search.

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_water_sources.py --run
```

Plan for **roughly 2–3 hours**, with a **2.5-hour invocation budget** and monthly
checkpoints. It may finish sooner. If the budget expires, the same command
resumes the remaining cases; completed cases and annual evidence are verified
and reused. A current incomplete month may need recomputing from its last
committed checkpoint. Numerical/provenance failures stop for diagnosis.

This is a regional development experiment. No parameter optimizer, NOAA
requests or atlas publication is included. The short weather-reference audit
can be retried separately later; this batch does not assume its result or
pretend to measure real weather covariance.

## Fixed design

Twenty cases: California and Iberia, uniform and spatial monthly background
winds, and five fixed synthetic storm seeds **41, 67, 103, 149, 211**. Within
each region, both wind backgrounds use exactly the same catalogue for each
seed. Seeds change weather generation only; humidity remains 1.0, storm rate
1/month, and all settings, geometry, targets and corrected thermal transport
remain identical to the completed pressure-based cases.

Each case starts from the original physical initial state and runs three to
six repeated annual cycles. Settling requires the existing physical criteria
and additional p95 source-store/monthly-source-rain changes <=1 mm. Unsettled
six-cycle cases remain labelled as such; they do not become validated results
or stop independent later cases. Numerical/source-budget failures do stop.

At seed 41's original completed cycle, physical water, energy, soil, monthly
rain and temperature/reference arrays must reproduce the saved pressure-based
controls exactly. This is a full integration check of the passive-diagnostic
implementation. Seed 41's climate is deliberately recomputed because its saved
fields cannot recover the missing history of water sources.

Order pairs the two wind backgrounds within each region before moving to the
next seed. Partial results therefore yield usable matched comparisons early.
All five catalogues are predeclared; there is no best-seed selection, early
winner promotion or parameter adjustment.

## What the new tracers measure

Four tags partition every atmospheric vapor store:

- Vapor present in the physical initial state.
- Water supplied through the external atmospheric boundaries.
- Evaporation from ocean cells inside the regional domain.
- Latest evaporation from land soil, including initial soil water.

The tracers use the exact water donor-cell face fluxes and vertical transfers.
Incoming prescribed boundary vapor receives the boundary tag. After the
unchanged physical evaporation step, each evaporative injection receives its
ocean/land tag. Rain at every layer and cell removes the tags in proportion to
the available vapor. No tag enters the physical step's equations or changes
the water, energy, evaporation, rainfall, soil or wind solution.

This is **last entry to atmospheric vapor**, not molecular ancestry. Rain
entering soil loses its old tag when it evaporates again, becoming land
recycling. Vapor that leaves the domain is not tracked through the external
forcing system. The model still assumes well-mixed sources within each cell
and layer. Source fractions are diagnostic, not causal attribution of errors.

Each source has an explicit atmospheric ledger: initial/end stores, gross
boundary inflow/outflow, local evaporation, all precipitation, and bounded
numerical reconciliation. Per-step source errors and reconciliation must be
<=1e-9 mm; annual source errors <=1e-6 mm. Tag sums reproduce physical water
and rain independently. The original water/energy/thermal checks remain active.

## What to read on return

Results live in `output/v10_water_sources/`:

- `summary.md`: completed-case rain skill, source fractions, settling and paired
  spatial-minus-uniform annual/coastal-winter rain contrasts.
- `state.json`: full coast/interior and winter source amounts, gross source
  transfers, physical budgets and repeated-weather comparisons.
- `progress.json` and `run.log`: current case, cycle and month.
- Per-case monthly/annual checkpoints: exact source stores, rain-by-source
  maps, physical fields, checksums and source budgets.
- `manifest.json`: immutable source identities, input hashes, settings and plan.

The main questions are whether moisture mostly exits without precipitating,
whether coastal/interior rain draws on different sources, and whether severe
spatial-wind drying is consistent across all five paired catalogues. Interpret
gross transport together with stores and rainfall; a ratio to boundary inflow
alone is not land precipitation efficiency. Separate source amount from rain
fraction: a large ocean fraction can still correspond to almost no rain.

Five synthetic catalogue draws measure sensitivity to the existing generator,
not real weather uncertainty or a multi-year climate ensemble. Repeated
warm-up cycles and neighboring cells are not independent samples. Existing
broad screens and zero-rain skill are reported without changing acceptance
rules. These reference-forced Earth runs cannot directly publish the fantasy
atlas or waive its Mediterranean/cold-dry/hot-dry protections.

Afterward, combine the source/placement evidence with the separately measured
real weather covariance before choosing a mechanism change. Retain a source
deficit, transport problem, immediate rainout and vertical quadrature as
distinct hypotheses; this batch does not prejudge which one dominates.

## Preparation checks and timing basis

Thirty-nine focused tests pass across source diagnostics, frozen pressure-based
transport, reference-weather parsing and Köppen maps. New tests cover known
source mixtures through condensation, pure ocean/land evaporation, boundary
transport without physics, exact physical equality, a manufactured small
calendar, serialized monthly resume, source summaries, corrupted evidence,
read-only defaults and the global time cap.

Sixteen independent January/July single-step probes on actual saved regional
states, both wind modes and seeds 41/67, reproduce physical arrays exactly.
Maximum per-source budget error is 3.34e-17 mm. Each probe integrates no more
than 60 seconds; no real annual/seasonal simulation was launched by the
assistant. These probes establish operator behavior, not annual rain results.

The completed four-case control batch took 16.67 minutes. The new probes add
about 1.6× median per-step cost; scaling that to twenty cases suggests roughly
two hours, but other catalogues, settling and checkpoint costs can change the
duration. The 2.5-hour budget is the practical limit, not a promise that all
twenty cases finish in one invocation. Preflight identities and checks are
saved separately under `output/v10_pressure_review/`.
