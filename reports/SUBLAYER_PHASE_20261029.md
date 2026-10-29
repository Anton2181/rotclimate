# Conservative phase sublayers on an unchanged circulation grid

The new nested phase operator resolves saturation and rain evaporation on
finer vertical cells while retaining the existing momentum grid. It preserves
each parent cell's water and gas static energy during reconstruction and
restriction, including gravitational potential. The fine phase state is
returned for retention rather than silently replaced by coarse means.

On one fixed manufactured 16-cell parent column, eight phase sublayers reduce
the coarse temperature RMS difference against a 32-sublayer comparison from
0.002984 K to 0.0000342 K. The source available-energy difference on the same
coarse grid falls from 12.19% to 0.095%. This is convergence within a declared
reconstruction, not Earth rainfall accuracy or an adopted physics change.

## Why the comparison changed

The preceding native-grid exploration found that the phase-induced quadratic
available-energy norm rose about 16% between 16 and 256 levels while the first
dry wave speed changed only 0.3%. Different native-grid norms include different
amounts of vertical variation. That entire difference cannot be classified as
phase-solver error. Nor is quadratic available energy the same as latent heat
or total gas/rain energy.

The new experiment holds the parent water/energy state fixed and compares all
outputs on the same 16 coarse cells. It separates the momentum resolution from
the phase resolution. The input is the conservative restriction of one smooth
manufactured 512-layer reference. Every candidate then reconstructs from that
identical parent state using the same limited-linear shape assumption. The
512-layer candidate reconstructs from that parent too; it does not gain access
to the original fine humidity structure. It is a comparison, not ground truth.

## Reconstruction and restriction

Fine dry masses are supplied by the fixed hydrostatic reference and must sum
to the actual parent dry mass; mismatches are rejected without normalization.
Vapor mixing ratio and temperature slopes come from neighboring parent means
with minmod limiting. Shapes are centered on the actual fine dry-mass centroid.
If a vapor slope would make q negative, its magnitude is reduced while keeping
the parent water unchanged. This is a conservative reconstruction limiter, not
humidity clipping after a transport or phase calculation.

The actual parent energy is

    Hgas = (cp_d*Md + cp_v*W)*(T-T0) + Lv0*W
    Egas = Hgas + g*(Md+W)*z

An explicit parent-wise temperature offset makes reconstructed fine energy
sum to this value. A supplied temperature gradient is also allowed as a stated
shape, but does not become an unbooked heat source. The existing multilevel
phase kernel processes the fine column, including vapor/liquid heat capacity,
rain enthalpy, evaporation and terminal fall work.

Restriction sums fine dry mass, vapor and Egas, then diagnoses the coarse
energy-equivalent temperature at the coarse reference height. Ground rain
carries its actual fine lowest-layer liquid enthalpy. That temperature is not
silently replaced by the coarse mean temperature.

Energy-equivalent coarse means can lie above a single-cell saturation curve
even when every fine cell is valid. Saturation is nonlinear. No second coarse
condensation or water loss is imposed to hide that variation. The complete fine
post-phase state must be retained for future fine-grid steps. Reconstructing it
anew from coarse means every timestep would introduce mixing and discard
unresolved information; that is a separate physical closure, not an identity.

## Fixed-parent convergence and dynamical response

The shallow 8 km reference uses surface T=300 K, ps=101325 Pa, lapse 6 K/km,
an explicit 200 K cap, and pressure-derived dry masses. A 12-by-16 horizontal
manufactured humidity pulse is the same spatial construction as the previous
dry phase-pulse test. All candidates share the same 16 parent cells.

| Phase sublayers per parent | Fine levels | RMS coarse T difference K | Coarse source available energy m²/s² |
| --- | ---: | ---: | ---: |
| 1 | 16 | 0.00298411 | 0.00730737 |
| 2 | 32 | 0.00072203 | 0.00670110 |
| 4 | 64 | 0.00015713 | 0.00655541 |
| 8 | 128 | 0.00003424 | 0.00651953 |
| 16 | 256 | 0.00000923 | 0.00651590 |
| 32 | 512 | comparison | 0.00651334 |

Using the actual restricted temperature and vapor changes, the experiment
derives a virtual-buoyancy increment and spreads it over one hour of otherwise
unchanged dry dynamics. Three 1/8/32-sublayer sources drive separate six-hour
runs at 2.5-minute timesteps, for 432 dry steps. All use the same 16-level
Lorenz-grid dynamics, including the exposed pressure-invisible thermal mode.

The six-hour pressure RMS difference against the 32-sublayer source falls
from 0.033901 to 0.0002694 m²/s². East/south velocity RMS differences fall from
0.003955/0.003574 to 0.0000444/0.0000404 m/s. This shows numerical source
sensitivity on an identical dynamical system, not validated atmospheric winds.
All falling liquid reevaporates in this particular manufactured pulse.

## Verification and next work

Ten new tests verify independent parent water/static-energy reconstruction,
the actual supplied-gradient heat ledger, the exact no-refinement limit,
dry and raining column budgets, valid fine states with supersaturated coarse
means, retained-state equilibrium, invalid grids and dry-mass mismatches. The
full focused suite passes 259 tests.

Publication independently reconstructs the original parent water/energy,
all fine/coarse phase budgets, saturation, source buoyancy and its common-grid
available energy, hydrostatic pressure, final dry energy and the saved actual
midpoint source-work integrals. Parent, phase and water errors are below 1e-15
relative; dry final energy versus integrated source work is below 2e-14.
Raw fine/coarse arrays are available as a NumPy archive alongside JSON methods,
source hashes and independent checks in the research atlas.

This resolves a numerical phase-grid option, not interactive moist circulation.
The next step can choose fine resolution by a declared state/rain convergence
tolerance and test different physical columns, including surviving rainfall.
Retained fine state and conservative transport must then be coupled without
adding both dry adiabatic cooling and moist-static-energy expansion cooling.
The pressure-invisible dynamical mode, reference-maintenance energy, incoming
states, radiation, terrain and compressible effects still require decisions.

The operator is fixed-pressure, dilute, warm/supercooled liquid-only with
instantaneous terminal rain. Ice, clouds with stored liquid, finite fall time,
precipitation kinetic storage and a full nonlinear moist mechanical energy law
remain absent. Phase static energy and dry quadratic source work are checked
separately; their sum is not claimed as a complete coupled energy budget.

No Earth integrations were run. Earthr39 and normal world/biome/population
atlas datasets remain unchanged. Counters remain 1934 attempts / 1929 strict
passes / four historical failures / one historical interruption.
