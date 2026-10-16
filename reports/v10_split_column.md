# Five-layer vertical-structure comparison

## Completed review — 15 October 2026

All twelve cases settle after four cycles (48 total; 31.85 saved integration
minutes). All immutable inputs, case identities, annual evidence hashes,
summaries, physical balances and annual signed thermal changes verify. The
maximum reconstructed annual residuals are 4.99e-12 mm total water,
2.26e-5 J/m² energy, 3.31e-11 mm gross/net boundary flow and 3.48e-11 mm
atmospheric water. No atlas update.

California uniform MAE falls 40.07 → 27.37 mm in the column-matched control,
but **all net improvement comes from reducing error in previously over-wet
cells**: +13.72 mm improvement there, offset by -1.02 mm in already under-wet
cells. Coastal winter rain falls 335.0 → 250.5 mm against 534.8 observed;
Mediterranean-to-arid errors increase 46.4% → 56.5%. Iberia uniform monthly
error barely changes. Matched spatial controls produce 20.4 / 26.6 mm/year
against 401.8 / 424.2 observed.

Matched column concentration still increases gross boundary water import by
9.6–15.3%. About 97–98% of additional rain from the RH300 upper assumption
forms in the highest, 150 hPa representative layer. This is formation-layer
accounting, not source tagging; upper humidity and cloud/ice treatment remain
unvalidated. More levels alone do not restore Mediterranean winter rain.

The separate [completed saved-field review](../output/v10_split_review/review.md)
includes new [Köppen maps](../output/v10_split_review/koppen_comparison.png),
coastal/interior seasonal comparisons and complete case statistics.
Thirty-nine focused tests cover the review, circulation audit and related
split/source/map mechanisms.

A [three-hour forcing-only audit](../output/v10_split_review/storm_ascent.md)
finds coastal winter descent in both spatial backgrounds. Existing storms
reverse descent in only 2.08% / 1.94% of coastal cell/tick pairs. These are
engine-implied motions, not observed omega or proof that the monthly means
should be made wetter. The next [event-forcing design](v10_event_forcing_plan.md)
separates episodic lifting from moisture timing and explicitly requires
actual influx controls. No new seasonal integration was launched.

The original pre-run design and acceptance interpretation follow unchanged.

## Original prepared protocol

15 October 2026. The completed [source-water review](v10_water_sources_review.md)
verifies all twenty cases and finds severe drying under spatial background
winds in all five synthetic catalogues. Roughly 98–99% of incoming boundary
and local ocean vapor is exported. The following prototype targets a separate,
measured vertical-profile weakness; it does not assume that weakness caused
all missing rain.

## Why this change earns a test

The current upper cell spans 607.95–0 hPa and samples reference humidity near
304 hPa. In the reference-covered 608–300 hPa portion, that midpoint represents only
26.7% of native-reference water in California and 27.4% in Iberia. A cached-data
quadrature calculation with a split at 300 hPa represents 95.5% / 94.5% there;
over the entire shared 925–300 hPa window, representation changes from
83.2% / 84.8% to 97.0% / 96.3%.

These numbers compare prescribed monthly reanalysis profiles, not transported model
water, complete atmospheric moisture or simulated rain. No climate improvement
has yet been calculated. They support testing vertical structure with
pressure-consistent heat/moisture rather than simply increasing humidity in
the old cold cell. See the [cached forcing audit](../output/v10_water_sources_review/forcing_audit.md).

## Run

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_split_column.py --run
```

Estimated **45–75 minutes**, with a **90-minute invocation budget**, three to
six repeated cycles per case, monthly checkpoints and same-command resume.
The estimate scales from completed controls; changed settling can require a
second invocation. A budget stop preserves completed cases and the last
committed month; the unfinished month may need recomputing. Numerical or
provenance failures stop for diagnosis.

There are twelve new fixed cases and four reused controls. Inputs are cached;
no NOAA access, parameter optimization or atlas export is included. Default
without `--run` prints the plan only. The assistant launched no real seasonal
integration; this is the user's next run.

## Controlled structure and circulation

The lowest three pressure layers, their masses, heights, local thermal targets
and profile humidity entries remain identical to the completed four-layer
controls. The old upper cell splits at 300 hPa, producing representative
pressures **453.975 and 150 hPa**. New upper thermal targets and annual mean
heights are sampled from the cached local pressure-level temperature/height
data. Column mass and original surface pressure are retained.

The circulation deliberately remains a coarse-flow control. The original
four-layer projected face flux is computed exactly as before. Its upper
horizontal flux is partitioned in proportion to the two new dry masses;
lower face fluxes and the aggregate upper flux are preserved. Interface
exchange follows stationary layer continuity, including the new internal
interface. This resolves a new vertical path, not new observed horizontal
winds at 454 and 150 hPa. A separate reference-wind update would be another
experiment.

Potential-temperature transport, fixed-pressure conversion, evaporation,
instantaneous rainout, soil and six-process thermal accounting retain the
frozen algorithms. Relaxation still assigns the lowest two layers the lower
timescale and all remaining layers the upper timescale. The new engine is
separate; original four-layer sources and evidence remain intact. Diagnosed
prescribed-flow work remains explicit. Momentum/kinetic energy and radiation
are unsolved; budget closure is not a new total-energy GCM claim.

## Three hypotheses, each in both regions and both wind backgrounds

| Variant | Incoming humidity above 300 hPa | Boundary water amount |
|---|---|---|
| `split_dry` | Zero prescribed upper humidity | New split profile |
| `split_rh300` | Offshore monthly RH300 retained at 150 hPa temperature/pressure | New split profile |
| `split_column_matched` | Same retained-RH300 assumption | Original four-layer local column vapor concentration |

The new 454 hPa offshore mixing ratio comes from the cached humidity reference.
There is **no cached observed humidity above 300 hPa**. Zero incoming humidity
and retained RH300 are explicit sensitivity assumptions; neither is claimed
as observed upper-air forcing or a rigorous physical bound. The upper cell
can still receive transported water internally, so “dry” does not mean an
impermeable lid or a permanently empty layer.

For the matched control, after each model's local saturation caps, scale the
five-layer boundary mixing ratios down so their mass-weighted column vapor
equals the original value at that cell and time. No upward scaling or
supersaturation is introduced; infeasible matches stop. This holds the
column concentration fixed, **not wind-weighted moisture import**, because
different vertical distributions encounter different layer velocities.
Initialization retains the common 60%-saturation ceiling, so its initial
store need not match exactly; periodic settling is evaluated separately.

The paired comparison therefore tests coupled vertical heat/moisture structure,
with controls for bulk column water and the unknown upper humidity. It is
not a pure humidity perturbation or coordinate-invariance test. All cases use
seed 41's unchanged storm catalogue. The earlier five-seed results support
the baseline diagnosis, not robustness of a new five-layer result.

## What determines the next decision

Results go to `output/v10_split_column/`: immutable code/input/reference and
baseline identities, exact input arrays, monthly resume fields, annual hashes,
physical/thermal/work/layer-rain budgets, coast/interior winter/summer
responses, progress and a comparison summary. Gross vapor influx/outflux is
also saved and independently checked against net boundary transport, so the
column-matched case's actual moisture supply can be examined directly.

Read the controls together:

- Improvement in the column-matched case would support a role for vertical
  structure/thermal treatment at fixed column concentration. It would still
  require checking actual influx and other changed vertical processes.
- Improvement only with the larger native-informed profile leaves additional
  moisture supply entangled with vertical structure; it is not evidence for
  a geometry-only fix.
- Strong dependence on the two unobserved-upper humidity assumptions prevents
  a confident result and calls for better upper reference data.
- Continued coastal-winter drought in both cases directs effort back toward
  event-linked fronts, boundary structure, ascent and cloud/transport physics.

The existing broad rain/thermal screens are preserved. They do not establish
realistic circulation or independently predicted temperature. Compare coastal
wetting, interior dryness, zero-rain skill, thermal departures and diagnosed
work, rather than select a winner on monthly MAE alone. Six-cycle unsettled
cases remain labelled; independent cases can continue. No automatic selection,
fantasy transfer or atlas promotion occurs. Source tracers are not generalized
in this initial structural batch; whole water/energy and layer rain are saved.

## Verification

**60 focused tests pass**, covering new split behavior and the previous
pressure/source/weather/Köppen checks. New checks include exact four-layer
step and manufactured-year regression, conserved lower/aggregate upper
horizontal flux and mass, dry constant-theta behavior, moist five-layer
budgets/process shapes, column matching after caps, refusal of upward scaling,
serialized resume and corruption checks, settling that examines the fifth
water layer, read-only default, batch resume and the global time cap.

**48 independent regional probes integrate <=60 seconds each:** 36 five-layer
January/July/active-storm cases across all variants and wind backgrounds, plus
twelve four-layer saved-state regression comparisons. Four-layer physical
arrays and budgets reproduce exactly. Five-layer maximum absolute errors are
9.92e-16 mm water, 1.38e-8 J/m² energy, 4.04e-12 kg K/m² theta transport and
1.90e-13°C thermal accounting. Lower face fluxes remain exact and aggregate
upper fluxes agree to roundoff.

There are also 730 independent daily boundary-only queries, with no state
integration. Maximum column-matching error is 1.07e-14 mm. Downscale factors
span 0.661–0.960 in California and 0.817–0.967 in Iberia; no upward adjustment
is needed on those inputs. These checks verify mechanisms and serialization,
not annual settling or climate improvement.

Protocol, all probe results and frozen-parent verification are saved in
[`output/v10_water_sources_review/split_column_preflight.json`](../output/v10_water_sources_review/split_column_preflight.json).
The production model, atlas, all completed experiment sources and the paused
NOAA audit remain unchanged. The fantasy forcing bridge and protected-zone
requirements remain necessary before any eventual fantasy publication.
