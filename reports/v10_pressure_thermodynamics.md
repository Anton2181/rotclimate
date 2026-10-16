# Spatial-wind result: repair the dry thermodynamic transport law

15 October 2026. All four user-run spatial-wind cases settle in four cycles.
Sixteen saved cycles took 13.70 minutes. Source, input, configuration, completed
field hashes and recomputed summaries/settling were verified. None qualifies.
No atlas update is warranted.

## Completed spatial-wind result

| Region / humidity | Annual rain, uniform → spatial | Reference rain | Spatial coast / interior rain | Minimum-wet coverage |
|---|---:|---:|---:|---:|
| California / 0.8 | 309.2 → 24.2 mm | 401.8 mm | 37.7 / 8.5 mm | 41.3% |
| California / 1.0 | 512.5 → 47.3 mm | 401.8 mm | 73.2 / 18.0 mm | 59.1% |
| Iberia / 0.8 | 97.0 → 13.8 mm | 424.2 mm | 20.1 / 1.3 mm | 25.6% |
| Iberia / 1.0 | 193.5 → 21.6 mm | 424.2 mm | 27.8 / 12.7 mm | 34.9% |

At humidity 1.0, California monthly MAE falls from 41.66 to 29.88 mm, but
rainfall is only 11.8% of reference. Iberia MAE worsens from 32.07 to 34.91
mm, with rain only 5.1% of reference. California lower error accompanies severe
drying; it does not establish realistic rain placement. Most land remains far
too dry, with rain concentrated in a small number of cells.

Annual water residuals are below 3.16e-12 mm and energy residuals below
9.56e-6 J/m². Domain net moisture export is 94–99% of ocean evaporation in
these cases. This is a net budget comparison, not source attribution: without
water tags it cannot identify the origin of individual rain or export.
The failure could still involve monthly-mean forcing, missing storm covariance,
boundary humidity, vertical structure and numerical mixing. Spatial winds alone
do not resolve those mechanisms.

Saved-only review: `output/v10_spatial_review/review.json` and `review.md`.
Reproduce without climate integration:

```sh
.venv/bin/python scripts/review_v10_spatial_wind.py --write
```

## A demonstrated dry-law problem, rather than another rainfall knob

The current engine passively transports approximate moist static energy
m(cp*T + g*z) + Lv*water through prescribed horizontal/vertical air fluxes.
It then infers temperature by subtracting local potential and latent energy.
That is not a generally valid dry thermodynamic law for a prescribed flow
without the corresponding dynamical energy exchanges.

The dry atmospheric thermodynamic equation relates parcel temperature change
to parcel pressure change: DT/Dt = (Rd/cp) T/p Dp/Dt in adiabatic conditions.
Equivalently, potential temperature theta = T_K (p_ref/p)^(Rd/cp) is conserved.
The [ECMWF IFS equations, section 2.1, equation 2.3](https://www.ecmwf.int/sites/default/files/elibrary/2013/74361-ifs-documentation-cy38r1-part-iii-dynamics-and-numerical-procedures_1.pdf)
include this pressure-related thermodynamic term; moisture heat-capacity and
virtual-temperature effects give a more complete moist form. Our proposed
constant-dry-cp version remains an approximation, not the full IFS scheme.

Four independent manufactured probes now compare that dry law with the frozen
engine. They have no rain physics, evaporation, relaxation or seasonal feedback:

| Probe | Expected behavior | Frozen maximum error | New maximum error |
|---|---|---:|---:|
| Flat, constant pressure and temperature | No temperature change | 5.7e-14°C | 5.7e-14°C |
| Constant-pressure surface whose height changes along flow | No dry-adiabatic temperature change | 0.0130°C in 60 s | 5.7e-14°C |
| Hydrostatic dry-isentropic hill | Preserve constant theta | 5.7e-14°C | 1.1e-13°C |
| Donor-cell transfer across varying pressure | Mix donor theta, then convert at destination pressure | 0.00153°C | 1.7e-13°C |

The inclined isobar requires mechanical forcing to maintain prescribed steady
motion against its geopotential gradient. That forcing is part of the test's
explicit kinematic assumption; dry heating is not an automatic consequence of
changing height while pressure remains constant. The new diagnosed energy
exchange matches the analytic boundary potential-energy flux in this case.
The isentropic-hill control also shows that the old scheme was correct in an
important special limit; this is not a claim that every previous MSE result was
wrong.

Four further independent steps use the completed end-of-year states at their
periodic January boundary, keeping water transport and prescribed winds exactly
matched. The old/new upper-layer p95 temperature difference is about
0.0024–0.0028°C in a 60-second step. These snapshots show that the change acts
on the real model fields, not its effect on annual rainfall. Do not multiply
these changes by days or years to predict a climate response.

Audit evidence: `output/v10_spatial_review/pressure_law_audit.json`.
Reproduce without seasonal integration:

```sh
.venv/bin/python scripts/audit_v10_pressure_law.py --write
```

## Correcting the interpretation of the old heat split

Some saved horizontal/vertical terms reach tens of K/day with opposing signs.
These are conservative flux divergences; each contains a local scalar times
dry-mass divergence. The horizontal and vertical mass terms cancel because
layer mass is stationary. Their large separate magnitude is not evidence of
equally large physical heating or proof that one process causes the drought.
Earlier interpretations of a dominant negative horizontal contribution need
this qualification. The manufactured path tests remain separate evidence.

The new audit subtracts local dry-static-energy times mass divergence from
each old flux-divergence term. Their sum is unchanged, but the split now uses
donor-minus-local anomalies and does not acquire large cancelling contributions
from arbitrary constant offsets. The new transport records horizontal and
vertical temperature advection this way, with a separate pressure-expansion
term, relaxation, evaporation and condensation. Signed local closure is still
checked to 1e-9°C.

## Separate pressure-based implementation and energy policy

`experiments/v10_pressure_thermo.py` transports mass*theta with the exact same
dry-air fluxes used for vapor. It reconstructs temperature with the local Exner
factor (p/100000 Pa)^(287.05/1004). Water transport, saturation adjustment,
latent heating, soil/runoff, evaporation and relaxation retain the old closure.
No observed precipitation enters the engine and no fitted coefficient is added.

The saved state keeps the old energy representation for comparison. Its
transport energy change includes an explicit `prescribed_flow_work_j_m2`,
defined as the difference between pressure-based transport and passive old-MSE
transport. This records exchange with the unsolved prescribed circulation,
including pressure/geopotential effects and discretisation. The step and annual
energy ledger include it; there is no silent source or retroactive change to
old evidence. It is a diagnosed exchange, not an independently solved momentum
or kinetic-energy budget and not a claim of complete total-energy conservation.
Its magnitude and spatial structure must accompany any apparent rain gain.

## Next user-run comparison

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_pressure_thermo.py --run
```

Four new cases at 60 km and humidity 1.0: uniform and spatial winds in California
and Iberia. Reuse the four completed old-MSE controls from the storm/spatial
batches. The new comparison changes thermodynamic transport only; each wind
mode retains its exact mean flow construction, projection, geometry, boundary
moisture, initial state, thermal targets and old rate-one storm catalogue/seed.
This tests the correction under two distinct circulation backgrounds rather
than selecting one which already happens to favor it.

Estimated **15–30 minutes**, with a **one-hour invocation cap**, three to six
repeated cycles, monthly checkpoints and same-command resume. Default without
`--run` is read-only. Stop for diagnosis if numerical checks or bounded settling
fail. No downloads, optimization or atlas export.

Results go in `output/v10_pressure_thermo/`: immutable source/input/baseline
manifest, monthly/annual fields, exact field hashes, budgets including prescribed
flow work, theta-transport residuals, layer rain and the new six-process thermal
ledger, and separate coast/interior winter/summer responses. Historical source
fingerprints and broad screens remain intact. A broad screen pass is still
development evidence, not independent temperature or climate validation.

After the comparison, require adequate amounts and placement in both regions,
useful skill against zero rain, and no large unexplained energy exchange before
selecting further runs. If this physically motivated correction still leaves
severe drought, proceed to measured storm-conditioned moisture/thermal imports
and boundary forcing, not another blind storm-count sweep. It cannot by itself
solve the lack of transient covariance or the coarse vertical quadrature.

The fantasy thermal/circulation bridge remains outstanding. No reference-forced
Earth model can directly publish the fantasy atlas. Mediterranean, cold-dry and
hot-dry protections remain unchanged; the current validated atlas stays in place.

## Verification

76 focused tests pass, including the old projection/coordinate/upper-air tests
and new dry-law limits, analytic prescribed work, geopotential-shape independence
at fixed pressure, unchanged water transport, positive moist-step water,
water/energy/theta/temperature ledgers, CFL, both unchanged wind modes, exact
monthly resume and new work/process ledgers, read-only default and four-case
resume/provenance rejection.

Twelve independent actual-input January/July/active-storm steps also pass.
Maximum water error is 5.85e-16 mm, energy error 9.90e-9 J/m², theta-transport
error 5.27e-12 kg K/m² and signed-temperature error 2.03e-13°C. Protocol and
checks are saved in `output/v10_spatial_review/pressure_thermo_preflight.json`.
These are independent operator probes, not seasonal runs. The assistant started
no regional seasonal simulation or calibration and did not change the atlas.
