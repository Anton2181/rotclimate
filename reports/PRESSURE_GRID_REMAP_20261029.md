# Conservative lower-cell grid transfer: static results

All six declared static transfers pass independent checks of saved total water,
gas/surface/kinetic energy and vertically integrated face momentum. They start
zero climate integrations and do not measure rainfall skill.

| Region | First-cell parts | Old reference height m | New reference height m | Initial conversion rain mm |
|---|---:|---:|---:|---:|
| north india | 4 | 754.78 | 175.40 | 0.0089 |
| north india | 16 | 754.78 | 43.11 | 0.0092 |
| mexico | 4 | 745.22 | 173.22 | 0.0225 |
| mexico | 16 | 745.22 | 42.58 | 0.0234 |
| pacific nw | 4 | 731.72 | 170.07 | 0.0198 |
| pacific nw | 16 | 731.72 | 41.80 | 0.0201 |

Maximum independently reconstructed energy relative error is 2.127e-16;
water error is 2.422e-16. Every target-pressure phase rain
mass and actual liquid enthalpy is returned to the same surface before time zero.
This is initial conversion, not rain during a climate run.

The overlap operator assumes each source cell is piecewise constant. It transfers
extensive gas enthalpy and vapor by pressure overlap; target temperature follows
from those integrals. It does not invent an unobserved subcell lapse profile.
The fixed pressure lids preserve total dry mass. Refinement retains resolved
kinetic energy; the general coarsening operator reports its unresolved kinetic
variance separately without silently heating the atmosphere.

Eight new tests and an 86-test focused suite pass. Frozen original physics
sources remain unchanged. Raw source and target fields, literal protocol and
independent checks are retained in `output/pressure_grid_remap_20261029` and the
research atlas. No dynamic step, hydrostatic-balance test or calibration occurs.

The next literal protocol in `calibration/lower_cell_resolution_20261029`
declares nine 24-hour dynamic controls: four-way lower-cell subdivision at
900/450 seconds and sixteen-way subdivision at 900 seconds, in all three regions.
All six case preparations pass without integration. Pressure lids, planetary
parameters and physical closures remain fixed; no observed wind or humidity is
introduced. The wet 50 kg/m² state is the inherited baseline, not a state chosen
because of its rainfall. The ongoing fourteen-day initialization test is separate.

The next analysis will retain all outcomes and compare rain, evaporation, soil
water, temperature, budget closure and timestep sensitivity. Piecewise-constant
refinement changes resolved initial stability and flux geometry, so its response
is not proof of a better resolved climate. The sixteen-way case has no finer
timestep control in this first pilot. Surface-layer validity, terrain, upper
atmosphere and nonlinear momentum remain unresolved. No dynamic outcome from
this new protocol is known in this report. Earth r39 and normal maps are unchanged.
