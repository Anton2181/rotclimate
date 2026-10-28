# Resolved liquid-phase and moist-static-energy composition

`multilevel_phase.py` moves the conservative phase/falling-water step onto the
same arbitrary vertical cells/interfaces as the new hydrostatic and transport
grids. `multilevel_moist.py` composes that phase step with native vapor and moist
static-energy transport. Winds are supplied; pressure/momentum feedback is not
yet closed. This is a resolved fixed-wind thermodynamic prototype, not a new
Earth forecast or claimed rainfall gain.

## Rain through every vertical cell

Cells are ordered upward from ground0. Rain is processed top to bottom and
carries its actual upstream liquid temperature. For liquid Lin entering a cell
at its upper interface and Lout leaving below, local terminal drag heat is

    g Lin (edge_above-zcenter) + g Lout (zcenter-edge_below)

All lost precipitation potential becomes local gas/liquid heat; stored drop
kinetic energy, ice, finite fall time and surface impact are omitted. Uniform
drag per fall distance is a specified reduced closure. The saturation root
includes its dependence on actual evaporation/condensation, not an after-the-
fact warming. With vapor change x, Lout=Lin-x, the existing enthalpy root uses
extra=g*Lin*cell_width and beta=g*(zcenter-edge_below).

Every cell retains dry/vapor/liquid heat capacity. Surviving rain reaches ground
at the lowest adjusted temperature and exports liquid sensible enthalpy. The
whole-column budget balances initial gas static energy as final gas static
energy plus ground rain enthalpy. Initial vapor equals final vapor plus rain.
Potential-energy release equals summed drag heating. The existing two-layer
kernel remains unchanged and is recovered as an exact limit.

## Resolved time step and physical sources

The composed step solves vapor and gas moist static energy with identical dry
donor fluxes, backward Euler and actual sources, then adjusts phase. Static
energy includes dry/vapor gravitational potential. Vapor injection carries its
temperature-dependent enthalpy and local potential energy; external heat and
boundary supplies are explicitly booked. Reaction1/dt represents time tendency,
not rainfall. No second adiabatic c²divU temperature adjustment is added.

Nine new tests (seven phase, two composition) verify exact old two-cell limits,
multi-interface water/energy/fall-work budgets, complete reevaporation, the
zero-height enthalpy limit, invalid geometry and actual external-source budgets.
Together with nine new multilevel transport tests and the previous199 focused
checks,217 tests pass this development round. Test-time numerical checks are
not Earth integrations or calibration attempts.

## Controlled repeated-step demonstration

`demo_multilevel_moist.py` uses32 vertical cells in an8km hydrostatic reference,
with surface theta300K,N0.01/s and ps101325Pa. The shallow domain keeps this
liquid-only test in warm/supercooled temperatures rather than pretending to
model the icy upper troposphere. It is an explicit test domain, not a fitted
Earth depth or a complete atmospheric column. Pressure-derived cell mass dp/g
is used as the reference density for the vertical mode. An initial small dry
thermal anomaly generates winds for6hours; those exact mode winds are then
held fixed for24hours of resolved moist transport/phase adjustment.

Initial relative humidity is a smooth0.8 to1.05 pulse. No observed humidity,
wind or rainfall, external water/heat or numerical humidity reset is supplied.
The closed case tracks cumulative ground rain and rain enthalpy and all
terminal drag heat. Four timestep sequences3/1.5/0.75/0.375hours test first-order
transport/phase splitting at fixed elapsed time. Differences against the finest
run are numerical refinement, not climate accuracy.

The passive15km moisture comparison and the actual dry adiabatic response
convergence audit are retained separately. Uniform-density mode response at
32levels is0.997592; stratified ascent/descent are1.01764/0.97845 there and
1.00932/0.98970 at64. Vertical resolution reduces the old box mismatch without
a fitted correction, but finite-grid thermodynamic/mode and mechanical-energy
consistency still require checks before bidirectional moist momentum coupling.

This model remains fixed-pressure/height, dilute, liquid-only and instantaneous
terminal fall. Supercooled liquid is a limiting approximation; no freezing,
melting, snow, cloud storage, predicted radiation, moving compressible density,
terrain or wind kinetic-energy feedback is supplied. Conservation of the
specified static-energy/rain ledger is not proof of a complete atmospheric
mechanical/first-law budget. The moist state is not yet driving momentum.
Earthr39 and normal atlas climates remain unchanged. Counters stay1934attempts
/1929strictpasses/four historicalfailures/one historicalinterruption.
