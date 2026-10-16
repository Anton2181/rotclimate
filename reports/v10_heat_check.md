# First V10 results and the next heat/terrain check

Follow-up: the user completed this experiment. All eight cases fail at least
one screen; read [completed results and the next atmospheric reference audit](v10_forcing_audit.md).
The protocol below is retained as the original experiment record.

The user completed all four Earth pilot cases. Their twelve saved years, input
hashes and frozen source fingerprint were verified. Water-budget errors are
small, but the rainfall representation fails this first accuracy check:

| Region | Storms: model / observed annual rain (mm) | Storms monthly MAE | Mean-only monthly MAE |
|---|---:|---:|---:|
| California | 1,469 / 402 | 115.87 mm | 108.27 mm |
| Iberia | 1,013 / 424 | 89.57 mm | 88.61 mm |

California's storm result worsens error. Iberia's mean-only control fails the
soil-settling check, so its comparison is diagnostic rather than a settled
verdict. Rain itself is nearly stable there; final soil p95 change is 3.66 mm
against the declared 1 mm limit. Do not relax that limit to call it a success.

Rain is concentrated in implausible mountain peaks. In California with storms,
13.4% of scored land exceeds 3,000 mm/year and supplies 69.2% of predicted land
rain; the maximum is 26,575 mm/year versus 721 observed at that cell. The
mean-only maximum is already 22,261 mm/year. Storm frequency alone is therefore
not the main explanation for this failure.

## Diagnosis

The frozen source imposes observed temperatures when calculating saturation;
water condensation cannot warm the air. At the maximum-rain Sierra cell, the
saved end-of-year state under January mean-flow forcing yields lower-layer
condensation equivalent to about 1.50°C/hour of latent heating that the engine
does not retain. In the Atlas Mountains counterpart the tendency is 1.31°C/hour.
These are single frozen-state diagnostics, not averaged annual heat sources.

Most rain in that January snapshot is from lower-layer saturation, not only
upper-layer rain from the terrain-induced return flow. Disabling drag while
holding the saved state fixed reduces mean California rain only from 8.62 to
8.28 mm/day. A new equilibrated run is needed to establish annual effects.

The hypothesis is that fixed cold terrain temperatures create a persistent
condensation sink. The next experiment couples water to heat, rather than
reducing precipitation by an arbitrary multiplier. This follows latent heating
in [NOAA/GFDL moist adjustment](https://www.gfdl.noaa.gov/bibliography/related_files/yk9801.pdf)
and the [NCAR static-energy formulation](https://www.ncl.ucar.edu/Document/Functions/Contributed/static_energy_atm.shtml).
The latter is an approximate hydrostatic diagnostic; its conservation is not
a claim to have solved full atmospheric dynamics.

The reproducible saved-state diagnosis is in
`output/v10_pilot_diagnosis/diagnosis.md` and `diagnosis.json`. Rerun analysis
without a seasonal simulation:

```sh
.venv/bin/python scripts/diagnose_v10_pilot.py --write
```

## Next user-run command

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_thermodynamics.py --run
```

All existing data and four original controls are reused. No downloads or
calibration. Eight new fixed cases: two regions × storms/mean-only × two closures:

1. **Heat:** same circulation, terrain and air masses, but transport approximate
   moist static energy with water, retain latent heating during condensation,
   and relax sensible temperature toward the same observed reference over five
   days. This tests the thermal-closure package together, not latent heating
   independently of heat transport/relaxation.
2. **Heat without terrain drag:** identical thermal closure, with the terrain
   factor removed from the prescribed wind only. Elevation, air mass, pressure,
   thermodynamic height, observed forcing and precipitation references remain
   unchanged. This is a diagnostic ablation, not a proposed mountain-free model.

Each new case has three repeated-forcing years. Compare years 2 and 3 for water,
rain and temperature settling. The one unsettled original control gets at most
two additional unchanged years in a separate output folder. Stop extending it
as soon as it meets the original settling check. If it still fails, retain the
failure rather than use it as a settled comparator. At most 26 new simulated
years; no unbounded search and no automatic atlas publication.

Original pilot integrations totaled about 31 seconds across the twelve years
on this computer. The coupled solver does more work per step and its regional
runtime is not measured. Expect monthly progress with measured time estimates;
there is no basis for calling this another eight-hour run.

Output: `output/v10_heat_check/summary.md`, `summary.json`, two rainfall/temperature
comparison PNGs, case checkpoints and progress records. Completed years resume
after checksum and budget verification. An unfinished year restarts. Manifest
checks refuse changed code/configuration/input. Preserve old results using a
new `--out` if the experiment code changes. Both frozen V10 and production V9
source/input fingerprints are unchanged by this follow-up implementation.

## Energy model and limits

Transport `h = cp*T + g*z + Lv*r` per kg dry air with the same discrete dry-air
fluxes used for water. Layer heights use terrain plus the existing pressure
fractions and 8,400 m scale height. Saturation adjustment solves for rain and
the resulting warmer temperature while holding static energy fixed. Moving to
a higher layer also includes the geopotential term. A safeguarded nonlinear
solve has a fixed iteration limit; unsupported thermodynamic states fail
explicitly instead of clipping their temperature.

The approximation neglects water heat capacity, rain sensible enthalpy, ice,
kinetic energy, radiation dynamics and momentum feedback. Land/ocean surface
latent enthalpy is an external input, and finite temperature relaxation is an
explicit heating/cooling reservoir. Ocean temperature is still prescribed.
Thus this is a **budgeted approximate static-energy experiment**, not a closed
Earth energy budget or an independently predicted temperature climatology.

Per-step water error <=1e-9 mm and annual error <=1e-6 mm are retained. Static
energy closure must be <=1e-5 J/m² per step and <=1 J/m² over a year; boundary
energy export, latent input and temperature relaxation are recorded separately.
Small accounting errors alone do not establish physical accuracy.

Year-2/3 monthly and final layer temperature changes must each be <=0.05°C at
p95, in addition to the original rain/storage settling limits. Report lower/
upper temperature departures from the time-averaged prescribed reference.
Provisional screening guards: p95 absolute monthly departure <=5°C lower and
<=10°C upper. These are declared development screens, not validated uncertainty
intervals. A case that reduces rain error through implausible warming fails
the mechanism-comparison eligibility screen.

Observed precipitation never enters either closure or its forcing. Temperature
is still informed by observations; do not claim independent temperature skill.
California and Iberia are development/transfer evidence already examined, not
a fresh untouched validation set. The fantasy-map Mediterranean/dry-zone policy
and atlas remain unchanged. Further climate integration requires Earth evidence
that survives these checks.

## Verification

Manufactured tests cover constant-MSE/constant-mixing-ratio transport,
open-boundary energy accounting, latent warming, dry adiabatic height changes,
evaporation/condensation ledgers, finite relaxation, a tiny zero-flow year,
checkpoint resume, failed-budget rejection, temperature-drift screening,
bounded control extension and a complete runner with fake integrations.
Seventeen new tests pass; together with the relevant frozen pilot/audit/policy
checks, 66 tests pass in 21 seconds.
No regional integration, calibration or atlas export was launched by the
assistant. Only saved-field analysis and fast tests were run.
