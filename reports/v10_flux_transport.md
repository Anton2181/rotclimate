# A coupled, less diffusive transport candidate

16 October 2026. The transport prototype is implemented in separate files and
passes its first manufactured comparisons. **False contact rain falls 26–54%
across the tested grids, and smooth-profile transport becomes substantially
more accurate, without changing the cloud adjustment.** These are numerical
results, not new regional climate or atlas scores.

Seventy fixed manufactured runs take seconds. Seventy-nine focused checks
pass, including 35 new transport checks and the 44 parent laboratory checks.
The fourteen upwind column controls match their saved parent results exactly.
All frozen climate sources and completed parent evidence remain unchanged.

## What the prototype does

The existing first-order upwind step supplies a conservative, positive
baseline. A centered explicit-midpoint flux proposes a more accurate transfer.
Local budgets bound the accepted correction at each face. **Theta and vapor
use one common face coefficient**, and the diagnostic temperature and passive
static-energy transfers reuse it. The coefficient is recomputed from the
local fields; it is not a cloud or rainfall parameter fitted to Earth targets.

This follows the general flux-correction approach of
[Zalesak (1979)](https://www.sciencedirect.com/science/article/pii/0021999179900512).
The use of limiting budgets and synchronized coefficients is also described
in [Möller, Kuzmin and Turek, sections 7.1–7.2](https://diamhomes.ewi.tudelft.nl/~mmoller/files/publications/TecRep221.pdf).
Our implementation is an explicit finite-volume prototype, not their
implicit finite-element Euler solver.

The mesh has fixed positive dry masses and balanced face fluxes. The outgoing
CFL remains at or below the existing 0.6 limit. Corrections enter one cell
and leave its neighbor in equal amounts. There is no post-update scalar
clipping. Bounded fields have a 64-machine-epsilon arithmetic allowance,
scaled independently for each field, with an exact zero lower floor.

That allowance matters: a nominally uniform 300K theta reconstructed from
energy can vary by roughly 1e-13K. Without an arithmetic allowance, those
differences can veto a genuine moisture correction through the shared
limiter. A dedicated regression now checks agreement with scalar vapor
transport on four nested neutral grids. A field with zero correction at a
face spends no limiting budget there.

## Known-answer transport results

The smooth test translates analytic cell averages around a periodic circuit.
The saturated warm/cold contact makes the same translation without ascent or
physical diffusion; its exact inviscid rain is zero. Both schemes use the
same time step and saturation law.

| Cells | Smooth theta MAE, upwind → candidate | False contact rain, upwind → candidate |
|---|---:|---:|
| 16 | 2.35557 → 0.53739K | 0.549843 → 0.405094g/kg |
| 32 | 1.35351 → 0.17883K | 0.405328 → 0.257584g/kg |
| 64 | 0.72811 → 0.05601K | 0.287878 → 0.164691g/kg |
| 128 | 0.37798 → 0.01547K | 0.203668 → 0.104774g/kg |
| 256 | 0.19262 → 0.00423K | 0.144051 → 0.066403g/kg |

Candidate smooth-error refinement orders rise from 1.59 to 1.87, while the
upwind controls approach first order. These measured orders apply to this
smooth case, not to every front or condensation problem. False contact rain
still exists and decreases under refinement; the candidate has not solved
the nonlinear subgrid mixing problem exactly.

Additional checks cover reversal, half steps, nonuniform cell masses, sharp
nonnegative tracers, affine relationships between fields, and a diagonal
two-dimensional periodic translation. All tests use manufactured inputs.

## Unchanged clouds in the closed rising circulation

The second comparison reuses the parent laboratory's two-column circulation,
its integral-preserving pressure grids, finite vapor pool and duration. Both
the bulk and unmixed cloud rules remain unchanged. No evaporation, external
moisture input, relaxation or terrain is added.

| Layers | Upwind bulk / unmixed rain | Candidate bulk / unmixed rain |
|---|---:|---:|
| 4 | 0.267085 / 0.517523mm | 0.578049 / 0.672321mm |
| 32 | 0.760928 / 0.798584mm | 1.343270 / 1.365644mm |
| 128 | 1.044480 / 1.049440mm | 1.431123 / 1.433814mm |
| 256 | 1.139513 / 1.141168mm | 1.404873 / 1.406009mm |

**Less artificial mixing makes this ascending example wetter**, even though
it reduces false rain at the isobaric contact. This is why the candidate
should be chosen for transport accuracy rather than whichever toy produces
less rain. The result supports testing whether excessive averaging destroys
moist ascending structures before grid saturation, but does not quantify
that effect in California or Iberia.

The candidate's 128→256-layer bulk rain changes by about -1.8%, compared with
+9.1% for upwind. Its refinement curve is not monotonic, so this does not
establish spatial convergence. At 128 layers halving the candidate step
changes bulk/unmixed rain by +0.01115/+0.00422mm, about 0.78%/0.29%.
A small difference between the cloud rules remains insufficient evidence of
convergence or validated cloud physics.

Periodic maximum water and enthalpy residuals are 8.67e-18kg/kg and
2.91e-10J/kg. Closed-column maximum water and diagnosed energy/work residuals
are 5.11e-15mm and 2.15e-6J/m². Signed temperature changes close independently.
As in the parent prototype, expansion work is diagnosed under prescribed
circulation and condensate leaves with zero exported enthalpy under the
declared constant-Cp/Lv convention. This is not full GCM energy closure.

## Next development and the eventual user-run comparison

The prototype currently **rejects open boundaries**. It has not been wired
into regional monthly forcing, checkpoints or annual integration. Therefore
there is no new regional command to run yet.

The next implementation should:

1. Add an open-boundary contract that retains identical prescribed incoming
   dry-air, vapor and theta fluxes in both controls. Begin with no high-order
   correction at external faces. Check inflow, outflow and reversed flow
   against independent water/heat accounts on manufactured domains.
2. Exercise realistic multidimensional geometry/flow shapes and measure cost
   on a larger manufactured mesh. The thin two-column timings are not an
   annual ETA. Keep the frozen upwind path as an exact regression control.
3. Check the interface to the original unmixed rule. Its donor-cell rain dose
   must never exceed the vapor actually available after corrected transport.
   The toy cases pass; that does not guarantee real-region compatibility.
   Retain rejection rather than clipping rain or quietly changing the rule.
4. After these controls pass, prepare a small fixed, resumable California/
   Iberia comparison for the user. Keep humidity, circulation and cloud rules
   paired. Compare coastal winter and dry-interior summer responses, not
   just aggregate rainfall. Do not commission another parameter sweep first.

This is the numerical transport branch of the research strategy. Coherent
winter weather remains a separate physical question; neither the prototype
nor these tiny tests closes the large regional winter rainfall deficit.
The fantasy atlas and its Mediterranean/dry-zone acceptance policy remain
unchanged. NOAA six-hourly downloads stay paused.

## Artifacts

- [Saved audit, full tables and figures](../output/v10_flux_transport_lab/audit.md)
- [Machine-readable results, parent evidence hashes and source identity](../output/v10_flux_transport_lab/audit.json)
- [Saved fields and trajectories](../output/v10_flux_transport_lab/paths.npz)
- [Transport implementation](../experiments/v10_flux_transport.py)
- [Common-forcing test adapters](../experiments/v10_transport_lab.py)
- [Test coverage](../tests/test_v10_flux_transport.py)

The tiny audit is already complete. Reproduce it only if desired:

```sh
.venv/bin/python scripts/audit_v10_flux_transport.py --write
```

All real regional simulations, calibrations and long tasks remain user-run.
