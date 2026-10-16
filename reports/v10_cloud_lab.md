# Cloud-process laboratory: transport and mixing before another fit

16 October 2026. Implemented and evaluated **166 manufactured parcel paths,
18 closed two-column circulations and 10 periodic contact controls**. The
numerical audit took 6.02 seconds, excluding plotting. No real regional year,
calibration, download or atlas update was performed.

## What changed in our diagnosis

**The transport/phase-change interaction deserves its own numerical test before
we fit another cloud parameter.** This is stronger than the previous claim
that a large layer jump or dry receiving cell makes parcel rain suspicious.
The laboratory separates three effects that cannot be inferred from those
diagnostics alone:

1. Splitting the same isolated ascent into shorter pressure steps adds a little
   condensate in the five wet cases: the one-jump result is 0.49–3.89% below
   an independently integrated moist-path reference. Simply shortening those
   jumps does not suppress the diagnosed excess summer rain in these cases.
2. Mixing with a finite dry environment can suppress condensation strongly,
   but mixing saturated warm and cold populations can create it. Neither
   perfectly unmixed air nor grid-average saturation is a universal rainfall
   bound. A fitted universal dilution multiplier would conceal this distinction.
3. Conservative numerical mixing alone can create rain in a manufactured
   transport problem whose exact inviscid answer is zero. Water/heat closure
   does not ensure correct cloud formation.

These results identify mechanisms and numerical failure modes. They do not
measure their contribution to California/Iberia rainfall error or establish
that a finer regional grid will improve the fantasy painting.

## Experiments and controls

### A fixed parcel ascent, without changing forcing

Every refinement retains the same starting state, full pressure drop and
liquid-only saturation law. A segment applies dry Poisson expansion followed
by the existing energy-coupled saturation adjustment. Expansion/compression
work is accumulated explicitly, rather than asserting constant enthalpy
during a prescribed pressure change.

The reference independently integrates the saturated temperature/work ODE
after locating first saturation on the dry path. It uses exact derivatives
of this project's saturation law and the same constant dry-air Cp/Lv. It is
neither an observed cloud nor a separate thermodynamic dataset. The 256-step
solution differs by at most 0.00134g/kg condensate and 0.00229°C across the
declared eight inputs, including dry/no-lift/zero-vapor controls.

An ascent/descent excursion also checks the declared instantaneous-removal
convention: the return parcel is drier after liquid has left. It introduces
no terrain circulation, hydrometeor drift or evaporation.

### Closed mixing with a finite environment

Two populations have fixed finite dry masses. Symmetric exchange conserves
their total vapor and sensible-plus-vapor enthalpy, rather than mixing a parcel
against an unlimited external reservoir. The same total exchange exposure
is distributed over all pressure intervals. Both populations traverse the
same declared manufactured pressure path; this is not a model of a plume
entraining a real environmental profile.

For one dry-environment lift, whole-mixture condensate falls from 0.45657 to
0.00982g/kg at 50% total exchange. For the isobaric saturated warm/cold pair,
50% exchange instead creates 0.54125g/kg from an initial zero-cloud pair.
The latter is a physical mixing-fog counterexample under the permitted
exchange, not a reason to delete every mixing-induced cloud.

### Actual vertical-grid comparison in a manufactured circulation

This is a separate experiment from subdividing one parcel trajectory. Two
closed equal-area columns cover 1000–500hPa. A common analytic circulation
rises in one and descends in the other. Column mass and initial vapor/energy
integrals match across 4, 8, 16, 32, 64, 128 and 256 layers. Fine horizontal
band fluxes sum to coarse fluxes; vertical fluxes match at shared interfaces.
The neutral dry hydrostatic profile uses analytic pressure-band integrals.
There is no external moisture input, evaporation or relaxation.

| Layer count | Bulk rain | Unmixed-rule rain | Difference |
|---|---:|---:|---:|
| 4 | 0.267085mm | 0.517523mm | +0.250438mm |
| 32 | 0.760928mm | 0.798584mm | +0.037656mm |
| 128 | 1.044480mm | 1.049440mm | +0.004960mm |
| 256 | 1.139513mm | 1.141168mm | +0.001654mm |

All runs cover one common column-mass/peak-flux timescale, about 7.08 toy
hours, from a finite 6.628mm vapor pool. These are not seasonal rainfall
rates. The same frozen potential-temperature/vapor transport kernel is used;
the two cloud rules reproduce its bulk and diagnostic unmixed concepts on
an arbitrary-layer toy geometry. The unmixed rule does not prognose two
separate populations through subsequent cell mixing.

The rule difference shrinks by about 99.3%, while total rain continues to
increase. From 128 to 256 layers bulk rain still rises 9.1%. **A small gap
between cloud rules is not evidence that either climate has converged.**
Halving the time step at 32/128 layers changes absolute rain by about
0.010/0.020mm; the cloud-rule difference changes by only 0.000056/0.000119mm.
These controls separate some temporal sensitivity from the larger grid
dependence, without claiming temporal or spatial convergence.

### Exact-answer periodic transport control

Saturated 20°C and 0°C air at 900hPa make one complete periodic translation,
with no ascent, imposed physical diffusion or external sources. Every parcel
keeps its initial state in the exact inviscid solution, so exact condensate
is zero. The periodic implementation uses the same first-order upwind stencil
as the frozen transport; it does not run the real open-boundary region.

| Cells | Upwind CFL 0.5 rain | Exact one-cell-shift control |
|---|---:|---:|
| 16 | 0.549843g/kg | 0g/kg |
| 32 | 0.405328g/kg | 0g/kg |
| 64 | 0.287878g/kg | 0g/kg |
| 128 | 0.203668g/kg | 0g/kg |
| 256 | 0.144051g/kg | 0g/kg |

Artificial averaging across the contact creates condensate even though its
water and heat budgets close. Refinement reduces this artifact slowly. CFL 1
is an exact cell shift on this uniform toy grid; **it is not a proposal to
increase the regional model's CFL limit**. Unlike the earlier closed pair,
this problem deliberately excludes physical exchange.

## Development decision

The next implementation should compare a less diffusive **conservative
transport** option against the frozen upwind control in this laboratory.
Transport potential temperature and vapor consistently with the same dry-mass
flux. Preserve the signed temperature/work ledger, positivity and closed
water accounting. Do not change cloud removal, source humidity or circulation
at the same time.

Before any annual case, require:

- An exactly transported dry/uniform state and a smooth passive-tracer
  convergence test with a known translated solution.
- Reduced artificial rain and convergent vapor/temperature error in the
  periodic saturated contact. Finite-resolution contact error need not be
  identically zero; the comparison must demonstrate its trend and cost.
- Closed two-column comparisons at common initial integrals and physical
  fluxes, with separate half-step checks and both existing cloud rules.
- No negative vapor or uncontrolled temperature/phase overshoot. A limiter
  or remapping method must not quietly use different moisture and heat routes.

The periodic fixture is a development diagnostic, not a way to choose a
regional scheme by one favourable rainfall number. If a candidate passes,
prepare a small fixed California/Iberia comparison with identical forcing and
protected winter/summer spatial responses. There is no new regional command
to run at this stage. Coherent winter weather remains a separate investigation:
none of these toy results closes the several-hundred-mm coastal winter deficit.

## Verification and artifacts

Forty-four new laboratory checks pass. Thirty-five existing focused pressure,
parcel and geometry checks also pass: **79 checks total**. They cover analytic
dry ascent, the independent moist ODE, saturated-start root handling, exchange
invariance, frozen endpoint dose, matching nested grids, closed circulation,
exact periodic translation and read-only/protected-output behavior.

Parcel paths/exchange close water to 5.90e-17kg/kg and enthalpy/work to
8.80e-10J/kg. Closed columns close water to 4.44e-15mm and diagnosed energy/work
to 7.45e-7J/m². This retains the prototype's liquid-only, constant-Cp/Lv and
zero exported precipitation enthalpy convention; it is not full moist-air
thermodynamics or a total-energy momentum model.

The cloud, local-humidity and geometry source fingerprints are unchanged.
The completed geometry manifest/state hashes also match the prior handoff.
No completed runner was invoked to obtain that check.

- [Saved numerical audit and figures](../output/v10_cloud_lab/audit.md)
- [Machine-readable results and source fingerprint](../output/v10_cloud_lab/audit.json)
- [Saved trajectories and contact fields](../output/v10_cloud_lab/paths.npz)
- [Parcel/closed-mixing implementation](../experiments/v10_cloud_lab.py)
- [Column/contact implementation](../experiments/v10_cloud_column_lab.py)
- [Audit entry point](../scripts/audit_v10_cloud_lab.py)

The lab applies the controlled-comparison method discussed in the
[cross-model research](model_precipitation_research_20261016.md), rather than
porting a large microphysics package. The independent pressure-path ODE is
related to the [moist-lapse equations documented by MetPy](https://unidata.github.io/MetPy/latest/api/generated/metpy.calc.moist_lapse.html),
with this project's exact saturation derivatives and constants.

The tiny audit is already complete. For reproducibility only:

```sh
.venv/bin/python scripts/audit_v10_cloud_lab.py --write
```

The user continues to run all real regional years, calibrations and long tasks.
The fantasy atlas stays unchanged, with the existing dry-zone protections;
NOAA six-hourly downloads remain paused.
