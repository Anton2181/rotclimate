# Test cloud formation before coarse-cell mixing

**Completed 16 October:** all 52 jobs / 192 saved years verify. Lower-interface
cloud gains repeat across four catalogues; coastal winter rain changes by at
most 0.173mm when the permitted time step is halved. Severe Mediterranean
drought remains. Iberia-domain wetting of reference-arid land offsets useful
Mediterranean gains. See the [complete saved-field review and maps](../output/v10_cloud_review/review.md)
and [next passive source replay](v10_cloud_sources_replay.md). The protocol
below is retained as the original handoff. No atlas update.

16 October 2026. The afternoon batch stopped at its budget: 51/100 jobs,
including all four reference diagnostics, 32 climates and 15 new-weather
diagnostics. The first four catalogues now have both regions' four forcing
comparisons. Stronger lifting consistently wets the coast but leaves a very
large deficit; repeating more catalogues addresses repeatability, not the
main missing process. Parent evidence is preserved and can be resumed later.

## Start now; no action needed in the middle of the night

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_cloud_mixing.py --run --stage overnight --hours 7
```

This begins with four exact controls and a four-case regional screen, estimated
20–40 minutes. It expands automatically only if the declared screen passes.
The full fixed plan is estimated at 5–8 hours, not a completion guarantee. The
invocation stops near seven hours and saves monthly checkpoints; the same
command resumes it with another budget. If the screen is unhelpful or fails
the settling/temperature guards, it stops without spending the remainder on
expansion. Physical/source failures stop for diagnosis.

To pause after the short screen for discussion first, use instead:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_cloud_mixing.py --run --stage smoke --hours 0.75
```

The overnight command then reuses the completed short-stage evidence in the
same output folder. Do not edit experiment sources during a run.

## Three inexpensive checks already completed

The [saved-field audit](../output/v10_cloud_mixing_audit/audit.md) records:

1. **Heating-stage suppression:** winter net differences in instantaneous
   condensation opportunities before/after relaxation are about 8–14% of
   realized winter rain in the four reference cases. These are opportunities
   along a fixed trajectory, potentially recounting vapor. They are not the
   rainfall of a climate without thermal relaxation, and cannot establish
   the size of that climate response.
2. **Mixing counterexample:** a constructed 20°C, 70%-RH parcel lifted from
   1000 to 800hPa condenses. Adjusting the parcel separately gives 0.451g/kg
   mixture at a 20% parcel fraction. Mixing with dry environmental air first
   gives a bulk RH of 41.9% and zero condensation. This proves the order and
   representation of mixing can matter, not that this example matches either
   real region.
3. **Independent real-input steps:** 24 Jan-1 probes of at most 60 simulated
   seconds, from saved year-end states, reproduce the bulk physics exactly.
   The unmixed parcel bound increases per-probe coastal rain while conserving
   water and the parent's diagnosed energy budget. These are not an annual
   rainfall result. Maximum residuals are 1.88e-16mm water, 6.08e-9J/m² energy
   and 2.22e-13°C in the signed temperature-change ledger.

The [ECMWF cloud-cover lecture](https://www.ecmwf.int/sites/default/files/elibrary/2005/16958-parametrization-cloud-cover.pdf)
explains why unresolved humidity/temperature variability permits cloud in a
partially cloudy grid cell whose mean humidity is below saturation. Our
60km cells and five atmospheric layers currently homogenize transported air
before applying all-or-nothing mean-cell saturation. The evidence motivates
testing this closure; it does not calibrate a subgrid distribution or validate
the proposed unmixed limit.

## Conservative prototype and its limits

Use only the existing positive upward dry-mass flux. Its donor vapor and
temperature are carried isentropically to the receiving-layer pressure, then
experience that layer's unchanged linear thermal relaxation. The separately
represented incoming parcel undergoes the same energy-coupled liquid
saturation adjustment as the parent. Remove condensate from its carried vapor
before bulk adjustment; retain its latent energy as sensible heat. Total rain
enters soil/runoff using the existing immediate-fallout convention.

No extra humidity, ascent, target cooling or boundary water is introduced.
The parcel is deliberately unentraining. This is a sensitivity bound on how
unresolved rising air is represented, not a realistic or formally exhaustive
upper bound for actual precipitation. It has no cloud-water memory, fallout
time, ice, rain re-evaporation, buoyant plume dynamics or inferred entrainment.
Prescribed circulation/work and reference-informed temperature remain. A wet
result would earn a more realistic cloud/transport design, not atlas promotion.

## Fixed staged design

- **Four controls:** one exact saved final-year replay for each region and
  original/steady or strong-lifting/linked setting, seed 41. Physical fields
  and all original ledgers must reproduce; no new warm-up.
- **Four screen cases:** the same seed-41 pairs with condensation permitted
  on the first three upward interfaces, excluding the highest 150hPa receiver.
  Initialize from the settled baseline's final state. Run three to six cycles.
- **Expansion gate:** all four screens settle and satisfy lower/upper thermal
  departure guards of 5/10°C. In each region the stronger-lifting/linked case
  gains at least 5mm of coastal winter rain. This is a predeclared mechanism
  screen, not independent climate validation or a statistical significance test.
- **32 fixed repeated cases:** seeds 67,103,149,211 × two regions × two fixed
  lifting/timing settings × lower-interface/all-interface parcel modes. Each
  is paired with the exact unchanged completed baseline and forcing table.
  The all-interface mode tests sensitivity to the coarse highest layer.
- **12 numerical checks:** seed 67 × two regions × two lifting/timing settings
  × bulk/lower-parcel/all-parcel modes, with half the permitted transport time
  step. Compare these with their normal-step counterparts before interpreting
  the mechanism as independent of numerical resolution.

52 jobs total. The amplification/timing settings are original/steady and
lift16/linked; they are not a pure lifting-only contrast. The causal contrast
of interest is the cloud rule at the same forcing. All forcing tables,
boundary moisture doses, settings and baseline evidence are pinned. Synthetic
catalogues were used before and do not represent observed-weather uncertainty.
No best seed, parameter optimization or inference about fantasy-map skill.

## Validation and evidence

139 focused tests pass, including manufactured parcel limits, exact bulk step
and tiny-year reproduction, real case-summary/checkpoint paths on tiny inputs,
monthly binary resume, water/energy closure, source/evidence corruption guards,
stage expansion and budget stops. The real-input preflight performs only the
24 independent short steps described above. The assistant started no real
annual climate or calibration.

Source:
`6eb5a1698f3be8d1529b528c11a57a002f5e46c7a97eae57eb8e5212c655e732`.
Prototype: `experiments/v10_parcel_condensation.py`; runner:
`scripts/check_v10_cloud_mixing.py`; prepared checks:
`output/v10_cloud_mixing_preflight/manifest.json`. Outputs accumulate in
`output/v10_cloud_mixing/{progress.json,state.json,summary.md,run.log,cases/}`.
All parent experiment sources/evidence and the fantasy atlas remain unchanged.
